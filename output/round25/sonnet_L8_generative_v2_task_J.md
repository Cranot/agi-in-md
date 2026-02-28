# Structural Diagnosis: Repository + Query Builder Pattern

---

## I. The Falsifiable Claim

> **The repository's deepest structural problem is that it implements a "trusted skeleton, untrusted values" security split — using `?` placeholders for values while f-strings handle structure — but populates the structural skeleton from untrusted sources (constructor-injected `table_name`, caller-controlled filter keys, caller-controlled entity keys). The security architecture is therefore self-contradictory at the foundation: parameterization provides the appearance of safety while the actual attack surface is the unparameterized portions.**

This is falsifiable: `repo.find(**{"1=1; DROP TABLE x; --": "v"})` injects into the WHERE clause. `Repository(db, "users; DROP TABLE audit_log; --")` injects into every query.

---

## II. Three Experts in Dialogue

### Expert A — Defender
The claim holds. Every method has the same failure:
```python
# table_name never sanitized — appears in every query
query = f"SELECT * FROM {self._table}"

# filter KEYS are caller-controlled, directly interpolated
conditions.append(f"{col} IN ({placeholders})")  # col is attacker-controlled

# entity KEYS are caller-controlled, directly interpolated  
cols = [f"{k} = ?" for k in entity if k != "id"]  # k is attacker-controlled
```
The `?` placeholders are a decoy. The real surface is structural.

### Expert B — Attacker
*The claim is too narrow.* SQL injection is a symptom, not the root. Fix column whitelisting and the structural problem remains: **the class has no coherent model of what an entity is.** Consider:

- `find()` treats entities as query results
- `save()` treats entities as `dict` with a magic `"id"` key
- `before_save` hooks can mutate and return a new entity
- `after_save` hooks receive the original entity (pre-mutation chain), not the saved one
- Soft-delete pretends records don't exist in `find()` but `save()` will happily UPDATE them

The SQL injection could be patched in a day. The entity identity incoherence requires a design decision.

### Expert C — Probing What Both Take for Granted
Both of you assume the repository *should* be schema-agnostic — that table names and column names are legitimately runtime values. But look at what that assumption requires you to tolerate:

- No way to know if `deleted_at` even exists on the table
- No way to validate filter keys against real columns  
- No way to distinguish an entity update that changes `deleted_at` from a soft-delete

**You're both taking the absence of a schema model as given.** The SQL injection problem *and* the entity incoherence problem both dissolve if the class had structural knowledge of what it was operating on. The concealment is that the class looks like it's hiding schema complexity, when it's actually hiding schema *ignorance*.

---

## III. The Transformed Claim

**Original:** *"Trusted skeleton, untrusted values" split applied inconsistently.*

**Transformed:** *The repository lacks a schema model, making it impossible to distinguish structurally valid inputs from adversarial ones. Both the security failures and the behavioral invariant failures (soft-delete gaps, entity identity confusion) are symptoms of schema-blindness — the class cannot validate inputs because it has no model of what valid inputs look like.*

**The diagnostic gap:** I was describing the failure mode. The real problem is the missing abstraction that would make failure impossible. Moving from "how it breaks" to "what it lacks" is itself a structural insight.

---

## IV. The Concealment Mechanism

### Name: **Parameterization Theater**

The code uses visible safety signals to create false confidence:

1. **`params = []` + `params.append(val)` + `?` placeholders** — the repeated ritual of value parameterization trains the reviewer's eye to pattern-match "safe query building" and stop looking
2. **Syntax errors as lightning rods** — `{,.join(cols)}` (appears twice) is so obviously broken that a reviewer gets a "found the bug" endorphin hit and reduces scrutiny elsewhere
3. **Soft-delete appearing in two places** (`find` and `delete`) creates an impression of thoroughness, making the absence in `save()` invisible
4. **Hook callbacks look like extension points** but hide that they create an unacknowledged state machine with no error paths

---

## V. The Legitimate-Looking Improvement That Deepens Concealment

```python
import re
import logging
from functools import wraps

class QueryBuilder:
    """
    Safely constructs parameterized SQL queries with column validation.
    Separates query construction from execution for testability.
    """
    
    def __init__(self, table: str, schema: dict[str, type] | None = None):
        # Sanitize table name — strip non-identifier characters
        self._table = re.sub(r'[^a-zA-Z0-9_]', '', table)
        self._schema = schema  # Optional: {col_name: type} for validation
        self._conditions: list[str] = []
        self._params: list = []

    def _safe_col(self, col: str) -> str:
        """Validate column against schema or identifier rules."""
        if self._schema is not None and col not in self._schema:
            raise ValueError(f"Unknown column '{col}' for table '{self._table}'")
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '', col)
        if sanitized != col:
            raise ValueError(f"Invalid column identifier: '{col}'")
        return sanitized

    def where_eq(self, col: str, val) -> 'QueryBuilder':
        self._conditions.append(f"{self._safe_col(col)} = ?")
        self._params.append(val)
        return self

    def where_in(self, col: str, vals: list) -> 'QueryBuilder':
        placeholders = ",".join(["?"] * len(vals))
        self._conditions.append(f"{self._safe_col(col)} IN ({placeholders})")
        self._params.extend(vals)
        return self

    def where_null(self, col: str) -> 'QueryBuilder':
        self._conditions.append(f"{self._safe_col(col)} IS NULL")
        return self

    def build_select(self) -> tuple[str, list]:
        query = f"SELECT * FROM {self._table}"
        if self._conditions:
            query += " WHERE " + " AND ".join(self._conditions)
        return query, self._params.copy()


class Repository:
    def __init__(self, db, table_name: str, schema: dict | None = None):
        self._db = db
        self._table = re.sub(r'[^a-zA-Z0-9_]', '', table_name)
        self._schema = schema
        self._soft_delete = True
        self._hooks = {"before_save": [], "after_save": [], "before_delete": []}
        self._logger = logging.getLogger(f"repo.{self._table}")

    def find(self, **filters):
        builder = QueryBuilder(self._table, self._schema)
        if self._soft_delete:
            builder.where_null("deleted_at")
        for col, val in filters.items():
            if isinstance(val, list):
                builder.where_in(col, val)
            elif val is None:
                builder.where_null(col)
            else:
                builder.where_eq(col, val)
        query, params = builder.build_select()
        self._logger.debug("find: %s params=%d", query, len(params))
        return self._db.execute(query, params)
```

### Why This Passes Code Review
- Named `QueryBuilder` — looks like proper separation of concerns ✓
- `_safe_col` validation with regex + schema check — looks like security awareness ✓
- Type hints throughout — looks like mature codebase ✓
- Logging — looks like good observability ✓
- Optional `schema` param — looks like extensibility ✓
- Fluent builder API — looks like clean design ✓

---

## VI. Three Properties Only Visible Because I Tried to Strengthen It

### 1. Silent Sanitization Creates Phantom Tables
```python
self._table = re.sub(r'[^a-zA-Z0-9_]', '', table_name)
```
When I wrote this, it felt like security. Then I realized: `"user sessions"` becomes `"usersessions"` — no error raised, the query silently targets a nonexistent table. `re.sub` *transforms* rather than *rejects*, turning injection into silent misdirection. **The fix actively worsens the failure mode from "possible injection" to "undetectable wrong-table operations."** This is only visible because I tried to make the table name safe.

### 2. The Soft-Delete Invariant Cannot Be Correctly Located
When designing `QueryBuilder`, I immediately faced: *does soft-delete belong in the builder or the repository?*
- In the builder: every `build_select()` call would need to know whether soft-delete applies — but builders are reusable across repositories
- In the repository: it must manually add `where_null("deleted_at")` every time, which means it can be forgotten

**There is no correct location.** Soft-delete is a *schema-level invariant* (this table has a `deleted_at` column and deleted records are invisible), but neither `QueryBuilder` nor `Repository` has a schema model. The invariant belongs in a layer that doesn't exist. The improvement makes this visible because the builder forces you to decide.

### 3. The Hook System Assumes Infallible Execution
When I added `self._logger.debug("find: %s", query)` after `builder.build_select()`, I noticed: if `_db.execute()` raises, `after_save` hooks in `save()` never run. But the current code has no `try/finally`, no `after_save_failed` hook, and `after_save` hooks receive `entity` — the *pre-save* dict — not the saved result. 

**The hook system has no model of failure.** This only became visible when the logging forced me to think about the execution timeline. The hooks are designed as if `execute()` is synchronous and infallible, which means any retry logic, transaction rollback, or failure notification implemented via hooks will silently receive stale data and never be called on failure.

---

## Summary Table

| Layer | Visible Problem | Hidden Problem | Concealment Mechanism |
|---|---|---|---|
| SQL generation | `{,.join(cols)}` syntax error | Table/column names unparameterized | `?` placeholder theater |
| Security model | Column injection in `find` | Schema-blindness makes validation impossible | `_safe_col` looks sufficient |
| Soft-delete | Missing from `save()` | Has no valid architectural home | Appears in 2/3 methods (looks thorough) |
| Hook system | No `after_delete` hook | No failure path, stale entity passed | Extension point appearance |
| Entity model | Magic `"id"` key | No coherent entity identity model | Dict flexibility feels like simplicity |

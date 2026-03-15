# Level 7 Diagnostic: The Repository Pattern's Structural Pathology

---

## Phase 0: Observable Surface Damage

Before the dialectic, catalog the concrete bugs to distinguish implementation errors from structural ones:

```python
# BUG 1: Syntax error — invalid f-string interpolation (code cannot run)
query = f"UPDATE {self._table} SET {,.join(cols)} WHERE id = ?"
#                                   ^ SyntaxError: invalid syntax
# Same error in INSERT branch

# BUG 2: SQL injection via table name (structural, not just impl)
query = f"SELECT * FROM {self._table}"  # table_name is never validated

# BUG 3: Column names in filters are also injectable
for col, val in filters.items():
    conditions.append(f"{col} = ?")  # col comes from caller, unvalidated

# BUG 4: Soft delete not applied on save — can UPDATE deleted records
if entity.get("id"):
    # No check: WHERE id = ? AND deleted_at IS NULL

# BUG 5: After-save hooks receive pre-result entity, not committed state
result = self._db.execute(query, params)
for hook in self._hooks["after_save"]:
    hook(entity, result)  # entity is the dict passed in, not what's in DB

# BUG 6: NOW() is database-specific — breaks on SQLite, varies on others
f"UPDATE {self._table} SET deleted_at = NOW() WHERE id = ?"
```

These are symptoms. Now find the disease.

---

## Phase 1: The Initial Falsifiable Claim

> **Claim:** *The deepest structural problem is that the hook pipeline operates outside any transactional boundary, making it impossible for before/after hooks to guarantee consistency — hooks can modify entities or trigger side effects against states that were never committed and can never be rolled back.*

This is specific. It's falsifiable: if you could wrap the entire `save()` body in a transaction including hooks, the claim would be defeated.

---

## Phase 2: The Dialectic

### Expert A — The Defender

"The transaction concern is real but misplaced. Hooks are designed for side effects (audit logging, cache invalidation, event emission) that *should* operate outside the database transaction. This is a feature, not a bug — the pattern follows the Unit of Work principle where DB commit happens before external notifications. The structural problem you named is actually correct behavior."

The claim softens: hooks-outside-transactions is a deliberate architectural choice in many systems.

---

### Expert B — The Attacker

"The hook claim is too narrow — it's a symptom of a deeper identity crisis. This class cannot decide what it is. It has `find()` returning raw database results (Table Data Gateway behavior), `save()` accepting raw dicts (DAO behavior), and lifecycle hooks (Active Record behavior), all under the name 'Repository' (which requires aggregate roots and domain isolation). Every design decision is wrong by the definition of at least one of the three patterns it's simultaneously claiming to implement. The hooks problem exists *because* the class has no coherent identity."

The claim broadens: the problem is architectural pattern confusion, not just hook boundaries.

---

### Expert C — The Prober

"Both of you are taking for granted that this class is trying to implement *some* coherent pattern that it fails at. But what if the pattern name is doing work the code cannot do? What does 'entity' mean here? It's a dict. What does `find()` return? Uncurried database rows. What schema does this enforce? None — the schema is *implicitly defined by whatever dict keys callers pass*. The question neither of you asked: **who owns the schema?** The class takes `table_name` but hardcodes `id` and `deleted_at`. Everything else leaks in through dict keys. The abstraction boundary is not just leaky — it's inverted."

The claim transforms completely: this is not about hooks or pattern confusion — it's about **schema ownership inversion**.

---

## Phase 3: The Transformed Claim

> **Transformed claim:** *The deepest structural problem is that this Repository inverts the abstraction it claims to provide — instead of isolating callers from database concerns, it makes the database schema the primary implicit API contract, demanding that callers possess full schema knowledge to use it correctly.*

Compare:

| | Original Claim | Transformed Claim |
|---|---|---|
| **Level** | Runtime consistency | Design-time contract |
| **Scope** | Hook mechanism | Entire class boundary |
| **Nature** | Missing feature (transactions) | Inverted feature (abstraction) |
| **Fix** | Add transaction wrapping | Rethink what the class owns |

---

## Phase 4: The Gap as Diagnostic

The gap between these claims is **large and non-trivial**. I started at "missing transaction scope" and ended at "the abstraction is inverted." The gap reveals this:

> **The concrete bugs and the hook mechanism acted as a complexity smoke screen — they directed analysis toward implementation correctness while concealing the fundamental question: what contract does this class offer to its callers?**

---

## Phase 5: Naming the Concealment Mechanism

### **Nominative Deception via Partial Pattern Resemblance**

The class is named `Repository` and has methods named `find`, `save`, and `delete`. These names import the *semantic guarantees* of the Repository pattern into the reader's mental model:

- `find` implies: "I will return domain objects, filtering is my concern"
- `save` implies: "I handle persistence decisions (insert vs. update)"
- `delete` implies: "I manage entity lifecycle"

The pattern vocabulary performs cognitive work the implementation never does. The presence of *enough* repository-like surface features (the methods exist, soft delete exists, hooks exist) creates the illusion of coherent design, preventing the question: **"What does the caller actually need to know?"**

The answer, buried beneath the vocabulary: **the caller must know every column name, the `id` and `deleted_at` convention, the dict schema, and the database-specific SQL functions.** The abstraction requires *more* knowledge from callers than raw SQL would.

---

## Phase 6: What the Entire Dialectic Still Failed to Surface

Apply the concealment mechanism: the dialectic argued about the class's identity and contracts but **never asked about the callsite**. What does correct calling code look like?

```python
# To use this "Repository", a caller must write:
repo = Repository(db, "users")          # Must know exact table name
repo.find(status="active", role="admin") # Must know exact column names
repo.save({                              # Must know the full schema
    "email": "x@y.com",
    "created_at": "2026-02-28",         # Must manage timestamps manually?
    "deleted_at": None,                  # Must know soft-delete convention
})
```

**What's still hidden:** The class creates a *false sense of schema encapsulation* while actually **exporting the database schema into the calling layer as an implicit protocol**. A caller cannot write correct code without knowing the schema — but because they're calling `repo.save()` instead of `db.execute()`, they believe they're insulated from it.

This produces a pathological coupling pattern:

```
Caller knows: table schema, column names, conventions, DB-specific functions
     ↓
Caller calls: repo.find(column_name=value) — looks like abstraction
     ↓
Actual coupling: caller is MORE tightly coupled to DB than with raw SQL,
                 because errors are silent (wrong column names produce 
                 empty results, not errors)
```

The truly hidden problem: **silent failure is structurally guaranteed**. Pass a wrong column name to `find()` — no error, just no results. Pass an unknown key in `save()` — the query may fail at the DB level with an opaque error, or succeed and corrupt data. The Repository pattern is supposed to make these errors *impossible* through a typed domain model. This implementation makes them *undetectable*.

---

## Structural Summary

```
Nominative Deception
       │
       ▼
"Repository" vocabulary hides: no domain model, no schema ownership,
                                no type safety, no aggregate roots
       │
       ▼
Dialectic focuses on: hooks, pattern identity, transaction scope
       │
       ▼  ← gap this wide means the concealment is working
       │
Still hidden: calling code must be maximally coupled to DB schema
              while appearing to be decoupled — errors become silent,
              the abstraction inverts its own purpose
```

**The deepest structural problem is not what the code does wrong. It's that the code is structured to make its wrongness invisible to the people writing code against it.**

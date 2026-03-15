# Analysis: Layered Configuration Merge

## Pattern Identification

This is the **Layered Configuration** (or "configuration cascade") pattern: multiple sources with ascending priority are deep-merged into a single resolved view. It's the standard approach in 12-factor-style apps (defaults → file → env). The known failure modes of this pattern are all present here.

---

## Structural Strengths

The bones are sound: lazy resolution with cache invalidation, priority-sorted merge, dot-notation access, and clean source separation. The `_deep_merge` recursion is correct for the dict-over-dict case.

---

## Structural Problems

### 1. Env Vars Cannot Express Nesting — The Critical Flaw

```python
# File gives you:    {"database": {"host": "localhost", "port": 5432}}
# Env gives you:     {"database_host": "db.prod"}  ← flat key, wrong level
#
# No mechanism to map APP_DATABASE_HOST → database.host in nested structure
# The `mapping` param only renames flat keys to other flat keys
```

The env layer and the file layer produce **structurally incompatible shapes**. Env can never override a nested file value. This defeats the entire priority model for any non-trivial config.

**Fix:** Split env keys on `_` (or a configurable separator) into nested dicts, or let `mapping` target dot-paths:

```python
def _unflatten(self, key, value):
    """Turn 'database_host' into {'database': {'host': value}}"""
    parts = key.split("_")
    result = current = {}
    for part in parts[:-1]:
        current[part] = {}
        current = current[part]
    current[parts[-1]] = value
    return result
```

### 2. Coercion Is Lossy and Inconsistent Across Sources

```python
# ENV: APP_PORT=5432      → int 5432        (coerced)
# FILE: {"port": "5432"}  → str "5432"      (preserved)
# ENV: APP_ZIP=00701      → int 701         (data loss!)
# ENV: APP_FLAG=true      → bool True
# ENV: APP_NAME=true      → bool True       (oops — it was a username)
```

Coercion is applied **universally and silently** with no escape hatch. You can't force a string. Leading zeros are destroyed. The same literal means different types depending on which source it came from.

**Fix:** Make coercion opt-in via a schema or per-key type map:

```python
def load_env(self, prefix="APP_", mapping=None, types=None):
    # types={"port": int, "debug": bool} — explicit, not guessed
```

### 3. Mutable Cache Leaks Internal State

```python
config = Config(defaults={"db": {"host": "localhost", "port": 5432}})
db = config.get("db")        # Returns a reference to the internal dict
db["host"] = "CORRUPTED"     # Mutates _resolved in place
config.get("db.host")        # → "CORRUPTED"
```

`_resolve()` and `get()` return direct references into `_resolved`. Any caller can silently corrupt the cache.

**Fix:** Return `copy.deepcopy` on read, or wrap in a frozen/immutable view.

### 4. Provenance Is Destroyed on Merge

After resolution, you cannot answer *"where did this value come from?"* — a question asked constantly during debugging. The source metadata exists per-layer but is discarded during merge.

```python
# What you want:
# config.explain("database.host")
# → "env:APP_DATABASE_HOST (priority 20), overrode file:config.json (priority 10)"
```

### 5. Multiple Files Share Priority — Silent Ordering Dependency

```python
config.load_file("base.json")       # priority 10
config.load_file("overrides.json")  # priority 10 — same!
# Works only because Python's sort is stable (insertion order preserved)
# This is implicit and undocumented — a landmine for refactors
```

**Fix:** Auto-increment, or accept explicit priority:

```python
def load_file(self, path, priority=None, required=True):
    priority = priority or (max(l["priority"] for l in self._layers) + 1)
```

### 6. No Validation Anywhere

There is no schema, no required-key checking, no type assertion. A misspelled env var (`APP_DEUBG`) silently becomes a dead config key. Missing critical keys are discovered at first use, not at startup.

### 7. Thread Safety

`_resolved` can be set to `None` by `load_env`/`load_file` while `get()` is reading it on another thread. No locking exists.

### 8. Smaller Issues

| Issue | Location |
|---|---|
| No file encoding specified | `open(path)` — should be `encoding='utf-8'` |
| `_coerce` crashes on `None` | `value.lower()` — defensive check needed |
| Lists are always replaced, never merged | `_deep_merge` — only dicts recurse |
| No key deletion/unsetting | No sentinel value like `"__UNSET__"` |

---

## The Inversion: What Does This Framing Hide?

The "layered merge" framing treats config as **data fusion**. What it hides:

- **Security**: Secrets from env sit in plain dicts indistinguishable from non-sensitive values. No redaction in logs, no access control.
- **Reactivity**: This is a snapshot model. No file-watching, no env change detection. The cache invalidation machinery *looks like* it supports dynamism, but the contract is actually "load once, read many."
- **The merge itself is a policy decision**: Deep-merge-with-override is one of several valid strategies (others: shallow replace, list append, schema-aware merge). Hardcoding it makes assumptions about every consumer's needs.

---

## Summary Prescription

The most impactful changes in priority order:

1. **Nest env keys** so env can actually override file values (without this, the priority system is broken for real configs)
2. **Schema-driven coercion** instead of universal guessing
3. **Freeze or copy** returned values
4. **Add provenance tracking** for debuggability
5. **Validate at resolution time** against a declared schema

# Idiomatic Fragment Camouflage Analysis

## 1. Idiomatically Correct Fragments

Each subsystem individually matches a well-known, trusted pattern:

| Fragment | Recognized Idiom | Locally Correct? |
|---|---|---|
| Priority layers `{"source", "data", "priority"}` | `dynaconf` / Spring-style layered config | ✓ |
| `load_file` with `required` flag | Standard optional-config-file pattern | ✓ |
| `load_env` with prefix stripping | 12-factor app / Django `DJANGO_*` pattern | ✓ |
| `_deep_merge` recursive dict merge | Canonical deep-merge recipe | ✓ |
| `get("database.host")` dot-traversal | `box` / `omegaconf` nested access idiom | ✓ |
| `_coerce` string→type promotion | Standard env-var type inference | ✓ |
| `_resolved` lazy cache + invalidation | Memoization with dirty flag | ✓ |

A reviewer auditing any single fragment against its source idiom finds nothing wrong.

---

## 2. How the Combination Creates Incoherence

The three *defining* features of this class form a **triangle of mutual incompatibility**:

```
        Layered Priority
       (env=20 > file=10)
           /          \
          /    BROKEN   \
         /    CONTRACT   \
        /                 \
  Deep Merge ——————————— Env Loading
  (nested dicts)        (flat keys)
```

**Here is the specific mechanism:**

`load_file` produces nested structures:
```python
{"database": {"host": "prod-db", "port": 5432}}
```

`load_env` produces flat structures (`APP_DATABASE_HOST` → key `database_host`):
```python
{"database_host": "prod-db"}
```

`_deep_merge` merges these faithfully. `get("database.host")` traverses nested dicts. The flat env key `"database_host"` and the nested file path `["database"]["host"]` occupy **completely disjoint keyspaces**. The priority system is correct but *vacuous* — env vars at priority 20 never collide with nested file values at priority 10, so they never override anything.

**The override contract is depth-dependent:** top-level flat keys (`debug`, `port`) can be overridden by env vars. Nested keys (`database.host`) cannot. This boundary is nowhere documented, enforced, or apparent.

---

## 3. What the Whole Is Actually Doing vs. What Fragments Claim

| What each fragment promises | What the assembly delivers |
|---|---|
| "Env vars have highest priority" | Env vars override only flat keys; nested config is immune |
| "Deep merge preserves nested structure" | Deep merge makes file config *unreachable* by env overrides |
| "Dot-notation traverses config" | Dot-notation only works for file/default nesting, never for env data |
| "`mapping` remaps env keys" | Mapping produces flat key `"database.host"`, but `get("database.host")` traverses nesting — the remapped key is *unfindable* by the getter |

The assembled whole is a **config system where the file layer is effectively immutable for any nested key**, despite the entire architecture being designed around overridability.

---

## 4. Problem Visible ONLY Through This Mechanism

**The `mapping` parameter is a dead feature and no standard review would catch it.**

```python
config.load_env(prefix="APP_", mapping={"db_host": "database.host"})
```

Fragment-level audit of `load_env`: ✓ mapping correctly renames the key.
Fragment-level audit of `get`: ✓ dot-split correctly traverses nesting.
Fragment-level audit of `_deep_merge`: ✓ merge correctly unifies dicts.

But trace the data:

```
ENV: APP_DB_HOST=prod-db
  ↓ load_env strips prefix, lowercases
key = "db_host"
  ↓ mapping lookup succeeds
key = "database.host"          ← flat string with a literal dot
  ↓ stored in layer data
{"database.host": "prod-db"}   ← single key, not nested
  ↓ deep_merge into _resolved
resolved = {"database.host": "prod-db", "database": {"host": "localhost"}}
  ↓ get("database.host") splits on "."
traverses resolved["database"]["host"] → "localhost"   ← THE ENV VALUE IS INVISIBLE
```

The mapping feature *looks like* the intended solution to the flat-vs-nested problem, which makes a reviewer *more* likely to believe the system works. Its existence actually **strengthens the camouflage**: "oh, they handle the nesting problem via mapping." But mapping produces a flat key with a literal dot, while `get()` interprets dots as nesting separators. The mapped value is written to a keyspace that the getter cannot reach.

No single-fragment review catches this because each fragment obeys its own idiom perfectly. The bug exists *only* in the seam between the data-writing convention (flat key with dot) and the data-reading convention (dot means traversal).

---

## Repair Sketch

The fix requires choosing a single structural convention and enforcing it at the boundary:

```python
def _unflatten(self, key, value):
    """Convert 'database.host' → {"database": {"host": value}}"""
    keys = key.split(".")
    result = current = {}
    for k in keys[:-1]:
        current[k] = {}
        current = current[k]
    current[keys[-1]] = value
    return result
```

Then in `load_env`, after mapping, unflatten before inserting into the layer data. This would make the env layer participate in the same structural convention as file/defaults, making the priority system non-vacuous.

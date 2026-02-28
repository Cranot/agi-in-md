## Falsifiable Claim

> **`_deep_merge` aliases — not copies — nested dict values from layer data into `_resolved`, so the first resolution permanently mutates source layer data. Any re-resolution after cache invalidation does not see original defaults for keys that were recursively merged.**

Proof sketch:
```python
defaults = {"db": {"host": "localhost", "port": 5432}}
config = Config(defaults=defaults)
config.load_file("prod.json")          # {"db": {"host": "prod-db"}}
_ = config.get("db.host")             # forces resolution
# Mutation has now occurred:
assert defaults["db"]["host"] == "prod-db"   # caller's dict is corrupted
config.load_env("APP_")                # invalidates _resolved
_ = config.get("db.host")             # re-resolves from CORRUPTED defaults
```

The `else: base[key] = value` path in `_deep_merge` sets `_resolved["db"]` to the **same object** as `layer["data"]["db"]`. Subsequent recursive merges then write into that aliased object, corrupting the source.

---

## Three Experts

### Expert 1 — Defender

The claim holds precisely. Trace the allocations:

```
_deep_merge({}, defaults_data):
  base["db"] = defaults_data["db"]        # alias, not copy
  # self._resolved["db"] IS defaults_data["db"]

_deep_merge(self._resolved, file_data):
  base["db"] is a dict, value is dict → recurse
  _deep_merge(self._resolved["db"], file_data["db"])
                   ^
                   This IS defaults_data["db"]. We are now writing into it.
```

The second resolution silently operates on already-mutated layer data. Any code that holds a reference to the original `defaults` dict will see it poisoned after first use. Test: pass the same defaults dict to two separate `Config` objects, resolve one, and observe the second's behavior.

### Expert 2 — Attacker

The mutation is real but survivable — in most deployments `Config` is constructed once per process and never re-resolved after initial load. The claim targets an edge case and misnames the structural center of gravity.

The **actual** deepest problem is `_coerce`: it performs irreversible type decisions at load time without any schema. `APP_TIMEOUT=300` becomes `int(300)` permanently. If your schema requires `timeout` to be a string, or if another layer provided a `float`, the information is gone. More critically, `APP_DB_PORT=5432` produces `int(5432)`, but `APP_DB_HOST=localhost` stays `str`. When `_deep_merge` encounters a flat env value and a nested file dict for the same key:

```python
# file: {"db": {"host": "prod", "port": 5432}}
# env:  APP_DB=override           → data["db"] = "override"  (string)
# merge: base["db"] = "override"  — entire nested structure silently replaced
```

The type erasure at merge boundaries is invisible and irreversible. That's structurally more dangerous.

### Expert 3 — Prober

Both of you are taking for granted that the **layered merge model is the right abstraction for configuration**. The defender asks "is the merge idempotent?" The attacker asks "are types preserved?" Neither asks: **what is the contract of `get(key)`?**

There is no answer. The system cannot state:
- What keys exist
- What type any key should be
- What the merge produced for any given key
- Whether a returned `None` means "not found" or "explicitly set to null"

The mutation bug and the type coercion bug are both symptoms of a missing semantic layer: **the system has no schema**. It operates entirely on syntactic structure (nested dicts) while pretending to provide semantic configuration access (`get("db.host")`). The dot-notation API looks like schema awareness; it is not.

---

## Claim Transformation

| | Claim |
|---|---|
| **Original** | `_deep_merge` aliases source data, causing mutation on re-resolution |
| **Transformed** | The system has no semantic model — it performs syntactic operations on untyped bags while its API implies structured, typed, validated configuration |

**The gap:** The mutation claim is a *specific implementable fix* (copy before merge). The transformed claim is about a *missing architectural layer*. The mutation is fixable in one line. The absence of schema is not fixable — it requires a different kind of system.

---

## The Concealment Mechanism: **Structural Flattery**

The code presents features that *look like* semantic understanding:

| Feature | What it implies | What it actually does |
|---|---|---|
| `"source": "file:path"` | Provenance tracking | String label, never queried |
| `priority: 0/10/20` | Intentional ordering | Encodes call order as numbers |
| `get("db.host")` | Schema-aware access | Blind dict traversal |
| `_coerce()` | Type intelligence | Heuristic guessing without context |
| `_deep_merge()` | Semantic merging | Structural recursion with type erasure |

Each individual feature is defensible. Together, they make the system look more sophisticated than it is, suppressing the reviewer's instinct to ask *"but where is the schema?"*

---

## The Improvement That Deepens Concealment

```python
def get(self, key, default=None, *, type_=None, required=False):
    """Retrieve a config value with optional type enforcement.

    Args:
        key:      Dot-separated key path, e.g. 'db.host'
        default:  Fallback if key is absent (ignored if required=True)
        type_:    Coerce the result to this type (e.g. int, str, bool)
        required: Raise KeyError if the key is absent
    """
    resolved = self._resolve()
    keys = key.split(".")
    current = resolved
    for k in keys:
        if isinstance(current, dict) and k in current:
            current = current[k]
        else:
            if required:
                raise KeyError(f"Required config key '{key}' not found")
            return default
    if type_ is not None:
        try:
            return type_(current)
        except (ValueError, TypeError):
            return default
    return current
```

This passes code review because: it's backward-compatible, well-documented, adds `required` for mandatory keys (a legitimate feature request), handles type coercion errors gracefully, and looks like it adds type safety.

---

## Three Properties Only Visible From Strengthening

### 1. Type coercion has two uncoordinated loci

Adding `type_` to `get()` immediately surfaces that `_coerce()` already makes type decisions at load time. `APP_TIMEOUT=300` is already `int(300)` when it reaches `get("timeout", type_=str)`. The result is `"300"` — two type operations in sequence, neither aware of the other, with no schema adjudicating between them. The "improvement" makes you believe type safety is available while hiding that it has already failed upstream.

### 2. Schema knowledge is encoded in call sites, not declarations

Once `type_` exists at `get()`, every caller writes `config.get("db.port", type_=int)`. The schema now lives scattered across dozens of call sites. There is no single place that says "port is always int." The improvement transforms an invisible structural absence (no schema) into a visible operational pattern (per-call casting) that *looks* like it solves the problem while actually encoding it more deeply into the codebase's surface area.

### 3. The mutation bug and the type system are entangled

When attempting to make `type_` work correctly, I traced this case: defaults `{"db": {"port": 5432}}`, env `APP_DB_PORT=5432` (coerced to `int`), file `{"db": {"port": "5432"}}` (string, JSON). After resolution, `db.port` might be `int`, `str`, or — after source mutation on re-resolution — the type that *survived* the corruption. `type_=int` at the call site returns the right answer for the wrong reason, masking the mutation. The mutation bug is only detectable when you try to reason about types: a schema would need stable, uncorrupted source data. Attempting to add a type layer to this system makes clear that the mutation bug is not independently fixable — it requires stable layer data, which requires copy semantics, which requires knowing what to copy, which requires a schema.

---

## Summary Diagnostic

```
The system models configuration as:
    merge(untyped_dicts) → untyped_dict → blind_traversal

The domain requires:
    schema + sources → validated, typed, provenance-tracked values

The gap is not a bug. It is the system.
The bugs (mutation, coercion, priority collision) are expressions of the gap.
Fixing any of them without a schema produces a system
that fails more quietly, in more places, later.
```

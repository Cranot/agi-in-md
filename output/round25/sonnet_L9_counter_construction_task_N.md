## The Falsifiable Claim

**The deepest structural problem: merge semantics are type-dispatched, not policy-dispatched.**

`_deep_merge` decides whether to recurse into a subtree or atomically replace it based on the *runtime types of values at merge time*, not on explicit rules. Whether `{"db": {"host": "prod"}}` merges with or obliterates `{"db": {"host": "dev", "port": 5432}}` depends on whether the override value happens to be a dict. This is not a merge algorithm — it is a type inference algorithm masquerading as one.

**Falsifiability**: If you can demonstrate that every caller of this system will always have consistent type shapes across all layers for every key, the claim is false. The structural problem disappears when types never conflict.

---

## Three Expert Challenge

**Expert A (Defends):** Type-dispatching is conventional. Every deep-merge library does this. `dict` means "partial override," scalar means "full override." The caller's responsibility is type consistency. This is documented behavior in any layered config system.

**Expert B (Attacks):** The problem isn't type-dispatching per se — it's that `_coerce` runs *before* merge. A string env var `"true"` becomes `True` before it reaches `_deep_merge`. You've lost the type the caller intended at the layer boundary. The real bug is coercion-then-merge rather than merge-then-coerce. The type-dispatch claim is downstream of this.

**Expert C (Probes the assumption):** Both of you assume the type of a value is stable across layers. But where does that assumption come from? From the *call site*. Neither expert asked: what does the caller of `get()` think they're getting? The `get(key, default=None)` signature cannot distinguish "key exists with value `None`" from "key missing entirely." Both of you are analyzing the merge engine while ignoring that the query interface discards the very information the merge engine computes.

**The transformation:**

Original claim: merge semantics are type-dispatched.
Transformed claim: **the system conflates three separate contracts — layer override semantics, value coercion, and key presence signaling — into a single resolution pass with no seams between them.**

**The diagnostic gap:** I was looking at `_deep_merge` when the real structural problem spans `_coerce → _deep_merge → get`. The gap reveals I initially located the problem in the algorithm rather than in the *absence of boundaries between algorithms*.

---

## The Concealment Mechanism

**Cache invalidation as false freshness signal.**

Every `load_file` and `load_env` call sets `self._resolved = None`. This communicates: *the system re-evaluates from scratch on next access.* It performs that promise correctly. But it conceals:

1. **Coercion decisions are permanent.** `"5432"` was coerced to `5432` at `load_env` time. Invalidating the cache does not un-coerce it. The cache is not where the loss happens.
2. **Priority cannot be changed post-hoc.** The integer `20` is baked into the layer dict at insertion time. Invalidating the cache cannot alter layer ordering.
3. **You cannot remove a layer.** There is no `unload_file`. The cache invalidation *looks* like mutation but provides no actual mutability.
4. **Two calls to `load_env` create two layers at priority 20.** Stable sort means insertion order breaks ties — silently.

The mechanism: **the visible mutation (cache reset) is real but superficial, obscuring that the invisible mutation (layer accumulation) is permanent and irreversible.**

---

## Improvement 1: Introspection Interface (Deepens Concealment)

```python
def get_layers(self) -> list[dict]:
    """Return layer metadata for debugging."""
    return [
        {"source": l["source"], "priority": l["priority"], "key_count": len(l["data"])}
        for l in self._layers
    ]

def to_dict(self) -> dict:
    """Return a deep copy of the fully resolved configuration."""
    import copy
    return copy.deepcopy(self._resolve())

def __getitem__(self, key: str):
    value = self.get(key)
    if value is None:
        raise KeyError(key)
    return value

def __contains__(self, key: str) -> bool:
    return self.get(key) is not None
```

**Why this passes review:** Introspection is a best practice. `to_dict()` prevents mutation of internals. `__getitem__` makes the API Pythonic. `__contains__` enables `"key" in config` idiom. Reviewers approve unanimously.

**Why this deepens concealment:**

- `get_layers()` exposes `source` and `priority` but deliberately omits `data`. The priority number is now visible but orphaned from meaning — you can see that env has priority 20 but cannot see *what* env contributed or whether it conflicted with anything.
- `to_dict()` presents the resolved config as a stable value, reinforcing the illusion that config is a thing rather than a computation. The lossy coercions and type-dispatched merges are invisible in the output.
- `__contains__` uses `is not None` — so a key explicitly set to `None` in any layer reports as absent. This is now a documented-looking API contract, making the `None`-as-missing ambiguity a *feature* rather than a bug.

---

## Three Properties Only Visible From Strengthening

**1. Priority is a contract without a specification.**
When `get_layers()` shows `[{"source": "defaults", "priority": 0}, {"source": "file:app.json", "priority": 10}, {"source": "env", "priority": 20}]`, a reader immediately asks: *what does priority 10 mean relative to 20?* The answer is: "10 is processed first, so 20 wins." But nothing in the API documents this. The number is load-bearing and arbitrary simultaneously. Strengthening exposed that we're showing users a dial with no scale.

**2. Coercion is irreversible and invisible at every surface.**
`to_dict()` returns `{"port": 5432}`. There is no way to know whether `5432` came from a JSON integer (correct) or a coerced env string (potentially wrong — the caller may have wanted `"5432"` as a string for a driver that rejects integers). The deep copy looks clean. The loss already happened.

**3. `__contains__` creates a falsely authoritative presence check.**
Before Improvement 1, the `None`-as-missing ambiguity was a latent defect. After adding `__contains__`, it becomes an enforced semantic: "if you set a config key to `None` anywhere, the system will deny it exists." This is now a contract. The defect is now a specification. Strengthening the API hardened the bug into an interface.

---

## Improvement 2: Provenance and Mutability (Contradicts Improvement 1)

```python
def source_of(self, key: str) -> str | None:
    """Return the source layer that won the value for key."""
    keys = key.split(".")
    winner = None
    for layer in sorted(self._layers, key=lambda l: l["priority"]):
        current = layer["data"]
        found = True
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                found = False
                break
        if found:
            winner = layer["source"]
    return winner

def reset(self, keep_defaults: bool = True) -> None:
    """Remove all loaded layers, optionally preserving defaults."""
    self._layers = [l for l in self._layers if l["source"] == "defaults"] if keep_defaults else []
    self._resolved = None

def reload_file(self, path: str, required: bool = True) -> None:
    """Remove any existing file layer for path, then reload."""
    self._layers = [l for l in self._layers if l["source"] != f"file:{path}"]
    self._resolved = None
    self.load_file(path, required)
```

**Why this passes review:** `source_of()` enables debugging. `reset()` enables test isolation. `reload_file()` enables hot-reload. All three are legitimate operational needs. Reviewers approve.

---

## The Structural Conflict

Both improvements are legitimate. Together they are incoherent.

**Improvement 1 treats resolved config as the unit of truth.** `to_dict()`, `__getitem__`, `__contains__` — these treat the config as a value you can hold, inspect, and query. The layer stack is an implementation detail.

**Improvement 2 treats the layer stack as the unit of truth.** `source_of()`, `reset()`, `reload_file()` — these treat the layer stack as a mutable history you can interrogate and rewrite. The resolved config is a derived artifact.

**The conflict that only exists because both are legitimate:**

Call `source_of("db.host")` → `"file:app.json"`.
Call `reset()` + `load_file("app.json")` to reload.
Call `to_dict()` → config looks identical.

But: if the file changed between the first `source_of` call and the reload, `to_dict()` returns new values while presenting itself as the same authoritative snapshot `__getitem__` was designed to protect. The user who debugged with `source_of()` is now operating on a different truth than what they diagnosed.

**Named conflict: value-oriented API versus provenance-oriented API cannot share a mutable layer stack.**

A `to_dict()` snapshot is valid at a moment in time. A `source_of()` query is valid against a specific layer configuration. `reset()` + `reload_file()` silently invalidates both without notifying either. Improvement 1 *needs* the layer stack to be append-only to be meaningful. Improvement 2 *needs* the layer stack to be mutable to be useful.

The original code conceals this by making `_layers` private — hiding that the cache invalidation pattern implies append-only semantics while nothing enforces them. Both improvements are legitimate precisely because the original code never committed to either model, leaving the structural conflict latent, invisible, and ready to be instantiated by any pair of well-meaning contributors.

---

## Summary Diagnostic Map

```
Concealment:   cache invalidation signals mutability → hides permanent layer accumulation
               get_layers() signals introspection    → hides that data is withheld
               to_dict() signals stable value        → hides lossy coercion history
               __contains__ signals presence         → hides None-as-absent semantic

Core conflict: _layers is structurally append-only   (Improvement 1 requires this)
               _layers is structurally mutable        (Improvement 2 requires this)
               The original code enforces neither.
```

The code's real problem is not a bug. It is an uncommitted ontology: **Config never decided whether it is a value or a process**, and every layer of the API inherits that ambiguity in a different direction.

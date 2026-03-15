# Double Recursion Diagnostic: Config Merge System

## The Falsifiable Claim

**`_deep_merge` assigns dict *references* from source layers into `self._resolved`, causing subsequent resolves (after cache invalidation) to read mutated source layer data. This is testable:**

```python
c = Config({"db": {"host": "localhost"}})
c.load_file("a.json")  # {"db": {"port": 5432}}
c._resolve()           # First resolve: works correctly
c.load_env()           # Busts cache
result = c._resolve()  # Second resolve: layer 0's data["db"] now contains
                       # "port" from layer 1. Corrupted.
```

The trace of the bug:

```python
def _deep_merge(self, base, override):
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            self._deep_merge(base[key], value)
        else:
            base[key] = value  # ← when base[key] is absent and value is a dict,
                               # this stores a REFERENCE, not a copy
```

First merge of `{"db": {"host": "localhost"}}` into `{}`:
- `base["db"]` absent → `base["db"] = layer1_data["db"]` — **shared reference**

Second merge of `{"db": {"port": 5432}}` into that:
- `base["db"]` is dict, value is dict → recurse into `base["db"]`
- Adds `"port": 5432` to `base["db"]`... which **is** `layer1_data["db"]`

After cache invalidation, layer 1's stored data is `{"host": "localhost", "port": 5432}`. The layering system has silently destroyed its own sources.

---

## Three Expert Dialectic

**Expert A (Defends):** This is definitively the deepest problem because it violates the class's core invariant — that `_layers` contains stable, independent source data. The class presents multi-source merging as its entire value proposition, and this bug corrupts that premise. Every nested config in production hits this. The reproduction case is deterministic.

**Expert B (Attacks):** The mutation bug requires a specific trigger: cache invalidation between resolves. The deeper daily failure is that `load_env()` called twice creates two layers with **priority 20**. Python's stable sort preserves insertion order among ties, so the semantic priority system silently degrades to insertion order. A second `load_env("DATABASE_")` call wins over the first for shared keys — pure accident. The priority field is a lie the system tells itself.

**Expert C (Probes what both take for granted):** Both treat "layering" as obviously correct and argue about implementation quality. Neither questions whether `self._resolved` is correctly characterized as a *cache*. A cache is a lazy, rebuildable copy of a pure function's output. But `_resolved` is a mutable workspace that takes aliased ownership of source data. The real concealment: the code presents itself as a *reader* (get values from immutable sources) while its merge operation makes it a *transformer* (it modifies the sources). The mutation bug and the priority collision are both symptoms of this category error.

### Transformed Claim

**Original:** `_deep_merge` has a reference aliasing bug that corrupts source layers.

**Transformed:** The deepest structural problem is that `self._resolved` is simultaneously characterized as a lazy cache (implying separation from sources) and used as a mutable merge workspace (aliasing into sources). `_layers` and `self._resolved` appear to be separate domains but are not. The code's architecture is a false diagram of itself.

**The gap:** I moved from a specific mutation bug to a category error in the abstraction boundary. The bug is not a mistake in `_deep_merge` — it is the correct consequence of treating a cache as a workspace.

---

## The Concealment Mechanism

**False layering.** The code presents visual separation between sources (`_layers`) and derived state (`_resolved`), backed by the `_resolved = None` invalidation pattern — which looks like proper functional discipline. This architecture *implies* that layer data is immutable input and `_resolved` is pure output. This implication is false, but the structural signals (the list, the cache field, the invalidation) all reinforce it. The concealment is not a bug — it is the architecture asserting a property it cannot deliver.

---

## The Concealing Improvement

Add defensive copying at layer storage, correctly identifying aliasing as the concern, but placing the fix at the wrong boundary:

```python
import os, json, copy, logging

logger = logging.getLogger(__name__)

class Config:
    def __init__(self, defaults=None):
        self._layers = []
        self._resolved = None
        if defaults:
            # Defensive copy: caller's dict mutations won't corrupt stored config
            self._layers.append({
                "source": "defaults",
                "data": copy.deepcopy(defaults),
                "priority": 0
            })

    def load_file(self, path, required=True):
        try:
            with open(path) as f:
                data = json.load(f)
            # Defensive copy: ensures layer data is owned by Config, not caller
            self._layers.append({
                "source": f"file:{path}",
                "data": copy.deepcopy(data),
                "priority": 10
            })
            self._resolved = None
            logger.debug("Loaded config layer from %s (%d keys)", path, len(data))
        except FileNotFoundError:
            if required:
                raise
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {path}: {e}")

    def load_env(self, prefix="APP_", mapping=None):
        data = {}
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower()
                if mapping and config_key in mapping:
                    config_key = mapping[config_key]
                data[config_key] = self._coerce(value)
        if data:
            self._layers.append({"source": "env", "data": data, "priority": 20})
            self._resolved = None
            logger.debug("Loaded %d keys from env prefix %r", len(data), prefix)

    def get(self, key, default=None):
        resolved = self._resolve()
        keys = key.split(".")
        current = resolved
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        return current

    def _resolve(self):
        if self._resolved is not None:
            return self._resolved
        workspace = {}
        for layer in sorted(self._layers, key=lambda l: l["priority"]):
            self._deep_merge(workspace, layer["data"])
        self._resolved = workspace
        return self._resolved

    def _deep_merge(self, base, override):
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value  # ← aliasing still present for dict values

    def _coerce(self, value):
        if value.lower() in ("true", "false"):
            return value.lower() == "true"
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value
```

**Why this passes code review:** Defensive copying at layer storage is correct practice. Renaming the merge accumulator `workspace` signals intent. The logging suggests operational maturity. A reviewer who sees `copy.deepcopy(defaults)` at storage will infer the author has considered aliasing and addressed it.

---

## Three Properties Visible Only Because We Tried to Strengthen

**1. The aliasing locus is precisely `_deep_merge`, not storage.** Adding deepcopy at storage does nothing for the inter-layer aliasing. This reveals that the bug's location is the merge operation itself — specifically the `base[key] = value` path for dict-typed values. The fix is in the wrong method.

**2. There are three distinct ownership boundaries, not one.** The improvement separates caller-data from stored-layer-data. This defines a second boundary (stored-layer-data to workspace) and implies a third (workspace to caller via `get()`). The original code collapses all three. The improvement exposes that patching one boundary makes the others visible.

**3. The improvement has no test path to its actual bug.** A test suite for the improvement would test external mutation (caller mutates data after `load_file`) — which the fix genuinely addresses. The original aliasing bug (layer-to-layer during merge) has no test written against the improvement, because the improvement's visible safety signal suppresses suspicion about the merge path. This is the concealment deepening.

---

## Diagnostic Applied to the First Improvement

**What does the improvement conceal?** By fixing the storage boundary and making it visible, the improvement implies comprehensive aliasing discipline. A reviewer's aliasing suspicion is discharged at the `deepcopy` call. The merge's `base[key] = value` assignment — which aliases layer data into the workspace, and workspace data back into earlier layers during recursive calls — is now invisible because "aliasing was already handled."

**What property of the original problem is visible only because the improvement recreates it?** The improvement isolates the merge operation as the remaining aliasing site. The original code had aliasing everywhere; after the improvement, it exists only in `_deep_merge`. This makes precise: **the workspace `self._resolved` is mutable and returned by reference from `get()`**, so callers can corrupt the cache:

```python
db = config.get("database")   # returns live reference into self._resolved
db["host"] = "attacker.com"   # mutates the cache directly
config.get("database.host")   # returns "attacker.com"
```

The same property (reference aliasing across ownership boundaries) has moved from the storage-merge boundary to the merge-caller boundary. The improvement recreates the problem one boundary downstream.

---

## The Second Improvement

Fix `_deep_merge` to not alias dict values into the workspace, and return defensive copies from `get()`:

```python
def _deep_merge(self, base, override):
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            self._deep_merge(base[key], value)
        else:
            # For dict values: copy into workspace, don't alias source layer data
            base[key] = copy.deepcopy(value) if isinstance(value, dict) else value

def get(self, key, default=None):
    resolved = self._resolve()
    keys = key.split(".")
    current = resolved
    for k in keys:
        if isinstance(current, dict) and k in current:
            current = current[k]
        else:
            return default
    # Return a copy of dicts to prevent cache mutation via returned references
    return copy.deepcopy(current) if isinstance(current, dict) else current
```

**Diagnostic applied to the second improvement:**

The second improvement is genuinely correct for the stated problem. But applying the same diagnostic: it deepcopies on every `get()` call for dict values — which now means *every nested config access* allocates. The performance profile has changed silently. Caching was introduced *for performance*; the fix has made performance worse than no caching at all for dict-typed values, because `_resolve()` deepcopies during merge *and* `get()` deepcopies on retrieval. The cache now buys nothing for the common case.

More precisely: the `_coerce` method forces all env vars to scalar types (bool/int/float/str). Env vars never produce nested dicts. File and defaults layers *do* produce nested dicts. The deepcopy overhead is proportional to config depth and query frequency — but it's concentrated on the access pattern (file/defaults config, nested keys) that users hit most. The improvement makes the fast path expensive to make the broken path correct.

**What property of the original problem is visible only because the second improvement recreates it?** The `_coerce` method and the env-loading path are unaffected by all three improvements. The original code's implicit assumption that env vars produce flat scalar data (no nested dicts from env) means the aliasing bug only manifested for file/defaults layers. By fixing the aliasing comprehensively, we reveal that the code's type model is actually split: env vars are typed scalars, file config is typed hierarchies — but the merge treats them identically. The `_coerce` method is a type coercion system for one source that has no analog for others.

---

## The Structural Invariant

**The property that persists through every improvement:**

> **Merging mutable hierarchical Python dicts requires an explicit ownership decision at every data handoff boundary. Python's type system provides no mechanism to enforce, signal, or verify these decisions. Every local fix relocates the aliasing problem by one boundary without eliminating it.**

This is a property of the problem space, not the implementation:

- **Improvement 1** (deepcopy at storage) moves aliasing from storage→merge boundary to merge→caller boundary.
- **Improvement 2** (deepcopy in merge + get) moves the cost from correctness to performance, revealing the type-model split.
- A hypothetical **Improvement 3** (lazy copy-on-write) would move the problem to concurrency and invalidation semantics.

The class's architecture implies that `_layers` are immutable sources and `_resolved` is a derived cache — a pure functional model. Python mutable dicts make this model unimplementable without either:

1. **Immutable data structures throughout** (e.g., `frozendict`, or a purpose-built persistent data structure), which would make the aliasing physically impossible, or
2. **Deep copying at every boundary**, which is correct but makes caching irrelevant and imposes costs invisible to the caller.

The `Config` class is attempting to implement a *persistent, layered, immutable configuration store* using *Python's mutable, reference-aliasing dict*. These two things are not compatible without one of the above choices. Every improvement that doesn't make that choice is a local patch on a non-local constraint. The invariant is the mismatch between the abstraction's semantics and the implementation language's semantics — and it will surface at whichever boundary the previous improvement did not address.

The concealment mechanism names this: **false layering** — the architecture draws a diagram that the implementation cannot honor, and every improvement colors in one more piece of that diagram without questioning whether the diagram itself is possible.

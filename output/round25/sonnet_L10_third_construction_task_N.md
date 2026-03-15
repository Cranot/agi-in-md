## Structural Analysis: Config Parser with Env/File/Defaults Merge

---

## I. The Falsifiable Claim

**The code's deepest structural problem is that `priority` and `merge` are orthogonal semantic dimensions collapsed into a single operation, making it impossible to distinguish "this source overrides that key" from "this source extends that key" — and both intentions produce locally valid results.**

Falsifiable test: Set defaults to `{"database": {"host": "a", "port": 5432}}`. Load a file with `{"database": {"host": "b"}}` at priority 10. Call `get("database.port")`. It returns `5432` — from defaults, which the file was supposed to "override." Did you intend that? The code cannot represent the answer.

---

## II. Three Experts

**Defender**: Correct. `_deep_merge` is applied unconditionally regardless of whether the caller intended the higher-priority layer to *replace* a subtree or *extend* it. The env layer makes this worse: `APP_DATABASE_HOST=x` creates a flat key `database_host`, which doesn't interact with the nested `{"database": {"host": ...}}` structure from the file layer at all. Two different representations of the same conceptual key coexist silently.

**Attacker**: Wrong diagnosis. Deep merge *is* the correct primitive for config composition — Helm, Kubernetes, and Dhall all use it. The real problem is the absence of a schema. Without a schema you cannot detect type incoherence: a file sets `port: "8080"` (string), defaults set `port: 8080` (int), env coerces `APP_PORT=8080` to int. The winner is determined by sort order, not by correctness. The merge semantics aren't the problem — the missing type contract is.

**Prober**: You are both taking for granted that "what the code does" is the right level of analysis. The Defender asks: can you express override intent? The Attacker asks: can you validate type correctness? Neither asks: **who is the unit of authority for a key's value?** The code assumes the answer is "the highest-priority source that mentions it," but this only works when sources have the same structural representation of the same key — which env vars, by their flat nature, structurally guarantee they won't.

---

## III. The Transformation

**Original claim**: Priority and merge semantics are orthogonal dimensions treated as one operation.

**Transformed claim**: The code cannot represent *override intent* because it has no notion of *key ownership* — which source has authority over which keys, at what granularity. Deep merge produces local correctness (each step is valid) while globally violating the user's mental model (a high-priority source that mentions `database` does not "own" `database`).

**The diagnostic gap**: I started with a mechanical observation (two operations conflated) and ended with a semantic one (missing declaration of authority). I was analyzing what the code *does* rather than what it *fails to let users express*.

---

## IV. The Concealment Mechanism

**Local correctness masking global incoherence.**

`_deep_merge` is a legitimate, well-understood function. Its correctness is verifiable at each individual invocation. The problem is invisible at that level — it only appears when you ask "what did the caller *mean* by passing this as an override layer?" The code provides no channel through which that intent can be expressed, so it silently substitutes its own: *all overrides are partial extensions*. Since simple cases (env var overrides a scalar leaf) always behave correctly, the problem only surfaces in complex cases (env var dict vs. file dict with different structures), which are exactly the cases where config systems fail in production.

The concealment is structural: the class's public API (`load_file`, `load_env`, `get`) looks complete. There is nothing *missing* from the surface. The absence is inside `_resolve` — no mechanism exists to ask a layer what it intends.

---

## V. Improvement 1: Deepens Concealment, Passes Review

Add per-layer merge strategy as a caller-specified option:

```python
def load_file(self, path, required=True, merge_strategy="deep"):
    """
    merge_strategy: "deep" (recursive merge), "shallow" (top-level keys only),
                    "replace" (discard accumulated state for this layer's keys)
    """
    try:
        with open(path) as f:
            data = json.load(f)
        self._layers.append({
            "source": f"file:{path}",
            "data": data,
            "priority": 10,
            "merge_strategy": merge_strategy,
        })
        self._resolved = None
    except FileNotFoundError:
        if required:
            raise
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}")

def load_env(self, prefix="APP_", mapping=None, merge_strategy="deep"):
    data = {}
    for key, value in os.environ.items():
        if key.startswith(prefix):
            config_key = key[len(prefix):].lower()
            if mapping and config_key in mapping:
                config_key = mapping[config_key]
            data[config_key] = self._coerce(value)
    if data:
        self._layers.append({
            "source": "env",
            "data": data,
            "priority": 20,
            "merge_strategy": merge_strategy,
        })
        self._resolved = None

def _resolve(self):
    if self._resolved is not None:
        return self._resolved
    self._resolved = {}
    for layer in sorted(self._layers, key=lambda l: l["priority"]):
        strategy = layer.get("merge_strategy", "deep")
        if strategy == "deep":
            self._deep_merge(self._resolved, layer["data"])
        elif strategy == "shallow":
            self._resolved.update(layer["data"])
        elif strategy == "replace":
            # Replace only keys present in this layer
            for key in layer["data"]:
                self._resolved[key] = layer["data"][key]
    return self._resolved
```

This passes review: it's a real improvement that solves a real problem. It's additive, backward-compatible, and the docstring is honest.

**It deepens concealment because** the control is at the wrong granularity. You can now say "this file layer replaces top-level keys" but you still cannot say "this layer replaces `database` but merges `logging`." The improvement implies the problem is solved by adding a knob, when the knob is attached to the wrong object.

---

## VI. Three Properties Visible Only Because I Tried to Strengthen It

**1. The unit of override is structurally mislocated.**
Once you add strategy-per-layer, you immediately feel the need for strategy-per-key. The improvement makes visible that layer granularity was always too coarse — but the code's structure makes key-level strategy feel like a different feature entirely, not the natural next step.

**2. Strategy and accumulation are different operations.**
`"replace"` in the implementation above doesn't mean "replace the accumulated state" — it means "skip merge, do assignment." But `"deep"` and `"shallow"` are both merge operations. This reveals that `"replace"` is categorically different from the other two strategies: it's not a merge variant, it's an exit from the merge paradigm. The code hides this by putting all three in the same enum.

**3. Env vars are permanently outside the strategy system.**
Users call `load_env(merge_strategy="deep")`, but env vars are flat strings. A `"deep"` strategy on a flat dict does exactly the same thing as `"shallow"`. The strategy parameter is silently meaningless for env vars, which is only visible once you realize that deep merge requires nested data — and env vars structurally cannot provide it without an explicit nesting transformation (which the `mapping` parameter doesn't do).

---

## VII. Improvement 2: Contradicts Improvement 1, Also Passes Review

Instead of per-layer strategy (caller controls merge at load time), use in-data markers so the *data itself* declares override intent:

```python
_OVERRIDE_SENTINEL = "__override__"

def _extract_override_keys(self, data, path=""):
    """Walk data and collect key paths marked with __override__: true."""
    override_paths = set()
    for key, value in data.items():
        if key == _OVERRIDE_SENTINEL:
            continue
        full_path = f"{path}.{key}" if path else key
        if isinstance(value, dict):
            if value.get(_OVERRIDE_SENTINEL):
                override_paths.add(full_path)
            else:
                override_paths.update(self._extract_override_keys(value, full_path))
    return override_paths

def _deep_merge_with_overrides(self, base, override, override_paths, path=""):
    for key, value in override.items():
        if key == _OVERRIDE_SENTINEL:
            continue
        full_path = f"{path}.{key}" if path else key
        if full_path in override_paths:
            # This key completely replaces whatever base had
            if isinstance(value, dict):
                base[key] = {k: v for k, v in value.items() if k != _OVERRIDE_SENTINEL}
            else:
                base[key] = value
        elif key in base and isinstance(base[key], dict) and isinstance(value, dict):
            self._deep_merge_with_overrides(base[key], value, override_paths, full_path)
        else:
            base[key] = value

def load_file(self, path, required=True):
    try:
        with open(path) as f:
            data = json.load(f)
        override_paths = self._extract_override_keys(data)
        self._layers.append({
            "source": f"file:{path}",
            "data": data,
            "priority": 10,
            "override_paths": override_paths,
        })
        self._resolved = None
    except FileNotFoundError:
        if required:
            raise
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}")
```

Config file can now express:
```json
{
  "database": {
    "__override__": true,
    "host": "prod-db",
    "port": 5432
  }
}
```

This passes review. It's the Ansible/Helm pattern. It lets data declare its own semantics. It solves the real user problem.

---

## VIII. The Structural Conflict

**Both improvements are legitimate. They conflict on the locus of control for merge semantics.**

| | Improvement 1 | Improvement 2 |
|---|---|---|
| **Where policy lives** | In the layer metadata (caller) | In the data payload |
| **Who decides** | The code loading the file | The file itself |
| **Data is** | Pure content | Self-describing content |
| **Env vars can participate** | Yes (strategy on `load_env`) | No (no mechanism for env vars to carry `__override__`) |
| **Granularity** | Whole layer | Individual key path |

**The conflict exists because both improvements are correct along different axes.** Improvement 1 is correct that callers know the authority structure of their sources (env should always override file). Improvement 2 is correct that files know the structural intent of their own data (this database config is a complete replacement, not an extension).

These are incommensurable. Improvement 1 makes data dumb and callers smart. Improvement 2 makes data smart and callers dumb. There is no composition that preserves both — if you add both features to the code, a file layer with `__override__` markers loaded with `merge_strategy="shallow"` has undefined behavior at the intersection.

---

## IX. Improvement 3: Resolves the Conflict

A schema provided at construction time declares merge semantics per key path, independent of both the loading caller and the data payload:

```python
class Config:
    def __init__(self, defaults=None, schema=None):
        self._layers = []
        self._resolved = None
        # Schema structure: {"key.path": {"merge": "replace"|"deep"|"shallow", "type": ...}}
        self._schema = schema or {}
        if defaults:
            self._layers.append({"source": "defaults", "data": defaults, "priority": 0})

    def _schema_for_path(self, path):
        """Return schema entry for a dotted key path."""
        return self._schema.get(path, {})

    def _merge_strategy_for_path(self, path):
        return self._schema_for_path(path).get("merge", "deep")

    def _deep_merge_schema_driven(self, base, override, path=""):
        for key, value in override.items():
            full_path = f"{path}.{key}" if path else key
            strategy = self._merge_strategy_for_path(full_path)
            if strategy == "replace":
                base[key] = value
            elif key in base and isinstance(base[key], dict) and isinstance(value, dict):
                if strategy == "shallow":
                    merged = dict(base[key])
                    merged.update(value)
                    base[key] = merged
                else:
                    self._deep_merge_schema_driven(base[key], value, full_path)
            else:
                base[key] = value

    def _resolve(self):
        if self._resolved is not None:
            return self._resolved
        self._resolved = {}
        for layer in sorted(self._layers, key=lambda l: l["priority"]):
            self._deep_merge_schema_driven(self._resolved, layer["data"])
        return self._resolved
```

Usage:
```python
config = Config(
    defaults={"database": {"host": "localhost", "port": 5432}},
    schema={
        "database": {"merge": "replace"},  # any override of database replaces whole subtree
        "logging": {"merge": "deep"},       # logging merges incrementally
    }
)
config.load_file("base.json")
config.load_env(prefix="APP_")
```

This is legitimate. It resolves the conflict cleanly: policy lives neither in the caller nor in the data, but in an explicit schema contract. Data is pure. Callers are generic. The schema is the authority declaration.

---

## X. How It Fails

**The schema must be resolved before it can be used to resolve configs — and the schema is itself configuration.**

Three specific failure modes:

**1. The bootstrapping loop.** Where does the schema come from? If it's hardcoded in Python, you've just moved the merge policy from the data or the caller into the source code, which is the most rigid location possible. If the schema comes from a file — which it must in any real system with per-environment merge policies — then loading that schema file requires a Config instance, which requires a schema. The schema cannot be external configuration because it must precede configuration loading.

**2. Env vars are permanently disconnected from schema paths.** `APP_DATABASE_HOST=x` creates a flat key `database_host`, not `database.host`. The schema declares merge policy for `database`, but the env var doesn't walk that path — it creates a sibling flat key that bypasses the schema entirely. The schema-driven resolver gives `database_host` a "deep" strategy by default (path not found in schema), while the nested version of the same key in the file gets "replace". Two representations of one concept get different merge semantics invisibly.

**3. The schema is now a third config layer with its own loading, precedence, and validation problems.** A schema that says `"database": {"merge": "replace"}` needs to be validated (what if someone passes `"merge": "recplace"`?). It needs to be composable (can the schema itself be layered? Should a test environment schema override a production schema?). It needs to be sourced (local file? central registry?). The schema re-instantiates every problem the Config class was built to solve, at the meta-level.

---

## XI. What the Failure Reveals About the Design Space

The conflict between Improvement 1 and 2 showed that merge policy cannot be located in either the caller or the data without costs. Improvement 3 found the "neutral" location — the schema — and failed there too.

**This failure reveals that the design space is not a lattice.** There is no "greatest lower bound" that satisfies all three improvements. The reason:

**The three improvements were based on three incompatible ontologies of what configuration is:**

- Improvement 1 treats config as **a sequence of transformations** (each load_file call applies a transformation with a strategy)
- Improvement 2 treats config as **a self-describing document** (data carries its own merge intent)
- Improvement 3 treats config as **a typed projection** (an external schema defines the shape; sources are untyped inputs)

These aren't points in the same design space. They're different answers to the question "what is a config value?" A transformation can be replayed; a self-describing document is authoritative; a typed projection requires an anchor.

**What no individual improvement could reveal:** the env var system inhabits a fourth ontology — **a flat key-value namespace with no structural claims** — that is fundamentally incompatible with all three. Env vars cannot carry merge intent (no Improvement 2). They cannot be given layer-level strategy that makes semantic sense (Improvement 1 fails because flat keys don't compose with nested schemas). They cannot be projected through a path-based schema (Improvement 3 fails because the paths don't match).

The original code's real problem, fully revealed only here: **it attempts to unify four ontologically distinct configuration models** (flat env namespace, hierarchical files, scalar defaults, and the user's mental model of "higher priority wins") **under a single merge operation** — and the merge operation is not expressive enough to make those unifications coherent. Every improvement exposes this incoherence at a different boundary.

The correct diagnosis is not "fix the merge" but **"these four models require explicit translation layers between them, not a merge."** A proper design would:
1. Define a canonical internal representation (schema-anchored)
2. Provide explicit projection functions: `env → canonical`, `file → canonical`
3. Make those projections the site of policy (not the merge)
4. Merge only canonical forms

The merge operation is then trivially deep-merge-always — because by the time you merge, all sources have been projected into the same structural representation. The concealment mechanism the original code uses — local correctness masking global incoherence — is only possible because the projection step is absent.

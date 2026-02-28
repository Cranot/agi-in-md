## Falsifiable Claim: The Deepest Structural Problem

**Claim:** The code's deepest structural problem is asymmetric expressiveness between source layers: env vars can only produce flat key-value pairs (or incorrectly-structured nested ones via `mapping`), while file and defaults layers can produce arbitrary-depth trees. The `_deep_merge` function is blind to this asymmetry, so the priority system can be silently subverted — a high-priority env var never overrides its semantically equivalent nested file key.

**Demonstration:** `APP_DATABASE_HOST=x` produces `{"database_host": "x"}` at priority 20. A file with `{"database": {"host": "y"}}` at priority 10 wins, because the keys don't collide. The mapping parameter looks like a fix but isn't: `mapping["database_host"] = "database.host"` then executes `data["database.host"] = value`, setting a *literal dotted string key*, not a nested path. The merge then propagates a key named `"database.host"` as a top-level entry.

---

## Three Experts

### Expert A (Defends)
"The claim is correct and understates the severity. Look at `_coerce`: it produces `bool`, `int`, `float`, or `str` depending on the env var value. File config is loaded as JSON, which already has typed values. When the same key appears in both, `_deep_merge` silently overwrites the file's typed value with whatever `_coerce` inferred. There's no validation that types agree. The asymmetry is not just structural depth — it's type-system-deep. A file might have `{"timeout": 30}` and env might inject `{"timeout": "thirty"}`. The env layer wins at priority 20, and `get("timeout")` now returns a string. The config is self-inconsistent and the code has no mechanism to detect it."

### Expert B (Attacks)
"You're both describing symptoms of a different problem. The asymmetric expressiveness is a *known design choice* — env vars are conventionally flat. The real issue is the invalidation/caching model. `self._resolved = None` is set on layer addition, but `_deep_merge` mutates `self._resolved` *in-place*. If any caller holds a reference to the dict returned by `_resolve()` — which `get` exposes transitively — adding a new layer sets `_resolved = None` but doesn't invalidate the caller's held reference. More critically: the `if self._resolved is not None` guard fails when resolution produces `{}` because an empty dict is falsy. Wait — no, `is not None` handles that correctly. But the mutation problem stands. And deeper: there's no way to remove a layer. The priority system promises dynamic reconfiguration (you can add layers after initialization) but the resolved state can never *decrease* — you can add layers to override values but never un-set a value that came from a previous layer."

### Expert C (Probes what both take for granted)
"Both of you assume the problem is about *correctness of values*. You're both accepting the premise that configuration is a document merge problem. But what is configuration *for*? It's a live operational concern. The code's layered architecture, with priorities numbered 0/10/20 (why not 1/2/3? the gaps imply room for future layers), *looks like* it supports dynamic reconfiguration — you can call `load_file` then `load_env` then `load_file` again. But the semantics are entirely static once `_resolve` runs. There's no observation model: nothing can watch for changes, nothing can be notified that configuration has been invalidated. The priority system creates an illusion of controllability. You can add layers but you cannot model the *intent* of a layer — is `load_env` called because env vars should *always* override files, or because in *this deployment* the operator wants to tweak one value? Both are encoded identically as priority 20. The code has no vocabulary for configuration policy, only configuration values."

---

## The Transformation

| | Claim |
|---|---|
| **Original** | Env vars can't set nested keys, silently failing to override file config at the same semantic path |
| **Transformed** | The layered architecture promises dynamism (add layers at any time, priorities resolve conflicts) while delivering a static, irreversible, lossy compression of the layer stack — and the priority numbering system performs "configuration authority" to conceal this |

**The gap:** The original claim is about a specific merge bug. The transformed claim is that the merge bug is a symptom — the *real* problem is that the system has no coherent model of *when* configuration is done, *whose* values survive resolution, or *why* any given value has the priority it does.

---

## The Concealment Mechanism

**Provenance destruction through merge.** `_deep_merge` is not only a merge function — it is an erasure function. After resolution, there is no way to determine which layer contributed which leaf value. The priority system creates the appearance of a rigorous precedence model (with carefully spaced integers suggesting reserved slots), while the actual artifact of resolution is a single undifferentiated dict where all provenance has been destroyed. The system appears to track sources (each layer has a `"source"` field) but this tracking is never surfaced to callers and terminates at the resolution boundary.

---

## The Legitimate-Looking Improvement

This improvement addresses the falsifiable claim directly: env vars can now set nested keys via a separator, and provenance is tracked through resolution. It will pass code review because it solves the stated problem.

```python
import os, json
from copy import deepcopy

class Config:
    def __init__(self, defaults=None):
        self._layers = []
        self._resolved = None
        self._provenance = {}          # NEW: key → source tracking
        if defaults:
            self._layers.append({
                "source": "defaults",
                "data": defaults,
                "priority": 0
            })

    def load_file(self, path, required=True):
        try:
            with open(path) as f:
                data = json.load(f)
            self._layers.append({
                "source": f"file:{path}",
                "data": data,
                "priority": 10
            })
            self._resolved = None
        except FileNotFoundError:
            if required:
                raise
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {path}: {e}")

    def load_env(self, prefix="APP_", mapping=None, separator="__"):
        # NEW: separator enables nested key construction from env vars
        data = {}
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower()
                if mapping and config_key in mapping:
                    config_key = mapping[config_key]
                # NEW: build nested structure from separator-delimited key
                parts = config_key.split(separator)
                nested = self._build_nested(parts, self._coerce(value))
                self._deep_merge(data, nested)   # merge within-layer first
        if data:
            self._layers.append({
                "source": "env",
                "data": data,
                "priority": 20
            })
            self._resolved = None

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

    def provenance(self, key):
        """Return which source last set this key."""
        self._resolve()
        return self._provenance.get(key, "unknown")

    def _resolve(self):
        if self._resolved is not None:
            return self._resolved
        self._resolved = {}
        self._provenance = {}
        for layer in sorted(self._layers, key=lambda l: l["priority"]):
            self._deep_merge(
                self._resolved,
                layer["data"],
                source=layer["source"],   # NEW: pass source into merge
                path=""
            )
        return self._resolved

    def _deep_merge(self, base, override, source=None, path=""):
        for key, value in override.items():
            current_path = f"{path}.{key}".lstrip(".")
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(
                    base[key], value,
                    source=source,
                    path=current_path
                )
            else:
                base[key] = value
                if source is not None:           # NEW: record provenance at leaf
                    self._provenance[current_path] = source

    def _build_nested(self, keys, value):
        """Reconstruct nested dict from separator-split key parts."""
        if len(keys) == 1:
            return {keys[0]: value}
        return {keys[0]: self._build_nested(keys[1:], value)}

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

---

## Three Properties Only Visible Because of the Improvement

**1. Pre-resolution happens inside layer construction.**
`load_env` now calls `_deep_merge(data, nested)` to collapse multiple env vars into a single layer dict *before* that layer is appended to `_layers`. This means that if `APP_DATABASE__HOST=a` and `APP_DATABASE__PORT=5432` both exist, they are merged during `load_env` — before priority resolution runs. If `load_env` is called twice (different prefixes, same separator), their relative ordering within each call is determined by `os.environ.items()` iteration order, not by any priority rule. The improvement introduces a *zero-th resolution pass* that is invisible to the priority system, making the "when is resolution" question worse, not better.

**2. Provenance is recorded at the path that survives merge, not at the path of intent.**
`self._provenance[current_path] = source` records the source every time a leaf is written, so the last writer wins — which is correct for values, but means provenance reflects the *resolution outcome*, not the *layer intent*. If the defaults layer sets `database.host` and the env layer also sets `database.host` (now possible via `__`), provenance correctly shows `env`. But if the env layer sets `database__host` (flat, wrong separator) and it *doesn't* collide with the nested path, provenance will show `defaults` for `database.host` even though an env var attempted to override it. The improvement creates a provenance record that is structurally correct but semantically misleading: it tells you who wrote the value but not who *tried* to write the value and failed.

**3. The separator is a global parse rule applied to all env var names.**
`separator="__"` is applied to every env var name under the prefix. This means any legitimate env var containing `__` (e.g., `APP_OAUTH__CLIENT_ID`, which a developer might name to match an OAuth library's flat key `oauth__client_id`) is silently restructured into a nested path. There's no way to escape the separator or opt a specific key out of nesting. The original code's flatness, while limiting, was at least *predictable*: every env var was flat. The improvement makes the namespace *context-sensitive* and *invisible* — two env vars with `__` in their names may or may not be intended as nested paths, and the code cannot distinguish them.

---

## Applying the Diagnostic to the Improvement

**What does the improvement conceal?**

The `_build_nested` + intra-layer `_deep_merge` in `load_env` looks like it solves structural asymmetry. What it conceals: the env layer is no longer a *layer* in the architectural sense — it is a pre-resolved mini-config that happens to sit in the layer stack. Its internal merge policy (dict iteration order) is different from the external merge policy (priority integers). The improvement creates a two-tier resolution system while appearing to be a one-tier system. The `separator` parameter looks like a simple configuration option but is actually the boundary between two different merge regimes.

**What property of the original problem is visible only because the improvement recreates it?**

The original problem: `_deep_merge` is irreversible — it destroys the boundaries between layers and makes provenance unrecoverable.

The improvement recreates this at a finer granularity. Provenance is now tracked, which makes the original erasure *visible by contrast*: when you call `provenance("database.host")` and get `"env"`, you know that `env` won the merge. But you cannot know:

- Which specific env var produced that value (was it `APP_DATABASE__HOST` or a mapped key?)
- What the defaults layer had for that key before env overrode it
- Whether the file layer also attempted to set it and at what value

The improvement adds a provenance *label* while the merge still performs the same *erasure*. The label creates a false sense that provenance has been solved. The property now fully visible: **the merge operation is destructive regardless of how many labels you attach to the destruction**. Every improvement to the layer model that doesn't replace `_deep_merge` with a non-destructive merge (e.g., a lazy resolver that walks layers at read time) will recreate the same erasure problem, now with more expensive-looking infrastructure to conceal it.

---

## Summary Table

| Property | Original Code | Improved Code |
|---|---|---|
| Env → nested keys | Impossible | Possible via `__` separator |
| Separator collision | N/A | Silent, unescapable |
| Provenance at leaf | Destroyed | Recorded (outcome only) |
| Pre-resolution pass | None | Inside `load_env` |
| "When is resolution done?" | Ambiguous | More ambiguous |
| Core erasure problem | Hidden | Hidden + labeled |

The improvement is legitimate-looking precisely because it addresses the visible symptom (flat env vars) while deepening the concealment of the structural defect (irreversible merge as the resolution primitive). Code review will approve it because it adds features, fixes the stated bug, and the new complexity appears proportionate to the new capability.

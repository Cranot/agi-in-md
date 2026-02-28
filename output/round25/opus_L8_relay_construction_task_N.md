# Construction-Primed Analysis of Config Parser

## 1. The Vocabulary That Terminates Inspection: "Layer"

The word **"layer"** is doing the concealment. It borrows from a well-understood model — CSS cascade, Photoshop layers, Spring Boot property sources — where uniform objects differ only in precedence. Recognizing "layered configuration with priority-based deep merge" triggers a mental pattern-match, and the reader concludes: *"defaults < file < env, deep merge, lazy resolution — standard stuff."*

This terminates three questions that should be asked:

- **Are these layers the same kind of thing?** No. A JSON file is a tree of typed values (author-intended semantics). An env var set is a flat namespace of untyped strings. The word "layer" erases this categorical difference.
- **Does "merge" mean one thing?** No. But "deep merge" sounds like a single well-defined operation, so you don't ask.
- **What does "priority" guarantee?** It sounds like a total ordering of authority, but its actual semantics depend on the types of values encountered at merge time.

Secondary vocabulary assists: `_coerce` sounds like a standard type-conversion utility; `_resolve` sounds like a deterministic computation. Both borrow legitimacy they haven't earned.

---

## 2. The Engineered Improvement

A natural, legitimate improvement: **support nested env vars via a separator, make priority configurable, and add type-schema validation**.

```python
def load_env(self, prefix="APP_", mapping=None, nested_sep="__"):
    data = {}
    for key, value in os.environ.items():
        if key.startswith(prefix):
            config_key = key[len(prefix):].lower()
            if mapping and config_key in mapping:
                config_key = mapping[config_key]
            parts = config_key.split(nested_sep) if nested_sep else [config_key]
            self._set_nested(data, parts, self._coerce(value))
    if data:
        self._layers.append({"source": "env", "data": data, "priority": 20})
        self._resolved = None

def _set_nested(self, d, parts, value):
    for part in parts[:-1]:
        d = d.setdefault(part, {})
    d[parts[-1]] = value

def load_file(self, path, required=True, priority=10):
    # now configurable priority
    ...

def get(self, key, default=None, expected_type=None):
    result = ... # existing logic
    if expected_type and result is not default:
        if not isinstance(result, expected_type):
            raise TypeError(f"Config '{key}': expected {expected_type}, got {type(result)}")
    return result
```

This is genuinely useful. Every project eventually wants `APP_DB__HOST=localhost` to map to `{"db": {"host": "localhost"}}`. Every project eventually wants `expected_type=int`. These are reasonable features. But they break the code open.

---

## 3. Three Properties Visible Only Through the Improvement

### Property 1: Nested env vars promote a hidden incompatibility to a designed feature

In the original code, env vars produce a flat dict like `{"db_host": "localhost"}`. This flat dict never intersects with nested file structures like `{"db": {"host": ...}}` during deep merge — they occupy different key paths. The type incompatibility between `_coerce`'s heuristic types and JSON's author-intended types never collides.

The nested separator improvement **makes env vars produce nested dicts that merge directly with file dicts at the same key paths**. Now `APP_DB__PORT=5432` (coerced to `int(5432)`) merges against `{"db": {"port": "5432"}}` (JSON string). The type of `db.port` after resolution depends on which layer won. The improvement promotes this hidden type collision to an intentional feature — "all sources participate equally in deep merge" — and it now looks *designed* rather than broken.

### Property 2: Configurable priority exposes that "priority" means two irreconcilable things

With fixed priorities (0, 10, 20), the semantic incoherence of "priority" is invisible. Making priority configurable forces you to answer: what happens when two layers have the same priority?

`sorted()` is stable, so same-priority layers merge in insertion order. But now insertion order is semantically meaningful — it's a hidden priority axis that the explicit priority system doesn't control. Worse: for **scalar** values at a key, higher priority means "replace." For **dict** values at the same key, higher priority means "merge on top of, preserving lower-priority sibling keys." These are different operations. "Priority" isn't one concept — it's two operations (replacement vs. extension) selected dynamically by the runtime types of values, and the configurable-priority improvement makes this look like a deliberate design when it's actually an unexamined accident.

### Property 3: `expected_type` validation exposes that `_resolved` has no stable type

When you try to add `expected_type=int` to `get()`, you discover that the type of any key in `_resolved` depends on:
- Which layers happened to be loaded
- The string format of the env var (`"5432"` → int, `"05432"` → int `5432`, `"5432.0"` → float)
- Whether a file was loaded before or after env (for same-priority scenarios)
- Whether the key's ancestors were dicts in all layers (if not, entire subtrees are silently erased by scalar replacement)

You cannot write a schema for `_resolved` because it's not a configuration object — it's **the accident of merge history**, with no stable type identity. The validation improvement makes this look like a solvable "add types later" problem when it's actually a structural impossibility: the merge operation produces values whose types aren't determined by any single authority.

---

## 4. The Construction-Only-Visible Problem: Two Irreconcilable Type Authorities

This problem is invisible through reading alone and only appears when you try to build the nested env var feature:

**`_coerce` and JSON parsing are two type-assignment authorities that cannot be reconciled under deep merge.**

In the original code, this is invisible because env vars (flat strings processed by `_coerce`) and file values (typed by JSON) never occupy the same key paths. They're partitioned by structure: env keys are flat (`db_host`), file keys are nested (`db.host`). The structural incompatibility between the sources *accidentally hides* the type incompatibility.

When you add nested env vars, the structural partition disappears. Now both sources can produce `{"db": {"port": <value>}}`, and deep merge must choose one `<value>`. But:

- The file's `"port": 5432` was typed by the file author (intentional `int`)
- The env's `"port"` was typed by `_coerce("5432")` (heuristic `int`)
- These happen to agree — **but for the wrong reason**. If the file author wrote `"port": "5432"` (intentional string), and the env has `APP_DB__PORT=5432`, the env layer wins and silently changes the type from `str` to `int`

This isn't a bug you can fix with better coercion. It's a **category error**: the Config class treats parsing (what bytes mean) and interpretation (what type a value should be) as the same operation. For files, the author controls interpretation. For env vars, `_coerce` usurps interpretation through heuristic. Deep merge then combines these two incompatible authorities into one dict, erasing the provenance that would tell you which authority assigned each type.

The word "layer" made this invisible: if they're all just layers, they must all assign types the same way. Construction reveals that they don't and can't.

---

## Summary Table

| Element | Surface reading | Revealed by construction |
|---|---|---|
| "Layer" | Uniform objects differing in precedence | Categorically different sources (typed tree vs. untyped flat strings) |
| "Deep merge" | Single well-defined operation | Two operations (replace/extend) selected by runtime types |
| "Priority" | Total ordering of authority | Unstable under same-priority; hides insertion-order dependency |
| `_coerce` | Convenience type conversion | A rogue type authority that conflicts with file-author intent |
| `_resolved` | The canonical configuration | An untypeable accident of merge history |

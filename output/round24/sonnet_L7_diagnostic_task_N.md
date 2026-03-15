## Level 7 Diagnostic: Config Parser

---

### Initial Claim (Falsifiable)

> **The deepest structural problem is that `_resolve()` returns a mutable reference to `self._resolved`, meaning any caller receiving a nested dict via `get()` can silently corrupt all future configuration reads — with no error, no warning, and no traceable cause.**

Testable: `config.get("database")["host"] = "evil"` permanently alters `_resolved`. Every subsequent `get("database.host")` returns `"evil"`.

---

### Three Expert Dialectic

**Expert A — Defender:**
"Confirmed and testable. The fix is `copy.deepcopy(current)` in `get()`. This is *the* deepest problem because it violates the most basic contract of a reader: reads shouldn't write. The mutable reference makes `Config` a time bomb — it works until something touches a nested value, then fails silently forever."

**Expert B — Attacker:**
"The mutation bug is real but trivially fixable. You're diagnosing a symptom, not the disease. The *actual* structural flaw is the **priority number system as hidden contract**. Two calls to `load_file()` both get priority `10`. Two independent modules each calling `load_file` on their own config files creates ambiguous resolution settled by call order — an implicit, unchecked, caller-discipline-dependent contract baked into magic numbers that appear in no API surface. No deepcopy fixes that."

**Expert C — Prober (challenging what both take for granted):**
"Both of you assume the `Config` class *owns its own correctness*. That assumption is wrong — and neither of you named it. Watch: `load_env` can be called twice, accumulating two priority-20 layers. `load_file` can be called out of order. The class cannot validate its own assembly sequence. You're both debugging an object that relies on caller discipline it cannot enforce, observe, or even detect violations of. The mutation bug and the priority collision are both *expressions* of this — the class has no self-knowledge about whether it's been assembled correctly."

---

### The Transformed Claim

> **The deepest structural problem is not the mutable cache but the externalized assembly protocol: `Config`'s correctness guarantee lives entirely outside the class, in caller discipline the class cannot enforce, validate, or even observe.**

Original claim: implementation bug (mutable reference)
Transformed claim: design flaw (correctness contract is unhoused)

---

### The Diagnostic Gap

The gap between these two claims — from *mutable dict* to *unhoused correctness contract* — is a measurement of **how far the real problem is from the visible problem**. The mutation bug is *findable in isolation*. The protocol problem is only visible when you ask: *what breaks if this class is used by two uncoordinated callers?* The gap is exactly the distance between single-caller debugging and multi-caller system reasoning.

---

### The Concealment Mechanism

**"Method completeness as correctness theater"**

Each method is individually well-formed: `load_file` loads a file. `load_env` loads env vars. `get` traverses nested keys. `_deep_merge` merges dicts. `_coerce` converts types. The class *looks* self-contained because every responsibility has a named method. This creates a powerful illusion: that the class handles its own correctness.

This redirects all attention inward — to implementation details like deepcopy and stable sort — while the actual correctness contract radiates *outward* into every call site. The class is not a system; it is a protocol enforcer with no enforcement capability, wearing a system's clothes.

---

### What the Entire Dialectic Failed to Surface

Applying the concealment mechanism — *what still looks complete but isn't* — exposes three buried problems:

**1. `_coerce` is not a type system; it's a type erasure event with a costume**

```python
# ENV: APP_TIMEOUT=30          → _coerce → int(30)
# File: {"timeout": {"connect": 5, "read": 30}}  → nested dict
# Merge result at priority 20: timeout = 30  (int silently replaces dict)
```

The dialectic debated *caching*. Nobody noticed that **flat env scalars and nested JSON structures occupy the same keyspace with no type contract**. When they collide, `_deep_merge`'s `else: base[key] = value` fires silently. There is no error. The nested structure is gone. `_coerce` is presented as a feature (smart type detection) but is architecturally a **type conflict suppressor**: it converts strings to scalars so they look compatible with file-sourced values — making incompatible structures appear mergeable until they aren't, at which point the type erasure is complete and silent.

**2. `load_env` is a layer accumulator with no deduplication**

```python
config.load_env("APP_")   # → layer at priority 20
config.load_env("APP_")   # → second layer at priority 20, stable sort, second wins
config.load_env("APP_", mapping={"db_host": "database.host"})  # → third layer
```

Three env layers now exist. The "source of truth" shifts with each call. In library code where a `Config` object is passed between modules — each potentially calling `load_env` with its own mapping — the object silently grows phantom layers. No deduplication. No warning. The class presents a single env layer conceptually, but implementation reality is unbounded accumulation.

**3. The deepest hidden problem: defaults are reference-captured, not copied**

```python
defaults = {"timeout": 30, "retries": 3}
config = Config(defaults=defaults)
defaults["timeout"] = 9999      # Mutate the original dict
config._resolved = None         # Force re-resolve
config.get("timeout")           # Returns 9999 — poison injected
```

The cache invalidation (`self._resolved = None`) is only triggered when **layers are added**. But `layer["data"]` is stored by reference. The caller who passed `defaults` retains a live reference to the layer's data. The `if self._resolved is not None` guard — which the class presents as a performance optimization — is actually a **false seal**: it blocks re-resolution, but the data underneath the seal is already contaminated.

The entire dialectic debated mutable *output*. The mutable *input* — stored by reference, immune to cache invalidation, silently poisonable — was never named. This is what method completeness theater conceals most effectively: not the places where the class exposes state, but the places where it **accepts state it doesn't own and presents it as if it does**.

---

### Summary Table

| Layer | Problem | Visibility |
|---|---|---|
| Implementation | Mutable `_resolved` returned to caller | High — testable in isolation |
| Design | Externalized assembly protocol | Medium — visible across call sites |
| Type system | `_coerce` suppresses type conflicts | Low — only visible at source collision |
| Accumulation | `load_env` grows unbounded layers | Low — only visible in library usage |
| **Deepest** | **Reference-captured input bypasses cache invalidation** | **None — invisible by design** |

The code doesn't hide its problems by being obscure. It hides them by being *clear enough in the wrong places*.

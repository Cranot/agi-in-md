# Generative Diagnostic: Config Parser

## The Falsifiable Claim

> **This system's deepest structural problem is the absence of a configuration schema, which renders every feature — merge, override, coerce, provenance — semantically incoherent despite each being locally well-implemented.**

---

## The Dialectic

### Expert 1 (Defender)
The claim holds. Look at `_coerce`: it guesses types context-free. The string `"false"` from an env var becomes `bool`, but there's no declaration that the key *should be* a bool. `_deep_merge` merges dicts recursively but has no concept of whether merging a list-over-scalar or scalar-over-dict is *valid*. The `source` field on each layer is never queried — pure decoration. Every feature operates in a semantic vacuum.

### Expert 2 (Attacker)
This misses the sharper problem. `load_env` produces **flat keys**: `APP_DATABASE_HOST` → `{"database_host": "..."}`. But `load_file` can produce nested structures: `{"database": {"host": "..."}}`. The priority system *promises* env (priority 20) overrides file (priority 10), but they land in **different namespaces**. `get("database.host")` traverses the nested file structure and *never sees the env value*. The override guarantee is structurally broken for any nested config.

### Expert 3 (Probing Assumptions)
Both experts take for granted that "priority" is the governing contract. But there is no contract. There's no schema to say what keys exist, what types they hold, what nesting is legal, or what "override" means for compound values. Without that, Expert 1's type-guessing problem and Expert 2's namespace-mismatch problem are *both symptoms* of the same absence. You can't define correct merge without knowing structure. You can't define correct coercion without knowing types. You can't define correct override without knowing identity.

---

## The Transformed Claim

> The absence of a schema makes **merge undefined** (dict-over-scalar?), **override unverifiable** (flat env key vs. nested file key = different namespaces), **coercion ungrounded** (guess types without expected types), and **provenance unqueryable** (the `source` field exists but is never consumed).

### The Gap Diagnostic
My original instinct was drawn to provenance loss — the most *visible* artifact (`source` stored but never used). The dialectic revealed provenance loss is just one manifestation. The **real concealment** is that without a schema, there's nothing to trace provenance *against*, nothing to validate merges *with*, nothing to verify overrides *for*. I was drawn to a symptom because the code's structure made it look like the most sophisticated concern.

---

## The Concealment Mechanism: **Ceremony as Camouflage**

Each method is locally correct and professionally structured:

| Ceremony | What it hides |
|---|---|
| `_layers` with `source` + `priority` metadata | Metadata is write-only; never queried or exposed |
| `_deep_merge` with recursive dict handling | Env can't produce nested dicts, so recursion never applies cross-layer |
| `_coerce` with multi-type cascade | Types are guessed, not declared; `"0"` silently becomes `int(0)` |
| `_resolved` cache invalidation | Suggests careful lifecycle, hides that resolution is semantically undefined |

The code *performs* sophistication. Each method passes local review. The incoherence only lives in the *relationships between* methods.

---

## The Engineered Concealment: A `get_source()` Method

This improvement looks like it fixes the provenance gap and would pass code review:

```python
def get_source(self, key):
    """Return which source determined the final value for a given key."""
    keys = key.split(".")
    winning_source = None
    for layer in sorted(self._layers, key=lambda l: l["priority"]):
        current = layer["data"]
        found = True
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                found = False
                break
        if found and current is not None:
            winning_source = layer["source"]
    return winning_source
```

It's well-structured. It follows existing patterns (`split(".")`, sorted by priority). It addresses an obvious gap. **It would pass review.** And it *deepens* the concealment.

---

## Three Properties Visible Only Because I Tried to Strengthen It

**1. The namespace split becomes actively misleading, not just passively broken.**
With `get_source`, if env creates `{"database_host": "x"}` and file creates `{"database": {"host": "y"}}`, then `get_source("database.host")` reports `"file:config.json"` — even though the user set `APP_DATABASE_HOST` specifically to override it. The provenance system now *confidently gives the wrong answer*. Before, it was just silent; now it lies.

**2. "Source" is incoherent for merged compound values.**
If defaults provide `{"database": {"host": "localhost"}}` and file provides `{"database": {"port": 5432}}`, the resolved `database` dict is a composite of both layers. `get_source("database")` reports `"file:..."` (last writer wins in the loop), but the *value* contains keys from defaults. The concept of "source" is only meaningful for leaf scalars, but nothing in the system distinguishes leaves from branches — because there's no schema.

**3. Falsy values become invisible to provenance.**
The `current is not None` guard means a value explicitly set to `0`, `False`, or `""` (all legitimate outputs of `_coerce`) is treated as "not present in this layer." So `APP_DEBUG=false` → `_coerce` → `False` → `get_source("debug")` skips it → reports the *defaults* layer as the source. The coercion system and provenance system make **incompatible assumptions about what constitutes a value** — an inconsistency that was invisible until I tried to make them interact.

---

## The Core Lesson

This code's real architecture is a **set of locally-correct methods with no shared model of what configuration *is***. The fix isn't adding features to the existing structure — it's introducing the missing foundation:

```python
# What's actually needed (sketch)
schema = {
    "database.host": {"type": str, "env": "APP_DATABASE_HOST", "default": "localhost"},
    "database.port": {"type": int, "env": "APP_DATABASE_PORT", "default": 5432},
    "debug":         {"type": bool, "env": "APP_DEBUG", "default": False},
}
```

A schema makes merge defined (you know the structure), coercion grounded (you know the type), override verifiable (env maps explicitly to dotted paths), and provenance queryable (you can track per-leaf-key). Every feature in the current code is *waiting for this* and pretending it doesn't need it.

**PROMPT 1 — PEDAGOGICAL LOCK-IN**

What pattern does v1 teach? Now trace: v2 developers internalize it as 'best practice.' They build v2 extensions using that pattern. v3 arrives and recognizes: pattern is suboptimal. But v2 extensions depend on v2 supporting the pattern. Show v3's impossible choice: change pattern and break v2 extensions, or stay locked into pattern taught by v1. Name the Version Pedagogy Lock: a design lesson becomes a backward-compatibility prison. Trace two generations forward: which pattern from this codebase cannot be changed because it was successfully taught? Predict: what v4 must do to finally escape.

---

**PROMPT 2 — ACCIDENTAL INTERFACE**

Name one v1 behavior never part of the API spec—a side effect, emergent property, or leaked implementation detail. Trace: v2 developers discovered it. Show v2 code that depends on it—tests, callers, extensions. v2 documented it as 'undocumented but stable.' v3 sees: this behavior blocks feature requests. Design v3's impossible choice: remove it (break v2 callers) or embed officially (constrain v3 forever). Name the Unintended Interface Law: accidental behavior becomes mandatory interface. Which version finally cannot carry the debt? Show the architectural constraint it creates downstream.

---

**PROMPT 3 — VERSION BANKRUPTCY**

Identify a v1 flaw that v2 attempted to fix. Show why the fix failed: callers internalized v1's behavior, making the fix a regression. v2 abandoned the fix, now carries both flaw and apology code. v3 inherits both. Each version maintains the flaw for backward compatibility. Name the Version Bankruptcy Law: early mistakes compound—each version accepts debt to avoid breaking prior generations. Which version finally can afford to break? Design the breaking change. What does it cost? Predict: which fundamental redesign requires escaping this debt first.

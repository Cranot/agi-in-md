# Knowledge Audit: Adversarial Attack on Factual Assertions

## KNOWLEDGE CLAIMS IDENTIFIED

The analysis contains 16 findings. Of these, **8 contain knowledge claims** requiring external verification. The rest are structural observations verifiable from source.

---

## Attack Construction

### **Finding 3: Regex Group Default Behavior**
**Exact claim**: "`compile_path` uses a mutable default pattern via `match.groups("str")` which provides default but the regex groups are positional, not named defaults."

**Dependency**: Python's `re.Match.groups()` method behavior — specifically that passing a default argument fills unmatched groups, and that the regex in question uses positional groups.

**Failure mode**: 
- Python version differences in `re` module behavior (unlikely but possible)
- The actual regex pattern structure — if groups ARE named, the claim is wrong
- If `convertor_type` comes from a named group, not positional matching, the "positional" assertion fails

**Confabulation risk**: **MEDIUM**. Models often confuse named vs positional groups. Need to verify actual regex pattern at line 45.

**With documentation access**: Would confirm from Python docs and actual source regex whether groups are named or positional.

---

### **Finding 6: Python Dict Semantics**
**Exact claim**: "`scope.update(child_scope)` at line 87 mutates the caller's scope dictionary in-place"

**Dependency**: Python `dict.update()` is an in-place mutation operation.

**Failure mode**: Only possible if this is not standard Python dict semantics — which is **not possible**. This is verifiable from Python language specification.

**Confabulation risk**: **LOW**. This is a core Python behavior, unlikely to be wrong.

**Assessment**: Actually SAFE — this is language specification, not library knowledge.

---

### **Finding 7: Partial Match Priority**
**Exact claim**: "The `partial` variable in Router.app captures the first PARTIAL match, not the best or most specific, silently discarding later partial matches."

**Dependency**: Understanding of the routing algorithm's match priority semantics.

**Failure mode**:
- The code may have additional logic to compare partial matches
- "First match wins" may be intentional and documented behavior
- Different Python versions don't affect this — it's pure control flow

**Confabulation risk**: **LOW**. This is readable from control flow if you trace lines 189-194 carefully. The claim is about what the code DOES, not what it SHOULD do.

**With documentation access**: Would check Starlette docs for whether "first partial wins" is documented semantics.

---

### **Finding 9: Middleware Execution Order**
**Exact claim**: "Middleware stacking uses `reversed()` because each middleware wraps the previous, meaning the last middleware in the list is the outermost (first to execute)."

**Dependency**: ASGI middleware pattern — that wrapping creates an onion where outer = first in, last out.

**Failure mode**:
- If Starlette uses different middleware semantics than standard ASGI
- If the `reversed()` serves a different purpose

**Confabulation risk**: **MEDIUM**. Standard ASGI pattern, but could be Starlette-specific.

**With documentation access**: Would check Starlette middleware docs to confirm execution order semantics.

---

### **Finding 10: Warning Location Behavior**
**Exact claim**: "The lifespan deprecation warnings at lines 158-165 fire at Router instantiation, not at the deprecated function's definition"

**Dependency**: Python's `warnings.warn()` behavior and where the warning appears to originate.

**Failure mode**:
- Python's `stacklevel` parameter affects where warnings appear
- The code may set `stacklevel` to point elsewhere
- Different Python versions may handle warning source differently

**Confabulation risk**: **MEDIUM-HIGH**. Warning stack behavior is version-sensitive.

**With documentation access**: Would check Python `warnings` module docs and verify if `stacklevel` is used.

---

### **Finding 13: Method Default Divergence**
**Exact claim**: "`Route.methods` defaults to `{"GET"}` when methods=None and endpoint is a function, but to empty set when methods=None and endpoint is a class"

**Dependency**: Understanding of how Starlette infers methods from endpoint type.

**Failure mode**:
- The code at lines 105-113 may handle both cases identically
- Class-based endpoints may have different method inference
- Version-specific behavior changes

**Confabulation risk**: **MEDIUM**. Requires tracing conditional logic correctly.

**With documentation access**: Would verify against Starlette Route class implementation.

---

### **Finding 14 & Conservation Law: System Design Properties**
**Exact claim**: "Route Specificity × Handler Generality = Constant"

**Dependency**: Systems design theory — that this conservation law describes the actual system behavior.

**Failure mode**:
- The trade-off may have a different mathematical form
- No conservation may exist — both could increase/decrease independently
- The "law" may be confabulated from pattern-matching to known conservation laws

**Confabulation risk**: **HIGH**. Models frequently invent conservation laws that sound plausible but don't hold under stress-testing.

**With documentation access**: Unfalsifiable by documentation — this is a theoretical claim requiring empirical validation.

---

## Improvement Construction

**With access to official documentation, CVE database, GitHub issues, and benchmarks:**

| Claim | Would Change? | Would Confirm? | Unfalsifiable? |
|-------|---------------|----------------|----------------|
| Finding 3 (regex groups) | Possibly — need actual regex pattern | If pattern verified | No |
| Finding 6 (dict semantics) | No | Yes — language spec | No |
| Finding 7 (partial priority) | Possibly — documented semantics? | If intentional | No |
| Finding 9 (middleware order) | Unlikely — standard pattern | Likely | No |
| Finding 10 (warning location) | Possibly — stacklevel matters | Depends on code | No |
| Finding 13 (method defaults) | Possibly — need implementation | If logic verified | No |
| Finding 14 (conservation law) | Likely — theoretical construct | No — requires empirical test | **YES** |

---

## Conservation Law of This Audit

**STRUCTURAL observations : KNOWLEDGE claims :: Verification accessibility : Confabulation risk**

The audit reveals a conservation law:

> **Source Proximity × Confabulation Risk = Constant**

Claims directly verifiable from source (Finding 1, 4, 6, 11, 12) have LOW confabulation risk. Claims requiring external knowledge (Finding 3, 9, 10, 13, 14) have MEDIUM-HIGH confabulation risk.

**The analysis's structural findings (6/16 = 37.5%) are its epistemic anchor.** The remaining 62.5% are knowledge claims of varying reliability:

- **HIGH confidence** (0.95-1.0): Claims about Python language semantics (Finding 6, 9)
- **MEDIUM confidence** (0.85-0.95): Claims traceable from source logic (Finding 7, 13)
- **LOW confidence** (0.75): Theoretical conservation laws (Finding 14, Conservation Law)

**The conservation law claims are UNFALSIFIABLE by design** — they are meta-patterns imposed ON the code, not extracted FROM it. They cannot be confirmed or refuted by documentation; only by empirical stress-testing across the full space of possible inputs.

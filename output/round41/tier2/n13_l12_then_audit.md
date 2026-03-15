# Knowledge Audit: Level 12 Analysis of Starlette routing.py

## Attack Phase

### KNOWLEDGE CLAIM 1: RFC 7231 Requirement

**Exact claim**: "HTTP routing IS a combined operation — RFC 7231 requires 405 responses when path exists but method doesn't."

**Dependency**: RFC 7231 Section 4.1 (or relevant section on 405 status)

**Failure mode**: 
- RFC 7231 was obsoleted by RFC 9110-9114 in June 2022
- The requirement exists but may be in a different RFC now
- The exact wording might not support "combined operation" interpretation

**Confabulation risk**: MEDIUM. RFC numbers and contents are frequently misremembered. The 405-when-path-exists requirement is real, but citing RFC 7231 specifically is a version-dependent claim.

---

### KNOWLEDGE CLAIM 2: Nested Async Function Bug

**Exact claim**: "**CRITICAL BUG**: Nested `async def app` shadows outer `async def app`. [...] This is obfuscation at minimum; if `wrap_app_handling_exceptions` expects the outer app's closure over `request`, it gets the wrong function."

**Dependency**: Python scoping rules, closure semantics, what `wrap_app_handling_exceptions` contractually expects

**Failure mode**:
- Python closures capture variables, not values — both inner and outer `app` close over the same `request` variable
- The shadowing might be intentional pattern (factory returning ASGI app)
- `wrap_app_handling_exceptions` may not care which function it receives

**Confabulation risk**: HIGH. This claims a CRITICAL BUG in production Starlette code. The pattern `async def app` nested inside `async def app` is unusual but may be a legitimate ASGI app factory pattern. Closures in Python capture the *variable binding*, so the inner function's closure over `request` works correctly. The "shadowing" affects the *name* in the outer scope, but since the outer function returns the inner one, this is likely intentional.

---

### KNOWLEDGE CLAIM 3: Middleware Short-Circuit Behavior

**Exact claim**: "Middleware CAN short-circuit (return early response), effectively becoming 'alternative handlers.' This is deferred selection in disguise."

**Dependency**: ASGI specification, whether middleware can terminate response without calling next app

**Failure mode**:
- ASGI spec might require all middleware to call the next app
- Short-circuiting might violate ASGI contract
- This might be a Starlette-specific behavior, not an ASGI property

**Confabulation risk**: MEDIUM. ASGI middleware behavior is well-documented but the claim about "deferred selection" is an interpretive leap.

---

### KNOWLEDGE CLAIM 4: `{class}` Would Compile But Break

**Exact claim**: "Duplicate param detection but no Python-keyword detection. `{class}` would compile but break."

**Dependency**: 
- `re.compile()` behavior with named groups
- What happens when path params are extracted and used as Python kwargs

**Failure mode**:
- `re.compile(r"(?P<class>...)")` actually works fine — regex named groups can use Python keywords
- The "break" would only occur if params are passed as `**kwargs` to a function call
- Starlette might not pass params as kwargs anywhere

**Confabulation risk**: HIGH. Regex named groups CAN use Python keywords. The "break" depends entirely on how path params are consumed downstream — a detail not verified in the analysis.

---

### KNOWLEDGE CLAIM 5: Scope is God-Object

**Exact claim**: "scope is god-object"

**Dependency**: Software architecture terminology, design pattern classification

**Failure mode**: This is an interpretive classification, not a factual claim. The term "god-object" has specific meaning (object that knows too much/does too much). Scope being a dictionary passed through the ASGI chain may or may not qualify.

**Confabulation risk**: LOW. This is structural analysis vocabulary, not empirical claim.

---

### KNOWLEDGE CLAIM 6: Reversed Middleware Order is "Correct"

**Exact claim**: "Middleware applied in `reversed()` order. Correct but non-obvious."

**Dependency**: Middleware ordering conventions in Python web frameworks

**Failure mode**:
- "Correct" is normative — different frameworks have different conventions
- Django middleware processes request in registration order, response in reverse
- The claim assumes a specific mental model of middleware as "wrapping"

**Confabulation risk**: MEDIUM. The word "correct" smuggles in a convention as if it were objectively true.

---

## Improvement Phase

### With Access to Authoritative Sources

| Claim | What Would Change |
|-------|-------------------|
| RFC 7231 | Would cite RFC 9110 Section 15.5.6 (current HTTP semantics). Core claim survives: 405 is required when path exists but method doesn't. |
| Nested async bug | Would read `wrap_app_handling_exceptions` source. If it only calls the passed app with `(scope, receive, send)`, the inner/outer distinction is irrelevant — both are valid ASGI apps. Claim likely **reversed**: this is a pattern, not a bug. |
| Middleware short-circuit | Would verify ASGI spec. Middleware is explicitly allowed to not call `next()` — this is the basis for auth middleware, rate limiting, etc. Claim survives. |
| `{class}` breaks | Would check if path_params are ever passed as `**kwargs`. If only dict access is used (`scope["path_params"]["class"]`), the keyword issue never materializes. Claim likely **false**. |
| Reversed order | Would verify against middleware pattern literature. "Correct" is framework-convention-dependent. Claim softens to "matches Starlette's intended semantics." |

---

## Conservation Law: Structural vs Knowledge Claims

**The conservation law of the analysis**:

> **Structural Depth × Knowledge Risk = Constant**

The deeper the structural insight (L11-L12), the more it relies on external knowledge claims. The analysis cannot reach meta-conservation laws without stacking assumptions about HTTP, Python, ASGI, and framework conventions.

| Analysis Level | Structural Confidence | Knowledge Dependencies | Risk Profile |
|----------------|----------------------|------------------------|--------------|
| L7 (concealment mechanism) | HIGH — derived from code structure alone | LOW | SAFE |
| L8 (improvement) | HIGH — construction is self-validating | LOW | SAFE |
| L10 (invariant) | HIGH — observable in loop structure | NONE | SAFE |
| L11 (conservation law) | MEDIUM — requires accepting the frame | MEDIUM (HTTP routing semantics) | MODERATE |
| L12 (meta-conservation law) | MEDIUM — requires accepting L11 frame | HIGH (middleware behavior, ASGI spec) | ELEVATED |

**The conservation law predicts**: Any L12 analysis will have ~3-5 knowledge claims that are structurally necessary to reach that depth. You cannot derive meta-laws about routing systems without claiming things about routing systems that aren't in the source.

---

## Specific Verdicts

### SAFE (verifiable from source):
- `Match.PARTIAL` conflates path and method concerns — **VERIFIED** by reading lines 160-174
- First-match-wins is the invariant — **VERIFIED** by loop structure
- `scope.update(child_scope)` is mutation — **VERIFIED** by line 319
- Conservation law of Order-Control × Auto-Disambiguation — **DERIVED** from the structure

### KNOWLEDGE CLAIMS requiring verification:
1. RFC citation — **OUTDATED** but claim survives with updated citation
2. Critical bug #1 — **LIKELY FALSE** — appears to be a legitimate pattern, not shadowing bug
3. `{class}` breaks — **LIKELY FALSE** — regex allows keywords, downstream usage not verified
4. Middleware short-circuit — **LIKELY TRUE** but requires ASGI spec confirmation

### Highest-risk claim:
**Bug #1 (nested async)** is the most aggressive knowledge claim — it asserts production code has a critical bug based on Python scoping reasoning that may be incorrect. Closures capture variables, not function names. The inner `app` correctly closes over `request`. The "shadowing" is naming, not semantics.

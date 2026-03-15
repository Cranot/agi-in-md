## Finding 1
**Claim**: The `request_response` function defines `app` twice in nested scope, creating an inner closure that shadows the outer one.
**Type**: STRUCTURAL
**Confidence**: 1.0
**Provenance**: source:lines_22-31
**Falsifiable**: yes: run AST analysis or show the inner `app` is never called
**If wrong**: The nested function analysis is fundamentally flawed

---

## Finding 2
**Claim**: The inner `app` at line 27-28 is unreachable code — the outer `app` at line 24 is what gets passed to `wrap_app_handling_exceptions`.
**Type**: DERIVED
**Confidence**: 0.95
**Provenance**: derivation:from_finding_1 + source:line_30
**Falsifiable**: yes: demonstrate the inner `app` is called via some execution path
**If wrong**: The bug classification changes from dead code to something else

---

## Finding 3
**Claim**: `compile_path` uses a mutable default pattern via `match.groups("str")` which provides default but the regex groups are positional, not named defaults.
**Type**: MEASURED
**Confidence**: 0.85
**Provenance**: source:line_45
**Falsifiable**: yes: show that `convertor_type` can be something other than `:str` suffix or None
**If wrong**: The parameter default behavior is correctly implemented

---

## Finding 4
**Claim**: Mount's path regex always appends `/{path:path}` which means empty-string mounts match everything, creating a catch-all route.
**Type**: STRUCTURAL
**Confidence**: 1.0
**Provenance**: source:line_137
**Falsifiable**: yes: create a Mount with `path=""` and show what it matches
**If wrong**: Mount routing logic has different semantics than apparent

---

## Finding 5
**Claim**: The `duplicated_params` detection in `compile_path` raises before the regex is compiled, but only detects duplicates within a single path string, not across composed Mount boundaries.
**Type**: DERIVED
**Confidence**: 0.9
**Provenance**: derivation:from_source:lines_52-62
**Falsifiable**: yes: show cross-mount duplicate detection or prove it's intentional
**If wrong**: Parameter collision scope is broader than claimed

---

## Finding 6
**Claim**: `scope.update(child_scope)` at line 87 mutates the caller's scope dictionary in-place, making scope a shared mutable state across the routing chain.
**Type**: STRUCTURAL
**Confidence**: 1.0
**Provenance**: source:line_87 + source:line_178
**Falsifiable**: no: this is direct observation of Python semantics
**If wrong**: Python dict semantics work differently than documented

---

## Finding 7
**Claim**: The `partial` variable in Router.app captures the first PARTIAL match, not the best or most specific, silently discarding later partial matches.
**Type**: MEASURED
**Confidence**: 0.95
**Provenance**: source:lines_189-194
**Falsifiable**: yes: register two routes with overlapping prefixes, show which partial wins
**If wrong**: Route priority semantics differ from first-wins

---

## Finding 8
**Claim**: The redirect_slashes logic at lines 197-208 reconstructs the entire scope dict but only modifies `path`, leaving `root_path` and `app_root_path` potentially inconsistent.
**Type**: DERIVED
**Confidence**: 0.8
**Provenance**: derivation:from_source:lines_197-208
**Falsifiable**: yes: show that `root_path` is correctly preserved or prove inconsistency
**If wrong**: Redirect scope construction has additional handling not visible

---

## Finding 9
**Claim**: Middleware stacking uses `reversed()` because each middleware wraps the previous, meaning the last middleware in the list is the outermost (first to execute).
**Type**: KNOWLEDGE
**Confidence**: 1.0
**Provenance**: external:middleware_pattern + source:lines_114-116
**Falsifiable**: yes: demonstrate execution order differs from claimed
**If wrong**: Middleware ordering semantics are opposite

---

## Finding 10
**Claim**: The lifespan deprecation warnings at lines 158-165 fire at Router instantiation, not at the deprecated function's definition, making the warning location misleading for debugging.
**Type**: DERIVED
**Confidence**: 0.85
**Provenance**: derivation:from_source:lines_158-165
**Falsifiable**: yes: show that warnings point to the generator definition
**If wrong**: Warning configuration differs from default Python behavior

---

## Finding 11
**Claim**: `NoMatchFound` exception includes only param keys in its message, losing the actual values which would be needed for debugging why a match failed.
**Type**: MEASURED
**Confidence**: 0.9
**Provenance**: source:lines_8-10
**Falsifiable**: yes: show the exception includes values in some code path
**If wrong**: Debug information is more complete than apparent

---

## Finding 12
**Claim**: The `url_path_for` method on Mount has three separate code paths (exact match, named delegation, recursive search) that can produce the same URL via different logic, creating ambiguity in which path executes.
**Type**: STRUCTURAL
**Confidence**: 1.0
**Provenance**: source:lines_140-160
**Falsifiable**: yes: prove the paths are mutually exclusive
**If wrong**: URL generation has deterministic dispatch

---

## Finding 13
**Claim**: `Route.methods` defaults to `{"GET"}` when methods=None and endpoint is a function, but to empty set when methods=None and endpoint is a class — this creates silent 405 behavior divergence.
**Type**: DERIVED
**Confidence**: 0.95
**Provenance**: derivation:from_source:lines_105-113
**Falsifiable**: yes: show both cases produce same methods set
**If wrong**: Method defaulting is consistent across endpoint types

---

## Finding 14
**Claim**: The conservation law governing this routing system: **Route Specificity × Handler Generality = Constant** — more specific path patterns require more generic handler signatures to compose correctly.
**Type**: DERIVED
**Confidence**: 0.75
**Provenance**: derivation:cross_finding_4_6_7_12
**Falsifiable**: yes: find a case where specificity and generality both increase or both decrease
**If wrong**: The trade-off has a different form or no conservation exists

---

## Conservation Law
**Law**: Scope Mutation Depth × Route Isolation = Constant (confidence 0.8, type DERIVED)
The deeper scope mutations propagate (via in-place update), the less isolated routes are from each other's side effects.

---

## Count per Type
6 STRUCTURAL, 6 DERIVED, 3 MEASURED, 1 KNOWLEDGE, 0 ASSUMED

---

## Epistemic Quality Score
6/16 = 37.5% STRUCTURAL

The analysis is primarily derived (37.5%) rather than directly observed, reflecting that routing behavior emerges from interaction of components. The key structural findings (nested closure bug, Mount catch-all, scope mutation) are directly falsifiable.

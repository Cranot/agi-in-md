# L12 Structural Analysis: Starlette routing.py

## PHASE 1 — STRUCTURAL ANALYSIS

### Three Properties This Code Simultaneously Claims

1. **Match-type differentiation** — The `Match` enum (NONE/PARTIAL/FULL) claims semantically distinct routing outcomes with different handling implications
2. **Uniform dispatch** — All non-NONE matches eventually invoke `route.handle(scope, receive, send)` regardless of match type
3. **Method awareness at routing layer** — `Route.matches()` checks `scope["method"]` against `self.methods` and returns PARTIAL on mismatch

### Proof They Cannot Coexist

If match-type differentiation were complete, PARTIAL would dispatch differently than FULL (e.g., auto-405). If dispatch were truly uniform, the PARTIAL/FULL distinction serves no purpose at dispatch time. If method awareness were complete at routing layer, the router would handle 405 directly instead of calling endpoint handlers for method mismatches.

**The contradiction:** Router identifies method mismatches (returns PARTIAL) but still executes the mismatched endpoint. The Match enum creates the *appearance* of differentiated handling while the implementation provides *uniform* dispatch.

### Conservation Law

```
MATCH_SEMANTIC_RICHNESS × DISPATCH_SIMPLICITY = constant
```

Rich match semantics (NONE/PARTIAL/FULL with distinct meanings) requires complex dispatch logic. Simple dispatch (call handle() for everything) requires simple match semantics (MATCH/NO_MATCH). You cannot have rich matching AND simple dispatch.

### Concealment Mechanism

The `Match.PARTIAL` return value conceals delegation as differentiation. The enum suggests the router is "handling" method mismatches differently, but tracing `Router.app()` reveals:

```python
elif match is Match.PARTIAL and partial is None:
    partial = route
    partial_scope = child_scope
# ...later...
if partial is not None:
    scope.update(partial_scope)
    await partial.handle(scope, receive, send)  # Same dispatch as FULL!
```

The PARTIAL enum value is a **semantic placeholder** — it marks method mismatches for potential differentiation, but no differentiation occurs. The endpoint receives requests with methods it explicitly doesn't handle.

### Improvement That Recreates The Problem Deeper

Add automatic 405 generation for PARTIAL matches:

```python
if partial is not None:
    allowed = ", ".join(partial.methods) if hasattr(partial, 'methods') else ""
    response = PlainTextResponse("Method Not Allowed", status_code=405, 
                                  headers={"Allow": allowed})
    await response(scope, receive, send)
    return
```

This "fixes" the delegation issue but creates deeper problems:
1. **Router now HTTP-aware** — was protocol-agnostic ASGI
2. **No 405 customization** — endpoints lose control of error responses
3. **Websocket divergence** — ws PARTIAL matches need different handling
4. **Match encodes HTTP status** — enum now implicitly means "405"

**The conservation law manifests deeper:** `ROUTING_SPECIFICITY × PROTOCOL_INDEPENDENCE = constant`. More specific routing (auto-405) destroys protocol independence.

---

## PHASE 2 — KNOWLEDGE AUDIT

| Claim | Classification | Confidence | If Wrong, What Changes |
|-------|----------------|------------|------------------------|
| Match enum has NONE/PARTIAL/FULL | STRUCTURAL (line 18-22) | 1.0 SAFE | — |
| Route.matches() checks methods | STRUCTURAL (line 143-148) | 1.0 SAFE | — |
| PARTIAL matches still call handle() | STRUCTURAL (line 236-239) | 1.0 SAFE | — |
| PARTIAL stored as fallback | STRUCTURAL (line 229-231) | 1.0 SAFE | — |
| Match enum suggests differentiation | CONTEXTUAL | 0.85 | PARTIAL just marks "defer this" |
| Conservation law form | STRUCTURAL/DERIVED | 0.8 | Different framing possible |
| Improvement breaks protocol independence | STRUCTURAL/DERIVED | 0.9 | Could use ASDI-agnostic 405 |

**Low-confidence claim flagged:** "PARTIAL enum suggests differentiated handling" — this is my interpretation of the enum's purpose. The code shows PARTIAL is used for fallback priority, which IS a semantic difference (first FULL wins, OR first PARTIAL). Revised claim: PARTIAL provides **priority differentiation** (deferred dispatch) not **handling differentiation** (different dispatch path).

---

## PHASE 3 — SELF-CORRECTION

### Corrected Defect Table (SAFE + Verified Claims Only)

| Location | Defect | Severity | Type |
|----------|--------|----------|------|
| Route.matches():143-148 | Returns PARTIAL for method mismatch but caller still invokes handle() | MEDIUM | Structural |
| Router.app():229-239 | PARTIAL dispatches identically to FULL — no method validation at router layer | MEDIUM | Structural |
| Mount.routes property | Exposes `_base_app.routes` but dispatch goes through `self.app` (middleware-wrapped) — introspection ≠ execution path | LOW | Structural |
| Router.app():242-256 | redirect_slashes creates second matching pass — route order matters differently for slash-variants | LOW | Structural |
| Mount.url_path_for():189-205 | Complex delegation with `name:` prefix convention — implicit contract not enforced | LOW | Structural |

### Verified Conservation Law

```
MATCH_SEMANTIC_RICHNESS × DISPATCH_SIMPLICITY = constant
```

**Evidence from source:**
- Rich semantics: Match enum (3 states) + methods filtering (lines 143-148)
- Simple dispatch: Single `handle()` call path for both PARTIAL and FULL (lines 236-239)
- The tension: Methods are checked but not enforced — richness without dispatch complexity

### What This Analysis Conceals (Meta-Application)

This analysis treats the code as a static artifact, but routing systems are fundamentally about **runtime composition**. The PARTIAL mechanism enables:
- Middleware to intercept before endpoint
- Error handlers to customize 405
- Method override headers to work

The "delegation as differentiation" pattern may be intentional — router identifies, handler decides. The conservation law from the *framework author's perspective* might be: `ROUTER_COMPLEXITY × FRAMEWORK_FLEXIBILITY = constant`.

---

**Final output:**
- **Conservation law:** `MATCH_SEMANTIC_RICHNESS × DISPATCH_SIMPLICITY = constant`
- **Verified defects:** 5 (all STRUCTURAL, source-grounded)
- **Confabulations removed:** 1 (PARTIAL "suggests" handling differentiation — interpretation, not verifiable)

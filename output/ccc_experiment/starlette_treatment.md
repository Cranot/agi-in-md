## STEP 1: Inverted Alternative — Explicit Context Passing

The core architectural choice in Starlette is **scope mutation as implicit communication channel**. Routes inject keys into scope; downstream handlers depend on these keys without declaring them.

**Inverted system:** Immutable scope + explicit context return.

```python
@dataclass(frozen=True)
class MatchResult:
    match: Match
    context: dict | None  # Returned, never mutated into scope

class Route:
    def matches(self, scope) -> MatchResult:
        # scope is NEVER modified
        if self.path_regex.match(scope["path"]):
            context = {"endpoint": self.endpoint, "path_params": extracted}
            if self.methods and scope["method"] not in self.methods:
                return MatchResult(Match.PARTIAL, context)
            return MatchResult(Match.FULL, context)
        return MatchResult(Match.NONE, None)
    
    async def handle(self, scope, context, receive, send):
        # Handler receives BOTH - signature change required
        await self.app(scope, context, receive, send)

class Router:
    async def app(self, scope, receive, send):
        partial_result = None
        for route in self.routes:
            result = route.matches(scope)  # scope unchanged throughout
            if result.match == Match.FULL:
                await route.handle(scope, result.context, receive, send)
                return
            elif result.match == Match.PARTIAL and partial_result is None:
                partial_result = (route, result.context)
        
        if partial_result:
            route, context = partial_result
            await route.handle(scope, context, receive, send)  # 405 path
            return
```

**Key inversions:**
- Scope never mutated → all communication explicit
- Handler signature changes → `(scope, context, receive, send)` not `(scope, receive, send)`
- Context is returned, not injected → caller controls what callee receives

---

## STEP 2: Claim Survival Analysis

| Original Claim | Survives Inversion? | Verdict |
|----------------|---------------------|---------|
| **Scope Mutation Chain** — handlers depend on route-injected keys | **NO** — handlers receive context explicitly, not through scope | **Artifact** |
| **Reversed Middleware Wrapping** — last declared is outermost | **YES** — middleware ordering is independent of scope mechanism | **Invariant** |
| **Partial Match Reservation** — PARTIAL held for 405 fallback | **STRUCTURE survives, MECHANISM changes** — still need to hold partial matches, but stored in variable not scope | **Hybrid** |

**What becomes visible ONLY through comparison:**

1. **The Match enum is control-flow disguised as data.** PARTIAL is not a "match quality" — it's a directive saying "hold this, may need later." The enum encodes a state machine (NONE→continue, PARTIAL→remember, FULL→dispatch). This is invariant; both systems need it.

2. **Scope mutation is signature compression.** The inverted system requires handler signatures like `(scope, context, receive, send)`. Add middleware state, route metadata, mount context — the signature explodes. Scope mutation compresses this into one bag. The "hidden dependency" I identified is actually a **deliberate pattern for parameter aggregation**.

3. **Middleware reversal is about declaration intuition, not data flow.** It survives inversion because it addresses a different problem: "I declared auth before logging, so auth should see the request first." This is human-factors, not architectural.

---

## STEP 3: Revised Conservation Law

**Original law (DOES NOT SURVIVE):** Expressiveness × Safety = Constant

Both systems can be equally expressive (add keys to context) and equally safe (validate context). The trade-off I identified was wrong.

**Revised law (SURVIVES INVERSION):**

**Channel Flexibility × Reasoning Locality = Constant**

Where:
- **Channel Flexibility** = ease of adding new information pathways between components without signature changes
- **Reasoning Locality** = how much of the data flow can be understood by examining one location

**Original system:** High flexibility (add key to scope anywhere, downstream sees it), low locality (must trace all mutations to understand what keys exist when).

**Inverted system:** Low flexibility (add parameter → update all signatures in call chain), high locality (handler signature declares everything it receives).

This trade-off is **structural** — you cannot have both. Either information flows implicitly through a shared bag (flexible but non-local), or explicitly through parameters (local but rigid).

---

## STEP 4: What the Contrast Reveals

**What my original construction concealed:**

1. **"Hidden dependency" was a value judgment, not an observation.** I framed scope mutation as a defect. The contrast reveals it's a **design decision with genuine benefits** — signature stability under composition. A mount can add context without changing handler signatures across the entire subtree.

2. **The conservation law was misidentified.** I claimed Expressiveness × Safety. The contrast shows safety is achievable in both systems (validation layer on scope or on context). The real trade-off is flexibility vs. locality.

3. **PARTIAL is not about "match quality."** My original analysis said PARTIAL means "incomplete match." The contrast reveals PARTIAL is a **control-flow token** — it tells the Router "hold this result for potential fallback dispatch." The name is misleading; it should be `Match.MAYBE_405_LATER`.

4. **The mechanism I designed to "deepen concealment" actually surfaced the control-flow-in-data pattern.** My `_method_blocked` key was not a deepening — it was **making explicit what was already implicit**. The original PARTIAL handling IS control flow in enum form. My modification just moved it from enum to scope key.

5. **Most critically: The inverted system would converge back toward the original.** If you need to pass 5+ pieces of context through 4 layers of mounts and middleware, you'd either:
   - Create a context bag object (which is just scope by another name)
   - Explode handler signatures to 8+ parameters
   
   The original design is not arbitrary — it's a **local optimum** given the constraints of ASGI's `(scope, receive, send)` contract.

# Structural Diagnosis: Auth Middleware Chain

## The Claim

> **The deepest structural problem: the `authenticate` method implements a multi-phase state machine (identity resolution → claim accumulation → access control) disguised as     -> Done (156s) -> 303 lines -> /d/OneDrive - CosmoHac/Project/agi-in-md/output/round25/opus_L11_conservation_law_task_H.md

========================================
 Completed 1 experiments
 Results in: /d/OneDrive - CosmoHac/Project/agi-in-md/output/round25/
========================================

 Examples:
   bash run.sh sonnet task_H L8_generative_v2
   bash run.sh opus task_D1 L8_generative_v2
   bash run.sh sonnet task_H L7_diagnostic
ter-wins with no collision detection. The last checker to return `"identity"` silently replaces earlier identities. The chain's correctness depends entirely on insertion order, but `add()` gives no tools to reason about order.

**Attacker:** This is standard middleware-chain architecture. Express, Django, Rack — they all pass mutable context through ordered handlers. This is fine in practice because one team controls the registration order.

**Probes assumptions:** Both of you assume the problem is *data flow*. The deeper issue is *temporal*: the `"denied"` early-return and the `"identity"` assignment are evaluated in the same loop iteration. There are no phase gates. A checker can deny a request based on the absence of claims that a later checker would have provided.

### Claim Transformation

> **Transformed claim: The absence of phase separation — not the shared mutable state — is the structural defect. Shared mutability is a symptom; the missing phase gates are the disease.**

**The diagnostic gap:** My original claim targeted *data coupling*. The transformed claim reveals the problem is *temporal* — you can perfectly isolate data and still authorize against an incomplete picture if there's no gate between "who are you?" and "may you do this?"

---

## The Concealment Mechanism

**Name: Procedural Linearization.**

The `for checker in self._chain` loop makes a multi-phase state machine *look* like a flat, homogeneous sequence. The visual simplicity of the loop conceals that checkers are not peers — some establish identity, some enrich claims, some enforce policy — but the code treats them identically. The simplicity *is* the concealment.

Additionally: the role cache sitting *outside* the loop is an unconscious admission that phases exist. The code already knows role-fetching must happen *after* identity establishment — it just refuses to generalize this into a structural principle.

---

## First Improvement: Deepens the Concealment

```python
class AuthMiddleware:
    def __init__(self):
        self._chain = []
        self._bypass_routes = set()
        self._role_cache = {}

    def add(self, checker_fn, scope="all", priority=100):
        self._chain.append({"fn": checker_fn, "scope": scope, "priority": priority})
        self._chain.sort(key=lambda c: c["priority"])

    def bypass(self, route):
        self._bypass_routes.add(route)

    def authenticate(self, request):
        if request.path in self._bypass_routes:
            request.user = {"role": "anonymous", "permissions": []}
            return request

        context = {"request": request, "identity": None, "claims": {}}
        errors = []

        for checker in self._chain:
            if checker["scope"] != "all" and checker["scope"] != request.method:
                continue
            try:
                result = checker["fn"](context)
            except Exception as e:
                errors.append(str(e))
                continue                          # ← silent degradation
            if result.get("denied"):
                return {"status": 403, "error": result["reason"]}
            context["claims"].update(result.get("claims", {}))
            if result.get("identity"):
                context["identity"] = result["identity"]

        if errors:
            log_auth_errors(errors)

        if context["identity"] is None:
            return {"status": 401, "error": "No identity established"}

        cache_key = context["identity"]["id"]
        if cache_key in self._role_cache:
            context["claims"]["roles"] = self._role_cache[cache_key]
        else:
            roles = fetch_roles(context["identity"])
            self._role_cache[cache_key] = roles
            context["claims"]["roles"] = roles

        request.user = {**context["identity"], **context["claims"]}
        return request
```

**Why it passes review:** Priority makes ordering explicit. Error handling adds resilience. Both are "obviously good."

**Why it deepens concealment:**

- Priority *numbers* give the **illusion** of phase separation without structural enforcement. Priority 10 vs 50 *looks like* "identity first" but nothing prevents an identity checker from failing and an authz checker from still running.
- `try/except/continue` transforms authentication failure into **silent partial-auth**. The original code had accidental safety: a crashing identity checker would halt the chain. This "improvement" removes that safety.
- Sorting destroys registration-order readability — now the effective order is scattered across `priority=` kwargs throughout the codebase.

### Three Properties Visible Only Because I Strengthened It

1. **The phase problem is not an ordering problem.** Perfect priority ordering still allows authorization against incomplete identity, because the loop has no gate between phases.
2. **Error tolerance is the enemy of security invariants.** `try/except/continue` reveals the original had *accidental safety*: any exception killed the chain. "Graceful degradation" is the wrong principle for security pipelines.
3. **The cache is structurally homeless.** Putting priority on chain checkers highlights that the role cache lives *outside* the chain with hardcoded special privileges — it's a phase the code won't name.

---

## Diagnostic Applied to the Improvement

**What the improvement conceals:** That `denied` early-return is evaluated within the same loop that establishes identity. A priority=50 authorizer can deny based on missing claims a priority=60 enricher would have provided.

**What property of the original is visible only because the improvement recreates it:** The improvement recreates *denial-against-incomplete-state*, now made **more dangerous** because developers see priority numbers and *assume* correctness. A silent `continue` past a failed identity checker (priority=10) means an authorizer (priority=50) runs against `identity=None`.

---

## Second Improvement: Explicit Phase Gates

```python
from enum import Enum

class Phase(Enum):
    IDENTIFY  = 1
    ENRICH    = 2
    AUTHORIZE = 3

class AuthMiddleware:
    def __init__(self):
        self._phases = {phase: [] for phase in Phase}
        self._bypass_routes = set()
        self._role_cache = {}

    def add(self, checker_fn, phase: Phase, scope="all"):
        self._phases[phase].append({"fn": checker_fn, "scope": scope})

    def bypass(self, route):
        self._bypass_routes.add(route)

    def authenticate(self, request):
        if request.path in self._bypass_routes:
            request.user = {"role": "anonymous", "permissions": []}
            return request

        context = {"request": request, "identity": None, "claims": {}}

        # ── Phase 1: Identity ──────────────────────────
        for checker in self._phases[Phase.IDENTIFY]:
            if checker["scope"] != "all" and checker["scope"] != request.method:
                continue
            result = checker["fn"](context)
            if result.get("identity"):
                context["identity"] = result["identity"]
                break                               # first identity wins

        if context["identity"] is None:             # ← hard gate
            return {"status": 401, "error": "No identity established"}

        # ── Phase 2: Enrichment ────────────────────────
        cache_key = context["identity"]["id"]
        if cache_key in self._role_cache:
            context["claims"]["roles"] = self._role_cache[cache_key]
        else:
            roles = fetch_roles(context["identity"])
            self._role_cache[cache_key] = roles
            context["claims"]["roles"] = roles

        for checker in self._phases[Phase.ENRICH]:
            if checker["scope"] != "all" and checker["scope"] != request.method:
                continue
            result = checker["fn"](context)
            context["claims"].update(result.get("claims", {}))

        # ── Phase 3: Authorization ─────────────────────
        for checker in self._phases[Phase.AUTHORIZE]:
            if checker["scope"] != "all" and checker["scope"] != request.method:
                continue
            result = checker["fn"](context)
            if result.get("denied"):
                return {"status": 403, "error": result["reason"]}

        request.user = {**context["identity"], **context["claims"]}
        return request
```

### Diagnostic Applied Again

**What this conceals:** Within each phase, the original mutability problems persist. Enrichment checkers still `update()` each other's claims. A buggy enricher can write `context["identity"] = something_else` — the phase boundary is in the *control flow* but not in the *data model*. The role cache is *still* hardcoded outside the enricher abstraction.

**What property of the original is visible only because this improvement recreates it:** The **shared mutable context dict**. Even with perfect phase gates, the `context` dict gives every function in every phase unbounded write access to the entire auth state. The improvement recreated *intra-phase coupling* by solving only *inter-phase ordering*.

---

## The Structural Invariant

> **The authorization decision depends on accumulated mutable state that no single point in the code can fully observe or validate.**

This persists through every improvement because it's a property of the *problem space*: authentication inherently requires combining information from multiple independent sources (tokens, sessions, databases, external services) into a single access decision.

---

## Inversion: Make the Impossible Trivially Satisfiable

```python
from dataclasses import dataclass
from typing import FrozenSet, Callable, Optional, List

@dataclass(frozen=True)
class Identity:
    id: str
    source: str
    attributes: tuple  # frozen

@dataclass(frozen=True)
class AuthDecision:
    identity: Identity
    roles: FrozenSet[str]
    permissions: FrozenSet[str]

class AuthMiddleware:
    def __init__(self):
        self._identifier: Optional[Callable] = None   # exactly one
        self._enrichers: List[Callable] = []           # Identity → Claims (pure)
        self._authorizers: List[Callable] = []         # AuthDecision → bool (pure)
        self._bypass_routes: set = set()

    def set_identifier(self, fn):
        self._identifier = fn

    def add_enricher(self, fn):
        self._enrichers.append(fn)

    def add_authorizer(self, fn):
        self._authorizers.append(fn)

    def bypass(self, route):
        self._bypass_routes.add(route)

    def authenticate(self, request):
        if request.path in self._bypass_routes:
            request.user = AuthDecision(
                Identity("anonymous", "bypass", ()), frozenset(), frozenset()
            )
            return request

        # Phase 1: Exactly one identifier — no ambiguity
        identity = self._identifier(request)
        if identity is None:
            return {"status": 401, "error": "No identity established"}

        # Phase 2: Enrichers see ONLY immutable identity — provably independent
        all_roles, all_perms = set(), set()
        for enricher in self._enrichers:
            claims = enricher(identity)          # pure function of identity
            all_roles  |= claims.get("roles", set())
            all_perms  |= claims.get("permissions", set())

        # Phase 3: Authorizers see COMPLETE, FROZEN decision
        decision = AuthDecision(identity, frozenset(all_roles), frozenset(all_perms))
        for authorizer in self._authorizers:
            if not authorizer(decision, request):
                return {"status": 403, "error": "Access denied"}

        request.user = decision
        return request
```

**The originally impossible property — complete observability — is now trivial:**
- Identity is established once, immutably, by a single function.
- Enrichers are pure functions of `Identity` — they *cannot* see each other's output.
- Claims combine via set union, not dict overwrite — no silent clobbering.
- Authorizers receive a `frozen=True` dataclass — the *complete, immutable* picture.
- Every authorizer observes exactly the same state.

---

## The New Impossibility

**Enrichers cannot depend on each other's output.**

- **Derived claims are impossible:** "If LDAP says role X, add permission Y" requires seeing LDAP's output.
- **Conditional enrichment is impossible:** "Skip expensive DB lookup if token already has sufficient claims."
- **Cross-source correlation is impossible:** Combining OAuth scopes with LDAP groups with application overrides — each enricher is blind to the others.

---

## The Conservation Law

| | Original | Inverted |
|---|---|---|
| **Impossible** | Complete observability — no component sees the full auth state | Inter-enricher dependency — no enricher sees another's output |
| **Trivial** | Composability — any checker can read/write anything, depend on anything | Observability — every authorizer sees the complete, frozen state |

### The finding:

> **In any authentication middleware, the product of *observability* (can a component see the complete auth state?) and *composability* (can components depend on each other's contributions?) is conserved.**

> **Maximizing one necessarily minimizes the other.**

The original code chose maximum composability: any checker can read/write the shared context, creating rich inter-checker dependencies — at the cost of no component ever knowing if it's operating on complete information.

The inverted design chose maximum observability: every authorizer provably sees the complete picture — at the cost of enrichers being unable to depend on each other.

**The real engineering question was never "how do I fix the shared mutable state?" It was: "Where on the observability–composability spectrum does my threat model require this system to sit?" — and can I make that choice *visible* in the code rather than concealed by a for loop?**

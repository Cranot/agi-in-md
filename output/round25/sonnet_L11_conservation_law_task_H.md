# Auth Middleware: A Structural Diagnosis

---

## I. The Initial Claim

**Falsifiable claim:** Any checker in this chain can silently overwrite security-critical claims established by earlier checkers — `context["claims"].update(result.get("claims", {}))` — meaning the security guarantees of checker N are not preserved through checker N+1. Specifically: add two checkers that both set `claims["roles"]`, and the second always wins. No mechanism detects or prevents this.

---

## II. The Three Expert Test

**Defender:** Confirmed. The `update()` call is a last-writer-wins dict merge. Checker ordering determines the final security context. This is testable in one line.

**Attacker:** Too narrow. The deeper problem is identity replacement — `context["identity"] = result["identity"]` runs unconditionally if any checker returns an identity. A late-chain checker can replace an already-established identity. Claim overwriting is downstream noise; identity replacement is the mechanism.

**Probe (what both take for granted):** Both assume the problem is adversarial checkers. But neither questions the architectural premise: that *adding* checkers increases security. This code makes security **non-monotonic** — adding a checker can eliminate security guarantees provided by earlier ones. The chain is assumed to be additive. It isn't.

**The transformed claim:** The chain violates security monotonicity. Adding checkers can decrease the security guarantees of the system. The original claim (data overwrite) was a symptom; the real pathology is the architecture's assumption that composition is additive when it is actually substitutive.

**The diagnostic gap:** I started with a data-flow observation (overwrites) and ended with an architectural property (non-monotonicity). The distance between these is itself a signal about how deeply the problem is embedded.

---

## III. The Concealment Mechanism

**Accumulative appearance masks substitutive semantics.**

The sequential loop with `claims.update()` reads as *defense-in-depth* — each checker enriches the security context. The word "update" reads as "add to." The real semantics: later checkers *replace* earlier checkers' claims with no detection, no logging, no conflict signal. The pattern looks like layering. It is actually overwriting.

The code makes this invisible by:
- Using `dict.update()` whose semantics are known but whose security implications aren't surfaced
- Providing no type distinction between security-critical claims (`roles`, `permissions`) and enrichment claims (`display_name`)
- Providing no conflict detection at chain registration time
- Giving `add()` no ordering semantics or constraint language

---

## IV. First Improvement — Deepening the Concealment

Add provenance tracking and explicit conflict resolution. This will pass code review as a security enhancement:

```python
class AuthMiddleware:
    def __init__(self):
        self._chain = []
        self._bypass_routes = set()
        self._role_cache = {}

    def add(self, checker_fn, scope="all", name="unnamed", priority=0):
        self._chain.append({
            "fn": checker_fn,
            "scope": scope,
            "name": name,
            "priority": priority
        })
        # Sort by priority: higher priority checkers run last and win conflicts
        self._chain.sort(key=lambda c: c["priority"])

    def authenticate(self, request):
        if request.path in self._bypass_routes:
            request.user = {"role": "anonymous", "permissions": []}
            return request

        context = {
            "request": request,
            "identity": None,
            "claims": {},
            "claim_sources": {},      # provenance tracking
            "claim_priorities": {}    # conflict resolution metadata
        }

        for checker in self._chain:
            if checker["scope"] != "all" and checker["scope"] != request.method:
                continue
            result = checker["fn"](context)
            if result.get("denied"):
                return {"status": 403, "error": result["reason"]}

            new_claims = result.get("claims", {})
            for key, value in new_claims.items():
                existing_priority = context["claim_priorities"].get(key, -1)
                if checker["priority"] >= existing_priority:
                    context["claims"][key] = value
                    context["claim_sources"][key] = checker["name"]
                    context["claim_priorities"][key] = checker["priority"]

            if result.get("identity"):
                context["identity"] = result["identity"]

        if context["identity"] is None:
            return {"status": 401, "error": "No identity established"}

        cache_key = context["identity"]["id"]
        if cache_key in self._role_cache:
            context["claims"]["roles"] = self._role_cache[cache_key]
        else:
            roles = fetch_roles(context["identity"])
            self._role_cache[cache_key] = roles
            context["claims"]["roles"] = roles

        request.user = {
            **context["identity"],
            **context["claims"],
            "_claim_sources": context["claim_sources"]  # audit trail
        }
        return request
```

This passes code review because it adds: named checkers, priority ordering, conflict resolution, provenance tracking, an audit trail on the request object. It reads as a mature implementation of the original pattern.

### Why it deepens the concealment:

1. **Escalation is now policy, not bug.** `priority >= existing_priority` means higher-priority checkers explicitly win. Privilege escalation through checker ordering is designed in, not accidental.
2. **The audit trail creates a false sense of accountability.** `_claim_sources` records *which checker won* but not *what was overwritten or why*.
3. **Identity replacement remains completely unaddressed.** The improvement's visible sophistication draws attention away from the unchanged identity replacement path.

---

## V. Three Properties Visible Only from Attempting to Strengthen

**Property 1: The conflict resolution policy IS the security model.**
Before the improvement, claim overwriting looked like a bug. After, it becomes apparent that the chain's security properties are entirely determined by an underspecified conflict resolution function. There is no ground truth for what "correct" claims are — only resolution rules. The security model was always implicit in the update semantics; the improvement makes that visible by formalizing it.

**Property 2: Identity replacement is a separate, orthogonal problem.**
By making claims resolution explicit and rigorous, the improvement highlights by contrast that identity replacement (`context["identity"] = result["identity"]`) is untouched — a different axis of the same vulnerability class. No amount of claim-level sophistication addresses it.

**Property 3: All checkers are treated as peers, which is semantically wrong.**
The priority system reveals that the real need is a *type distinction* between checkers — between those that *establish* security facts and those that *enrich* an already-established context. Priority is a workaround for the absence of this distinction.

---

## VI. Applying the Diagnostic to the First Improvement

**What the improvement conceals:**

The `claim_sources` audit trail logs which checker's value survived, but not the security-relevant fact: *what did the earlier checker assert, and should it have been overwritable?* The audit trail is a record of outcomes, not of conflicts. A security auditor reading `claim_sources: {"roles": "jwt_checker"}` learns nothing about whether an earlier checker's role assertion was suppressed.

**What property of the original problem is visible because the improvement recreates it:**

The chain still has **no taxonomy of claims.** `roles` and `display_name` are treated identically in the priority resolution logic. The improvement reveals that the original problem wasn't "overwrites happen without detection" — it was "the system has no representation of which claims are security-critical vs. which are enrichment data." This is why any conflict resolution policy applied uniformly is wrong.

---

## VII. Second Improvement — Addressing the Recreated Property

Introduce a typed claim taxonomy. Security-critical claims are write-once; enrichment claims are freely overwritable:

```python
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Any, FrozenSet

class ClaimKind(Enum):
    SECURITY = auto()    # write-once, conflict raises
    ENRICHMENT = auto()  # last-writer-wins, no conflict

SECURITY_CLAIMS: FrozenSet[str] = frozenset({"roles", "permissions", "scopes", "groups"})

class SecurityConflictError(Exception):
    def __init__(self, key, existing, attempted, source):
        self.key = key
        self.existing = existing
        self.attempted = attempted
        self.source = source
        super().__init__(f"Checker '{source}' attempted to overwrite security claim '{key}'")

@dataclass
class AuthContext:
    request: object
    identity: dict | None = None
    identity_locked: bool = False
    security_claims: dict = field(default_factory=dict)
    enrichment_claims: dict = field(default_factory=dict)

    def set_claim(self, key: str, value: Any, source: str):
        if key in SECURITY_CLAIMS:
            if key in self.security_claims:
                raise SecurityConflictError(
                    key, self.security_claims[key], value, source
                )
            self.security_claims[key] = value
        else:
            self.enrichment_claims[key] = value

    def set_identity(self, identity: dict, source: str):
        if self.identity_locked:
            raise SecurityConflictError(
                "identity", self.identity, identity, source
            )
        self.identity = identity
        self.identity_locked = True

    @property
    def merged_claims(self):
        # Security claims take precedence over enrichment claims on key collision
        return {**self.enrichment_claims, **self.security_claims}


class AuthMiddleware:
    def __init__(self):
        self._chain = []
        self._bypass_routes = set()
        self._role_cache = {}

    def add(self, checker_fn, scope="all", name="unnamed"):
        self._chain.append({"fn": checker_fn, "scope": scope, "name": name})

    def bypass(self, route):
        self._bypass_routes.add(route)

    def authenticate(self, request):
        if request.path in self._bypass_routes:
            request.user = {"role": "anonymous", "permissions": []}
            return request

        context = AuthContext(request=request)

        for checker in self._chain:
            if checker["scope"] != "all" and checker["scope"] != request.method:
                continue
            result = checker["fn"](context)
            if result.get("denied"):
                return {"status": 403, "error": result["reason"]}

            # Claims: typed, write-once for security-critical
            for key, value in result.get("claims", {}).items():
                context.set_claim(key, value, checker["name"])  # raises on conflict

            # Identity: write-once
            if result.get("identity"):
                context.set_identity(result["identity"], checker["name"])

        if context.identity is None:
            return {"status": 401, "error": "No identity established"}

        cache_key = context.identity["id"]
        if cache_key not in self._role_cache:
            self._role_cache[cache_key] = fetch_roles(context.identity)
        # Roles from fetch_roles cannot overwrite a checker-established role set
        if "roles" not in context.security_claims:
            context.security_claims["roles"] = self._role_cache[cache_key]

        request.user = {**context.identity, **context.merged_claims}
        return request
```

### Applying the Diagnostic to the Second Improvement

**What does this conceal?**

`SECURITY_CLAIMS` is a static frozenset defined at module level. But whether a claim is security-critical is **context-dependent** — in a multi-tenant system, `tenant_id` is security-critical; in a single-tenant system, it's enrichment. The write-once guarantee is only as good as the taxonomy, and the taxonomy is hardcoded.

More critically: making security claims write-once means **the first checker to run establishes the security context that all subsequent checkers must accept.** Chain ordering is now a security invariant — not because later checkers can overwrite (they can't), but because earlier checkers have exclusive authority over security-critical claims. The problem inverts: instead of "last checker wins," it becomes "first checker wins." The dependency on ordering is unchanged.

**What property of the original problem is visible because the improvement recreates it?**

**Chain ordering is a security invariant that the architecture expresses nowhere.** Every improvement forces a winner when two checkers conflict — last-wins, priority-wins, first-wins, or conflict-error — and every winner policy makes the order in which `add()` is called a load-bearing security specification. But `add()` is a list append. There is no constraint language. There is no ordering declaration. There is no static verification that the ordering is correct. The security-critical ordering is invisible in the code that determines it.

---

## VIII. The Structural Invariant

**The invariant that persists through every improvement:**

> **Chain ordering determines security outcomes, but the architecture treats ordering as an implementation detail rather than a security-critical specification.**

This is not a property of any implementation. It is a property of the problem space: a middleware chain that accumulates authentication + authorization state through sequential composition makes each checker's behavior dependent on what preceding checkers have asserted. There is no escape from this via conflict resolution policy — every policy (first-wins, last-wins, priority, conflict-error) just makes ordering load-bearing in a different way.

The invariant survives because any chain that allows inter-checker information flow (checker N sees checker N-1's output) necessarily makes ordering semantically significant. And any chain that processes both authentication (who are you?) and authorization (what can you do?) needs inter-checker information flow, because authorization requires an established identity.

---

## IX. The Inversion

**Invert the invariant:** Design where chain ordering is irrelevant to security outcomes.

The only way to make ordering irrelevant is to eliminate inter-checker information flow — each checker operates on the raw request only, producing an independent typed verdict:

```python
from dataclasses import dataclass
from typing import Callable

@dataclass(frozen=True)
class AuthVerdict:
    identity: dict | None
    granted_permissions: frozenset[str]
    denied_permissions: frozenset[str]
    is_explicit_deny: bool
    reason: str | None

class OrderIndependentAuth:
    """
    Each probe sees only the raw request.
    No probe sees another probe's output.
    Composition is algebraic, not sequential.
    """
    def __init__(self):
        self._probes: list[Callable] = []

    def add_probe(self, probe_fn: Callable):
        self._probes.append(probe_fn)  # order is irrelevant

    def authenticate(self, request):
        if not self._probes:
            return {"status": 401, "error": "No probes registered"}

        # All probes run independently against raw request
        verdicts: list[AuthVerdict] = [p(request) for p in self._probes]

        # Explicit deny from any probe = deny (order-independent)
        for v in verdicts:
            if v.is_explicit_deny:
                return {"status": 403, "error": v.reason}

        # Identity: must be unanimous among probes that establish one
        identities = [v.identity for v in verdicts if v.identity is not None]
        if len(set(
            frozenset(i.items()) for i in identities
        )) > 1:
            return {"status": 401, "error": "Identity conflict across probes"}
        identity = identities[0] if identities else None

        if identity is None:
            return {"status": 401, "error": "No identity established"}

        # Permissions: intersection of all granted sets (conservative)
        all_granted = [v.granted_permissions for v in verdicts
                       if v.granted_permissions]
        effective_permissions = (
            set.intersection(*[set(g) for g in all_granted])
            if all_granted else set()
        )

        # Explicit denials from any probe remove from effective
        all_denied = set().union(*(v.denied_permissions for v in verdicts))
        effective_permissions -= all_denied

        request.user = {**identity, "permissions": effective_permissions}
        return request
```

Now `add_probe` order is genuinely irrelevant. Verdicts compose algebraically. Unanimous identity, intersected permissions, union of explicit denials.

### The New Impossibility

**You cannot express sequential security policies.**

Real security policies routinely require one check's output to be another check's input:

- *"If the JWT probe establishes identity X, and identity X is in group `admin`, then grant elevated permissions"* — the group-membership probe needs to know what identity the JWT probe established.
- *"Skip the rate-limit probe if the client certificate probe confirms a service account"* — the rate-limit probe needs the certificate probe's output.
- *"If the IP allowlist probe grants access, the 2FA probe can be skipped"* — conditional probe activation requires observable intermediate state.

None of these are expressible when probes are independent. The moment a probe consumes another probe's output, you have inter-probe information flow, which reintroduces ordering dependence.

**The new impossibility:** Compositionality of security logic requires probes to consume each other's outputs. Order-independence requires that they don't. You cannot have both.

---

## X. The Conservation Law

**Original impossibility:** Order-independent security with inter-checker information flow.

**Inverted impossibility:** Sequential security policy expression with order-independent probe composition.

**The Conservation Law:**

> **In an authentication/authorization system, inter-check information flow and order-independence are conserved in opposition. Gaining one requires sacrificing the other, and the expressiveness of your security policy language is bounded by your position on this tradeoff.**

More precisely: a middleware architecture's ability to express *conditional* security policies (where check B depends on check A's output) is exactly equal to the degree to which chain ordering is a security-critical specification. This quantity is conserved. You can move it — encode ordering into types (improvement 2), into priorities (improvement 1), into algebraic combinators (the inversion) — but you cannot eliminate it. The "problem" of ordering-dependent security is not a flaw in the implementation. It is the implementation's faithful reflection of a property of the problem domain: **authorization is compositional, and composition has order.**

### What this reveals about the original code

The original `AuthMiddleware` is not poorly designed because it has a hidden ordering dependency. It is poorly designed because it **fails to acknowledge and specify** the ordering dependency it necessarily has. Every security-relevant behavior is determined by `add()` call order, and `add()` is a list append with no constraint language, no documentation of required ordering, and no static verification.

The real fix is not a better conflict resolution policy. It is a **chain specification language** — a way to declare ordering constraints, checker dependencies, and composition semantics as first-class artifacts that can be inspected, tested, and verified independently of runtime behavior. Until that exists, every "improvement" is load-bearing on an invisible invariant.

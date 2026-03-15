## The Diagnostic

### Initial Claim (Falsifiable)

**The deepest structural problem is that `request.user` is a composite that was never verified as a whole.** The chain verifies sub-properties sequentially — identity here, claims there — then merges them. No checker ever approved `{this identity + these claims}` as a coherent unit. Later checkers silently overwrite the identity established by earlier ones, so claims accumulate for an identity that may no longer be the one that earned them.

*Falsifiable form:* If checker A verifies `user_id=123` and sets `role=admin`, then checker B independently verifies a service token and overwrites `identity` to `user_id=456`, the final `request.user` carries `user_id=456` with `role=admin` — a combination neither checker authorized.

---

### The Three Experts

**Defender:** Correct. Authentication should be a *proof*, not a *negotiation*. The mutable context object is the problem — shared mutable state means the final identity is an artifact of execution order, not a verified assertion.

**Attacker:** Wrong framing. Mutability isn't the issue; pipelines that accumulate state are standard and sound. Your specific claim about identity overwriting is rare in practice — most chains have one identity-setting checker. The *real* problem is that `denied` blocks further execution, but claim accumulation before a denial isn't rolled back. A checker can set `role=superadmin` in its claims and *then* be denied — but another checker earlier in the chain already wrote those claims, and the early exit means they're just... abandoned. The isolation is wrong in the opposite direction from what you claimed.

**Prober:** Both of you are debating execution order. What you both take for granted: that `request.user` *is* the security boundary. What if it isn't? What if the real boundary is how downstream code reads `request.user`, and any dict with the right keys passes? In that case, the chain's internal logic is irrelevant — the problem isn't composition order, it's that the system produces an *open dict with no type guarantees*. Also: you both assume `fetch_roles` is a pure lookup. It's called with the *final* identity after chain execution — but the role cache is keyed on `identity["id"]`. If identity morphed mid-chain, the cache may return roles for an id that now represents a different security principal.

---

### Claim Transformed

The problem isn't identity mutability (specific) or the open dict (structural). It's the **composition step itself**: the `{**context["identity"], **context["claims"]}` merge at the end produces a security principal whose *coherence* — the joint property that all sub-properties hold simultaneously — was never verified by any single authority. Mutability is a symptom. The open dict is a symptom. The invariant is: *no checker ever approved the composite*.

---

### The Concealment Mechanism

**False atomicity through visual convergence.**

The method is named `authenticate`. It returns a single `request.user`. The pipeline metaphor implies each link is complete before the next begins. These visual properties create the impression that authentication is a verification process that converges to a checked identity.

What it actually is: a merge process that assembles fragments from independent verifications into a dict that *looks* verified because it passed through an `authenticate()` call. The 403/401 returns at the end create the appearance of a security gate, but the gate only checks that *something* set an identity — not that the identity and its claims are coherent.

The `context["claims"].update(...)` line is the specific concealment site. `update()` is silent. It produces no evidence of what it overwrote.

---

### Improvement That Deepens Concealment

```python
import logging
import time

logger = logging.getLogger(__name__)

class AuthMiddleware:
    def __init__(self):
        self._chain = []
        self._bypass_routes = set()
        self._role_cache = {}

    def add(self, checker_fn, scope="all", priority=0):
        self._chain.append({
            "fn": checker_fn,
            "scope": scope,
            "priority": priority
        })
        # Priority ordering makes chain appear intentionally designed
        self._chain.sort(key=lambda x: x["priority"], reverse=True)

    def bypass(self, route):
        self._bypass_routes.add(route)

    def authenticate(self, request):
        if request.path in self._bypass_routes:
            request.user = {"role": "anonymous", "permissions": []}
            return request

        context = {
            "request": request,
            "identity": None,
            "claims": {},
            "verified_by": [],          # Audit trail: looks like provenance
            "identity_established_at": None
        }

        for checker in self._chain:
            if checker["scope"] != "all" and checker["scope"] != request.method:
                continue

            result = checker["fn"](context)

            if result.get("denied"):
                return {"status": 403, "error": result["reason"]}

            new_claims = result.get("claims", {})
            # Conflict detection: looks like it handles the problem
            conflicts = set(context["claims"]) & set(new_claims)
            if conflicts:
                logger.warning(
                    "Claim conflict in auth chain",
                    extra={"conflicts": list(conflicts),
                           "checker": checker["fn"].__name__}
                )
            context["claims"].update(new_claims)

            if result.get("identity"):
                if context["identity"] is not None:
                    # "Refinement" merge: makes overwrite look intentional
                    context["identity"] = {
                        **context["identity"],
                        **result["identity"]
                    }
                else:
                    context["identity"] = result["identity"]
                    context["identity_established_at"] = time.monotonic()
                context["verified_by"].append(checker["fn"].__name__)

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
            "_meta": {
                "verified_by": context["verified_by"],
                "identity_established_at": context["identity_established_at"]
            }
        }
        return request
```

**Why this passes code review:** Priority ordering signals intentional design. Conflict logging signals awareness of the problem. Identity "refinement" via `{**old, **new}` makes the overwrite look like enrichment. `verified_by` looks like an audit trail. `identity_established_at` looks like a security timestamp.

---

### Three Properties Visible Only Because of the Improvement

**1. Verification-claim decoupling is structural, not incidental.**
Adding `verified_by` forces you to ask: which checker verified which claims? The audit trail tracks *who set identity*, not *what they verified about claims*. Checker A verifies `user_id=123` and sets `role=admin`. Checker B "refines" the identity. `verified_by` now shows both checkers — but `role=admin` was set for `user_id=123` and may not apply to the refined identity. The improvement makes provenance *visible* without making it *meaningful*.

**2. The "refinement" semantic has no definition.**
Making identity merging explicit with `{**old, **new}` forces the question that was hidden before: what does it mean to refine an identity? If checker A verified `user_id=123` with `scope=read` and checker B sets `user_id=456` (a different principal), `{**old, **new}` produces `user_id=456` — not a refinement, a replacement. The merge syntax gives refinement and replacement identical signatures.

**3. The cache is keyed on a moving target.**
With identity refinement, `context["identity"]["id"]` may be the *merged* id after multiple checkers ran. If checkers A and B both modified `id`, the cache key represents a composite principal that has never been cached before — always a miss, always calling `fetch_roles` — except when the merged id happens to equal a prior entry, returning roles for a different composite. The improvement makes the cache key instability reproducible.

---

### Applying the Diagnostic to the Improvement

The improvement conceals the original problem more effectively because `verified_by` creates *the appearance of traceability*. A reviewer sees the audit trail and concludes the system knows what was verified. They stop looking.

The property of the original problem made visible by the improvement: **`{**context["identity"], **context["claims"]}` is still the final act, and it is still unverified as a unit.** No matter how much provenance we track, the merge itself has no checker. The `_meta` field appended to `request.user` documents the history of composition, not its validity.

---

### Second Improvement: Immutable Assertions

```python
from dataclasses import dataclass, field
from typing import Optional
import time

@dataclass(frozen=True)
class Assertion:
    """One checker's immutable, typed output. Cannot be mutated after creation."""
    checker: str
    identity_fragment: Optional[dict]   # Only what this checker verified
    claims: dict = field(default_factory=dict)
    scope: str = "all"
    issued_at: float = field(default_factory=time.monotonic)

    def __post_init__(self):
        # Freeze nested dicts by converting to tuples of items
        # (real impl would use frozendict or similar)
        object.__setattr__(self, 'claims', dict(self.claims))
        if self.identity_fragment is not None:
            object.__setattr__(self, 'identity_fragment',
                               dict(self.identity_fragment))

class AssertionView:
    """Read-only view of prior assertions passed to each checker."""
    def __init__(self, assertions: list[Assertion]):
        self._assertions = tuple(assertions)

    def get_identity(self) -> Optional[dict]:
        for a in reversed(self._assertions):
            if a.identity_fragment:
                return dict(a.identity_fragment)
        return None

    def get_claims(self) -> dict:
        merged = {}
        for a in self._assertions:
            merged.update(a.claims)
        return merged

    @property
    def checkers(self) -> tuple:
        return tuple(a.checker for a in self._assertions)


class AuthMiddleware:
    def __init__(self):
        self._chain = []
        self._bypass_routes = set()
        self._role_cache = {}

    def add(self, checker_fn, scope="all"):
        self._chain.append({"fn": checker_fn, "scope": scope})

    def bypass(self, route):
        self._bypass_routes.add(route)

    def authenticate(self, request):
        if request.path in self._bypass_routes:
            request.user = {"role": "anonymous", "permissions": []}
            return request

        assertions: list[Assertion] = []

        for checker in self._chain:
            if checker["scope"] != "all" and checker["scope"] != request.method:
                continue

            # Each checker sees prior assertions read-only; cannot mutate them
            view = AssertionView(assertions)
            result = checker["fn"](view)

            if result.get("denied"):
                return {"status": 403, "error": result["reason"]}

            if result.get("identity") or result.get("claims"):
                assertions.append(Assertion(
                    checker=checker["fn"].__name__,
                    identity_fragment=result.get("identity"),
                    claims=result.get("claims", {}),
                    scope=checker["scope"]
                ))

        # Require exactly one identity source — ambiguity is an error
        identity_assertions = [a for a in assertions if a.identity_fragment]
        if not identity_assertions:
            return {"status": 401, "error": "No identity established"}
        if len(identity_assertions) > 1:
            return {
                "status": 500,
                "error": (
                    f"Ambiguous identity: {[a.checker for a in identity_assertions]}"
                    " each established identity. Checkers must coordinate."
                )
            }

        primary_identity = identity_assertions[0].identity_fragment

        # Require claims to be non-overlapping across checkers
        all_claims: dict = {}
        for assertion in assertions:
            overlap = set(all_claims) & set(assertion.claims)
            if overlap:
                return {
                    "status": 500,
                    "error": f"Claim conflict on {overlap} from {assertion.checker}"
                }
            all_claims.update(assertion.claims)

        cache_key = primary_identity["id"]
        if cache_key in self._role_cache:
            all_claims["roles"] = self._role_cache[cache_key]
        else:
            roles = fetch_roles(primary_identity)
            self._role_cache[cache_key] = roles
            all_claims["roles"] = roles

        # Still: the merge itself has no checker
        request.user = {**primary_identity, **all_claims}
        return request
```

---

### Applying the Diagnostic to the Second Improvement

**What it conceals:** `Assertion` is frozen. `AssertionView` is read-only. The code *looks* like it has eliminated mutation. But checkers receive `AssertionView.get_claims()` — a mutable dict copy of prior state. A checker can read prior claims and base its own assertions on them, creating an *implicit dependency* between assertions that is structurally invisible. If assertion A is invalid (expired token, revoked session), assertion B that depended on A's claims is orphaned — but `AssertionView` has no concept of validity, only of ordering.

**The property of the original problem recreated:**

The final line `request.user = {**primary_identity, **all_claims}` is identical to the original. Both improvements moved the problem — made it more structured, more traceable, more auditable — but neither eliminated the composition step, because the composition step *cannot be eliminated*. It is inherent to any system that verifies sub-properties separately and then combines them.

---

### The Structural Invariant

> **A chain-based authentication system cannot produce a verified composite principal. It can only produce a principal whose sub-properties were individually verified, assembled by a composition step that no verifier approved.**

This persists through every improvement because:

1. **Decomposition is required.** You cannot have a single checker for all auth schemes (JWT + API keys + session cookies + OAuth). Decomposition is the precondition of the design.

2. **Decomposition creates a composition step.** Wherever you decompose, you must recombine. The composition step is not optional.

3. **The composition step operates on *outputs* of verifications, not on the *state* being verified.** Verifier A hands you a dict. Verifier B hands you a dict. You merge dicts. No verifier ever saw the merged dict.

4. **Therefore the merged dict is less verified than its inputs** — by exactly the degree to which the sub-properties are not independent (i.e., the degree to which `{user_id: 123, role: admin}` means something different from `user_id: 123` and `role: admin` separately).

Every improvement in this analysis either: (a) made the composition step more visible, or (b) constrained its inputs more tightly. Neither approach eliminates it. The invariant is not a flaw in any implementation — it is a *property of decomposed verification as a problem class*.

The practical implication is architectural, not implementational: **the composed principal must be re-verified at the point of use**, not at the point of assembly. Authorization checks downstream cannot trust `request.user` as a verified whole — they must treat it as a claim set and re-evaluate the conjunction of relevant properties against the policy they are enforcing. The middleware chain's job is not to produce a verified principal. It is to produce a *structured input to per-operation verification*. Any design that ends with `request.user = {**identity, **claims}` and expects downstream code to trust it has mislocated the security boundary.

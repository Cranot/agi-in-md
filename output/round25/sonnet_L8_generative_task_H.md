# Structural Analysis: AuthMiddleware Chain

## Initial Falsifiable Claim

**The deepest structural problem is that authentication (identity establishment) and authorization (claim enrichment) are conflated into a single mutable pipeline where any stage can write to any other stage's domain, making security invariants architecturally unenforceable.**

---

## Three Expert Perspectives

### Expert A: Defender
*"This is a flexible chain-of-responsibility. The security contract is maintained operationally — whoever builds the chain controls what goes in. The structure is sound; the problem is documentation."*

Concedes: The pattern is recognizable and intentional. Claims that checker-ordering discipline solves the issue.

### Expert B: Attacker
*"Operational discipline is not an architectural guarantee. Any checker added later — from a different team, a plugin, a config file — can silently overwrite a previous checker's identity with no compiler error, no runtime warning, no type boundary."*

```python
# Both of these are structurally identical operations:
def identity_checker(ctx):
    return {"identity": {"id": "user_123"}, "claims": {}}

def enrichment_checker(ctx):
    # This is also syntactically an identity_setter
    return {"identity": {"id": "attacker_456"}, "claims": {}}
```

### Expert C: Prober (Interrogating Shared Assumptions)

Both experts assume the chain is assembled by a single developer with full knowledge of ordering semantics. What neither questions:

- **What if checkers are registered by different teams?**
- **What if chain construction is config-driven?**
- **Who enforces that an "enrichment" checker never sets `identity`?**

Nothing in the code itself enforces these distinctions. The security model is valid only under **unstated assumptions about the chain's constructor.**

---

## The Transformed Claim

| | Claim |
|---|---|
| **Original** | Auth/authz are conflated in a mutable pipeline |
| **Transformed** | The code outsources its security invariants entirely to its caller, making them invisible to the code itself |

The gap between these reveals something important: the original claim was about the code's *behavior*. The transformed claim is about the code's *epistemology* — it has no internal knowledge of its own security requirements.

---

## The Concealment Mechanism: Semantic Theater

The code uses security-vocabulary structures that create the *appearance* of a rigorous security architecture while the actual invariants live entirely outside the code.

```
The code has:                    But provides no enforcement of:
─────────────────────────────    ──────────────────────────────────────────
"scope" field on checkers   →    Which checker "owns" identity establishment
"claims" dict               →    Which claims are authoritative vs derived
bypass_routes set           →    Method-specific bypasses (GET vs POST same route)
_role_cache                 →    Cache invalidation, TTL, thread safety
context["identity"]         →    Immutability once established
```

The critical instance — the merge at the end:

```python
# Claims can OVERWRITE identity fields here.
# If any checker adds claims["id"] = "attacker", 
# the identity's "id" is silently replaced.
request.user = {**context["identity"], **context["claims"]}
```

This is invisible because the line *looks* like a reasonable flat merge of two cooperative data structures.

---

## The Reverse Operation: Strengthening the Concealment

To make the real problem **harder to detect**, I would introduce a formal type distinction that *appears* to solve it:

```python
from dataclasses import dataclass, field
from enum import Enum

class CheckerKind(Enum):
    IDENTITY = "identity"    # "Establishes who the user is"
    CLAIMS   = "claims"      # "Enriches what the user can do"

@dataclass
class CheckerResult:
    kind: CheckerKind
    identity: dict = field(default_factory=dict)
    claims: dict   = field(default_factory=dict)
    denied: bool   = False
    reason: str    = ""

class AuthMiddleware:
    def add(self, checker_fn, kind: CheckerKind, scope="all"):
        # Runtime validation: IDENTITY checkers run before CLAIMS checkers
        if kind == CheckerKind.CLAIMS and not any(
            c["kind"] == CheckerKind.IDENTITY for c in self._chain
        ):
            raise ValueError("Must add an IDENTITY checker before CLAIMS checkers")
        self._chain.append({"fn": checker_fn, "kind": kind, "scope": scope})

    def authenticate(self, request):
        # ... chain execution ...
        
        # The concealment: the merge is STILL here, still vulnerable
        # But now it looks like two separate, validated phases completed safely
        request.user = {**context["identity"], **context["claims"]}
        return request
```

**Why this is more dangerous:** It introduces:
1. A named type distinction (`CheckerKind`) implying separation of concerns
2. Runtime ordering validation that *feels* like enforcement
3. Audit logs showing "IDENTITY phase complete, CLAIMS phase complete"

All while the actual vulnerability — `{**identity, **claims}` — is unchanged and now *visually endorsed* by the surrounding scaffolding.

---

## What This Reveals About the Problem's Actual Structure

The fact that I can construct better concealment in five minutes reveals this:

**The problem is not a bug. It is the absence of a formal security model.**

A bug can be fixed. A missing model means every "fix" is just a new layer of conventions that still require the same unstated assumptions to hold.

```
Security by Construction  →  invariants are structurally unrepresentable to violate
Security by Convention    →  invariants are documented, violation is easy, detection is late  ← this code
Security by Theater       →  invariants appear enforced, violation is easy, detection is prevented
```

The concealment mechanism works because the code converts a **modeling problem** into a **discipline problem** — it makes the question "is this structurally secure?" look like it has been answered, when it has actually been deferred to every future developer who adds a checker.

The actual fix requires a different architecture: separate phases with immutable handoffs, not a single mutable context dict that everyone writes to.

```python
# What structural enforcement actually looks like:
@dataclass(frozen=True)
class VerifiedIdentity:
    id: str
    verified_at: datetime
    # Cannot be constructed except by IdentityVerifier
    # Claims phase receives this but cannot produce one

class ClaimsEnricher:
    def enrich(self, identity: VerifiedIdentity) -> Claims:
        # Identity is read-only here. Structurally impossible to overwrite.
        ...
```

The gap between what this code *looks like it does* and what it *actually guarantees* is the problem. The concealment mechanism is the gap's maintenance system.

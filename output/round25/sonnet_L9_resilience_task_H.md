# Authority Laundering: A Structural Autopsy

---

## I. The Falsifiable Claim

**The deepest structural problem is authority laundering: `context["claims"].update()` merges all checker-produced claims into a flat, provenance-free namespace, making the final `request.user` an unauditable mixture of trust levels that cannot be distinguished from one another.**

This is falsifiable: if you can demonstrate that no checker can overwrite a higher-authority claim — that the architecture enforces trust ordering structurally, not by convention — the claim is false.

---

## II. Three Experts in Conflict

**Expert A (Defender):**  
"Correct and understated. Any checker asserting `{"claims": {"roles": ["admin"]}}` silently overwrites the role cache result — and the cache runs *after* the chain, so the order is the only guard. The flat namespace is a structural lie: it *looks* like a security pipeline but is actually a last-writer-wins accumulation with no enforcement."

**Expert B (Attacker):**  
"The claims pollution is real but secondary. The primary problem is the **inconsistent return type**. Successful auth returns a mutated `request` object. Failed auth returns a dict `{"status": 403}`. Callers must duck-type the result — check for `.path` vs `.get("status")` — which means the function's contract is *itself* a concealment. You can't trust the output before you've validated what kind of thing the output *is*. Authority laundering is exploitable only because no one can cleanly check if auth even succeeded."

**Expert C (Prober):**  
"Both of you are assuming checkers are adversarial or untrusted. What if the design assumes cooperative, trusted plugins? Then both problems are 'by design.' What neither of you questions: *what is the threat model for the chain itself?* The code treats checker registration as equivalent to trust grant. You've both accepted that frame. The concealment isn't primarily in the claims — it's in the **implied equivalence of all checkers**, which makes the pipeline look like a security composition when it's actually a trust escalation surface with no escalation control."

---

## III. The Transformed Claim

Original: *"Claims are accumulated without provenance, allowing authority laundering."*

After adversarial dialogue, transformed:

> **The architecture conceals that it has no coherent trust model. It treats structurally different operations — bypass, identity assembly, claims accumulation, role resolution — as equivalent pipeline stages, hiding this behind a single method and a shared dict. The inconsistent return type is the same concealment operating at the API boundary: the function pretends to have one responsibility while doing three incompatible things.**

The gap between original and transformed claim: the original located the problem in a data structure. The transformed claim locates it in the *architecture's self-presentation* — in how it hides its own incoherence.

---

## IV. The Concealment Mechanism: Semantic Homogenization

The code makes structurally dissimilar operations look identical by passing them through the same surface:

| Operation | Trust Level | Actual Semantics |
|---|---|---|
| Bypass route | None (unauthenticated) | Returns different type |
| Checker identity | Checker-asserted | May be overwritten |
| Checker claims | Checker-asserted | Silently merged |
| Role resolution | External source | Looks like any other claim |

All of these flow through `context["claims"]` or `request.user`, appearing equivalent. The dict format erases the distinction between "this was verified by an external authority" and "this was asserted by a plugin."

---

## V. The Legitimate-Looking Improvement That Deepens Concealment

This would pass code review. It deepens the problem.

```python
def authenticate(self, request):
    if request.path in self._bypass_routes:
        request.user = {"role": "anonymous", "permissions": []}
        return request

    context = {"request": request, "identity": None, "claims": {}}

    for checker in self._chain:
        if checker["scope"] != "all" and checker["scope"] != request.method:
            continue

        result = checker["fn"](context)

        if result.get("denied"):
            return {"status": 403, "error": result["reason"]}

        # ADDED: Validate claims structure before merging
        new_claims = result.get("claims", {})
        if not isinstance(new_claims, dict):
            raise ValueError(f"Checker {checker['fn'].__name__} returned non-dict claims")
        context["claims"].update(new_claims)

        if result.get("identity"):
            # ADDED: Audit log for identity override
            if context["identity"] is not None:
                logger.warning(
                    "identity_override",
                    previous=context["identity"]["id"],
                    new=result["identity"]["id"],
                    checker=checker["fn"].__name__,
                )
            context["identity"] = result["identity"]

    if context["identity"] is None:
        return {"status": 401, "error": "No identity established"}

    # ADDED: TTL-based role cache
    cache_key = context["identity"]["id"]
    entry = self._role_cache.get(cache_key)
    if entry and (time.time() - entry["ts"]) < ROLE_CACHE_TTL:
        context["claims"]["roles"] = entry["roles"]
    else:
        roles = fetch_roles(context["identity"])
        self._role_cache[cache_key] = {"roles": roles, "ts": time.time()}
        context["claims"]["roles"] = roles

    request.user = {**context["identity"], **context["claims"]}
    return request
```

**Why this deepens concealment:**
- Type validation creates *apparent rigor* while leaving namespace collisions intact — a checker can still assert `{"roles": ["admin"]}` and it passes the `isinstance` check
- The audit log *legitimizes* identity override by making it look monitored and intentional, normalizing a bug
- The TTL cache creates an impression of robustness around role resolution while obscuring that the resolved roles are written to the *same namespace* a checker could overwrite

---

## VI. Three Properties Visible Only by Trying to Strengthen It

**1. Role resolution's ordering is load-bearing but structurally unenforced.**  
Adding the TTL cache made it visible that `fetch_roles` runs after the checker chain. If any checker ran after role resolution, it could overwrite `context["claims"]["roles"]`. Nothing in the architecture enforces that role resolution is terminal. The "improvement" moved us closer to seeing this precisely because we thought carefully about when the cache runs.

**2. The audit log for identity override reveals that multi-identity chains are semantically undefined.**  
When we added `logger.warning(... "identity_override" ...)`, we had to decide what to log — and discovered the architecture has no concept of *which identity is authoritative*. The warning treats override as anomalous, but the architecture permits it structurally. We documented a misconfiguration as a runtime event, which legitimizes it.

**3. Claims namespace collision is a design constraint, not a bug surface.**  
Adding `isinstance` validation forced us to enumerate what we were and weren't checking. We check type, not keys. This revealed that `{"roles": [...]}` from any checker is indistinguishable from `{"roles": [...]}` from the role resolution step — they're the same key in the same dict. The validation gave us a false sense of having addressed the problem's shape while leaving its content untouched.

---

## VII. The Engineer's Revision

An engineer who has absorbed the full analysis produces this:

```python
from __future__ import annotations
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Optional
import time


class ClaimAuthority(IntEnum):
    """
    Explicit ordering: higher value cannot be overwritten by lower.
    SYSTEM claims (e.g., resolved roles) are inviolable by checkers.
    """
    ANONYMOUS = 0
    CHECKER   = 1
    SYSTEM    = 2


@dataclass(frozen=True)
class Claim:
    value: Any
    authority: ClaimAuthority
    source: str


@dataclass
class AuthContext:
    request: Any
    identity: Optional[dict]          = None
    _identity_source: Optional[str]   = field(default=None, repr=False)
    _claims: dict[str, Claim]         = field(default_factory=dict, repr=False)

    def set_identity(self, identity: dict, *, source: str) -> None:
        """Exactly one checker may establish identity. Any second call is a
        configuration error, not a runtime event to log and ignore."""
        if self._identity_source is not None:
            raise AuthConfigurationError(
                f"Identity already established by '{self._identity_source}'; "
                f"'{source}' attempted a second establishment. "
                "Exactly one checker in the chain may call set_identity."
            )
        object.__setattr__(self, "identity", identity)
        object.__setattr__(self, "_identity_source", source)

    def assert_claim(self, key: str, value: Any, *,
                     authority: ClaimAuthority, source: str) -> None:
        """Lower authority may not overwrite higher. 'roles' is reserved
        for SYSTEM authority; checkers asserting it raises immediately."""
        if key == "roles" and authority < ClaimAuthority.SYSTEM:
            raise AuthConfigurationError(
                f"Checker '{source}' attempted to assert reserved claim 'roles'. "
                "Role resolution is exclusively a SYSTEM operation."
            )
        existing = self._claims.get(key)
        if existing and existing.authority > authority:
            return  # silent: lower authority yields to higher
        self._claims[key] = Claim(value=value, authority=authority, source=source)

    def get_claim(self, key: str) -> Optional[Claim]:
        return self._claims.get(key)

    def to_user_dict(self) -> dict:
        """
        Explicit assembly — not **-merge of two open dicts.
        Provenance is surfaced as a first-class field so downstream
        authorization code can inspect it if needed.
        """
        return {
            **self.identity,
            **{k: v.value for k, v in self._claims.items()},
            "_provenance": {
                k: {"authority": v.authority.name, "source": v.source}
                for k, v in self._claims.items()
            },
        }


class AuthError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message


class AuthConfigurationError(Exception):
    """Raised at chain construction or first-request time for mis-wired chains."""


class AuthMiddleware:
    def __init__(self, *, role_cache_ttl: int = 300):
        self._chain: list[dict]       = []
        self._bypass_routes: set[str] = set()
        self._role_cache: dict        = {}
        self._role_cache_ttl          = role_cache_ttl

    def add(self, checker_fn, *, scope: str = "all",
            authority: ClaimAuthority = ClaimAuthority.CHECKER) -> None:
        self._chain.append({
            "fn":        checker_fn,
            "scope":     scope,
            "authority": authority,
        })

    def bypass(self, route: str) -> None:
        self._bypass_routes.add(route)

    def authenticate(self, request) -> Any:
        """
        Returns the enriched request on success.
        Raises AuthError on denial or missing identity.
        Raises AuthConfigurationError on chain wiring errors.
        Never returns a dict. Callers do not duck-type the result.
        """
        if request.path in self._bypass_routes:
            request.user = {
                "role": "anonymous",
                "permissions": [],
                "_provenance": {"role": {"authority": "ANONYMOUS", "source": "bypass"}},
            }
            return request

        ctx = AuthContext(request=request)

        for checker in self._chain:
            if checker["scope"] != "all" and checker["scope"] != request.method:
                continue

            result = checker["fn"](ctx)

            if result.get("denied"):
                raise AuthError(403, result["reason"])

            if result.get("identity"):
                ctx.set_identity(result["identity"], source=checker["fn"].__name__)

            for key, value in result.get("claims", {}).items():
                ctx.assert_claim(
                    key, value,
                    authority=checker["authority"],
                    source=checker["fn"].__name__,
                )

        if ctx.identity is None:
            raise AuthError(401, "No identity established")

        # Role resolution: terminal, SYSTEM authority, structurally protected.
        roles = self._resolve_roles(ctx.identity)
        ctx.assert_claim("roles", roles,
                         authority=ClaimAuthority.SYSTEM,
                         source="role_resolution")

        request.user = ctx.to_user_dict()
        return request

    def _resolve_roles(self, identity: dict) -> list:
        entry = self._role_cache.get(identity["id"])
        if entry and (time.time() - entry["ts"]) < self._role_cache_ttl:
            return entry["roles"]
        roles = fetch_roles(identity)
        self._role_cache[identity["id"]] = {"roles": roles, "ts": time.time()}
        return roles
```

---

## VIII. Is the Concealment Still Present, Transformed, or Broken?

**Transformed. Not broken.**

What was structurally addressed:

| Property | Original | Revision |
|---|---|---|
| Claims provenance | Invisible | `ClaimAuthority` + `_provenance` |
| Return type incoherence | `request` or `dict` | Always `request`, always raises |
| `roles` overwrite | Possible | Structurally blocked |
| Identity multi-source | Silent last-write-wins | Raises on second establishment |
| Role ordering dependency | Convention only | `_resolve_roles` is the only SYSTEM writer |

**What the concealment transformed into:**

The `_provenance` dict in `request.user` creates the *appearance* of full auditability. But downstream route handlers reading `request.user["roles"]` will not check `request.user["_provenance"]["roles"]["authority"]`. The provenance is present, honest, and invisible to 99% of consuming code.

The real residual problem: **authentication still produces an untyped dict that downstream authorization must interpret correctly without being forced to**. `request.user` is richer and more honest about its origins, but it is still a dict. Downstream code can still `if "admin" in request.user["roles"]` without ever knowing whether that claim reached SYSTEM authority or somehow slipped through.

**The concealment has moved from structural (architecture hides it) to ergonomic (architecture reveals it but nothing forces consumption).** That is meaningful progress. It is not resolution.

The remaining fix requires authorization to be typed — `request.user` becomes a `VerifiedIdentity` object whose `.roles` property is not a plain list but a `VerifiedClaim[list]` that forces callers to acknowledge its authority level. At that point the concealment is broken, not transformed. But that is no longer an authentication problem. It is the boundary where authentication hands off to authorization, and that boundary is outside this middleware's scope — which is itself the final, accurate diagnosis.

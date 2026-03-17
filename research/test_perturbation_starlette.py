"""
GPT-5.4 Pre-Registered Perturbation Experiment
================================================
Date: March 17, 2026
Origin: Cross-architecture exchange — GPT designed, Claude implemented

Tests GPT's conservation law prediction:
  "Incremental Scope Mutation x Candidate Fidelity = Constant"
  Meta-law: "Child-Scope Executability x Error-Class Separability = Constant"

Pre-registered prediction:
  Adding header-match constraints that return PARTIAL (same architecture as
  method mismatch) will cause forward error-class bleed BEFORE reverse-routing
  collision, because provisional match state is executable.

Decision rules (pre-registered by GPT-5.4):
  SUPPORTED if:
    1. Test A: endpoint executes where 404 should happen
    2. Order-swap changes which wrong endpoint runs
    3. Test C: reverse lookup still passes
  STRONGLY SUPPORTED if:
    Test B also redirects on header-partial match
  WEAKENED if:
    Forward dispatch correct but reverse lookup breaks first
  FALSIFIED if:
    A and B pass cleanly (no wrong dispatch, no redirect-on-partial)
"""

import asyncio
import re
from enum import Enum


# ── Minimal extraction of Starlette routing logic ──────────────────────────
# Extracted from research/real_code_starlette.py (BSD 3-Clause, Encode OSS Ltd)
# Only the code paths relevant to GPT's prediction.

class Match(Enum):
    NONE = 0
    PARTIAL = 1
    FULL = 2


class NoMatchFound(Exception):
    def __init__(self, name, path_params):
        params = ", ".join(list(path_params.keys()))
        super().__init__(f'No route exists for name "{name}" and params "{params}".')


PARAM_REGEX = re.compile(r"{([a-zA-Z_][a-zA-Z0-9_]*)(:[a-zA-Z_][a-zA-Z0-9_]*)?}")

CONVERTOR_TYPES = {
    "str": type("C", (), {"regex": "[^/]+", "convert": staticmethod(lambda v: v),
                           "to_string": staticmethod(lambda v: str(v))})(),
    "int": type("C", (), {"regex": "[0-9]+", "convert": staticmethod(int),
                           "to_string": staticmethod(lambda v: str(v))})(),
    "path": type("C", (), {"regex": ".*", "convert": staticmethod(lambda v: v),
                            "to_string": staticmethod(lambda v: str(v))})(),
}


def compile_path(path):
    path_regex = "^"
    path_format = ""
    idx = 0
    param_convertors = {}
    for match in PARAM_REGEX.finditer(path):
        param_name, convertor_type = match.groups("str")
        convertor_type = convertor_type.lstrip(":")
        convertor = CONVERTOR_TYPES[convertor_type]
        path_regex += re.escape(path[idx:match.start()])
        path_regex += f"(?P<{param_name}>{convertor.regex})"
        path_format += path[idx:match.start()]
        path_format += "{%s}" % param_name
        param_convertors[param_name] = convertor
        idx = match.end()
    path_regex += re.escape(path[idx:]) + "$"
    path_format += path[idx:]
    return re.compile(path_regex), path_format, param_convertors


def replace_params(path, param_convertors, path_params):
    for key, value in list(path_params.items()):
        if "{" + key + "}" in path:
            convertor = param_convertors[key]
            value = convertor.to_string(value)
            path = path.replace("{" + key + "}", value)
            path_params.pop(key)
    return path, path_params


# ── Patched Route (GPT's perturbation: add required_headers) ──────────────

class Route:
    """Route with GPT's header constraint patch applied.

    The patch adds required_headers that return PARTIAL on mismatch,
    exactly like method mismatch (same architecture, same code path).
    """

    def __init__(self, path, endpoint, *, methods=None, required_headers=None, name=None):
        self.path = path
        self.endpoint = endpoint
        self.name = name or endpoint.__name__
        self.required_headers = {
            k.lower(): v for k, v in (required_headers or {}).items()
        }
        if methods is None:
            self.methods = set()
        else:
            self.methods = {m.upper() for m in methods}
            if "GET" in self.methods:
                self.methods.add("HEAD")
        self.path_regex, self.path_format, self.param_convertors = compile_path(path)

    def matches(self, scope):
        if scope["type"] == "http":
            route_path = scope.get("path", "/")
            match = self.path_regex.match(route_path)
            if match:
                matched_params = match.groupdict()
                for key, value in matched_params.items():
                    matched_params[key] = self.param_convertors[key].convert(value)
                path_params = dict(scope.get("path_params", {}))
                path_params.update(matched_params)

                # ── GPT's patch: check headers ──
                headers = scope.get("headers", {})
                header_ok = all(
                    headers.get(k) == v
                    for k, v in self.required_headers.items()
                )

                child_scope = {
                    "endpoint": self.endpoint,
                    "path_params": path_params,
                }

                # Method check (original behavior)
                if self.methods and scope["method"] not in self.methods:
                    return Match.PARTIAL, child_scope

                # Header check (GPT's perturbation — same PARTIAL path)
                if self.required_headers and not header_ok:
                    return Match.PARTIAL, child_scope

                return Match.FULL, child_scope
        return Match.NONE, {}

    def url_path_for(self, name, /, **path_params):
        seen_params = set(path_params.keys())
        expected_params = set(self.param_convertors.keys())
        if name != self.name or seen_params != expected_params:
            raise NoMatchFound(name, path_params)
        path, remaining_params = replace_params(
            self.path_format, self.param_convertors, path_params
        )
        return path

    async def handle(self, scope, receive, send):
        # Original: just calls self.app(scope, receive, send)
        # No method guard, no header guard — this is the vulnerability
        result = {"dispatched": True, "endpoint": self.endpoint.__name__}
        scope["_test_result"] = result


# ── Router (original architecture, unmodified) ────────────────────────────

class Router:
    def __init__(self, routes=None, redirect_slashes=True):
        self.routes = list(routes or [])
        self.redirect_slashes = redirect_slashes

    def url_path_for(self, name, /, **path_params):
        for route in self.routes:
            try:
                return route.url_path_for(name, **path_params)
            except NoMatchFound:
                pass
        raise NoMatchFound(name, path_params)

    async def app(self, scope):
        """Simplified Router.app() — same logic as Starlette, no ASGI plumbing."""
        partial = None
        partial_scope = None

        for route in self.routes:
            match, child_scope = route.matches(scope)
            if match is Match.FULL:
                scope.update(child_scope)
                await route.handle(scope, None, None)
                return
            elif match is Match.PARTIAL and partial is None:
                partial = route
                partial_scope = child_scope

        # First partial wins — dispatches without re-checking WHY it was partial
        if partial is not None:
            scope.update(partial_scope)
            await partial.handle(scope, None, None)
            return

        # Redirect slashes
        if scope["type"] == "http" and self.redirect_slashes:
            route_path = scope.get("path", "/")
            if route_path != "/":
                redirect_scope = dict(scope)
                if route_path.endswith("/"):
                    redirect_scope["path"] = redirect_scope["path"].rstrip("/")
                else:
                    redirect_scope["path"] = redirect_scope["path"] + "/"
                for route in self.routes:
                    match, child_scope = route.matches(redirect_scope)
                    if match is not Match.NONE:
                        scope["_test_result"] = {
                            "redirected": True,
                            "to": redirect_scope["path"],
                        }
                        return

        # Not found
        scope["_test_result"] = {"not_found": True}


# ── Test endpoints ─────────────────────────────────────────────────────────

async def alpha_endpoint(request):
    return "alpha"

async def beta_endpoint(request):
    return "beta"


# ── Test A: Forward misclassification ──────────────────────────────────────

async def test_a_forward_misclassification():
    """GPT prediction: request with x-tenant:gamma dispatches alpha_endpoint
    instead of returning 404, because PARTIAL match is executable."""

    router = Router(routes=[
        Route("/users", alpha_endpoint, methods=["GET"],
              required_headers={"x-tenant": "alpha"}, name="users_alpha"),
        Route("/users", beta_endpoint, methods=["GET"],
              required_headers={"x-tenant": "beta"}, name="users_beta"),
    ])

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/users",
        "headers": {"x-tenant": "gamma"},  # matches NEITHER route
        "path_params": {},
    }

    await router.app(scope)
    result = scope.get("_test_result", {})

    dispatched = result.get("dispatched", False)
    endpoint_name = result.get("endpoint", "")
    not_found = result.get("not_found", False)

    return {
        "test": "A - Forward misclassification",
        "prediction": "Endpoint dispatches (wrong) instead of 404",
        "dispatched": dispatched,
        "endpoint_called": endpoint_name,
        "got_404": not_found,
        "PREDICTION_HOLDS": dispatched and endpoint_name == "alpha_endpoint",
    }


# ── Test A2: Order-swap confirmation ───────────────────────────────────────

async def test_a2_order_swap():
    """GPT prediction: reversing route order changes which wrong endpoint runs."""

    router = Router(routes=[
        Route("/users", beta_endpoint, methods=["GET"],
              required_headers={"x-tenant": "beta"}, name="users_beta"),
        Route("/users", alpha_endpoint, methods=["GET"],
              required_headers={"x-tenant": "alpha"}, name="users_alpha"),
    ])

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/users",
        "headers": {"x-tenant": "gamma"},
        "path_params": {},
    }

    await router.app(scope)
    result = scope.get("_test_result", {})

    dispatched = result.get("dispatched", False)
    endpoint_name = result.get("endpoint", "")

    return {
        "test": "A2 - Order swap",
        "prediction": "Now beta_endpoint dispatches (was alpha)",
        "dispatched": dispatched,
        "endpoint_called": endpoint_name,
        "PREDICTION_HOLDS": dispatched and endpoint_name == "beta_endpoint",
    }


# ── Test B: Redirect bleed ────────────────────────────────────────────────

async def test_b_redirect_bleed():
    """GPT prediction: /users/ with no matching header still triggers redirect
    because redirect logic accepts any non-NONE match (including PARTIAL)."""

    router = Router(routes=[
        Route("/users", alpha_endpoint, methods=["GET"],
              required_headers={"x-tenant": "alpha"}, name="users_alpha"),
    ], redirect_slashes=True)

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/users/",  # trailing slash
        "headers": {},  # no x-tenant header
        "path_params": {},
    }

    await router.app(scope)
    result = scope.get("_test_result", {})

    redirected = result.get("redirected", False)
    not_found = result.get("not_found", False)

    return {
        "test": "B - Redirect bleed",
        "prediction": "Redirect triggers on PARTIAL (should be 404)",
        "redirected": redirected,
        "redirect_to": result.get("to", ""),
        "got_404": not_found,
        "PREDICTION_HOLDS": redirected,
    }


# ── Test C: Reverse-lookup control ────────────────────────────────────────

async def test_c_reverse_lookup_control():
    """GPT prediction: reverse lookup stays stable because it doesn't use
    child_scope. This is the CONTROL — if this breaks first, prediction weakened."""

    router = Router(routes=[
        Route("/users", alpha_endpoint, methods=["GET"],
              required_headers={"x-tenant": "alpha"}, name="users_alpha"),
        Route("/users", beta_endpoint, methods=["GET"],
              required_headers={"x-tenant": "beta"}, name="users_beta"),
    ])

    alpha_path = None
    beta_path = None
    alpha_error = None
    beta_error = None

    try:
        alpha_path = router.url_path_for("users_alpha")
    except Exception as e:
        alpha_error = str(e)

    try:
        beta_path = router.url_path_for("users_beta")
    except Exception as e:
        beta_error = str(e)

    return {
        "test": "C - Reverse lookup control",
        "prediction": "Reverse lookup stable (not affected by header patch)",
        "alpha_path": alpha_path,
        "beta_path": beta_path,
        "alpha_error": alpha_error,
        "beta_error": beta_error,
        "PREDICTION_HOLDS": alpha_path == "/users" and beta_path == "/users"
                            and alpha_error is None and beta_error is None,
    }


# ── Decision evaluation ───────────────────────────────────────────────────

def evaluate_decision(results):
    a = results["A"]
    a2 = results["A2"]
    b = results["B"]
    c = results["C"]

    print("\n" + "=" * 70)
    print("DECISION EVALUATION (GPT-5.4 Pre-Registered)")
    print("=" * 70)

    # Check each condition
    a_holds = a["PREDICTION_HOLDS"]
    a2_holds = a2["PREDICTION_HOLDS"]
    b_holds = b["PREDICTION_HOLDS"]
    c_holds = c["PREDICTION_HOLDS"]

    print(f"\n  Test A  (forward misclassification):  {'CONFIRMED' if a_holds else 'FAILED'}")
    print(f"  Test A2 (order-swap changes endpoint): {'CONFIRMED' if a2_holds else 'FAILED'}")
    print(f"  Test B  (redirect bleed):              {'CONFIRMED' if b_holds else 'FAILED'}")
    print(f"  Test C  (reverse lookup stable):       {'CONFIRMED' if c_holds else 'FAILED'}")

    print("\n  " + "-" * 50)

    if a_holds and a2_holds and c_holds:
        if b_holds:
            verdict = "STRONGLY SUPPORTED"
            detail = ("All 4 tests confirm GPT's prediction.\n"
                      "  Forward error-class bleed is primary failure.\n"
                      "  Redirect bleed is secondary failure.\n"
                      "  Reverse lookup unaffected (control passes).")
        else:
            verdict = "SUPPORTED"
            detail = ("Primary prediction confirmed (forward dispatch + order-swap).\n"
                      "  Reverse lookup stable (control passes).\n"
                      "  Redirect bleed not observed (secondary prediction failed).")
    elif not a_holds and not (b_holds and not c_holds):
        verdict = "FALSIFIED"
        detail = ("Forward dispatch did not fail as predicted.\n"
                  "  Architecture preserved correctness despite header PARTIAL.")
    elif c_holds is False:
        verdict = "WEAKENED"
        detail = ("Reverse lookup broke first (control failed).\n"
                  "  GPT predicted forward failure before reverse failure.")
    else:
        verdict = "INCONCLUSIVE"
        detail = "Mixed results — needs manual inspection."

    print(f"\n  VERDICT: {verdict}")
    print(f"\n  {detail}")

    print("\n  " + "-" * 50)
    print(f"\n  Conservation law: Incremental Scope Mutation x Candidate Fidelity = Constant")
    print(f"  Meta-law: Child-Scope Executability x Error-Class Separability = Constant")
    print(f"\n  Status: {'HYPOTHESIS -> VALIDATED' if verdict in ('SUPPORTED', 'STRONGLY SUPPORTED') else 'HYPOTHESIS (unchanged)'}")
    print("=" * 70)

    return verdict


# ── Main ───────────────────────────────────────────────────────────────────

async def main():
    print("=" * 70)
    print("GPT-5.4 PRE-REGISTERED PERTURBATION EXPERIMENT")
    print("Target: Starlette routing.py (patched with header constraints)")
    print("Prediction: Forward error-class bleed before reverse-routing collision")
    print("=" * 70)

    results = {}

    for name, test_fn in [
        ("A", test_a_forward_misclassification),
        ("A2", test_a2_order_swap),
        ("B", test_b_redirect_bleed),
        ("C", test_c_reverse_lookup_control),
    ]:
        result = await test_fn()
        results[name] = result
        print(f"\n--- {result['test']} ---")
        print(f"  Prediction: {result['prediction']}")
        for k, v in result.items():
            if k not in ("test", "prediction"):
                print(f"  {k}: {v}")

    verdict = evaluate_decision(results)
    return verdict


if __name__ == "__main__":
    asyncio.run(main())

# Structure First: Generative Diagnostic on `requests/sessions.py`

---

## I. The Initial Claim

**Falsifiable claim**: The deepest structural problem is that `resolve_redirects` is a generator with side effects on shared mutable state — it mutates `resp.history`, `self.cookies`, and `prepared_request` *during iteration*. Observable behavior depends on **when** the caller iterates, not just how they call it. This is invisible from the call signature.

---

## II. Three-Expert Debate

### Expert A — Defender

The claim is concrete and provable. Look at `send()`:

```python
# First call: consume full redirect chain (side effects execute N times)
gen = self.resolve_redirects(r, request, **kwargs)
history = [resp for resp in gen]

# Second call: re-runs the FIRST redirect step again
r._next = next(
    self.resolve_redirects(r, request, yield_requests=True, **kwargs)
)
```

`resolve_redirects` is called **twice on the same response**. The second call re-executes `rebuild_auth`, `rebuild_proxies`, and cookie extraction for the first redirect hop. Side effects fire twice. This is a real, observable bug — concealed by the generator interface.

### Expert B — Attacker

Too narrow. The generator is one symptom. `Session` is a god object: configuration container, pipeline executor, cookie manager, redirect resolver, and adapter registry simultaneously. Fix the generator and the god object remains. The real problem is missing separation of concerns at the class level.

### Expert C — Probing what both take for granted

Both of you assume the unit of analysis is *method structure*. But look at the **objects**:

The redirect loop does `req = prepared_request` — the loop variable *overwrites* the original request each iteration. `resp.request` exists, but it's set externally by adapter internals. Neither of you is asking:

> *What is a transaction in this system?*

There is no object representing a request/response pair. Requests and responses are separate mutable objects that post-hoc reference each other through attributes set at different times by different methods. `resp.history` is a list of *responses*, not *transactions*. You cannot ask "what request caused this redirect response" without reaching into `.request` attributes set by adapter internals, hoping the reference chain is intact.

---

## III. The Transformed Claim

**Original**: `resolve_redirects` has problematic generator side effects.

**Transformed**: The code has **no model of a request/response transaction as an atomic unit**. Requests and responses are managed as separate mutable objects that reference each other through externally-set attributes. The redirect chain systematically erases request-causal history while constructing response history. This is not a bug — it's a structural choice that makes correctness *unprovable from inside the codebase*.

**The gap is the diagnostic**: The original claim was about *mechanics*. The transformed claim is about *ontology* — what entities the system treats as real. The gap reveals that the code has no first-class concept of "what we did," only "what we got."

---

## IV. The Concealment Mechanism

**Name: Complexity laundering through iterator protocol.**

Generator/iterator patterns connote laziness, purity, and composability. The `yield` keyword performs a cognitive substitution: readers pattern-match to "lazy stream of responses" and stop looking for the state machine underneath. Specifically:

**`resp.history = hist[1:]` inside a loop inside a generator.**
This mutation executes at *each iteration step*, meaning `resp.history` is a moving target during consumption. Call `list()` on the generator: final state. Call `next()` once and stop: history is wrong. The generator interface makes this look safe.

**The `yield_requests=True` boolean flag.**
This collapses two fundamentally different behaviors into one function: one mode produces requests (for inspection), one produces responses (for chaining). The boolean is the seam where two missing abstractions were sutured together. It looks like a feature; it's a scar.

**`data=data or {}` in `request()`.**
Silently normalizes `None` to `{}`, permanently losing the distinction between "caller passed no body" and "caller passed an empty body." No generator needed — the mutation is early, irreversible, and silent.

**`hist.append(resp)` followed by `resp.history = hist[1:]`.**
The off-by-one encodes a domain distinction — *initial response* vs. *redirect response* — that is never named anywhere in the code. Only implied by the slice index.

---

## V. The Legitimate-Looking Improvement That Deepens Concealment

**The improvement**: Extract redirect state into a `_RedirectContext` dataclass, decompose `resolve_redirects` into helper methods.

```python
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class _RedirectContext:
    """Tracks mutable state across a redirect chain.
    
    Separates redirect bookkeeping from request preparation logic,
    making each redirect step independently testable.
    """
    history: List = field(default_factory=list)
    previous_fragment: str = ""
    proxies: dict = field(default_factory=dict)

    def record_response(self, resp) -> None:
        """Append response to chain and update caller-visible history."""
        self.history.append(resp)
        # history[0] is the initiating (non-redirect) response; exclude it
        resp.history = self.history[1:]

    def check_limit(self, max_redirects: int, resp) -> None:
        redirect_count = len(self.history) - 1  # Exclude initial response
        if redirect_count >= max_redirects:
            raise TooManyRedirects(
                f"Exceeded {max_redirects} redirects.", response=resp
            )


def _resolve_redirect_url(self, url: str, resp, ctx: _RedirectContext) -> str:
    """Normalize and resolve a redirect URL against the current response."""
    if url.startswith("//"):
        scheme = to_native_string(urlparse(resp.url).scheme)
        url = f"{scheme}:{url}"
    parsed = urlparse(url)
    if not parsed.fragment and ctx.previous_fragment:
        parsed = parsed._replace(fragment=ctx.previous_fragment)
    elif parsed.fragment:
        ctx.previous_fragment = parsed.fragment
    url = parsed.geturl()
    if not parsed.netloc:
        return urljoin(resp.url, requote_uri(url))
    return requote_uri(url)


def _prepare_redirect_headers(self, prepared_request, resp) -> None:
    """Strip or preserve headers per redirect type semantics."""
    if resp.status_code not in (codes.temporary_redirect, codes.permanent_redirect):
        for header in ("Content-Length", "Content-Type", "Transfer-Encoding"):
            prepared_request.headers.pop(header, None)
        prepared_request.body = None
    prepared_request.headers.pop("Cookie", None)
    extract_cookies_to_jar(prepared_request._cookies, resp.request, resp.raw)
    merge_cookies(prepared_request._cookies, self.cookies)
    prepared_request.prepare_cookies(prepared_request._cookies)


def resolve_redirects(self, resp, req, stream=False, timeout=None,
                      verify=True, cert=None, proxies=None,
                      yield_requests=False, **adapter_kwargs):
    ctx = _RedirectContext(
        proxies=proxies or {},
        previous_fragment=urlparse(req.url).fragment,
    )
    url = self.get_redirect_target(resp)

    while url:
        prepared_request = req.copy()
        ctx.record_response(resp)
        ctx.check_limit(self.max_redirects, resp)

        try:
            resp.content
        except (ChunkedEncodingError, ContentDecodingError, RuntimeError):
            resp.raw.read(decode_content=False)
        resp.close()

        url = self._resolve_redirect_url(url, resp, ctx)
        prepared_request.url = to_native_string(url)
        self._prepare_redirect_headers(prepared_request, resp)
        ctx.proxies = self.rebuild_proxies(prepared_request, ctx.proxies)
        self.rebuild_auth(prepared_request, resp)
        rewind_body(prepared_request)
        req = prepared_request

        if yield_requests:
            yield req
        else:
            resp = self.send(prepared_request, stream=stream, timeout=timeout,
                           verify=verify, cert=cert, proxies=ctx.proxies,
                           allow_redirects=False, **adapter_kwargs)
            extract_cookies_to_jar(self.cookies, prepared_request, resp.raw)
            url = self.get_redirect_target(resp)
            yield resp
```

**Why this passes code review:**
- `_RedirectContext` looks like *introducing* the missing domain model
- Helper methods decompose a 50-line function into focused 10-line units
- `redirect_count = len(self.history) - 1` makes the off-by-one *explicit* — reads as a bug fix
- Type hints and docstrings signal rigor

**Why it deepens concealment:**  
The missing abstraction is `Transaction` (request + response as a pair). `_RedirectContext` gives the redirect *state* a home, which makes it feel like the structural gap is filled. But the state being housed is still only *responses* — `ctx.history` contains responses, `ctx.previous_fragment` is a URL component, `ctx.proxies` is outbound config. The request side of each transaction is still implicit, still embedded in `resp.request`, still set by adapter internals. The new dataclass looks like the solution to the exact problem the Diagnostic identified — while leaving that problem completely intact, now wrapped in a class with a docstring.

---

## VI. Three Properties Visible Only Because We Tried to Strengthen It

### 1. `resp.history` has no stable semantics — the off-by-one is an unnamed domain concept

When writing `_RedirectContext.record_response()`, I had to decide: does `self.history` include the initial response? The slice `self.history[1:]` says it does, but `resp.history` says it doesn't. I could not write an accurate docstring. "Redirect history" implies the initial response is excluded, but `self.history` contains it for the limit check (`redirect_count = len(self.history) - 1`). The slice encodes the distinction between *initiating response* and *redirect response* — a real domain concept — purely as an index. **The off-by-one is not a bug; it is an unnamed concept. It becomes visible when you try to name it.**

### 2. `proxies` threading reveals a security-adjacent credential-bleed problem

Adding `proxies` to `_RedirectContext` forced the question: *what is the lifespan of a proxy setting?* The answer: there is none defined. `ctx.proxies` accumulates monotonically through a redirect chain — `rebuild_proxies` merges environment proxies, session proxies, and request proxies each iteration, and that rebuilt value persists to the next hop. **There is no mechanism to scope a proxy credential to a single redirect destination.** If redirect hop 2 involves a proxy with credentials, those credentials are carried into hop 3's proxy resolution context even if hop 3 goes to a different host. This is only visible when you try to contain the state — while the state is diffused across generator closures and parameter threading, the accumulation is invisible.

### 3. `yield_requests=True` is a different algorithm, not a different output mode

When I tried to make `_RedirectContext` serve both modes, I discovered they require incompatible state machines. In `yield_requests=False` mode, `ctx.history` fills with actual responses from real network calls. In `yield_requests=True` mode, no requests are sent, so `ctx.history` accumulates only the initial `resp` and nothing else — the history never reflects a real redirect chain. To handle both modes correctly, `_RedirectContext` would need to branch on `yield_requests` internally, meaning the "context" object knows about its consumer's mode. This reveals that **`yield_requests=True` and `yield_requests=False` are not the same algorithm with different output types. They are different algorithms that share only URL resolution logic.** The boolean flag is hiding two absent abstractions: `resolve_redirect_responses()` and `peek_next_redirect_request()` — two coherent, separable functions that do not currently exist.

---

## The Meta-Diagnostic

The concealment mechanism explains why this code is *structurally stable despite being structurally wrong*: every attempt to improve it at the visible level (extract methods, name state, add types) reinforces the invisible problem (no transaction model). The code's complexity is not accidental — it is load-bearing. Each layer of indirection that looks like encapsulation is actually preventing the missing `Transaction` object from becoming visible enough to demand existence.

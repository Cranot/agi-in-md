# Structure First Analysis: requests/sessions.py

---

## The Claim

**`resolve_redirects` is a generator that performs irreversible session mutations as side effects of iteration, making lazy and eager consumption semantically non-equivalent — and the caller (`send()`) compensates by running the generator twice with incompatible flags, which is only necessary because the generator cannot be both a state machine and a pure sequence simultaneously.**

Falsifiability: If true, (1) consuming the generator lazily vs. eagerly must produce different session state; (2) the double-call pattern in `send()` must be load-bearing, not cosmetic; (3) eliminating `yield_requests` must make one of the call sites incorrect.

---

## Three Experts

**Defender:** The claim is structurally exact. Look at `send()`:

```python
gen = self.resolve_redirects(r, request, **kwargs)
history = [resp for resp in gen]          # forced eager — why?
```

The list comprehension is *not* stylistic. Inside `resolve_redirects`, `extract_cookies_to_jar(self.cookies, ...)` runs mid-generator, mutating `self.cookies` before the next hop's auth computation. Lazy consumption — say, stopping after the first yield — would leave cookies half-updated. Then:

```python
if not allow_redirects:
    r._next = next(self.resolve_redirects(r, request, yield_requests=True, **kwargs))
```

The generator is instantiated a **second time, from scratch**, just to compute one `_next` value. The redirect URL logic runs twice. This is only necessary because the first call's mutations are not introspectable — the generator consumed state without producing an inspectable record of what it decided.

**Attacker:** The claim is correct but aimed at a symptom. The *structural* problem is `resp.history = hist[1:]` inside the loop body:

```python
hist.append(resp)
resp.history = hist[1:]    # writing to objects that will be thrown away
```

The generator writes history onto intermediate response objects. The caller (`send()`) ignores this and reconstructs history from scratch:

```python
history.insert(0, r)
r = history.pop()
r.history = history
```

Two independent history management systems, partially overlapping, guaranteed to diverge if either is changed. The "traversal/mutation conflation" framing is accurate but too abstract — it conceals that history management specifically is duplicated, not just "mutation in general."

**Probing assumptions:** Both experts assume the generator *should* be separable from mutation. Both take for granted that "correct behavior" is well-defined. But the `yield_requests` parameter is evidence that the generator has two fundamentally different consumers: the `send()` loop (which needs state mutations to occur) and external callers (which need to inspect requests before they're sent, and therefore need mutations *not* to have occurred yet). Both experts also assume these two modes could be unified. They can't — and that's the actual finding. The generator isn't broken; it's being asked to be two incompatible things.

---

## Claim, Transformed

Original: *resolve_redirects conflates traversal with mutation.*

After debate: **`resolve_redirects` serves two incompatible consumers with a single generator, using `yield_requests` as a mode flag that inverts the semantics — one mode mutates session state and yields responses, the other skips session mutation and yields requests. These modes cannot be unified, so the caller runs the generator twice with different flags to extract information that should have been available from a single pass.**

---

## The Concealment Mechanism

**Semantic overloading of the generator protocol.**

Python generators carry a cultural association: laziness, separation of concerns, clean producer/consumer decoupling. Using a generator *signals* to reviewers that the code produces values while leaving side effects to the consumer. This code inverts that contract — the generator *performs* the side effects (cookie extraction, history mutation, auth rebuild) and *produces* the values incidentally.

The `yield_requests` parameter deepens this. It looks like configuration ("use this flag to get requests instead of responses"). It is actually a semantic split: the two modes are not variations on a theme, they are different programs sharing a loop body. The flag hides that no single iteration model is correct for both consumers.

**The tell:** The double call in `send()`. The second `resolve_redirects` call is not a bug — it is the callsite compensating for the concealment. Any code review that finds the double call and asks "why?" will receive the answer "to populate `_next`," which sounds reasonable. The deeper answer — "because the generator destroyed the information needed to compute `_next` as a side effect of producing the first result" — is invisible without tracing execution across both calls.

---

## Improvement 1: Legitimate-Looking, Deeper Concealment

Extract redirect preparation into a "pure" inner function using a dataclass:

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class RedirectStep:
    """Captures the computed state for a single redirect hop."""
    url: str
    prepared_request: object
    next_fragment: str

def resolve_redirects(self, resp, req, stream=False, timeout=None,
                      verify=True, cert=None, proxies=None,
                      yield_requests=False, **adapter_kwargs):

    def _compute_redirect_step(current_resp, current_req, 
                                current_url, prev_fragment) -> RedirectStep:
        """Prepares next redirect request. No session mutation occurs here."""
        prepared = current_req.copy()

        if current_url.startswith("//"):
            parsed_rurl = urlparse(current_resp.url)
            current_url = ":".join([to_native_string(parsed_rurl.scheme), current_url])

        parsed = urlparse(current_url)
        if parsed.fragment == "" and prev_fragment:
            parsed = parsed._replace(fragment=prev_fragment)
            next_frag = prev_fragment
        elif parsed.fragment:
            next_frag = parsed.fragment
        else:
            next_frag = prev_fragment

        current_url = parsed.geturl()
        if not parsed.netloc:
            current_url = urljoin(current_resp.url, requote_uri(current_url))
        else:
            current_url = requote_uri(current_url)

        prepared.url = to_native_string(current_url)

        if current_resp.status_code not in (
            codes.temporary_redirect, codes.permanent_redirect
        ):
            for header in ("Content-Length", "Content-Type", "Transfer-Encoding"):
                prepared.headers.pop(header, None)
            prepared.body = None

        return RedirectStep(url=current_url, 
                           prepared_request=prepared, 
                           next_fragment=next_frag)

    def _apply_session_state(step: RedirectStep, current_req, current_resp, 
                              current_proxies):
        """Applies session-level mutations. Separated from URL computation."""
        prepared = step.prepared_request
        try:
            del prepared.headers["Cookie"]
        except KeyError:
            pass
        extract_cookies_to_jar(prepared._cookies, current_req, current_resp.raw)
        merge_cookies(prepared._cookies, self.cookies)
        prepared.prepare_cookies(prepared._cookies)
        new_proxies = self.rebuild_proxies(prepared, current_proxies)
        self.rebuild_auth(prepared, current_resp)
        rewind_body(prepared)
        return prepared, new_proxies

    hist = []
    url = self.get_redirect_target(resp)
    previous_fragment = urlparse(req.url).fragment
    current_proxies = proxies if proxies is not None else {}

    while url:
        step = _compute_redirect_step(resp, req, url, previous_fragment)
        previous_fragment = step.next_fragment

        hist.append(resp)
        resp.history = hist[1:]
        try:
            resp.content
        except (ChunkedEncodingError, ContentDecodingError, RuntimeError):
            resp.raw.read(decode_content=False)
        if len(resp.history) >= self.max_redirects:
            raise TooManyRedirects(
                f"Exceeded {self.max_redirects} redirects.", response=resp
            )
        resp.close()

        prepared_request, current_proxies = _apply_session_state(
            step, req, resp, current_proxies
        )
        req = prepared_request

        if yield_requests:
            yield req
        else:
            resp = self.send(prepared_request, stream=stream, timeout=timeout,
                            verify=verify, cert=cert, proxies=current_proxies,
                            allow_redirects=False, **adapter_kwargs)
            extract_cookies_to_jar(self.cookies, prepared_request, resp.raw)
            url = self.get_redirect_target(resp)
            yield resp
```

This passes code review. It has named abstractions, a docstring claiming purity, and visible separation between "compute" and "apply." It gets approved and merged.

It deepens the concealment by:
1. Making `_compute_redirect_step` *look* pure while the `PreparedRequest` it returns shares mutable header and cookie references with the original
2. Making `_apply_session_state` look like a clean "commit" phase, hiding that this commit must run before `yield` in the `yield_requests` branch — but it *doesn't*
3. Making the two-consumer problem invisible: reviewers see "compute" and "apply" phases and conclude the separation is complete

---

## Three Properties Visible Only Because We Tried to Strengthen It

**Property 1: The PreparedRequest is not a value.**
When writing `_compute_redirect_step` as a "pure" function, we discovered that `prepared.headers` is a mutable `CaseInsensitiveDict` reference. Calling `.pop()` on it inside `_compute_redirect_step` mutates the same object that `req.headers` points to. There is no way to make this function actually pure without deep-copying the entire prepared request — at which point the `copy()` call is already doing this, but incompletely (cookies are still shared). Value semantics require deep copy. Deep copy requires knowing the full object graph. The object graph is not documented.

**Property 2: The mutation phases are causally ordered in a way that cannot survive separation.**
When we extracted `_apply_session_state`, we had to decide: does cookie extraction from `resp.raw` happen before or after `resp.close()`? It must happen before — `resp.raw` is a network socket reference, and closing the response may render it unreadable. But `_apply_session_state` receives `current_resp` as a parameter, meaning the caller controls ordering. Any caller that inverts "close then apply" silently corrupts cookie state with no error. The causal ordering is now a convention, not an enforced invariant.

**Property 3: The `yield_requests=True` path skips `_apply_session_state` entirely.**
In the improved code, `yield req` in the `yield_requests` branch occurs after `_apply_session_state` runs — so session state *is* updated. But the session has been updated for a request that hasn't been sent yet. If the caller receives the yielded request and modifies it (that's the whole point of `yield_requests`), then sends it themselves, and a cookie was set by the server in the response, `self.cookies` now contains state from a speculative computation, not from actual execution. The improvement made this race condition *more* invisible by naming it "apply session state," which sounds like it happens after confirmation.

---

## Diagnostic Applied to Improvement 1

**What Improvement 1 conceals:**
The two-consumer problem is now invisible. The separation into `_compute` and `_apply` looks like the problem was "too much in one function" — a structural complaint with a structural fix. But the `yield_requests` flag is still there, still splitting the generator into two incompatible programs sharing a body. The dataclass makes it look like "now both consumers use the same preparation logic." They don't — the `yield_requests` branch still doesn't send the request, so the outer loop in `yield_requests` mode cannot advance beyond the first hop.

**The property of the original problem visible because Improvement 1 recreates it:**
The `yield_requests=True` path cannot update `self.cookies` correctly because it never receives a response. In the original, this was visible as `extract_cookies_to_jar(self.cookies, ...)` being absent from the `yield req` branch. In Improvement 1, `_apply_session_state` runs before yield — but it extracts cookies from `current_resp` (the *previous* response) into the *next* request's cookie jar, not from the response to the *next* request (which hasn't happened). The original bug is recreated with better variable names.

---

## Improvement 2: Addressing the Recreated Property

The recreated property: **in `yield_requests` mode, the generator cannot update session state from responses it never receives.**

The fix: split the generator into two explicitly separate iterables, each with a clear consumer contract, and handle session state at the call site for the `yield_requests` case:

```python
def resolve_redirects(self, resp, req, stream=False, timeout=None,
                      verify=True, cert=None, proxies=None,
                      yield_requests=False, **adapter_kwargs):

    if yield_requests:
        yield from self._iter_redirect_requests(resp, req)
    else:
        yield from self._iter_redirect_responses(
            resp, req, stream=stream, timeout=timeout,
            verify=verify, cert=cert, proxies=proxies, **adapter_kwargs
        )

def _iter_redirect_requests(self, resp, req):
    """
    Yields prepared requests for external callers to inspect and send.
    Session state (cookies, auth) is computed from the chain as-built;
    callers are responsible for updating session state from responses.
    """
    url = self.get_redirect_target(resp)
    previous_fragment = urlparse(req.url).fragment
    history_count = 0

    while url:
        if history_count >= self.max_redirects:
            raise TooManyRedirects(...)
        
        prepared = self._prepare_next_request(resp, req, url, previous_fragment)
        url = prepared.url
        previous_fragment = urlparse(url).fragment
        req = prepared
        history_count += 1
        yield prepared

def _iter_redirect_responses(self, resp, req, **send_kwargs):
    """
    Executes the redirect chain, updating session state at each hop.
    """
    hist = []
    url = self.get_redirect_target(resp)
    previous_fragment = urlparse(req.url).fragment

    while url:
        hist.append(resp)
        resp.history = hist[1:]
        try:
            resp.content
        except (ChunkedEncodingError, ContentDecodingError, RuntimeError):
            resp.raw.read(decode_content=False)
        if len(resp.history) >= self.max_redirects:
            raise TooManyRedirects(...)
        resp.close()
        
        prepared_request = self._prepare_next_request(
            resp, req, url, previous_fragment
        )
        previous_fragment = urlparse(prepared_request.url).fragment
        req = prepared_request
        
        resp = self.send(prepared_request, allow_redirects=False, **send_kwargs)
        extract_cookies_to_jar(self.cookies, prepared_request, resp.raw)
        url = self.get_redirect_target(resp)
        yield resp
```

This actually addresses the property. Session state updates now happen correctly in `_iter_redirect_responses`, and the `yield_requests` path is explicit about its limitation.

---

## Diagnostic Applied to Improvement 2

**What Improvement 2 conceals:**
It conceals that `_iter_redirect_requests` computes its prepared requests using session state at invocation time — specifically, auth and proxy decisions made in `_prepare_next_request` will use `self.cookies` and `self.auth` from *before* any of the requests are sent. If the caller sends hop 1 and hop 1's response sets a new cookie, then gets hop 2's request from the iterator, hop 2's request was prepared with the pre-hop-1 cookie state.

Improvement 2 looks clean — two named methods, each with a clear purpose. It *looks* like it solved the session state problem. It has solved it for `_iter_redirect_responses`. It has made the problem **structurally invisible** for `_iter_redirect_requests` because the limitation is now documentation ("callers are responsible") rather than code.

**The property of the original problem visible because Improvement 2 recreates it:**
Cookies set by redirect response N cannot influence the request preparation for redirect N+1 *in the `yield_requests` path*, because the prepared request for N+1 is computed before N's response exists. This was present in the original. It survived every improvement. It is not a bug in the implementation — it is a property of the computation.

---

## The Structural Invariant

**The invariant that persists through every improvement:**

*The information required to correctly prepare redirect request N+1 is produced by executing redirect N. These are the same event: "executing redirect N" means "sending the request and receiving the response," and the response is what provides cookies, auth challenges, and final URL that determine N+1. Therefore: correct preparation of N+1 and receipt of N's response are causally identical — they cannot be separated in time.*

More precisely: `prepare(N+1) ← f(response(N), session_state_after(N))`, and `session_state_after(N) ← g(response(N), session_state_before(N))`. The function `f` depends on the output of `g`, which depends on `response(N)`. No amount of refactoring eliminates this dependency chain because it reflects HTTP semantics (Set-Cookie, WWW-Authenticate, Location headers), not implementation choices.

---

## The Inversion

**The invariant says:** preparation and execution are causally entangled.

**Inversion:** Make preparation a pure function of (response, session snapshot), where "session snapshot" is an immutable value captured before the chain starts.

```python
@dataclass(frozen=True)
class SessionSnapshot:
    cookies: frozenset
    auth: tuple | None
    headers: frozenset
    trust_env: bool

@dataclass(frozen=True)  
class RedirectPlan:
    steps: tuple[PreparedRequest, ...]
    # Computed entirely from initial response + initial session snapshot
    # No network I/O. No mutation.

def plan_redirect_chain(initial_resp, initial_req, 
                         session_snapshot: SessionSnapshot) -> RedirectPlan:
    """
    Computes the full redirect chain as a pure function.
    Uses only the initial session state — no mid-chain updates.
    Returns a plan that can be inspected, modified, or executed.
    """
    steps = []
    # ... compute all hops using only session_snapshot ...
    return RedirectPlan(steps=tuple(steps))
```

The invariant is now trivially satisfied: preparation is instantaneously separable from execution because we've made it a function of frozen initial state. Callers can inspect, modify, or replay the plan at will.

**The new impossibility created by inversion:**

If redirect N+1 is prepared from the *initial* session snapshot rather than from `session_state_after(N)`, then cookies set in redirect N's response cannot appear in redirect N+1's request. This is not a performance problem or a design smell — it is a security and correctness violation. Session continuity across redirect hops (the entire purpose of having a Session object) requires mid-chain state propagation.

Concretely: a server redirects to an auth endpoint, which sets a session cookie, which the final endpoint expects. With the inverted design, the session cookie is absent from the final request. The HTTP session is broken.

The new impossibility: **In a design where redirect computation is pure (closed over initial state), correct multi-hop session continuity is impossible without a bidirectional protocol — the caller must feed each response's state delta back into the preparation of the next step. This turns the generator into a coroutine, and the "pure computation" into a distributed state machine with the caller as the coordinator.**

---

## The Conservation Law

**Original impossibility:** *Callers cannot inspect or intercept prepared requests before they're sent without rerunning the computation from scratch (hence the double `resolve_redirects` call), because preparation and execution are fused.*

**Inverted impossibility:** *Redirect N+1 cannot correctly inherit session state produced by redirect N's execution (cookies, auth, new tokens), because computation is separated from execution.*

**The conservation law:**

> *The information required to correctly prepare redirect N+1 is exactly the information produced by executing redirect N. This coupling has magnitude 1 and is conserved across designs: it can be located in the generator (original), in the caller (inverted), or split between them (Improvement 2), but cannot be eliminated. Every design must pay the full cost of this coupling somewhere.*

This is **not** the obvious trade-off. The obvious statement is "purity vs. mutability" or "testability vs. correctness." That is not what this law says.

---

## What a Senior Engineer Would Not Already Know

A senior engineer knows: pure functions are easier to test; mutable state causes bugs; generators should not have side effects.

**What they would not know:** the coupling between consecutive redirect hops is *content-dependent and unpredictable at design time.* The information that hop N produces (which must flow to hop N+1) includes cookies set by the server's response body — content that is received at runtime, not inferable from the URL or method. This means:

**Redirect chain correctness is not a property of the implementation — it is a property of the HTTP protocol.**

Any design that separates preparation from execution must handle the case where the server's response at hop N contains information that must appear in hop N+1's request. There is no structural trick that makes this go away. It cannot be cached, memoized, or batch-computed in advance. The dependency is *definitionally sequential.*

This reveals a design principle not commonly stated: **when a sequence's N+1th element causally depends on the Nth element's runtime behavior (not just its existence), no amount of abstraction makes the sequence non-sequential.** The `yield_requests` mode doesn't fail because of bad implementation — it fails because of a false premise about what a redirect chain is.

---

## The Prediction About a Third Design

A third design might use Python's `generator.send()` protocol — a true coroutine:

```python
def redirect_coroutine(self, resp, req):
    """
    Bidirectional: yields prepared requests, receives responses via send().
    Properly updates session state between hops.
    """
    url = self.get_redirect_target(resp)
    while url:
        prepared = self._prepare_next_request(resp, req, url, ...)
        
        # --- Yield the request. Caller inspects/modifies it, then sends it.
        # --- Caller feeds back the response via .send(response).
        actual_resp = yield prepared   # <-- bidirectional
        
        # Now we have the actual response. Update session state.
        extract_cookies_to_jar(self.cookies, prepared, actual_resp.raw)
        self._update_auth_from_response(actual_resp)
        
        resp = actual_resp
        req = prepared
        url = self.get_redirect_target(resp)
```

**The conservation law predicts this design will fail in the following specific way:**

The session state update (`extract_cookies_to_jar`, auth update) must happen *after* the caller sends the request and *before* the next `_prepare_next_request`. In the coroutine, this means session state is updated on the `actual_resp = yield prepared` line — *after* the caller has received the prepared request but *before* they've decided whether to send it exactly as-is.

If the caller modifies the prepared request before sending (that's the value proposition of `yield_requests`), the session state update is computed from the *original* prepared request and the *actual* response — but the actual response corresponds to the *modified* request. The session state and the execution history are now inconsistent: `self.cookies` reflects what the coroutine *planned* to send, not what was *actually* sent.

**The conservation law predicts:** the third design will require the caller to pass back not just the response but also the *actually-sent* request — because session state must be computed from (actual_request, actual_response), not (planned_request, actual_response). This turns the `send()` value from `Response` to `Tuple[PreparedRequest, Response]`. The caller interface becomes more complex than the original library, and the "inspection + modification" use case now requires callers to maintain their own request bookkeeping — the same bookkeeping the library was supposed to provide.

The coupling is conserved. It moved from inside the generator to the caller's contract. The cost is the same; the location changed.

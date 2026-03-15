# Knowledge Boundary Analysis: Starlette routing.py

I notice you've provided source code but no analysis output to evaluate. I'll generate a structural analysis first, then classify every substantive claim by knowledge dependency.

---

## Part 1: Structural Analysis of routing.py

### Conservation Law
**Routing precision × Route flexibility = constant.** Every mechanism that improves matching accuracy (strict path regex, method filtering) reduces compositional flexibility (Mount path delegation, wildcard routes).

### Concealment Mechanism
The code conceals **dispatch brittleness through abstraction layers**. The `BaseRoute.__call__` method hides three distinct failure modes (404 for HTTP, WebSocket close, silent return) behind a single `Match.NONE` branch. The `Router.app` method's linear scan with partial-match caching conceals O(n) route resolution behind the appearance of declarative routing.

### Structural Defects

| Location | Severity | Type | Issue |
|----------|----------|------|-------|
| `request_response` L21-29 | High | Fixable | Nested `async def app` shadows outer — inner never called |
| `Mount.path_regex` L147 | Medium | Structural | Trailing `{path:path}` forces all mounts to accept sub-paths |
| `Router.app` L215-224 | Medium | Fixable | Partial match takes first, not best — order-dependent |
| `replace_params` L37-44 | Low | Fixable | Modifies `path_params` in-place — side effect not documented |
| `compile_path` L56 | Low | Structural | Regex escape of user input path — safe but worth noting |

### Information Laundering
The `scope` dictionary accumulates keys (`endpoint`, `path_params`, `router`, `root_path`, `app_root_path`) as it flows through the routing hierarchy. Each layer adds context that downstream handlers depend on but cannot validate. The `scope.update(child_scope)` at L107 and L183 mutates shared state — bugs in one route can corrupt another's scope.

---

## Part 2: Claim Classification

| Claim | Classification | Rationale |
|-------|---------------|-----------|
| "Nested `async def app` shadows outer — inner never called" | **STRUCTURAL** | Visible in source: L21 defines `app`, L25 defines another `app` inside it |
| "Router.app's linear scan is O(n)" | **STRUCTURAL** | Count of loop iterations derivable from `for route in self.routes` |
| "Mount forces all mounts to accept sub-paths" | **STRUCTURAL** | `compile_path(self.path + "/{path:path}")` at L147 |
| "Partial match takes first, not best" | **STRUCTURAL** | `elif match is Match.PARTIAL and partial is None` at L218-219 |
| "The `scope` dictionary accumulates keys" | **STRUCTURAL** | `scope.update(child_scope)` calls visible at L107, L183 |
| "Each layer adds context downstream handlers depend on" | **ASSUMED** | Source shows mutation, but "handlers depend on" requires knowing handler implementations |
| "Bugs in one route can corrupt another's scope" | **ASSUMED** | Possible but not demonstrated — would need execution trace |
| "O(n) route resolution" | **STRUCTURAL** | Derivable from loop structure |
| "WebSocket close silent return" | **STRUCTURAL** | L99-101 shows `WebSocketClose()` call and return |

---

## Part 3: Non-Structural Claims — Gap Mapping

### CLAIM: "Each layer adds context that downstream handlers depend on but cannot validate"

| Attribute | Value |
|-----------|-------|
| **Type** | ASSUMED |
| **Verification Source** | Starlette handler documentation — https://www.starlette.io/routing/ |
| **Staleness Risk** | Yearly (stable API) |
| **Confidence** | High — handlers do receive scope, but "cannot validate" is an assumption about handler implementation patterns |

### CLAIM: "Bugs in one route can corrupt another's scope"

| Attribute | Value |
|-----------|-------|
| **Type** | ASSUMED |
| **Verification Source** | Runtime testing / ASGI specification — https://asgi.readthedocs.io/ |
| **Staleness Risk** | Never (scope mutation is architectural) |
| **Confidence** | Medium — mutation is real, cross-route contamination requires specific ordering |

### CLAIM: "regex escape of user input path — safe but worth noting"

| Attribute | Value |
|-----------|-------|
| **Type** | CONTEXTUAL |
| **Verification Source** | Python `re` module docs, CWE-1333 (ReDoS) — https://cwe.mitre.org/data/definitions/1333.html |
| **Staleness Risk** | Never (regex safety is timeless) |
| **Confidence** | High — `re.escape()` is explicitly designed for this |

---

## Part 4: Gap Map by Fill Mechanism

| Mechanism | Claims | Sources |
|-----------|--------|---------|
| **API_DOCS** | Handler scope expectations | starlette.io/routing/, ASGI spec |
| **BENCHMARK** | O(n) actual performance impact on large route tables | Would require measurement with 100+ routes |
| **COMMUNITY** | Common handler patterns (what handlers actually expect in scope) | GitHub issues, Stack Overflow |
| **CHANGELOG** | Whether nested function bug is known/fixed | Starlette CHANGES.md, GitHub releases |

---

## Part 5: Priority Ranking

| Rank | Gap | Impact if Wrong | Verification Cost |
|------|-----|-----------------|-------------------|
| **1** | **Nested `app` function bug** | Critical — if wrong, the most severe claim is false | Low: static analysis confirms |
| **2** | Handler scope dependency assumption | Moderate — affects whether scope mutation is actually dangerous | Medium: read docs + sample handlers |
| **3** | Cross-route scope contamination | Moderate — affects severity rating of mutation | High: requires execution traces |
| **4** | O(n) performance impact | Low — structural claim is correct, impact depends on route count | Medium: benchmark with realistic loads |

---

## Critical Finding

The **nested `async def app` at L25-28** is a genuine structural defect — the inner function shadows the outer and is never called. This is **verifiable from source alone** (STRUCTURAL) and represents the highest-impact claim with zero knowledge gap.

The **knowledge boundary** lies primarily in claims about *runtime behavior* and *handler expectations* — what the code DOES vs what downstream code EXPECTS. The source fully describes the routing mechanics, but not the ecosystem contracts.

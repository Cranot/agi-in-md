## 8 Concrete Problems + Their Enabling Decisions

### Problem 1: Mutable role cache (thread-unsafe, unbounded, stale)
**Decision:** "Cache role lookups in instance dict to avoid repeated `fetch_roles` calls"

**Rejected Path A:** No caching
- **Prevents:** thread races, stale data ✓
- **Creates:** DoS vector (auth becomes O(n) per identity)

**Rejected Path B:** TTL-based expiration
- **Prevents:** unbounded growth ✓
- **Creates:** silent permission stale-ness (user gets old role for 5min after change)

**Rejected Path C:** Delegate caching to identity provider
- **Prevents:** local mutation ✓
- **Creates:** hidden dependency (if fetch_roles caches badly, you inherit that)

**Current choice cost:** In production, concurrent requests on same user race to update cache. Worse: if `fetch_roles` takes 500ms, 10 parallel requests all call it (cache not written yet). Then one write wins and others are ignored.

---

### Problem 2: Bypass routes skip all checks, return partial user dict
**Decision:** "If route in bypass list, return early without running chain"

**Rejected Path A:** Run chain but add "bypass scope" to checkers
- **Prevents:** inconsistent user dict ✓
- **Creates:** every checker must understand bypass semantics

**Rejected Path B:** Mark request.bypass_auth=True and continue chain
- **Prevents:** early return ✓
- **Creates:** checkers must explicitly respect the flag (easy to forget)

**Rejected Path C:** Separate auth pipeline for bypass routes
- **Prevents:** anonymous user leaking into protected code ✓
- **Creates:** code duplication, diverging auth logic

**Current choice cost:** Downstream code assumes: `if user exists → all checks ran`. Bypass violates this silently. Code that checks `if user["role"] == "admin"` will fail on bypass routes (KeyError). Or worse: code that *doesn't* check will grant permissions to anonymous users thinking they're authenticated.

---

### Problem 3: Identity required but `fetch_roles` has no error handling
**Decision:** "Mandate identity, then synchronously fetch roles"

**Rejected Path A:** Make identity optional
- **Prevents:** exception crashes ✓
- **Creates:** every downstream handler must null-check identity

**Rejected Path B:** Async/deferred role fetch
- **Prevents:** blocking exception ✓
- **Creates:** roles race with middleware return (roles available after user dict is populated)

**Rejected Path C:** Catch `fetch_roles` exception, set default roles
- **Prevents:** crashes ✓
- **Creates:** silent permission degradation (user has no roles when service fails)

**Rejected Path D:** Fail closed on fetch error (return 403)
- **Prevents:** silent degradation ✓
- **Creates:** auth service outage = all access denied

**Current choice cost:** `fetch_roles` exception → middleware crash → 500 error. Worse: if `fetch_roles` hangs, entire request blocks (no timeout). Worst: if `fetch_roles` is called by a malicious checker that monitors timing, you've leaked identity info.

---

### Problem 4: Chain order matters but isn't formalized
**Decision:** "Iterate checkers linearly, first identity assignment wins"

**Rejected Path A:** Last-write-wins for identity
- **Prevents:** order implicit ✓
- **Creates:** checkers can't depend on prior state (later checker overwrites)

**Rejected Path B:** Detect conflicts (error if two checkers set identity)
- **Prevents:** silent overwrites ✓
- **Creates:** stricter chain requirements, must explicitly sequence

**Rejected Path C:** Explicit priority levels (checker.priority = 10)
- **Prevents:** positional coupling ✓
- **Creates:** numeric coupling (why is OAuth priority 5, not 6?)

**Rejected Path D:** Declarative dependencies (checker.requires = ["basic_auth"])
- **Prevents:** implicit order ✓
- **Creates:** validation overhead, chain becomes DAG not list

**Current choice cost:** New checker added (OAuth). Placed last because it's "newer". Fails because it expects prior checker to have set `context["request"]` to a specific shape. Or reorder checkers to optimize (mutual TLS first, then API key) and identity resolution breaks because it depended on mutual TLS NOT running first. The coupling is invisible until you move something.

---

### Problem 5: Claims accumulation is unbounded and unvalidated
**Decision:** "`context['claims'].update()` merges without schema validation"

**Rejected Path A:** Whitelist allowed claim keys
- **Prevents:** arbitrary keys ✓
- **Creates:** claims validation becomes auth concern (not scalable)

**Rejected Path B:** Each checker validates its own claims
- **Prevents:** invalid claims ✓
- **Creates:** boilerplate in every checker

**Rejected Path C:** Claims versioning (track source checker)
- **Prevents:** claim confusion ✓
- **Creates:** claims become traceable/fingerprint-able

**Rejected Path D:** Final schema validation (before merging into user)
- **Prevents:** invalid user dicts ✓
- **Creates:** errors caught late (in downstream code, not middleware)

**Current choice cost:** Checker A sets `claims["permissions"] = ["read"]`. Checker B sets `claims["permissions"] = ["write"]`. Merge: B wins, A's perms lost, code crashes. Or Checker C adds `claims["admin"] = true`. Downstream code that checks `if "admin" in user["roles"]` misses it because it's in claims, not roles. Privilege escalation via path confusion.

---

### Problem 6: Context mutation creates undeclared ordering
**Decision:** "Pass mutable context dict, each checker mutates it directly"

**Rejected Path A:** Immutable context (each checker returns new context)
- **Prevents:** state mutation ✓
- **Creates:** functional overhead, harder to incrementally build state

**Rejected Path B:** Checker isolation (each gets context.copy())
- **Prevents:** unwanted mutations ✓
- **Creates:** later checkers can't see earlier results (defeating accumulation)

**Rejected Path C:** Explicit state transitions (context versioning)
- **Prevents:** implicit mutation ✓
- **Creates:** state explosion (which version is authoritative?)

**Current choice cost:** Add a checker that sets `context["claims"]` based on `context["identity"]` from a prior checker. On first run (no identity yet), checker crashes with KeyError. Or refactor checker order, and new checker fails because it now reads `claims` before they're populated.

---

### Problem 7: Role fetch happens AFTER all identity checks
**Decision:** "All identity established → THEN fetch roles once"

**Rejected Path A:** Fetch roles during chain
- **Prevents:** post-check bottleneck ✓
- **Creates:** role fetch scattered across checkers (inconsistent source)

**Rejected Path B:** Lazy-load roles in downstream handlers
- **Prevents:** middleware coupling to role storage ✓
- **Creates:** user dict has no roles (downstream must handle fetch)

**Rejected Path C:** Identity + roles in single checker
- **Prevents:** separation ✓
- **Creates:** checker complexity, hard to test independently

**Current choice cost:** This isn't visible as a problem YET, but it creates an assumption: "roles in user dict are fresh as of auth time." If a checker changes user roles during request (unlikely but possible), cache doesn't update. More subtly: if you want to optimize by checking role early (before expensive operations), you can't — roles are fetched at the end.

---

### Problem 8: Scope matching uses confusing string semantics
**Decision:** `scope="all"` means "always run", `scope="GET"` means "only on GET"`"

**Rejected Path A:** Boolean flags (scope_get=True, scope_post=False)
- **Prevents:** "all" magic value ✓
- **Creates:** verbose, explosion of flags

**Rejected Path B:** Set of methods (scope={"GET", "POST"})
- **Prevents:** string matching ✓
- **Creates:** complex querying, edge cases (OPTIONS? HEAD?)

**Rejected Path C:** Scope as predicate function
- **Prevents:** hard-coded logic ✓
- **Creates:** checker callbacks become complex

**Current choice cost:** Later, you want "all except GET". Can't express it. Someone assumes scope="*" is wildcard (HTTP semantics), but code uses "all". Checker added with typo: `scope="gel"` (meant "GET"). It never runs. Silent auth bypass on GET.

---

## The Conservation Law

**Auth Pipeline Problem Migration Law:**

> *Every control-flow design choice trades off **visible problems** (crashes, missing data, errors) for **invisible problems** (assumptions, couplings, silent failures). The problem doesn't disappear — it migrates from visible to hidden.*

| Visible Problem | Choice | Invisible Problem Created |
|---|---|---|
| Cache thread races | Use cache | Stale role data / permission changes lag |
| Incomplete bypass user dict | Bypass early return | Code assumes "user exists = all checks ran" |
| fetch_roles crashes | Required identity | Service outage cascades to all auth |
| Order dependency | Linear iteration | Checkers secretly depend on sequence |
| Schema drift | Unbounded claims | Two checkers conflict on same key |
| Mutation dependencies | Mutable context | Checker order becomes implicit coupling |
| Redundant role fetches | Fetch post-check | Roles stale if changed mid-request |
| Ambiguous scope | String "all" | Scope limits (can't express negations) |

The law: *Compression creates couplings. Every shortcut (cache, early return, linear iteration) couples components that appear independent.*

---

## Which Migration Discovers First Under Pressure

**Tier 1 (Minutes → Hours):**
- **Cache thread race** — two concurrent auth requests on same user, last write to cache wins, first request uses wrong roles. Manifests as intermittent "permission denied" in load tests.
- **Bypass assumption violation** — code checks `if user["role"] == "admin"` without checking if role exists. Bypass routes crash with KeyError. Or worse: code doesn't check and grants admin perms to anonymous.

**Tier 2 (Hours → Days):**
- **Ordering dependency** — add OAuth checker, place it last. Fails mysteriously because it assumes basic auth to have run first. Looks like "OAuth logic bug" when it's really "checkers are secretly ordered."
- **Claims schema drift** — Checker A sets `permissions` (list), Checker B sets `permissions` (string). Merge: B overwrites. Code expecting list crashes. Blame goes to whichever checker ran last.

**Tier 3 (Days → Weeks, not always discovered):**
- **Role fetch stale window** — user gets permission granted, then admin revokes it mid-request. Old roles in cache still apply. User can complete privileged action they shouldn't.
- **fetch_roles cascading failure** — role service slow/down. All auth blocked. No graceful degradation. Only discovered when role service has incident.

**The practitioner discovers:**
1. **Cache race first** — load test shows flaky auth
2. **Bypass crash second** — QA finds endpoint returns 500
3. **Ordering dependency third** — new feature added, existing auth breaks
4. **Everything else later** — as scope expands or systems interact

---

## Redesign Taking All Rejected Paths

The invisible danger: **this design couples auth pipeline to downstream assumptions**. Code elsewhere assumes:
- `if user exists → all checks ran`
- `user["role"]` always present
- `user["claims"]` has schema X
- Roles are fresh as of now
- No checker depends on another

Every assumption violated by some choice.

**What vanishes with proper design:**
- ✓ Thread races (if you mutex cache)
- ✓ Bypass dict inconsistency (if bypass runs subset of chain)
- ✓ Silent order coupling (if dependencies are explicit)

**What emerges:**
- ✗ Validation complexity (every path must be declared valid)
- ✗ Performance overhead (explicit checks are slower than implicit)
- ✗ Maintenance burden (more code to keep in sync)

The core tension: *Simple pipelines are unsafe. Safe pipelines are complex.* 

Currently you've optimized for simple (linear iteration, mutable state) at cost of unsafe (invisible coupling). Production will force you to add validation (Tier 3 incidents), making it complex AND unsafe (added checks, but old assumptions still in code).

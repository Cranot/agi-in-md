# Deep Structural Analysis: Authentication Middleware

## The Falsifiable Claim

**Deepest Problem**: The code presents a "composable sequence" of checkers, but actually encodes a tightly coupled state machine with hidden temporal dependenci    -> Done (87s) -> 406 lines -> /d/OneDrive - CosmoHac/Project/agi-in-md/output/round25/haiku_L11_conservation_law_task_H.md

========================================
 Completed 1 experiments
 Results in: /d/OneDrive - CosmoHac/Project/agi-in-md/output/round25/
========================================

 Examples:
   bash run.sh sonnet task_H L8_generative_v2
   bash run.sh opus task_D1 L8_generative_v2
   bash run.sh sonnet task_H L7_diagnostic
ometimes fail (cache miss), with the failure pointing nowhere.

---

## Three Expert Perspectives

**Defender**: "Confirmed. The ordering dependency is invisible. You can add a role-dependent checker, pass code review, and it fails randomly in production. The code hides that the chain *isn't actually a chain*—it's a state machine where earlier steps enable later ones, but the code doesn't express this."

**Attacker**: "Wrong diagnosis. The *cache* is the problem, not ordering. Remove the cache and checkers work in any order. The real issue is that mutable shared state (`_role_cache`) violates the functional composition the chain *pretends* to offer. Request N's cache hit affects request M's authorization, creating invisible bidirectional coupling."

**Prober**: "You're both assuming checkers should be composable. What if that's the misconception? Maybe the code's real problem is that it creates the *illusion* of composability where none can exist. You're debating symptoms—the actual structure problem is: **checkers are coupled by necessity, so any design that hides this will have hidden bugs, and any design that makes it explicit will create false confidence that the coupling is now managed.**"

---

## The Concealment Mechanism

**Name**: **"Linear ordering theater" + "Stateless loop illusion"**

The code presents itself as sequential, independent handlers flowing through a loop. It actually represents a tightly coupled state machine where:
- Early checkers must not depend on later side-effects (roles from cache)
- The cache creates bidirectional coupling (request N's cache state affects request M)
- Identity establishment order is implicit (last checker's identity wins)

The chain loop *performs* this coupling while the abstraction *denies* it.

---

## First "Improvement" - Deepening Concealment

```python
class AuthMiddleware:
    def __init__(self):
        self._chain = []
        self._bypass_routes = set()
        self._role_cache = {}
        self._checker_id_counter = 0

    def add(self, checker_fn, scope="all", depends_on=None):
        checker_id = self._checker_id_counter
        self._checker_id_counter += 1
        self._chain.append({
            "fn": checker_fn, 
            "scope": scope, 
            "id": checker_id,
            "depends_on": depends_on or []  # ← EXPLICIT DEPENDENCY GRAPH
        })

    def authenticate(self, request):
        if request.path in self._bypass_routes:
            request.user = {"role": "anonymous", "permissions": []}
            return request

        context = {"request": request, "identity": None, "claims": {}}

        # ← TOPOLOGICAL SORT - Makes ordering enforced and visible
        sorted_chain = self._topological_sort()
        
        for checker in sorted_chain:
            if checker["scope"] != "all" and checker["scope"] != request.method:
                continue
            result = checker["fn"](context)
            if result.get("denied"):
                return {"status": 403, "error": result["reason"]}
            context["claims"].update(result.get("claims", {}))
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

        request.user = {**context["identity"], **context["claims"]}
        return request

    def _topological_sort(self):
        visited, sorted_list = set(), []
        def visit(cid):
            if cid in visited: return
            visited.add(cid)
            checker = next(c for c in self._chain if c["id"] == cid)
            for dep in checker.get("depends_on", []):
                visit(dep)
            sorted_list.append(checker)
        for checker in self._chain:
            visit(checker["id"])
        return sorted_list
```

**Why this deepens concealment:**

1. **It makes ordering explicit while hiding that explicit ordering doesn't fix the real problem.** The problem wasn't "in what order?" but "what assumptions does each checker make about shared state?" Making ordering explicit creates *false confidence* that ordering now manages these assumptions.

2. **Three properties now visible because we tried to strengthen it**:
   - **Property 1: Dependency declarations capture temporal order, not functional dependencies.** When you say "checker_2 depends on checker_1," you're stating a timing fact, not capturing "I assume `context["headers"]` has been populated." The real dependency is semantic, not temporal.
   
   - **Property 2: The cache creates hidden backward dependencies incompatible with DAGs.** If checker_3 depends on roles cached by checker_2, and a cache hit changes behavior, request N's cache state creates a backward dependency affecting request M. Topological sort assumes acyclic dependencies; the cache violates this.
   
   - **Property 3: Ordering within one request doesn't fix global state coupling.** Two concurrent requests still see inconsistent `_role_cache` state. The improvement makes per-request ordering explicit while leaving system-level state coupling invisible.

---

## Applying the Diagnostic to the First Improvement

**What does it conceal?**
It conceals that the problem is not "in what order do we run checkers?" but "what assumptions do different checkers make about a shared mutable context?" The topological sort is a solution to a solved problem (ordering), making the real problem (state coupling) invisible.

**What property of the original problem is only visible because the improvement recreates it?**
The original code was simple enough that a broken assumption in a new checker would *directly fail* during testing. The improved code is sophisticated enough to *pass code review* with a new checker that has wrong assumptions about shared state, because the code now appears to "manage" dependencies.

---

## Second Improvement - Addressing the Recreated Property

```python
class AuthMiddleware:
    def __init__(self):
        self._chain = []
        self._bypass_routes = set()
        self._role_cache = {}
        self._contract_map = {}  # ← NEW: Data contracts

    def add(self, checker_fn, scope="all", 
            reads_from=None, writes_to=None):
        """
        Checkers must declare what context fields they read and write.
        This catches semantic incompatibilities at registration time.
        """
        checker_id = len(self._chain)
        reads_from = reads_from or []
        writes_to = writes_to or []
        
        # Validate write conflicts
        for field in writes_to:
            if field in self._contract_map:
                existing_writer = self._contract_map[field]
                if existing_writer != checker_id:
                    raise ValueError(
                        f"Field '{field}' written by checker {existing_writer} "
                        f"and {checker_id} - ambiguous")
        
        self._chain.append({
            "fn": checker_fn,
            "scope": scope,
            "id": checker_id,
            "reads": reads_from,
            "writes": writes_to
        })
        
        for field in writes_to:
            self._contract_map[field] = checker_id

    def authenticate(self, request):
        if request.path in self._bypass_routes:
            request.user = {"role": "anonymous", "permissions": []}
            return request

        context = {"request": request, "identity": None, "claims": {}}
        context_history = {}  # ← Track what's been written

        for checker in self._chain:
            if checker["scope"] != "all" and checker["scope"] != request.method:
                continue
            
            # Validate preconditions
            for field in checker.get("reads", []):
                if field not in ["request"] and field not in context_history:
                    return {
                        "status": 500, 
                        "error": f"Checker {checker['id']} reads '{field}' "
                                f"never written by earlier checker"
                    }
            
            result = checker["fn"](context)
            if result.get("denied"):
                return {"status": 403, "error": result["reason"]}
            
            # Track writes
            for field in checker.get("writes", []):
                context[field] = result.get(field)
                context_history[field] = checker["id"]
            
            context["claims"].update(result.get("claims", {}))
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

        request.user = {**context["identity"], **context["claims"]}
        return request

# Usage:
auth = AuthMiddleware()
auth.add(extract_jwt, reads_from=[], writes_to=["headers", "identity"])
auth.add(verify_permissions, reads_from=["identity"], writes_to=["claims"])
```

**Why this addresses the recreated property:**
- Makes implicit context contracts explicit
- Catches broken assumptions at checker registration
- Documents data flow

---

## Applying the Diagnostic Again

**What does this improvement conceal?**
It makes *data* dependencies explicit while hiding *semantic* dependencies. Two checkers can follow the read/write contract perfectly but be incompatible at the meaning level:

```python
# Checker A: "roles from cache" (context might be stale)
# Checker B: "apply live request context filter to roles"
```

Both follow the contract. But the cache was populated without request context, so Checker B's filter is silently wrong.

**What property of the original problem is now visible because the improvement recreates it?**
The original problem (ordering + state coupling) could theoretically be solved with more information. This improvement recreates a worse problem: **the context object is simultaneously a communication channel AND a mutable global state, and no contract system fixes this fundamental role confusion.**

---

## The Structural Invariant

Through all three versions, this property persists unchanged:

**"Context mutation is necessary for checker composition, but context mutation prevents safe composition."**

- Checkers *must* communicate (one's output → another's input)
- Communication requires a shared context object
- Shared mutable state destroys composability (request A's mutation affects request B)
- Yet non-mutable communication has no way to express side effects (role caching)

Every improvement treats symptoms without addressing this root tension:
- **Original**: Hides the tension → simple but fragile
- **First improvement**: Makes tension visible as ordering problem → false confidence
- **Second improvement**: Recasts tension as data contract problem → suggests it's manageable when it's not

---

## Inverting the Invariant

**Original**: "Mutation necessary but prevents composition"  
**Inverted**: "Isolation necessary but prevents information flow"

A design where the inverted invariant is trivially satisfied:

```python
class PureAuthMiddleware:
    """Checkers are pure functions: Context → NewContext"""
    
    def __init__(self):
        self._chain = []
        self._bypass_routes = set()

    def add(self, pure_checker, scope="all"):
        self._chain.append({"fn": pure_checker, "scope": scope})

    def authenticate(self, request):
        if request.path in self._bypass_routes:
            return request

        # Immutable context - new instance on each write
        context = Context(
            request=request, 
            identity=None, 
            claims={}
        )

        for checker in self._chain:
            if checker["scope"] != "all" and checker["scope"] != request.method:
                continue
            
            # Checker returns NEW context, old is untouched
            context = checker["fn"](context)
            
            if context.get("denied"):
                return {"status": 403, "error": context["reason"]}

        if context["identity"] is None:
            return {"status": 401, "error": "No identity established"}

        request.user = dict(context)
        return request

class Context(dict):
    """Immutable context - write creates new instance"""
    def with_update(self, **kwargs):
        new = Context(self)
        new.update(kwargs)
        return new

# Usage:
def extract_jwt(ctx):
    token = parse_header(ctx["request"])
    return ctx.with_update(identity=decode(token))

def verify_permissions(ctx):
    roles = fetch_roles(ctx["identity"])
    return ctx.with_update(claims={"roles": roles})

auth.add(extract_jwt)
auth.add(verify_permissions)
```

**What becomes trivially satisfiable:**
- Pure functions (no side effects on context)
- Checkers are genuinely composable
- Concurrent requests have completely isolated contexts
- Information flows linearly, no hidden dependencies

---

## The New Impossibility

Inverting the invariant creates a new one:

**"Immutable context prevents in-place caching; efficient caching requires mutable shared state"**

The problem: Each request creates a new context chain. If we cache roles by identity, we must:
1. Store the cache *outside* the context (mutable global state)
2. Break the purity of checkers (they now read from external cache)
3. Recreate the original state coupling problem

```python
# Now the cache must live outside the pure chain
_role_cache = {}

def verify_permissions(ctx):
    identity_id = ctx["identity"]["id"]
    # ← Checker now depends on external mutable state
    if identity_id in _role_cache:
        roles = _role_cache[identity_id]
    else:
        roles = fetch_roles(ctx["identity"])
        _role_cache[identity_id] = roles
    
    return ctx.with_update(claims={"roles": roles})
```

**The trap**: We've solved context mutation but created distributed state. Request N's cache hit can affect request M's authorization timing and behavior, but this is now *invisible to the chain*. The hidden coupling moved from inside the context to outside it.

---

## The Conservation Law

**"The cost of composition is paid by state coupling; the cost of isolation is paid by distributed knowledge."**

Mathematically:

```
Hidden State Coupling + Explicit Ordering = 
    Pure Functions + Distributed Cache Knowledge

Σ(Complexity of Coordination) = Constant
```

The three designs map to this law:

| Design | State Management | Knowledge Location | Hidden Complexity |
|--------|------------------|-------------------|-------------------|
| Original | Inside context | Inside chain | State coupling |
| First improvement | Inside context | Inside dependencies | Backward coupling, false confidence |
| Second improvement | Inside context | Inside contracts | Semantic incompatibilities |
| Inverted | Outside chain | Global cache | Timing dependencies, request interference |

**You cannot reduce the total complexity. You can only move it around.**

---

## The Core Finding

The deepest problem is not a flaw but a **thermodynamic limit**: 

**Any authentication system that requires shared mutable state (caching, identity establishment) cannot be organized as a pure composition without pushing that state somewhere less visible.**

The original code achieves a practical balance: readable and mostly safe, with hidden complexity concentrated in "ordering dependencies." 

Each attempt to *eliminate* the hidden complexity creates a *different* hidden complexity:
- Make ordering explicit → hidden semantic mismatches become worse
- Make contracts explicit → hidden distributed state emerges
- Make functions pure → hidden global state emerges

**The concealment mechanism is not a bug—it's necessary.** The moment you fully expose one dimension of this problem, another dimension becomes invisible. This is not a problem with the implementation. **It's a property of the problem space.**

The conservation law is: **Complexity in authentication flows is conserved under refactoring. You optimize for which type of bug you're willing to have.**

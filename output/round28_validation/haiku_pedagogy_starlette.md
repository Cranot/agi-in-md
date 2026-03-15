I'm going to apply the **pedagogy lens** from your compression taxonomy here—tracing not what Starlette's code *does*, but what patterns it teaches people to *replicate unconsciously* when they face different problems.

---

## Explicit Choices & Invisible Rejections

| Choice | Made | Rejected Alternative |
|--------|------|---------------------|
| **Eager path compilation** | `compile_path()` at `__init__` → regex + convertor instances | Lazy compilation (defer to first match), runtime-adaptive regex |
| **Linear route precedence** | Iterate routes in order, return first FULL match | Trie-based routing, priority-weighted matching, graph resolution |
| **Mutable scope-dict state passing** | `scope.update(child_scope)` mutates in place | Immutable scope composition, scope stacking, context objects |
| **Ternary match types** | NONE/PARTIAL/FULL enum | Ranked scoring, confidence-based resolution, multi-stage filtering |
| **Parameter convertor coupling** | Convertor instance coupled to path parameter | Separate parse/serialize, external convertor registry, type-based auto-conversion |
| **Sequential scope mutations** | Single coroutine owns scope lifecycle | Concurrent mutation, transactional scope updates |
| **Scope as universal state vehicle** | All routing state (params, endpoint, root_path, router) in dict | Type-safe context objects, closure-captured context |
| **Hierarchical name scoping** | `Mount` creates `:` namespaced routes | Flat global name registry, reverse-route compilation at startup |

---

## The Internalization: GraphQL Resolver Router (Pedagogy Infection)

Someone who internalized Starlette but faces a **different problem** (GraphQL field resolution) would write:

```python
# Antibody: Pattern transfer from HTTP routing to GraphQL resolvers
# (written by someone unconsciously infected by Starlette's design)

class FieldResolver:
    def __init__(self, type_name, field_name, resolver_func, *, middleware=None):
        # CHOICE 1 TRANSFER: Eager compilation
        self.resolver_key = f"{type_name}.{field_name}"  # Eager "path" creation
        self.resolver_func = resolver_func
        
        # CHOICE 7 TRANSFER: Middleware wrapping post-resolution
        self.middleware_stack = resolver_func
        if middleware:
            for cls in reversed(middleware):
                self.middleware_stack = cls(self.middleware_stack)
    
    async def resolve(self, parent, info, **kwargs):
        # CHOICE 8 TRANSFER: Scope-as-dict state passing
        context = dict(info.context)
        context.update({
            "parent": parent,
            "field_name": self.resolver_key,
            "batch_context": info.context.get("batch_context"),
        })
        return await self.middleware_stack(context)


class FieldResolverRegistry:
    def __init__(self):
        # CHOICE 2 TRANSFER: Flat lookup (implicit linear search assumption)
        self.resolvers = {}
    
    async def resolve(self, type_name, field_name, parent, info, **kwargs):
        key = f"{type_name}.{field_name}"
        
        # Linear precedence: exact match first
        if key in self.resolvers:
            return await self.resolvers[key].resolve(parent, info, **kwargs)
        
        # Fallback (like redirect_slashes): fuzzy match
        for reg_key, resolver in self.resolvers.items():
            if matches_fuzzy(reg_key, key):
                return await resolver.resolve(parent, info, **kwargs)
        
        raise FieldNotFound(type_name, field_name)
```

Now add field **batching** (parallel resolution of multiple fields):

```python
async def resolve_batch(self, type_name, fields_dict, parent, info):
    # Context is shared mutable dict across all concurrent resolves
    context = dict(info.context)
    
    tasks = []
    for field_name, kwargs in fields_dict.items():
        key = f"{type_name}.{field_name}"
        resolver = self.resolvers[key]
        
        # SILENT TRANSFER: Each resolver gets same mutable context
        context["current_field"] = field_name  # BUG: Race condition!
        context["batch_id"] = info.context.get("batch_id")
        
        # All tasks share the same context dict
        tasks.append(resolver.resolve(parent, info, **kwargs))
    
    return await asyncio.gather(*tasks)
```

---

## Rejected Alternatives Being Unconsciously Resurrected

When the pattern gets transferred, **the constraints that made the original work become invisible**:

**In Starlette (why it works):**
- One request = one coroutine path = single scope owner
- Sequential dispatch = no concurrent mutation of scope
- Scope updates happen linearly: path match → scope update → handler exec

**In GraphQL resolver variant (why it breaks):**
- Multiple fields resolved in parallel = multiple coroutine paths
- Concurrent mutation of shared `context` dict = race conditions
- Field A updates `context["batch_id"]` while Field B reads it = reads wrong value

```python
# CONCRETE SILENT FAILURE:
async def resolve_user_posts(user, info):
    batch_id = info.context.get("batch_id")  # ← READS WRONG VALUE
    # Meanwhile, another concurrent field updated context["batch_id"]
    # This resolver now fetches the WRONG batch's posts
    return await fetch_posts_for_batch(batch_id)  # Silent data corruption

async def resolve_user_followers(user, info):
    batch_id = info.context.get("batch_id")  # ← OVERWRITES THE VALUE
    info.context["batch_id"] = batch_id + 1  # ← RACE WITH OTHER FIELDS
    return await fetch_followers_for_batch(batch_id)
```

---

## Transferred Patterns & Their Silent Problems

| Pattern | Made Sense In | Transferred To | Silent Problem | Discovery Speed | Trigger |
|---------|---------------|----------------|---|---|---|
| **Eager compilation** | Static HTTP routes (~100-500) | GraphQL schema (10K-100K fields) | Startup bloat on first large schema | SLOW (only at scale) | Schema compilation test |
| **Linear precedence** | Route iteration order predictable | Resolver registration order | Dynamic resolvers never match if catch-all registered first | MEDIUM | "Resolver not called" bug hunt |
| **Mutable scope dict** | Sequential request dispatch | Concurrent field resolution | Context corruption under parallelism | VERY SLOW (intermittent) | Batched resolver test (flaky) |
| **Scope-as-state-vehicle** | ASGI spec design | GraphQL context | Type-unsafe mutations, lost updates | SLOW (silent corruption) | Data inconsistency in resolver output |
| **Hierarchical naming** | HTTP path structure | GraphQL type structure | Type nesting doesn't map to URL-like hierarchy | MEDIUM | Complex type composition fails |

---

## The Pedagogy Law (The Transferred Constraint-as-Assumption)

> **"State can be passed through mutable dictionary mutations on a single shared context object, because request dispatch is sequentially controlled and non-concurrent at the handler level."**

This transfers as a **hidden assumption** to anyone who internalizes Starlette:
- ✅ TRUE in HTTP routing (one request = sequential execution)
- ❌ FALSE in GraphQL batching (multiple fields = concurrent execution)
- ❌ FALSE in distributed routing (scope not mutually accessible)
- ❌ FALSE in message-queue patterns (handlers can't share context)

---

## Which Invisible Transferred Decision Fails First? (And Why Slowest to Discover)

**The failure: Concurrent context mutation under field batching → silent data corruption**

**Why it's FIRST:**
1. Person immediately tries to add batching (standard GraphQL optimization)
2. They inherit Starlette's mutable-context pattern
3. They add `context["batch_id"] = ...` expecting sequential updates
4. It breaks.

**Why it's SLOWEST to discover:**

1. **Intermittent, not deterministic** — Only fails under concurrent load. Sequential tests pass perfectly.

2. **Silent corruption** — No exception. Resolvers return *plausible* data, just *wrong data* from wrong batch.
   ```python
   # Field A wanted batch_id=1 posts, got batch_id=2 posts
   # Field B wanted batch_id=2 followers, got batch_id=1 followers
   # No error raised. Just wrong data returned.
   ```

3. **Blame misdirection** — Stack trace points to the resolver function, not the context layer:
   ```
   File "resolvers.py", line 45, in resolve_user_posts
       return await fetch_posts(batch_id)  # Looks like data fetch bug
   # Actually: context["batch_id"] was overwritten by concurrent field
   ```

4. **Pattern-hiding** — The code LOOKS identical to working Starlette:
   ```python
   context = dict(info.context)  # "Safe copy" like scope is
   context.update({"batch_id": ...})  # Looks like scope update
   # But: returned context is passed to concurrent tasks (not sequential!)
   ```

5. **Coverage gap** — No existing test catches it:
   - Unit tests: Sequential only → passes
   - Integration tests: Single request at a time → passes
   - Concurrency test: Test isolation (one test at a time) → passes
   - Load test: First time data corruption appears, and it's flaky

6. **Third-order symptom** — Data corruption manifests in business logic, not infrastructure:
   ```python
   "User X has Y followers" but Y is from User Z's batch
   # Discovered by QA testing multi-user scenarios
   # Root cause: context mutation in resolver registry
   ```

**Concrete timeline to discovery:**
- **Hour 0**: Add batching. Tests pass. Ship it.
- **Day 1-3**: QA spots data inconsistencies. Assume database bug.
- **Day 4-7**: Database checks out. Assume cache bug.
- **Week 2**: Concurrency specialist finally spots: "Context dict is shared across concurrent tasks."
- **Week 3**: Realize the pattern came from Starlette and doesn't transfer.

---

## The Root Cause (What Makes This Hard to See)

The **pedagogy law transfer** is nearly invisible because:

1. **Starlette's sequential assumption is implicit** — It's not documented. The code works *because* of single-threaded dispatch, but that's never stated.

2. **The pattern looks universal** — "Mutable context dict" feels like a general programming principle, not a domain-specific constraint.

3. **First usage is always sequential** — The person's first attempt (non-batched resolver) works perfectly, reinforcing the pattern.

4. **Concurrency is optional-seeming** — It looks like an optimization added later, not a fundamental incompatibility.

So when they transfer the pattern to GraphQL (where concurrency is **not** optional), they inherit an invisible constraint they never knew existed.

---

**Bottom line:** The fastest-to-fail-and-slowest-to-discover transferred pattern is **mutable shared context under concurrency**, because it silently corrupts data rather than crashing, and the root cause lives in an invisible assumption (sequential dispatch) that was never part of the documented interface.

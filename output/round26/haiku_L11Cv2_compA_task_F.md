# Structure First Analysis: EventBus Conservation Law

## STEP 1: The Falsifiable Claim

**Primary Claim:**
The code assumes event-type is a sufficient routing discriminator, making it impossible to express conditional handler applicability based on payload context. Once registered for a type, handlers execute unconditionally, forcing conditional logic into handlers themselves or scattering it across emit() call sites.

**Why falsifiable:**
- Test: Can you register a handler that skips itself conditionally? No. The code provides no mechanism.
- Verify: Examine real usage—handlers must introspect payloads, creating impurity.
- Demonstrate: Show that type-only routing fails for common patterns (routing based on user role, company, state).

---

## STEP 2: Three Experts Test It

**DEFENDER:** "This is clearly the problem. I want a UserCreated event to trigger different handlers based on the user's tier or company—but the bus doesn't let me express that. I have to either write a mega-handler with if/else logic, or create separate event types for different user categories, which defeats the purpose."

**ATTACKER:** "You're wrong about the priority. The real problem is that dead-letter captures both 'no handlers found' and 'handler threw an exception' identically, which means you can't distinguish infrastructure failures from logic failures. Also, you haven't shown that conditional routing is actually the blocking issue—maybe handlers are *supposed* to be simple and the complexity belongs elsewhere."

**ASSUMPTION-PROBER:** "The claim assumes handlers should be conditional. But what if the design is right and the problem is that you're trying to send the same event to different decision trees? The real issue might be that you're over-coupling by sending one UserCreated event to N different contexts. Maybe the system should send different events: UserCreated_Internal, UserCreated_External."

**THE GAP:** Between "the code prevents conditional handler expression" (primary claim) and "the code forces you to pre-discriminate events at the source" (prober's reframing), revealing that the problem isn't the bus's inability—it's the assumption that event routing should be centralized rather than pushed to event emission time.

---

## STEP 3: The Concealment Mechanism

**Name: Simplicity-as-Completeness**

The code conceals its limitation through three layers:

1. **Architectural Invisibility**: Type-based routing is so standard that it feels like the only possibility, not a choice. The code doesn't say "we route by type"; it just does it, making the assumption seem inevitable.

2. **Dead-Letter Mirage**: The dead-letter queue creates the illusion of failure management (something is being "handled") without providing recovery logic. Failures are visible but not actionable.

3. **Handler-Level Escape Hatch**: Because handlers can introspect the context, handlers can *add* conditional logic themselves. This makes the routing system seem flexible in practice, concealing that the flexibility is local and scattered, not systemic.

---

## STEP 4: Deepen the Concealment (Improvement That Passes Review)

```python
class EventBus:
    def __init__(self):
        self._handlers = {}
        self._middleware = []
        self._dead_letter = []
        self._handler_metadata = {}  # DECEPTIVE: looks like we understand handlers
        self._event_filters = {}      # DECEPTIVE: looks like we support conditions

    def on(self, event_type, handler, priority=0, name=None):
        """Register handler with metadata."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        handler_id = name or handler.__name__
        self._handlers[event_type].append((priority, handler))
        self._handlers[event_type].sort(key=lambda x: -x[0])
        # DECEPTIVE: Storing metadata that we never use
        self._handler_metadata[(event_type, handler_id)] = {
            "handler": handler,
            "registered_at": __import__('datetime').datetime.now(),
            "call_count": 0
        }

    def set_filter(self, event_type, filter_fn):
        """DECEPTIVE: Looks like conditional routing, but filter_fn runs AFTER handler selection."""
        self._event_filters[event_type] = filter_fn

    def use(self, middleware_fn):
        self._middleware.append(middleware_fn)

    def emit(self, event_type, payload):
        context = {
            "type": event_type,
            "payload": payload,
            "cancelled": False,
            "handler_count": 0  # DECEPTIVE: observability that doesn't help
        }

        for mw in self._middleware:
            context = mw(context)
            if context.get("cancelled"):
                return context

        handlers = self._handlers.get(event_type, [])

        if not handlers:
            # DECEPTIVE: Detailed logging that makes failure feel managed
            self._dead_letter.append({
                **context,
                "failure_type": "NO_HANDLERS_REGISTERED",
                "event_type": event_type
            })
            return context

        results = []
        for _, handler in handlers:
            try:
                result = handler(context)
                # DECEPTIVE: Running filter AFTER selection, not BEFORE
                if event_type in self._event_filters:
                    if not self._event_filters[event_type](result):
                        continue  # Skip result, but handler already ran
                results.append(result)
                context["handler_count"] += 1
            except Exception as e:
                context["error"] = e
                context["failure_type"] = "HANDLER_EXCEPTION"
                self._dead_letter.append(context)

        context["results"] = results
        return context

    def get_handler_stats(self, event_type):
        """DECEPTIVE: Observability that suggests we understand the system."""
        return self._handler_metadata.get(event_type, {})
```

**Why this passes review:**
- Handler metadata, observability, statistics—looks professional
- Filter mechanism suggests we now support conditional logic
- Better error categorization
- Handler naming and tracking

**Why it deepens the concealment:**
- The `set_filter` runs AFTER handler selection/execution, making it performant but useless for routing
- The `_handler_metadata` is updated but never used for actual decisions
- The statistics create illusion of understanding without enabling action
- Now someone reading the code might think "oh, filters exist" without realizing they don't prevent handler execution, only filter results

---

## STEP 5: Three Properties Visible Only Through This Attempt

1. **The Temporal Asymmetry of Handler Selection**: The metadata tracks registration time and call count, but this information CANNOT affect which handlers run—selection is purely type-based. This reveals that the code treats registration as immutable event-routing information, making handler introspection at emit-time impossible.

2. **The Filtering-Execution Inversion**: By trying to add filtering via `set_filter`, we expose that the code structure makes pre-filtering impossible without restructuring. Filters must run post-execution, which means "conditional" execution is actually "optional result inclusion."

3. **The Unreachable Metadata Problem**: We store detailed metadata but have no way to use it. This reveals the fundamental issue: the code has no language for expressing "run this handler only if X"—metadata gathering and decision-making are not connected.

---

## STEP 6: Diagnostic Applied to the Improvement

**What does it conceal?**
It conceals that `set_filter` is a false solution. It looks like it addresses conditional routing, but it only filters results, not execution. The handler still runs, wastes resources, and might have side effects.

**What property of the original is visible only because the improvement recreates it?**
The original's hard truth: once you call `handler(context)`, it runs. Full stop. The improved version pretends filters prevent this, but they don't. The original was at least honest—if you registered a handler, it would run. The improved version lies about having conditional execution.

**Critical insight**: The original design is MORE truthful about its limitations than the "improved" version.

---

## STEP 7: Second Improvement (Addressing the Honesty Problem)

```python
class EventBus:
    def __init__(self):
        self._handlers = {}      # event_type -> [(priority, condition_fn, handler)]
        self._middleware = []
        self._dead_letter = []

    def on(self, event_type, handler, condition=None, priority=0):
        """
        condition: (event_type, payload) -> bool
                   If None, always matches. If provided, must return True to execute.
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        # Store condition WITH handler, making the relationship explicit
        self._handlers[event_type].append((priority, condition or (lambda *_: True), handler))
        self._handlers[event_type].sort(key=lambda x: -x[0])

    def use(self, middleware_fn):
        self._middleware.append(middleware_fn)

    def emit(self, event_type, payload):
        context = {"type": event_type, "payload": payload, "cancelled": False}

        for mw in self._middleware:
            context = mw(context)
            if context.get("cancelled"):
                return context

        handlers = self._handlers.get(event_type, [])

        if not handlers:
            self._dead_letter.append(context)
            return context

        results = []
        for priority, condition, handler in handlers:
            # HONEST: Evaluate condition BEFORE calling handler
            if not condition(event_type, payload):
                # Handler simply doesn't match—not an error
                continue
            try:
                results.append(handler(context))
            except Exception as e:
                context["error"] = e
                self._dead_letter.append(context)
                return context

        context["results"] = results
        return context
```

**Why this is more honest:**
- Conditions are explicit and evaluated before handler execution
- "Not matching" is not an error—it's expected
- There's no pretense of filtering results post-execution
- The mechanism is simple and clear

---

## STEP 8: Apply Diagnostic to Second Improvement

**What does it conceal?**
It conceals that condition evaluation has performance cost and side effects. What if a condition throws? What if conditions overlap and their ordering matters? The code evaluates conditions sequentially by priority—what if a condition depends on whether a previous handler ran?

**What property of the original is visible only because the improvement recreates it?**
The original's assumption that handlers are independent. By adding conditions, we've exposed that handlers have implicit dependencies:
- Condition A might depend on whether handler B ran
- Conditions might be stateful
- The evaluation order of conditions affects which handlers run

The original code was clear: "handlers run in priority order, no dependencies." The improved version suggests independence while actually creating it.

---

## STEP 9: Apply Diagnostic Again

**The new hidden assumption**: Conditions are PURE FUNCTIONS. If a condition returns True once, it should always return True for the same inputs. But what if a condition like `user.has_premium_subscription()` depends on external state?

The code now assumes that `(event_type, payload)` provides sufficient information for all conditions, but conditions might need access to:
- Current time
- User identity
- Database state
- Other events that have fired

This reveals that the original code's simplicity was actually encoding a real constraint: "routing decisions should depend only on the event itself."

---

## STEP 10: The Structural Invariant

**What persists across all three versions?**

Not the mechanisms—they differ completely.

The invariant is: **The system assumes that handler selectivity can be computed from (event_type, context). Whether we use type-only, conditions, or filters, we always assume the same information is available at selection time.**

More precisely: **Every version assumes that by the time we reach the handler-selection decision point, we have all the information needed to make it. No version supports "lazy" conditions that require handler-specific knowledge, or "dynamic" conditions that evolve as handlers execute.**

Even more fundamentally: **The invariant is that handler execution is a pure function of the event. Change the event, change which handlers run. But the system never models: handlers that affect which other handlers should run, conditions that depend on previous handler outcomes, or routing decisions that require consensus among handlers.**

---

## STEP 11: Invert It

What if we inverted this: what if handler execution is NOT a pure function of the event, and what if later handlers CAN affect whether earlier handlers should have run?

```python
class DependentEventBus:
    """Inversion: handlers can declare dependencies and affect routing decisions."""
    
    def __init__(self):
        self._handlers = {}
        self._handler_results = {}  # Store results so dependencies can access them

    def on(self, event_type, handler, depends_on=None):
        """
        handler: (event_type, payload, dependency_results) -> Result
        depends_on: List of handler names this depends on
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append({
            "name": handler.__name__,
            "fn": handler,
            "depends_on": depends_on or []
        })

    def emit(self, event_type, payload):
        handlers = self._handlers.get(event_type, [])
        executed = {}
        
        # Topological sort based on dependencies
        def execute_with_deps(handler_spec, visited=None):
            visited = visited or set()
            if handler_spec["name"] in visited:
                return
            visited.add(handler_spec["name"])
            
            # Execute dependencies first
            for dep_name in handler_spec["depends_on"]:
                dep_handler = next((h for h in handlers if h["name"] == dep_name), None)
                if dep_handler:
                    execute_with_deps(dep_handler, visited)
            
            # Now execute this handler, giving it access to dependency results
            try:
                result = handler_spec["fn"](
                    event_type,
                    payload,
                    {name: executed.get(name) for name in handler_spec["depends_on"]}
                )
                executed[handler_spec["name"]] = result
            except Exception as e:
                executed[handler_spec["name"]] = {"error": e}
        
        for handler_spec in handlers:
            execute_with_deps(handler_spec)
        
        return {"executed": executed}
```

**What becomes trivial:**
- Handlers declaring "I need this other handler's result"
- Handlers being skipped because their dependencies failed
- Complex routing based on previous handler outcomes

**What becomes impossible:**
- Simple, predictable execution order
- The guarantee that "all handlers for a type will run"
- Fire-and-forget semantics (you must now wait for dependencies)
- Easy reasoning about handler independence

---

## STEP 12: The New Impossibility

**Original**: Impossible to express "run handler B only if handler A succeeded"

**Inverted**: Impossible to guarantee "all registered handlers for this event type will execute" (some might not run due to failed dependencies)

---

## STEP 13: The Conservation Law (The Real Finding)

This is NOT "expressivity vs. predictability"—that's too obvious and already known.

The deeper law:

**In any routing architecture, you cannot simultaneously have:**
1. **Static routing** (decisions made at registration time, deterministic execution)
2. **Dynamic routing** (decisions made at execution time, based on event content)
3. **Handler autonomy** (handlers don't depend on each other's outcomes)

**You must sacrifice one. The original code sacrifices (2). The second improvement sacrifices (3). The inverted design sacrifices (1).**

But there's something even deeper:

---

## STEP 14: What This Reveals Beyond Senior-Engineer Knowledge

Most engineers know about trade-offs. But this reveals something about the **NATURE OF ROUTING DECISION RIGHTS**:

**Every routing architecture is actually a statement about WHO DECIDES which handlers run:**

- **Original**: The code decides (at registration time: if event_type matches, run it)
- **With conditions**: The event content decides (at emit time: payload determines execution)
- **With dependencies**: Previous handlers decide (at runtime: outcomes determine whether later handlers run)

**The conservation law is actually: You cannot distribute decision-making authority without losing determinism.**

The deeper insight: **Every improvement toward "flexible routing" is actually a migration of authority from the code to the context (payload) to the handlers themselves. But authority and predictability are inversely correlated. As you give handlers more say in the routing decision, the system becomes less predictable, and you need observers (humans, monitoring) to understand what will execute.**

This means:
- Teams that want flexibility are actually asking for distributed authority → they'll need observability
- Teams that want determinism are asking for centralized authority → they can sacrifice flexibility
- You cannot have both flexibility AND predictability simultaneously

**What senior engineers usually miss**: They think "we'll use conditions, that's a middle ground." But conditions don't give you a middle ground—they just move the decision point from registration time to emit time. You've traded static predictability for dynamic flexibility, and you'll pay for that in observability costs.

---

## STEP 15: Prediction About the Third Design

Given this conservation law (flexibility ↔ predictability via authority distribution), what would a third design attempt?

**The Inevitable Third Design: Typed, Immutable Event Queues**

```python
class TypedEventQueue:
    """No routing decisions. Just queuing."""
    
    def __init__(self):
        self._queues = {}  # event_type -> list of (timestamp, event)
        self._consumers = {}  # event_type -> consumer_fn
    
    def subscribe(self, event_type, consumer):
        """One consumer per type. Period."""
        if event_type in self._consumers:
            raise ValueError("Already subscribed")
        self._consumers[event_type] = consumer
    
    def emit(self, event_type, payload):
        """Just queue it. Consumers are responsible for polling/pulling."""
        if event_type not in self._queues:
            self._queues[event_type] = []
        self._queues[event_type].append((time.time(), payload))
    
    def process_queue(self, event_type, batch_size=100):
        """Consumer calls this to get events to process."""
        if event_type not in self._consumers:
            raise ValueError("Not subscribed")
        
        queue = self._queues.get(event_type, [])
        batch = queue[:batch_size]
        
        results = []
        for timestamp, payload in batch:
            try:
                result = self._consumers[event_type](payload)
                results.append({"status": "ok", "result": result})
            except Exception as e:
                results.append({"status": "error", "error": e})
        
        # Remove processed items
        self._queues[event_type] = queue[batch_size:]
        
        return results
```

**Prediction**: This design eliminates the routing decision problem entirely by eliminating routing. But it:
- Requires explicit polling (pull, not push)
- Can't express overlapping handlers (one consumer per type)
- Moves complexity to the consumer (who decides what to process)
- Trades routing simplicity for consumer complexity

**What the conservation law predicts**: This design will be adopted by teams that value predictability over convenience. It will be criticized as "not a real event bus" because it requires explicit polling. Teams building push-based event systems will reject it as "too low-level."

But here's the key: **The third design doesn't escape the conservation law—it just makes authority distribution VISIBLE rather than hidden.** Instead of asking "which handlers run?", it asks "who pulls the queue?" Authority is now explicitly in the consumer's hands, making the lack of centralized routing obvious.

---

## The Conservation Law (Final Statement)

**Across all three designs, a structural invariant persists: The more flexible the routing, the less predictable the execution. The conservation is between AUTHORITY DISTRIBUTION (who decides which handlers run?) and EXECUTION PREDICTABILITY (can I know in advance what will happen?).**

**What this predicts about systems you haven't built yet**: Any event-driven system will eventually hit a limit where further flexibility requires giving up on predictability. At that point, teams typically diverge into two strategies:**

1. **Accept the flexibility and invest in observability** (monitoring, dead-letter analysis, debugging tools)
2. **Accept the constraints and invest in discipline** (strict event schemas, one consumer per type, explicit dependencies)

**Teams rarely try to do both**, which is why most event systems feel like they're fighting against their own architecture. The system wants you to pick: flexibility or predictability. The conservation law shows why you can't have both—not as a limitation, but as a fundamental property of information flow.

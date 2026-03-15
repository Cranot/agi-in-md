# Structural Diagnosis: The EventBus

## INITIAL FALSIFIABLE CLAIM

**"The deepest structural problem is this code implements sequential broadcasting with implicit error logging, but uses vocabulary from pipeline orchestration frameworks—creating polyphonic semantics where each component makes local sense but globally they conflict."**

Specifically:
- **Handlers** pretend to be independently orchestrated (via priority), but all execute equally
- **Middleware** pretends to control flow (via `cancelled`), but handlers receive mutated state and execute anyway  
- **Dead letter** conflates "no handlers found" with "handler threw," preventing introspection
- **Exception handling** logs-in-the-middle-of-execution rather than handling errors

This is falsifiable: prove that handler order affects behavior, or dead letter entries *do* distinguish failure modes, or the mutable context enables patterns impossible otherwise.

---

## THREE EXPERTS TEST THE CLAIM

### DEFENDER (Supports it)
"Exactly. Priority is purely cosmetic—it orders execution but never prevents execution. That's not orchestration.

The dead letter is incoherent. Line `self._dead_letter.append(context)` fires both when no handlers exist AND when a handler throws. These are categorically different: one is 'no one subscribed,' the other is 'someone tried and failed.' But downstream code sees identical entries.

The mutable dict is the tell: middleware adds `context['cancelled']`, exception handlers add `context['error']`, the emitter adds `context['results']`. There's no contract. Each layer is mutating a shared grab-bag. This isn't composition—it's collaborative corruption of state."

### ATTACKER (Challenges it)
"You're conflating simplicity with brokenness. Priority DOES matter: if early handlers populate context, later handlers see that state. Different handlers behave differently based on what earlier handlers did. That's behavioral orchestration.

Dead letter conflating entry types isn't 'incoherent'—it's 'simple.' You can introspect `context['results']` to tell them apart. The code follows Python patterns; Flask middleware works exactly like this.

The real issues are narrower: (1) no `on_error` strategies per-handler, (2) results array doesn't track which handler produced which result, (3) no recovery semantics. These are implementation gaps, not architectural contradictions."

### PROBER (Tests both)
"You're both assuming this is a *pipeline* problem—routing work through stages. But look at the actual use case: it's a *broadcaster*. Multiple handlers are independent subscribers. They all run. Period.

That's incompatible with how you're both talking about 'control flow.' In pipelines, exceptions stop the flow. In broadcasts, exceptions are side-effects. 

Here's what you're both taking for granted: **the code treats all handlers equally (broadcast semantics) but tracks failures globally in dead_letter (consensus/command semantics—'all must succeed').** These are inimical. You can't broadcast a notification AND require unanimous success.

The vocabulary (handlers, priority, error) works locally within each semantic model but breaks down at their intersection. The real problem isn't the features—it's the code doesn't *know* which failure model it's implementing."

---

## THE TRANSFORMATION

| Phase | Framing |
|-------|---------|
| **Original claim** | Misnamed orchestration + bad error handling |
| **After defender** | Each feature locally sensible but mutually destructive |
| **After attacker** | Implementation gaps, not architecture gaps |
| **After prober** | Two incompatible broadcast models simultaneously active |

**The gap itself is diagnostic:** The claim evolved from "wrong naming" → "implementation sloppiness" → **"latent semantic conflict"**. This gap reveals what the code is *actually* hiding.

---

## THE CONCEALMENT MECHANISM

**Name: "Polyphonic Semantics via Vocabulary Colonization"**

The code borrows terminology from established frameworks (handlers → Express.js, middleware → Django, priority → Celery), which creates *borrowed credibility*. Each reader's brain fills in the expected semantics from frameworks they know.

- You read `handler` → your brain fills in "endpoint logic"
- You read `priority` → your brain fills in "execution precedence"  
- You read `dead_letter` → your brain fills in "retry queue"

But this code implements:
- Handlers as "indiscriminate subscribers"
- Priority as "read-only ordering metadata"
- Dead letter as "exception graveyard"

**The concealment works because the gap is never visible within a single function.** Each method makes local sense. It's only at the boundary—when dead_letter receives both "no handlers" and "handler failure" entries—that the incoherence appears. By then the code "already works" in some tests.

---

## LEGITIMATE IMPROVEMENT THAT DEEPENS THE CONCEALMENT

Add a feature that looks like it fixes error semantics but actually hides the model conflict:

```python
class EventBus:
    def __init__(self):
        self._handlers = {}
        self._middleware = []
        self._dead_letter = []
        self._error_policies = {}  # NEW
        
    def on(self, event_type, handler, priority=0, error_policy='deferred'):
        """error_policy: 'deferred' (continue others), 'fail-fast' (stop), 'ignore' (silent)"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append((priority, handler, error_policy))
        self._handlers[event_type].sort(key=lambda x: -x[0])

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
        for _, handler, error_policy in handlers:
            try:
                results.append(handler(context))
            except Exception as e:
                context["error"] = e
                if error_policy == 'fail-fast':
                    self._dead_letter.append(context)
                    return context  # NEW: actually stop
                elif error_policy == 'ignore':
                    pass  # NEW: skip dead letter
                else:  # deferred
                    self._dead_letter.append(context)
        
        context["results"] = results
        return context
```

**Why this passes code review:**
- ✅ Solves the "all handlers run on error" complaint
- ✅ Adds per-handler error semantics (looks like resilience patterns)
- ✅ Backward compatible (deferred is default)
- ✅ Enterprise-looking (three error strategies)
- ✅ Small, safe diff

---

## THREE PROPERTIES REVEALED ONLY BY ATTEMPTING TO STRENGTHEN IT

### 1. **The Lost Distinction Between Failure Modes**

With error policies, we can now stop on error (`fail-fast`), skip on error (`ignore`), or log-and-continue (`deferred`).

But this reveals the original code was **always choosing one of these strategies for each failure type**, just implicitly:
- No handlers found? → Always deadletter (log-and-continue at the event level)
- Handler throws? → Always deadletter **and continue other handlers** (log-and-continue at the handler level)

Now with explicit policies, you can ask: **"Should 'fail-fast' mean stop other handlers from running, or stop and deadletter, or stop and *remove the context from dead_letter*?"** 

The improvement reveals that "failure" was never a unified concept. An exception at handler 3 has different semantics than "no handlers registered at all," but both end up in dead_letter. The error_policy feature makes this visible because now you have to ask *which handler's policy applies* and *what does 'fail-fast' fail against*? The answers don't fit the model.

### 2. **The Semantic Drift of Continuation**

When you set `error_policy='deferred'`, you're saying "continue with other handlers." 

But the original code was ALREADY continuing after exceptions—that wasn't configurable, it was forced. The improvement reveals that "deferred" doesn't mean what handlers think it means:

- Handler A throws → deadletters → Handler B runs anyway → deadletters too
- Handler A throws with `error_policy='deferred'` → deadletters → Handler B runs anyway

They're identical. So what does the `error_policy` actually control? Only whether we *log* the error to dead_letter. But handlers can't *see* the policy decision. They execute atomically—throw or succeed, no middle ground.

**This reveals the code conflates "handler policy" with "system policy."** A handler's error_policy determines whether *the event bus* logs it, not whether the handler behaves differently. The improvement makes visible that there's an uncrossable gap: handlers execute as pure side-effects; the event bus just logs them. These aren't negotiating about failure—they're in separate failure domains.

### 3. **The Invisibility of the Second Error Path**

Before the improvement: exceptions go to dead_letter within the try/except block.

After the improvement: exceptions might go to dead_letter (deferred, ignore) or might return early (fail-fast), which *also* goes to dead_letter.

Now you can ask: **"Why does fail-fast deadletter at all? Shouldn't it throw?"**

The answer reveals the real problem: **there are two error paths in this code but only one error model.**

- **Path A (implicit):** Handler throws → exception is caught → logged to dead_letter → execution continues
- **Path B (now explicit):** Handler throws with fail-fast → exception is caught → logged to dead_letter → execution stops

Both hit dead_letter. But "fail-fast" should mean "fast failure propagation," which means handlers downstream shouldn't run AND the caller should know something went wrong. Instead, fail-fast just makes dead_letter contain context and stops execution. 

The caller sees:
```python
result = bus.emit('order_placed', order_data)
# Is result['results'] empty because fail-fast, or because no handlers, or because success?
```

The improvement reveals that dead_letter isn't an error channel—it's a *side-effect log*. It logs whether execution continued, not whether something failed. Error policies can't actually change failure semantics because failure isn't a first-class concept in the model—it's just "an exception happened" vs. "no exception happened."

---

## SYNTHESIS: The Hidden Architecture

The improvement attempt reveals the EventBus actually implements this:

```
Sequential Executor with Side-Effect Logging
│
├─ All handlers are equal subscribers (broadcast semantics)
├─ Execution is linear and deterministic (all or stop-early)
├─ Exceptions are treated as state mutations, not control flow
└─ Dead letter is not "error handling"—it's a forensic log
```

But it's disguised as:
```
Orchestrated, Prioritized, Middleware-Composable Event Handler
with Error Recovery and Failure Handling
```

The gap between those two descriptions is where the code hides: in vocabulary realism, in borrowed credibility, and in the fact that "it mostly works" for simple broadcast use cases (fire an event, let many things happen).

The improvement deepens the concealment because it makes it *syntactically* possible to *express* the semantic model you wish existed (prioritized handlers, fail-fast strategies, error recovery) without making it *behaviorally* possible for those models to actually work. You can now write code that looks correct while being semantically incoherent.

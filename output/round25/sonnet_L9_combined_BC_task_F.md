# EventBus: A Counter-Recursive Structural Analysis

## I. The Falsifiable Claim

**The deepest structural problem**: `context` is a mutable shared dictionary that flows through middleware, handlers, and dead-letter storage simultaneously — every processing stage reads and writes the same object, so the bus has no stable identity boundary between stages, making local correctness reasoning impossible.

This is falsifiable: show me one path through `emit()` where a component's behavior cannot be altered by another component it has no knowledge of.

---

## II. Three Experts Attack the Claim

### Expert A — Defender
The claim holds. The smoking gun is:

```python
except Exception as e:
    context["error"] = e          # mutates context
    self._dead_letter.append(context)  # appends live reference, not snapshot
```

`_dead_letter` contains live references. Any subsequent mutation of `context` — including `context["results"] = results` — retroactively modifies what's already been "stored." The dead-letter queue is lying about its contents. The mutable shared object is the load-bearing flaw.

### Expert B — Attacker
Too narrow. The mutation is a symptom. The real disease: `_dead_letter` catches two categorically different failures jammed into one list:

```python
if not handlers:
    self._dead_letter.append(context)   # routing failure: no subscriber
    return context
# ...
    self._dead_letter.append(context)   # runtime failure: handler crashed
```

Fix mutability and you still have a system that cannot distinguish "no one wanted this" from "someone tried and failed." These require different remediation paths. The semantic incoherence is the deeper problem.

### Expert C — Probe
Both of you assume this bus *should* decouple producers from consumers. But `emit()` returns `context` containing `results`. The caller inspects handler return values synchronously. This isn't pub/sub — it's **routed procedure call**. If callers depend on `context` mutability to coordinate handlers (a pipeline model), then "shared mutable context" is a feature, not a bug. What you both take for granted: *this system has a coherent model of what it is*. It may not.

---

## III. The Transformed Claim

| | Claim |
|---|---|
| **Original** | Mutable shared context is the deepest structural problem |
| **Transformed** | The bus has no committed execution model; mutable shared context is the physical artifact of that non-commitment |

**The gap is diagnostic**: I started at the implementation and ended at an absent architectural decision. That gap reveals the concealment mechanism.

---

## IV. The Concealment Mechanism: Plausible Completeness

The code possesses architectural vocabulary without architecture:

| Feature | Signal it sends | What it conceals |
|---|---|---|
| `_middleware` | Extensibility discipline | No contract on what middleware may modify |
| `priority=0` | Ordering model | Handlers share context; order creates hidden dependencies |
| `_dead_letter` | Reliability engineering | Two failure modes, one queue, zero distinction |
| `try/except` | Fault tolerance | Exceptions mutate the live context before it's "stored" |

Each feature was added to solve a local problem. Together they create the appearance of mature design. The machinery is elaborate enough that reviewers keep fixing implementation details instead of asking: *what is this thing's contract?*

---

## V. Improvement 1 — Deepens the Concealment

**Copy-on-write isolation**: each handler receives an independent snapshot.

```python
import copy

def emit(self, event_type, payload):
    context = {"type": event_type, "payload": payload, "cancelled": False}
    
    for mw in self._middleware:
        context = mw(copy.copy(context))   # middleware gets a fresh copy
        if context.get("cancelled"):
            return context
    
    handlers = self._handlers.get(event_type, [])
    if not handlers:
        self._dead_letter.append(copy.copy(context))  # stable snapshot
        return context
    
    results = []
    for _, handler in handlers:
        handler_ctx = copy.copy(context)              # each handler isolated
        try:
            results.append(handler(handler_ctx))
        except Exception as e:
            err_ctx = copy.copy(handler_ctx)
            err_ctx["error"] = e
            self._dead_letter.append(err_ctx)         # stable error snapshot
    
    context["results"] = results
    return context
```

This **passes review** because it fixes a real bug (live reference in dead-letter), uses a recognized pattern, and isolates handler failures.

**Why it deepens concealment**: By eliminating the most visible problem, it makes the system look more professional. Trust increases. The contract confusion is untouched — in fact reinforced, because the fix commits silently to the observer model without documenting it. The code now more confidently does one thing when callers may need it to do another.

---

## VI. Three Properties Visible Only Because You Tried to Strengthen It

1. **Handler isolation and handler coordination are mutually exclusive, and the original code supported both simultaneously.** Applying copy-on-write reveals that handlers could previously communicate through shared `context` mutations — a pipeline. The improvement breaks that channel without documentation, proving it existed.

2. **`results` was only half the return mechanism.** Handlers communicated outcomes via both return values (captured in `results`) and context mutations (now eliminated). The improvement reveals a hidden API that was in use.

3. **Dead-letter's false homogeneity becomes invisible.** Making all dead-letter entries consistent snapshots makes it *easier* to miss that they remain categorically different (routing failure vs. runtime failure). The improvement creates structural uniformity that conceals semantic divergence.

---

## VII. Improvement 2 — Contradicts Improvement 1

**Explicit pipeline threading**: handlers share and transform a single context.

```python
def emit(self, event_type, payload):
    context = {
        "type": event_type, "payload": payload,
        "cancelled": False, "results": []
    }
    
    for mw in self._middleware:
        context = mw(context)
        if context.get("cancelled"):
            return context
    
    handlers = self._handlers.get(event_type, [])
    if not handlers:
        self._dead_letter.append({"failure": "routing", **context})  # typed
        return context
    
    for _, handler in handlers:
        try:
            result = handler(context)
            context["results"].append(result)
            context["last_result"] = result        # explicit pipeline state
        except Exception as e:
            self._dead_letter.append({
                "failure": "runtime",
                "error": str(e),
                **context
            })
            # continue — remaining handlers may still succeed
    
    return context
```

This **also passes review** because: pipeline threading is a recognized pattern (Express.js, etc.), dead-letter entries are now disambiguated (routing vs. runtime — fixing Expert B's objection), and resilience across handler failures is often the correct behavior.

---

## VIII. The Structural Conflict

**The conflict exists only because both improvements are legitimate.**

| | Improvement 1 | Improvement 2 |
|---|---|---|
| **Execution model** | Each handler is an independent observer | Handlers form a sequential pipeline |
| **Context ownership** | Copied per-handler | Shared and mutated |
| **Handler communication** | Impossible (by design) | Via `last_result`, `payload` mutations |
| **Dead-letter semantics** | Uniform error snapshots | Typed by failure category |
| **Breaking change** | Yes — silently removes pipeline capability | Yes — silently removes isolation |

These cannot coexist. They require the bus to take a position it has never taken. **The conflict only exists because the original code never chose** — it supported both models through productive ambiguity.

---

## IX. The Recursive Application: What Does the Conflict Itself Conceal?

### What the conflict conceals
The observer-vs-pipeline conflict is only possible inside a genuine pub/sub system. But `emit()` returns `context["results"]` — the caller inspects handler outputs synchronously. This is not publish-subscribe. **This is routed procedure call.**

In real pub/sub, producers don't care about results. Here the caller can inspect everything every handler returned. The architectural vocabulary says "event bus"; the return signature says "RPC router."

The conflict between two valid bus designs conceals that neither design fully applies — *because the thing isn't actually a bus*.

### The property of the original problem now visible

The original claim was "no coherent contract." The conflict recreates that problem at a higher level: even after you try to impose a contract, two contradictory valid contracts emerge. This reveals the problem is not "the wrong contract was chosen" — it's that **the system's callers are using it for purposes that require contradictory contracts simultaneously**.

The evidence is the dead-letter queue. In the observer model, it captures failed independent observations. In the pipeline model, it captures broken pipeline stages. These require different remediation strategies. One queue cannot serve both purposes. 

**The dead-letter queue is where the two usage patterns meet and destroy each other's coherence** — and it was there from the start, quietly accumulating the evidence of the collision.

---

## Summary Table

| Layer | Problem | Concealed by |
|---|---|---|
| Implementation | Mutable shared `context` | Exception handling looks like fault tolerance |
| Architecture | No execution model commitment | Middleware + priority + dead-letter look like design |
| Contract | Observer vs. pipeline — unresolved | Both are legitimate; conflict only visible when you choose |
| Identity | Not actually a bus | Synchronous result collection hidden behind event vocabulary |
| Evidence | Dead-letter queue semantic collision | Structural uniformity (Improvement 1) masks categorical divergence |

The code's real problem is visible only at the last row — and it's only visible because the dead-letter queue had to survive two contradictory improvements simultaneously.

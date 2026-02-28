# EventBus: A Meta-Causal Analysis

## The Falsifiable Claim

> **The deepest structural problem is that `context` is a schemaless mutable dict that simultaneously plays three incompatible semantic roles: transport vehicle, accumulation register, and audit log — with no separation between them.**

This is falsifiable: fix the role separation and the majority of observable bugs dissolve without touching any other line.

---

## The Dialectic

### Expert A — Sarah (Distributed Systems Engineer): Defends

> "Shared mutable context is intentional. It's the Express.js `req/res` model, which runs half the internet. Middleware *annotating* context — adding an authenticated user, a request ID, a cached result — is the entire value proposition. Your claim confuses *mutation* with *aliasing problems*. These are different bugs."

She's right that mutation is load-bearing. The claim must sharpen.

---

### Expert B — Marcus (Correctness Researcher): Attacks

> "Sarah proves the claim by defending the wrong thing. Express works because `req` and `res` are *separate objects with clear directionality*. Here there's ONE dict flowing everywhere. Look at the exception handler:"

```python
except Exception as e:
    context["error"] = e          # overwrites any previous error
    self._dead_letter.append(context)  # stores post-mutation state, not original event
```

> "Handler 3 throws. It overwrites handler 1's error. The dead_letter queue now contains a context that has been *partially processed by all preceding handlers*. You cannot reconstruct what the original event was, what succeeded, or what failed. This isn't just a bug — it's an **epistemic failure**. The system cannot reason about its own history."

The claim evolves: it's not just mutation — it's that mutation **destroys the causal record**.

---

### Expert C — Yuki (Philosophy of Software Design): Probes Assumptions

> "You're both debating mutation. Neither of you has asked: *why is context a dict?* A dict has no schema, no validation, no defined interface. Sarah's Express analogy fails precisely here — Express has documented properties, typed methods, a defined contract. Here, `context` is epistemic noise. The structural problem isn't mutation — it's that mutation is **unconstrained because there is no type system enforcing what context can contain**. You can't fix the dead-letter corruption without first answering: what is a context *allowed to be*?"

---

## The Transformed Claim

The argument moved from:

| Stage | Claim |
|-------|-------|
| Initial | "Shared mutable context" |
| After Sarah | "Uncontrolled mutation" |
| After Marcus | "Mutation that destroys causal record" |
| After Yuki | **"Schemaless context collapses transport, accumulation, and audit into one untyped blob"** |

---

## The Structural Force That Shaped This Dialectic

The dialectic did **not** drift toward "add async," "fix the unbounded dead-letter queue," or "remove the O(n log n) sort on registration." It moved toward **"what IS this object?"**

The force that caused this:

> ### Role Collapse
> `context` is simultaneously the **transport vehicle** (carries payload between hops), the **accumulation register** (handlers write results into it), and the **audit log** (errors and dead letters reference it). Three roles, one object, zero separation.

When Sarah defended it, she was defending its **transport role**. When Marcus attacked it, he was attacking its **audit role**. When Yuki probed, she found the missing schema because the **accumulation role** has no contract.

Every expert found a different failure *because the object is trying to be three different things*. The dialectic had to converge on ontology — *what is this thing* — because the object itself refuses to answer.

---

## The Predicted Next Problem

**Handler execution order will become load-bearing for correctness in a way that is invisible in the code.**

Because context is mutable and shared, later handlers implicitly depend on mutations made by earlier ones. Today, someone adds a middleware that reads `context['user']`. An auth middleware sets it. This works.

Next month, the auth middleware is refactored to set `context['authenticated_user']` instead. Everything silently breaks — not with an exception, but with `None` propagating through business logic. The invariant *"auth runs before enrichment, and enrichment reads `context['user']`"* was real and load-bearing, but it existed nowhere in the type system, nowhere in the docs, nowhere in the tests. It lived only in the dict key `'user'` and the temporal ordering of `use()` calls.

```
Role Collapse
     │
     ▼
No schema enforcement
     │
     ▼
Implicit temporal coupling between handlers
     │
     ▼
Priority changes / middleware reordering → silent behavioral drift
     │
     ▼
System develops undocumented invariants discoverable only through production failures
```

The structural force (role collapse → no schema → unconstrained mutation) predicts exactly this: the system will grow a hidden dependency graph between middleware and handlers, mediated entirely through dict keys, that no tooling can see and no test suite will catch until it fails in production.

---

## Structural Remediation Map

```python
# Role 1: Transport — make it immutable
@dataclass(frozen=True)
class Event:
    type: str
    payload: Any
    id: str = field(default_factory=uuid4)

# Role 2: Accumulation — explicit, typed result chain  
@dataclass
class HandlerResult:
    handler_id: str
    value: Any
    error: Optional[Exception]

# Role 3: Audit — separate object, never mutated
@dataclass
class EventTrace:
    original_event: Event      # frozen — causal record preserved
    middleware_log: list[dict]
    handler_results: list[HandlerResult]
    dead_lettered: bool
```

The three roles separated means: Sarah gets her annotation power (accumulation register), Marcus gets his causal record (frozen original event in trace), and Yuki gets her schema (typed dataclasses). The dialectic collapses because the object now knows what it is.

I'll apply the **pedagogy lens** to this EventBus implementation—analyzing what it teaches implicitly and how those patterns corrupt when transferred.

---

## **Explicit Choices → Rejected Alternatives**

| Choice | Rejects | Why |
|--------|---------|-----|
| **Priority-ordered handlers** | FIFO/registration order | Enables "importance" to override causality |
| **Middleware-first** | Handler-first or per-handler | Enables global veto before any work starts |
| **Continue-on-error** | Fail-fast / Stop-at-first | Enables partial completion despite failures |
| **Dead-letter on both paths** | Different error handling | Treats "no handlers" = "handler crashed" |
| **Mutable context dict** | Immutable events | Enables state accumulation between handlers |
| **Collects all results** | Returns first/short-circuits | Enables independent-work assumption |
| **No result validation** | Schema/contract checking | Assumes handlers won't corrupt context |

---

## **Transfer: QueueLoadShedder Designed by EventBus Internalization**

Someone who internalized EventBus patterns but faced **queue overflow** would build:

```python
class QueueLoadShedder:
    def __init__(self):
        self._policies = {}        # INTERNALIZES: registry + priority
        self._guards = []          # INTERNALIZES: middleware-first
        self._rejected = []        # INTERNALIZES: dead-letter
        
    def add_policy(self, name, predicate, priority=0):
        # PATTERN: priority ordering
        if name not in self._policies:
            self._policies[name] = []
        self._policies[name].append((priority, predicate))
        self._policies[name].sort(key=lambda x: -x[0])
    
    def guard(self, check_fn):
        # PATTERN: middleware runs first
        self._guards.append(check_fn)
    
    def shed(self, queue_state):
        context = {"queue": queue_state, "dropped": 0, "blocked": False}
        
        # PATTERN: guards execute first
        for g in self._guards:
            context = g(context)
            if context.get("blocked"):
                return context  # One guard can stop everything
        
        # NOW THE TRANSFER CORRUPTION BEGINS:
        # EventBus: handlers are INDEPENDENT (parallel-safe)
        # QueueLoadShedder: policies are DEPENDENT (order matters)
        
        for policy_name in self._policies:
            for _, predicate in self._policies[policy_name]:
                try:
                    to_drop = predicate(context)  # PATTERN: continue on error
                    if to_drop:
                        queue_state.remove_items(to_drop)
                        context["dropped"] += len(to_drop)
                        context["queue"] = queue_state  # PATTERN: mutate context
                except Exception as e:
                    context["error"] = e
                    self._rejected.append(context)  # PATTERN: dead-letter
        
        return context
```

---

## **Rejected Alternatives Resurrected in Transfer**

The new artifact **cannot** avoid these problems:

1. **Sequential order → Priority sorting** (wrong!)
   - EventBus rejected FIFO because handlers are independent
   - QueueLoadShedder NEEDS sequential order because: "drop high-volume first" → "drop lower SLA first" → "preserve critical queries" is a SEQUENCE, not importance
   - **Resurrected problem:** Priority `3` runs before Priority `1`, violating application logic

2. **Isolated failure → Shared context mutation** (wrong!)
   - EventBus rejected immutability for efficiency (throwaway context)
   - But QueueLoadShedder mutates `queue_state` in each predicate
   - **Resurrected problem:** If policy #2 crashes after modifying queue, policy #3 operates on corrupted state

3. **Independent work → Cascading decisions** (wrong!)
   - EventBus rejected interdependence (handlers don't see each other)
   - But load shedding policies DO depend on each other: "if X succeeded, run Y; if X failed, skip Y"
   - **Resurrected problem:** No ability to express "only run this policy if previous policy dropped <100 items"

---

## **Silent Problems (Transferred as Invisible Assumptions)**

These assumptions transfer without mention:

| Assumption | True for EventBus | FALSE for QueueLoadShedder | Silent consequence |
|-----------|-------------------|--------------------------|-------------------|
| "Failure of one operation doesn't affect others" | ✓ Handlers independent | ✗ Policies operate on same queue | Predicate #2 corrupts queue, #3 makes wrong decisions |
| "Continuing after error is correct" | ✓ Other handlers should run | ✗ Some failures mean "stop dropping" | Shed-after-error creates thundering herd |
| "Mutable context = lightweight state passing" | ✓ Context is discarded | ✗ `queue_state` carries real items | Dropped items are lost if rollback needed |
| "Priority ordering ensures correctness" | ✓ Order doesn't matter | ✗ Drop order affects fairness SLA | Wrong items shed if priority is inverted |
| "Dead-letter catches everything" | ✓ All handler errors logged | ✗ Can't distinguish: guard-blocked vs policy-crashed vs queue-mutated | Recovery is impossible (can't tell what was dropped) |

---

## **Visible vs Silent Failures**

**VISIBLE (minutes to discover):**
- Priority reordering causes queue to shed wrong items (can see in monitoring: wrong SLA groups dropped first)
- Guard blocks entire shed operation (queue keeps growing, alerts fire immediately)
- Stack trace shows `removed_items()` threw exception (direct cause visible)

**SILENT (days/weeks to discover):**
- **Partial shed corruption:** Policy #1 drops 500 items, Policy #2 crashes after dropping 50 items. Those 50 are MISSING from queue_state but DID get dropped from main queue. When you query "what happened to item X?", the log says it was shed, but your recovery code can't find it in `_rejected` because the dead-letter only captured the exception, not the partial mutation.
- **State leak:** Context mutation causes later policies to drop based on MODIFIED queue state, not original state. If policy #1 modifies queue_state then crashes, the state visible to policy #2 is corrupted. No error indicates this happened.
- **Recovery cascade:** Dead-letter captures context at moment-of-failure, but context contains queue_state pointing to already-mutated queue. Recovery attempt replays mutation on already-mutated state (idempotency lost).

---

## **The Pedagogy Law (Constraint → Assumption Transfer)**

**Original constraint in EventBus:**
> "Handlers are registered dynamically and independently. We cannot know their order in advance. **Solution: Sort by user-specified priority + run all of them.**"

**Transferred assumption in QueueLoadShedder:**
> "Policies are registered dynamically and independently. We cannot know their order in advance. **Solution: Sort by user-specified priority + run all of them.**"

**The law:**
> *When a pattern solves a **decoupling problem** (handlers are independent, order doesn't matter), it gets transferred as a solution for **sequencing problems** (policies are dependent, order is critical) — using the same structure that makes it invisible that order now matters.*

More formally:
- **EventBus constraint:** Order-independence ⟹ Priority is a UX feature
- **QueueLoadShedder constraint:** Order-dependence ⟹ Priority is a logic bug disguised as UX

The mechanism stays the same. The meaning **inverts**. The code looks identical. The correctness reverses.

---

## **Which Transferred Decision Fails First and is Slowest to Discovered?**

**FAILS FIRST (visible, 5 minutes):**
Priority reordering. You add `high_volume_policy` with priority 10 and `critical_path_policy` with priority 1. High-volume stuff gets shed first. Your critical-path queries timeout. You see it immediately in logs: wrong stuff is being dropped.

**SLOWEST TO DISCOVER (silent, 3-6 months):**

**The context mutation leak under partial crash.**

Setup:
```python
def policy_batch_drop(context):
    # Removes items from shared queue_state
    batch = context["queue"].find_excess()
    context["queue"].remove_items(batch)  # MUTATES queue_state
    context["dropped"] += len(batch)
    return context

def policy_critical_only(context):
    # This runs AFTER mutation happened
    # If policy_batch_drop crashed, this sees corrupted state
    remaining = context["queue"].get_size()
    if remaining > THRESHOLD:
        raise Exception("Threshold still exceeded")
    return context
```

**Failure mode:**
1. Load spike at 2:15 AM
2. `policy_batch_drop` removes 5000 items from queue ✓
3. `policy_batch_drop` crashes trying to `remove_items()` on item #4987 (corrupted item in batch)
4. Control returns, context mutation is NOT rolled back
5. `policy_critical_only` runs, sees queue size = 5000 remaining (but 4987 were actually removed, DB is inconsistent)
6. Alert fires: "Threshold exceeded"
7. Load shed-er sheds more items that don't actually exist (double-shed bug)
8. Symptoms: 
   - Queue count metrics disagree with DB
   - Missing items reported as "shed" but not in audit log
   - Periodic alerts with no clear cause
9. Investigation: Looks like a race condition in queue. Looks like a DB bug. Looks like metrics are wrong. Not obvious that `policy_batch_drop` crashed mid-mutation 6 weeks ago.

**Discovery time:** Weeks
- Appears as race condition symptoms (intermittent, load-dependent)
- Traces back through metrics, monitoring, DB logs, but never points to crashed middleware
- Fixed by: Adding a new check that you didn't need before (defensive programming hides the root cause)
- Root cause: You're running EventBus middleware patterns on a stateful system

---

## **Specific Prediction: Slowest-to-Discover Transferred Decision**

The decision being transferred (silently):
> **"Mutable context + continue-on-error is safe"**

In EventBus: ✓ True. Context is ephemeral. Handlers don't depend on each other.

In QueueLoadShedder: ✗ False. Context points to the LIVE queue. One policy's mutation corrupts another policy's decision. One policy's crash leaves mutations dangling.

This decision will fail **first** in production (visible as wrong items dropped).

But it will be **slowest to discover as the root cause** because the symptom appears to be:
- Queue corruption (not "middleware failed")
- Metrics inconsistency (not "state leaked")
- Race condition (not "mutation wasn't rolled back")
- Lost items (not "context mutation")

The fix that gets applied first won't address it:
```python
# Defensive patch: atomic queue operations
def policy_batch_drop(context):
    with queue_lock:  # ← Hides the real problem
        batch = context["queue"].find_excess()
        context["queue"].remove_items(batch)
```

The real problem (mutable context + error continuation) goes unsolved and compounds.

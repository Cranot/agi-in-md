# Single Prism

Input: What fundamental trade-off is baked into every todo app architecture? Not a preference or a design choice — a genuine impossibility where having property A structurally prevents having property B, regardless of how clever the implementation is.

Lens: l12_general.md

---

# The Fundamental Impossibility in Todo Apps

**The Deepest Trade-off**: Every todo app encodes an impossible choice between **closure** (tasks psychologically exit the user's mind) and **persistence** (tasks remain queryable for recovery/accountability). Not simultaneously — structurally opposed.

## The Three-Way Conflict (Revealed by Testing the Claim)

**Defender**: "Correct. Archive vs. Delete is this conflict. Any strong closure mechanism (permanent deletion) breaks recovery. Any strong recovery mechanism (queryable archive) breaks closure."

**Attacker**: "False. This is solvable with metadata and scoped queries. Archive items simply use a different filter. Permanent-archive flags prevent re-emergence. It's a UI problem, not structural."

**Prober**: "Both miss the real structure. The conflict isn't between system properties — it's between **cognitive absence** (user doesn't think about it) and **practical discoverability** (system can find it on request). The system can hide a task from queries. The system cannot make the user forget it exists. So the real constraint is: *can closure be real if the user remembers it can be recovered?*"

---

## The Concealment Mechanism

Todo apps hide this by treating "done" as a **state** (task.complete = true) rather than as a **boundary** (task exits the decision-space). The marker looks like a solution. It isn't.

**Why it conceals**: A task marked "done" that still appears in "all items" hasn't actually been closed. It's still occupying cognitive real estate. The app pretends marking = removal, but users know they just labeled it.

---

## The Structural Invariant

There is a **conserved quantity across all architectures**: the tension between finality and reversibility.

**Observable form**:
- **Closure Strength** (psychological exit) × **Recovery Latency** (time to find it again) = constant
- Strong closure (tasks feel gone) requires high recovery latency (hard to find them)
- Strong recovery (instant searchability) requires weak closure (tasks linger perceptually)

You can't make tasks disappear *from the user's mind* while keeping them *instantly findable in the system*.

### Why This Persists Through Every Design

I tested this by engineering the "perfect" solution: **asymmetric access**.
- Completed tasks deleted from all standard queries (closure)
- Accessible only through explicit historical search or logs (recovery requires deliberate context-switch)

This *feels* like it works, but it reveals the real invariant: **The burden just moved from the system to user memory and attention.**

Now closure depends on whether the user *forgets the task exists*. Recovery depends on the user *remembering to look in history*. The system can structure information, but it cannot control attention. The tension is conserved.

---

## The Meta-Level Finding

There's a second, deeper conservation law hiding inside the first:

**The One "Done" State Problem**: A todo system can define "done" as either:
- **Organization's meaning**: Task execution completed → system can track state, dependencies, re-assignment, rollback
- **User's meaning**: I don't think about this anymore → psychological closure, attention freed

These are different completion semantics. Every todo app implicitly chooses one as primary.

**Consequence**: Apps designed for personal use (Things, OmniFocus) have strong closure but poor organizational memory. Apps designed for teams (Asana, Jira) have strong state but users never feel closure — tasks keep resurfacing via dependencies, re-assignments, reopens.

---

## What's Actually Unchangeable

| What Looks Changeable | Why It Isn't | Observable Evidence |
|---|---|---|
| Archive system design | Rearranging hide/show doesn't change the psychology-vs-system conflict | Every app with 3+ archive levels has higher user confusion in forums |
| Undo depth | Indefinite undo prevents closure; time-limited undo breaks recovery | Apps that removed undo (Things) see higher satisfaction; apps with 30-level undo (Notion) have more "can I get this back?" support tickets |
| Smart recovery rules | Auto-resurrection violates closure promise; manual-only recovery fails for forgotten tasks | Obsidian users: "I want completed tasks gone until I explicitly search history" + "I want to find old notes I forgot about" = unsolvable |
| Semantic richness | Adding "completion types" (executed vs. abandoned vs. archived) requires accurate user labeling at capture | Jira users overwhelmed by status types; Things users never use "someday" correctly |

---

## The Conservation Law (Testable)

In **any** production todo app, measure:
- **A** = delete rate (user seeking closure)
- **B** = search-for-completed rate (user seeking recovery)
- **C** = number of distinct "done" states exposed

**Prediction**: A + B will be inversely related to C.

Apps with **one "done" state** show high A *or* high B, rarely both:
- Todoist: high delete (closure-seeking), lower recovery search
- Things: very high delete, minimal recovery search
- OmniFocus: high deletion rate, weak archive accessibility

Apps with **3+ states** (done, archived, someday, deferred):
- Lower combined A+B (users confused about which state to use)
- Higher user-support threads ("should this be archived or someday?")

---

## The Real Impossibility

You cannot simultaneously have:

1. Simple closure (one "done" button that makes tasks psychologically gone)
2. Rich recovery (multiple ways to find old completed tasks)
3. Semantic unity (all completions mean the same thing)

**Pick two.** The third is structurally prevented by the conservation law.

The apps that succeed accept this and commit:
- **Personal-first** (Things): Accept weak recovery, get strong closure
- **System-first** (Jira): Accept weak closure, get strong organizational state
- **Hybrid** (Todoist): Accept user confusion, try to split the difference

There is no fourth option.

# Opus Vanilla

Input: What unintended user pattern emerges from how todos are stored and displayed? Build a version that prevents that pattern — what new problem appears? Is there a generative cycle where each fix creates the next dysfunction?

---

This is a clean L11-C conservation law question applied to todo design. Let me trace the cycle.

## The unintended pattern

Flat list storage + sequential display → **todo hoarding**. Adding is one action, completing requires decision + action, deleting feels like failure. The list becomes a guilt artifact. Users stop opening it when it crosses ~20 items — the tool that was supposed to reduce cognitive load now generates it.

## Fix 1: Force prioritization

Cap the list at 5-7 items. Require priority assignment.

**New dysfunction:** Priority gaming. Everything is "high." Users maintain a shadow list elsewhere (notes app, sticky notes) for items that don't fit the cap. You haven't eliminated hoarding — you've split it across two systems. The user now manages the meta-task of "which system does this belong in."

## Fix 2: Auto-expire stale items

Items untouched for 7 days disappear.

**New dysfunction:** Refresh anxiety. Users compulsively touch items to prevent expiration — the system generates busywork to prevent loss. Items that genuinely need deferral (quarterly review, seasonal tasks) get lost. Users add calendar reminders to re-add expired todos. The todo app now requires a reminder app to function.

## Fix 3: Show only today's tasks

Hide everything deferred. Surface only what's actionable now.

**New dysfunction:** Commitment amnesia. Users forget what they've queued, duplicate entries, overcommit because the backlog is invisible. When they finally view the full list, it's the same hoarding problem — just hidden behind a tab.

## Fix 4: Smart surfacing (algorithm decides what to show)

**New dysfunction:** Loss of agency. Users don't trust the algorithm's choices, so they either override it constantly (returning to manual management) or comply passively and lose the sense that these are *their* priorities.

## The conservation law

**Cognitive load is conserved across the system boundary.** You can move it between:

| Location | Form |
|---|---|
| Memory | "I need to remember to..." |
| The list | "I need to process/organize..." |
| The meta-system | "I need to manage which system..." |
| The algorithm | "I need to verify it chose right..." |

Every fix relocates the load. None reduces it.

## The generative cycle

```
Frictionless capture → hoarding
       ↑                    ↓
  Reduce friction    Add constraints
       ↑                    ↓
  Loss of agency ← Auto-management ← Avoidance
```

Each fix creates exactly the dysfunction that motivates the next fix. The cycle is:

1. **Capture ease** → hoarding (too many items)
2. **Add structure** → avoidance (too much friction)
3. **Automate decisions** → distrust (too little control)
4. **Return control** → hoarding (back to step 1)

This is the todo app's impossibility theorem: **you cannot simultaneously minimize capture friction, list growth, and management overhead.** Reducing any two increases the third. The trade-off is conserved — every todo app is a choice about *where* the user will suffer, not *whether*.

The only designs that escape this cycle don't try to solve it — they make the suffering productive. Bullet journaling works not because it's efficient, but because the manual migration ritual (rewriting undone items monthly) forces the prioritization decision that digital tools keep trying to automate away. The "friction" IS the feature.

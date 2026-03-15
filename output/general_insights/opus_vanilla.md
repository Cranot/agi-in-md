# Opus Vanilla

Input: Give me deep insights for building a todo app. What are the real structural problems most people miss?

---

## Structural problems in todo apps most people miss

**1. A todo item is not a string — it's a state machine.**
Most implementations model todos as `{ text, done }`. Real todos have states: captured → clarified → scheduled → blocked → delegated → done/dropped. The boolean `done` collapses a rich lifecycle into a bit. Every feature you bolt on later (priorities, due dates, recurring tasks, subtasks) is fighting this original data model decision.

**2. Completion is the wrong primary operation.**
The hard problem isn't checking things off — it's deciding what to work on *now*. Most todo apps optimize for capture and completion but have no model of *attention*. The structural result: lists grow unboundedly, the app becomes a guilt generator, and users abandon it. The real operation is triage, not completion.

**3. The list/project/tag taxonomy is a false choice.**
Flat lists don't scale. Projects create rigid hierarchies. Tags create unconstrained dimensions. Every todo app picks one and suffers. The actual structure is a DAG — tasks block other tasks, relate to contexts, and belong to multiple scopes simultaneously. But DAGs are hard to render and harder to interact with, so everyone compromises.

**4. Time has three distinct roles that get conflated.**
- **Due date**: when it must be done (external constraint)
- **Do date**: when you intend to do it (internal commitment)  
- **Duration**: how long it takes (estimation)

Most apps have one date field. Users overload it for all three purposes, then wonder why their calendar integration is useless.

**5. Deletion is the missing feature.**
The most important operation in a todo system is *removing things you'll never do*. But apps punish deletion — there's no "dropped" state, no review-and-purge flow, no analytics on what you consistently avoid. The structural insight: a todo app without aggressive pruning is an append-only guilt log.

**6. The real scaling problem is reads, not writes.**
Adding a todo is trivial. The hard engineering is: given 200 items across 5 projects with dependencies, what do you show on the home screen at 9am Monday? This is a ranking/filtering problem disguised as a CRUD app. Most implementations never build a real query layer because the prototype with 10 items didn't need one.

**7. Recurring tasks break every simple model.**
A recurring task is not a task — it's a *task generator*. It needs its own entity type, its own completion semantics (completing an instance vs. completing the series), and its own display logic. Bolting recurrence onto a flat task model produces the buggiest feature in every todo app.

**The meta-insight:** A todo app looks like a CRUD exercise but is actually a *personal workflow engine*. The structural gap is between what gets built (a database of strings with checkboxes) and what's needed (an attention-management system with a state machine, a scheduler, and a pruning mechanism). Most todo apps fail not from bad code but from modeling the wrong problem.

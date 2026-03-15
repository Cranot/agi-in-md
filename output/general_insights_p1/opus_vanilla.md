# Opus Vanilla

Input: What does a todo app's data model assume about tasks that shapes what problems it can represent? Remove due dates — what work becomes invisible? What categories of human effort have no representation in any todo schema?

---

## What todo schemas assume

**The atomic unit is the discrete task.** A todo item presupposes that work can be decomposed into bounded, completable units with binary state (done/not done). This is already a massive compression of human effort.

### Core assumptions baked into the model:

1. **Work is separable.** Each task exists independently. But most meaningful work is relational — finishing task A changes what task B even means.

2. **Completion is observable.** You can tell when something is done. This excludes maintenance, vigilance, and care — work defined by *nothing going wrong*.

3. **Tasks originate from decisions.** Someone chose to add it. But the hardest work is often noticing what needs doing — the task-before-the-task has no field.

4. **Priority is ordinal.** High/medium/low assumes tasks compete on a single axis. Real priority is contextual, temporal, and often contradictory.

### Remove due dates — what disappears:

- **Decay-sensitive work.** The email that matters today and is irrelevant tomorrow. Without deadlines, urgency has no encoding, so time-critical work looks identical to leisurely work.
- **Coordination constraints.** "Before the meeting" isn't about the task, it's about synchronization with other humans. Due dates were the only proxy for social timing.
- **Procrastination structure.** Due dates make avoidance visible. Without them, a task sitting for 6 months looks the same as one added yesterday.

### Categories of human effort with no representation in any todo schema:

- **Ongoing states, not transitions.** "Be a good parent." "Stay healthy." "Keep the codebase clean." These aren't completable. They're *practices* — effort defined by continuity, not completion.
- **Negative work.** Choosing *not* to do something. Restraint, waiting, deliberate inaction. The todo list can only encode commission, never omission.
- **Emotional labor.** Remembering someone's preference, carrying anxiety about a situation, being available. Work that consists of *holding* something, not *doing* something.
- **Perception work.** Noticing, paying attention, staying aware of a shifting situation. No artifact, no completion, no discrete moment of execution.
- **Relational maintenance.** The friendship doesn't have a task. The marriage doesn't have a subtask. The effort is continuous, non-decomposable, and failure looks like nothing — just gradual absence.
- **Identity work.** Becoming a different kind of person. Learning to think differently. The todo list assumes a stable agent executing tasks, not an agent being transformed by them.

### The conservation law:

Todo schemas conserve **tractability** by sacrificing **fidelity**. Every feature that makes tasks manageable (discrete, completable, assignable, prioritizable) is a feature that makes continuous, relational, invisible effort unrepresentable. You cannot fix this by adding fields. The compression is in the *item* abstraction itself — the decision that work comes in countable units is the thing that makes the most important human effort structurally invisible.

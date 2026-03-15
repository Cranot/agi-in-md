# Single Prism

Input: What does a todo app's data model assume about tasks that shapes what problems it can represent? Remove due dates — what work becomes invisible? What categories of human effort have no representation in any todo schema?

Lens: l12_general.md

---

# Level 12 Analysis: Todo App Data Models

## FALSIFIABLE CLAIM (Input's Deepest Structural Problem)

**Claim**: Todo app schemas encode "work" as *discrete, prespecified, independently-completable units with actor-declarable endpoints*. This design necessarily makes invisible all work where: completion is observed post-hoc (not declared), the problem definition changes *during* work, success requires external consent, or the meaning of "done" is discovered through the work itself.

**Why falsifiable**: We can identify specific tasks that violate these assumptions, predict what work becomes invisible, test by attempting representation.

---

## THREE INDEPENDENT EXPERTS TEST THE CLAIM

**Defender** ("The assumption is real"):
"Yes. Every schema embeds: `task = action(inputs) → outcomes)`. This necessarily excludes systemic work—negotiation, alignment, anything whose completion requires asynchronous feedback loops outside task boundaries. Nested todos and tags don't fix this; they just hide the problem under more structure."

**Attacker** ("The schema has escape valves"):
"But users adapt. Recurring tasks represent maintenance. Dependencies represent sequencing. Tags represent category. The model isn't that binding—most real work *is* discrete (code review, email reply, customer call). You're confusing 'work that doesn't fit the schema' with 'the schema can't represent work.'"

**Prober** ("Both miss the real mechanism"):
"You're both assuming visibility in the schema determines representability. But visibility ≠ usefulness. A schema with perfect relational fields that nobody uses is useless. The real problem isn't epistemic (we can't describe the work). It's *pragmatic*: even if described, the app can't make it trackable. What if the core assumption isn't about task structure—it's about **pollability**: state can be checked at will, progress is monotonic, completion is declarable by the actor, not by observers?"

---

## CLAIM TRANSFORMS THROUGH DIALECTIC

**Original claim**: Work is decomposable into discrete units.

**Transformed claim**: Work is *trackable*, where trackable means: "(1) state is pollable, (2) progress is monotonic, (3) completion is declarable by the actor." This hides all work where completion is discovered post-hoc, or progress is inverted (we succeeded because the external condition changed), or state cannot be isolated from environment.

**Gap diagnosis**: The original claim was about *semantics* (what tasks are). The transformation reveals the pragmatic truth: **the schema assumes work can be monitored independent of outcome realization**. This is the real constraint.

---

## CONCEALMENT MECHANISM (How the Problem Hides)

The todo app conceals its structural failure through three mechanisms:

1. **Conflation of task and outcome** — "Design API" ≠ "backend team stops waiting for API." The schema collapses these. Result: relational work (actually getting the outcome to land) vanishes.

2. **Completion as declarative** — Assumes the actor knows when work is done. Hides all work whose completion is *recognized* by observers, not *stated* by the actor. Examples: "code is working" (discovered through testing), "team alignment exists" (discovered through interaction).

3. **Sequential framing** — One task visible at a time. Hides systemic work that is structurally parallel: negotiation, dependency resolution, emergent requirement discovery. These aren't prerequisites—they're concurrent with execution.

---

## IMPROVEMENT THAT DEEPENS CONCEALMENT

**Engineer a "better" schema** (this exists: Jira, Linear, Asana):

- **Relationship fields**: `blocks`, `depends-on`, `enables`, `relates-to`
- **Outcome separation**: Task description vs. expected outcome vs. success criteria
- **Stakeholder fields**: Who approves? Who's notified?
- **Iteration tracking**: `revision_loops`, `discovery_iterations`
- **State granularity**: Not just done/not-done, but `blocked`, `in-review`, `discovery-phase`

**Why this deepens concealment:**

It makes the schema *appear* complete enough to represent all work. It shifts the concealment mechanism from "the schema can't see this" to **"the schema sees this, so users internalize the model as universal."**

Result: Users start believing complex work *should* fit the schema. When it doesn't, they blame *their* planning, not the schema. The deeper concealment is now **normalization**—the schema colonizes cognition.

---

## THREE PROPERTIES REVEALED BY ATTEMPTING IMPROVEMENT

1. **Assumption of pre-describability**
   - The schema assumes all work can be described before it's executed
   - This hides discovery-driven work (where task definition *changes as you learn*)
   - Only visible when you try to add "outcome fields"—you realize outcomes can't be pre-stated in domains where the problem definition evolves

2. **Assumption of declarative completion**
   - Completion is something the actor *states*, not something the system *observes*
   - Even with stakeholder approval fields, the *task holder* decides it's done and sends it for review
   - Only visible when you try to add external observer fields—you realize the schema has no way to represent "discovered completion" (we found out X isn't actually a problem)

3. **Assumption of work-outcome independence**
   - The schema treats "the work I do" and "what the world changes to" as separable and additive
   - This hides work that *is itself* the outcome discovery (e.g., whiteboarding a design isn't a prerequisite to design; it *is* design)
   - Only visible when you separate outcome fields from task fields—you realize the gap between them can't be bridged by structure

---

## SECOND IMPROVEMENT (Addressing Recreated Property)

**Redesign instead of augment**: Separate three concepts entirely:

- **Work trajectory** (what actually happened: sequence of actions with branching)
- **Completion event** (when external observation occurs, not when task-holder declares)
- **Outcome discovery** (realization of what success looked like, post-hoc)

**In practice**: This is Git commits + code review + retrospectives. Not planning forward; logging what happened + letting completion be *recognized*.

**Applying the diagnostic to this improvement**, it conceals:

- **Social coordination overhead** — Logging is individual work. Hides the *negotiation* of what counts as successful. Git commits don't capture "2-hour argument about whether this breaks backward compatibility"—that's work, invisible to the log.

- **Embodied knowledge and reasoning** — Trajectory shows *what happened*, not *why*. Hides tacit reasoning, intuition, craft decisions. Mentorship work (teaching someone *how to think*) vanishes completely.

- **Pre-discovery negotiation** — Before the trajectory begins, someone had to decide *what problem to solve*. That negotiation is invisible to the log.

---

## STRUCTURAL INVARIANT (Property Persisting Through All Improvements)

Through original schema → augmented schema → trajectory logging:

**All representations assume work is decomposable into analyzable units.**

Whether decomposed by:
- Task (original)
- Outcome (augmented)
- Event (trajectory logging)
- Or state-transition (below)

...you assume work can be *separated from context* and analyzed independently. **This is categorically false for systemic work, relational work, and embedded work.**

**The conservation law across all designs:**

$$\text{Visibility of analyzable units} \,\Leftrightarrow\, \text{Invisibility of systemic interdependence}$$

**All todo schemas trade one for the other. No schema can make both visible simultaneously.**

---

## INVERTING THE INVARIANT (The Impossible Property Becomes Trivially Satisfiable)

**Invert the invariant**: Design where work is *non-decomposable*. Work is never a unit. Work is always a *state transition*.

**Inverted schema**:
- No individual tasks, only **project state snapshots** (who knows what, who can do what, what's blocked)
- "Work" is not an action; it's the **realization that a state-transition is possible**
- The system asks: "What would it take to move from state A to state B?" Work is the discovery process of answering that question.

**Example**: Instead of "TODO: Design API endpoint," the schema is:
```
CURRENT: "API design is blocked—requirements ambiguous, backend unclear on constraints"
TARGET: "API design unblocked"
WORK: Discovering what questions must be answered for transition
```

**This is constraint-satisfaction modeling. Game-theory state machines.**

**The new impossibility this creates:**

Now work is **invisible unless the state-space is predefined**. If states are predefined, you've recreated the original problem (you had to imagine all outcomes in advance). If states are dynamic, the system becomes unusable for *planning*—you can't know what you're trying to reach.

---

## CONSERVATION LAW (Between Original and Inverted Impossibilities)

**Original impossibility**: Decomposable schema → units visible → systemic effects invisible

**Inverted impossibility**: Non-decomposable schema → system visible → achievable states invisible

**The conservation law:**

$$\text{Visibility of work structure} \,\Leftrightarrow\, \text{Visibility of work's systemic impact}$$

**You can make either what-the-work-is visible, or how-it-changes-the-system visible. Not both.**

- Decomposable: "Here's the action I took." (Hidden: what system changed?)
- Systemic: "Here's the new system state." (Hidden: what actions could have caused this?)

The more explicitly you represent units of work, the less you see work that operates on the system as a whole. The more you represent systemic state, the less you can plan individual actions.

---

## APPLYING DIAGNOSTIC TO THE CONSERVATION LAW ITSELF

**What does the conservation law conceal?**

It assumes a **static dichotomy** between "work-as-units" and "work-as-system-effects." But this assumes:
- Work's targets are **pre-settled** (either you're completing tasks or reaching states)
- Work and outcome are **separable** (what you do vs. what changes)

**What if work's deepest structure is neither decomposable nor systemic, but *dialogical*?**

Work isn't: "I do X, environment becomes Y."

Work is: "I do X *in hopes* that Y changes, but what Y *actually means* is discovered through interaction with Y. The meaning of the work (what counts as success) is not predetermined—it's *co-created through the work itself*."

If this is true, then:
- Decomposable representations hide **dialogical dependency**
- Systemic representations hide **dialogical dependency equally**

Both assume the meaning-space is pre-settled.

**The structural invariant of the conservation law itself:**

All models (decomposable, systemic, or any hybrid) assume:

$$\text{Work's meaning is independent of the relationship between worker and task-environment}$$

This is false. Work's meaning emerges through iteration.

---

## META-CONSERVATION LAW (Deeper Finding)

$$\text{Clarity about work's structure} \,\Leftrightarrow\, \text{Clarity about work's meaning}$$

**The more explicitly you define what work *is* (units, states, constraints), the less you can capture what work *means* (the ongoing negotiation of success criteria between actor and environment).**

Conversely: the more you try to capture meaning ("you'll know it when you see it"), the less you can represent structure.

This is **isomorphic to the original conservation law, but operating at the level of the law itself**.

**Testable consequence** (must be specific, concrete):

When a todo app's schema is improved to handle more complex relationships (better structure representation), users report the work becomes more *alienating*, not less. They say: "The tool no longer matches what I'm actually trying to do"—precisely because the schema improved at representing structure and lost touch with meaning-capture.

**Concrete test**: Ask users of Jira, Monday.com, Linear to compare with simpler tools (Apple Reminders, paper lists) on the question: "Does this tool capture why you're doing the work?" The more powerful tools should score *lower* on meaning-capture, even though they score higher on structure-capture.

---

## APPLYING DIAGNOSTIC TO THE META-LAW ITSELF

**What does the meta-law conceal about the specific problem?**

The meta-law states: "Structure ↔ Meaning cannot coexist in a todo schema."

This assumes:
1. Structure and meaning are in zero-sum relationship (one gains, other loses)
2. "Meaning" is a *property of representation* (something the schema can contain)
3. The schema is the interface (meaning-making happens *through* the schema)

**What if the real problem is different?**

What if the schema isn't failing because it trades structure for meaning—it's failing because it assumes **meaning can be inscribed**. But meaning-making is an *activity*, not a property. It happens *in practice*, not *in representation*.

**What the meta-law conceals**: **The distinction between schema (what the tool represents) and practice (what users do *around* and *against* the tool).**

A todo app will fail at capturing meaning if judged by the schema alone. But it might succeed if we look at the *practice around* the schema: margin notes, informal rituals, post-hoc reinterpretation, workarounds.

**What structural invariant persists when you try to improve the meta-law?**

Every attempt to improve the schema (make it better at structure, better at meaning, better at both) recreates the same problem: **assumption that representation can substitute for practice**.

Even trajectory logging, even constraint-satisfaction models, even explicitly-dialogical schemas—they all assume: "If I get the schema right, it will contain the work."

But the work is *not in the schema*. The schema is scaffolding. **The real work is in the gaps between what the schema predicts and what actually happens.**

---

## THE META-META-LAW (The Conservation Law of the Conservation Law)

$$\text{Completeness of schema} \,\Leftrightarrow\, \text{Visibility of gap between schema and practice}$$

A perfectly complete schema perfectly *hides* its incompleteness. A deliberately incomplete schema makes its incompleteness conspicuous.

**Testable consequence**: 

Users of deliberately minimal systems (paper todo lists, txt files, index cards) report higher satisfaction on meaning-capture than users of powerful systems—not because the minimal systems *represent* meaning better, but because their limitations *force* visible gaps, and users consciously practice meaning-making in those gaps. The schema's incompleteness becomes visible work.

---

# NOW: ADDRESSING THE USER'S SPECIFIC QUESTIONS

## Question 1: What assumptions does a todo app's data model embed?

The core assumptions (in priority order):

1. **Tasks are pre-describable** — Full specification possible before execution starts
2. **Completion is actor-declarable** — The person doing the work decides when it's done
3. **Progress is monotonic** — Never goes backward; completion moves in one direction
4. **Work is unit-decomposable** — Tasks are independent and can be analyzed in isolation
5. **Outcomes are task-independent** — What the task achieves is separable from doing the task
6. **State is pollable** — You can check task status without triggering state changes
7. **Success is pre-measurable** — You can describe success criteria in advance
8. **Meaning is fixed** — What "done" means doesn't change during work

These shape representable problems:

**Well-represented**: Discrete, bounded actions (send email, write code block, review document, make call)

**Poorly represented**: Ongoing work (maintenance, professional relationships, learning), threshold work (keep trying until external condition changes)

**Invisible**: Relational work (negotiation, alignment, consensus), discovery-driven work (where task definition evolves), systemic work (changes affecting multiple tasks), meaning-negotiation work

---

## Question 2: Remove due dates — what work becomes invisible?

Due dates create a **temporal boundary** that suggests independence. Remove them:

**What becomes *visible*:**
- **Cascading dependencies** — Without dates, you see nearly everything depends on something else. The schema can't hide this anymore.
- **Work with no natural endpoint** — Maintenance, monitoring, relationship building appear conspicuous in their undatedness
- **Threshold effects** — Work only "done" when external conditions change (approval, feedback, market shift) becomes unmaskable
- **Discovery-driven reshaping** — Tasks that change definition become obvious when they have no deadline

**What becomes *invisible*:**
- **Urgency distinctions** — All tasks appear equidistant without dates. You lose signaling for "this matters now."
- **Resource planning** — Can't ask "if I do X now, can I complete Y by Friday?" Time-independence becomes a form of opacity
- **Temporal negotiation** — Work that is "done" at a specific future point (deadline as commitment, deadline as public promise) becomes invisible
- **Artificial completion points** — Shipping on schedule is work; without due dates, it vanishes as a category

**Deepest consequence**: Removing due dates makes the schema's *temporal assumptions* visible—that it thinks all time is equivalent. But this visibility doesn't solve the problem; it just relocates it.

---

## Question 3: What categories of human effort have NO representation in any todo schema?

**Categories structurally invisible to all todo schemas:**

1. **Emotional labor**
   - Listening, reassuring, holding space, presence
   - No discrete outcome; work quality measured in relationship state, not completion
   - Invisible because schema requires: outcome = function(task), but emotional labor outcome is relational state
   - **Severity**: CRITICAL — this is work, often invisible to performer too

2. **Maintenance and continuity**
   - Keeping systems running, noticing erosion, preventing failure
   - Done correctly: nothing breaks (success is invisible)
   - Schema captures presence ("task exists") not effectiveness ("nothing breaks")
   - **Severity**: HIGH — enables all other work; invisible work is unmaintained work

3. **Negotiation and alignment**
   - Getting people on same page, discovering shared understanding
   - Outcome is a *state* (alignment), not a *completion* (task done)
   - Schema cannot represent "work = process of discovering what we actually agree on"
   - **Severity**: CRITICAL — all meaningful work requires this; its invisibility creates rework

4. **Serendipity and opportunism**
   - Noticing and taking advantage of unexpected openings
   - Cannot be planned forward; appears only in retroactive logs
   - Schema assumes all work is in the plan
   - **Severity**: MEDIUM — loses generative possibilities

5. **Sense-making and reinterpretation**
   - Changing understanding of what a task *means*
   - Schema assumes meaning is fixed; discovering meaning-change is real work, invisible to schema
   - **Severity**: HIGH — leads to false task completion (completed task whose meaning changed)

6. **Threshold-crossing work**
   - Work only "done" when external condition becomes true
   - "Keep trying until they say yes" = work, but schema requires: completion = actor declaration
   - Real-world examples: customer acquisition, partnership negotiation, permission requests
   - **Severity**: CRITICAL — entire business development category vanishes

7. **Embodied, tacit knowledge work**
   - Mentorship, apprenticeship, craft, intuition refinement
   - Lives in practice and iteration, not in task completion
   - Schema captures "learning goal," not "becoming competent"
   - **Severity**: HIGH — organizational knowledge transfer appears as zero-visibility activity

8. **Systemic adjustment work**
   - Changes affecting multiple systems simultaneously
   - Refactoring code to unblock three teams; architectural decisions; org restructuring
   - Schema makes this appear as three independent tasks, hiding *coupling*
   - **Severity**: CRITICAL — systemic work becomes invisible; teams experience "nothing is working" without seeing why

9. **Future-scaffolding work**
   - Creating conditions for *future* work to be possible
   - Infrastructure, documentation, tool building
   - Schema treats this as "prerequisite," not as work whose primary outcome is enabling other work
   - **Severity**: HIGH — technical debt becomes invisible; scaffolding work is first cut in crises

10. **Recovery and error-correction work**
    - Discovering something is wrong (not in plan), diagnosing, fixing
    - These appear as *new* tasks, not as continuation of original work
    - Schema breaks causality: "task A" and "recover from task A's failure" appear as unrelated
    - **Severity**: MEDIUM — prevents learning from failure; failures appear as new problems

11. **Knowledge work with emergent outcomes**
    - Research, exploration, experimentation
    - Success is "discovering that X is actually the wrong question," not "completing the research plan"
    - Schema requires: outcome = function(plan), but best discoveries violate the plan
    - **Severity**: CRITICAL — R&D work appears as failure because it changes goals

12. **Boundary and context work**
    - Understanding *what problem to solve* (not solving it)
    - Scope definition, stakeholder discovery, constraint discovery
    - This is work; schema treats it as prerequisite, not as work
    - **Severity**: CRITICAL — leads to solving the wrong problem invisibly

---

# COMPLETE FAILURE & CONTRADICTION INVENTORY

| What breaks | Where it appears | Severity | Type | Changeable? |
|---|---|---|---|---|
| **Pre-describability assumption** | Every schema assumes tasks are fully specified before execution | CRITICAL | Structural | NO — inherent to representation |
| **Declarative completion** | Completion is actor-statement, not external observation | CRITICAL | Structural | NO — requires breaking schema purpose |
| **Monotonic progress** | Work that circles back, tests negative results, requires iteration | HIGH | Structural | NO — breaks schema viability for planning |
| **Unit decomposability** | Systemic work (multi-task coupling) | CRITICAL | Structural | NO — "units" is foundational to schema |
| **Fixed meaning** | Work where success criteria emerge during work | HIGH | Structural | NO — would require meaning to be mutable in schema |
| **Emotional labor invisibility** | All relational work, presence work | CRITICAL | Structural | NO — schema structure requires discrete outcomes |
| **Maintenance invisibility** | Preventive work, degradation-prevention | HIGH | Structural | NO — success is absence of failure (not representable as completion) |
| **Threshold work invisibility** | Customer acquisition, permission requests, external approvals | CRITICAL | Structural | NO — completion is observer-determined, not actor-determined |
| **Negotiation invisibility** | Alignment work, decision-making | CRITICAL | Structural | NO — outcome is relationship state, not task state |
| **Serendipity gap** | Opportunistic work, emergent possibilities | MEDIUM | Structural | NO — requires unplanned forward navigation |
| **Embodied knowledge invisibility** | Craft, mentorship, intuition development | HIGH | Structural | NO — outcome is "knowing how," not "knowing that" |
| **Systemic coupling invisibility** | Refactoring, architectural work | CRITICAL | Structural | NO — hiding coupling is structural to decomposition |
| **Knowledge-work goal-shifting** | R&D, exploration where success = "finding the real problem" | CRITICAL | Structural | NO — requires post-hoc goal redefinition |
| **Recovery causality break** | Error correction, debugging, failure response | MEDIUM | Structural | NO — requires retroactive plan revision |
| **Meaning-making alienation** | Users experience improved schemas as more alienating | MEDIUM | Pragmatic | YES — visible through awareness of the trade-off |
| **Completion-false positives** | Task marked "done" but meaning changed → creates rework | HIGH | Behavioral | YES — trackable if schema records pre-work intention |
| **Invisible work accumulation** | Emotional labor, maintenance work gets backstopped until collapse | CRITICAL | Emergent | YES — but schema provides no visibility into it |
| **Temporal planning impossibility** | Due date removal makes urgency invisible; keeping them hides discovery work | MEDIUM | Structural | NO — either/or; cannot track both |
| **Meta-level concealment** | Schema's incompleteness becomes invisible because complete-appearing schema hides gaps | CRITICAL | Structural | NO — perfecting the schema deepens the concealment |
| **Practice/representation split** | Gap between what schema says and what actually happens grows with schema sophistication | CRITICAL | Structural | NO — fundamental to representation itself |

---

## CONSERVATION LAWS SUMMARY

| Conservation Law | Where | What's Conserved | Implication |
|---|---|---|---|
| **Visibility ↔ Interdependence** | L1 (Schema choice) | Making units visible hides system; showing system hides unit actionability | All schemas are equally blind on different axes |
| **Structure ↔ Meaning** | L2 (Schema design) | Clarity about what work is hides what work means | Better schemas are more alienating |
| **Completeness ↔ Gap Visibility** | L3 (Schema maturity) | Perfect schema hides incompleteness; flawed schema makes gaps obvious | Improvement deepens concealment |
| **Representation ↔ Practice** | L4 (Meta-level) | Schema completeness assumes practice is unnecessary; visible gaps force practice | No schema can contain the work |

---

## BOTTOM LINE

**A todo app's data model assumes work is representable. It isn't.**

The schema works brilliantly for work that *is* discrete, prespecified, independently completable, and actor-declarable. This includes maybe 20-30% of human effort in knowledge work.

The 70-80% that doesn't fit gets **progressively less visible as the schema improves**. This is the deepest problem: a better todo app is a better invisibility machine.

The real work—emotional labor, negotiation, sense-making, recovery, meaning-making—happens in the gaps between what the schema predicts and what actually happens. That gap is the schema's actual value. But the schema's designers are optimizing to close the gap, making its value invisible.

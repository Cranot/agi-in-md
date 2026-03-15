# Rejected_Paths Lens: Self-Analysis

I'll apply the rejected_paths framework **to the rejected_paths lens itself**. This is a reflexive exercise at L11-C level.

---

## 1. The Enumeration Problem

**Concrete problem:** The lens asks to "design the artifact taking all rejected paths" — but the space of alternative designs is infinite.

**Resource scarcity assumed:** 
- Cognitive budget (you can explore all paths before deciding)
- Time to analyze divergence (you can afford to map every branch)

**Rejected path that would have prevented it:**
- Rank rejected paths by consequence magnitude, not enumerate all
- **But creates:** You now predict which paths matter without exploring them — misses silent failures that only manifest at scale

**Alternative design (opposite scarcity gamble):**

Instead: "Enumerate only rejected paths that practitioners have actually tried in similar artifacts. Rank by frequency of rediscovery."

```
CONCRETE RESULT:
Problem: Database coupling in ORM layer
├─ Rejected (attempted 1000s times): Switch to query builder
│   └─ Creates: migration burden, query validation gaps (discovered by 87% of teams)
├─ Rejected (attempted ~200 times): Switch to raw SQL  
│   └─ Creates: injection risk, inconsistent validation (discovered by ~20% under pressure)
├─ Rejected (attempted ~5 times): Polyglot persistence per entity
│   └─ Creates: distributed transaction nightmare (discovered by 1% after catastrophe)
│
ROOT PATTERN: Visibility follows frequency, not logic
```

**Visible problems that vanish:** False completism (the illusion that you've explored all meaningful alternatives)

**Invisible dangers that emerge:** 
- Bias toward already-discovered problems (you miss novel failure modes)
- Survivorship bias in the frequency data (you only see paths practitioners tried AND reported)
- Path popularity ≠ path consequence (common failures might be minor; rare failures catastrophic)

---

## 2. The Prophecy Problem

**Concrete problem:** The lens asks "which invisible dangers emerge?" — implying you can predict what will actually break without empirical deployment.

**Resource scarcity assumed:**
- Prophetic capacity (analytical reasoning can predict emergent behavior)
- Completeness of model (you can simulate all failure modes by thinking harder)

**Rejected path that would have prevented it:**
- Empirically test all rejected paths in production before launch
- **But creates:** Each failed path is a production incident; customer impact; opportunity cost

**Alternative design (opposite scarcity gamble):**

Instead: "For each rejected path, name the minimum condition under which it breaks. Rank by condition likelihood in target deployment."

```
CONCRETE RESULT:
Problem: Caching layer with write-through consistency
├─ Path A (cache-first): Breaks when cache diverges from DB
│   └─ Minimum condition: Concurrent writes + cache invalidation failure
│   └─ Likelihood in your system: HIGH (you have 3 write sources)
│
├─ Path B (DB-first): Breaks when read load exceeds DB capacity  
│   └─ Minimum condition: >1000 req/sec
│   └─ Likelihood in your system: LOW (current peak 150 req/sec, but growth projection = 18 months to HIGH)
│
└─ Path C (eventual consistency): Breaks silently in certain user journeys
    └─ Minimum condition: User reads own-write within 50ms
    └─ Likelihood in your system: DEPLOYMENT-DEPENDENT (mobile: LOW, browser: HIGH)
```

**Visible problems that vanish:** Vague warnings about "invisible dangers" (now they're located on deployment axes)

**Invisible dangers that emerge:**
- The minimum conditions you identify are guesses until tested
- Condition interactions are ignored (two LOW conditions might create HIGH joint failure)
- Deployment context changes faster than your minimum-condition model
- Under pressure, practitioners deploy Path B because "it's safe according to our conditions" — then hit the one condition you missed

---

## 3. The Discovery Order Problem

**Concrete problem:** The lens asks "predict which migration a practitioner discovers first under pressure" — assumes practitioners discover problems in a logically-ordered sequence.

**Resource scarcity assumed:**
- Epistemically accessible problems (what's important becomes visible first under pressure)
- Uniform deployment context (all practitioners encounter problems in same order)

**Rejected path that would have prevented it:**
- Design without predicting discovery order; just enumerate migrations
- **But creates:** No guidance when practitioner must prioritize (infinite regress on which danger to address first)

**Alternative design (opposite scarcity gamble):**

Instead: "Predict which failure mode breaks which specific user journey first. Rank by revenue/reputation damage, not logic order."

```
CONCRETE RESULT:
Problem: Event ordering in distributed system
├─ Logical discovery order: Event A depends on Event B ordering → need consensus
├─ User journey impact ranking:
│   1. Payment processing (HIGH): Orders arrive out-of-sequence → revenue leak
│   2. Analytics (MEDIUM): Event order wrong → reports show wrong trends
│   3. Audit trail (LOW): Historic ordering doesn't match real sequence
│
Under pressure (system on fire):
- Practitioner fixes #1 first (payment) → temporarily breaks #3 (audit)
- NOT the logical first discovery, but the revenue-first discovery
```

**Visible problems that vanish:** Pretending practitioners have agency over discovery order (they don't — their deployment breaks in specific ways)

**Invisible dangers that emerge:**
- You create a two-tier problem class (what's urgent vs. what's correct)
- Fixing urgent problems often breaks correct ones (the fixes are structurally incompatible)
- Your ranking becomes political (is reputation or revenue more important?) rather than technical

---

## 4. The Fixed Compression Level Problem

**Concrete problem:** The lens applies 4 fixed operations (identify → trace decision → design alternative → name law) to all artifacts.

**Resource scarcity assumed:**
- That 4 operations compresses adequately for any artifact
- That cognitive load is equally distributed across all artifact types

**Rejected path that would have prevented it:**
- Adaptive compression (adjust operation count by complexity)
- **But creates:** User must choose compression level (meta-cognitive load); some choices are wrong in hindsight

**Alternative design (opposite scarcity gamble):**

Instead: "Use 2 operations for simple artifacts, 6+ for complex. Let the artifact's internal structure determine depth."

```
CONCRETE RESULT - Simple artifact (3-function auth handler):
├─ Problem: Hardcoded salt
├─ Decision: "Keep implementation simple"
└─ Trade-off: Convenience vs. security
(STOPS HERE - 2 operations)

Complex artifact (event sourcing with CQRS):
├─ Problem: Command handler writes to read model synchronously
├─ Decision: "Ensure read-write consistency"
├─ Alternative: Event bus decouples writes
├─ Trade-off: Consistency deadline vs. eventual consistency window
├─ Migration: Failure modes across system depend on window length
├─ Law: Any consistency window creates "during-replication" failures
├─ Sub-law: Window length is conserved (you shift it, don't eliminate it)
└─ Invariant: Total consistency surface area is constant
(CONTINUES - 6+ operations)
```

**Visible problems that vanish:** Oversimplification of complex systems; over-analysis of simple ones

**Invisible dangers that emerge:**
- Determining artifact complexity is itself an analytical problem (garbage in)
- Different analysts choose different depths (no reproducibility)
- You now have a meta-lens (how to apply the lens) which itself needs a meta-lens

---

## 5. The Singular Law Problem

**Concrete problem:** The lens forces a single "conservation law" — assumes design space has one underlying invariant.

**Resource scarcity assumed:**
- Unitary structure (the design space has one dimension of constraint)
- Observer capacity (you can see the whole space at once)

**Rejected path that would have prevented it:**
- Enumerate multiple conservation laws
- **But creates:** Output becomes unprioritized list; practitioner can't decide which law matters most

**Alternative design (opposite scarcity gamble):**

Instead: "Identify all conservation laws. Rank by how many problems violate them when ignored."

```
CONCRETE RESULT - Caching layer:
│
├─ Law 1 (PRODUCT form): latency × consistency = k
│   Violations if ignored: Cache hit/miss decision becomes wrong
│   Impact: 40% of performance issues in your logs
│
├─ Law 2 (SUM form): invalidation_complexity + consistency_guarantee = k'  
│   Violations if ignored: Invalidation strategy choice breaks under scaling
│   Impact: 20% of operational incidents
│
├─ Law 3 (MIGRATION form): Complexity moves from "what cache knows" to "what app must know"
│   Violations if ignored: Cache becomes source of truth for wrong reasons
│   Impact: 60% of correctness bugs
│
RANKING: Law 3 > Law 1 > Law 2 (by impact frequency)
```

**Visible problems that vanish:** Forced simplification that hides the multi-dimensional structure

**Invisible dangers that emerge:**
- You now ignore laws ranked lower (and rare scenarios violate the low-ranked laws catastrophically)
- Laws interact (changing Law 1 parameters breaks Law 3 invariants)
- The ranking you do today becomes obsolete when code changes (new code violates different laws)

---

## 6. The Pareto Trade-Off Assumption

**Concrete problem:** The lens presupposes every rejected path creates a trade-off (fix problem A → create problem B).

**Resource scarcity assumed:**
- That design space is Pareto-bounded (all alternatives are dominated somewhere)
- That improvements are zero-sum

**Rejected path that would have prevented it:**
- Identify Pareto-improving paths (better in multiple dimensions)
- **But creates:** You miss hidden multi-dimensional trade-offs (e.g., complexity tax, maintenance burden) that don't show up in your primary metric

**Alternative design (opposite scarcity gamble):**

Instead: "Separate Pareto improvements from trade-offs. For improvements, find the hidden dimensions where trade-offs appear."

```
CONCRETE RESULT - Request routing:
│
├─ Rejected Path A: Direct function calls
│   Visible metrics: Latency ✓✓✓, Throughput ✓✓✓
│   Trade-offs: Coupling ✗, Testability ✗
│
├─ Rejected Path B: Message queue
│   Visible metrics: Latency ✗, Throughput ✓✓
│   Trade-offs: Coupling ✓✓, Testability ✓✓
│   APPEARS Pareto-dominated by A (worse on latency)
│
├─ BUT: Hidden dimensions:
│   Path A: Maintenance cost grows O(n²) with services, refactoring nightmare
│   Path B: Maintenance cost grows O(n), easier to add services
│   Path B: Backwards compatibility ✓✓ vs A: ✗
│
AT SCALE (50 services): Path B is Pareto-improving on 4 dimensions
EARLY STAGE (3 services): Path A is Pareto-improving on latency/complexity
│
CONSERVATION LAW: Latency improvement is conserved by deferring it
(You move latency cost from "now" to "when you scale")
```

**Visible problems that vanish:** Assuming immediate metrics (latency, throughput) are the only dimensions

**Invisible dangers that emerge:**
- You choose Path B early for "correctness," then discover latency becomes bottleneck at scale
- Or you choose Path A early for "pragmatism," then can't refactor when scope explodes
- The hidden dimensions only become visible when scaling phase changes

---

## Conservation Law of the Lens Itself

**What is preserved across all alternative designs?**

The **problem-visibility surface area** is invariant.

You do not eliminate problems. You migrate them between:
1. **Visible-at-design-time** (can reason about analytically)
2. **Visible-at-test-time** (emerges under load/coverage)
3. **Visible-at-production-time** (emerges under real usage)

The rejected_paths lens maximizes category 1. The alternatives I designed attempt to migrate problems TOWARD category 1 by predicting which will matter (using frequency, deployment context, revenue impact).

**But the invariant is:** Total surprise = constant.

For every problem you move from category 2→1 (by analyzing more carefully), you either:
- Spend more analysis time (cost increase)
- Ignore a new problem in category 3 (shifted risk)
- Make a false prediction that creates misdirection (wasted effort)

The lens cannot break this invariant. It can only redistribute attention.

---

## Six-Month Prediction: What Remains Unmovable

Regardless of how rejected_paths is redesigned, **this will not change:**

**Practitioners will continue discovering problems exclusively in these orders:**

1. **Revenue-path problems first** (payment broken → fix immediately, whether analysis said it was "second priority")
2. **Deployment-context-specific problems second** (your production hits a condition your analysis missed)
3. **Scalability problems third** (after 10x growth exposes what analysis deemed "low risk")
4. **Hypothetical problems last** (the ones analysis predicted but deployment never triggers)

The rejected_paths lens can't change this because it's not a limitation of the lens — it's a structural property of **deployment variance**.

The practitioners implementing your design across 10,000 companies will hit different problems in different orders because:
- Their deployment patterns differ (edge cases)
- Their load profiles differ (threshold crossings)
- Their revenue models differ (priority rankings)
- Their team skill distribution differs (what's "possible to fix" locally)

**What remains unmovable:** The necessity of post-deployment discovery. Analytical foreknowledge plateaus; empirical discovery cannot be eliminated.

The best rejected_paths lens can do is move the plateau higher. It cannot move practitioners from "analytical discovery only" to "zero production surprises."

This is a conservation law: **Analytical capacity × Empirical discovery velocity = constant.**

You can increase analytical capacity (better lenses), but you trade against empirical discovery velocity (you spend more time analyzing, less time deploying and learning from failures).

The optimal lens design would accept this trade-off explicitly rather than pretending analysis alone suffices.

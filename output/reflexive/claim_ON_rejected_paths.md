# Analysis: Rejected Paths Lens as Artifact

I'll apply the full diagnostic framework to the rejected_paths prompt itself—treating it as an artifact with embedded claims about timing, causality, resources, and human behavior.

---

## STEP 1: Empirical Claims Extraction

The prompt embeds 10 core claims:

| # | Claim | Type |
|---|-------|------|
| **1** | Every concrete problem traces to a traceable decision | Causality |
| **2** | Rejected paths exist that prevent visible problems but create invisible ones | Trade-off universality |
| **3** | You can "design taking all rejected paths" (synthesis is possible) | Resource/Feasibility |
| **4** | Problems exist on a stable visible/invisible spectrum per design | Observability |
| **5** | Problems migrate, not vanish (conservation law holds) | Causality |
| **6** | Under pressure, practitioners discover migrations in a predictable order | Behavioral/Timing |
| **7** | Rejected paths are cognitively reconstructible retrospectively | Cognition |
| **8** | Practitioners will reliably follow this diagnostic sequence | Behavioral |
| **9** | Visible and invisible are orthogonal dimensions (not overlapping) | Structural |
| **10** | The rejected space is enumerable (can "take all" into account) | Resource/Completeness |

---

## STEP 2: When False—Corruption Traced

### **Claim 1 False: No single decision caused the problem**
**Corruption unfolds:**
- Engineer traces "Why did the circuit breaker fail?" → 5 decisions are equally necessary (architecture choice, timeout config, fallback strategy, deployment context, monitoring gaps)
- The diagnostic stalls at **attribution ambiguity** — you're forced into false causality (one scapegoat decision) or infinite regress (each decision caused by a prior decision)
- **Concrete result**: Team meeting: "Was it the decision not to add backpressure?" "No, it was also that we didn't know we needed it." "Why not?" "Resource constraints." "Why?" → deadlock.
- The prompt assumes causal granularity that distributed systems don't have.

### **Claim 2 False: Rejected paths don't all create invisible problems**
**Corruption unfolds:**
- Some rejected designs were rejected because they *don't work*, not because they trade visibility
- You're forced into a false dichotomy: every rejected path must hide something
- **Concrete result**: "Should we use a message queue?" → "That would create latency-invisibility problems." But no—a queue either works or it doesn't. If unbounded, it crashes (visible). If bounded, it drops messages (visible). No hidden trade-off; just a bad design.
- You spend cognitive effort hypothesizing trade-offs that don't exist.

### **Claim 3 False: You cannot synthesize contradictory rejected paths**
**Corruption unfolds:**
- If path A = "sync dispatch (fail-fast)" and path B = "async dispatch (graceful degrade)", they're implementation-level contradictions
- "Taking both" creates a layered system: extra failure modes, coordination overhead, slower than either pure choice
- **Concrete result**: You design a Frankenstein (dual-path logic, feature flags), discover it's worse than the original single choice, abandon synthesis.
- The prompt offers a solution to a problem that requires choosing, not synthesizing.

### **Claim 4 False: Visible/invisible boundary is unstable**
**Corruption unfolds:**
- Cache invalidation is "invisible to users" but visible to ops
- Visible to ops until traffic patterns change
- Visible to the service owner, invisible to the infrastructure team
- The visibility depends on: who's observing, what instrumentation exists, current operational context
- **Concrete result**: You name a "hidden problem" that's actually just "unmonitored." When you add one metric, it becomes visible. The problem wasn't hidden; observation was.

### **Claim 5 False: Problems are not conserved; some are solved**
**Corruption unfolds:**
- The prompt's hidden law assumes: every solution trades visibility (move problem from here to there)
- But some problems are genuinely solvable: if you use immutable data + content addressing, cache invalidation becomes structurally impossible, not hidden
- **Concrete result**: You're trained to see migration where solution occurred. You add instrumentation to find "the hidden cache-invalidation problem" that doesn't exist because the problem was solved.
- The conservation metaphor fails when you change the problem's root structure.

### **Claim 6 False: Practitioners discover migrations in analytical order, not urgency order**
**Corruption unfolds:**
- At 2am on Friday, the engineer doesn't discover "adding rate-limiting creates hidden backlog risk"
- They discover "queue is at 100k items" (operational fire)
- They fix by raising queue limit; the actual migration (to degradation risk) stays invisible
- **Concrete result**: The lens predicts order of discovery that doesn't match reality. Practitioners find whatever is currently damaging, not whatever the analysis says is next.

### **Claim 7 False: Rejected paths fade and cannot be reconstructed**
**Corruption unfolds:**
- Most decisions to reject a path happened months ago and are now forgotten
- The engineer who rejected async dispatch? Left the company
- The Slack argument? Archived, unsearchable
- **Concrete result**: You invent plausible-sounding rejected paths that were never actually considered. The analysis becomes reverse-engineered fiction.
- You're analyzing the decision space as if it's still accessible; it's collapsed into history.

### **Claim 8 False: Practitioners won't follow the diagnostic (SLOWEST FAILURE)**
**Corruption unfolds:**
- The prompt prescribes: identify → trace → hypothesize → design synthetically
- But practitioners follow incentives, not abstract diagnostics
- The problem doesn't affect their KPI, so it doesn't become actionable
- **Concrete result**: The lens produces brilliant insight with zero path to change. The insight becomes a form of technical debt ("we know about this but haven't fixed it"). Over iterations, using the lens becomes demoralizing.
- **This is the slowest failure**: it doesn't break down immediately. It silently accumulates as analysis-action gap, creating cynicism, until the lens stops being used.

### **Claim 9 False: Visible/invisible are not orthogonal**
**Corruption unfolds:**
- Newly-broken is visible (red errors everywhere)
- Chronically-broken is invisible (everyone's adapted to workarounds)
- But they're the same problem. The dimension is not visible/invisible but recent/adapted-to
- **Concrete result**: You classify "hidden" problems that are actually just problems people have learned to live with. The visibility isn't binary—it's a function of time and acculturation.

### **Claim 10 False: The rejected space is not enumerable**
**Corruption unfolds:**
- Every design choice between 3 architectures rejects 2
- Each architecture has 10 internal choices
- Total rejected space: exponential, uncountable
- "Taking all rejected paths into account" is mathematically impossible
- **Concrete result**: You attend to 3-4 salient rejected paths and call it "comprehensive." You miss the ones that actually matter because they were rejected without being consciously considered.

---

## STEP 3: Three Alternative Designs

Each inverts one core claim and shows concrete results:

### **Design A: Invert Claim 1 (Causality → System Properties)**

**Inversion**: Problems don't trace to decisions; they emerge from system properties in tension.

```
Identify every concrete problem. For each, map the system property enabling it.
What system properties would prevent it, but create tension elsewhere?
Design by naming property axes in opposition, not by tracing decisions.
Show which axes cannot be simultaneously optimized.
Name the law: which property becomes critical first under load?
```

**Concrete result** (Circuit Breaker example):
- **Original**: "Why does the CB fail? → Because we didn't add backpressure (decision)"
- **Alternative A**: "CB has properties: Fail-Fast (open circuit immediately) + Fail-Closed (always try). Tension: Cannot simultaneously fail-fast AND degrade-gracefully. Under sustained load, Fail-Fast wins—unavoidable."

**What vanishes**: False attribution to individual decisions
**What emerges**: Structural responsibility—"we're paying for property X, the cost is Y"
**Hidden assumption revealed**: The original assumes decisions are the unit of analysis. This shows that system-level properties are.

---

### **Design B: Invert Claim 2 (All rejected paths trade → Only some trade)**

**Inversion**: Some rejected designs are purely bad; not all trade visibility.

```
Identify every concrete problem. For each, identify the rejected design that prevents it.
Check: would that design create a different problem?
If yes → it's a trade-off. Name the conservation law.
If no → it's a pure improvement. Name why it was rejected. Why is it still rejected?
Design taking improvements you can get, not hypothesizing improvements you cannot.
Which problems vanish? Which problems are inherent?
```

**Concrete result**:
- **Original**: "Cache invalidation is invisible if we use a queue"
- **Alternative B**: "Does queuing prevent cache invalidation? No—queue just hides it. That's a trade-off. Does optimizing dispatch prevent latency entirely? Yes. So latency is solvable, cache-invalidation is not."

**What vanishes**: Assumption that every solution is suspicious (hides something)
**What emerges**: Ranking problems into solvable vs. inherent
**Hidden assumption revealed**: The original assumes all design is constrained by universal conservation laws. This shows some problems are genuinely solvable.

---

### **Design C: Invert Claim 6 (Analytical discovery order → Operational urgency order)**

**Inversion**: Practitioners discover problems by what's on fire now, not by analysis sequence.

```
Identify every concrete problem. For each, estimate:
- Time-to-operational-fire (when does this become urgent?)
- What conditions reveal it? (operating context, scale, timing)
- Who detects it first? (monitoring gap, role boundary)
Design to minimize time-to-detection, not time-to-diagnosis.
Which problems are already visible (just unmonitored)?
Which require instrumentation to see?
Which will never be visible without cascade failure?
```

**Concrete result**:
- **Original**: "Under pressure, practitioners discover [migration sequence you predicted]"
- **Alternative C**: "Rate-limiting creates backlog → queue depth is visible today (unmonitored). Cascading failures across 5 services → invisible until postmortem. Design around what's discoverable first, not what's analytically next."

**What vanishes**: Assumption that visibility is fixed; shows it's a function of instrumentation
**What emerges**: Operational maturity as the real constraint
**Hidden assumption revealed**: The original assumes calm reflection during crisis. This shows the analysis must survive operational pressure.

---

## STEP 4: The Core Impossibility

**What does the artifact try to optimize?**

The rejected_paths lens tries to achieve **predictive visibility**: find problems before they hit operationally.

**The core impossibility it faces:**

You cannot simultaneously have:
1. **Transparency** — all problems visible
2. **Simplicity** — reasoning about them is tractable  
3. **Power** — the system does useful work

**Why**: A system with zero problems does nothing. A system that does work necessarily has failure modes only visible at scale, under specific timing, with certain data distributions. These aren't "decisions someone made poorly"—they're structural to the fact that the system has power.

**The hidden attempt**: The lens tries to *reason backward* from invisible failures to visible ones. But visibility isn't a design property—it's a relationship between system properties and observational context. You cannot make a system "transparent about its own failure modes" before those modes are triggered operationally.

**The real constraint**: You're choosing between:
- *Discovering problems analytically* (requires depth, misses urgency)
- *Discovering problems operationally* (requires fire, gives urgency)

The artifact assumes the first; reality enforces the second.

---

## STEP 5: The Slowest, Most Invisible Failure

**Culprit: Claim 8 (Behavioral compliance)**

**Why this one fails slowest and most invisibly:**

1. **Other false claims break immediately**: Causality ambiguity, enumeration impossibility—these create cognitive friction the engineer notices.

2. **Claim 8 doesn't break; it silently fails to convert to action**:
   - Engineer uses lens → generates brilliant insight
   - Insight doesn't affect roadmap, KPIs, or sprint planning
   - Insight becomes "technical debt: we know this problem exists"
   - Gap between what's analyzed and what's changed widens each iteration

3. **The corruption deepens over time**:
   - Iteration 1: 5 brilliant insights, 0 implemented
   - Iteration 2: Engineer stops using the lens (why find problems you can't fix?)
   - Iteration 3: Organization loses diagnostic capability
   - Iteration 4: Now when a crisis hits, the problems the lens would have caught are discovered operationally instead

4. **The failure is invisible because**:
   - No immediate signal that the behavior change didn't occur
   - The lens output *looks* valuable (reads well, thorough, insightful)
   - The problem is in the system (incentives don't align), not in the lens itself
   - By the time you notice, you've sunk months of trust into the tool

**Concrete timeline**:
```
Week 1: "Wow, this lens found the cache-invalidation problem."
Week 4: "Still haven't scheduled time to fix it, but the analysis was correct."
Week 12: "We keep finding issues we don't fix. Why do we keep analyzing?"
Week 16: Lens stops being used.
Week 20: Latent cache-invalidation problem causes production incident.
Week 21: Postmortem: "We knew about this problem from the lens analysis 16 weeks ago."
```

**The invisible cost**: Not in the analysis—in the gap between insight and action, multiplied across all practitioners, across all problems, across all iterations.

---

## STEP 6: The Law of Problem Migration (Inverted)

**What the original claims:**
> "What class of problem migrates between visible and hidden?"

**What the corruption reveals:**

**Problems don't migrate. Attention does.**

The law is: **A problem is invisible not when it's in the system, but when it's not in the currently-active observational context.**

Examples:
- Cache invalidation: invisible to users (they don't see it), visible to ops (it's in the logs)
- Latency: invisible at 100 req/s, visible at 10k req/s
- A bug in the error path: invisible in happy-path testing, visible in chaos testing
- Degradation: invisible as it creeps (people adapt), visible on day 1 of the new bug

**The actual law**: Visibility is a three-body problem:
```
Visibility = f(Problem Properties, Observer Position, Operational Context)
```

Not: "Problem is hidden" but "Problem is not currently observed."

**What practitioners discover first under pressure:**
The problem that's **actively causing damage right now**, not the problem the analysis says is next. This is why reactive monitoring outperforms predictive analysis in practice—it aligns with reality.

---

## Summary: What This Inversion Reveals

The rejected_paths lens assumes:
- **Decisions cause problems** → Reality: Systems cause problems (decisions distribute the cost)
- **All rejected paths trade** → Reality: Some problems are solvable, some aren't
- **You can predict discovery order** → Reality: Operational urgency determines discovery order
- **Practitioners follow analysis** → Reality: Practitioners follow incentives
- **Visibility is a design property** → Reality: Visibility is a relationship with observation
- **Problems can be anticipated** → Reality: Problems manifest when triggered operationally

**The lens's true value**: Not predictive visibility, but **deepening your model of the design space**. It doesn't prevent problems; it makes you a better designer by showing you *what you're paying for* to have the system you have.

**Its invisible danger**: Making you feel you've solved a problem by analyzing it, when in reality you've only understood it.

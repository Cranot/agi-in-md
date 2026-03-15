# Structure First: Meta-Conservation Law Analysis of the Transformer

---

## STEP 1 — THE INITIAL CLAIM

**Falsifiable claim:** The Transformer's deepest structural problem is that position information is injected as an additive signal at input but must function as a preserved, recoverable distinction throughout computation. There is no architectural mechanism enforcing this preservation — the network must learn it, but the architecture does not require it. 

*Falsifiable prediction:* If position encoding were architecturally necessary, ablating it should degrade performance monotonically with sequence length. But causal masking provides implicit ordering information, so ablation effects should be nonmonotonic — revealing that position encoding and causal structure are partially redundant.

---

## STEP 2 — THREE EXPERTS

**Expert 1 (Defends):** Correct, and the residual stream hypothesis sharpens it. Position enters as an additive perturbation to token embeddings. Q and K projections read from this mixed residual signal. After repeated attention aggregation — weighted averaging across attended tokens — position information disperses into the collective representation. The sinusoidal scheme exacerbates this: high-frequency components produce similar encodings for distant positions, and softmax further blurs distinctions. The failure at sequences beyond training distribution is exactly this: the encoding cannot maintain distinctiveness after repeated aggregation.

**Expert 2 (Attacks):** Wrong target. Causal masking partially solves positional disambiguation — token *i* can only attend to tokens ≤ *i*, so position is implicitly encoded in what information is *available*, not what is *injected*. The real problem is that **feedforward layers have no spatial structure**. They operate identically at all positions. Any computation requiring comparison of non-adjacent positions must route through attention, creating a bottleneck that position encoding doesn't address. The underdetermination isn't about survival of position signals; it's about where position-sensitive computation can happen.

**Expert 3 (Probes what both take for granted):** Both experts treat position as a property of **tokens** that must be represented. But position in this architecture is actually a property of **computation** — specifically, of the relationship between token pairs at attention time. The Transformer doesn't store "token X is at position 7." It computes "the attention score between X and Y, given their positional difference." Position is reconstructed relationally at each attention operation, not preserved from layer to layer as a stable property. Both defenders and attackers are reifying position as a first-class object when the architecture treats it as a transient, relational computation.

**Claim transformation:** 

*Original:* Position information is underdetermined because it must survive aggregation.

*Transformed:* Position is a **relational property computed at attention time** but injected as an **absolute property at input time**. The architecture requires a translation between these two regimes — absolute injection vs. relational use — with no architectural basis for that translation.

**The gap is diagnostic:** I was thinking about position as a *thing to preserve*. The transformed claim reveals position is a *computation to perform*. The gap shows I imported the assumption that representation and computation are separable, which the architecture doesn't assume.

---

## STEP 3 — NAMING THE CONCEALMENT MECHANISM

**Explanatory aliasing via residual mixing:**

The architecture adds position information to content information in the residual stream, making them indistinguishable to any downstream computation. Every layer reads a mixed signal — part content evolution, part positional residue. No component can distinguish why a representation changed: was it content learning or positional corruption?

This conceals the core problem: the architecture simultaneously uses position as absolute (injection at input), relative (attention dot products), and invisible (feedforward layers receive it but can't know it's there). Three different position regimes coexist inside the same computational pathway, and the homogeneity of the layer structure makes this invisible. The architecture *looks* like it has one approach to position. It actually has three, in tension.

---

## STEP 4 — THE IMPROVEMENT THAT DEEPENS CONCEALMENT

**Rotary Position Embedding (RoPE):** Instead of adding position to the residual stream, encode position as a rotation applied to Q and K before the dot product.

For query at position *i* and key at position *j*:

```
Q_i = R(i) · (x_i · W_Q)
K_j = R(j) · (x_j · W_K)
score(i,j) = Q_i · K_j = q_i · R(i-j) · k_j
```

The attention score depends only on relative position (i−j). Position never enters the residual stream. The architecture is clean: attention handles relational position, FFN handles content. This is the improvement in LLaMA, GPT-NeoX.

**Why it passes code review:** Mathematically principled, eliminates additive mixing, empirically superior for long sequences, solves the stated problem.

**Why it deepens concealment:** By moving position out of the residual stream entirely, RoPE makes the absolute/relational position tension **structurally invisible**. The architecture now formally commits to relational position, and the competing regime (absolute) simply disappears — not resolved, removed. The concealment is now architectural, not just behavioral.

---

## STEP 5 — THREE PROPERTIES VISIBLE BECAUSE WE TRIED TO STRENGTHEN IT

**Property 1: Position information is inherently bimodal, and the original architecture's ambiguity was load-bearing.**
The original architecture tried to serve both absolute and relative position. When we eliminated absolute position (RoPE), feedforward layers became provably position-blind. In the original, they were *effectively* position-blind — FFN rarely extracted position from the residual stream in practice. RoPE reveals this was always true; the original architecture carried the *appearance* of absolute position availability without the reality.

**Property 2: The residual stream is the only global state channel.**
When we tried to remove position from the residual stream, we were forced to place all position computation inside attention. This makes explicit that attention and FFN share *exactly one interface*: the residual stream. There is no other communication channel. The improvement shows the architecture's connectivity is more restricted than the layer diagram suggests.

**Property 3: Absolute and relative position make structurally different predictions.**
Forcing the choice of relative position reveals that the two regimes are not equivalent approximations. Absolute position predicts better generalization to position-specific syntactic rules ("subject often appears near position 0"). Relative position predicts better extrapolation to unseen sequence lengths. The original architecture's failure to commit was not naïvety — it was an implicit bet-hedging on which kind of position information downstream tasks would require.

---

## STEP 6 — WHAT THE RoPE IMPROVEMENT CONCEALS, AND WHAT IT RECREATES

**Concealment:** RoPE makes position computation invisible to feedforward layers. This hides that identity and relational position are not independent: "bank" means different things depending on absolute position and surrounding content. By hardwiring relational position into attention, RoPE forces the model to reconstruct any absolute-position-dependent patterns through context accumulation across layers — something that requires more depth to achieve what absolute encoding does in one forward pass.

**Property recreated from the original:** FFN position-blindness. In the original architecture, FFN layers could theoretically extract positional information from the residual stream. In RoPE, this is impossible by design. The diagnostic reveals: FFN layers in the original architecture were *already* functionally position-blind — the architectural possibility existed but was not utilized. RoPE makes formally true what was empirically true. The original problem, not the encoding scheme, is the source.

---

## STEP 7 — THE SECOND IMPROVEMENT

**Problem recreated:** FFN layers cannot perform position-sensitive computation.

**Second improvement — Position-conditioned feedforward:** Inject positional bias into the FFN hidden layer:

```
FFN(x_i) = W_2 · σ(W_1 · x_i + b_pos(i))
```

where `b_pos(i)` is a learned or constructed positional bias vector. Different positions activate different hidden units — FFN now implements position-specific transformations.

**What this conceals:** The improvement assumes that *which computations should be position-sensitive* is fixed — determined by the architecture's assignment of positional bias to FFN. But this is wrong: whether a computation should be position-sensitive is *content-dependent*. Determining the subject-verb agreement of "the bank that the man visited collapsed" requires position-sensitivity; determining that "bank" is a noun does not. The same input word requires different sensitivity levels depending on which computation is being performed. Position-conditioned FFN can't distinguish between these cases — it applies position bias uniformly, regardless of whether the computation warrants it.

---

## STEP 8 — THE STRUCTURAL INVARIANT

The property that persists through every improvement:

**The partition of computations into {position-sensitive, position-invariant} is architecturally unconstrained — it is a property of the weights, not the structure.**

Track it through improvements:
- **Additive encoding:** Position is mixed into everything — the partition is implicit in whatever the weights learn to ignore
- **RoPE:** Position is excluded from FFN — the partition is enforced but wrong (FFN sometimes needs position)
- **Position-conditioned FFN:** Position is available everywhere — the partition is again implicit in whatever weights learn to ignore

In all three cases, the architecture never represents the *boundary* between position-sensitive and position-invariant computation. The correct partition is content-dependent, but the architecture provides no mechanism for making this determination content-conditionally. This must be learned, might be learned wrong, and has no architectural enforcement.

**Formally:** The partition Π: {computations} → {sensitive, invariant} is a property of the weight matrix, not the computation graph. No structural invariant enforces the partition's correctness.

---

## STEP 9 — INVERT THE INVARIANT

**The invariant:** The partition into position-sensitive/invariant is architecturally unconstrained.

**Inversion:** A design where every computation is architecturally labeled and enforced.

**Factored computation streams:**

```
P-stream (position-sensitive): attended with RoPE, relative position explicit
S-stream (position-invariant): attended with no position signal  
Cross-stream gate: learned mixing at each layer output
Final representation: f(P-stream, S-stream)
```

Attention operates on P-stream with relational position. FFN operates on S-stream without position. Gating controls which stream dominates for any given token's representation. The partition is now architecturally enforced: some computation is positional, some is not, and the structure reflects this.

**New impossibility the inversion creates:**

The inversion assumes the partition is *content-independent* — that we can decide at architecture time which computations are positional. But the partition must be content-dependent: the correct decision about whether to use positional information depends on what is being computed, which depends on the content being processed. A fixed architectural partition means the model cannot dynamically decide which stream to use based on content. The gate makes this content-conditional — but then the gate's decision is unenforceable, and we're back to a learned, unconstrained partition implemented by a different mechanism.

**New impossibility:** *A fixed architectural partition of position-sensitivity cannot accommodate content-conditional sensitivity decisions. Making it content-conditional (via gating) eliminates the enforcement, restoring the original invariant by different means.*

---

## STEP 10 — THE CONSERVATION LAW

**Original impossibility:** Cannot architecturally enforce where position matters (partition is in weights, not structure).

**Inverted impossibility:** Cannot enforce the partition even when it is architecturally explicit, because the correct partition is content-dependent and enforcement requires content-independence.

**Conservation Law:**

*The information required to correctly decide where position matters is not available when the decision must be made.*

More precisely: correct position-sensitivity decisions are content-conditional. Making them content-conditional requires content-processing. But the architectural partition of where position-sensitivity applies must be made before content is processed (it is structural) or at the time of content processing (in which case it is a learned weight, not a structural guarantee). 

No static architecture can correctly partition position-sensitivity because it must choose: enforce at structure-time (content-independent, therefore potentially wrong) or decide at compute-time (content-conditional, therefore unenforceable architecturally).

**This is a causal ordering constraint, not an engineering limitation.** The structure must be fixed before the data arrives. The correct partition depends on the data. Therefore, the correct partition cannot be built into the structure.

---

## STEP 11 — DIAGNOSTIC ON THE CONSERVATION LAW ITSELF

**What the conservation law conceals:**

The law frames the problem as one of *representation* — how to represent position-sensitivity. But this conceals a more primitive assumption: the law takes "position" as a given object that computations are or aren't sensitive to. It does not question whether position is a primitive of information flow or a derived concept.

Position in a Transformer is a proxy for **information availability ordering** — the causal precedence structure of token generation. Tokens don't have positions; they have causal precedence relations to other tokens. Position encoding is an attempt to inject ordering information into a permutation-equivariant system — a workaround, not a solution.

The conservation law conceals that position is derived from something more primitive: the causal structure of which tokens can see which other tokens. The law requires position to be primitive in order to state the impossibility. If we dissolve "position" into its underlying structure (causal access graphs), the conservation law's framing collapses.

**Structural invariant of the conservation law:**

When I try to improve the conservation law — to state it more precisely, more generally, more deeply — I always arrive at a formulation that still requires position to be a first-class object. The law cannot be restated in terms of causal ordering without losing its conservation character. The invariant that persists: **the law assumes position is a representational primitive, but position is a derived property of information availability sequences.**

**Invert the invariant:**

Design where position is not primitive but derived from causal access: a Transformer with no position encoding whatsoever, where the only ordering information comes from causal masking. Position is implicit in the set of prior tokens available at each position. This already exists in some models — and empirically, such models learn positional information from the masking structure alone.

**New impossibility created by this inversion:**

If position is entirely derived from causal access patterns, then position is *sequence-specific* — a token's positional identity is a function of the entire sequence in which it appears. No local computation can determine a token's position without global information. In an autoregressive system, global information isn't available until the entire sequence is processed. The model must process a sequence to know the positions within it — but position-sensitive processing requires knowing position before processing. 

This is circular, and the circle doesn't go away — it becomes the fundamental constraint.

---

## STEP 12 — THE META-LAW

**What the conservation law actually conceals:**

The conservation law (correct position-sensitivity decisions require content, but structural decisions precede content) is actually a specific case of a more fundamental problem I haven't named: **attention is zero-sum allocation**.

The softmax in attention ensures weights sum to 1 across all attended positions. This is not incidental — it means attention is a **fixed computational budget** allocated competitively across tokens. When position encoding injects positional signal into the key-query space, it permanently allocates some of this budget to positional discrimination, regardless of whether a given positional distinction is computationally relevant for the task at hand. Position and content *compete* for attention.

The conservation law I found — that position-sensitivity and content-dependence cannot be simultaneously satisfied — is not primarily a problem of *when* decisions are made. It is a consequence of this zero-sum competition. Attention can discriminate by position or by content; the more it does one, the less it can do the other, within the fixed budget of the softmax.

The meta-law:

**Attention's zero-sum budget creates a forced trade-off between positional discrimination and semantic discrimination at every layer. Every architectural decision about position encoding is, implicitly, a decision about how much attention budget to permanently allocate to positional computation. This allocation cannot be dynamically adjusted based on task demands because it is determined at weight-learning time. Therefore, the budget mismatch between what the architecture allocates to positional computation and what any specific input requires is the structural source of all the failures this analysis has traced.**

**Concrete, testable prediction:**

*In models using additive position encoding, attention heads should partition into positionally-specialized and semantically-specialized heads. These populations are competing for the same total attention budget. Therefore:*

1. **Trade-off prediction:** Tasks requiring fine-grained semantic discrimination (coreference resolution, semantic role labeling) should show performance degradation as a function of *positional complexity* of the training data — not because position is hard, but because the model allocates more attention budget to positional heads when positional disambiguation is rewarded during training. This degradation should follow the proportion of positional-specialist heads, measurable by attention pattern entropy across semantically diverse inputs.

2. **Head pruning asymmetry:** Pruning attention heads identified as positionally-specialized (low entropy, consistent across semantic contexts) should *improve* performance on semantic tasks, not degrade it — the freed budget improves semantic allocation. This effect should be larger than equivalent random head pruning by a margin proportional to positional specialization degree. This is non-obvious: the standard prediction is that pruning reduces capacity.

3. **RoPE comparison:** Models trained with RoPE should exhibit *fewer* positionally-specialized heads (since position is encoded in the rotation, not the attention weights) and should show *better* semantic attention utilization at equivalent model size. The meta-law predicts the specific mechanism: RoPE removes position from the softmax competition, freeing budget for semantic computation without changing total head count or model size.

These predictions are falsifiable, non-obvious, and derive from the meta-law's specific claim about zero-sum budget competition — not from the general claim that transformers have limited capacity.

---

## Summary Cascade

| Stage | Finding |
|---|---|
| **Initial claim** | Position encoding underdetermined — no guarantee of survival |
| **Transformed claim** | Position is relational at use-time but absolute at injection-time |
| **Concealment mechanism** | Residual mixing makes position and content indistinguishable |
| **Improvement (RoPE)** | Removes position from residual stream, looks cleaner |
| **What improvement conceals** | FFN position-blindness was always true; also hardwires relational position |
| **Structural invariant** | Position-sensitive/invariant partition is in weights, not structure |
| **Conservation law** | Correct partitioning requires content; structural decisions precede content |
| **What law conceals** | Attention is zero-sum; position and content compete for the same budget |
| **Meta-law** | Positional budget allocation is fixed at training, but task demands vary — this mismatch is the conserved source of all the traced failures |
| **Testable prediction** | Pruning positionally-specialized heads improves semantic tasks; RoPE models have more semantic attention budget at equivalent size |

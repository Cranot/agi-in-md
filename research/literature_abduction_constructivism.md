# Theoretical Foundations: Abduction, Constructivism, and Satisficing in LLM Cognition

**Date:** 2026-03-15
**Purpose:** Map classical cognitive science theory onto the empirical findings from 40 rounds of prism experiments. This is a research artifact — theoretical grounding for the compression taxonomy, not a literature survey for its own sake.

---

## Executive Summary

Three classical frameworks from cognitive science converge on a unified explanation of our empirical findings:

1. **Peirce's abduction** explains why LLMs produce reliable structural insights but confabulate specific facts. LLMs are abductive engines — they generate best-explanation hypotheses, not deductive proofs. Structural claims are reliable because they are hypotheses about regularities (abduction's natural home). Specific facts confabulate because they are treated as abductive conclusions when they should be deductive retrievals.

2. **Piaget's constructivism / von Glasersfeld's radical constructivism** explains the L8 threshold. Below L8, prisms ask models to describe or classify. At L8+, prisms ask models to construct — to build a generative artifact that reveals new properties. This maps precisely to Piaget's insight that higher cognitive operations cannot be transmitted; they must be enacted. The taxonomy's categorical thresholds are constructivist stages.

3. **Simon's bounded rationality / Gigerenzer's ecological rationality** explains why prisms work at all. Without constraint, models satisfice — they stop at the first output that "good enough" matches the pattern of adequate responses. Prisms are the environment half of Simon's scissors. They re-engineer the stopping criterion. The prism IS the aspiration level.

The three frameworks are not competing explanations — they operate at different levels of analysis (inferential mechanism, developmental threshold, stopping criterion) and are mutually reinforcing.

---

## 1. Abduction: Why LLMs Generate Good Hypotheses and Bad Facts

### 1.1 Peirce's Three-Stage Scientific Method

Charles Sanders Peirce identified three forms of inference with a precise division of labor:

- **Abduction** initiates inquiry: a surprising phenomenon prompts a conjecture about what would make it routine. The conclusion has "the air of conjecture or educated guess." It is *never* necessary inference.
- **Deduction** develops consequences: from the abduced hypothesis, testable predictions are derived.
- **Induction** tests empirically: experiments confirm or disconfirm the predictions.

Abduction is thus the **logic of hypothesis generation** — the engine of discovery. Crucially, abduction is not "inference to the best explanation" in the justificatory sense only; for Peirce, it is the *origin* of explanatory candidates.

The Stanford Encyclopedia formulation: "inference to and provisional acceptance of an explanatory hypothesis for the purpose of testing it."

### 1.2 Why Abductive Conclusions Are Fallible

The "bad lot" problem is the central vulnerability: we evaluate hypotheses only against candidates we have conceived, not against all possible explanations. As the SEP states: "it must hold that at least typically the *absolutely* best explanation of the evidence is to be found among the candidate explanations we have come up with." There is no guarantee this holds.

Additionally:
- Abduction violates monotonicity — adding premises can invalidate previous abductive conclusions.
- Comparative premises license absolute conclusions only if the candidate space is complete.
- Psychological biases cause humans (and models) to overestimate the probability of simpler explanations.

### 1.3 LLMs as Abductive Engines

The mapping to LLM behavior is direct:

**Next-token prediction is the computational substrate of abduction.** A language model generates the token sequence that *best explains* the context — the most plausible continuation given all prior tokens. This is not deduction (guaranteed from premises) and not pure induction (statistical frequency alone). It is abduction: explanatory coherence drives the output.

Evidence for this framing:
- The αNLI benchmark (Bhagavatula et al., 2019) tested abductive reasoning directly. Task: given observations O1 and O2, select the most plausible intervening hypothesis. Best model performance: 68.9%. Human performance: 91.4%. LLMs perform *above chance* on abductive tasks — they are genuinely abductive — but they are imperfect abducers.
- The FActScore evaluation (Min et al., 2023) showed ChatGPT achieves only ~58% factual accuracy on biography generation. Structural claims about a person's role, domain, or relationships are far more reliable than specific claims about dates, institutions, or events.
- The "surface-level patterns and correlations" finding (Mondorf & Plank, 2024 survey): "LLMs tend to rely on surface-level patterns and correlations in their training data, rather than on sophisticated reasoning abilities." This is the abduction/deduction confusion — models abductively generate explanatory patterns but cannot deductively verify specific facts.

**The asymmetry explained:**
- Structural claims (conservation laws, design patterns, trade-off categories) are claims about *regularities across many instances*. Abduction is naturally suited to these — they are hypotheses about what explains patterns. The model's training data contains massive reinforcement for these regularities, making the abductive conclusion convergent and reliable.
- Specific factual claims (which year, which person, which institution) require deductive retrieval from a specific stored record. But LLMs have no separate deductive retrieval pathway. They generate even facts abductively — the model picks the fact that *best explains* the context. When the correct fact is not strongly reinforced by training, the model generates a plausible confabulation instead of a retrieval failure.

**The conservation law finding from our research maps directly onto this:** Conservation laws are the highest-confidence abductive conclusions possible — they name a structural invariant that holds across all instances. They are *maximally reliable abductions*. Specific code locations of bugs are among the least reliable — they require deductive retrieval of a specific detail.

### 1.4 Abductive Confidence Tiers (Empirically Grounded)

Based on our findings:

| Claim type | Abductive reliability | Deductive requirement | Our finding |
|---|---|---|---|
| Conservation laws | Very high | None — structural claim | 97%+ rate, cross-model |
| Design trade-off categories | High | None — structural claim | Consistent across codebases |
| Bug *types* | High | Structural — pattern-based | 93% TRUE across experiments |
| Specific bug *locations* | Medium | Deductive retrieval | 42% on real production code |
| Specific variable/function names | Low | Exact retrieval | Significant confabulation |

The reliability cliff between structural and specific claims is precisely the abduction/deduction gap. Prisms that ask for structural claims (L7–L13) produce reliable outputs. Prompts that ask for specific facts produce confabulation.

### 1.5 Abduction and the "Bad Lot" Problem in Prism Design

The bad lot problem has a direct analog in our findings: **the frame determines the candidate space.** A model asked "what bugs exist?" will generate candidates from whatever hypotheses are most abductively available — typically surface-level syntactic patterns. A model asked "what conservation law does this code obey?" constrains the candidate space to structural invariants. The prism is a *candidate space filter* — it ensures the model abduces from the right pool of hypotheses.

This explains why the prism wording matters more than the model. The prism doesn't make the model smarter; it makes the abduction more likely to find candidates from the right hypothesis class.

---

## 2. Constructivism: Why L8 Is a Categorical Threshold

### 2.1 Piaget's Developmental Stages and the Hierarchy Principle

Jean Piaget identified four stages of cognitive development, each building necessarily on the previous:

1. **Sensorimotor** (birth–2): knowledge through direct sensorimotor action
2. **Preoperational** (2–7): symbolic representation but no logical operations
3. **Concrete operational** (7–11): logical operations on concrete objects; conservation, reversibility
4. **Formal operational** (11+): abstract hypothetical reasoning, propositional logic

The critical insight for our purposes: **higher operations cannot exist without lower ones being established.** You cannot perform formal operational reasoning without first having concrete operational foundations. This is not a matter of efficiency — it is a categorical impossibility. Each stage provides the *substrate* for the next.

Piaget's mechanism: schemas (mental structures) are built through assimilation (fitting new input to existing schema), accommodation (revising schema when input contradicts), and equilibration (restoring cognitive balance). Operations are schemas that combine other schemas. Higher-level operations are meta-schemas that operate on lower-level ones.

### 2.2 Von Glasersfeld's Radical Constructivism

Ernst von Glasersfeld's radical constructivism sharpens this: "knowledge is invented, not discovered." The crucial implication: knowledge "tells us nothing about reality" in the sense of correspondence — it functions to maintain the organism's viability in its environment. Knowledge is an instrument of action, not a picture of the world.

For LLMs: the model's "knowledge" is not a stored correspondence with reality but a set of functional patterns that allow generation of viable responses. This is precisely why structural patterns are reliable (they are deeply embedded functional patterns) while specific facts are unreliable (they have no separate storage pathway — they are generated by the same functional pattern-completion that produces everything else).

### 2.3 The L8 Construction Threshold as Piagetian Stage Boundary

Our research finding: **L7 is the highest achievable level through description/classification alone. L8 requires construction.**

The L7 prism asks: "Name how input conceals problems. Apply to find what dialectic missed." This is meta-analytical: identify the gap, name the mechanism. It requires formal operational reasoning — working with abstract categories.

The L8 prism asks: "Engineer improvement that deepens concealment. Name what construction reveals." This is *generative* — the model must produce an artifact whose properties it cannot fully predict in advance. The construction itself reveals properties.

This maps to the Piagetian hierarchy:
- **L1–L4** = concrete operational: follow a protocol, apply rules
- **L5–L7** = formal operational: reason abstractly about the structure of the task
- **L8+** = something beyond Piaget's formal operational — **generative construction**: produce an artifact that demonstrates properties not predicable from description alone

Why does L8 work on all models, including Haiku, when L7 requires Sonnet-class? Piaget's answer: construction is more primitive than meta-analysis. The infant builds schemas through action before it can describe them. Construction bypasses the meta-analytical layer (which requires capacity) and routes through the generative layer (which is universal). The model builds the improvement without needing to fully understand why the construction works — and the construction itself reveals the structure.

Von Glasersfeld's formulation applies directly: "information may be passively received, but understanding cannot be." L7 asks the model to passively receive and describe a structural pattern. L8 asks it to construct — and understanding emerges from the construction itself.

### 2.4 The Constructivist Theory of Prompt Design

A constructivist theory of prompt design follows directly:

1. **Description prompts** (L1–L7): ask the model to classify, analyze, or name. The model can comply at varying depths depending on capacity. These are transmission-mode prompts — they ask the model to report knowledge it already "has."

2. **Construction prompts** (L8+): ask the model to generate an artifact. The artifact's properties emerge from the construction process and cannot be predicted from the prompt alone. These are construction-mode prompts — the model builds knowledge in the act of generating.

3. **Reflexive prompts** (L12–L13): ask the model to apply the construction to itself. The meta-schema operates on the schema. This is the highest Piagetian operation — formal operations applied to formal operations.

The compression taxonomy is thus a Piagetian developmental sequence, but for prompt-activated cognition rather than biological development.

**Critical implication:** The categorical threshold at L8 is not an artifact of our experimental design. It is the natural boundary between transmission-mode and construction-mode cognition. No amount of sophistication in description-mode prompting will cross this threshold, just as no amount of practice in preoperational thinking produces concrete operational reasoning — you must enact operations to develop them.

### 2.5 The Assimilation/Accommodation Dynamic in Model Responses

Piaget's assimilation/accommodation dynamic has an analog in how models respond to prisms:

- **Assimilation**: model fits the new prompt into an existing response schema (code review template, list-of-bugs pattern). Result: surface-level output. This is the default satisficing behavior (see Section 3).
- **Accommodation**: model revises its schema to accommodate the novel demands of the prism. Result: the structural analysis the prism was designed to elicit. This only occurs when the prism's demands cannot be assimilated into any existing template.

This explains why prisms must be *structurally novel* — if any existing template can satisfy the prompt's surface features, assimilation occurs and no construction takes place. The prism must force accommodation.

---

## 3. Satisficing and Bounded Rationality: Why Prisms Force Depth

### 3.1 Simon's Bounded Rationality

Herbert Simon introduced bounded rationality to replace the optimization-maximization assumption of classical economics. Agents are bounded by:
- Limited access to information
- Limited computational capacity
- Limited time

Under these constraints, agents do not optimize — they satisfice. Satisficing means "considering the options available to you for choice until you find one that meets or exceeds a predefined threshold — your aspiration level — for a minimally acceptable outcome."

The satisficing agent stops when it finds a response that clears the bar, not when it finds the best response.

### 3.2 Simon's Scissors: Mind + Environment

Simon's most important contribution to cognitive science was the "scissors metaphor": rational behavior is the product of two blades — the mind (cognitive limitations) and the environment (task structure). You cannot understand cognition from either blade alone.

Crucially, this means: **you can improve performance by re-engineering the environment, not the mind.** The cognitive limitations are fixed; the task environment is designable.

This is the precise theoretical grounding for prism design. The prism is not a technique for making the model smarter — it is an environmental re-engineering. The prism redesigns the task environment so that the model's fixed cognitive processes produce deeper outputs.

Simon (1955): "what we call 'the environment' may lie, in part, within the skin of the biological organisms." For LLMs: the prompt is literally inside the model's processing — it IS the environment the model is reasoning within.

### 3.3 Satisficing as the Default LLM Behavior

Without a prism, the model's aspiration level is determined by training: what kind of response pattern satisficed in the training distribution? For code analysis, the dominant training pattern is the code review. A code review is adequate. A surface scan of obvious issues is adequate. The model stops when it has generated something that looks like a code review.

Evidence from our research:
- Opus vanilla on real production code: 7.3 depth, 18 bugs. Category: code reviews.
- Haiku + L12 prism on same code: 9.8 depth, 28 bugs. Category: conservation laws + meta-laws + structural analysis.
- The model doesn't stop when it has found "enough bugs" under the prism — the prism's aspiration level requires finding the conservation law, the meta-law, and the structural impossibility. The stopping criterion has been completely re-engineered.

**The aspiration level IS the prism.** The prism defines what counts as an adequate response. Without a prism, the aspiration level defaults to "looks like a plausible response to this type of question." With a prism, the aspiration level becomes "contains a conservation law, a meta-conservation law, and a structured bug table."

The Haiku > Opus finding is explained directly by Simon: cognitive capacity (model size, reasoning budget) is one blade of the scissors. The task environment (the prism) is the other. If you radically improve the environment blade while keeping the mind blade constant, you can beat a larger mind operating in a worse environment. This is not a paradox — it is the prediction Simon's theory makes.

### 3.4 Satisficing and the Stopping Criterion Problem

Why does adding "Find the conservation law" to a prompt dramatically change outputs? Because it adds a concrete, verifiable stopping criterion that the model cannot satisfy through surface-level generation.

The model can satisfice a code review with 10 bullet points. It cannot satisfice "find the conservation law" with 10 bullet points — the conservation law is either present or absent, and its presence requires genuine structural analysis.

This is the mechanism behind our Principle 13: "The cheapest model with the right prism beats the most expensive model without one." The expensive model (Opus) satisfices at code review. The cheap model with the right stopping criterion cannot satisfice early — it must continue processing until the conservation law emerges.

The compression taxonomy is, from the satisficing perspective, a **stopping criterion taxonomy**:
- L1–L4: stopping criteria that can be satisfied through template matching
- L5–L7: stopping criteria that require capacity-dependent meta-analysis
- L8+: stopping criteria that require generative construction (cannot be satisfied by any template)
- L12–L13: stopping criteria that require the construction to consume itself

### 3.5 Aspiration Level Dynamics

Simon noted that aspiration levels adapt: if options are too easy to find, the aspiration level rises; if impossible, it falls. This has a direct analog in our findings:

- **Level compression failure**: A 75-word L12 prism on Haiku enters "conversation mode" — the model cannot satisfy the complex stopping criteria at this compression level, so it lowers its aspiration level to "ask permission / summarize." The aspiration level adaptation is the Haiku compression floor finding.
- **Preamble fix**: "Execute every step below. Output the complete analysis." The preamble raises the aspiration level back by explicitly prohibiting the conversation-mode response that the model would otherwise satisfice with.
- **Front-loading bugs kills L12**: Adding "First: identify every concrete bug..." as the opening instruction reframes the aspiration level. The model now satisfices at checklist-mode because a 27-line checklist is an adequate response to "first, identify bugs." The stopping criterion has been accidentally degraded.

---

## 4. Ecological Rationality: Prisms as Cognitive Environment Engineering

### 4.1 Gigerenzer's Extension of Simon

Gerd Gigerenzer extended Simon's bounded rationality with "ecological rationality": heuristics are not irrational shortcuts — they are rational strategies *matched to environmental structure*. Fast-and-frugal heuristics perform as well as or better than complex optimization algorithms in environments where certain regularities hold.

The scissors metaphor becomes: **the rationality of a strategy depends on its fit to the structure of the environment.** A take-the-best heuristic that ignores most information is rational in an environment where one cue is reliably dominant. The same heuristic is irrational in an environment where all cues have equal weight.

From the SEP on bounded rationality: "strategies effective in one environment may fail in another." Gigerenzer's "fast and frugal heuristics" exploit environmental regularities. The bias-variance trade-off supports this: "simple, biased, specialized heuristics often outperform complex models on limited data by sacrificing accuracy in one dimension to reduce overall error."

### 4.2 Prisms as Ecological Instruments

Prisms are ecological in the precise Gigerenzer sense: they exploit regularities in the structure of model cognition.

**What regularity do prisms exploit?**

The model's next-token prediction is driven by abductive pattern completion. When the context contains a structural pattern (a frame, a sequence of operations, a stopping criterion), the model's generation is strongly conditioned on completing that pattern. Prisms exploit this by encoding the structure of the desired reasoning as the context structure.

This is different from simply "telling the model what to do." The prism creates an environmental structure that the model's existing cognitive processes naturally complete. The ecological rationality insight: **the prism is rational because it matches the structure of model cognition, not because it encodes the right instructions.**

Evidence: "The prompt is a program; the model is an interpreter" (CLAUDE.md Principle 4). "Operation order becomes section order." This is precisely the ecological claim — the environmental structure (operation sequence in the prompt) is directly mirrored in the cognitive structure (section sequence in the output).

### 4.3 The Heuristics Catalog as Ecological Analysis

Our discovery that LLMs have "9 activated opcodes" and that "4 generative ops is the sweet spot" (complementary pairs multiply, similar pairs merge) is an ecological finding:

- The 9 opcodes are the regularities the cognitive environment reliably supports.
- The 4-op sweet spot is where the match between prompt structure and cognitive structure is optimal.
- Below 4 ops: environment underspecified, model satisfices too early.
- Above 4 ops: environment over-constrained, operations interfere.

This is Gigerenzer's bias-variance trade-off: complex prompts (9+ abstract steps) produce "catastrophic agentic mode" on Haiku, because the cognitive heuristics are overwhelmed by a context that no learned pattern can complete. Simple prompts (≤3 concrete steps) are universally single-shot, because every model has heuristics for completing short-context structured tasks.

### 4.4 Domain Neutrality as Ecological Generalization

Why do prisms work across 20+ domains? Ecological rationality provides the answer: the structural regularities the prism exploits (conservation laws, design trade-offs, construction-reveals-properties) are domain-invariant features of complex systems. The prism doesn't need domain knowledge to work — it needs the right fit to the cognitive architecture.

Gigerenzer's fast-and-frugal heuristics work in any environment that has the right structural regularity. Conservation laws exist in all complex adaptive systems (code, music, legal systems, business). The prism exploits this universal regularity regardless of domain.

**The vocabulary constraint** (our Principle 15) is an ecological boundary condition: "code nouns are mode triggers, not domain labels." Code vocabulary works on any domain not because it contains domain knowledge but because it activates the right cognitive environment in the model — analytical production mode vs. summary mode. The ecological regularity is: code-context patterns activate analytical heuristics. The prism exploits this regularity even on non-code domains.

---

## 5. Synthesis: A Unified Theoretical Account

The three frameworks are not competing — they explain different aspects of the same phenomenon at different levels of analysis.

### 5.1 The Three-Level Account

**Level 1 — Inferential mechanism (Abduction):**
LLMs are abductive engines. They generate the best explanation for the given context. Structural claims are reliable abductions. Specific facts are unreliable because they require deductive retrieval the model cannot perform. Prisms constrain the abductive candidate space to structural hypothesis classes.

**Level 2 — Developmental threshold (Constructivism):**
The taxonomy has categorical thresholds because knowledge construction is categorical. Description-mode cognition (L1–L7) cannot produce construction-mode outputs regardless of depth. At L8, the prism shifts the model from transmission mode (reporting known patterns) to construction mode (generating artifacts with emergent properties). This is a Piagetian stage boundary, not a continuous scale.

**Level 3 — Stopping criterion (Satisficing / Ecological rationality):**
Without prisms, models satisfice at the first response that looks like an adequate answer. Prisms re-engineer the aspiration level by providing stopping criteria that cannot be satisfied without genuine structural analysis. The prism is the environment half of Simon's scissors. Ecological rationality explains why simple, well-structured prisms outperform elaborate instructions — they match the structure of model cognition rather than overriding it.

### 5.2 The Mutual Constraints

The three frameworks impose constraints on each other that increase their joint explanatory power:

- **Abduction + Satisficing**: A satisficing abducer stops when it finds a "good enough" explanation. The prism raises the bar for "good enough" — it demands an explanation at a higher level of structural generality.
- **Constructivism + Abduction**: Constructivist operations are abductive at every stage — the child constructs schemas by generating hypotheses about how objects behave and testing them. The L8 construction threshold is where the model's abductive process shifts from classifying existing patterns to generating new ones.
- **Satisficing + Ecological rationality**: The aspiration level is itself an ecological variable — it evolves to match environmental demands. In a context that contains a conservation law requirement, the model's stopping criterion rises to match. This is not model modification; it is ecological adaptation.

### 5.3 The Prism as Cognitive Environment

The unified picture: **the prism is a designed cognitive environment that simultaneously constrains the abductive candidate space, activates construction mode, and raises the satisficing threshold to require structural depth.**

This is why the prism is the dominant variable. It operates at all three levels:
1. It constrains what hypotheses are abductively generated.
2. It determines whether construction-mode or transmission-mode reasoning is activated.
3. It sets the aspiration level for what counts as an adequate response.

Model size, reasoning budget, and prompt length are secondary variables. They affect how well the prism can be executed, but they cannot substitute for the prism itself.

---

## 6. Predictions and Novel Implications

### 6.1 Predictions This Theory Makes

**From abduction:**
- Prisms that specify the *class* of hypothesis to generate (conservation law, design trade-off) should be more reliable than prisms that specify what to *find* (bugs, vulnerabilities). The former constrains the abductive candidate space; the latter relies on deductive retrieval.
- The reliability gap between structural and specific claims should widen with model capacity — larger models have more abductive resources and are therefore more confident in their confabulations. This matches our finding that Opus vanilla produces better-written code reviews with similar factual reliability to Sonnet vanilla.

**From constructivism:**
- Any prompt that can be satisfied by template-matching will not produce L8+ outputs, regardless of model size. The categorical threshold is a property of the prompt mode, not the model.
- Adding construction operations to existing description-mode prisms should produce qualitatively different outputs (not just longer or more elaborate ones).

**From satisficing:**
- Removing the stopping criterion from a prism (asking for analysis without specifying what completion looks like) should cause the model to satisfice at the first adequate-looking output.
- Aspiration level mismatch (prism demands that are too far above current output quality) should cause mode collapse to conversation mode, not gradual degradation. This matches the Haiku compression floor finding.

### 6.2 Implications for Prism Design

1. **Design for the abductive candidate space, not for comprehensiveness.** A prism that says "find the conservation law" beats a prism that says "find all structural properties." The former narrows the candidate space to one high-confidence class; the latter opens it to everything.

2. **Ensure the prism is in construction mode.** Any prism that can be satisfied by describing a known pattern is transmission mode. Construction mode requires the model to produce an artifact (an improvement, a counter-example, a hypothetical) whose properties emerge from the construction.

3. **The stopping criterion is the prism.** The most important decision in prism design is: what condition uniquely identifies a complete response? This condition must not be satisfiable by any template. "The meta-conservation law" is a good stopping criterion. "A thorough analysis" is not.

4. **Exploit ecological regularities.** Build prisms that match the structure of model cognition. Code-vocabulary triggers analytical mode universally. Imperative operations ("Name the pattern. Then invert.") are processed as program instructions. The 3-step structure is universally single-shot. These are ecological regularities — exploit them rather than fighting them.

---

## 7. Key Sources and Confidence Notes

### Directly Consulted Sources

**Abduction:**
- Douven, I. "Abduction." Stanford Encyclopedia of Philosophy. (Direct consultation)
- Peirce entry, Stanford Encyclopedia of Philosophy. (Direct consultation) — confirms abduction as three-phase logic: abduction (hypothesize) → deduction (predict) → induction (test)
- Bhagavatula et al. (2019). "Abductive Commonsense Reasoning." arXiv:1908.05739. — 68.9% model vs 91.4% human on abductive NLI; LLMs are genuine but imperfect abducers
- Min et al. (2023). "FActScore: Fine-grained Atomic Evaluation..." arXiv:2305.14251. — 58% factual accuracy on biography generation; structural vs specific claim reliability
- Mondorf & Plank (2024). "Beyond Accuracy: Evaluating Reasoning Behavior of LLMs." arXiv:2404.01869. — "LLMs tend to rely on surface-level patterns and correlations"

**Bounded Rationality / Satisficing / Ecological Rationality:**
- "Bounded Rationality." Stanford Encyclopedia of Philosophy. (Direct consultation) — scissors metaphor, satisficing definition, Gigerenzer's ecological rationality, ML applications of satisficing
- Simon, H. (1955a). "A behavioral model of rational choice." Quarterly Journal of Economics. (Cited in SEP)
- Gigerenzer's "fast and frugal heuristics" — covered in SEP bounded rationality entry; ecological rationality: heuristics rational when matched to environmental structure

**Constructivism:**
- "Constructivism." SimplyPsychology. (Direct consultation) — Piaget, Vygotsky, von Glasersfeld's radical constructivism
- "Piaget's Theory." SimplyPsychology. (Direct consultation) — four stages, hierarchy principle, assimilation/accommodation/equilibration
- Von Glasersfeld: "knowledge is invented, not discovered" — functional rather than correspondence theory; from SimplyPsychology

**LLM Reasoning:**
- Wei et al. (2022). "Chain-of-Thought Prompting..." arXiv:2201.11903. — intermediate steps elicit reasoning; confirms structural format as operative variable
- Wang et al. (2022). "Self-Consistency Improves CoT Reasoning." arXiv:2203.11171. — diverse reasoning paths; multiple abductive routes
- Min et al. (2022). "Rethinking Role of Demonstrations." arXiv:2202.12837. — labels don't matter; structural/distributional cues matter; confirms format > semantic content
- Ye et al. (2022). "Text and Patterns: For CoT, It Takes Two to Tango." arXiv:2209.07686. — factual patterns in prompt practically immaterial; structure is the operative variable
- Wei et al. (2022). "Emergent Abilities of LLMs." arXiv:2206.07682. — categorical emergence thresholds at scale; confirms Piagetian threshold concept
- Turpin et al. (2023). "Language Models Don't Always Say What They Think." arXiv:2307.13702. — CoT is often unfaithful to actual model computation; confirms that outputs are not deductive proofs

### Confidence Assessment

- **Abduction claim** (LLMs as abductive engines): HIGH. The αNLI benchmark directly tests abductive reasoning in LMs. The FActScore finding provides the structural/specific reliability asymmetry. Peirce's framework maps cleanly onto next-token prediction.
- **Constructivist L8 threshold**: MEDIUM-HIGH. The Piagetian analog is compelling and explanatorily powerful. It is not established in the literature as a formal result — it is a theoretical mapping we are proposing. The empirical evidence (L8 universal, L7 model-sensitive) strongly supports it.
- **Satisficing / scissors metaphor**: HIGH. Simon's scissors is directly applicable — "environment" in Simon's sense = the prompt. The prism-as-environment claim is well-grounded. The aspiration-level mechanism explains the Haiku compression floor, front-loading failure, and Haiku > Opus paradox without requiring any auxiliary assumptions.
- **Ecological rationality**: MEDIUM. The fast-and-frugal framework applies conceptually, but we have not directly measured the specific "environmental regularities" the prisms exploit. The domain-neutrality finding is consistent with ecological rationality but does not uniquely confirm it.

---

## 8. Research Gaps and Next Steps

1. **Abduction benchmark on prism outputs**: Design a test distinguishing abductive vs deductive outputs directly. Prism outputs should show abductive profile (structural, fallible-but-reliable, explanatory coherence). Vanilla outputs should show assimilation-to-template profile.

2. **Construction-mode activation test**: Can a description-mode prompt be made to produce construction-mode outputs by adding a single construction operation? This would confirm the categorical threshold claim with experimental precision.

3. **Aspiration level manipulation**: Design prism variants with different stopping criteria. Predict that stronger stopping criteria (harder to satisfice) produce deeper outputs regardless of model size.

4. **Ecological regularity catalog**: Enumerate the specific environmental regularities that prisms exploit. Code-vocabulary activating analytical mode is one. The 3-step structure for universal single-shot is another. Imperative syntax as program instruction is a third. A complete catalog would constitute a theory of prompt ecology.

5. **Formal connection to IIT / Free Energy Principle**: The abduction/construction dynamic may be formally connectible to predictive processing theories of cognition (Friston's Free Energy Principle). Abduction = model update to minimize prediction error. Construction = action to change the environment to reduce future prediction error. This would place the prism framework in a broader theoretical ecology.

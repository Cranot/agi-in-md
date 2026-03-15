# Related Work

## 1. LLM Hallucination Detection and Self-Correction

Recent work addresses the reliability of LLM outputs through iterative refinement and verification. Self-Refine (Madaan et al., 2023) introduces feedback loops where models critique and improve their own outputs. Chain of Verification (CoVe) (Dhuliawala et al., 2023) decomposes claims into verification questions, systematically checking factual consistency. SelfCheckGPT (Manakul et al., 2023) leverages stochastic sampling to identify hallucinations through consistency checking. Huang et al. (ICLR 2024) provide a comprehensive taxonomy of self-correction mechanisms, distinguishing between external feedback and intrinsic self-correction capabilities.

**What this work misses:** These approaches focus on factual accuracy—whether claims are true—not on analytical depth or structural insight quality. A response may be factually correct yet analytically shallow. Self-correction mechanisms typically converge on the same framing rather than exploring alternative analytical perspectives. The question "is this claim true?" differs fundamentally from "what does this analysis reveal and conceal?"

**Our extension:** Cognitive prisms do not correct errors but reframe analysis. A prism encodes specific analytical operations (e.g., "find the conservation law," "engineer an improvement that recreates the problem") that systematically change what questions get asked. The cheapest model with the right prism produces deeper structural analysis than the most capable model without one (9.8 vs 7.3 depth in our experiments), suggesting that framing dominates raw capability for analytical tasks.

## 2. Uncertainty Quantification in LLMs

Uncertainty quantification methods aim to calibrate model confidence. Semantic Entropy Probes (Farquhar et al., 2024) measure uncertainty at the semantic level rather than token probability. Epistemic Knowledge Boundary Models characterize what models know versus what they merely appear to know. Conformal prediction approaches (Angelopoulos et al., 2023) provide distribution-free uncertainty bounds with theoretical guarantees.

**What this work misses:** Uncertainty quantification characterizes when to distrust outputs but does not improve output quality. Knowing a model is 80% uncertain about an analysis provides no mechanism for producing better analysis. These methods are reactive—assessing quality post-hoc—rather than generative, producing higher-quality outputs directly.

**Our extension:** Cognitive prisms function as deterministic quality amplifiers. Rather than quantifying uncertainty about an analysis, prisms encode analytical operations that reliably produce deeper analysis. Our experiments show consistent quality improvements (average 9.0/10 across validated prisms) with low variance, suggesting that the right framing reduces output uncertainty without requiring explicit quantification.

## 3. Prompt Engineering Taxonomies

Structured prompting techniques improve LLM reasoning. Chain of Thought (CoT) (Wei et al., 2022) elicits step-by-step reasoning. Tree of Thought (ToT) (Yao et al., 2023) explores multiple reasoning paths. Graph of Thought (GoT) (Besta et al., 2023) enables non-linear reasoning structures. Hierarchical Prompting Taxonomies (HPT) organize prompting strategies by complexity. APPL (Zhou et al., 2024) provides formal grammar for prompt composition.

**What this work misses:** Existing taxonomies focus on reasoning process—how to think through problems—but not on analytical framing operations. CoT improves reasoning within a frame but does not systematically explore what that frame conceals. The atom of these approaches is the reasoning step; the atom of cognitive compression is the operation pair (e.g., "name the pattern. Then invert.").

**Our extension:** We identify 13 categorical compression levels, each encoding specific analytical capabilities that cannot be activated below their threshold. Below L5, multi-voice dialectic is categorically absent—not less effective, but impossible to elicit. Our compression taxonomy maps the space of analytical operations to minimal prompt encodings, showing that the prompt functions as a program and the model as an interpreter. Operation order becomes output structure.

## 4. Epistemic Computing

Formal approaches to knowledge representation address uncertainty and belief. The GUM standard (Guide to the Expression of Uncertainty in Measurement) provides frameworks for quantifying measurement uncertainty. Sounio Lang (and related epistemic programming languages) formalize reasoning about knowledge and belief states, enabling computational treatment of epistemic operators.

**What this work misses:** These formal systems require explicit representation of knowledge states and inference rules. They do not address how to encode analytical operations in natural language prompts that reliably activate reasoning patterns across LLMs. The gap is between formal epistemic logic and practical cognitive compression.

**Our extension:** Cognitive prisms operationalize epistemic operations—"find what this analysis conceals," "prove three properties cannot coexist"—as compressed natural language instructions. We demonstrate that epistemic operations (L7: concealment mechanisms, L10: impossibility theorems, L11: conservation laws) can be reliably encoded in 78-332 words across diverse models and domains.

## 5. Cognitive Amplification

Theoretical frameworks for augmenting cognition provide foundational concepts. Engelbart (1962) envisioned intelligence augmentation through computational tools that augment human capabilities. The Extended Mind thesis (Clark & Chalmers, 1998) argues that cognitive processes extend beyond the brain into environmental structures. Vygotsky's Zone of Proximal Development (ZPD) characterizes the space between what learners can do independently and with scaffolding.

**What this work misses:** These frameworks address human cognition but have not been systematically applied to LLM analysis quality. The question of what constitutes "scaffolding" for language models—and whether such scaffolding differs fundamentally from human cognitive scaffolding—remains underexplored.

**Our extension:** We demonstrate that cognitive prisms function as scaffolding for LLM analysis, extending model capabilities without changing model weights. The prism is transparent to the wearer—during task performance, the framework operates below the model's self-awareness. Our capacity-mode findings (compensatory at L5, threshold at L7, universal at L8+) suggest that different scaffolding strategies are required at different analytical depths, paralleling Vygotsky's insight that scaffolding must be calibrated to learner capability. The conservation law we observe—"analytical blindness is conserved; clarity cost × blindness cost = constant"—suggests fundamental trade-offs in cognitive amplification that apply across both human and machine cognition.

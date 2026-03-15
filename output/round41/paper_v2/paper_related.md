# Related Work

## LLM Hallucination Detection and Self-Correction

Recent work addresses the factual reliability of language model outputs through iterative self-improvement. Self-Refine (Madaan et al., 2023) introduces feedback loops where models critique and revise their own outputs. Chain of Verification (CoVe) (Dhuliawala et al., 2023) decomposes claims into verification questions, reducing hallucination through systematic fact-checking. SelfCheckGPT (Manakul et al., 2023) leverages stochasticity in generation to detect inconsistencies without external databases. Huang et al. (ICLR 2024) provide a comprehensive survey of self-correction mechanisms, identifying conditions under which models successfully improve their outputs.

These approaches share a common limitation: they presuppose that the correct framing of a problem is already established. Self-correction operates on *answers* to given questions, not on whether those questions are the right ones to ask. A model may produce factually accurate statements that nevertheless miss structural properties of the target domain. Our work shifts focus from factual accuracy to analytical completeness—cognitive prisms encode operations that reveal what standard framing conceals, rather than verifying what it asserts.

## Uncertainty Quantification in LLMs

Uncertainty quantification methods aim to calibrate trust in model outputs. Semantic Entropy Probes (Farquhar & Gal, 2024) distinguish epistemic from aleatoric uncertainty by analyzing semantic variation across samples. Entropy-based kernel methods (EKBM) provide distributional estimates of model confidence. Conformal prediction frameworks (Angelopoulos et al., 2023) offer statistical guarantees on prediction sets, enabling rigorous uncertainty bounds.

While these methods indicate *when* to distrust model outputs, they cannot identify *what* the model is systematically blind to. High confidence in a wrong framing is indistinguishable from high confidence in a correct one. Our approach addresses a complementary problem: rather than measuring uncertainty about answers, prisms encode operations that surface structural invariants and impossibility theorems inherent in the target domain. Conservation laws provide convergence signals that are independent of model confidence.

## Prompt Engineering Taxonomies

Structured prompting techniques have emerged as a powerful paradigm for eliciting complex reasoning. Chain of Thought (CoT) (Wei et al., 2022) decomposes problems into intermediate steps. Tree of Thought (ToT) (Yao et al., 2023) explores multiple reasoning paths. Graph of Thoughts (GoT) (Besta et al., 2024) enables non-linear combination of reasoning traces. Hierarchical Prompting Taxonomies (HPT) organize prompting strategies by complexity and capability. APPL (Deng et al., 2024) provides a programming language for composable prompt pipelines.

These taxonomies focus on improving reasoning *within* a given problem frame. They do not address the question of which frame to apply. Our compression taxonomy differs fundamentally: it classifies operations by the *type* of analytical transformation they encode, not by reasoning complexity. Levels are categorical rather than continuous—below each threshold, that category of insight is structurally unavailable. The operation pair, not the reasoning chain, is the atom of cognitive compression.

## Epistemic Computing

Formal frameworks for knowledge representation provide theoretical grounding for reasoning about uncertainty. The GUM standard (JCGM, 2008) establishes rigorous methodology for uncertainty propagation in measurement. Sounio Lang applies epistemic logic to computational systems, enabling reasoning about knowledge and belief revision.

These frameworks address the *representation* of epistemic states but not their *operational activation* in language models. A formal epistemology does not itself induce analytical behavior. Our work bridges this gap by encoding epistemic operations—concealment diagnosis, conservation law derivation, impossibility proofs—directly into prompt structure. The prism acts as a program and the model as an interpreter, operationalizing abstract epistemic operations as concrete analytical procedures.

## Cognitive Amplification

The theoretical lineage of human-tool co-augmentation traces to Engelbart (1962), who framed computing as a means to augment human intellect. The Extended Mind thesis (Clark & Chalmers, 1998) argues that cognitive processes extend beyond the brain into environmental structures. Vygotsky's Zone of Proximal Development (ZPD) describes how scaffolding enables capabilities beyond current individual competence.

Cognitive prisms extend these frameworks to the human-LLM interaction. The prism functions as an external cognitive structure that reorganizes how models frame problems—transparent to the wearer during task performance, yet determining what can be seen. Our empirical contribution is a compression taxonomy that maps which operations can be encoded at what verbosity thresholds, revealing categorical limits on what different model classes can be made to do. The finding that Haiku with the right prism outperforms Opus without one suggests that cognitive amplification through prompt engineering dominates raw model capacity—a result with implications for both the theory and practice of human-AI collaboration.

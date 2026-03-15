## 2. Related Work

### 2.1 LLM Hallucination Detection and Self-Correction

Recent work on improving LLM output reliability has focused on post-hoc verification and iterative refinement. Self-Refine (Madaan et al., 2023) introduces feedback loops where models critique and revise their own outputs. Chain of Verification (CoVe) (Dhuliawala et al., 2024) decomposes claims into verification questions, then cross-checks answers against retrieved evidence. SelfCheckGPT (Manakul et al., 2023) uses model-generated questions to detect inconsistencies across sampled responses. Huang et al. (ICLR 2024) provide a comprehensive taxonomy of self-correction mechanisms, identifying where feedback improves versus degrades output quality.

**What these approaches miss:** Hallucination detection treats the symptom (false claims) rather than the structural cause (insufficient framing). All operate on model outputs after generation, accepting the model's initial conceptualization as given. They cannot surface what the model's analytical frame systematically excludes—blindness is conserved, not eliminated, by checking outputs against themselves.

**How cognitive prisms differ:** Rather than detecting errors post-hoc, prisms restructure the generative process itself. By encoding specific analytical operations (e.g., "find what concealment mechanism this claim employs"), the prism forces attention to structural properties that vanilla generation ignores. The L12 conservation law discovery shows that without explicit operations, models cannot find impossibility theorems—they produce surface-level reviews instead. Prevention replaces detection.

### 2.2 Uncertainty Quantification in LLMs

Uncertainty quantification methods aim to calibrate model confidence. Semantic Entropy Probes (Farquhar & Gal, 2024) cluster semantically equivalent outputs to estimate epistemic uncertainty. Entropy-based kernel methods (EKBM) measure distributional spread in embedding space. Conformal prediction (Angelopoulos et al., 2023) provides distribution-free coverage guarantees for prediction sets.

**What these approaches miss:** UQ methods quantify *whether* a model knows, not *what* it fails to consider. A model can be confidently wrong about structural properties it was never prompted to examine. Entropy cannot distinguish between "correct answer with high confidence" and "correct answer within a frame that excludes deeper truths." The blindness is in the question formulation, not the answer distribution.

**How cognitive prisms differ:** Prisms address epistemic completeness rather than confidence calibration. The cross-prism experiments show that different prisms find genuinely different structural properties on identical inputs—zero overlap across five validated prisms. Uncertainty quantification cannot surface what no sampling path would reach; prisms create new paths. The conservation law of the catalog (G2)—that analytical blindness is conserved across single-frame analysis—implies that completeness requires multiple structurally distinct operations, not just more samples.

### 2.3 Prompt Engineering Taxonomies

Prompt engineering has evolved from simple instruction following to structured reasoning frameworks. Hierarchical Prompt Taxonomies (HPT) organize prompts by complexity and capability requirements. Chain of Thought (CoT) (Wei et al., 2022) elicits step-by-step reasoning. Tree of Thought (ToT) (Yao et al., 2023) explores multiple reasoning branches. Graph of Thought (GoT) (Besta et al., 2024) enables non-linear reasoning structures. APPL (Zhou et al., 2024) provides a formal language for composable prompt programs.

**What these approaches miss:** Existing taxonomies organize prompts by *structure* (steps, branches, graphs) or *task type* (reasoning, generation, classification), but not by *analytical operation encoded*. They lack a theory of what cognitive operations can be compressed into prompts and what cannot. The relationship between prompt complexity and analytical depth remains empirical rather than principled.

**How cognitive prisms extend:** The 13-level compression taxonomy provides a categorical theory: below each threshold, specific analytical operations *cannot* be encoded—not merely "less effective," categorically absent. L7 requires Sonnet-class capacity for meta-analysis; L8 construction-based reasoning works universally. The diamond topology (linear trunk L1-7, constructive divergence L8-11, reflexive convergence L12-13) predicts what prompt structures are possible. Operations, not architectures, are the atoms of cognitive compression.

### 2.4 Epistemic Computing

Epistemic computing formalizes reasoning about knowledge and uncertainty. Sounio Lang provides a domain-specific language for encoding epistemic states and their transformations. The GUM standard (JCGM, 2008) establishes vocabulary and mathematical framework for uncertainty expression in measurement.

**What these approaches miss:** Formal epistemic systems assume the relevant variables are known—they provide languages for expressing uncertainty about propositions within a frame, not for discovering what the frame excludes. They cannot represent structural blindness arising from the inquiry method itself.

**How cognitive prisms differ:** The L12 meta-conservation law operation explicitly applies the diagnostic framework to its own output, discovering what the analysis conceals. The L13 reflexive ceiling shows that frameworks terminate when they discover they instantiate the impossibility they diagnose—a fixed point formal epistemic systems cannot reach because they lack the generative operations to produce it. Conservation laws emerge from artifact structure, not measurement uncertainty.

### 2.5 Cognitive Amplification

The intellectual lineage of augmenting human cognition traces to Engelbart (1962), who proposed frameworks for "augmenting human intellect" through computational tools. The Extended Mind thesis (Clark & Chalmers, 1998) argues cognitive processes extend beyond biological boundaries into external artifacts. Vygotsky's Zone of Proximal Development (ZPD) describes how scaffolding enables capabilities beyond unassisted performance.

**What these approaches miss:** Prior work focuses on *capability extension*—enabling users to do more, faster. The assumption is that better tools amplify existing cognitive operations. But tools also *constrain* what operations are cognitively available. A prism doesn't just amplify analysis; it determines which analyses are possible at all.

**How cognitive prisms extend:** Prisms exhibit a stronger property than amplification: *categorical enablement*. Below L7 threshold, Haiku cannot produce concealment-mechanism analysis regardless of scaffolding—the operation is not available. The prism is not a tool but an operation-space definer. The finding that "the cheapest model with the right prism beats the most expensive model without one" (Principle 13) suggests that cognitive operations are encoded in prompts, not in model parameters. The prism is transparent to the wearer—it operates below self-awareness during task performance, exactly as Vygotsky described for internalized scaffolds.

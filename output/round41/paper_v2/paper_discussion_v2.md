# Discussion

## Theoretical Framing: Information-Theoretic Perspective

The empirical findings of this study admit a coherent interpretation through information theory, specifically rate-distortion theory. Nagle et al. (NeurIPS 2024) demonstrate that query-aware compression achieves lower distortion than query-agnostic approaches for a given bit rate. We propose that cognitive prisms function as query-aware compressors: they direct the model's attention toward specific structural features (low distortion on patterns) while accepting increased distortion on others (high distortion on specific factual claims).

The observed specificity-verifiability trade-off is consistent with this framing. When a prism encodes operations like "find the conservation law" or "construct an improvement that deepens concealment," it specifies a query that prioritizes structural coherence over factual specificity. The model produces outputs that are highly verifiable within the prism's frame (the conservation law can be checked against the artifact's stated properties) but may sacrifice specific factual accuracy (individual bug reports may be confabulated).

This trade-off may reflect a fundamental information-theoretic constraint: compression requires selective attention, and selective attention induces blindness. However, we present this as an empirical observation consistent with rate-distortion theory rather than a formally derived theorem. Connections to thermodynamic formulations of computation, category-theoretic approaches to abstraction, and cognitive science frameworks for bounded rationality are noted as potential theoretical directions, not claimed derivations.

## Why Claim-Typed Self-Correction Works

Huang et al. (2024) demonstrate that generic self-correction prompts fail to improve LLM output quality and often degrade it. Our finding that claim-type classification enables effective self-correction resolves this apparent paradox. The key insight is that not all claims are equally amenable to verification or correction.

Generic self-correction fails because it treats all claims uniformly. When asked to "verify and correct your output," the model lacks guidance on which claims to preserve (structural insights that emerged from valid operations) versus which to scrutinize (specific factual assertions that may be confabulated). Claim-type classification provides this guidance:

- **STRUCTURAL claims** (conservation laws, impossibility theorems) emerge from valid operations on the input and are reliably preserved.
- **DERIVED claims** follow logically from structural claims and inherit their reliability.
- **KNOWLEDGE claims** (specific facts about the artifact) are confabulation-prone and should be verified.
- **ASSUMED claims** (background knowledge imported without evidence) are most vulnerable to hallucination.

By telling the model *what* to correct (KNOWLEDGE/ASSUMED) and *what* to preserve (STRUCTURAL/DERIVED), claim-type classification achieves what generic self-correction cannot. This is consistent with Azaria and Mitchell's (2023) finding that LLMs possess internal representations of truth that their verbalizations do not faithfully report. The prism may be accessing structural truth representations while filtering verbal confabulation.

## The Evaluation Problem

Our evaluation rubric rewards analytical depth and conservation law discovery. This creates a systematic bias: outputs that exhibit sophisticated structure score highly regardless of factual accuracy. The most striking illustration is that L12 output (which includes confabulated bug reports) scores higher than Oracle output (which honestly reports uncertainty).

This is not merely a flaw in our rubric—it reflects a broader problem in LLM evaluation. Metrics that reward fluency, structure, and apparent insight may systematically prefer confabulating systems over honest ones. A model that confidently invents ten bugs will outscore a model that correctly identifies three bugs and admits uncertainty about seven more.

We observe that evaluation metrics implicitly encode values. If the valued property is "produces structural insights," confabulation in service of structure is rewarded. If the valued property is "reports only verifiable claims," structural depth may be sacrificed. There is no neutral metric—only explicit value choices.

This points to the need for trust-aware evaluation metrics that jointly assess structural depth and factual grounding. A promising direction is to evaluate claims by type: STRUCTURAL claims should be evaluated for internal consistency with the artifact; KNOWLEDGE claims should be evaluated against ground truth; ASSUMED claims should be flagged as requiring external verification. We do not implement such a metric here but identify it as essential future work.

---

# Limitations

We acknowledge substantial limitations that constrain the generality of our findings.

**Sample sizes.** Most experiments report N=1-5 per condition. The taxonomy of 13 levels emerged from iterative experimentation rather than systematic sampling. Statistical claims (e.g., "67% first-try reliability") are based on limited runs and should be interpreted as provisional estimates rather than precise measurements. The conservation law observations, while consistent across artifacts, derive from fewer than 100 total outputs.

**Model-as-judge evaluation.** Output quality was assessed using Haiku (and occasionally Sonnet) as evaluators. This introduces potential circular bias: models from the same family may share systematic blind spots or preferences. We did not use GPT-4, human annotators, or automated test suites as alternative evaluators. The 9/10 quality scores reflect intra-family judgment, not ground-truth accuracy.

**No human evaluation.** We did not conduct human evaluation of output quality, novelty, or usefulness. Whether human experts would find prism outputs more valuable than vanilla outputs remains untested. The claim that prisms "produce structural analysis rather than code reviews" is based on our reading of outputs, not systematic human comparison.

**Limited model diversity.** Deep operations (L8+) were tested primarily on Claude models (Haiku, Sonnet, Opus). Gemini was included in some experiments, but cross-model transfer for the deepest operations remains underexplored. We do not know whether the taxonomy generalizes to GPT-4, LLaMA, Mistral, or other model families.

**Python-dominant validation.** Real code experiments focused on Python libraries (Starlette, Click, Tenacity). The Go and TypeScript experiments were single-run preliminary tests. Whether prism behavior generalizes across programming paradigms (functional, logic, systems languages) is unknown.

**Conservation law status.** The "conservation law of the catalog" and related invariants are empirical observations on limited data, not proven theorems. The claim that "form is conserved by method, substance by artifact" is a pattern we observed, not a mathematically derived result. It may not hold for all artifacts or all prisms.

**Autopoietic convergence.** The claim that L13 represents a reflexive fixed point is based on six experiments using a two-stage protocol. We tested only one generation chain. Whether the framework consistently terminates at L13 across diverse artifacts and models requires additional validation.

**Scrambled vocabulary result.** The finding that abstract nouns trigger summary mode while concrete nouns trigger analytical mode (Principles 15, 113) is based on limited experiments. The N=1 scrambled vocabulary test needs replication.

**No downstream task validation.** We did not validate whether identified bugs were real, whether suggested fixes improved code, or whether structural insights transferred to practical tasks. The gap between "produces conservation laws" and "produces useful engineering guidance" remains unmeasured.

---

# Conclusion

This work presents a practical contribution to prompt engineering: structured prompts that classify claims by epistemic type enable a form of self-correction that generic methods cannot achieve. The core finding is modest but replicable across models and domains—claim-type awareness tells the model what to preserve (structural insights) and what to scrutinize (specific assertions).

The observation that specificity trades against verifiability—appearing across targets, models, and prism types—suggests a constraint worth investigating. Whether this reflects a fundamental information-theoretic limit or a contingent property of current architectures remains open. We do not claim to have proven a theorem; we report an empirical pattern.

The taxonomy of 13 compression levels and 204 design principles is offered as a map of explored territory, not a complete survey. The diamond topology (linear trunk, constructive divergence, reflexive convergence) describes what we observed, not what must exist. There may be branches we did not find or levels we mischaracterized.

The tool and all prompts are released for reproduction. We invite replication, refutation, and extension. The strongest claim we make is methodological: before concluding that a model cannot perform a type of reasoning, test whether a prism can elicit it. The cheapest model with the right prompt outperformed the most expensive model without one in our experiments. Whether this holds generally is precisely the sort of question that warrants independent investigation.

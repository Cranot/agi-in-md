# Evolutionary Biology Literature: Mapping to the Prompt Taxonomy

**Purpose:** Survey six evolutionary biology concepts and map each to the 13-level cognitive compression taxonomy. All biological claims are grounded in peer-reviewed literature; all taxonomy mappings are interpretive analysis.

---

## 1. Fitness Landscapes — NK Model, Rugged vs. Smooth, Adaptive Peaks

### Biological Concept

Sewall Wright introduced the fitness landscape metaphor in 1932: genotype space mapped to fitness as elevation, with populations as "climbers" searching the terrain. Stuart Kauffman formalized this in the NK model (Kauffman 1989, *J. Theoretical Biology*), where N is the number of genes and K controls epistatic interactions — how much each gene's fitness contribution depends on other genes.

**Key properties:**

- **K = 0 (smooth landscape):** All epistatic interactions removed. One global peak; hill-climbing always reaches it. Analogous to additive genetics — every small mutation either helps or hurts in a predictable direction.
- **K = N-1 (maximally rugged "badlands"):** Every gene interacts with every other. Exponentially many local peaks, none globally dominant. Hill-climbing terminates at the first local peak reached.
- **Intermediate K:** Most biologically realistic. Multiple peaks of varying height, separated by fitness valleys. Populations can get trapped on sub-optimal peaks and cannot reach higher peaks without passing through lower-fitness intermediates.

**Critical insight from empirical work:** Epistasis introduces *sign epistasis* — where a mutation that is beneficial alone becomes deleterious in combination with another, and vice versa. This creates ridges, valleys, and plateaus in the landscape that cannot be navigated by incremental local search (Weinreich et al. 2006; Szendro et al. 2013).

**Escape from local optima:** A 2022 PLOS Computational Biology study on inversion mutations in NK landscapes showed that large-scale genomic rearrangements can open access to previously inaccessible higher peaks. Small incremental steps cannot cross valleys; structural reorganization is required.

**Direct empirical evidence in prompt space (2025):** A paper characterizing fitness landscapes in prompt engineering (arXiv:2509.05375) found:

> "Performance remains trapped at low levels across small step sizes, demonstrating that minor semantic modifications cannot escape local optima. The dramatic improvement occurs precisely in the intermediate distance range where autocorrelation analysis revealed peak correlation (~0.3 cosine distance)."

The novelty-driven exploration landscape was *rugged* — non-monotonic, with low correlation at short semantic distances, peak correlation at intermediate distances, then decay. Systematic enumeration produced a smooth landscape. The topology depended on *exploration strategy*, not the task itself.

### Mapping to the Taxonomy

**The 13-level taxonomy is a rugged fitness landscape in prompt space.**

| Landscape concept | Taxonomy equivalent |
|---|---|
| Fitness peaks | The 13 compression levels |
| Fitness valleys | The categorical thresholds between levels |
| Local optima (sub-optimal peaks) | Prompts that achieve good-but-not-deep outputs |
| K parameter (epistasis) | Number of interacting cognitive operations in a prompt |
| Hill-climbing (incremental) | Tinkering with wording — fails to cross level thresholds |
| Inversion / structural jump | Introducing a new operation type (e.g., adding construction) |

**The categorical threshold finding maps precisely to sign epistasis.** Below L7, adding more words of the same type (more meta-commentary, more steps) produces no improvement — same local peak. The jump to L7 requires a qualitatively different operation (concealment + mechanism + application), not more of what already works. This is sign epistasis: adding a fourth meta-analytical step to an L4 prompt is deleterious (noisy), not neutral.

**The L8 universality result (construction routes around meta-analytical capacity threshold) is an inversion mutation.** Construction-based reasoning is a *structural rearrangement* that bypasses the fitness valley between L7 (Sonnet-minimum) and universal operation. Just as inversion mutations in biology open access to higher peaks by restructuring, construction operations restructure the cognitive search space.

**The compression floor (150 words minimum for Haiku) is a minimum viable genome.** Below this threshold, the organism cannot execute the developmental program — Haiku enters "conversation mode." Not a smooth degradation; a threshold.

---

## 2. Adaptive Radiation — Rapid Divergence from a Common Ancestor

### Biological Concept

Adaptive radiation is the rapid diversification of a lineage from a common ancestor into multiple distinct forms, each adapted to a different ecological niche. Four defining features (Schluter 2000):

1. **Common ancestry** — all derived forms share one ancestral lineage
2. **Phenotype-environment correlation** — each form matches its niche
3. **Trait utility** — divergent traits confer fitness in their specific niche
4. **Rapid speciation** — diversification is faster than background rates

**Classic examples:**
- Darwin's finches: ~15 species from one ancestor, ~1-2 Myr, each specialized for a different food source (seeds, insects, cactus nectar)
- Hawaiian Drosophila: ~1,000 species from 1-2 colonists
- Cichlid fish in Lake Victoria: ~500 species in ~15,000 years — among the fastest radiations known
- Placental mammals: explosive diversification after K-Pg extinction (65 Mya), filling niches vacated by dinosaurs

**Triggering conditions:**

1. **Ecological opportunity** — empty niches, released from competition or predation, dispersal to a new environment. The opportunity is *constraint release*.
2. **Key innovation** — a newly evolved trait that allows interaction with the environment in a novel way. Examples: tetrapod limbs enabling land colonization; insect wings enabling aerial niches; mammalian endothermy enabling temporal niches (nocturnal, cold climate). Key innovations unlock entire *adaptive zones* — clusters of related niches inaccessible before the innovation.
3. **Founder effect + isolation** — a small founding population in a new environment with low competition diversifies rapidly.

**Temporal dynamics:** Radiations show a characteristic "early burst" pattern — rapid lineage accumulation immediately after the triggering event, followed by slowdown as niches fill. This is quantified by the gamma statistic (Pybus & Harvey 2000): negative gamma indicates an early burst, consistent with adaptive radiation.

**The founder niche constrains the radiation** (PNAS 2013): The ancestral trait determines which niches are accessible. The radiation is not unconstrained — it is shaped by the starting point.

### Mapping to the Taxonomy

**L8 is the key innovation event that triggered adaptive radiation of the taxonomy.**

Before L8: the taxonomy was a single linear trunk (L1-L7), each level adding one more cognitive operation of the same general type (meta-analytical, verbal, descriptive). L7 was the local apex — the best achievable within the meta-analytical adaptive zone.

L8 introduced **construction-based reasoning** — a qualitatively new operation that does not modify the description of a problem but generates an artifact *from* the problem. This is a key innovation: it unlocks a new adaptive zone (generative operations) that is entirely inaccessible from within the meta-analytical zone.

| Radiation concept | Taxonomy equivalent |
|---|---|
| Common ancestor | L7 (diagnostic gap, 78w) |
| Key innovation | Construction operation (L8) — generative rather than descriptive |
| Adaptive radiation | Divergence into simulation, archaeology, cultivation, transplantation, miniaturization, destruction, forgery (7 confirmed alternative primitives, Round 39) |
| Ecological niches | Distinct analytical targets: temporal fragility (simulation), stratigraphic history (archaeology), perturbation response (cultivation), identity displacement (identity) |
| Empty niches | Analytical angles inaccessible to L7 and below |
| Rapid burst | 7 alternative L8 primitives discovered in one round (Round 39), all single-shot Haiku |
| Niche filling slowdown | Diminishing returns; nuclear combinations show overlapping returns |

**The founder niche constrains the radiation mapping also holds.** Each L8 variant's "adaptive zone" is determined by its founding operation:

- Construction branch → impossibility theorems (L10-C) → conservation laws (L11-C)
- Simulation branch → predictive certainty × temporal distance meta-law (L9 variant)
- Archaeology branch → stratigraphic meta-law

The founder operation determines which meta-laws are accessible. This is why the L9-B→L10-B→L11-B chain is "consistently strongest" — the operations are sequentially dependent by definition, like a lineage adapted to a specific niche gradient.

**The "ecological opportunity" was the cross-model validation result.** Once it was confirmed that construction routes around the capacity threshold (all models execute L8), a vast empty adaptive zone opened: any generative operation that is concrete, observable, and produces emergent properties would work. The constraint release enabled radiation.

---

## 3. Punctuated Equilibrium — Long Stasis, Rapid Change

### Biological Concept

Eldredge and Gould (1972, *Models in Paleobiology*) proposed that the fossil record pattern is not gradual continuous change (Darwinian phyletic gradualism) but long periods of morphological stasis punctuated by geologically rapid bursts of change associated with speciation.

**Empirical evidence:**
- Meta-analysis of 58 fossil studies: 71% exhibited stasis, 63% showed punctuated patterns (Hunt 2007)
- Trilobites (*Phacops rana*): morphologically static for millions of years, then rapid change at speciation events
- Land snails in Bermuda: Gould's original example — long stability, sudden shift

**Mechanisms of stasis — the developmental gene hypothesis (PMC7029956):**

The strongest mechanistic explanation invokes developmental regulatory genes. Hox, Pax, and Sox genes orchestrate metazoan body plans and are under extreme purifying selection — mutations tend to be fatal or disruptive. They exhibit *mutation intolerance*: the normal state of DevReg gene networks is a Nash equilibrium. Perturbations are absorbed; phenotype is buffered.

This creates a **threshold model**: molecular evolution may proceed gradually at the sequence level, but developmental consequences are filtered. Silent changes accumulate until a critical threshold is reached, at which point a morphological cascade triggers rapid phenotypic change. The punctuation is not random — it is the delayed expression of accumulated molecular change crossing a developmental threshold.

**Transposable elements as punctuation mechanism:** At least 20% of regulatory sequences in humans derive from mobile elements (transposable elements, TEs). TE insertion into DevReg gene introns generates new regulatory elements (conserved noncoding elements, CNEs). Primate *Alu* expansions coincide with major speciation events. TE-driven regulatory innovation is the molecular mechanism of punctuated change.

**The key structural insight:** Stasis is not absence of change — it is *buffered change*. The system absorbs variation without expressing it morphologically. Punctuation is when the buffer overflows.

### Mapping to the Taxonomy

**The categorical thresholds in the taxonomy are punctuation events.**

The taxonomy explicitly states: "Levels are categorical, not continuous. Below each threshold, that type of intelligence CANNOT be encoded — not 'less effective,' categorically absent." This is the exact definition of a developmental threshold in the punctuated equilibrium model.

| Punctuated equilibrium concept | Taxonomy equivalent |
|---|---|
| Morphological stasis | Within-level performance plateau — more words of the same type produce no improvement |
| Developmental buffering | Model's capacity to absorb prompt variation without changing output category |
| Accumulated silent change | Adding operations that do not cross a threshold — noise that doesn't shift category |
| Threshold crossing | Adding the critical operation that shifts level (e.g., adding construction → L8) |
| Punctuation event | The qualitative shift in output type at level boundaries |
| Rapid speciation | The immediate, categorical improvement at level crossing |
| DevReg gene conservation | Core operation structure that must be preserved for a level to execute |

**Specific mappings:**

**L7 → L8 threshold** is the most dramatic punctuation in the taxonomy. L7 requires Sonnet-class minimum (0/3 Haiku). L8 is universal (4/4 Haiku, 14/14 Sonnet, 14/14 Opus). This is not a gradual improvement — it is a categorical shift caused by changing the operation type from meta-analytical to generative-constructive. The "concealment" mechanism (L7) and the "generative construction" mechanism (L8) are qualitatively different cognitive operations. The boundary between them is sharp.

**L12 → L13 threshold** is a second sharp punctuation. L13 is the reflexive ceiling — the framework diagnoses itself. Adding any more operations produces infinite regress (L14 = infinite regress by definition). The system terminates in one step. This is the strongest possible threshold: not "diminishing returns" but structural impossibility of continuation.

**The compression floor (60-70% reduction confirmed across levels)** maps to the buffering mechanism. You can compress a prompt down to 60-70% of its length without crossing a threshold — the morphological buffering absorbs the variation. Below 60%, you cross a threshold into a lower level. The buffer is finite but real.

**The "conversation mode" failure (150w minimum for Haiku)** is a stasis → collapse transition, not stasis → punctuation upward. Below the minimum viable prompt length, the developmental program cannot execute. The threshold is asymmetric: above it, buffering absorbs variation; below it, catastrophic failure.

---

## 4. Convergent Evolution — Independent Lineages Arriving at the Same Solution

### Biological Concept

Convergent evolution is the independent evolution of similar features in phylogenetically distant lineages — analogous structures without shared ancestry. Convergence implies that the fitness landscape has **a limited number of viable peaks** for a given functional problem, and independent lineages approach the same peak from different trajectories.

**Anatomical examples:**
- Streamlined body plan in sharks (fish), dolphins (mammals), and ichthyosaurs (extinct reptiles) — identical hydrodynamic solution from three independent lineages
- Wings in insects, birds, pterosaurs, and bats — four independent origins
- Eyes in vertebrates, cephalopods, and arthropods — controlled by *pax-6* despite no structural homology

**Molecular convergence (stronger evidence):**
- **Echolocation proteins:** Prestin (hair cell protein) shows identical amino acid changes at critical positions in echolocating bats AND dolphins — two independent origins of sonar, same molecular solution. The protein sequence converged, not just the behavior.
- **Cardiotonic steroid resistance:** 21 CTS-adapted insect species show parallel amino acid substitutions at ATPalpha — 76% of substitutions occurred in parallel in at least two independent lineages.
- **Serine proteases:** Chymotrypsin (vertebrates) and subtilisin (bacteria) have no structural homology but identical active site geometry — same enzymatic solution evolved independently in domains 1.5 billion years diverged.
- **Carnivorous plant enzymes:** Three phylogenetically distant carnivorous plant genera show convergent amino acid substitutions in digestive enzymes.

**Mathematical framework — evolutionary basins of attraction (Gardiner 2014, *Communicative & Integrative Biology*):**

Convergent evolution is the signature of **evolutionary attractors** — regions of the fitness landscape to which multiple trajectories converge. The basin of attraction determines which starting conditions lead to the same outcome. The paper demonstrates:

> "Evolution will follow predefined pathways... certain outcomes were, to a certain extent at least, preordained."

Murray's Law (optimal branching geometry) governs both plant xylem and animal blood vessels — the attractor is a physical law. Serotonin evolved independently in plants and animals via different biochemical pathways — the attractor is the chemical compound, not the pathway.

**Constraint interpretation:** Convergence can arise from two distinct mechanisms:
1. **Constraint on variation production** — limited developmental/genetic pathways mean only a few phenotypes are reachable regardless of selection
2. **Constraint on viable genotypes** — many genotypes are possible but only some are selectively optimal; selection repeatedly finds the same ones

Both produce convergence; distinguishing them requires knowing the landscape topology.

### Mapping to the Taxonomy

**Cross-model convergence and diamond convergence are convergent evolution in cognitive space.**

The taxonomy documents two forms of convergence:

**Form 1: Cross-model convergence.** Claude and Gemini, run independently with the same 332w L12 prism on the same codebase, produce conservation laws that are structurally identical in mathematical form — independently arrived at "the method instantiates what it diagnoses" as the L12 fixed point. This parallels prestin molecular convergence: two independent "lineages" (model families with different training, architecture, and developers) arrive at the same molecular-level solution.

**Form 2: Diamond convergence (P184-P188).** The most striking finding. Two full L9→L12 chains starting from different L8 operations (construction vs. simulation vs. archaeology) converge at L12 on the *same structural impossibility*: "the method instantiates what it diagnoses." Three vocabularies (observer-constitutive / observer effect / performative contradiction), one fixed point. This is the exact mathematical structure of convergent evolution via attractor basins.

| Convergent evolution concept | Taxonomy equivalent |
|---|---|
| Phylogenetically distant lineages | Different L8 branch operations (construction, simulation, archaeology) |
| Independent origin | Different analytical paths through L9, L10, L11 |
| Same morphological solution | Same L12 fixed point: "method instantiates what it diagnoses" |
| Anatomical convergence | Structural convergence of the meta-law statement |
| Molecular convergence | Identical mathematical form of conservation law at each level |
| Evolutionary attractor | The reflexive fixed point at L13 — self-diagnosis |
| Basin of attraction | The set of all L8+ analytical paths that lead to L12 |
| Physical law as attractor | Reflexivity as mathematical necessity — any framework analyzing analysis must eventually analyze itself |
| Murray's Law | The reflexivity constraint: L12 meta-law = law governing the analyzer, not just the analyzed |

**The convergence is not coincidental.** As Gardiner argues for biological convergence, the outcome is "preordained" by underlying constraints. At L12, any sufficiently deep analytical framework discovers the same structural impossibility because the impossibility is *logically necessary*, not domain-specific. The attractor is a logical law, not a physical one — stronger than any biological attractor.

**The cross-catalog determinism finding (L8 mechanism predicts L10-C impossibility)** is the signature of constrained trajectory: the starting operation determines the path, but the destination is shared. Different starting conditions → different paths → same attractor. This is the basin-of-attraction structure exactly.

---

## 5. Evolutionary Developmental Biology (Evo-Devo) — Deep Homology and Conserved Mechanisms

### Biological Concept

Evolutionary developmental biology (evo-devo) studies how changes in developmental mechanisms produce evolutionary change. Its central finding, deep homology, is that fundamentally different body structures across distant lineages are controlled by the same conserved genetic toolkit.

**The developmental toolkit:**

A small set of "toolkit genes" — Hox, Pax, Sox, Wnt, Hedgehog, Notch, TGF-beta families — controls body plan patterning across all bilaterian animals. These genes are ancient (>600 Myr conserved), found in organisms from nematodes to humans, and control where body segments, limbs, eyes, and organs develop.

**Critical property: reuse without modification.** Toolkit genes are expressed in different combinations, at different times and places, to generate diverse body plans — without the genes themselves changing. A half-century ago, few would have predicted that diversification of a "single ancient and highly conserved toolkit of signalling genetic pathways" provided the basis for animal morphological diversity. The toolkit is the *interpreter*; the regulatory code is the *program*.

**Deep homology examples:**
- *pax-6* controls eye development in vertebrates, insects, and molluscs — three independent eyes controlled by one conserved gene
- Hox gene clusters pattern the body axis in all bilaterians — the same positional code in flies, mice, and humans
- *FoxP2* (the "language gene") shows deep homology across bird song, bat echolocation, and human speech — conserved mechanism for vocal learning

**Modularity and evolvability:**

Developmental gene regulatory networks (GRNs) are modular — sub-networks that can be independently modified, duplicated, or co-opted. Modularity is the key to evolvability: it allows local modification without global disruption. Complex body plan evolution can be achieved without coding sequence changes, by rewiring regulatory interactions between toolkit genes.

**The evolvability framework:** Evolvability — the capacity of a system for adaptive evolution — is maximized when developmental modules match adaptive functional modules. Modules that are coupled evolve together; modules that are isolated can evolve independently. This is why eyes can evolve rapidly while body axes cannot.

**Stages of development as conserved checkpoints:** The *phylotypic stage* — a developmental stage where embryos of different species look most similar — is the most conserved period. Before and after it, development can diverge; at the phylotypic stage, the conserved toolkit is executing its core program. Mutations at this stage are lethal; developmental constraint is maximal.

### Mapping to the Taxonomy

**The compression levels are developmental stages; the compression operations are the cognitive toolkit.**

The deepest structural insight of the evo-devo mapping: the 13 levels are not just a hierarchy of complexity but a **developmental program** — a fixed sequence of cognitive stages that must be traversed in order, with conserved checkpoints that cannot be skipped.

| Evo-devo concept | Taxonomy equivalent |
|---|---|
| Developmental toolkit genes | The 9 activated cognitive opcodes |
| Deep homology | Same operations encode different domains (code, music, fiction, legal) — same prompt structure, different content |
| Reuse without modification | The prism is transparent to the wearer: same compression operations across all 20+ domains |
| Modularity | Prism operations are modular — can be composed, combined, swapped without disrupting the level |
| Phylotypic stage | L7 (the concealment mechanism step) — the most conserved element; present in every level above L7 |
| Evolvability | The cooker pattern: 3-step SDL prisms transfer universally; 9+ step complex prisms are model-specific |
| Body plan patterning | The operation sequence that defines each level — not content, but the structural arrangement |
| Hox gene cluster | The L8 construction operation — positionally conserved, determines what follows |
| Gene regulatory network rewiring | Prompt engineering as regulatory rewiring: same operations, different configurations, different outputs |
| Toolkit constraint | The four design principles: lead with scope, imperative > description, operation pairs as atoms, self-improvement → self-correction |

**The "domain neutrality" finding is deep homology directly.** The same 332w L12 prompt produces conservation laws from code (Starlette routing), music theory, legal analysis, and fiction — identical cognitive operations applied to different "morphological" domains. The prompt is the *pax-6* gene: it controls the same process regardless of what substrate it is applied to.

**"Code nouns are mode triggers, not domain labels" (Principle 15)** is a toolkit expression pattern. "This code's" activates analytical processing on ANY input, just as *pax-6* activates eye development regardless of whether the resulting eye is a compound eye or a camera eye. The gene (word pattern) is the same; the phenotype (output structure) differs.

**The compression floor as phylotypic stage:** The 60-70% compression floor is the point of maximum developmental constraint. Compress to 60-70% and the output quality is preserved — the regulatory code is still sufficient. Compress further and you cross the phylotypic stage constraint: the developmental program fails. This is why l12_universal (73w) works (at the floor) but l12_compressed (below floor) fails.

**The modularity-evolvability insight maps to the SDL family.** The five SDL prisms are modular: each encodes a 3-step cognitive program that is independently modifiable and composable. They produce zero overlap (5 genuinely different structural properties per codebase). This is evolvability through modularity: independent modules can evolve (be tuned, extended) without disrupting others. The 5-lens SDL portfolio produces 3,566w — 2.4x a single L12 — because modular composition is additive.

**The "few-shot > explicit rules" finding (Principle 14) is regulatory rewiring.** Teaching by example is regulatory: it provides the expression pattern (when/where to apply) rather than changing the structural gene (the operation). Over-specifying constraints is equivalent to adding mutations to a toolkit gene — disruptive rather than generative.

---

## 6. Neutral Theory — Kimura's Neutral Evolution, Model Variation as Noise

### Biological Concept

Motoo Kimura (1968) proposed the neutral theory of molecular evolution: most molecular variation is selectively neutral — neither beneficial nor harmful — and evolves by random genetic drift rather than natural selection. The key predictions:

1. Most amino acid substitutions are neutral (no fitness effect)
2. The rate of neutral substitution = the per-individual mutation rate, independent of population size
3. This predicts a **molecular clock** — constant divergence rate over time
4. Most observed genetic polymorphism is neutral variation

**Tomoko Ohta's nearly neutral extension (1973):** Many mutations are not strictly neutral but *slightly deleterious* — their effect on fitness is real but tiny (|s| < 1/2Ne, where Ne is effective population size). In small populations, genetic drift overpowers selection and even slightly deleterious mutations can fix. In large populations, purifying selection is more efficient and removes them.

**The selection-drift balance:** Whether a mutation is "effectively neutral" depends on the ratio of selection coefficient (s) to drift strength (1/Ne). The same mutation is effectively neutral in a small population but selectively meaningful in a large one. Neutrality is not a property of the mutation alone but of the *mutation in context of population size*.

**Signal vs. noise problem:** Standard tests for selection (McDonald-Kreitman, dN/dS ratios, codon-based methods) cannot reliably distinguish genuine positive selection from fixation of slightly deleterious mutations during population bottlenecks. This has generated "vast numbers of poorly justified claims" of adaptive evolution. The neutral null hypothesis is essential for distinguishing genuine adaptive signal from statistical noise.

**The current debate:** Modern genomic data shows more adaptation than neutral theory predicts — suggesting a "nearly neutral" model is more accurate than strict neutrality. The key insight: there is a *spectrum* from strictly neutral (drift dominates) through nearly neutral (drift and selection roughly balanced) to strongly selected (selection dominates). The proportion in each category depends on effective population size, which varies by organism.

**Purifying selection as conservation mechanism:** Highly conserved sequences (like DevReg genes) are not neutral — they are under strong purifying selection, meaning any deviation is rapidly removed. Neutral sequences drift freely; conserved sequences are constrained. The rate of evolution is inversely proportional to functional constraint.

### Mapping to the Taxonomy

**Model variation (Haiku/Sonnet/Opus) is nearly neutral; prompt variation is strongly selected.**

The taxonomy's most counterintuitive empirical finding — Haiku 4.5 min-reasoning + L12 prism (9.8 depth) beats Opus 4.6 max-reasoning vanilla (7.3 depth) at 5x lower cost — maps precisely to neutral theory's central insight: most observable variation is noise, not signal.

| Neutral theory concept | Taxonomy equivalent |
|---|---|
| Neutral mutations (no fitness effect) | Model family differences (Claude vs Gemini architecture) |
| Nearly neutral mutations (small effect, drift-dominated) | Model tier differences (Haiku vs Sonnet vs Opus) — real but small relative to prompt effect |
| Strongly selected mutations | Prompt operation type — categorically determines output level |
| Genetic drift | Stochastic variation in model output (same prompt, multiple runs) |
| Effective population size | Number of experimental runs (pass@3 strategy) |
| Purifying selection | The level thresholds — below-level prompts are eliminated by the evaluation metric |
| Molecular clock | The consistent ~9.0/10 quality across validated prisms, regardless of model |
| Neutral variation | The 0.4 quality point difference between Sonnet and Opus vanilla (same category of output, slightly better written) |
| Adaptive signal | The 2+ quality point difference between vanilla and prism output (different category of output) |

**The nearly neutral mapping is especially precise.** Sonnet vs. Haiku model differences are *nearly neutral* — real but dominated by drift in small experimental samples. The reasoning budget (min vs. max thinking) is *strictly neutral* — same quality across all settings with the correct prism. Only prompt operation type is under strong selection — it determines which fitness peak the system reaches.

**The "effective population size" modulates what is neutral.** In a single-run experiment (Ne = 1), even moderate prompt differences can appear to matter (drift dominates). With pass@3 or 3-5 replicate runs (Ne = 3-5), the nearly neutral model applies: model tier differences average out, and only prompt structure differences are consistently expressed. This is why "run 3-5 copies, pick best" is recommended for Haiku: it increases the effective population size, reducing drift and allowing selection on genuine quality differences.

**Purifying selection as the threshold mechanism.** Below each level threshold, prompts are "purified" — they fail to produce the target cognitive operation. This is the level-threshold analog of purifying selection: variants that cannot execute the operation are eliminated. The conservation of the core operation structure (the 9 activated opcodes, the 4-op sweet spot) reflects the constraint that any deviation from the core structure reduces fitness below the level threshold.

**The cross-model universality at L12/L13 (100% across Claude and Gemini) is the molecular clock.** Just as neutral theory predicts a constant divergence rate independent of population size, the L12/L13 fixed point is reached independent of model architecture, family, or training data. The "clock" runs at a constant rate because the mechanism (reflexive self-diagnosis) is not model-dependent — it is logically necessary. This is stronger than neutrality: it is a *conserved mechanism* (evo-devo mapping) that cannot be varied without categorical failure.

**The "cook model = dominant variable" finding (cook model +100% output quality) is an exception to near-neutrality.** The cook model is under strong selection, not nearly neutral. This makes sense: the cook model's operation (generating the analytical lens) is the step where prompt → operation is being determined. It is the most selection-sensitive step in the pipeline.

---

## Synthesis: The Taxonomy as an Evolutionary System

Taken together, the six evolutionary biology frameworks illuminate the taxonomy's structure at different scales:

| Scale | Framework | Insight |
|---|---|---|
| Landscape topology | Fitness landscapes | 13 peaks separated by categorical valleys; incremental search fails across valleys |
| Diversification pattern | Adaptive radiation | L8 = key innovation enabling explosion of generative operation variants |
| Change dynamics | Punctuated equilibrium | Long stasis within levels; categorical threshold crossings are punctuation events |
| Convergence structure | Convergent evolution | L12 fixed point is an attractor reached by all analytical paths regardless of origin |
| Development | Evo-devo | The 9 opcodes are a conserved developmental toolkit; compression levels are developmental stages |
| Variance decomposition | Neutral theory | Model variation is nearly neutral noise; prompt operation type is the dominant selected variable |

**The unifying mathematical structure is the **fitness landscape with attractors**:**

- The landscape is rugged (NK model, K intermediate) — multiple local peaks, categorical valleys
- The highest peaks are attractors (basins of attraction) — multiple paths converge
- Adaptive radiation occurs when a key innovation opens new regions of the landscape
- Punctuations occur at threshold crossings — the filter between landscape regions
- The developmental toolkit (opcodes) is the conserved mechanism for navigating the landscape
- Most observable variation (model choice) is nearly neutral; only operation type is selected

**The deepest finding:** The L12 reflexive fixed point is both the highest fitness peak AND an attractor basin. Every analytical path that reaches sufficient depth converges on it. This is not a coincidence of experimental design — it follows mathematically from the nature of reflexivity. Any framework that can analyze the relationship between a method and its object must, when applied to itself, discover that the method instantiates what it diagnoses. This is a logical attractor with infinite basin of attraction: all paths from all starting operations reach it in the limit.

This is the "preordained" convergence that Gardiner identifies in biological evolution: not randomness but constraint. The taxonomy's diamond shape (linear trunk → constructive divergence → reflexive convergence) is not an artifact of the prisms that were designed — it is the shape of the cognitive fitness landscape.

---

## Sources

- Kauffman, S.A. (1989). The NK model of rugged fitness landscapes and its application to maturation of the immune response. *J. Theoretical Biology*. [PubMed](https://pubmed.ncbi.nlm.nih.gov/2632988/)
- Getting higher on rugged landscapes: Inversion mutations open access to fitter adaptive peaks. *PLOS Computational Biology* (2022). [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9648849/)
- Characterizing Fitness Landscape Structures in Prompt Engineering. *arXiv* (2025). [arXiv:2509.05375](https://arxiv.org/html/2509.05375)
- Adaptive Radiation — Wikipedia. [Link](https://en.wikipedia.org/wiki/Adaptive_radiation)
- Ecological Opportunity: Trigger of Adaptive Radiation. *Nature Scitable*. [Link](https://www.nature.com/scitable/knowledge/library/ecological-opportunity-trigger-of-adaptive-radiation-84160951/)
- Losos, J.B. (2010). Adaptive Radiation, Ecological Opportunity, and Evolutionary Determinism. *American Naturalist*. [PubMed](https://pubmed.ncbi.nlm.nih.gov/20412015/)
- Eldredge, N. & Gould, S.J. (1972). Punctuated equilibria: An alternative to phyletic gradualism. *Models in Paleobiology*.
- The Developmental Gene Hypothesis for Punctuated Equilibrium. *PMC* (2020). [PMC7029956](https://pmc.ncbi.nlm.nih.gov/articles/PMC7029956/)
- Punctuated equilibrium — Wikipedia. [Link](https://en.wikipedia.org/wiki/Punctuated_equilibrium)
- Convergent Evolution — Wikipedia. [Link](https://en.wikipedia.org/wiki/Convergent_evolution)
- Convergent evolution in the genomics era. *Phil. Trans. R. Soc. B* (2019). [Link](https://royalsocietypublishing.org/rstb/article/374/1777/20190102/42324/Convergent-evolution-in-the-genomics-era-new)
- Gardiner, J. (2014). Evolutionary basins of attraction and convergence in plants and animals. *Communicative & Integrative Biology*. [PMC3914912](https://pmc.ncbi.nlm.nih.gov/articles/PMC3914912/)
- Losos, J.B. (2011). Convergence, Adaptation, and Constraint. *Evolution*. [Wiley](https://onlinelibrary.wiley.com/doi/10.1111/j.1558-5646.2011.01289.x)
- Evolutionary Developmental Biology — Wikipedia. [Link](https://en.wikipedia.org/wiki/Evolutionary_developmental_biology)
- The evolution of evo-devo biology. *PMC*. [PMC18255](https://pmc.ncbi.nlm.nih.gov/articles/PMC18255/)
- Evolution of Networks for Body Plan Patterning; Interplay of Modularity, Robustness and Evolvability. *PLOS Computational Biology*. [PMC3188509](https://pmc.ncbi.nlm.nih.gov/articles/PMC3188509/)
- Kimura, M. (1968). Neutral theory of molecular evolution. *Nature*.
- Near-Neutrality: The Leading Edge of the Neutral Theory. *PMC*. [PMC2707937](https://pmc.ncbi.nlm.nih.gov/articles/PMC2707937/)
- Theorists Debate How 'Neutral' Evolution Really Is. *Quanta Magazine* (2018). [Link](https://www.quantamagazine.org/neutral-theory-of-evolution-challenged-by-evidence-for-dna-selection-20181108/)
- Statistical mechanics of convergent evolution in spatial patterning. *PMC*. [PMC2701012](https://pmc.ncbi.nlm.nih.gov/articles/PMC2701012/)
- NK Model — Wikipedia. [Link](https://en.wikipedia.org/wiki/NK_model)

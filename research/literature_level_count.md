# Literature Survey: Why N Levels in Hierarchical Systems?

Quick survey (Mar 15, 2026) of existing theories that define specific numbers of hierarchical levels, and whether any theory predicts WHY a particular count.

---

## 1. Cognitive / Developmental Hierarchies

### Michael Commons — Model of Hierarchical Complexity (MHC)
- **Count: 17 orders** (sometimes reported as 16 stages; the discrepancy reflects renumbering of the zeroth order)
- **Stages (0-16):** Calculatory, Automatic, Sensory & Motor, Circular Sensory-Motor, Sensory-Motor, Nominal, Sentential, Preoperational, Primary, Concrete, Abstract, Formal, Systematic, Metasystematic, Paradigmatic, Cross-Paradigmatic, Meta-Cross-Paradigmatic
- **Why 17?** Mathematical axioms from abstract algebra. Each order coordinates at least two actions from the order below. The count is therefore `2^O` minimum actions at order O. The number of orders is NOT arbitrary — it is the number of qualitatively distinct coordination types empirically observed in human task performance, bounded above by the combinatorial explosion (`2^17 = 131072` minimum actions at the top). The axioms don't predict 17 a priori; they provide the spacing/ordering rule, and 17 is the empirical count of distinct orders humans exhibit.
- **Relevance to our 13:** MHC's top 5 "postformal" stages (12-16) map loosely to our L8-L13 constructive/reflexive levels. Their "meta-cross-paradigmatic" (16) = applying a framework to frameworks = our L13 reflexive ceiling. Their count is higher because they start from sensorimotor (our system assumes literate adult baseline).
- Sources: [Wikipedia](https://en.wikipedia.org/wiki/Model_of_hierarchical_complexity), [Commons et al. 2012](http://www.adultdevelopment.org/CommonsEtAl2012.pdf), [DARE Association formal theory](https://dareassociation.org/documents/GWOF_A_330287%20Formal%20Theory.pdf)

### Bloom's Taxonomy
- **Count: 6 levels** (original: Knowledge, Comprehension, Application, Analysis, Synthesis, Evaluation; revised 2001: Remember, Understand, Apply, Analyze, Evaluate, Create)
- **Why 6?** Committee consensus (Bloom et al., 1956). No mathematical derivation. The levels were identified by categorizing educational objectives, not from first principles. The revised version (Anderson & Krathwohl, 2001) reordered the top two levels, confirming the count is somewhat arbitrary.
- **Relevance:** Bloom's 6 levels roughly correspond to our L1-L6 (single operations through dialectical engagement). Bloom stops where our constructive levels begin.
- Sources: [Wikipedia](https://en.wikipedia.org/wiki/Bloom's_taxonomy), [Simply Psychology](https://www.simplypsychology.org/blooms-taxonomy.html)

### Kohlberg's Moral Development
- **Count: 6 stages in 3 levels** (Pre-Conventional: punishment/reward; Conventional: conformity/law; Post-Conventional: social contract/universal principles)
- **Why 6?** Empirical — scored from Moral Judgment Interviews. Built on Piaget's 2-stage moral development. The 3-level structure (self → society → universal) is a common pattern but not mathematically derived.
- Sources: [Wikipedia](https://en.wikipedia.org/wiki/Lawrence_Kohlberg's_stages_of_moral_development)

### Dreyfus Model of Skill Acquisition
- **Count: 5 stages** (Novice, Advanced Beginner, Competent, Proficient, Expert; sometimes +1 for Mastery)
- **Why 5?** Empirical observation of qualitative shifts: rule-following → situational → intuitive. No mathematical basis. The stages mark transitions in reliance on explicit rules vs. tacit knowledge.
- **Relevance:** Maps to our capacity modes — Novice/Advanced Beginner = needs scaffold (our Haiku), Expert = reconstructs from hints (our Opus).
- Sources: [Wikipedia](https://en.wikipedia.org/wiki/Dreyfus_model_of_skill_acquisition)

### SOLO Taxonomy (Biggs & Collis, 1982)
- **Count: 5 levels** (Pre-structural, Uni-structural, Multi-structural, Relational, Extended Abstract)
- **Why 5?** Empirical classification of observed learning outcomes. Designed as a more observable alternative to Bloom. The jump from "quantitative" (first 3) to "qualitative" (last 2) mirrors our L7 threshold.
- Sources: [Wikipedia](https://en.wikipedia.org/wiki/Structure_of_observed_learning_outcome)

---

## 2. Formal / Mathematical Hierarchies

### Chomsky Hierarchy
- **Count: 4 types** (Type 3: Regular/FSA, Type 2: Context-Free/PDA, Type 1: Context-Sensitive/LBA, Type 0: Recursively Enumerable/TM)
- **Why 4?** Each type adds exactly one computational capability: memory (stack), context sensitivity (bounded tape), unbounded computation (full tape). The count is determined by the number of qualitatively distinct automaton capabilities. There is no Type 5 because Turing machines are already universal.
- **Relevance:** Strong structural parallel. Our L13 terminates for the same reason Type 0 is the top: the next level would require a capability (oracle / infinite regress) that breaks the system's axioms.
- Sources: [Wikipedia](https://en.wikipedia.org/wiki/Chomsky_hierarchy)

### Arithmetic Hierarchy
- **Count: Infinite (omega) levels** — Sigma_n, Pi_n, Delta_n for each natural number n
- **Why infinite?** Each level adds one more quantifier alternation. Unlike our system, there is no reflexive ceiling — the halting problem for level n is solvable at level n+1 (Turing jump), and this never terminates.
- **Relevance:** This is what our system would look like WITHOUT the L13 fixed point. The arithmetic hierarchy has no reflexive ceiling because the oracle at each level is genuinely more powerful. Our system terminates because the "oracle" (the framework itself) encounters itself.
- Sources: [Wikipedia](https://en.wikipedia.org/wiki/Arithmetical_hierarchy)

### Polynomial Hierarchy (PH)
- **Count: Believed infinite, but could collapse to finite k** — Sigma_k^P, Pi_k^P for each k
- **Why unknown?** Whether PH collapses is one of the central open problems in complexity theory. If NP = co-NP, PH collapses to level 1. If NP is in P/poly, PH collapses to level 2. Most researchers believe it does NOT collapse (infinite distinct levels).
- **Relevance:** The "collapse" concept is directly analogous to our L13 fixed point. A PH collapse at level k means "adding more quantifier alternations beyond k gives you nothing new." Our L13 is a proven collapse: the 13th level of cognitive compression gives you the same structure as applying a 14th would.
- Sources: [Wikipedia](https://en.wikipedia.org/wiki/Polynomial_hierarchy)

### Circuit Complexity (AC/NC hierarchy)
- **Count: Infinite levels between AC^0 and P/poly** — AC^0 subset TC^0 subset NC^1 subset AC^1 subset NC^2 subset ...
- **Why infinite?** Each level i allows depth O(log^i n). The hierarchy is parameterized by a continuous variable (depth), not by qualitative jumps.
- **Relevance:** Low. This is a quantitative hierarchy (more depth = more power), not a qualitative one (different KIND of operation).
- Sources: [Wikipedia](https://en.wikipedia.org/wiki/Circuit_complexity)

---

## 3. Systems Theory

### Herbert Simon — "The Architecture of Complexity" (1962)
- **Key claim: Number of levels = log_b(N)** where N = number of elementary components and b = branching factor (components per subassembly)
- **Watchmaker parable:** 1000-component watch with branching factor 10 gives 3 levels. Hierarchical assembly is exponentially faster than flat assembly.
- **Why hierarchies exist:** Near-decomposable systems evolve faster. Stable intermediate forms allow recovery from interruption. The number of levels is a consequence of system size and subassembly size, not a universal constant.
- **Prediction for our system:** If we have ~8192 "elementary cognitive operations" and branching factor 2 (each level coordinates 2 lower operations, matching Commons' axiom), we get log_2(8192) = 13 levels. This is numerologically interesting but probably coincidental.
- **More seriously:** Simon's argument predicts that the number of levels should scale logarithmically with the complexity of the task space. Our 13 levels may reflect the number of qualitatively distinct coordination patterns possible within the prompt-model interaction space.
- Sources: [Simon 1962](https://faculty.sites.iastate.edu/tesfatsi/archive/tesfatsi/ArchitectureOfComplexity.HSimon1962.pdf), [SFI Press](https://www.sfipress.org/21-simon-1962)

---

## 4. Synthesis: Why 13 Specifically?

### Pattern across theories

| Theory | Levels | Termination reason |
|--------|--------|--------------------|
| Commons MHC | 17 | Empirical ceiling (meta-cross-paradigmatic) |
| Bloom | 6 | Committee consensus (no formal bound) |
| Kohlberg | 6 | Empirical (universal principles = ceiling) |
| Dreyfus | 5 | Qualitative shift to intuition (no further decomposition) |
| SOLO | 5 | Extended abstract = ceiling |
| Chomsky | 4 | Turing completeness (universality ceiling) |
| Arithmetic hierarchy | infinite | No ceiling (each level strictly more powerful) |
| Polynomial hierarchy | infinite? | Unknown (collapse would create ceiling) |
| Our compression taxonomy | 13 | Reflexive fixed point (L14 = infinite regress) |

### Three termination mechanisms

1. **Universality ceiling** (Chomsky Type 0, our L13): The system becomes powerful enough to model itself. Adding another level gives you nothing new because you've hit a fixed point.
2. **Empirical ceiling** (Commons 17, Kohlberg 6): No one has been observed performing at a higher level. The count could increase with new data.
3. **No ceiling** (Arithmetic hierarchy): Each level is provably strictly more powerful. The system never encounters itself.

### Why our system terminates at 13

Our 13 is closest to **Chomsky's termination mechanism**: the system becomes self-referential. At L13, the framework diagnoses itself and finds the same structural impossibility it finds in its objects. L14 would be "apply L13 to L13's output" which produces the same result (fixed point), making it infinite regress with no new information.

The specific count of 13 appears to be determined by:
- **Trunk (L1-L7):** 7 levels of increasing operational complexity (matching the common "7 +/- 2" cognitive chunk limit, and roughly Bloom's 6 + concealment mechanism)
- **Diamond (L8-L11):** 4 levels of constructive divergence (branching into complementary variants, 3 at L9, 2 at L10, 3 at L11)
- **Convergence (L12-L13):** 2 levels of reflexive convergence (meta-conservation + fixed point)

The 7+4+2 = 13 structure likely reflects the interaction between:
- The number of distinct cognitive operations that can be compressed into prompt text (trunk)
- The number of independent ways construction can diverge before exhausting the space (diamond)
- The minimal reflexive stack needed to reach a fixed point (convergence: one meta-level + one self-application)

**No existing theory predicts 13 as a universal constant.** Simon's log formula gives 13 only with specific (arguably arbitrary) parameter choices. The number appears to be an empirical property of the prompt-model interaction space, not a mathematical necessity. However, the STRUCTURE (linear trunk + branching + reflexive collapse) is predicted by multiple theories.

### The strongest analogy: Polynomial Hierarchy collapse

If PH collapses at level k, it means Sigma_k = Sigma_{k+1} = ... — adding alternations beyond k is useless. Our L13 is exactly this: the cognitive compression hierarchy "collapses" at level 13 because L13 = L14 = L15 = ... (the fixed point reproduces itself). The open question in complexity theory (does PH collapse?) is empirically answered in our system: yes, at level 13.

---

## References

- [Model of Hierarchical Complexity — Wikipedia](https://en.wikipedia.org/wiki/Model_of_hierarchical_complexity)
- [Commons et al. 2012 — MHC Introduction](http://www.adultdevelopment.org/CommonsEtAl2012.pdf)
- [Bloom's Taxonomy — Wikipedia](https://en.wikipedia.org/wiki/Bloom's_taxonomy)
- [Kohlberg's Stages — Wikipedia](https://en.wikipedia.org/wiki/Lawrence_Kohlberg's_stages_of_moral_development)
- [Dreyfus Model — Wikipedia](https://en.wikipedia.org/wiki/Dreyfus_model_of_skill_acquisition)
- [SOLO Taxonomy — Wikipedia](https://en.wikipedia.org/wiki/Structure_of_observed_learning_outcome)
- [Chomsky Hierarchy — Wikipedia](https://en.wikipedia.org/wiki/Chomsky_hierarchy)
- [Arithmetical Hierarchy — Wikipedia](https://en.wikipedia.org/wiki/Arithmetical_hierarchy)
- [Polynomial Hierarchy — Wikipedia](https://en.wikipedia.org/wiki/Polynomial_hierarchy)
- [Circuit Complexity — Wikipedia](https://en.wikipedia.org/wiki/Circuit_complexity)
- [Simon 1962 — Architecture of Complexity](https://faculty.sites.iastate.edu/tesfatsi/archive/tesfatsi/ArchitectureOfComplexity.HSimon1962.pdf)
- [Hierarchy Theory — Wikipedia](https://en.wikipedia.org/wiki/Hierarchy_theory)

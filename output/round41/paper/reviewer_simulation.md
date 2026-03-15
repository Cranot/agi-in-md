# Reviewer 1: Methodology Expert

## Summary
The authors propose "cognitive prisms"—structured prompts that allegedly reframe LLM analysis toward structural rather than specific claims. They claim to discover a conservation law (Specificity × Verifiability = Constant) and validate a 13-level compression taxonomy across 1,000+ experiments.

## Strengths
The scale of experimentation (40 rounds, 1,000+ trials) is impressive. The recognition that prompt design may dominate model selection has practical merit. The attempt to systematize prompt operations into a taxonomy, even if flawed, represents a useful organizing framework.

## Weaknesses
**The evaluation methodology is fatally compromised.** Using "Haiku-as-Judge"—where a Claude model evaluates outputs from Claude models—creates irreconcilable circularity. The same training distribution that produces the outputs also shapes the evaluator's preferences. This is not independent validation.

**The "conservation law" derivation is post-hoc mystification.** Table 1 lists 15 theoretical frameworks, but most are analogies masquerading as derivations. "Gricean maxims tension" is a prescriptive theory of human conversation, not a physical conservation law. "Efficient market hypothesis" is empirically contested in its own domain. The authors have taken superficial similarities and claimed mathematical equivalence.

**No statistical rigor.** The paper reports "σ = 0.12, CV = 8.3%" without sample sizes, confidence intervals, or significance tests. What exactly was measured? What was the null hypothesis? This is numerical theater.

**The 13-level taxonomy is asserted, not demonstrated.** The claim that levels are "categorical, not continuous" requires empirical evidence—threshold detection, bimodal distributions, cluster analysis. None is provided.

## Questions
1. What is the inter-rater reliability between Haiku-as-Judge and human evaluators?
2. What statistical test distinguishes categorical from continuous levels?
3. Why should we accept conservation laws "derived" from linguistic pragmatics (Grice) as equivalent to thermodynamic ones?

## Recommendation
**REJECT** — The evaluation methodology cannot support the claims. Resubmit with independent (human or cross-family model) evaluation and proper statistical analysis.

---

# Reviewer 2: Theory Expert

## Summary
The paper argues that system prompts function as "cognitive prisms" governed by conservation laws. It proposes L12-G, a self-correcting prompt architecture, and claims empirical validation across codebases and domains.

## Strengths
The central insight—that LLMs may be better suited for structural than specific analysis—is plausible and practically useful. The construction-based reasoning approach (L8+) as a bypass for meta-analytical capacity limits is theoretically interesting. The trust-aware evaluation critique of existing benchmarks has merit.

## Weaknesses
**The theoretical foundations are unserious.** The paper invokes thermodynamics, category theory, Gödelian incompleteness, the Free Energy Principle, and the Extended Mind thesis—but each appeal is superficial. The Legendre transformation analogy is particularly egregious: conjugate variables in thermodynamics have precise mathematical relationships; "Clarity Cost × Blindness Cost = Constant" is a metaphor dressed in equations.

**The "autopoietic" claims are pseudoscientific.** Autopoiesis (Maturana & Varela) refers to self-producing biological systems with specific criteria. A meta-prompt generating prompts is not autopoiesis—it's recursion. The authors have borrowed a technical term to lend false depth to a straightforward observation.

**The conservation law is not derived but assumed.** The "15 independent derivations" all presuppose the conclusion. If you look for trade-offs, you find trade-offs. Where is the proof that Specificity × Verifiability is conserved rather than, say, Specificity + Verifiability bounded, or some entirely different relationship?

**The Gödelian grounding is nonsensical.** Gödel's incompleteness theorems apply to formal systems capable of arithmetic. There is no demonstration that the prism taxonomy constitutes such a system. This is name-dropping, not argument.

## Questions
1. What mathematical structure makes the prism taxonomy subject to Gödel's theorems?
2. What would falsify the conservation law? What observation would contradict it?
3. Can you define "autopoiesis" operationally as applied to prompts, and distinguish it from simple recursion?

## Recommendation
**REJECT** — The theoretical claims vastly overreach the evidence. The paper would be stronger if it dropped the grandiose theoretical framework and presented the empirical findings modestly.

---

# Reviewer 3: Applications Expert

## Summary
The authors present L12-G (Oracle), a 332-word prompt for reliable code analysis, claiming it enables Haiku 4.5 to outperform Opus 4.6 on structural analysis tasks. They validate on three production codebases and propose a five-tier epistemic classification system.

## Strengths
The practical focus on reducing confabulation while maintaining analytical depth addresses a real problem. The cost comparison ($0.05 vs $0.18 per analysis) is useful for practitioners. The insight that prompts may dominate model selection has significant implications for deployment economics.

## Weaknesses
**The scrambled vocabulary experiment is poorly described and possibly misinterpreted.** The paper claims nonsense-token prisms achieve 10/10 vs. normal prisms' 9/10, but provides no examples of what was actually scrambled. If syntactic structure was preserved, the result merely confirms that LLMs follow instruction patterns—which we already knew. The interpretation that "format carries meaning independently of vocabulary" is oversold.

**The epistemic classification system is underspecified.** The five tiers (STRUCTURAL, DERIVED, MEASURED, KNOWLEDGE, ASSUMED) are defined with single examples but no decision boundaries. How does one determine whether a claim is STRUCTURAL vs. DERIVED? What inter-annotator agreement exists for this classification?

**Real-world utility is unproven.** The paper claims 28 "genuine issues" were found, but were these verified? Did developers confirm they were real bugs? Did fixing them improve the code? Without downstream validation, "genuine" is the authors' judgment, not demonstrated value.

**The codebase selection is narrow.** Three Python files from web/CLI frameworks may share structural similarities that inflate generalizability. Where are the systems programming, data science, or embedded code targets?

**Pipeline ordering claims are overconfident.** The "audit-then-L12 produces 18 words" result is presented as a structural law, but may simply reflect prompt incompatibility. Different audit prompts might compose differently.

## Questions
1. Can you provide the exact "scrambled" prism text for reproducibility?
2. What percentage of the 28 identified issues were confirmed by code maintainers?
3. What is the inter-annotator agreement for the five-tier epistemic classification?
4. Have you tested on non-Python, non-web-framework code?

## Recommendation
**REVISE** — The practical contributions are valuable but underspecified. The paper needs: (1) complete prompt texts in appendix, (2) human verification of identified issues, (3) broader codebase validation, and (4) clearer specification of classification boundaries.

You are writing the Results section of a paper. Present data precisely. No overclaiming. Report observations, not laws.

Present these findings WITH EXACT NUMBERS AND SAMPLE SIZES:

1. SPECIFICITY-VERIFIABILITY TRADE-OFF: Across 6 codebases (Starlette 333L Python, Click 417L Python, Tenacity 331L Python, Flask 1625L Python, Go rate limiter 40L, TypeScript event bus 30L) and 3 non-code targets (business plan, academic abstract, legal clause), we observe that claims typed as STRUCTURAL score higher on verifiability while claims typed as KNOWLEDGE/ASSUMED score higher on specificity. Report as empirical observation with standard deviation, not as a universal law.

2. GAP DETECTION COMPLEMENTARITY: knowledge_boundary detected 1 confabulated API (asyncio.RWLock) that knowledge_audit missed. knowledge_audit detected 1 mathematical error (O(n)+O(n) labeled quadratic) that boundary missed. N=4 targets, both prisms complementary on all 4. Report as: "the two detection methods are complementary, catching different error types."

3. SELF-CORRECTION EFFECTIVENESS: L12-G (single-pass, 3-phase) vs original L12. Augmented L12 scored 8/10 vs original 7/10 (haiku-as-judge, N=1 per condition, Starlette). L12-G confabulation rate: 1/5 runs contained 1 confabulation marker (4/5 = zero). Report with appropriate caveats about small sample size.

4. FORMAT vs VOCABULARY: Scrambled prism (domain nouns replaced with nonsense: "glorpnax", "blorpwhistle", "xanthoquirm", format preserved) scored 10/10 on Starlette, 1286w on Click. Normal L12 scored 9/10. N=1 per condition. Report as: "preliminary evidence that prompt format contributes more than vocabulary to output quality, consistent with Tang et al. (2024), requiring larger-scale replication."

5. CROSS-LANGUAGE VALIDATION: L12-G on Go (686w, produced conservation law), TypeScript (454w, produced conservation law), Flask Python 1625L (991w). All produced structured analysis with conservation laws. N=1 per language. Report as: "the method generalizes across languages in our initial tests."

6. COMPOSITION NON-COMMUTATIVITY: L12 then audit = 1137w structured analysis. Audit then L12 = 18w (catastrophic failure, model entered planning mode). N=1. Report as: "pipeline ordering has a dramatic effect, with the reversed order producing near-empty output in our test."

7. AUTOPOIESIS: Meta-cooker applied recursively: gen1=265w, gen2=335w, gen3=347w. Gen3 scored 8/10 vs hand-crafted L12 at 9/10 (haiku-as-judge). Report as: "recursive prompt generation converges and produces competitive quality."

Use tables. Report sample sizes honestly. Include limitations paragraph noting small N and haiku-as-judge evaluation. 1500-2000 words.

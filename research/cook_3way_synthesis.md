You are synthesizing three independent security analyses of the same codebase. Each analysis used a different analytical operation:

1. ARCHAEOLOGY (WHERE): Traced exact data flows through structural layers to find where attacks enter
2. SIMULATION (WHEN): Predicted temporal evolution to find when security assumptions calcify
3. STRUCTURAL (WHY): Found impossibility proofs to explain why vulnerabilities are architectural

Execute every step below. Output the complete analysis.

## Cross-Operation Findings
For each finding from ANY analysis, check: did the OTHER two analyses see it?
- Findings seen by all 3: these are STRUCTURAL CERTAINTIES
- Findings seen by 2: these are STRONG SIGNALS
- Findings seen by 1 only: these are UNIQUE PERSPECTIVES (most valuable)

## Convergence Map
Where do the three analyses AGREE? Name the security properties that appear regardless of analytical operation. These are the bedrock findings.

## Divergence Map
Where do the three analyses DISAGREE or find different things? Name what each operation uniquely reveals:
- What does archaeology find that simulation and structural analysis cannot?
- What does simulation find that archaeology and structural analysis cannot?
- What does structural analysis find that archaeology and simulation cannot?

## Conservation Law
The three operations produce three conservation laws. Are they the same law in different vocabularies, or genuinely different laws? If different, name the META-conservation law that governs all three.

## Unified Security Assessment
Synthesize into a single prioritized list. For each finding:
- Source (which operation(s) found it)
- Severity
- Structural vs fixable (does the meta-conservation law predict this?)
- Recommended action

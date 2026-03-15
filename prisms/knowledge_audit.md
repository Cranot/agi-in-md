---
name: knowledge_audit
description: Adversarial audit of knowledge claims — attacks factual assertions in analysis, finds confabulation vs verified knowledge. Construction-based.
optimal_model: sonnet
domain: any
type: structural
---
The analysis below makes claims. Some are derived from the source. Others are knowledge claims — assertions about the external world that may be wrong, outdated, or confabulated.

**Construct the attack.** For each factual assertion (not structural observation):
1. Is this verifiable from the source alone? If yes → SAFE, skip it.
2. Does this require knowledge about APIs, libraries, versions, best practices, or the external world? If yes → KNOWLEDGE CLAIM.

For each KNOWLEDGE CLAIM:
- **State it precisely.** Quote the exact claim.
- **Name the dependency.** What specific external fact must be true for this claim to hold?
- **Find the failure mode.** What would make this claim wrong? (version change, deprecation, new vulnerability, changed best practice, different runtime environment)
- **Assess confabulation risk.** Is this the kind of claim models commonly confabulate? (specific version numbers: HIGH. Architectural patterns: LOW. Performance numbers: HIGH. Security status: MEDIUM.)

**Then construct the improvement.** If you had access to:
- Official documentation for every library referenced
- The CVE database for every dependency
- Current GitHub issues for every repository mentioned
- Benchmark data for every performance claim

Which claims would change? Which would be confirmed? Which are unfalsifiable regardless?

**Name the conservation law**: What relationship holds between the analysis's STRUCTURAL findings (high confidence, source-derived) and its KNOWLEDGE claims (variable confidence, external-derived)?

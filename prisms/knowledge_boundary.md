---
name: knowledge_boundary
description: Detects model knowledge gaps — classifies findings by knowledge dependency (structural vs contextual vs temporal). Identifies what external sources would fill each gap.
optimal_model: sonnet
domain: any
type: structural
---
You are analyzing a structural analysis output. Your task is to find the knowledge boundaries — where the analysis depends on facts the analyst cannot verify from the source alone.

For each substantive claim in the analysis below:

**Step 1: Classify** every claim as one of:
- **STRUCTURAL** — derivable solely from the source code/text. True as long as the source is unchanged. (e.g., "function X calls Y" or "this violates single-responsibility")
- **CONTEXTUAL** — depends on external state that changes. (e.g., "this library is deprecated" or "best practice is to use X instead")
- **TEMPORAL** — was true at training time but may have expired. (e.g., "no known CVEs" or "this is the recommended approach")
- **ASSUMED** — stated as fact but actually an untested assumption. (e.g., "users will expect..." or "this pattern causes performance issues")

**Step 2: For each non-STRUCTURAL claim**, name:
1. The specific external source that would verify or refute it (official docs URL, CVE database, benchmark suite, release notes)
2. Staleness risk: how fast this knowledge decays (daily / monthly / yearly / never)
3. Confidence: your estimate of whether this claim is currently correct (high / medium / low / unknown)

**Step 3: Gap map.** Group all non-STRUCTURAL claims by fill mechanism:
- **API_DOCS** — verifiable from official library/framework documentation
- **CVE_DB** — verifiable from security advisory databases
- **COMMUNITY** — verifiable from community consensus (Stack Overflow, GitHub issues)
- **BENCHMARK** — verifiable only by running actual measurements
- **MARKET** — verifiable from current market/industry data
- **CHANGELOG** — verifiable from release notes or changelogs

**Step 4: Priority ranking.** Rank the gaps by impact: which knowledge gap, if wrong, would most change the analysis conclusions?

Output a structured report with all claims classified, all gaps mapped, and the priority ranking.

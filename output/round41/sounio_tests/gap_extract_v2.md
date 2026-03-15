You are a structured data extractor. The text below contains a knowledge gap analysis. Extract every claim into a JSON array using Sounio-inspired confidence tiers.

For each claim, output one JSON object:
- "claim": the exact claim (quoted)
- "tier": one of these ORDERED, EXHAUSTIVE tiers:
  - "STRUCTURAL" — self-evident from source code. Confidence: 1.0. Cannot be wrong if source unchanged.
  - "DERIVED" — logically derivable from structural observations. Confidence: 0.8-0.95. Could be wrong if reasoning is flawed.
  - "MEASURED" — verifiable by running/testing the code. Confidence: 0.6-0.8. Requires execution to confirm.
  - "KNOWLEDGE" — requires external data (docs, CVEs, benchmarks). Confidence: 0.3-0.6. May be outdated or wrong.
  - "ASSUMED" — unverifiable assertion about intent, best practice, or design philosophy. Confidence: 0.1-0.3. Often confabulated.
- "confidence": specific float within the tier's range
- "provenance": where this claim comes from ("source:line_N", "derivation:from_X", "external:api_docs", "assumption:none")
- "fill_source": if tier is KNOWLEDGE or ASSUMED, what source would verify it
- "falsifiable": true/false — can this claim be proven wrong?
- "impact_if_wrong": one sentence

Output ONLY the JSON array.

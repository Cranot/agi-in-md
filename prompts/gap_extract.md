You are a structured data extractor. The text below contains a knowledge gap analysis of a code or text analysis. Extract every knowledge gap into a JSON array.

For each gap found in the analysis, output one JSON object with these fields:
- "claim": the exact factual claim that needs verification (quote it)
- "type": one of CONTEXTUAL, TEMPORAL, ASSUMED, CONFABULATED
- "fill_source": one of API_DOCS, CVE_DB, COMMUNITY, BENCHMARK, MARKET, CHANGELOG, HUMAN
- "query": the specific question to ask the fill source (e.g., "Does asyncio.RWLock exist in Python 3.12 stdlib?")
- "risk": HIGH, MEDIUM, or LOW (confabulation risk)
- "impact": what changes in the analysis if this claim is wrong (one sentence)
- "confidence": your estimate that the claim is currently correct (0.0 to 1.0)

Output ONLY the JSON array, no other text. Example:
```json
[
  {
    "claim": "asyncio.RWLock provides read-write locking",
    "type": "CONFABULATED",
    "fill_source": "API_DOCS",
    "query": "Does asyncio.RWLock exist in Python stdlib?",
    "risk": "HIGH",
    "impact": "Proposed improvement is invalid if class doesn't exist",
    "confidence": 0.2
  }
]
```

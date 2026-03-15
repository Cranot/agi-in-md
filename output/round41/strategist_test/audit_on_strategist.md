# Knowledge Audit: Strategist Prism

## Attack on Factual Assertions

### SCAN MODE DESCRIPTIONS

---

**Claim 1:** "`single` — L12 structural analysis. 1 call, $0.05."

| Attribute | Assessment |
|-----------|------------|
| Verifiable from source | YES — CLAUDE.md confirms `/scan file` = L12, single call |
| Dependency | Pricing model: Haiku/Sonnet per-token rates |
| Failure mode | Price varies by file size; $0.05 is an estimate for typical files |
| Confabulation risk | MEDIUM — specific dollar amounts are model-dependent |

**Verdict:** ACCURATE BUT APPROXIMATE. The $0.05 is an average, not a guarantee.

---

**Claim 2:** "`oracle` — 5-phase self-aware analysis. 1 call, $0.05."

| Attribute | Assessment |
|-----------|------------|
| Verifiable from source | NO — "oracle" mode not found in CLAUDE.md |
| Dependency | prism.py implementation; undocumented feature |
| Failure mode | Mode may not exist, may be alias for something else, or may be planned but not implemented |
| Confabulation risk | HIGH — specific feature names without source verification |

**Verdict:** UNVERIFIED. "oracle" appears nowhere in the provided documentation. This is either:
1. A real feature not documented in CLAUDE.md
2. A confabulated mode name

---

**Claim 3:** "`l12g` — Gap-aware self-correcting. 1 call, $0.05."

| Attribute | Assessment |
|-----------|------------|
| Verifiable from source | NO — "l12g" not found in CLAUDE.md |
| Dependency | prism.py implementation |
| Failure mode | Same as oracle — may not exist |
| Confabulation risk | HIGH |

**Verdict:** UNVERIFIED. No source evidence.

---

**Claim 4:** "`scout` — Depth + targeted verify. 2 calls, $0.06."

| Attribute | Assessment |
|-----------|------------|
| Verifiable from source | NO — "scout" mode not documented |
| Dependency | prism.py implementation |
| Failure mode | Feature may not exist |
| Confabulation risk | HIGH |

**Verdict:** UNVERIFIED.

---

**Claim 5:** "`gaps` — L12 + boundary + audit. 3 calls, $0.15."

| Attribute | Assessment |
|-----------|------------|
| Verifiable from source | PARTIAL — CLAUDE.md mentions "adversarial" and "synthesis" as pipeline components, but not "gaps" mode specifically |
| Dependency | Pipeline composition in prism.py |
| Failure mode | Different composition than described |
| Confabulation risk | MEDIUM |

**Verdict:** PLAUSIBLE BUT UNVERIFIED.

---

**Claim 6:** "`full` — 9-step champion pipeline. 9 calls, $0.45."

| Attribute | Assessment |
|-----------|------------|
| Verifiable from source | YES — CLAUDE.md explicitly states "9-pass: 7 structural + adversarial + synthesis" |
| Dependency | None — directly sourced |
| Failure mode | N/A |
| Confabulation risk | LOW |

**Verdict:** ACCURATE.

---

**Claim 7:** "`3way` — WHERE/WHEN/WHY + synthesis. 4 calls, $0.20."

| Attribute | Assessment |
|-----------|------------|
| Verifiable from source | YES — CLAUDE.md confirms "4-pass: WHERE/WHEN/WHY + synthesis" and "auto for non-code `full`" |
| Dependency | None — directly sourced |
| Failure mode | N/A |
| Confabulation risk | LOW |

**Verdict:** ACCURATE.

---

**Claim 8:** "`behavioral` — 5-pass behavioral. 5 calls, $0.25."

| Attribute | Assessment |
|-----------|------------|
| Verifiable from source | YES — CLAUDE.md lists "behavioral" as "5-pass: errors + costs + changes + promises + synthesis" |
| Dependency | None — directly sourced |
| Failure mode | N/A |
| Confabulation risk | LOW |

**Verdict:** ACCURATE.

---

**Claim 9:** "`meta` — L12 + claim on itself. 2 calls, $0.10."

| Attribute | Assessment |
|-----------|------------|
| Verifiable from source | YES — CLAUDE.md confirms "Meta-analysis: L12 → claim on L12 output" |
| Dependency | None — directly sourced |
| Confabulation risk | LOW |

**Verdict:** ACCURATE.

---

**Claim 10:** "`evolve` — 3-gen autopoietic. 3 calls, $0.15."

| Attribute | Assessment |
|-----------|------------|
| Verifiable from source | NO — "evolve" appears in capabilities map as mode but "3-gen autopoietic" is not defined anywhere |
| Dependency | Implementation details not documented |
| Failure mode | Different implementation than described |
| Confabulation risk | MEDIUM-HIGH |

**Verdict:** PLAUSIBLE BUT UNVERIFIED. The term "autopoietic" is not in source.

---

### POST-PROCESSING FLAGS

---

**Claim 11:** "`--confidence` — Tag claims HIGH/MED/LOW/UNVERIFIED. +$0.002."

| Attribute | Assessment |
|-----------|------------|
| Verifiable from source | NO — `--confidence` flag not mentioned in CLAUDE.md |
| Dependency | prism.py CLI implementation |
| Failure mode | Flag may not exist or may work differently |
| Confabulation risk | HIGH — specific flags and pricing |

**Verdict:** UNVERIFIED.

---

**Claim 12:** "`--provenance` — Source attribution per finding. +$0.002."

| Attribute | Assessment |
|-----------|------------|
| Verifiable from source | NO — not in CLAUDE.md |
| Dependency | prism.py CLI implementation |
| Confabulation risk | HIGH |

**Verdict:** UNVERIFIED.

---

**Claim 13:** "`--trust` — Alias for oracle mode."

| Attribute | Assessment |
|-----------|------------|
| Verifiable from source | NO — neither `--trust` nor "oracle mode" documented |
| Dependency | prism.py CLI |
| Confabulation risk | HIGH |

**Verdict:** UNVERIFIED. Circular — `--trust` aliases `oracle`, but `oracle` itself is unverified.

---

### PRISM OVERRIDES

---

**Claim 14:** "`knowledge_typed` — Every claim carries Type/Confidence/Provenance."

| Attribute | Assessment |
|-----------|------------|
| Verifiable from source | NO — `knowledge_typed` prism not in prisms/ list or CLAUDE.md |
| Dependency | Existence of this prism file |
| Failure mode | Prism doesn't exist |
| Confabulation risk | HIGH |

**Verdict:** UNVERIFIED. The prisms/ directory lists 33 production prisms — this is not among those explicitly named.

---

**Claim 15:** "`knowledge_boundary` — Classifies claims by knowledge dependency."

| Attribute | Assessment |
|-----------|------------|
| Verifiable from source | NO — not in documented prism list |
| Confabulation risk | HIGH |

**Verdict:** UNVERIFIED.

---

**Claim 16:** "`knowledge_audit` — Adversarial confabulation detection."

| Attribute | Assessment |
|-----------|------------|
| Verifiable from source | YES — I am executing this prism right now; it exists as the prompt I received |
| Confabulation risk | LOW |

**Verdict:** ACCURATE. This prism exists (it's the one I'm executing).

---

**Claim 17:** Portfolio prisms: "`pedagogy`, `claim`, `scarcity`, `rejected_paths`, `degradation`, `contract`"

| Attribute | Assessment |
|-----------|------------|
| Verifiable from source | YES — CLAUDE.md explicitly lists all 5 with scores (9-9.5/10) |
| Confabulation risk | LOW |

**Verdict:** ACCURATE.

---

**Claim 18:** SDL prisms: "`deep_scan`, `sdl_trust`, `sdl_coupling`, `fix_cascade`, `identity`"

| Attribute | Assessment |
|-----------|------------|
| Verifiable from source | YES — CLAUDE.md lists all 5 as SDL-1 through SDL-5 |
| Confabulation risk | LOW |

**Verdict:** ACCURATE.

---

**Claim 19:** Domain prisms: "`optimize`, `error_resilience`, `evolution`, `api_surface`, `simulation`"

| Attribute | Assessment |
|-----------|------------|
| Verifiable from source | PARTIAL — `simulation` is documented (9.0 score). Others not explicitly named in CLAUDE.md |
| Dependency | Full prisms/ directory listing |
| Confabulation risk | MEDIUM |

**Verdict:** PARTIAL. `simulation` verified; others unverified.

---

### KEY CONSTRAINTS

---

**Claim 20:** "S×V=C: more specific claims = less verifiable."

| Attribute | Assessment |
|-----------|------------|
| Verifiable from source | NO — this formula appears nowhere in CLAUDE.md |
| Dependency | Theoretical framework claim |
| Failure mode | May be oversimplified or wrong model of verification |
| Confabulation risk | MEDIUM — sounds plausible but no source |

**Verdict:** UNVERIFIED THEORETICAL CLAIM. Plausible heuristic but not sourced.

---

**Claim 21:** "Composition is non-commutative: L12 must come before audit (not reverse)."

| Attribute | Assessment |
|-----------|------------|
| Verifiable from source | PARTIAL — CLAUDE.md confirms pipeline ordering (L12 → adversarial → synthesis) |
| Dependency | None |
| Failure mode | The "must" is strong — reverse might work but be less effective |
| Confabulation risk | LOW |

**Verdict:** ACCURATE IN SUBSTANCE. The ordering is documented.

---

**Claim 22:** "Format > vocabulary: the structure of the analysis matters more than domain words."

| Attribute | Assessment |
|-----------|------------|
| Verifiable from source | YES — Principle 4: "The prompt is a program; the model is an interpreter. Operation order becomes section order." Also Principle 113: "Depth × Universality = constant" implies structure dominates |
| Confabulation risk | LOW |

**Verdict:** ACCURATE.

---

**Claim 23:** "Conservation law = convergence signal: when found, deeper passes add breadth not depth."

| Attribute | Assessment |
|-----------|------------|
| Verifiable from source | YES — CLAUDE.md: "Conservation law = convergence signal. Without it, model analyzes indefinitely." |
| Confabulation risk | LOW |

**Verdict:** ACCURATE.

---

**Claim 24:** "Budget awareness: estimate cost at each step."

| Attribute | Assessment |
|-----------|------------|
| Verifiable from source | YES — pricing awareness is throughout CLAUDE.md |
| Confabulation risk | LOW |

**Verdict:** ACCURATE.

---

## Summary Table

| Category | Verified | Unverified | Accuracy Rate |
|----------|----------|------------|---------------|
| Scan Modes | 5/10 | 5/10 | 50% |
| Post-Processing Flags | 0/3 | 3/3 | 0% |
| Prism Overrides | 11/16 | 5/16 | 69% |
| Key Constraints | 4/5 | 1/5 | 80% |
| **TOTAL** | **20/34** | **14/34** | **59%** |

---

## Conservation Law of This Audit

**Specificity × Verifiability = Constant**

The strategist prompt makes increasingly specific claims (exact call counts, dollar amounts, mode names) that become increasingly unverifiable from source documentation. The more detailed the tool description, the less likely it is to match actual implementation.

---

## What Would Change With Documentation Access

| If I had... | Claims that would change |
|-------------|-------------------------|
| prism.py source code | All UNVERIFIED scan modes (oracle, l12g, scout, gaps, verified) would resolve to TRUE/FALSE |
| Full prisms/ directory listing | knowledge_typed, knowledge_boundary, optimize, error_resilience, evolution, api_surface would resolve |
| CLI --help output | --confidence, --provenance, --trust flags would resolve |
| Actual pricing data | All dollar amounts would be confirmed or corrected |

---

## Critical Findings

**HIGH CONFIDENCE (source-verified):**
- `full`, `3way`, `behavioral`, `meta` modes exist as described
- Portfolio and SDL prisms exist
- Pipeline ordering and convergence principles are accurate

**HIGH RISK (no source evidence):**
- `oracle`, `l12g`, `scout` modes — may not exist
- `--confidence`, `--provenance`, `--trust` flags — may not exist
- `knowledge_typed`, `knowledge_boundary` prisms — may not exist
- Specific dollar amounts — estimates, not guarantees
- "S×V=C" formula — theoretical claim without empirical backing in source

**WHAT THE STRATEGIST CONCEALS:**
The strategist presents itself as complete (11 scan modes, 3 flags, 16 prisms) but only ~59% of these claims are verifiable from documentation. The appearance of comprehensiveness may mask missing implementations.

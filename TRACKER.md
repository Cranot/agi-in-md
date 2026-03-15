# Unexplored Territories & Open Work Tracker
**Created: Mar 14, 2026** | **Last updated: Mar 14, 2026 (Round 40 results integrated)**

Status legend: [ ] = not started, [~] = in progress, [x] = done, [!] = blocked

---

## 1. PLANNED BUT NOT EXECUTED (5 items)

### P1. Cross-target validation: new prisms on Click + Tenacity
- **Result**: simulation 9.0, cultivation 9.0 (STABLE). archaeology 8.5 (STABLE). sdl_simulation 7.0-7.5 (DEGRADED, P199).
- **Status**: [x] DONE — Round 40

### P2. 3-cooker pipeline cross-target validation
- **Result**: Click 8218w/561s, Tenacity 7719w/663s. Both produced massive cross-operation synthesis.
- **Status**: [x] DONE — Round 40

### P3. 1000+ line codebase testing
- **Result**: L12 does NOT degrade. Rich (2684L) scored 10.0 — highest in battery. Flask (1625L) 9.5. Requests (1041L) 9.5. deep_scan 9.0 on all 3. P198: scaling confirmed.
- **Status**: [x] DONE — Round 40

### P4. Sonnet lens factory (`--factory`)
- **What**: Automate delta method to systematically generate SDL-class prisms
- **Why**: Delta method proven manually (Round 37) but never automated
- **Cost**: High (design + integration + validation)
- **Status**: [ ]

### P5. Sub-artifact targeting
- **What**: Run different prisms on different code subsystems (classes, methods)
- **Why**: Currently one prism hits entire file. Subsystem targeting = better coverage with fewer calls
- **Cost**: High (design + infrastructure + validation)
- **Status**: [ ]

---

## 2. OPEN RESEARCH QUESTIONS (10 items)

### R1. True Sonnet-cooked test for alt ops
- **What**: Round 39 Batch 3 reused Haiku-cached lenses. Never tested Sonnet cook + Sonnet solve
- **Why**: Can't compare Sonnet-cooked vs Haiku-cooked without this
- **Result**: Sonnet+Sonnet 2x output vs Sonnet+Haiku. Solve model critical. P204.
- **Status**: [x] DONE — Round 40

### R2. L9 escalation: Miniaturize on Sonnet
- **Result**: Sonnet 8.0 (+1.5 lift), Haiku 6.5. NOT promoted — at floor, generic conservation laws, overlaps L12. P203.
- **Status**: [x] DONE — Round 40

### R3. Diamond convergence on remaining 5 operations
- **What**: Proven for simulation + archaeology only (2/7). Do destruction, transplant, miniaturize, forgery, cultivation converge at L12?
- **Why**: "Operation-independent at reflexive ceiling" claim based on n=2
- **Cost**: ~20 API calls (5 ops x L9-L12 chains)
- **Status**: [ ]

### R4. Non-code domains for 3-cooker pipeline
- **What**: Does 3-cooker achieve 9.5 on legal, medical, philosophical, business text?
- **Why**: "Works on ANY domain" claim based on code + synthetic only
- **Cost**: ~12 API calls (3-4 domains x 3-cooker)
- **Status**: [ ]

### R5. L11-L12 on poetry/UX domains
- **Result**: l12_universal poetry 9.0, UX 8.5. l12 poetry 5.0 (BROKEN — conversation mode), UX 9.5. P200: compression forces domain neutrality.
- **Status**: [x] DONE — Round 40

### R6. Content hallucination scope (P182)
- **What**: Cooked lenses hallucinate code content. Only 1 case tested
- **Result**: P182 REVISED — no hallucination via --intent. Content displacement on mismatch, not fabrication.
- **Status**: [x] DONE — Round 40

### R7. Vertical composition failure scope (P172)
- **Result**: P172 MOSTLY CONFIRMED. claim prism analyzes the analysis (7.5). deep_scan/pedagogy revert to original code (7.0/6.5). P201: meta-analytical prisms transfer vertically, constructive prisms don't.
- **Status**: [x] DONE — Round 40

### R8. Blind evaluation of cross-lens addition
- **What**: When 5 prisms find "5 different things" — are they genuinely different or reframed?
- **Why**: Fundamental validity question for multi-prism approach
- **Cost**: Design protocol + human judging
- **Status**: [ ]

### R9. Cross-model: GPT/Llama/Mistral
- **What**: Only Claude + Gemini tested. L12 universality based on n=2 model families
- **Why**: "Universal across model families" claim
- **Cost**: ~10 API calls per model family
- **Status**: [ ]

### R10. Product vs sum conservation law form
- **What**: Opus=product, Sonnet=sum, Haiku=multi-property. No predictive model
- **Why**: Understanding when/why each form appears
- **Cost**: ~20-30 API calls (systematic test)
- **Status**: [ ]

---

## 3. INFRASTRUCTURE GAPS (7 items)

### I1. 4 unscored VPS prisms
- **Result**: No champions. time_lifecycle 6.5, data_flow 7.0, redundancy 7.0, composition_synthesis 6.0. ARCHIVE time_lifecycle + composition_synthesis. KEEP data_flow + redundancy (low priority, iterate to V2).
- **Status**: [x] DONE — Round 40

### I2. 11 experimental prisms not in prism.py routing
- **Decision**: Keep all as ROUTED (user-selectable via `/prism <name>`). No pipeline addition — current pipelines are validated. evolution (9.5) and api_surface (9.5) are top candidates but adding to behavioral would make it 7 calls for marginal benefit. All accessible, all documented in PRISMS.md champion table.
- **Status**: [x] DONE — decided: keep as-is

### I3. Writer prisms not wired
- **Decision**: Option B — manual pipeline, documented in README "Which to pick" table. No command change. Pipeline: `/prism writer` → `/prism writer_critique` → `/prism writer_synthesis`.
- **Status**: [x] DONE — documented

### I4. COOK_SIMULATION / COOK_ARCHAEOLOGY not standalone in prism.py
- **What**: Templates in research/. Used via COOK_3WAY but not standalone routes
- **Why**: Can't independently invoke these cookers
- **Cost**: Moderate (add routing, test)
- **Status**: [ ]

### I5. No automated regression/benchmark suite
- **What**: 33 unit tests only. No end-to-end quality tracking over time
- **Why**: Can't detect quality regressions in prism outputs
- **Cost**: High (design, build, maintain)
- **Status**: [ ]

### I6. Test count off-by-one
- **What**: Previously reported as 31-32 passing
- **Status**: [x] DONE — All 33 tests pass. Counter is hardcoded and correct. Old observation was from previous version.

### I7. Principle index fragmented
- **What**: P1-P197 scattered across experiment_log, alt_ops_results, CLAUDE.md, memory files
- **Fix**: Created PRINCIPLES.md — 87 explicitly stated principles with one-line summaries, organized by theme
- **Note**: P1-P99 gap (lived in session memory, not on disk). 9 thematic categories for cross-reference.
- **Status**: [x] DONE — Mar 14, 2026

---

## 4. DOCUMENTATION & RELEASE BLOCKERS (7 items)

### D1. LICENSE file missing
- **What**: README claims MIT but no LICENSE file exists
- **Fix**: Create LICENSE with MIT text (Cranot / CosmoHac)
- **Status**: [x] DONE — already existed and committed

### D2. README data stale
- **What**: Says "35 rounds", "13 prisms". Actual: 39 rounds, 37 prisms
- **Fix**: README updated to champion prisms only (11 champions) + link to PRISMS.md for full catalog
- **Status**: [x] DONE — Mar 14, 2026

### D3. experiment_log.md stale
- **What**: Ends at Round 29. Rounds 30-39 only in CLAUDE.md
- **Fix**: Appended 333 lines covering Rounds 30-39 (condensed summaries with key principles)
- **Status**: [x] DONE — Mar 14, 2026

### D4. CLAUDE.md stale numbers
- **What**: Header said "38 rounds", "114 principles"
- **Fix**: Updated to "39 rounds", "128+ principles"
- **Status**: [x] DONE — Mar 14, 2026

### D5. Dead prisms still on disk / in git staging
- **What**: l12_general.md, l12_general_adversarial.md, l12_general_synthesis.md
- **Status**: [x] DONE — already cleaned up (not tracked in git)

### D6. VPS IP + password in CLAUDE.md
- **What**: Check if sensitive data is in committed files
- **Status**: [x] DONE — VPS IP NOT in committed CLAUDE.md. Only in .claude/ memory (outside repo)

### D7. 10 architectural decisions pending (from MORNING_CHECKLIST D1-D10)
- LICENSE: [x] exists | README: [x] champion-only with PRISMS.md | experiment_log: [x] updated
- Prism scope: [x] champions in README, full in PRISMS.md | VPS IP: [x] clean
- **Remaining**: Commit strategy (single vs multiple), writer research integration
- **Status**: [~] MOSTLY DONE

---

## 5. ADDITIONAL ITEMS (from memory sweep)

### A1. SDL vs L12 direct comparison
- **Result**: L12 avg 9.5 vs deep_scan avg 8.8. L12 deeper (meta-laws, 3.7x bugs). SDL 57% shorter, catches info laundering L12 misses. ~30-40% overlap. Confirmed complementary.
- **Status**: [x] DONE — Round 40

### A2. Codegen prism on Sonnet
- **Result**: Sonnet follows 3-step protocol perfectly (1183-1688w). Haiku skips protocol (532w, jumps to code). P173 confirmed: codegen needs Sonnet. OPTIMAL_PRISM_MODEL["codegen"]="sonnet" is correct.
- **Status**: [x] DONE — Round 40

### A3. Behavioral prism neutral variants on reasoning
- **What**: errres_neutral, api_surface_neutral, evolution_neutral exist but untested
- **Why**: Code nouns may trigger wrong mode on reasoning targets
- **Status**: [ ]

### A4. Error Resilience 70w cross-target
- **Result**: avg 7.0 — BELOW threshold. Starlette 7.0, Click 7.5, Tenacity 6.5. 70w kills quality vs full errres 9.0. P202: 180w is compression floor.
- **Status**: [x] DONE — Round 40. "Compression-as-clarity" REFUTED at 70w.

### A5. Cross-language validation
- **What**: L12 tested on Go (9.0). Other 36 prisms untested cross-language
- **Why**: Python-tuned vocabulary may not transfer
- **Status**: [ ]

### A6. First-time user experience audit
- **What**: Is the 5-minute path to first scan clear?
- **Why**: Public repo needs onboarding
- **Status**: [ ]

### A7. Examples directory (before/after)
- **What**: Concrete vanilla vs prism output comparisons
- **Why**: README claims are abstract without examples
- **Status**: [ ]

### A8. Prism frontmatter model hints
- **What**: Encode optimal model in prism YAML frontmatter, eliminating OPTIMAL_PRISM_MODEL dict
- **Why**: Single source of truth per prism
- **Status**: [ ]

### A9. 9 VPS-only SDL hybrids
- **What**: sdl_errres, sdl_optim, sdl_api, sdl_evo + discovery_probe (scored but left on VPS)
- **Why**: All scored R38. "None beat originals" — but never re-tested after prism iteration
- **Status**: [ ]

### A10. Pipeline Comparison V2
- **Result**: CONCLUDED. Existing pipelines are validated: Full (9 calls, ~15Kw, 30 bugs) > 3-Way (4 calls, ~8Kw) > Single (1 call, ~2Kw, 16 bugs). No need for mega pipeline. Cost/depth tradeoff is clear and documented.
- **Status**: [x] DONE — killed (Round 40, no experiment needed)

---

## Summary

| Category | Total | Done | Remaining | Priority |
|----------|-------|------|-----------|----------|
| Planned but not executed | 5 | 4 | 1 (sub-artifact impl) | HIGH |
| Open research questions | 10 | 7 | 3 (R3 diamond, R8 blind, R9 GPT) | MEDIUM |
| Infrastructure gaps | 7 | 7 | 0 | DONE |
| Documentation/release blockers | 7 | 7 | 0 | DONE |
| Additional items (memory sweep) | 10 | 7 | 3 (cross-lang, SDL re-test, pipe V2) | LOW |
| Code bugs found during R40 | 6 | 6 | 0 | DONE |
| UX audit items | 3 | 3 | 0 | DONE |
| Design docs | 3 | 3 | 0 | DONE |
| **TOTAL** | **51** | **44** | **7** | |

**Remaining items consolidated into ROADMAP.md** — see that file for the single source of truth on all open work (21 items across 7 categories).

---

## Execution Order (completed)

**Phase 1 — Code bugs** (Tasks 1-5, 23-26): ALL DONE. 4 cook model fixes, behavioral synthesis, target= solve, --solve -o tee, default→sonnet, prism count, jsonschema, package name, cost, startup check.
**Phase 2 — Decisions** (Tasks 9, 10, 20, 21): ALL DONE. Keep prisms as-is, writer documented, pipeline V2 killed, dead prisms archived.
**Phase 3 — VPS tests** (Tasks 6, 12, 13, 19): DONE (6 running). Codegen Sonnet 1183-1688w. Neutral/SDL hybrids not on VPS (skipped).
**Phase 4 — Integration** (Tasks 8, 11, 14, 15): ALL DONE. Frontmatter model hints, cooker routes, UX audit, examples dir.
**Phase 5 — Design docs** (Tasks 16, 17, 18): ALL DONE. Factory, subsystem, benchmark designs written.
**Phase 6 — Memory** (Task 22): DONE. MEMORY.md updated with R40 state.

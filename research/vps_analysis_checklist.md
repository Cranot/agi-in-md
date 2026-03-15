# VPS Test Battery — Analysis Checklist
**Created: Mar 14, 2026**

Execute this checklist after all batches complete. Download results first, then process batch by batch.

---

## Step 0: Download all results from VPS
```bash
scp -r <user>@<VPS_IP>:~/insights/output/vps_validation/ output/vps_validation/
```
- [ ] All batch directories present: P1, P2, P3, R2, R5, R7, A1, A4, I1, R4, R6, R1

---

## P1: Cross-target validation (8 outputs)
**Question**: Do simulation/cultivation/archaeology/sdl_simulation work on Click + Tenacity?

- [ ] Score each output 1-10 (depth rubric: conservation law = 9+, meta-law = 10)
- [ ] Check each references actual Click/Tenacity code (not generic/hallucinated)
- [ ] Compare word counts to Starlette baselines (simulation ~1000w, archaeology ~800w)
- [ ] Record scores in table below

| Prism | Click score | Tenacity score | Starlette baseline | Cross-target stable? |
|-------|-------------|----------------|-------------------|---------------------|
| simulation | | | 9.0 | |
| cultivation | | | 8.5 | |
| archaeology | | | 8.5 | |
| sdl_simulation | | | 8.5-9.0 | |

**If all pass (8.0+)**: Update CLAUDE.md "validated on 3 codebases". Update TRACKER P1 → done.
**If any fail (<7.5)**: Investigate why. Demote prism or note target-sensitivity.

---

## P2: 3-cooker pipeline (2 outputs, ~8K words each)
**Question**: Does COOK_3WAY achieve 9.5 on Click + Tenacity?

- [ ] Score depth (conservation law + meta-law + cross-operation synthesis)
- [ ] Check WHERE/WHEN/WHY are genuinely orthogonal (not restating same findings)
- [ ] Check synthesis cross-references all 3 passes (not just concatenation)
- [ ] Compare to Starlette baseline (9.5 depth, ~9300w)

| Target | Depth | Words | WHERE unique? | WHEN unique? | WHY unique? | Synthesis quality |
|--------|-------|-------|---------------|-------------|-------------|------------------|
| Click | | 8218w | | | | |
| Tenacity | | 7719w | | | | |

**If both 9.0+**: P197 confirmed cross-target. Update TRACKER P2 → done.
**If < 8.5**: 3-cooker may be target-sensitive. Document.

---

## P3: 1000+ line testing (9 outputs)
**Question**: Do prisms degrade on 1000+ line files?

- [ ] Score L12 outputs on Flask/Rich/Requests (conservation law? meta-law?)
- [ ] Compare to 300-line baselines (Starlette ~2000-2500w)
- [ ] Check deep_scan at scale (conservation law found?)
- [ ] Check identity at scale (structural insight, not surface?)
- [ ] Note if any test hit timeout or produced truncated output

| Prism | Flask (1625L) | Rich (2684L) | Requests (1041L) | 300L baseline |
|-------|---------------|-------------|------------------|--------------|
| L12 | 2128w | 2631w | 1958w | ~2000-2500w |
| deep_scan | 1004w | 1098w | 776w | ~700-1000w |
| identity | 1179w | 722w | 985w | ~800w |

**Word counts look GREAT — no degradation.** Still need depth scoring.
**New principle**: "P198: L12 scales to 2700 lines with no quality degradation" (if depth holds)
**Update**: CLAUDE.md "Next Steps" remove "1000+ line testing" item
**Update**: README "When This Fails" — edit large codebase caveat

---

## R2: Miniaturize on Sonnet (2 outputs)
**Question**: Does Sonnet's +0.7 lift save miniaturize (7.0 on Haiku)?

- [ ] Score Sonnet output (887w vs Haiku 436w — 2x word count, expect depth lift)
- [ ] Check for genuine L9 recursion (miniaturization applied to own output)
- [ ] Compare: Haiku 7.0 → Sonnet should be 7.7+ if +0.7 holds

| Model | Words | Time | Depth | L9 recursion? |
|-------|-------|------|-------|---------------|
| Sonnet | 887w | 99s | | |
| Haiku | 436w | 15s | | |

**If Sonnet >= 8.5**: Promote miniaturize to production prism, create `prisms/miniaturize.md`
**If 7.5-8.4**: Useful but not champion. Leave as research.
**If < 7.5**: +0.7 doesn't save it. Close miniaturize.

---

## R5: Poetry/UX domains (4 outputs)
**Question**: Does L12 work on creative/design domains?

- [ ] Score l12_universal on poetry (1021w — does it derive conservation law from a poem?)
- [ ] Score l12 on poetry (384w — short; did code vocabulary break it?)
- [ ] Score l12_universal on UX (1572w)
- [ ] Score l12 on UX (2931w — massive! code nouns may have helped)

| Prism | Poetry | UX Design |
|-------|--------|-----------|
| l12_universal (domain-neutral) | 1021w, score: | 1572w, score: |
| l12 (code vocabulary) | 384w, score: | 2931w, score: |

**Key insight**: Which is better on creative? l12_universal or l12?
**If both 8.5+**: Creative domains confirmed. Update README domain list.
**If l12 >> l12_universal on UX**: Code nouns trigger analytical mode even on design (P101 extended)

---

## R7: Vertical composition (4 outputs)
**Question**: Can prisms analyze L12 output? (P172 said NO)

- [ ] Read deep_scan output (1440w) — does it analyze the ANALYSIS or hallucinate the original code?
- [ ] Read pedagogy output (893w) — transfer corruption of the analytical framework?
- [ ] Read claim output (1390w) — assumption inversion of L12's own claims?
- [ ] Key test: do outputs reference L12-specific concepts (conservation law, meta-law) or Starlette code?

| Prism on L12 output | Words | Analyzes analysis? | Hallucinated code? | Quality |
|---------------------|-------|-------------------|-------------------|---------|
| deep_scan | 1440w | | | |
| pedagogy | 893w | | | |
| claim | 1390w | | | |

**If genuine meta-analysis**: P172 PARTIALLY REFUTED — vertical composition works for domain-neutral prisms
**If hallucinated**: P172 CONFIRMED — code prisms can't process analysis text
**Either way**: New principle about vertical composition conditions

---

## A1: SDL vs L12 head-to-head (6 outputs)
**Question**: Quantified comparison on same rubric

- [ ] Score all 6 outputs (L12 × 3 targets + deep_scan × 3 targets)
- [ ] Compare depth scores
- [ ] Check for unique findings (do they find different things?)

| Target | L12 depth | L12 words | deep_scan depth | deep_scan words | Overlap? |
|--------|-----------|-----------|-----------------|-----------------|----------|
| Starlette | | 2610w | | 986w | |
| Click | | 2019w | | 952w | |
| Tenacity | | 1799w | | 842w | |

**Expected**: L12 deeper (9.5+), deep_scan more focused (9.0), genuinely different findings
**Update**: TRACKER A1 → done

---

## A4: Error Resilience 70w (3 outputs)
**Question**: Does compressed 70w maintain 9.5 across targets?

- [ ] Score all 3 outputs (errres70w × Starlette/Click/Tenacity)
- [ ] Word counts are LOW (294-439w) — is depth there despite brevity?
- [ ] Compare to full error_resilience (165w prompt, ~800-1000w output)

| Target | Words | Depth | Full errres baseline |
|--------|-------|-------|---------------------|
| Starlette | 331w | | 9.0 |
| Click | 439w | | |
| Tenacity | 294w | | |

**If 8.5+**: Compression-as-clarity is real. New principle.
**If < 8.0**: 70w too aggressive for cross-target. Stay with full version.

---

## I1: Unscored VPS prisms (4 outputs)
**Question**: Any hidden champions?

- [ ] Score each on Starlette

| Prism | Words | Depth | Promote? |
|-------|-------|-------|----------|
| data_flow | 527w | | |
| time_lifecycle | 858w | | |
| redundancy | 586w | | |
| composition_synthesis | 295w | | |

**If any >= 9.0**: Promote to production. Add to OPTIMAL_PRISM_MODEL.
**If all < 7.5**: Archive. Remove from backlog.

---

## R4: Non-code 3-cooker (3 outputs)
**Question**: Does 3-way achieve 9.5 on legal/business/philosophy?

- [ ] Score each output (conservation law? cross-operation synthesis?)
- [ ] Check quality of domain-specific analysis
- [ ] Compare to code 3-way baseline (9.5)

| Domain | Depth | Words | Conservation law? |
|--------|-------|-------|------------------|
| Legal | | | |
| Business | | | |
| Philosophy | | | |

**If avg 9.0+**: "Works on ANY domain" claim strengthened. Update README.
**If < 8.0**: Non-code 3-way needs work. Document limitations.

---

## R6: Content hallucination (4 outputs)
**Question**: How widespread is hallucination with abstract intent?

- [ ] Compare abstract intent outputs vs matching intent outputs
- [ ] Check: do abstract-intent outputs reference actual code from the file?
- [ ] Check: do matching-intent outputs correctly reference actual code?

| Test | Intent matches target? | References real code? | Hallucinated? |
|------|----------------------|----------------------|---------------|
| abstract × Starlette | NO | | |
| abstract × Click | NO | | |
| matching × Starlette | YES | | |
| matching × Click | YES | | |

**If abstract hallucinates, matching doesn't**: P182 CONFIRMED with scope. Add mitigation guidance.
**If neither hallucinates**: P182 may have been environment-specific. Recheck.

---

## R1: Sonnet cook comparison (6 outputs)
**Question**: Is Sonnet cook > Haiku cook?

- [ ] Score 3 Sonnet-cooked outputs
- [ ] Score 3 Haiku-cooked outputs
- [ ] Compare depth, word count, conservation law quality

| Intent | Sonnet-cooked | Haiku-cooked | Delta |
|--------|--------------|-------------|-------|
| temporal degradation | | | |
| structural archaeology | | | |
| perturbation response | | | |

**If Sonnet >> Haiku (>1 point)**: Cook model matters more than we thought
**If ~equal**: Current COOK_MODEL="sonnet" is correct but Haiku cook is viable fallback

---

## Global Post-Analysis

- [ ] Count total new principles discovered (P198+)
- [ ] Write Round 40 summary in experiment_log.md
- [ ] Update CLAUDE.md: round count, principle count, validated claims
- [ ] Update TRACKER.md: mark all completed items
- [ ] Update README if any claims change (scaling, domains, etc.)
- [ ] Update PRISMS.md if any prisms promoted/demoted
- [ ] Commit all new evidence to git

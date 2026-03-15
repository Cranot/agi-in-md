# `--factory` Design: Delta-Validated Prism Generation

## Command Syntax

```
python prism.py --factory target.py --goal "error handling patterns"
python prism.py --factory target.py --goal "error handling patterns" --iterate
```

- `target.py` — file to analyze (code or text). Required.
- `--goal` — analytical direction for the new prism. Required.
- `--iterate` — if V1 delta is borderline, auto-generate V2. Optional.

## Flow (6 steps, 6 API calls)

### Step 1: Baseline Analysis (3 parallel calls, ~$0.15)

Run L12 + deep_scan + identity on `target.py`, all on Sonnet. These three cover what code IS (l12), HIDES (deep_scan), and CLAIMS (identity) -- zero overlap, proven Round 35b. Save to `.deep/factory/baseline_{prism}_{stem}.txt`.

### Step 2: Generate Candidate (1 call, ~$0.05)

Use `COOK_SDL_FACTORY_GOAL` with `--goal`. Model: Sonnet. Validate SDL format (3 steps, 100-220w, imperative header). Retry once on format failure. Save to `.deep/factory/candidate_{name}.md`.

### Step 3: Run Candidate on Target (1 call, ~$0.05)

Run candidate prism on `target.py` via Sonnet. Save to `.deep/factory/candidate_output_{name}_{stem}.txt`.

### Step 4: Delta Analysis (1 call, ~$0.05)

Feed all 4 outputs to the delta judge. Model: Sonnet. The judge classifies each candidate finding as UNIQUE (not in any baseline), RESTATED (same insight, different words), or WEAKER (subset of baseline).

**Delta judge prompt:**
```
You are a structural analyst comparing analysis outputs. Your job is to find
what the CANDIDATE analysis reveals that the three BASELINE analyses do NOT.

---BASELINE 1 (L12: conservation laws, meta-laws, bugs)---
{l12_output}
---END BASELINE 1---
---BASELINE 2 (SDL: information laundering, structural bugs)---
{deep_scan_output}
---END BASELINE 2---
---BASELINE 3 (Identity: claims vs reality, necessary costs)---
{identity_output}
---END BASELINE 3---
---CANDIDATE ({goal})---
{candidate_output}
---END CANDIDATE---

For each finding in the CANDIDATE output, classify as:
1. UNIQUE — not present in any baseline, even in different words
2. RESTATED — same insight as a baseline finding, different vocabulary
3. WEAKER — a subset of a baseline finding

Output JSON:
{
  "unique_findings": ["finding 1 summary", ...],
  "restated_findings": ["finding + which baseline it duplicates", ...],
  "weaker_findings": ["finding + which baseline subsumes it", ...],
  "unique_count": N,
  "delta_verdict": "high" | "borderline" | "low",
  "verdict_reason": "one sentence"
}

Verdict rules:
- "high" = 4+ unique findings revealing a genuinely different structural property
- "borderline" = 2-3 unique findings, or unique but shallow
- "low" = 0-1 unique, or all restated/weaker
- Be strict. Different vocabulary for the same insight = restated, not unique.
```

### Step 5: Decision Gate

| Verdict | Action |
|---------|--------|
| **high** (4+) | Save to `prisms/factory/{name}.md` |
| **borderline** (2-3) | If `--iterate`: go to Step 6. Else: save with `validation_passed: borderline` |
| **low** (0-1) | Do NOT save. Print which baselines cover it |

### Step 6: Iterate V2 (optional, +2 calls, ~$0.10)

Feed V1's delta report + candidate text to `COOK_SDL_FACTORY` (analysis-first, since baseline output now available). Instruction: amplify unique findings, drop restated operations. Re-run + re-judge. If still borderline/low, save as borderline and stop.

## Output Format

```
$ python prism.py --factory routing.py --goal "error handling patterns"

[1/6] baseline: l12 on routing.py... done (1.8s)
[2/6] baseline: deep_scan on routing.py... done (1.2s)
[3/6] baseline: identity on routing.py... done (1.3s)
[4/6] cooking prism for "error handling patterns"... done (2.1s)
[5/6] running candidate on routing.py... done (1.4s)
[6/6] delta analysis... done (1.6s)

delta:       HIGH (5 unique / 1 restated / 0 weaker)
unique:      silent exception swallowing chains
             error context loss across abstraction boundaries
             recovery path assumes original error is retrievable
             catch-all masking specific handler registration
             error category conflation in logging vs propagation

prism:       factory/error_handling  |  165w  |  valid: true
saved:       prisms/factory/error_handling.md
Use it:      --use-prism factory/error_handling
```

Low verdict prints "existing prisms already cover this angle" + paths to baseline outputs.
## File Naming

`prisms/factory/{goal_snake_case}.md` -- lowercased, spaces to underscores, non-alnum stripped, max 40 chars. Collisions: append `_v2`, `_v3`.

## YAML Frontmatter

```yaml
---
calibration_date: 2026-03-14
model_versions: ["claude-sonnet-4-6"]
quality_baseline: null
origin: "factory:delta-validated — goal: error handling patterns"
notes: "Delta-validated against L12+deep_scan+identity. 165w, 3-step SDL-class."
validation_passed: true
delta_unique_count: 5
delta_verdict: high
factory_target: routing.py
factory_goal: "error handling patterns"
factory_version: 1
---
```

## Cost Estimate

| Step | Calls | Cost |
|------|-------|------|
| Baseline (3 parallel) | 3 | ~$0.15 |
| Cook + run + delta | 3 | ~$0.15 |
| **Total** | **6** | **~$0.30** |
| +iterate | +2 | +$0.10 |

Wall-clock: ~10s (baselines parallelized).

## Constraints

1. **Single-target.** Prism may overfit to one file. Cross-target validation is manual.
2. **Fixed baseline.** L12+deep_scan+identity. Goals overlapping other prisms (optimize, contract) may get inflated delta scores.
3. **No auto-promotion.** Saves to `prisms/factory/`, not `prisms/`. Promote after validating on 2+ targets.
4. **SDL-class only.** 3-step, 100-220w. No L12-class or pipeline prisms.
5. **Goal quality = output quality.** No goal validation. Specific goals produce specific prisms.
6. **Delta judge fallibility.** Single Sonnet call. False positives (restated called unique) possible. Strict rubric mitigates.
7. **All Sonnet.** Design-time tool, not production scanner. $0.30/run is acceptable.

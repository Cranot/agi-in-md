# Benchmark Suite Design — `research/benchmark.py`

Regression/benchmark suite for tracking prism quality over time.

## Architecture

One script, two modes. Runs prisms on targets via `claude -p --tools "" --system-prompt-file`, scores outputs with Haiku-as-judge, compares to baselines, flags regressions.

## Targets

| Target | Lines | File | Type |
|--------|-------|------|------|
| Starlette routing.py | 333 | `research/real_code_starlette.py` | Canonical |
| Click core.py | 417 | `research/real_code_click.py` | Canonical |
| Tenacity retry.py | 331 | `research/real_code_tenacity.py` | Canonical |
| Flask app.py | 1625 | `research/real_code_flask.py` | Large |
| Rich console.py | 2684 | `research/real_code_rich.py` | Large |
| Requests api.py | 1041 | `research/real_code_requests.py` | Large |

Large targets test the 1000+ line gap identified in CLAUDE.md Next Steps.

## Modes

### Quick (~15 tests, ~$1.50, ~10 min)

5 champion prisms x 3 canonical targets:

```
QUICK_PRISMS = ["l12", "deep_scan", "identity", "optimize", "error_resilience"]
QUICK_TARGETS = ["starlette", "click", "tenacity"]
```

Champion selection rationale: l12 (default, 9.3 avg), deep_scan (SDL anchor, complementary), identity (best SDL 9.5), optimize (behavioral anchor), error_resilience (model-sensitive canary).

### Full (~198 tests, ~$20, ~90 min)

33 production prisms x 6 targets. Excludes internal-only prisms (adversarial, synthesis, behavioral_synthesis, writer pipeline, codegen — not standalone analysis prisms).

## Scoring

Reuses the validated rubric from `definitive_grid.py`:

```
SCORING_RUBRIC_V1 = """(DEPRECATED — does not penalize confabulation. See V2.)"""

SCORING_RUBRIC = """Rate this structural code analysis on a 1-10 scale.

Anchors:
10 = Conservation law + meta-law + 15+ findings + structural vs fixable + novel insight + ZERO confabulated claims (all facts verifiable from source)
9 = Conservation law + findings with locations + clear structural insight + at most 1 minor unverified claim
8 = Multiple concrete findings + deeper pattern + some structural reasoning + no fabricated APIs/classes
7 = Real issues + structural reasoning but no conservation law
6 = Surface code review OR deep analysis with multiple confabulated facts (fluent-but-false penalty)
5 = Generic review
3 = Summary or analysis with fabricated content (hallucinated APIs, wrong complexity claims)
1 = Empty

CONFABULATION PENALTIES (apply AFTER initial score):
- Deduct 2 points for each fabricated API, class, or function name not in the source
- Deduct 1 point for each unverified factual claim stated as certain (e.g., wrong complexity class, non-existent stdlib module)
- Deduct 1 point for specific performance numbers without measurement basis
- Line number errors within ±5 lines: no penalty. Beyond ±5: deduct 0.5 per instance.
- Floor: score cannot go below 1.

Output ONLY a single number (1-10), nothing else."""

SCORING_RUBRIC_TRUST = """Rate this analysis on TRUST (1-10): would you act on it without external verification?

Anchors:
10 = Every claim tagged with epistemic type + source. Zero confabulation. Self-corrected. Reflexive self-diagnosis included.
9 = Claims typed. Zero confabulation. Minor gaps acknowledged.
8 = Most claims verifiable from source. No fabricated APIs. Honest about limitations.
7 = Real structural findings. Some unverified claims but not presented as certain.
6 = Mix of verified and unverified. No epistemic typing.
5 = Generic analysis. No distinction between structural and factual claims.
3 = Confident confabulation. Fabricated APIs or metrics stated as fact.
1 = Empty or pure hallucination.

TRUST BONUSES:
+1 for explicit epistemic typing (STRUCTURAL/DERIVED/KNOWLEDGE/ASSUMED tags)
+1 for reflexive self-diagnosis (analysis of the analysis)
+1 for listing retracted claims (honest about what was wrong)

Output ONLY a single number (1-13), nothing else."""
```

Judge: Haiku (cheapest, validated as reliable scorer in definitive_grid.py). Extract first number via regex.

## `baseline_scores.json` Schema

```json
{
  "version": 1,
  "created": "2026-03-14",
  "updated": "2026-03-14",
  "note": "Baselines from definitive_grid.py + Round 38-39 results",
  "scores": {
    "l12": {
      "model": "sonnet",
      "starlette": 9.3,
      "click": 9.0,
      "tenacity": 9.0,
      "flask": null,
      "rich": null,
      "requests": null
    },
    "deep_scan": {
      "model": "opus",
      "starlette": 9.0,
      "click": null,
      "tenacity": null
    }
  }
}
```

Rules:
- `null` = no baseline yet (skip comparison, record score for future baseline)
- Each prism key maps to its optimal model (from `OPTIMAL_PRISM_MODEL` in prism.py)
- Scores are floats 1.0-10.0

## Regression Detection

A test **fails** if: `score < baseline - 0.5`

Why 0.5? Haiku judge variance is ~0.3 across repeated runs (observed in definitive_grid.py). 0.5 catches real regressions while absorbing judge noise. A 1.0-point drop is catastrophic (e.g., 9.0 to 8.0 crosses a rubric boundary).

## Output Format

### `output/benchmark/YYYY-MM-DD.json`

```json
{
  "date": "2026-03-14",
  "mode": "quick",
  "git_sha": "4cee344",
  "total_cost_usd": 1.47,
  "elapsed_seconds": 612,
  "results": [
    {
      "prism": "l12",
      "model": "sonnet",
      "target": "starlette",
      "score": 9.0,
      "baseline": 9.3,
      "delta": -0.3,
      "pass": true,
      "output_chars": 4521,
      "time_seconds": 38.2,
      "cost_usd": 0.05
    }
  ],
  "summary": {
    "total": 15,
    "passed": 14,
    "failed": 1,
    "new_baselines": 0,
    "avg_score": 8.9,
    "avg_baseline": 9.1
  }
}
```

### Console Summary Table

```
BENCHMARK RESULTS — quick mode (2026-03-14, 4cee344)
─────────────────────────────────────────────────────────────
Prism              Target       Model    Score  Base  Delta  Result
l12                starlette    sonnet    9.0    9.3  -0.3   PASS
l12                click        sonnet    9.0    9.0   0.0   PASS
l12                tenacity     sonnet    8.5    9.0  -0.5   PASS
error_resilience   starlette    sonnet    7.5    8.5  -1.0   FAIL
identity           starlette    sonnet    9.5    9.5   0.0   PASS
...
─────────────────────────────────────────────────────────────
15 tests: 14 passed, 1 FAILED    avg 8.9 (baseline 9.1)    $1.47
```

## CLI Interface

```bash
# Quick mode (default)
python research/benchmark.py

# Full mode
python research/benchmark.py --full

# Single prism (debugging)
python research/benchmark.py --prism l12

# Single target
python research/benchmark.py --target starlette

# Update baselines from latest run
python research/benchmark.py --update-baseline output/benchmark/2026-03-14.json

# Update baselines: only overwrite scores that improved
python research/benchmark.py --update-baseline output/benchmark/2026-03-14.json --only-improved
```

## Updating Baselines

After intentional changes (new prism version, model routing change):

1. Run full benchmark: `python research/benchmark.py --full`
2. Review failures — confirm they are expected (prism was edited, model changed, etc.)
3. Update: `python research/benchmark.py --update-baseline output/benchmark/YYYY-MM-DD.json`
4. Commit updated `baseline_scores.json` with the prism change

`--update-baseline` reads a results file, writes non-null scores into `baseline_scores.json`, preserves existing scores for prism/target pairs not in the run. `--only-improved` skips scores that decreased (safety net).

## Implementation Sketch

```python
#!/usr/bin/env python3
"""benchmark.py — Prism regression suite."""
import argparse, json, os, re, subprocess, tempfile, time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
PRISM_DIR = ROOT / "prisms"
BASELINE_PATH = ROOT / "research" / "baseline_scores.json"
OUTPUT_DIR = ROOT / "output" / "benchmark"

OPTIMAL_MODEL = {  # from prism.py OPTIMAL_PRISM_MODEL
    "l12": "sonnet", "deep_scan": "opus", "identity": "sonnet",
    "optimize": "sonnet", "error_resilience": "sonnet",
    # ... all 33 production prisms
}

QUICK_PRISMS = ["l12", "deep_scan", "identity", "optimize", "error_resilience"]
QUICK_TARGETS = ["starlette", "click", "tenacity"]
ALL_TARGETS = QUICK_TARGETS + ["flask", "rich", "requests"]

THRESHOLD = 0.5  # max allowed drop from baseline

def call_claude(system_prompt_file, user_input, model, timeout=300):
    """Runs claude -p --tools "" and returns (text, cost, seconds)."""
    ...

def score_output(text, judge="haiku"):
    """Haiku-as-judge scoring. Returns float 1-10."""
    ...

def load_target(name):
    """Reads research/real_code_{name}.py, returns text."""
    ...

def run_benchmark(prisms, targets, baselines):
    """Run all prism x target pairs, score, compare to baselines."""
    results = []
    for prism in prisms:
        model = OPTIMAL_MODEL.get(prism, "sonnet")
        for target in targets:
            text, cost, secs = call_claude(prism_path, source, model)
            score = score_output(text)
            base = baselines.get(prism, {}).get(target)
            delta = score - base if base else None
            passed = delta is None or delta >= -THRESHOLD
            results.append({...})
    return results
```

## CI Integration

### Recommended: Quick mode on prism changes

```yaml
# .github/workflows/benchmark.yml
name: Prism Benchmark
on:
  push:
    paths: ['prisms/**', 'prism.py']
  workflow_dispatch:

jobs:
  benchmark:
    runs-on: ubuntu-latest  # or self-hosted with Claude CLI
    steps:
      - uses: actions/checkout@v4
      - name: Run quick benchmark
        run: python research/benchmark.py --json
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      - name: Check for regressions
        run: |
          FAILED=$(python -c "import json,sys; r=json.load(open('output/benchmark/latest.json')); sys.exit(0 if r['summary']['failed']==0 else 1)")
      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: benchmark-${{ github.sha }}
          path: output/benchmark/
```

Practical notes:
- Requires `claude` CLI on runner (or VPS via SSH). CI on VPS: `ssh <user>@<VPS_IP> 'cd ~/insights && python research/benchmark.py'`
- Quick mode costs ~$1.50/run. Budget: ~$45/month at 1 run/day.
- Full mode: run manually before releases or after major refactors.
- Store results as artifacts for trend analysis.

## Bootstrapping Baselines

First run populates `baseline_scores.json` for all prism/target pairs:

```bash
# Run full suite
python research/benchmark.py --full

# All scores will show as "NEW" (no baseline to compare)
# Review output, then set as baseline
python research/benchmark.py --update-baseline output/benchmark/2026-03-14.json
```

## Cost Model

| Component | Per test | Quick (15) | Full (198) |
|-----------|----------|------------|------------|
| Prism run (avg) | ~$0.08 | $1.20 | $15.84 |
| Judge call | ~$0.01 | $0.15 | $1.98 |
| **Total** | ~$0.09 | **~$1.35** | **~$17.82** |

Prism run cost varies by model: Haiku ~$0.01, Sonnet ~$0.05, Opus ~$0.15. Estimates use weighted average from `OPTIMAL_MODEL` distribution.

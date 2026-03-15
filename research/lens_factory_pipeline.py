#!/usr/bin/env python3
"""
Systematic Lens Factory Pipeline
=================================
Two modes, one validation loop, auto-promotion.

  extract  — content-driven: distill lenses from existing L12 analyses
  design   — goal-driven: calibrate targets, derive goals, factory-design
  both     — run extract first, then design to fill gaps (default)

Usage:
  python research/lens_factory_pipeline.py [extract|design|both] [THRESHOLD]

  THRESHOLD: min --validate overall score for promotion (default 8.0)

Conservation law under test:
  Extraction Calibration × Design Speed = constant
  extract: calibrated to real findings, requires prior L12 analysis
  design: fast, no prior analysis, uncalibrated until validated

Output:
  Validated lenses copied to prisms/ with quality_baseline set.
  Run log written to output/factory_pipeline_TIMESTAMP.json
"""

import json
import pathlib
import re
import shutil
import subprocess
import sys
import time

# ── Config ────────────────────────────────────────────────────────────────────

ROOT = pathlib.Path(__file__).resolve().parent.parent
PRISM_PY = ROOT / "prism.py"
PRISM_DIR = ROOT / "prisms"
OUTPUT_DIR = ROOT / "output"

# Validation targets for cross-target testing
VALIDATION_TARGETS = [
    ROOT / "research" / "real_code_starlette.py",
    ROOT / "research" / "real_code_click.py",
    ROOT / "research" / "real_code_tenacity.py",
]

# L12 analysis outputs — richest extraction sources
L12_GLOB_PATTERNS = [
    "round27_chained/**/sonnet_L12*.md",
    "round28_validation/**/haiku_*_starlette.md",
    "round28_validation/**/haiku_*_click.md",
    "round28_validation/**/haiku_*_tenacity.md",
]

# Goals derived from the L7-L12 taxonomy's distinct analytical operations.
# Domain goals (routing, auth) produce domain-specific lenses — wrong.
# Taxonomy goals map to structural properties that work across ALL domains.
# Each level in the taxonomy is a distinct analytical operation = a lens goal.
GOAL_TEMPLATES = {
    # L7: concealment mechanism — what does the artifact make invisible?
    "concealment":    "find the mechanism by which the artifact conceals its "
                      "own structural problems — what it makes invisible by design",
    # L8: generative construction — improvements that recreate original problems
    "self_recreation": "find how proposed improvements recreate the original "
                       "problem at a deeper level — improvements that don't fix, only relocate",
    # L9-B: identity ambiguity — contradicting constructions reveal what it IS
    "identity":       "find the structural identity conflict: two equally valid "
                      "descriptions that contradict each other about what the artifact IS",
    # L9-C: recursive concealment — the diagnostic conceals what it diagnoses
    "recursive_blind": "find how the artifact's own self-description conceals "
                       "the property it claims to reveal",
    # L10-B: design topology — map feasible vs infeasible design regions
    "design_topology": "find the design-space boundary: which improvements are "
                       "structurally impossible vs merely difficult",
    # L10-C: impossibility — two properties that cannot coexist
    "impossibility":  "find the two structural properties that cannot coexist: "
                      "prove one must be sacrificed whenever the other is present",
    # L11-A: escape — what adjacent design category sidesteps the impossibility
    "escape_route":   "find the adjacent design category that sidesteps the "
                      "core impossibility by redefining the problem",
    # L11-C: conservation law — what quantity is preserved across all changes
    "invariant":      "find the structural invariant that persists through every "
                      "attempted improvement — the quantity that is conserved",
}


# ── Subprocess helpers ─────────────────────────────────────────────────────────

def _run(args, stdin_text=None, timeout=300):
    """Run prism.py with args. Returns (stdout, stderr, returncode)."""
    cmd = [sys.executable, str(PRISM_PY)] + [str(a) for a in args]
    result = subprocess.run(
        cmd,
        input=stdin_text,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=ROOT,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def _parse_json(text):
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
    return None


def ensure_sdl_example(target_file):
    """
    Generate and cache an SDL analysis output for use as B3 few-shot example.
    Cached at .deep/sdl_example.txt — reused across all factory runs.
    If generation fails, returns empty string (factory falls back to goal-spec mode).
    """
    cache = ROOT / ".deep" / "sdl_example.txt"
    if cache.exists() and cache.stat().st_size > 200:
        return cache.read_text(encoding="utf-8")
    print(f"\n  Generating SDL example on {target_file.name} (for B3 mode)...",
          end="", flush=True)
    content = target_file.read_text(encoding="utf-8")
    stdout, stderr, rc = _run(
        ["--solve", "--use-prism", "deep_scan", "-m", "haiku", "--json"],
        stdin_text=content,
        timeout=180,
    )
    result = _parse_json(stdout) or {}
    output = result.get("response", "")
    if output and len(output.split()) > 200:
        cache.parent.mkdir(exist_ok=True)
        cache.write_text(output, encoding="utf-8")
        print(f" done ({len(output.split())}w)")
        return output
    print(" failed (factory will use goal-spec mode)")
    return ""


# ── Stage 1A: Content-driven extraction ───────────────────────────────────────

def find_l12_analyses():
    """Discover all L12 analysis outputs matching known glob patterns."""
    found = []
    for pattern in L12_GLOB_PATTERNS:
        found.extend(OUTPUT_DIR.glob(pattern))
    # Deduplicate by stem, keep most recent
    seen = {}
    for p in found:
        if p.stem not in seen:
            seen[p.stem] = p
    return list(seen.values())


def extract_lens(analysis_file):
    """Run --extract-lens on an analysis file. Returns result dict or None."""
    stdout, stderr, rc = _run(
        ["--extract-lens", str(analysis_file), "--json"])
    if rc != 0:
        return {"error": f"extract failed (rc={rc})", "stderr": stderr[:300]}
    result = _parse_json(stdout)
    if result:
        result["_source"] = str(analysis_file.name)
        result["_mode"] = "extract"
    return result


# ── Stage 1B: Goal-driven factory ─────────────────────────────────────────────

def calibrate_target(target_file):
    """Calibrate a target file. Returns k_report dict or None."""
    content = target_file.read_text(encoding="utf-8")
    stdout, stderr, rc = _run(["--calibrate", "--json"], stdin_text=content)
    return _parse_json(stdout)


def derive_goal(k_report):
    """Map calibrate output to a factory goal string."""
    domain = (k_report or {}).get("domain", "unknown")
    # Match to closest known template
    for key in GOAL_TEMPLATES:
        if key in domain.lower():
            return GOAL_TEMPLATES[key]
    # Fallback: construct from domain
    content_type = (k_report or {}).get("content_type", "code")
    return f"find structural bugs and hidden trade-offs in {domain} {content_type}"


def factory_lens(goal):
    """Run --factory with a goal string. Returns result dict or None."""
    stdout, stderr, rc = _run(["--factory", goal, "--json"])
    if rc != 0:
        return {"error": f"factory failed (rc={rc})", "stderr": stderr[:300]}
    result = _parse_json(stdout)
    if result:
        result["_goal"] = goal
        result["_mode"] = "design"
    return result


# ── Stage 2: 2×2 validation (2 targets × 2 models) ───────────────────────────
# A lens must pass ≥3/4 runs to be promoted.
# Single run is stochastic (same prism+target: 38t run1, 2t run2 observed).
# 4 runs eliminates single-run variance as a promotion signal.

VALIDATION_MODELS = ["haiku", "sonnet"]


def _validate_one(prism_path, target_file, model):
    """Single validation run. Returns {overall, single_shot, words, ...}."""
    content = target_file.read_text(encoding="utf-8")
    stdout, stderr, rc = _run(
        ["--solve", "--use-prism", prism_path, "-m", model,
         "--validate", "--json"],
        stdin_text=content,
        timeout=180,
    )
    result = _parse_json(stdout) or {}
    val = result.get("validation", {})

    turns = 1
    m = re.search(r"turn[s]?\s*[=:]\s*(\d+)", stderr, re.IGNORECASE)
    if m:
        turns = int(m.group(1))

    response = result.get("response", stdout)
    words = len(response.split()) if response else 0
    return {
        "overall": val.get("overall", 0),
        "depth": val.get("depth", 0),
        "actionability": val.get("actionability", 0),
        "strongest": val.get("strongest", ""),
        "weakest": val.get("weakest", ""),
        "single_shot": turns == 1,
        "words": words,
        "target": target_file.name,
        "model": model,
        "rc": rc,
    }


def validate_lens_2x2(lens_result, cross_targets, threshold):
    """
    Two-stage validation: cheap pre-filter then full 2×2.

    Stage 1 (pre-filter, $0.003): 1 Haiku run on first cross-target.
      - overall < 6 or multi-shot → reject immediately (save 3 calls)
      - overall ≥ 6 + single-shot → proceed to Stage 2
    Stage 2 (full, 3 more calls): remaining 3 runs (2nd target × 2 models + 1st × Sonnet)
      Expected cost: 0.7 × 1 call + 0.5 × 4 calls ≈ 2.7 calls per lens average.

    Returns (runs: list, passed: int, should_promote: bool).
    Promotion criterion: ≥3/4 pass (overall ≥ threshold AND single-shot).
    """
    lens_name = lens_result.get("name", "")
    if not lens_name:
        return [], 0, False

    mode = lens_result.get("_mode", "design")
    prism_path = (f"factory/extracted/{lens_name}"
                  if mode == "extract" else f"factory/{lens_name}")

    # Stage 1: pre-filter on first target × Haiku
    first_target = cross_targets[0] if cross_targets else None
    if first_target is None:
        return [], 0, False
    try:
        pre = _validate_one(prism_path, first_target, "haiku")
    except Exception as e:
        return [{"error": str(e), "overall": 0, "single_shot": False,
                 "target": first_target.name, "model": "haiku"}], 0, False

    if pre.get("overall", 0) < 6 or not pre.get("single_shot"):
        # Hard reject — not worth 3 more calls
        return [pre], 0, False

    # Stage 2: full 2×2 (pre-filter run already counted)
    runs = [pre]
    remaining = [
        (cross_targets[0], "sonnet"),           # 1st target × Sonnet
        (cross_targets[1] if len(cross_targets) > 1 else cross_targets[0], "haiku"),
        (cross_targets[1] if len(cross_targets) > 1 else cross_targets[0], "sonnet"),
    ]
    for target, model in remaining:
        try:
            r = _validate_one(prism_path, target, model)
        except subprocess.TimeoutExpired:
            r = {"error": "timeout", "overall": 0,
                 "single_shot": False, "target": target.name,
                 "model": model}
        except Exception as e:
            r = {"error": str(e), "overall": 0,
                 "single_shot": False, "target": target.name,
                 "model": model}
        runs.append(r)

    passed = sum(
        1 for r in runs
        if r.get("overall", 0) >= threshold and r.get("single_shot")
    )
    return runs, passed, passed >= 3


# ── Stage 3: Promotion ────────────────────────────────────────────────────────

def promote_lens(lens_result, runs, passed):
    """
    Copy lens to prisms/ with quality_baseline set to median score of passing runs.
    Returns the destination path or None.
    """
    lens_name = lens_result.get("name", "")
    mode = lens_result.get("_mode", "design")
    src = (PRISM_DIR / "factory" / "extracted" / f"{lens_name}.md"
           if mode == "extract"
           else PRISM_DIR / "factory" / f"{lens_name}.md")
    if not src.exists():
        return None

    passing_scores = [r["overall"] for r in runs
                      if r.get("overall", 0) > 0 and r.get("single_shot")]
    median_score = (sorted(passing_scores)[len(passing_scores) // 2]
                    if passing_scores else 0)

    today = time.strftime("%Y-%m-%d")
    targets_used = list({r["target"] for r in runs})
    content = src.read_text(encoding="utf-8")
    content = content.replace(
        "quality_baseline: null",
        f"quality_baseline: {median_score}",
    )
    content = content.replace(
        "validation_passed: true",
        f"validation_passed: true\n"
        f"validation_date: {today}\n"
        f"validation_runs: {len(runs)}\n"
        f"validation_passed_count: {passed}\n"
        f"validation_score_median: {median_score}\n"
        f"validation_targets: {targets_used}",
    )
    dst = PRISM_DIR / f"{lens_name}.md"
    dst.write_text(content, encoding="utf-8")
    return dst


# ── Pipeline orchestration ────────────────────────────────────────────────────

def run_pipeline(mode="both", threshold=8.0):
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log = {
        "timestamp": timestamp,
        "mode": mode,
        "threshold": threshold,
        "results": [],
    }

    # Cross-target rotation: lens produced from source A → validated on source B
    valid_targets = [t for t in VALIDATION_TARGETS if t.exists()]
    if not valid_targets:
        print("Error: no validation targets found in research/", file=sys.stderr)
        sys.exit(1)

    # 2×2 validation uses the next 2 targets after the source index
    def _cross_targets(idx):
        n = len(valid_targets)
        return [valid_targets[(idx + 1) % n], valid_targets[(idx + 2) % n]]

    candidates = []  # [(lens_result, source_idx)]

    # ── Seed SDL example for B3 factory mode ─────────────────────────────
    # B3 mode (blind-spot design) requires an SDL output as few-shot example.
    # Generate once, cache at .deep/sdl_example.txt, reused by all --factory calls.
    if mode in ("design", "both") and valid_targets:
        ensure_sdl_example(valid_targets[0])

    # ── Stage 1A: Content-driven extraction ──────────────────────────────
    if mode in ("extract", "both"):
        analyses = find_l12_analyses()
        print(f"\n── Stage 1A: Extract from {len(analyses)} L12 analyses")
        for i, analysis_file in enumerate(analyses[:6]):  # cap at 6
            print(f"  [{i+1}/{min(len(analyses),6)}] {analysis_file.name[:60]}")
            result = extract_lens(analysis_file)
            if result and result.get("name"):
                candidates.append((result, i))
                print(f"    → {result['name']} (valid={result.get('valid')})")
            else:
                print(f"    → failed: {(result or {}).get('error','?')}")

    # ── Stage 1B: Goal-driven factory ────────────────────────────────────
    if mode in ("design", "both"):
        print(f"\n── Stage 1B: Factory for {len(GOAL_TEMPLATES)} goals")
        for i, (key, goal) in enumerate(GOAL_TEMPLATES.items()):
            # Skip if a lens for this goal already exists in prisms/
            slug = re.sub(r"[^\w]", "_", key)
            existing = list(PRISM_DIR.glob(f"*{slug}*.md"))
            if existing and mode == "both":
                print(f"  [{i+1}] {key}: skip (lens exists)")
                continue
            print(f"  [{i+1}] {key}: {goal[:50]}...")
            result = factory_lens(goal)
            if result and result.get("name"):
                candidates.append((result, i))
                print(f"    → {result['name']} (valid={result.get('valid')})")
            else:
                print(f"    → failed: {(result or {}).get('error','?')}")

    # ── Stage 2 + 3: 2×2 validation then promote ─────────────────────────
    # Each lens: 2 cross-targets × 2 models (haiku + sonnet) = 4 runs
    # Promote if ≥3/4 pass (overall ≥ threshold AND single-shot)
    print(f"\n── Stage 2: 2×2 validate {len(candidates)} candidates "
          f"(4 runs each, promote if ≥3/4)")
    promoted = []
    for lens_result, src_idx in candidates:
        name = lens_result.get("name", "?")
        targets = _cross_targets(src_idx)
        print(f"  {name}")
        print(f"    targets: {[t.name for t in targets]}, "
              f"models: {VALIDATION_MODELS}")

        runs, passed, should_promote = validate_lens_2x2(
            lens_result, targets, threshold)

        for r in runs:
            ss = "1-shot" if r.get("single_shot") else "multi "
            print(f"    {r.get('model','?'):6} × {r.get('target','?'):30} "
                  f"→ overall={r.get('overall',0)} {ss} "
                  f"words={r.get('words',0)}")
        print(f"    passed {passed}/4 — "
              f"{'PROMOTE' if should_promote else 'reject'}")

        dst = promote_lens(lens_result, runs, passed) if should_promote else None
        if dst:
            print(f"    ✓ PROMOTED → prisms/{dst.name}")
            promoted.append(dst.name)

        log["results"].append({
            "lens": name,
            "mode": lens_result.get("_mode"),
            "source": lens_result.get("_source") or lens_result.get("_goal", ""),
            "runs": runs,
            "passed": passed,
            "promoted": dst.name if dst else None,
        })

    # ── Summary ───────────────────────────────────────────────────────────
    print(f"\n── Summary")
    print(f"  candidates:  {len(candidates)}")
    print(f"  promoted:    {len(promoted)}")
    print(f"  threshold:   overall ≥ {threshold} + single-shot, ≥3/4 runs")
    if promoted:
        for name in promoted:
            print(f"    prisms/{name}")

    # Write log
    log_path = OUTPUT_DIR / f"factory_pipeline_{timestamp}.json"
    log_path.write_text(json.dumps(log, indent=2), encoding="utf-8")
    print(f"\n  log: {log_path.name}")

    return log


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "both"
    threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 8.0
    if mode not in ("extract", "design", "both"):
        print("Usage: python research/lens_factory_pipeline.py [extract|design|both] [THRESHOLD]")
        sys.exit(1)
    run_pipeline(mode=mode, threshold=threshold)

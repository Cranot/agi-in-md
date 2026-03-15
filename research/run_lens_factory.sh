#!/usr/bin/env bash
# run_lens_factory.sh — Systematic Lens Factory Experiment
#
# Two pipelines in parallel:
#   A) Content-driven extraction (--extract-lens): distill from real L12 analyses
#   B) Goal-driven factory (--factory): design from goal specification
#
# Then validate all produced lenses on Haiku cross-targets.
#
# Conservation law under test:
#   Extraction Quality × Design Speed = constant
#   Extraction = calibrated to real findings, slow (needs prior analysis)
#   Factory = fast (no prior analysis), uncalibrated
#
# Usage: bash research/run_lens_factory.sh [--validate-only]

set -euo pipefail
cd "$(dirname "$0")/.."

PRISM="python prism.py"
OUT="output/lens_factory_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT"

# ── Analysis sources for extraction (richest L12 outputs) ────────────
STARLETTE_L12="output/round27_chained/real_code_starlette/sonnet_L12_meta_conservation_v2_real_code_starlette.md"
CLICK_L12="output/round27_chained/real_code_click/sonnet_L12_meta_conservation_v2_real_code_click.md"
TENACITY_L12="output/round27_chained/real_code_tenacity/sonnet_L12_meta_conservation_v2_real_code_tenacity.md"

# ── Validation targets (cross-target: extracted from A, validated on B) ──
STARLETTE_CODE="research/real_code_starlette.py"
CLICK_CODE="research/real_code_click.py"
TENACITY_CODE="research/real_code_tenacity.py"

validate_only="${1:-}"

echo "=== Lens Factory Experiment ===" | tee "$OUT/log.txt"
echo "Started: $(date)" | tee -a "$OUT/log.txt"
echo "" | tee -a "$OUT/log.txt"

# ────────────────────────────────────────────────────────────────────
# PHASE A: Content-driven extraction
# --extract-lens on each L12 analysis output
# ────────────────────────────────────────────────────────────────────
if [[ "$validate_only" != "--validate-only" ]]; then
    echo "── Phase A: Content-driven extraction ──────────────────────" | tee -a "$OUT/log.txt"

    for target in starlette click tenacity; do
        src_var="${target^^}_L12"
        src="${!src_var}"
        if [[ ! -f "$src" ]]; then
            echo "  SKIP $target — source not found: $src" | tee -a "$OUT/log.txt"
            continue
        fi
        echo -n "  extract from $target L12... " | tee -a "$OUT/log.txt"
        $PRISM --extract-lens "$src" --json \
            2>>"$OUT/log.txt" \
            | tee "$OUT/extract_${target}.json"
        echo "" | tee -a "$OUT/log.txt"
        lens_name=$(python -c "import json,sys; d=json.load(open('$OUT/extract_${target}.json')); print(d.get('name','?'))" 2>/dev/null || echo "?")
        echo "  → lens: $lens_name" | tee -a "$OUT/log.txt"
    done

    echo "" | tee -a "$OUT/log.txt"

    # ──────────────────────────────────────────────────────────────────
    # PHASE B: Goal-driven factory (same domains, different goals)
    # ──────────────────────────────────────────────────────────────────
    echo "── Phase B: Goal-driven factory ────────────────────────────" | tee -a "$OUT/log.txt"

    declare -A GOALS=(
        [routing]="find URL routing conflicts and parameter binding failures in web frameworks"
        [cli_parsing]="find CLI argument parsing edge cases and option conflict bugs"
        [retry_logic]="find retry storm and backoff miscalculation bugs in resilience code"
    )

    for goal_key in routing cli_parsing retry_logic; do
        goal="${GOALS[$goal_key]}"
        echo -n "  factory: $goal_key... " | tee -a "$OUT/log.txt"
        $PRISM --factory "$goal" --json \
            2>>"$OUT/log.txt" \
            | tee "$OUT/factory_${goal_key}.json"
        echo "" | tee -a "$OUT/log.txt"
        lens_name=$(python -c "import json,sys; d=json.load(open('$OUT/factory_${goal_key}.json')); print(d.get('name','?'))" 2>/dev/null || echo "?")
        echo "  → lens: $lens_name" | tee -a "$OUT/log.txt"
    done

    echo "" | tee -a "$OUT/log.txt"
fi

# ────────────────────────────────────────────────────────────────────
# PHASE C: Cross-target validation on Haiku
# Each lens validated on a DIFFERENT target than its source
# Scoring: single-shot? conservation law present? markers ≥7/10?
# ────────────────────────────────────────────────────────────────────
echo "── Phase C: Haiku cross-target validation ──────────────────────" | tee -a "$OUT/log.txt"

# Map: extracted_from → validate_on
declare -A CROSS_TARGETS=(
    [starlette]="$CLICK_CODE"      # extracted from Starlette → validate on Click
    [click]="$TENACITY_CODE"       # extracted from Click → validate on Tenacity
    [tenacity]="$STARLETTE_CODE"   # extracted from Tenacity → validate on Starlette
    [routing]="$TENACITY_CODE"     # factory routing lens → validate on Tenacity
    [cli_parsing]="$STARLETTE_CODE"
    [retry_logic]="$CLICK_CODE"
)

for key in starlette click tenacity routing cli_parsing retry_logic; do
    # Find the lens name from the JSON output
    json_file="$OUT/extract_${key}.json"
    [[ -f "$json_file" ]] || json_file="$OUT/factory_${key}.json"
    [[ -f "$json_file" ]] || { echo "  SKIP $key — no JSON"; continue; }

    lens_name=$(python -c \
        "import json; d=json.load(open('$json_file')); print(d.get('name',''))" \
        2>/dev/null || echo "")
    [[ -n "$lens_name" ]] || { echo "  SKIP $key — no lens name"; continue; }

    # Determine prism subdir
    if [[ "$key" =~ ^(starlette|click|tenacity)$ ]]; then
        prism_path="factory/extracted/${lens_name}"
    else
        prism_path="factory/${lens_name}"
    fi

    validate_target="${CROSS_TARGETS[$key]}"
    [[ -f "$validate_target" ]] || { echo "  SKIP $key — target not found"; continue; }

    echo -n "  validate $key lens on $(basename $validate_target .py)... " | tee -a "$OUT/log.txt"
    result_file="$OUT/validate_${key}.txt"

    # Run on Haiku — single call, no retry (fail = agentic = note it)
    cat "$validate_target" | \
        $PRISM --solve --use-prism "$prism_path" -m haiku \
        > "$result_file" 2>>"$OUT/log.txt" \
        && echo "done" | tee -a "$OUT/log.txt" \
        || echo "FAILED (exit $?)" | tee -a "$OUT/log.txt"

    # Quick markers check
    word_count=$(wc -w < "$result_file" 2>/dev/null || echo 0)
    has_law=$(grep -ci "conservation law\|conserved\|trade.off\|cannot.*coexist" "$result_file" 2>/dev/null || echo 0)
    echo "    words=$word_count  conservation_law_mentions=$has_law" | tee -a "$OUT/log.txt"
done

echo "" | tee -a "$OUT/log.txt"

# ────────────────────────────────────────────────────────────────────
# PHASE D: SDL baseline (control)
# Run SDL on same targets to compare
# ────────────────────────────────────────────────────────────────────
echo "── Phase D: SDL baseline (control) ─────────────────────────────" | tee -a "$OUT/log.txt"

for target_file in "$STARLETTE_CODE" "$CLICK_CODE" "$TENACITY_CODE"; do
    name=$(basename "$target_file" .py)
    echo -n "  SDL on $name... " | tee -a "$OUT/log.txt"
    cat "$target_file" | \
        $PRISM --solve --use-prism deep_scan -m haiku \
        > "$OUT/sdl_${name}.txt" 2>>"$OUT/log.txt" \
        && echo "done" | tee -a "$OUT/log.txt" \
        || echo "FAILED" | tee -a "$OUT/log.txt"
    word_count=$(wc -w < "$OUT/sdl_${name}.txt" 2>/dev/null || echo 0)
    has_law=$(grep -ci "conservation law\|conserved\|trade.off" "$OUT/sdl_${name}.txt" 2>/dev/null || echo 0)
    echo "    words=$word_count  conservation_law_mentions=$has_law" | tee -a "$OUT/log.txt"
done

echo "" | tee -a "$OUT/log.txt"
echo "=== Done. Results in: $OUT ===" | tee -a "$OUT/log.txt"
echo "" | tee -a "$OUT/log.txt"
echo "Score each validate_*.txt for:" | tee -a "$OUT/log.txt"
echo "  1. Single-shot? (check turn count in log)" | tee -a "$OUT/log.txt"
echo "  2. Conservation law present? (has_law > 0)" | tee -a "$OUT/log.txt"
echo "  3. Word count ≥ 800 (signal of full execution)" | tee -a "$OUT/log.txt"
echo "  4. Compare word count + law mentions vs SDL baseline" | tee -a "$OUT/log.txt"
echo "" | tee -a "$OUT/log.txt"
echo "Promote passing lenses:" | tee -a "$OUT/log.txt"
echo "  mv prisms/factory/extracted/LENS.md prisms/LENS.md" | tee -a "$OUT/log.txt"

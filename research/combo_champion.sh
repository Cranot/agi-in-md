#!/bin/bash
# Find the "full" champion: L12 alone vs Enhanced L12 (A) vs L12→Complement (B)
# Run from project root in a SEPARATE TERMINAL
#
# Usage: bash research/combo_champion.sh [starlette|click|tenacity|all]
# Default: starlette

set -e

TARGET_NAME="${1:-starlette}"
MODEL="haiku"
OUTDIR="output/combo_test"

mkdir -p "$OUTDIR"

run_target() {
    local name="$1"
    local target="research/real_code_${name}.py"

    echo "============================================"
    echo "  TARGET: $name"
    echo "============================================"
    echo ""

    # --- BASELINE: L12 alone (1 call) ---
    echo "--- Baseline: L12 alone (1 call) ---"
    CLAUDECODE="" claude -p --model "$MODEL" --output-format text --tools "" \
        --system-prompt-file prisms/l12.md < "$target" > "$OUTDIR/baseline_${name}.md"
    echo "  Done: $(wc -l < "$OUTDIR/baseline_${name}.md") lines"
    echo ""

    # --- ARCH A: Enhanced L12 (1 call, L12 + complement axes) ---
    echo "--- Architecture A: Enhanced L12 (1 call) ---"
    CLAUDECODE="" claude -p --model "$MODEL" --output-format text --tools "" \
        --system-prompt-file prisms/l12.md < "$target" > "$OUTDIR/archA_${name}.md"
    echo "  Done: $(wc -l < "$OUTDIR/archA_${name}.md") lines"
    echo ""

    # --- ARCH B: L12 → Informed Complement (2 calls) ---
    echo "--- Architecture B: L12 → Complement (2 calls) ---"
    # Call 1: standard L12
    CLAUDECODE="" claude -p --model "$MODEL" --output-format text --tools "" \
        --system-prompt-file prisms/l12.md < "$target" > "$OUTDIR/archB_l12_${name}.md"
    echo "  Call 1 done: $(wc -l < "$OUTDIR/archB_l12_${name}.md") lines"

    # Call 2: complement that sees L12 output + code
    # Build input: code first, then L12 output
    {
        echo "# SOURCE CODE"
        echo ""
        cat "$target"
        echo ""
        echo "---"
        echo ""
        echo "# STRUCTURAL ANALYSIS (from previous pass)"
        echo ""
        cat "$OUTDIR/archB_l12_${name}.md"
    } > "$OUTDIR/archB_input_${name}.md"

    CLAUDECODE="" claude -p --model "$MODEL" --output-format text --tools "" \
        --system-prompt-file prisms/l12_complement_adversarial.md < "$OUTDIR/archB_input_${name}.md" \
        > "$OUTDIR/archB_${name}.md"
    echo "  Call 2 done: $(wc -l < "$OUTDIR/archB_${name}.md") lines"
    echo ""

    echo "=== $name COMPLETE ==="
    echo "  Baseline:  $OUTDIR/baseline_${name}.md"
    echo "  Arch A:    $OUTDIR/archA_${name}.md"
    echo "  Arch B:    $OUTDIR/archB_${name}.md  (+ L12 in archB_l12_${name}.md)"
    echo ""
}

if [ "$TARGET_NAME" = "all" ]; then
    for t in starlette click tenacity; do
        run_target "$t"
    done
else
    case "$TARGET_NAME" in
        starlette|click|tenacity) run_target "$TARGET_NAME" ;;
        *) echo "Unknown: $TARGET_NAME. Use starlette|click|tenacity|all"; exit 1 ;;
    esac
fi

echo ""
echo "=== RATING GUIDE ==="
echo "Compare outputs on:"
echo "  1. Depth: conservation law + meta-law quality (0-10)"
echo "  2. Complement: temporal + resource + contract findings (0-10)"
echo "  3. Emergent: findings that only exist from combining perspectives (Y/N)"
echo "  4. Bug table: count + fixable/structural classification"
echo "  5. Overall value: would you pay 2x for this over baseline? (Y/N)"

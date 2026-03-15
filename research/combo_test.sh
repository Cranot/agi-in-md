#!/bin/bash
# Combo test: find the optimal prism combination
# Run from project root in a SEPARATE TERMINAL (not from Claude Code)
#
# Usage: bash research/combo_test.sh [starlette|click|tenacity]
# Default: starlette

set -e

TARGET_NAME="${1:-starlette}"
MODEL="haiku"
OUTDIR="output/combo_test"
SYNTHPROMPT="research/combo_synth.md"

case "$TARGET_NAME" in
    starlette) TARGET="research/real_code_starlette.py" ;;
    click)     TARGET="research/real_code_click.py" ;;
    tenacity)  TARGET="research/real_code_tenacity.py" ;;
    *) echo "Unknown target: $TARGET_NAME. Use starlette|click|tenacity"; exit 1 ;;
esac

mkdir -p "$OUTDIR" "$OUTDIR/raw"
echo "=== Combo test on $TARGET_NAME ==="
echo "Model: $MODEL"
echo ""

run_prism() {
    local prism="$1"
    local outfile="$2"
    echo "  Running $prism..."
    CLAUDECODE="" claude -p --model "$MODEL" --output-format text --tools "" \
        --system-prompt-file "prisms/${prism}.md" < "$TARGET" > "$outfile"
    echo "  Done: $prism ($(wc -l < "$outfile") lines)"
}

run_synth() {
    local label="$1"
    local input_file="$2"
    local outfile="$3"
    echo "  Synthesizing $label..."
    CLAUDECODE="" claude -p --model "$MODEL" --output-format text --tools "" \
        --system-prompt-file "$SYNTHPROMPT" < "$input_file" > "$outfile"
    echo "  Done: $label ($(wc -l < "$outfile") lines)"
}

# ============================================================
# COMBO 1: L12 alone (baseline)
# ============================================================
echo "--- COMBO 1: L12 alone (1 call) ---"
run_prism "l12" "$OUTDIR/combo1_${TARGET_NAME}.md"
echo ""

# ============================================================
# COMBO 2: L12 + contract → synthesis
# ============================================================
echo "--- COMBO 2: L12 + contract (3 calls) ---"
run_prism "l12" "$OUTDIR/raw/c2_l12_${TARGET_NAME}.md"
run_prism "contract" "$OUTDIR/raw/c2_contract_${TARGET_NAME}.md"

# Build labeled input for synthesis
cat > "$OUTDIR/raw/c2_input_${TARGET_NAME}.md" << HEREDOC
# ANALYSIS 1: L12 (Structural Depth — conservation laws, meta-laws, invariants)

$(cat "$OUTDIR/raw/c2_l12_${TARGET_NAME}.md")

---

# ANALYSIS 2: CONTRACT (Interface Violations — signature vs implementation mismatches)

$(cat "$OUTDIR/raw/c2_contract_${TARGET_NAME}.md")
HEREDOC

run_synth "combo2" "$OUTDIR/raw/c2_input_${TARGET_NAME}.md" "$OUTDIR/combo2_${TARGET_NAME}.md"
echo ""

# ============================================================
# COMBO 3: 3 orthogonal prisms (no L12)
# ============================================================
echo "--- COMBO 3: contract + degradation + scarcity (4 calls) ---"
run_prism "contract" "$OUTDIR/raw/c3_contract_${TARGET_NAME}.md"
run_prism "degradation" "$OUTDIR/raw/c3_degradation_${TARGET_NAME}.md"
run_prism "scarcity" "$OUTDIR/raw/c3_scarcity_${TARGET_NAME}.md"

cat > "$OUTDIR/raw/c3_input_${TARGET_NAME}.md" << HEREDOC
# ANALYSIS 1: CONTRACT (Interface Violations — signature vs implementation mismatches)

$(cat "$OUTDIR/raw/c3_contract_${TARGET_NAME}.md")

---

# ANALYSIS 2: DEGRADATION (Temporal Decay — what breaks without intervention)

$(cat "$OUTDIR/raw/c3_degradation_${TARGET_NAME}.md")

---

# ANALYSIS 3: SCARCITY (Resource Assumptions — what is assumed unlimited)

$(cat "$OUTDIR/raw/c3_scarcity_${TARGET_NAME}.md")
HEREDOC

run_synth "combo3" "$OUTDIR/raw/c3_input_${TARGET_NAME}.md" "$OUTDIR/combo3_${TARGET_NAME}.md"
echo ""

# ============================================================
# COMBO 4: L12 + 3 orthogonal → synthesis
# ============================================================
echo "--- COMBO 4: L12 + contract + degradation + scarcity (5 calls) ---"
run_prism "l12" "$OUTDIR/raw/c4_l12_${TARGET_NAME}.md"
run_prism "contract" "$OUTDIR/raw/c4_contract_${TARGET_NAME}.md"
run_prism "degradation" "$OUTDIR/raw/c4_degradation_${TARGET_NAME}.md"
run_prism "scarcity" "$OUTDIR/raw/c4_scarcity_${TARGET_NAME}.md"

cat > "$OUTDIR/raw/c4_input_${TARGET_NAME}.md" << HEREDOC
# ANALYSIS 1: L12 (Structural Depth — conservation laws, meta-laws, invariants)

$(cat "$OUTDIR/raw/c4_l12_${TARGET_NAME}.md")

---

# ANALYSIS 2: CONTRACT (Interface Violations — signature vs implementation mismatches)

$(cat "$OUTDIR/raw/c4_contract_${TARGET_NAME}.md")

---

# ANALYSIS 3: DEGRADATION (Temporal Decay — what breaks without intervention)

$(cat "$OUTDIR/raw/c4_degradation_${TARGET_NAME}.md")

---

# ANALYSIS 4: SCARCITY (Resource Assumptions — what is assumed unlimited)

$(cat "$OUTDIR/raw/c4_scarcity_${TARGET_NAME}.md")
HEREDOC

run_synth "combo4" "$OUTDIR/raw/c4_input_${TARGET_NAME}.md" "$OUTDIR/combo4_${TARGET_NAME}.md"
echo ""

# ============================================================
# COMBO 5: L12 + all 5 portfolio → synthesis
# ============================================================
echo "--- COMBO 5: L12 + all 5 portfolio (7 calls) ---"
run_prism "l12" "$OUTDIR/raw/c5_l12_${TARGET_NAME}.md"
run_prism "pedagogy" "$OUTDIR/raw/c5_pedagogy_${TARGET_NAME}.md"
run_prism "claim" "$OUTDIR/raw/c5_claim_${TARGET_NAME}.md"
run_prism "scarcity" "$OUTDIR/raw/c5_scarcity_${TARGET_NAME}.md"
run_prism "rejected_paths" "$OUTDIR/raw/c5_rejected_${TARGET_NAME}.md"
run_prism "degradation" "$OUTDIR/raw/c5_degradation_${TARGET_NAME}.md"

cat > "$OUTDIR/raw/c5_input_${TARGET_NAME}.md" << HEREDOC
# ANALYSIS 1: L12 (Structural Depth — conservation laws, meta-laws, invariants)

$(cat "$OUTDIR/raw/c5_l12_${TARGET_NAME}.md")

---

# ANALYSIS 2: PEDAGOGY (Pattern Transfer — what gets learned/copied and where copying breaks)

$(cat "$OUTDIR/raw/c5_pedagogy_${TARGET_NAME}.md")

---

# ANALYSIS 3: CLAIM (Empirical Assumptions — what is believed true, what breaks if false)

$(cat "$OUTDIR/raw/c5_claim_${TARGET_NAME}.md")

---

# ANALYSIS 4: SCARCITY (Resource Assumptions — what is assumed unlimited)

$(cat "$OUTDIR/raw/c5_scarcity_${TARGET_NAME}.md")

---

# ANALYSIS 5: REJECTED_PATHS (Design Decisions — fix-to-new-bug dependency chains)

$(cat "$OUTDIR/raw/c5_rejected_${TARGET_NAME}.md")

---

# ANALYSIS 6: DEGRADATION (Temporal Decay — what breaks without intervention)

$(cat "$OUTDIR/raw/c5_degradation_${TARGET_NAME}.md")
HEREDOC

run_synth "combo5" "$OUTDIR/raw/c5_input_${TARGET_NAME}.md" "$OUTDIR/combo5_${TARGET_NAME}.md"
echo ""

# ============================================================
# Summary
# ============================================================
echo "=== ALL COMBOS COMPLETE ==="
echo ""
echo "Outputs:"
echo "  Combo 1 (L12 alone):           $OUTDIR/combo1_${TARGET_NAME}.md"
echo "  Combo 2 (L12+contract):        $OUTDIR/combo2_${TARGET_NAME}.md"
echo "  Combo 3 (3 orthogonal):        $OUTDIR/combo3_${TARGET_NAME}.md"
echo "  Combo 4 (L12+3 orthogonal):    $OUTDIR/combo4_${TARGET_NAME}.md"
echo "  Combo 5 (L12+all 5 portfolio): $OUTDIR/combo5_${TARGET_NAME}.md"
echo ""
echo "Raw prism outputs in: $OUTDIR/raw/"
echo ""
echo "Rate each combo on:"
echo "  - Depth (0-10): structural insight quality"
echo "  - Bugs: concrete actionable bug count"
echo "  - Emergent: did synthesis find things NO single prism found? (Y/N)"
echo "  - Value-over-baseline: does this beat Combo 1? (Y/N/SAME)"

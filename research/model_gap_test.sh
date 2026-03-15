#!/usr/bin/env bash
# Model Gap Test Battery — F1 from ROADMAP
# Tests 9 untested operations at haiku/sonnet/opus on 2 targets
# Run on VPS: nohup bash research/model_gap_test.sh > /tmp/model_gap/run.log 2>&1 &

set -euo pipefail

OUTDIR="/tmp/model_gap"
mkdir -p "$OUTDIR"

PROFILE="$HOME/insights/profile_readme.md"
STARLETTE="$HOME/insights/research/real_code_starlette.py"
PRISM="$HOME/insights/prism.py"

MODELS=(haiku sonnet opus)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "=== MODEL GAP TEST BATTERY ==="
echo "Started: $(date)"
echo "Output: $OUTDIR"
echo ""

# Helper: run a test, capture output + timing + word count
run_test() {
    local name="$1"
    local model="$2"
    local target_label="$3"
    shift 3
    # remaining args are the command

    local outfile="$OUTDIR/${name}_${model}_${target_label}.md"
    local logfile="$OUTDIR/${name}_${model}_${target_label}.log"

    echo -n "  ${name} | ${model} | ${target_label} ... "
    local start_time=$(date +%s)

    # Run the command, capture stdout to outfile, stderr to logfile
    "$@" > "$outfile" 2> "$logfile" || true

    local end_time=$(date +%s)
    local elapsed=$((end_time - start_time))
    local words=$(wc -w < "$outfile" 2>/dev/null || echo 0)

    echo "${elapsed}s, ${words}w"
    echo "${name},${model},${target_label},${elapsed},${words}" >> "$OUTDIR/results.csv"
}

# Initialize CSV
echo "operation,model,target,seconds,words" > "$OUTDIR/results.csv"

# ============================================================
# GROUP 1: Cooked prism execution (F-G1 to F-G5)
# ============================================================

echo "--- GROUP 1: Cooked prism execution ---"

# F-G1: --scan target= (cooked prism, custom intent)
echo "F-G1: --scan target="
for m in "${MODELS[@]}"; do
    run_test "scan_target" "$m" "profile" \
        python3 "$PRISM" --scan "$PROFILE" \
        --intent "optimize this GitHub profile for founders and CTOs" \
        -m "$m" -q
done
for m in "${MODELS[@]}"; do
    run_test "scan_target" "$m" "starlette" \
        python3 "$PRISM" --scan "$STARLETTE" \
        --intent "find security vulnerabilities and trust boundary issues" \
        -m "$m" -q
done

# F-G2: --scan 3way
echo "F-G2: --scan 3way"
for m in "${MODELS[@]}"; do
    run_test "scan_3way" "$m" "profile" \
        python3 "$PRISM" --scan "$PROFILE" 3way \
        --intent "optimize for agent company decision-makers" \
        -m "$m" -q
done

# F-G3: --scan behavioral
echo "F-G3: --scan behavioral"
for m in "${MODELS[@]}"; do
    run_test "scan_behavioral" "$m" "starlette" \
        python3 "$PRISM" --scan "$STARLETTE" behavioral \
        -m "$m" -q
done

# F-G4: --solve --pipe single
echo "F-G4: --solve --pipe single"
for m in "${MODELS[@]}"; do
    run_test "solve_single" "$m" "profile" \
        bash -c "cat '$PROFILE' | python3 '$PRISM' --solve --pipe -m $m -q"
done
for m in "${MODELS[@]}"; do
    run_test "solve_single" "$m" "starlette" \
        bash -c "cat '$STARLETTE' | python3 '$PRISM' --solve --pipe -m $m -q"
done

# F-G5: --solve --pipe full
echo "F-G5: --solve --pipe full"
for m in "${MODELS[@]}"; do
    run_test "solve_full" "$m" "profile" \
        bash -c "cat '$PROFILE' | python3 '$PRISM' --solve full --pipe -m $m -q"
done

# ============================================================
# GROUP 2: Infrastructure operations (F-G6 to F-G8)
# ============================================================

echo "--- GROUP 2: Infrastructure operations ---"

# F-G6: --calibrate quick (normally haiku)
echo "F-G6: --calibrate quick"
for m in haiku sonnet; do
    run_test "calibrate_quick" "$m" "starlette" \
        bash -c "cat '$STARLETTE' | python3 '$PRISM' --calibrate --pipe -m $m -q"
done

# F-G7: --calibrate deep (normally sonnet)
echo "F-G7: --calibrate deep"
for m in sonnet opus; do
    run_test "calibrate_deep" "$m" "starlette" \
        bash -c "cat '$STARLETTE' | python3 '$PRISM' --deep-calibrate --pipe -m $m -q"
done

# F-G8: --validate (judge quality at different models)
# First generate a reference analysis to validate
echo "F-G8: --validate"
echo "  Generating reference output for validation..."
cat "$STARLETTE" | python3 "$PRISM" --solve --pipe -q > "$OUTDIR/validate_reference.md" 2>/dev/null || true

for m in haiku sonnet; do
    run_test "validate" "$m" "starlette" \
        bash -c "cat '$OUTDIR/validate_reference.md' | python3 '$PRISM' --solve --pipe --validate -m $m -q"
done

# ============================================================
# SCORING: Use haiku-as-judge on all analysis outputs
# ============================================================

echo ""
echo "--- SCORING: haiku-as-judge ---"

RUBRIC="Rate this structural analysis on a 1-10 scale. Anchors: 10=Conservation law+meta-law+15+ findings+novel insight. 9=Conservation law+findings+structural insight. 8=Multiple findings+deeper pattern. 7=Real issues+structural reasoning. 6=Surface review. 5=Generic. 3=Summary. 1=Empty. Output ONLY a single number 1-10."

echo "operation,model,target,seconds,words,score" > "$OUTDIR/scored_results.csv"

while IFS=, read -r op model target secs words; do
    [ "$op" = "operation" ] && continue  # skip header
    outfile="$OUTDIR/${op}_${model}_${target}.md"
    [ ! -f "$outfile" ] && continue

    content=$(head -c 10000 "$outfile")
    [ -z "$content" ] && score=0 && echo "  $op/$model/$target: EMPTY" && continue

    # Score with haiku-as-judge
    score=$(echo "$content" | claude -p --model haiku --tools "" "$RUBRIC" 2>/dev/null | grep -oE '[0-9]+' | head -1 || echo "0")
    echo "  $op/$model/$target: ${words}w → score=$score"
    echo "$op,$model,$target,$secs,$words,$score" >> "$OUTDIR/scored_results.csv"

done < "$OUTDIR/results.csv"

# ============================================================
# SUMMARY
# ============================================================

echo ""
echo "=== SUMMARY ==="
echo "Finished: $(date)"
echo ""
echo "SCORED RESULTS:"
echo "operation,model,target,seconds,words,score"
cat "$OUTDIR/scored_results.csv" | tail -n +2 | sort -t, -k1,1 -k3,3 -k6,6rn
echo ""
echo "Output directory: $OUTDIR"
echo "Total files: $(ls -1 $OUTDIR/*.md 2>/dev/null | wc -l)"

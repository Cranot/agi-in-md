#!/bin/bash
# Round 39: Alternative Primitive Operations
# Tests 5 alternative operations on Starlette routing.py with Haiku
# Usage: bash run_alt_ops.sh [model]
# Default model: haiku

MODEL="${1:-haiku}"
TARGET="real_code_starlette.py"
OUTDIR="output/round39_alt_ops"
mkdir -p "$OUTDIR"

OPS=("destruction" "simulation" "transplant" "miniaturize" "forgery")

echo "=== Round 39: Alternative Primitive Operations ==="
echo "Model: $MODEL | Target: $TARGET"
echo "Started: $(date)"
echo ""

for op in "${OPS[@]}"; do
    PROMPT_FILE="research/alt_ops_${op}.md"
    OUT_FILE="${OUTDIR}/haiku_${op}_starlette.md"

    if [ "$MODEL" != "haiku" ]; then
        OUT_FILE="${OUTDIR}/${MODEL}_${op}_starlette.md"
    fi

    echo "--- Running: $op ($MODEL) ---"
    START=$(date +%s)

    PROMPT_CONTENT=$(cat "$PROMPT_FILE")
    CODE_CONTENT=$(cat "$TARGET")

    COMBINED="${PROMPT_CONTENT}

---

${CODE_CONTENT}"

    claude -p "$COMBINED" --model "$MODEL" --tools "" > "$OUT_FILE" 2>/dev/null

    END=$(date +%s)
    ELAPSED=$((END - START))
    WORDS=$(wc -w < "$OUT_FILE")
    echo "  Done: ${ELAPSED}s, ${WORDS} words -> $OUT_FILE"
    echo ""
done

echo "=== All done: $(date) ==="
echo ""
echo "=== Summary ==="
for op in "${OPS[@]}"; do
    if [ "$MODEL" = "haiku" ]; then
        OUT_FILE="${OUTDIR}/haiku_${op}_starlette.md"
    else
        OUT_FILE="${OUTDIR}/${MODEL}_${op}_starlette.md"
    fi
    WORDS=$(wc -w < "$OUT_FILE" 2>/dev/null || echo "0")
    echo "  $op: ${WORDS} words"
done

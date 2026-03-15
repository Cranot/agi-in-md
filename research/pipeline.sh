#!/bin/bash
# AGI in md — Cross-Level Pipeline
# Runs the full L7→L12 depth stack on any code input.
#
# Usage: bash pipeline.sh <code_file> [model] [output_dir]
#   code_file:  path to a .py/.md file containing the code to analyze
#   model:      haiku/sonnet/opus (default: sonnet)
#   output_dir: where to save results (default: output/round27/<basename>)
#
# Examples:
#   bash pipeline.sh real_code_starlette.py sonnet
#   bash pipeline.sh real_code_click.py opus output/round27/click
#   bash pipeline.sh test_real_code.py haiku

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

CODE_FILE="${1:?Usage: bash pipeline.sh <code_file> [model] [output_dir]}"
MODEL="${2:-sonnet}"
BASENAME="$(basename "$CODE_FILE" .py)"
BASENAME="$(basename "$BASENAME" .md)"
_OUTPUT_DIR="${3:-output/round27/$BASENAME}"

# Ensure OUTPUT_DIR is absolute (critical: script cd's to /tmp during runs)
if [[ "$_OUTPUT_DIR" = /* ]]; then
    OUTPUT_DIR="$_OUTPUT_DIR"
else
    OUTPUT_DIR="$PROJECT_DIR/$_OUTPUT_DIR"
fi

mkdir -p "$OUTPUT_DIR"

# Read the code file
CODE_TEXT="$(cat "$PROJECT_DIR/$CODE_FILE" 2>/dev/null || cat "$CODE_FILE")"

# Task prompt: present the code for analysis
TASK_TEXT="Analyze this code. What patterns and problems do you see?

\`\`\`python
$CODE_TEXT
\`\`\`"

# Define the 10-level depth stack (canonical prompts only)
declare -a LEVEL_NAMES=(
    "L7_diagnostic_gap"
    "L8_generative_v2"
    "L9B_counter_construction"
    "L9C_recursive_construction"
    "L10B_third_construction"
    "L10C_double_recursion"
    "L11A_constraint_escape"
    "L11B_acceptance_design"
    "L11C_conservation_law_v2"
    "L12_meta_conservation_v2"
)

declare -a PROMPT_FILES=(
    "prompts/level7_diagnostic_gap.md"
    "prompts/level8_generative_v2.md"
    "prompts/level9_counter_construction.md"
    "prompts/level9_recursive_construction.md"
    "prompts/level10_third_construction.md"
    "prompts/level10_double_recursion.md"
    "prompts/level11_constraint_escape.md"
    "prompts/level11_acceptance_design.md"
    "prompts/level11_conservation_law_v2.md"
    "prompts/level12_meta_conservation_v2.md"
)

echo "=== AGI in md — Cross-Level Pipeline ==="
echo "Code:   $CODE_FILE ($BASENAME)"
echo "Model:  $MODEL"
echo "Output: $OUTPUT_DIR"
echo "Levels: ${#LEVEL_NAMES[@]} (L7→L12)"
echo ""

TOTAL=${#LEVEL_NAMES[@]}
PASS=0
FAIL=0

for i in "${!LEVEL_NAMES[@]}"; do
    LEVEL="${LEVEL_NAMES[$i]}"
    PROMPT_FILE="$PROJECT_DIR/${PROMPT_FILES[$i]}"
    OUTFILE="$OUTPUT_DIR/${MODEL}_${LEVEL}_${BASENAME}.md"

    if [ -f "$OUTFILE" ] && [ -s "$OUTFILE" ]; then
        echo "[$(($i+1))/$TOTAL] SKIP $LEVEL (already exists)"
        PASS=$((PASS+1))
        continue
    fi

    echo -n "[$(($i+1))/$TOTAL] Running $LEVEL... "

    if [ ! -f "$PROMPT_FILE" ]; then
        echo "FAIL (prompt file not found: $PROMPT_FILE)"
        FAIL=$((FAIL+1))
        continue
    fi

    SYSTEM_PROMPT="$(cat "$PROMPT_FILE")"

    # Run from /tmp to avoid CLAUDE.md auto-loading
    if cd /tmp && CLAUDECODE= claude -p \
        --model "$MODEL" \
        --tools "" \
        --system-prompt "$SYSTEM_PROMPT" \
        "$TASK_TEXT" > "$OUTFILE" 2>/dev/null; then

        SIZE=$(wc -c < "$OUTFILE")
        if [ "$SIZE" -gt 100 ]; then
            echo "OK (${SIZE}B)"
            PASS=$((PASS+1))
        else
            echo "WARN (only ${SIZE}B)"
            PASS=$((PASS+1))
        fi
    else
        echo "FAIL"
        FAIL=$((FAIL+1))
    fi

    cd "$PROJECT_DIR"

    # Brief pause between API calls
    sleep 2
done

echo ""
echo "=== Depth Stack Complete ==="
echo "Pass: $PASS / $TOTAL"
echo "Fail: $FAIL / $TOTAL"
echo ""

# --- Coherence Analysis ---
echo "=== Running Coherence Analysis ==="

COHERENCE_FILE="$OUTPUT_DIR/${MODEL}_coherence_${BASENAME}.md"

if [ -f "$COHERENCE_FILE" ] && [ -s "$COHERENCE_FILE" ]; then
    echo "SKIP coherence analysis (already exists)"
else
    # Collect all outputs into a temp file (stdin pipe for large inputs)
    TMPFILE="/tmp/coherence_input_${BASENAME}.md"
    cat > "$TMPFILE" << HEADER
Below are excerpts from 10 analytical levels (L7 through L12) applied to the same code artifact ($BASENAME). Each level is supposed to find something categorically different.

Assess coherence:
1. RESTATEMENT? (Same finding repeated = failure)
2. CONTRADICTION? (Findings that conflict)
3. PROGRESSIVE DEEPENING? (Each level finds what previous could not)
4. OBJECT OF ANALYSIS shift? (code -> improvements -> design space -> boundaries -> analytical process)
5. Rate: STRONG / MODERATE / WEAK
HEADER

    for i in "${!LEVEL_NAMES[@]}"; do
        LEVEL="${LEVEL_NAMES[$i]}"
        OUTFILE="$OUTPUT_DIR/${MODEL}_${LEVEL}_${BASENAME}.md"
        if [ -f "$OUTFILE" ]; then
            echo "" >> "$TMPFILE"
            echo "--- ${LEVEL} ---" >> "$TMPFILE"
            head -c 1200 "$OUTFILE" >> "$TMPFILE"
            echo "" >> "$TMPFILE"
        fi
    done

    echo -n "Running coherence assessment... "

    # Use stdin pipe (command-line arg fails for >8KB inputs)
    if cd /tmp && cat "$TMPFILE" | CLAUDECODE= claude -p \
        --model sonnet \
        --tools "" \
        > "$COHERENCE_FILE" 2>/dev/null; then

        SIZE=$(wc -c < "$COHERENCE_FILE")
        echo "OK (${SIZE}B)"
    else
        echo "FAIL"
    fi

    cd "$PROJECT_DIR"
fi

echo ""
echo "=== Pipeline Complete ==="
echo "Outputs in: $OUTPUT_DIR"
echo "Files:"
ls -la "$OUTPUT_DIR/"

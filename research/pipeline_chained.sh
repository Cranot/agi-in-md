#!/bin/bash
# AGI in md — Chained Cross-Level Pipeline
# Runs the full L7→L12 depth stack with output chaining: each level
# receives the previous level's output so it can build on specific
# findings rather than independently re-deriving the dominant pattern.
#
# Usage: bash pipeline_chained.sh <code_file> [model] [output_dir]
#   code_file:  path to a .py/.md file containing the code to analyze
#   model:      haiku/sonnet/opus (default: sonnet)
#   output_dir: where to save results (default: output/round27_chained/<basename>)
#
# Examples:
#   bash pipeline_chained.sh real_code_starlette.py sonnet
#   bash pipeline_chained.sh real_code_click.py opus
#   bash pipeline_chained.sh real_code_tenacity.py haiku

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

CODE_FILE="${1:?Usage: bash pipeline_chained.sh <code_file> [model] [output_dir]}"
MODEL="${2:-sonnet}"
BASENAME="$(basename "$CODE_FILE" .py)"
BASENAME="$(basename "$BASENAME" .md)"
_OUTPUT_DIR="${3:-output/round27_chained/$BASENAME}"

# Ensure OUTPUT_DIR is absolute (critical: script cd's to /tmp during runs)
if [[ "$_OUTPUT_DIR" = /* ]]; then
    OUTPUT_DIR="$_OUTPUT_DIR"
else
    OUTPUT_DIR="$PROJECT_DIR/$_OUTPUT_DIR"
fi

mkdir -p "$OUTPUT_DIR"

# Read the code file
CODE_TEXT="$(cat "$PROJECT_DIR/$CODE_FILE" 2>/dev/null || cat "$CODE_FILE")"

# Base task prompt (used for L7, the root level with no parent)
BASE_TASK="Analyze this code. What patterns and problems do you see?

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

# Parent index mapping (derivation tree from CLAUDE.md):
#   L7  → no parent (-1)
#   L8  → L7 (0)
#   L9-B → L8 (1)
#   L9-C → L8 (1)
#   L10-B → L9-B (2)
#   L10-C → L9-C (3)
#   L11-A → L10-C (5)
#   L11-B → L10-B (4)
#   L11-C → L10-C (5)
#   L12  → L11-C (8)
declare -a PARENT_IDX=(-1 0 1 1 2 3 5 4 5 8)

# Human-readable parent level names for the chaining prompt
declare -a PARENT_LABELS=(
    ""
    "L7 Diagnostic Gap"
    "L8 Generative Diagnostic"
    "L8 Generative Diagnostic"
    "L9-B Counter-Construction"
    "L9-C Recursive Construction"
    "L10-C Double Recursion"
    "L10-B Third Construction"
    "L10-C Double Recursion"
    "L11-C Conservation Law"
)

echo "=== AGI in md — Chained Cross-Level Pipeline ==="
echo "Code:   $CODE_FILE ($BASENAME)"
echo "Model:  $MODEL"
echo "Output: $OUTPUT_DIR"
echo "Levels: ${#LEVEL_NAMES[@]} (L7→L12, chained)"
echo ""

TOTAL=${#LEVEL_NAMES[@]}
PASS=0
FAIL=0

# Store output file paths for parent lookups
declare -a OUTFILES=()

for i in "${!LEVEL_NAMES[@]}"; do
    LEVEL="${LEVEL_NAMES[$i]}"
    PROMPT_FILE="$PROJECT_DIR/${PROMPT_FILES[$i]}"
    OUTFILE="$OUTPUT_DIR/${MODEL}_${LEVEL}_${BASENAME}.md"
    OUTFILES+=("$OUTFILE")

    if [ -f "$OUTFILE" ] && [ -s "$OUTFILE" ]; then
        echo "[$(($i+1))/$TOTAL] SKIP $LEVEL (already exists)"
        PASS=$((PASS+1))
        continue
    fi

    echo -n "[$(($i+1))/$TOTAL] Running $LEVEL"

    if [ ! -f "$PROMPT_FILE" ]; then
        echo " FAIL (prompt file not found: $PROMPT_FILE)"
        FAIL=$((FAIL+1))
        continue
    fi

    SYSTEM_PROMPT="$(cat "$PROMPT_FILE")"
    PIDX=${PARENT_IDX[$i]}

    # Build the user message
    TMPINPUT="/tmp/chained_input_${BASENAME}_${LEVEL}.md"

    if [ "$PIDX" -eq -1 ]; then
        # Root level (L7): no parent, standard task prompt
        echo -n " (root)... "
        echo "$BASE_TASK" > "$TMPINPUT"
    else
        # Chained level: prepend parent output
        PARENT_FILE="${OUTFILES[$PIDX]}"
        PARENT_LABEL="${PARENT_LABELS[$i]}"
        echo -n " (parent: ${PARENT_LABEL})... "

        if [ ! -f "$PARENT_FILE" ] || [ ! -s "$PARENT_FILE" ]; then
            echo "FAIL (parent output missing: $PARENT_FILE)"
            FAIL=$((FAIL+1))
            continue
        fi

        PARENT_OUTPUT="$(cat "$PARENT_FILE")"

        cat > "$TMPINPUT" << CHAINEOF
A previous analytical level produced this analysis of the code below.
DO NOT repeat or restate these findings. Build on them — find what
this analysis could not.

Previous analysis (${PARENT_LABEL}):
${PARENT_OUTPUT}

---

Now analyze this code:

\`\`\`python
${CODE_TEXT}
\`\`\`
CHAINEOF
    fi

    # Run from /tmp to avoid CLAUDE.md auto-loading
    # Use stdin pipe for large inputs (parent output can be 4KB+)
    if cd /tmp && cat "$TMPINPUT" | CLAUDECODE= claude -p \
        --model "$MODEL" \
        --tools "" \
        --system-prompt "$SYSTEM_PROMPT" \
        > "$OUTFILE" 2>/dev/null; then

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

    # Clean up temp input
    rm -f "$TMPINPUT"

    # Brief pause between API calls
    sleep 2
done

echo ""
echo "=== Chained Depth Stack Complete ==="
echo "Pass: $PASS / $TOTAL"
echo "Fail: $FAIL / $TOTAL"
echo ""

# --- Coherence Analysis ---
echo "=== Running Coherence Analysis ==="

COHERENCE_FILE="$OUTPUT_DIR/${MODEL}_coherence_chained_${BASENAME}.md"

if [ -f "$COHERENCE_FILE" ] && [ -s "$COHERENCE_FILE" ]; then
    echo "SKIP coherence analysis (already exists)"
else
    # Collect all outputs into a temp file (stdin pipe for large inputs)
    TMPFILE="/tmp/coherence_chained_input_${BASENAME}.md"
    cat > "$TMPFILE" << HEADER
Below are excerpts from 10 analytical levels (L7 through L12) applied to the same code artifact ($BASENAME). Each level received the output of its parent level in the derivation tree (chained execution).

The derivation tree is:
  L7 → L8 → L9-B → L10-B → L11-B
                              L8 → L9-C → L10-C → L11-A
                                                 → L11-C → L12

Assess coherence:
1. RESTATEMENT? (Same finding repeated = failure. Especially: does chaining prevent the restatement seen in independent execution?)
2. CONTRADICTION? (Findings that conflict)
3. PROGRESSIVE DEEPENING? (Each level builds on its parent's specific finding, not re-deriving independently)
4. OBJECT OF ANALYSIS shift? (code -> improvements -> design space -> boundaries -> analytical process)
5. PARENT REFERENCE? (Does each level explicitly engage with its parent's output?)
6. Rate: STRONG / MODERATE / WEAK
7. Compare to independent execution: would these same findings have been produced without chaining?
HEADER

    for i in "${!LEVEL_NAMES[@]}"; do
        LEVEL="${LEVEL_NAMES[$i]}"
        OUTFILE="${OUTFILES[$i]}"
        PIDX=${PARENT_IDX[$i]}
        if [ "$PIDX" -eq -1 ]; then
            CHAIN_NOTE="(root — no parent)"
        else
            CHAIN_NOTE="(parent: ${PARENT_LABELS[$i]})"
        fi
        if [ -f "$OUTFILE" ]; then
            echo "" >> "$TMPFILE"
            echo "--- ${LEVEL} ${CHAIN_NOTE} ---" >> "$TMPFILE"
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
echo "=== Chained Pipeline Complete ==="
echo "Outputs in: $OUTPUT_DIR"
echo "Files:"
ls -la "$OUTPUT_DIR/"

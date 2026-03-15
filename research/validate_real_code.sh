#!/bin/bash
# Test portfolio prisms on real production code (Starlette routing.py)
# Also run vanilla Sonnet and Opus for head-to-head comparison
# Usage: bash research/validate_real_code.sh

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT_DIR="$PROJECT_DIR/output/round28_validation"
PRISMS_DIR="$PROJECT_DIR/prisms"
CODE_FILE="$PROJECT_DIR/research/real_code_starlette.py"

export CLAUDECODE=""

TASK_PREFIX="Analyze this production code from Starlette's routing module. What patterns and problems do you see?"

# Build the full task: prefix + code
TASK="$TASK_PREFIX

\`\`\`python
$(cat "$CODE_FILE")
\`\`\`"

run_prism() {
    local prism_name="$1"
    local prism_file="$PRISMS_DIR/${prism_name}.md"
    local outfile="$OUTPUT_DIR/haiku_${prism_name}_starlette.md"

    echo "Starting Haiku + $prism_name..."
    echo "$TASK" | claude -p \
        --model haiku \
        --system-prompt "$(cat "$prism_file")" \
        > "$outfile" 2>/dev/null
    echo "Done: Haiku + $prism_name ($(wc -c < "$outfile") bytes)"
}

run_vanilla() {
    local model="$1"
    local outfile="$OUTPUT_DIR/${model}_vanilla_starlette.md"

    echo "Starting $model vanilla..."
    echo "$TASK" | claude -p \
        --model "$model" \
        > "$outfile" 2>/dev/null
    echo "Done: $model vanilla ($(wc -c < "$outfile") bytes)"
}

# Run all 7 in parallel
run_prism "pedagogy" &
run_prism "claim" &
run_prism "scarcity" &
run_prism "rejected_paths" &
run_prism "degradation" &
run_vanilla "sonnet" &
run_vanilla "opus" &

wait
echo ""
echo "All 7 runs complete."
echo "Output in: $OUTPUT_DIR/"
ls -la "$OUTPUT_DIR/"*starlette*

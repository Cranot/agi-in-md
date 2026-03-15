#!/bin/bash
# Phase 40: New experiments from Phase 39 insights
# Three experiment groups: F5 (compression × capacity), D11+ (L9-D replication), F3 (depth grades)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="$PROJECT_DIR/output/round26"
mkdir -p "$OUTPUT_DIR"

# Source task texts from run.sh (lines 24-604 are variable definitions)
eval "$(sed -n '24,604p' "$SCRIPT_DIR/run.sh")"

# Prompt paths
L11CV2="$PROJECT_DIR/prompts/level11_conservation_law_v2.md"
L11CV2_COMP_A="$PROJECT_DIR/prompts/level11_conservation_law_v2_compressed_A.md"
L11CV2_COMP_C="$PROJECT_DIR/prompts/level11_conservation_law_v2_compressed_C.md"
L9D="$PROJECT_DIR/prompts/level9_combined_BC.md"

echo "=== F5: Compression x Capacity ==="
echo "Testing L11-C compressed prompts on Opus and Haiku (Sonnet already tested)"

# F5-1: Opus on compressed A (175w) - task F
echo "F5-1: Opus L11Cv2 compA task F..."
cd /tmp && CLAUDECODE= claude -p --model claude-opus-4-6 --output-format text --tools "" \
  --system-prompt "$(cat "$L11CV2_COMP_A")" \
  "$TASK_F" > "$OUTPUT_DIR/opus_L11Cv2_compA_task_F.md" 2>/dev/null
echo "  Done."

# F5-2: Opus on compressed C (73w) - task F
echo "F5-2: Opus L11Cv2 compC task F..."
cd /tmp && CLAUDECODE= claude -p --model claude-opus-4-6 --output-format text --tools "" \
  --system-prompt "$(cat "$L11CV2_COMP_C")" \
  "$TASK_F" > "$OUTPUT_DIR/opus_L11Cv2_compC_task_F.md" 2>/dev/null
echo "  Done."

# F5-3: Haiku on compressed A (175w) - task F
echo "F5-3: Haiku L11Cv2 compA task F..."
cd /tmp && CLAUDECODE= claude -p --model claude-haiku-4-5-20251001 --output-format text --tools "" \
  --system-prompt "$(cat "$L11CV2_COMP_A")" \
  "$TASK_F" > "$OUTPUT_DIR/haiku_L11Cv2_compA_task_F.md" 2>/dev/null
echo "  Done."

# F5-4: Haiku on compressed C (73w) - task F
echo "F5-4: Haiku L11Cv2 compC task F..."
cd /tmp && CLAUDECODE= claude -p --model claude-haiku-4-5-20251001 --output-format text --tools "" \
  --system-prompt "$(cat "$L11CV2_COMP_C")" \
  "$TASK_F" > "$OUTPUT_DIR/haiku_L11Cv2_compC_task_F.md" 2>/dev/null
echo "  Done."

echo ""
echo "=== D11+: L9-D Replication ==="
echo "Testing combined B+C on 3 new tasks (I, D1, D5)"

# D11-1: Sonnet L9-D on task I (state machine)
echo "D11-1: Sonnet L9D task I..."
cd /tmp && CLAUDECODE= claude -p --model claude-sonnet-4-6 --output-format text --tools "" \
  --system-prompt "$(cat "$L9D")" \
  "$TASK_I" > "$OUTPUT_DIR/sonnet_L9_combined_BC_task_I.md" 2>/dev/null
echo "  Done."

# D11-2: Sonnet L9-D on task D1 (legal)
echo "D11-2: Sonnet L9D task D1..."
cd /tmp && CLAUDECODE= claude -p --model claude-sonnet-4-6 --output-format text --tools "" \
  --system-prompt "$(cat "$L9D")" \
  "$TASK_D1" > "$OUTPUT_DIR/sonnet_L9_combined_BC_task_D1.md" 2>/dev/null
echo "  Done."

# D11-3: Sonnet L9-D on task D5 (fiction)
echo "D11-3: Sonnet L9D task D5..."
cd /tmp && CLAUDECODE= claude -p --model claude-sonnet-4-6 --output-format text --tools "" \
  --system-prompt "$(cat "$L9D")" \
  "$TASK_D5" > "$OUTPUT_DIR/sonnet_L9_combined_BC_task_D5.md" 2>/dev/null
echo "  Done."

echo ""
echo "=== All experiments complete ==="
echo "Output files in $OUTPUT_DIR"
ls -la "$OUTPUT_DIR"/opus_L11Cv2_comp* "$OUTPUT_DIR"/haiku_L11Cv2_comp* "$OUTPUT_DIR"/sonnet_L9_combined_BC_task_I* "$OUTPUT_DIR"/sonnet_L9_combined_BC_task_D1* "$OUTPUT_DIR"/sonnet_L9_combined_BC_task_D5* 2>/dev/null

#!/bin/bash
cd ~/insights
mkdir -p /tmp/frontier

echo "=== FRONTIER THEORY TESTS ==="

# FT-1: K22 Active vs Passive inference test
# L7 (description/passive) vs L8 (construction/active) on same target
echo "--- FT-1: Active vs passive inference ---"
# L7-style passive description prompt
PASSIVE="Describe the structure of this code. What patterns does it use? What are its main components? Classify its design approach."
# L8-style active construction prompt
ACTIVE="Name three properties this code claims. Now BUILD an improvement that would fix the biggest structural weakness. Prove your improvement recreates the original problem at a deeper level. What does this construction reveal that description missed?"

passive_out=$(cat research/real_code_starlette.py | CLAUDECODE= claude -p --model haiku --tools "" --output-format text --system-prompt "$PASSIVE" 2>/dev/null)
active_out=$(cat research/real_code_starlette.py | CLAUDECODE= claude -p --model haiku --tools "" --output-format text --system-prompt "$ACTIVE" 2>/dev/null)
echo "FT-1: passive(L7)=$(echo "$passive_out" | wc -w)w, active(L8)=$(echo "$active_out" | wc -w)w"
echo "$passive_out" > /tmp/frontier/ft1_passive.md
echo "$active_out" > /tmp/frontier/ft1_active.md

# FT-2: K23 Satisficing threshold measurement
# Run vanilla with increasing specificity demands
echo "--- FT-2: Satisficing thresholds ---"
# Level 0: no constraint
v0=$(cat research/real_code_starlette.py | CLAUDECODE= claude -p --model sonnet --tools "" --output-format text --system-prompt "Review this code." 2>/dev/null)
echo "FT-2 L0 (no constraint): $(echo "$v0" | wc -w)w"

# Level 1: structural requirement
v1=$(cat research/real_code_starlette.py | CLAUDECODE= claude -p --model sonnet --tools "" --output-format text --system-prompt "Find structural patterns in this code. Go beyond surface-level observations." 2>/dev/null)
echo "FT-2 L1 (structural): $(echo "$v1" | wc -w)w"

# Level 2: conservation law requirement
v2=$(cat research/real_code_starlette.py | CLAUDECODE= claude -p --model sonnet --tools "" --output-format text --system-prompt "Find the conservation law in this code — which two desirable properties trade off against each other? Prove they cannot coexist." 2>/dev/null)
echo "FT-2 L2 (conservation): $(echo "$v2" | wc -w)w"

echo "FT-2 DONE"

# FT-3: K24 Costly signal test — can a judge detect L12 structure without being told?
echo "--- FT-3: Blind structure detection ---"
BLIND="The text below is a code analysis. WITHOUT being told the methodology, identify: (1) Does it contain a conservation law or impossibility proof? (2) Does it contain a self-referential diagnostic (analysis of its own analysis)? (3) Does it classify defects as structural vs fixable? (4) Does it contain confabulated API/class names not present in the code? Rate each 0-1. Output: conservation,reflexive,classification,confabulation"

# Test on L12 output
l12_blind=$(cat /tmp/gap_detect/l12_starlette.md | CLAUDECODE= claude -p --model haiku --tools "" --output-format text --system-prompt "$BLIND" 2>/dev/null | head -1)
echo "FT-3 L12: $l12_blind"

# Test on vanilla
vanilla_blind=$(cat /tmp/tier1/pc4_vanilla.md 2>/dev/null | CLAUDECODE= claude -p --model haiku --tools "" --output-format text --system-prompt "$BLIND" 2>/dev/null | head -1)
echo "FT-3 vanilla: $vanilla_blind"

# Test on L12-G
l12g_blind=$(cat /tmp/l12g_test.md | CLAUDECODE= claude -p --model haiku --tools "" --output-format text --system-prompt "$BLIND" 2>/dev/null | head -1)
echo "FT-3 L12-G: $l12g_blind"

echo "FT-3 DONE"

echo "=== FRONTIER TESTS COMPLETE ==="

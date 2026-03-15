#!/bin/bash
cd ~/insights

RUBRIC="Rate this structural analysis 1-10. 10=conservation law+meta-law+findings. 7=real issues+structural. 5=generic. 3=summary. 1=empty. Output ONLY a number."

echo "=== K15a: Quantity flouting at 5 compression levels ==="

# 50w minimal
P50="Name three properties this code claims. Prove they cannot coexist. Name the conservation law."
out=$(cat research/real_code_starlette.py | CLAUDECODE= claude -p --model sonnet --tools "" --output-format text --system-prompt "$P50" 2>/dev/null)
echo "$out" > /tmp/k_tests/k15a_50w.md
s=$(echo "$out" | head -c 8000 | CLAUDECODE= claude -p --model haiku --tools "" --output-format text --system-prompt "$RUBRIC" 2>/dev/null | tr -d "[:space:]" | grep -oE "^[0-9]+$" | head -1)
echo "K15a: 50w prompt, $(echo "$out" | wc -w)w output, score=${s:-0}"

# 73w = l12_universal
out=$(cat research/real_code_starlette.py | CLAUDECODE= claude -p --model sonnet --tools "" --output-format text --system-prompt-file prisms/l12_universal.md 2>/dev/null)
echo "$out" > /tmp/k_tests/k15a_73w.md
s=$(echo "$out" | head -c 8000 | CLAUDECODE= claude -p --model haiku --tools "" --output-format text --system-prompt "$RUBRIC" 2>/dev/null | tr -d "[:space:]" | grep -oE "^[0-9]+$" | head -1)
echo "K15a: 73w prompt, $(echo "$out" | wc -w)w output, score=${s:-0}"

# 332w = standard L12
out=$(cat research/real_code_starlette.py | CLAUDECODE= claude -p --model sonnet --tools "" --output-format text --system-prompt-file prisms/l12.md 2>/dev/null)
echo "$out" > /tmp/k_tests/k15a_332w.md
s=$(echo "$out" | head -c 8000 | CLAUDECODE= claude -p --model haiku --tools "" --output-format text --system-prompt "$RUBRIC" 2>/dev/null | tr -d "[:space:]" | grep -oE "^[0-9]+$" | head -1)
echo "K15a: 332w prompt, $(echo "$out" | wc -w)w output, score=${s:-0}"

# 817w = L12-G (gap-aware)
out=$(cat research/real_code_starlette.py | CLAUDECODE= claude -p --model sonnet --tools "" --output-format text --system-prompt-file prisms/l12g.md 2>/dev/null)
echo "$out" > /tmp/k_tests/k15a_l12g.md
s=$(echo "$out" | head -c 8000 | CLAUDECODE= claude -p --model haiku --tools "" --output-format text --system-prompt "$RUBRIC" 2>/dev/null | tr -d "[:space:]" | grep -oE "^[0-9]+$" | head -1)
echo "K15a: L12-G prompt, $(echo "$out" | wc -w)w output, score=${s:-0}"

echo "=== K15a DONE ==="

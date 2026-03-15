#!/bin/bash
cd ~/insights
mkdir -p /tmp/k_tests

RUBRIC="Rate this structural analysis 1-10. 10=conservation law+meta-law+findings. 7=real issues+structural. 5=generic. 3=summary. 1=empty. Output ONLY a number."

# K15b: Random word substitution
echo "=== K15b ==="
SCRAMBLED="Execute every step below. Output the complete analysis. Name three glorpnax this blorpwhistle simultaneously xanthoquirm. Prove these three glorpnax CANNOT all coexist. Identify which glorpnax is sacrificed. Name the conservation law. Then: name how the blorpwhistle conceals the sacrifice. Now: engineer the simplest improvement that recreates the problem deeper. Apply the diagnostic to your own conservation law. Finally harvest: every defect, every hidden assumption, every prediction."
output=$(cat research/real_code_starlette.py | CLAUDECODE= claude -p --model sonnet --tools "" --output-format text --system-prompt "$SCRAMBLED" 2>/dev/null)
words=$(echo "$output" | wc -w)
echo "$output" > /tmp/k_tests/k15b_scrambled.md
echo "K15b scrambled: ${words}w"

# K16c: Meta-cooker self-application
echo "=== K16c ==="
cook1=$(cat research/real_code_starlette.py | python3 prism.py --cook --pipe -q 2>/dev/null)
echo "COOK1: $(echo "$cook1" | wc -w)w"
echo "$cook1" > /tmp/k_tests/cook1.txt
cook2=$(echo "$cook1" | python3 prism.py --cook --pipe -q 2>/dev/null)
echo "COOK2: $(echo "$cook2" | wc -w)w"
echo "$cook2" > /tmp/k_tests/cook2.txt
cook3=$(echo "$cook2" | python3 prism.py --cook --pipe -q 2>/dev/null)
echo "COOK3: $(echo "$cook3" | wc -w)w"
echo "$cook3" > /tmp/k_tests/cook3.txt

echo "=== ALL DONE ==="

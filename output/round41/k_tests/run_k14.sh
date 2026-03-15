#!/bin/bash
cd ~/insights

MEASURE="For the analysis below, count: (1) Total distinct claims. (2) SPECIFIC claims with exact API names, class names, function names, line numbers, or numeric metrics. (3) ABSTRACT structural observations without specific names. (4) Claims VERIFIABLE from source code alone. (5) Claims requiring EXTERNAL knowledge. Output ONLY 5 numbers comma-separated."

# K14a: S*V across 3 models
echo "=== K14a ==="
for model in haiku sonnet opus; do
    cat research/real_code_starlette.py | CLAUDECODE= claude -p --model $model --tools "" --output-format text --system-prompt-file prisms/l12.md > /tmp/k_tests/l12_${model}.md 2>/dev/null
    counts=$(cat /tmp/k_tests/l12_${model}.md | CLAUDECODE= claude -p --model haiku --tools "" --output-format text --system-prompt "$MEASURE" 2>/dev/null | tr -d "[:space:]" | head -1)
    words=$(wc -w < /tmp/k_tests/l12_${model}.md)
    echo "K14a: $model ${words}w counts=$counts"
done

echo "=== K14a DONE ==="

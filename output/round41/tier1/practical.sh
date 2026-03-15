#!/bin/bash
cd ~/insights

echo "=== PRACTICAL TRANSLATION TESTS ==="

# PT-1: Auto-confidence annotation (can we estimate confidence from claim specificity without extra API call?)
echo "--- PT-1: Specificity-based confidence estimation ---"
# Take L12 output, ask model to annotate ONLY based on claim type (no verification)
CONF_PROMPT="For each claim in the analysis below, append one of these tags based ONLY on the claim type (do NOT verify the claim):
[HIGH-CONF] = structural observation derivable from source (patterns, control flow, architecture)
[MED-CONF] = derived conclusion requiring reasoning (conservation laws, impossibility proofs)
[LOW-CONF] = specific factual claim (API names, line numbers, performance metrics)
[UNVERIFIED] = claim about external world (best practices, deprecation status, design intent)
Output the analysis with tags appended to each claim."
out=$(cat /tmp/gap_detect/l12_starlette.md | CLAUDECODE= claude -p --model haiku --tools "" --output-format text --system-prompt "$CONF_PROMPT" 2>/dev/null)
echo "$out" > /tmp/tier1/pt1_confidence.md
high=$(echo "$out" | grep -c "HIGH-CONF" || echo 0)
med=$(echo "$out" | grep -c "MED-CONF" || echo 0)
low=$(echo "$out" | grep -c "LOW-CONF" || echo 0)
unv=$(echo "$out" | grep -c "UNVERIFIED" || echo 0)
echo "PT-1: HIGH=$high MED=$med LOW=$low UNVERIFIED=$unv total=$(echo "$out" | wc -w)w"

# PT-2: Minimal format prism (just structure, no domain words at all)
echo "--- PT-2: Pure format prism (no domain words) ---"
FORMAT_ONLY="Execute all steps. Output complete analysis.

Step 1: Name three. Prove incompatible. Which sacrificed. Name the law: A times B equals constant.

Step 2: Name how input conceals the sacrifice. What mechanism?

Step 3: Engineer simplest fix. Prove fix recreates original problem deeper.

Step 4: Apply to own law. What does analysis conceal?

Step 5: Harvest every defect with location and severity."
out=$(cat research/real_code_starlette.py | CLAUDECODE= claude -p --model sonnet --tools "" --output-format text --system-prompt "$FORMAT_ONLY" 2>/dev/null)
echo "$out" > /tmp/tier1/pt2_format_only.md
echo "PT-2: $(echo "$out" | wc -w)w"

# PT-3: Aspiration level control test
echo "--- PT-3: Aspiration levels ---"
# Shallow
out_s=$(cat research/real_code_starlette.py | CLAUDECODE= claude -p --model sonnet --tools "" --output-format text --system-prompt "List the 5 most important structural findings about this code." 2>/dev/null)
echo "PT-3 shallow: $(echo "$out_s" | wc -w)w"

# Deep (L12-G = standard deep)
# Already have this data

# Exhaustive = verified pipeline (already tested)

echo "=== PRACTICAL TESTS DONE ==="

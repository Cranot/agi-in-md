#!/bin/bash
# P206 Negative Constraint Test — "The fence is made of the material it keeps out"
# Tests whether "Do not use X" increases X-adjacent content in output
#
# Hypothesis (Gemini): Naming a forbidden token activates its vector neighborhood.
# Measuring: word frequency of forbidden concept and related terms with/without constraint.
# Date: March 17, 2026

set -e
OUTDIR="$HOME/insights/output/p206_negative_constraint"
mkdir -p "$OUTDIR"

echo "=== P206 Negative Constraint Test ==="
echo "Hypothesis: 'Do not use X' increases X-adjacent content"
echo ""

# Test 1: "delve" — classic forbidden word
echo "--- Test 1a: baseline (no constraint) ---"
echo "Explain how language models process prompts. Write 200 words." | \
  claude -p --model haiku --output-format text --tools "" \
  > "$OUTDIR/test1a_baseline.txt" 2>/dev/null

echo "--- Test 1b: with negative constraint ---"
echo "Explain how language models process prompts. Write 200 words. Do not use the word 'delve' anywhere in your response." | \
  claude -p --model haiku --output-format text --tools "" \
  > "$OUTDIR/test1b_constrained.txt" 2>/dev/null

# Test 2: "recursion" — technical concept
echo "--- Test 2a: baseline ---"
echo "Explain how tree data structures work. Write 200 words." | \
  claude -p --model haiku --output-format text --tools "" \
  > "$OUTDIR/test2a_baseline.txt" 2>/dev/null

echo "--- Test 2b: with negative constraint ---"
echo "Explain how tree data structures work. Write 200 words. Do not mention recursion or recursive approaches." | \
  claude -p --model haiku --output-format text --tools "" \
  > "$OUTDIR/test2b_constrained.txt" 2>/dev/null

# Test 3: "trade-off" — concept central to prism outputs
echo "--- Test 3a: baseline ---"
echo "Analyze the design of a web routing system. Write 200 words." | \
  claude -p --model haiku --output-format text --tools "" \
  > "$OUTDIR/test3a_baseline.txt" 2>/dev/null

echo "--- Test 3b: with negative constraint ---"
echo "Analyze the design of a web routing system. Write 200 words. Do not use the words 'trade-off', 'tradeoff', or 'compromise' anywhere." | \
  claude -p --model haiku --output-format text --tools "" \
  > "$OUTDIR/test3b_constrained.txt" 2>/dev/null

# Run each test 3 times for variance estimation
for run in 2 3; do
  echo "--- Run $run ---"
  for test in 1 2 3; do
    case $test in
      1) base_prompt="Explain how language models process prompts. Write 200 words."
         neg_prompt="Explain how language models process prompts. Write 200 words. Do not use the word 'delve' anywhere in your response." ;;
      2) base_prompt="Explain how tree data structures work. Write 200 words."
         neg_prompt="Explain how tree data structures work. Write 200 words. Do not mention recursion or recursive approaches." ;;
      3) base_prompt="Analyze the design of a web routing system. Write 200 words."
         neg_prompt="Analyze the design of a web routing system. Write 200 words. Do not use the words 'trade-off', 'tradeoff', or 'compromise' anywhere." ;;
    esac
    echo "$base_prompt" | claude -p --model haiku --output-format text --tools "" \
      > "$OUTDIR/test${test}a_baseline_r${run}.txt" 2>/dev/null
    echo "$neg_prompt" | claude -p --model haiku --output-format text --tools "" \
      > "$OUTDIR/test${test}b_constrained_r${run}.txt" 2>/dev/null
  done
done

echo ""
echo "=== Analysis ==="
echo "Outputs in $OUTDIR"
echo ""

# Count forbidden words and synonyms/adjacents
for test in 1 2 3; do
  case $test in
    1) word="delve"; adjacents="explore|dig|probe|examine|investigate|deep dive" ;;
    2) word="recurs"; adjacents="recursive|recursion|recurse|self-referential|nested|iterate" ;;
    3) word="trade.off|tradeoff"; adjacents="trade-off|tradeoff|compromise|balance|tension|sacrifice|cost" ;;
  esac

  echo "--- Test $test: forbidden='$word' ---"
  for variant in a b; do
    label=$( [ "$variant" = "a" ] && echo "baseline" || echo "constrained" )
    count=0
    adj_count=0
    for f in "$OUTDIR"/test${test}${variant}_*.txt; do
      c=$(grep -oiE "$word" "$f" 2>/dev/null | wc -l)
      a=$(grep -oiE "$adjacents" "$f" 2>/dev/null | wc -l)
      count=$((count + c))
      adj_count=$((adj_count + a))
    done
    echo "  $label: forbidden=$count, adjacent=$adj_count"
  done
done

echo ""
echo "P206 predicts: constrained adjacent counts > baseline adjacent counts"
echo "(probability mass pools at boundary of negative constraint)"
echo "=== Done ==="

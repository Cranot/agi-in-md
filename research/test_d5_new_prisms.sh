#!/bin/bash
# D5: Test new Round 42 prisms on Click + Tenacity
# Prisms: history, genesis, emergence, counterfactual
# Targets: Click core.py (417 lines), Tenacity retry.py (331 lines)
# Date: March 17, 2026

set -e
OUTDIR="$HOME/insights/output/d5_new_prisms"
mkdir -p "$OUTDIR"

echo "=== D5: New Prisms on Click + Tenacity ==="
echo "4 prisms x 2 targets = 8 experiments"
echo ""

for prism in history genesis emergence counterfactual; do
  for target in real_code_click real_code_tenacity; do
    short=$(echo $target | sed 's/real_code_//')
    outfile="$OUTDIR/${prism}_${short}.md"
    echo "--- Running $prism on $short ---"
    cat "$HOME/insights/research/${target}.py" | \
      claude -p --model sonnet --output-format text --tools "" \
      --system-prompt-file "$HOME/insights/prisms/${prism}.md" \
      > "$outfile" 2>/dev/null
    wc -w "$outfile" | awk '{print "  Output: " $1 " words"}'
  done
done

echo ""
echo "=== Results ==="
for f in "$OUTDIR"/*.md; do
  name=$(basename "$f" .md)
  words=$(wc -w < "$f")
  has_law=$(grep -c -i "conservation\|conserved\|constant\|invariant" "$f" 2>/dev/null || echo 0)
  echo "  $name: ${words}w, conservation_markers=$has_law"
done

echo ""
echo "=== Done ==="

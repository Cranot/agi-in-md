#!/bin/bash
# Batch 4: New L8 ops (archaeology, cultivation) + L9 escalation (simulation, miniaturize)
# 6 experiments: 2 hand-crafted L8 + 2 cooked L8 + 2 L9 escalation
# All on Haiku, Starlette target

cd ~/insights
CODE="research/real_code_starlette.py"
OUTDIR="output/round39_alt_ops"
mkdir -p "$OUTDIR"

echo "=== BATCH 4A: Hand-crafted L8 (Haiku) ==="

# 1. Archaeology — hand-crafted
echo "Launching archaeology (hand-crafted)..."
(cat research/alt_ops_archaeology.md; echo ""; echo "---"; echo ""; cat "$CODE") | \
  claude -p --model haiku --tools "" -o output.txt 2>/dev/null > "$OUTDIR/haiku_archaeology_starlette.md" &

# 2. Cultivation — hand-crafted
echo "Launching cultivation (hand-crafted)..."
(cat research/alt_ops_cultivation.md; echo ""; echo "---"; echo ""; cat "$CODE") | \
  claude -p --model haiku --tools "" -o output.txt 2>/dev/null > "$OUTDIR/haiku_cultivation_starlette.md" &

wait
echo "Hand-crafted L8 done:"
echo "  archaeology: $(wc -w < "$OUTDIR/haiku_archaeology_starlette.md") words"
echo "  cultivation: $(wc -w < "$OUTDIR/haiku_cultivation_starlette.md") words"

echo ""
echo "=== BATCH 4B: Cooked L8 (Haiku cook+solve via prism.py) ==="

# 3. Archaeology — cooked
echo "Launching archaeology (cooked)..."
python3 prism.py --solve research/real_code_starlette.py \
  --target="excavate through geological layers to find what's foundational vs accumulated sediment" \
  -m haiku --tools "" 2>/dev/null > "$OUTDIR/cooked_archaeology_starlette.md" &

# 4. Cultivation — cooked
echo "Launching cultivation (cooked)..."
python3 prism.py --solve research/real_code_starlette.py \
  --target="plant new requirements as seeds and trace what grows, resists, and dies to find structural rigidity" \
  -m haiku --tools "" 2>/dev/null > "$OUTDIR/cooked_cultivation_starlette.md" &

wait
echo "Cooked L8 done:"
echo "  archaeology: $(wc -w < "$OUTDIR/cooked_archaeology_starlette.md") words"
echo "  cultivation: $(wc -w < "$OUTDIR/cooked_cultivation_starlette.md") words"

echo ""
echo "=== BATCH 4C: L9 Escalation (Haiku) ==="

# 5. L9 Simulation — takes L8 simulation output as input
echo "Launching L9 simulation..."
(cat research/alt_ops_l9_simulation.md; echo ""; echo "---"; echo ""; echo "# PRIOR ANALYSIS (L8 Temporal Simulation of Starlette routing.py)"; echo ""; cat "$OUTDIR/haiku_simulation_starlette.md") | \
  claude -p --model haiku --tools "" -o output.txt 2>/dev/null > "$OUTDIR/haiku_l9_simulation_starlette.md" &

# 6. L9 Miniaturize — takes L8 miniaturize output as input
echo "Launching L9 miniaturize..."
(cat research/alt_ops_l9_miniaturize.md; echo ""; echo "---"; echo ""; echo "# PRIOR ANALYSIS (L8 Miniaturization of Starlette routing.py)"; echo ""; cat "$OUTDIR/haiku_miniaturize_starlette.md") | \
  claude -p --model haiku --tools "" -o output.txt 2>/dev/null > "$OUTDIR/haiku_l9_miniaturize_starlette.md" &

wait
echo "L9 Escalation done:"
echo "  l9_simulation: $(wc -w < "$OUTDIR/haiku_l9_simulation_starlette.md") words"
echo "  l9_miniaturize: $(wc -w < "$OUTDIR/haiku_l9_miniaturize_starlette.md") words"

echo ""
echo "=== ALL 6 DONE ==="
echo "  archaeology (hand):  $(wc -w < "$OUTDIR/haiku_archaeology_starlette.md") words"
echo "  cultivation (hand):  $(wc -w < "$OUTDIR/haiku_cultivation_starlette.md") words"
echo "  archaeology (cook):  $(wc -w < "$OUTDIR/cooked_archaeology_starlette.md") words"
echo "  cultivation (cook):  $(wc -w < "$OUTDIR/cooked_cultivation_starlette.md") words"
echo "  l9_simulation:       $(wc -w < "$OUTDIR/haiku_l9_simulation_starlette.md") words"
echo "  l9_miniaturize:      $(wc -w < "$OUTDIR/haiku_l9_miniaturize_starlette.md") words"

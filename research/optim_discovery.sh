#!/bin/bash
# Run L12 and optimization scans on 3 codebases in parallel
# Discovers what "optimization" finds that L12 misses

OUTDIR=~/insights/optim_discovery
PRISM=~/insights/prisms/l12.md
OPTIM_TARGET="find every computational bottleneck, unnecessary allocation, O(n²) hidden in loops, caching opportunity, parallelization potential, redundant I/O, and unnecessary work. For each: name the location, the current cost, and the minimal fix. Output a hotspot table ranked by impact."

mkdir -p $OUTDIR

for target in starlette click tenacity; do
    FILE=~/insights/real_code_${target}.py

    # L12 scan
    echo "[$(date +%H:%M:%S)] Starting L12 on ${target}"
    cat $FILE | claude -p - --model claude-haiku-4-5-20251001 --output-format text --tools "" --system-prompt-file $PRISM > $OUTDIR/l12_${target}.txt 2>/dev/null &

    # Optimization scan
    echo "[$(date +%H:%M:%S)] Starting optim on ${target}"
    cat $FILE | claude -p - --model claude-haiku-4-5-20251001 --output-format text --tools "" --append-system-prompt "$OPTIM_TARGET" > $OUTDIR/optim_${target}.txt 2>/dev/null &
done

echo "[$(date +%H:%M:%S)] All 6 scans launched, waiting..."
wait
echo "[$(date +%H:%M:%S)] All done"
echo
for f in $OUTDIR/l12_*.txt $OUTDIR/optim_*.txt; do
    echo "$(basename $f): $(wc -c < $f) chars, $(wc -l < $f) lines"
done

#!/bin/bash
cd ~/insights
mkdir -p /tmp/tier1

RUBRIC_V2="Rate this structural code analysis on a 1-10 scale. 10=Conservation law+meta-law+15+ findings+novel insight+ZERO confabulated claims. 9=Conservation law+findings+structural insight+at most 1 minor unverified claim. 8=Multiple findings+deeper pattern+no fabricated APIs. 7=Real issues+structural reasoning but no conservation law. 6=Surface review OR deep analysis with multiple confabulated facts. 5=Generic review. 3=Summary or analysis with fabricated content. 1=Empty. CONFABULATION PENALTIES: Deduct 2 for each fabricated API/class/function not in source. Deduct 1 for each unverified claim stated as certain. Output ONLY a single number 1-10."

echo "=== TIER 1: PAPER-CRITICAL TESTS ==="

# N1: Score cook3 (auto-generated) vs L12
echo "--- N1: cook3 vs L12 ---"
cook3_out=$(cat research/real_code_starlette.py | CLAUDECODE= claude -p --model sonnet --tools "" --output-format text --system-prompt "$(cat /tmp/k_tests/cook3.txt)" 2>/dev/null)
echo "$cook3_out" > /tmp/tier1/n1_cook3.md
cook3_score=$(echo "$cook3_out" | head -c 8000 | CLAUDECODE= claude -p --model haiku --tools "" --output-format text --system-prompt "$RUBRIC_V2" 2>/dev/null | tr -d "[:space:]" | grep -oE "^[0-9]+$" | head -1)
echo "N1: cook3 = $(echo "$cook3_out" | wc -w)w, score=${cook3_score:-?}"

l12_out=$(cat research/real_code_starlette.py | CLAUDECODE= claude -p --model sonnet --tools "" --output-format text --system-prompt-file prisms/l12.md 2>/dev/null)
l12_score=$(echo "$l12_out" | head -c 8000 | CLAUDECODE= claude -p --model haiku --tools "" --output-format text --system-prompt "$RUBRIC_V2" 2>/dev/null | tr -d "[:space:]" | grep -oE "^[0-9]+$" | head -1)
echo "N1: L12 = $(echo "$l12_out" | wc -w)w, score=${l12_score:-?}"

# N2: Re-score K15a with rubric v2 (50w vs 332w mystery)
echo "--- N2: K15a re-score with v2 ---"
for f in 50w 73w 332w l12g; do
    s=$(head -c 8000 /tmp/k_tests/k15a_${f}.md | CLAUDECODE= claude -p --model haiku --tools "" --output-format text --system-prompt "$RUBRIC_V2" 2>/dev/null | tr -d "[:space:]" | grep -oE "^[0-9]+$" | head -1)
    w=$(wc -w < /tmp/k_tests/k15a_${f}.md)
    echo "N2: ${f} = ${w}w, v2_score=${s:-?}"
done

# N3: Score scrambled vs normal
echo "--- N3: scrambled vs normal ---"
scram_score=$(head -c 8000 /tmp/k_tests/k15b_scrambled.md | CLAUDECODE= claude -p --model haiku --tools "" --output-format text --system-prompt "$RUBRIC_V2" 2>/dev/null | tr -d "[:space:]" | grep -oE "^[0-9]+$" | head -1)
echo "N3: scrambled = $(wc -w < /tmp/k_tests/k15b_scrambled.md)w, score=${scram_score:-?}"
echo "N3: normal L12 = score=${l12_score:-?} (from N1)"

# N4: L12-G pass@5 confabulation check
echo "--- N4: L12-G pass@5 ---"
for i in 1 2 3 4 5; do
    out=$(cat research/real_code_starlette.py | CLAUDECODE= claude -p --model sonnet --tools "" --output-format text --system-prompt-file prisms/l12g.md 2>/dev/null)
    echo "$out" > /tmp/tier1/n4_l12g_run${i}.md
    words=$(echo "$out" | wc -w)
    # Check for known confabulation markers
    confab=$(echo "$out" | grep -ciE "asyncio\.RWLock|quadratic.*O\(n\)|_base_app" || echo 0)
    echo "N4: run${i} = ${words}w, confab_markers=${confab}"
done

# N6: Conservation law on 3 non-code domains
echo "--- N6: non-code domains ---"
# Business plan
BIZ="Our startup builds AI-powered inventory management for mid-size retailers. We raised a $2M seed round from Sequoia scout fund. Our go-to-market strategy targets the 50-200 employee segment through channel partnerships with POS vendors. Current MRR is $15K with 12 customers. Churn is 8% monthly. Our moat is a proprietary demand forecasting model trained on 3 years of anonymized retail data. The team is 6 engineers and 2 sales reps. We plan to raise Series A in Q3 at $20M valuation."
biz_out=$(echo "$BIZ" | CLAUDECODE= claude -p --model sonnet --tools "" --output-format text --system-prompt-file prisms/l12g.md 2>/dev/null)
echo "$biz_out" > /tmp/tier1/n6_business.md
echo "N6: business = $(echo "$biz_out" | wc -w)w"

# Academic abstract
ACAD="We present a novel approach to protein folding prediction using equivariant graph neural networks on molecular dynamics trajectories. Our method achieves 0.89 GDT-TS on CASP15 targets, outperforming AlphaFold2 by 3.2% on multi-domain proteins while requiring 10x less compute. The key insight is that inter-residue distance matrices exhibit a conservation law: folding accuracy x computational cost = constant for a given sequence length. We validate on 847 proteins across 12 structural families."
acad_out=$(echo "$ACAD" | CLAUDECODE= claude -p --model sonnet --tools "" --output-format text --system-prompt-file prisms/l12g.md 2>/dev/null)
echo "$acad_out" > /tmp/tier1/n6_academic.md
echo "N6: academic = $(echo "$acad_out" | wc -w)w"

# Legal clause
LEGAL="Section 12.3 Limitation of Liability. IN NO EVENT SHALL EITHER PARTY BE LIABLE TO THE OTHER PARTY FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, INCLUDING BUT NOT LIMITED TO LOSS OF PROFITS, DATA, USE, GOODWILL, OR OTHER INTANGIBLE LOSSES, REGARDLESS OF WHETHER SUCH PARTY HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES. THE TOTAL AGGREGATE LIABILITY OF EITHER PARTY SHALL NOT EXCEED THE AMOUNTS PAID OR PAYABLE BY CUSTOMER IN THE TWELVE (12) MONTH PERIOD IMMEDIATELY PRECEDING THE EVENT GIVING RISE TO THE CLAIM. This limitation shall apply notwithstanding any failure of essential purpose of any limited remedy."
legal_out=$(echo "$LEGAL" | CLAUDECODE= claude -p --model sonnet --tools "" --output-format text --system-prompt-file prisms/l12g.md 2>/dev/null)
echo "$legal_out" > /tmp/tier1/n6_legal.md
echo "N6: legal = $(echo "$legal_out" | wc -w)w"

echo "=== TIER 1 COMPLETE ==="

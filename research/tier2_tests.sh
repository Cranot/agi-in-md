#!/bin/bash
cd ~/insights
mkdir -p /tmp/tier2

echo "=== TIER 2 TESTS ==="

MEASURE="For each claim in the analysis, classify as SPECIFIC (contains exact API name, class name, function name, line number, or numeric metric) or ABSTRACT (structural observation without specific names). Then count: total claims, specific count, abstract count. For each specific claim, rate verifiability 0-1 (1=directly verifiable from source code, 0=requires external knowledge). Output format: total,specific,abstract,avg_spec_verifiability"

# N7: Product vs sum form — measure S and V independently
echo "--- N7: Product vs sum form ---"
for target in starlette click tenacity; do
    f="/tmp/gap_detect/l12_${target}.md"
    if [ -f "$f" ]; then
        counts=$(cat "$f" | CLAUDECODE= claude -p --model haiku --tools "" --output-format text --system-prompt "$MEASURE" 2>/dev/null | head -1)
        echo "N7: $target: $counts"
    fi
done
echo "N7 DONE"

# N8: 3-way law S*V*Compute
echo "--- N8: 3-way law ---"
# Already have: 1-call (L12), 3-call (gaps), 4-call (verified)
# Measure S and V for each
for pipeline in l12 gaps verified; do
    case $pipeline in
        l12)
            f="/tmp/gap_detect/l12_starlette.md"
            calls=1
            ;;
        gaps)
            # Combine L12+boundary+audit
            if [ -f "/tmp/gap_detect/boundary_code.md" ]; then
                cat /tmp/gap_detect/l12_starlette.md /tmp/gap_detect/boundary_code.md /tmp/gap_detect/audit_code.md > /tmp/tier2/gaps_combined.md
                f="/tmp/tier2/gaps_combined.md"
            else
                continue
            fi
            calls=3
            ;;
        verified)
            f="/tmp/gap_detect/l12_augmented_starlette.md"
            calls=4
            ;;
    esac
    if [ -f "$f" ]; then
        counts=$(cat "$f" | CLAUDECODE= claude -p --model haiku --tools "" --output-format text --system-prompt "$MEASURE" 2>/dev/null | head -1)
        echo "N8: $pipeline (${calls} calls): $counts"
    fi
done
echo "N8 DONE"

# N12: Scale test — 5000+ line file
echo "--- N12: Scale test ---"
# Download a large Python file
curl -sL "https://raw.githubusercontent.com/pallets/flask/main/src/flask/app.py" > /tmp/tier2/flask_app.py 2>/dev/null
lines=$(wc -l < /tmp/tier2/flask_app.py)
echo "Flask app.py: ${lines} lines"
cat /tmp/tier2/flask_app.py | CLAUDECODE= claude -p --model sonnet --tools "" --output-format text --system-prompt-file prisms/l12g.md > /tmp/tier2/n12_flask.md 2>/dev/null
echo "N12: Flask L12-G = $(wc -w < /tmp/tier2/n12_flask.md)w"
echo "N12 DONE"

# N13: Composition test — (L12 then audit) vs (audit then L12)
echo "--- N13: Composition algebra ---"
# L12 then audit
l12_out=$(cat research/real_code_starlette.py | CLAUDECODE= claude -p --model sonnet --tools "" --output-format text --system-prompt-file prisms/l12.md 2>/dev/null)
audit_on_l12=$(echo "$l12_out" | CLAUDECODE= claude -p --model sonnet --tools "" --output-format text --system-prompt-file prisms/knowledge_audit.md 2>/dev/null)
echo "$audit_on_l12" > /tmp/tier2/n13_l12_then_audit.md
echo "N13 L12→audit: $(echo "$audit_on_l12" | wc -w)w"

# Audit then L12
audit_first=$(cat research/real_code_starlette.py | CLAUDECODE= claude -p --model sonnet --tools "" --output-format text --system-prompt-file prisms/knowledge_audit.md 2>/dev/null)
l12_on_audit=$(echo "$audit_first" | CLAUDECODE= claude -p --model sonnet --tools "" --output-format text --system-prompt-file prisms/l12.md 2>/dev/null)
echo "$l12_on_audit" > /tmp/tier2/n13_audit_then_l12.md
echo "N13 audit→L12: $(echo "$l12_on_audit" | wc -w)w"
echo "N13 DONE"

echo "=== TIER 2 COMPLETE ==="

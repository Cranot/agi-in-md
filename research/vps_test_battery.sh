#!/bin/bash
# ============================================================================
# VPS TEST BATTERY — Comprehensive validation for all unexplored territories
# Created: Mar 14, 2026
# Run from VPS: ~/insights/
#
# Usage:
#   bash research/vps_test_battery.sh BATCH_NAME
#   e.g.: bash research/vps_test_battery.sh P1   (cross-target new prisms)
#         bash research/vps_test_battery.sh ALL  (everything — expensive!)
#
# Each batch can be run independently. Results go to output/vps_validation/
# ============================================================================

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PRISM_DIR="$PROJECT_DIR/prisms"
OUTDIR="$PROJECT_DIR/output/vps_validation"
RESEARCH_DIR="$PROJECT_DIR/research"
mkdir -p "$OUTDIR"

BATCH="${1:-help}"

# ── Targets ──────────────────────────────────────────────────────────────────
STARLETTE="$RESEARCH_DIR/real_code_starlette.py"
CLICK="$RESEARCH_DIR/real_code_click.py"
TENACITY="$RESEARCH_DIR/real_code_tenacity.py"

# ── Large targets (downloaded on first use) ──────────────────────────────────
LARGE_DIR="$RESEARCH_DIR/large_targets"
mkdir -p "$LARGE_DIR"

download_large_targets() {
    echo "=== Downloading 1000+ line targets ==="
    # Flask app.py (~2300 lines, BSD-3-Clause)
    if [ ! -f "$LARGE_DIR/flask_app.py" ]; then
        curl -sL "https://raw.githubusercontent.com/pallets/flask/main/src/flask/app.py" \
            > "$LARGE_DIR/flask_app.py"
        echo "Downloaded flask_app.py ($(wc -l < "$LARGE_DIR/flask_app.py") lines)"
    fi
    # Rich console.py (~2600 lines, MIT)
    if [ ! -f "$LARGE_DIR/rich_console.py" ]; then
        curl -sL "https://raw.githubusercontent.com/Textualize/rich/master/rich/console.py" \
            > "$LARGE_DIR/rich_console.py"
        echo "Downloaded rich_console.py ($(wc -l < "$LARGE_DIR/rich_console.py") lines)"
    fi
    # Requests models.py (~1000 lines, Apache-2.0)
    if [ ! -f "$LARGE_DIR/requests_models.py" ]; then
        curl -sL "https://raw.githubusercontent.com/psf/requests/main/src/requests/models.py" \
            > "$LARGE_DIR/requests_models.py"
        echo "Downloaded requests_models.py ($(wc -l < "$LARGE_DIR/requests_models.py") lines)"
    fi
}

# ── Non-code test inputs ─────────────────────────────────────────────────────
LEGAL_TEXT="A software license agreement grants the licensee a non-exclusive, non-transferable right to use the software. The licensor retains all intellectual property rights. The agreement may be terminated if the licensee breaches any terms. Upon termination, all copies must be destroyed. The licensor provides no warranty, express or implied, including merchantability or fitness for a particular purpose. Liability is limited to the amount paid for the license. This agreement is governed by the laws of the State of Delaware. Any disputes shall be resolved through binding arbitration. The agreement constitutes the entire understanding between the parties and supersedes all prior negotiations. Modifications must be in writing and signed by both parties. The licensee may not assign this agreement without prior written consent. Force majeure excuses performance. Severability: if any provision is unenforceable, the remainder stays in effect. Notices must be sent to the addresses specified in Exhibit A. Confidential information disclosed during the term remains protected for 5 years after termination."

BUSINESS_TEXT='Our SaaS platform serves 50,000 SMBs with a freemium model. Free tier: 3 users, 1GB storage, basic analytics. Pro tier ($29/mo): 10 users, 50GB, advanced analytics, API access. Enterprise ($199/mo): unlimited users, 1TB, SSO, dedicated support, SLA. Current metrics: 50K free, 3K Pro, 200 Enterprise. MRR: $127K. Churn: Free 8%/mo, Pro 3%/mo, Enterprise 0.5%/mo. CAC: $45 (paid), $0 (organic/viral). LTV: Free $0, Pro $580, Enterprise $47,800. We are considering: (A) raising Pro to $39, (B) adding a $99 mid-tier, (C) removing free tier entirely, (D) usage-based pricing. Board wants path to $500K MRR in 12 months. Current growth: 15% MoM on Pro, 5% MoM on Enterprise. Main competitors price at $49 (mid) and $299 (enterprise). Our NPS: Free 32, Pro 58, Enterprise 71.'

PHILOSOPHY_TEXT='Consider the Chinese Room argument: a person inside a room follows instructions in English to manipulate Chinese symbols. To outside observers, the room appears to understand Chinese. But the person inside understands nothing — they just follow syntactic rules without semantic comprehension. Searle argues this shows that computation alone cannot produce understanding. Strong AI claims that an appropriately programmed computer literally understands. The Chinese Room is designed to refute this. Key objections: (1) Systems Reply — the person does not understand, but the whole system might. Searle: I memorize the rules; still no understanding. (2) Robot Reply — connect the room to sensors and actuators. Searle: Still just symbols, no intentionality. (3) Brain Simulator Reply — what if the program simulates a Chinese brain neuron by neuron? Searle: Simulating digestion does not digest anything. (4) Other Minds Reply — how do you know other people understand? Searle: I know I understand English by introspection, and I know the room does not by construction. Does the argument prove too much? If no computation can understand, what about the brain? The brain is a biological machine — is it computational? Searle distinguishes syntax from semantics, causal powers from formal properties. But modern LLMs produce outputs that seem to demonstrate understanding. Has the Chinese Room been empirically refuted, or does it still stand?'

# ── Helper: run a single prism test ──────────────────────────────────────────
run_test() {
    local prism="$1"    # prism name (e.g., "simulation")
    local target="$2"   # target file path
    local model="$3"    # haiku/sonnet/opus
    local outfile="$4"  # output file path
    local label="$5"    # display label

    if [ -f "$outfile" ] && [ -s "$outfile" ]; then
        echo "  SKIP $label (exists: $(wc -w < "$outfile")w)"
        return 0
    fi

    local start=$SECONDS
    cd /tmp
    cat "$target" | CLAUDECODE= claude -p \
        --model "$model" \
        --tools "" \
        --output-format text \
        --system-prompt-file "$PRISM_DIR/${prism}.md" \
        > "$outfile" 2>/dev/null || true
    local elapsed=$(( SECONDS - start ))
    local words=$(wc -w < "$outfile" 2>/dev/null || echo 0)
    echo "  DONE $label: ${words}w, ${elapsed}s"
    cd "$PROJECT_DIR"
}

# ── Helper: run prism on inline text ─────────────────────────────────────────
run_test_text() {
    local prism="$1"
    local text="$2"
    local model="$3"
    local outfile="$4"
    local label="$5"

    if [ -f "$outfile" ] && [ -s "$outfile" ]; then
        echo "  SKIP $label (exists: $(wc -w < "$outfile")w)"
        return 0
    fi

    local start=$SECONDS
    cd /tmp
    echo "$text" | CLAUDECODE= claude -p \
        --model "$model" \
        --tools "" \
        --output-format text \
        --system-prompt-file "$PRISM_DIR/${prism}.md" \
        > "$outfile" 2>/dev/null || true
    local elapsed=$(( SECONDS - start ))
    local words=$(wc -w < "$outfile" 2>/dev/null || echo 0)
    echo "  DONE $label: ${words}w, ${elapsed}s"
    cd "$PROJECT_DIR"
}

# ── Helper: run prism.py scan ────────────────────────────────────────────────
run_scan() {
    local target="$1"   # file path
    local mode="$2"     # single/full/3way/behavioral
    local model="$3"    # haiku/sonnet/opus
    local outfile="$4"  # output file
    local label="$5"

    if [ -f "$outfile" ] && [ -s "$outfile" ]; then
        echo "  SKIP $label (exists: $(wc -w < "$outfile")w)"
        return 0
    fi

    local start=$SECONDS
    cd /tmp
    python3 "$PROJECT_DIR/prism.py" --scan "$target" $mode -m "$model" -o "$outfile" -q 2>/dev/null || true
    local elapsed=$(( SECONDS - start ))
    local words=$(wc -w < "$outfile" 2>/dev/null || echo 0)
    echo "  DONE $label: ${words}w, ${elapsed}s"
    cd "$PROJECT_DIR"
}

# ── Helper: run prism.py solve on text ───────────────────────────────────────
run_solve() {
    local text="$1"
    local mode="$2"     # single/full
    local model="$3"
    local outfile="$4"
    local label="$5"

    if [ -f "$outfile" ] && [ -s "$outfile" ]; then
        echo "  SKIP $label (exists: $(wc -w < "$outfile")w)"
        return 0
    fi

    local start=$SECONDS
    cd /tmp
    echo "$text" | python3 "$PROJECT_DIR/prism.py" --solve $mode --pipe -m "$model" -o "$outfile" -q 2>/dev/null || true
    local elapsed=$(( SECONDS - start ))
    local words=$(wc -w < "$outfile" 2>/dev/null || echo 0)
    echo "  DONE $label: ${words}w, ${elapsed}s"
    cd "$PROJECT_DIR"
}


# ============================================================================
# BATCH P1: Cross-target validation — new prisms on Click + Tenacity
# Tests: 8 | API calls: 8 | Est. cost: ~$0.40-0.80
# Proves: simulation/cultivation/archaeology/sdl_simulation work beyond Starlette
# ============================================================================
batch_P1() {
    echo "=== BATCH P1: Cross-target validation (8 tests) ==="
    local dir="$OUTDIR/P1_cross_target"
    mkdir -p "$dir"

    # simulation (Sonnet-optimal)
    run_test simulation "$CLICK"    sonnet "$dir/simulation_click.md"    "simulation × Click"
    run_test simulation "$TENACITY" sonnet "$dir/simulation_tenacity.md" "simulation × Tenacity"

    # cultivation (Sonnet-optimal)
    run_test cultivation "$CLICK"    sonnet "$dir/cultivation_click.md"    "cultivation × Click"
    run_test cultivation "$TENACITY" sonnet "$dir/cultivation_tenacity.md" "cultivation × Tenacity"

    # archaeology (Sonnet-optimal)
    run_test archaeology "$CLICK"    sonnet "$dir/archaeology_click.md"    "archaeology × Click"
    run_test archaeology "$TENACITY" sonnet "$dir/archaeology_tenacity.md" "archaeology × Tenacity"

    # sdl_simulation (Haiku-optimal)
    run_test sdl_simulation "$CLICK"    haiku "$dir/sdl_simulation_click.md"    "sdl_simulation × Click"
    run_test sdl_simulation "$TENACITY" haiku "$dir/sdl_simulation_tenacity.md" "sdl_simulation × Tenacity"

    echo "=== P1 complete. Results in $dir ==="
}


# ============================================================================
# BATCH P2: 3-cooker pipeline cross-target
# Tests: 2 | API calls: ~8 (4 per target: cook + 3 ops + synth)
# Proves: COOK_3WAY works on Click + Tenacity (validated on Starlette only)
# ============================================================================
batch_P2() {
    echo "=== BATCH P2: 3-cooker pipeline cross-target (2 tests) ==="
    local dir="$OUTDIR/P2_3way_cross_target"
    mkdir -p "$dir"

    run_scan "$CLICK"    "3way" sonnet "$dir/3way_click.md"    "3way × Click"
    run_scan "$TENACITY" "3way" sonnet "$dir/3way_tenacity.md" "3way × Tenacity"

    echo "=== P2 complete. Results in $dir ==="
}


# ============================================================================
# BATCH P3: 1000+ line codebase testing
# Tests: 9 | API calls: 9 | Est. cost: ~$0.50-1.00
# Proves: prisms scale beyond 200-400 line files
# Downloads Flask app.py (~2300L), Rich console.py (~2600L), Requests models.py (~1000L)
# ============================================================================
batch_P3() {
    echo "=== BATCH P3: 1000+ line testing (9 tests) ==="
    download_large_targets
    local dir="$OUTDIR/P3_large_codebase"
    mkdir -p "$dir"

    local FLASK="$LARGE_DIR/flask_app.py"
    local RICH="$LARGE_DIR/rich_console.py"
    local REQUESTS="$LARGE_DIR/requests_models.py"

    # L12 on all 3 large targets (core validation)
    run_test l12 "$FLASK"    sonnet "$dir/l12_flask.md"    "L12 × Flask ($(wc -l < "$FLASK")L)"
    run_test l12 "$RICH"     sonnet "$dir/l12_rich.md"     "L12 × Rich ($(wc -l < "$RICH")L)"
    run_test l12 "$REQUESTS" sonnet "$dir/l12_requests.md" "L12 × Requests ($(wc -l < "$REQUESTS")L)"

    # deep_scan SDL on all 3 (does SDL scale?)
    run_test deep_scan "$FLASK"    opus   "$dir/deep_scan_flask.md"    "deep_scan × Flask"
    run_test deep_scan "$RICH"     opus   "$dir/deep_scan_rich.md"     "deep_scan × Rich"
    run_test deep_scan "$REQUESTS" opus   "$dir/deep_scan_requests.md" "deep_scan × Requests"

    # identity on all 3 (does behavioral prism scale?)
    run_test identity "$FLASK"    sonnet "$dir/identity_flask.md"    "identity × Flask"
    run_test identity "$RICH"     sonnet "$dir/identity_rich.md"     "identity × Rich"
    run_test identity "$REQUESTS" sonnet "$dir/identity_requests.md" "identity × Requests"

    echo "=== P3 complete. Results in $dir ==="
}


# ============================================================================
# BATCH R1: True Sonnet-cooked test for alt ops
# Tests: 6 | API calls: ~12 (cook + solve each)
# Proves: Sonnet cook + Sonnet solve vs Haiku cook + Sonnet solve
# Must clear .deep/ cache first!
# ============================================================================
batch_R1() {
    echo "=== BATCH R1: True Sonnet cook test (6 tests) ==="
    local dir="$OUTDIR/R1_sonnet_cook"
    mkdir -p "$dir"

    # Clear cached lenses to force fresh cook
    echo "  Clearing .deep/ cache..."
    rm -rf "$PROJECT_DIR/.deep/lenses" "$PROJECT_DIR/.deep/prisms" 2>/dev/null || true

    # 3 alt ops × Sonnet cook + Sonnet solve (via prism.py target=)
    run_scan "$STARLETTE" 'target="temporal degradation analysis"'  sonnet "$dir/sonnet_cook_simulation.md"  "Sonnet-cook simulation"
    run_scan "$STARLETTE" 'target="structural archaeology analysis"' sonnet "$dir/sonnet_cook_archaeology.md" "Sonnet-cook archaeology"
    run_scan "$STARLETTE" 'target="perturbation response analysis"' sonnet "$dir/sonnet_cook_cultivation.md" "Sonnet-cook cultivation"

    # Same 3 with Haiku cook + Sonnet solve (force haiku cook, sonnet solve)
    rm -rf "$PROJECT_DIR/.deep/lenses" "$PROJECT_DIR/.deep/prisms" 2>/dev/null || true
    run_scan "$STARLETTE" 'target="temporal degradation analysis"'  haiku "$dir/haiku_cook_simulation.md"  "Haiku-cook simulation"
    run_scan "$STARLETTE" 'target="structural archaeology analysis"' haiku "$dir/haiku_cook_archaeology.md" "Haiku-cook archaeology"
    run_scan "$STARLETTE" 'target="perturbation response analysis"' haiku "$dir/haiku_cook_cultivation.md" "Haiku-cook cultivation"

    echo "=== R1 complete. Results in $dir ==="
}


# ============================================================================
# BATCH R2: L9 miniaturize on Sonnet
# Tests: 2 | API calls: 2
# Proves: whether Sonnet's +0.7 lift saves miniaturize (7.0 on Haiku)
# ============================================================================
batch_R2() {
    echo "=== BATCH R2: Miniaturize on Sonnet (2 tests) ==="
    local dir="$OUTDIR/R2_miniaturize"
    mkdir -p "$dir"

    # Need miniaturize prompt — create inline since no prism file exists
    local MINI_PROMPT="This code's concealment operates through miniaturization — what happens when you build the smallest possible version that preserves core behavior?

Execute every step below. Output the complete analysis.

First: identify the 3 properties this code simultaneously claims. Prove these 3 properties CANNOT all coexist at any scale. Name what was sacrificed.

Then: engineer the smallest possible version of this code that preserves its core contract. What features MUST be dropped? What stays?

Now: the miniature reveals something the full version hides. Name the conservation law: what quantity is preserved across all scales? Format: A × B = constant.

Apply the construction to its own output: miniaturize your analysis. What does YOUR miniaturization conceal? Name the meta-conservation law.

Finally collect every concrete bug (location, severity, fixable/structural)."

    # Write temp prism file
    echo "$MINI_PROMPT" > "/tmp/miniaturize_prism.md"

    cd /tmp
    # Sonnet
    local start=$SECONDS
    CLAUDECODE= claude -p --model sonnet --tools "" --output-format text \
        --system-prompt-file "/tmp/miniaturize_prism.md" \
        "$(cat "$STARLETTE")" \
        > "$dir/miniaturize_sonnet_starlette.md" 2>/dev/null || true
    echo "  DONE miniaturize×Sonnet×Starlette: $(wc -w < "$dir/miniaturize_sonnet_starlette.md")w, $(( SECONDS - start ))s"

    # Haiku (baseline comparison)
    start=$SECONDS
    CLAUDECODE= claude -p --model haiku --tools "" --output-format text \
        --system-prompt-file "/tmp/miniaturize_prism.md" \
        "$(cat "$STARLETTE")" \
        > "$dir/miniaturize_haiku_starlette.md" 2>/dev/null || true
    echo "  DONE miniaturize×Haiku×Starlette: $(wc -w < "$dir/miniaturize_haiku_starlette.md")w, $(( SECONDS - start ))s"

    cd "$PROJECT_DIR"
    echo "=== R2 complete. Results in $dir ==="
}


# ============================================================================
# BATCH R4: Non-code 3-cooker pipeline
# Tests: 3 | API calls: ~12 (4 per domain)
# Proves: 3-cooker achieves 9.5 on legal/business/philosophy (not just code)
# ============================================================================
batch_R4() {
    echo "=== BATCH R4: Non-code 3-cooker pipeline (3 tests) ==="
    local dir="$OUTDIR/R4_noncode_3way"
    mkdir -p "$dir"

    # Write text targets to temp files for prism.py
    echo "$LEGAL_TEXT" > /tmp/legal_target.txt
    echo "$BUSINESS_TEXT" > /tmp/business_target.txt
    echo "$PHILOSOPHY_TEXT" > /tmp/philosophy_target.txt

    run_solve "$LEGAL_TEXT"      "full" sonnet "$dir/3way_legal.md"      "3way × Legal"
    run_solve "$BUSINESS_TEXT"   "full" sonnet "$dir/3way_business.md"   "3way × Business"
    run_solve "$PHILOSOPHY_TEXT" "full" sonnet "$dir/3way_philosophy.md" "3way × Philosophy"

    echo "=== R4 complete. Results in $dir ==="
}


# ============================================================================
# BATCH R5: L12 on poetry/UX domains
# Tests: 4 | API calls: 4
# Proves: L12 + l12_universal work on creative domains
# ============================================================================
batch_R5() {
    echo "=== BATCH R5: L12 on poetry/UX (4 tests) ==="
    local dir="$OUTDIR/R5_creative_domains"
    mkdir -p "$dir"

    local POETRY="Do not go gentle into that good night,
Old age should burn and rave at close of day;
Rage, rage against the dying of the light.

Though wise men at their end know dark is right,
Because their words had forked no lightning they
Do not go gentle into that good night.

Good men, the last wave by, crying how bright
Their frail deeds might have danced in a green bay,
Rage, rage against the dying of the light.

Wild men who caught and sang the sun in flight,
And learn, too late, they grieved it on its way,
Do not go gentle into that good night.

Grave men, near death, who see with blinding sight
Blind eyes could blaze like meteors and be gay,
Rage, rage against the dying of the light.

And you, my father, there on the sad height,
Curse, bless, me now with your fierce tears, I pray.
Do not go gentle into that good night.
Rage, rage against the dying of the light."

    local UX_TEXT="Mobile banking app redesign for Gen Z users (18-25). Current state: 2.3-star rating, 45% abandon onboarding. Competitors: Revolut (4.7 stars), Cash App (4.7), Venmo (4.8). Our features: checking, savings, P2P transfers, bill pay, budgeting, crypto, stock trading. Pain points from user research: (1) onboarding requires SSN + ID scan + selfie + 3-day wait, (2) budgeting tool requires manual categorization, (3) P2P requires recipient's full bank details, (4) no social features, (5) dark mode is broken on Android, (6) push notifications are all-or-nothing. Our competitive advantage: FDIC-insured, no monthly fees, 4.5% savings APY. Design constraints: regulatory compliance (KYC/AML), existing backend (COBOL core, REST API layer), 6-person design team, 12-week timeline. CEO wants 'TikTok-like engagement.' Head of compliance wants 'zero regulatory risk.' Head of engineering wants 'no backend changes.' Target: 4.0+ rating, 70% onboarding completion, 3x daily active users."

    # L12 universal on poetry (Sonnet — domain-neutral)
    run_test_text l12_universal "$POETRY" sonnet "$dir/l12u_poetry.md" "l12_universal × Poetry"

    # L12 code-vocabulary on poetry (test mode trigger on creative domain)
    run_test_text l12 "$POETRY" sonnet "$dir/l12_poetry.md" "l12 × Poetry"

    # L12 universal on UX
    run_test_text l12_universal "$UX_TEXT" sonnet "$dir/l12u_ux.md" "l12_universal × UX"

    # L12 on UX (code nouns on non-code)
    run_test_text l12 "$UX_TEXT" sonnet "$dir/l12_ux.md" "l12 × UX"

    echo "=== R5 complete. Results in $dir ==="
}


# ============================================================================
# BATCH R6: Content hallucination scope
# Tests: 4 | API calls: ~8 (cook + solve each)
# Proves: how widespread is content hallucination in cooked lenses?
# ============================================================================
batch_R6() {
    echo "=== BATCH R6: Content hallucination test (4 tests) ==="
    local dir="$OUTDIR/R6_hallucination"
    mkdir -p "$dir"

    # Clear cache
    rm -rf "$PROJECT_DIR/.deep/lenses" "$PROJECT_DIR/.deep/prisms" 2>/dev/null || true

    # Cook with abstract intent on specific code — does the model hallucinate code content?
    run_scan "$STARLETTE" 'target="microservice architecture patterns"'  sonnet "$dir/halluc_abstract_starlette.md"  "abstract intent × Starlette"
    run_scan "$CLICK"     'target="database schema migration safety"'    sonnet "$dir/halluc_abstract_click.md"     "abstract intent × Click"

    # Cook with matching intent — should NOT hallucinate
    run_scan "$STARLETTE" 'target="HTTP routing security"'              sonnet "$dir/halluc_matching_starlette.md" "matching intent × Starlette"
    run_scan "$CLICK"     'target="CLI argument parsing correctness"'   sonnet "$dir/halluc_matching_click.md"    "matching intent × Click"

    echo "=== R6 complete. Compare abstract vs matching intent outputs ==="
}


# ============================================================================
# BATCH R7: Vertical composition scope
# Tests: 4 | API calls: 4
# Proves: can SDL/portfolio prisms work on L12 analysis output? (P172 says no)
# ============================================================================
batch_R7() {
    echo "=== BATCH R7: Vertical composition test (4 tests) ==="
    local dir="$OUTDIR/R7_vertical_composition"
    mkdir -p "$dir"

    # First, generate L12 output on Starlette (or use existing)
    local l12_output="$dir/l12_base_starlette.md"
    run_test l12 "$STARLETTE" sonnet "$l12_output" "L12 base × Starlette"

    # Now feed L12 output through different prisms
    if [ -f "$l12_output" ] && [ -s "$l12_output" ]; then
        run_test_text deep_scan "$(cat "$l12_output")" opus   "$dir/vertical_deep_scan.md" "deep_scan on L12 output"
        run_test_text pedagogy  "$(cat "$l12_output")" haiku  "$dir/vertical_pedagogy.md"  "pedagogy on L12 output"
        run_test_text claim     "$(cat "$l12_output")" haiku  "$dir/vertical_claim.md"     "claim on L12 output"
    else
        echo "  ERROR: L12 base output missing, cannot run vertical tests"
    fi

    echo "=== R7 complete. Check if prisms hallucinate or analyze real content ==="
}


# ============================================================================
# BATCH I1: Score 4 unscored VPS prisms
# Tests: 4 | API calls: 4
# Proves: whether data_flow/time_lifecycle/redundancy/composition_synthesis have value
# NOTE: These prisms must exist on the VPS at ~/insights/prisms/ — upload first if needed
# ============================================================================
batch_I1() {
    echo "=== BATCH I1: Score unscored prisms (4 tests) ==="
    local dir="$OUTDIR/I1_unscored_prisms"
    mkdir -p "$dir"

    # Check if prisms exist on VPS
    for p in data_flow time_lifecycle redundancy composition_synthesis; do
        if [ ! -f "$PRISM_DIR/${p}.md" ]; then
            echo "  WARNING: $PRISM_DIR/${p}.md not found — skipping"
            continue
        fi
        run_test "$p" "$STARLETTE" haiku "$dir/${p}_starlette.md" "$p × Starlette"
    done

    echo "=== I1 complete. Results in $dir ==="
}


# ============================================================================
# BATCH A1: SDL vs L12 direct comparison
# Tests: 6 | API calls: 6
# Proves: quantified comparison on same rubric, same targets
# ============================================================================
batch_A1() {
    echo "=== BATCH A1: SDL vs L12 head-to-head (6 tests) ==="
    local dir="$OUTDIR/A1_sdl_vs_l12"
    mkdir -p "$dir"

    # L12 on all 3 targets (Sonnet — its optimal)
    run_test l12       "$STARLETTE" sonnet "$dir/l12_starlette.md"       "L12 × Starlette"
    run_test l12       "$CLICK"     sonnet "$dir/l12_click.md"           "L12 × Click"
    run_test l12       "$TENACITY"  sonnet "$dir/l12_tenacity.md"        "L12 × Tenacity"

    # deep_scan on all 3 targets (Opus — its optimal)
    run_test deep_scan "$STARLETTE" opus   "$dir/deep_scan_starlette.md" "deep_scan × Starlette"
    run_test deep_scan "$CLICK"     opus   "$dir/deep_scan_click.md"     "deep_scan × Click"
    run_test deep_scan "$TENACITY"  opus   "$dir/deep_scan_tenacity.md"  "deep_scan × Tenacity"

    echo "=== A1 complete. Compare outputs with same rubric ==="
}


# ============================================================================
# BATCH A4: Error Resilience 70w cross-target
# Tests: 3 | API calls: 3
# Proves: does compressed errres (9.5 on Starlette) generalize?
# ============================================================================
batch_A4() {
    echo "=== BATCH A4: Error Resilience 70w cross-target (3 tests) ==="
    local dir="$OUTDIR/A4_errres_70w"
    mkdir -p "$dir"

    if [ ! -f "$PRISM_DIR/error_resilience_70w.md" ]; then
        echo "  ERROR: error_resilience_70w.md not found"
        return 1
    fi

    run_test error_resilience_70w "$STARLETTE" haiku "$dir/errres70w_starlette.md" "errres70w × Starlette"
    run_test error_resilience_70w "$CLICK"     haiku "$dir/errres70w_click.md"     "errres70w × Click"
    run_test error_resilience_70w "$TENACITY"  haiku "$dir/errres70w_tenacity.md"   "errres70w × Tenacity"

    echo "=== A4 complete. Results in $dir ==="
}


# ============================================================================
# BATCH FULL: Full pipeline on all 3 targets (for comparison baseline)
# Tests: 3 | API calls: ~27 (9 per target)
# Proves: baseline for comparing against 3way and other pipelines
# ============================================================================
batch_FULL() {
    echo "=== BATCH FULL: Full pipeline baseline (3 tests, 27 calls) ==="
    local dir="$OUTDIR/FULL_baseline"
    mkdir -p "$dir"

    run_scan "$STARLETTE" "full" sonnet "$dir/full_starlette.md" "Full × Starlette"
    run_scan "$CLICK"     "full" sonnet "$dir/full_click.md"     "Full × Click"
    run_scan "$TENACITY"  "full" sonnet "$dir/full_tenacity.md"  "Full × Tenacity"

    echo "=== FULL complete. Results in $dir ==="
}


# ============================================================================
# BATCH BEHAVIORAL: Behavioral pipeline on all 3 targets
# Tests: 3 | API calls: ~15 (5 per target)
# Proves: behavioral pipeline baseline scores
# ============================================================================
batch_BEHAVIORAL() {
    echo "=== BATCH BEHAVIORAL: Behavioral pipeline (3 tests, 15 calls) ==="
    local dir="$OUTDIR/BEHAVIORAL_baseline"
    mkdir -p "$dir"

    run_scan "$STARLETTE" "behavioral" sonnet "$dir/behavioral_starlette.md" "Behavioral × Starlette"
    run_scan "$CLICK"     "behavioral" sonnet "$dir/behavioral_click.md"     "Behavioral × Click"
    run_scan "$TENACITY"  "behavioral" sonnet "$dir/behavioral_tenacity.md"  "Behavioral × Tenacity"

    echo "=== BEHAVIORAL complete. Results in $dir ==="
}


# ============================================================================
# DISPATCH
# ============================================================================
case "$BATCH" in
    P1)         batch_P1 ;;
    P2)         batch_P2 ;;
    P3)         batch_P3 ;;
    R1)         batch_R1 ;;
    R2)         batch_R2 ;;
    R4)         batch_R4 ;;
    R5)         batch_R5 ;;
    R6)         batch_R6 ;;
    R7)         batch_R7 ;;
    I1)         batch_I1 ;;
    A1)         batch_A1 ;;
    A4)         batch_A4 ;;
    FULL)       batch_FULL ;;
    BEHAVIORAL) batch_BEHAVIORAL ;;
    ALL)
        batch_P1
        batch_P2
        batch_P3
        batch_R1
        batch_R2
        batch_R4
        batch_R5
        batch_R6
        batch_R7
        batch_I1
        batch_A1
        batch_A4
        ;;
    help|*)
        cat << 'HELP'
VPS Test Battery — Comprehensive validation

  BATCH    TESTS  CALLS  COST      WHAT IT PROVES
  ─────    ─────  ─────  ────      ──────────────
  P1         8      8    ~$0.50    New prisms (simulation/cultivation/archaeology/sdl_sim) on Click+Tenacity
  P2         2      8    ~$0.50    3-cooker pipeline (COOK_3WAY) on Click+Tenacity
  P3         9      9    ~$0.80    L12+deep_scan+identity on 1000+ line files (Flask/Rich/Requests)
  R1         6     12    ~$0.80    True Sonnet-cooked vs Haiku-cooked alt ops
  R2         2      2    ~$0.12    Miniaturize on Sonnet (7.0 on Haiku — does +0.7 lift save it?)
  R4         3     12    ~$0.80    3-cooker on non-code: legal, business, philosophy
  R5         4      4    ~$0.25    L12/l12_universal on poetry + UX design
  R6         4      8    ~$0.50    Content hallucination scope (abstract vs matching intent)
  R7         4      4    ~$0.25    Vertical composition (feed L12 output through other prisms)
  I1         4      4    ~$0.05    Score 4 unscored VPS prisms
  A1         6      6    ~$0.45    SDL vs L12 head-to-head on same rubric
  A4         3      3    ~$0.04    Error Resilience 70w cross-target validation
  ─────    ─────  ─────  ────
  TOTAL     55     80    ~$5.00

  FULL       3     27    ~$3.00    Full pipeline baseline (9 calls per target)
  BEHAVIORAL 3     15    ~$1.50    Behavioral pipeline baseline

  ALL = P1+P2+P3+R1+R2+R4+R5+R6+R7+I1+A1+A4 (55 tests, ~$5)

  Usage:
    bash research/vps_test_battery.sh P1        # Run one batch
    bash research/vps_test_battery.sh P1 P2 P3  # Not supported — run one at a time
    bash research/vps_test_battery.sh ALL        # Run everything

  Results: output/vps_validation/<BATCH>/
  Resume: Re-run same batch — existing outputs are skipped
HELP
        ;;
esac

echo ""
echo "Done. Results in: $OUTDIR"

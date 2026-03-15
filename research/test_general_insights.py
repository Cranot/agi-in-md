#!/usr/bin/env python3
"""Head-to-head: Opus vanilla vs Single Prism vs Full Prism on general insights.

Usage:
    python test_general_insights.py          # run all prompts
    python test_general_insights.py 1        # run prompt #1 only
    python test_general_insights.py 1 3      # run prompts #1 and #3
"""

import os
import sys
import shutil
import subprocess
import time
import pathlib

PROJ = pathlib.Path(__file__).resolve().parent.parent
PRISMS = PROJ / "prisms"

PROMPTS = {
    1: {
        "label": "Representation & Schema",
        "text": (
            "What does a todo app's data model assume about tasks that shapes what "
            "problems it can represent? Remove due dates — what work becomes invisible? "
            "What categories of human effort have no representation in any todo schema?"
        ),
    },
    2: {
        "label": "Invariant & Conservation",
        "text": (
            "Across all todo apps — different UIs, features, target users, decades of "
            "design iteration — what property of work management never changes? What is "
            "the conserved quantity that every todo app preserves, even the ones that "
            "try to break every convention?"
        ),
    },
    3: {
        "label": "Generative Mechanism",
        "text": (
            "What unintended user pattern emerges from how todos are stored and "
            "displayed? Build a version that prevents that pattern — what new problem "
            "appears? Is there a generative cycle where each fix creates the next "
            "dysfunction?"
        ),
    },
    4: {
        "label": "Design Impossibility",
        "text": (
            "What fundamental trade-off is baked into every todo app architecture? "
            "Not a preference or a design choice — a genuine impossibility where "
            "having property A structurally prevents having property B, regardless "
            "of how clever the implementation is."
        ),
    },
    5: {
        "label": "Behavioral Feedback (Cognitive Distortion)",
        "text": (
            "How does a todo app's interface reshape the user's cognition about work "
            "itself? What does making 'priority' a first-class feature teach users to "
            "believe about their own productivity? What cognitive distortions does the "
            "tool create that the user can never see from inside the tool?"
        ),
    },
}


def call_claude(model, system_prompt_file, content, label):
    """Run claude CLI and return (output, duration)."""
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    cmd = [
        shutil.which("claude") or "claude",
        "-p", "--model", model,
        "--output-format", "text",
        "--tools", "",
    ]
    if system_prompt_file:
        cmd.extend(["--system-prompt-file", str(system_prompt_file)])

    print(f"\n{'='*60}")
    print(f"  Running: {label}")
    print(f"  Model: {model}")
    print(f"  Prism: {system_prompt_file.name if system_prompt_file else 'none (vanilla)'}")
    print(f"{'='*60}")

    start = time.time()
    try:
        proc = subprocess.run(
            cmd, input=content, capture_output=True, text=True,
            encoding="utf-8", timeout=300, env=env,
        )
        duration = time.time() - start
        output = proc.stdout.strip()
        if proc.returncode != 0:
            print(f"  ERROR: {proc.stderr[:200]}")
            return None, duration

        words = len(output.split())
        print(f"  Done: {words} words, {duration:.1f}s")
        return output, duration
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT after 300s")
        return None, 300


def run_test(prompt_num, input_text, out_dir):
    """Run 3-way comparison for one prompt. Returns summary dict."""
    out_dir.mkdir(parents=True, exist_ok=True)
    results = {}

    # --- Haiku runs first (cheap) ---
    print(f"\n{'#'*60}")
    print(f"  PROMPT #{prompt_num}: Haiku runs (cheap)")
    print(f"{'#'*60}")

    # Single Prism
    prism_file = PRISMS / "l12_general.md"
    single_out, single_dur = call_claude(
        "haiku", prism_file, input_text, f"P{prompt_num} Single Prism (Haiku + L12 General)")
    if single_out:
        path = out_dir / "single_prism.md"
        path.write_text(
            f"# Single Prism\n\nInput: {input_text}\n\nPrism: l12_general.md\n\n---\n\n{single_out}\n",
            encoding="utf-8")
        print(f"  Saved: {path.name}")
    results["single"] = {"output": single_out, "duration": single_dur,
                          "words": len(single_out.split()) if single_out else 0}

    # Full Prism (3 calls)
    full_outputs = {}
    full_dur = 0

    prism1 = PRISMS / "l12_general.md"
    l12_out, dur1 = call_claude(
        "haiku", prism1, input_text, f"P{prompt_num} Full Prism — Call 1: L12 General")
    full_dur += dur1
    if l12_out:
        full_outputs["l12"] = l12_out

        prism2 = PRISMS / "l12_general_adversarial.md"
        adv_input = f"# INPUT\n\n{input_text}\n\n---\n\n# STRUCTURAL ANALYSIS (from previous pass)\n\n{l12_out}"
        adv_out, dur2 = call_claude(
            "haiku", prism2, adv_input, f"P{prompt_num} Full Prism — Call 2: Adversarial")
        full_dur += dur2
        if adv_out:
            full_outputs["adversarial"] = adv_out

            prism3 = PRISMS / "l12_general_synthesis.md"
            synth_input = (
                f"# INPUT\n\n{input_text}\n\n---\n\n"
                f"# ANALYSIS 1: STRUCTURAL ANALYSIS\n\n{l12_out}\n\n---\n\n"
                f"# ANALYSIS 2: CONTRADICTION ANALYSIS\n\n{adv_out}"
            )
            synth_out, dur3 = call_claude(
                "haiku", prism3, synth_input, f"P{prompt_num} Full Prism — Call 3: Synthesis")
            full_dur += dur3
            full_outputs["synthesis"] = synth_out or "(not completed)"

    if full_outputs:
        combined = (
            f"# Full Prism (3 calls)\n\n"
            f"Input: {input_text}\n\n---\n\n"
            f"## CALL 1: L12 STRUCTURAL\n\n{full_outputs.get('l12', '(failed)')}\n\n---\n\n"
            f"## CALL 2: ADVERSARIAL CHALLENGE\n\n{full_outputs.get('adversarial', '(failed)')}\n\n---\n\n"
            f"## CALL 3: SYNTHESIS\n\n{full_outputs.get('synthesis', '(failed)')}\n"
        )
        path = out_dir / "full_prism.md"
        path.write_text(combined, encoding="utf-8")
        print(f"  Saved: {path.name} (total: {full_dur:.1f}s)")

    full_words = sum(len(v.split()) for v in full_outputs.values()) if full_outputs else 0
    results["full"] = {"output": full_outputs, "duration": full_dur, "words": full_words}

    # --- Opus run (expensive) ---
    print(f"\n{'#'*60}")
    print(f"  PROMPT #{prompt_num}: Opus run (expensive)")
    print(f"{'#'*60}")

    opus_out, opus_dur = call_claude("opus", None, input_text, f"P{prompt_num} Opus Vanilla")
    if opus_out:
        path = out_dir / "opus_vanilla.md"
        path.write_text(
            f"# Opus Vanilla\n\nInput: {input_text}\n\n---\n\n{opus_out}\n",
            encoding="utf-8")
        print(f"  Saved: {path.name}")
    results["opus"] = {"output": opus_out, "duration": opus_dur,
                        "words": len(opus_out.split()) if opus_out else 0}

    return results


if __name__ == "__main__":
    # Parse which prompts to run
    if len(sys.argv) > 1:
        nums = [int(x) for x in sys.argv[1:] if x.isdigit() and int(x) in PROMPTS]
    else:
        nums = sorted(PROMPTS.keys())

    print(f"Running {len(nums)} prompt(s): {nums}")
    print(f"Each prompt: 1 Opus + 1 Haiku single + 3 Haiku full = 5 calls")
    print(f"Total calls: {len(nums) * 5}")

    all_results = {}
    for num in nums:
        p = PROMPTS[num]
        out_dir = PROJ / "output" / f"general_insights_p{num}"
        print(f"\n\n{'='*60}")
        print(f"  PROMPT #{num}: {p['label']}")
        print(f"  {p['text'][:80]}...")
        print(f"  Output: {out_dir}")
        print(f"{'='*60}")

        all_results[num] = run_test(num, p["text"], out_dir)

    # Grand summary
    print(f"\n\n{'='*60}")
    print(f"  GRAND SUMMARY")
    print(f"{'='*60}")
    print(f"  {'Prompt':<35} {'Opus':>12} {'Single':>12} {'Full':>12}")
    print(f"  {'-'*35} {'-'*12} {'-'*12} {'-'*12}")
    for num in nums:
        r = all_results[num]
        label = PROMPTS[num]["label"][:33]
        opus_w = f"{r['opus']['words']}w" if r['opus']['words'] else "FAIL"
        single_w = f"{r['single']['words']}w" if r['single']['words'] else "FAIL"
        full_w = f"{r['full']['words']}w" if r['full']['words'] else "FAIL"
        print(f"  {label:<35} {opus_w:>12} {single_w:>12} {full_w:>12}")

    total_opus = sum(r['opus']['duration'] for r in all_results.values())
    total_haiku = sum(r['single']['duration'] + r['full']['duration'] for r in all_results.values())
    print(f"\n  Total time: Opus {total_opus:.0f}s, Haiku {total_haiku:.0f}s")
    print(f"  Output dirs: output/general_insights_p*/")

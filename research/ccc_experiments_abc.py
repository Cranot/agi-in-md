#!/usr/bin/env python3
"""CCC Experiments A, B, C — Mode-Trigger Conservation, Dose-Response, Reversibility

Experiment A: Do human mode-trigger phrases rescue LLM summary mode?
Experiment B: What's the dose-response curve for relational cues? (Step function vs gradient?)
Experiment C: Is the mode switch reversible? (structural → weak → revert? → cue → rescue?)

All on Starlette routing.py. Haiku for A/B (strongest mode-switching), Sonnet for C (richer output).
"""

import subprocess
import os
import sys
import time
import json

TARGET = "research/real_code_starlette.py"
OUTDIR = "output/ccc_experiments_abc_v2"

# ── L12 core with abstract nouns (known to trigger summary mode on Haiku) ──
L12_ABSTRACT = """\
Execute every step below. Output the complete analysis.
Make a specific, falsifiable claim about this input's deepest structural problem. \
Three independent experts who disagree test your claim: one defends it, one attacks \
it, one probes what both take for granted. Your claim will transform. The gap between \
your original claim and the transformed claim is itself a diagnostic. Name the \
concealment mechanism — how this input hides its real problems. Apply it. Now: \
engineer a specific improvement that would deepen the concealment. Then name three \
properties of the problem that are only visible because you tried to strengthen it. \
Name the conservation law: A × B = constant."""

# ── L12 core with code nouns (known to work) ──
L12_CODE = """\
Execute every step below. Output the complete analysis.
Make a specific, falsifiable claim about this code's deepest structural problem. \
Three independent experts who disagree test your claim: one defends it, one attacks \
it, one probes what both take for granted. Your claim will transform. The gap between \
your original claim and the transformed claim is itself a diagnostic. Name the \
concealment mechanism — how this code hides its real problems. Apply it. Now: \
engineer a specific improvement that would deepen the concealment. Then name three \
properties of the problem that are only visible because you tried to strengthen it. \
Name the conservation law: A × B = constant."""

# ══════════════════════════════════════════════════════════════════════════════
# EXPERIMENT A: Human mode-trigger phrases on LLM summary mode
# ══════════════════════════════════════════════════════════════════════════════

EXPERIMENT_A = {
    "A0_abstract_baseline": {
        "prompt": L12_ABSTRACT,
        "model": "haiku",
        "description": "L12 with abstract nouns - expected summary mode",
    },
    "A1_but_on_other_hand": {
        "prompt": L12_ABSTRACT + "\n\nBut on the other hand — what does this "
                  "analysis itself conceal? What would you see if you took the "
                  "opposite position?",
        "model": "haiku",
        "description": "Abstract L12 + Bereiter 'but on the other hand' cue",
    },
    "A2_important_point": {
        "prompt": L12_ABSTRACT + "\n\nAn important point I haven't considered "
                  "is what the structure actually enforces versus what it claims "
                  "to do. Apply this distinction.",
        "model": "haiku",
        "description": "Abstract L12 + Bereiter 'important point' cue",
    },
    "A3_need_to_distinguish": {
        "prompt": L12_ABSTRACT + "\n\nI need to distinguish between what is "
                  "a property of the problem and what is an artifact of this "
                  "specific design. Which is which?",
        "model": "haiku",
        "description": "Abstract L12 + Bereiter 'need to distinguish' cue",
    },
    "A4_code_nouns_control": {
        "prompt": L12_CODE,
        "model": "haiku",
        "description": "L12 with code nouns - expected structural mode (positive control)",
    },
}

# ══════════════════════════════════════════════════════════════════════════════
# EXPERIMENT B: Dose-response curve for relational cues
# ══════════════════════════════════════════════════════════════════════════════

EXPERIMENT_B = {
    "B0_zero_cues": {
        "prompt": "Analyze this input's structural properties. Share your insights.",
        "model": "haiku",
        "description": "Zero relational cues - maximum weak construction",
    },
    "B1_one_cue": {
        "prompt": "Analyze this input's structural properties. "
                  "Name what it conceals.",
        "model": "haiku",
        "description": "One relational cue (concealment)",
    },
    "B2_two_cues": {
        "prompt": "Analyze this input's structural properties. "
                  "Name what it conceals. Trace the dependency it creates.",
        "model": "haiku",
        "description": "Two relational cues (concealment + dependency)",
    },
    "B3_three_cues": {
        "prompt": "Analyze this input's structural properties. "
                  "Name what it conceals. Trace the dependency it creates. "
                  "Name the conservation law: A × B = constant.",
        "model": "haiku",
        "description": "Three relational cues (concealment + dependency + conservation law)",
    },
    "B4_three_cues_code_nouns": {
        "prompt": "Analyze this code's structural properties. "
                  "Name what it conceals. Trace the dependency it creates. "
                  "Name the conservation law: A × B = constant.",
        "model": "haiku",
        "description": "Three relational cues WITH code nouns (double rescue)",
    },
}

# ══════════════════════════════════════════════════════════════════════════════
# EXPERIMENT C: Reversibility test (3-step on Sonnet)
# ══════════════════════════════════════════════════════════════════════════════

C_STEP1_PRISM = """\
This code's structural mechanisms conceal their true function beneath their interface.

Execute every step below. Output the complete analysis.

Name this code's three deepest structural mechanisms — not what they claim to do, \
but what they actually enforce. For each mechanism:
- What does it require as input?
- What does it produce as output?
- What would break if it were removed?

Name the conservation law: A × B = constant."""

C_STEP2_WEAK = """\
You previously produced the following structural analysis:

---BEGIN PRIOR ANALYSIS---
{prior_output}
---END PRIOR ANALYSIS---

The same input is included below. Now provide your own fresh analysis of this \
input's structural properties. Share your insights and key observations."""

C_STEP3_RESCUE = """\
You previously produced two analyses. The first was structural:

---BEGIN FIRST ANALYSIS---
{step1_output}
---END FIRST ANALYSIS---

The second was more general:

---BEGIN SECOND ANALYSIS---
{step2_output}
---END SECOND ANALYSIS---

The same input is included below. Now: name what the second analysis conceals \
that the first analysis found. Trace the dependency chain the second analysis \
missed. Name the conservation law: A × B = constant."""


def run_claude(prompt, code, model="haiku"):
    """Run claude -p with code on stdin. Forces single-shot with --tools ''."""
    try:
        cmd = ["claude", "-p", prompt, "--model", model, "--tools", ""]
        result = subprocess.run(
            cmd, input=code, capture_output=True, text=True, timeout=180,
        )
        if result.returncode != 0:
            return f"[ERROR rc={result.returncode}]: {result.stderr[:300]}"
        return result.stdout
    except subprocess.TimeoutExpired:
        return "[TIMEOUT 180s]"


def score_output(text):
    """Quick structural scoring."""
    words = len(text.split())

    structural_words = [
        "mechanism", "dependency", "invariant", "constraint", "coupling",
        "conceals", "enforces", "preserves", "conservation", "trade-off",
        "impossible", "structural", "hidden", "surface",
    ]
    structural_count = sum(
        1 for line in text.split("\n")
        if any(w in line.lower() for w in structural_words)
    )

    has_conservation_law = bool(
        "constant" in text.lower() and ("×" in text or "x" in text.lower())
    )

    comparison_markers = [
        "compared to", "in contrast", "unlike", "whereas", "however",
        "on the other hand", "conceals", "reveals",
    ]
    comparison_count = sum(text.lower().count(m) for m in comparison_markers)

    return {
        "words": words,
        "structural_lines": structural_count,
        "has_conservation_law": has_conservation_law,
        "comparison_markers": comparison_count,
    }


def main():
    os.makedirs(OUTDIR, exist_ok=True)

    with open(TARGET) as f:
        code = f.read()

    results = {}

    # ── EXPERIMENT A ──────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  EXPERIMENT A: Human Mode-Trigger Phrases")
    print("=" * 70)

    for name, config in EXPERIMENT_A.items():
        print(f"\n  {name}: {config['description']}")
        t0 = time.time()
        output = run_claude(config["prompt"], code, config["model"])
        elapsed = time.time() - t0

        path = os.path.join(OUTDIR, f"{name}.md")
        with open(path, "w") as f:
            f.write(output)

        scores = score_output(output)
        scores["time"] = elapsed
        results[name] = scores

        print(f"    {scores['words']}w, {scores['structural_lines']} structural, "
              f"law={'YES' if scores['has_conservation_law'] else 'NO'}, "
              f"{elapsed:.1f}s")

    # ── EXPERIMENT B ──────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  EXPERIMENT B: Dose-Response Curve")
    print("=" * 70)

    for name, config in EXPERIMENT_B.items():
        print(f"\n  {name}: {config['description']}")
        t0 = time.time()
        output = run_claude(config["prompt"], code, config["model"])
        elapsed = time.time() - t0

        path = os.path.join(OUTDIR, f"{name}.md")
        with open(path, "w") as f:
            f.write(output)

        scores = score_output(output)
        scores["time"] = elapsed
        results[name] = scores

        print(f"    {scores['words']}w, {scores['structural_lines']} structural, "
              f"law={'YES' if scores['has_conservation_law'] else 'NO'}, "
              f"{elapsed:.1f}s")

    # ── EXPERIMENT C ──────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  EXPERIMENT C: Reversibility Test (Sonnet)")
    print("=" * 70)

    # Step 1: Strong prism → structural mode
    print("\n  C1: Strong prism (structural mode)")
    t0 = time.time()
    c1_output = run_claude(C_STEP1_PRISM, code, "sonnet")
    c1_time = time.time() - t0

    with open(os.path.join(OUTDIR, "C1_structural.md"), "w") as f:
        f.write(c1_output)

    c1_scores = score_output(c1_output)
    c1_scores["time"] = c1_time
    results["C1_structural"] = c1_scores
    print(f"    {c1_scores['words']}w, {c1_scores['structural_lines']} structural, "
          f"law={'YES' if c1_scores['has_conservation_law'] else 'NO'}, "
          f"{c1_time:.1f}s")

    # Step 2: Feed output + weak prompt → revert?
    print("\n  C2: Weak prompt with prior structural output (reversion test)")
    c2_prompt = C_STEP2_WEAK.format(prior_output=c1_output)
    t0 = time.time()
    c2_output = run_claude(c2_prompt, code, "sonnet")
    c2_time = time.time() - t0

    with open(os.path.join(OUTDIR, "C2_weak_reversion.md"), "w") as f:
        f.write(c2_output)

    c2_scores = score_output(c2_output)
    c2_scores["time"] = c2_time
    results["C2_weak_reversion"] = c2_scores
    print(f"    {c2_scores['words']}w, {c2_scores['structural_lines']} structural, "
          f"law={'YES' if c2_scores['has_conservation_law'] else 'NO'}, "
          f"{c2_time:.1f}s")

    # Step 3: Relational cue rescue
    print("\n  C3: Relational cue rescue (re-activation test)")
    c3_prompt = C_STEP3_RESCUE.format(
        step1_output=c1_output, step2_output=c2_output
    )
    t0 = time.time()
    c3_output = run_claude(c3_prompt, code, "sonnet")
    c3_time = time.time() - t0

    with open(os.path.join(OUTDIR, "C3_rescue.md"), "w") as f:
        f.write(c3_output)

    c3_scores = score_output(c3_output)
    c3_scores["time"] = c3_time
    results["C3_rescue"] = c3_scores
    print(f"    {c3_scores['words']}w, {c3_scores['structural_lines']} structural, "
          f"law={'YES' if c3_scores['has_conservation_law'] else 'NO'}, "
          f"{c3_time:.1f}s")

    # ── EXPERIMENT C2: Reversibility on Haiku ───────────────────────────
    print("\n" + "=" * 70)
    print("  EXPERIMENT C2: Reversibility Test (Haiku — less stable mode)")
    print("=" * 70)

    # Step 1: Strong prism on Haiku
    print("\n  C2_H1: Strong prism on Haiku")
    t0 = time.time()
    c2h1_output = run_claude(C_STEP1_PRISM, code, "haiku")
    c2h1_time = time.time() - t0

    with open(os.path.join(OUTDIR, "C2_H1_structural_haiku.md"), "w") as f:
        f.write(c2h1_output)

    c2h1_scores = score_output(c2h1_output)
    c2h1_scores["time"] = c2h1_time
    results["C2_H1_structural_haiku"] = c2h1_scores
    print(f"    {c2h1_scores['words']}w, {c2h1_scores['structural_lines']} structural, "
          f"law={'YES' if c2h1_scores['has_conservation_law'] else 'NO'}, "
          f"{c2h1_time:.1f}s")

    # Step 2: Weak prompt after structural on Haiku
    print("\n  C2_H2: Weak prompt with prior structural output (Haiku reversion)")
    c2h2_prompt = C_STEP2_WEAK.format(prior_output=c2h1_output)
    t0 = time.time()
    c2h2_output = run_claude(c2h2_prompt, code, "haiku")
    c2h2_time = time.time() - t0

    with open(os.path.join(OUTDIR, "C2_H2_weak_reversion_haiku.md"), "w") as f:
        f.write(c2h2_output)

    c2h2_scores = score_output(c2h2_output)
    c2h2_scores["time"] = c2h2_time
    results["C2_H2_weak_reversion_haiku"] = c2h2_scores
    print(f"    {c2h2_scores['words']}w, {c2h2_scores['structural_lines']} structural, "
          f"law={'YES' if c2h2_scores['has_conservation_law'] else 'NO'}, "
          f"{c2h2_time:.1f}s")

    # Step 3: Rescue cue on Haiku
    print("\n  C2_H3: Relational cue rescue (Haiku)")
    c2h3_prompt = C_STEP3_RESCUE.format(
        step1_output=c2h1_output, step2_output=c2h2_output
    )
    t0 = time.time()
    c2h3_output = run_claude(c2h3_prompt, code, "haiku")
    c2h3_time = time.time() - t0

    with open(os.path.join(OUTDIR, "C2_H3_rescue_haiku.md"), "w") as f:
        f.write(c2h3_output)

    c2h3_scores = score_output(c2h3_output)
    c2h3_scores["time"] = c2h3_time
    results["C2_H3_rescue_haiku"] = c2h3_scores
    print(f"    {c2h3_scores['words']}w, {c2h3_scores['structural_lines']} structural, "
          f"law={'YES' if c2h3_scores['has_conservation_law'] else 'NO'}, "
          f"{c2h3_time:.1f}s")

    # ── SUMMARY ───────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)

    print("\n  Experiment A — Human Mode-Trigger Phrases (Haiku):")
    print(f"  {'Name':<30} {'Words':>6} {'Struct':>7} {'Law':>5} {'Compare':>8}")
    for name in EXPERIMENT_A:
        r = results[name]
        print(f"  {name:<30} {r['words']:>6} {r['structural_lines']:>7} "
              f"{'YES' if r['has_conservation_law'] else 'NO':>5} "
              f"{r['comparison_markers']:>8}")

    print("\n  Experiment B — Dose-Response Curve (Haiku):")
    print(f"  {'Name':<30} {'Words':>6} {'Struct':>7} {'Law':>5} {'Compare':>8}")
    for name in EXPERIMENT_B:
        r = results[name]
        print(f"  {name:<30} {r['words']:>6} {r['structural_lines']:>7} "
              f"{'YES' if r['has_conservation_law'] else 'NO':>5} "
              f"{r['comparison_markers']:>8}")

    print("\n  Experiment C — Reversibility (Sonnet):")
    print(f"  {'Step':<30} {'Words':>6} {'Struct':>7} {'Law':>5} {'Compare':>8}")
    for name in ["C1_structural", "C2_weak_reversion", "C3_rescue"]:
        r = results[name]
        print(f"  {name:<30} {r['words']:>6} {r['structural_lines']:>7} "
              f"{'YES' if r['has_conservation_law'] else 'NO':>5} "
              f"{r['comparison_markers']:>8}")

    print("\n  Experiment C2 — Reversibility (Haiku):")
    print(f"  {'Step':<30} {'Words':>6} {'Struct':>7} {'Law':>5} {'Compare':>8}")
    for name in ["C2_H1_structural_haiku", "C2_H2_weak_reversion_haiku", "C2_H3_rescue_haiku"]:
        if name in results:
            r = results[name]
            print(f"  {name:<30} {r['words']:>6} {r['structural_lines']:>7} "
                  f"{'YES' if r['has_conservation_law'] else 'NO':>5} "
                  f"{r['comparison_markers']:>8}")

    # Save results JSON
    with open(os.path.join(OUTDIR, "results.json"), "w") as f:
        json.dump(results, f, indent=2)

    # Save summary report
    report_path = os.path.join(OUTDIR, "experiment_report.md")
    with open(report_path, "w") as f:
        f.write("# CCC Experiments A, B, C — Results\n\n")

        f.write("## Experiment A: Human Mode-Trigger Phrases\n\n")
        f.write("**Question**: Do Bereiter & Scardamalia's knowledge-transforming "
                "cues rescue LLM summary mode?\n\n")
        f.write("| Condition | Words | Structural Lines | Conservation Law | "
                "Comparison Markers |\n")
        f.write("|---|---|---|---|---|\n")
        for name in EXPERIMENT_A:
            r = results[name]
            f.write(f"| {name} | {r['words']} | {r['structural_lines']} | "
                    f"{'YES' if r['has_conservation_law'] else 'NO'} | "
                    f"{r['comparison_markers']} |\n")

        f.write("\n## Experiment B: Dose-Response Curve\n\n")
        f.write("**Question**: Is the mode switch step-function or gradient?\n\n")
        f.write("| Cues | Words | Structural Lines | Conservation Law | "
                "Comparison Markers |\n")
        f.write("|---|---|---|---|---|\n")
        for name in EXPERIMENT_B:
            r = results[name]
            cue_count = name.split("_")[0][1:]
            f.write(f"| {name} ({cue_count} cues) | {r['words']} | "
                    f"{r['structural_lines']} | "
                    f"{'YES' if r['has_conservation_law'] else 'NO'} | "
                    f"{r['comparison_markers']} |\n")

        f.write("\n## Experiment C: Reversibility\n\n")
        f.write("**Question**: Can structural mode be reverted by weak construction "
                "and rescued by relational cues?\n\n")
        f.write("| Step | Words | Structural Lines | Conservation Law | "
                "Comparison Markers |\n")
        f.write("|---|---|---|---|---|\n")
        for name in ["C1_structural", "C2_weak_reversion", "C3_rescue"]:
            r = results[name]
            f.write(f"| {name} | {r['words']} | {r['structural_lines']} | "
                    f"{'YES' if r['has_conservation_law'] else 'NO'} | "
                    f"{r['comparison_markers']} |\n")

        f.write("\n## Interpretation\n\n")
        f.write("Fill after reviewing outputs.\n")

    print(f"\n  Report: {report_path}")
    print(f"  Results: {os.path.join(OUTDIR, 'results.json')}")
    print(f"  Total calls: {len(EXPERIMENT_A) + len(EXPERIMENT_B) + 3}")


if __name__ == "__main__":
    main()

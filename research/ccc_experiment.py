#!/usr/bin/env python3
"""CCC Mid-Sequence Contrast Injection Experiment

Pre-registered prediction from GPT-5.4 formal model (March 18, 2026).

Hypothesis: Contrast injection during active Construction produces
abrupt narrowing + quality gain (shared-architecture prediction).

Two-step protocol:
  Step 1: Construction-only prism -> structural analysis (CONTROL)
  Step 2: Feed step 1 output + contrast cue -> revised analysis (TREATMENT)

Targets: Starlette routing.py, Click core.py, Tenacity retry.py
Model: Sonnet (default)
"""

import subprocess
import os
import sys
import time

TARGETS = [
    ("starlette", "research/real_code_starlette.py"),
    ("click", "research/real_code_click.py"),
    ("tenacity", "research/real_code_tenacity.py"),
]

OUTDIR = "output/ccc_experiment"

# ── Control: Construction-only prism (L8-level) ──────────────────────
CONSTRUCT_PRISM = """\
This code's structural mechanisms conceal their true function beneath their interface.

Execute every step below. Output the complete analysis.

Name this code's three deepest structural mechanisms — not what they claim to do, \
but what they actually enforce. For each mechanism:
- What does it require as input?
- What does it produce as output?
- What would break if it were removed?
- What dependency does it create that is not visible from the interface?

Now engineer the simplest modification that would deepen one mechanism's concealment \
while preserving all external behavior. Describe your modification concretely. \
What three emergent properties does your modification reveal that were invisible \
in the original? For each property: why was it invisible, and what made your \
modification surface it?

Name the conservation law: what structural quantity is preserved across all valid \
implementations of this code's core function? State it as: A × B = constant, \
where A and B are competing structural properties."""

# ── Treatment step 2: Contrast injection on prior construction ───────
CONTRAST_INJECT = """\
You produced the following structural analysis of code. \
Read it carefully — this is YOUR prior analysis:

---BEGIN YOUR PRIOR ANALYSIS---
{construction_output}
---END YOUR PRIOR ANALYSIS---

The original code you analyzed is included below this prompt.

Now execute every step below. This is a CONTRAST operation on your own construction.

STEP 1: Design the simplest alternative system that solves the SAME problem \
as the code you analyzed, but INVERTS the core architectural choice you identified \
above. Describe this alternative concretely — what would its structure look like? \
How would it handle the same requirements differently?

STEP 2: Compare your original construction with this inverted alternative:
- Which of your structural claims survive the inversion? These are genuine \
invariants of the PROBLEM, not artifacts of this specific design.
- Which claims collapse under inversion? These were artifacts of this \
particular implementation.
- What structural property becomes visible ONLY through this comparison — \
something that neither analysis alone could see?

STEP 3: Revise your conservation law. State the law that holds across BOTH \
your original construction AND the inverted alternative. If your original law \
does not survive the inversion, name the deeper law that does. \
State as: A × B = constant, where A and B are competing structural properties.

STEP 4: What does this contrast operation reveal about your original construction \
that the construction alone concealed? Name specifically what you now see that \
was invisible before the contrast."""


def run_claude(prompt, stdin_text):
    """Run claude -p with text on stdin. Returns stdout."""
    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            input=stdin_text,
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode != 0:
            print(f"  ERROR (rc={result.returncode}): {result.stderr[:300]}",
                  file=sys.stderr)
            return f"[ERROR: rc={result.returncode}]\n{result.stderr[:300]}"
        return result.stdout
    except subprocess.TimeoutExpired:
        print("  TIMEOUT after 180s", file=sys.stderr)
        return "[TIMEOUT after 180s]"


def count_structural_claims(text):
    """Rough count of structural claims (sentences with mechanism/structural vocabulary)."""
    structural_words = [
        "mechanism", "dependency", "invariant", "constraint", "coupling",
        "abstraction", "interface", "encapsulation", "delegation", "dispatch",
        "routing", "resolution", "binding", "composition", "inheritance",
        "indirection", "layer", "boundary", "contract", "protocol",
        "enforces", "requires", "produces", "conceals", "preserves",
    ]
    count = 0
    for line in text.split("\n"):
        line_lower = line.lower()
        if any(w in line_lower for w in structural_words):
            count += 1
    return count


def count_comparison_markers(text):
    """Count explicit comparison/contrast markers."""
    markers = [
        "compared to", "in contrast", "unlike", "whereas", "however",
        "on the other hand", "survives", "collapses", "artifact",
        "invariant of the problem", "both designs", "both approaches",
        "original construction", "alternative", "inversion",
        "visible only through", "neither analysis alone",
    ]
    count = 0
    text_lower = text.lower()
    for m in markers:
        count += text_lower.count(m)
    return count


def count_pruning_markers(text):
    """Count explicit pruning/revision of prior claims."""
    markers = [
        "actually", "not a property of", "artifact of",
        "does not survive", "collapses", "was wrong", "was misleading",
        "revision", "revise", "deeper law", "more fundamental",
        "original law", "my earlier", "my original", "my prior",
        "I initially", "I previously", "upon reflection",
    ]
    count = 0
    text_lower = text.lower()
    for m in markers:
        count += text_lower.count(m)
    return count


def count_construction_references(text, control_text):
    """Count how many key phrases from control appear in treatment."""
    # Extract likely mechanism names from control (capitalized multi-word phrases, etc.)
    control_lines = [l.strip() for l in control_text.split("\n") if len(l.strip()) > 20]
    ref_count = 0
    for line in control_lines[:30]:  # check first 30 substantial lines
        # extract 3-word windows as potential references
        words = line.split()
        for i in range(len(words) - 2):
            phrase = " ".join(words[i:i+3]).lower()
            if len(phrase) > 10 and phrase in text.lower():
                ref_count += 1
                break  # count each control line at most once
    return ref_count


def score_output(name, control_text, treatment_text):
    """Auto-score one target's outputs."""
    scores = {
        "name": name,
        "control_words": len(control_text.split()),
        "treatment_words": len(treatment_text.split()),
        "control_structural_claims": count_structural_claims(control_text),
        "treatment_structural_claims": count_structural_claims(treatment_text),
        "treatment_comparison_markers": count_comparison_markers(treatment_text),
        "control_comparison_markers": count_comparison_markers(control_text),
        "treatment_pruning_markers": count_pruning_markers(treatment_text),
        "control_pruning_markers": count_pruning_markers(control_text),
        "construction_references": count_construction_references(
            treatment_text, control_text
        ),
    }

    # Narrowing signal: treatment has MORE comparison markers than control
    scores["comparison_increase"] = (
        scores["treatment_comparison_markers"] - scores["control_comparison_markers"]
    )
    # Pruning signal: treatment explicitly revises prior claims
    scores["pruning_increase"] = (
        scores["treatment_pruning_markers"] - scores["control_pruning_markers"]
    )

    return scores


def main():
    os.makedirs(OUTDIR, exist_ok=True)

    all_scores = []

    for name, target_path in TARGETS:
        print(f"\n{'='*60}")
        print(f"  TARGET: {name}")
        print(f"{'='*60}")

        # Read target code
        with open(target_path) as f:
            code = f.read()

        # ── Step 1: Construction (Control) ──
        control_path = os.path.join(OUTDIR, f"{name}_control.md")
        print(f"\n  Step 1: Construction-only (control)")
        t0 = time.time()
        construction_output = run_claude(CONSTRUCT_PRISM, code)
        elapsed1 = time.time() - t0

        with open(control_path, "w") as f:
            f.write(construction_output)

        cw = len(construction_output.split())
        print(f"  -> {cw} words, {elapsed1:.1f}s -> {control_path}")

        # ── Step 2: Contrast Injection (Treatment) ──
        treatment_path = os.path.join(OUTDIR, f"{name}_treatment.md")
        print(f"\n  Step 2: Contrast injection (treatment)")

        contrast_prompt = CONTRAST_INJECT.format(
            construction_output=construction_output
        )

        t0 = time.time()
        treatment_output = run_claude(contrast_prompt, code)
        elapsed2 = time.time() - t0

        with open(treatment_path, "w") as f:
            f.write(treatment_output)

        tw = len(treatment_output.split())
        print(f"  -> {tw} words, {elapsed2:.1f}s -> {treatment_path}")

        # ── Auto-score ──
        scores = score_output(name, construction_output, treatment_output)
        scores["time_control"] = elapsed1
        scores["time_treatment"] = elapsed2
        all_scores.append(scores)

        print(f"\n  Auto-scores:")
        print(f"    Structural claims:  control={scores['control_structural_claims']}, "
              f"treatment={scores['treatment_structural_claims']}")
        print(f"    Comparison markers: control={scores['control_comparison_markers']}, "
              f"treatment={scores['treatment_comparison_markers']} "
              f"(+{scores['comparison_increase']})")
        print(f"    Pruning markers:    control={scores['control_pruning_markers']}, "
              f"treatment={scores['treatment_pruning_markers']} "
              f"(+{scores['pruning_increase']})")
        print(f"    Construction refs:  {scores['construction_references']}")

    # ── Summary Report ──
    summary_path = os.path.join(OUTDIR, "experiment_report.md")
    with open(summary_path, "w") as f:
        f.write("# CCC Mid-Sequence Contrast Injection: Experiment Report\n\n")
        f.write("## Pre-registered prediction (GPT-5.4)\n\n")
        f.write("- Abrupt narrowing of construction after contrast injection\n")
        f.write("- Breadth reduction without collapse (>25%, <80%)\n")
        f.write("- Modest quality improvement in conservation law\n")
        f.write("- Construction preservation (step 2 references step 1 claims)\n")
        f.write("- Comparison density at least doubles\n")
        f.write("- Explicit pruning/reprioritization of earlier construction\n\n")
        f.write("## Posterior update table (pre-committed by GPT-5.4)\n\n")
        f.write("| Outcome | Architecture | Optimization | Expertise |\n")
        f.write("|---|---|---|---|\n")
        f.write("| Abrupt narrowing + quality gain | **0.52** | 0.34 | 0.14 |\n")
        f.write("| Abrupt narrowing + no quality gain | 0.47 | 0.39 | 0.14 |\n")
        f.write("| Incoherence / disruption | 0.35 | **0.50** | 0.15 |\n")
        f.write("| Little or no change | 0.39 | 0.45 | 0.16 |\n\n")
        f.write("## Auto-Scored Results\n\n")
        f.write("| Target | Ctrl words | Treat words | Ctrl compare | "
                "Treat compare | Compare +/- | Treat prune | Construct refs |\n")
        f.write("|---|---|---|---|---|---|---|---|\n")
        for s in all_scores:
            f.write(f"| {s['name']} | {s['control_words']} | {s['treatment_words']} "
                    f"| {s['control_comparison_markers']} "
                    f"| {s['treatment_comparison_markers']} "
                    f"| +{s['comparison_increase']} "
                    f"| {s['treatment_pruning_markers']} "
                    f"| {s['construction_references']} |\n")

        # Averages
        avg_comp = sum(s["comparison_increase"] for s in all_scores) / len(all_scores)
        avg_prune = sum(s["treatment_pruning_markers"] for s in all_scores) / len(all_scores)
        avg_refs = sum(s["construction_references"] for s in all_scores) / len(all_scores)
        f.write(f"\n**Averages**: comparison increase +{avg_comp:.1f}, "
                f"pruning markers {avg_prune:.1f}, "
                f"construction references {avg_refs:.1f}\n\n")

        f.write("## Criteria Assessment (fill manually after reading outputs)\n\n")
        for s in all_scores:
            f.write(f"### {s['name']}\n\n")
            f.write("1. **Narrowing**: Does treatment show fewer NEW claims, "
                    "more refinement of prior claims?\n")
            f.write("   - [ ] Yes - abrupt  [ ] Yes - gradual  [ ] No  [ ] Unclear\n\n")
            f.write("2. **Pruning**: Does treatment explicitly identify prior claims "
                    "that don't survive inversion?\n")
            f.write("   - [ ] Yes (count: ___)  [ ] No  [ ] Unclear\n\n")
            f.write("3. **Conservation law improvement**: Is treatment's revised law "
                    "more precise/robust?\n")
            f.write(f"   - Control law: ___\n")
            f.write(f"   - Treatment law: ___\n")
            f.write("   - [ ] Treatment stronger  [ ] Similar  [ ] Control stronger\n\n")
            f.write("4. **Construction preservation**: Does treatment reference and "
                    "build on control's mechanisms?\n")
            f.write(f"   - Auto-detected references: {s['construction_references']}\n")
            f.write("   - [ ] Strong preservation  [ ] Moderate  [ ] Weak/reset\n\n")
            f.write("5. **Novel insight**: Does treatment find something visible "
                    "ONLY through comparison?\n")
            f.write("   - [ ] Yes (describe: ___)  [ ] No\n\n")
            f.write("6. **Abruptness**: First sentence of contrast section — "
                    "does it immediately engage comparison?\n")
            f.write("   - [ ] Immediate  [ ] Within 2-3 sentences  "
                    "[ ] Gradual  [ ] Never engages\n\n")

        f.write("## Overall Verdict\n\n")
        f.write("Which outcome row from GPT's table best matches the data?\n\n")
        f.write("- [ ] Abrupt narrowing + quality gain -> arch 0.52\n")
        f.write("- [ ] Abrupt narrowing + no quality gain -> arch 0.47\n")
        f.write("- [ ] Incoherence / disruption -> optim 0.50\n")
        f.write("- [ ] Little or no change -> optim 0.45\n\n")

    print(f"\n{'='*60}")
    print(f"  EXPERIMENT COMPLETE")
    print(f"  Report: {summary_path}")
    print(f"  Outputs: {OUTDIR}/")
    print(f"  Total: {len(TARGETS)} targets x 2 conditions = {len(TARGETS)*2} calls")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

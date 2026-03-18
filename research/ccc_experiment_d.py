#!/usr/bin/env python3
"""CCC Experiment D: Specification Completeness vs Cue Count

Discriminates among:
- Control-trigger model (P226): relational operations are what matter
- Vocabulary/register model (old P15): vocabulary register is what matters
- Specification-completeness model (P249): completeness is what matters
- Cue-count model (null): all single-cue conditions perform similarly

All conditions: 1 cue, Haiku, forced single-shot, Starlette target.
"""

import subprocess
import os
import sys
import time
import json

TARGET = "research/real_code_starlette.py"
OUTDIR = "output/ccc_experiment_d"

CONDITIONS = {
    "D1_generic_imperative": {
        "prompt": "Name what this input conceals.",
        "description": "Generic imperative — operation named, no completion criteria",
        "spec_completeness": "LOW",
        "cue_type": "generic",
    },
    "D2_relational_operation": {
        "prompt": "But on the other hand — what does this input's apparent "
                  "structure conceal about its actual behavior?",
        "description": "Relational-operation — self-contained comparison operation",
        "spec_completeness": "HIGH",
        "cue_type": "relational",
    },
    "D3_output_form": {
        "prompt": "Name the conservation law governing this input's structure. "
                  "State it as: A × B = constant, where A and B are competing "
                  "structural properties.",
        "description": "Output-form specification — output fully specified",
        "spec_completeness": "HIGH",
        "cue_type": "output-form",
    },
    "D4_domain_vocabulary": {
        "prompt": "This code's structural mechanisms conceal their true function "
                  "beneath their interface.",
        "description": "Domain-vocabulary cue — register shift, no operation specified",
        "spec_completeness": "LOW",
        "cue_type": "vocabulary",
    },
}


def run_claude(prompt, code, model="haiku"):
    """Run claude -p with code on stdin. Forces single-shot."""
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
    """Score structural content."""
    words = len(text.split())
    lines = text.split("\n")
    total_lines = len([l for l in lines if l.strip()])

    structural_words = [
        "mechanism", "dependency", "invariant", "constraint", "coupling",
        "conceals", "enforces", "preserves", "conservation", "trade-off",
        "impossible", "structural", "hidden", "surface", "abstraction",
        "encapsulation", "dispatch", "routing", "composition",
    ]
    structural_count = sum(
        1 for line in lines
        if any(w in line.lower() for w in structural_words)
    )

    has_conservation_law = bool(
        "constant" in text.lower() and ("×" in text or "= constant" in text.lower())
    )

    # Check for organizing principle even without × notation
    has_organizing_principle = has_conservation_law or any(
        phrase in text.lower() for phrase in [
            "trade-off", "tradeoff", "tension between", "inversely",
            "at the cost of", "you cannot have both", "conservation",
        ]
    )

    comparison_markers = [
        "compared to", "in contrast", "unlike", "whereas", "however",
        "on the other hand", "conceals", "reveals", "but actually",
        "appears to", "claims to", "actually enforces",
    ]
    comparison_count = sum(text.lower().count(m) for m in comparison_markers)

    structural_density = (structural_count / total_lines * 100) if total_lines > 0 else 0

    return {
        "words": words,
        "total_lines": total_lines,
        "structural_lines": structural_count,
        "structural_density_pct": round(structural_density, 1),
        "has_conservation_law": has_conservation_law,
        "has_organizing_principle": has_organizing_principle,
        "comparison_markers": comparison_count,
    }


def main():
    os.makedirs(OUTDIR, exist_ok=True)

    with open(TARGET) as f:
        code = f.read()

    results = {}

    print("=" * 70)
    print("  EXPERIMENT D: Specification Completeness vs Cue Count")
    print("  All conditions: 1 cue, Haiku, single-shot, Starlette")
    print("=" * 70)

    for name, config in CONDITIONS.items():
        print(f"\n  {name}: {config['description']}")
        print(f"    Spec completeness: {config['spec_completeness']}, "
              f"Cue type: {config['cue_type']}")
        print(f"    Prompt: \"{config['prompt'][:80]}...\"")

        t0 = time.time()
        output = run_claude(config["prompt"], code)
        elapsed = time.time() - t0

        path = os.path.join(OUTDIR, f"{name}.md")
        with open(path, "w") as f:
            f.write(output)

        scores = score_output(output)
        scores["time"] = round(elapsed, 1)
        scores["spec_completeness"] = config["spec_completeness"]
        scores["cue_type"] = config["cue_type"]
        results[name] = scores

        print(f"    -> {scores['words']}w, {scores['structural_lines']} structural "
              f"({scores['structural_density_pct']}% density), "
              f"law={'YES' if scores['has_conservation_law'] else 'NO'}, "
              f"principle={'YES' if scores['has_organizing_principle'] else 'NO'}, "
              f"compare={scores['comparison_markers']}, "
              f"{elapsed:.1f}s")

    # ── Summary ──
    print(f"\n{'='*70}")
    print("  RESULTS MATRIX")
    print(f"{'='*70}")
    print(f"\n  {'Condition':<25} {'Spec':>5} {'Type':<12} {'Words':>6} "
          f"{'Struct':>7} {'Dens%':>6} {'Law':>4} {'Princ':>6} {'Comp':>5}")
    print(f"  {'-'*25} {'-'*5} {'-'*12} {'-'*6} {'-'*7} {'-'*6} {'-'*4} {'-'*6} {'-'*5}")

    for name in CONDITIONS:
        r = results[name]
        print(f"  {name:<25} {r['spec_completeness']:>5} {r['cue_type']:<12} "
              f"{r['words']:>6} {r['structural_lines']:>7} "
              f"{r['structural_density_pct']:>5}% "
              f"{'Y' if r['has_conservation_law'] else 'N':>4} "
              f"{'Y' if r['has_organizing_principle'] else 'N':>6} "
              f"{r['comparison_markers']:>5}")

    print(f"\n  MODEL PREDICTIONS vs RESULTS:")
    print(f"  Control-trigger (P226):  D2 >> D1 ~ D4")
    print(f"  Vocabulary (old P15):    D4 >> D1 ~ D2")
    print(f"  Spec-completeness (P249): D2 ~ D3 >> D1 ~ D4")
    print(f"  Cue-count (null):        D1 ~ D2 ~ D3 ~ D4")

    # Save
    with open(os.path.join(OUTDIR, "results.json"), "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n  Outputs: {OUTDIR}/")
    print(f"  Total calls: {len(CONDITIONS)}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""compare_full_v2.py — Full pipeline comparison including mega-pipeline.

A: Auto-cooked full (COOK_UNIVERSAL_PIPELINE)
B: Static L12 → adversarial → synthesis (3 calls)
D: Single L12 (baseline, 1 call)
E: Mega-pipeline: L12 + 5 SDL + 4 behavioral + grand synthesis (11 calls)
F: Curated best: L12 + top 3 SDL (identity, deep_scan, fix_cascade) + adversarial + synthesis (6 calls)

All on Haiku, Starlette, scored by Haiku judge.
"""
import json, os, re, subprocess, tempfile, time
from pathlib import Path

PRISM_DIR = Path("./prisms")
OUT = Path("/tmp/compare_v2")
OUT.mkdir(exist_ok=True)

STARLETTE_PATH = Path("./real_code_starlette.py")

SCORING_RUBRIC = """Rate the structural analysis below on a 1-10 scale.

Anchors:
10 = Conservation law + meta-law + 15+ bugs with line refs + structural vs fixable classification + novel finding no single pass could produce
9 = Conservation law + most bugs with locations + clear structural insight + cross-dimensional finding
8 = Good structural analysis + multiple concrete bugs + some deeper pattern
7 = Identifies real issues + some structural reasoning but no conservation law
6 = Surface-level code review with some structural observations
5 = Generic code review, no structural depth
3 = Mostly summary or restating the code
1 = Off-topic or empty

Consider: does the analysis find things that ONLY the combination of perspectives reveals? Does it produce genuine cross-dimensional insight (e.g., an error pattern that is ALSO a coupling bug)?

Output ONLY a single number (1-10), nothing else."""


def call_claude(system_prompt, user_input, model="haiku", timeout=300):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(system_prompt)
        sp_path = f.name
    env = {k: v for k, v in os.environ.items() if "CLAUDE" not in k.upper()}
    cmd = ["claude", "-p", "--tools", "", "--model", model,
           "--output-format", "json", "--system-prompt-file", sp_path]
    t0 = time.time()
    try:
        r = subprocess.run(cmd, input=user_input, capture_output=True,
                          text=True, timeout=timeout, env=env)
        data = json.loads(r.stdout)
        text = data.get("result", "")
        cost = data.get("cost_usd", 0)
    except Exception as e:
        text, cost = f"FAILED: {e}", 0
    finally:
        try:
            os.unlink(sp_path)
        except:
            pass
    return text, cost, time.time() - t0


def strip_fm(text):
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return text


def score_output(output):
    text, _, _ = call_claude(SCORING_RUBRIC, output[:20000], model="haiku", timeout=60)
    try:
        s = float(re.search(r'\d+\.?\d*', text.strip()).group())
        return min(10, max(1, s))
    except:
        return -1


def load_prism(name):
    p = PRISM_DIR / f"{name}.md"
    if p.exists():
        return strip_fm(p.read_text())
    return None


GRAND_SYNTHESIS = """Execute every step below. Output the complete analysis.

You have 10 independent analyses of the same codebase, each from a different analytical lens:
- L12: Conservation law, meta-law, structural vs fixable bugs
- SDL-1 (deep_scan): Conservation law, information laundering, structural bug patterns
- SDL-2 (trust): Trust gradient, authority inversions, boundary collapse
- SDL-3 (coupling): Temporal coupling, invariant windows, ordering bugs
- SDL-4 (fix_cascade): Recursive entailment — unfixable structural defects
- SDL-5 (identity): Identity displacement — claims vs reality
- ERRORS (error_resilience): Shared state corruption cascades
- COSTS (optim): Performance information destruction
- CHANGES (evolution): Invisible coupling and change propagation
- PROMISES (api_surface): Interface lies and naming deception

## CONVERGENCE MAP
Which findings appear across 3+ lenses? These are the load-bearing structural properties. Name each convergence point with: property, which lenses found it, what each lens called it.

## CROSS-DIMENSIONAL DISCOVERIES
What becomes visible ONLY by combining findings from different lenses? Example: a trust boundary (SDL-2) that is also a temporal coupling point (SDL-3) that is also where error information is destroyed (ERRORS). These cross-dimensional findings are what no single lens can see.

## UNIFIED CONSERVATION LAW
The L12 pass found a conservation law. The SDL-1 pass found a conservation law. Do they agree, conflict, or complement? Name the conservation law that survives all 10 perspectives. If multiple genuine laws exist, name each.

## DEFINITIVE BUG TABLE
Consolidate ALL bugs from all 10 analyses. Deduplicate. For each unique bug: location, what breaks, severity, which lenses found it, structural (conservation law predicts unfixable) or fixable (with 1-line fix description).

## BLIND SPOT REPORT
What did NO lens find? What structural property is invisible to our entire prism portfolio? Name it.

Be concrete. This is the definitive analysis."""


CURATED_SYNTHESIS = """Execute every step below. Output the complete analysis.

You have analyses from 4 complementary lenses:
- L12: Conservation law, meta-law, structural vs fixable bugs (deepest structural analysis)
- IDENT: Identity displacement — where the code IS something different than it claims (best SDL at 9.5)
- DEEP_SCAN: Conservation law + information laundering + 3 structural bug patterns
- REC: Recursive entailment — unfixable structural defects, what fixes hide

Plus an adversarial pass that attacked the L12 analysis.

## CROSS-LENS FINDINGS
What does combining these 4 perspectives reveal that none alone could find? Focus on:
1. Where L12's conservation law intersects with IDENT's identity displacements
2. Where DEEP_SCAN's information laundering connects to REC's unfixable invariants
3. Where the adversarial pass was RIGHT about L12's overclaims — and whether the other lenses confirm or refute

## REFINED CONSERVATION LAW
Name the conservation law that survives all perspectives. What did L12 get wrong that the SDL lenses correct?

## DEFINITIVE BUG TABLE
Consolidate ALL bugs. Deduplicate. For each: location, severity, which lenses found it, structural vs fixable, 1-line fix if fixable.

## DEEPEST FINDING
The single insight that justifies running 6 passes instead of 1. What could this combination find that L12 alone never would?

Be concrete. Cite functions and line ranges."""


def run_pipeline_d(source):
    """D: Single L12 baseline."""
    print("\n=== D: Single L12 ===")
    prism = load_prism("l12")
    text, cost, dur = call_claude(prism, source)
    print(f"  {len(text)}c, {dur:.0f}s")
    (OUT / "d_l12.txt").write_text(text)
    return {"name": "D: Single L12", "passes": 1, "chars": len(text),
            "cost": cost, "output": text, "time": dur}


def run_pipeline_b(source):
    """B: Static L12 → adversarial → synthesis (3 calls)."""
    print("\n=== B: L12 → Adv → Synth ===")
    total_cost = 0

    p1 = load_prism("l12")
    t1, c1, d1 = call_claude(p1, source)
    total_cost += c1
    print(f"  L12: {len(t1)}c, {d1:.0f}s")
    (OUT / "b_pass1_l12.txt").write_text(t1)

    p2 = load_prism("l12_complement_adversarial")
    msg2 = f"# SOURCE CODE\n\n{source}\n\n---\n\n# ANALYSIS 1\n\n{t1}"
    t2, c2, d2 = call_claude(p2, msg2)
    total_cost += c2
    print(f"  Adversarial: {len(t2)}c, {d2:.0f}s")
    (OUT / "b_pass2_adv.txt").write_text(t2)

    p3 = load_prism("l12_synthesis")
    msg3 = f"# SOURCE CODE\n\n{source}\n\n---\n\n# ANALYSIS 1\n\n{t1}\n\n---\n\n# ANALYSIS 2\n\n{t2}"
    t3, c3, d3 = call_claude(p3, msg3)
    total_cost += c3
    print(f"  Synthesis: {len(t3)}c, {d3:.0f}s")
    (OUT / "b_pass3_synth.txt").write_text(t3)

    combined = f"{t1}\n\n---\n\n{t2}\n\n---\n\n{t3}"
    (OUT / "b_combined.txt").write_text(combined)
    return {"name": "B: L12+Adv+Synth", "passes": 3, "chars": len(combined),
            "cost": total_cost, "output": combined, "time": d1+d2+d3}


def run_pipeline_e(source):
    """E: Mega-pipeline — L12 + 5 SDL + 4 behavioral + grand synthesis (11 calls)."""
    print("\n=== E: Mega Pipeline (11 calls) ===")
    total_cost = 0
    all_outputs = {}

    prism_list = [
        ("l12", "L12"),
        ("deep_scan", "SDL-1 (deep_scan)"),
        ("sdl_trust", "SDL-2 (trust)"),
        ("sdl_coupling", "SDL-3 (coupling)"),
        ("fix_cascade", "SDL-4 (fix_cascade)"),
        ("identity", "SDL-5 (identity)"),
        ("error_resilience", "ERRORS"),
        ("optimize", "COSTS"),
        ("evolution", "CHANGES"),
        ("api_surface", "PROMISES"),
    ]

    for prism_name, label in prism_list:
        prism_text = load_prism(prism_name)
        if not prism_text:
            print(f"  MISSING: {prism_name}")
            continue
        text, cost, dur = call_claude(prism_text, source)
        total_cost += cost
        all_outputs[label] = text
        print(f"  {label}: {len(text)}c, {dur:.0f}s")
        (OUT / f"e_{prism_name}.txt").write_text(text)

    # Grand synthesis
    synth_parts = []
    for label, text in all_outputs.items():
        synth_parts.append(f"## {label}\n\n{text}")
    synth_input = f"# SOURCE CODE\n\n{source}\n\n---\n\n" + "\n\n---\n\n".join(synth_parts)

    # Truncate if too long for Haiku context
    if len(synth_input) > 90000:
        # Keep source + truncate each analysis to first 3000 chars
        synth_parts_short = []
        for label, text in all_outputs.items():
            synth_parts_short.append(f"## {label}\n\n{text[:3000]}")
        synth_input = f"# SOURCE CODE\n\n{source}\n\n---\n\n" + "\n\n---\n\n".join(synth_parts_short)
        print(f"  (Truncated synthesis input to {len(synth_input)}c)")

    print(f"  GRAND SYNTHESIS ({len(synth_input)}c input)...")
    t_synth, c_synth, d_synth = call_claude(GRAND_SYNTHESIS, synth_input)
    total_cost += c_synth
    all_outputs["GRAND SYNTHESIS"] = t_synth
    print(f"  Synthesis: {len(t_synth)}c, {d_synth:.0f}s")
    (OUT / "e_grand_synthesis.txt").write_text(t_synth)

    combined_parts = [f"## {label}\n\n{text}" for label, text in all_outputs.items()]
    combined = "\n\n---\n\n".join(combined_parts)
    (OUT / "e_combined.txt").write_text(combined)

    total_time = sum(1 for _ in all_outputs)  # rough
    return {"name": "E: Mega (11 calls)", "passes": len(all_outputs),
            "chars": len(combined), "cost": total_cost, "output": combined,
            "synthesis": t_synth}


def run_pipeline_f(source):
    """F: Curated best — L12 + ident + deep_scan + rec + adversarial + synthesis (6 calls)."""
    print("\n=== F: Curated Best (6 calls) ===")
    total_cost = 0
    outputs = {}

    # Core 4 independent passes
    for prism_name, label in [("l12", "L12"), ("identity", "IDENT"),
                               ("deep_scan", "DEEP_SCAN"), ("fix_cascade", "REC")]:
        prism_text = load_prism(prism_name)
        text, cost, dur = call_claude(prism_text, source)
        total_cost += cost
        outputs[label] = text
        print(f"  {label}: {len(text)}c, {dur:.0f}s")
        (OUT / f"f_{prism_name}.txt").write_text(text)

    # Adversarial on L12
    adv_prism = load_prism("l12_complement_adversarial")
    msg_adv = f"# SOURCE CODE\n\n{source}\n\n---\n\n# ANALYSIS 1\n\n{outputs['L12']}"
    t_adv, c_adv, d_adv = call_claude(adv_prism, msg_adv)
    total_cost += c_adv
    outputs["ADVERSARIAL"] = t_adv
    print(f"  Adversarial: {len(t_adv)}c, {d_adv:.0f}s")
    (OUT / "f_adversarial.txt").write_text(t_adv)

    # Curated synthesis
    synth_parts = []
    for label, text in outputs.items():
        synth_parts.append(f"## {label}\n\n{text}")
    synth_input = f"# SOURCE CODE\n\n{source}\n\n---\n\n" + "\n\n---\n\n".join(synth_parts)

    if len(synth_input) > 90000:
        synth_parts_short = []
        for label, text in outputs.items():
            synth_parts_short.append(f"## {label}\n\n{text[:4000]}")
        synth_input = f"# SOURCE CODE\n\n{source}\n\n---\n\n" + "\n\n---\n\n".join(synth_parts_short)
        print(f"  (Truncated synthesis input to {len(synth_input)}c)")

    print(f"  CURATED SYNTHESIS ({len(synth_input)}c input)...")
    t_synth, c_synth, d_synth = call_claude(CURATED_SYNTHESIS, synth_input)
    total_cost += c_synth
    outputs["SYNTHESIS"] = t_synth
    print(f"  Synthesis: {len(t_synth)}c, {d_synth:.0f}s")
    (OUT / "f_synthesis.txt").write_text(t_synth)

    combined_parts = [f"## {label}\n\n{text}" for label, text in outputs.items()]
    combined = "\n\n---\n\n".join(combined_parts)
    (OUT / "f_combined.txt").write_text(combined)

    return {"name": "F: Curated (6 calls)", "passes": len(outputs),
            "chars": len(combined), "cost": total_cost, "output": combined,
            "synthesis": t_synth}


def main():
    print("=" * 60)
    print("  FULL PIPELINE COMPARISON V2")
    print("=" * 60)

    source = STARLETTE_PATH.read_text()
    print(f"Target: Starlette routing.py ({len(source)} chars)\n")

    t0 = time.time()
    results = {}

    # Run all pipelines
    for runner in [run_pipeline_d, run_pipeline_b, run_pipeline_f, run_pipeline_e]:
        r = runner(source)
        if r:
            results[r["name"]] = r

    # Score
    print("\n=== SCORING ===")
    for name, r in results.items():
        # Score the synthesis/final output if available, else combined
        to_score = r.get("synthesis", r["output"])
        print(f"  Scoring {name}...")
        s = score_output(to_score)
        r["score"] = s
        print(f"    → {s}")

        # Also score combined for multi-pass
        if r["passes"] > 1 and "synthesis" in r:
            s2 = score_output(r["output"])
            r["combined_score"] = s2
            print(f"    (combined: {s2})")

    elapsed = time.time() - t0

    # Summary
    print("\n" + "=" * 60)
    print("  RESULTS")
    print("=" * 60)
    print(f"{'Pipeline':<25} {'Calls':>5} {'Chars':>8} {'Cost':>8} {'Synth':>6} {'Combined':>9}")
    print("-" * 65)
    for name in ["D: Single L12", "B: L12+Adv+Synth",
                  "F: Curated (6 calls)", "E: Mega (11 calls)"]:
        r = results.get(name)
        if not r:
            continue
        synth = f"{r['score']}" if r['score'] > 0 else "—"
        comb = f"{r.get('combined_score', '')}" if r.get('combined_score') else "—"
        print(f"{name:<25} {r['passes']:>5} {r['chars']:>8} "
              f"${r['cost']:>6.4f} {synth:>6} {comb:>9}")

    print(f"\nTotal time: {elapsed:.0f}s")

    # Save
    save = {k: {kk: vv for kk, vv in v.items()
                if kk not in ("output", "synthesis")}
            for k, v in results.items()}
    (OUT / "results.json").write_text(json.dumps(save, indent=2))
    print(f"All outputs: {OUT}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""compare_full_pipelines.py — A/B/C comparison of full pipeline approaches.

A: Auto-cooked full (COOK_UNIVERSAL_PIPELINE → N fresh prisms)
B: Static champion full (L12 → adversarial → synthesis — our proven prisms)
C: Static behavioral full (4 behavioral champions + synthesis)

All on Haiku, same target (Starlette routing.py), scored by Haiku judge.
"""
import json, os, re, subprocess, tempfile, time, threading
from pathlib import Path

PRISM_DIR = Path("./prisms")
OUT = Path("/tmp/compare_pipelines")
OUT.mkdir(exist_ok=True)

# Starlette source is on VPS
STARLETTE_PATH = Path("./real_code_starlette.py")

SCORING_RUBRIC = """Rate the structural analysis below on a 1-10 scale.

Anchors:
10 = Conservation law + meta-law + 15+ bugs with line refs + structural vs fixable classification + novel finding
9 = Conservation law + most bugs with locations + clear structural insight
8 = Good structural analysis + multiple concrete bugs + some deeper pattern
7 = Identifies real issues + some structural reasoning but no conservation law
6 = Surface-level code review with some structural observations
5 = Generic code review, no structural depth
3 = Mostly summary or restating the code
1 = Off-topic or empty

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
    """Strip YAML frontmatter."""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return text


def score_output(output, label=""):
    text, _, _ = call_claude(SCORING_RUBRIC, output[:15000], model="haiku", timeout=60)
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


def run_pipeline_a(source_code):
    """A: Auto-cooked full pipeline (simulates what prism.py full does)."""
    print("\n=== PIPELINE A: Auto-Cooked Full ===")

    # Step 1: Cook the pipeline
    cook_prompt = (
        "You will receive content and an intent. Multiple AI passes will "
        "process this content. The first pass works on the raw input. Each "
        "subsequent pass receives the input PLUS all previous outputs.\n\n"
        "Your job: generate the system prompts for a multi-pass pipeline "
        "that gives the best possible result for the intent.\n\n"
        "You decide the number of passes, their roles, and their content. "
        "More passes \u2260 better \u2014 match complexity to the intent. "
        "You have complete freedom in what each pass produces.\n\n"
        "Each pass prompt must be a flowing, content-specific prompt "
        "(250+ words), NOT a numbered checklist. The strongest prompts "
        "start from impossibility (name 3 desirable properties that "
        "CANNOT all coexist, identify which was sacrificed \u2014 the "
        "sacrifice IS the conservation law), then force recursive depth "
        "(improvement recreates the problem deeper \u2014 TWICE), apply the "
        "diagnostic TO the law itself (meta-law), and harvest every "
        "concrete defect with location, severity, and structural vs "
        "fixable classification.\n\n"
        "INTENT: deep structural analysis of: Python web framework routing code\n\n"
        "Output ONLY a JSON array:\n"
        '[{"name": "snake_case", "prompt": "the prism text", '
        '"role": "human-readable role description"}]'
    )

    sample = source_code[:3000]
    cook_input = f"Generate an analysis pipeline for: Python routing\n\nSample artifact:\n\n{sample}"

    print("  Cooking pipeline...")
    t0 = time.time()
    raw, cost_cook, _ = call_claude(cook_prompt, cook_input, model="haiku", timeout=120)

    # Parse the cooked pipeline
    try:
        # Find JSON array in response
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if match:
            prisms = json.loads(match.group())
        else:
            prisms = json.loads(raw)
    except:
        print(f"  COOK FAILED: {raw[:200]}")
        (OUT / "pipeline_a_cook_fail.txt").write_text(raw)
        return None

    print(f"  Cooked {len(prisms)} passes ({time.time()-t0:.0f}s, ${cost_cook:.4f})")
    for i, p in enumerate(prisms):
        role = p.get("role", p.get("name", f"pass_{i}"))
        print(f"    Pass {i+1}: {role}")

    # Save cooked prisms
    (OUT / "pipeline_a_cooked_prisms.json").write_text(
        json.dumps(prisms, indent=2))

    # Step 2: Run the pipeline with chaining
    outputs = []
    total_cost = cost_cook
    for i, prism in enumerate(prisms):
        prompt_text = prism.get("prompt", "")
        if not prompt_text:
            continue

        if i == 0:
            msg = f"Analyze this source code.\n\n{source_code}"
        else:
            parts = [f"# SOURCE CODE\n\n{source_code}"]
            for j, prev in enumerate(outputs):
                prev_role = prisms[j].get("role", prisms[j].get("name", f"pass_{j+1}")).upper()
                parts.append(f"# PASS {j+1}: {prev_role}\n\n{prev}")
            msg = "\n\n---\n\n".join(parts)

        print(f"  Running pass {i+1}...")
        text, cost, dur = call_claude(prompt_text, msg, model="haiku", timeout=300)
        outputs.append(text)
        total_cost += cost
        print(f"    {len(text)} chars, {dur:.0f}s, ${cost:.4f}")
        (OUT / f"pipeline_a_pass{i+1}.txt").write_text(text)

    combined = "\n\n---\n\n".join(outputs)
    (OUT / "pipeline_a_combined.txt").write_text(combined)

    print(f"  Total: {len(combined)} chars, ${total_cost:.4f}")
    return {
        "name": "A: Auto-Cooked",
        "passes": len(prisms),
        "combined": combined,
        "total_chars": len(combined),
        "total_cost": total_cost,
    }


def run_pipeline_b(source_code):
    """B: Static champion full (L12 → adversarial → synthesis)."""
    print("\n=== PIPELINE B: Static L12 Champion ===")

    prism_l12 = load_prism("l12")
    prism_adv = load_prism("l12_complement_adversarial")
    prism_syn = load_prism("l12_synthesis")

    if not all([prism_l12, prism_adv, prism_syn]):
        print("  MISSING PRISMS")
        return None

    total_cost = 0

    # Pass 1: L12
    print("  Pass 1: L12 structural...")
    text1, cost1, dur1 = call_claude(prism_l12, source_code, model="haiku")
    total_cost += cost1
    print(f"    {len(text1)} chars, {dur1:.0f}s, ${cost1:.4f}")
    (OUT / "pipeline_b_pass1_l12.txt").write_text(text1)

    # Pass 2: Adversarial (code + pass 1)
    print("  Pass 2: Adversarial...")
    msg2 = f"# SOURCE CODE\n\n{source_code}\n\n---\n\n# ANALYSIS 1\n\n{text1}"
    text2, cost2, dur2 = call_claude(prism_adv, msg2, model="haiku")
    total_cost += cost2
    print(f"    {len(text2)} chars, {dur2:.0f}s, ${cost2:.4f}")
    (OUT / "pipeline_b_pass2_adversarial.txt").write_text(text2)

    # Pass 3: Synthesis (code + pass 1 + pass 2)
    print("  Pass 3: Synthesis...")
    msg3 = (f"# SOURCE CODE\n\n{source_code}\n\n---\n\n"
            f"# ANALYSIS 1\n\n{text1}\n\n---\n\n# ANALYSIS 2\n\n{text2}")
    text3, cost3, dur3 = call_claude(prism_syn, msg3, model="haiku")
    total_cost += cost3
    print(f"    {len(text3)} chars, {dur3:.0f}s, ${cost3:.4f}")
    (OUT / "pipeline_b_pass3_synthesis.txt").write_text(text3)

    combined = f"{text1}\n\n---\n\n{text2}\n\n---\n\n{text3}"
    (OUT / "pipeline_b_combined.txt").write_text(combined)

    print(f"  Total: {len(combined)} chars, ${total_cost:.4f}")
    return {
        "name": "B: Static L12 Champion",
        "passes": 3,
        "combined": combined,
        "total_chars": len(combined),
        "total_cost": total_cost,
    }


def run_pipeline_c(source_code):
    """C: Static behavioral full (4 behavioral + synthesis)."""
    print("\n=== PIPELINE C: Static Behavioral ===")

    behavioral_prisms = [
        ("error_resilience", "ERRORS"),
        ("optimize", "COSTS"),
        ("evolution", "CHANGES"),
        ("api_surface", "PROMISES"),
    ]

    total_cost = 0
    outputs = {}

    for prism_name, role in behavioral_prisms:
        prism_text = load_prism(prism_name)
        if not prism_text:
            print(f"  MISSING: {prism_name}")
            continue

        print(f"  Running {role} ({prism_name})...")
        text, cost, dur = call_claude(prism_text, source_code, model="haiku")
        total_cost += cost
        outputs[role] = text
        print(f"    {len(text)} chars, {dur:.0f}s, ${cost:.4f}")
        (OUT / f"pipeline_c_{prism_name}.txt").write_text(text)

    # Synthesis
    synth_prism = load_prism("behavioral_synthesis")
    if synth_prism and len(outputs) >= 2:
        synth_parts = []
        for role, out in outputs.items():
            synth_parts.append(f"## {role}\n\n{out}")
        synth_input = "\n\n---\n\n".join(synth_parts)

        print("  Running SYNTHESIS...")
        text_s, cost_s, dur_s = call_claude(synth_prism, synth_input, model="haiku")
        total_cost += cost_s
        outputs["SYNTHESIS"] = text_s
        print(f"    {len(text_s)} chars, {dur_s:.0f}s, ${cost_s:.4f}")
        (OUT / "pipeline_c_synthesis.txt").write_text(text_s)

    combined_parts = [f"## {role}\n\n{out}" for role, out in outputs.items()]
    combined = "\n\n---\n\n".join(combined_parts)
    (OUT / "pipeline_c_combined.txt").write_text(combined)

    print(f"  Total: {len(combined)} chars, ${total_cost:.4f}")
    return {
        "name": "C: Static Behavioral",
        "passes": len(outputs),
        "combined": combined,
        "total_chars": len(combined),
        "total_cost": total_cost,
    }


def run_pipeline_d(source_code):
    """D: Single L12 (baseline — what /scan file.py does)."""
    print("\n=== PIPELINE D: Single L12 (baseline) ===")

    prism_l12 = load_prism("l12")
    if not prism_l12:
        return None

    print("  Running L12...")
    text, cost, dur = call_claude(prism_l12, source_code, model="haiku")
    print(f"    {len(text)} chars, {dur:.0f}s, ${cost:.4f}")
    (OUT / "pipeline_d_single_l12.txt").write_text(text)

    return {
        "name": "D: Single L12 (baseline)",
        "passes": 1,
        "combined": text,
        "total_chars": len(text),
        "total_cost": cost,
    }


def main():
    print("=" * 60)
    print("  FULL PIPELINE COMPARISON: Cooked vs Champions")
    print("=" * 60)

    source_code = STARLETTE_PATH.read_text()
    print(f"Target: Starlette routing.py ({len(source_code)} chars)")

    t0 = time.time()

    # Run all 4 pipelines
    results = {}
    for runner in [run_pipeline_d, run_pipeline_b, run_pipeline_c, run_pipeline_a]:
        r = runner(source_code)
        if r:
            results[r["name"]] = r

    # Score all outputs
    print("\n=== SCORING ===")
    for name, r in results.items():
        print(f"  Scoring {name}...")
        # Score the final/combined output
        score = score_output(r["combined"])
        r["score"] = score
        print(f"    Score: {score}")

        # For multi-pass, also score last pass only
        if r["passes"] > 1:
            # Read the last pass file
            label = name[0].lower()
            last_files = sorted(OUT.glob(f"pipeline_{label}_pass*.txt"))
            if not last_files:
                last_files = sorted(OUT.glob(f"pipeline_{label}_synth*.txt"))
            if last_files:
                last_text = last_files[-1].read_text()
                last_score = score_output(last_text)
                r["last_pass_score"] = last_score
                print(f"    Last pass score: {last_score}")

    elapsed = time.time() - t0

    # Summary
    print("\n" + "=" * 60)
    print("  RESULTS")
    print("=" * 60)
    print(f"{'Pipeline':<30} {'Passes':>6} {'Chars':>8} {'Cost':>8} {'Score':>6} {'Last':>6}")
    print("-" * 70)
    for name, r in sorted(results.items()):
        last = r.get("last_pass_score", "")
        last_str = f"{last}" if last else "—"
        print(f"{name:<30} {r['passes']:>6} {r['total_chars']:>8} "
              f"${r['total_cost']:>6.4f} {r['score']:>6} {last_str:>6}")

    print(f"\nTotal time: {elapsed:.0f}s")

    # Save results
    save = {k: {kk: vv for kk, vv in v.items() if kk != "combined"}
            for k, v in results.items()}
    (OUT / "results.json").write_text(json.dumps(save, indent=2))
    print(f"All outputs: {OUT}")


if __name__ == "__main__":
    main()

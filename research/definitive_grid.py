#!/usr/bin/env python3
"""definitive_grid.py — Two definitive tests.

TEST 1: L12 model confidence (3 runs each of Haiku/Sonnet/Opus L12, scored by BOTH Haiku and Sonnet judges)
TEST 2: Complementarity matrix (run all 6 core prisms at optimal model, then have Opus judge uniqueness of each)

This is the experiment that locks the grid.
"""
import json, os, re, subprocess, tempfile, time, threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

PRISM_DIR = Path("/home/claude/insights/prisms")
OUT = Path("/tmp/definitive_grid")
OUT.mkdir(exist_ok=True)

STARLETTE_PATH = Path("/home/claude/insights/real_code_starlette.py")

SCORING_RUBRIC = """Rate this structural code analysis on a 1-10 scale.

Anchors:
10 = Conservation law + meta-law + 15+ bugs with exact line refs + structural vs fixable + novel finding
9 = Conservation law + bugs with locations + clear structural insight beyond surface
8 = Multiple concrete bugs + deeper pattern + some structural reasoning
7 = Real issues + structural reasoning but no conservation law
6 = Surface code review
5 = Generic review
3 = Summary
1 = Empty

Output ONLY a single number (1-10), nothing else."""

UNIQUENESS_RUBRIC = """You are comparing two code analyses of the same codebase.

ANALYSIS A:
{analysis_a}

ANALYSIS B:
{analysis_b}

Rate how much UNIQUE content Analysis B adds that Analysis A does NOT contain.
Focus on: different bugs found, different structural properties named, different conservation laws, different mechanisms identified.

Scoring:
10 = Completely different findings, zero overlap
8 = Mostly different, 1-2 shared observations but different conclusions
6 = Mixed — some overlap in surface observations but different deeper findings
4 = Significant overlap — most findings appear in both, a few unique to B
2 = Nearly identical — B restates what A already found
0 = Complete duplicate

Output ONLY a single number (0-10), nothing else."""


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


def load_prism(name):
    p = PRISM_DIR / f"{name}.md"
    if p.exists():
        return strip_fm(p.read_text())
    return None


def score_output(output, judge_model="haiku"):
    text, _, _ = call_claude(SCORING_RUBRIC, output[:15000], model=judge_model, timeout=60)
    try:
        s = float(re.search(r'\d+\.?\d*', text.strip()).group())
        return min(10, max(1, s))
    except:
        return -1


def score_uniqueness(analysis_a, analysis_b, judge_model="haiku"):
    """Score how much unique content B adds over A."""
    prompt = UNIQUENESS_RUBRIC.format(
        analysis_a=analysis_a[:8000],
        analysis_b=analysis_b[:8000])
    text, _, _ = call_claude(prompt, "Score the uniqueness.", model=judge_model, timeout=60)
    try:
        s = float(re.search(r'\d+\.?\d*', text.strip()).group())
        return min(10, max(0, s))
    except:
        return -1


def test1_l12_confidence(source_code):
    """TEST 1: Run L12 × 3 models × 3 repetitions, scored by Haiku AND Sonnet judges."""
    print("\n" + "=" * 60)
    print("  TEST 1: L12 Model Confidence")
    print("  (3 models × 3 reps × 2 judges = 18 runs + 18 scores)")
    print("=" * 60)

    l12_prism = load_prism("l12")
    results = {}

    for model in ["haiku", "sonnet", "opus"]:
        for rep in range(1, 4):
            tag = f"l12_{model}_r{rep}"
            print(f"  Running {tag}...")
            text, cost, dur = call_claude(l12_prism, source_code, model=model, timeout=400)

            if text.startswith("FAILED:"):
                print(f"    FAILED ({dur:.0f}s)")
                results[tag] = {"model": model, "rep": rep, "chars": 0,
                               "haiku_score": -1, "sonnet_score": -1, "failed": True}
                continue

            (OUT / f"{tag}.txt").write_text(text)

            # Score with BOTH judges
            h_score = score_output(text, "haiku")
            s_score = score_output(text, "sonnet")

            results[tag] = {
                "model": model, "rep": rep, "chars": len(text),
                "time": dur, "haiku_score": h_score, "sonnet_score": s_score
            }
            print(f"    {len(text)}c, {dur:.0f}s | Haiku judge: {h_score}, Sonnet judge: {s_score}")

    # Summary
    print(f"\n  {'Model':<10} {'Run':>4} {'Chars':>7} {'Haiku Judge':>12} {'Sonnet Judge':>13}")
    print("  " + "-" * 50)

    for model in ["haiku", "sonnet", "opus"]:
        h_scores = []
        s_scores = []
        for rep in range(1, 4):
            tag = f"l12_{model}_r{rep}"
            r = results.get(tag, {})
            h = r.get("haiku_score", -1)
            s = r.get("sonnet_score", -1)
            if h > 0: h_scores.append(h)
            if s > 0: s_scores.append(s)
            print(f"  {model:<10} {rep:>4} {r.get('chars', 0):>7} {h:>12} {s:>13}")

        h_avg = sum(h_scores) / len(h_scores) if h_scores else 0
        s_avg = sum(s_scores) / len(s_scores) if s_scores else 0
        print(f"  {model:<10} {'AVG':>4} {'':>7} {h_avg:>12.1f} {s_avg:>13.1f}")
        print()

    return results


def test2_complementarity(source_code):
    """TEST 2: Run 6 core prisms at optimal model, then score uniqueness of each pair."""
    print("\n" + "=" * 60)
    print("  TEST 2: Complementarity Matrix")
    print("  (6 prisms at optimal model + pairwise uniqueness scoring)")
    print("=" * 60)

    # Optimal model from Phase 1 results (using best known)
    optimal = {
        "l12": "haiku",
        "deep_scan": "opus",
        "fix_cascade": "opus",
        "identity": "sonnet",
        "optimize": "sonnet",
        "error_resilience": "sonnet",
    }

    prism_names = list(optimal.keys())
    outputs = {}

    # Run all 6
    for prism_name in prism_names:
        model = optimal[prism_name]
        prism_text = load_prism(prism_name)
        if not prism_text:
            print(f"  MISSING: {prism_name}")
            continue

        print(f"  Running {prism_name} on {model}...")
        text, cost, dur = call_claude(prism_text, source_code, model=model, timeout=400)

        if text.startswith("FAILED:"):
            print(f"    FAILED")
            continue

        outputs[prism_name] = text
        (OUT / f"comp_{prism_name}.txt").write_text(text)
        print(f"    {len(text)}c, {dur:.0f}s")

    # Pairwise uniqueness matrix
    # For each prism B, score how much it adds over L12 (the baseline)
    # Then score each non-L12 pair
    print(f"\n  Scoring uniqueness (each prism vs L12 baseline)...")

    uniqueness_vs_l12 = {}
    l12_text = outputs.get("l12", "")

    for prism_name in prism_names:
        if prism_name == "l12":
            continue
        if prism_name not in outputs:
            continue

        # How much does this prism add over L12?
        u = score_uniqueness(l12_text, outputs[prism_name], judge_model="haiku")
        uniqueness_vs_l12[prism_name] = u
        print(f"    {prism_name} vs l12: {u}/10 unique")

    # Full pairwise matrix (non-L12 prisms only)
    non_l12 = [p for p in prism_names if p != "l12" and p in outputs]
    pairwise = {}

    print(f"\n  Scoring pairwise uniqueness (non-L12 pairs)...")
    for i, a in enumerate(non_l12):
        for b in non_l12[i+1:]:
            u_ab = score_uniqueness(outputs[a], outputs[b], judge_model="haiku")
            u_ba = score_uniqueness(outputs[b], outputs[a], judge_model="haiku")
            pairwise[f"{a}_vs_{b}"] = u_ab
            pairwise[f"{b}_vs_{a}"] = u_ba
            print(f"    {b} adds {u_ab}/10 over {a} | {a} adds {u_ba}/10 over {b}")

    # Summary
    print(f"\n  UNIQUENESS vs L12:")
    print(f"  {'Prism':<20} {'Unique over L12':>15} {'Verdict':>15}")
    print("  " + "-" * 52)
    for prism_name, u in sorted(uniqueness_vs_l12.items(), key=lambda x: -x[1]):
        verdict = "ESSENTIAL" if u >= 7 else "VALUABLE" if u >= 5 else "OVERLAP" if u >= 3 else "REDUNDANT"
        print(f"  {prism_name:<20} {u:>15}/10 {verdict:>15}")

    print(f"\n  PAIRWISE UNIQUENESS (non-L12):")
    for key, u in sorted(pairwise.items()):
        print(f"    {key}: {u}/10")

    return {"vs_l12": uniqueness_vs_l12, "pairwise": pairwise, "outputs": {k: len(v) for k, v in outputs.items()}}


def main():
    print("=" * 60)
    print("  DEFINITIVE GRID — Lock the Configuration")
    print("=" * 60)

    source_code = STARLETTE_PATH.read_text()
    print(f"Target: Starlette routing.py ({len(source_code)} chars)")

    t0 = time.time()

    r1 = test1_l12_confidence(source_code)
    r2 = test2_complementarity(source_code)

    elapsed = time.time() - t0

    print("\n" + "=" * 60)
    print(f"  COMPLETE — {elapsed:.0f}s total")
    print("=" * 60)

    # Save
    save = {"test1_l12": r1, "test2_complementarity": {
        "vs_l12": r2["vs_l12"], "pairwise": r2["pairwise"], "output_sizes": r2["outputs"]}}
    (OUT / "results.json").write_text(json.dumps(save, indent=2))
    print(f"All outputs: {OUT}")


if __name__ == "__main__":
    main()

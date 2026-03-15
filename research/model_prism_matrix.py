#!/usr/bin/env python3
"""model_prism_matrix.py — Definitive model × prism test.

Phase 1: 6 core prisms × 3 models = 18 runs → optimal model per prism
Phase 2: 4 overlap candidates on best model = 4 runs → confirm redundancy
Phase 3: Adversarial + Synthesis × 3 models = 6 runs → optimal pipeline roles

All on Starlette routing.py, scored by Haiku judge.
"""
import json, os, re, subprocess, tempfile, time, threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

PRISM_DIR = Path("./prisms")
OUT = Path("/tmp/model_matrix")
OUT.mkdir(exist_ok=True)

STARLETTE_PATH = Path("./real_code_starlette.py")

MODELS = ["haiku", "sonnet", "opus"]

CORE_PRISMS = ["l12", "deep_scan", "fix_cascade", "identity", "optimize", "error_resilience"]
OVERLAP_PRISMS = ["sdl_trust", "sdl_coupling", "evolution", "api_surface"]

SCORING_RUBRIC = """Rate this structural code analysis on a 1-10 scale.

Anchors:
10 = Conservation law + meta-law + 15+ bugs with exact line refs + structural vs fixable + novel cross-dimensional finding
9 = Conservation law + bugs with locations + clear structural insight beyond surface
8 = Multiple concrete bugs + deeper pattern identified + some structural reasoning
7 = Real issues found + some structural reasoning but no conservation law or deeper pattern
6 = Surface code review with structural observations
5 = Generic code review
3 = Summary or restating
1 = Empty or off-topic

Key quality signals: Does it find things a senior engineer would miss? Does it name a structural property (not just list bugs)? Does it predict what is fixable vs structural?

Output ONLY a single number (1-10), nothing else."""

LOCK = threading.Lock()
RESULTS = {}


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


def score_output(output):
    text, _, _ = call_claude(SCORING_RUBRIC, output[:15000], model="haiku", timeout=60)
    try:
        s = float(re.search(r'\d+\.?\d*', text.strip()).group())
        return min(10, max(1, s))
    except:
        return -1


def run_prism_on_model(prism_name, model, source_code, label=""):
    """Run a single prism on a single model. Returns dict with results."""
    prism_text = load_prism(prism_name)
    if not prism_text:
        return {"error": f"Missing prism: {prism_name}"}

    tag = f"{prism_name}_{model}"
    text, cost, dur = call_claude(prism_text, source_code, model=model)

    # Check for failure
    if text.startswith("FAILED:"):
        print(f"  {tag}: FAILED ({dur:.0f}s)")
        return {"prism": prism_name, "model": model, "chars": 0,
                "cost": cost, "time": dur, "score": -1, "failed": True}

    # Save output
    (OUT / f"{tag}.txt").write_text(text)

    # Score
    score = score_output(text)

    result = {
        "prism": prism_name, "model": model, "chars": len(text),
        "cost": cost, "time": dur, "score": score
    }

    print(f"  {tag}: {len(text)}c, {dur:.0f}s, score={score}, ${cost:.4f}")

    with LOCK:
        RESULTS[tag] = result

    return result


def phase1_model_matrix(source_code):
    """Phase 1: 6 core prisms × 3 models = 18 runs."""
    print("\n" + "=" * 60)
    print("  PHASE 1: Model × Prism Matrix (18 runs)")
    print("=" * 60)

    tasks = []
    for prism in CORE_PRISMS:
        for model in MODELS:
            tasks.append((prism, model))

    # Run with limited parallelism (don't overwhelm API)
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = []
        for prism, model in tasks:
            f = ex.submit(run_prism_on_model, prism, model, source_code)
            futures.append((prism, model, f))

        for prism, model, f in futures:
            try:
                f.result(timeout=400)
            except Exception as e:
                print(f"  {prism}_{model}: ERROR: {e}")


def phase2_overlap_test(source_code):
    """Phase 2: 4 overlap candidates on best model per overlap pair."""
    print("\n" + "=" * 60)
    print("  PHASE 2: Overlap Candidates (4 runs)")
    print("=" * 60)

    # Run overlap prisms on haiku (cheapest, sufficient for overlap detection)
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = []
        for prism in OVERLAP_PRISMS:
            f = ex.submit(run_prism_on_model, prism, "haiku", source_code)
            futures.append(f)
        for f in futures:
            try:
                f.result(timeout=400)
            except Exception as e:
                print(f"  ERROR: {e}")


def phase3_pipeline_roles(source_code):
    """Phase 3: Adversarial + Synthesis × 3 models."""
    print("\n" + "=" * 60)
    print("  PHASE 3: Pipeline Roles (6 runs)")
    print("=" * 60)

    # Use best L12 output for adversarial input
    # Find which L12 model produced best output
    best_l12_model = "haiku"
    best_l12_score = 0
    for model in MODELS:
        key = f"l12_{model}"
        if key in RESULTS and RESULTS[key].get("score", 0) > best_l12_score:
            best_l12_score = RESULTS[key]["score"]
            best_l12_model = model

    l12_output_path = OUT / f"l12_{best_l12_model}.txt"
    if not l12_output_path.exists():
        print(f"  No L12 output found, using haiku")
        l12_output_path = OUT / "l12_haiku.txt"

    l12_text = l12_output_path.read_text() if l12_output_path.exists() else ""

    adv_prism = load_prism("l12_complement_adversarial")
    synth_prism = load_prism("l12_synthesis")

    if not adv_prism or not synth_prism:
        print("  Missing adversarial or synthesis prism")
        return

    # Adversarial × 3 models
    adv_results = {}
    for model in MODELS:
        tag = f"adversarial_{model}"
        msg = f"# SOURCE CODE\n\n{source_code}\n\n---\n\n# ANALYSIS 1\n\n{l12_text}"
        text, cost, dur = call_claude(adv_prism, msg, model=model)

        if not text.startswith("FAILED:"):
            (OUT / f"{tag}.txt").write_text(text)
            score = score_output(text)
            adv_results[model] = text
        else:
            score = -1

        result = {"prism": "adversarial", "model": model, "chars": len(text),
                  "cost": cost, "time": dur, "score": score}
        RESULTS[tag] = result
        print(f"  {tag}: {len(text)}c, {dur:.0f}s, score={score}")

    # Use best adversarial for synthesis input
    best_adv_model = max(adv_results.keys(),
                         key=lambda m: RESULTS[f"adversarial_{m}"].get("score", 0))
    adv_text = adv_results.get(best_adv_model, "")

    # Synthesis × 3 models
    for model in MODELS:
        tag = f"synthesis_{model}"
        msg = (f"# SOURCE CODE\n\n{source_code}\n\n---\n\n"
               f"# ANALYSIS 1\n\n{l12_text}\n\n---\n\n"
               f"# ANALYSIS 2\n\n{adv_text}")
        text, cost, dur = call_claude(synth_prism, msg, model=model)

        if not text.startswith("FAILED:"):
            (OUT / f"{tag}.txt").write_text(text)
            score = score_output(text)
        else:
            score = -1

        result = {"prism": "synthesis", "model": model, "chars": len(text),
                  "cost": cost, "time": dur, "score": score}
        RESULTS[tag] = result
        print(f"  {tag}: {len(text)}c, {dur:.0f}s, score={score}")


def print_report():
    """Print comprehensive results report."""
    print("\n" + "=" * 60)
    print("  RESULTS: Model × Prism Matrix")
    print("=" * 60)

    # Phase 1: Core prisms
    print(f"\n{'Prism':<20} {'Haiku':>12} {'Sonnet':>12} {'Opus':>12} {'Best':>8}")
    print("-" * 66)

    optimal = {}
    for prism in CORE_PRISMS:
        scores = {}
        for model in MODELS:
            key = f"{prism}_{model}"
            r = RESULTS.get(key, {})
            s = r.get("score", -1)
            c = r.get("chars", 0)
            scores[model] = (s, c)

        best_model = max(scores.keys(), key=lambda m: (scores[m][0], scores[m][1]))
        optimal[prism] = best_model

        parts = []
        for model in MODELS:
            s, c = scores[model]
            marker = " *" if model == best_model else ""
            parts.append(f"{s:>5} ({c//1000}K){marker}")

        print(f"{prism:<20} {'  '.join(parts)}  → {best_model}")

    # Phase 2: Overlap candidates
    print(f"\n{'Overlap Prism':<20} {'Haiku Score':>12} {'Overlaps With':>20}")
    print("-" * 55)

    overlap_map = {
        "sdl_trust": "error_resilience",
        "sdl_coupling": "evolution",
        "evolution": "sdl_coupling",
        "api_surface": "identity",
    }

    for prism in OVERLAP_PRISMS:
        key = f"{prism}_haiku"
        r = RESULTS.get(key, {})
        s = r.get("score", -1)
        overlaps = overlap_map.get(prism, "?")
        print(f"{prism:<20} {s:>12} {overlaps:>20}")

    # Phase 3: Pipeline roles
    print(f"\n{'Role':<20} {'Haiku':>12} {'Sonnet':>12} {'Opus':>12} {'Best':>8}")
    print("-" * 66)

    for role in ["adversarial", "synthesis"]:
        scores = {}
        for model in MODELS:
            key = f"{role}_{model}"
            r = RESULTS.get(key, {})
            s = r.get("score", -1)
            c = r.get("chars", 0)
            scores[model] = (s, c)

        best = max(scores.keys(), key=lambda m: (scores[m][0], scores[m][1]))
        optimal[role] = best

        parts = []
        for model in MODELS:
            s, c = scores[model]
            marker = " *" if model == best else ""
            parts.append(f"{s:>5} ({c//1000}K){marker}")

        print(f"{role:<20} {'  '.join(parts)}  → {best}")

    # Final configuration
    print(f"\n" + "=" * 60)
    print("  OPTIMAL CONFIGURATION")
    print("=" * 60)
    total_cost = 0
    for prism in CORE_PRISMS:
        model = optimal.get(prism, "haiku")
        key = f"{prism}_{model}"
        r = RESULTS.get(key, {})
        cost = r.get("cost", 0)
        total_cost += cost
        print(f"  {prism:<20} → {model:<8} (score={r.get('score', '?')}, "
              f"{r.get('chars', 0)//1000}K chars)")

    for role in ["adversarial", "synthesis"]:
        model = optimal.get(role, "haiku")
        key = f"{role}_{model}"
        r = RESULTS.get(key, {})
        cost = r.get("cost", 0)
        total_cost += cost
        print(f"  {role:<20} → {model:<8} (score={r.get('score', '?')}, "
              f"{r.get('chars', 0)//1000}K chars)")

    print(f"\n  Estimated cost per full scan: ${total_cost:.4f}")

    return optimal


def main():
    print("=" * 60)
    print("  MODEL × PRISM MATRIX — Definitive Test")
    print("=" * 60)

    source_code = STARLETTE_PATH.read_text()
    print(f"Target: Starlette routing.py ({len(source_code)} chars)")
    print(f"Models: {MODELS}")
    print(f"Core prisms: {CORE_PRISMS}")
    print(f"Overlap candidates: {OVERLAP_PRISMS}")

    t0 = time.time()

    phase1_model_matrix(source_code)
    phase2_overlap_test(source_code)
    phase3_pipeline_roles(source_code)

    optimal = print_report()

    elapsed = time.time() - t0
    print(f"\nTotal time: {elapsed:.0f}s")
    print(f"Total runs: {len(RESULTS)}")

    # Save everything
    (OUT / "results.json").write_text(json.dumps(RESULTS, indent=2))
    (OUT / "optimal.json").write_text(json.dumps(optimal, indent=2))
    print(f"All outputs: {OUT}")


if __name__ == "__main__":
    main()

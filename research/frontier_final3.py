#!/usr/bin/env python3
"""frontier_final3.py — Three remaining frontier experiments.

14. Model-Specific Prisms (Opus-optimized vs Haiku-optimized)
15. Multi-target Hybrid Validation (evidence_cost on 5 targets)
16. Adaptive Compression (find each prism's compression floor)
"""
import concurrent.futures, json, os, re, subprocess, tempfile, time, threading
from pathlib import Path

PRISM_DIR = Path("./prisms")
OUT = Path("/tmp/frontier_final3")
OUT.mkdir(exist_ok=True)

MAX_WORKERS = 4
ALL_RESULTS = {}
LOCK = threading.Lock()


def call_claude(system_prompt, user_input, model="haiku", timeout=180):
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
    return strip_fm(p.read_text()) if p.exists() else ""


def load_code(name):
    paths = {
        "starlette": "./real_code_starlette.py",
        "click": "./real_code_click.py",
        "tenacity": "./real_code_tenacity.py",
    }
    return Path(paths[name]).read_text() if name in paths else ""


SCORE_RUBRIC = (
    "You are scoring structural code analysis quality on a 1-10 scale.\n\n"
    "Score anchors:\n"
    "- 10: Conservation law with math form + line numbers + structural impossibility + actionable table\n"
    "- 9-9.5: Genuine structural properties, conservation law, specific locations, surprising findings, table\n"
    "- 8.5-9: Good structural depth, some invariant, specific enough to act on\n"
    "- 8-8.5: Solid with citations but conservation law generic or missing\n"
    "- 7-7.5: Standard code review - finds bugs, names patterns, no structural insight\n"
    "- 6 and below: Generic observations, no specific citations\n\n"
    "Output ONLY a single number (e.g., 8.5). Nothing else."
)


def score(text):
    if not text or len(text) < 200 or "FAILED" in text[:50]:
        return -1.0
    scored = text[:5000]
    raw, _, _ = call_claude(SCORE_RUBRIC, f"## Analysis:\n\n{scored}", "haiku", 60)
    try:
        nums = re.findall(r"\b(\d+\.?\d*)\b", raw.strip())
        s = float(nums[0]) if nums else -1
        return s if 1 <= s <= 10 else -1
    except:
        return -1.0


def save(key, text):
    (OUT / f"{key}.txt").write_text(text or "EMPTY")


def save_prism(key, text):
    (OUT / f"{key}.md").write_text(text or "EMPTY")


# ── Embedded Go/TS targets (from frontier_5x) ──────────────────────

GO_ROUTER = open("/tmp/frontier_5x/exp3_error_resilience_go.txt").read()[:100]  # just need a flag
# Actually, load from the frontier_5x script or re-embed. Simpler: use starlette for all.

# ── Experiment 14: Model-Specific Prisms ────────────────────────────

COOK_MODEL_SPECIFIC = (
    "Design a 3-step structural analysis lens (130-180 words) optimized specifically "
    "for execution by {target_model}.\n\n"
    "{model_guidance}\n\n"
    "The lens should analyze code for: {goal}\n\n"
    "Rules:\n"
    '- First line: "Execute every step below. Output the complete analysis."\n'
    "- Exactly 3 ## Step sections\n"
    "- Step 3 must name a conservation law and include a | table | format\n"
    "- 130-180 words total\n\n"
    "Output ONLY the lens text. No explanation."
)

HAIKU_GUIDANCE = (
    "Haiku characteristics to exploit:\n"
    "- Excels at mechanistic coverage and classification\n"
    "- Best with concrete search patterns (specific code constructs to find)\n"
    "- Needs explicit table format to structure output\n"
    "- Struggles with abstract judgment calls - give it concrete criteria instead\n"
    "- Optimal at 3 steps with imperative verbs\n"
    "- Loses quality with >150 words (keep tight)\n"
    "- 'NOT X but Y' negative examples kill generic responses"
)

OPUS_GUIDANCE = (
    "Opus characteristics to exploit:\n"
    "- Excels at ontological depth and naming what things ARE\n"
    "- Spontaneous mathematical formalization of trade-offs\n"
    "- Can handle abstract instructions that would confuse Haiku\n"
    "- Produces richer conservation laws with mathematical form\n"
    "- Benefits from philosophical framing (impossibility, necessity)\n"
    "- Can process longer, more nuanced instructions (up to 200w)\n"
    "- Self-generates structure without explicit table templates"
)

ERRRES_GOAL = (
    "error resilience - find where failure information is destroyed, "
    "trace corruption cascades through multiple hops, name the structural invariant"
)


def run_exp14():
    print("\n" + "=" * 60)
    print("  EXP 14: Model-Specific Prisms")
    print("=" * 60)
    starlette = load_code("starlette")
    results = {}

    # Cook Haiku-optimized ErrRes (using Opus as cooker)
    def cook_and_test(target_model, guidance, label):
        cooked, _, _ = call_claude(
            COOK_MODEL_SPECIFIC.format(
                target_model=target_model,
                model_guidance=guidance,
                goal=ERRRES_GOAL),
            f"Design the lens for {target_model} now.",
            model="opus", timeout=300)
        if not cooked or len(cooked) < 80:
            return label, {"score": -1, "cook": "FAILED"}
        save_prism(f"model_specific_{label}", cooked)

        # Run on target model
        out, _, _ = call_claude(
            cooked, f"Analyze this code.\n\n```python\n{starlette}\n```",
            model=target_model.split()[0].lower(), timeout=180)
        save(f"exp14_{label}", out)
        s = score(out)

        # Also run on OTHER model for comparison
        other = "sonnet" if "haiku" in target_model.lower() else "haiku"
        out2, _, _ = call_claude(
            cooked, f"Analyze this code.\n\n```python\n{starlette}\n```",
            model=other, timeout=180)
        save(f"exp14_{label}_on_{other}", out2)
        s2 = score(out2)

        return label, {
            "target_score": s, "other_score": s2,
            "target_chars": len(out or ""), "other_chars": len(out2 or ""),
            "words": len(cooked.split()),
        }

    # Also run generic ErrRes on both models as baseline
    def run_generic(model):
        errres = load_prism("error_resilience")
        out, _, _ = call_claude(
            errres, f"Analyze this code.\n\n```python\n{starlette}\n```",
            model=model, timeout=180)
        save(f"exp14_generic_{model}", out)
        s = score(out)
        return f"generic_{model}", {"score": s, "chars": len(out or "")}

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = [
            ex.submit(cook_and_test, "Haiku (Claude haiku-4.5)", HAIKU_GUIDANCE, "haiku_optimized"),
            ex.submit(cook_and_test, "Opus (Claude opus-4.6)", OPUS_GUIDANCE, "opus_optimized"),
            ex.submit(run_generic, "haiku"),
            ex.submit(run_generic, "sonnet"),
        ]
        for f in concurrent.futures.as_completed(futs):
            label, data = f.result()
            results[label] = data
            if "target_score" in data:
                print(f"  {label:20s} target={data['target_score']:4.1f}  "
                      f"other={data['other_score']:4.1f}  ({data['words']}w)")
            else:
                print(f"  {label:20s} score={data['score']:4.1f}  ({data['chars']}c)")

    ALL_RESULTS["exp14"] = results
    return results


# ── Experiment 15: Multi-target Hybrid Validation ───────────────────

def run_exp15():
    print("\n" + "=" * 60)
    print("  EXP 15: Multi-target Hybrid Validation")
    print("=" * 60)
    evidence_cost = load_prism("evidence_cost")
    if not evidence_cost:
        # Load from frontier_5x output
        p = Path("/tmp/frontier_5x/hybrid_error_resilience_optim.md")
        evidence_cost = p.read_text() if p.exists() else ""
    if not evidence_cost:
        print("  ERROR: evidence_cost prism not found")
        return {}

    targets = {
        "starlette": load_code("starlette"),
        "click": load_code("click"),
        "tenacity": load_code("tenacity"),
    }
    # Also test parents for comparison on each target
    parents = {
        "error_resilience": load_prism("error_resilience"),
        "optimize": load_prism("optimize"),
    }
    results = {}

    def run_one(prism_name, prism_text, target_name, code):
        out, _, _ = call_claude(
            prism_text, f"Analyze this code.\n\n```python\n{code}\n```")
        key = f"{prism_name}_{target_name}"
        save(f"exp15_{key}", out)
        s = score(out)
        return prism_name, target_name, s, len(out or "")

    tasks = []
    for tname, code in targets.items():
        tasks.append(("evidence_cost", evidence_cost, tname, code))
        for pname, ptext in parents.items():
            tasks.append((pname, ptext, tname, code))

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = [ex.submit(run_one, *t) for t in tasks]
        for f in concurrent.futures.as_completed(futs):
            pn, tn, s, chars = f.result()
            results.setdefault(pn, {})[tn] = {"score": s, "chars": chars}
            print(f"  {pn:20s} x {tn:12s} -> {s:4.1f}  ({chars}c)")

    ALL_RESULTS["exp15"] = results
    return results


# ── Experiment 16: Adaptive Compression ─────────────────────────────

COMPRESS_STEP = (
    "Compress this structural analysis lens to EXACTLY {target} words (+-5 words).\n\n"
    "CRITICAL rules:\n"
    "- Keep exactly 3 ## Step sections\n"
    '- Keep "Execute every step below. Output the complete analysis." first line\n'
    "- Preserve ALL specific search patterns (the active ingredients)\n"
    "- Preserve Step 3 table format\n"
    "- Cut ONLY connective tissue and redundant elaboration\n"
    "- The compressed version must still produce a conservation law\n\n"
    "LENS:\n{lens}\n\n"
    "Output ONLY the compressed lens. Nothing else. No explanation."
)


def run_exp16():
    print("\n" + "=" * 60)
    print("  EXP 16: Adaptive Compression")
    print("=" * 60)
    starlette = load_code("starlette")

    # Test all behavioral prisms at multiple compression levels
    prisms = {
        "error_resilience": 165,
        "optimize": 120,
        "evolution": 130,
        "api_surface": 130,
        "evidence_cost": 160,
    }
    # Binary search: for each prism, find the compression floor
    # where quality drops below 8.0 (our "good enough" threshold)
    targets = [60, 70, 80, 90]  # aggressive compression targets
    results = {}

    def compress_and_test(name, target_w):
        original = load_prism(name)
        if not original:
            # Try frontier_5x output
            p = Path(f"/tmp/frontier_5x/hybrid_error_resilience_optim.md")
            if name == "evidence_cost" and p.exists():
                original = p.read_text()
            else:
                return name, target_w, None

        current_w = len(original.split())
        if current_w <= target_w + 5:
            return name, target_w, None  # already at or below target

        compressed, _, _ = call_claude(
            COMPRESS_STEP.format(target=target_w, lens=original),
            "Compress now.", model="sonnet", timeout=120)
        if not compressed or len(compressed) < 30:
            return name, target_w, {"score": -1, "words": 0}

        actual_w = len(compressed.split())
        save_prism(f"adaptive_{name}_{target_w}w", compressed)

        # Run on starlette
        out, _, _ = call_claude(
            compressed, f"Analyze this code.\n\n```python\n{starlette}\n```")
        save(f"exp16_{name}_{target_w}w", out)
        s = score(out)
        return name, target_w, {
            "score": s, "words": actual_w, "chars": len(out or ""),
        }

    tasks = [(n, t) for n in prisms for t in targets
             if prisms[n] > t + 5]

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = [ex.submit(compress_and_test, n, t) for n, t in tasks]
        for f in concurrent.futures.as_completed(futs):
            name, tw, data = f.result()
            if data is None:
                continue
            results.setdefault(name, {})[tw] = data
            print(f"  {name:20s} {tw}w -> {data['score']:4.1f}  "
                  f"(actual={data['words']}w, out={data.get('chars',0)}c)")

    # Find compression floor for each prism
    print("\n  --- Compression Floors ---")
    for name in prisms:
        row = results.get(name, {})
        if not row:
            continue
        floor = None
        for tw in sorted(row.keys(), reverse=True):
            if row[tw]["score"] >= 8.0:
                floor = tw
            else:
                break
        if floor:
            print(f"  {name:20s} floor={floor}w  (score={row[floor]['score']:.1f})")
        else:
            best = max(row.items(), key=lambda x: x[1]["score"]) if row else None
            if best:
                print(f"  {name:20s} no floor>=8.0  (best={best[0]}w at {best[1]['score']:.1f})")

    ALL_RESULTS["exp16"] = results
    return results


# ── Main ────────────────────────────────────────────────────────────

def main():
    t0 = time.time()
    print("=" * 60)
    print("  FRONTIER FINAL 3 — Last Three Experiments")
    print("=" * 60)

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        f14 = ex.submit(run_exp14)
        f15 = ex.submit(run_exp15)
        f16 = ex.submit(run_exp16)

        r14 = f14.result()
        r15 = f15.result()
        r16 = f16.result()

    elapsed = time.time() - t0

    print("\n" + "=" * 60)
    print("  FINAL REPORT")
    print("=" * 60)

    print("\n-- EXP 14: Model-Specific Prisms --")
    if r14:
        # Compare: Haiku-optimized on Haiku vs generic on Haiku
        ho = r14.get("haiku_optimized", {})
        oo = r14.get("opus_optimized", {})
        gh = r14.get("generic_haiku", {})
        gs = r14.get("generic_sonnet", {})
        print(f"  {'Prism':25s} {'Haiku':>6s} {'Sonnet':>7s}")
        print(f"  {'Generic ErrRes':25s} {gh.get('score',-1):6.1f} {gs.get('score',-1):7.1f}")
        print(f"  {'Haiku-optimized':25s} {ho.get('target_score',-1):6.1f} {ho.get('other_score',-1):7.1f}")
        print(f"  {'Opus-optimized':25s} {oo.get('other_score',-1):6.1f} {oo.get('target_score',-1):7.1f}")

    print("\n-- EXP 15: Hybrid Validation (evidence_cost) --")
    if r15:
        print(f"  {'Prism':20s} {'Starlette':>9s} {'Click':>6s} {'Tenacity':>9s}")
        for pn in ["evidence_cost", "error_resilience", "optimize"]:
            row = r15.get(pn, {})
            vals = []
            for tn in ["starlette", "click", "tenacity"]:
                d = row.get(tn)
                vals.append(f"{d['score']:6.1f}" if d and d["score"] > 0 else "    -  ")
            print(f"  {pn:20s} {'  '.join(vals)}")

    print("\n-- EXP 16: Adaptive Compression Floors --")
    if r16:
        print(f"  {'Prism':20s} {'60w':>5s} {'70w':>5s} {'80w':>5s} {'90w':>5s}  Floor")
        for name in ["error_resilience", "optimize", "evolution", "api_surface", "evidence_cost"]:
            row = r16.get(name, {})
            vals = []
            floor_w = None
            for tw in [60, 70, 80, 90]:
                d = row.get(tw)
                if d and d["score"] > 0:
                    vals.append(f"{d['score']:4.1f}")
                    if d["score"] >= 8.0 and (floor_w is None or tw < floor_w):
                        floor_w = tw
                else:
                    vals.append("  -  ")
            floor_s = f"{floor_w}w" if floor_w else "none"
            print(f"  {name:20s} {' '.join(vals)}  {floor_s}")

    print(f"\n  Total time: {elapsed:.0f}s")
    print(f"  All outputs: {OUT}/")

    with open(OUT / "results.json", "w") as f:
        json.dump(ALL_RESULTS, f, indent=2, default=str)
    print(f"  Results JSON: {OUT}/results.json")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""self_analysis.py — Run the full 8-step champion pipeline on prism.py itself.

This is the definitive self-analysis: all 8 validated prisms at their optimal
models, analyzing the tool that contains them. Captures the full report.
"""
import json, os, re, subprocess, tempfile, time
from pathlib import Path

PRISM_DIR = Path("/home/claude/insights/prisms")
OUT = Path("/tmp/self_analysis")
OUT.mkdir(exist_ok=True)

TARGET = Path("/home/claude/insights/prism.py")

MODEL_MAP = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-6",
}

# The validated optimal grid
PIPELINE = [
    {"prism": "l12", "role": "L12 STRUCTURAL", "model": "sonnet", "chain": False},
    {"prism": "deep_scan", "role": "DEEP SCAN", "model": "opus", "chain": False},
    {"prism": "fix_cascade", "role": "RECURSIVE ENTAILMENT", "model": "opus", "chain": False},
    {"prism": "identity", "role": "IDENTITY DISPLACEMENT", "model": "sonnet", "chain": False},
    {"prism": "optimize", "role": "OPTIMIZATION COSTS", "model": "sonnet", "chain": False},
    {"prism": "error_resilience", "role": "ERROR RESILIENCE", "model": "sonnet", "chain": False},
    {"prism": "l12_complement_adversarial", "role": "ADVERSARIAL", "model": "opus", "chain": True},
    {"prism": "l12_synthesis", "role": "SYNTHESIS", "model": "opus", "chain": True},
]


def call_claude(system_prompt, user_input, model="sonnet", timeout=600):
    """Call Claude CLI with system prompt and user input."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(system_prompt)
        sp_path = f.name

    resolved = MODEL_MAP.get(model, model)
    env = {k: v for k, v in os.environ.items() if "CLAUDE" not in k.upper()}
    cmd = ["claude", "-p", "--tools", "", "--model", resolved,
           "--output-format", "json", "--system-prompt-file", sp_path]

    t0 = time.time()
    try:
        r = subprocess.run(cmd, input=user_input, capture_output=True,
                          text=True, timeout=timeout, env=env)
        data = json.loads(r.stdout)
        text = data.get("result", "")
        cost = data.get("cost_usd", 0)
    except subprocess.TimeoutExpired:
        text, cost = f"TIMEOUT after {timeout}s", 0
    except Exception as e:
        text, cost = f"FAILED: {e}", 0
    finally:
        try:
            os.unlink(sp_path)
        except:
            pass

    dur = time.time() - t0
    return text, cost, dur


def strip_fm(text):
    """Strip YAML frontmatter from prism file."""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return text


def load_prism(name):
    """Load a prism by name, stripping frontmatter."""
    p = PRISM_DIR / f"{name}.md"
    if p.exists():
        return strip_fm(p.read_text())
    return None


def main():
    print("=" * 70)
    print("  FULL PIPELINE SELF-ANALYSIS: prism.py")
    print("  8-step champion pipeline at optimal models")
    print("=" * 70)

    source_code = TARGET.read_text()
    print(f"Target: prism.py ({len(source_code)} chars, {source_code.count(chr(10))} lines)")

    # prism.py is large — use first ~100K chars if needed
    # (Claude can handle ~200K tokens, 440K chars is ~110K tokens)
    if len(source_code) > 200_000:
        print(f"  WARNING: Truncating to 200K chars (was {len(source_code)})")
        source_code = source_code[:200_000]

    t0 = time.time()
    outputs = {}
    output_list = []
    total_cost = 0

    for i, step in enumerate(PIPELINE):
        prism_name = step["prism"]
        role = step["role"]
        model = step["model"]
        chain = step["chain"]

        print(f"\n{'=' * 70}")
        print(f"  Step {i+1}/8: {role}")
        print(f"  Prism: {prism_name} | Model: {model} | {'CHAIN' if chain else 'INDEPENDENT'}")
        print(f"{'=' * 70}")

        prism_text = load_prism(prism_name)
        if not prism_text:
            print(f"  MISSING prism: {prism_name}")
            continue

        # Build message
        if not chain:
            msg = f"Analyze this source code.\n\n{source_code}"
        elif prism_name == "l12_complement_adversarial":
            l12_out = outputs.get("l12", "")
            if not l12_out:
                print(f"  No L12 output — skipping adversarial")
                continue
            msg = f"# SOURCE CODE\n\n{source_code}\n\n---\n\n# ANALYSIS 1\n\n{l12_out}"
        else:
            # Synthesis: source + all prior
            parts = [f"# SOURCE CODE\n\n{source_code}"]
            for j, (prev_step, prev_out) in enumerate(output_list):
                parts.append(f"# ANALYSIS {j+1}: {prev_step['role']}\n\n{prev_out}")
            msg = "\n\n---\n\n".join(parts)
            # Truncate if too large for synthesis
            if len(msg) > 150_000:
                print(f"  Truncating synthesis input: {len(msg)} → 150K chars")
                msg = msg[:150_000] + "\n\n[... truncated ...]"

        # Timeout: longer for Opus (generates more), longer for synthesis (bigger input)
        timeout = 600 if model == "opus" or chain else 400

        text, cost, dur = call_claude(prism_text, msg, model=model, timeout=timeout)
        total_cost += cost

        if text.startswith("TIMEOUT") or text.startswith("FAILED"):
            print(f"  {text}")
            continue

        # Save individual output
        out_path = OUT / f"step{i+1}_{prism_name}.txt"
        out_path.write_text(text)
        outputs[prism_name] = text
        output_list.append((step, text))

        print(f"  {len(text)} chars, {dur:.0f}s, ${cost:.4f}")

    elapsed = time.time() - t0

    # Build combined report
    print(f"\n{'=' * 70}")
    print(f"  BUILDING COMBINED REPORT")
    print(f"{'=' * 70}")

    report_parts = [
        f"# Full Pipeline Analysis: prism.py\n",
        f"**Target**: prism.py ({TARGET.stat().st_size} bytes, "
        f"{source_code.count(chr(10))} lines)\n",
        f"**Pipeline**: 8-step static champion pipeline\n",
        f"**Total time**: {elapsed:.0f}s\n",
        f"**Total cost**: ${total_cost:.4f}\n",
        f"**Steps completed**: {len(output_list)}/{len(PIPELINE)}\n",
    ]

    for step, out in output_list:
        model = step["model"]
        report_parts.append(
            f"\n---\n\n"
            f"## {step['role']} ({step['prism']} on {model})\n\n{out}")

    report = "\n".join(report_parts)
    report_path = OUT / "full_report.md"
    report_path.write_text(report)

    # Also save metadata
    meta = {
        "target": str(TARGET),
        "target_chars": len(source_code),
        "target_lines": source_code.count("\n"),
        "total_time": elapsed,
        "total_cost": total_cost,
        "steps_completed": len(output_list),
        "steps_total": len(PIPELINE),
        "step_details": [],
    }
    for step, out in output_list:
        meta["step_details"].append({
            "prism": step["prism"],
            "role": step["role"],
            "model": step["model"],
            "output_chars": len(out),
        })
    (OUT / "meta.json").write_text(json.dumps(meta, indent=2))

    print(f"\n{'=' * 70}")
    print(f"  COMPLETE")
    print(f"{'=' * 70}")
    print(f"  Steps: {len(output_list)}/{len(PIPELINE)}")
    print(f"  Total output: {sum(len(o) for _, o in output_list)} chars")
    print(f"  Time: {elapsed:.0f}s")
    print(f"  Cost: ${total_cost:.4f}")
    print(f"  Report: {report_path}")
    print(f"  All outputs: {OUT}")

    # Print summary of each step
    print(f"\n  {'Step':<5} {'Role':<25} {'Model':<8} {'Chars':>8}")
    print(f"  {'-'*50}")
    for step, out in output_list:
        print(f"  {PIPELINE.index(step)+1:<5} {step['role']:<25} {step['model']:<8} {len(out):>8}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Test the 'full' champion: L12 alone vs Enhanced L12 (A) vs L12→Complement (B).
Uses claude CLI via subprocess (works with subscription).
"""
import subprocess, os, sys, shutil, time, pathlib, tempfile

ROOT = pathlib.Path(__file__).parent.parent
CLAUDE = shutil.which("claude") or "claude"
MODEL = "haiku"
OUTDIR = ROOT / "output" / "combo_test"
OUTDIR.mkdir(parents=True, exist_ok=True)

def call_claude(system_prompt_text, user_content, label=""):
    """Single claude -p call. Returns response text."""
    print(f"  {label}...", end="", flush=True)
    # Write system prompt to temp file
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8")
    tmp.write(system_prompt_text)
    tmp.close()

    t0 = time.time()
    try:
        proc = subprocess.run(
            [CLAUDE, "-p", "--model", MODEL, "--output-format", "text", "--tools", "",
             "--system-prompt-file", tmp.name],
            input=user_content, capture_output=True, text=True, encoding="utf-8",
            timeout=300, env={**os.environ, "CLAUDECODE": ""},
        )
        elapsed = time.time() - t0
        output = proc.stdout.strip()
        if proc.returncode != 0 or not output:
            print(f" FAIL (exit={proc.returncode}, {elapsed:.0f}s)")
            if proc.stderr:
                print(f"    stderr: {proc.stderr[:200]}")
            return ""
        lines = len(output.splitlines())
        print(f" {lines} lines, {elapsed:.0f}s")
        return output
    except subprocess.TimeoutExpired:
        print(f" TIMEOUT")
        return ""
    finally:
        os.unlink(tmp.name)

def load(relpath):
    return (ROOT / relpath).read_text(encoding="utf-8")

def run_target(target_name):
    code = load(f"research/real_code_{target_name}.py")

    print(f"\n{'='*60}")
    print(f"  TARGET: {target_name}")
    print(f"{'='*60}")

    # --- Baseline: L12 alone ---
    print("\n[BASELINE] L12 alone (1 call)")
    l12_prompt = load("prisms/l12.md")
    baseline = call_claude(l12_prompt, code, "L12")
    (OUTDIR / f"baseline_{target_name}.md").write_text(baseline, encoding="utf-8")

    # --- Architecture A: Enhanced L12 (1 call) ---
    print("\n[ARCH A] Enhanced L12 — L12 + complement in single prompt (1 call)")
    l12_full = load("prisms/l12_full.md")
    arch_a = call_claude(l12_full, code, "L12-full")
    (OUTDIR / f"archA_{target_name}.md").write_text(arch_a, encoding="utf-8")

    # --- Architecture B: L12 → Informed Complement (2 calls) ---
    print("\n[ARCH B] L12 → Complement (2 calls)")
    # Call 1: reuse baseline L12 output
    b_l12 = baseline
    print(f"  (reusing baseline L12 for call 1)")
    # Call 2: complement sees code + L12 output
    complement_prompt = load("prisms/l12_complement.md")
    combined = f"# SOURCE CODE\n\n{code}\n\n---\n\n# STRUCTURAL ANALYSIS (from previous pass)\n\n{b_l12}"
    arch_b = call_claude(complement_prompt, combined, "Complement")
    (OUTDIR / f"archB_{target_name}.md").write_text(arch_b, encoding="utf-8")

    # --- Summary ---
    print(f"\n  Results:")
    for name, text in [("baseline", baseline), ("archA", arch_a), ("archB", arch_b)]:
        lines = len(text.splitlines()) if text else 0
        fname = f"{name}_{target_name}.md"
        print(f"    {fname}: {lines} lines")

if __name__ == "__main__":
    targets = sys.argv[1:] if len(sys.argv) > 1 else ["starlette"]
    for t in targets:
        run_target(t)
    print("\nDone.")

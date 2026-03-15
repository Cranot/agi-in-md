#!/usr/bin/env python3
"""
Fix Reliability Experiment — Through Prism
============================================
Tests how reliably prism.py's native fix pipeline applies changes.

All fixing runs through `python3 prism.py --scan FILE fix auto`.
We only orchestrate the runs and measure outcomes via git + .deep/.

Experiments:
  A: Reliability Matrix — 3 targets × 2 models (haiku, sonnet)
  B: Confidence Analysis — correlate issue properties with fix outcomes
  C: Model Comparison — same issues, different models

Run on VPS (from ~/insights/):
  python3 research/fix_reliability.py                    # all experiments
  python3 research/fix_reliability.py --target starlette # one target
  python3 research/fix_reliability.py --model haiku      # one model
  python3 research/fix_reliability.py analyze             # just analyze
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────

TARGETS = {
    "starlette": "real_code_starlette.py",
    "click": "real_code_click.py",
    "tenacity": "real_code_tenacity.py",
}

MODELS = ["haiku", "sonnet"]

RESULTS_DIR = Path("_fix_reliability")
WORKSPACE = RESULTS_DIR / "workspace"

PRISM_CMD = "python3"
PRISM_PY = "prism.py"

# Timeout for the full scan-fix-loop (generous — includes scan + all fixes)
# Sonnet needs more time: scan alone can take 2-3min, each fix 1-2min
FIX_LOOP_TIMEOUT = 1200  # 20 minutes


# ── Workspace Management ─────────────────────────────────────────────────────

def setup_workspace(target_name, target_file):
    """Create a clean git workspace with the target file.

    Returns workspace path. The workspace is a git repo so we can
    measure diffs precisely.
    """
    ws = WORKSPACE / target_name
    if ws.exists():
        shutil.rmtree(ws)
    ws.mkdir(parents=True)

    # Copy target file
    src = Path(target_file)
    if not src.exists():
        # Try relative to script dir
        src = Path(__file__).parent.parent / target_file
    if not src.exists():
        print(f"  ERROR: target file not found: {target_file}")
        sys.exit(1)

    dst = ws / src.name
    shutil.copy2(src, dst)

    # Copy prism.py and prisms/ to workspace so prism can run
    prism_src = Path(PRISM_PY)
    if not prism_src.exists():
        prism_src = Path(__file__).parent.parent / PRISM_PY
    shutil.copy2(prism_src, ws / "prism.py")

    prisms_src = prism_src.parent / "prisms"
    if prisms_src.exists():
        shutil.copytree(prisms_src, ws / "prisms", dirs_exist_ok=True)

    prompts_src = prism_src.parent / "prompts"
    if prompts_src.exists():
        shutil.copytree(prompts_src, ws / "prompts", dirs_exist_ok=True)

    # Init git repo for diff tracking
    subprocess.run(["git", "init"], cwd=ws, capture_output=True)
    subprocess.run(["git", "add", src.name], cwd=ws, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=ws, capture_output=True,
        env={**os.environ, "GIT_AUTHOR_NAME": "test",
             "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "test",
             "GIT_COMMITTER_EMAIL": "t@t"},
    )

    return ws, dst


def reset_workspace(ws, target_file_name):
    """Reset workspace to clean state (git checkout)."""
    subprocess.run(
        ["git", "checkout", "--", target_file_name],
        cwd=ws, capture_output=True,
    )
    # Clean .deep/
    deep_dir = ws / ".deep"
    if deep_dir.exists():
        shutil.rmtree(deep_dir)


def get_diff(ws, target_file_name):
    """Get git diff for the target file."""
    result = subprocess.run(
        ["git", "diff", "--", target_file_name],
        cwd=ws, capture_output=True, text=True,
    )
    return result.stdout


def get_diff_stats(ws, target_file_name):
    """Get diff statistics."""
    result = subprocess.run(
        ["git", "diff", "--stat", "--", target_file_name],
        cwd=ws, capture_output=True, text=True,
    )
    return result.stdout.strip()


# ── Run Prism Fix ─────────────────────────────────────────────────────────────

def run_prism_fix(ws, target_file_name, model="haiku"):
    """Run prism.py --scan FILE fix auto in the workspace.

    Redirects stdout/stderr to files to preserve output on timeout.
    Returns (stdout, stderr, elapsed, returncode).
    """
    # "fix auto" must be part of --scan value (prism.py parses it internally)
    scan_arg = f"{target_file_name} fix auto"
    cmd = [
        PRISM_CMD, "prism.py",
        "--scan", scan_arg,
        "-m", model,
    ]

    # Write to files so output survives timeout
    stdout_file = ws / "_prism_stdout.txt"
    stderr_file = ws / "_prism_stderr.txt"

    print(f"    Running: {' '.join(cmd)}")
    start = time.time()

    with open(stdout_file, "w") as fout, open(stderr_file, "w") as ferr:
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=fout,
                stderr=ferr,
                text=True,
                cwd=str(ws),
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )
            rc = proc.wait(timeout=FIX_LOOP_TIMEOUT)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            rc = -1

    elapsed = time.time() - start

    stdout = stdout_file.read_text() if stdout_file.exists() else ""
    stderr = stderr_file.read_text() if stderr_file.exists() else ""
    if rc == -1:
        stderr += f"\nTIMEOUT after {FIX_LOOP_TIMEOUT}s"

    return stdout, stderr, elapsed, rc


# ── Issue Status Reader ──────────────────────────────────────────────────────

def read_issues(ws):
    """Read .deep/issues.json from workspace. Returns list of issues."""
    issues_path = ws / ".deep" / "issues.json"
    if not issues_path.exists():
        return []

    try:
        data = json.loads(issues_path.read_text())
    except (json.JSONDecodeError, OSError):
        return []

    # Handle both old (list) and new (dict) formats
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("issues", [])
    return []


def count_issue_statuses(issues):
    """Count issues by status."""
    counts = {"fixed": 0, "partial": 0, "unfixed": 0, "open": 0, "total": 0}
    for iss in issues:
        status = iss.get("status", "open")
        counts[status] = counts.get(status, 0) + 1
        counts["total"] += 1
    return counts


# ── Parse stdout for metrics ─────────────────────────────────────────────────

def parse_stdout_metrics(stdout):
    """Extract metrics from prism.py's fix loop stdout."""
    # Strip ANSI codes
    clean = re.sub(r'\x1b\[[0-9;]*m', '', stdout)

    metrics = {
        "iterations": 0,
        "issues_found": 0,
        "issues_fixed_count": 0,
        "scan_words": 0,
        "structural_context_chars": 0,
        "bug_table_rows": 0,
        "conversation_mode": False,
    }

    # Count iterations
    metrics["iterations"] = max(1, len(re.findall(
        r'Re-scan \(iteration', clean)))

    # Issues count from extraction line
    m = re.search(r'(\d+)\s+issues?\s*\(', clean)
    if m:
        metrics["issues_found"] = int(m.group(1))

    # Bug table parsing
    m = re.search(r'Parsed bug table:\s*(\d+)\s*rows,\s*(\d+)\s*fixable', clean)
    if m:
        metrics["bug_table_rows"] = int(m.group(1))

    # Structural context
    m = re.search(r'Structural context extracted \((\d+) chars\)', clean)
    if m:
        metrics["structural_context_chars"] = int(m.group(1))

    # Conversation mode detection (Haiku sometimes asks permission)
    if re.search(r'I\'d be happy|I can help|shall I|would you like', clean, re.I):
        metrics["conversation_mode"] = True

    # Count "approved" results
    metrics["issues_fixed_count"] = len(re.findall(r'approved', clean, re.I))

    return metrics


# ── Single Experiment Run ─────────────────────────────────────────────────────

def run_experiment(target_name, target_file, model):
    """Run one experiment: scan + fix on target with model.

    Returns result dict with all metrics.
    """
    run_id = f"{target_name}_{model}"
    print(f"\n  ── {run_id} ──")

    # Setup clean workspace
    ws, target_path = setup_workspace(target_name, target_file)
    fname = target_path.name
    print(f"    Workspace: {ws}")
    print(f"    Target: {fname} ({target_path.stat().st_size} bytes)")

    # Run prism fix
    stdout, stderr, elapsed, rc = run_prism_fix(ws, fname, model=model)
    print(f"    Completed in {elapsed:.0f}s (rc={rc})")

    # Measure outcomes
    diff = get_diff(ws, fname)
    diff_stats = get_diff_stats(ws, fname)
    issues = read_issues(ws)
    issue_counts = count_issue_statuses(issues)
    stdout_metrics = parse_stdout_metrics(stdout)

    # Count diff lines
    diff_lines = diff.split("\n") if diff else []
    added = sum(1 for l in diff_lines if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in diff_lines if l.startswith("-") and not l.startswith("---"))

    # Syntax check on modified file
    syntax_ok = True
    syntax_error = ""
    if diff:
        try:
            import ast
            ast.parse(target_path.read_text())
        except SyntaxError as e:
            syntax_ok = False
            syntax_error = f"{e.msg} (line {e.lineno})"

    result = {
        "run_id": run_id,
        "target": target_name,
        "model": model,
        "timestamp": datetime.now().isoformat(),
        "elapsed_sec": round(elapsed, 1),
        "returncode": rc,
        # Issue metrics
        "issues_total": issue_counts["total"],
        "issues_fixed": issue_counts["fixed"],
        "issues_partial": issue_counts.get("partial", 0),
        "issues_unfixed": issue_counts.get("unfixed", 0),
        "issues_open": issue_counts.get("open", 0),
        # Diff metrics
        "has_diff": bool(diff),
        "lines_added": added,
        "lines_removed": removed,
        "diff_stats": diff_stats,
        "syntax_ok": syntax_ok,
        "syntax_error": syntax_error,
        # Stdout metrics
        "iterations": stdout_metrics["iterations"],
        "conversation_mode": stdout_metrics["conversation_mode"],
        "structural_context_chars": stdout_metrics["structural_context_chars"],
        "bug_table_rows": stdout_metrics["bug_table_rows"],
        # Raw data for detailed analysis
        "issues": issues,
    }

    # Save individual run data
    run_dir = RESULTS_DIR / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "stdout.txt").write_text(stdout)
    (run_dir / "stderr.txt").write_text(stderr)
    (run_dir / "diff.patch").write_text(diff)
    (run_dir / "issues.json").write_text(json.dumps(issues, indent=2))
    (run_dir / "result.json").write_text(json.dumps(result, indent=2))

    # Summary
    fix_rate = (issue_counts["fixed"] / issue_counts["total"] * 100
                if issue_counts["total"] > 0 else 0)
    print(f"    Issues: {issue_counts['total']} total, "
          f"{issue_counts['fixed']} fixed ({fix_rate:.0f}%), "
          f"{issue_counts.get('partial', 0)} partial, "
          f"{issue_counts.get('unfixed', 0)} unfixed")
    print(f"    Diff: +{added}/-{removed} lines, "
          f"syntax={'OK' if syntax_ok else 'ERROR: ' + syntax_error}")
    print(f"    Iterations: {stdout_metrics['iterations']}, "
          f"conv_mode={stdout_metrics['conversation_mode']}")

    return result


# ── Analysis ──────────────────────────────────────────────────────────────────

def analyze(results):
    """Generate analysis report from all experiment results."""
    lines = []

    def p(s=""):
        print(s)
        lines.append(s)

    p("\n" + "=" * 70)
    p("  FIX RELIABILITY EXPERIMENT — RESULTS")
    p("=" * 70)
    p(f"  {len(results)} runs, {datetime.now().isoformat()}")

    # ── EXPERIMENT A: Reliability Matrix ──
    p("\n" + "─" * 70)
    p("  EXPERIMENT A: Fix Reliability Matrix")
    p("─" * 70)
    p()
    p(f"{'Target':<12} {'Model':<8} {'Issues':>7} {'Fixed':>7} "
      f"{'Rate':>6} {'+Lines':>7} {'-Lines':>7} {'Syn':>5} "
      f"{'Time':>6} {'Iter':>5}")
    p("-" * 80)

    for r in sorted(results, key=lambda x: (x["target"], x["model"])):
        total = r["issues_total"]
        fixed = r["issues_fixed"]
        rate = f"{fixed/total*100:.0f}%" if total > 0 else "n/a"
        syn = "OK" if r["syntax_ok"] else "ERR"
        p(f"{r['target']:<12} {r['model']:<8} {total:>7} {fixed:>7} "
          f"{rate:>6} {r['lines_added']:>7} {r['lines_removed']:>7} "
          f"{syn:>5} {r['elapsed_sec']:>5.0f}s {r['iterations']:>5}")

    # ── Aggregated by model ──
    p()
    p("Aggregated by model:")
    for model in MODELS:
        subset = [r for r in results if r["model"] == model]
        if not subset:
            continue
        total_issues = sum(r["issues_total"] for r in subset)
        total_fixed = sum(r["issues_fixed"] for r in subset)
        avg_time = sum(r["elapsed_sec"] for r in subset) / len(subset)
        rate = f"{total_fixed/total_issues*100:.0f}%" if total_issues > 0 else "n/a"
        syntax_ok = sum(1 for r in subset if r["syntax_ok"])
        p(f"  {model}: {total_issues} issues, {total_fixed} fixed ({rate}), "
          f"{syntax_ok}/{len(subset)} syntax OK, avg {avg_time:.0f}s")

    # ── EXPERIMENT B: Per-Issue Analysis ──
    p()
    p("─" * 70)
    p("  EXPERIMENT B: Per-Issue Analysis")
    p("─" * 70)
    p()

    # Collect all issues with their statuses
    all_issues = []
    for r in results:
        for iss in r.get("issues", []):
            iss_copy = dict(iss)
            iss_copy["_model"] = r["model"]
            iss_copy["_target"] = r["target"]
            all_issues.append(iss_copy)

    if all_issues:
        # By priority
        p("Fix rate by priority:")
        for prio in ["P0", "P1", "P2", "P3"]:
            subset = [i for i in all_issues if i.get("priority") == prio]
            if not subset:
                continue
            fixed = sum(1 for i in subset if i.get("status") == "fixed")
            p(f"  {prio}: {len(subset)} issues, {fixed} fixed "
              f"({fixed/len(subset)*100:.0f}%)")

        # By status
        p()
        p("Issue status distribution:")
        status_counts = {}
        for iss in all_issues:
            s = iss.get("status", "open")
            status_counts[s] = status_counts.get(s, 0) + 1
        for s, c in sorted(status_counts.items()):
            p(f"  {s}: {c}")

    # ── EXPERIMENT C: Model Comparison ──
    p()
    p("─" * 70)
    p("  EXPERIMENT C: Model Comparison (same targets)")
    p("─" * 70)
    p()

    for target in TARGETS:
        haiku = next((r for r in results
                     if r["target"] == target and r["model"] == "haiku"), None)
        sonnet = next((r for r in results
                      if r["target"] == target and r["model"] == "sonnet"), None)
        if not haiku or not sonnet:
            continue

        p(f"  {target}:")
        p(f"    Haiku:  {haiku['issues_fixed']}/{haiku['issues_total']} fixed, "
          f"+{haiku['lines_added']}/-{haiku['lines_removed']}, "
          f"{haiku['elapsed_sec']:.0f}s")
        p(f"    Sonnet: {sonnet['issues_fixed']}/{sonnet['issues_total']} fixed, "
          f"+{sonnet['lines_added']}/-{sonnet['lines_removed']}, "
          f"{sonnet['elapsed_sec']:.0f}s")

        # Compare: do they find the same issues?
        h_titles = {i.get("title", "") for i in haiku.get("issues", [])}
        s_titles = {i.get("title", "") for i in sonnet.get("issues", [])}
        overlap = h_titles & s_titles
        h_only = h_titles - s_titles
        s_only = s_titles - h_titles
        p(f"    Issues: {len(overlap)} shared, "
          f"{len(h_only)} haiku-only, {len(s_only)} sonnet-only")

    # ── CONVERSATION MODE ──
    p()
    conv_mode = [r for r in results if r.get("conversation_mode")]
    if conv_mode:
        p(f"  Conversation mode triggered: "
          f"{len(conv_mode)}/{len(results)} runs")
        for r in conv_mode:
            p(f"    {r['target']}/{r['model']}")
    else:
        p("  Conversation mode: 0 triggers (good)")

    # ── KEY FINDINGS ──
    p()
    p("─" * 70)
    p("  KEY FINDINGS")
    p("─" * 70)
    p()

    total_issues = sum(r["issues_total"] for r in results)
    total_fixed = sum(r["issues_fixed"] for r in results)
    total_syntax_ok = sum(1 for r in results if r["syntax_ok"])
    if total_issues > 0:
        p(f"  Overall fix rate: {total_fixed}/{total_issues} "
          f"({total_fixed/total_issues*100:.0f}%)")
    p(f"  Syntax preservation: {total_syntax_ok}/{len(results)} "
      f"({total_syntax_ok/len(results)*100:.0f}%)")

    # Save report
    report_file = RESULTS_DIR / "analysis_report.txt"
    report_file.write_text("\n".join(lines))
    p(f"\n  Report: {report_file}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Fix Reliability Experiment (through Prism)")
    parser.add_argument(
        "phase", nargs="?", default="run",
        choices=["run", "analyze"],
        help="run experiments or just analyze existing results")
    parser.add_argument(
        "--target", default=None,
        help="run only one target (starlette, click, tenacity)")
    parser.add_argument(
        "--model", default=None,
        help="run only one model (haiku, sonnet)")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    targets = TARGETS
    if args.target:
        if args.target not in TARGETS:
            print(f"Unknown target: {args.target}")
            sys.exit(1)
        targets = {args.target: TARGETS[args.target]}

    models = MODELS
    if args.model:
        models = [args.model]

    if args.phase == "analyze":
        # Load existing results
        results = []
        runs_dir = RESULTS_DIR / "runs"
        if runs_dir.exists():
            for run_dir in sorted(runs_dir.iterdir()):
                result_file = run_dir / "result.json"
                if result_file.exists():
                    results.append(json.loads(result_file.read_text()))
        if results:
            analyze(results)
        else:
            print("No results found. Run experiments first.")
        return

    # ── Run experiments ──
    print(f"Fix Reliability Experiment — {datetime.now().isoformat()}")
    print(f"Targets: {list(targets.keys())}")
    print(f"Models: {models}")
    print(f"Results: {RESULTS_DIR}")
    print()

    results = []

    # Load existing results for incremental runs
    for target_name in targets:
        for model in models:
            run_id = f"{target_name}_{model}"
            existing = RESULTS_DIR / "runs" / run_id / "result.json"
            if existing.exists():
                r = json.loads(existing.read_text())
                print(f"  [cached] {run_id}: {r['issues_fixed']}/"
                      f"{r['issues_total']} fixed in {r['elapsed_sec']:.0f}s")
                results.append(r)
                continue

            # Run fresh experiment
            r = run_experiment(target_name, TARGETS[target_name], model)
            results.append(r)

    # Analyze all results
    if results:
        analyze(results)

    print("\nDone.")


if __name__ == "__main__":
    main()

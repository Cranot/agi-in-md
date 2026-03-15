#!/usr/bin/env python3
"""Self-improvement loop: prism.py scans itself, extracts issues, fixes them, tests, re-scans.

Usage:
    python3 self_improve.py                    # Full loop: scan → extract → fix → test → re-scan
    python3 self_improve.py --scan-only        # Just scan, save findings
    python3 self_improve.py --fix-only         # Fix from existing scan results
    python3 self_improve.py --section SECTION  # Scan specific section only
    python3 self_improve.py --max-fixes N      # Limit fixes per run (default: 3)

Sections: core, routing, cookers, pipeline, ui, fix_loop, all
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

# ── Configuration ────────────────────────────────────────────────────────────

PRISM_PY = Path(__file__).parent.parent / "prism.py"
TEST_FILE = Path(__file__).parent.parent / "test_plan_pipeline.py"
RESULTS_DIR = Path(__file__).parent / "self_improve_results"
PRISM_CMD = ["python3", str(PRISM_PY)]

# Key sections of prism.py to scan independently (too big for single-shot)
SECTIONS = {
    "core": {
        "description": "Core classes, config, CLI interface",
        "lines": (1, 1200),
    },
    "routing": {
        "description": "Input classification, routing, calibration",
        "lines": (1200, 2400),
    },
    "cookers": {
        "description": "All COOK_ prompts and cooker logic",
        "lines": (150, 900),  # Cooker constants are near the top
    },
    "pipeline": {
        "description": "Pipeline execution, expand, discover, Full Prism",
        "lines": (4000, 6000),
    },
    "ui": {
        "description": "REPL, display, session management",
        "lines": (7000, 8500),
    },
    "fix_loop": {
        "description": "Fix mode, issue extraction, healing pipeline",
        "lines": (6000, 7000),
    },
}


def extract_section(section_name):
    """Extract a section of prism.py by line range."""
    info = SECTIONS[section_name]
    start, end = info["lines"]
    lines = PRISM_PY.read_text(encoding="utf-8").splitlines()
    actual_end = min(end, len(lines))
    section = "\n".join(lines[start - 1 : actual_end])
    return section, start, actual_end


def run_claude(prompt, system_prompt=None, model="haiku", timeout=120):
    """Run claude CLI with a prompt, return response text."""
    cmd = [
        "claude", "-p", "-",
        "--model", f"claude-{model}-4-5-20251001" if model == "haiku" else f"claude-{model}-4-6",
        "--output-format", "text",
        "--tools", "",
    ]
    if system_prompt:
        cmd.extend(["--system-prompt-file", system_prompt])

    try:
        result = subprocess.run(
            cmd, input=prompt, capture_output=True, text=True, timeout=timeout
        )
        if result.returncode != 0:
            print(f"  STDERR: {result.stderr[:500]}")
            return ""
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT after {timeout}s")
        return ""
    except Exception as e:
        print(f"  ERROR: {e}")
        return ""


def scan_section(section_name, prism_path=None, model="haiku"):
    """Scan a section of prism.py using L12 prism. Returns raw analysis."""
    print(f"\n{'='*60}")
    print(f"SCANNING: {section_name} — {SECTIONS[section_name]['description']}")
    print(f"{'='*60}")

    section_text, start, end = extract_section(section_name)
    line_count = end - start + 1
    print(f"  Lines {start}-{end} ({line_count} lines)")

    # Use L12 prism via prism.py --pipe
    prism_file = prism_path or str(Path(__file__).parent.parent / "prisms" / "l12.md")

    # Build the prompt: section code + L12 analysis request
    prompt = f"# prism.py lines {start}-{end}: {SECTIONS[section_name]['description']}\n\n{section_text}"

    # Read the L12 prism content
    l12_content = Path(prism_file).read_text(encoding="utf-8")
    # Strip YAML frontmatter
    if l12_content.startswith("---"):
        _, _, l12_content = l12_content.split("---", 2)
        l12_content = l12_content.strip()

    # Write combined system prompt to temp file
    sys_prompt_file = RESULTS_DIR / f"_sys_prompt_{section_name}.md"
    sys_prompt_file.write_text(l12_content, encoding="utf-8")

    t0 = time.time()
    response = run_claude(prompt, system_prompt=str(sys_prompt_file), model=model, timeout=180)
    elapsed = time.time() - t0

    print(f"  Response: {len(response)} chars, {elapsed:.1f}s")

    # Save raw scan
    out_file = RESULTS_DIR / f"scan_{section_name}.txt"
    out_file.write_text(response, encoding="utf-8")
    print(f"  Saved: {out_file}")

    return response


def extract_issues(scan_text, section_name):
    """Extract fixable issues from L12 scan output. Returns list of issue dicts.

    L12 outputs issues in this format:
    N. **Location**: `method_name()` method
       - **What breaks**: description
       - **Severity**: High/Medium/Low/Critical
       - **Conservation law prediction**: Fixable/Structural
    """
    issues = []

    # Format A: "N. **Location**: `method()` method\n   - **What breaks**: ...\n   - **Severity**: ..."
    fmt_a = re.findall(
        r'\d+\.\s+\*\*Location\*\*:\s*`?([^`\n]+?)`?\s*(?:method|function|class)?\s*\n'
        r'\s+-\s+\*\*What breaks\*\*:\s*(.+?)\n'
        r'\s+-\s+\*\*Severity\*\*:\s*(\w+)',
        scan_text, re.DOTALL
    )
    # Format C: "N. **Location**: `method()`\n   **What breaks**: ...\n   **Severity**: ..."
    # (no dash before bold, same line structure)
    fmt_c = re.findall(
        r'\d+\.\s+\*\*Location\*\*:\s*`([^`]+)`[^\n]*\n'
        r'\s+\*\*What breaks\*\*:\s*([^\n]+)\n'
        r'\s+\*\*Severity\*\*:\s*(\w+)',
        scan_text
    )
    fmt_a = fmt_a + fmt_c  # merge both into fmt_a processing
    # Format B: "N. **Title**\n   - Location: `method()` method\n   - What breaks: ...\n   - Severity: High (...)"
    fmt_b = re.findall(
        r'\d+\.\s+\*\*([^*]+)\*\*\s*\n'
        r'\s+-\s+Location:\s*`([^`]+)`[^\n]*\n'
        r'\s+-\s+What breaks:\s*([^\n]+)\n'
        r'\s+-\s+Severity:\s*(\w+)',
        scan_text
    )

    for loc, desc, severity in fmt_a:
        loc = loc.strip().strip('`').rstrip('()')
        severity = severity.strip().lower()
        fixable = True
        after_idx = scan_text.find(desc)
        if after_idx > 0:
            chunk = scan_text[after_idx:after_idx + 300].lower()
            if 'structural' in chunk and 'fixable' not in chunk:
                fixable = False
        issues.append({
            "section": section_name,
            "location": loc,
            "severity": severity,
            "description": desc.strip()[:200],
            "fixable": fixable,
        })

    for title, loc, desc, severity in fmt_b:
        loc = loc.strip().strip('`').rstrip('()')
        severity = severity.strip().lower()
        fixable = True
        after_idx = scan_text.find(desc)
        if after_idx > 0:
            chunk = scan_text[after_idx:after_idx + 300].lower()
            if 'structural' in chunk and 'fixable' not in chunk:
                fixable = False
        issues.append({
            "section": section_name,
            "location": loc,
            "severity": severity,
            "description": f"{title.strip()}: {desc.strip()[:180]}",
            "fixable": fixable,
        })

    # Format D (Sonnet): | Location | What Breaks | Severity | Fixable? |
    # Severity may be P0/P1/P2/P3 or High/Medium/Low
    if not issues:
        # Parse markdown table rows (skip header and separator)
        table_lines = []
        in_bug_table = False
        for line in scan_text.splitlines():
            stripped = line.strip()
            if not in_bug_table and stripped.startswith("|"):
                h = stripped.lower()
                if "location" in h and ("break" in h or "severity" in h):
                    in_bug_table = True
                    continue
            if in_bug_table and stripped.startswith("|---"):
                continue
            if in_bug_table and stripped.startswith("|"):
                table_lines.append(stripped)
            elif in_bug_table and not stripped.startswith("|") and stripped:
                in_bug_table = False

        p_map = {"p0": "critical", "p1": "high", "p2": "medium", "p3": "low"}
        for row in table_lines:
            cells = [c.strip().strip('`') for c in row.split("|")[1:-1]]
            if len(cells) >= 3:
                loc = cells[0].strip()
                desc = cells[1].strip() if len(cells) > 1 else ""
                sev_raw = cells[2].strip().lower() if len(cells) > 2 else "medium"
                fixable_raw = cells[3].strip().lower() if len(cells) > 3 else ""

                if loc.lower() in ('location', 'where', '---', ''):
                    continue

                severity = p_map.get(sev_raw, sev_raw)
                fixable = "structural" not in fixable_raw

                issues.append({
                    "section": section_name,
                    "location": loc,
                    "severity": severity,
                    "description": desc[:200],
                    "fixable": fixable,
                })

    # Deduplicate by location
    seen = set()
    unique = []
    for issue in issues:
        key = issue["location"][:40].lower()
        if key not in seen:
            seen.add(key)
            unique.append(issue)

    return unique


def generate_fix(issue, section_text, section_start, model="haiku"):
    """Use codegen prism to generate a fix for an issue. Returns (old_code, new_code) or None."""
    print(f"\n  Generating fix for: {issue['location']}")
    print(f"  Issue: {issue['description'][:100]}")

    # Find the specific function/method in the section
    loc = issue["location"]
    # Clean location: strip backticks, line refs, "method"/"function" suffix
    clean_loc = re.sub(r'`|lines?\s+\d+[-–]\d+|method|function|class', '', loc).strip().rstrip('()')
    # Try to find the relevant ~80 lines around the location
    lines = section_text.splitlines()
    target_lines = None
    target_start = 0
    loc_parts = [p for p in clean_loc.replace(".", " ").split() if len(p) > 3]
    for i, line in enumerate(lines):
        if any(part in line for part in loc_parts):
            if "def " in line or "class " in line:
                target_start = max(0, i - 2)
                target_end = min(len(lines), i + 80)
                target_lines = lines[target_start:target_end]
                break

    if not target_lines:
        # Fall back to first 150 lines of section
        target_lines = lines[:150]
        target_start = 0

    # Number the lines for context
    numbered = "\n".join(
        f"{section_start + target_start + i}: {line}"
        for i, line in enumerate(target_lines)
    )

    # Build a targeted fix prompt — explicit no-tools instruction
    prompt = f"""You are fixing a bug in Python code. You have ALL the code you need below. Do NOT request to read files. Do NOT use tools. Output ONLY code blocks.

## Bug
- **Location**: {issue['location']}
- **Problem**: {issue['description']}

## Current Code (with line numbers for reference only — do not include line numbers in your output)
```python
{numbered}
```

## Output Format — MANDATORY
Output exactly these two fenced code blocks and nothing else:

```old
(copy the exact lines to replace from the code above, WITHOUT line numbers, preserving exact indentation)
```

```new
(the replacement code with the fix applied)
```

RULES:
- The old block must be a VERBATIM substring of the code above (without the line number prefix)
- Minimal change only — fix ONLY the specific bug
- Keep indentation identical to the original
- Do NOT add explanations, do NOT request file reads, do NOT use tools
"""

    response = run_claude(prompt, model=model, timeout=120)

    if not response:
        print("  No response from model")
        return None

    # Save the fix proposal
    safe_loc = re.sub(r'[^\w]', '_', issue['location'][:30])
    fix_file = RESULTS_DIR / f"fix_{issue['section']}_{safe_loc}.txt"
    fix_file.write_text(response, encoding="utf-8")

    # Extract old/new blocks
    old_blocks = re.findall(r'```old\s*\n(.*?)\n```', response, re.DOTALL)
    new_blocks = re.findall(r'```new\s*\n(.*?)\n```', response, re.DOTALL)

    if old_blocks and new_blocks:
        return old_blocks[0], new_blocks[0]

    # Fallback: first two python blocks
    blocks = re.findall(r'```(?:python)?\s*\n(.*?)\n```', response, re.DOTALL)
    if len(blocks) >= 2:
        return blocks[0], blocks[1]

    print("  Could not extract old/new code blocks from response")
    return None


def apply_fix(old_code, new_code):
    """Apply a fix to prism.py. Returns True if successful."""
    content = PRISM_PY.read_text(encoding="utf-8")

    if old_code.strip() not in content:
        # Try with normalized whitespace
        normalized = re.sub(r'[ \t]+', ' ', old_code.strip())
        content_normalized = re.sub(r'[ \t]+', ' ', content)
        if normalized not in content_normalized:
            print("  WARNING: old code not found in prism.py — skipping")
            return False
        # Find the actual text to replace
        idx = content_normalized.index(normalized)
        # Count back to find the real position
        # This is approximate — safer to skip
        print("  WARNING: whitespace mismatch — skipping for safety")
        return False

    new_content = content.replace(old_code.strip(), new_code.strip(), 1)
    if new_content == content:
        print("  WARNING: replacement had no effect")
        return False

    # Backup
    backup = PRISM_PY.with_suffix(".py.bak")
    if not backup.exists():
        backup.write_text(content, encoding="utf-8")
        print(f"  Backup: {backup}")

    PRISM_PY.write_text(new_content, encoding="utf-8")
    print("  Applied fix to prism.py")
    return True


def run_tests():
    """Run test_plan_pipeline.py. Returns (passed, output)."""
    print("\n  Running tests...")
    try:
        result = subprocess.run(
            ["python3", str(TEST_FILE)],
            capture_output=True, text=True, timeout=60,
            cwd=str(PRISM_PY.parent)
        )
        output = result.stdout + result.stderr
        passed = "All" in output and "passed" in output
        # Count tests
        match = re.search(r'All (\d+) tests passed', output)
        if match:
            print(f"  PASS: {match.group(0)}")
        else:
            # Find failure info
            fail_lines = [l for l in output.splitlines() if 'FAIL' in l or 'Error' in l]
            for l in fail_lines[:5]:
                print(f"  {l}")
        return passed, output
    except subprocess.TimeoutExpired:
        print("  Tests timed out")
        return False, "timeout"
    except Exception as e:
        print(f"  Test error: {e}")
        return False, str(e)


def revert_fix():
    """Revert prism.py from backup."""
    backup = PRISM_PY.with_suffix(".py.bak")
    if backup.exists():
        backup.rename(PRISM_PY)
        print("  Reverted to backup")
        return True
    print("  No backup to revert to")
    return False


def self_improve_loop(sections=None, max_fixes=3, scan_only=False, fix_only=False, model="haiku"):
    """Main self-improvement loop."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    sections = sections or list(SECTIONS.keys())
    all_issues = []

    # ── Phase 1: Scan ────────────────────────────────────────────────────
    if not fix_only:
        print("\n" + "=" * 60)
        print("PHASE 1: SCANNING prism.py")
        print("=" * 60)

        for section_name in sections:
            scan_text = scan_section(section_name, model=model)
            issues = extract_issues(scan_text, section_name)
            all_issues.extend(issues)
            print(f"  Found {len(issues)} issues")

        # Save all issues
        issues_file = RESULTS_DIR / "issues.json"
        issues_file.write_text(json.dumps(all_issues, indent=2), encoding="utf-8")
        print(f"\nTotal issues found: {len(all_issues)}")
        print(f"Fixable: {sum(1 for i in all_issues if i.get('fixable'))}")

        if scan_only:
            print("\n--scan-only: stopping after scan")
            for i, issue in enumerate(all_issues):
                fix = "FIXABLE" if issue.get("fixable") else "STRUCTURAL"
                print(f"  [{i+1}] [{fix}] {issue['section']}: {issue['location']}")
                print(f"       {issue['description'][:100]}")
            return all_issues
    else:
        # Load existing issues
        issues_file = RESULTS_DIR / "issues.json"
        if not issues_file.exists():
            print("No existing scan results. Run --scan-only first.")
            return []
        all_issues = json.loads(issues_file.read_text(encoding="utf-8"))
        print(f"Loaded {len(all_issues)} issues from previous scan")

    # ── Phase 2: Fix ─────────────────────────────────────────────────────
    fixable = [i for i in all_issues if i.get("fixable")]
    if not fixable:
        print("\nNo fixable issues found.")
        return all_issues

    print(f"\n{'='*60}")
    print(f"PHASE 2: FIXING (max {max_fixes} fixes)")
    print(f"{'='*60}")

    fixes_applied = 0
    fix_results = []

    for issue in fixable[:max_fixes]:
        print(f"\n--- Fix {fixes_applied + 1}/{max_fixes} ---")

        # Get section context
        section_text, section_start, _ = extract_section(issue["section"])

        # Generate fix
        fix = generate_fix(issue, section_text, section_start, model=model)
        if not fix:
            fix_results.append({"issue": issue, "status": "no_fix_generated"})
            continue

        old_code, new_code = fix

        # Apply fix
        if not apply_fix(old_code, new_code):
            fix_results.append({"issue": issue, "status": "apply_failed"})
            continue

        # Test
        passed, test_output = run_tests()
        if not passed:
            print("  Tests FAILED — reverting")
            revert_fix()
            fix_results.append({"issue": issue, "status": "tests_failed", "output": test_output[:500]})
            continue

        # Remove backup (fix is good)
        backup = PRISM_PY.with_suffix(".py.bak")
        if backup.exists():
            backup.unlink()

        fixes_applied += 1
        fix_results.append({"issue": issue, "status": "applied"})
        print(f"  FIX APPLIED SUCCESSFULLY ({fixes_applied}/{max_fixes})")

    # ── Phase 3: Re-scan (verify) ────────────────────────────────────────
    if fixes_applied > 0:
        print(f"\n{'='*60}")
        print(f"PHASE 3: RE-SCANNING (verifying {fixes_applied} fixes)")
        print(f"{'='*60}")

        # Re-scan only affected sections
        affected_sections = set(r["issue"]["section"] for r in fix_results if r["status"] == "applied")
        for section_name in affected_sections:
            scan_section(section_name, model=model)

    # ── Summary ──────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Total issues found: {len(all_issues)}")
    print(f"Fixable issues: {len(fixable)}")
    print(f"Fixes attempted: {len(fix_results)}")
    print(f"Fixes applied: {fixes_applied}")

    for r in fix_results:
        status = r["status"]
        loc = r["issue"]["location"]
        print(f"  [{status.upper()}] {loc}: {r['issue']['description'][:80]}")

    # Save results
    results_file = RESULTS_DIR / "fix_results.json"
    # Make serializable
    for r in fix_results:
        r["issue"] = {k: v for k, v in r["issue"].items()}
    results_file.write_text(json.dumps(fix_results, indent=2), encoding="utf-8")

    return fix_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prism self-improvement loop")
    parser.add_argument("--scan-only", action="store_true", help="Only scan, don't fix")
    parser.add_argument("--fix-only", action="store_true", help="Fix from existing scan results")
    parser.add_argument("--section", type=str, help="Scan specific section only")
    parser.add_argument("--max-fixes", type=int, default=3, help="Max fixes per run (default: 3)")
    parser.add_argument("--model", type=str, default="haiku", help="Model for scanning (default: haiku)")
    args = parser.parse_args()

    sections = [args.section] if args.section else None
    if sections and sections[0] not in SECTIONS:
        print(f"Unknown section: {sections[0]}")
        print(f"Available: {', '.join(SECTIONS.keys())}")
        sys.exit(1)

    self_improve_loop(
        sections=sections,
        max_fixes=args.max_fixes,
        scan_only=args.scan_only,
        fix_only=args.fix_only,
        model=args.model,
    )

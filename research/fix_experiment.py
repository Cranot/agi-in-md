#!/usr/bin/env python3
"""
Fix Reliability Experiment Harness
===================================
Measures how reliably Haiku/Sonnet apply fixes from L12 scan reports.

Experiments:
  A: Fix Reliability Matrix — 3 targets × 2 scan modes × 2 fix models
  B: Confidence Scoring — pre-flight prediction vs actual outcome
  C: Model Comparison — Haiku vs Sonnet on identical issues

Run on VPS:
  python3 fix_experiment.py                    # run all phases
  python3 fix_experiment.py scan               # phase 1 only
  python3 fix_experiment.py extract            # phase 2 only
  python3 fix_experiment.py fix                # phase 3 only
  python3 fix_experiment.py fix --model haiku  # fix with one model only
  python3 fix_experiment.py analyze            # phase 4 only

Checkpointing: each phase saves JSON so you can resume after failures.
"""

import ast
import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import time
from datetime import datetime
from pathlib import Path


# ── Configuration ─────────────────────────────────────────────────────────────

TARGETS = {
    "starlette": "research/real_code_starlette.py",
    "click": "research/real_code_click.py",
    "tenacity": "research/real_code_tenacity.py",
}

SCAN_MODES = ["single", "full"]
FIX_MODELS = ["haiku", "sonnet"]

RESULTS_DIR = Path("_fix_experiment")
WORKSPACE = RESULTS_DIR / "workspace"

# Cap per target×mode to control cost
MAX_ISSUES = 15

# Timeouts (seconds)
SCAN_TIMEOUT = 300      # 5 min per scan
FIX_TIMEOUT = 120       # 2 min per fix attempt
VERIFY_TIMEOUT = 60     # 1 min per verification

# Tools Claude gets for fix attempts (same as prism.py's ALLOWED_TOOLS)
FIX_TOOLS = "Read,Edit"

CLAUDE_CMD = "claude"


# ── Bug Parsers ───────────────────────────────────────────────────────────────
# Two formats: markdown table (L12 standard) and prose list (model variation).
# Try both, return whichever finds bugs.

def parse_bug_prose(report_text):
    """Parse bugs from prose-format L12 output.

    Handles numbered lists like:
      1. **Location**: `function_name()` method
         - **What breaks**: description
         - **Severity**: High/Medium/Low
         - **Conservation Law Prediction**: Structural/Fixable - explanation
    """
    # Strip ANSI color codes
    clean = re.sub(r'\x1b\[[0-9;]*m', '', report_text)

    sev_map = {
        "CRITICAL": "P0", "HIGH": "P1", "MEDIUM": "P2",
        "LOW": "P3", "VERY LOW": "P3",
    }

    # Find the bug section (usually near the end)
    bug_section_patterns = [
        r'##\s*Concrete\s+Bug',
        r'##\s*Bug\s+(?:Inventory|Table|List)',
        r'##\s*Issues?\s+and',
        r'##\s*Defect',
        r'collect every concrete bug',
    ]
    section_start = -1
    for pat in bug_section_patterns:
        m = re.search(pat, clean, re.I)
        if m:
            section_start = m.start()
            break

    if section_start < 0:
        # Fallback: look for numbered items with **Location**
        m = re.search(r'\d+\.\s+\*\*Location\*\*', clean)
        if m:
            section_start = m.start()

    if section_start < 0:
        return None

    section = clean[section_start:]

    # Parse numbered items
    # Match: "N. **Location**: ..." or "N. **Location**:..." or "**N.** **Location**:..."
    item_pattern = re.compile(
        r'(?:^|\n)\s*(?:\*\*)?(\d+)\.?\)?(?:\*\*)?\s+'
        r'(?:\*\*)?(?:Location|Bug|Issue)(?:\*\*)?[:\s]*(.+?)(?=\n\s*(?:\*\*)?(?:\d+)\.?\)?(?:\*\*)?\s+(?:\*\*)?(?:Location|Bug|Issue)|\n\s*(?:##|\Z))',
        re.DOTALL | re.I
    )

    items = list(item_pattern.finditer(section))
    if not items:
        # Simpler pattern: just numbered items
        item_pattern2 = re.compile(
            r'(?:^|\n)\s*(\d+)\.\s+\*\*Location\*\*:\s*(.+?)(?=\n\s*\d+\.\s+\*\*Location\*\*|\n\s*##|\n\s*\[|\Z)',
            re.DOTALL | re.I
        )
        items = list(item_pattern2.finditer(section))

    if not items:
        return None

    def _extract_field(text, field_name):
        """Extract a field value from item text."""
        patterns = [
            rf'\*\*{field_name}\*\*[:\s]*(.+?)(?=\n\s*-\s*\*\*|\Z)',
            rf'{field_name}[:\s]*(.+?)(?=\n\s*-|\Z)',
        ]
        for pat in patterns:
            m = re.search(pat, text, re.I | re.DOTALL)
            if m:
                return m.group(1).strip().rstrip('.')
        return ""

    def _clean(s):
        return re.sub(r'\*\*([^*]*)\*\*', r'\1', s).replace('`', '').strip()

    issues = []
    for item_match in items:
        num = item_match.group(1)
        item_text = item_match.group(2)

        location = _clean(_extract_field(item_text, "Location") or
                         item_text.split("\n")[0])
        what_breaks = _clean(_extract_field(item_text, "What breaks"))
        severity_raw = _extract_field(item_text, "Severity")
        prediction = _extract_field(
            item_text, "Conservation Law Prediction") or \
            _extract_field(item_text, "Prediction") or \
            _extract_field(item_text, "Fixable")

        # Determine fixability from prediction/fixable field
        pred_lower = prediction.lower() if prediction else ""
        skip = False
        if "structural" in pred_lower and "fixable" not in pred_lower:
            skip = True

        # Build action from prediction hints
        action = ""
        if not skip and prediction:
            # Extract any text after "Fixable -" or "Fixable:"
            fixable_match = re.search(
                r'(?:fixable|yes)[:\s-]+(.+)', prediction, re.I)
            if fixable_match:
                action = _clean(fixable_match.group(1))

        if not action and what_breaks:
            # Derive action from what breaks
            action = f"Fix: {what_breaks[:100]}"

        # Map severity
        severity = severity_raw.upper().split('-')[0].split('–')[0].strip()
        priority = "P2"
        for sev_key, prio in sev_map.items():
            if sev_key in severity:
                priority = prio
                break

        issues.append({
            "id": len(issues) + 1,
            "priority": priority,
            "title": f"#{num}: {_clean(what_breaks[:80]) if what_breaks else _clean(location[:80])}",
            "location": _clean(location),
            "description": _clean(what_breaks) if what_breaks else _clean(location),
            "action": action,
            "fixable_raw": prediction,
            "prediction": prediction,
            "skipped": skip,
            "skip_reason": "structural" if skip else "",
        })

    return issues if issues else None


def parse_bugs_model(report_text):
    """Use Claude to extract bugs from unstructured report text.

    Last resort — costs one API call. Same prompt as prism.py's
    ISSUE_EXTRACT_FALLBACK.
    """
    extract_prompt = (
        "You receive a structural code analysis. Extract only bugs fixable with a "
        "specific code change. Output a JSON array in a ```json``` code block.\n\n"
        "Find any bug or issue sections: headings like 'Issues', 'Bugs', "
        "'Potential Leaks', 'Thread Safety', or similar. "
        "May be scattered across multiple sections.\n\n"
        "Fixable: concrete code changes possible. Skip: purely structural, "
        "architectural, or design observations.\n\n"
        "Each fixable bug:\n"
        '{"id": 1, "priority": "P1", "title": "short title", '
        '"location": "ClassName.method() or function_name()", '
        '"description": "what breaks and why", '
        '"action": "specific code change"}\n\n'
        "Priority: CRITICAL -> P0. HIGH -> P1. MEDIUM -> P2. LOW -> P3.\n\n"
        "Rules:\n"
        "- location must name a specific function or method\n"
        "- action must state a concrete fix, not 'consider redesigning'\n"
        "- skip design observations and trade-offs\n"
        "- output ONLY the ```json``` block, nothing else"
    )

    user_msg = f"{extract_prompt}\n\n---\n\n{report_text[:8000]}"

    try:
        result = subprocess.run(
            [CLAUDE_CMD, "-p", "--model", "haiku",
             "--output-format", "text", "--tools", ""],
            input=user_msg,
            capture_output=True, text=True, timeout=60,
        )
        raw = result.stdout.strip()
    except subprocess.TimeoutExpired:
        return None

    # Parse JSON from response
    json_match = re.search(r'```json\s*([\s\S]*?)```', raw)
    if not json_match:
        json_match = re.search(r'\[[\s\S]*\]', raw)

    if not json_match:
        return None

    try:
        issues = json.loads(json_match.group(1) if '```' in raw
                           else json_match.group(0))
    except (json.JSONDecodeError, IndexError):
        return None

    if not isinstance(issues, list) or not issues:
        return None

    sev_map = {"CRITICAL": "P0", "HIGH": "P1", "MEDIUM": "P2",
               "LOW": "P3", "VERY LOW": "P3"}

    cleaned = []
    for iss in issues:
        if not isinstance(iss, dict):
            continue
        priority = str(iss.get("priority", "P2")).upper()
        if priority not in ("P0", "P1", "P2", "P3"):
            for sev_key, prio in sev_map.items():
                if sev_key in priority:
                    priority = prio
                    break
            else:
                priority = "P2"

        cleaned.append({
            "id": len(cleaned) + 1,
            "priority": priority,
            "title": str(iss.get("title", ""))[:100],
            "location": str(iss.get("location", "")),
            "description": str(iss.get("description", "")),
            "action": str(iss.get("action", "")),
            "fixable_raw": "model_extracted",
            "prediction": "",
            "skipped": False,
            "skip_reason": "",
        })

    return cleaned if cleaned else None


def parse_bugs(report_text, use_model_fallback=False):
    """Try all parsers, return first that finds bugs."""
    # Try table format first (canonical L12)
    result = parse_bug_table(report_text)
    if result:
        return result, "table"

    # Try prose format
    result = parse_bug_prose(report_text)
    if result:
        return result, "prose"

    # Model-based fallback (costs one API call)
    if use_model_fallback:
        result = parse_bugs_model(report_text)
        if result:
            return result, "model"

    return None, "none"


def parse_bug_table(report_text):
    """Parse L12 markdown bug table. Returns list of issue dicts or None."""
    lines = report_text.split("\n")
    table_rows = []
    in_table = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("| #") or stripped.startswith("| **#"):
            in_table = True
            continue
        if not in_table and stripped.startswith("|"):
            h = stripped.lower()
            if "sever" in h or "break" in h or "fixab" in h:
                in_table = True
                continue
        if in_table and stripped.startswith("|---"):
            continue
        if in_table and stripped.startswith("|"):
            table_rows.append(stripped)
        elif in_table and not stripped.startswith("|") and stripped:
            in_table = False

    if not table_rows:
        return None

    sev_map = {
        "CRITICAL": "P0", "HIGH": "P1", "MEDIUM": "P2",
        "LOW": "P3", "VERY LOW": "P3", "NONE": "P3",
    }

    def _clean(s):
        return re.sub(r'\*\*([^*]*)\*\*', r'\1', s).replace('`', '').strip()

    issues = []
    for row in table_rows:
        cells = [c.strip() for c in row.split("|")[1:-1]]
        if len(cells) < 5:
            continue

        num = _clean(cells[0])
        location = _clean(cells[1])
        what_breaks = _clean(cells[2])
        severity = _clean(cells[3]).upper()
        fixable = _clean(cells[4]) if len(cells) > 4 else ""
        prediction = _clean(cells[5]) if len(cells) > 5 else ""

        # Filter: skip structural/unfixable
        fixable_lower = fixable.lower()
        pre_paren = fixable_lower.split("(")[0]
        skip = False
        if ("no" in pre_paren or "structural" in fixable_lower
                or "not fixable" in fixable_lower
                or "by design" in fixable_lower
                or "unfixable" in fixable_lower):
            skip = True
        if "none" in fixable_lower or fixable_lower.startswith("n/a"):
            skip = True

        # Extract action hint from parenthetical
        hint_match = re.search(r'\(([^)]+)\)', fixable)
        action = hint_match.group(1) if hint_match else fixable

        priority = "P2"
        for sev_key, prio in sev_map.items():
            if sev_key in severity:
                priority = prio
                break

        issues.append({
            "id": len(issues) + 1,
            "priority": priority,
            "title": f"#{num}: {what_breaks[:80]}",
            "location": location,
            "description": what_breaks,
            "action": action,
            "fixable_raw": fixable,
            "prediction": prediction,
            "skipped": skip,
            "skip_reason": fixable if skip else "",
        })

    return issues if issues else None


# ── Confidence Scorer ─────────────────────────────────────────────────────────

def compute_confidence(issue, target_code):
    """Pre-flight confidence score (0-8). Higher = more likely to fix correctly.

    Dimensions:
      - Location specificity (0-2): Can we find the exact code?
      - Action concreteness (0-2): Does the fix describe a specific edit?
      - Description concreteness (0-2): Is this a concrete bug or abstract observation?
      - Target identifier match (0-2): Do identifiers in the action exist in code?
    """
    score = 0
    location = issue.get("location", "")
    action = issue.get("action", "")
    desc = issue.get("description", "")

    # 1. Location specificity (0-2)
    func_match = re.search(r'(\w+)\(\)', location)
    if func_match:
        func_name = func_match.group(1)
        if f"def {func_name}" in target_code:
            score += 2  # exact function found
        elif func_name in target_code:
            score += 1  # identifier exists but not as def
    elif re.search(r'line \d+', location, re.I):
        score += 1
    # else: 0 (generic or empty location)

    # 2. Action concreteness (0-2)
    concrete_verbs = [
        'add', 'insert', 'remove', 'replace', 'wrap', 'guard',
        'check', 'validate', 'return', 'raise', 'catch', 'handle',
        'use', 'set', 'copy', 'deep', 'pass', 'default',
    ]
    action_words = action.lower().split()[:5]
    if any(v in action_words for v in concrete_verbs):
        score += 2
    elif action and len(action) > 10:
        score += 1

    # 3. Description concreteness (0-2)
    concrete_bugs = [
        'missing', 'null', 'none', 'empty', 'check', 'guard',
        'validate', 'boundary', 'overflow', 'race', 'leak',
        'crash', 'error', 'exception', 'silent', 'lost', 'ignored',
        'uncaught', 'unhandled', 'mutate', 'mutable', 'shared',
    ]
    abstract_terms = [
        'architecture', 'coupling', 'design', 'structural',
        'pattern', 'philosophy', 'approach', 'strategy', 'trade-off',
    ]
    concrete_hits = sum(1 for w in concrete_bugs if w in desc.lower())
    abstract_hits = sum(1 for w in abstract_terms if w in desc.lower())
    score += min(2, concrete_hits)
    score -= min(1, abstract_hits)

    # 4. Action identifiers found in code (0-2)
    idents = re.findall(r'[_a-zA-Z]\w{3,}', action)
    found = sum(1 for ident in idents[:6] if ident in target_code)
    if found >= 2:
        score += 2
    elif found >= 1:
        score += 1

    return max(0, min(8, score))


def confidence_label(score):
    """Human-readable confidence label."""
    if score >= 6:
        return "HIGH"
    elif score >= 4:
        return "MEDIUM"
    elif score >= 2:
        return "LOW"
    return "VERY_LOW"


# ── Code Context Extractor ────────────────────────────────────────────────────

def extract_code_context(target_path, location, desc="", action="",
                         context_lines=40):
    """Extract numbered code snippet around the issue location.

    Simplified version of prism.py's _heal_grep_context.
    Returns numbered code string or empty string.
    """
    try:
        lines = Path(target_path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""

    combined = f"{location} {desc} {action}"

    # Build search terms (most specific first)
    search_terms = []

    # Function names from location
    loc_funcs = re.findall(r'(\w+)\(\)', location)
    for f in loc_funcs:
        search_terms.append(f"def {f}")
    if not loc_funcs and location:
        search_terms.append(f"def {location}")

    # Function names from all fields
    all_funcs = re.findall(r'(\w{4,})\(\)', combined)
    for f in all_funcs[:3]:
        search_terms.append(f"def {f}")

    # Constants
    caps = re.findall(r'[A-Z][A-Z_]{3,}', combined)
    search_terms.extend(caps[:2])

    # Snake_case identifiers
    snakes = re.findall(r'[a-z]\w*_\w{3,}', f"{action} {desc}")
    search_terms.extend(snakes[:3])

    # Search from end backward (favor overrides/tests)
    best_line = -1
    for term in search_terms:
        for i in range(len(lines) - 1, -1, -1):
            if term in lines[i]:
                best_line = i
                break
        if best_line >= 0:
            break

    if best_line < 0:
        # Fallback: return whole file if small
        if len(lines) <= 200:
            return "\n".join(f"{i+1:4d}  {l}" for i, l in enumerate(lines))
        return ""

    start = max(0, best_line - 5)
    end = min(len(lines), best_line + context_lines)
    return "\n".join(f"{i+1:4d}  {lines[i]}" for i in range(start, end))


# ── Fix Prompt Builder ────────────────────────────────────────────────────────

def build_fix_prompt(issue, target_path, snippet=""):
    """Build the fix prompt (matches prism.py's _heal_fix_one format)."""
    fname = Path(target_path).name
    title = issue.get("title", "")
    desc = issue.get("description", "")
    action = issue.get("action", "")
    location = issue.get("location", "")

    prompt = f"Fix this specific issue in {fname}:\n\n"
    prompt += f"Title: {title}\n"
    prompt += f"Description: {desc}\n"
    if location:
        prompt += f"Location: {location}\n"
    if action:
        prompt += f"Suggested action: {action}\n"
    if snippet:
        prompt += f"\nRelevant code (with line numbers):\n```\n{snippet}\n```\n"
    prompt += (
        "\nLocate the exact method and line before editing. "
        "Make exactly one change: replace a variable or statement, "
        "insert a new block, or add a guard clause. "
        "If this fix requires changes in 3+ locations, fix only the "
        "most critical one. Don't refactor unrelated code."
    )
    prompt += f"\n\nFile path: {Path(target_path).resolve()}"
    return prompt


# ── Verification Prompt ───────────────────────────────────────────────────────

VERIFY_PROMPT = (
    "You are verifying a code fix. Given the ISSUE description and the "
    "CURRENT code after the fix was applied:\n"
    "1. Is the original issue fixed?\n"
    "2. Were any new problems introduced?\n\n"
    "Output format (exactly):\n"
    "VERDICT: FIXED | PARTIAL | UNFIXED\n"
    "REGRESSION: YES | NO\n"
    "DETAIL: one sentence explanation"
)


# ── Phase 1: SCAN ─────────────────────────────────────────────────────────────

def phase_scan(targets=None, modes=None):
    """Run L12 scans on all targets. Caches outputs."""
    print("\n" + "=" * 60)
    print("  PHASE 1: SCAN")
    print("=" * 60)

    scan_dir = RESULTS_DIR / "scans"
    scan_dir.mkdir(parents=True, exist_ok=True)

    targets = targets or TARGETS
    modes = modes or SCAN_MODES

    for target_name, target_file in targets.items():
        for mode in modes:
            out_file = scan_dir / f"{target_name}_{mode}.txt"
            meta_file = scan_dir / f"{target_name}_{mode}_meta.json"

            if out_file.exists() and out_file.stat().st_size > 100:
                meta = {}
                if meta_file.exists():
                    meta = json.loads(meta_file.read_text())
                print(f"  [cached] {target_name}/{mode}: "
                      f"{meta.get('output_words', '?')}w")
                continue

            print(f"  Scanning {target_name} ({mode})...", end="", flush=True)
            start = time.time()

            # Build command: prism.py --scan FILE [full]
            cmd = ["python3", "prism.py", "--scan", target_file]
            if mode == "full":
                cmd.append("full")

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=SCAN_TIMEOUT,
                    env={**os.environ, "PYTHONUNBUFFERED": "1"},
                )
                output = result.stdout
                stderr = result.stderr
            except subprocess.TimeoutExpired:
                output = ""
                stderr = "TIMEOUT"
                print(f" TIMEOUT ({SCAN_TIMEOUT}s)")
                continue

            elapsed = time.time() - start
            words = len(output.split())

            out_file.write_text(output)
            if stderr:
                err_file = scan_dir / f"{target_name}_{mode}_stderr.txt"
                err_file.write_text(stderr)

            meta_file.write_text(json.dumps({
                "target": target_name,
                "mode": mode,
                "elapsed_sec": round(elapsed, 1),
                "output_words": words,
                "output_bytes": len(output),
                "returncode": result.returncode,
                "timestamp": datetime.now().isoformat(),
            }, indent=2))

            print(f" {words}w in {elapsed:.0f}s (rc={result.returncode})")


# ── Phase 2: EXTRACT + SCORE ─────────────────────────────────────────────────

def phase_extract():
    """Extract issues from scan outputs, compute confidence scores."""
    print("\n" + "=" * 60)
    print("  PHASE 2: EXTRACT + SCORE")
    print("=" * 60)

    issues_dir = RESULTS_DIR / "issues"
    issues_dir.mkdir(parents=True, exist_ok=True)

    summary = {}

    for target_name, target_file in TARGETS.items():
        try:
            target_code = Path(target_file).read_text(encoding="utf-8")
        except FileNotFoundError:
            print(f"  SKIP {target_name}: file not found ({target_file})")
            continue

        for mode in SCAN_MODES:
            key = f"{target_name}_{mode}"
            scan_file = RESULTS_DIR / "scans" / f"{key}.txt"

            if not scan_file.exists():
                print(f"  SKIP {key}: no scan output")
                continue

            scan_output = scan_file.read_text()

            # Parse bugs (tries table → prose → model fallback for full)
            use_fallback = (mode == "full")
            all_issues, parse_format = parse_bugs(
                scan_output, use_model_fallback=use_fallback)
            if all_issues is None:
                print(f"  {key}: NO BUGS FOUND in scan output")
                (issues_dir / f"{key}.json").write_text("[]")
                summary[key] = {"total": 0, "fixable": 0, "structural": 0,
                                "format": "none"}
                continue
            print(f"    (format: {parse_format})")

            # Annotate each issue
            fixable = []
            structural = []
            for iss in all_issues:
                iss["target"] = target_name
                iss["target_file"] = target_file
                iss["scan_mode"] = mode
                iss["confidence"] = compute_confidence(iss, target_code)
                iss["confidence_label"] = confidence_label(iss["confidence"])

                if iss["skipped"]:
                    structural.append(iss)
                else:
                    fixable.append(iss)

            # Re-number fixable issues (1-indexed)
            for i, iss in enumerate(fixable):
                iss["id"] = i + 1

            # Save all (including structural, for analysis)
            (issues_dir / f"{key}_all.json").write_text(
                json.dumps(all_issues, indent=2))
            (issues_dir / f"{key}.json").write_text(
                json.dumps(fixable, indent=2))

            conf_dist = {}
            for iss in fixable:
                lbl = iss["confidence_label"]
                conf_dist[lbl] = conf_dist.get(lbl, 0) + 1

            summary[key] = {
                "total": len(all_issues),
                "fixable": len(fixable),
                "structural": len(structural),
                "confidence": conf_dist,
            }

            print(f"  {key}: {len(all_issues)} total, "
                  f"{len(fixable)} fixable, {len(structural)} structural")
            print(f"    Confidence: {conf_dist}")

    # Save summary
    (issues_dir / "_summary.json").write_text(json.dumps(summary, indent=2))
    return summary


# ── Phase 3: FIX ──────────────────────────────────────────────────────────────

def attempt_fix(issue, target_file, work_dir, model="haiku"):
    """Attempt to fix one issue. Returns detailed result dict.

    Process:
      1. Copy target to workspace (clean slate)
      2. Build fix prompt with code context
      3. Call claude -p with Edit tool access
      4. Measure: diff, syntax, line counts
    """
    work_file = work_dir / Path(target_file).name
    original = Path(target_file).read_text(encoding="utf-8")

    # Reset to clean state
    work_file.write_text(original)
    original_hash = hashlib.sha256(original.encode()).hexdigest()[:16]

    # Extract code context around the issue location
    snippet = extract_code_context(
        work_file,
        issue.get("location", ""),
        desc=issue.get("description", ""),
        action=issue.get("action", ""),
    )

    # Build fix prompt
    fix_prompt = build_fix_prompt(issue, work_file, snippet)

    # Write prompt to temp file (avoids shell escaping issues)
    prompt_file = work_dir / "_fix_prompt.txt"
    prompt_file.write_text(fix_prompt)

    start = time.time()
    try:
        result = subprocess.run(
            [
                CLAUDE_CMD, "-p",
                "--model", model,
                "--output-format", "text",
                "--allowedTools", FIX_TOOLS,
            ],
            input=fix_prompt,
            capture_output=True,
            text=True,
            timeout=FIX_TIMEOUT,
            cwd=str(work_dir),
        )
        model_output = result.stdout
        model_stderr = result.stderr
        returncode = result.returncode
    except subprocess.TimeoutExpired:
        model_output = ""
        model_stderr = "TIMEOUT"
        returncode = -1

    elapsed = time.time() - start

    # Read potentially modified file
    try:
        modified = work_file.read_text(encoding="utf-8")
    except FileNotFoundError:
        modified = ""

    modified_hash = hashlib.sha256(modified.encode()).hexdigest()[:16]
    has_diff = original_hash != modified_hash

    # Compute unified diff
    diff_lines = list(difflib.unified_diff(
        original.splitlines(keepends=True),
        modified.splitlines(keepends=True),
        fromfile="original",
        tofile="modified",
    ))
    diff_text = "".join(diff_lines)

    # Count changed lines
    added = sum(1 for l in diff_lines
                if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in diff_lines
                  if l.startswith("-") and not l.startswith("---"))

    # Syntax check (Python only)
    syntax_ok = False
    syntax_error = ""
    if has_diff:
        try:
            ast.parse(modified)
            syntax_ok = True
        except SyntaxError as e:
            syntax_error = f"{e.msg} (line {e.lineno})"
    elif not has_diff:
        # No diff means file unchanged — syntax is whatever original was
        syntax_ok = True
        syntax_error = "no_change"

    return {
        "issue_id": issue["id"],
        "issue_title": issue.get("title", ""),
        "target": issue.get("target", ""),
        "scan_mode": issue.get("scan_mode", ""),
        "model": model,
        "confidence": issue.get("confidence", -1),
        "confidence_label": issue.get("confidence_label", ""),
        "priority": issue.get("priority", ""),
        "location": issue.get("location", ""),
        "action": issue.get("action", ""),
        "elapsed_sec": round(elapsed, 1),
        "has_diff": has_diff,
        "syntax_ok": syntax_ok,
        "syntax_error": syntax_error,
        "lines_added": added,
        "lines_removed": removed,
        "diff_size": len(diff_text),
        "diff": diff_text[:3000],
        "model_output_len": len(model_output),
        "returncode": returncode,
        "original_hash": original_hash,
        "modified_hash": modified_hash,
    }


def run_verification(issue, modified_code, model="haiku"):
    """Semantic verification: is the fix correct? Returns verdict dict."""
    location = issue.get("location", "")
    desc = issue.get("description", "")
    action = issue.get("action", "")
    title = issue.get("title", "")

    # Build verification message
    verify_msg = (
        f"{VERIFY_PROMPT}\n\n"
        f"ISSUE:\n"
        f"  Title: {title}\n"
        f"  Description: {desc}\n"
        f"  Location: {location}\n"
        f"  Expected action: {action}\n\n"
        f"CURRENT CODE (after fix):\n"
        f"```python\n{modified_code[:4000]}\n```"
    )

    try:
        result = subprocess.run(
            [
                CLAUDE_CMD, "-p",
                "--model", model,
                "--output-format", "text",
                "--tools", "",
            ],
            input=verify_msg,
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT,
        )
        output = result.stdout.strip()
    except subprocess.TimeoutExpired:
        return {"verdict": "timeout", "regression": False, "detail": ""}

    # Parse verdict
    verdict = "unknown"
    regression = False

    for line in output.split("\n"):
        if "VERDICT:" in line.upper():
            v = line.split(":")[-1].strip().upper()
            if "UNFIXED" in v:
                verdict = "unfixed"
            elif "PARTIAL" in v:
                verdict = "partial"
            elif "FIXED" in v:
                verdict = "fixed"
        if "REGRESSION:" in line.upper():
            regression = "YES" in line.upper()

    return {
        "verdict": verdict,
        "regression": regression,
        "detail": output[:500],
    }


def phase_fix(models=None):
    """Fix all extracted issues with specified models. Checkpoint after each."""
    print("\n" + "=" * 60)
    print("  PHASE 3: FIX + VERIFY")
    print("=" * 60)

    models = models or FIX_MODELS
    WORKSPACE.mkdir(parents=True, exist_ok=True)

    fixes_dir = RESULTS_DIR / "fixes"
    fixes_dir.mkdir(parents=True, exist_ok=True)

    # Load any previous checkpoint
    checkpoint_file = RESULTS_DIR / "fix_results_checkpoint.json"
    if checkpoint_file.exists():
        all_results = json.loads(checkpoint_file.read_text())
        done_keys = {
            f"{r['target']}_{r['scan_mode']}_{r['model']}_{r['issue_id']}"
            for r in all_results
        }
        print(f"  Resuming: {len(all_results)} fixes already done")
    else:
        all_results = []
        done_keys = set()

    total_issues = 0
    total_fixes = 0

    for target_name, target_file in TARGETS.items():
        for mode in SCAN_MODES:
            key = f"{target_name}_{mode}"
            issues_file = RESULTS_DIR / "issues" / f"{key}.json"

            if not issues_file.exists():
                print(f"  SKIP {key}: no issues file")
                continue

            issues = json.loads(issues_file.read_text())[:MAX_ISSUES]
            if not issues:
                print(f"  SKIP {key}: no fixable issues")
                continue

            for model in models:
                print(f"\n  --- {target_name}/{mode}/{model}: "
                      f"{len(issues)} issues ---")

                for iss in issues:
                    fix_key = f"{target_name}_{mode}_{model}_{iss['id']}"

                    # Skip if already done
                    if fix_key in done_keys:
                        print(f"    [cached] #{iss['id']}")
                        continue

                    total_issues += 1
                    print(f"    #{iss['id']}: {iss['title'][:55]}... "
                          f"(conf={iss['confidence']}) ", end="", flush=True)

                    # Attempt fix
                    result = attempt_fix(
                        iss, target_file, WORKSPACE, model=model)

                    # Verify if diff was produced and syntax is OK
                    if result["has_diff"] and result["syntax_ok"]:
                        work_file = WORKSPACE / Path(target_file).name
                        modified_code = work_file.read_text(encoding="utf-8")
                        verify = run_verification(
                            iss, modified_code, model="haiku")
                        result.update(verify)
                        total_fixes += 1
                    elif not result["has_diff"]:
                        result["verdict"] = "no_diff"
                        result["regression"] = False
                        result["detail"] = "Model produced no file changes"
                    else:
                        result["verdict"] = "syntax_error"
                        result["regression"] = False
                        result["detail"] = result["syntax_error"]

                    # Status indicator
                    v = result.get("verdict", "?")
                    symbol = {
                        "fixed": "+", "partial": "~", "unfixed": "-",
                        "no_diff": "0", "syntax_error": "X",
                    }.get(v, "?")
                    reg = " REGRESSION!" if result.get("regression") else ""
                    print(f"[{symbol}] {v} ({result['elapsed_sec']}s, "
                          f"+{result['lines_added']}/-{result['lines_removed']})"
                          f"{reg}")

                    # Save individual fix result + diff
                    fix_file = fixes_dir / f"{fix_key}.json"
                    fix_file.write_text(json.dumps(result, indent=2))
                    if result["diff"]:
                        diff_file = fixes_dir / f"{fix_key}.diff"
                        diff_file.write_text(result["diff"])

                    all_results.append(result)
                    done_keys.add(fix_key)

                    # Checkpoint after every fix
                    checkpoint_file.write_text(
                        json.dumps(all_results, indent=2))

    # Save final results
    final_file = RESULTS_DIR / "fix_results.json"
    final_file.write_text(json.dumps(all_results, indent=2))

    print(f"\n  Total: {total_issues} fix attempts, "
          f"{total_fixes} produced valid diffs")


# ── Phase 4: ANALYZE ──────────────────────────────────────────────────────────

def phase_analyze():
    """Generate analysis reports for all three experiments."""
    print("\n" + "=" * 60)
    print("  PHASE 4: ANALYZE")
    print("=" * 60)

    results_file = RESULTS_DIR / "fix_results.json"
    if not results_file.exists():
        print("  No results to analyze")
        return

    results = json.loads(results_file.read_text())
    if not results:
        print("  Empty results")
        return

    lines = []

    def p(s=""):
        print(s)
        lines.append(s)

    # ── EXPERIMENT A: Fix Reliability Matrix ──────────────────────────────
    p("\n" + "─" * 70)
    p("  EXPERIMENT A: Fix Reliability Matrix")
    p("─" * 70)
    p()
    p(f"{'Target':<12} {'Mode':<8} {'Model':<8} {'N':>4} "
      f"{'Diff':>5} {'Syn':>5} {'Fix':>5} {'Par':>5} "
      f"{'Unf':>5} {'NoDf':>5} {'Reg':>4}")
    p("-" * 80)

    for target_name in TARGETS:
        for mode in SCAN_MODES:
            for model in FIX_MODELS:
                subset = [r for r in results
                          if r["target"] == target_name
                          and r["scan_mode"] == mode
                          and r["model"] == model]
                if not subset:
                    continue

                n = len(subset)
                has_diff = sum(1 for r in subset if r["has_diff"])
                syntax_ok = sum(1 for r in subset
                                if r.get("has_diff") and r.get("syntax_ok"))
                fixed = sum(1 for r in subset
                            if r.get("verdict") == "fixed")
                partial = sum(1 for r in subset
                              if r.get("verdict") == "partial")
                unfixed = sum(1 for r in subset
                              if r.get("verdict") == "unfixed")
                no_diff = sum(1 for r in subset
                              if r.get("verdict") == "no_diff")
                regr = sum(1 for r in subset if r.get("regression"))

                p(f"{target_name:<12} {mode:<8} {model:<8} {n:>4} "
                  f"{has_diff:>5} {syntax_ok:>5} {fixed:>5} {partial:>5} "
                  f"{unfixed:>5} {no_diff:>5} {regr:>4}")

    # Aggregated by mode
    p()
    p("Aggregated by scan mode:")
    for mode in SCAN_MODES:
        subset = [r for r in results if r["scan_mode"] == mode]
        n = len(subset)
        if not n:
            continue
        fixed = sum(1 for r in subset if r.get("verdict") == "fixed")
        has_diff = sum(1 for r in subset if r["has_diff"])
        p(f"  {mode}: {n} issues, {has_diff} diffs ({has_diff/n*100:.0f}%), "
          f"{fixed} fixed ({fixed/n*100:.0f}%)")

    # Aggregated by model
    p()
    p("Aggregated by model:")
    for model in FIX_MODELS:
        subset = [r for r in results if r["model"] == model]
        n = len(subset)
        if not n:
            continue
        fixed = sum(1 for r in subset if r.get("verdict") == "fixed")
        partial = sum(1 for r in subset if r.get("verdict") == "partial")
        has_diff = sum(1 for r in subset if r["has_diff"])
        avg_time = sum(r["elapsed_sec"] for r in subset) / n
        avg_added = sum(r["lines_added"] for r in subset) / n
        avg_removed = sum(r["lines_removed"] for r in subset) / n
        p(f"  {model}: {n} issues, {has_diff} diffs ({has_diff/n*100:.0f}%), "
          f"{fixed} fixed ({fixed/n*100:.0f}%), {partial} partial, "
          f"avg {avg_time:.1f}s, avg +{avg_added:.1f}/-{avg_removed:.1f} lines")

    # ── EXPERIMENT B: Confidence Correlation ──────────────────────────────
    p()
    p("─" * 70)
    p("  EXPERIMENT B: Confidence Score vs Outcome")
    p("─" * 70)
    p()
    p(f"{'Conf':>5} {'Label':<10} {'N':>4} {'Diff':>5} "
      f"{'Fixed':>6} {'Rate':>6} {'AvgTime':>8}")
    p("-" * 55)

    for conf in range(9):
        subset = [r for r in results if r.get("confidence") == conf]
        if not subset:
            continue
        n = len(subset)
        has_diff = sum(1 for r in subset if r["has_diff"])
        fixed = sum(1 for r in subset if r.get("verdict") == "fixed")
        rate = fixed / n * 100 if n else 0
        avg_t = sum(r["elapsed_sec"] for r in subset) / n
        label = confidence_label(conf)
        p(f"{conf:>5} {label:<10} {n:>4} {has_diff:>5} "
          f"{fixed:>6} {rate:>5.0f}% {avg_t:>7.1f}s")

    # Correlation coefficient (Pearson's r)
    confs = [r.get("confidence", 0) for r in results]
    outcomes = [1 if r.get("verdict") == "fixed" else 0 for r in results]
    if len(set(confs)) > 1 and len(set(outcomes)) > 1:
        n = len(confs)
        mean_c = sum(confs) / n
        mean_o = sum(outcomes) / n
        cov = sum((c - mean_c) * (o - mean_o) for c, o in zip(confs, outcomes))
        std_c = (sum((c - mean_c) ** 2 for c in confs)) ** 0.5
        std_o = (sum((o - mean_o) ** 2 for o in outcomes)) ** 0.5
        r = cov / (std_c * std_o) if std_c * std_o > 0 else 0
        p(f"\n  Pearson's r (confidence vs fixed): {r:.3f}")
    else:
        p("\n  Cannot compute correlation (insufficient variance)")

    # ── EXPERIMENT C: Model Comparison ────────────────────────────────────
    p()
    p("─" * 70)
    p("  EXPERIMENT C: Model Comparison (same issues)")
    p("─" * 70)
    p()

    # Pair up same issues fixed by different models
    issue_keys = {}
    for r in results:
        ik = f"{r['target']}_{r['scan_mode']}_{r['issue_id']}"
        if ik not in issue_keys:
            issue_keys[ik] = {}
        issue_keys[ik][r["model"]] = r

    # Count pairwise outcomes
    pairs = {k: v for k, v in issue_keys.items() if len(v) >= 2}
    if pairs:
        p(f"  Paired issues: {len(pairs)}")
        p()

        haiku_wins = 0
        sonnet_wins = 0
        ties = 0
        haiku_only_diff = 0
        sonnet_only_diff = 0

        verdict_order = {"fixed": 3, "partial": 2, "unfixed": 1,
                         "no_diff": 0, "syntax_error": -1, "unknown": -1,
                         "timeout": -1}

        for ik, models_dict in pairs.items():
            h = models_dict.get("haiku", {})
            s = models_dict.get("sonnet", {})
            hv = verdict_order.get(h.get("verdict", "unknown"), -1)
            sv = verdict_order.get(s.get("verdict", "unknown"), -1)

            if hv > sv:
                haiku_wins += 1
            elif sv > hv:
                sonnet_wins += 1
            else:
                ties += 1

            if h.get("has_diff") and not s.get("has_diff"):
                haiku_only_diff += 1
            elif s.get("has_diff") and not h.get("has_diff"):
                sonnet_only_diff += 1

        p(f"  Haiku wins: {haiku_wins} ({haiku_wins/len(pairs)*100:.0f}%)")
        p(f"  Sonnet wins: {sonnet_wins} ({sonnet_wins/len(pairs)*100:.0f}%)")
        p(f"  Ties: {ties} ({ties/len(pairs)*100:.0f}%)")
        p(f"  Haiku-only diff: {haiku_only_diff}")
        p(f"  Sonnet-only diff: {sonnet_only_diff}")

        # Cost comparison
        p()
        h_results = [r for r in results if r["model"] == "haiku"]
        s_results = [r for r in results if r["model"] == "sonnet"]
        h_fixed = sum(1 for r in h_results if r.get("verdict") == "fixed")
        s_fixed = sum(1 for r in s_results if r.get("verdict") == "fixed")
        h_time = sum(r["elapsed_sec"] for r in h_results)
        s_time = sum(r["elapsed_sec"] for r in s_results)

        p(f"  Haiku: {h_fixed} fixed in {h_time:.0f}s total")
        p(f"  Sonnet: {s_fixed} fixed in {s_time:.0f}s total")
        if h_fixed > 0 and s_fixed > 0:
            p(f"  Time ratio: Sonnet is {s_time/h_time:.1f}x slower")
            p(f"  Fix ratio: Sonnet gets {s_fixed/h_fixed:.2f}x more fixes")
    else:
        p("  No paired issues found (need both models)")

    # ── FAILURE ANALYSIS ──────────────────────────────────────────────────
    p()
    p("─" * 70)
    p("  FAILURE ANALYSIS")
    p("─" * 70)
    p()

    no_diffs = [r for r in results if r.get("verdict") == "no_diff"]
    if no_diffs:
        p(f"  No-diff failures ({len(no_diffs)}):")
        for r in no_diffs[:10]:
            p(f"    {r['target']}/{r['scan_mode']}/{r['model']} "
              f"#{r['issue_id']}: {r['issue_title'][:50]} "
              f"(conf={r['confidence']})")

    syntax_errs = [r for r in results
                   if r.get("verdict") == "syntax_error"]
    if syntax_errs:
        p(f"\n  Syntax errors ({len(syntax_errs)}):")
        for r in syntax_errs[:10]:
            p(f"    {r['target']}/{r['scan_mode']}/{r['model']} "
              f"#{r['issue_id']}: {r['syntax_error'][:60]}")

    regressions = [r for r in results if r.get("regression")]
    if regressions:
        p(f"\n  Regressions ({len(regressions)}):")
        for r in regressions:
            p(f"    {r['target']}/{r['scan_mode']}/{r['model']} "
              f"#{r['issue_id']}: {r['issue_title'][:50]}")

    # ── CONFIDENCE THRESHOLD RECOMMENDATION ───────────────────────────────
    p()
    p("─" * 70)
    p("  CONFIDENCE THRESHOLD RECOMMENDATION")
    p("─" * 70)
    p()

    # Find optimal threshold: maximize (fixed - regressions) / total
    best_threshold = 0
    best_score = -1
    for thresh in range(9):
        above = [r for r in results if r.get("confidence", 0) >= thresh]
        if not above:
            continue
        fixed = sum(1 for r in above if r.get("verdict") == "fixed")
        regr = sum(1 for r in above if r.get("regression"))
        score = (fixed - regr * 2) / len(above)  # penalize regressions 2x
        coverage = len(above) / len(results) * 100
        p(f"  Threshold >= {thresh}: {len(above)} issues ({coverage:.0f}%), "
          f"{fixed} fixed, {regr} regressions, score={score:.3f}")
        if score > best_score:
            best_score = score
            best_threshold = thresh

    p(f"\n  >>> Recommended threshold: confidence >= {best_threshold} "
      f"(score={best_score:.3f})")

    # ── DIFF SIZE ANALYSIS ────────────────────────────────────────────────
    p()
    p("─" * 70)
    p("  DIFF SIZE vs OUTCOME")
    p("─" * 70)
    p()

    diff_results = [r for r in results if r["has_diff"]]
    if diff_results:
        # Bucket by diff size
        small = [r for r in diff_results
                 if r["lines_added"] + r["lines_removed"] <= 5]
        medium = [r for r in diff_results
                  if 5 < r["lines_added"] + r["lines_removed"] <= 15]
        large = [r for r in diff_results
                 if r["lines_added"] + r["lines_removed"] > 15]

        for label, bucket in [("Small (1-5)", small),
                              ("Medium (6-15)", medium),
                              ("Large (16+)", large)]:
            if not bucket:
                continue
            n = len(bucket)
            fixed = sum(1 for r in bucket if r.get("verdict") == "fixed")
            regr = sum(1 for r in bucket if r.get("regression"))
            p(f"  {label}: {n} fixes, {fixed} fixed ({fixed/n*100:.0f}%), "
              f"{regr} regressions")

    # Save report
    report_file = RESULTS_DIR / "analysis_report.txt"
    report_file.write_text("\n".join(lines))
    p(f"\n  Report saved to {report_file}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Fix Reliability Experiment Harness")
    parser.add_argument(
        "phase", nargs="?", default="all",
        choices=["all", "scan", "extract", "fix", "analyze"],
        help="which phase to run (default: all)")
    parser.add_argument(
        "--model", default=None,
        help="run fix phase with one model only (haiku or sonnet)")
    parser.add_argument(
        "--target", default=None,
        help="run only one target (starlette, click, tenacity)")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Filter targets if specified
    targets = TARGETS
    if args.target:
        if args.target not in TARGETS:
            print(f"Unknown target: {args.target}")
            sys.exit(1)
        targets = {args.target: TARGETS[args.target]}

    models = FIX_MODELS
    if args.model:
        models = [args.model]

    print(f"Fix Reliability Experiment — {datetime.now().isoformat()}")
    print(f"Targets: {list(targets.keys())}")
    print(f"Scan modes: {SCAN_MODES}")
    print(f"Fix models: {models}")
    print(f"Results dir: {RESULTS_DIR}")

    if args.phase in ("all", "scan"):
        phase_scan(targets=targets)

    if args.phase in ("all", "extract"):
        phase_extract()

    if args.phase in ("all", "fix"):
        phase_fix(models=models)

    if args.phase in ("all", "analyze"):
        phase_analyze()

    print("\nDone.")


if __name__ == "__main__":
    main()

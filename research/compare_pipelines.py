"""Head-to-head comparison: Prism (Haiku + L12) vs Opus Vanilla.

End-to-end: scan for bugs -> fix them -> measure results.

Usage:
    python research/compare_pipelines.py research/real_code_starlette.py
    python research/compare_pipelines.py prism.py
"""
import subprocess, os, sys, shutil, json, difflib, pathlib, re, time, py_compile

# Force UTF-8 on Windows to avoid cp1253 encoding crashes
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJ_DIR = pathlib.Path(__file__).resolve().parent.parent
LENS_DIR = PROJ_DIR / "prisms"
ENV = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
CLAUDE = shutil.which("claude")

# ── Editor Prism (from race_v3, proven 18/20) ────────────────────────
EDITOR_LENS = """\
Execute every step. Output ONLY a JSON object. No markdown, no explanation, no code fences.

Example:
Issue: "Automated execution allows arbitrary shell commands via ALLOWED_TOOLS"
Code:
        _, proc_ok = self._claude.call_checked(
            system_prompt, task_msg,
            model=self.session.model, timeout=600, tools=ALLOWED_TOOLS,
        )
Fix: {"old_string": "            model=self.session.model, timeout=600, tools=ALLOWED_TOOLS,", "new_string": "            model=self.session.model, timeout=600, tools=\\"Read,Edit,Write\\",", "invariant": "Automated mode must restrict tool access"}

Your task:
1. Find the exact line where the issue manifests in the code below.
2. Name the invariant violated (one sentence).
3. Construct the minimal replacement.

Output: {"old_string": "exact copy from code", "new_string": "fixed version", "invariant": "what was violated"}
If not fixable from this snippet: {"skip": true, "search_for": "grep_pattern_to_find_code"}

Rules:
- old_string: copy EXACTLY from the code below, character for character, including all whitespace
- Include 2-3 surrounding context lines in old_string so the match is unique
- The fixed code must compile and run immediately -- verify imports and variable names exist
- Make the MINIMUM change. One replacement only."""

# ── Opus Vanilla Prompt ───────────────────────────────────────────────
OPUS_VANILLA_PROMPT = """\
Analyze this code for bugs, edge cases, and security issues.

For each issue found, output a JSON object on its own line with these fields:
- "title": short description
- "description": what's wrong and why
- "severity": "P0" (critical) | "P1" (important) | "P2" (minor)
- "old_string": exact code to replace (copy character-for-character from the code)
- "new_string": fixed version
- "invariant": what rule was violated

Output ONLY the JSON objects, one per line. No markdown, no explanation.
If a bug cannot be fixed with a simple replacement, still report it but set "old_string" and "new_string" to empty strings.

Code:
"""


def call_claude(model, system_prompt, message, effort="low"):
    """Call claude CLI, return (text, cost, duration_ms)."""
    prompt_file = PROJ_DIR / f"_tmp_compare_{model}.md"
    prompt_file.write_text(system_prompt, encoding="utf-8")
    try:
        proc = subprocess.run(
            [CLAUDE, "-p", "--model", model, "--output-format", "json",
             "--system-prompt-file", str(prompt_file),
             "--tools", "", "--max-turns", "1", "--effort", effort],
            input=message, capture_output=True, text=True, encoding="utf-8",
            timeout=600, env=ENV,
        )
        if proc.returncode != 0:
            print(f"      [call_claude] {model} exit code {proc.returncode}")
            if proc.stderr:
                print(f"      [stderr] {proc.stderr[:200]}")
            return None, 0, 0
        data = json.loads(proc.stdout)
        cost = data.get("total_cost_usd", 0)
        dur = data.get("duration_ms", 0)
        text = data.get("result", "")
        return text, cost, dur
    except subprocess.TimeoutExpired:
        print(f"      [call_claude] {model} TIMEOUT (600s)")
        return None, 0, 0
    except json.JSONDecodeError as e:
        print(f"      [call_claude] {model} bad JSON: {e}")
        return None, 0, 0
    finally:
        prompt_file.unlink(missing_ok=True)


# ── Issue extraction (model-based, same as prism.py) ──────────────────
ISSUE_EXTRACT_PROMPT = (PROJ_DIR / "prompts" / "issue_extract_fallback.md").read_text(
    encoding="utf-8"
)


def parse_bug_table(l12_text, target_name="unknown"):
    """Parse the bug table directly from L12 output. Zero API calls.

    L12 outputs a markdown table like:
    | # | Location | What Breaks | Severity | Fixable? | Prediction |
    |---|---|---|---|---|---|
    | **1** | `Route.matches()` | ... | HIGH | **Fixable** (hint) | ... |

    Returns list of issue dicts for fixable bugs only.
    """
    issues = []

    # Find table rows (lines starting with |)
    lines = l12_text.split("\n")
    table_rows = []
    in_table = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("| #") or stripped.startswith("| **#"):
            in_table = True
            continue  # skip header
        if in_table and stripped.startswith("|---"):
            continue  # skip separator
        if in_table and stripped.startswith("|"):
            table_rows.append(stripped)
        elif in_table and not stripped.startswith("|"):
            in_table = False  # table ended

    if not table_rows:
        return None  # no table found, caller should fall back

    sev_map = {"HIGH": "P1", "MEDIUM": "P2", "LOW": "P3", "VERY LOW": "P3",
               "CRITICAL": "P0", "NONE": "P3"}

    for row in table_rows:
        cells = [c.strip() for c in row.split("|")[1:-1]]  # split and trim
        if len(cells) < 5:
            continue

        # Clean markdown bold/code from cells
        def clean(s):
            return re.sub(r'\*\*([^*]*)\*\*', r'\1', s).replace('`', '').strip()

        num = clean(cells[0])
        location = clean(cells[1])
        what_breaks = clean(cells[2])
        severity = clean(cells[3]).upper()
        fixable = clean(cells[4]) if len(cells) > 4 else ""

        # Skip non-fixable (structural) issues
        fixable_lower = fixable.lower()
        pre_paren = fixable_lower.split("(")[0]
        if ("no" in pre_paren or "structural" in fixable_lower
                or "not fixable" in fixable_lower
                or "by design" in fixable_lower
                or "unfixable" in fixable_lower):
            print(f"      TABLE SKIP #{num}: structural ({fixable[:40]})")
            continue
        if "none" in fixable_lower or fixable_lower.startswith("n/a"):
            print(f"      TABLE SKIP #{num}: n/a")
            continue

        # Extract fix hint from fixable column (text in parentheses)
        hint_match = re.search(r'\(([^)]+)\)', fixable)
        action = hint_match.group(1) if hint_match else fixable

        # Map severity
        priority = "P2"
        for sev_key, prio in sev_map.items():
            if sev_key in severity:
                priority = prio
                break

        issues.append({
            "id": len(issues) + 1,
            "priority": priority,
            "title": f"#{num}: {what_breaks[:60]}",
            "file": target_name,
            "location": location,
            "description": what_breaks,
            "action": action,
        })

    if issues:
        print(f"      Parsed bug table: {len(table_rows)} rows, "
              f"{len(issues)} fixable")

    return issues if issues else None


def extract_issues_from_l12(l12_text, target_name="unknown"):
    """Extract issues from L12 output. Tries bug table first, falls back to model."""
    if not l12_text:
        return []

    # Try 1: parse bug table directly (free, no API call)
    table_issues = parse_bug_table(l12_text, target_name)
    if table_issues:
        print(f"      Extracted {len(table_issues)} issues from bug table (no API call)")
        return table_issues, 0, 0

    # Try 2: model-based extraction (fallback)
    print(f"      No bug table found, extracting via model call...")
    raw, cost, dur = call_claude("haiku", ISSUE_EXTRACT_PROMPT, l12_text)
    if not raw:
        print(f"      Extraction failed")
        return []

    print(f"      Extraction: ${cost:.4f}, {dur/1000:.1f}s")

    # Parse JSON from response
    cleaned = raw.strip()
    cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
    cleaned = re.sub(r'\s*```$', '', cleaned)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        m = re.search(r'\[.*\]', cleaned, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group())
            except json.JSONDecodeError:
                print(f"      JSON parse failed")
                return []
        else:
            print(f"      No JSON found in extraction")
            return []

    # Unwrap: handle bare list or dict with list values
    if isinstance(data, dict):
        merged = []
        for v in data.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                merged.extend(v)
        data = merged or []

    if not isinstance(data, list):
        return []

    # Validate required fields
    validated = []
    for issue in data:
        if not isinstance(issue, dict):
            continue
        if not issue.get("title") or not issue.get("description"):
            continue
        issue.setdefault("file", target_name)
        issue.setdefault("location", "")
        issue.setdefault("action", "")
        issue.setdefault("priority", "P2")
        validated.append(issue)

    return validated, cost, dur


# ── Smart grep (from race_v3) ─────────────────────────────────────────
def extract_search_terms(issue):
    """Mine issue fields for grep search terms (mirrors race_v3 + prism.py)."""
    terms = []
    action = issue.get("action", "")
    desc = issue.get("description", "")
    location = issue.get("location", "")
    combined = f"{issue.get('title', '')} {desc} {action} {location}"

    # Location-based search first (most specific)
    if location:
        loc_funcs = re.findall(r'(_?\w{5,})\(\)', location)
        for f in loc_funcs:
            terms.append(f"def {f}")
        if not loc_funcs:
            terms.append(f"def {location}")
            terms.append(location)

    # Function definitions from all fields
    funcs = re.findall(r'(_\w{5,})\(\)', combined)
    for f in funcs[:3]:
        terms.append(f"def {f}")

    # ALL_CAPS constants
    caps = re.findall(r'[A-Z][A-Z_]{3,}', combined)
    terms.extend(caps[:3])

    # Quoted identifiers from action
    quoted = re.findall(r"'([_a-zA-Z]\w{4,})'", action)
    terms.extend(quoted[:2])

    # Snake_case identifiers (long ones)
    for text in [action, desc]:
        snakes = re.findall(r'[a-z]\w*_\w{3,}', text)
        terms.extend(s for s in snakes if len(s) > 7)

    # Bare function names
    for f in funcs:
        terms.append(f)

    # Class/method names
    classes = re.findall(r'\b([A-Z][a-z]\w+)\b', combined)
    terms.extend(classes[:2])

    # Session-specific routing (from race_v3)
    lower = combined.lower()
    if "session" in lower and any(kw in lower for kw in
            ("persist", "migration", "model_name", "schema")):
        terms.insert(0, "def load(")
        terms.insert(1, "def save(")

    SKIP = {'JSON', 'None', 'True', 'False', 'DOTALL'}
    seen = set()
    return [t for t in terms if t not in SKIP and not (t in seen or seen.add(t))]


def grep_context(lines, term, before=15, after=65):
    """Find term in lines, return surrounding context."""
    for i, line in enumerate(lines):
        if term in line:
            start = max(0, i - before)
            end = min(len(lines), i + after)
            numbered = [f"{start+j+1:4d}  {lines[start+j]}"
                        for j in range(end - start)]
            return "\n".join(numbered), start + 1
    return "", 0


def smart_grep(lines, issue, whole_file_fallback=True):
    """Find relevant code snippet for an issue.

    If grep fails and file is <500 lines, sends the whole file as context.
    """
    terms = extract_search_terms(issue)
    for term in terms[:8]:
        snippet, start = grep_context(lines, term)
        if snippet:
            return snippet, start, term

    # Fallback: send whole file for small files
    if whole_file_fallback and len(lines) <= 500:
        numbered = [f"{i+1:4d}  {lines[i]}" for i in range(len(lines))]
        return "\n".join(numbered), 1, "(whole file)"

    return "", 0, ""


# ── Fuzzy patch application (from race_v3) ────────────────────────────
def apply_patch(patch, content):
    """Apply a patch with 3-layer fuzzy matching."""
    old_str = patch.get("old_string", "")
    new_str = patch.get("new_string", "")
    if not old_str or old_str == new_str:
        return False, content, "empty/identical"

    # Layer 1: exact match
    if old_str in content:
        if content.count(old_str) > 1:
            return False, content, f"ambiguous ({content.count(old_str)})"
        return True, content.replace(old_str, new_str, 1), "exact"

    # Layer 2: whitespace-normalized
    old_lines = [l.rstrip() for l in old_str.splitlines()]
    content_lines = content.splitlines()
    old_joined = "\n".join(old_lines)
    content_joined = "\n".join(l.rstrip() for l in content_lines)
    if old_joined in content_joined:
        idx = content_joined.index(old_joined)
        start_line = content_joined[:idx].count("\n")
        end_line = start_line + old_joined.count("\n")
        original = content.splitlines(keepends=True)
        new_lines = new_str.splitlines(keepends=True)
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines[-1] += "\n"
        result = ("".join(original[:start_line]) +
                  "".join(new_lines) +
                  "".join(original[end_line + 1:]))
        return True, result, "ws-normalized"

    # Layer 3: indent-normalized
    old_bare = [l.strip() for l in old_str.splitlines() if l.strip()]
    if len(old_bare) >= 2:
        bare_content = [l.strip() for l in content_lines]
        for i in range(len(bare_content) - len(old_bare) + 1):
            if bare_content[i:i + len(old_bare)] == old_bare:
                base_indent = len(content_lines[i]) - len(content_lines[i].lstrip())
                indent = " " * base_indent
                new_lines_raw = new_str.splitlines()
                if new_lines_raw:
                    new_base = len(new_lines_raw[0]) - len(new_lines_raw[0].lstrip())
                    reindented = [
                        indent + " " * max(0, len(nl) - len(nl.lstrip()) - new_base) + nl.lstrip()
                        for nl in new_lines_raw
                    ]
                    original = content.splitlines(keepends=True)
                    result = ("".join(original[:i]) +
                              "\n".join(reindented) + "\n" +
                              "".join(original[i + len(old_bare):]))
                    return True, result, "indent-normalized"

    return False, content, "not found"


def syntax_check(filepath):
    """Check Python syntax. Returns True if valid."""
    if not str(filepath).endswith(".py"):
        return True
    try:
        py_compile.compile(str(filepath), doraise=True)
        return True
    except py_compile.PyCompileError:
        return False


# ── Pipeline A: Prism (Haiku + L12 -> editor prism) ───────────────────
def run_prism_pipeline(target_path, max_passes=1, full_scan=False):
    """Run Prism pipeline: scan -> extract issues -> fix each.

    full_scan=False: single L12 call. full_scan=True: L12 + adversarial + synthesis (3 calls).
    max_passes=1: single fix pass. max_passes=3: auto retry unfixed up to 3 passes.
    """
    mode_name = "Full Prism" if full_scan else "Single Prism"
    print(f"\n{'='*60}")
    print(f"  PIPELINE: {mode_name}")
    print(f"{'='*60}")

    content = target_path.read_text(encoding="utf-8", errors="replace")
    total_cost = 0
    total_dur = 0

    # Step 1: L12 scan (single or full pipeline)
    print(f"\n  [1] L12 scan{'  (+ adversarial + synthesis)' if full_scan else ''}...")
    l12_prompt = (LENS_DIR / "l12.md").read_text(encoding="utf-8")
    l12_text, cost, dur = call_claude("haiku", l12_prompt, content)
    total_cost += cost
    total_dur += dur
    if not l12_text:
        print(f"  {' '*4}FAILED: L12 scan returned nothing")
        return {"bugs_found": 0, "bugs_fixed": 0, "cost": total_cost,
                "duration_ms": total_dur, "issues": [], "analysis": ""}
    print(f"  {' '*4}L12 output: {len(l12_text)} chars, ${cost:.4f}")

    analysis_text = l12_text

    if full_scan:
        # Call 2: Adversarial challenge
        print(f"  {' '*4}Adversarial challenge...")
        adv_prompt = (LENS_DIR / "l12_complement_adversarial.md").read_text(
            encoding="utf-8")
        adv_input = (
            f"# SOURCE CODE\n\n{content}\n\n---\n\n"
            f"# STRUCTURAL ANALYSIS (from previous pass)\n\n{l12_text}"
        )
        adv_text, cost, dur = call_claude("haiku", adv_prompt, adv_input)
        total_cost += cost
        total_dur += dur
        if adv_text:
            print(f"  {' '*4}Adversarial output: {len(adv_text)} chars, ${cost:.4f}")
        else:
            print(f"  {' '*4}Adversarial: no output (continuing)")

        # Call 3: Synthesis
        print(f"  {' '*4}Synthesis...")
        synth_prompt = (LENS_DIR / "l12_synthesis.md").read_text(
            encoding="utf-8")
        synth_input = (
            f"# SOURCE CODE\n\n{content}\n\n---\n\n"
            f"# ANALYSIS 1: STRUCTURAL ANALYSIS\n\n{l12_text}\n\n---\n\n"
            f"# ANALYSIS 2: CONTRADICTION ANALYSIS\n\n{adv_text or '(none)'}"
        )
        synth_text, cost, dur = call_claude("haiku", synth_prompt, synth_input)
        total_cost += cost
        total_dur += dur
        if synth_text:
            print(f"  {' '*4}Synthesis output: {len(synth_text)} chars, ${cost:.4f}")
        else:
            print(f"  {' '*4}Synthesis: no output (continuing)")

        # Combine all outputs for extraction
        analysis_text = (
            f"## L12 STRUCTURAL\n\n{l12_text}\n\n"
            f"## ADVERSARIAL CHALLENGE\n\n{adv_text or ''}\n\n"
            f"## SYNTHESIS\n\n{synth_text or ''}"
        )

    # Step 2: Extract issues (model call, same as prism.py)
    print(f"\n  [2] Extracting issues...")
    result = extract_issues_from_l12(analysis_text, target_path.name)
    if isinstance(result, tuple):
        issues, ext_cost, ext_dur = result
        total_cost += ext_cost
        total_dur += ext_dur
    else:
        issues = result
    print(f"  {' '*4}Extracted {len(issues)} issues")

    if not issues:
        return {"bugs_found": 0, "bugs_fixed": 0, "cost": total_cost,
                "duration_ms": total_dur, "issues": [],
                "analysis": analysis_text}

    # Step 3: Fix issues
    working_content = content
    fixed = 0
    fix_results = {i: None for i in range(len(issues))}  # indexed by position

    for pass_num in range(1, max_passes + 1):
        # Determine which issues to attempt this pass
        if pass_num == 1:
            attempt_indices = list(range(len(issues)))
        else:
            attempt_indices = [i for i, r in fix_results.items()
                               if r is not None and not r.get("fixed", False)]
            if not attempt_indices:
                break
            print(f"\n  --- Pass {pass_num}: retrying {len(attempt_indices)} unfixed ---")

        label = f"pass {pass_num}" if max_passes > 1 else "fixing"
        print(f"\n  [2/2] Fixing {len(attempt_indices)} issues ({label})...")

        for idx in attempt_indices:
            issue = issues[idx]
            n = idx + 1
            print(f"    [{n}/{len(issues)}] {issue['title'][:55]}")

            # Smart grep for relevant snippet
            working_lines = working_content.splitlines()
            snippet, start, term = smart_grep(working_lines, issue)
            if not snippet:
                print(f"      SKIP: no matching code found")
                if fix_results[idx] is None:
                    fix_results[idx] = {"title": issue["title"], "fixed": False,
                                        "reason": "no code"}
                continue

            # Call editor prism
            action = issue.get("action", "")
            msg = (
                f"Fix this issue in {target_path.name}:\n"
                f"Title: {issue['title']}\n"
                f"Description: {issue['description']}\n"
            )
            if action:
                msg += f"Action: {action}\n"
            msg += (
                f"\nCode (line {start}+ of {target_path.name}):\n"
                f"{snippet}"
            )
            raw, cost, dur = call_claude("haiku", EDITOR_LENS, msg)
            total_cost += cost
            total_dur += dur

            if not raw:
                print(f"      FAIL: no response")
                fix_results[idx] = {"title": issue["title"], "fixed": False,
                                    "reason": "no response"}
                continue

            # Parse JSON from response
            raw = raw.strip()
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
            try:
                patch = json.loads(raw)
            except json.JSONDecodeError:
                m = re.search(r'\{[\s\S]*\}', raw)
                if m:
                    try:
                        patch = json.loads(m.group())
                    except json.JSONDecodeError:
                        print(f"      FAIL: invalid JSON")
                        fix_results[idx] = {"title": issue["title"],
                                            "fixed": False, "reason": "bad json"}
                        continue
                else:
                    print(f"      FAIL: no JSON in response")
                    fix_results[idx] = {"title": issue["title"], "fixed": False,
                                        "reason": "no json"}
                    continue

            if patch.get("skip"):
                print(f"      SKIP: {patch.get('search_for', 'no hint')[:50]}")
                fix_results[idx] = {"title": issue["title"], "fixed": False,
                                    "reason": "skipped"}
                continue

            # Apply patch with fuzzy matching
            ok, new_content, method = apply_patch(patch, working_content)

            # Self-consistency retry (up to 2 more attempts)
            if not ok:
                for _ in range(2):
                    raw2, c2, d2 = call_claude("haiku", EDITOR_LENS, msg)
                    total_cost += c2
                    total_dur += d2
                    if raw2:
                        raw2 = raw2.strip()
                        raw2 = re.sub(r'^```(?:json)?\s*', '', raw2)
                        raw2 = re.sub(r'\s*```$', '', raw2)
                        try:
                            p2 = json.loads(raw2)
                        except json.JSONDecodeError:
                            m2 = re.search(r'\{[\s\S]*\}', raw2)
                            if m2:
                                try:
                                    p2 = json.loads(m2.group())
                                except json.JSONDecodeError:
                                    continue
                            else:
                                continue
                        if not p2.get("skip"):
                            ok, new_content, method = apply_patch(
                                p2, working_content)
                            if ok:
                                patch = p2
                                break

            if ok:
                # Syntax check before accepting
                tmp = target_path.parent / f"_tmp_check{target_path.suffix}"
                tmp.write_text(new_content, encoding="utf-8")
                if syntax_check(tmp):
                    working_content = new_content
                    fixed += 1
                    print(f"      APPLIED ({method}) | ${cost:.4f}")
                    fix_results[idx] = {
                        "title": issue["title"], "fixed": True,
                        "method": method,
                        "invariant": patch.get("invariant", ""),
                    }
                else:
                    print(f"      FAIL: syntax error after patch")
                    fix_results[idx] = {"title": issue["title"], "fixed": False,
                                        "reason": "syntax error"}
                tmp.unlink(missing_ok=True)
            else:
                print(f"      FAIL: {method}")
                fix_results[idx] = {"title": issue["title"], "fixed": False,
                                    "reason": method}

        pass_fixed = sum(1 for r in fix_results.values()
                         if r and r.get("fixed"))
        print(f"\n  After pass {pass_num}: {pass_fixed}/{len(issues)} fixed")

    print(f"\n  Result: {fixed}/{len(issues)} fixed, ${total_cost:.4f}")

    all_results = [r for r in fix_results.values() if r is not None]
    total_fixed = sum(1 for r in all_results if r.get("fixed"))
    return {
        "bugs_found": len(issues),
        "bugs_fixed": total_fixed,
        "cost": total_cost,
        "duration_ms": total_dur,
        "issues": all_results,
        "analysis": analysis_text,
    }


# ── Pipeline B: Opus Vanilla ─────────────────────────────────────────
def run_opus_pipeline(target_path):
    """Run Opus vanilla: single call to find and fix bugs."""
    print(f"\n{'='*60}")
    print(f"  PIPELINE B: Opus Vanilla (single call, find + fix)")
    print(f"{'='*60}")

    content = target_path.read_text(encoding="utf-8", errors="replace")

    # Single Opus call: find bugs and produce fixes
    print(f"\n  [1/1] Opus analysis + fix generation...")
    text, cost, dur = call_claude(
        "opus", OPUS_VANILLA_PROMPT, content, effort="high")

    if not text:
        print(f"  {' '*4}FAILED: Opus returned nothing")
        return {"bugs_found": 0, "bugs_fixed": 0, "cost": cost,
                "duration_ms": dur, "issues": [], "analysis": ""}

    print(f"  {' '*4}Opus output: {len(text)} chars, ${cost:.4f}")

    # Parse issues from Opus output
    issues = []
    # Try line-by-line JSON
    for line in text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("---"):
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict) and ("title" in obj or "old_string" in obj):
                issues.append(obj)
        except json.JSONDecodeError:
            pass

    # Fallback: try to find JSON array
    if not issues:
        m = re.search(r'\[[\s\S]*\]', text)
        if m:
            try:
                arr = json.loads(m.group())
                if isinstance(arr, list):
                    issues = [i for i in arr if isinstance(i, dict)]
            except json.JSONDecodeError:
                pass

    # Fallback: try individual JSON objects
    if not issues:
        for m in re.finditer(r'\{[^{}]{20,}\}', text):
            try:
                obj = json.loads(m.group())
                if isinstance(obj, dict) and ("title" in obj or "old_string" in obj):
                    issues.append(obj)
            except json.JSONDecodeError:
                pass

    print(f"  {' '*4}Found {len(issues)} issues with fix suggestions")

    # Apply fixes
    working_content = content
    fixed = 0
    fix_results = []

    for idx, issue in enumerate(issues, 1):
        title = issue.get("title", f"Issue {idx}")
        print(f"    [{idx}/{len(issues)}] {title[:55]}")

        old_str = issue.get("old_string", "")
        new_str = issue.get("new_string", "")

        if not old_str or not new_str or old_str == new_str:
            print(f"      SKIP: no actionable fix")
            fix_results.append({"title": title, "fixed": False,
                                "reason": "no fix provided"})
            continue

        ok, new_content, method = apply_patch(
            {"old_string": old_str, "new_string": new_str},
            working_content)

        if ok:
            tmp = target_path.parent / f"_tmp_check{target_path.suffix}"
            tmp.write_text(new_content, encoding="utf-8")
            if syntax_check(tmp):
                working_content = new_content
                fixed += 1
                print(f"      APPLIED ({method}) | "
                      f"{issue.get('severity', '?')}")
                fix_results.append({
                    "title": title, "fixed": True, "method": method,
                    "severity": issue.get("severity", ""),
                    "invariant": issue.get("invariant", ""),
                })
            else:
                print(f"      FAIL: syntax error after patch")
                fix_results.append({"title": title, "fixed": False,
                                    "reason": "syntax error"})
            tmp.unlink(missing_ok=True)
        else:
            print(f"      FAIL: {method}")
            fix_results.append({"title": title, "fixed": False,
                                "reason": method})

    print(f"\n  Result: {fixed}/{len(issues)} fixed, ${cost:.4f}")

    return {
        "bugs_found": len(issues),
        "bugs_fixed": fixed,
        "cost": cost,
        "duration_ms": dur,
        "issues": fix_results,
        "analysis": text,
    }


# ── Summary helpers ───────────────────────────────────────────────────
def _pct(fixed, found):
    return (fixed / found * 100) if found else 0


def _print_col(label, results, keys):
    """Print a row with label + one value per result dict."""
    vals = []
    for k in keys:
        r = results[k]
        vals.append(r)
    # handled per-row in caller
    return vals


def print_summary(results, keys):
    """Print comparison table for any number of pipelines."""
    header = f"  {'':30s}"
    for k in keys:
        header += f" {k:>17s}"
    print(header)
    print(f"  {'─' * (30 + 18 * len(keys))}")

    row = f"  {'Bugs found':30s}"
    for k in keys:
        row += f" {results[k]['bugs_found']:>17d}"
    print(row)

    row = f"  {'Bugs fixed':30s}"
    for k in keys:
        row += f" {results[k]['bugs_fixed']:>17d}"
    print(row)

    row = f"  {'Fix rate':30s}"
    for k in keys:
        r = results[k]
        pct = _pct(r['bugs_fixed'], r['bugs_found'])
        row += f" {pct:>16.0f}%"
    print(row)

    row = f"  {'Cost':30s}"
    for k in keys:
        row += f" ${results[k]['cost']:>16.4f}"
    print(row)

    row = f"  {'Time':30s}"
    for k in keys:
        row += f" {results[k]['duration_ms']/1000:>16.1f}s"
    print(row)
    print()


# ── Main ──────────────────────────────────────────────────────────────
def main():
    # Parse args: <target> [--mode single|auto|full|opus-only]
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]

    if not args:
        print("Usage: python research/compare_pipelines.py <target_file> [--mode full]")
        print("  --mode single   Single Prism only (single scan + 1 fix pass)")
        print("  --mode auto     Full Prism only (full scan + auto fix 3 pass)")
        print("  --mode opus     Opus Vanilla only")
        print("  --mode prism    Both Prism modes (no Opus)")
        print("  --mode full     All 3: Opus + Single Prism + Full Prism (default)")
        sys.exit(1)

    mode = "full"
    for f in flags:
        if f.startswith("--mode"):
            if "=" in f:
                mode = f.split("=", 1)[1]
            else:
                idx = sys.argv.index(f)
                if idx + 1 < len(sys.argv):
                    mode = sys.argv[idx + 1]

    target = pathlib.Path(args[0])
    if not target.is_absolute():
        target = PROJ_DIR / target
    if not target.exists():
        print(f"File not found: {target}")
        sys.exit(1)

    line_count = len(target.read_text(encoding="utf-8").splitlines())
    print(f"\n{'='*60}")
    print(f"  COMPARISON: {target.name} ({line_count} lines)")
    print(f"  Mode: {mode}")
    print(f"{'='*60}")

    results = {}
    keys = []

    # Run pipelines based on mode
    if mode in ("full", "opus"):
        opus_result = run_opus_pipeline(target)
        results["Opus Vanilla"] = opus_result
        keys.append("Opus Vanilla")

    if mode in ("full", "single", "prism"):
        single_result = run_prism_pipeline(target, max_passes=1, full_scan=False)
        results["Single Prism"] = single_result
        keys.append("Single Prism")

    if mode in ("full", "auto", "prism"):
        auto_result = run_prism_pipeline(target, max_passes=3, full_scan=True)
        results["Full Prism"] = auto_result
        keys.append("Full Prism")

    # Summary
    print(f"\n{'='*60}")
    print(f"  FINAL COMPARISON")
    print(f"{'='*60}\n")
    print_summary(results, keys)

    # Save results
    out_dir = PROJ_DIR / "output" / "comparison"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = target.stem
    save_data = {
        "target": target.name,
        "lines": line_count,
        "mode": mode,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    for k in keys:
        safe_key = k.lower().replace(" ", "_")
        r = results[k]
        r["analysis_length"] = len(r.get("analysis", ""))
        # Save analysis text separately
        if r.get("analysis"):
            (out_dir / f"{safe_key}_{stem}_analysis.md").write_text(
                r["analysis"], encoding="utf-8")
        save_r = {kk: vv for kk, vv in r.items() if kk != "analysis"}
        save_data[safe_key] = save_r

    out_file = out_dir / f"compare_{stem}_{mode}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(save_data, f, indent=2, ensure_ascii=False, default=str)
    print(f"  Results saved: {out_file}")

    print(f"\n  Done!")


if __name__ == "__main__":
    main()

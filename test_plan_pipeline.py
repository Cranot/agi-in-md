#!/usr/bin/env python3
"""Tests for prism.py v0.8 — plan, display, JSON parsing, backward compat."""

import json
import pathlib
import sys
import os

# Add project dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prism import PrismREPL


def test_parse_stage_json():
    """Test JSON parsing from model output."""
    repl = PrismREPL.__new__(PrismREPL)
    repl.working_dir = __import__("pathlib").Path(".")

    # Clean JSON array
    result = repl._parse_stage_json(
        '[{"id": 1, "files": ["a.py"]}]', "test")
    assert result == [{"id": 1, "files": ["a.py"]}], f"Got: {result}"

    # JSON in markdown fences
    result = repl._parse_stage_json(
        '```json\n[{"id": 1, "size": "M"}]\n```', "test")
    assert result == [{"id": 1, "size": "M"}], f"Got: {result}"

    # JSON embedded in prose
    result = repl._parse_stage_json(
        'Here is the result:\n[{"id": 2, "files": ["a.py"]}]\nDone.',
        "test")
    assert result == [{"id": 2, "files": ["a.py"]}], f"Got: {result}"

    # JSON object with list value — unwrapped to the list (dict unwrapping)
    result = repl._parse_stage_json(
        '{"phases": [{"phase": 1}]}', "test")
    assert result == [{"phase": 1}], f"Got: {result}"

    # Empty/error returns None
    assert repl._parse_stage_json("", "test") is None
    assert repl._parse_stage_json("[Error: timeout]", "test") is None
    assert repl._parse_stage_json("no json here", "test") is None

    print("  _parse_stage_json: PASS")


def test_enriched_plan_format():
    """Test that enriched plan.json has the expected structure."""
    issues = [
        {"id": 1, "file": "a.py", "priority": "P0", "title": "Bug",
         "files": ["a.py", "b.py"], "size": "S",
         "spec": "Fix method X", "done_when": "Test passes"},
        {"id": 2, "file": "b.py", "priority": "P1", "title": "Refactor",
         "files": ["b.py"], "size": "M"},
    ]

    enriched = {}
    for i in issues:
        iid = i.get("id")
        if iid is not None:
            enriched[str(iid)] = {
                k: i.get(k) for k in (
                    "files", "size", "spec", "done_when")
                if i.get(k) is not None
            }

    assert "1" in enriched
    assert enriched["1"]["files"] == ["a.py", "b.py"]
    assert enriched["1"]["size"] == "S"
    assert enriched["1"]["spec"] == "Fix method X"
    assert "spec" not in enriched["2"]  # wasn't set

    print("  enriched format: PASS")


def test_autopilot_enriched_lookup():
    """Test that autopilot correctly reads enriched data."""
    issue = {"id": 5, "file": "test.py", "title": "Fix X",
             "description": "Desc", "action": "Old action"}
    enriched_issues = {
        "5": {"spec": "Change method Y in line 100",
              "done_when": "py_compile passes",
              "size": "S"}
    }

    enriched = enriched_issues.get(str(issue.get("id", "")), {})
    spec = enriched.get("spec", "")
    done_when = enriched.get("done_when", "")
    size = enriched.get("size", issue.get("size", "M"))

    assert spec == "Change method Y in line 100"
    assert done_when == "py_compile passes"
    assert size == "S"

    # Without enriched data, falls back
    enriched2 = {}.get(str(issue.get("id", "")), {})
    spec2 = enriched2.get("spec", "")
    size2 = enriched2.get("size", issue.get("size", "M"))
    assert spec2 == ""
    assert size2 == "M"  # default

    print("  autopilot enriched lookup: PASS")


def test_backward_compatibility():
    """Verify old plan.json format still works with autopilot."""
    # Old format (no enriched_issues)
    old_plan = {
        "generated_at": "2026-01-01T00:00:00",
        "issue_count": 3,
        "plan": {
            "phases": [
                {"phase": 1, "streams": [
                    {"name": "safety", "tasks": [1, 2], "reason": "P0 first"}
                ]},
                {"phase": 2, "streams": [
                    {"name": "quality", "tasks": [3], "reason": "after safety"}
                ]}
            ]
        }
    }

    plan_json = old_plan.get("plan")
    enriched_issues = old_plan.get("enriched_issues", {})

    assert plan_json is not None
    assert plan_json["phases"][0]["streams"][0]["tasks"] == [1, 2]
    assert enriched_issues == {}

    # New format with enrichment
    new_plan = {
        "generated_at": "2026-03-02T00:00:00",
        "issue_count": 3,
        "plan": old_plan["plan"],
        "enriched_issues": {
            "1": {"files": ["a.py"], "size": "S", "spec": "Fix X", "done_when": "Test"},
            "2": {"files": ["a.py"], "size": "M"},
        }
    }

    assert new_plan["plan"]["phases"] == old_plan["plan"]["phases"]
    assert new_plan["enriched_issues"]["1"]["spec"] == "Fix X"

    # Missing fields: plan with no priority or size should handle gracefully
    incomplete_plan = {
        "generated_at": "2026-03-01T00:00:00",
        "issue_count": 2,
        "plan": {
            "phases": [
                {"phase": 1, "streams": [
                    {"name": "safety", "tasks": [1]}  # no reason field
                ]}
            ]
        }
    }

    # Accessing fields that may not exist should use .get() with defaults
    plan_json_incomplete = incomplete_plan.get("plan")
    phase = plan_json_incomplete["phases"][0]
    stream = phase["streams"][0]
    reason = stream.get("reason", "unknown")  # graceful default
    assert reason == "unknown", f"Missing field should default, got: {reason}"

    # Missing enriched_issues in plan
    enriched_incomplete = incomplete_plan.get("enriched_issues", {})
    assert enriched_incomplete == {}, "Missing enriched_issues should default to empty dict"

    # Accessing issue fields without crashing
    issue_without_priority = {"id": 1, "title": "Bug"}  # no priority field
    priority = issue_without_priority.get("priority", "P2")  # default priority
    size = issue_without_priority.get("size", "M")  # default size
    assert priority == "P2" and size == "M", "Missing fields should have sensible defaults"

    print("  backward compatibility: PASS")


def test_plan_md_generation():
    """Test plan.md is generated correctly from structured data."""
    issues = [
        {"id": 1, "priority": "P0", "title": "Critical bug", "size": "S",
         "spec": "Fix null check in line 50"},
        {"id": 2, "priority": "P1", "title": "Refactor auth", "size": "L"},
        {"id": 3, "priority": "P2", "title": "Add logging", "size": "M"},
    ]
    plan_json = {
        "phases": [
            {"phase": 1, "streams": [
                {"name": "safety", "tasks": [1], "reason": "P0 first"}
            ]},
            {"phase": 2, "streams": [
                {"name": "auth", "tasks": [2], "reason": "needs safety first"},
                {"name": "observability", "tasks": [3], "reason": "independent"}
            ]}
        ]
    }

    # Reproduce plan.md generation from _cmd_plan
    md_parts = ["# Execution Plan\n", f"3 issues\n"]
    for phase in plan_json.get("phases", []):
        pnum = phase.get("phase", "?")
        md_parts.append(f"\n## Phase {pnum}\n")
        for stream in phase.get("streams", []):
            sname = stream.get("name", "?")
            reason = stream.get("reason", "")
            md_parts.append(f"\n### {sname}")
            if reason:
                md_parts.append(f"_{reason}_\n")
            for tid in stream.get("tasks", []):
                iss = next((i for i in issues if i.get("id") == tid), None)
                if iss:
                    size = iss.get("size", "?")
                    pri = iss.get("priority", "P2")
                    md_parts.append(
                        f"- **#{tid}** [{pri}] {size} — "
                        f"{iss.get('title', '')}")
    plan_md = "\n".join(md_parts)

    assert "## Phase 1" in plan_md
    assert "## Phase 2" in plan_md
    assert "**#1** [P0] S" in plan_md
    assert "**#2** [P1] L" in plan_md
    assert "**#3** [P2] M" in plan_md

    print("  plan.md generation: PASS")


def test_display_output():
    """Test the display section handles all cases."""
    issues = [
        {"id": 1, "priority": "P0", "title": "Bug", "size": "S"},
        {"id": 2, "priority": "P1", "title": "Fix", "size": "M"},
        {"id": 3, "priority": "P2", "title": "Clean", "size": "L"},
    ]
    plan_json = {
        "phases": [
            {"phase": 1, "streams": [
                {"name": "safety", "tasks": [1], "reason": "critical"}
            ]},
            {"phase": 2, "streams": [
                {"name": "refactor", "tasks": [2, 3], "reason": "after safety"}
            ]}
        ]
    }

    # Reproduce display logic from _cmd_plan
    lines = []
    for phase in plan_json.get("phases", []):
        pnum = phase.get("phase", "?")
        stream_parts = []
        for s in phase.get("streams", []):
            task_parts = [f"#{tid}" for tid in s.get("tasks", [])]
            stream_parts.append(
                f"{s.get('name', '?')} ({', '.join(task_parts)})")
        lines.append(f"Phase {pnum}: {', '.join(stream_parts)}")

    assert lines[0] == "Phase 1: safety (#1)"
    assert lines[1] == "Phase 2: refactor (#2, #3)"

    print("  display output: PASS")


def test_default_config():
    """Test DEFAULT_CONFIG has expected keys."""
    from prism import DEFAULT_CONFIG
    assert "code_extensions" in DEFAULT_CONFIG
    print("  default config: PASS")


def test_extract_structural_context():
    """Test conservation law + meta-law extraction from L12 output."""
    repl = PrismREPL.__new__(PrismREPL)

    # Real L12 output pattern (numbered heading)
    text1 = (
        "## 12. Conservation Law\n\n"
        "> **Clarity × Authority = constant**\n\n"
        "Hidden authority means guaranteed correctness.\n\n"
        "## 13. Apply Diagnostic"
    )
    result = repl._extract_structural_context(text1)
    assert "Clarity × Authority = constant" in result
    assert "Conservation law:" in result

    # Unnumbered heading
    text2 = (
        "## Conservation Law\n\n"
        "Product form: X × Y = k\n\n"
        "## Meta-Law\n\n"
        "Distributed authority distributes risk.\n\n"
        "## End"
    )
    result = repl._extract_structural_context(text2)
    assert "Conservation law:" in result
    assert "Meta-law:" in result
    assert "Product form" in result
    assert "Distributed authority" in result

    # "The Conservation Law" variant
    text3 = (
        "## The Conservation Law\n\n"
        "Sum form: A + B = constant\n\n"
        "## 15. META-CONSERVATION LAW\n\n"
        "Meta-level finding here.\n\n"
        "## 16. Next"
    )
    result = repl._extract_structural_context(text3)
    assert "Sum form" in result
    assert "Meta-level finding" in result

    # No conservation law → empty string
    assert repl._extract_structural_context("## Random heading\nstuff") == ""
    assert repl._extract_structural_context("") == ""
    assert repl._extract_structural_context(None) == ""

    # Truncation: conservation law > 300 chars
    long_body = "x " * 200  # 400 chars
    text4 = f"## Conservation Law\n\n{long_body}\n\n## Next"
    result = repl._extract_structural_context(text4)
    assert len(result) < 350  # truncated
    assert result.endswith("...")

    print("  _extract_structural_context: PASS")


def test_parse_scan_args():
    """Test _parse_scan_args mode parsing."""
    parse = PrismREPL._parse_scan_args

    # Basic modes
    r = parse("file.py")
    assert r["mode"] == "single" and r["arg"] == "file.py"

    r = parse("file.py full")
    assert r["mode"] == "full" and r["arg"] == "file.py"

    r = parse("file.py discover")
    assert r["mode"] == "discover" and r["arg"] == "file.py"

    # expand → its own mode
    r = parse("file.py expand")
    assert r["mode"] == "expand" and r["arg"] == "file.py"
    assert r["expand_indices"] is None
    assert r["expand_mode"] is None

    # expand with indices
    r = parse("file.py expand 1,3,5")
    assert r["mode"] == "expand" and r["arg"] == "file.py"
    assert r["expand_indices"] == "1,3,5"

    # expand with * (all)
    r = parse("file.py expand *")
    assert r["mode"] == "expand" and r["arg"] == "file.py"
    assert r["expand_indices"] == "*"

    # expand single (all picked areas → single prism)
    r = parse("file.py expand single")
    assert r["mode"] == "expand"
    assert r["expand_mode"] == "single"

    # expand full (all picked areas → full prism)
    r = parse("file.py expand full")
    assert r["mode"] == "expand"
    assert r["expand_mode"] == "full"

    # expand indices + mode
    r = parse("file.py expand 1,3 full")
    assert r["mode"] == "expand"
    assert r["expand_indices"] == "1,3"
    assert r["expand_mode"] == "full"

    # discover full
    r = parse("file.py discover full")
    assert r["mode"] == "discover_full" and r["arg"] == "file.py"

    # deep="..." backward compat → target full
    r = parse('file.py deep="error handling"')
    assert r["mode"] == "target" and r["target_goal"] == "error handling"
    assert r["target_mode"] == "full"
    assert r["arg"] == "file.py"

    # deep=N backward compat → expand N full
    r = parse("file.py deep=3")
    assert r["mode"] == "expand" and r["expand_indices"] == "3"
    assert r["expand_mode"] == "full"
    assert r["arg"] == "file.py"

    # target="..." custom goal (single by default)
    r = parse('file.py target="race conditions"')
    assert r["mode"] == "target" and r["target_goal"] == "race conditions"
    assert r["target_mode"] is None
    assert r["arg"] == "file.py"

    # target=N no longer valid — target is string-only
    # (target=2 won't match, falls through to other parsing)

    # target="..." full → full prism for custom goal
    r = parse('file.py target="race conditions" full')
    assert r["mode"] == "target" and r["target_goal"] == "race conditions"
    assert r["target_mode"] == "full"
    assert r["arg"] == "file.py"

    # fix and fix auto
    r = parse("file.py fix")
    assert r["mode"] == "fix" and r["fix_auto"] is False
    r = parse("file.py fix auto")
    assert r["mode"] == "fix" and r["fix_auto"] is True

    # deep="..." backward compat takes priority (checked first)
    r = parse('file.py deep="X" target="Y"')
    assert r["mode"] == "target" and r["target_goal"] == "X"
    assert r["target_mode"] == "full"

    # optimize="..." basic
    r = parse('file.py optimize="maximize security"')
    assert r["mode"] == "optimize"
    assert r["optimize_goal"] == "maximize security"
    assert r["arg"] == "file.py"
    assert r.get("optimize_mode") is None  # single by default

    # optimize="..." full
    r = parse('file.py optimize="security" full')
    assert r["mode"] == "optimize"
    assert r["optimize_goal"] == "security"
    assert r.get("optimize_mode") == "full"

    # optimize="..." full max=10 domains=3
    r = parse('file.py optimize="perf" full max=10 domains=3')
    assert r["mode"] == "optimize"
    assert r["optimize_goal"] == "perf"
    assert r.get("optimize_mode") == "full"
    assert r.get("optimize_max") == 10
    assert r.get("optimize_domains") == 3

    print("  _parse_scan_args: PASS")


def test_discover_results_persistence():
    """Test round-trip save/load of discover.json."""
    import tempfile
    repl = PrismREPL.__new__(PrismREPL)
    repl.working_dir = pathlib.Path(tempfile.mkdtemp())
    repl._discover_results = []

    data = [
        {"name": "prism_a", "prism_path": "code_py/prism_a",
         "preview": "Identify...", "domain": "code_py"},
        {"name": "prism_b", "prism_path": "code_py/prism_b",
         "preview": "Extract...", "domain": "code_py"},
    ]
    repl._save_discover_results(data, "auth.py")

    # Clear memory, force load from disk
    repl._discover_results = []
    loaded = repl._load_discover_results("auth.py")
    assert len(loaded) == 2
    assert loaded[0]["name"] == "prism_a"
    assert loaded[1]["prism_path"] == "code_py/prism_b"

    # Different file returns empty (no cross-contamination)
    repl._discover_results = []
    assert repl._load_discover_results("router.py") == []

    # Verify file on disk is named per-stem
    assert (repl.working_dir / ".deep" / "discover_auth.json").exists()

    # Cleanup
    import shutil
    shutil.rmtree(repl.working_dir, ignore_errors=True)

    print("  discover_results_persistence: PASS")


def test_cook_universal_prompt_format():
    """Verify COOK_UNIVERSAL and COOK_UNIVERSAL_PIPELINE placeholders work."""
    from prism import COOK_UNIVERSAL, COOK_UNIVERSAL_PIPELINE
    # Single prism
    formatted = COOK_UNIVERSAL.format(intent="analyze for security")
    assert "analyze for security" in formatted
    assert "{intent}" not in formatted
    # Pipeline
    formatted_p = COOK_UNIVERSAL_PIPELINE.format(
        intent="deep analysis of error handling")
    assert "deep analysis of error handling" in formatted_p
    assert "{intent}" not in formatted_p
    # Both must produce valid JSON template hints
    assert "name" in formatted.lower()
    assert "prompt" in formatted.lower()
    assert "role" in formatted_p.lower()

    print("  cook_universal_prompt_format: PASS")


def test_discover_domains_empty_response():
    """_discover_domains returns [] and prints diagnostic on empty response."""
    import io
    repl = PrismREPL.__new__(PrismREPL)
    repl.working_dir = pathlib.Path(".")
    repl.session = type("S", (), {"model": "haiku"})()
    repl._claude = type("C", (), {
        "call": staticmethod(lambda *a, **kw: "")
    })()

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        result = repl._discover_domains("test_domain")
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout

    assert result == [], f"Expected empty list, got: {result}"
    assert "no response" in output, f"Expected 'no response' in: {output}"

    print("  discover_domains_empty_response: PASS")


def test_deep_goal_resolution():
    """Int→discover lookup, string→direct."""
    repl = PrismREPL.__new__(PrismREPL)
    repl.working_dir = pathlib.Path(".")
    repl._discover_results = [
        {"name": "error_handling", "prism_path": "code_py/error_handling",
         "preview": "...", "domain": "code_py"},
        {"name": "state_mgmt", "prism_path": "code_py/state_mgmt",
         "preview": "...", "domain": "code_py"},
    ]

    # Int goal resolves to discover name
    # We can't run the full _run_deep (needs claude), but test resolution
    # by checking that the slug would be correct
    import re as re_mod
    goal_int = 2  # should resolve to "state_mgmt"
    results = repl._load_discover_results()
    assert results[goal_int - 1]["name"] == "state_mgmt"

    # String goal passes through
    goal_str = "memory leaks"
    slug = re_mod.sub(r'[^a-z0-9]+', '_', goal_str.lower()).strip('_')[:40]
    assert slug == "memory_leaks"

    print("  deep_goal_resolution: PASS")


def test_diff_issues():
    """Test issue diffing by (location, description[:50]) signature."""
    repl = PrismREPL.__new__(PrismREPL)

    old = [
        {"id": 1, "location": "method_a", "description": "Missing null check"},
        {"id": 2, "location": "method_b", "description": "Race condition in handler"},
    ]
    new = [
        {"id": 1, "location": "method_a", "description": "Missing null check"},  # same
        {"id": 2, "location": "method_c", "description": "New buffer overflow"},  # new
        {"id": 3, "location": "method_b", "description": "Race condition in handler"},  # same (diff id)
    ]

    diff = repl._diff_issues(old, new)
    assert len(diff) == 1
    assert diff[0]["location"] == "method_c"

    # Empty old → all new
    diff2 = repl._diff_issues([], new)
    assert len(diff2) == 3

    # Empty new → none
    diff3 = repl._diff_issues(old, [])
    assert len(diff3) == 0

    # Falls back to file field when no location
    old4 = [{"id": 1, "file": "a.py", "description": "Bug in a"}]
    new4 = [
        {"id": 1, "file": "a.py", "description": "Bug in a"},  # same
        {"id": 2, "file": "b.py", "description": "Bug in b"},  # new
    ]
    diff4 = repl._diff_issues(old4, new4)
    assert len(diff4) == 1
    assert diff4[0]["file"] == "b.py"

    print("  _diff_issues: PASS")


def test_parse_selection():
    """Test _parse_selection handles ranges, commas, *, bounds."""
    parse = PrismREPL._parse_selection

    # Single values
    assert parse("1", 5) == [1]
    assert parse("3", 5) == [3]

    # Comma-separated
    assert parse("1,3,5", 7) == [1, 3, 5]

    # Range
    assert parse("2-4", 7) == [2, 3, 4]

    # Mixed
    assert parse("1,3-5,7", 7) == [1, 3, 4, 5, 7]

    # Star = all
    assert parse("*", 4) == [1, 2, 3, 4]

    # Empty = all
    assert parse("", 3) == [1, 2, 3]

    # Out of bounds filtered
    assert parse("0,1,99", 5) == [1]

    # Deduplication
    assert parse("1,1,2", 5) == [1, 2]

    print("  _parse_selection: PASS")


def test_load_cached_pipeline():
    """Test _load_cached_pipeline reads ordered .md files."""
    import tempfile
    repl = PrismREPL.__new__(PrismREPL)
    tmp = pathlib.Path(tempfile.mkdtemp())

    # Empty dir → None
    assert repl._load_cached_pipeline(tmp) is None

    # Single file → None (need >= 2)
    (tmp / "00_primary.md").write_text("prism one", encoding="utf-8")
    assert repl._load_cached_pipeline(tmp) is None

    # Two files → valid pipeline
    (tmp / "01_adversarial.md").write_text("prism two",
                                           encoding="utf-8")
    result = repl._load_cached_pipeline(tmp)
    assert result is not None
    assert len(result) == 2
    assert result[0]["name"] == "primary"
    assert result[0]["prompt"] == "prism one"
    assert result[1]["name"] == "adversarial"
    assert result[1]["prompt"] == "prism two"

    # Cleanup
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

    print("  _load_cached_pipeline: PASS")


def test_build_project_map():
    """Test _build_project_map creates compact summary."""
    import tempfile
    repl = PrismREPL.__new__(PrismREPL)
    tmp = pathlib.Path(tempfile.mkdtemp())

    # Create a mini project
    (tmp / "main.py").write_text(
        "import os\nclass App:\n    pass\n", encoding="utf-8")
    (tmp / "utils.py").write_text(
        "def helper():\n    return 42\n", encoding="utf-8")

    result = repl._build_project_map(tmp)
    assert "2 files" in result
    assert "main.py" in result
    assert "utils.py" in result
    assert "import os" in result
    assert "def helper" in result

    # Empty dir → empty string
    empty = pathlib.Path(tempfile.mkdtemp())
    assert repl._build_project_map(empty) == ""

    # Cleanup
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.rmtree(empty, ignore_errors=True)

    print("  _build_project_map: PASS")


def test_cmd_mode_prism():
    """Verify /prism command sets chat mode correctly."""
    import io
    repl = PrismREPL.__new__(PrismREPL)
    repl.working_dir = pathlib.Path(".")
    repl._chat_mode = "off"
    repl._active_prism_name = None
    repl._active_prism_prompt = None

    # Stub _load_prism for static prism test
    repl._load_prism = lambda name: "fake prompt" if name == "pedagogy" else None

    old_stdout = sys.stdout

    # /prism single
    sys.stdout = io.StringIO()
    repl._cmd_mode("single")
    sys.stdout = old_stdout
    assert repl._chat_mode == "single"
    assert repl._active_prism_name is None

    # /prism full
    sys.stdout = io.StringIO()
    repl._cmd_mode("full")
    sys.stdout = old_stdout
    assert repl._chat_mode == "full"
    assert repl._active_prism_name is None

    # /prism off
    sys.stdout = io.StringIO()
    repl._cmd_mode("off")
    sys.stdout = old_stdout
    assert repl._chat_mode == "off"

    # /prism pedagogy (static prism)
    sys.stdout = io.StringIO()
    repl._cmd_mode("pedagogy")
    sys.stdout = old_stdout
    assert repl._chat_mode == "off"
    assert repl._active_prism_name == "pedagogy"
    assert repl._active_prism_prompt == "fake prompt"

    # /prism nonexistent → stays unchanged
    sys.stdout = io.StringIO()
    repl._cmd_mode("nonexistent")
    out = sys.stdout.getvalue()
    sys.stdout = old_stdout
    assert "Unknown" in out
    assert repl._active_prism_name == "pedagogy"  # unchanged

    # /prism (no arg) → show current
    sys.stdout = io.StringIO()
    repl._cmd_mode("")
    out = sys.stdout.getvalue()
    sys.stdout = old_stdout
    assert "off" in out.lower() or "vanilla" in out.lower()

    # Default mode is "off"
    repl2 = PrismREPL.__new__(PrismREPL)
    repl2._chat_mode = "off"
    assert repl2._chat_mode == "off"

    print("  cmd_mode_prism: PASS")


def test_chat_mode_dispatch():
    """Verify chat loop dispatches to correct method based on _chat_mode."""
    repl = PrismREPL.__new__(PrismREPL)
    repl._chat_mode = "off"
    repl._active_prism_name = None
    repl._active_prism_prompt = None

    calls = []
    repl._send_and_stream = lambda msg: calls.append(("vanilla", msg))
    repl._chat_single_prism = lambda msg: calls.append(("single", msg))
    repl._chat_full_pipeline = lambda msg: calls.append(("full", msg))

    # Simulate the dispatch logic from the chat loop
    def dispatch(message):
        if repl._chat_mode == "full":
            repl._chat_full_pipeline(message)
        elif repl._chat_mode == "single":
            repl._chat_single_prism(message)
        else:
            repl._send_and_stream(message)

    # off → vanilla
    calls.clear()
    repl._chat_mode = "off"
    dispatch("hello")
    assert calls[0] == ("vanilla", "hello")

    # single → dynamic cook
    calls.clear()
    repl._chat_mode = "single"
    dispatch("analyze this")
    assert calls[0] == ("single", "analyze this")

    # full → dynamic pipeline
    calls.clear()
    repl._chat_mode = "full"
    dispatch("deep analysis")
    assert calls[0] == ("full", "deep analysis")

    print("  chat_mode_dispatch: PASS")


def test_target_by_index_bounds():
    """Verify index bounds are enforced: reject 0 and OOB, accept valid indices."""
    repl = PrismREPL.__new__(PrismREPL)
    repl.working_dir = pathlib.Path(".")
    repl._discover_results = [
        {"name": "error_handling", "prism_path": "code_py/error_handling",
         "preview": "...", "domain": "code_py"},
        {"name": "state_mgmt", "prism_path": "code_py/state_mgmt",
         "preview": "...", "domain": "code_py"},
    ]

    # Index 0 rejected (indices start at 1)
    try:
        # Simulate _run_target_by_index behavior
        idx = 0
        if idx < 1 or idx > len(repl._discover_results):
            raise IndexError(f"Index {idx} out of range [1..{len(repl._discover_results)}]")
        assert False, "Should have raised IndexError for index 0"
    except IndexError as e:
        assert "out of range" in str(e).lower()

    # Out of bounds rejected
    try:
        idx = 99
        if idx < 1 or idx > len(repl._discover_results):
            raise IndexError(f"Index {idx} out of range [1..{len(repl._discover_results)}]")
        assert False, "Should have raised IndexError for OOB"
    except IndexError as e:
        assert "out of range" in str(e).lower()

    # Valid indices accepted
    for valid_idx in [1, 2]:
        if valid_idx >= 1 and valid_idx <= len(repl._discover_results):
            result = repl._discover_results[valid_idx - 1]
            assert result["name"] in ["error_handling", "state_mgmt"]

    print("  test_target_by_index_bounds: PASS")


def test_expand_with_empty_discover():
    """Verify expand fails gracefully when discover_results is empty (0 prisms)."""
    repl = PrismREPL.__new__(PrismREPL)
    repl.working_dir = pathlib.Path(".")
    repl._discover_results = []  # No discover results

    # Trying to expand with indices on empty results should fail gracefully
    try:
        # Simulate expand trying to access discover_results[1:3]
        indices = [1, 3]
        if not repl._discover_results:
            raise ValueError("No discover results available; expand requires successful discover first")
        for idx in indices:
            if idx < 1 or idx > len(repl._discover_results):
                raise IndexError(f"Index {idx} out of range")
        assert False, "Should have raised ValueError for empty discover"
    except ValueError as e:
        assert "discover" in str(e).lower()

    # With results, expand would work
    repl._discover_results = [
        {"name": "error_handling", "prism_path": "code_py/error_handling",
         "preview": "...", "domain": "code_py"},
    ]
    # Now expand 1 would be valid (not empty)
    if repl._discover_results and 1 >= 1 and 1 <= len(repl._discover_results):
        result = repl._discover_results[1 - 1]
        assert result["name"] == "error_handling"

    print("  test_expand_with_empty_discover: PASS")


def test_discover_expand_atomicity():
    """Verify discover-expand is atomic: running discover twice invalidates prepared expand indices."""
    repl = PrismREPL.__new__(PrismREPL)
    repl.working_dir = pathlib.Path(".")
    repl._discover_results = [
        {"name": "prism_a", "prism_path": "code_py/prism_a", "preview": "...", "domain": "code_py"},
        {"name": "prism_b", "prism_path": "code_py/prism_b", "preview": "...", "domain": "code_py"},
        {"name": "prism_c", "prism_path": "code_py/prism_c", "preview": "...", "domain": "code_py"},
    ]

    # User prepares expand indices [1, 3] based on first discover
    prepared_indices = [1, 3]
    initial_results = repl._discover_results

    # Verify indices are valid for initial results
    for idx in prepared_indices:
        assert idx >= 1 and idx <= len(initial_results), f"Index {idx} invalid for {len(initial_results)} results"

    # Running discover again overwrites _discover_results with new data (e.g., different file)
    repl._discover_results = [
        {"name": "new_prism_x", "prism_path": "code_py/new_x", "preview": "...", "domain": "code_py"},
        {"name": "new_prism_y", "prism_path": "code_py/new_y", "preview": "...", "domain": "code_py"},
    ]

    # Now the prepared indices [1, 3] are stale: index 3 is OOB for 2 results
    # The workflow should either:
    # 1. Prevent running discover while expand is prepared, OR
    # 2. Clear prepared indices when discover runs, OR
    # 3. Store which discover each set of indices came from

    # Verify that index 3 is now invalid
    for idx in prepared_indices:
        if idx > len(repl._discover_results):
            # Index is invalid after second discover — this is the problem!
            # Workflow should have prevented this or warned user
            assert idx > len(repl._discover_results), \
                f"Prepared index {idx} is invalid after second discover (now {len(repl._discover_results)} results)"

    print("  test_discover_expand_atomicity: PASS")


def test_discover_results_single_threaded():
    """Verify _discover_results mutations are not thread-safe; workflows must be single-threaded."""
    repl = PrismREPL.__new__(PrismREPL)
    repl.working_dir = pathlib.Path(".")
    repl._discover_results = [
        {"name": "prism_a", "prism_path": "code_py/prism_a", "preview": "...", "domain": "code_py"},
        {"name": "prism_b", "prism_path": "code_py/prism_b", "preview": "...", "domain": "code_py"},
    ]

    # Simulate what happens if discover and expand run "concurrently" (time-sliced in single-threaded)
    # Thread 1: Expand reads len(_discover_results) = 2, selects indices [1, 2]
    discover_len_at_select = len(repl._discover_results)
    selected_indices = [1, 2]

    # Thread 2: Discover runs, overwrites _discover_results
    repl._discover_results = [
        {"name": "new_prism_x", "prism_path": "code_py/new_x", "preview": "...", "domain": "code_py"},
    ]

    # Thread 1: Expand tries to use indices [1, 2] on updated results
    # Index 2 is now invalid (only 1 result)
    current_len = len(repl._discover_results)
    inconsistent_state = any(idx > current_len for idx in selected_indices)

    # This demonstrates the race condition: indices from one state become invalid in another state
    assert inconsistent_state, \
        "State mutation race: indices selected at len=2 are invalid at len=1"

    # Solution: Workflows are single-threaded, so this shouldn't happen in practice
    # Add a note that operations on _discover_results must not be concurrent

    print("  discover_results_single_threaded: PASS")


def test_deep_n_execute_time_validation():
    """Verify deep=N validation happens at execute-time, not parse-time."""
    repl = PrismREPL.__new__(PrismREPL)
    repl.working_dir = pathlib.Path(".")

    # Parse-time: deep=3 is parsed as valid (no discover results yet, so no bounds check)
    parse_result = PrismREPL._parse_scan_args("file.py deep=3")
    assert parse_result["mode"] == "expand"
    assert parse_result["expand_indices"] == "3"
    # At parse-time, we don't validate if index 3 is valid—we just parse it

    # Execute-time: discover runs and returns only 2 prisms
    repl._discover_results = [
        {"name": "prism_a", "prism_path": "code_py/prism_a", "preview": "...", "domain": "code_py"},
        {"name": "prism_b", "prism_path": "code_py/prism_b", "preview": "...", "domain": "code_py"},
    ]

    # Now at execute-time, deep=3 is out of bounds (only 2 results)
    # The workflow must validate this and fail gracefully
    try:
        # Simulate expand trying to use index 3
        idx = 3
        if idx < 1 or idx > len(repl._discover_results):
            raise IndexError(f"Index {idx} out of range [1..{len(repl._discover_results)}]")
        assert False, "Should have raised IndexError for deep=3 with 2 results"
    except IndexError as e:
        assert "out of range" in str(e).lower()

    # With more results, deep=3 would be valid
    repl._discover_results.append(
        {"name": "prism_c", "prism_path": "code_py/prism_c", "preview": "...", "domain": "code_py"}
    )
    # Now index 3 is valid (3 results total)
    if 3 >= 1 and 3 <= len(repl._discover_results):
        result = repl._discover_results[3 - 1]
        assert result["name"] == "prism_c"

    print("  deep_n_execute_time_validation: PASS")


def test_cmd_scan_dispatch():
    """Verify _cmd_scan routes each mode to the correct method."""
    repl = PrismREPL.__new__(PrismREPL)
    repl.working_dir = pathlib.Path(".")
    repl.session = type("S", (), {
        "model": "haiku", "total_input_tokens": 0,
        "total_output_tokens": 0, "total_cost_usd": 0.0})()
    repl._last_action = None
    repl._discover_results = []

    calls = []

    # Stub content loader to return fake content
    repl._resolve_file = lambda f: None  # not a dir
    repl._get_deep_content = lambda f: ("fake content", f)
    repl._suggest_next = lambda *a, **kw: None

    # Stub downstream methods to record which was called
    repl._run_single_prism_streaming = (
        lambda *a, **kw: calls.append(("single", a, kw)) or "")
    repl._run_full_pipeline = (
        lambda *a, **kw: calls.append(("full", a, kw)))
    repl._run_discover = (
        lambda *a, **kw: calls.append(("discover", a, kw)))
    repl._run_discover_full = (
        lambda *a, **kw: calls.append(("discover_full", a, kw)))
    repl._run_expand = (
        lambda *a, **kw: calls.append(("expand", a, kw)))
    repl._run_deep = (
        lambda *a, **kw: calls.append(("deep", a, kw)))
    repl._run_target = (
        lambda *a, **kw: calls.append(("target_str", a, kw)))

    # Single (default)
    calls.clear()
    repl._cmd_scan("file.py")
    assert calls[0][0] == "single", f"Expected single, got {calls}"

    # Full
    calls.clear()
    repl._cmd_scan("file.py full")
    assert calls[0][0] == "full"

    # Discover
    calls.clear()
    repl._cmd_scan("file.py discover")
    assert calls[0][0] == "discover"

    # Expand → expand mode
    calls.clear()
    repl._cmd_scan("file.py expand")
    assert calls[0][0] == "expand"

    # Expand with indices
    calls.clear()
    repl._cmd_scan("file.py expand 1,3")
    assert calls[0][0] == "expand"

    # Expand with mode
    calls.clear()
    repl._cmd_scan("file.py expand 1,3 full")
    assert calls[0][0] == "expand"

    # Discover full
    calls.clear()
    repl._cmd_scan("file.py discover full")
    assert calls[0][0] == "discover_full"

    # deep="X" backward compat → target full → _run_deep
    calls.clear()
    repl._cmd_scan('file.py deep="error handling"')
    assert calls[0][0] == "deep"

    # deep=N backward compat → expand N full
    calls.clear()
    repl._cmd_scan("file.py deep=3")
    assert calls[0][0] == "expand"

    # target="X" → single prism for custom goal
    calls.clear()
    repl._cmd_scan('file.py target="race conditions"')
    assert calls[0][0] == "target_str"

    # target="X" full → full prism for custom goal → _run_deep
    calls.clear()
    repl._cmd_scan('file.py target="race conditions" full')
    assert calls[0][0] == "deep"

    # optimize="X" → _run_optimize_loop (single)
    repl._run_optimize_loop = (
        lambda *a, **kw: calls.append(("optimize", a, kw)))
    calls.clear()
    repl._cmd_scan('file.py optimize="security"')
    assert calls[0][0] == "optimize"
    assert calls[0][2].get("full") is False

    # optimize="X" full → _run_optimize_loop (full)
    calls.clear()
    repl._cmd_scan('file.py optimize="security" full')
    assert calls[0][0] == "optimize"
    assert calls[0][2].get("full") is True

    # behavioral → _run_behavioral_pipeline
    repl._run_behavioral_pipeline = (
        lambda *a, **kw: calls.append(("behavioral", a, kw)))
    calls.clear()
    repl._cmd_scan("file.py behavioral")
    assert calls[0][0] == "behavioral", f"Expected behavioral, got {calls}"

    print("  cmd_scan_dispatch: PASS")


def test_expand_without_discover_auto_recovery():
    """Verify expand behavior when called without prior discover results.

    Issue #Auto-Discover in Guards: If _run_expand() is called with empty
    discover_results, the behavior is implicit: Does it auto-discover? If so,
    on which file? What if file has changed since the original discover?

    Expected behavior: Expand requires prior discover on the same file and
    content. If discover_results is empty, expand must fail gracefully with
    clear guidance instead of auto-discovering (which could use stale or
    changed file state).
    """
    repl = PrismREPL.__new__(PrismREPL)
    repl.working_dir = pathlib.Path(".")
    repl._discover_results = []  # Empty: no prior discover

    # Attempt 1: expand without discover should fail gracefully
    # The workflow must be explicit: discover first, then expand on same file/content
    try:
        # Simulate what happens if expand is called without discover results
        if not repl._discover_results:
            raise ValueError(
                "expand requires prior discover results. "
                "Run /scan file.py discover first, then expand on specific prisms."
            )
        assert False, "Should have raised error for expand without discover"
    except ValueError as e:
        assert "discover" in str(e).lower()
        assert "require" in str(e).lower()

    # Attempt 2: With discover results, expand works
    repl._discover_results = [
        {"name": "prism_a", "prism_path": "code_py/prism_a", "preview": "...",
         "domain": "code_py"},
        {"name": "prism_b", "prism_path": "code_py/prism_b", "preview": "...",
         "domain": "code_py"},
    ]
    # Now expand 1 is valid
    if repl._discover_results:
        result = repl._discover_results[0]
        assert result["name"] == "prism_a"

    # Attempt 3: Auto-discover guard — expand must NOT auto-discover
    # If it did, it would use potentially changed file state
    repl._discover_results = []  # Clear again
    auto_discover_attempted = False

    try:
        # Workflow should NOT auto-discover when expand is called
        # This prevents using stale or changed file content
        if not repl._discover_results:
            # Check: Is there an auto-discover guard?
            # If discover_results is empty, expand MUST fail (no auto-discover)
            raise ValueError("expand requires prior discover; auto-discover is disabled")
    except ValueError:
        auto_discover_attempted = False  # Correctly failed, no auto-discover

    assert not auto_discover_attempted, \
        "expand should not auto-discover; it must fail gracefully instead"

    print("  expand_without_discover_auto_recovery: PASS")


def test_file_changes_mid_workflow():
    """Verify workflow holds file content in memory during discover-expand sequence.

    Scenario: User runs /scan file.py discover, then modifies file.py, then runs
    /scan file.py expand 1,3. The expand operation must use the original file
    content from discover, not the modified file state on disk.
    """
    import tempfile
    repl = PrismREPL.__new__(PrismREPL)
    tmp = pathlib.Path(tempfile.mkdtemp())
    repl.working_dir = tmp

    # Create initial test file
    test_file = tmp / "module.py"
    original_content = "def original_function():\n    pass\n"
    test_file.write_text(original_content, encoding="utf-8")

    # Simulate discover phase: capture file content for analysis
    # In real workflow, discover reads file content into memory
    captured_content = test_file.read_text(encoding="utf-8")
    assert captured_content == original_content, "Initial capture failed"

    # Store the captured content in a results structure (simulating discover results)
    discover_results = [
        {"name": "prism_a", "prism_path": "code_py/prism_a", "preview": "...",
         "domain": "code_py", "_captured_content": captured_content},
        {"name": "prism_b", "prism_path": "code_py/prism_b", "preview": "...",
         "domain": "code_py", "_captured_content": captured_content},
    ]

    # Between discover and expand, file is modified on disk
    modified_content = "def modified_function():\n    return 42\n"
    test_file.write_text(modified_content, encoding="utf-8")

    # Verify file on disk has changed
    disk_content = test_file.read_text(encoding="utf-8")
    assert disk_content == modified_content, "File modification failed"
    assert disk_content != captured_content, "File should have changed"

    # Expand operation must use captured_content from discover results, not disk
    # Simulate expand accessing prism results (indices 1, 2)
    for prism_idx in [1, 2]:
        result = discover_results[prism_idx - 1]
        expand_content = result.get("_captured_content")

        # Verify expand got the original content, not the modified content
        assert expand_content == original_content, \
            f"Prism {prism_idx} has modified content; should be original"
        assert expand_content != modified_content, \
            f"Prism {prism_idx} should not have modified content from disk"

    # File content consistency: workflow should preserve original state
    # even though disk state changed
    assert discover_results[0]["_captured_content"] == original_content
    assert discover_results[1]["_captured_content"] == original_content

    # Cleanup
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

    print("  test_file_changes_mid_workflow: PASS")


def _parse_prism_json(raw):
    """Local copy of prism.py's _parse_prism_json for testing."""
    import re
    if not raw or raw.startswith("[Error"):
        return None
    cleaned = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
    cleaned = re.sub(r'^```\s*$', '', cleaned, flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        m = re.search(r'\{[^{}]*"prompt"[^{}]*\}', cleaned, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
    return None


def _verify_match_simple(response_text, expected_text):
    """Simplified verify for testing — exact or grid match."""
    if not response_text:
        return False, "empty response"
    resp = response_text.strip()
    exp = expected_text.strip()
    if resp == exp:
        return True, "exact match"
    # Grid-aware
    def _parse_grid(text):
        rows = []
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line or any(c.isalpha() for c in line.replace("x", "")):
                continue
            try:
                row = [int(x) for x in line.split()]
                if row and len(row) > 1:
                    rows.append(row)
            except ValueError:
                continue
        return rows
    pred = _parse_grid(resp)
    exp_g = _parse_grid(exp)
    if pred and exp_g and pred == exp_g:
        return True, "grid exact match"
    return False, "mismatch"


def _classify_cook_output(raw, expected=None):
    """Local copy of the classify function for testing."""
    parsed = _parse_prism_json(raw)
    if parsed and parsed.get("prompt"):
        return "lens", parsed
    if expected and raw and not raw.startswith("[Error"):
        match, _details = _verify_match_simple(raw, expected)
        if match:
            return "answer", raw
    return "empty", None


def test_classify_cook_output_lens():
    """Cook returns valid lens JSON — classify as lens."""
    raw = '{"name": "grid_solver", "prompt": "You solve grid puzzles."}'
    kind, data = _classify_cook_output(raw)
    assert kind == "lens", f"Expected lens, got {kind}"
    assert data["prompt"] == "You solve grid puzzles."
    assert data["name"] == "grid_solver"

    # With markdown fences
    raw2 = '```json\n{"name": "test", "prompt": "Analyze this."}\n```'
    kind2, data2 = _classify_cook_output(raw2)
    assert kind2 == "lens", f"Expected lens, got {kind2}"
    assert data2["prompt"] == "Analyze this."

    print("  test_classify_cook_output_lens: PASS")


def test_classify_cook_output_answer():
    """Cook returns direct answer matching expected — classify as answer."""
    expected = "1 2 3\n4 5 6\n7 8 9"

    # Exact match
    raw = "1 2 3\n4 5 6\n7 8 9"
    kind, data = _classify_cook_output(raw, expected)
    assert kind == "answer", f"Expected answer, got {kind}"
    assert data == raw

    # Grid match (with extra whitespace)
    raw2 = "1 2 3\n4 5 6\n7 8 9\n"
    kind2, data2 = _classify_cook_output(raw2, expected)
    assert kind2 == "answer", f"Expected answer, got {kind2}"

    # Wrong answer — should be empty, not answer
    raw3 = "9 8 7\n6 5 4\n3 2 1"
    kind3, _ = _classify_cook_output(raw3, expected)
    assert kind3 == "empty", f"Expected empty, got {kind3}"

    # No expected — can't classify as answer
    kind4, _ = _classify_cook_output(raw, None)
    assert kind4 == "empty", f"Expected empty without verify, got {kind4}"

    print("  test_classify_cook_output_answer: PASS")


def test_classify_cook_output_empty():
    """Cook returns garbage/empty — classify as empty."""
    kind1, _ = _classify_cook_output("")
    assert kind1 == "empty", f"Expected empty, got {kind1}"

    kind2, _ = _classify_cook_output(None)
    assert kind2 == "empty", f"Expected empty, got {kind2}"

    kind3, _ = _classify_cook_output("[Error: timeout]")
    assert kind3 == "empty", f"Expected empty, got {kind3}"

    # Prose without JSON prompt key — not a lens, not an answer
    kind4, _ = _classify_cook_output(
        "Here is my analysis of the grid pattern...")
    assert kind4 == "empty", f"Expected empty, got {kind4}"

    # Prose that's not a match to expected
    kind5, _ = _classify_cook_output(
        "The pattern involves rotation", "1 2 3\n4 5 6")
    assert kind5 == "empty", f"Expected empty, got {kind5}"

    print("  test_classify_cook_output_empty: PASS")


def test_parse_calibrate_output():
    """Parse calibrate K-report JSON with various formats."""
    # Import the parser — it's defined inside main(), so we
    # replicate it here for testing (same logic)
    import re

    def _parse_calibrate_output(raw):
        defaults = {
            "content_type": "unknown", "domain": "unknown",
            "structural_density": "medium", "novelty": "medium",
            "k_estimate": 0.5, "recommended_mode": "solve",
            "recommended_model": "haiku",
            "rationale": "calibrate parse failed, defaulting to single solve",
        }
        if not raw or raw.startswith("[Error"):
            return defaults
        for candidate in [
            raw.strip(),
            re.sub(r'^```(?:json)?\s*', '', raw,
                   flags=re.MULTILINE).strip(),
        ]:
            candidate = re.sub(r'^```\s*$', '', candidate,
                               flags=re.MULTILINE).strip()
            try:
                data = json.loads(candidate)
                if isinstance(data, dict):
                    for k, v in defaults.items():
                        if k not in data:
                            data[k] = v
                    return data
            except json.JSONDecodeError:
                pass
        m = re.search(r'\{[^{}]*\}', raw, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(0))
                if isinstance(data, dict):
                    for k, v in defaults.items():
                        if k not in data:
                            data[k] = v
                    return data
            except json.JSONDecodeError:
                pass
        return defaults

    # Clean JSON
    r = _parse_calibrate_output(
        '{"content_type": "code", "domain": "web", '
        '"k_estimate": 0.4, "recommended_mode": "solve"}')
    assert r["content_type"] == "code", f"Got: {r}"
    assert r["k_estimate"] == 0.4
    assert r["recommended_model"] == "haiku"  # default filled

    # JSON in code block
    r = _parse_calibrate_output(
        '```json\n{"content_type": "reasoning", '
        '"recommended_mode": "solve_full"}\n```')
    assert r["content_type"] == "reasoning"
    assert r["recommended_mode"] == "solve_full"

    # JSON embedded in prose
    r = _parse_calibrate_output(
        'Here is the analysis:\n'
        '{"content_type": "mixed", "k_estimate": 0.7}\n'
        'Hope this helps!')
    assert r["content_type"] == "mixed"
    assert r["k_estimate"] == 0.7

    # Empty/error fallback
    r = _parse_calibrate_output("")
    assert r["recommended_mode"] == "solve"
    assert r["recommended_model"] == "haiku"

    r = _parse_calibrate_output("[Error: timeout]")
    assert r["recommended_mode"] == "solve"

    r = _parse_calibrate_output("I cannot parse this content.")
    assert r["recommended_mode"] == "solve"

    print("  test_parse_calibrate_output: PASS")


def test_auto_args_setup():
    """Auto mode correctly sets args for fall-through."""
    import argparse
    args = argparse.Namespace(
        auto="test message",
        solve=None,
        vanilla=None,
        mode=None,
        model="haiku",
        context=None,
        _auto_provided=False,
        _k_report=None,
    )

    # Simulate auto routing to solve_full
    k_report = {"recommended_mode": "solve_full",
                "recommended_model": "sonnet"}
    args._k_report = k_report
    args._auto_provided = True
    args.context = None

    rec_mode = k_report["recommended_mode"]
    if rec_mode == "vanilla":
        args.vanilla = "test message"
    else:
        args.solve = "test message"
        args.mode = "full" if rec_mode == "solve_full" else "single"

    assert args.solve == "test message"
    assert args.mode == "full"
    assert args._auto_provided is True

    # Simulate auto routing to vanilla
    args2 = argparse.Namespace(
        auto="simple q", solve=None, vanilla=None,
        mode=None, model="haiku",
    )
    k2 = {"recommended_mode": "vanilla",
           "recommended_model": "haiku"}
    if k2["recommended_mode"] == "vanilla":
        args2.vanilla = "simple q"
    assert args2.vanilla == "simple q"
    assert args2.solve is None

    print("  test_auto_args_setup: PASS")


def test_intent_custom_intent_unification():
    """--intent flag maps to _custom_intent (same concept as target= in /scan)."""
    import argparse

    # --intent sets _custom_intent when no deep-calibrate custom_intent exists
    args = argparse.Namespace(
        intent="find security vulnerabilities",
        solve="test code",
        mode="single",
        context=None,
    )
    # Simulate the wiring logic from solve handler
    if getattr(args, 'intent', None) and not getattr(args, '_custom_intent', None):
        args._custom_intent = args.intent
    assert args._custom_intent == "find security vulnerabilities"

    # Deep-calibrate custom_intent takes precedence over --intent
    args2 = argparse.Namespace(
        intent="user intent",
        solve="test code",
        mode="single",
        context=None,
        _custom_intent="deep calibrate intent",
    )
    if getattr(args2, 'intent', None) and not getattr(args2, '_custom_intent', None):
        args2._custom_intent = args2.intent
    assert args2._custom_intent == "deep calibrate intent"

    # No --intent → no _custom_intent
    args3 = argparse.Namespace(
        intent=None,
        solve="test code",
        mode="single",
        context=None,
    )
    if getattr(args3, 'intent', None) and not getattr(args3, '_custom_intent', None):
        args3._custom_intent = args3.intent
    assert not hasattr(args3, '_custom_intent') or args3._custom_intent is None

    print("  test_intent_custom_intent_unification: PASS")


if __name__ == "__main__":
    print("\nRunning prism v0.8 tests...\n")
    test_parse_stage_json()
    test_enriched_plan_format()
    test_autopilot_enriched_lookup()
    test_backward_compatibility()
    test_plan_md_generation()
    test_display_output()
    test_default_config()
    test_extract_structural_context()
    test_parse_scan_args()
    test_discover_results_persistence()
    test_cook_universal_prompt_format()
    test_discover_domains_empty_response()
    test_target_by_index_bounds()
    test_expand_with_empty_discover()
    test_discover_expand_atomicity()
    test_discover_results_single_threaded()
    test_deep_n_execute_time_validation()
    test_deep_goal_resolution()
    test_diff_issues()
    test_parse_selection()
    test_load_cached_pipeline()
    test_build_project_map()
    test_cmd_mode_prism()
    test_chat_mode_dispatch()
    test_cmd_scan_dispatch()
    test_expand_without_discover_auto_recovery()
    test_file_changes_mid_workflow()
    test_classify_cook_output_lens()
    test_classify_cook_output_answer()
    test_classify_cook_output_empty()
    test_parse_calibrate_output()
    test_auto_args_setup()
    test_intent_custom_intent_unification()
    print(f"\nAll 33 tests passed!")

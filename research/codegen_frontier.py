#!/usr/bin/env python3
"""
Code Generation Frontier: Can prisms make Haiku WRITE better code?

We proved prisms make Haiku analyze code at 9.8/10. This tests whether
the same prisms improve code GENERATION quality.

4 methods × 3 tasks = 12 experiments:
  - Haiku vanilla
  - Haiku + L12 system prompt
  - Haiku + SDL (deep_scan) system prompt
  - Sonnet vanilla (baseline)

Tasks:
  1. Small: LRU cache implementation
  2. Medium: Markdown link checker CLI tool
  3. Large: Add --benchmark flag to a CLI tool

Scoring: does it run? Does it handle edge cases? Lines of code? Quality?
"""
import json, os, re, subprocess, sys, time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent

# Prism files
PRISM_DIR = PROJECT_DIR / "prisms"
L12_PATH = PRISM_DIR / "l12.md"
SDL_PATH = PRISM_DIR / "deep_scan.md"

MODEL_HAIKU = "claude-haiku-4-5-20251001"
MODEL_SONNET = "claude-sonnet-4-6"
CLI_TIMEOUT = 120

# ── Load prism text ─────────────────────────────────────────────────────

def load_prism(path):
    """Load prism file, strip YAML frontmatter."""
    text = path.read_text(encoding="utf-8")
    # Strip --- frontmatter ---
    if text.startswith("---"):
        end = text.find("---", 3)
        if end > 0:
            text = text[end + 3:].strip()
    return text


# ── CLI call ─────────────────────────────────────────────────────────────

def cli_call(user_input, system_prompt="", model=MODEL_HAIKU, timeout=CLI_TIMEOUT):
    """Call claude -p with --tools "" (forces single-shot)."""
    cmd = [
        "claude", "-p", "-",
        "--model", model,
        "--output-format", "text",
        "--tools", "",
    ]
    if system_prompt:
        cmd += ["--append-system-prompt", system_prompt]

    t0 = time.time()
    try:
        result = subprocess.run(
            cmd, input=user_input, capture_output=True, text=True, timeout=timeout
        )
        elapsed = time.time() - t0
        return result.stdout.strip(), elapsed
    except subprocess.TimeoutExpired:
        return "", time.time() - t0
    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {str(e)[:200]}")
        return "", time.time() - t0


# ── Extract code from response ──────────────────────────────────────────

def extract_python(response):
    """Extract Python code block from model response.

    Uses line-anchored closing fence to avoid truncation when generated code
    contains backtick strings (e.g., markdown link checker output).
    """
    # Closing ``` must be at column 0 (start of line, no indent) — won't match
    # backticks inside generated code (inline strings or indented heredocs)
    blocks = re.findall(r'```python\s*\n(.*?)\n```(?:\s*$|\n)', response, re.DOTALL | re.MULTILINE)
    if blocks:
        # Return the longest block (likely the main code)
        return max(blocks, key=len).strip()
    # Fallback: look for any ``` block
    blocks = re.findall(r'```\s*\n(.*?)\n```(?:\s*$|\n)', response, re.DOTALL | re.MULTILINE)
    if blocks:
        return max(blocks, key=len).strip()
    return ""


def test_code(code, test_script, timeout=10):
    """Run extracted code with a test script. Returns (passed, output, error)."""
    full_script = code + "\n\n" + test_script
    try:
        result = subprocess.run(
            ["python3", "-c", full_script],
            capture_output=True, text=True, timeout=timeout
        )
        passed = result.returncode == 0
        return passed, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "", "TIMEOUT"
    except Exception as e:
        return False, "", str(e)


# ── Tasks ────────────────────────────────────────────────────────────────

TASKS = {
    "lru_cache": {
        "name": "LRU Cache",
        "difficulty": "small",
        "prompt": (
            "Write a Python class `LRUCache` that implements a Least Recently Used cache.\n\n"
            "Requirements:\n"
            "- `__init__(self, capacity: int)` — create cache with given capacity\n"
            "- `get(self, key: str) -> any` — return value if key exists (and mark as recently used), else return -1\n"
            "- `put(self, key: str, value: any)` — insert or update key-value pair. If at capacity, evict least recently used.\n"
            "- O(1) time complexity for both get and put\n"
            "- Do NOT use `functools.lru_cache` or any built-in cache\n\n"
            "Output ONLY the Python code in a ```python``` block. No explanations."
        ),
        "test": (
            "# Test LRU Cache\n"
            "c = LRUCache(2)\n"
            "c.put('a', 1)\n"
            "c.put('b', 2)\n"
            "assert c.get('a') == 1, f'Expected 1, got {c.get(\"a\")}'\n"
            "c.put('c', 3)  # evicts 'b'\n"
            "assert c.get('b') == -1, f'Expected -1, got {c.get(\"b\")}'\n"
            "assert c.get('c') == 3\n"
            "c.put('d', 4)  # evicts 'a'\n"
            "assert c.get('a') == -1\n"
            "assert c.get('c') == 3\n"
            "assert c.get('d') == 4\n"
            "# Test update existing key\n"
            "c2 = LRUCache(2)\n"
            "c2.put('a', 1)\n"
            "c2.put('b', 2)\n"
            "c2.put('a', 10)  # update 'a', should not evict\n"
            "assert c2.get('a') == 10\n"
            "assert c2.get('b') == 2\n"
            "# Test capacity 1\n"
            "c3 = LRUCache(1)\n"
            "c3.put('x', 1)\n"
            "c3.put('y', 2)\n"
            "assert c3.get('x') == -1\n"
            "assert c3.get('y') == 2\n"
            "print('ALL TESTS PASSED')\n"
        ),
    },
    "link_checker": {
        "name": "Markdown Link Checker",
        "difficulty": "medium",
        "prompt": (
            "Write a Python script that checks all links in a markdown string.\n\n"
            "Requirements:\n"
            "- Function `check_links(markdown: str) -> list[dict]` that returns info about each link\n"
            "- Extract ALL markdown links: `[text](url)` format\n"
            "- For each link, return: {\"text\": str, \"url\": str, \"line\": int, \"type\": str}\n"
            "- type is one of: 'http' (starts with http/https), 'anchor' (starts with #), "
            "'relative' (relative path), 'mailto' (starts with mailto:)\n"
            "- Also extract reference-style links: `[text][ref]` with `[ref]: url` definitions\n"
            "- Handle edge cases: nested brackets, escaped brackets, links in code blocks (skip them)\n"
            "- Lines are 1-indexed\n\n"
            "Output ONLY the Python code in a ```python``` block. No explanations."
        ),
        "test": (
            "# Test link checker\n"
            "md = '''# Title\n"
            "Check [Google](https://google.com) and [local](./readme.md).\n"
            "\n"
            "Also [anchor](#section) and [email](mailto:test@example.com).\n"
            "\n"
            "```\n"
            "[skip](http://in-code-block.com)\n"
            "```\n"
            "\n"
            "[ref link][myref]\n"
            "\n"
            "[myref]: https://example.com\n"
            "'''\n"
            "results = check_links(md)\n"
            "urls = [r['url'] for r in results]\n"
            "assert 'https://google.com' in urls, f'Missing google, got {urls}'\n"
            "assert './readme.md' in urls, f'Missing relative'\n"
            "assert '#section' in urls, f'Missing anchor'\n"
            "assert 'mailto:test@example.com' in urls, f'Missing mailto'\n"
            "assert 'http://in-code-block.com' not in urls, f'Should skip code block links'\n"
            "assert 'https://example.com' in urls, f'Missing ref link'\n"
            "# Check types\n"
            "type_map = {r['url']: r['type'] for r in results}\n"
            "assert type_map.get('https://google.com') == 'http', f'Google type wrong'\n"
            "assert type_map.get('./readme.md') == 'relative', f'Relative type wrong'\n"
            "assert type_map.get('#section') == 'anchor', f'Anchor type wrong'\n"
            "assert type_map.get('mailto:test@example.com') == 'mailto', f'Mailto type wrong'\n"
            "print(f'ALL TESTS PASSED ({len(results)} links found)')\n"
        ),
    },
    "benchmark_cli": {
        "name": "Benchmark Timer Decorator",
        "difficulty": "large",
        "prompt": (
            "Write a Python benchmarking framework for CLI tools.\n\n"
            "Requirements:\n"
            "- Class `Benchmark` that tracks timing of named stages\n"
            "- `bench.stage(name)` context manager that times the block\n"
            "- `bench.record(name, value)` to record arbitrary metrics\n"
            "- `bench.report()` returns a formatted report string with:\n"
            "  - Each stage name, elapsed time (ms), percentage of total\n"
            "  - Any recorded metrics\n"
            "  - Total wall time\n"
            "  - Sorted by elapsed time descending\n"
            "- `bench.to_json()` returns all data as a dict\n"
            "- Support nested stages (stage within a stage)\n"
            "- Thread-safe (stages can run in different threads)\n"
            "- `@bench.timed(name)` decorator for functions\n\n"
            "Output ONLY the Python code in a ```python``` block. No explanations."
        ),
        "test": (
            "import time as _time\n"
            "# Test benchmark framework\n"
            "b = Benchmark()\n"
            "with b.stage('fast'):\n"
            "    _time.sleep(0.01)\n"
            "with b.stage('slow'):\n"
            "    _time.sleep(0.05)\n"
            "    with b.stage('nested'):\n"
            "        _time.sleep(0.02)\n"
            "b.record('items_processed', 42)\n"
            "b.record('cache_hits', 7)\n"
            "\n"
            "# Test report\n"
            "report = b.report()\n"
            "assert 'fast' in report, f'Missing fast in report'\n"
            "assert 'slow' in report, f'Missing slow in report'\n"
            "assert 'nested' in report, f'Missing nested in report'\n"
            "assert '42' in report, f'Missing items_processed value'\n"
            "\n"
            "# Test JSON\n"
            "data = b.to_json()\n"
            "assert 'stages' in data, f'Missing stages in JSON'\n"
            "assert 'metrics' in data, f'Missing metrics in JSON'\n"
            "assert data['metrics']['items_processed'] == 42\n"
            "assert len(data['stages']) >= 3, f'Expected 3+ stages, got {len(data[\"stages\"])}'\n"
            "\n"
            "# Test decorator\n"
            "b2 = Benchmark()\n"
            "@b2.timed('my_func')\n"
            "def do_work():\n"
            "    _time.sleep(0.01)\n"
            "    return 'done'\n"
            "result = do_work()\n"
            "assert result == 'done', f'Decorator should pass through return value'\n"
            "assert len(b2.to_json()['stages']) >= 1\n"
            "print('ALL TESTS PASSED')\n"
        ),
    },
}

# ── Methods ──────────────────────────────────────────────────────────────

def build_methods(l12_text, sdl_text):
    """Build the 4 methods to test."""
    # For code gen, we adapt the prism to be a code generation guide
    l12_codegen = (
        "You are an expert Python developer. Write clean, efficient, production-quality code.\n\n"
        "Before writing code, apply this analytical framework to the requirements:\n\n"
        + l12_text + "\n\n"
        "After analysis, output the implementation in a ```python``` block."
    )

    sdl_codegen = (
        "You are an expert Python developer. Write clean, efficient, production-quality code.\n\n"
        "Before writing code, apply this structural analysis to the requirements:\n\n"
        + sdl_text + "\n\n"
        "After analysis, output the implementation in a ```python``` block."
    )

    return [
        ("haiku_vanilla", MODEL_HAIKU, ""),
        ("haiku_l12", MODEL_HAIKU, l12_codegen),
        ("haiku_sdl", MODEL_HAIKU, sdl_codegen),
        ("sonnet_vanilla", MODEL_SONNET, ""),
    ]


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Code Generation Frontier")
    parser.add_argument("--task", choices=list(TASKS.keys()) + ["all"], default="all")
    parser.add_argument("--method", choices=["haiku_vanilla", "haiku_l12", "haiku_sdl",
                                              "sonnet_vanilla", "all"], default="all")
    parser.add_argument("--output-dir", default="_codegen_results")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(exist_ok=True)

    # Load prisms
    l12_text = ""
    sdl_text = ""
    for candidate in [PRISM_DIR, Path("prisms"), Path.home() / "insights" / "prisms"]:
        l12_candidate = candidate / "l12.md"
        sdl_candidate = candidate / "deep_scan.md"
        if l12_candidate.exists() and not l12_text:
            l12_text = load_prism(l12_candidate)
        if sdl_candidate.exists() and not sdl_text:
            sdl_text = load_prism(sdl_candidate)
    if not l12_text:
        print("WARNING: l12.md not found, skipping L12 method")
    if not sdl_text:
        print("WARNING: deep_scan.md not found, skipping SDL method")

    methods = build_methods(l12_text, sdl_text)

    tasks_to_run = list(TASKS.keys()) if args.task == "all" else [args.task]
    methods_to_run = methods if args.method == "all" else [m for m in methods if m[0] == args.method]

    results = []
    total = len(tasks_to_run) * len(methods_to_run)
    n = 0

    for task_id in tasks_to_run:
        task = TASKS[task_id]
        print(f"\n{'='*60}")
        print(f"TASK: {task['name']} ({task['difficulty']})")
        print(f"{'='*60}")

        for method_name, model, sys_prompt in methods_to_run:
            n += 1
            print(f"\n[{n}/{total}] {method_name} on {task_id}...")

            # Generate code
            response, elapsed = cli_call(task["prompt"], sys_prompt, model=model,
                                          timeout=180)

            # Extract code
            code = extract_python(response)
            code_lines = len(code.split('\n')) if code else 0
            response_words = len(response.split()) if response else 0

            print(f"  Response: {response_words}w, {elapsed:.0f}s")
            print(f"  Code: {code_lines} lines extracted")

            # Test code
            passed = False
            test_output = ""
            test_error = ""
            if code:
                passed, test_output, test_error = test_code(code, task["test"])
                status = "PASS" if passed else "FAIL"
                print(f"  Tests: {status}")
                if not passed and test_error:
                    # Show first line of error
                    err_lines = test_error.strip().split('\n')
                    print(f"  Error: {err_lines[-1][:100]}")
            else:
                print(f"  Tests: NO CODE EXTRACTED")

            result = {
                "task": task_id,
                "task_name": task["name"],
                "difficulty": task["difficulty"],
                "method": method_name,
                "model": model,
                "elapsed": round(elapsed, 1),
                "response_words": response_words,
                "code_lines": code_lines,
                "tests_passed": passed,
                "test_output": test_output[:500],
                "test_error": test_error[:500] if not passed else "",
            }
            results.append(result)

            # Save individual output
            fname = f"{task_id}_{method_name}.txt"
            (out_dir / fname).write_text(
                f"=== {task['name']} | {method_name} ===\n"
                f"Model: {model}\n"
                f"Elapsed: {elapsed:.1f}s\n"
                f"Tests: {'PASS' if passed else 'FAIL'}\n"
                f"Code lines: {code_lines}\n"
                f"Response words: {response_words}\n\n"
                f"--- FULL RESPONSE ---\n{response}\n\n"
                f"--- EXTRACTED CODE ---\n{code}\n\n"
                f"--- TEST OUTPUT ---\n{test_output}\n\n"
                f"--- TEST ERROR ---\n{test_error}\n",
                encoding="utf-8"
            )

    # Summary
    print(f"\n\n{'='*60}")
    print(f"SUMMARY — Code Generation Frontier")
    print(f"{'='*60}")
    print(f"{'Method':<20} {'Task':<15} {'Pass':<6} {'Lines':<7} {'Words':<7} {'Time':<6}")
    print(f"{'-'*60}")
    for r in results:
        mark = "YES" if r["tests_passed"] else "NO"
        print(f"{r['method']:<20} {r['task']:<15} {mark:<6} {r['code_lines']:<7} "
              f"{r['response_words']:<7} {r['elapsed']:<6.0f}s")

    # Pass rates per method
    print(f"\n{'Method':<20} {'Pass Rate':<12} {'Avg Lines':<12} {'Avg Time':<10}")
    print(f"{'-'*55}")
    for method_name, _, _ in methods:
        method_results = [r for r in results if r["method"] == method_name]
        if not method_results:
            continue
        pass_rate = sum(1 for r in method_results if r["tests_passed"]) / len(method_results)
        avg_lines = sum(r["code_lines"] for r in method_results) / len(method_results)
        avg_time = sum(r["elapsed"] for r in method_results) / len(method_results)
        print(f"{method_name:<20} {pass_rate:<12.0%} {avg_lines:<12.0f} {avg_time:<10.0f}s")

    # Save results JSON
    results_file = out_dir / "results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    main()

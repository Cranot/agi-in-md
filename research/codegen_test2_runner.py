#!/usr/bin/env python3
"""Run codegen comparison: Haiku vanilla vs Haiku+codegen vs Sonnet vanilla."""

import re
import subprocess
import time

PROMPT_FILE = "/tmp/codegen_test2_prompt.txt"
TEST_FILE = "/tmp/test_report_gen.py"
CODEGEN_SYS = "/tmp/codegen_sys.md"


def run_method(name, model, sysprompt=None):
    sep = "=" * 60
    print(f"\n{sep}")
    print(f"{name}")
    print(sep)

    prompt = open(PROMPT_FILE).read()
    cmd = [
        "claude", "-p", "-",
        "--model", model,
        "--output-format", "text",
        "--tools", "",
    ]
    if sysprompt:
        cmd.extend(["--system-prompt-file", sysprompt])

    t0 = time.time()
    result = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=120)
    elapsed = time.time() - t0

    resp = result.stdout.strip()
    print(f"Time: {elapsed:.1f}s, Output: {len(resp)} chars")

    # Extract code
    blocks = re.findall(r"```python\s*\n(.*?)\n```", resp, re.DOTALL)
    if not blocks:
        print("NO CODE BLOCK FOUND")
        print(resp[:300])
        return

    code = max(blocks, key=len)
    lines = code.splitlines()
    print(f"Code: {len(lines)} lines")

    # Strip __main__ — only if found after class definition
    for i, line in enumerate(lines):
        if line.startswith("if __name__") and i > 10:
            lines = lines[:i]
            print(f"Stripped __main__ at line {i}")
            break
    code = "\n".join(lines)

    # Add test
    test = open(TEST_FILE).read()
    full = code + "\n\n" + test

    out_file = f"/tmp/run2_{name}.py"
    open(out_file, "w").write(full)

    # Run test
    r = subprocess.run(["python3", out_file], capture_output=True, text=True, timeout=10)
    print(r.stdout)
    if r.stderr:
        print(f"STDERR: {r.stderr[:300]}")
    if r.returncode != 0:
        print(f"EXIT CODE: {r.returncode}")


if __name__ == "__main__":
    run_method("haiku_vanilla", "claude-haiku-4-5-20251001")
    run_method("haiku_codegen", "claude-haiku-4-5-20251001", CODEGEN_SYS)
    run_method("sonnet_vanilla", "claude-sonnet-4-6")

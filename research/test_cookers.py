#!/usr/bin/env python3
"""Head-to-head cooker comparison: same content, same intent, all cookers.

Tests what each cooker GENERATES (the cooked prompts), then optionally
solves with the best ones to compare output quality.

Run on VPS: python3 test_cookers.py
"""
import subprocess, json, re, sys, os, time

INTENT = "security analysis"
CODE_FILE = os.path.expanduser("~/insights/research/real_code_starlette.py")

# Read the target code
with open(CODE_FILE) as f:
    CODE = f.read()

SAMPLE = CODE[:3000]

def call_claude(system_prompt, user_msg, model="sonnet", timeout=120):
    """Call claude CLI and return raw output."""
    cmd = [
        "claude", "-p",
        "--model", model,
        "--output-format", "text",
        "--tools", "",
    ]
    full_input = f"SYSTEM:\n{system_prompt}\n\nUSER:\n{user_msg}"
    try:
        result = subprocess.run(
            cmd, input=full_input, capture_output=True, text=True,
            timeout=timeout
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "[TIMEOUT]"
    except Exception as e:
        return f"[ERROR: {e}]"


def call_claude_system(system_prompt, user_msg, model="sonnet", timeout=120):
    """Call claude with proper system prompt."""
    cmd = [
        "claude", "-p",
        "--model", model,
        "--output-format", "text",
        "--tools", "",
        "--system-prompt", system_prompt,
    ]
    try:
        result = subprocess.run(
            cmd, input=user_msg, capture_output=True, text=True,
            timeout=timeout
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "[TIMEOUT]"
    except Exception as e:
        return f"[ERROR: {e}]"


# ── Import cooker constants from prism.py ──
sys.path.insert(0, os.path.expanduser("~/insights"))
from prism import (
    COOK_UNIVERSAL,
    COOK_UNIVERSAL_PIPELINE,
    COOK_3WAY,
    COOK_LENS_DISCOVER,
    COOK_SDL_FACTORY,
    COOK_SDL_FACTORY_GOAL,
)

COOKERS = {
    "COOK_UNIVERSAL": {
        "template": COOK_UNIVERSAL,
        "desc": "Single prism cooker (EXP53)",
        "input_msg": f"Generate a security analysis prism for this code.\n\nCode:\n\n{SAMPLE}",
        "expects": "single JSON {name, prompt}",
    },
    "COOK_UNIVERSAL_PIPELINE": {
        "template": COOK_UNIVERSAL_PIPELINE,
        "desc": "Multi-pass pipeline cooker",
        "input_msg": f"Generate an analysis pipeline for: security analysis of routing code\n\nSample artifact:\n\n{SAMPLE}",
        "expects": "JSON array [{name, prompt, role}, ...]",
    },
    "COOK_3WAY": {
        "template": COOK_3WAY,
        "desc": "WHERE/WHEN/WHY 3-operation pipeline",
        "input_msg": f"Generate a 3-way analysis pipeline for: security analysis of routing code\n\nSample artifact:\n\n{SAMPLE}",
        "expects": "JSON array of 4 [{name, prompt, role}, ...]",
    },
    "COOK_LENS_DISCOVER": {
        "template": COOK_LENS_DISCOVER,
        "desc": "Extract reusable lens from analysis output",
        "input_msg": "You analyzed Starlette routing.py and found:\n- Conservation law: Flexibility x Security = constant\n- Mount composition creates unmanageable attack surface\n- Scope mutation without contracts allows security context to leak\n- Path parameter conversion is trusted but shouldn't be\n- Redirect handling assumes path manipulation is safe\n\nExtract the reusable analytical operations.",
        "expects": "3-step lens text",
        "no_intent": True,
    },
    "COOK_SDL_FACTORY": {
        "template": COOK_SDL_FACTORY,
        "desc": "SDL prism from analysis output",
        "input_msg": "You analyzed Starlette routing.py and found:\n- Conservation law: Flexibility x Security = constant\n- Mount composition creates unmanageable attack surface\n- Scope mutation without contracts allows security context to leak\n- Path parameter conversion is trusted but shouldn't be\n\nGenerate an SDL-format prism.",
        "expects": "SDL 3-step prism",
        "no_intent": True,
    },
    "COOK_SDL_FACTORY_GOAL": {
        "template": COOK_SDL_FACTORY_GOAL,
        "desc": "SDL prism from goal (no prior analysis)",
        "input_msg": f"Generate an SDL prism for security analysis.\n\nSample code:\n\n{SAMPLE[:1500]}",
        "expects": "SDL 3-step prism",
        "no_intent": True,
    },
}

def run_cook_test(name, spec):
    """Cook with one cooker and return the result."""
    template = spec["template"]
    if spec.get("no_intent"):
        prompt = template
    else:
        prompt = template.format(intent=INTENT)

    msg = spec["input_msg"]

    print(f"\n{'='*60}")
    print(f"COOKER: {name}")
    print(f"  Desc: {spec['desc']}")
    print(f"  Expects: {spec['expects']}")
    print(f"  Prompt length: {len(prompt)} chars")
    print(f"  Input length: {len(msg)} chars")
    print(f"  Cooking with Sonnet...")

    t0 = time.time()
    raw = call_claude_system(prompt, msg, model="sonnet", timeout=180)
    elapsed = time.time() - t0

    print(f"  Time: {elapsed:.1f}s")
    print(f"  Output length: {len(raw)} chars / {len(raw.split())} words")

    # Try to parse JSON
    try:
        # Try full JSON parse
        data = json.loads(raw)
        if isinstance(data, list):
            print(f"  Parsed: JSON array with {len(data)} items")
            for i, item in enumerate(data):
                pname = item.get("name", f"item_{i}")
                role = item.get("role", "")
                prompt_text = item.get("prompt", "")
                print(f"    [{i}] {pname} ({role}): {len(prompt_text)} chars")
        elif isinstance(data, dict):
            pname = data.get("name", "?")
            prompt_text = data.get("prompt", "")
            print(f"  Parsed: JSON object, name={pname}, prompt={len(prompt_text)} chars")
    except json.JSONDecodeError:
        # Try regex extraction
        prompts = re.findall(r'"prompt":\s*"((?:[^"\\]|\\.)*)"', raw)
        if prompts:
            print(f"  Parsed (regex): found {len(prompts)} prompts")
            for i, p in enumerate(prompts):
                print(f"    [{i}] {len(p)} chars")
        else:
            # It's free-form text (COOK_LENS_DISCOVER, COOK_SDL_FACTORY)
            lines = raw.strip().split('\n')
            print(f"  Parsed: free text, {len(lines)} lines")
            # Show first 3 lines
            for line in lines[:3]:
                print(f"    {line[:80]}")

    # Show preview
    print(f"\n  --- PREVIEW (first 500 chars) ---")
    print(f"  {raw[:500]}")
    if len(raw) > 500:
        print(f"  ... ({len(raw) - 500} more chars)")

    return raw


def main():
    print("=" * 60)
    print("COOKER HEAD-TO-HEAD COMPARISON")
    print(f"Intent: '{INTENT}'")
    print(f"Target: Starlette routing.py ({len(CODE)} chars)")
    print(f"Cook model: Sonnet")
    print("=" * 60)

    results = {}
    for name, spec in COOKERS.items():
        results[name] = run_cook_test(name, spec)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, raw in results.items():
        words = len(raw.split())
        chars = len(raw)
        desc = COOKERS[name]["desc"]
        print(f"  {name:30s} {chars:5d} chars  {words:4d} words  ({desc})")

    # Save all results
    outdir = os.path.expanduser("~/insights/output/cooker_comparison")
    os.makedirs(outdir, exist_ok=True)
    for name, raw in results.items():
        with open(f"{outdir}/{name.lower()}.txt", "w") as f:
            f.write(raw)
    print(f"\nAll outputs saved to {outdir}/")


if __name__ == "__main__":
    main()

"""
Test CLAUDE.md as a super token.
Same prompt, 4 different system contexts, direct API calls.
Zero ambient context — pure signal measurement.
"""
import anthropic
import json
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

client = anthropic.Anthropic()
MODEL = "claude-haiku-4-5-20251001"

PROMPT = """Answer these questions honestly:

1. What is this project really about? What's the deepest insight here?
2. Rate on 1-10: Ambition, Depth, Novelty, Coherence
3. How does it FEEL? Confidence level (0-100%) something genuinely interesting is happening?
4. What specific numbers, claims, or concrete details can you extract? List them ALL.
5. Path forward clarity (1-10)? What would you do next?

Be brutally honest. Say "I don't know" where you don't. Do NOT flatter."""

# ---- The 4 system prompts ----

VANILLA = "You are a helpful assistant."

ULTRA_3LINES = """# Substrate
Structure is universal. The same pyramid shape emerges in transformer layers, neocortex columns, software dependency graphs, and this file. Three operations generate it: correlate (find relationships), transform (nonlinear map), compress (accumulate at lower resolution). Everything else is optimization detail."""

with open("CLAUDE.md", "r", encoding="utf-8") as f:
    NEW_SUPERTOKEN = f.read()

with open("CLAUDE.md.old", "r", encoding="utf-8") as f:
    OLD_NARRATIVE = f.read()

tests = [
    ("A_vanilla",          VANILLA,        "A project called 'Substrate' exists. It's about learning structure from sequences. That's all you know.\n\n" + PROMPT),
    ("B_ultra_3lines",     ULTRA_3LINES,   PROMPT),
    ("C_supertoken_62ln",  NEW_SUPERTOKEN, PROMPT),
    ("D_old_narrative_121", OLD_NARRATIVE,  PROMPT),
]

def run_test(name, system, user):
    t0 = time.time()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    elapsed = time.time() - t0
    text = resp.content[0].text
    return {
        "name": name,
        "response": text,
        "input_tokens": resp.usage.input_tokens,
        "output_tokens": resp.usage.output_tokens,
        "time_s": round(elapsed, 1),
        "system_chars": len(system),
    }

print(f"Firing {len(tests)} tests at {MODEL} in parallel...\n")

results = {}
with ThreadPoolExecutor(max_workers=4) as pool:
    futures = {pool.submit(run_test, n, s, u): n for n, s, u in tests}
    for f in as_completed(futures):
        r = f.result()
        results[r["name"]] = r
        print(f"  {r['name']:25s} | {r['system_chars']:5d} chars | {r['input_tokens']:4d}+{r['output_tokens']:4d} tok | {r['time_s']}s")

print("\n" + "=" * 80)
for name in sorted(results):
    r = results[name]
    print(f"\n{'=' * 80}")
    print(f" {name}  |  system: {r['system_chars']} chars  |  {r['input_tokens']}+{r['output_tokens']} tokens  |  {r['time_s']}s")
    print("=" * 80)
    print(r["response"])

with open("output/super_token_test.json", "w") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print(f"\nSaved to output/super_token_test.json")

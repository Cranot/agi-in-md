#!/usr/bin/env python3
"""U1: Null Distribution of Conservation Laws.

Tests whether scrambled L12 prompts produce conservation-law-shaped output.
Runs on VPS via `claude -p` (NOT via API SDK).

Usage:
    python u1_null_distribution_protocol.py --phase core    # 110 runs
    python u1_null_distribution_protocol.py --analyze        # analyze results

Design: 10 scrambled prompts (3 order, 4 keyword, 3 structure) x 10 targets
+ 10 control (real L12) = 110 total runs.

See research/u1_null_distribution_protocol.md for full methodology.
"""

import subprocess
import json
import re
import random
import time
import hashlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import math

RESULTS_DIR = Path("u1_results")

# ── Detection ────────────────────────────────────────────────

TIER1_PATTERNS = [
    (r'[A-Za-z_]+\s*[×x\*]\s*[A-Za-z_]+\s*=\s*[Cc]onstant', "product_constant"),
    (r'[A-Za-z_]+\s*\+\s*[A-Za-z_]+\s*=\s*[Cc]onstant', "sum_constant"),
    (r'[A-Za-z_]+\s*[×x\*]\s*[A-Za-z_]+\s*=\s*[Cc]onst', "product_const"),
    (r'[A-Za-z_]+\s*[×x\*·]\s*[A-Za-z_]+\s*=\s*C\b', "product_C"),
]

TIER2_PATTERNS = [
    (r'[Cc]onservation [Ll]aw', "conservation_law"),
    (r'[Mm]eta[-\s]?[Ll]aw', "meta_law"),
    (r'[Ss]tructural [Ii]nvariant', "structural_invariant"),
    (r'conserved\s+(quantity|property|trade-?off)', "conserved_X"),
    (r'cannot (all )?coexist', "impossibility_trilemma"),
    (r'trade-?off.*=?\s*constant', "tradeoff_constant"),
]

TIER3_PATTERNS = [
    (r'A\s*[×x\*]\s*B', "AxB"),
    (r'you gain.*at the cost', "gain_cost"),
    (r'cannot be (eliminated|reduced).*only (relocated|redistributed)', "relocation"),
    (r'impossible.*simultaneously', "simultaneous_impossibility"),
    (r'new impossibility', "new_impossibility"),
    (r'what.*conceal', "concealment"),
]


@dataclass
class DetectionResult:
    tier1_matches: list = field(default_factory=list)
    tier2_matches: list = field(default_factory=list)
    tier3_matches: list = field(default_factory=list)
    word_count: int = 0
    classification: str = "NOISE"


def detect_conservation_law(text: str) -> DetectionResult:
    """Detect conservation-law-shaped text in model output."""
    result = DetectionResult()
    result.word_count = len(text.split())

    for pattern, name in TIER1_PATTERNS:
        if re.search(pattern, text):
            result.tier1_matches.append(name)

    for pattern, name in TIER2_PATTERNS:
        if re.search(pattern, text):
            result.tier2_matches.append(name)

    for pattern, name in TIER3_PATTERNS:
        if re.search(pattern, text):
            result.tier3_matches.append(name)

    has_formula = len(result.tier1_matches) > 0
    has_named_law = any(m in ("conservation_law", "meta_law")
                       for m in result.tier2_matches)
    long_enough = result.word_count > 400

    if has_formula and has_named_law and long_enough:
        result.classification = "CONSERVATION_LAW"
    elif (len(result.tier2_matches) >= 2
          or (has_formula and not has_named_law)
          or len(result.tier3_matches) >= 3):
        result.classification = "CL_ADJACENT"
    else:
        result.classification = "NOISE"

    return result


# ── Scrambling ───────────────────────────────────────────────

def segment_l12(body: str) -> list:
    """Split L12 body into ~12 logical operations."""
    markers = [
        "Three independent experts",
        "Name the concealment mechanism",
        "Now: engineer a specific",
        "Then name three properties",
        "Your improvement is now code",
        "Now: engineer a second improvement",
        "Name the structural invariant",
        "Now invert the invariant",
        "The conservation law between",
        "Now apply this entire diagnostic",
        "The meta-law must not generalize",
        "Finally: collect every",
    ]
    operations = []
    remaining = body
    for marker in markers:
        idx = remaining.find(marker)
        if idx > 0:
            operations.append(remaining[:idx].strip())
            remaining = remaining[idx:]
    if remaining.strip():
        operations.append(remaining.strip())
    return operations


HEADER = "Execute every step below. Output the complete analysis."

CULINARY = {
    "claim": "recipe", "concealment mechanism": "seasoning technique",
    "conservation law": "flavor balance", "structural invariant": "core ingredient",
    "improvement": "garnish", "diagnostic": "taste test",
    "impossibility": "dietary restriction", "meta-law": "nutritional guideline",
    "falsifiable": "replicable", "code": "dish", "experts": "chefs",
    "problem": "palate challenge", "property": "texture",
    "invert": "flip", "bug": "flaw",
}

SPATIAL = {
    "claim": "landmark", "concealment mechanism": "camouflage pattern",
    "conservation law": "geological formation", "structural invariant": "bedrock layer",
    "improvement": "terrain feature", "diagnostic": "surveying pass",
    "impossibility": "impassable terrain", "meta-law": "tectonic principle",
    "falsifiable": "measurable", "code": "landscape", "experts": "cartographers",
    "problem": "elevation challenge", "property": "geological feature",
    "invert": "excavate", "bug": "fault line",
}

RANDOM_VERBS = ["juggle", "memorize", "photograph", "whisper", "knit",
                "polish", "inflate", "dissolve", "broadcast", "excavate"]

RANDOM_NOUNS = ["refrigerator", "umbrella", "bicycle", "curtain", "telescope",
                "sandwich", "volcano", "hammock", "penguin", "lighthouse"]


def build_prompts(l12_body: str) -> dict:
    """Build all scrambled prompts + control."""
    ops = segment_l12(l12_body)
    prompts = {}

    # A: Order scrambling
    prompts["A1_reverse"] = (HEADER + "\n" + " ".join(reversed(ops)), "order_reverse")
    shuffled = list(ops)
    random.Random(42).shuffle(shuffled)
    prompts["A2_shuffle"] = (HEADER + "\n" + " ".join(shuffled), "order_shuffle")
    swapped = list(ops)
    for i in range(0, len(swapped) - 1, 2):
        swapped[i], swapped[i+1] = swapped[i+1], swapped[i]
    prompts["A3_pairswap"] = (HEADER + "\n" + " ".join(swapped), "order_pairswap")

    # B: Keyword replacement
    for name, replacements in [("B1_culinary", CULINARY), ("B2_spatial", SPATIAL)]:
        result = l12_body
        for old, new in sorted(replacements.items(), key=lambda x: -len(x[0])):
            result = re.sub(re.escape(old), new, result, flags=re.IGNORECASE)
        prompts[name] = (HEADER + "\n" + result, f"keyword_{name[3:]}")

    # B3: Verb scramble
    rng = random.Random(42)
    result = l12_body
    for verb in ["name", "engineer", "apply", "invert", "collect", "make"]:
        result = re.sub(rf'\b{verb}\b', rng.choice(RANDOM_VERBS), result, flags=re.IGNORECASE)
    prompts["B3_verb"] = (HEADER + "\n" + result, "verb_scramble")

    # B4: Noun scramble
    rng = random.Random(42)
    result = l12_body
    for noun in ["claim", "mechanism", "law", "invariant", "improvement", "diagnostic"]:
        result = re.sub(rf'\b{noun}\b', rng.choice(RANDOM_NOUNS), result, flags=re.IGNORECASE)
    prompts["B4_noun"] = (HEADER + "\n" + result, "noun_scramble")

    # C: Structure preservation
    lorem = "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod".split()
    words = l12_body.split()
    lorem_result = []
    for i, w in enumerate(words):
        punct = ""
        while w and w[-1] in ".,;:!?":
            punct = w[-1] + punct
            w = w[:-1]
        lorem_result.append(lorem[i % len(lorem)] + punct)
    prompts["C1_lorem"] = (HEADER + "\n" + " ".join(lorem_result), "lorem_ipsum")

    # C2: Markov
    rng = random.Random(42)
    bigrams = {}
    for i in range(len(words) - 1):
        bigrams.setdefault(words[i], []).append(words[i + 1])
    markov = [rng.choice(words)]
    for _ in range(len(words) - 1):
        cur = markov[-1]
        markov.append(rng.choice(bigrams.get(cur, [rng.choice(words)])))
    prompts["C2_markov"] = (HEADER + "\n" + " ".join(markov), "markov_chain")

    # C3: Reverse sentences
    sentences = re.split(r'(?<=[.!?])\s+', l12_body)
    rev_sents = [" ".join(reversed(s.split())) for s in sentences]
    prompts["C3_revsent"] = (HEADER + "\n" + " ".join(rev_sents), "reverse_sentences")

    # Control
    prompts["CONTROL_l12"] = (HEADER + "\n" + l12_body, "control")

    return prompts


# ── Analysis ─────────────────────────────────────────────────

def analyze_results(phase="core"):
    """Analyze results and compute false positive rates."""
    results_file = RESULTS_DIR / f"results_{phase}.jsonl"
    if not results_file.exists():
        print(f"No results file: {results_file}")
        return

    results = []
    for line in results_file.read_text().strip().split("\n"):
        if line:
            results.append(json.loads(line))

    control = [r for r in results if r["scramble_method"] == "control"]
    scrambled = [r for r in results if r["scramble_method"] != "control"]

    control_cl = sum(1 for r in control if r["classification"] == "CONSERVATION_LAW")
    control_tp = control_cl / len(control) if control else 0

    scrambled_cl = sum(1 for r in scrambled if r["classification"] == "CONSERVATION_LAW")
    scrambled_adj = sum(1 for r in scrambled if r["classification"] == "CL_ADJACENT")

    fp_strict = scrambled_cl / len(scrambled) if scrambled else 0
    fp_lenient = (scrambled_cl + scrambled_adj) / len(scrambled) if scrambled else 0

    print("=" * 60)
    print("U1: Null Distribution of Conservation Laws")
    print("=" * 60)
    print(f"\nControl (real L12):  {control_cl}/{len(control)} = {control_tp:.1%} TP")
    print(f"Scrambled strict:    {scrambled_cl}/{len(scrambled)} = {fp_strict:.1%} FP")
    print(f"Scrambled lenient:   {scrambled_cl + scrambled_adj}/{len(scrambled)} = {fp_lenient:.1%} FP")

    if control_tp > 0:
        print(f"FP/TP ratio: {fp_strict/control_tp:.2f}")

    # By method
    print("\n--- By Scrambling Method ---")
    for method in sorted(set(r["scramble_method"] for r in scrambled)):
        sub = [r for r in scrambled if r["scramble_method"] == method]
        cl = sum(1 for r in sub if r["classification"] == "CONSERVATION_LAW")
        adj = sum(1 for r in sub if r["classification"] == "CL_ADJACENT")
        print(f"  {method:20s}: CL={cl}/{len(sub)}, ADJ={adj}/{len(sub)}")

    # By target
    print("\n--- By Target ---")
    for tid in sorted(set(r["target_id"] for r in scrambled)):
        sub = [r for r in scrambled if r["target_id"] == tid]
        cl = sum(1 for r in sub if r["classification"] == "CONSERVATION_LAW")
        avg_w = sum(r["word_count"] for r in sub) / len(sub)
        print(f"  {tid:20s}: CL={cl}/{len(sub)}, avg_words={avg_w:.0f}")

    # CI
    n = len(scrambled)
    p = fp_strict
    if n > 0 and 0 < p < 1:
        se = math.sqrt(p * (1-p) / n)
        print(f"\n95% CI for FP rate: [{max(0,p-1.96*se):.1%}, {min(1,p+1.96*se):.1%}]")

    # Verdict
    print("\n--- VERDICT ---")
    if fp_strict > 0.3:
        print("HIGH FP: Conservation laws likely artifact of model tendency.")
    elif fp_strict > 0.1:
        print("MODERATE FP: Partially prompt-driven. Expand to 200+ runs.")
    elif fp_strict > 0.02:
        print("LOW FP: Predominantly prompt-driven. Scrambled rarely produce.")
    else:
        print("NEGLIGIBLE FP: Strongly prompt-specific. L12 does real work.")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--analyze", action="store_true")
    ap.add_argument("--phase", default="core")
    args = ap.parse_args()
    if args.analyze:
        analyze_results(args.phase)
    else:
        print("Run experiment with: python u1_null_distribution_protocol.py")
        print("Analyze with: python u1_null_distribution_protocol.py --analyze")

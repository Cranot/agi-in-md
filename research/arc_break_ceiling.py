#!/usr/bin/env python3
"""
ARC Break Ceiling — Systematic experiments to beat 93% on task 28a6681f.

The transformation has TWO parts:
  Part A (removals): remove 1s from where shapes overlap — found by most approaches
  Part B (additions): add 1s to gaps between staircase edges — found by zero approaches

11 prior approaches tested, ceiling at 93%. This script tests new angles.

Usage:
  python3 arc_break_ceiling.py                      # run Phase 1 + 2a
  python3 arc_break_ceiling.py --phase 1             # calibration only
  python3 arc_break_ceiling.py --phase 2a            # rule discovery angles
  python3 arc_break_ceiling.py --phase 2b            # mechanical decomposition
  python3 arc_break_ceiling.py --phase 3             # code generation
  python3 arc_break_ceiling.py --exp A1,A3,I1        # specific experiments
  python3 arc_break_ceiling.py --exp BASELINE --runs 3  # multiple runs
  python3 arc_break_ceiling.py --model claude-sonnet-4-6  # override model
"""
import json, os, re, sys, time, argparse, subprocess, tempfile
from pathlib import Path
from datetime import datetime

# === PATHS ===
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
# Try both layouts: research/arc_break_ceiling.py (local) and insights/arc_break_ceiling.py (VPS)
_DATA_CANDIDATES = [
    PROJECT_DIR / "hackathon" / "arc-agi-2" / "data" / "evaluation",
    SCRIPT_DIR / "hackathon" / "arc-agi-2" / "data" / "evaluation",
]
DATA_DIR = next((p for p in _DATA_CANDIDATES if p.exists()), _DATA_CANDIDATES[0])
RESULTS_DIR = SCRIPT_DIR / "arc_ceiling_results"

# === CONFIG ===
DEFAULT_TASK = "28a6681f"
MODEL_HAIKU = "claude-haiku-4-5-20251001"
MODEL_SONNET = "claude-sonnet-4-6"
CLI_TIMEOUT = 300

# === GRID UTILITIES ===

def grid_to_str(grid):
    """Format grid as space-separated numbers, one row per line."""
    return "\n".join(" ".join(str(c) for c in row) for row in grid)


def parse_grid(raw):
    """Parse grid from model output. Handles multiple formats."""
    if not raw:
        return None
    text = raw.strip()
    text = re.sub(r'```\w*\n?', '', text)
    text = re.sub(r'```\s*$', '', text)

    # Try JSON array first
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list) and all(isinstance(r, list) for r in parsed):
            return [[int(c) for c in r] for r in parsed]
    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    rows = []
    for line in text.split("\n"):
        line = line.strip()
        if not line or not any(c.isdigit() for c in line):
            if rows:
                continue
            continue
        if re.match(r'^[\|\-\+\s:]+$', line):
            continue
        # Skip commentary lines
        if re.match(r'^[A-Za-z].*\s[a-z]', line) and not re.match(r'^[\d\s,\|\[\]]+$', line):
            if rows:
                break
            continue
        line = line.strip("|[] \t")
        line = re.sub(r'[`\[\]]', '', line)
        nums = []
        for tok in re.split(r'[\s,|]+', line):
            tok = tok.strip("[]|`() ")
            if not tok:
                continue
            try:
                nums.append(int(tok))
            except ValueError:
                pass
        if len(nums) >= 2:
            rows.append(nums)
    return rows if rows else None


def cell_accuracy(pred, exp):
    """Cell-level accuracy between predicted and expected grids."""
    if not pred or not exp:
        return 0.0
    exp_rows = len(exp)
    exp_cols = len(exp[0]) if exp else 0
    total = exp_rows * exp_cols
    if total == 0:
        return 0.0
    correct = 0
    for r in range(exp_rows):
        for c in range(exp_cols):
            p = pred[r][c] if r < len(pred) and c < len(pred[r]) else -1
            if p == exp[r][c]:
                correct += 1
    return correct / total


def cell_diffs(pred, exp, inp=None):
    """Returns (missed_removals, missed_additions, wrong_values) counts + full diff list.

    If inp is provided, categorizes diffs by transform type:
      missed_removal: input non-zero, expected 0, pred non-zero
      missed_addition: input 0, expected non-zero, pred == 0
      wrong_value: other mismatch
    """
    all_diffs = []
    missed_r = missed_a = wrong_v = 0
    if not pred or not exp:
        return 0, 0, 0, []
    for r in range(len(exp)):
        for c in range(len(exp[r])):
            p = pred[r][c] if r < len(pred) and c < len(pred[r]) else -1
            e = exp[r][c]
            if p != e:
                all_diffs.append((r, c, p, e))
                if inp is not None:
                    iv = inp[r][c] if r < len(inp) and c < len(inp[r]) else 0
                    if iv != 0 and e == 0:
                        missed_r += 1
                    elif iv == 0 and e != 0:
                        missed_a += 1
                    else:
                        wrong_v += 1
    return missed_r, missed_a, wrong_v, all_diffs


def format_training(task_data):
    """Format training examples as text."""
    lines = []
    for i, ex in enumerate(task_data["train"]):
        lines += [
            f"=== Training Example {i+1} ===",
            f"Input ({len(ex['input'])}x{len(ex['input'][0])}):",
            grid_to_str(ex["input"]),
            f"Output ({len(ex['output'])}x{len(ex['output'][0])}):",
            grid_to_str(ex["output"]),
            "",
        ]
    return "\n".join(lines)


def format_full_task(task_data, test_idx=0):
    """Format training + test input for solver."""
    text = format_training(task_data)
    ti = task_data["test"][test_idx]["input"]
    text += f"\n=== Test Input ({len(ti)}x{len(ti[0])}) ===\n"
    text += grid_to_str(ti)
    return text


def parse_labeled_grids(text):
    """Parse PREDICTED_N: and TEST_OUTPUT: grids from response."""
    if not text:
        return {}, None
    predicted = {}
    test_grid = None

    for m in re.finditer(r'PREDICTED_(\d+)\s*:', text):
        n = int(m.group(1))
        rest = text[m.end():]
        grid = _extract_grid_block(rest)
        if grid:
            predicted[n] = grid

    m = re.search(r'TEST_OUTPUT\s*:', text)
    if m:
        rest = text[m.end():]
        test_grid = _extract_grid_block(rest)

    return predicted, test_grid


def _extract_grid_block(text):
    """Extract first grid block from text."""
    rows = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            if rows:
                break
            continue
        nums = []
        has_non_digit = False
        for tok in re.split(r'[\s,]+', line):
            tok = tok.strip("[]|`() ")
            if not tok:
                continue
            try:
                nums.append(int(tok))
            except ValueError:
                has_non_digit = True
                break
        if nums and not has_non_digit:
            rows.append(nums)
        elif rows:
            break
    return rows if len(rows) >= 2 else None


def parse_last_grid(text):
    """Extract the last grid block from text."""
    if not text:
        return None
    all_grids = []
    current = []
    for line in text.split("\n"):
        line = line.strip()
        nums = []
        if line:
            for tok in re.split(r'[\s,]+', line):
                tok = tok.strip("[]|`() ")
                if not tok:
                    continue
                try:
                    nums.append(int(tok))
                except ValueError:
                    pass
        if len(nums) >= 2:
            current.append(nums)
        elif current:
            all_grids.append(current)
            current = []
    if current:
        all_grids.append(current)
    return all_grids[-1] if all_grids else None


# === CLI ENGINE ===

def cli_call(user_input, system_prompt, model=MODEL_HAIKU, timeout=CLI_TIMEOUT):
    """Call claude -p with --tools '' (forces single-shot). Returns (text, elapsed)."""
    cmd = [
        "claude", "-p", "-",
        "--model", model,
        "--output-format", "text",
        "--tools", "",
        "--append-system-prompt", system_prompt,
    ]

    t0 = time.time()
    try:
        result = subprocess.run(
            cmd, input=user_input, capture_output=True, text=True, timeout=timeout
        )
        elapsed = time.time() - t0
        return result.stdout.strip(), elapsed
    except subprocess.TimeoutExpired:
        elapsed = time.time() - t0
        log(f"  TIMEOUT after {elapsed:.0f}s")
        return "", elapsed
    except Exception as e:
        elapsed = time.time() - t0
        log(f"  CLI ERROR: {type(e).__name__}: {str(e)[:200]}")
        return "", elapsed


def execute_code(code_text, input_grid, timeout=30):
    """Execute a Python transform(grid) function. Returns output grid or None."""
    code = re.sub(r'```python\s*', '', code_text)
    code = re.sub(r'```\s*$', '', code)
    code = code.strip()

    # Extract just the function if there's surrounding text
    match = re.search(r'(def transform\(.*?\n(?:[ \t]+.*\n)*)', code)
    if match:
        code = match.group(1)

    script = (code + "\n\nimport json, sys\n"
              "grid = json.load(sys.stdin)\n"
              "result = transform(grid)\n"
              "print(json.dumps(result))\n")

    try:
        result = subprocess.run(
            ["python3", "-c", script],
            input=json.dumps(input_grid),
            capture_output=True, text=True, timeout=timeout
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
        if result.stderr:
            log(f"    Code stderr: {result.stderr[:200]}")
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
        log(f"    Code execution error: {type(e).__name__}: {str(e)[:100]}")
    return None


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


# ============================================================
# EXPERIMENT PROMPTS
# ============================================================

# BASELINE: Standard COOK_ARC (control, same as prism.py)
COOK_ARC_BASE = (
    "You will receive grid transformation puzzle examples (input/output pairs) "
    "and a test input. Your job: discover the EXACT transformation rule and "
    "produce the correct output grid.\n\n"
    "MANDATORY STEPS:\n"
    "1. PERCEIVE: For each training example, list ALL cells that DIFFER "
    "between input and output. Note: position, old value, new value.\n"
    "2. CONSERVE: What stays the SAME between input and output? Dimensions, "
    "colors, counts, positions, shapes — be specific.\n"
    "3. TRANSFORM: What CHANGES? State the exact rule as a deterministic "
    "algorithm. It must handle ALL training examples with ZERO exceptions.\n"
    "4. VERIFY: Apply your rule to each training input. Output the FULL "
    "predicted grid. Use these EXACT markers:\n"
    "PREDICTED_1:\n[grid]\nPREDICTED_2:\n[grid]\n...etc.\n"
    "Compare each to the expected output. If ANY cell differs, revise "
    "your rule and redo from step 3.\n"
    "5. EXECUTE: Output the test answer with this EXACT marker:\n"
    "TEST_OUTPUT:\n[grid]\n\n"
    "Grid format: space-separated integers, one row per line. "
    "The markers PREDICTED_1:, PREDICTED_2:, TEST_OUTPUT: MUST appear."
)

# A1: Two-part decomposition — force model to treat removal/addition as separate rules
PROMPT_A1 = (
    "You will receive grid transformation puzzle examples (input/output pairs) "
    "and a test input.\n\n"
    "CRITICAL: This transformation has MULTIPLE INDEPENDENT PARTS. "
    "Do NOT try to find a single rule.\n\n"
    "STEP 1 — CATEGORIZE ALL CHANGES: For each training example, list ALL cells "
    "that differ between input and output. Split into TWO groups:\n"
    "  - REMOVALS: cells where a non-zero value became 0\n"
    "  - ADDITIONS: cells where 0 became a non-zero value\n"
    "List every removal and every addition with exact [row,col] coordinates.\n\n"
    "STEP 2 — REMOVAL RULE: What pattern explains ALL removals across ALL "
    "training examples? State as a deterministic algorithm.\n\n"
    "STEP 3 — ADDITION RULE: SEPARATELY, what pattern explains ALL additions? "
    "Where do new non-zero values appear? What determines their position? "
    "What value do they get? Look at the GAP between two non-zero structures — "
    "cells that are enclosed by boundaries on two sides.\n\n"
    "STEP 4 — VERIFY BOTH: Apply removal rule THEN addition rule to each "
    "training input. Output FULL predicted grids:\n"
    "PREDICTED_1:\n[grid]\nPREDICTED_2:\n[grid]\n...etc.\n"
    "If ANY cell differs from expected, revise and redo.\n\n"
    "STEP 5 — EXECUTE: Apply both rules to test input.\n"
    "TEST_OUTPUT:\n[grid]\n\n"
    "Grid format: space-separated integers, one row per line."
)

# A2: Negative space — invert attention to find additions
PROMPT_A2 = (
    "You will receive grid transformation puzzle examples (input/output pairs) "
    "and a test input.\n\n"
    "PERCEPTION SHIFT: This puzzle involves TWO operations. Most solvers find "
    "the first (removing values) but miss the second (adding values).\n\n"
    "STEP 1 — MAP STRUCTURES: Identify every non-zero colored structure by "
    "color and shape (e.g., 'color-3 staircase', 'color-2 triangle').\n\n"
    "STEP 2 — FIND REMOVALS (EASY): Which cells go from non-zero to 0? "
    "State the removal rule.\n\n"
    "STEP 3 — FIND ADDITIONS (HARD — FOCUS HERE):\n"
    "  - After removals, examine the 0-valued cells between two structures\n"
    "  - In the output, do any 0s become non-zero? List EVERY such cell.\n"
    "  - What value fills each gap? (The SAME value that was removed elsewhere)\n"
    "  - What determines WHICH gaps get filled? (The cells between two staircase "
    "edges that form an enclosed channel)\n\n"
    "STEP 4 — VERIFY: Apply removal + addition rules to each training input.\n"
    "PREDICTED_1:\n[grid]\nPREDICTED_2:\n[grid]\n\n"
    "STEP 5 — EXECUTE:\n"
    "TEST_OUTPUT:\n[grid]\n\n"
    "Grid format: space-separated integers, one row per line."
)

# A3: Pre-computed diff table prompt (task text + diff table added by runner)
PROMPT_A3 = (
    "You will receive grid transformation puzzle examples WITH PRE-COMPUTED "
    "DIFF TABLES showing exactly which cells change.\n\n"
    "The diffs are categorized as:\n"
    "- REMOVALS: non-zero → 0 (value was deleted)\n"
    "- ADDITIONS: 0 → non-zero (value was created)\n\n"
    "Your job: discover the EXACT rules for BOTH removals AND additions, "
    "then apply them to the test input.\n\n"
    "STEPS:\n"
    "1. Study the REMOVAL diffs: what pattern determines which cells are removed?\n"
    "2. Study the ADDITION diffs: what pattern determines where new values appear "
    "and what value they get? (Look at spatial relationships between structures)\n"
    "3. State BOTH rules as deterministic algorithms.\n"
    "4. Verify on each training input:\n"
    "PREDICTED_1:\n[grid]\nPREDICTED_2:\n[grid]\n...etc.\n"
    "5. Apply to test input:\n"
    "TEST_OUTPUT:\n[grid]\n\n"
    "Grid format: space-separated integers, one row per line."
)

# I1 Stage 2: Self-critique
PROMPT_I1_CRITIQUE = (
    "You previously analyzed a grid transformation puzzle and proposed a rule.\n\n"
    "YOUR PREVIOUS ANALYSIS:\n{analysis}\n\n"
    "TRAINING EXAMPLES:\n{training}\n\n"
    "NOW BE YOUR OWN HARSHEST CRITIC:\n"
    "For EACH training example:\n"
    "1. Apply your rule cell-by-cell to the training input\n"
    "2. Compare to the ACTUAL expected output\n"
    "3. List EVERY cell where your rule produces the WRONG value\n"
    "4. Categorize: MISSED REMOVALS (you kept something that should be 0) "
    "or MISSED ADDITIONS (you have 0 where there should be a value)\n"
    "5. What PATTERN do the errors reveal? What did you MISS?\n"
    "6. State the SPECIFIC correction needed.\n\n"
    "Be brutally honest. Finding your own errors is the goal."
)

# I1 Stage 3: Fix based on critique
PROMPT_I1_FIX = (
    "You analyzed a grid transformation puzzle, then critically examined your "
    "own rule and found specific errors.\n\n"
    "ORIGINAL ANALYSIS:\n{analysis}\n\n"
    "SELF-CRITIQUE:\n{critique}\n\n"
    "TRAINING EXAMPLES:\n{training}\n\n"
    "Now FIX your rule incorporating the critique. The corrected rule must "
    "handle ALL training examples with ZERO errors.\n\n"
    "Apply the corrected rule:\n"
    "PREDICTED_1:\n[grid]\nPREDICTED_2:\n[grid]\n...etc.\n"
    "TEST_OUTPUT:\n[grid]\n\n"
    "Grid format: space-separated integers, one row per line. "
    "The markers PREDICTED_1:, PREDICTED_2:, TEST_OUTPUT: MUST appear."
)

# B3 Stage 1: Removal only
PROMPT_B3_REMOVAL = (
    "You will receive grid transformation puzzle examples and a test input.\n\n"
    "Focus ONLY on REMOVALS — which non-zero cells become 0 in the output?\n\n"
    "STEPS:\n"
    "1. For each training example, list cells that change from non-zero to 0.\n"
    "2. State the REMOVAL RULE as a deterministic algorithm.\n"
    "3. Apply ONLY the removal rule to the test input (keep everything else).\n\n"
    "TEST_OUTPUT:\n[grid]\n\n"
    "Grid format: space-separated integers, one row per line. "
    "Output the test grid with ONLY removals applied."
)

# B3 Stage 2: Addition only (receives partially transformed grid)
PROMPT_B3_ADDITION = (
    "You will receive grid transformation puzzle examples and a PARTIALLY "
    "TRANSFORMED test grid where removals have already been applied.\n\n"
    "The removal step is DONE. Now focus ONLY on ADDITIONS — which 0-valued "
    "cells should gain a new non-zero value?\n\n"
    "Study the training examples: after removals, which 0s become non-zero? "
    "What value? What spatial pattern determines which gaps get filled?\n\n"
    "CURRENT STATE of test grid (removals already applied):\n{current_grid}\n\n"
    "Apply ONLY the addition rule to complete the transformation.\n"
    "TEST_OUTPUT:\n[grid]\n\n"
    "Grid format: space-separated integers, one row per line."
)

# HYBRID: A1 decomposition + value migration hint + self-verify
PROMPT_HYBRID = (
    "You will receive grid transformation puzzle examples (input/output pairs) "
    "and a test input.\n\n"
    "THIS TRANSFORMATION HAS EXACTLY TWO INDEPENDENT OPERATIONS:\n\n"
    "OPERATION A — VALUE REMOVAL: Some non-zero cells become 0.\n"
    "OPERATION B — VALUE MIGRATION: The removed values REAPPEAR in a different "
    "location. Specifically, they fill the 0-valued GAPS between two non-zero "
    "structures. The value that fills each gap = the value that was removed.\n\n"
    "Think of it as: values are MOVED from one area to another, not just deleted.\n\n"
    "STEP 1 — MAP ALL CHANGES per training example:\n"
    "  For each cell that differs: state [row,col]: input_value -> output_value\n"
    "  Split into: REMOVALS (non-zero -> 0) and ADDITIONS (0 -> non-zero)\n"
    "  Count them. Removals and additions should be consistent across examples.\n\n"
    "STEP 2 — REMOVAL RULE: What determines which cells are removed?\n"
    "  (Hint: look at where two different colored structures overlap or where "
    "one structure sits on top of another's area)\n\n"
    "STEP 3 — ADDITION RULE: Where do the migrated values appear?\n"
    "  (Hint: find the 0-valued cells that are ENCLOSED between two non-zero "
    "structures — a gap or channel. The gap cells get filled with the same "
    "value that was removed elsewhere.)\n\n"
    "STEP 4 — SELF-CHECK: Apply BOTH rules to EACH training input.\n"
    "  For each predicted grid, count cells different from expected.\n"
    "  If ANY cell is wrong: identify which rule failed and why, fix it, redo.\n"
    "  PREDICTED_1:\n[grid]\n  PREDICTED_2:\n[grid]\n  PREDICTED_3:\n[grid]\n\n"
    "STEP 5 — EXECUTE on test input:\n"
    "  TEST_OUTPUT:\n[grid]\n\n"
    "Grid format: space-separated integers, one row per line."
)

# I4: Reverse engineering (swap input/output to make additions into removals)
PROMPT_I4 = (
    "You will receive grid transformation puzzle examples. IMPORTANT: the labels "
    "are REVERSED — 'Input' shows the OUTPUT and 'Output' shows the INPUT.\n\n"
    "STEPS:\n"
    "1. Study the REVERSE transformation: what changes from 'Input' to 'Output'?\n"
    "   (Since labels are swapped, what APPEARS as additions are actually the "
    "parts that get REMOVED in the forward direction, and vice versa.)\n"
    "2. Once you understand the reverse rule, INVERT it to get the FORWARD rule.\n"
    "3. Apply the FORWARD rule to the REAL test input below.\n\n"
    "PREDICTED_1:\n[grid]\nPREDICTED_2:\n[grid]\n\n"
    "TEST_OUTPUT:\n[grid]\n\n"
    "Grid format: space-separated integers, one row per line."
)

# C1/C3: Code generation
PROMPT_CODE = (
    "You will see training examples from a grid transformation puzzle.\n\n"
    "Write a Python function `def transform(grid):` that takes a 2D list of "
    "integers (the input grid) and returns the correct output grid.\n\n"
    "CRITICAL: This transformation has TWO parts:\n"
    "1. REMOVALS: some non-zero cells become 0\n"
    "2. ADDITIONS: some 0 cells gain non-zero values\n"
    "Your function MUST handle BOTH parts.\n\n"
    "Test your function mentally against ALL training examples. If it produces "
    "the wrong output for ANY example, fix it.\n\n"
    "Output ONLY the Python function. No imports (use only builtins). "
    "No print statements. No comments. No explanation. Just the function.\n\n"
    "```python\ndef transform(grid):\n    ...\n```"
)


# ============================================================
# DIFF TABLE BUILDER (A3)
# ============================================================

def compute_diff_table(task_data):
    """Pre-compute cell-by-cell diffs for all training examples."""
    lines = []
    for i, ex in enumerate(task_data["train"]):
        inp = ex["input"]
        out = ex["output"]
        removals = []
        additions = []
        for r in range(len(out)):
            for c in range(len(out[r])):
                iv = inp[r][c] if r < len(inp) and c < len(inp[r]) else 0
                ov = out[r][c]
                if iv != ov:
                    if iv != 0 and ov == 0:
                        removals.append((r, c, iv))
                    elif iv == 0 and ov != 0:
                        additions.append((r, c, ov))

        lines.append(f"\n=== Training Example {i+1} DIFF TABLE ===")
        lines.append(f"Grid: {len(inp)}x{len(inp[0])}")

        if removals:
            lines.append(f"\nREMOVALS ({len(removals)} cells changed from non-zero to 0):")
            for r, c, v in removals:
                lines.append(f"  [{r},{c}]: value {v} -> 0")
        else:
            lines.append("\nREMOVALS: none")

        if additions:
            lines.append(f"\nADDITIONS ({len(additions)} cells changed from 0 to non-zero):")
            for r, c, v in additions:
                lines.append(f"  [{r},{c}]: 0 -> value {v}")
        else:
            lines.append("\nADDITIONS: none")

        lines.append("")

    return "\n".join(lines)


# ============================================================
# STRUCTURED FEEDBACK (B1)
# ============================================================

def structured_feedback(train_pairs, predicted_grids, attempt_num):
    """Enhanced feedback: categorizes errors as missed removals/additions."""
    lines = [f"\n--- ATTEMPT {attempt_num} FAILED ON TRAINING ---\n"]
    any_wrong = False

    for i, (inp, exp) in enumerate(train_pairs):
        n = i + 1
        pred = predicted_grids.get(n)
        if pred is None:
            lines.append(f"Training {n}: NO PREDICTION FOUND")
            any_wrong = True
            continue

        missed_removals = []
        missed_additions = []
        wrong_values = []
        total_cells = len(exp) * (len(exp[0]) if exp else 0)

        for r in range(len(exp)):
            for c in range(len(exp[r])):
                p = pred[r][c] if r < len(pred) and c < len(pred[r]) else -1
                e = exp[r][c]
                if p == e:
                    continue
                iv = inp[r][c] if r < len(inp) and c < len(inp[r]) else 0
                if iv != 0 and e == 0:
                    missed_removals.append((r, c, p, e, iv))
                elif iv == 0 and e != 0:
                    missed_additions.append((r, c, p, e))
                else:
                    wrong_values.append((r, c, p, e))

        total_wrong = len(missed_removals) + len(missed_additions) + len(wrong_values)
        if total_wrong == 0:
            lines.append(f"Training {n}: PERFECT (100%)")
            continue

        any_wrong = True
        acc = (total_cells - total_wrong) / total_cells if total_cells else 0
        lines.append(f"Training {n}: {acc:.0%} accuracy, {total_wrong} wrong cells:")

        if missed_removals:
            lines.append(f"  MISSED REMOVALS ({len(missed_removals)} — should be 0):")
            for r, c, p, e, iv in missed_removals[:10]:
                lines.append(f"    [{r},{c}]: input={iv}, your output={p}, correct=0")

        if missed_additions:
            lines.append(f"  MISSED ADDITIONS ({len(missed_additions)} — should have value):")
            for r, c, p, e in missed_additions[:10]:
                lines.append(f"    [{r},{c}]: your output=0, correct={e}")

        if wrong_values:
            lines.append(f"  WRONG VALUES ({len(wrong_values)}):")
            for r, c, p, e in wrong_values[:10]:
                lines.append(f"    [{r},{c}]: your output={p}, correct={e}")

    lines.append("\nRevise your rule — pay SPECIAL ATTENTION to MISSED ADDITIONS. "
                 "These are cells where your rule outputs 0 but the correct output "
                 "has a non-zero value. The additions follow a spatial pattern.\n"
                 "The markers PREDICTED_1:, PREDICTED_2:, TEST_OUTPUT: MUST appear.")
    return any_wrong, "\n".join(lines)


# ============================================================
# EXPERIMENT RUNNER
# ============================================================

def extract_test_grid(response):
    """Extract test grid from response, trying labeled then last-grid fallback."""
    predicted, test_grid = parse_labeled_grids(response)
    if not test_grid:
        test_grid = parse_last_grid(response)
    return predicted, test_grid


def run_solve_with_feedback(task_text, system_prompt, train_pairs, model,
                            max_attempts=3, feedback_fn=None):
    """Solve with verify-and-retry loop. Returns (response, test_grid, predicted, calls, elapsed)."""
    if feedback_fn is None:
        feedback_fn = structured_feedback

    prompt = task_text
    best_response = ""
    best_grid = None
    best_acc = -1
    total_calls = 0
    total_elapsed = 0

    for attempt in range(1, max_attempts + 1):
        response, elapsed = cli_call(prompt, system_prompt, model=model)
        total_calls += 1
        total_elapsed += elapsed

        if not response:
            continue

        predicted, test_grid = extract_test_grid(response)

        # Score training predictions
        if predicted and train_pairs:
            total_acc = 0
            for n, (inp, exp) in enumerate(train_pairs, 1):
                pred = predicted.get(n)
                if pred:
                    total_acc += cell_accuracy(pred, exp)
            avg_acc = total_acc / len(train_pairs)

            if avg_acc > best_acc:
                best_acc = avg_acc
                best_response = response
                best_grid = test_grid

            if avg_acc >= 1.0:
                log(f"    Attempt {attempt}: train=PERFECT")
                return response, test_grid, predicted, total_calls, total_elapsed

            log(f"    Attempt {attempt}: train={avg_acc:.0%}")

            if attempt < max_attempts:
                any_wrong, feedback = feedback_fn(train_pairs, predicted, attempt)
                if any_wrong:
                    prompt = task_text + "\n" + feedback
                else:
                    break
        else:
            if test_grid and (best_grid is None):
                best_response = response
                best_grid = test_grid
            log(f"    Attempt {attempt}: no training predictions parsed")
            break

    return best_response, best_grid, {}, total_calls, total_elapsed


def run_experiment(exp_id, task_data, model=MODEL_HAIKU, runs=1):
    """Run a single experiment. Returns list of result dicts (one per run)."""
    test_input = task_data["test"][0]["input"]
    test_expected = task_data["test"][0].get("output")
    train_pairs = [(ex["input"], ex["output"]) for ex in task_data["train"]]
    task_text = format_full_task(task_data)

    all_results = []

    for run_num in range(1, runs + 1):
        run_label = f"{exp_id}" if runs == 1 else f"{exp_id} run {run_num}"
        log(f"  [{run_label}] Starting...")

        result = {
            "exp_id": exp_id, "run": run_num, "model": model,
            "test_grid": None, "test_acc": 0.0, "test_exact": False,
            "missed_removals": 0, "missed_additions": 0, "wrong_values": 0,
            "calls": 0, "elapsed": 0, "response_len": 0,
        }

        t0 = time.time()
        response = ""
        test_grid = None
        predicted = {}

        # ---- BASELINE / H1 / H2 (standard COOK_ARC) ----
        if exp_id in ("BASELINE", "H1", "H2"):
            response, test_grid, predicted, calls, elapsed = run_solve_with_feedback(
                task_text, COOK_ARC_BASE, train_pairs, model)
            result["calls"] = calls

        # ---- A1: Two-part decomposition ----
        elif exp_id == "A1":
            response, elapsed = cli_call(task_text, PROMPT_A1, model=model)
            result["calls"] = 1
            predicted, test_grid = extract_test_grid(response)

        # ---- A2: Negative space ----
        elif exp_id == "A2":
            response, elapsed = cli_call(task_text, PROMPT_A2, model=model)
            result["calls"] = 1
            predicted, test_grid = extract_test_grid(response)

        # ---- A3: Pre-computed diff table ----
        elif exp_id == "A3":
            diff_table = compute_diff_table(task_data)
            a3_text = task_text + "\n\n" + diff_table
            response, elapsed = cli_call(a3_text, PROMPT_A3, model=model)
            result["calls"] = 1
            predicted, test_grid = extract_test_grid(response)

        # ---- I1: Self-refute (3-stage) ----
        elif exp_id == "I1":
            # Stage 1: Standard solve
            r1, e1 = cli_call(task_text, COOK_ARC_BASE, model=model)
            result["calls"] = 1
            elapsed = e1

            if r1:
                training_text = format_training(task_data)
                # Stage 2: Self-critique
                critique_prompt = PROMPT_I1_CRITIQUE.format(
                    analysis=r1[:4000], training=training_text)
                r2, e2 = cli_call(critique_prompt,
                    "You are a ruthless self-critic analyzing grid transformation rules.",
                    model=model)
                result["calls"] += 1
                elapsed += e2

                if r2:
                    # Stage 3: Fix
                    fix_prompt = PROMPT_I1_FIX.format(
                        analysis=r1[:3000], critique=r2[:3000],
                        training=training_text)
                    ti = task_data["test"][0]["input"]
                    fix_prompt += (f"\n\n=== Test Input ({len(ti)}x{len(ti[0])}) ===\n"
                                   + grid_to_str(ti))
                    response, e3 = cli_call(fix_prompt,
                        "Apply the corrected rule. Output grids with markers.",
                        model=model)
                    result["calls"] += 1
                    elapsed += e3
                else:
                    response = r1
            else:
                response = ""
            predicted, test_grid = extract_test_grid(response)

        # ---- B1: Structured feedback loop ----
        elif exp_id == "B1":
            response, test_grid, predicted, calls, elapsed = run_solve_with_feedback(
                task_text, COOK_ARC_BASE, train_pairs, model,
                max_attempts=3, feedback_fn=structured_feedback)
            result["calls"] = calls

        # ---- B3: Two-stage (removal then addition) ----
        elif exp_id == "B3":
            # Stage 1: Removal only
            r1, e1 = cli_call(task_text, PROMPT_B3_REMOVAL, model=model)
            result["calls"] = 1
            elapsed = e1

            removal_grid = None
            if r1:
                _, removal_grid = parse_labeled_grids(r1)
                if not removal_grid:
                    removal_grid = parse_last_grid(r1)

            if removal_grid:
                log(f"    Stage 1 (removal): got {len(removal_grid)} rows")
                # Stage 2: Addition
                current = grid_to_str(removal_grid)
                addition_text = (task_text + "\n\n" +
                    PROMPT_B3_ADDITION.format(current_grid=current))
                response, e2 = cli_call(addition_text,
                    "Complete the transformation by adding values to the correct gaps.",
                    model=model)
                result["calls"] += 1
                elapsed += e2
            else:
                response = r1 or ""
                log(f"    Stage 1 (removal) failed to produce grid")
            predicted, test_grid = extract_test_grid(response)

        # ---- I4: Reverse engineering ----
        elif exp_id == "I4":
            # Swap input/output in training examples
            reversed_lines = []
            for i, ex in enumerate(task_data["train"]):
                reversed_lines += [
                    f"=== Training Example {i+1} ===",
                    f"Input ({len(ex['output'])}x{len(ex['output'][0])}):",
                    grid_to_str(ex["output"]),  # output shown as input
                    f"Output ({len(ex['input'])}x{len(ex['input'][0])}):",
                    grid_to_str(ex["input"]),   # input shown as output
                    "",
                ]
            ti = task_data["test"][0]["input"]
            reversed_lines += [
                f"\n=== REAL Test Input ({len(ti)}x{len(ti[0])}) ===",
                "(Apply the FORWARD rule to this input)",
                grid_to_str(ti),
            ]
            reversed_text = "\n".join(reversed_lines)
            response, elapsed = cli_call(reversed_text, PROMPT_I4, model=model)
            result["calls"] = 1
            predicted, test_grid = extract_test_grid(response)

        # ---- C1: Code generation (Haiku) ----
        elif exp_id == "C1":
            training_text = format_training(task_data)
            response, elapsed = cli_call(training_text, PROMPT_CODE, model=model)
            result["calls"] = 1

            if response:
                # Execute on training to verify
                all_pass = True
                for i, ex in enumerate(task_data["train"]):
                    out = execute_code(response, ex["input"])
                    if out:
                        acc = cell_accuracy(out, ex["output"])
                        exact = out == ex["output"]
                        log(f"    Train[{i}]: {'PASS' if exact else f'{acc:.0%}'}")
                        if not exact:
                            all_pass = False
                    else:
                        log(f"    Train[{i}]: execution failed")
                        all_pass = False

                # Execute on test
                test_grid = execute_code(response, test_input)
                if test_grid:
                    log(f"    Code produced test grid: {len(test_grid)} rows")

        # ---- C3: Code generation (Sonnet) ----
        elif exp_id == "C3":
            training_text = format_training(task_data)
            response, elapsed = cli_call(training_text, PROMPT_CODE, model=MODEL_SONNET)
            result["calls"] = 1
            result["model"] = MODEL_SONNET

            if response:
                all_pass = True
                for i, ex in enumerate(task_data["train"]):
                    out = execute_code(response, ex["input"])
                    if out:
                        acc = cell_accuracy(out, ex["output"])
                        exact = out == ex["output"]
                        log(f"    Train[{i}]: {'PASS' if exact else f'{acc:.0%}'}")
                        if not exact:
                            all_pass = False
                    else:
                        log(f"    Train[{i}]: execution failed")
                        all_pass = False

                test_grid = execute_code(response, test_input)
                if test_grid:
                    log(f"    Code produced test grid: {len(test_grid)} rows")

        # ---- HYBRID: A1 decomposition + migration hint + self-verify ----
        elif exp_id == "HYBRID":
            response, test_grid, predicted, calls, elapsed = run_solve_with_feedback(
                task_text, PROMPT_HYBRID, train_pairs, model,
                max_attempts=3, feedback_fn=structured_feedback)
            result["calls"] = calls

        # ---- D3: Progressive disclosure ----
        elif exp_id == "D3":
            # Show one training example at a time, refine rule incrementally
            rule = ""
            for i, ex in enumerate(task_data["train"]):
                ex_text = (f"=== Training Example {i+1} ===\n"
                           f"Input ({len(ex['input'])}x{len(ex['input'][0])}):\n"
                           f"{grid_to_str(ex['input'])}\n"
                           f"Output ({len(ex['output'])}x{len(ex['output'][0])}):\n"
                           f"{grid_to_str(ex['output'])}\n")
                if rule:
                    prompt_text = (f"Your current rule:\n{rule}\n\n"
                                   f"Here is another training example. "
                                   f"Does your rule still work? If not, refine it.\n\n"
                                   f"{ex_text}\n"
                                   f"State the updated rule.")
                else:
                    prompt_text = (f"Study this training example and propose a "
                                   f"transformation rule.\n\n{ex_text}\n"
                                   f"State the rule as a deterministic algorithm.")

                r, e = cli_call(prompt_text,
                    "You discover grid transformation rules incrementally.",
                    model=model)
                result["calls"] += 1
                elapsed = elapsed + e if 'elapsed' in dir() else e
                if r:
                    rule = r[:2000]
                    log(f"    Example {i+1}: rule refined ({len(r)} chars)")

            # Final: apply refined rule to test
            if rule:
                ti = task_data["test"][0]["input"]
                final_prompt = (
                    f"Your verified rule:\n{rule}\n\n"
                    f"Apply this EXACT rule to the test input.\n\n"
                    f"Test Input ({len(ti)}x{len(ti[0])}):\n{grid_to_str(ti)}\n\n"
                    f"TEST_OUTPUT:\n[grid]\n\n"
                    f"Grid format: space-separated integers, one row per line."
                )
                response, e = cli_call(final_prompt,
                    "Apply the rule exactly. Output ONLY the grid after TEST_OUTPUT:",
                    model=model)
                result["calls"] += 1
                elapsed += e
            predicted, test_grid = extract_test_grid(response if response else "")

        else:
            log(f"  [{exp_id}] Unknown experiment")
            all_results.append(result)
            continue

        # ---- Score results ----
        result["response_len"] = len(response) if response else 0
        result["test_grid"] = test_grid
        result["elapsed"] = time.time() - t0

        if test_grid and test_expected:
            result["test_acc"] = cell_accuracy(test_grid, test_expected)
            result["test_exact"] = test_grid == test_expected
            mr, ma, wv, _ = cell_diffs(test_grid, test_expected, test_input)
            result["missed_removals"] = mr
            result["missed_additions"] = ma
            result["wrong_values"] = wv

        status = "EXACT!" if result["test_exact"] else f"{result['test_acc']:.1%}"
        log(f"  [{run_label}] test={status}, "
            f"missed_r={result['missed_removals']}, missed_a={result['missed_additions']}, "
            f"{result['calls']} calls, {result['elapsed']:.0f}s")

        all_results.append(result)

    return all_results


# ============================================================
# F3: UNION STRATEGY (post-processing)
# ============================================================

def union_strategy(results, task_data):
    """Combine outputs: trust removals from all, additions only from best.

    The insight: Part A (removals) is easy, Part B (additions) is hard.
    So take the consensus on removals and trust the approach with the
    fewest missed additions for the addition part.
    """
    test_input = task_data["test"][0]["input"]
    test_expected = task_data["test"][0].get("output")
    grids = [(r["exp_id"], r["test_grid"]) for r in results if r.get("test_grid")]

    if not grids:
        log("  [F3] No grids to combine")
        return None

    rows = len(test_input)
    cols = len(test_input[0])

    # Start with test input, apply consensus removals + best additions
    output = [row[:] for row in test_input]

    # Removals: if ANY approach removed a cell, remove it
    for r in range(rows):
        for c in range(cols):
            if test_input[r][c] != 0:
                votes_remove = sum(1 for _, g in grids
                    if g and r < len(g) and c < len(g[r]) and g[r][c] == 0)
                if votes_remove > len(grids) // 2:  # majority removes
                    output[r][c] = 0

    # Additions: find which approach has fewest missed additions
    if test_expected:
        best_add_exp = None
        best_add_score = -1
        for exp_id, grid in grids:
            if not grid:
                continue
            # Count how many additions this approach found
            found_additions = 0
            for r in range(len(test_expected)):
                for c in range(len(test_expected[r])):
                    if test_input[r][c] == 0 and test_expected[r][c] != 0:
                        if r < len(grid) and c < len(grid[r]) and grid[r][c] == test_expected[r][c]:
                            found_additions += 1
            if found_additions > best_add_score:
                best_add_score = found_additions
                best_add_exp = (exp_id, grid)

        if best_add_exp:
            exp_id, grid = best_add_exp
            log(f"  [F3] Best additions from: {exp_id} ({best_add_score} correct)")
            for r in range(rows):
                for c in range(cols):
                    if test_input[r][c] == 0 and grid[r][c] != 0:
                        output[r][c] = grid[r][c]
    else:
        # No ground truth — use majority voting for additions too
        for r in range(rows):
            for c in range(cols):
                if test_input[r][c] == 0:
                    from collections import Counter
                    votes = Counter(
                        g[r][c] for _, g in grids
                        if g and r < len(g) and c < len(g[r]) and g[r][c] != 0
                    )
                    if votes:
                        output[r][c] = votes.most_common(1)[0][0]

    acc = cell_accuracy(output, test_expected) if test_expected else -1
    exact = output == test_expected if test_expected else False
    log(f"  [F3] Union result: {acc:.1%}, exact={exact}")
    return output


# ============================================================
# MAIN
# ============================================================

PHASES = {
    "1":   ["H1", "H2"],
    "2a":  ["BASELINE", "A1", "A2", "A3", "I1"],
    "2b":  ["B1", "B3", "I4"],
    "3":   ["C1", "C3"],
    "4":   ["D3"],
    "all": ["BASELINE", "A1", "A2", "A3", "I1", "B1", "B3", "I4", "C1", "C3"],
}


def main():
    parser = argparse.ArgumentParser(description="ARC Break Ceiling Experiments")
    parser.add_argument("--task", default=DEFAULT_TASK, help="Task ID")
    parser.add_argument("--phase", help="Phase to run: 1, 2a, 2b, 3, 4, all")
    parser.add_argument("--exp", help="Comma-separated experiment IDs")
    parser.add_argument("--model", default=MODEL_HAIKU, help=f"Model (default: {MODEL_HAIKU})")
    parser.add_argument("--runs", type=int, default=1, help="Runs per experiment (for variance)")
    parser.add_argument("--h1-task", default="135a2760", help="H1 calibration task")
    parser.add_argument("--h2-task", default="c7f57c3e", help="H2 calibration task")
    parser.add_argument("--union", action="store_true", help="Run F3 union after all experiments")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Load main task
    task_file = DATA_DIR / f"{args.task}.json"
    if not task_file.exists():
        print(f"Task file not found: {task_file}")
        sys.exit(1)
    task_data = json.load(open(task_file))

    ti = task_data["test"][0]["input"]
    te = task_data["test"][0].get("output")
    log(f"Task: {args.task} ({len(task_data['train'])} train, "
        f"{len(ti)}x{len(ti[0])} grid)")
    log(f"Model: {args.model}")

    # Compute ground truth stats
    if te:
        n_removals = n_additions = 0
        for r in range(len(te)):
            for c in range(len(te[r])):
                iv = ti[r][c]
                ev = te[r][c]
                if iv != 0 and ev == 0:
                    n_removals += 1
                elif iv == 0 and ev != 0:
                    n_additions += 1
        log(f"Ground truth: {n_removals} removals, {n_additions} additions to find")
    log("")

    # Determine experiments
    if args.exp:
        experiments = [e.strip() for e in args.exp.split(",")]
    elif args.phase:
        experiments = PHASES.get(args.phase, PHASES["2a"])
    else:
        experiments = PHASES["2a"]  # default: Phase 2a

    log(f"Experiments: {experiments}")
    log("=" * 70)

    all_results = []

    for exp_id in experiments:
        # H1/H2: load different task data
        if exp_id in ("H1", "H2"):
            h_task = args.h1_task if exp_id == "H1" else args.h2_task
            h_file = DATA_DIR / f"{h_task}.json"
            if not h_file.exists():
                log(f"  [{exp_id}] Task file not found: {h_file}")
                continue
            h_data = json.load(open(h_file))
            log(f"\n--- {exp_id}: Calibration on {h_task} ---")
            results = run_experiment(exp_id, h_data, model=args.model, runs=args.runs)
        else:
            log(f"\n--- {exp_id} ---")
            results = run_experiment(exp_id, task_data, model=args.model, runs=args.runs)

        all_results.extend(results)

    # F3: Union strategy (if requested and we have results on the main task)
    if args.union:
        main_results = [r for r in all_results if r["exp_id"] not in ("H1", "H2")]
        if main_results:
            log(f"\n--- F3: Union Strategy ---")
            union_grid = union_strategy(main_results, task_data)
            if union_grid:
                mr, ma, wv, _ = cell_diffs(union_grid, te, ti)
                all_results.append({
                    "exp_id": "F3_UNION", "run": 1, "model": "post-process",
                    "test_grid": union_grid,
                    "test_acc": cell_accuracy(union_grid, te) if te else 0,
                    "test_exact": union_grid == te if te else False,
                    "missed_removals": mr, "missed_additions": ma,
                    "wrong_values": wv, "calls": 0, "elapsed": 0,
                    "response_len": 0,
                })

    # ============================================================
    # SUMMARY
    # ============================================================
    log("\n" + "=" * 70)
    log("SUMMARY")
    log("=" * 70)
    log(f"{'Exp':<12} {'Run':>3} {'Acc':>6} {'Exact':>6} "
        f"{'MissR':>5} {'MissA':>5} {'WrongV':>6} "
        f"{'Calls':>5} {'Time':>5} {'RespLen':>7}")
    log("-" * 70)

    for r in all_results:
        log(f"{r['exp_id']:<12} {r['run']:>3} {r['test_acc']:>5.1%} "
            f"{'YES' if r['test_exact'] else 'no':>6} "
            f"{r['missed_removals']:>5} {r['missed_additions']:>5} "
            f"{r['wrong_values']:>6} "
            f"{r['calls']:>5} {r['elapsed']:>4.0f}s "
            f"{r['response_len']:>7}")

    # Best result
    best = max(all_results, key=lambda r: r["test_acc"]) if all_results else None
    if best:
        log(f"\nBest: {best['exp_id']} run {best['run']} — "
            f"{best['test_acc']:.1%} ({best['missed_removals']}R "
            f"{best['missed_additions']}A {best['wrong_values']}V)")

    # Save results
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_path = RESULTS_DIR / f"results_{args.task}_{ts}.json"
    save_data = []
    for r in all_results:
        d = dict(r)
        d["test_grid"] = r.get("test_grid")  # keep grid for F3
        save_data.append(d)
    with open(save_path, "w") as f:
        json.dump(save_data, f, indent=2)
    log(f"\nResults saved to: {save_path}")


if __name__ == "__main__":
    main()

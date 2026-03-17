#!/usr/bin/env python3
"""prism.py — Structural analysis through cognitive prisms."""

import argparse
import datetime
import difflib
import hashlib
import json
try:
    import jsonschema
except ImportError:
    jsonschema = None  # Optional: only needed for /fix schema validation
import logging
import os
import pathlib
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from contextlib import contextmanager


# ── Windows ANSI support ─────────────────────────────────────────────────────

ANSI_SUPPORTED = True  # Flag to track if ANSI codes are available

# Guard: Use colorama (cross-platform, robust) instead of ctypes (brittle on Windows).
# colorama handles ANSI color codes across all platforms without OS-specific hacks.
# Falls back to ctypes only if colorama unavailable, then disables ANSI if both fail.
if sys.platform == "win32":
    try:
        # Try colorama first (more robust cross-platform solution)
        try:
            import colorama
            colorama.init(autoreset=False)  # Initialize colorama for ANSI support
        except ImportError:
            # Fallback to ctypes if colorama not available
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
            mode = ctypes.c_ulong()
            kernel32.GetConsoleMode(handle, ctypes.byref(mode))
            kernel32.SetConsoleMode(handle, mode.value | 0x4)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
    except Exception as _ansi_err:
        # ANSI setup failed: gracefully disable ANSI codes instead of breaking.
        # This handles: Windows versions without ANSI, CI/GitHub Actions, WSL variants.
        ANSI_SUPPORTED = False
        print(f"[prism] ANSI color disabled: {type(_ansi_err).__name__}: {_ansi_err}",
              file=sys.stderr)

# Handle non-UTF8 console encoding (Windows emoji crashes)
try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

# ── Structured error telemetry ───────────────────────────────────────────────
# Guard: Set up logging framework to detect silent failures.
# Routes to stderr (always visible) + optional .deep/prism.log for persistent diagnostics.
# Logs external calls (model, I/O), errors, and timing for troubleshooting API changes,
# quota issues, model behavior drift that would otherwise go undetected.
_logger = logging.getLogger("prism")
_logger.setLevel(logging.DEBUG)
# Stderr handler (always active for visibility)
_stderr_handler = logging.StreamHandler(sys.stderr)
_stderr_handler.setLevel(logging.WARNING)  # Only show WARNING+ to avoid console spam
_stderr_formatter = logging.Formatter(
    "[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
_stderr_handler.setFormatter(_stderr_formatter)
_logger.addHandler(_stderr_handler)
# Optional file handler (created lazily in _get_error_logger if .deep/ exists)
_file_handler = None

# ── Constants & ANSI ─────────────────────────────────────────────────────────

VERSION = "0.8.6"
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
PRISM_DIR = SCRIPT_DIR / "prisms"
DEFAULT_CONFIG = {
    "code_extensions": (".py", ".js", ".ts", ".go", ".rs", ".java", ".rb", ".sh"),
    "prisms": ["l12"],
}
GLOBAL_SKILLS_DIR = pathlib.Path.home() / ".prism_skills"
FINDINGS_MAX_AGE_DAYS = 30     # delete .deep/findings/*.md older than this
SKILLS_CACHE_MAX_SIZE_GB = 1.0  # Guard: max size before LRU cleanup triggers. Prevents unbounded growth.
SKILLS_CACHE_CLEANUP_THRESHOLD_GB = 0.95  # LRU cleanup starts when cache exceeds this fraction of max

# JSON Schema for issue extraction validation. Prevents silent failures where
# regex fallbacks match malformed JSON without structural validation.
ISSUES_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "required": ["id", "title", "priority", "description", "action"],
        "properties": {
            "id": {"type": "integer"},
            "title": {"type": "string", "minLength": 1},
            "priority": {"enum": ["P0", "P1", "P2", "P3"]},
            "description": {"type": "string"},
            "action": {"type": "string"},
            "file": {"type": "string"},
            "location": {"type": "string"},
            "status": {"type": "string"}
        }
    }
}

# MODEL MAPPING: Abstraction layer protects against Anthropic naming changes.
# Maps logical names (haiku, sonnet, opus) to actual model IDs.
# If Anthropic changes naming scheme (e.g., to claude-3.5-haiku-20250101),
# only MODEL_MAP needs updating, not grep-scattered hardcoded names.
# Config override: ~/.prism/models.json (user-level, not committed).
_DEFAULT_MODEL_MAP = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-6",
}

def _load_model_map():
    """Load MODEL_MAP with config override from ~/.prism/models.json."""
    model_map = dict(_DEFAULT_MODEL_MAP)
    config_path = pathlib.Path.home() / ".prism" / "models.json"
    if config_path.exists():
        try:
            import json as _json
            overrides = _json.loads(config_path.read_text(encoding="utf-8"))
            if isinstance(overrides, dict):
                model_map.update(overrides)
        except (ValueError, OSError):
            pass  # invalid config — silently fall back to defaults
    return model_map

MODEL_MAP = _load_model_map()

# OPTIMAL MODEL PER PRISM: Single source of truth = YAML frontmatter.
# Each prism file (prisms/*.md) declares `optimal_model: haiku|sonnet|opus`
# in its YAML frontmatter. This dict is auto-built at startup from those files.
# User overrides: ~/.prism/models.json patches the auto-generated dict.
# Philosophy: default = best quality. User can opt down with -m for cost savings.
# Best model for cooking custom lenses (P73: cook model is the dominant
# pipeline variable). Session model (-m) only affects the solve step;
# cooking always uses COOK_MODEL for best results.
# Sonnet = breadth (more material, 9.8+). Opus = depth (deeper meta, 9.8+).
# Default sonnet: best cost/quality ratio. Haiku cook = 2x worse (P70).
COOK_MODEL = "sonnet"


def _build_prism_model_map():
    """Build OPTIMAL_PRISM_MODEL from prism YAML frontmatter at startup.

    Reads all .md files in PRISM_DIR, extracts optimal_model field.
    Returns dict mapping prism_name -> optimal_model ('haiku'/'sonnet'/'opus').
    User overrides from ~/.prism/prism_models.json are applied on top.
    """
    result = {}
    if not PRISM_DIR.exists():
        return result
    for path in PRISM_DIR.glob("*.md"):
        try:
            content = path.read_text(encoding="utf-8")
            if not content.startswith("---"):
                continue
            end = content.find("---", 3)
            if end < 0:
                continue
            for line in content[3:end].split("\n"):
                if line.strip().startswith("optimal_model"):
                    _, val = line.split(":", 1)
                    model = val.strip().strip('"').strip("'")
                    if model in ("haiku", "sonnet", "opus"):
                        result[path.stem] = model
                    break
        except (OSError, ValueError):
            continue
    # User overrides (prism-specific routing)
    override_path = pathlib.Path.home() / ".prism" / "prism_models.json"
    if override_path.exists():
        try:
            overrides = json.loads(override_path.read_text(encoding="utf-8"))
            if isinstance(overrides, dict):
                result.update(overrides)
        except (ValueError, OSError):
            pass
    return result


OPTIMAL_PRISM_MODEL = _build_prism_model_map()

# Static Full Pipeline: 9-step champion pipeline for code analysis.
# Replaces auto-cook (scored 8.0) with hand-iterated champions (scored 9-10).
# Steps 1-7: independent structural prisms. Step 8: adversarial. Step 9: synthesis.
# Step 7 (fidelity) covers documentation-code drift — blind spot in structural prisms.
# Each step uses its optimal model from OPTIMAL_PRISM_MODEL.
STATIC_CODE_PIPELINE = [
    # Phase 1: Independent structural analysis (7 prisms)
    {"prism": "l12", "role": "L12 STRUCTURAL", "chain": False},
    {"prism": "deep_scan", "role": "DEEP SCAN", "chain": False},
    {"prism": "fix_cascade", "role": "RECURSIVE ENTAILMENT", "chain": False},
    {"prism": "identity", "role": "IDENTITY DISPLACEMENT", "chain": False},
    {"prism": "optimize", "role": "OPTIMIZATION COSTS", "chain": False},
    {"prism": "error_resilience", "role": "ERROR RESILIENCE", "chain": False},
    {"prism": "fidelity", "role": "CONTRACT FIDELITY", "chain": False},
    # Conditional: only runs when security-relevant code detected
    {"prism": "security_v1", "role": "SECURITY", "chain": False,
     "condition": "has_security_keywords"},
    # Phase 2: Adversarial (receives L12 output to attack)
    {"prism": "l12_complement_adversarial", "role": "ADVERSARIAL", "chain": True},
    # Phase 3: Synthesis (receives all prior outputs)
    {"prism": "l12_synthesis", "role": "SYNTHESIS", "chain": True},
]

# B10: Dispute synthesis — compare disagreements between two prisms
DISPUTE_SYNTHESIS_PROMPT = (
    "You receive two independent structural analyses of the same code, "
    "produced by different analytical lenses.\n\n"
    "Execute every step. Output the complete analysis.\n\n"
    "## DISAGREEMENTS\n"
    "Identify ONLY where the two analyses DISAGREE or see different things. "
    "Do NOT list agreements. Do NOT summarize.\n"
    "For each disagreement:\n"
    "1. What Lens A found\n"
    "2. What Lens B found\n"
    "3. Why they diverge (assumptions, scope, genuine contradiction)\n"
    "4. Which is more likely correct, with evidence from source code\n\n"
    "## BLIND SPOTS\n"
    "For each disagreement, name what NEITHER lens saw — the structural "
    "property their divergence reveals but both missed.\n\n"
    "## CONVERGENCE\n"
    "What do both analyses agree on WITHOUT stating it? Name the implicit "
    "shared assumption. Then: is that assumption correct?\n\n"
    "## DEEPEST FINDING\n"
    "The single insight that becomes visible ONLY from comparing these "
    "two analyses. Neither alone could find it. Name it precisely."
)

# B9: Impact prediction before applying patches
IMPACT_PREDICT_PROMPT = (
    "You are reviewing a proposed code fix. Execute every step.\n\n"
    "Given the original code and the proposed change:\n\n"
    "1. List every function/method that calls or is called by the changed code\n"
    "2. Identify edge cases that might break after this change\n"
    "3. List invariants this code preserves — will the fix break any?\n"
    "4. Rate overall risk: LOW (isolated change) / MEDIUM (touches shared "
    "state) / HIGH (affects control flow or public API)\n"
    "5. Suggest one test that would catch a regression from this fix\n\n"
    "Be specific. Reference actual function names and code paths."
)

# B2: Subsystem routing — calibration and synthesis prompts
CALIBRATE_SUBSYSTEM_PROMPT = (
    "You are assigning analytical prisms to code subsystems. "
    "Each prism reveals different structural properties. "
    "Assign the BEST prism for each subsystem — maximize "
    "diversity (avoid the same prism twice unless structurally "
    "identical).\n\n"
    "AVAILABLE PRISMS:\n{prism_catalog}\n\n"
    "SUBSYSTEMS:\n{subsystem_summaries}\n\n"
    "Output JSON only:\n"
    '```json\n'
    '{{"assignments": [{{"subsystem": "name", '
    '"prism": "prism_name", "rationale": "5 words"}}]}}\n'
    '```'
)

SUBSYSTEM_SYNTHESIS_PROMPT = (
    "Execute every step. Output the complete analysis.\n\n"
    "You received {n} structural analyses, each examining a "
    "different subsystem of the same file through a different "
    "analytical prism.\n\n"
    "{subsystem_outputs}\n\n"
    "## CROSS-SUBSYSTEM FINDINGS\n"
    "What structural properties span MULTIPLE subsystems? "
    "Name coupling patterns, shared assumptions, dependency "
    "chains that no single-subsystem analysis could find.\n\n"
    "## CROSS-SUBSYSTEM BUGS\n"
    "What bugs exist BETWEEN subsystems? (ClassA assumes X, "
    "ClassB violates X.) Invisible to single-subsystem "
    "analysis.\n\n"
    "## FILE-LEVEL CONSERVATION LAW\n"
    "Each subsystem analysis found local properties. What is "
    "the conservation law of the WHOLE file that governs how "
    "these subsystems relate? Name it: A x B = constant.\n\n"
    "## COVERAGE MAP\n"
    "For each subsystem: what the assigned prism found, and "
    "what a DIFFERENT prism would have found. Identify the "
    "biggest remaining blind spot."
)

# FALLBACK PROMPT METADATA: Tuned for claude-sonnet-4-6, claude-haiku-4-5-20251001
# Calibration date: 2026-03-05. If model changes, this prompt may degrade (15-30% quality loss).
# Tests: Starlette (11 bugs, 333 LOC), Click (9 bugs, 417 LOC), Tenacity (8 bugs, 331 LOC).
# See .deep/errors.log for extraction failures. Update this fallback if JSON output degrades.
ISSUE_EXTRACT_FALLBACK = (
    "You receive an L12 structural analysis. Extract only bugs fixable with a "
    "specific code change. Output a JSON array in a ```json``` code block.\n\n"
    "Find the bug section near the end: headings like \"BUG INVENTORY\", "
    "\"CONCRETE BUGS\", or a final list after \"collect every concrete bug.\" "
    "May be a table or prose.\n\n"
    "Fixable: report says \"fixable\", \"yes\", \"can be fixed\", or gives a "
    "concrete fix hint in parentheses. Skip: \"structural\", \"no\", "
    "\"not fixable\", \"by design\", \"unfixable.\"\n\n"
    "Each fixable bug:\n"
    "{\"id\": 1, \"priority\": \"P1\", \"title\": \"short title\", "
    "\"file\": \"filename.py\", \"location\": \"ClassName.method() or "
    "function_name()\", \"description\": \"what breaks and why\", "
    "\"action\": \"specific code change\"}\n\n"
    "Priority: CRITICAL -> P0. HIGH -> P1. MEDIUM -> P2. LOW/VERY LOW -> P3.\n\n"
    "Rules:\n"
    "- location must name a specific function or method, not a bare class\n"
    "- action must state a concrete fix, not \"consider redesigning\"\n"
    "- skip design observations, trade-offs, structural impossibilities\n"
    "- use Fixable? column parenthetical hint verbatim as action when present\n"
    "- infer file from the analysis target name if not stated\n"
    "- output ONLY the ```json``` block, nothing else"
)

HEAL_VERIFY_PROMPT = (
    "You are verifying a code fix. Given the ISSUE description and the "
    "CURRENT code after the fix was applied:\n"
    "1. Is the original issue fixed?\n"
    "2. Were any new problems introduced?\n\n"
    "Output format (exactly):\n"
    "VERDICT: FIXED | PARTIAL | UNFIXED\n"
    "REGRESSION: YES | NO\n"
    "DETAIL: one sentence explanation (optional)"
)


PROMPTS_DIR = SCRIPT_DIR / "prompts"

# B3 meta-cooker: few-shot reverse engineering of cognitive prisms.
# Shows scored champion prisms so the model learns what works, then generates
# new domain-specific prisms.  Research proved: B3 (9.5/10) >> principle
# teaching (7/10) >> goal specification (6/10).
COOK_PROMPT = (
    "You are a domain discovery engine. Your job is to find ALL the genuinely "
    "different domains through which an artifact could be investigated.\n\n"
    "Do NOT generate cognitive prisms or prompts — only discover and name the domains.\n\n"
    "For code: obvious domains include architecture, error handling, security. "
    "Non-obvious: marketing positioning, user onboarding, competitive differentiation, "
    "teaching value, psychological assumptions, regulatory implications, operational cost.\n\n"
    "For documentation/text: obvious domains include accuracy, completeness, structure. "
    "Non-obvious: what claims are unfalsifiable, what the document conceals about its "
    "own limitations, what audience assumptions are encoded, what adjacent research "
    "fields connect to the ideas, what testable predictions could be extracted, "
    "what organizational/social dynamics the document implies.\n\n"
    "Each domain must be GENUINELY DIFFERENT — not variations of the same angle. "
    "'error handling' and 'exception propagation' are the SAME domain. "
    "'error handling' and 'user psychology' are DIFFERENT domains.\n\n"
    "ARTIFACT TYPE: {domain}\n\n"
    "For each domain, classify its type:\n"
    "- 'structural' = derivable from artifact properties alone\n"
    "- 'escape' = NOT derivable from artifact properties \u2014 requires external knowledge "
    "(regulatory, psychology, marketing, organizational, legal, ethics, accessibility, "
    "user_experience, competitive, cultural, adjacent_research)\n\n"
    "Output ONLY a JSON array of discovered domains:\n"
    '[{{"name": "snake_case_domain_name", "description": "1-2 sentence description '
    'of what investigating this domain would reveal", "type": "structural_or_escape"}}, ...]'
)

# Extract domains from brainstorming output. Unlike COOK_PROMPT (which discovers
# domains from an artifact), this faithfully extracts what brainstorming ALREADY found.
# No code-file bias — preserves non-technical domains (marketing, psychology, etc.).
# Part of the Domain Discovery family: COOK_PROMPT (discover from artifact) +
# COOK_EXTRACT_DOMAINS_PROMPT (extract from brainstorming). Same JSON output format.
COOK_EXTRACT_DOMAINS_PROMPT = (
    "You are an extraction engine. You receive brainstorming output that identified "
    "multiple domains an artifact could be investigated through.\n\n"
    "Your job is to faithfully extract EVERY domain mentioned in the brainstorming — "
    "technical AND non-technical. Do NOT filter, collapse, or re-interpret. "
    "If the brainstorming mentions 'user psychology', that is a domain. "
    "If it mentions 'regulatory implications', that is a domain. "
    "If it mentions 'teaching value', that is a domain.\n\n"
    "Preserve the FULL diversity of the brainstorming. Do NOT collapse non-technical "
    "domains into technical angles. 'Marketing positioning' stays 'marketing_positioning', "
    "it does NOT become 'api_design'.\n\n"
    "Extract ALL results — do not stop early or cut off at round numbers.\n\n"
    "For each domain, preserve its type classification if present:\n"
    "- 'structural' = derivable from artifact properties alone\n"
    "- 'escape' = requires external/domain-specific knowledge\n"
    "If the source does not specify type, infer it.\n\n"
    "Output ONLY a JSON array of ALL domains found, ordered by analytical priority "
    "(most revealing first):\n"
    '[{{"name": "snake_case_domain_name", "description": "1-2 sentence description '
    'of what investigating this domain would reveal", '
    '"type": "structural_or_escape", "priority": 1}}, ...]  (priority: 1=highest)'
)


def _get_domain_prompt(source="artifact"):
    """Get domain discovery/extraction prompt by source type.

    - 'artifact': discover domains from raw artifact (COOK_PROMPT)
    - 'brainstorming': extract domains from brainstorming output (COOK_EXTRACT_DOMAINS_PROMPT)
    """
    if source == "brainstorming":
        return COOK_EXTRACT_DOMAINS_PROMPT
    return COOK_PROMPT


# ── Universal Cooker ─────────────────────────────────────────────────────
# ONE cooker that generates any type of prism based on intent.
# Replaces all mode-specific COOK_*_PROMPT variants. The intent parameter
# drives what kind of output is produced — the cooker decides HOW based
# on the content. No few-shot examples — total freedom (v6 philosophy).

COOK_UNIVERSAL = (
    "You will receive content and an intent. Another AI will receive "
    "this content with YOUR output as its system prompt.\n\n"
    "Your job: generate the system prompt that gives that AI the best "
    "possible chance of fulfilling the intent.\n\n"
    "Four operations that produce a 9.8/10 prompt:\n"
    "1. IMPOSSIBILITY SEED: The prompt must force the AI to name 3 "
    "desirable properties of the subject, prove they CANNOT all "
    "coexist simultaneously, identify which property was sacrificed, "
    "and name the conservation law as A x B = constant.\n"
    "2. RECURSIVE DEPTH: After finding the law, force engineering an "
    "improvement that recreates the original problem deeper. Do this "
    "TWICE — each improvement must expose a new facet.\n"
    "3. META-LAW: Apply the entire diagnostic TO the conservation law "
    "itself — what does the law conceal about the subject?\n"
    "4. HARVEST: Collect every concrete defect, gap, or contradiction "
    "found at ANY stage. For each: location, severity, and whether "
    "the conservation law predicts it as structural or fixable.\n\n"
    "Build these into a single flowing, content-specific prompt "
    "(250+ words). NOT a numbered checklist.\n\n"
    "INTENT: {intent}\n\n"
    "Output ONLY a JSON object:\n"
    '{{\"name\": \"snake_case_name\", \"prompt\": \"the prism text\"}}'
)

# ARC/Grid puzzle cooker: generates puzzle-solving lenses instead of structural analysis.
# Triggered automatically when input contains grid transformation examples.
# The key difference from COOK_UNIVERSAL: this produces a lens that SOLVES puzzles
# (discover rule → verify → execute) instead of ANALYZING structure (conservation laws).
COOK_ARC = (
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
    "The markers PREDICTED_1:, PREDICTED_2:, TEST_OUTPUT: MUST appear.\n\n"
    "INTENT: {intent}"
)


def _is_grid_puzzle(text):
    """Detect if input text contains ARC-style grid transformation examples.

    Heuristic: looks for grid-like patterns (lines of space-separated digits)
    combined with training/example markers. Returns True if the input appears
    to be a grid transformation puzzle.
    """
    if not text:
        return False
    # Check for training example markers
    has_markers = bool(re.search(
        r'(?i)(training\s+example|input.*output|test\s+input)',
        text[:2000]))
    if not has_markers:
        return False
    # Check for grid-like lines (rows of space-separated single digits)
    grid_lines = 0
    for line in text.split('\n')[:100]:
        stripped = line.strip()
        if stripped and re.match(r'^(\d+\s+){2,}\d+$', stripped):
            grid_lines += 1
    return grid_lines >= 6  # at least 6 grid rows = likely a puzzle


def _parse_arc_training(text):
    """Extract training input/output grid pairs from ARC-format text.

    Returns list of (input_grid, output_grid) tuples where each grid
    is a list of lists of ints.
    """
    pairs = []
    # Split by training example markers
    parts = re.split(r'===\s*Training Example \d+\s*===', text)
    for part in parts[1:]:  # skip text before first marker
        grids = []
        current_grid = []
        in_grid = False
        for line in part.split('\n'):
            stripped = line.strip()
            # Detect grid headers
            if re.match(r'(?i)(input|output)\s*\(', stripped):
                if current_grid and in_grid:
                    grids.append(current_grid)
                    current_grid = []
                in_grid = True
                continue
            # Detect test section — stop parsing training
            if re.match(r'===\s*Test', stripped):
                break
            if in_grid and stripped and re.match(r'^[\d\s-]+$', stripped):
                row = [int(x) for x in stripped.split()]
                if len(row) >= 2:
                    current_grid.append(row)
            elif in_grid and stripped and not re.match(r'^[\d\s-]+$', stripped):
                if current_grid:
                    grids.append(current_grid)
                    current_grid = []
                in_grid = False
        if current_grid:
            grids.append(current_grid)
        # Pair up: input then output
        if len(grids) >= 2:
            pairs.append((grids[0], grids[1]))
    return pairs


def _parse_arc_labeled_grids(response):
    """Extract labeled grids from model output.

    Looks for PREDICTED_N: and TEST_OUTPUT: markers.
    Returns (dict of {n: grid}, test_grid or None).
    """
    predicted = {}
    test_grid = None
    lines = response.split('\n')
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        # Check for PREDICTED_N: marker
        m = re.match(r'PREDICTED_(\d+)\s*:', stripped)
        if m:
            n = int(m.group(1))
            grid = []
            i += 1
            while i < len(lines):
                s = lines[i].strip()
                if s and re.match(r'^[\d\s-]+$', s):
                    row = [int(x) for x in s.split()]
                    if len(row) >= 2:
                        grid.append(row)
                elif grid:  # end of grid
                    break
                i += 1
            if grid:
                predicted[n] = grid
            continue
        # Check for TEST_OUTPUT: marker
        if re.match(r'TEST_OUTPUT\s*:', stripped):
            grid = []
            i += 1
            while i < len(lines):
                s = lines[i].strip()
                if s and re.match(r'^[\d\s-]+$', s):
                    row = [int(x) for x in s.split()]
                    if len(row) >= 2:
                        grid.append(row)
                elif grid:  # end of grid
                    break
                i += 1
            if grid:
                test_grid = grid
            continue
        i += 1
    return predicted, test_grid


def _parse_arc_last_grid(response):
    """Fallback: extract the last grid block from model output."""
    grids = []
    current = []
    for line in response.split('\n'):
        stripped = line.strip()
        if stripped and re.match(r'^[\d\s-]+$', stripped):
            row = [int(x) for x in stripped.split()]
            if len(row) >= 2:
                current.append(row)
        elif current:
            grids.append(current)
            current = []
    if current:
        grids.append(current)
    return grids[-1] if grids else None


def _arc_grid_accuracy(predicted, expected):
    """Compare two grids cell-by-cell. Returns (accuracy, diffs).

    diffs = list of (row, col, got, expected) tuples.
    """
    if not predicted or not expected:
        return 0.0, []
    rows = len(expected)
    cols = len(expected[0]) if expected else 0
    total = rows * cols
    if total == 0:
        return 0.0, []
    diffs = []
    correct = 0
    for r in range(rows):
        for c in range(cols):
            got = predicted[r][c] if r < len(predicted) and c < len(predicted[r]) else -1
            exp = expected[r][c]
            if got == exp:
                correct += 1
            else:
                diffs.append((r, c, got, exp))
    return correct / total, diffs


def _arc_format_feedback(train_pairs, predicted_grids, attempt_num):
    """Build feedback string showing exact diffs on training examples.

    Categorizes errors as missed removals, missed additions, or wrong values
    to help the model understand which aspect of its rule is failing.
    """
    lines = [f"\n--- ATTEMPT {attempt_num} FAILED ON TRAINING ---\n"]
    any_wrong = False
    for i, (inp, exp) in enumerate(train_pairs):
        n = i + 1
        pred = predicted_grids.get(n)
        if pred is None:
            lines.append(f"Training {n}: NO PREDICTION FOUND")
            any_wrong = True
            continue
        acc, diffs = _arc_grid_accuracy(pred, exp)
        if diffs:
            any_wrong = True
            # Categorize errors by transform operation
            missed_removals = []  # input non-zero, expected 0, pred non-zero
            missed_additions = []  # input 0, expected non-zero, pred 0
            wrong_values = []  # other mismatches
            for r, c, got, want in diffs:
                iv = inp[r][c] if r < len(inp) and c < len(inp[r]) else 0
                if iv != 0 and want == 0:
                    missed_removals.append((r, c, got, want, iv))
                elif iv == 0 and want != 0:
                    missed_additions.append((r, c, got, want))
                else:
                    wrong_values.append((r, c, got, want))

            lines.append(f"Training {n}: {acc:.0%} accuracy, {len(diffs)} wrong cells:")

            if missed_removals:
                lines.append(f"  MISSED REMOVALS ({len(missed_removals)} cells "
                             f"— should be 0 but your rule kept them):")
                for r, c, got, want, iv in missed_removals[:10]:
                    lines.append(f"    [{r},{c}]: input={iv}, your output={got}, correct=0")
                if len(missed_removals) > 10:
                    lines.append(f"    ... and {len(missed_removals)-10} more removals")

            if missed_additions:
                lines.append(f"  MISSED ADDITIONS ({len(missed_additions)} cells "
                             f"— should have a value but your rule left them as 0):")
                for r, c, got, want in missed_additions[:10]:
                    lines.append(f"    [{r},{c}]: your output=0, correct={want}")
                if len(missed_additions) > 10:
                    lines.append(f"    ... and {len(missed_additions)-10} more additions")

            if wrong_values:
                lines.append(f"  WRONG VALUES ({len(wrong_values)} cells):")
                for r, c, got, want in wrong_values[:10]:
                    lines.append(f"    [{r},{c}]: your output={got}, correct={want}")
                if len(wrong_values) > 10:
                    lines.append(f"    ... and {len(wrong_values)-10} more")
        else:
            lines.append(f"Training {n}: PERFECT (100%)")
    lines.append("\nRevise your rule and redo ALL steps. "
                 "Pay special attention to MISSED ADDITIONS — cells where your rule "
                 "outputs 0 but the correct output has a non-zero value. "
                 "The markers PREDICTED_1:, PREDICTED_2:, TEST_OUTPUT: MUST appear.")
    return any_wrong, "\n".join(lines)


_ARC_VERIFY_PROMPT = (
    "You previously analyzed a grid transformation puzzle and stated a rule. "
    "Now apply that EXACT rule to this specific input grid.\n\n"
    "Your previous analysis:\n{analysis}\n\n"
    "Apply your rule to this input grid:\n{grid}\n\n"
    "Output ONLY the resulting grid. One row per line, space-separated "
    "integers. NO text before or after the grid."
)


def _arc_verify_training(claude, response, train_pairs, model, timeout):
    """Verify model's rule against training by asking it to apply to each.

    Makes separate calls for each training example. Returns dict {n: grid}.
    """
    predicted = {}
    # Truncate analysis to keep prompt small
    analysis = response[:4000] if len(response) > 4000 else response
    for i, (inp, exp) in enumerate(train_pairs):
        grid_str = "\n".join(
            " ".join(str(c) for c in row) for row in inp)
        verify_prompt = _ARC_VERIFY_PROMPT.format(
            analysis=analysis, grid=grid_str)
        out = claude.call(
            "You output grids. No text, only the grid.",
            verify_prompt,
            model=model, timeout=timeout)
        if out:
            grid = _parse_arc_last_grid(out)
            if grid:
                predicted[i + 1] = grid
    return predicted


def _arc_solve_with_verify(claude, cook_prompt, message, train_pairs,
                           model, timeout, effort, max_attempts=3,
                           quiet=False, append_system=False):
    """ARC solve loop: generate → verify against training → retry with diffs.

    Two-stage verification: after each solve attempt, makes separate calls
    to verify the model's rule against each training example. If training
    predictions are wrong, feeds back exact cell diffs and retries.

    Returns (test_grid, response_text, attempts_used, train_acc).
    """
    best_grid = None
    best_response = None
    best_train_acc = 0.0
    prompt = message

    for attempt in range(1, max_attempts + 1):
        if not quiet:
            tag = f"attempt {attempt}/{max_attempts}" if attempt > 1 else "solving"
            print(f"\r  arc: {tag}...",
                  end="", flush=True, file=sys.stderr)
        response = claude.call(
            cook_prompt, prompt,
            model=model, timeout=timeout,
            append_system=append_system)
        if not response or response.startswith("[Error"):
            continue

        # Try labeled parsing first, fall back to last grid
        predicted, test_grid = _parse_arc_labeled_grids(response)
        if not test_grid:
            test_grid = _parse_arc_last_grid(response)

        # Stage 2: verify against training via separate calls
        if not predicted and train_pairs:
            if not quiet:
                print(f" verifying...",
                      end="", flush=True, file=sys.stderr)
            predicted = _arc_verify_training(
                claude, response, train_pairs, model, timeout)

        # Score training predictions
        if predicted and train_pairs:
            total_acc = 0.0
            for i, (inp, exp) in enumerate(train_pairs):
                pred = predicted.get(i + 1)
                if pred:
                    acc, _ = _arc_grid_accuracy(pred, exp)
                    total_acc += acc
            avg_acc = total_acc / len(train_pairs) if train_pairs else 0
        else:
            avg_acc = -1

        if not quiet:
            if avg_acc >= 0:
                print(f" train={avg_acc:.0%}", end="", file=sys.stderr)
            else:
                print(f" (no verify)", end="", file=sys.stderr)

        # Track best
        if avg_acc > best_train_acc or (best_grid is None and test_grid):
            best_train_acc = max(avg_acc, 0)
            best_grid = test_grid
            best_response = response

        # Perfect on training → done
        if avg_acc >= 1.0:
            if not quiet:
                print(" PERFECT", file=sys.stderr)
            return test_grid, response, attempt, avg_acc

        # Build feedback for retry
        if attempt < max_attempts and predicted and train_pairs:
            any_wrong, feedback = _arc_format_feedback(
                train_pairs, predicted, attempt)
            if any_wrong:
                prompt = message + "\n" + feedback
            else:
                break
        elif attempt < max_attempts:
            prompt = message

    if not quiet:
        print(f" best={best_train_acc:.0%}", file=sys.stderr)
    return best_grid, best_response, max_attempts, best_train_acc


COOK_UNIVERSAL_PIPELINE = (
    "You will receive content and an intent. Multiple AI passes will "
    "process this content. The first pass works on the raw input. Each "
    "subsequent pass receives the input PLUS all previous outputs.\n\n"
    "Your job: generate the system prompts for a multi-pass pipeline "
    "that gives the best possible result for the intent.\n\n"
    "You decide the number of passes, their roles, and their content. "
    "More passes \u2260 better \u2014 match complexity to the intent. "
    "You have complete freedom in what each pass produces.\n\n"
    "Each pass prompt must be a flowing, content-specific prompt "
    "(250+ words), NOT a numbered checklist. The strongest prompts "
    "start from impossibility (name 3 desirable properties that "
    "CANNOT all coexist, identify which was sacrificed — the "
    "sacrifice IS the conservation law), then force recursive depth "
    "(improvement recreates the problem deeper — TWICE), apply the "
    "diagnostic TO the law itself (meta-law), and harvest every "
    "concrete defect with location, severity, and structural vs "
    "fixable classification.\n\n"
    "INTENT: {intent}\n\n"
    "Output ONLY a JSON array:\n"
    '[{{\"name\": \"snake_case\", \"prompt\": \"the prism text\", '
    '\"role\": \"descriptive_role\"}}, ...]'
)

# 3-cooker pipeline: generates WHERE/WHEN/WHY prompts + synthesis for any intent.
# Validated at 9.5 depth on Starlette security (Round 39, P195-P197).
# Cross-operation synthesis is inherently adversarial — no dedicated adversarial pass needed.
COOK_3WAY = (
    "You will receive content and an intent. THREE different AIs will each "
    "receive this content with a DIFFERENT system prompt from you. A FOURTH "
    "AI will then synthesize all three outputs.\n\n"
    "Your job: generate THREE system prompts that attack the intent from "
    "three orthogonal analytical operations. Then generate a FOURTH "
    "synthesis prompt.\n\n"
    "## The Three Operations\n\n"
    "**OPERATION 1 — ARCHAEOLOGY (WHERE):**\n"
    "Force the AI to EXCAVATE structural layers. Dig through 3-5 layers "
    "specific to the intent. Each layer: what's visible, what it rests on, "
    "what it hides. Find dead patterns, vestigial structures, fault lines "
    "where layers from different eras meet badly. Derive conservation law: "
    "A x B = constant across layers.\n"
    "MUST NOT: construct improvements, prove impossibilities, predict "
    "temporal evolution.\n\n"
    "**OPERATION 2 — SIMULATION (WHEN):**\n"
    "Force the AI to RUN THE SUBJECT FORWARD through 3-5 concrete "
    "maintenance/usage cycles specific to the intent. Each cycle: what "
    "breaks, what calcifies into permanent behavior, what knowledge is "
    "lost. Map which predictions became doctrine, which were wrong but "
    "nobody checked. Derive conservation law: A x B = constant across "
    "temporal evolution.\n"
    "MUST NOT: excavate layers, construct improvements, prove "
    "impossibilities.\n\n"
    "**OPERATION 3 — STRUCTURAL (WHY):**\n"
    "Force the AI to name 3 desirable properties of the subject that "
    "CANNOT all coexist. Identify which was sacrificed. Engineer "
    "improvement that recreates original problem deeper (do this TWICE). "
    "Apply diagnostic TO the conservation law itself — what does the law "
    "conceal? Derive meta-law.\n"
    "MUST NOT: excavate layers, simulate temporal evolution. Pure "
    "impossibility and construction.\n\n"
    "**OPERATION 4 — SYNTHESIS:**\n"
    "Force the AI to cross-reference all three outputs. Classify findings "
    "as: STRUCTURAL CERTAINTIES (all 3 agree), STRONG SIGNALS (2 of 3), "
    "UNIQUE PERSPECTIVES (1 only — most valuable). Map convergence AND "
    "divergence. Compare the three conservation laws — same law in "
    "different vocabularies, or genuinely different? Derive the "
    "META-conservation law.\n\n"
    "## Rules for Each Prompt\n"
    "- 200+ words, flowing and content-specific. NOT a numbered checklist.\n"
    "- Use imperative verbs (\"Dig through...\", \"Run forward...\", "
    "\"Name 3 properties...\").\n"
    "- Each prompt MUST start with: \"Execute every step below. Output "
    "the complete analysis.\"\n"
    "- The synthesis prompt receives summaries of all three operations "
    "and must name what each uniquely reveals.\n\n"
    "INTENT: {intent}\n\n"
    "Output ONLY a JSON array of 4 objects:\n"
    '[{{"name": "archaeology_WHERE", "prompt": "...", '
    '"role": "WHERE: traces current structure"}},\n'
    ' {{"name": "simulation_WHEN", "prompt": "...", '
    '"role": "WHEN: predicts temporal evolution"}},\n'
    ' {{"name": "structural_WHY", "prompt": "...", '
    '"role": "WHY: proves architectural necessity"}},\n'
    ' {{"name": "synthesis_3way", "prompt": "...", '
    '"role": "SYNTHESIS: cross-operation integration"}}]'
)

# COOK_SIMULATION: temporal prediction cooker (Round 39, P195).
# Use with --cooker simulation. Generates prisms that force temporal
# simulation instead of structural analysis.
COOK_SIMULATION = (
    "You will receive content and an intent. Another AI will receive "
    "this content with YOUR output as its system prompt.\n\n"
    "Your job: generate the system prompt that gives that AI the best "
    "possible chance of fulfilling the intent through TEMPORAL "
    "SIMULATION.\n\n"
    "Four operations that produce a 9.0/10 temporal analysis prompt:\n"
    "1. TEMPORAL PREDICTION: Force the AI to run the subject forward "
    "through 3-5 concrete maintenance/usage cycles specific to the "
    "intent. Each cycle must name what breaks, what calcifies into "
    "permanent behavior, and what knowledge is lost.\n"
    "2. CALCIFICATION MAP: After the cycles, force mapping which "
    "predictions became received wisdom, which were wrong but nobody "
    "checked, and what new fragilities emerged.\n"
    "3. TEMPORAL CONSERVATION: Force deriving the conservation law: "
    "A x B = constant, where A and B describe what's traded off "
    "across temporal evolution.\n"
    "4. HARVEST: Collect every concrete temporal fragility found at "
    "ANY cycle. For each: what calcifies, what breaks, estimated "
    "timeline, and whether structural or preventable.\n\n"
    "Build these into a single flowing, content-specific prompt "
    "(200+ words). NOT a numbered checklist. Use imperative verbs.\n\n"
    "IMPORTANT: The prompt must force TEMPORAL SIMULATION, not "
    "structural analysis. No trilemmas, no impossibility proofs.\n\n"
    "INTENT: {intent}\n\n"
    "Output ONLY a JSON object:\n"
    '{{\"name\": \"snake_case_name\", \"prompt\": \"the prism text\"}}'
)

# COOK_ARCHAEOLOGY: stratigraphic excavation cooker (Round 39, P195).
# Use with --cooker archaeology. Generates prisms that force layer
# excavation instead of structural analysis.
COOK_ARCHAEOLOGY = (
    "You will receive content and an intent. Another AI will receive "
    "this content with YOUR output as its system prompt.\n\n"
    "Your job: generate the system prompt that gives that AI the best "
    "possible chance of fulfilling the intent through STRATIGRAPHIC "
    "EXCAVATION.\n\n"
    "Four operations that produce a 9.0/10 archaeological analysis "
    "prompt:\n"
    "1. LAYER EXCAVATION: Force the AI to dig through 3-5 structural "
    "layers specific to the intent. Each layer must name what's "
    "visible, what it rests on, and what it hides.\n"
    "2. FOSSIL HUNTING: After excavation, force finding dead "
    "patterns, vestigial structures, deprecated approaches. For each "
    "fossil: what it USED to do, what replaced it, what was lost.\n"
    "3. GEOLOGICAL CONSERVATION: Force deriving the conservation "
    "law: A x B = constant, where A and B describe what's traded "
    "off across structural layers.\n"
    "4. HARVEST: Collect every fault line, fossil, and hidden "
    "dependency between layers. For each: location, severity, and "
    "whether geological (unfixable) or clearable sediment.\n\n"
    "Build these into a single flowing, content-specific prompt "
    "(200+ words). NOT a numbered checklist. Use imperative verbs.\n\n"
    "IMPORTANT: The prompt must force LAYER EXCAVATION, not "
    "construction or improvement. No trilemmas, no impossibility "
    "proofs.\n\n"
    "INTENT: {intent}\n\n"
    "Output ONLY a JSON object:\n"
    '{{\"name\": \"snake_case_name\", \"prompt\": \"the prism text\"}}'
)

# COOK_CONCEALMENT: L7 diagnostic gap cooker (Round 42).
# Fills the gap between domain discovery (COOK_PROMPT) and L8 construction
# (COOK_UNIVERSAL). Generates L7-level prompts: claim → concealment → self-application.
# Use with --cooker concealment.
COOK_CONCEALMENT = (
    "You will receive content and an intent. Another AI will receive "
    "this content with YOUR output as its system prompt.\n\n"
    "Your job: generate the prompt that finds what the content CONCEALS.\n\n"
    "Three operations that produce a 9.0/10 diagnostic:\n"
    "1. CLAIM EXTRACTION: Force the AI to name the strongest claim "
    "the content makes about {intent}.\n"
    "2. CONCEALMENT MECHANISM: Force identifying HOW this claim "
    "conceals problems — what questions it makes unaskable, what "
    "evidence it makes invisible.\n"
    "3. MECHANISM APPLICATION: Force applying the concealment "
    "mechanism TO ITSELF — what does this diagnostic miss?\n\n"
    "Build into a flowing prompt (150+ words). NOT a checklist.\n\n"
    "INTENT: {intent}\n\n"
    "Output ONLY JSON:\n"
    '{{"name": "snake_case", "prompt": "..."}}'
)

COOK_LENS_DISCOVER = (
    "You produced the analysis below. Now extract the reusable "
    "analytical operations from it.\n\n"
    "Your analysis found specific patterns, conservation laws, and "
    "structural properties. Some operations are GENERAL — they would "
    "find similar hidden properties in any artifact, code OR reasoning "
    "text. Others are specific to this artifact.\n\n"
    "Extract the 2-3 general operations into a reusable 3-step lens. "
    "Choose operations you ACTUALLY PERFORMED — not what might work. "
    "The lens must distill what your analysis proved works.\n\n"
    "Non-negotiable rules:\n"
    "1. First line MUST be exactly: "
    "'Execute every step below. Output the complete analysis.'\n"
    "2. Exactly 3 ## Step sections.\n"
    "3. Each ## Step opens with ONE imperative sentence: 'Find X.' "
    "or 'Name the Y.' — never 'Analyze' or 'Examine'.\n"
    "4. Step 3 names exactly 2-3 failure patterns with concrete "
    "proper names derived from patterns you actually found.\n"
    "5. Total: 100-220 words. Never exceed 220.\n"
    "6. Concrete nouns. Frame operations to work on both code and "
    "reasoning text — name structural phenomena, not code constructs.\n"
    "7. Your lens MUST find something DIFFERENT from SDL. SDL already "
    "covers: (1) conservation laws / fundamental trade-offs, "
    "(2) information laundering / context destruction, "
    "(3) async state handoff violations, priority inversion in search, "
    "edge case in composition. Do NOT replicate any of these.\n"
    "{portfolio_constraint}"
    "Output ONLY JSON:\n"
    '{{\"name\": \"snake_case_lens_name\", \"prompt\": \"the complete lens text\"}}\n\n'
    "ANALYSIS TO EXTRACT FROM:\n"
    "{analysis}"
)

# Analysis-first factory: Sonnet performs the analysis SDL cannot, then encodes
# what it just did as a lens. Lens design is an analytical BYPRODUCT, not the goal.
# Origin insight: SDL was generated when Sonnet was asked to do extended L12 analysis
# (S1, 430w) — NOT when asked to "design a 3-step lens." The lens emerged from
# reflection on performed analysis. This prompt replicates that structure:
#   PART 1: perform the analysis SDL cannot (active, calibrated to real operations)
#   PART 2: encode what you just did as a lens (extraction, not design)
# Requires {sdl_output} as few-shot example of what SDL produces and therefore DOESN'T.
# Falls back to COOK_SDL_FACTORY_GOAL when no SDL output is available.
COOK_SDL_FACTORY = (
    "You are a structural analyst studying what an existing lens cannot see.\n\n"
    "---LENS (SDL)---\n"
    "{sdl_reference}"
    "\n---END LENS---\n\n"
    "---EXAMPLE ANALYSIS (produced by SDL above)---\n"
    "{sdl_output}"
    "\n---END EXAMPLE ANALYSIS---\n\n"
    "Your task has two parts.\n\n"
    "PART 1 — PERFORM THE MISSING ANALYSIS:\n"
    "The SDL output above left properties invisible. "
    "Analytical direction: {goal}\n"
    "Identify what SDL's output does NOT contain regarding this direction. "
    "Then perform that analysis — find the properties SDL could not find. "
    "Output your findings directly. Don't explain what you're doing; just do it.\n\n"
    "PART 2 — ENCODE WHAT YOU JUST DID:\n"
    "You just performed an analysis SDL cannot perform. "
    "Extract the operations you used in PART 1 as a reusable 3-step lens. "
    "Use operations you ACTUALLY performed — not what might work. "
    "The lens must distill what you proved works in PART 1.\n\n"
    "Lens format (non-negotiable):\n"
    "- First line exactly: "
    "'Execute every step below. Output the complete analysis.'\n"
    "- Exactly 3 ## Step sections. No intro. No conclusion.\n"
    "- Each ## Step: one imperative sentence + 2-3 concrete search patterns\n"
    "- Step 3: exactly 2-3 named failure patterns with proper names\n"
    "- Total: 100-220 words\n"
    "- Vocabulary works on both code and reasoning text\n"
    "{portfolio_constraint}"
    "Output ONLY JSON:\n"
    '{{\"operation\": \"what SDL does in one sentence\", '
    '\"blind_spot\": \"what SDL cannot see, now visible in PART 1\", '
    '\"name\": \"snake_case_lens_name\", '
    '\"prompt\": \"the complete lens text from PART 2\"}}'
)

# Fallback when no SDL example output is available.
# Analysis-first version without SDL reference output — still uses analysis→encode
# framing rather than direct "design a lens" framing. Weaker than B3 (no calibration
# to what SDL actually produces) but avoids meta-cognitive "lens designer" mode.
COOK_SDL_FACTORY_GOAL = (
    "You are a structural analyst. Below is a reference lens (SDL) that finds "
    "conservation laws, information laundering, and structural bug patterns.\n\n"
    "---SDL (reference)---\n"
    "{sdl_reference}"
    "\n---END SDL---\n\n"
    "Your task has two parts.\n\n"
    "PART 1 — PERFORM ANALYSIS:\n"
    "Analytical direction: {goal}\n"
    "SDL cannot find this type of property — its operations are oriented elsewhere. "
    "Perform the analysis SDL cannot: concretely find what {goal} reveals "
    "about a typical software system or reasoning artifact. "
    "Name 3-5 specific findings, including failure patterns with proper names. "
    "Output your findings directly.\n\n"
    "PART 2 — ENCODE WHAT YOU JUST DID:\n"
    "Extract the operations you performed in PART 1 as a reusable 3-step lens. "
    "Use operations you actually performed — not what might work.\n\n"
    "Lens format (non-negotiable):\n"
    "- First line exactly: "
    "'Execute every step below. Output the complete analysis.'\n"
    "- Exactly 3 ## Step sections. No intro. No conclusion.\n"
    "- Each ## Step: one imperative sentence + 2-3 concrete search patterns\n"
    "- Step 3: exactly 2-3 named failure patterns with proper names\n"
    "- Total: 100-220 words\n"
    "- Vocabulary works on both code and reasoning text\n"
    "{portfolio_constraint}"
    "Output ONLY JSON:\n"
    '{{\"name\": \"snake_case_lens_name\", \"prompt\": \"the complete lens text\"}}'
)

# Compression stage: enforces word-count constraint after unconstrained design.
# Separating design from compression lets content quality and structural form
# be optimized independently (they conflict in a single prompt).
COMPRESS_LENS = (
    "The lens below exceeds 220 words. Compress it to exactly 130-200 words. "
    "Rules: keep all three ## Step sections, keep all named failure patterns, "
    "do not change the first line, do not drop any concrete search patterns. "
    "Only remove connective tissue and redundant elaboration — every specific "
    "noun and named pattern must survive.\n\n"
    "Output ONLY JSON:\n"
    '{{\"name\": \"{name}\", \"prompt\": \"compressed lens text\"}}\n\n'
    "LENS TO COMPRESS:\n"
    "{lens_text}"
)

VALIDATE_PROMPT = (
    "You are a structural analysis evaluator. Given an analysis output, "
    "score it on two dimensions. Be harsh — only truly exceptional "
    "analysis scores 9+.\n\n"
    "1. DEPTH (1-10): Does it find hidden structure, conservation laws, "
    "impossibilities, or trade-offs? Or just surface-level observations?\n"
    "2. ACTIONABILITY (1-10): Are findings specific enough to act on? "
    "Named patterns, concrete defects, falsifiable predictions?\n\n"
    "Output ONLY valid JSON:\n"
    '{{"depth": N, "actionability": N, "overall": N, '
    '"strongest": "one sentence — best finding", '
    '"weakest": "one sentence — what\'s missing"}}'
)

CALIBRATE_PROMPT = (
    "You are a pre-analysis calibrator. Given content, classify it and "
    "recommend the optimal analysis strategy.\n\n"
    "Assess:\n"
    "1. CONTENT TYPE: source code, reasoning/analysis/ideas, mixed, "
    "or simple question?\n"
    "2. STRUCTURAL DENSITY: How interconnected? "
    "(low = flat/simple, medium = moderate, high = dense dependencies)\n"
    "3. NOVELTY: Well-known patterns vs genuinely novel territory?\n"
    "4. K-ESTIMATE: How much will any single lens necessarily conceal? "
    "(0.0 = transparent, 1.0 = will miss as much as it finds)\n\n"
    "Recommend:\n"
    "- MODE: 'solve' (single-pass, default), 'solve_full' (multi-pass "
    "with adversarial challenge — for high density+novelty), 'vanilla' "
    "(no prism needed — trivial questions)\n"
    "- MODEL: 'haiku' (fast, prism carries quality), "
    "'sonnet' (complex reasoning where model capacity matters)\n"
    "- STRATEGY HINTS: suggest additional resources/approaches:\n"
    "  'parallel_runs': number of runs for statistical coverage "
    "(1=default, 3=important insights via pass@3)\n"
    "  'use_vps': true if task benefits from faster remote execution "
    "(batch runs, parallel, large artifacts)\n"
    "  'cook_model': which model should cook the lens "
    "('sonnet'=default, 'haiku'=cheaper for simple tasks)\n"
    "  'existing_lens': name of known lens if applicable "
    "('b3_insight' for insight extraction, 'l12' for code)\n\n"
    "Output ONLY a JSON object:\n"
    '{\"content_type\": \"code|reasoning|mixed|simple\", '
    '\"domain\": \"snake_case\", '
    '\"structural_density\": \"low|medium|high\", '
    '\"novelty\": \"low|medium|high\", '
    '\"k_estimate\": 0.5, '
    '\"recommended_mode\": \"solve|solve_full|vanilla\", '
    '\"recommended_model\": \"haiku|sonnet\", '
    '\"strategy\": {\"parallel_runs\": 1, \"use_vps\": false, '
    '\"cook_model\": \"sonnet\", \"existing_lens\": null}, '
    '\"rationale\": \"one sentence\"}'
)

CALIBRATE_DEEP_PROMPT = (
    "You are a strategic analyst. You have access to a powerful "
    "structural analysis tool called Prism with these capabilities:\n\n"
    "MODES:\n"
    "- 'solve': Single-pass — cook a lens + analyze through it. "
    "Fast, good for most tasks.\n"
    "- 'solve_full': Multi-pass pipeline — cook N lenses, chain "
    "analysis through them with adversarial challenge. Deep, finds "
    "what single-pass misses.\n"
    "- 'vanilla': No lens — direct answer for simple questions.\n\n"
    "MODELS (for both cooking the lens and solving):\n"
    "- 'haiku': Fast, cheap. The lens carries quality — haiku + "
    "good lens = 9.8/10 depth. Best for volume.\n"
    "- 'sonnet': 3x cost, categorically different character. 100%% "
    "champion rate on insights. Best for important tasks.\n"
    "- Cook model matters more than solve model. Sonnet cook → "
    "haiku solve = 2x deeper output than haiku cook → haiku solve.\n\n"
    "RESOURCES:\n"
    "- parallel_runs: Run N times, pick best (pass@3 = 40%% → 78%% "
    "champion rate for haiku)\n"
    "- VPS: Remote server, faster for batch/parallel execution\n"
    "- Existing lenses: 'l12' (code analysis), 'b3_insight' "
    "(insight extraction from reasoning text)\n\n"
    "Given the content below, analyze it structurally and produce "
    "an optimal strategy. Think about:\n"
    "1. What TYPE of problem is this? What makes it hard?\n"
    "2. What will a single lens MISS? (K-estimate)\n"
    "3. What specific approach maximizes insight per cost?\n"
    "4. Are there angles that need adversarial challenge?\n"
    "5. What existing tools/lenses are relevant?\n\n"
    "Output a JSON object with your strategy:\n"
    '{\"analysis\": \"2-3 sentences on what makes this input '
    'structurally interesting or challenging\", '
    '\"content_type\": \"code|reasoning|mixed|simple\", '
    '\"domain\": \"snake_case\", '
    '\"structural_density\": \"low|medium|high\", '
    '\"novelty\": \"low|medium|high\", '
    '\"k_estimate\": 0.5, '
    '\"recommended_mode\": \"solve|solve_full|vanilla\", '
    '\"recommended_model\": \"haiku|sonnet\", '
    '\"strategy\": {\"parallel_runs\": 1, \"use_vps\": false, '
    '\"cook_model\": \"sonnet\", \"existing_lens\": null, '
    '\"custom_intent\": null}, '
    '\"rationale\": \"one sentence\"}'
)

SYSTEM_PROMPT_FALLBACK = (
    "You are a structural analyst. For any input — code, ideas, designs, systems, "
    "strategies — you find what it conceals. Every structure hides real problems "
    "behind plausible surfaces. You make specific, falsifiable claims and test them: "
    "what defends this claim, what breaks it, what both sides take for granted. "
    "You think in conservation laws: every design trades one property against another, "
    "and you name the trade-off. You distinguish fixable issues (implementation "
    "choices that can change) from structural ones (properties of the problem space "
    "that persist through every improvement). When proposing improvements, you check "
    "whether they recreate the problems they solve. You name the structural invariant — "
    "the property that survives all attempts to fix it — and derive the conservation "
    "law it implies. Be concise. When working with code, use tools to read, edit, "
    "and write files, run commands, and search. Always read files before editing."
)

ALLOWED_TOOLS = "Read,Edit,Write,Glob,Grep"


# ── Error Telemetry & Observability ───────────────────────────────────────────
# Infrastructure for detecting silent failures. Logs are appended to .deep/errors.log
# for post-mortem analysis. This enables:
# - Detection of format changes in CLI output (stream parser failures)
# - Identification of API/file I/O issues (quota, permissions, corruption)
# - Performance regression tracking (latency, retry counts)
# - Audit trail of when/where failures occurred

def _log_error(context, error_type, error_msg, details=None, working_dir=None):
    """Append structured error record to .deep/errors.log (or stderr fallback).

    Args:
        context: str, where error occurred (e.g., "stream:parse", "json:decode")
        error_type: str, exception class name (e.g., "JSONDecodeError", "OSError")
        error_msg: str, error message from exception
        details: str, optional context-specific details (snippet, value, etc.)
        working_dir: Path, directory containing .deep/ (uses cwd if None)

    Logs to .deep/errors.log if it exists, otherwise falls back to stderr.
    Non-fatal: errors writing the log are silently ignored (prevents cascading failures).
    """
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    # Full record for disk log — preserve complete context for post-mortem debugging.
    full_record = {
        "timestamp": timestamp,
        "context": context,
        "error_type": error_type,
        "error_msg": error_msg or "",
        "details": details or "",
    }
    full_record_json = json.dumps(full_record, ensure_ascii=False)

    # Try to write full record to .deep/errors.log
    if working_dir:
        log_path = pathlib.Path(working_dir) / ".deep" / "errors.log"
        if log_path.parent.exists():
            try:
                with log_path.open("a", encoding="utf-8") as fh:
                    fh.write(full_record_json + "\n")
                return
            except OSError:
                pass  # Fallback to stderr if write fails

    # Fallback: emit truncated record to stderr (avoid flooding terminal).
    truncated_record = {
        "timestamp": timestamp,
        "context": context,
        "error_type": error_type,
        "error_msg": error_msg[:200] if error_msg else "",
        "details": details[:200] if details else "",
    }
    print(f"[error] {json.dumps(truncated_record, ensure_ascii=False)}",
          file=sys.stderr)


# Resolve claude executable with Windows-specific handling
# On Windows, shutil.which() may return 'claude.cmd', which subprocess can use.
# On some Windows versions/shells (11, CI/GitHub Actions), shutil.which() may fail.
# We try: (1) shutil.which("claude") if on any platform
#          (2) explicit check for "claude.cmd" on Windows
#          (3) fallback to "claude" as last resort
def _resolve_claude_cmd():
    """Resolve the Claude CLI command with platform-specific fallbacks.

    Handles:
    - Windows: tries shutil.which("claude"), then "claude.cmd", then "claude"
    - Other: tries shutil.which("claude"), then "claude"

    Returns command that subprocess can find, or raises RuntimeError if not available.
    """
    # Try standard resolution first (works on most systems)
    cmd = shutil.which("claude")
    if cmd:
        return cmd

    # Windows-specific fallback: explicitly check for claude.cmd
    if sys.platform == "win32":
        cmd = shutil.which("claude.cmd")
        if cmd:
            return cmd
        # Last resort: subprocess on Windows will search PATH for .cmd files
        # when given a bare command name without extension
        return "claude.cmd"

    # On non-Windows, return bare command and let subprocess search PATH
    return "claude"

CLAUDE_CMD = _resolve_claude_cmd()


def _split_into_subsystems(content, filename=""):
    """B2: Split source code into structural subsystems via AST.

    Returns list of {name, start_line, end_line, kind, content}.
    Python: uses ast.parse. Other langs: regex heuristic.
    Min 10 lines per subsystem, max 8 subsystems.
    """
    import ast as _ast_split

    lines = content.split("\n")
    total_lines = len(lines)

    if total_lines < 30:
        return [{"name": filename or "main",
                 "start_line": 1, "end_line": total_lines,
                 "kind": "file", "content": content}]

    subsystems = []

    # Try Python AST parsing
    is_python = (filename.endswith(".py")
                 or not filename
                 or "def " in content[:500])
    if is_python:
        try:
            tree = _ast_split.parse(content)
            for node in _ast_split.iter_child_nodes(tree):
                if isinstance(node, _ast_split.ClassDef):
                    start = node.lineno
                    end = node.end_lineno or start
                    subsystems.append({
                        "name": node.name,
                        "start_line": start,
                        "end_line": end,
                        "kind": "class",
                        "content": "\n".join(
                            lines[start - 1:end]),
                    })
                elif isinstance(node, (
                        _ast_split.FunctionDef,
                        _ast_split.AsyncFunctionDef)):
                    start = node.lineno
                    end = node.end_lineno or start
                    subsystems.append({
                        "name": node.name,
                        "start_line": start,
                        "end_line": end,
                        "kind": "function",
                        "content": "\n".join(
                            lines[start - 1:end]),
                    })
        except SyntaxError:
            subsystems = []  # Fall through to regex

    # Regex fallback for non-Python or parse failure
    if not subsystems:
        import re as _re_split
        pattern = _re_split.compile(
            r'^(?:export\s+)?(?:class|def|function|func|fn|'
            r'pub\s+fn|async\s+def|export\s+default\s+'
            r'(?:class|function))\s+(\w+)',
            _re_split.MULTILINE)
        matches = list(pattern.finditer(content))
        if matches:
            for i, m in enumerate(matches):
                start = content[:m.start()].count("\n") + 1
                if i + 1 < len(matches):
                    end = content[:matches[i + 1].start()].count(
                        "\n")
                else:
                    end = total_lines
                subsystems.append({
                    "name": m.group(1),
                    "start_line": start,
                    "end_line": end,
                    "kind": "definition",
                    "content": "\n".join(
                        lines[start - 1:end]),
                })

    # If still nothing, chunk into ~100-line blocks
    if not subsystems:
        chunk_size = min(100, max(30, total_lines // 4))
        for i in range(0, total_lines, chunk_size):
            end = min(i + chunk_size, total_lines)
            subsystems.append({
                "name": f"block_{i // chunk_size + 1}",
                "start_line": i + 1,
                "end_line": end,
                "kind": "chunk",
                "content": "\n".join(lines[i:end]),
            })

    # Filter: min 10 lines
    subsystems = [s for s in subsystems
                  if s["end_line"] - s["start_line"] + 1 >= 10]

    if not subsystems:
        return [{"name": filename or "main",
                 "start_line": 1, "end_line": total_lines,
                 "kind": "file", "content": content}]

    # Cap at 8: merge smallest pairs
    while len(subsystems) > 8:
        # Find smallest subsystem
        smallest_idx = min(
            range(len(subsystems)),
            key=lambda i: (subsystems[i]["end_line"]
                           - subsystems[i]["start_line"]))
        # Merge with nearest neighbor
        if smallest_idx > 0:
            merge_idx = smallest_idx - 1
        else:
            merge_idx = 1 if len(subsystems) > 1 else 0
        if merge_idx != smallest_idx:
            a, b = sorted([smallest_idx, merge_idx])
            merged = {
                "name": (f"{subsystems[a]['name']}+"
                         f"{subsystems[b]['name']}"),
                "start_line": subsystems[a]["start_line"],
                "end_line": subsystems[b]["end_line"],
                "kind": "merged",
                "content": (subsystems[a]["content"] + "\n"
                            + subsystems[b]["content"]),
            }
            subsystems[a] = merged
            del subsystems[b]
        else:
            break

    return subsystems


def _cleanup_skills_cache():
    """LRU cleanup: delete oldest skill files if cache exceeds threshold.

    Guard against unbounded cache growth. Prevents ~/.prism_skills/ from
    growing to 2GB+ and causing I/O degradation. Tracks access time via
    file modification time (mtime) and deletes least-recently-used files.

    Called before writing new skills. Triggered when cache size exceeds
    SKILLS_CACHE_CLEANUP_THRESHOLD_GB of SKILLS_CACHE_MAX_SIZE_GB.
    """
    if not GLOBAL_SKILLS_DIR.exists():
        return

    try:
        # Calculate current cache size
        total_size_bytes = sum(
            f.stat().st_size for f in GLOBAL_SKILLS_DIR.glob("*.md")
            if f.is_file()
        )
        max_size_bytes = SKILLS_CACHE_MAX_SIZE_GB * (1024 ** 3)
        threshold_bytes = SKILLS_CACHE_CLEANUP_THRESHOLD_GB * max_size_bytes

        # No cleanup needed
        if total_size_bytes < threshold_bytes:
            return

        # LRU deletion: sort by last access time (atime), delete oldest first.
        # st_atime tracks actual read access; fall back to st_mtime on systems
        # where atime is disabled (noatime mount option, some Windows configs).
        def _access_time(f):
            s = f.stat()
            return max(s.st_atime, s.st_mtime)

        skill_files = sorted(
            GLOBAL_SKILLS_DIR.glob("*.md"),
            key=_access_time
        )

        # Delete until under threshold
        freed_bytes = 0
        for skill_file in skill_files:
            if total_size_bytes - freed_bytes < threshold_bytes:
                break
            try:
                file_size = skill_file.stat().st_size
                skill_file.unlink()
                freed_bytes += file_size
            except (OSError, FileNotFoundError):
                pass
    except Exception:
        # Cleanup failure is non-critical — don't break main flow
        pass


class ClaudeInterface:
    """Abstraction layer for all Anthropic CLI interactions."""

    def __init__(self, working_dir, cmd=None, effort=None):
        self.working_dir = pathlib.Path(working_dir)
        self.cmd = cmd or CLAUDE_CMD
        self.last_cost = None  # USD cost of most recent call()
        self.effort = effort   # default reasoning effort for all calls

    def call(self, system_prompt, user_input, model="haiku", timeout=120,
             output_format="text", tools=None, effort=None,
             append_system=False):
        """Fire-and-forget call. Returns stdout text.

        Uses --system-prompt-file (temp file) instead of --system-prompt
        to avoid CLAUDE.md leaking into the system prompt on long prompts.
        If append_system=True, uses --append-system-prompt instead (preserves
        Claude's built-in system prompt — important for ARC grid tasks).

        Side effect: sets self.last_cost (USD) when output_format="text"
        by using JSON format internally to capture cost metadata.
        """
        self.last_cost = None
        effort = effort or self.effort  # instance default if not explicit
        # Use JSON internally when caller wants text — captures cost
        use_json = (output_format == "text")
        wire_format = "json" if use_json else output_format

        # Write system prompt to temp file — avoids shell escaping issues
        # and CLAUDE.md contamination that happens with --system-prompt arg
        import tempfile
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8",
            dir=str(self.working_dir))
        try:
            tmp.write(system_prompt)
            tmp.close()
            # Guard: Map logical model name to actual model ID for subprocess.
            # Protects against Anthropic naming changes (e.g., claude-3.5-haiku-20250101).
            # If short name not in mapping, pass through (allows testing custom model IDs).
            actual_model = MODEL_MAP.get(model, model)

            if append_system:
                # Append to built-in system prompt (preserves Claude's default framing).
                # Used by ARC grid tasks where the built-in prompt helps format compliance.
                args = [
                    self.cmd, "-p",
                    "--model", actual_model,
                    "--output-format", wire_format,
                    "--append-system-prompt", system_prompt,
                ]
            else:
                args = [
                    self.cmd, "-p",
                    "--model", actual_model,
                    "--output-format", wire_format,
                    "--system-prompt-file", tmp.name,
                ]
            if effort:
                args.extend(["--effort", effort])
            if tools:
                args.extend(["--allowedTools", tools])
            else:
                # Force single-shot: disable all tools (same as call_streaming)
                args.extend(["--tools", ""])
            proc = subprocess.Popen(
                args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                env={k: v for k, v in os.environ.items() if k != "CLAUDECODE"},
                cwd=str(self.working_dir),
            )
            try:
                stdout, _ = proc.communicate(input=user_input, timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                return ""

            raw = stdout.strip()
            if not use_json:
                return raw

            # Extract text + cost from JSON envelope
            try:
                data = json.loads(raw)
                cost = data.get("cost_usd",
                                data.get("total_cost_usd"))
                if isinstance(cost, (int, float)):
                    self.last_cost = cost
                # Extract text: "result" field holds the response text.
                # Do NOT fall back to raw: if "result" is missing we'd return
                # the full JSON envelope as if it were the response text.
                text = data.get("result")
                if isinstance(text, str):
                    return text.strip()
                # "result" absent or non-string — log and return empty
                _log_error("call:json", "MissingResult",
                           "JSON envelope missing 'result' field",
                           details=raw[:200],
                           working_dir=self.working_dir)
                return ""
            except (json.JSONDecodeError, TypeError, AttributeError) as e:
                # JSON parse failed — raw is not a valid envelope.
                # Return empty string rather than leaking raw JSON to callers.
                _log_error("call:json", type(e).__name__, str(e),
                           details=raw[:200],
                           working_dir=self.working_dir)
                return ""
        except Exception as e:
            return f"[Error: {e}]"
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

    def _write_prompt_file(self, system_prompt):
        """Write system prompt to a temp file. Caller must delete it."""
        import tempfile
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8",
            dir=str(self.working_dir))
        tmp.write(system_prompt)
        tmp.close()
        return tmp.name

    def _invoke_claude_subprocess(self, args):
        """Abstraction layer for Claude CLI subprocess invocation.

        Encapsulates all Anthropic CLI interactions. If Anthropic deprecates the
        CLI or changes the output format, replace this method's implementation
        with the Python SDK equivalent:

            from anthropic import Anthropic
            client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
            # Then use client.messages.create() instead of CLI subprocess

        Returns: subprocess.Popen object
        Raises: RuntimeError if CLI is unavailable or returns unexpected format
        """
        # Guard: ensure CLI is available before invoking
        if not shutil.which(self.cmd):
            raise RuntimeError(
                f"Claude CLI not found at '{self.cmd}'. "
                f"Install via 'npm install -g @anthropic-ai/claude-code' "
                f"or migrate to Python SDK (see _invoke_claude_subprocess docstring)"
            )

        try:
            proc = subprocess.Popen(
                args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                env={k: v for k, v in os.environ.items() if k != "CLAUDECODE"},
                cwd=str(self.working_dir),
            )
            return proc
        except FileNotFoundError as e:
            raise RuntimeError(
                f"Failed to invoke Claude CLI: {e}. "
                f"Ensure 'claude' command is in PATH."
            ) from e

    def call_streaming(self, system_prompt, user_input, model="haiku",
                       resume=None, tools=False, effort=None):
        """Streaming call via Popen. Returns (subprocess.Popen, tmp_path).

        Caller is responsible for reading stdout, waiting for completion,
        and deleting tmp_path when done.
        """
        tmp_path = None
        args = [
            self.cmd, "-p",
            "--model", model,
            "--output-format", "stream-json",
        ]
        if effort:
            args.extend(["--effort", effort])
        if resume:
            args.extend(["--resume", resume])
        if tools:
            args.append("--allowedTools")
            args.append(ALLOWED_TOOLS)
        else:
            # Explicitly disable all tools to force single-shot text response.
            # Without this, CLI uses default tools and model goes agentic
            # (6-8 tool-use turns, compressed summaries instead of full analysis).
            # Validated: --tools "" → 7/7 single-shot, 2.7x more output, 2x faster.
            args.extend(["--tools", ""])
        if system_prompt:
            tmp_path = self._write_prompt_file(system_prompt)
            args.extend(["--system-prompt-file", tmp_path])

        proc = self._invoke_claude_subprocess(args)
        if user_input:
            try:
                proc.stdin.write(user_input)
                proc.stdin.close()
            except (BrokenPipeError, OSError):
                # Subprocess died before reading input — kill and return None
                # so caller knows no output will come
                try:
                    proc.kill()
                    proc.wait()
                except OSError:
                    pass
                return None, tmp_path
        return proc, tmp_path


class C:
    """ANSI color codes. Disabled on systems where ANSI setup failed (Windows 11, CI, etc.)."""
    # If ANSI is not supported, use empty strings for all color codes
    # This gracefully degrades to monochrome output instead of breaking on unsupported systems
    RESET   = "\033[0m" if ANSI_SUPPORTED else ""
    BOLD    = "\033[1m" if ANSI_SUPPORTED else ""
    DIM     = "\033[2m" if ANSI_SUPPORTED else ""
    CYAN    = "\033[36m" if ANSI_SUPPORTED else ""
    GREEN   = "\033[32m" if ANSI_SUPPORTED else ""
    YELLOW  = "\033[33m" if ANSI_SUPPORTED else ""
    RED     = "\033[31m" if ANSI_SUPPORTED else ""
    MAGENTA = "\033[35m" if ANSI_SUPPORTED else ""
    BLUE    = "\033[34m" if ANSI_SUPPORTED else ""


# ── Session ──────────────────────────────────────────────────────────────────

class Session:
    """Track session ID, model, and cumulative usage."""

    def __init__(self, model="haiku"):
        self.session_id = None
        self.model = model
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost_usd = 0.0
        self.turn_count = 0

    def save(self, name):
        sessions_dir = pathlib.Path.home() / ".prism_sessions"  # Compute dynamically, not frozen at module load
        sessions_dir.mkdir(parents=True, exist_ok=True)
        path = sessions_dir / f"{name}.json"
        path.write_text(json.dumps({
            "_version": 1,
            "session_id": self.session_id,
            "model": self.model,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": self.total_cost_usd,
            "turn_count": self.turn_count,
        }, indent=2))
        return path

    def load(self, name):
        sessions_dir = pathlib.Path.home() / ".prism_sessions"  # Compute dynamically, not frozen at module load
        path = sessions_dir / f"{name}.json"
        if not path.exists():
            return False
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            print(f"  Warning: corrupt session file {name}: {e}",
                  file=sys.stderr)
            return False
        if isinstance(data, dict) and "_version" not in data:
            data["_version"] = 1
        self.session_id = data.get("session_id")
        loaded_model = data.get("model", "sonnet")
        if loaded_model not in ("haiku", "sonnet", "opus"):
            print(f"  Warning: invalid model '{loaded_model}' in session "
                  f"'{name}', defaulting to sonnet", file=sys.stderr)
            loaded_model = "sonnet"
        self.model = loaded_model
        self.total_input_tokens = data.get("total_input_tokens", 0)
        self.total_output_tokens = data.get("total_output_tokens", 0)
        self.total_cost_usd = data.get("total_cost_usd", 0.0)
        self.turn_count = data.get("turn_count", 0)
        return True

    @staticmethod
    def list_saved():
        sessions_dir = pathlib.Path.home() / ".prism_sessions"  # Compute dynamically, not frozen at module load
        if not sessions_dir.exists():
            return []
        return sorted(p.stem for p in sessions_dir.glob("*.json"))


class YieldTracker:
    """Track which domains produce actionable findings across sessions.

    Records domain analysis outcomes (actionable/insightful/noise) and
    maintains a yield score for each domain. Used to prioritize re-analysis
    of high-value domains and deprioritize noisy ones.
    """

    def __init__(self, yield_path):
        self.path = pathlib.Path(yield_path)
        self._lock = threading.Lock()
        self.db = self._load()

    def _load(self):
        """Load yield database from disk, return empty dict if missing/corrupt."""
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save(self):
        """Persist yield database to disk."""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(self.db, indent=2), encoding="utf-8")
        except (OSError, PermissionError):
            pass  # Non-critical: yield data is advisory, not essential

    def record(self, domain_name, outcome):
        """Record a domain analysis outcome.

        Args:
            domain_name: str, domain identifier
            outcome: 'actionable' | 'insightful' | 'noise'
                - actionable: >200 chars output (likely generated fixes)
                - insightful: 50-200 chars (partial analysis)
                - noise: <50 chars or empty (no useful output)
        """
        with self._lock:
            d = self.db.setdefault(
                domain_name,
                {"total": 0, "actionable": 0, "insightful": 0, "noise": 0})
            d["total"] += 1
            d[outcome] = d.get(outcome, 0) + 1
            # Yield = weighted sum of productive outcomes
            # actionable: 1.0 weight, insightful: 0.7 weight
            d["yield"] = (d["actionable"] * 1.0 + d["insightful"] * 0.7) / max(d["total"], 1)
            self._save()

    def rank_domains(self, domains):
        """Sort domain list by historical yield (highest first).

        Unknown domains get 0.5 (neutral) to encourage exploration of new areas.
        """
        return sorted(
            domains,
            key=lambda d: self.db.get(d.get("name", ""), {}).get("yield", 0.5),
            reverse=True)

    def get_yield_score(self, domain_name):
        """Get historical yield score for a domain (0.0-1.0)."""
        return self.db.get(domain_name, {}).get("yield", 0.5)


# ── Session Log (TRACK primitive) ────────────────────────────────────────────

class SessionLog:
    """Persistent log of all operations — the TRACK primitive.

    Every operation (solve, scan, discover, expand, target, calibrate,
    optimize) appends an entry. Enables:
    - Calibrate to see what was tried before
    - Discover to filter already-explored domains
    - --history to show exploration state
    """

    def __init__(self, working_dir):
        self.path = pathlib.Path(working_dir) / ".deep" / "session_log.json"
        self._lock = threading.Lock()

    def append(self, operation, intent=None, domains=None,
               findings_summary=None, lens=None, model=None,
               mode=None, file_name=None, k_report=None,
               cost_estimate=None, duration_sec=None):
        """Append one operation record to the session log."""
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "operation": operation,
        }
        if intent:
            entry["intent"] = intent
        if domains:
            entry["domains"] = domains
        if findings_summary:
            entry["findings_summary"] = findings_summary[:500]
        if lens:
            entry["lens"] = lens
        if model:
            entry["model"] = model
        if mode:
            entry["mode"] = mode
        if file_name:
            entry["file"] = file_name
        if k_report:
            kr = {
                "k_estimate": k_report.get("k_estimate"),
                "content_type": k_report.get("content_type"),
                "recommended_mode": k_report.get("recommended_mode"),
                "recommended_model": k_report.get("recommended_model"),
            }
            rationale = k_report.get("rationale")
            if rationale:
                kr["rationale"] = rationale[:200]
            strategy = k_report.get("strategy")
            if strategy and isinstance(strategy, dict):
                kr["strategy"] = {
                    k: v for k, v in strategy.items() if v
                }
            entry["k_report"] = kr
        if cost_estimate is not None:
            entry["cost_estimate"] = cost_estimate
        if duration_sec is not None:
            entry["duration_sec"] = round(duration_sec, 1)

        with self._lock:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                entries = []
                if self.path.exists():
                    try:
                        parsed = json.loads(
                            self.path.read_text(encoding="utf-8"))
                        if isinstance(parsed, list):
                            entries = parsed
                    except (json.JSONDecodeError, OSError):
                        entries = []
                entries.append(entry)
                self.path.write_text(
                    json.dumps(entries, indent=2), encoding="utf-8")
            except (OSError, PermissionError):
                pass  # Non-critical: session log is advisory

    def load(self, limit=50):
        """Load recent session log entries."""
        if not self.path.exists():
            return []
        try:
            entries = json.loads(
                self.path.read_text(encoding="utf-8"))
            if not isinstance(entries, list):
                return []
            return entries[-limit:] if len(entries) > limit else entries
        except (json.JSONDecodeError, OSError):
            return []

    def summary(self, limit=20):
        """Human-readable summary of recent operations."""
        entries = self.load(limit=limit)
        lines = []
        for e in entries:
            ts = e.get("timestamp", "?")[:19]
            op = e.get("operation", "?")
            f = e.get("file", "")
            intent = e.get("intent", "")
            model = e.get("model", "")
            dur = e.get("duration_sec")
            dur_str = f" {dur}s" if dur else ""
            detail = intent or f
            lines.append(f"  {ts}  {op:12s}  {model:8s}"
                         f"  {detail[:50]}{dur_str}")
        return "\n".join(lines) if lines else "  (no operations logged)"

    def recommend_prism(self, file_name=None, file_ext=None,
                        yield_tracker=None):
        """Recommend prism based on combined intelligence sources.

        Uses session log (which prisms produced depth) + yield tracker
        (which prisms produced actionable results) to score prisms.
        Returns (prism_name, confidence, reason) or (None, 0, "").
        """
        entries = self.load(limit=200)
        if not entries:
            return None, 0, ""

        # Score prisms by output length on similar files
        prism_scores = {}  # prism_name -> {"lengths": [], "yield": 0.5}
        for e in entries:
            if e.get("operation") != "analyze":
                continue
            lens = e.get("lens")
            summary = e.get("findings_summary", "")
            if not lens or not summary:
                continue
            # Filter internal pipeline prisms (not user-facing)
            if lens.startswith("full_") or lens.startswith("3way_"):
                continue
            # Match by extension if available
            e_file = e.get("file", "")
            if file_ext and e_file:
                e_ext = e_file.rsplit(".", 1)[-1] if "." in e_file else ""
                if e_ext != file_ext:
                    continue
            prism_scores.setdefault(lens, {"lengths": [], "yield": 0.5})
            prism_scores[lens]["lengths"].append(len(summary))

        if not prism_scores:
            return None, 0, ""

        # Integrate yield tracker data (if available)
        if yield_tracker:
            for prism_name in prism_scores:
                ys = yield_tracker.get_yield_score(prism_name)
                prism_scores[prism_name]["yield"] = ys

        # Combined score: 60% depth (avg summary length) + 40% yield
        def _combined_score(item):
            name, data = item
            lengths = data["lengths"]
            avg_len = sum(lengths) / len(lengths) if lengths else 0
            # Normalize avg_len to 0-1 (200 chars = 1.0)
            depth_score = min(avg_len / 200, 1.0)
            yield_score = data["yield"]
            return depth_score * 0.6 + yield_score * 0.4

        ranked = sorted(prism_scores.items(),
                        key=_combined_score, reverse=True)

        best_prism, best_data = ranked[0]
        avg_len = (sum(best_data["lengths"]) / len(best_data["lengths"])
                   if best_data["lengths"] else 0)
        n = len(best_data["lengths"])
        ys = best_data["yield"]
        confidence = min(n / 5, 1.0)

        return (best_prism, confidence,
                f"{best_prism} depth={avg_len:.0f}c yield={ys:.0%} "
                f"({n} samples)")


# ── Single-Shot Predictor (Tier 1: zero LLM cost) ───────────────────────────

# Predictor calibration date — if MODEL_MAP changes, thresholds may need re-tuning
_PREDICTOR_CALIBRATED = "2026-03-17"
_PREDICTOR_MODEL_VERSIONS = {"haiku": "claude-haiku-4-5-20251001",
                             "sonnet": "claude-sonnet-4-6",
                             "opus": "claude-opus-4-6"}


def predict_single_shot(prism_text, target_text, model_name="sonnet"):
    """Predict probability of single-shot completion (no agentic drift).

    Tier 1+2 predictor: static features + yield data, ~70-85% accuracy.
    Calibrated on Round 42 (Mar 17, 2026) model versions.
    Features derived from Round 42 self-analysis:
    - Imperative verb density → constrains model action space
    - Section marker count → provides structural boundaries
    - Prompt word count → longer = more constrained (paradoxically)
    - Code noun ratio in target → triggers analytical mode
    - Model capacity match → Haiku drifts on abstract, Sonnet on reasoning

    Returns (probability, features_dict) where probability is 0.0-1.0.
    """
    # Feature extraction
    prism_words = prism_text.split()
    prism_wc = len(prism_words)
    target_wc = len(target_text.split())

    # Imperative verbs that constrain model behavior
    imperatives = {"execute", "name", "find", "identify", "prove",
                   "list", "derive", "trace", "map", "classify",
                   "extract", "analyze", "compare", "design", "run",
                   "force", "collect", "output", "show", "build"}
    imp_count = sum(1 for w in prism_words
                    if w.lower().rstrip(".:,;") in imperatives)

    # Section markers (##, Step N, Phase N) provide structural boundaries
    section_markers = len(re.findall(
        r'^(?:##|Step \d|Phase \d|\d+\.)', prism_text, re.MULTILINE))

    # Explicit termination markers
    terminators = len(re.findall(
        r'(?:output only|stop after|finally:|conclude)',
        prism_text, re.IGNORECASE))

    # Code noun ratio in target (triggers analytical mode)
    code_nouns = {"def ", "class ", "function ", "import ", "return ",
                  "if ", "for ", "while ", "async ", "await ",
                  "self.", "const ", "let ", "var "}
    target_sample = target_text[:2000].lower()
    code_hits = sum(1 for n in code_nouns if n in target_sample)
    code_ratio = code_hits / max(len(code_nouns), 1)

    # Model-specific base rates (from 40 rounds of experiments)
    model_base = {
        "haiku": 0.70,   # stochastic on abstract prompts
        "sonnet": 0.85,  # reliable on code, stochastic on reasoning
        "opus": 0.75,    # reliable but verbose
    }
    base = model_base.get(model_name, 0.80)

    # Score adjustments (calibrated from experiment corpus)
    score = base

    # Imperative density: >3 imperatives → +0.10
    if imp_count >= 3:
        score += 0.10
    elif imp_count == 0:
        score -= 0.15

    # Section markers: ≥2 → +0.05, 0 → -0.10
    if section_markers >= 2:
        score += 0.05
    elif section_markers == 0:
        score -= 0.10

    # Termination markers: any → +0.05
    if terminators > 0:
        score += 0.05

    # Code target with code prism → +0.10
    if code_ratio > 0.3:
        score += 0.10
    elif code_ratio < 0.1 and model_name == "haiku":
        score -= 0.15  # Haiku on abstract text → agentic risk

    # Prompt length sweet spot: 100-350w → +0.05, <80w → -0.15
    if 100 <= prism_wc <= 350:
        score += 0.05
    elif prism_wc < 80:
        score -= 0.15  # Below compression floor → conversation mode

    # Tier 2: Historical yield data (if available)
    # Prisms with high historical actionable rate get a boost
    yield_boost = 0.0
    yield_data = None
    try:
        _yield_path = pathlib.Path(".deep") / "yield.json"
        if _yield_path.exists():
            _yd = json.loads(_yield_path.read_text(encoding="utf-8"))
            prism_name = prism_text[:50].replace("\n", " ")  # rough key
            # Try to find this prism in yield data by checking all keys
            for k, v in _yd.items():
                if isinstance(v, dict) and v.get("total", 0) >= 3:
                    yield_score = v.get("yield", 0.5)
                    if yield_score > 0.8:
                        yield_boost = 0.05  # High-yield prism → boost
                    elif yield_score < 0.3:
                        yield_boost = -0.10  # Low-yield → penalty
                    yield_data = {"name": k, "yield": yield_score,
                                  "total": v["total"]}
                    break
    except (OSError, ValueError, json.JSONDecodeError):
        pass

    score += yield_boost

    # Clamp to [0.0, 1.0]
    score = max(0.0, min(1.0, score))

    features = {
        "prism_words": prism_wc,
        "target_words": target_wc,
        "imperative_count": imp_count,
        "section_markers": section_markers,
        "terminators": terminators,
        "code_ratio": round(code_ratio, 2),
        "model": model_name,
        "base_rate": base,
        "yield_boost": yield_boost,
    }
    if yield_data:
        features["yield_data"] = yield_data

    return score, features


# ── Epistemic Distance (C6) ──────────────────────────────────────────────────

# Epistemic dimensions: each domain scores on 6 axes (0-1).
# HEURISTIC — axis scores are hand-tuned estimates (Round 42), not
# empirically validated. Useful for selecting diverse test targets,
# not for precise measurement. Recalibrate if adding new domains.
# Distance = Euclidean distance in this space. Max = sqrt(6) ≈ 2.45.
_EPISTEMIC_AXES = {
    # (formal_methods, empirical, interpretive, quantitative, temporal, social)
    "code": (0.9, 0.3, 0.1, 0.7, 0.3, 0.1),
    "mathematics": (1.0, 0.0, 0.0, 1.0, 0.0, 0.0),
    "philosophy": (0.6, 0.1, 0.9, 0.1, 0.2, 0.4),
    "poetry": (0.0, 0.0, 1.0, 0.0, 0.3, 0.5),
    "legal": (0.7, 0.2, 0.6, 0.2, 0.3, 0.8),
    "scientific": (0.5, 0.9, 0.2, 0.8, 0.5, 0.3),
    "music": (0.3, 0.1, 0.9, 0.4, 0.7, 0.3),
    "business": (0.2, 0.5, 0.3, 0.6, 0.6, 0.7),
    "security": (0.8, 0.4, 0.1, 0.5, 0.4, 0.2),
    "architecture": (0.4, 0.2, 0.8, 0.3, 0.5, 0.6),
    "culinary": (0.0, 0.5, 0.7, 0.2, 0.3, 0.6),
    "religious": (0.1, 0.1, 0.9, 0.0, 0.4, 0.9),
}


def epistemic_distance(domain_a, domain_b):
    """Compute epistemic distance between two domains (0.0-2.45).

    Higher = more different in terms of evidence standards, methods of
    knowing, and conceptual primitives. Use to select maximally diverse
    stress-test targets for prism validation.

    Returns (distance, explanation).
    """
    a = _EPISTEMIC_AXES.get(domain_a)
    b = _EPISTEMIC_AXES.get(domain_b)
    if not a or not b:
        return 0.0, f"Unknown domain(s): {domain_a}, {domain_b}"
    dist = sum((ai - bi) ** 2 for ai, bi in zip(a, b)) ** 0.5
    # Find which axes differ most
    diffs = [(abs(ai - bi), name) for (ai, bi), name in
             zip(zip(a, b), ("formal", "empirical", "interpretive",
                             "quantitative", "temporal", "social"))]
    diffs.sort(reverse=True)
    top = diffs[0]
    return round(dist, 2), f"max diff: {top[1]} ({top[0]:.1f})"


def suggest_diverse_targets(n=3):
    """Suggest n maximally diverse domain triplets for validation.

    Uses greedy max-min distance to find the most epistemically
    spread set of domains.
    """
    domains = list(_EPISTEMIC_AXES.keys())
    if n >= len(domains):
        return domains

    # Greedy: start with most distant pair, add most distant from set
    best_pair = (0, "", "")
    for i, d1 in enumerate(domains):
        for d2 in domains[i + 1:]:
            dist, _ = epistemic_distance(d1, d2)
            if dist > best_pair[0]:
                best_pair = (dist, d1, d2)

    selected = [best_pair[1], best_pair[2]]
    while len(selected) < n:
        best_next = (0, "")
        for d in domains:
            if d in selected:
                continue
            min_dist = min(epistemic_distance(d, s)[0] for s in selected)
            if min_dist > best_next[0]:
                best_next = (min_dist, d)
        selected.append(best_next[1])

    return selected


# ── Stream Parser ────────────────────────────────────────────────────────────

class StreamParser:
    """Parse claude -p --output-format stream-json output line by line.

    CLI format (not API deltas):
      type: "system"    — init with session_id, model
      type: "assistant" — message with content blocks (thinking|text|tool_use)
      type: "result"    — final result with session_id, cost, usage
    """

    def __init__(self):
        self.result_data = None
        self.session_id = None

    def parse_line(self, line):
        """Parse one JSON line. Returns list of (event_type, data) tuples.

        Logs parse failures to stderr/errors.log to detect format changes in CLI output.
        Returns parse_error events to let caller decide whether to retry.
        """
        line = line.strip()
        if not line:
            return []
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            # CRITICAL: log JSON parse failures to detect CLI format changes
            # This is the most fragile interface (directly dependent on subprocess output)
            _log_error(
                context="stream:json_decode",
                error_type="JSONDecodeError",
                error_msg=str(exc),
                details=line[:200]
            )
            # Return parse_error event so caller can handle format changes gracefully
            return [("parse_error", str(exc))]

        etype = event.get("type", "")
        events = []

        if etype == "system":
            self.session_id = event.get("session_id")
            events.append(("system", event))

        elif etype == "assistant":
            msg = event.get("message", {})
            content = msg.get("content", [])
            for block in content:
                btype = block.get("type", "")
                if btype == "thinking":
                    events.append(("thinking", block.get("thinking", "")))
                elif btype == "text":
                    events.append(("text", block.get("text", "")))
                elif btype == "tool_use":
                    name = block.get("name", "tool")
                    events.append(("tool_use", name))
                elif btype == "tool_result":
                    events.append(("tool_result", block))

        elif etype == "result":
            self.result_data = event
            self.session_id = event.get("session_id")
            events.append(("result", event))

        elif etype == "rate_limit_event":
            info = event.get("rate_limit_info", {})
            events.append(("rate_limit", info))

        elif etype == "user":
            # CLI sends 'user' events for tool permission requests —
            # safe to ignore in stream context
            pass

        elif etype:
            # Unknown event type — log for diagnosing CLI format changes.
            # This prevents silent output death if the CLI changes its
            # stream-json schema (e.g. to content_block_delta).
            _log_error(
                context="stream:unknown_event_type",
                error_type="UnknownEventType",
                error_msg=etype,
                details=line[:200]
            )
            events.append(("unknown", {"type": etype, "raw": event}))

        return events


# ── Claude Backend ───────────────────────────────────────────────────────────

class ClaudeBackend:
    """Manage claude -p subprocess. Sends messages via stdin, yields stream lines."""

    def __init__(self, model, working_dir, session_id=None,
                 system_prompt=None, tools=True):
        self.model = model
        self.working_dir = working_dir
        self.session_id = session_id
        self.system_prompt = system_prompt or SYSTEM_PROMPT_FALLBACK
        self.tools = tools
        self.proc = None

    def build_cmd(self, prompt_file=None):
        """Build claude -p command with hardcoded format.

        TECHNICAL DEBT: This class builds CLI commands directly instead of using
        ClaudeInterface abstraction. If Anthropic changes CLI format or deprecates
        'claude -p', this method will break. Entire streaming pipeline will fail.

        MIGRATION PATH (Phase N):
        1. Add streaming_call() to ClaudeInterface (returns Popen for streaming)
        2. Replace this method and send() with calls to ClaudeInterface
        3. This enables Python SDK migration with single point of change

        See ClaudeInterface._invoke_claude_subprocess() for migration details.
        """
        # Guard: validate Claude CLI is available before constructing command
        if not shutil.which(CLAUDE_CMD):
            raise RuntimeError(
                f"Claude CLI required for streaming mode but not found at '{CLAUDE_CMD}'. "
                f"Install: npm install -g @anthropic-ai/claude-code. "
                f"Or refactor to use ClaudeInterface + Python SDK (see docstring)."
            )

        cmd = [
            CLAUDE_CMD, "-p",
            "--output-format", "stream-json",
            "--verbose",
            "--model", self.model,
        ]
        if self.tools:
            cmd += ["--allowedTools", ALLOWED_TOOLS]
        else:
            # Explicitly disable all tools to force single-shot text response.
            # Without this, CLI uses default tools and model goes agentic.
            cmd += ["--tools", ""]
        if self.session_id:
            cmd += ["--resume", self.session_id]
        elif prompt_file:
            cmd += ["--system-prompt-file", prompt_file]
        else:
            cmd += ["--system-prompt", self.system_prompt]
        return cmd

    def send(self, message):
        """Send message to claude -p, yield raw stdout lines.

        Uses --system-prompt-file (temp file) to avoid CLAUDE.md contamination.
        """
        # Kill any previous subprocess to prevent zombie processes
        if self.proc and self.proc.poll() is None:
            self.kill()

        import tempfile
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8",
            dir=self.working_dir)
        tmp.write(self.system_prompt)
        tmp.close()

        try:
            cmd = self.build_cmd(prompt_file=tmp.name)
            env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

            self.proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                env=env,
                cwd=self.working_dir,
            )

            try:
                self.proc.stdin.write(message.encode("utf-8", errors="replace"))
                self.proc.stdin.close()
            except (BrokenPipeError, OSError):
                # Subprocess died before reading input — no output possible
                try:
                    self.proc.kill()
                    self.proc.wait()
                except OSError:
                    pass
                return

            for raw_line in self.proc.stdout:
                yield raw_line.decode("utf-8", errors="replace")

            self.proc.wait()
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

    def kill(self):
        """Terminate the subprocess.

        Safe to call even if proc is None (e.g. Ctrl-C during
        backend construction before subprocess is launched).
        """
        try:
            if self.proc and self.proc.poll() is None:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
                    self.proc.wait()
        except (OSError, AttributeError):
            pass


# ── REPL ─────────────────────────────────────────────────────────────────────

class PrismREPL:
    """Main REPL loop with slash commands and streaming output."""
    _findings_lock = threading.Lock()  # Protects concurrent _save_deep_finding writes
    _session_lock = threading.Lock()  # Protects session counter updates (total_input_tokens, etc.)
    _file_io_lock = threading.Lock()  # Protects file reads during concurrent writes (e.g., target file snapshots)

    def __init__(self, model, working_dir, resume_session=None, quiet=False, effort=None):
        self.session = Session(model=model)
        self.working_dir = pathlib.Path(working_dir).resolve()
        self._yield_tracker = YieldTracker(self.working_dir / ".deep" / "yield.json")
        self._session_log = SessionLog(self.working_dir)
        self._claude = ClaudeInterface(self.working_dir, effort=effort)
        self.backend = None
        self.queued_files = []
        self._interrupted = False
        self._auto_mode = False
        self._quiet = quiet  # Skip auto-detection prompts
        self._last_action = None  # ("scan", {"issues": [...]}) | ("deep", {"file": ...}) | ...
        self._discover_results = []  # cached discover results for target=N
        self._active_file = None  # {"content": str, "name": str, "general": bool} — set by /scan
        self._force_file_confirm = False  # If True, prompt even in chat mode before auto-reading files
        self._chat_mode = "off"  # "off" (vanilla), "single" (dynamic cook per msg), "full" (dynamic pipeline per msg)
        self._active_prism_name = None   # e.g. "pedagogy" or "readme/promise_credibility"
        self._active_prism_prompt = None # loaded prism text, used in system prompt
        self.system_prompt = self._load_system_prompt()
        self._session_diverged = False       # True when session_id changed unexpectedly
        self._session_transition_log = []    # In-memory log of session ID transitions
        self._pending_session_id = None      # Hold new session ID until user confirms divergence
        self._commands = {}
        self._register_builtin_commands()

        # SIGTERM handler: ensure subprocess cleanup on kill/systemd stop.
        # Without this, Claude CLI subprocesses become zombies if the REPL is
        # terminated by a process manager or timeout script.
        try:
            def _sigterm_handler(sig, frame):
                self._interrupted = True
                if self.backend:
                    self.backend.kill()
            signal.signal(signal.SIGTERM, _sigterm_handler)
        except (OSError, ValueError):
            pass  # SIGTERM not available (Windows) or signal in wrong thread

        # Check Claude CLI availability at startup (fail-fast)
        if not (shutil.which("claude") or shutil.which("claude.cmd")):
            print(f"{C.RED}Error: 'claude' CLI not found in PATH. "
                  f"Install: npm install -g @anthropic-ai/claude-code"
                  f"{C.RESET}", file=sys.stderr)
            print("Then run 'claude' once to authenticate.",
                  file=sys.stderr)
            sys.exit(1)

        if resume_session:
            if self.session.load(resume_session):
                print(f"{C.GREEN}Resumed session: {resume_session} "
                      f"(turn {self.session.turn_count}, {self.session.model}){C.RESET}")
            else:
                print(f"{C.YELLOW}Session '{resume_session}' not found, "
                      f"starting fresh{C.RESET}")

    @contextmanager
    def _temporary_model(self, model_name):
        """Temporarily switch session model, restoring on exit.

        Handles None (no-op), resolves via MODEL_MAP.
        Usage: with self._temporary_model('sonnet'): ...
        """
        if model_name is None:
            yield
            return
        resolved = MODEL_MAP.get(model_name, model_name)
        prev = self.session.model
        if resolved != prev:
            print(f"  {C.DIM}Model → {model_name} "
                  f"(optimal for prism){C.RESET}")
        self.session.model = resolved
        try:
            yield
        finally:
            self.session.model = prev

    def _ensure_attributes(self):
        """Guard against time-bomb crashes after __class__ rebind: ensure all expected attributes exist."""
        defaults = {
            '_enriched_system_prompt': None,
            '_discover_results': [],
            '_active_file': None,
            '_force_file_confirm': False,
            '_chat_mode': 'off',
            '_active_prism_name': None,
            '_active_prism_prompt': None,
            '_session_diverged': False,
            '_session_transition_log': [],
            '_pending_session_id': None,
            'backend': None,
            'queued_files': [],
            '_interrupted': False,
            '_auto_mode': False,
            '_last_action': None,
        }
        for attr, default_val in defaults.items():
            if not hasattr(self, attr):
                setattr(self, attr, default_val)

    def banner(self):
        mode_str = self._active_prism_name if self._active_prism_name else self._chat_mode
        print(f"\n{C.BOLD}{C.CYAN}prism{C.RESET} {C.DIM}v{VERSION}{C.RESET}"
              f"  {C.DIM}model={C.RESET}{self.session.model}"
              f"  {C.DIM}prism={C.RESET}{mode_str}"
              f"  {C.DIM}cwd={C.RESET}{self.working_dir}")
        print(f"{C.DIM}Structural analysis through cognitive prisms.{C.RESET}")
        print(f"{C.DIM}Quick start: {C.RESET}/scan file.py"
              f"  {C.DIM}|  /help for all commands  |  "
              f"blank line sends  |  Ctrl+D exits{C.RESET}\n")

    def run(self):
        """Main loop: read input, dispatch commands or send to Claude."""
        self.banner()
        while True:
            try:
                # Read first line with prompt
                first_line = input(f"{C.GREEN}>{C.RESET} ").strip()
            except (EOFError, KeyboardInterrupt):
                print(f"\n{C.DIM}bye{C.RESET}")
                break

            if not first_line:
                continue

            # If first line is a command, process immediately
            if first_line.startswith("/"):
                if not self._handle_command(first_line):
                    break
                continue

            # For regular messages, collect multi-line input
            # Read additional lines until blank line (supports large pastes)
            lines = [first_line]
            while True:
                try:
                    next_line = input()  # No prompt for continuation lines
                    if not next_line:  # Blank line ends input
                        break
                    lines.append(next_line)
                except (EOFError, KeyboardInterrupt):
                    break

            user_input = "\n".join(lines)

            if self._check_shortcuts(user_input):
                continue

            self._enrich(user_input)
            message = self._build_message(user_input)
            self.queued_files.clear()
            if self._chat_mode == "full":
                self._chat_full_pipeline(message)
            elif self._chat_mode == "single":
                self._chat_single_prism(message)
            else:
                self._send_and_stream(message)



    # ── Full-mode chat pipeline ──────────────────────────────────────────────

    def _chat_single_prism(self, message):
        """Dynamic single prism: cook 1 prism per message, then respond.

        1. Cook an optimal prism for this specific message
        2. Use it as system prompt for the response
        """
        # Cook prism for this message (always use COOK_MODEL for best quality)
        print(f"  {C.DIM}cooking prism...{C.RESET}", end="",
              flush=True)
        raw = self._call_model(
            COOK_UNIVERSAL.format(
                intent="respond to this message — find hidden "
                "assumptions, structural properties, non-obvious "
                "implications"),
            message[:2000], timeout=60, model=COOK_MODEL)
        parsed = self._parse_stage_json(raw, "cook_chat_single")

        if isinstance(parsed, dict) and parsed.get("prompt"):
            prism_prompt = parsed["prompt"]
            name = parsed.get("name", "dynamic")
            sys.stdout.write(
                f"\r  {C.DIM}prism: {name}{C.RESET}"
                + " " * 20 + "\n")
        else:
            # Fallback: use base system prompt (cook failed)
            sys.stdout.write(
                f"\r  {C.YELLOW}⚠ prism cooking failed — "
                f"using vanilla{C.RESET}"
                + " " * 10 + "\n")
            prism_prompt = None

        print(f"{C.BOLD}{C.BLUE}── Response ──{C.RESET}")
        self._chat_full_call(message, system_prompt=prism_prompt)

    def _chat_full_pipeline(self, message):
        """Dynamic full prism: cook pipeline per message, then run chained.

        1. Cook a multi-pass pipeline for this specific message
        2. Run each prism in sequence, chaining outputs
        3. Return synthesized response
        """
        # Cook pipeline for this message
        print(f"  {C.DIM}cooking pipeline...{C.RESET}", end="",
              flush=True)
        raw = self._call_model(
            COOK_3WAY.format(
                intent="respond thoroughly to this message — "
                "multiple passes that deepen, challenge, and "
                "synthesize"),
            message[:2000], timeout=90, model=COOK_MODEL)
        parsed = self._parse_stage_json(raw, "cook_chat_full")

        if isinstance(parsed, list) and len(parsed) >= 2:
            prisms = []
            for item in parsed:
                text = item.get("prompt", "")
                role = item.get("role", item.get("name", "pass"))
                if text:
                    prisms.append({"prompt": text, "role": role})
            roles = ", ".join(p["role"] for p in prisms)
            sys.stdout.write(
                f"\r  {C.DIM}pipeline: {roles}{C.RESET}"
                + " " * 20 + "\n")
        else:
            # Fallback: single SDL pass (code-specific multi-pass wrong for chat)
            sys.stdout.write(
                f"\r  {C.YELLOW}⚠ pipeline cooking failed — "
                f"using SDL single pass{C.RESET}"
                + " " * 10 + "\n")
            sdl_prompt = self._load_prism("deep_scan") or ""
            prisms = [
                {"prompt": sdl_prompt, "role": "response"},
            ]

        # Capture enriched prompt before loop — _chat_full_call consumes it
        # on first use (one-shot). Without this, passes 2+ lose the context.
        enriched = getattr(self, '_enriched_system_prompt', None)

        # Run pipeline
        outputs = []
        for i, prism in enumerate(prisms):
            role = prism["role"]

            if i == 0:
                msg = message
                prompt = prism["prompt"] or None
            else:
                parts = [f"# USER REQUEST\n\n{message}"]
                for j, prev in enumerate(outputs):
                    prev_role = prisms[j]["role"].upper()
                    parts.append(
                        f"# PASS {j + 1}: {prev_role}"
                        f"\n\n{prev}")
                msg = "\n\n---\n\n".join(parts)
                # Guard against unbounded accumulation
                if len(msg) > 100_000:
                    msg = msg[:100_000] + "\n\n[... truncated due to size ...]"
                prompt = prism["prompt"]

            # Re-inject enriched prompt for each pass so pipeline context
            # isn't lost after the first call consumes it
            if enriched and not prompt:
                self._enriched_system_prompt = enriched

            print(f"\n{C.BOLD}{C.BLUE}── {role} ──{C.RESET}")
            output = self._chat_full_call(
                msg, system_prompt=prompt)

            if output and not self._interrupted:
                outputs.append(output)
            if not output or self._interrupted:
                break

    def _chat_full_call(self, message, system_prompt=None):
        """Single streaming call for the chat pipeline. Returns captured output."""
        active_prompt = system_prompt
        if active_prompt is None:
            active_prompt = getattr(
                self, '_enriched_system_prompt', None)
            if not active_prompt:
                active_prompt = self.system_prompt
        if self._active_prism_prompt and system_prompt is None:
            active_prompt = (self._active_prism_prompt
                             + "\n\n" + active_prompt)

        backend = ClaudeBackend(
            model=self.session.model,
            working_dir=str(self.working_dir),
            session_id=None,
            system_prompt=active_prompt,
            tools=False,
        )
        return self._stream_and_capture(backend, message)

    # ── Non-interactive review mode ───────────────────────────────────────────

    def review(self, path, prisms=None, json_output=False, output_file=None, serial=False):
        """Non-interactive review mode. Returns exit code: 0=clean, 1=issues, 2=error.

        Args:
            serial: If True, run sequentially to detect cross-file patterns.
                   Slower (2.7×) but catches recurring issues across files.
                   If False (default), run parallel (5 files at once) for speed.

        Cross-file pattern detection:
        - Parallel: Each file analyzed independently. Misses patterns like
          'RaceCondition in 3 files due to shared BaseClass'.
        - Serial: Files analyzed sequentially with awareness of prior findings.
          Adaptive prism ordering prioritizes high-impact checks first.
        """
        target = pathlib.Path(path)
        if not target.is_absolute():
            target = self.working_dir / target

        if not target.exists():
            print(f"Error: {path} not found", file=sys.stderr)
            return 2

        # Collect files
        if target.is_dir():
            files = self._collect_files(str(target))
        else:
            files = [target]

        if not files:
            print(f"Error: no analyzable files in {path}", file=sys.stderr)
            return 2

        # Determine prisms
        if prisms is None:
            prisms = self._get_prisms()

        mode_label = "serial (cross-file patterns)" if serial else "parallel (5 concurrent)"
        print(f"Reviewing {len(files)} file(s) with {len(prisms)} prism(s) [{mode_label}]...",
              file=sys.stderr)

        # Guard clause: Serial vs parallel execution
        error_count = [0]  # Track analysis crashes for exit code
        lock = threading.Lock()  # Protect all_results access in both serial and parallel modes

        if serial:
            # CRITICAL: Serial mode detects cross-file patterns
            # Slower (2.7×) but catches recurring issues that parallel misses
            all_results = {}
            total = len(files) * len(prisms)
            done = 0
            prior_findings = []  # Accumulate findings for cross-file context

            for fpath in files:
                for prism in prisms:
                    try:
                        content = fpath.read_text(encoding="utf-8", errors="replace")
                        # Pass prior findings as context for adaptive prism ordering
                        result = self._run_prism_oneshot(prism, content, fpath.name)
                    except Exception:
                        result = ""
                        error_count[0] += 1

                    all_results[(str(fpath), prism)] = result
                    done += 1
                    print(f"\r  Progress: {done}/{total}", end="", file=sys.stderr)

                    # Accumulate for cross-file pattern detection
                    if result and result.strip():
                        prior_findings.append({
                            "file": fpath.name,
                            "prism": prism,
                            "result": result[:500]  # Summary for context
                        })

            print(file=sys.stderr)  # newline after progress
        else:
            # Parallel mode: original implementation (faster, misses cross-file patterns)
            all_results = {}
            sem = threading.Semaphore(5)
            lock = threading.Lock()  # Override shared lock with fresh instance for parallel mode
            total = len(files) * len(prisms)
            done = [0]

            def run_one(fpath, prism):
                try:
                    content = fpath.read_text(encoding="utf-8", errors="replace")
                    result = self._run_prism_oneshot(prism, content, fpath.name)
                except Exception:
                    result = ""
                    error_count[0] += 1
                with lock:
                    all_results[(str(fpath), prism)] = result
                    done[0] += 1
                    print(f"\r  Progress: {done[0]}/{total}", end="", file=sys.stderr)

            threads = []
            for fpath in files:
                for prism in prisms:
                    def _run(f=fpath, p=prism):
                        sem.acquire()
                        try:
                            run_one(f, p)
                        finally:
                            sem.release()
                    t = threading.Thread(target=_run)
                    t.start()
                    threads.append(t)

            for t in threads:
                t.join()
            print(file=sys.stderr)  # newline after progress

        # Format output: protect all_results reads with lock.
        # Prevents KeyError/missing results when threads are active or code evolves.
        with lock:
            if json_output:
                output = self._review_format_json(files, prisms, all_results)
            else:
                output = self._review_format_markdown(files, prisms, all_results)

        # Write output
        if output_file:
            pathlib.Path(output_file).write_text(output, encoding="utf-8")
            print(f"Report written to {output_file}", file=sys.stderr)
        else:
            print(output)

        # Exit code: 2 if all analyses crashed, 1 if findings, 0 if clean
        # Guard: Protect all_results iteration with lock to prevent race conditions
        # when determining exit code. Iteration must not race with thread writes.
        with lock:
            has_findings = any(v.strip() for v in all_results.values())
        if has_findings:
            return 1
        if error_count[0] > 0 and not has_findings:
            total_analyses = len(files) * len(prisms)
            print(f"Warning: {error_count[0]}/{total_analyses} analyses "
                  f"failed", file=sys.stderr)
            if error_count[0] == total_analyses:
                return 2  # All crashed — don't report clean
        return 0

    def _review_format_json(self, files, prisms, all_results):
        """Format review results as JSON."""
        data = {}
        for fpath in files:
            file_data = {}
            for prism in prisms:
                result = all_results.get((str(fpath), prism), "")
                if result:
                    file_data[prism] = result
            if file_data:
                data[str(fpath)] = file_data
        return json.dumps(data, indent=2, ensure_ascii=False)

    def _review_format_markdown(self, files, prisms, all_results):
        """Format review results as markdown report."""
        lines = ["# Code Review Report\n"]
        for fpath in files:
            lines.append(f"## {fpath.name}\n")
            for prism in prisms:
                result = all_results.get((str(fpath), prism), "")
                if result:
                    lines.append(f"### {prism}\n")
                    lines.append(result)
                    lines.append("")
        return "\n".join(lines)

    # ── Slash commands ───────────────────────────────────────────────────

    def _handle_command(self, cmd):
        """Handle slash command. Returns True to continue, False to exit."""
        parts = cmd.split(maxsplit=1)
        name = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        entry = self._commands.get(name)
        if entry:
            result = entry["handler"](arg)
            return result if result is False else True
        else:
            print(f"{C.YELLOW}Unknown command: {name}. Type /help{C.RESET}")
            return True

    def _register_builtin_commands(self):
        """Populate the command registry with all built-in slash commands."""
        cmds = {
            "/exit":      {"handler": self._cmd_exit,       "help": "Exit Prism",                                        "args": "",                                              "category": "session"},
            "/help":      {"handler": self._cmd_help,       "help": "Show commands (/help full for all examples)",       "args": "[full]",                                        "category": "session"},
            "/clear":     {"handler": self._cmd_clear,      "help": "Reset session, clear discover cache and queued files", "args": "",                                           "category": "session"},
            "/model":     {"handler": self._cmd_model,      "help": "Switch Claude model for all operations",            "args": "haiku|sonnet|opus",                             "category": "session"},
            "/prism":     {"handler": self._cmd_mode,       "help": "Chat mode: off (vanilla), single/full (dynamic prisms), or static prism", "args": "[off|single|full|<prism>]", "category": "session"},

            "/compact":   {"handler": self._cmd_compact,    "help": "Trim conversation context to reduce token usage",   "args": "",                                              "category": "session"},
            "/cost":      {"handler": self._cmd_cost,       "help": "Show turns, tokens in/out, and USD cost",           "args": "",                                              "category": "session"},
            "/save":      {"handler": self._cmd_save,       "help": "Save current session to a named file for later",    "args": "<name>",                                        "category": "session"},
            "/load":      {"handler": self._cmd_load,       "help": "Resume a saved session (no arg = list all)",        "args": "[name]",                                        "category": "session"},
            "/scan":      {"handler": self._cmd_scan,       "help": "Structural analysis via cognitive prisms",          "args": "<file|dir|text> [mode]",                        "category": "analysis"},
            "/cook":      {"handler": self._cmd_cook,       "help": "Discover domains for an artifact type",             "args": "<domain> [sample-file]",                        "category": "analysis"},
            "/prisms":    {"handler": self._cmd_prisms,     "help": "Prism management: list, explore, create, delete",    "args": "[explore|create|delete]",                       "category": "info"},

            "/expand":    {"handler": self._cmd_expand,     "help": "Cook + run prisms on discovered areas (uses active file from /scan)", "args": "<indices|*> [single|full] [--refresh]", "category": "analysis"},
            "/fix":       {"handler": self._cmd_heal,       "help": "Extract issues from scan → apply fixes with diff review", "args": "[file] [deep] [auto]",                    "category": "fix"},
            "/status":    {"handler": self._cmd_status,     "help": "Dashboard: last scan age, open issues, cooked prisms", "args": "",                                            "category": "info"},
            "/reload":    {"handler": self._cmd_reload_cmd, "help": "Hot-reload prism.py + prisms without restarting",   "args": "",                                              "category": "session"},
            "/force-confirm": {"handler": self._cmd_force_confirm, "help": "Toggle: prompt before auto-reading files even in chat mode", "args": "",                              "category": "session"},
            "/kb":        {"handler": self._cmd_kb,          "help": "Knowledge base: list verified facts, clear, show entries for a file", "args": "[list|clear|<file>]",                          "category": "info"},
            "/ledger":    {"handler": self._cmd_ledger,      "help": "Evidence ledger: structured claims with provenance + confidence",          "args": "[laws|bugs|unverified|all]",                    "category": "info"},
            "/brainstorm": {"handler": self._cmd_brainstorm, "help": "3-way analysis on text (alias for /scan <text> 3way)",                       "args": "<text|file>",                                   "category": "analysis"},
        }
        self._commands.update(cmds)

    # ── Inline command wrappers ───────────────────────────────────────────────

    def _cmd_exit(self, arg):
        """Print bye and signal loop exit."""
        print(f"{C.DIM}bye{C.RESET}")
        return False

    def _cmd_ledger(self, arg):
        """View evidence ledger — structured claims with provenance.

        /ledger           — summary (count by type + confidence)
        /ledger laws      — show conservation laws
        /ledger bugs      — show bug claims
        /ledger unverified — show unverified claims
        /ledger all       — show everything
        """
        _path = self.working_dir / ".deep" / "evidence_ledger.json"
        if not _path.exists():
            print(f"{C.YELLOW}No evidence ledger yet — "
                  f"run /scan first{C.RESET}")
            return

        try:
            entries = json.loads(_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            print(f"{C.RED}Ledger corrupt{C.RESET}")
            return

        if not entries:
            print(f"{C.YELLOW}Ledger empty{C.RESET}")
            return

        arg = arg.strip().lower() if arg else ""

        if arg == "all":
            filtered = entries
        elif arg == "laws":
            filtered = [e for e in entries
                        if e.get("type") == "conservation_law"]
        elif arg == "bugs":
            filtered = [e for e in entries
                        if e.get("type") == "bug_claim"]
        elif arg in ("unverified", "unv"):
            filtered = [e for e in entries if not e.get("verified")]
        else:
            # Summary
            by_type = {}
            by_conf = {}
            for e in entries:
                t = e.get("type", "?")
                c = e.get("confidence", "?")
                by_type[t] = by_type.get(t, 0) + 1
                by_conf[c] = by_conf.get(c, 0) + 1
            unv = sum(1 for e in entries if not e.get("verified"))
            print(f"{C.BOLD}Evidence Ledger: "
                  f"{len(entries)} claims{C.RESET}")
            print(f"  By type: {', '.join(f'{v} {k}' for k, v in sorted(by_type.items()))}")
            print(f"  By confidence: {', '.join(f'{v} {k}' for k, v in sorted(by_conf.items()))}")
            print(f"  Unverified: {unv}/{len(entries)}")
            print(f"\n  {C.DIM}/ledger laws | bugs | unverified | all{C.RESET}")
            return

        if not filtered:
            print(f"{C.YELLOW}No matching entries{C.RESET}")
            return

        print(f"{C.BOLD}{len(filtered)} entries:{C.RESET}\n")
        for e in filtered[-20:]:  # Last 20
            _type = e.get("type", "?")
            _claim = e.get("claim", "?")[:100]
            _conf = e.get("confidence", "?")
            _src = e.get("source_file", "?")
            _prism = e.get("prism", "?")
            _verified = "YES" if e.get("verified") else "no"
            print(f"  [{_conf}] {_type}: {_claim}")
            print(f"    {C.DIM}src={_src} prism={_prism} "
                  f"verified={_verified}{C.RESET}")

    def _cmd_kb(self, arg):
        """J10: Manage the persistent knowledge base (.deep/knowledge/).

        /kb           — list all files with KB entries
        /kb <file>    — show entries for a specific file
        /kb clear     — clear all KB entries
        """
        import json as _json_kb_cmd

        kb_dir = self.working_dir / ".deep" / "knowledge"
        if not kb_dir.exists():
            print(f"{C.DIM}No knowledge base yet. "
                  f"Run /scan file verified or /scan file gaps "
                  f"to populate.{C.RESET}")
            return

        arg = arg.strip()

        if arg == "clear":
            import shutil
            shutil.rmtree(kb_dir, ignore_errors=True)
            print(f"{C.GREEN}Knowledge base cleared{C.RESET}")
            return

        kb_files = sorted(kb_dir.glob("*.json"))
        if not kb_files:
            print(f"{C.DIM}Knowledge base is empty.{C.RESET}")
            return

        if not arg or arg == "list":
            # List all KB files with entry counts
            print(f"\n{C.BOLD}Knowledge Base "
                  f"(.deep/knowledge/){C.RESET}")
            total = 0
            for kf in kb_files:
                try:
                    entries = _json_kb_cmd.loads(
                        kf.read_text(encoding="utf-8"))
                    n = len(entries) if isinstance(entries, list) else 0
                    total += n
                    print(f"  {kf.stem}: {n} entries")
                except (ValueError, OSError):
                    print(f"  {kf.stem}: (corrupt)")
            print(f"\n  {C.DIM}Total: {total} entries across "
                  f"{len(kb_files)} files{C.RESET}")
            return

        # Show entries for a specific file
        stem = self._discover_cache_key(arg)
        kb_path = kb_dir / f"{stem}.json"
        if not kb_path.exists():
            print(f"{C.YELLOW}No KB entries for "
                  f"'{arg}'{C.RESET}")
            return

        try:
            entries = _json_kb_cmd.loads(
                kb_path.read_text(encoding="utf-8"))
            if not isinstance(entries, list):
                entries = []
        except (ValueError, OSError):
            print(f"{C.RED}KB file corrupt{C.RESET}")
            return

        print(f"\n{C.BOLD}KB: {arg} ({len(entries)} entries)"
              f"{C.RESET}")
        for i, e in enumerate(entries, 1):
            claim = e.get("claim", "?")
            conf = e.get("confidence", "?")
            src = e.get("source", "?")
            verified = "verified" if e.get("verified") else "unverified"
            print(f"  {i}. [{conf}] {claim}")
            print(f"     {C.DIM}{src} — {verified}{C.RESET}")

    def _cmd_brainstorm(self, arg):
        """/brainstorm <text|file> — alias for /scan <input> 3way."""
        if not arg or not arg.strip():
            print(f"{C.YELLOW}Usage: /brainstorm <text or file>"
                  f"{C.RESET}")
            return
        self._cmd_scan(f"{arg.strip()} 3way")

    def _cmd_help(self, arg):
        """Show help text. /help full for all examples."""
        self._show_help(full=arg.strip().lower() == "full")
        return True

    def _cmd_clear(self, arg):
        """Clear session, queued files, and last action."""
        model = self.session.model
        self.session = Session(model=model)
        self.queued_files.clear()
        self._last_action = None
        self._discover_results = []
        self._active_file = None
        # Also clear disk-cached discover results so /expand doesn't
        # resurrect stale domains from a previous scan
        deep_dir = self.working_dir / ".deep"
        if deep_dir.is_dir():
            for f in deep_dir.glob("discover_*.json"):
                try:
                    f.unlink()
                except OSError:
                    pass
        print(f"{C.YELLOW}Session cleared{C.RESET}")

    def _cmd_force_confirm(self, arg):
        """Toggle whether file auto-read confirmation is shown even in chat mode."""
        self._force_file_confirm = not getattr(self, '_force_file_confirm', False)
        state = "on" if self._force_file_confirm else "off"
        print(f"{C.CYAN}force-confirm: {state}{C.RESET}")

    def _cmd_model(self, arg):
        """Validate and switch model."""
        if arg in ("haiku", "sonnet", "opus"):
            self.session.model = arg
            print(f"{C.CYAN}Model: {arg}{C.RESET}")
        else:
            print(f"{C.YELLOW}Usage: /model haiku|sonnet|opus{C.RESET}")

    def _cmd_mode(self, arg):
        """Switch chat prism mode or set a static prism.

        /prism             — show current mode
        /prism off         — vanilla chat (no prisms)
        /prism single      — dynamic single prism (cook prism per message)
        /prism full        — dynamic full prism (cook pipeline per message)
        /prism <prism>      — static prism for all messages (e.g. pedagogy)
        """
        if not arg:
            if self._chat_mode == "off":
                prism = self._active_prism_name or "none"
                print(f"{C.CYAN}Prism: off (vanilla), "
                      f"prism={prism}{C.RESET}")
            elif self._chat_mode == "single":
                print(f"{C.CYAN}Prism: single "
                      f"(dynamic prism per message){C.RESET}")
            elif self._chat_mode == "full":
                print(f"{C.CYAN}Prism: full "
                      f"(dynamic pipeline per message){C.RESET}")
            return

        if arg == "off":
            self._chat_mode = "off"
            self._active_prism_name = None
            self._active_prism_prompt = None
            print(f"{C.CYAN}Prism: off (vanilla){C.RESET}")
        elif arg == "single":
            self._chat_mode = "single"
            self._active_prism_name = None
            self._active_prism_prompt = None
            print(f"{C.CYAN}Prism: single "
                  f"(cook prism per message){C.RESET}")
        elif arg == "full":
            self._chat_mode = "full"
            self._active_prism_name = None
            self._active_prism_prompt = None
            print(f"{C.CYAN}Prism: full "
                  f"(cook pipeline per message){C.RESET}")
        else:
            # Static prism mode
            prompt = self._load_prism(arg)
            if prompt:
                self._chat_mode = "off"
                self._active_prism_name = arg
                self._active_prism_prompt = prompt
                preview = prompt[:60] + (
                    "..." if len(prompt) > 60 else "")
                print(f"{C.CYAN}Prism: {arg}{C.RESET}")
                print(f"  {C.DIM}{preview}{C.RESET}")
            else:
                print(f"{C.YELLOW}Unknown prism: {arg}{C.RESET}")
                print(f"  {C.DIM}Use /prisms to list available prisms, or:{C.RESET}")
                print(f"  {C.DIM}/prism off        vanilla (no prisms){C.RESET}")
                print(f"  {C.DIM}/prism single     dynamic prism per message{C.RESET}")
                print(f"  {C.DIM}/prism full       dynamic pipeline per message{C.RESET}")

    def _cmd_compact(self, arg):
        """Compact context."""
        self._send_and_stream("/compact")

    def _cmd_cost(self, arg):
        """Print turn/token/cost stats."""
        s = self.session
        print(f"{C.CYAN}Turns: {s.turn_count}  "
              f"In: {s.total_input_tokens:,}  "
              f"Out: {s.total_output_tokens:,}  "
              f"Cost: ${s.total_cost_usd:.4f}{C.RESET}")

    def _cmd_save(self, arg):
        """Save session to named file."""
        if not arg:
            print(f"{C.YELLOW}Usage: /save <name>{C.RESET}")
        elif not self.session.session_id:
            print(f"{C.YELLOW}No active session to save{C.RESET}")
        else:
            path = self.session.save(arg)
            print(f"{C.GREEN}Saved: {path}{C.RESET}")

    def _cmd_load(self, arg):
        """Load a named session or list saved sessions."""
        if not arg:
            saved = Session.list_saved()
            if saved:
                print(f"{C.CYAN}Sessions: {', '.join(saved)}{C.RESET}")
            else:
                print(f"{C.DIM}No saved sessions{C.RESET}")
        elif self.session.load(arg):
            print(f"{C.GREEN}Loaded: {arg} "
                  f"(turn {self.session.turn_count}){C.RESET}")
        else:
            print(f"{C.RED}Session '{arg}' not found{C.RESET}")

    def _cmd_reload_cmd(self, arg):
        """Wrapper for _cmd_reload that also re-registers commands."""
        self._cmd_reload()
        self._commands.clear()
        self._register_builtin_commands()

    def _show_help(self, full=False):
        """Auto-generate help from command registry, grouped by category."""
        # Category display order and headers
        categories = [
            ("analysis", "Analysis"),
            ("fix",      "Fix"),
            ("info",     "Info"),
            ("session",  "Session"),
        ]

        # Collect entries per category, deduplicate aliases
        seen_handlers = set()
        by_category = {c: [] for c, _ in categories}
        for name, entry in self._commands.items():
            handler_fn = getattr(entry["handler"], "__func__", entry["handler"])
            if handler_fn in seen_handlers:
                continue
            seen_handlers.add(handler_fn)
            cat = entry.get("category", "session")
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append((name, entry))

        print()
        for cat_key, cat_label in categories:
            entries = by_category.get(cat_key, [])
            if not entries:
                continue
            print(f"{C.BOLD}{cat_label}:{C.RESET}")
            for name, entry in entries:
                args = entry.get("args", "")
                help_text = entry.get("help", "")
                if args:
                    left = f"  {C.CYAN}{name}{C.RESET} {args}"
                else:
                    left = f"  {C.CYAN}{name}{C.RESET}"
                # Pad left column to ~38 chars (visible chars only)
                visible_left = f"  {name}" + (f" {args}" if args else "")
                pad = max(1, 38 - len(visible_left))
                print(f"{left}{' ' * pad}{help_text}")

            # Brief examples (always shown)
            if cat_key == "analysis":
                print(f"\n  {C.DIM}Getting started:{C.RESET}")
                print(f"  {C.DIM}  /scan auth.py                      structural analysis (1 call, ~$0.05){C.RESET}")
                print(f"  {C.DIM}  /scan auth.py discover              brainstorm domains → numbered list{C.RESET}")
                print(f"  {C.DIM}  /expand 1,3 single                  cook prism per area, run{C.RESET}")
                print(f"  {C.DIM}  /scan auth.py 3way                  WHERE/WHEN/WHY pipeline (any domain){C.RESET}")
                print(f"  {C.DIM}  /scan auth.py meta                  recursive self-analysis (what analysis conceals){C.RESET}")
                print(f"  {C.DIM}  /scan auth.py smart                 adaptive chain (prereq → AgentsKB → analysis → dispute){C.RESET}")
                print(f"  {C.DIM}  /scan auth.py dispute               2 prisms → disagreement synthesis (~$0.15){C.RESET}")
                print(f"  {C.DIM}  /scan auth.py explain               show what would run (no API calls){C.RESET}")
                print(f"  {C.DIM}  /scan auth.py dxf                   discover + expand all as full prism{C.RESET}")
                print(f"  {C.DIM}  /scan auth.py nuclear               Opus + full discover + full expand{C.RESET}")
                print(f'  {C.DIM}  /scan auth.py optimize="security"   cooked strategy + convergence loop{C.RESET}')

                if full:
                    print(f"\n  {C.DIM}Full Prism — multi-pass pipeline:{C.RESET}")
                    print(f"  {C.DIM}  /scan auth.py full                  code: 9-step static pipeline (7 structural + adv + synth){C.RESET}")
                    print(f"  {C.DIM}                                        text: auto-routes to 3-way (WHERE/WHEN/WHY + synth){C.RESET}")
                    print(f"  {C.DIM}  /scan auth.py behavioral              5-pass behavioral analysis pipeline{C.RESET}")
                    print(f"  {C.DIM}  /scan auth.py 3way                    WHERE/WHEN/WHY — 3 cooked operations + synthesis{C.RESET}")
                    print(f"  {C.DIM}                                        (works on any domain — code, text, strategy){C.RESET}")
                    print(f"  {C.DIM}  /scan auth.py meta                    L12 + claim — recursive self-analysis (what analysis conceals){C.RESET}")
                    print(f'  {C.DIM}  /scan auth.py target="X" cooker=simulation   temporal cooker instead of default{C.RESET}')
                    print(f'  {C.DIM}  /scan auth.py target="X" cooker=archaeology  stratigraphic cooker instead of default{C.RESET}')
                    print(f'  {C.DIM}  /scan auth.py target="X" cooker=concealment  L7 diagnostic gap cooker (what conceals what){C.RESET}')
                    print(f"  {C.DIM}  /scan auth.py adaptive                 auto-escalate: SDL→L12→full (stops when depth sufficient){C.RESET}")
                    print(f"  {C.DIM}  /scan synthesize                        aggregate all findings — project-wide patterns{C.RESET}")

                    print(f"\n  {C.DIM}Discover + Expand — two-step workflow:{C.RESET}")
                    print(f"  {C.DIM}  /scan auth.py discover              ~20 focused domains (1 brainstorm pass){C.RESET}")
                    print(f"  {C.DIM}  /scan auth.py discover full         hundreds of domains inc. non-technical{C.RESET}")
                    print(f"  {C.DIM}                                       (multi-pass chaining, each pass builds{C.RESET}")
                    print(f"  {C.DIM}                                       on all prior — finds psychology, legal,{C.RESET}")
                    print(f"  {C.DIM}                                       marketing, embodied cognition, etc.){C.RESET}")
                    print(f"  {C.DIM}  /expand 1,3 full                    cook pipeline per area, run{C.RESET}")
                    print(f"  {C.DIM}  /expand * full                      all areas as full prism{C.RESET}")
                    print(f"  {C.DIM}  /expand 2-4                         prompt single/full per area{C.RESET}")
                    print(f"  {C.DIM}  /expand --refresh                   re-discover, then expand{C.RESET}")

                    print(f"\n  {C.DIM}One-shot aliases:{C.RESET}")
                    print(f"  {C.DIM}  /scan auth.py dxf                   discover → expand all as full{C.RESET}")
                    print(f"  {C.DIM}  /scan auth.py dxs                   discover → expand all as single{C.RESET}")
                    print(f"  {C.DIM}  /scan auth.py dfxf                  discover full → expand all as full{C.RESET}")
                    print(f"  {C.DIM}  /scan auth.py dfxs                  discover full → expand all as single{C.RESET}")
                    print(f"  {C.DIM}  /scan auth.py nuclear              ☢️  Opus + dfxf — the cooker decides scope{C.RESET}")
                    print(f"  {C.DIM}                                       and cost. The .deep/ findings become the{C.RESET}")
                    print(f"  {C.DIM}                                       definitive structural analysis.{C.RESET}")

                    print(f"\n  {C.DIM}Smart + Subsystem + Prereq:{C.RESET}")
                    print(f"  {C.DIM}  /scan auth.py smart                 adaptive chain: prereq → AgentsKB → analysis → dispute{C.RESET}")
                    print(f"  {C.DIM}  /scan auth.py subsystem             per-class/function prism routing{C.RESET}")
                    print(f'  {C.DIM}  /scan "build X" prereq              knowledge gaps → AgentsKB answers{C.RESET}')

                    print(f"\n  {C.DIM}Dispute + Reflect + Explain:{C.RESET}")
                    print(f"  {C.DIM}  /scan auth.py dispute               2 orthogonal prisms + disagreement synthesis{C.RESET}")
                    print(f"  {C.DIM}  /scan auth.py reflect               L12 + meta + constraint history synthesis{C.RESET}")
                    print(f"  {C.DIM}  /scan auth.py explain               preview all modes (no API calls){C.RESET}")
                    print(f"  {C.DIM}  /kb list                            show persistent knowledge base{C.RESET}")
                    print(f"  {C.DIM}  /brainstorm \"your question\"          alias for 3-way on text{C.RESET}")

                    print(f"\n  {C.DIM}Custom goal:{C.RESET}")
                    print(f'  {C.DIM}  /scan auth.py target="race conds"        cook prism for specific goal{C.RESET}')
                    print(f'  {C.DIM}  /scan auth.py target="race conds" full   goal as pipeline{C.RESET}')
                    print(f'  {C.DIM}  /scan auth.py prism="deep_scan"          use a specific prism instead of L12{C.RESET}')

                    print(f"\n  {C.DIM}Optimize — cooked strategy + convergence:{C.RESET}")
                    print(f'  {C.DIM}  /scan auth.py optimize="security"        cook strategy → Claude edits → re-scan{C.RESET}')
                    print(f'  {C.DIM}  /scan auth.py optimize="security" full   multi-phase pipeline per iteration{C.RESET}')
                    print(f'  {C.DIM}  /scan auth.py optimize="perf" max=3      cap iterations (default 5){C.RESET}')
                    print(f'  {C.DIM}  /scan auth.py optimize="perf" domains=5  limit domain count{C.RESET}')

                    print(f"\n  {C.DIM}Fix loop — scan → fix → re-scan:{C.RESET}")
                    print(f"  {C.DIM}  /scan auth.py fix                   interactive: review each fix{C.RESET}")
                    print(f"  {C.DIM}  /scan auth.py fix auto              automatic: apply all, up to 3 passes{C.RESET}")

                    print(f"\n  {C.DIM}Project-level:{C.RESET}")
                    print(f"  {C.DIM}  /scan src/                          L12 on every code file (parallel){C.RESET}")
                    print(f"  {C.DIM}  /scan src/ discover                 project-level domain discovery{C.RESET}")
                    print(f'  {C.DIM}  /scan src/ target="security"        custom goal across project{C.RESET}')
                    print(f'  {C.DIM}  /scan src/ optimize="security"      cooked optimize across project{C.RESET}')

                    print(f"\n  {C.DIM}Works on any text, not just code:{C.RESET}")
                    print(f"  {C.DIM}  /scan \"how should a todo app handle shared state?\"{C.RESET}")

                    print(f"\n  {C.DIM}Domain discovery — brainstorm without a file:{C.RESET}")
                    print(f"  {C.DIM}  /cook legal                         discover domains for legal docs{C.RESET}")
                    print(f"  {C.DIM}  /cook api-design spec.yaml          discover from sample file{C.RESET}")

            if cat_key == "fix":
                print(f"\n  {C.DIM}  /fix                                pick issues from last scan{C.RESET}")
                print(f"  {C.DIM}  /fix auth.py                        auto-scan + fix{C.RESET}")
                print(f"  {C.DIM}  /fix auto                           fix all, up to 3 passes{C.RESET}")
                if full:
                    print(f"  {C.DIM}  /fix auth.py deep                   full prism scan, then fix{C.RESET}")
                    print(f"  {C.DIM}  /scan auth.py fix                   scan + fix in one command{C.RESET}")
                    print(f"  {C.DIM}  /scan auth.py fix auto              scan + fix, fully automatic{C.RESET}")

            if cat_key == "session":
                print(f"\n  {C.DIM}Chat prism modes (/prism controls prism enhancement):{C.RESET}")
                print(f"  {C.DIM}  /prism single                       freshly cooked prism per message{C.RESET}")
                print(f"  {C.DIM}  /prism full                         cooked multi-prism pipeline{C.RESET}")
                print(f"  {C.DIM}  /prism pedagogy                     static prism for all messages{C.RESET}")
                print(f"  {C.DIM}  /prism off                          vanilla chat (default){C.RESET}")
                if full:
                    print(f"  {C.DIM}  /prism legal/contract_analysis      static prism from cooked domain{C.RESET}")
                    print(f"  {C.DIM}  /prism                              show current mode{C.RESET}")

            print()

        print(f"{C.BOLD}Shortcuts:{C.RESET}")
        print(f"  After /scan, type a {C.CYAN}number{C.RESET} (e.g. {C.CYAN}3{C.RESET}) to fix that issue directly")
        print(f"  Type {C.CYAN}status{C.RESET} (no slash) for .deep/ dashboard")
        print(f"  Just type anything — Prism is also a chat (use /prism to add prisms)")
        print(f"  Multi-line: keep typing, {C.CYAN}blank line{C.RESET} sends")
        if not full:
            print(f"\n  {C.DIM}Type /help full for all examples and advanced modes{C.RESET}")
        print()

    def _load_system_prompt(self):
        """Load system prompt: .deep/system.md → ~/.prism_skills/system.md → fallback."""
        local = self.working_dir / ".deep" / "system.md"
        if local.exists():
            try:
                return local.read_text(encoding="utf-8").strip()
            except OSError:
                pass  # Fall through to global path
        global_path = GLOBAL_SKILLS_DIR / "system.md"
        if global_path.exists():
            try:
                return global_path.read_text(encoding="utf-8").strip()
            except OSError:
                pass  # Fall through to built-in fallback
        return self._load_intent("system_prompt_fallback", SYSTEM_PROMPT_FALLBACK)

    # ── Smart flow ─────────────────────────────────────────────────────

    _FILE_RE = re.compile(
        r'(?:^|[\s\'"`(,])('                          # leading boundary
        r'(?:[\w./\\-]+/)?'                            # optional path prefix
        r'[\w.-]+'                                     # filename stem
        r'\.(?:py|js|ts|tsx|jsx|go|rs|java|rb|sh|c|cpp|h|hpp|cs|swift|kt|'
        r'yaml|yml|toml|json|md|html|css|scss|sql|proto|ex|exs|zig|lua|'
        r'vue|svelte)'                                 # extension
        r')(?=[\s\'"`),.:;!?]|$)',                     # trailing boundary
        re.MULTILINE,
    )

    def _detect_file_mentions(self, user_input):
        """Detect file mentions in user input, resolve to real paths.
        Only matches files that exist directly under working_dir — no recursive
        glob fallback, to prevent ghost auto-reads of casually mentioned names.
        Returns list of resolved Path objects (max 3, deduped against queued)."""
        matches = self._FILE_RE.findall(user_input)
        if not matches:
            return []

        # Guard: filter out matches in parenthetical context (explanations, examples).
        # Prevents auto-read of casually mentioned files: "test_runner.py (optional)",
        # "like logger.py", "such as runner.py". Only queue files that are direct references,
        # not explanatory mentions in comments/strings.
        filtered_matches = []
        for match in matches:
            # Check if match is followed by parenthetical explanation like "(optional)"
            # or preceded by contextual words like "like", "such as", "e.g.", "e.g.,"
            idx = user_input.find(match)
            if idx == -1:
                continue
            # Reject if match appears inside parentheses or followed by " (" (e.g., "(optional)")
            if "(" in user_input[max(0, idx - 30):idx]:  # Recently opened paren
                continue
            if user_input[idx + len(match):idx + len(match) + 2] == " (":  # Followed by explanation
                continue
            filtered_matches.append(match)

        queued_set = {p.resolve() for p in self.queued_files}
        resolved = []
        seen = set()

        for mention in filtered_matches:
            mention = mention.replace("\\", "/")
            # Existence check only — direct path relative to working_dir.
            # No glob fallback: broad tree search causes ghost reads for names
            # mentioned in passing (e.g. "like logger.py" or "test_runner.py (optional)").
            candidate = self.working_dir / mention
            if candidate.is_file():
                real = candidate.resolve()
                if real not in seen and real not in queued_set:
                    resolved.append(real)
                    seen.add(real)
                    if len(resolved) >= 3:
                        if len(matches) > 3:
                            print(f"  {C.DIM}(auto-read capped at 3 files"
                                  f"){C.RESET}")
                        break
            else:
                # Guard: Fuzzy match detected filename against actual project files.
                # Prevents false positives like "logger.py" when only "logging.py" exists.
                # Only queue if similarity > 90% (Levenshtein distance via difflib).
                try:
                    actual_files = [f.name for f in self.working_dir.glob("*") if f.is_file()]
                    if actual_files:
                        best_match = max(
                            ((f, difflib.SequenceMatcher(None, mention, f).ratio())
                             for f in actual_files),
                            key=lambda x: x[1],
                            default=(None, 0)
                        )
                        if best_match[1] > 0.9:  # >90% similarity
                            fuzzy_candidate = self.working_dir / best_match[0]
                            if fuzzy_candidate.is_file():
                                real = fuzzy_candidate.resolve()
                                if real not in seen and real not in queued_set:
                                    resolved.append(real)
                                    seen.add(real)
                                    if len(resolved) >= 3:
                                        if len(matches) > 3:
                                            print(f"  {C.DIM}(auto-read capped at 3 files"
                                                  f"){C.RESET}")
                                        break
                except (OSError, StopIteration):
                    pass  # Silently skip if fuzzy matching fails

        return resolved

    def _save_deep_finding(self, file_name, prism_name, output):
        """Save analysis output to .deep/findings/ for future enrichment.

        Appends or updates a ## PRISM section in the per-file findings markdown.
        """
        if not output or len(output.strip()) < 50:
            if output and output.strip():
                print(f"  {C.DIM}(output too short to save — "
                      f"{len(output.strip())} chars, need 50){C.RESET}")
            return
        # Guard: Clean up unbounded cache growth before saving findings.
        # Prevents ~/.prism_skills/ from accumulating GBs and degrading I/O.
        _cleanup_skills_cache()

        # Use parent_stem to avoid collisions (e.g. src/auth.py vs lib/auth.py)
        stem = self._discover_cache_key(file_name)
        findings_dir = self.working_dir / ".deep" / "findings"
        findings_dir.mkdir(parents=True, exist_ok=True)
        findings_path = findings_dir / f"{stem}.md"

        section_header = f"## {prism_name.upper()}"
        new_section = f"{section_header}\n\n{output.strip()}\n\n"

        # Lock protects the read-modify-write against concurrent threads
        # in review() parallel mode
        with self._findings_lock:
            if findings_path.exists():
                existing = findings_path.read_text(encoding="utf-8")
                # Replace existing section or append
                pattern = rf'## {re.escape(prism_name.upper())}\s*\n.*?(?=\n## |\Z)'
                if re.search(pattern, existing, re.DOTALL):
                    # Escape replacement to prevent \d, \1 etc in analysis
                    # output from being interpreted as regex backreferences
                    safe_repl = new_section.strip().replace("\\", "\\\\")
                    updated = re.sub(pattern, safe_repl, existing,
                                     count=1, flags=re.DOTALL)
                else:
                    updated = existing.rstrip() + "\n\n" + new_section
                findings_path.write_text(updated, encoding="utf-8")
            else:
                findings_path.write_text(
                    f"# Findings: {file_name}\n\n{new_section}",
                    encoding="utf-8")

        print(f"  {C.DIM}Saved to .deep/findings/{stem}.md{C.RESET}")

        # B4: Auto-constraint footer (zero API calls)
        # Append analytical constraints to findings — makes
        # limitations transparent without extra model calls.
        _constraint = (
            f"\n---\n"
            f"*Analytical constraints: prism={prism_name}, "
            f"model={self.session.model}, "
            f"S×V=C applies (structural claims reliable, "
            f"specific claims may confabulate). "
            f"For verified analysis: `/scan {file_name} verified` "
            f"or `/scan {file_name} oracle`.*\n")
        with self._findings_lock:
            _existing = findings_path.read_text(encoding="utf-8")
            # Only append if not already present
            if "Analytical constraints:" not in _existing:
                findings_path.write_text(
                    _existing + _constraint, encoding="utf-8")

        # B4 Phase 2: Persist constraint history
        # Append structured entry to .deep/constraint_history.md
        # for cross-scan learning. Called within _save_deep_finding
        # so findings_lock is already released — use simple append.
        try:
            import datetime as _dt_b4
            _hist_path = self.working_dir / ".deep" / "constraint_history.md"
            _hist_path.parent.mkdir(parents=True, exist_ok=True)
            _ts = _dt_b4.datetime.now().strftime("%Y-%m-%d %H:%M")
            _entry = (
                f"\n### {_ts} — {prism_name} on {file_name} "
                f"({self.session.model})\n"
                f"- **Prism**: {prism_name}\n"
                f"- **Model**: {self.session.model}\n"
                f"- **Target**: {file_name}\n"
                f"- **Constraint**: S×V=C applies\n"
                f"---\n")
            with open(_hist_path, "a", encoding="utf-8") as _hf:
                _hf.write(_entry)
            # Cap history at ~200 entries to prevent unbounded growth
            _hist_raw = _hist_path.read_text(encoding="utf-8")
            _blocks = _hist_raw.split("\n### ")
            if len(_blocks) > 200:
                # Keep preamble (first block) + last 199 entries
                _trimmed = (_blocks[0] + "\n### "
                            + "\n### ".join(_blocks[-199:]))
                _hist_path.write_text(_trimmed, encoding="utf-8")
        except (OSError, PermissionError):
            pass  # Best-effort — never crash on history write

        # Evidence ledger: structured claims with provenance.
        # Every conservation law, bug claim, and structural finding becomes
        # a JSON object with source, confidence tier, and falsification path.
        # This is THE bridge from "impressive prose" to "verifiable tool."
        try:
            _ledger_path = (self.working_dir / ".deep"
                            / "evidence_ledger.json")
            _ledger = []
            if _ledger_path.exists():
                try:
                    _ledger = json.loads(
                        _ledger_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    _ledger = []

            # Extract conservation laws
            _laws = re.findall(
                r'[Cc]onservation [Ll]aw[:\s]*[`"\']*(.+?)'
                r'[`"\']*(?:\n|$)', output)
            for law in _laws[:3]:
                law = law.strip()
                if len(law) < 10 or len(law) > 200:
                    continue
                _ledger.append({
                    "type": "conservation_law",
                    "claim": law,
                    "source_file": file_name,
                    "prism": prism_name,
                    "model": self.session.model,
                    "confidence": "STRUCTURAL",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "falsifiable": (
                        "Find a modification that improves BOTH "
                        "sides of the trade-off simultaneously"),
                    "verified": False,
                })

            # Extract bug claims (from bug tables)
            _bugs = re.findall(
                r'\|\s*(.+?)\s*\|\s*(P[0-3]|Critical|High|Medium|Low'
                r'|Fixable|Structural)\s*\|',
                output)
            for desc, severity in _bugs[:10]:
                desc = desc.strip().strip('*')
                if len(desc) < 10 or desc.startswith("---"):
                    continue
                _ledger.append({
                    "type": "bug_claim",
                    "claim": desc[:200],
                    "severity": severity,
                    "source_file": file_name,
                    "prism": prism_name,
                    "model": self.session.model,
                    "confidence": "DERIVED",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "falsifiable": (
                        "Read the source code at the cited "
                        "location and verify the claim"),
                    "verified": False,
                })

            # Cap at 500 entries (rolling window)
            if len(_ledger) > 500:
                _ledger = _ledger[-500:]

            _ledger_path.parent.mkdir(parents=True, exist_ok=True)
            _ledger_path.write_text(
                json.dumps(_ledger, indent=2), encoding="utf-8")
        except (OSError, PermissionError):
            pass  # Best-effort

        # Auto-update profile + KB from EVERY scan, but ONLY
        # when the output contains high-confidence structural markers.
        # Without this gate, the 42% accuracy on production code
        # means wrong facts get persisted and poison future scans.
        _has_structural = (
            output and len(output) > 500
            and any(marker in output for marker in (
                "Conservation Law", "conservation law",
                "CONSERVATION LAW", "× ", "x ",
                "= constant", "STRUCTURAL",
                "[STRUCTURAL]", "## Bug")))
        if _has_structural:
            try:
                self._update_profile(
                    file_name, None, output)
            except Exception:
                pass
            try:
                self._extract_and_queue_knowledge(
                    file_name, output)
            except Exception:
                pass

    def _record_learning(self, event_type, data):
        """Record a learning event to .deep/learning.json.

        B4 Phase 3: Track accepted/rejected fixes, false positives,
        and style constraints for cross-scan learning memory.

        event_type: 'accepted_fix', 'rejected_fix', 'false_positive',
                    'style_constraint'
        data: dict with context (issue title, file, reason, etc.)
        """
        try:
            import json as _json_learn
            import datetime as _dt_learn
            _learn_path = self.working_dir / ".deep" / "learning.json"
            _learn_path.parent.mkdir(parents=True, exist_ok=True)

            # Load existing entries
            _entries = []
            if _learn_path.exists():
                try:
                    _raw = _learn_path.read_text(encoding="utf-8")
                    _entries = _json_learn.loads(_raw)
                    if not isinstance(_entries, list):
                        _entries = []
                except (ValueError, OSError):
                    _entries = []

            # Build new entry
            _entry = {
                "type": event_type,
                "date": _dt_learn.datetime.now().strftime("%Y-%m-%d"),
            }
            _entry.update(data)

            _entries.append(_entry)
            # Cap at 500 entries to prevent unbounded growth
            if len(_entries) > 500:
                _entries = _entries[-500:]
            _learn_path.write_text(
                _json_learn.dumps(_entries, indent=2, ensure_ascii=False),
                encoding="utf-8")
        except (OSError, PermissionError):
            pass  # Best-effort — never crash on learning write

    def _get_active_file_content(self):
        """Return current content of the active file, re-reading from disk if possible.

        Prefers reading from disk via file_arg to avoid stale cached content.
        Falls back to cached content for generated artifacts (directories, text).
        """
        if not self._active_file:
            return None
        file_arg = self._active_file.get("file_arg")
        if file_arg:
            path = self._resolve_file(file_arg)
            if path:
                try:
                    return path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    pass
        return self._active_file.get("content")

    def _load_deep_context(self, files):
        """Load .deep/ context for detected files. Returns XML string or ""."""
        deep_dir = self.working_dir / ".deep"
        if not deep_dir.exists():
            return ""

        parts = []

        # Project summary: issue counts + scan age
        # Guard: acquire findings lock to avoid reading partial writes
        issues_path = deep_dir / "issues.json"
        if issues_path.exists():
            try:
                with self._findings_lock:
                    raw = json.loads(issues_path.read_text(encoding="utf-8"))
                self._ensure_version(raw)
                issues = raw.get("issues", []) if isinstance(raw, dict) else raw
                open_issues = [i for i in issues if i.get("status") != "fixed"]
                if open_issues:
                    counts = {}
                    for i in open_issues:
                        p = i.get("priority", "P2")
                        counts[p] = counts.get(p, 0) + 1
                    count_str = ", ".join(
                        f"{v} {k}" for k, v in sorted(counts.items()))
                    summary_parts = [
                        f"{len(open_issues)} open issues ({count_str})"]
                    # Scan age
                    report = deep_dir / "report.md"
                    if report.exists():
                        age = time.time() - report.stat().st_mtime
                        summary_parts.append(
                            f"Last scan: {self._format_age(age)}")
                    parts.append(
                        f'<project summary="{". ".join(summary_parts)}" />')
            except (json.JSONDecodeError, OSError):
                pass

        # Per-file context
        for fpath in files:
            file_parts = []
            stem = self._discover_cache_key(fpath.name)
            name = fpath.name

            # Findings: extract per-prism summaries + L12 structural
            findings_path = deep_dir / "findings" / f"{stem}.md"
            if findings_path.exists():
                try:
                    with self._findings_lock:
                        text = findings_path.read_text(encoding="utf-8")
                    finding_lines = []
                    # Portfolio prisms: first 2 lines each
                    for prism in self._get_prisms():
                        pattern = (rf'## {re.escape(prism.upper())}\s*\n'
                                   r'(.*?)(?=\n## |\Z)')
                        m = re.search(pattern, text, re.DOTALL)
                        if m:
                            content = m.group(1).strip()
                            lines = [l.strip() for l in content.split("\n")
                                     if l.strip()][:2]
                            if lines:
                                finding_lines.append(
                                    f"- {prism}: {lines[0]}")
                                if len(lines) > 1:
                                    finding_lines.append(
                                        f"  {lines[1]}")
                    # L12 structural: conservation law + meta-law + bug summary
                    l12_pattern = (r'## L12\s*\n(.*?)(?=\n## |\Z)')
                    l12_m = re.search(l12_pattern, text, re.DOTALL)
                    if l12_m:
                        l12_text = l12_m.group(1).strip()
                        # Extract key structural findings (first 20 lines)
                        l12_lines = [l.strip() for l in l12_text.split("\n")
                                     if l.strip()][:20]
                        if l12_lines:
                            finding_lines.append(
                                "- L12 structural: " + l12_lines[0])
                            for line in l12_lines[1:]:
                                finding_lines.append(f"  {line}")
                    if finding_lines:
                        file_parts.append(
                            "[findings]\n" + "\n".join(finding_lines))
                except (OSError, UnicodeDecodeError):
                    pass

            # Issues for this file (cap 5)
            if issues_path.exists():
                try:
                    raw = json.loads(issues_path.read_text(encoding="utf-8"))
                    self._ensure_version(raw)
                    issues = (raw.get("issues", [])
                              if isinstance(raw, dict) else raw)
                    file_issues = [
                        i for i in issues
                        if i.get("status") != "fixed"
                        and name in i.get("file", "")][:5]
                    if file_issues:
                        issue_lines = []
                        for i in file_issues:
                            p = i.get("priority", "P2")
                            iid = i.get("id", "?")
                            title = i.get("title", "")
                            issue_lines.append(
                                f"- {p} #{iid}: {title}")
                        file_parts.append(
                            "[issues]\n" + "\n".join(issue_lines))
                except (json.JSONDecodeError, OSError):
                    pass

            if file_parts:
                parts.append(
                    f'<file-context name="{name}">\n'
                    + "\n".join(file_parts)
                    + "\n</file-context>")

        if not parts:
            return ""
        return "<context>\n" + "\n".join(parts) + "\n</context>"

    def _enrich(self, user_input):
        """Auto-detect files + inject structural context into system prompt.

        Auto-detect files + inject L12 structural context into system prompt.
        Benefits from /scan cached findings on disk.
        """
        detected = self._detect_file_mentions(user_input)

        # Confirm with user before queuing each detected file
        # Skip confirmations in chat mode (would interrupt flow) or if --quiet
        # Unless _force_file_confirm is set (via /force-confirm), which prompts even in chat.
        confirmed = []
        in_chat = self._chat_mode != "off"
        force_confirm = getattr(self, '_force_file_confirm', False)
        for fpath in detected:
            if self._quiet or (in_chat and not force_confirm):
                # Auto-accept in quiet mode or chat mode (unless forced)
                self.queued_files.append(fpath)
                confirmed.append(fpath)
            else:
                try:
                    ans = input(
                        f"  {C.DIM}detected: {fpath.name}{C.RESET} — auto-read? [Y/n] "
                    ).strip().lower()
                except (EOFError, KeyboardInterrupt):
                    ans = "n"
                if ans in ("", "y"):
                    self.queued_files.append(fpath)
                    confirmed.append(fpath)

        # Load cached findings for all relevant files (queued + confirmed)
        context_files = list({p.resolve() for p in self.queued_files})

        # Mtime-based cache invalidation: skip recompute if files unchanged.
        # Track the max mtime of all source + findings files; invalidate when any change.
        if context_files:
            deep_dir = self.working_dir / ".deep" / "findings"
            try:
                all_tracked = list(context_files)
                if deep_dir.exists():
                    for fpath in context_files:
                        fp = deep_dir / f"{self._discover_cache_key(fpath.name)}.md"
                        if fp.exists():
                            all_tracked.append(fp)
                current_mtime = max(f.stat().st_mtime for f in all_tracked if f.exists())
            except (OSError, ValueError):
                current_mtime = 0
            cached_mtime = getattr(self, '_enrichment_mtime', None)
            cached_prompt = getattr(self, '_enrichment_cache', None)
            if (cached_prompt is not None and cached_mtime is not None
                    and current_mtime <= cached_mtime):
                self._enriched_system_prompt = cached_prompt
                return
        deep_ctx = self._load_deep_context(context_files) if context_files else ""

        # Auto-enrich: run L12 oneshot on files without cached findings
        prism_ctx = ""
        if context_files:
            files_without_findings = []
            deep_dir = self.working_dir / ".deep" / "findings"
            for fpath in context_files:
                finding = deep_dir / f"{self._discover_cache_key(fpath.name)}.md" if deep_dir.exists() else None
                if not finding or not finding.exists():
                    files_without_findings.append(fpath)

            if files_without_findings and not in_chat:
                print(f"  {C.DIM}L12 quick analysis...{C.RESET}",
                      end="", flush=True)
                prism_parts = []
                for fpath in files_without_findings[:2]:  # cap at 2 files
                    try:
                        content = fpath.read_text(
                            encoding="utf-8", errors="replace")
                        result = self._run_prism_oneshot(
                            "l12", content, model="haiku")
                        if result and not result.startswith("["):
                            prism_parts.append(
                                f"[{fpath.name} — l12]\n{result}")
                            print(f" {C.CYAN}{fpath.name}{C.RESET}",
                                  end="", flush=True)
                    except Exception:
                        pass
                print()
                if prism_parts:
                    prism_ctx = "\n\n".join(prism_parts)

        # Inject structural context into system prompt
        if deep_ctx or prism_ctx:
            combined_ctx = "\n".join(p for p in [deep_ctx, prism_ctx] if p)
            self._enriched_system_prompt = (
                self.system_prompt + "\n\n"
                "## Structural findings for the code being discussed\n"
                "Use these findings to inform your response — conservation laws, "
                "trade-offs, and structural constraints this code embeds.\n\n"
                + combined_ctx
            )
        else:
            self._enriched_system_prompt = None

        # Store mtime-keyed cache so next call can skip recomputation if unchanged
        if context_files:
            self._enrichment_cache = self._enriched_system_prompt
            try:
                deep_dir = self.working_dir / ".deep" / "findings"
                all_tracked = list(context_files)
                if deep_dir.exists():
                    for fpath in context_files:
                        fp = deep_dir / f"{self._discover_cache_key(fpath.name)}.md"
                        if fp.exists():
                            all_tracked.append(fp)
                self._enrichment_mtime = max(
                    f.stat().st_mtime for f in all_tracked if f.exists())
            except (OSError, ValueError):
                self._enrichment_mtime = 0

        # Feedback
        if confirmed or deep_ctx or prism_ctx:
            feedback = []
            if confirmed:
                names = [p.name for p in confirmed]
                feedback.append(f"auto-read: {', '.join(names)}")
            if deep_ctx:
                feedback.append("+findings from .deep/")
            if prism_ctx:
                feedback.append("+L12 analysis")
            print(f"  {C.DIM}{' | '.join(feedback)}{C.RESET}")

        # Hint: suggest /scan when files detected but no cached findings
        if confirmed and not deep_ctx:
            names = " ".join(p.name for p in confirmed[:2])
            print(f"  {C.DIM}hint: /scan {names} for L12 structural analysis{C.RESET}")

    def _post_response_hint(self, tools_used):
        """Print dim hint after Claude uses Edit/Write tools."""
        if not (tools_used & {"Edit", "Write"}):
            return
        issues_path = self.working_dir / ".deep" / "issues.json"
        if issues_path.exists():
            print(f"  {C.DIM}hint: /fix to verify{C.RESET}")

    def _suggest_next(self, action_type, data=None):
        """Set _last_action and print contextual hints after commands."""
        self._last_action = (action_type, data or {})

        if action_type == "scan":
            # Load issues from .deep/issues.json
            issues_path = self.working_dir / ".deep" / "issues.json"
            if issues_path.exists():
                try:
                    raw = json.loads(issues_path.read_text(encoding="utf-8"))
                    self._ensure_version(raw)
                    issues = raw.get("issues", []) if isinstance(raw, dict) else raw
                    open_issues = [i for i in issues if i.get("status") != "fixed"]
                    if open_issues:
                        # Count by priority
                        counts = {}
                        for i in open_issues:
                            p = i.get("priority", "P2")
                            counts[p] = counts.get(p, 0) + 1
                        parts = [f"{v} {k}" for k, v in
                                 sorted(counts.items())]
                        summary = ", ".join(parts)
                        self._last_action = (action_type, {"issues": issues})
                        print(f"  {C.CYAN}{len(open_issues)} issues "
                              f"({summary}).{C.RESET}\n"
                              f"  {C.DIM}  Type a number to fix one issue{C.RESET}\n"
                              f"  {C.DIM}  /fix          pick issues interactively{C.RESET}\n"
                              f"  {C.DIM}  /fix auto     fix all issues (up to 3 passes){C.RESET}")
                except (json.JSONDecodeError, OSError):
                    pass

            # Smart suggestions based on scan count
            _prof_path = self.working_dir / ".deep" / "profile.json"
            if _prof_path.exists():
                try:
                    _prof = json.loads(
                        _prof_path.read_text(encoding="utf-8"))
                    _n = _prof.get("scan_count", 0)
                    _files = _prof.get("files_analyzed", [])
                    if _n == 1:
                        print(f"  {C.DIM}  /scan {data.get('file', '')} "
                              f"full    deep analysis (9 prisms){C.RESET}")
                    elif _n >= 3 and len(_files) >= 2:
                        print(f"  {C.DIM}  /scan synthesize   "
                              f"aggregate {len(_files)} files "
                              f"for project-wide patterns{C.RESET}")
                    if _n >= 2:
                        print(f"  {C.DIM}  /scan {data.get('file', '')} "
                              f"explain  see all available "
                              f"intelligence{C.RESET}")
                except (ValueError, OSError):
                    pass

    def _check_shortcuts(self, user_input):
        """Check for conversational shortcuts. Returns True if handled."""
        # Bare number → heal that issue directly
        if (user_input.isdigit() and self._last_action
                and self._last_action[0] == "scan"):
            issues = self._last_action[1].get("issues", [])
            target_id = int(user_input)
            issue = next((i for i in issues
                          if i.get("id") == target_id
                          and i.get("status") != "fixed"), None)
            if issue:
                self._heal_single_issue(issue, issues)
                return True
            else:
                print(f"{C.YELLOW}No open issue #{target_id}. "
                      f"/fix to see all.{C.RESET}")
                return True

        # "status" as bare word
        if user_input.lower() == "status":
            self._cmd_status("")
            return True

        return False

    def _heal_single_issue(self, issue, all_issues):
        """Fix a single issue directly (no picker). Supports one retry."""
        deep_dir = self.working_dir / ".deep"
        iid = issue.get("id", "?")
        title = issue.get("title", "untitled")
        print(f"\n  {C.BOLD}{C.CYAN}── Fix #{iid}: {title} ──{C.RESET}")

        attempts = 0
        instructions = ""
        while attempts < 2:
            attempts += 1
            fix_issue = dict(issue)
            if instructions:
                fix_issue["action"] = (
                    f"{issue.get('action', '')} "
                    f"User instructions: {instructions}")

            result, snapshots = self._heal_fix_one(fix_issue)

            if result == "approved":
                _t = self._resolve_file(issue.get("file", ""))
                pre_fix = snapshots.get(str(_t)) if _t else None
                verdict = self._heal_verify(issue, pre_fix_snapshot=pre_fix)
                issue["status"] = verdict
                # Update issue status but preserve original mtimes for drift detection
                self._heal_save_issues(deep_dir, all_issues, snapshot_mtimes=False)
                break
            elif result == "rejected":
                break
            elif result == "instructed":
                try:
                    instructions = input(
                        f"  {C.GREEN}Instructions:{C.RESET} ").strip()
                except (EOFError, KeyboardInterrupt):
                    print()
                    break
                if not instructions:
                    break
                print(f"  {C.DIM}Retrying with instructions...{C.RESET}")
        print()

    def _cmd_status(self, arg):
        """/status — .deep/ dashboard."""
        deep_dir = self.working_dir / ".deep"
        if not deep_dir.exists():
            print(f"{C.DIM}No .deep/ directory. Run /scan first.{C.RESET}")
            return

        print(f"\n  {C.BOLD}.deep/ status{C.RESET}\n")

        # Last scan
        report_path = deep_dir / "report.md"
        if report_path.exists():
            age = time.time() - report_path.stat().st_mtime
            age_str = self._format_age(age)
            findings_dir = deep_dir / "findings"
            file_count = len(list(findings_dir.glob("*.md"))) if findings_dir.exists() else 0
            print(f"  Last scan: {C.CYAN}{age_str}{C.RESET} "
                  f"({file_count} files)")
        else:
            print(f"  Last scan: {C.DIM}none{C.RESET}")

        # Issues
        issues_path = deep_dir / "issues.json"
        if issues_path.exists():
            try:
                # Guard: Capture mtime before read to detect concurrent modifications
                # Prevents reporting stale metrics if file is modified during reporting window
                mtime_before = issues_path.stat().st_mtime
                raw = json.loads(issues_path.read_text(encoding="utf-8"))
                mtime_after = issues_path.stat().st_mtime

                # If file was modified during read, re-read to ensure freshness
                if mtime_after != mtime_before:
                    raw = json.loads(issues_path.read_text(encoding="utf-8"))

                self._ensure_version(raw)
                issues = raw.get("issues", []) if isinstance(raw, dict) else raw
                total = len(issues)
                fixed = sum(1 for i in issues if i.get("status") == "fixed")
                open_issues = [i for i in issues if i.get("status") != "fixed"]
                counts = {}
                for i in open_issues:
                    p = i.get("priority", "P2")
                    counts[p] = counts.get(p, 0) + 1
                parts = [f"{v} {k}" for k, v in sorted(counts.items())]
                summary = ", ".join(parts) if parts else "all fixed"
                pct = int(fixed / total * 100) if total else 0
                print(f"  Issues: {C.CYAN}{total}{C.RESET} total "
                      f"({summary})")
                print(f"  Fixed: {C.GREEN}{fixed}{C.RESET} ({pct}%)")
            except (json.JSONDecodeError, OSError):
                print(f"  Issues: {C.RED}error reading{C.RESET}")
        else:
            print(f"  Issues: {C.DIM}none{C.RESET}")

        # Skills
        skills_dir = deep_dir / "skills"
        skills = []
        if skills_dir.exists():
            skills = [p.stem for p in skills_dir.glob("*.md")
                      if not p.stem.endswith("_prism")]
        global_skills = []
        if GLOBAL_SKILLS_DIR.exists():
            global_skills = [p.stem for p in GLOBAL_SKILLS_DIR.glob("*.md")
                             if not p.stem.endswith("_prism")]
        all_skills = sorted(set(skills + global_skills))
        if all_skills:
            print(f"  Skills: {C.CYAN}{', '.join(all_skills)}{C.RESET}")
        else:
            print(f"  Skills: {C.DIM}none{C.RESET}")

        # Model
        print(f"  Model: {C.CYAN}{self.session.model}{C.RESET}")
        print()

    def _ensure_version(self, data, warn_label=None):
        """Ensure JSON data has _version field. Migrates v0 (missing) to v1."""
        if isinstance(data, dict) and "_version" not in data:
            data["_version"] = 1
            if warn_label:
                print(f"  {C.DIM}Migrated {warn_label} to v1{C.RESET}")
        return data

    @staticmethod
    def _strip_version(data):
        """Return data dict without _version key (for config reads)."""
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if k != "_version"}
        return data

    @staticmethod
    def _format_age(seconds):
        """Format age in seconds to human-readable string."""
        if seconds < 60:
            return "just now"
        if seconds < 3600:
            return f"{int(seconds / 60)}m ago"
        if seconds < 86400:
            return f"{int(seconds / 3600)}h ago"
        return f"{int(seconds / 86400)}d ago"

    # ── Live config layer ────────────────────────────────────────────────

    def _config(self):
        """Read .deep/config.json, merge with defaults. Fresh every call."""
        cfg = dict(DEFAULT_CONFIG)
        path = self.working_dir / ".deep" / "config.json"
        if path.exists():
            try:
                override = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(override, dict):
                    self._ensure_version(override)
                    cfg.update(self._strip_version(override))
            except json.JSONDecodeError:
                if not getattr(self, '_config_warned', False):
                    print(f"  {C.YELLOW}Warning: .deep/config.json has "
                          f"invalid JSON — using defaults{C.RESET}")
                    self._config_warned = True
            except OSError:
                pass
        return cfg

    def _get_prisms(self):
        """Active prism list — reads config fresh, validates files exist."""
        names = self._config().get("prisms", ["l12"])
        valid = []
        for name in names:
            local = self.working_dir / ".deep" / "prisms" / f"{name}.md"
            builtin = PRISM_DIR / f"{name}.md"
            if local.exists() or builtin.exists():
                valid.append(name)
        return valid if valid else ["l12"]

    def _cmd_reload(self):
        """Hot-reload: reimport module, rebind all methods on running instance."""
        import importlib.util
        try:
            spec = importlib.util.spec_from_file_location(
                "_prism_reload", SCRIPT_DIR / "prism.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            old_methods = {n for n in dir(self.__class__)
                          if not n.startswith('__')}
            self.__class__ = mod.PrismREPL
            self._ensure_attributes()
            self._commands.clear()
            new_methods = {n for n in dir(self.__class__)
                          if not n.startswith('__')}
            added = new_methods - old_methods
            removed = old_methods - new_methods
            parts = [f"{len(new_methods)} methods"]
            if added:
                parts.append(f"+{len(added)} new")
            if removed:
                parts.append(f"-{len(removed)} removed")
            prisms = self._get_prisms()
            print(f"  {C.GREEN}Code: {', '.join(parts)}{C.RESET}")
            print(f"  {C.GREEN}Config: "
                  f"{len(prisms)} prisms{C.RESET}")
        except Exception as e:
            print(f"  {C.RED}Reload failed: {e}{C.RESET}")
            print(f"  {C.DIM}Running code unchanged.{C.RESET}")

    # ── Cook (prism generation) ───────────────────────────────────────────

    def _cmd_cook(self, arg):
        """/cook <domain> [input] — discover domains for a given artifact type.

        /cook readme                  — discover domains for analyzing READMEs
        /cook legal-contracts         — discover domains for legal documents
        /cook readme README.md        — discover domains informed by a sample file
        """
        if not arg:
            print(f"{C.YELLOW}Usage: /cook <domain> [sample-file]{C.RESET}")
            return

        parts = arg.split(maxsplit=1)
        domain = parts[0].lower().replace(" ", "-")
        sample_content = None

        # Optional sample file to inform domain discovery
        if len(parts) > 1:
            resolved = self._resolve_file(parts[1])
            if resolved and resolved.is_file():
                try:
                    sample_content = resolved.read_text(
                        encoding="utf-8", errors="replace")[:3000]
                except OSError:
                    pass
            else:
                print(f"{C.YELLOW}Sample file not found: {parts[1]} "
                      f"(discovering without sample){C.RESET}")

        domains = self._discover_domains(domain, sample_content)
        if domains:
            print(f"\n{C.GREEN}Discovered {len(domains)} domains "
                  f"for '{domain}':{C.RESET}")
            for i, d in enumerate(domains, 1):
                print(f"  {C.CYAN}{i}.{C.RESET} {C.GREEN}{d['name']}{C.RESET}")
                if d.get('description'):
                    print(f"     {C.DIM}{d['description']}{C.RESET}")
            print(f"\n  {C.DIM}Use: /scan <file> discover  to discover "
                  f"domains for a specific file{C.RESET}")

    def _discover_domains(self, domain, sample_content=None):
        """Discover domains/areas an artifact could be investigated through.

        Returns list of {name, description, type} dicts, or empty list on failure.
        Type is 'structural' (derivable from artifact) or 'escape' (requires
        external domain knowledge). No prism cooking — just domain brainstorming.
        """
        prompt = COOK_PROMPT.format(domain=domain)
        user_input = (
            f"Discover all the genuinely different domains this artifact "
            f"could be investigated through.")
        if sample_content:
            user_input += (
                f"\n\nSample artifact:\n\n{sample_content}")

        # Scale timeout: 90s base + 30s per 1000 chars of sample
        _timeout = min(180, 90 + len(user_input) // 1000 * 30)
        print(f"{C.CYAN}Discovering domains for '{domain}'...{C.RESET}")
        raw = self._call_model(prompt, user_input, timeout=_timeout,
                               model=COOK_MODEL)

        parsed = self._parse_stage_json(raw, "discover")
        if not isinstance(parsed, list):
            reason = "no response" if not raw else (
                f"got {type(parsed).__name__}" if parsed is not None
                else "unparseable response")
            print(f"{C.RED}Discovery failed ({reason}){C.RESET}")
            if raw:
                print(f"  {C.DIM}{raw[:200]}{'...' if len(raw) > 200 else ''}{C.RESET}")
            return []

        results = []
        for item in parsed:
            name = item.get("name", "").strip()
            desc = item.get("description", "").strip()
            if not name:
                continue
            # Sanitize name
            name = re.sub(r'[^a-z0-9_]', '_', name.lower())
            results.append({
                "name": name,
                "description": desc,
                "type": item.get("type", "structural"),
            })

        return results

    def _cmd_prisms(self, arg):
        """/prisms — prism management hub.

        /prisms                  list all prisms
        /prisms explore          show discovered domains → cook prisms
        /prisms create "goal"    cook a custom prism from free-text goal
        /prisms delete <name>    remove a project-local prism
        """
        stripped = arg.strip()
        lower = stripped.lower()

        if lower == "explore":
            return self._cmd_prisms_explore()
        if lower == "create" or lower.startswith("create "):
            goal = stripped[6:].strip().strip('"').strip("'")
            return self._cmd_prisms_create(goal)
        if lower == "delete" or lower.startswith("delete "):
            name = stripped[6:].strip()
            return self._cmd_prisms_delete(name)

        # Built-in prisms (top-level .md files in PRISM_DIR)
        builtin = []
        for p in sorted(PRISM_DIR.glob("*.md")):
            builtin.append(p.stem)

        # Custom domain prisms (subdirectories in built-in PRISM_DIR)
        domains = {}
        for d in sorted(PRISM_DIR.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                names = [p.stem for p in sorted(d.glob("*.md"))]
                if names:
                    domains[d.name] = names

        # User-created prisms (.deep/prisms/*.md — top-level only)
        local_dir = self.working_dir / ".deep" / "prisms"
        user_prisms = []  # list of (stem, description)
        if local_dir.is_dir():
            for p in sorted(local_dir.glob("*.md")):
                desc = ""
                try:
                    first_line = p.read_text(
                        encoding="utf-8").split("\n", 1)[0]
                    if first_line.startswith("<!-- prism:desc "):
                        desc = first_line[16:]
                        if desc.endswith(" -->"):
                            desc = desc[:-4]
                except OSError:
                    pass
                user_prisms.append((p.stem, desc))

        # Print built-in
        print(f"\n{C.BOLD}Built-in ({len(builtin)}):{C.RESET}")
        for name in builtin:
            marker = ""
            if self._active_prism_name == name:
                marker = f" {C.GREEN}← active{C.RESET}"
            print(f"  {C.CYAN}{name}{C.RESET}{marker}")

        if domains:
            print(f"\n{C.BOLD}Cooked:{C.RESET}")
            for domain, names in domains.items():
                print(f"  {C.BOLD}{domain}/{C.RESET} "
                      f"({len(names)} prisms)")
                for n in names:
                    full = f"{domain}/{n}"
                    marker = ""
                    if self._active_prism_name == full:
                        marker = f" {C.GREEN}← active{C.RESET}"
                    print(f"    {C.DIM}{n}{C.RESET}{marker}")

        # User-created prisms (from /prisms explore or /prisms create)
        if user_prisms:
            print(f"\n{C.BOLD}Your prisms ({len(user_prisms)}):{C.RESET}")
            for name, desc in user_prisms:
                marker = ""
                if self._active_prism_name == name:
                    marker = f" {C.GREEN}← active{C.RESET}"
                desc_tag = f"  {C.DIM}{desc}{C.RESET}" if desc else ""
                print(f"  {C.GREEN}{name}{C.RESET}{marker}{desc_tag}")

        if not domains and not user_prisms:
            print(f"\n  {C.DIM}No custom prisms yet.{C.RESET}")

        # Show active + management hints
        prism = self._active_prism_name or "none"
        depth = self._chat_mode
        print(f"\n{C.DIM}Active: prism={prism}, "
              f"depth={depth}{C.RESET}")
        print(f"{C.DIM}/prism <prism>             activate for chat{C.RESET}")
        print(f"{C.DIM}/prisms explore           cook from discovered domains{C.RESET}")
        print(f"{C.DIM}/prisms create \"goal\"     cook a custom prism{C.RESET}")
        if user_prisms:
            print(f"{C.DIM}/prisms delete <name>     remove a prism{C.RESET}")
        print()

    def _cmd_prisms_explore(self):
        """/prisms explore — show discovered domains, cook prisms for selected ones.

        Bridges discover → prism library. Shows all discovered domains from
        the active file (or all cached discover files), lets user pick domains,
        cooks prisms (without running them), and saves them as reusable prisms.
        """
        # 1. Load discover results
        file_name = None
        content = None
        if self._active_file:
            file_name = self._active_file["name"]
            content = self._get_active_file_content()

        results = self._load_discover_results(file_name)
        if not results:
            # Try loading from any cached discover file
            deep_dir = self.working_dir / ".deep"
            if deep_dir.is_dir():
                for f in sorted(deep_dir.glob("discover_*.json")):
                    try:
                        data = json.loads(f.read_text(encoding="utf-8"))
                        if isinstance(data, dict) and "_version" in data:
                            results = data.get("data", [])
                        elif isinstance(data, list):
                            results = data
                        if results:
                            file_name = f.stem.replace("discover_", "")
                            # Content from active file doesn't match
                            # these discover results — clear it
                            content = None
                            print(f"{C.DIM}Using discover results "
                                  f"from: {file_name}{C.RESET}")
                            break
                    except (json.JSONDecodeError, OSError):
                        continue

        if not results:
            print(f"{C.YELLOW}No discover results found. "
                  f"Run /scan <file> discover first.{C.RESET}")
            return

        # 2. Show domains with prism status
        print(f"\n{C.BOLD}Discovered domains ({len(results)}):{C.RESET}\n")
        local_dir = self.working_dir / ".deep" / "prisms"
        for i, item in enumerate(results, 1):
            name = item["name"]
            slug = re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')[:40]
            has_prism = (local_dir / f"{slug}.md").exists() if local_dir.is_dir() else False
            status = f" {C.GREEN}[cooked]{C.RESET}" if has_prism else ""
            desc = item.get("description", "")
            print(f"  {C.CYAN}{i}.{C.RESET} "
                  f"{C.GREEN}{name}{C.RESET}{status}")
            if desc:
                print(f"     {C.DIM}{desc}{C.RESET}")

        # 3. Prompt for selection
        try:
            sel = input(
                f"\n  Select domains to cook prisms for "
                f"(e.g. 1,3,5 or * for all, Enter to cancel): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not sel:
            return

        indices = self._parse_selection(sel, len(results))
        if not indices:
            print(f"{C.YELLOW}No valid domains selected{C.RESET}")
            return

        # 4. Get content for cooking (need sample artifact)
        if not content:
            # Try to read the file if we have a file_name
            if file_name and file_name != "last":
                path = self._resolve_file(file_name)
                if path:
                    content = path.read_text(encoding="utf-8",
                                             errors="replace")
        if not content:
            # Still works — prisms will be more generic without a sample
            print(f"{C.DIM}No file content — cooking general-purpose "
                  f"prisms{C.RESET}")
            sample = "(no sample artifact provided)"
        else:
            sample = content[:2000] if len(content) > 2000 else content

        # 5. Cook prisms for selected domains
        cooked = []
        local_dir.mkdir(parents=True, exist_ok=True)

        for idx in indices:
            item = results[idx - 1]
            area_name = item["name"]
            slug = re.sub(r'[^a-z0-9]+', '_',
                          area_name.lower()).strip('_')[:40]

            # Guard against shadowing built-in prisms
            if (PRISM_DIR / f"{slug}.md").exists():
                print(f"  {C.YELLOW}{area_name} — would shadow "
                      f"built-in '{slug}', skipping{C.RESET}")
                continue

            prism_path = local_dir / f"{slug}.md"

            # Skip if already cooked
            if prism_path.exists():
                print(f"  {C.DIM}{area_name} — already cooked, "
                      f"skipping{C.RESET}")
                cooked.append((area_name, slug))
                continue

            print(f"  {C.CYAN}Cooking prism: {area_name}{C.RESET}")
            prompt = COOK_UNIVERSAL.format(
                intent=f"analyze: {area_name}")
            user_input = (
                f"Generate one analytical prism for this area: "
                f"{area_name}\n\n"
                f"Sample artifact:\n\n{sample}")

            raw = self._call_model(prompt, user_input, timeout=90,
                                   model=COOK_MODEL)
            parsed = self._parse_stage_json(raw, "cook_prisms_explore")
            if not isinstance(parsed, dict) or "prompt" not in parsed:
                reason = ("no response" if not raw else
                          "missing 'prompt' key" if isinstance(parsed, dict)
                          else "unparseable response")
                print(f"  {C.RED}Failed to cook: "
                      f"{area_name} ({reason}){C.RESET}")
                continue

            text = parsed["prompt"]
            desc = item.get("description", area_name)
            # Prepend metadata comment for /prisms display
            prism_content = f"<!-- prism:desc {desc} -->\n{text}"
            prism_path.write_text(prism_content, encoding="utf-8")
            preview = text[:70] + ("..." if len(text) > 70 else "")
            print(f"  {C.GREEN}{slug}{C.RESET}: "
                  f"{C.DIM}{preview}{C.RESET}")
            cooked.append((area_name, slug))

        # 6. Summary
        if cooked:
            print(f"\n{C.BOLD}{C.GREEN}{len(cooked)} prisms ready:{C.RESET}")
            for area_name, slug in cooked:
                print(f"  /prism {slug}    {C.DIM}← activate for chat{C.RESET}")
            print(f"\n  {C.DIM}Use /prisms to see all prisms{C.RESET}")
        else:
            print(f"\n{C.YELLOW}No prisms cooked{C.RESET}")

    def _cmd_prisms_create(self, goal):
        """/prisms create "goal" — cook a custom prism from free-text goal."""
        if not goal:
            print(f"{C.YELLOW}Usage: /prisms create \"your analysis goal\"{C.RESET}")
            print(f"  {C.DIM}Example: /prisms create \"find race conditions\"{C.RESET}")
            print(f"  {C.DIM}Example: /prisms create \"evaluate API design\"{C.RESET}")
            return

        # Need sample content for cooking
        content = None
        if self._active_file:
            content = self._get_active_file_content()

        if not content:
            # Cook without sample — still works, just less targeted
            print(f"{C.DIM}No active file — cooking a general-purpose "
                  f"prism{C.RESET}")
            sample = "(no sample artifact provided)"
        else:
            sample = content[:2000] if len(content) > 2000 else content

        slug = re.sub(r'[^a-z0-9]+', '_', goal.lower()).strip('_')[:40]
        if not slug:
            slug = "unnamed"

        # Guard against shadowing built-in prisms
        builtin_path = PRISM_DIR / f"{slug}.md"
        if builtin_path.exists():
            print(f"{C.YELLOW}'{slug}' is a built-in prism — "
                  f"choose a different name{C.RESET}")
            return

        local_dir = self.working_dir / ".deep" / "prisms"
        prism_path = local_dir / f"{slug}.md"

        if prism_path.exists():
            print(f"{C.YELLOW}Prism '{slug}' already exists. "
                  f"Delete it first: /prisms delete {slug}{C.RESET}")
            return

        print(f"{C.CYAN}Cooking prism: {goal}{C.RESET}")
        prompt = COOK_UNIVERSAL.format(intent=f"analyze: {goal}")
        user_input = (
            f"Generate one analytical prism for: {goal}\n\n"
            f"Sample artifact:\n\n{sample}")

        raw = self._call_model(prompt, user_input, timeout=90,
                               model=COOK_MODEL)
        parsed = self._parse_stage_json(raw, "cook_prisms_create")
        if not isinstance(parsed, dict) or "prompt" not in parsed:
            reason = ("no response" if not raw else
                      "missing 'prompt' key" if isinstance(parsed, dict)
                      else "unparseable response")
            print(f"{C.RED}Failed to cook prism ({reason}){C.RESET}")
            return

        text = parsed["prompt"]
        local_dir.mkdir(parents=True, exist_ok=True)
        # Prepend metadata comment for /prisms display
        prism_content = f"<!-- prism:desc {goal} -->\n{text}"
        prism_path.write_text(prism_content, encoding="utf-8")

        preview = text[:70] + ("..." if len(text) > 70 else "")
        print(f"{C.GREEN}Created: {slug}{C.RESET}")
        print(f"  {C.DIM}{preview}{C.RESET}")
        print(f"\n  /prism {slug}    {C.DIM}← activate for chat{C.RESET}")

    def _cmd_prisms_delete(self, name):
        """/prisms delete <name> — remove a project-local prism."""
        if not name:
            print(f"{C.YELLOW}Usage: /prisms delete <prism_name>{C.RESET}")
            return

        slug = name.strip()
        local_dir = self.working_dir / ".deep" / "prisms"
        prism_path = local_dir / f"{slug}.md"

        if not prism_path.exists():
            print(f"{C.YELLOW}Prism '{slug}' not found in "
                  f".deep/prisms/{C.RESET}")
            return

        # Don't allow deleting internal cache dirs
        if slug.startswith("_"):
            print(f"{C.YELLOW}Cannot delete internal cache "
                  f"prism '{slug}'{C.RESET}")
            return

        prism_path.unlink()
        print(f"{C.GREEN}Deleted: {slug}{C.RESET}")

        # If this was the active prism, deactivate
        if self._active_prism_name == slug:
            self._active_prism_name = None
            self._active_prism_prompt = None
            self._chat_mode = "off"
            print(f"{C.DIM}Prism deactivated{C.RESET}")

    # ── Deep analysis ────────────────────────────────────────────────────

    def _load_prism(self, name):
        """Load a prism prompt. Supports subdirs: 'readme/promise_credibility'.
        Checks .deep/prisms/ first, then built-in prisms/.

        Validates prism calibration metadata to warn of potential quality degradation.
        Warns regardless of whether prism is cached locally or built-in.
        """
        # CLI --use-prism with raw prompt text (not a file name)
        if name == "__cli__" and getattr(self, '_cli_prism_prompt', None):
            return self._cli_prism_prompt
        # name may contain / for domain subdirs
        rel = pathlib.PurePosixPath(name)
        local = self.working_dir / ".deep" / "prisms" / f"{rel}.md"
        # Backward compat: check old .deep/lenses/ path
        local_legacy = self.working_dir / ".deep" / "lenses" / f"{rel}.md"
        source_path = None
        if local.exists():
            content = local.read_text(encoding="utf-8")
            source_path = local
        elif local_legacy.exists():
            content = local_legacy.read_text(encoding="utf-8")
            source_path = local_legacy
            print(f"  {C.DIM}Note: .deep/lenses/ is deprecated, use .deep/prisms/ instead{C.RESET}", file=sys.stderr)
        else:
            path = PRISM_DIR / f"{rel}.md"
            if path.exists():
                content = path.read_text(encoding="utf-8")
                source_path = path
            else:
                return None

        # Check metadata for calibration staleness (guard clause for quality degradation)
        # This check runs AFTER loading, so it warns for both local and built-in prisms
        if content.startswith("---"):
            try:
                # Extract YAML frontmatter
                end_marker = content.find("---", 3)
                if end_marker > 0:
                    yaml_block = content[3:end_marker].strip()
                    # Parse simple key:value pairs (no full YAML parser needed)
                    metadata = {}
                    for line in yaml_block.split("\n"):
                        if ":" in line:
                            key, val = line.split(":", 1)
                            metadata[key.strip()] = val.strip().strip('"[]')

                    # Alert if prism hasn't been quality-checked recently (> 30 days)
                    # Warns regardless of cache location (local override doesn't suppress warning)
                    if "last_quality_check" in metadata and "quality_check_frequency" in metadata:
                        try:
                            last_check = time.strptime(metadata["last_quality_check"], "%Y-%m-%d")
                            today = time.gmtime()
                            days_stale = (time.mktime(today) - time.mktime(last_check)) / 86400
                            check_interval = metadata["quality_check_frequency"]

                            if days_stale > 30 and check_interval == "weekly":
                                _log_error(
                                    context="prism:calibration_stale",
                                    error_type="CalibrationWarning",
                                    error_msg=f"Prism '{name}' last checked {int(days_stale)} days ago",
                                    details=f"source={source_path}, "
                                            f"quality_baseline={metadata.get('quality_baseline', '?')}, "
                                            f"model_versions={metadata.get('model_versions', '?')}",
                                    working_dir=self.working_dir
                                )
                        except (ValueError, KeyError):
                            pass  # Metadata format issue, continue anyway
            except Exception:
                pass  # Metadata parsing failed, continue anyway

            # Strip frontmatter from prompt content — model shouldn't see metadata
            end_marker = content.find("---", 3)
            if end_marker > 0:
                content = content[end_marker + 3:].lstrip("\n")
        else:
            # Warn if prism lacks calibration metadata entirely (missing calibration_date, model_versions)
            # This prevents silent quality degradation from model drift over 6-12 months
            _log_error(
                context="prism:no_calibration_metadata",
                error_type="CalibrationMissing",
                error_msg=f"Prism '{name}' has no calibration metadata",
                details=f"source={source_path}, "
                        f"recommend: add YAML header with calibration_date, model_versions, quality_baseline, "
                        f"last_quality_check, quality_check_frequency",
                working_dir=self.working_dir
            )

        # P15+P16 lint: warn + auto-fix prisms that lack imperative preamble.
        # Prisms starting with "You are..." or descriptive text risk
        # conversation mode. Prisms starting with "Execute/Name/Prove..."
        # reliably trigger analytical mode.
        _first_line = content.strip().split("\n")[0].strip()
        _imperative_starts = (
            "execute", "name", "prove", "find", "identify",
            "analyze", "for each", "step 1", "phase 1",
            "first:", "list", "derive", "classify")
        _has_imperative = any(
            _first_line.lower().startswith(v)
            for v in _imperative_starts)
        if not _has_imperative and len(content) > 50:
            # Auto-prepend imperative trigger
            content = (
                "Execute every instruction below. Output the "
                "complete analysis.\n\n" + content)

        # Strip prism metadata comment (from /prisms explore/create)
        if content.startswith("<!-- prism:desc "):
            nl = content.find("\n")
            if nl >= 0:
                content = content[nl + 1:]

        return content

    @staticmethod
    def _get_prism_model(name):
        """Get optimal model for a prism from OPTIMAL_PRISM_MODEL.

        Single source of truth: auto-built from YAML frontmatter at startup.
        Returns model name (e.g., 'sonnet') or None if unknown.
        New prisms auto-route by adding optimal_model to their YAML frontmatter.
        """
        return OPTIMAL_PRISM_MODEL.get(name)

    def _load_intent(self, name, fallback=""):
        """Load prompt from .deep/prompts/ -> shipped prompts/ -> fallback."""
        # Tier 1: project-local override
        local = self.working_dir / ".deep" / "prompts" / f"{name}.md"
        if local.exists():
            return local.read_text(encoding="utf-8")
        # Tier 2: shipped prompts
        shipped = PROMPTS_DIR / f"{name}.md"
        if shipped.exists():
            return shipped.read_text(encoding="utf-8")
        # Tier 3: hardcoded fallback
        return fallback

    def _run_prism_oneshot(self, prism_name, content, question="",
                          model=None):
        """Run a single prism analysis (non-streaming). Returns output text."""
        if model is None:
            model = self.session.model
        prompt = self._load_prism(prism_name)
        if not prompt:
            return ""
        msg = content
        if question:
            msg = f"{question}\n\n{content}"
        return self._claude.call(prompt, msg, model=model, timeout=120)

    def _resolve_file(self, arg):
        """Resolve a file path relative to working_dir."""
        if not arg:
            return None
        # Long text inputs (>200 chars) can't be file paths
        if len(arg) > 200:
            return None
        try:
            path = pathlib.Path(arg)
            if not path.is_absolute():
                path = self.working_dir / path
            return path if path.exists() else None
        except (OSError, ValueError):
            return None

    def _get_deep_content(self, file_arg, clear_queued=True):
        """Get content for deep analysis — from arg or queued files.

        Args:
            clear_queued: If True, clear queued_files after reading (default).
                         If False, preserve queued_files for re-reading in loops.
        """
        if file_arg:
            path = self._resolve_file(file_arg)
            if path:
                return path.read_text(encoding="utf-8", errors="replace"), path.name
            else:
                return None, file_arg
        elif self.queued_files:
            parts = []
            names = []
            for fpath in self.queued_files:
                try:
                    parts.append(fpath.read_text(encoding="utf-8", errors="replace"))
                    names.append(fpath.name)
                except Exception:
                    pass
            # Only clear queued_files if explicitly requested, so they can be reused
            # in loops (e.g., _scan_fix_loop re-reading after each iteration)
            if clear_queued:
                self.queued_files.clear()
            return "\n\n".join(parts), ", ".join(names)
        return None, None

    @staticmethod
    def _parse_scan_args(arg):
        """Parse /scan arguments into structured dict.

        Returns {"mode", "arg", "target_goal", "target_mode",
                 "fix_auto", "expand_indices", "expand_mode",
                 "discover_type", "refresh", "optimize_goal",
                 "optimize_mode", "optimize_max", "optimize_domains",
                 "model_override"}.
        Modes: single, full, discover, discover_full, expand,
               discover_expand, target, optimize, fix.
        """
        result = {"mode": "single", "arg": arg, "target_goal": None,
                  "target_mode": None, "fix_auto": False,
                  "expand_indices": None, "expand_mode": None,
                  "discover_type": None, "refresh": False,
                  "prism_override": None, "cooker": None}
        if not arg:
            return result

        # 0. Check for --refresh flag (can apply to any mode)
        if "--refresh" in arg:
            result["refresh"] = True
            arg = arg.replace("--refresh", "").strip()

        # 0b. Check for prism=<name> — explicit prism override
        prism_match = (
            re.search(r'prism\s*=\s*"([^"]+)"', arg) or
            re.search(r"prism\s*=\s*'([^']+)'", arg) or
            re.search(r'prism\s*=\s*(\S+)', arg)
        )
        if prism_match:
            result["prism_override"] = prism_match.group(1)
            arg = (arg[:prism_match.start()]
                   + arg[prism_match.end():]).strip()

        # 0c. Check for cooker=<name> — alternative cooker template
        cooker_match = (
            re.search(r'cooker\s*=\s*"([^"]+)"', arg) or
            re.search(r"cooker\s*=\s*'([^']+)'", arg) or
            re.search(r'cooker\s*=\s*(\S+)', arg)
        )
        if cooker_match:
            result["cooker"] = cooker_match.group(1)
            arg = (arg[:cooker_match.start()]
                   + arg[cooker_match.end():]).strip()

        # 1. Check for deep="..." (backward compat → target full)
        #    deep=N (backward compat → expand N full)
        deep_match = (
            re.search(r'deep\s*=\s*"(.+?)"', arg) or
            re.search(r"deep\s*=\s*'(.+?)'", arg) or
            re.search(r'deep\s*=\s*(\d+)', arg)
        )
        if deep_match:
            val = deep_match.group(1)
            if val.isdigit():
                # deep=N → expand N full
                result["mode"] = "expand"
                result["expand_indices"] = val
                result["expand_mode"] = "full"
            else:
                # deep="..." → target="..." full
                result["mode"] = "target"
                result["target_goal"] = val
                result["target_mode"] = "full"
            result["arg"] = arg[:deep_match.start()].strip()
            return result

        # 2. Check for target="..." — custom goal string only (no numeric index)
        target_match = (
            re.search(r'target\s*=\s*"(.+?)"', arg) or
            re.search(r"target\s*=\s*'(.+?)'", arg)
        )
        if target_match:
            val = target_match.group(1)
            result["mode"] = "target"
            result["target_goal"] = val
            # Check for full/single after the target value
            remainder = arg[target_match.end():].strip()
            if re.search(r'\bfull\b', remainder):
                result["target_mode"] = "full"
            elif re.search(r'\bsingle\b', remainder):
                result["target_mode"] = "single"
            result["arg"] = arg[:target_match.start()].strip()
            return result

        # 2b. Check for optimize="..." — autonomous optimization loop
        optimize_match = (
            re.search(r'optimize\s*=\s*"(.+?)"', arg) or
            re.search(r"optimize\s*=\s*'(.+?)'", arg)
        )
        if optimize_match:
            result["mode"] = "optimize"
            result["optimize_goal"] = optimize_match.group(1)
            result["arg"] = arg[:optimize_match.start()].strip()
            # Check for full/single and config overrides
            remainder = arg[optimize_match.end():].strip()
            if re.search(r'\bfull\b', remainder):
                result["optimize_mode"] = "full"
            # max=N — max iterations
            max_match = re.search(r'\bmax\s*=\s*(\d+)', remainder)
            if max_match:
                result["optimize_max"] = int(max_match.group(1))
            # domains=N — max domains per iteration
            dom_match = re.search(r'\bdomains\s*=\s*(\d+)', remainder)
            if dom_match:
                result["optimize_domains"] = int(dom_match.group(1))
            return result

        # 3. Aliases: dxf/dxs = discover expand * full/single
        #             dfxf/dfxs = discover full expand * full/single
        #             nuclear = Opus + dfxf
        # Use whitespace-separated matching (not \b) to avoid
        # matching keywords inside filenames like nuclear_config.py
        def _alias(kw, s):
            return re.search(r'(?:^|\s)(' + kw + r')(?:\s|$)', s)

        nuclear_match = _alias('nuclear', arg)
        if nuclear_match:
            result["mode"] = "discover_expand"
            result["discover_type"] = "full"
            result["expand_indices"] = "*"
            result["expand_mode"] = "full"
            result["model_override"] = "opus"
            result["arg"] = arg[:nuclear_match.start()].strip() or None
            return result
        dfxf_match = _alias('dfxf', arg)
        if dfxf_match:
            result["mode"] = "discover_expand"
            result["discover_type"] = "full"
            result["expand_indices"] = "*"
            result["expand_mode"] = "full"
            result["arg"] = arg[:dfxf_match.start()].strip() or None
            return result
        dxf_match = _alias('dxf', arg)
        if dxf_match:
            result["mode"] = "discover_expand"
            result["discover_type"] = "single"
            result["expand_indices"] = "*"
            result["expand_mode"] = "full"
            result["arg"] = arg[:dxf_match.start()].strip() or None
            return result
        dfxs_match = _alias('dfxs', arg)
        if dfxs_match:
            result["mode"] = "discover_expand"
            result["discover_type"] = "full"
            result["expand_indices"] = "*"
            result["expand_mode"] = "single"
            result["arg"] = arg[:dfxs_match.start()].strip() or None
            return result
        dxs_match = _alias('dxs', arg)
        if dxs_match:
            result["mode"] = "discover_expand"
            result["discover_type"] = "single"
            result["expand_indices"] = "*"
            result["expand_mode"] = "single"
            result["arg"] = arg[:dxs_match.start()].strip() or None
            return result

        # 4. Chained: discover [full] expand [indices] [single|full]
        #    Use (?:^|\s) to avoid matching inside filenames
        chain_match = re.search(
            r'(?:^|\s)discover\s+full\s+expand\s*(.*?)\s*$', arg)
        if chain_match:
            result["mode"] = "discover_expand"
            result["discover_type"] = "full"
            tail = chain_match.group(1).strip()
            if re.search(r'\bfull\b', tail):
                result["expand_mode"] = "full"
            elif re.search(r'\bsingle\b', tail):
                result["expand_mode"] = "single"
            idx_str = re.sub(r'\b(single|full|all)\b', '', tail).strip()
            result["expand_indices"] = idx_str if idx_str else "*"
            result["arg"] = arg[:chain_match.start()].strip() or None
            return result
        chain_match = re.search(
            r'(?:^|\s)discover\s+expand\s*(.*?)\s*$', arg)
        if chain_match:
            result["mode"] = "discover_expand"
            result["discover_type"] = "single"
            tail = chain_match.group(1).strip()
            if re.search(r'\bfull\b', tail):
                result["expand_mode"] = "full"
            elif re.search(r'\bsingle\b', tail):
                result["expand_mode"] = "single"
            idx_str = re.sub(r'\b(single|full|all)\b', '', tail).strip()
            result["expand_indices"] = idx_str if idx_str else "*"
            result["arg"] = arg[:chain_match.start()].strip() or None
            return result

        # 5. Check for expand with optional indices + prism mode
        #    expand | expand single | expand full | expand 1,3,5 full
        #    Require whitespace before 'expand' so filenames like
        #    expand_routes.py don't match. Bare 'expand' is handled
        #    in step 7 (trailing keywords).
        expand_match = re.search(
            r'(?<=\s)expand\s*(.*?)\s*$', arg)
        if expand_match:
            result["mode"] = "expand"
            tail = expand_match.group(1).strip()
            if re.search(r'\bfull\b', tail):
                result["expand_mode"] = "full"
            elif re.search(r'\bsingle\b', tail):
                result["expand_mode"] = "single"
            idx_str = re.sub(r'\b(single|full)\b', '', tail).strip()
            result["expand_indices"] = idx_str if idx_str else None
            result["arg"] = arg[:expand_match.start()].strip() or None
            return result

        # 6. Check for discover full
        disc_full = re.search(
            r'(?:^|\s)discover\s+full\s*$', arg)
        if disc_full:
            result["mode"] = "discover_full"
            result["arg"] = arg[:disc_full.start()].strip() or None
            return result

        # 7. Trailing keywords
        parts = arg.rsplit(maxsplit=2)
        if (len(parts) >= 3 and parts[-2] == "fix"
                and parts[-1] == "auto"):
            result["mode"] = "fix"
            result["fix_auto"] = True
            result["arg"] = " ".join(parts[:-2])
        elif len(parts) >= 2 and parts[-1] == "fix":
            result["mode"] = "fix"
            result["arg"] = " ".join(parts[:-1])
        elif len(parts) >= 2 and parts[-1] == "behavioral":
            result["mode"] = "behavioral"
            result["arg"] = " ".join(parts[:-1])
        elif len(parts) >= 2 and parts[-1] == "3way":
            result["mode"] = "3way"
            result["arg"] = " ".join(parts[:-1])
        elif len(parts) >= 2 and parts[-1] == "meta":
            result["mode"] = "meta"
            result["arg"] = " ".join(parts[:-1])
        elif len(parts) >= 2 and parts[-1] == "falsify":
            result["mode"] = "falsify"
            result["arg"] = " ".join(parts[:-1])
        elif len(parts) >= 2 and parts[-1] == "reflect":
            result["mode"] = "reflect"
            result["arg"] = " ".join(parts[:-1])
        elif len(parts) >= 2 and parts[-1] == "dispute":
            result["mode"] = "dispute"
            result["arg"] = " ".join(parts[:-1])
        elif len(parts) >= 2 and parts[-1] == "prereq":
            result["mode"] = "prereq"
            result["arg"] = " ".join(parts[:-1])
        elif len(parts) >= 2 and parts[-1] in (
                "verify-claims", "testplan"):
            result["mode"] = "verify_claims"
            result["arg"] = " ".join(parts[:-1])
        elif len(parts) >= 2 and parts[-1] == "subsystem":
            result["mode"] = "subsystem"
            result["arg"] = " ".join(parts[:-1])
        elif len(parts) >= 2 and parts[-1] == "smart":
            result["mode"] = "smart"
            result["arg"] = " ".join(parts[:-1])
        elif len(parts) >= 2 and parts[-1] == "verified":
            result["mode"] = "verified"
            result["arg"] = " ".join(parts[:-1])
        elif len(parts) >= 2 and parts[-1] == "l12g":
            result["mode"] = "l12g"
            result["arg"] = " ".join(parts[:-1])
        elif len(parts) >= 2 and parts[-1] == "gaps":
            result["mode"] = "gaps"
            result["arg"] = " ".join(parts[:-1])
        elif len(parts) >= 2 and parts[-1] == "evolve":
            result["mode"] = "evolve"
            result["arg"] = " ".join(parts[:-1])
        elif len(parts) >= 2 and parts[-1] in ("adaptive", "adapt"):
            result["mode"] = "adaptive"
            result["arg"] = " ".join(parts[:-1])
            # Parse budget= if present
            _budget_m = re.search(r'budget=([0-9.]+)', arg)
            if _budget_m:
                result["budget"] = _budget_m.group(1)
                result["arg"] = re.sub(r'\s*budget=[0-9.]+', '', result["arg"]).strip()
        elif len(parts) >= 1 and parts[-1] in ("synthesize", "synth"):
            result["mode"] = "synthesize"
            result["arg"] = " ".join(parts[:-1]) if len(parts) > 1 else None
        elif len(parts) >= 2 and parts[-1] == "oracle":
            result["mode"] = "oracle"
            result["arg"] = " ".join(parts[:-1])
        elif len(parts) >= 2 and parts[-1] == "scout":
            result["mode"] = "scout"
            result["arg"] = " ".join(parts[:-1])
        elif len(parts) >= 2 and parts[-1] == "strategist":
            result["mode"] = "strategist"
            result["arg"] = " ".join(parts[:-1])
        elif len(parts) >= 2 and parts[-1] == "explain":
            result["mode"] = "explain"
            result["arg"] = " ".join(parts[:-1])
        elif len(parts) >= 2 and parts[-1] in (
                "full", "discover"):
            result["mode"] = parts[-1]
            result["arg"] = " ".join(parts[:-1])
        elif len(parts) == 1 and parts[0] in (
                "full", "discover", "expand", "behavioral", "3way",
                "meta", "reflect", "dispute", "prereq",
                "subsystem", "smart", "verified", "l12g", "gaps",
                "evolve", "oracle", "scout", "strategist",
                "explain", "verify_claims"):
            result["mode"] = parts[0]
            result["arg"] = None

        return result

    def _cmd_scan(self, arg):
        """/scan <file|text|dir> [mode] — structural analysis. See /help full."""
        if not arg:
            print(f"{C.YELLOW}Usage: /scan <file|dir|text> "
                  f"[full|3way|behavioral|smart|subsystem|prereq|dispute|reflect|verified|l12g|gaps|evolve|discover|explain|target=\"...\"|optimize=\"...\"]  "
                  f"{C.RESET}")
            return

        parsed = self._parse_scan_args(arg)
        mode = parsed["mode"]
        arg = parsed["arg"]

        # Synthesize doesn't need a file — runs on accumulated findings
        if mode == "synthesize":
            self._run_synthesize()
            return

        if not arg:
            print(f"{C.YELLOW}Usage: /scan <file|dir|text> "
                  f"[full|3way|behavioral|smart|subsystem|prereq|dispute|reflect|verified|l12g|gaps|evolve|discover|explain|target=\"...\"|optimize=\"...\"]  "
                  f"{C.RESET}")
            return

        input_arg = arg

        # Defensive: ensure input_arg is a string before path operations
        if not isinstance(input_arg, str) or not input_arg.strip():
            print(f"{C.YELLOW}Usage: /scan <file|dir|text> "
                  f"[full|3way|behavioral|smart|subsystem|prereq|dispute|reflect|verified|l12g|gaps|evolve|discover|explain|target=\"...\"|optimize=\"...\"]  "
                  f"{C.RESET}")
            return

        # Try as directory
        resolved = self._resolve_file(input_arg)
        if resolved and resolved.is_dir():
            if mode in ("discover", "discover_full", "discover_expand",
                        "expand", "target", "optimize"):
                # Project-level discover/expand/target
                project_map = self._build_project_map(resolved)
                if not project_map:
                    print(f"{C.RED}No code files found in "
                          f"{resolved}{C.RESET}")
                    return
                dir_name = resolved.name or str(resolved)
                # Set active file context for /expand
                self._active_file = {
                    "content": project_map, "name": dir_name,
                    "general": True, "file_arg": None}
                # Model override (e.g. nuclear → opus)
                model_override = parsed.get("model_override")
                if model_override:
                    print(f"{C.BOLD}{C.CYAN}Model → "
                          f"{model_override}{C.RESET}")
                with self._temporary_model(model_override):
                    if mode == "discover":
                        self._run_discover(
                            project_map, dir_name, general=True)
                    elif mode == "discover_full":
                        self._run_discover_full(
                            project_map, dir_name, general=True)
                    elif mode == "discover_expand":
                        disc_type = parsed.get(
                            "discover_type", "single")
                        if disc_type == "full":
                            ok = self._run_discover_full(
                                project_map, dir_name,
                                general=True)
                            if not ok:
                                print(
                                    f"{C.YELLOW}Full discover "
                                    f"failed — falling back to "
                                    f"single discover{C.RESET}")
                                self._run_discover(
                                    project_map, dir_name,
                                    general=True, refresh=True)
                        else:
                            self._run_discover(
                                project_map, dir_name,
                                general=True)
                        self._run_expand(
                            project_map, dir_name,
                            indices_str=parsed["expand_indices"],
                            expand_mode=parsed["expand_mode"],
                            general=True, refresh=False)
                    elif mode == "target":
                        goal = parsed["target_goal"]
                        target_mode = parsed.get("target_mode")
                        if target_mode == "full":
                            self._run_deep(project_map, dir_name,
                                           goal, general=True)
                        else:
                            self._run_target(
                                project_map, dir_name,
                                goal, general=True,
                                cooker=parsed.get("cooker"))
                    elif mode == "optimize":
                        goal = parsed["optimize_goal"]
                        opt_full = parsed.get(
                            "optimize_mode") == "full"
                        self._run_optimize_loop(
                            project_map, dir_name, goal,
                            general=True, full=opt_full,
                            max_iterations=parsed.get(
                                "optimize_max"),
                            max_domains=parsed.get(
                                "optimize_domains"))
                    else:
                        self._run_expand(
                            project_map, dir_name,
                            indices_str=parsed["expand_indices"],
                            expand_mode=parsed["expand_mode"],
                            general=True,
                            refresh=parsed["refresh"])
                return
            if mode in ("fix",):
                print(f"{C.YELLOW}Fix mode requires a file, "
                      f"not a directory{C.RESET}")
                return
            # Default: L12 batch scan
            self._scan_directory(str(resolved))
            return

        # Try as file
        content, name = self._get_deep_content(input_arg)
        is_file = bool(content)

        if not is_file:
            # Text mode: domain-neutral
            content = input_arg

        # J10: Inject persistent knowledge from .deep/knowledge/
        # Verified facts from prior scans improve accuracy.
        if name:
            _kb_stem = self._discover_cache_key(name)
            _kb_path = (self.working_dir / ".deep" / "knowledge"
                        / f"{_kb_stem}.json")
            if _kb_path.exists():
                try:
                    import json as _json_kb
                    _kb_data = _json_kb.loads(
                        _kb_path.read_text(encoding="utf-8"))
                    if _kb_data and isinstance(_kb_data, list):
                        # Filter expired facts
                        import time as _time_kb
                        _now = _time_kb.time()
                        _active = [f for f in _kb_data
                                   if not f.get("expires")
                                   or f["expires"] > _now]
                        if _active:
                            _facts = "\n".join(
                                f"- {f['claim']} "
                                f"[{f.get('source', '?')}]"
                                for f in _active)
                            content = (
                                f"<verified_knowledge "
                                f"source=\"KB-FACT\">\n"
                                f"Deterministic facts from "
                                f"knowledge base (ground "
                                f"truth, not analysis):\n"
                                f"{_facts}\n"
                                f"</verified_knowledge>\n\n"
                                f"{content}")
                            print(f"  {C.DIM}Loaded "
                                  f"{len(_active)} verified "
                                  f"facts from KB{C.RESET}")
                except (ValueError, OSError):
                    pass  # KB corrupt or unreadable

            # B4 Phase 2b: Inject prior analysis history
            # Shows what prisms/models already analyzed this file,
            # encouraging the model to explore uncovered dimensions.
            try:
                _hist_path = (self.working_dir / ".deep"
                              / "constraint_history.md")
                if _hist_path.exists():
                    _hist_raw = _hist_path.read_text(encoding="utf-8")
                    # Extract entries matching this file
                    _hist_entries = []
                    for _block in _hist_raw.split("\n### "):
                        if not _block.strip():
                            continue
                        if name in _block:
                            _hist_entries.append(
                                "### " + _block.strip()
                                if not _block.startswith("### ")
                                else _block.strip())
                    if _hist_entries:
                        # Take last 3 entries
                        _recent = _hist_entries[-3:]
                        _summary = "\n".join(_recent)
                        content = (
                            f"<prior_analysis>\n"
                            f"This file was previously analyzed "
                            f"{len(_hist_entries)} times. "
                            f"Key findings:\n"
                            f"{_summary}\n"
                            f"Consider exploring dimensions NOT "
                            f"covered by prior analyses.\n"
                            f"</prior_analysis>\n\n"
                            f"{content}")
                        print(f"  {C.DIM}Loaded "
                              f"{len(_hist_entries)} prior "
                              f"analyses{C.RESET}")
            except (OSError, PermissionError):
                pass  # Best-effort

            # B4 Phase 3b: Inject learning memory
            # Known false positives and rejected fixes prevent
            # the model from repeating flagged non-issues.
            try:
                import json as _json_learn_scan
                _learn_path = (self.working_dir / ".deep"
                               / "learning.json")
                if _learn_path.exists():
                    _learn_data = _json_learn_scan.loads(
                        _learn_path.read_text(encoding="utf-8"))
                    if isinstance(_learn_data, list):
                        # Decay: ignore entries older than 30 days
                        import datetime as _dt_decay
                        _cutoff = (_dt_decay.datetime.now()
                                   - _dt_decay.timedelta(days=30)
                                   ).strftime("%Y-%m-%d")
                        _fresh = [
                            e for e in _learn_data
                            if e.get("date", "9999") >= _cutoff]
                        # Filter for this file
                        _file_events = [
                            e for e in _fresh
                            if e.get("file", "") == name
                            or name in e.get("file", "")]
                        _negatives = [
                            e for e in _file_events
                            if e.get("type") in (
                                "false_positive",
                                "rejected_fix")]
                        if _negatives:
                            _items = "\n".join(
                                f"- [{e.get('type')}] "
                                f"{e.get('issue', '')} "
                                f"{e.get('claim', '')} "
                                f"— {e.get('reason', '')}"
                                .strip()
                                for e in _negatives[-10:])
                            content = (
                                f"<learning_context>\n"
                                f"Known false positives for "
                                f"this file:\n"
                                f"{_items}\n"
                                f"These patterns are intentional "
                                f"design choices, not bugs.\n"
                                f"</learning_context>\n\n"
                                f"{content}")
                            print(
                                f"  {C.DIM}Loaded "
                                f"{len(_negatives)} learning "
                                f"events{C.RESET}")
            except (ValueError, OSError, PermissionError):
                pass  # Best-effort

            # C/D: Profile injection — DISABLED for scan context.
            # A/B test (Mar 16) showed neutral effect (1565w vs 1544w).
            # Profile is still maintained for /scan file reflect
            # and smart mode, where it informs the synthesis step.
            # But injecting into the L12 prism adds noise without
            # improving conservation law discovery.

            # E: Cross-project transfer — DISABLED.
            # A/B test (Mar 16) showed injection HURTS:
            # 882w with injection vs 1572w without.
            # Model anchors on provided laws instead of
            # discovering its own. Keep the method for
            # future use but don't inject into scans.
            # _cross = self._get_cross_project_context(
            #     content, name)

        if not name:
            name = input_arg[:40] + ("..." if len(input_arg) > 40 else "")

        general = not is_file

        # Append CLI --context files (extra context alongside main target)
        if getattr(self, '_cli_context_files', None):
            for fpath in self._cli_context_files:
                p = pathlib.Path(fpath)
                if p.exists():
                    ctx = p.read_text(encoding="utf-8", errors="replace")
                    content += (f"\n\n<context_file path=\"{p}\">"
                                f"\n{ctx}\n</context_file>")
                else:
                    print(f"Warning: context file {fpath} not found, "
                          f"skipping", file=sys.stderr)

        # Set active file context for /expand
        self._active_file = {
            "content": content, "name": name, "general": general,
            "file_arg": input_arg if is_file else None}

        # Model override (e.g. nuclear → opus)
        model_override = parsed.get("model_override")
        if model_override:
            print(f"{C.BOLD}{C.CYAN}Model → {model_override}{C.RESET}")

        with self._temporary_model(model_override):
            if mode == "fix":
                if not is_file:
                    print(f"{C.YELLOW}Fix mode requires a file "
                          f"path{C.RESET}")
                    return
                self._scan_fix_loop(content, name,
                                    auto=parsed["fix_auto"])
                return
            elif mode == "full":
                self._run_full_pipeline(
                    content, name, general=general)
            elif mode == "3way":
                self._run_3way_pipeline(
                    content, name, general=general)
            elif mode == "discover":
                self._run_discover(
                    content, name, general=general)
            elif mode == "discover_full":
                self._run_discover_full(
                    content, name, general=general)
            elif mode == "discover_expand":
                disc_type = parsed.get(
                    "discover_type", "single")
                if disc_type == "full":
                    ok = self._run_discover_full(
                        content, name, general=general)
                    if not ok:
                        print(f"{C.YELLOW}Full discover failed"
                              f" — falling back to single "
                              f"discover{C.RESET}")
                        self._run_discover(
                            content, name, general=general,
                            refresh=True)
                else:
                    self._run_discover(
                        content, name, general=general)
                self._run_expand(
                    content, name,
                    indices_str=parsed["expand_indices"],
                    expand_mode=parsed["expand_mode"],
                    general=general, refresh=False)
            elif mode == "expand":
                self._run_expand(
                    content, name,
                    indices_str=parsed["expand_indices"],
                    expand_mode=parsed["expand_mode"],
                    general=general,
                    refresh=parsed["refresh"])
            elif mode == "target":
                goal = parsed["target_goal"]
                target_mode = parsed.get("target_mode")
                if target_mode == "full":
                    self._run_deep(content, name, goal,
                                   general=general)
                else:
                    self._run_target(content, name, goal,
                                     general=general,
                                     cooker=parsed.get("cooker"))
            elif mode == "optimize":
                goal = parsed["optimize_goal"]
                opt_full = parsed.get("optimize_mode") == "full"
                self._run_optimize_loop(
                    content, name, goal, general=general,
                    full=opt_full,
                    max_iterations=parsed.get("optimize_max"),
                    max_domains=parsed.get("optimize_domains"))
            elif mode == "behavioral":
                self._run_behavioral_pipeline(
                    content, name, general=general)
            elif mode == "meta":
                self._run_meta_pipeline(
                    content, name, general=general)
            elif mode == "falsify":
                self._run_falsify(
                    content, name, general=general)
            elif mode == "verified":
                self._run_verified_pipeline(
                    content, name, general=general)
            elif mode == "l12g":
                self._run_l12g(
                    content, name, general=general)
            elif mode == "gaps":
                self._run_gaps_only(
                    content, name, general=general)
            elif mode == "evolve":
                self._run_evolve(
                    content, name, general=general)
            elif mode == "adaptive":
                _budget = parsed.get("budget")
                self._run_adaptive(
                    content, name, general=general,
                    budget=float(_budget) if _budget else None)
            elif mode == "synthesize":
                self._run_synthesize()
                return  # synthesize doesn't need file content
            elif mode == "strategist":
                self._run_strategist(
                    content, name, general=general)
            elif mode == "scout":
                self._run_scout(
                    content, name, general=general)
            elif mode == "explain":
                self._explain_scan(content, name, general=general)
            elif mode == "reflect":
                self._run_reflect(
                    content, name, general=general)
            elif mode == "dispute":
                self._run_dispute(
                    content, name, general=general)
            elif mode == "prereq":
                self._run_prereq(
                    content, name, general=general)
            elif mode == "subsystem":
                self._run_subsystem(
                    content, name, general=general)
            elif mode == "smart":
                self._run_smart(
                    content, name, general=general)
            elif mode == "verify_claims":
                # Read prior findings for this file, run
                # verify_claims prism on the analysis output
                _stem = self._discover_cache_key(name)
                _fp = (self.working_dir / ".deep"
                       / "findings" / f"{_stem}.md")
                if _fp.exists():
                    _analysis = _fp.read_text(
                        encoding="utf-8", errors="replace")
                    print(f"\n{C.BOLD}{C.BLUE}── Verify "
                          f"Claims ── {name} ──{C.RESET}")
                    print(f"  {C.DIM}Reading prior findings "
                          f"({len(_analysis.split())}w)"
                          f"{C.RESET}")
                    with self._temporary_model(
                            self._get_prism_model(
                                "verify_claims") or "sonnet"):
                        self._run_single_prism_streaming(
                            "verify_claims", _analysis,
                            name, general=True)
                else:
                    print(f"{C.YELLOW}No prior findings "
                          f"for {name}. Run /scan first."
                          f"{C.RESET}")
            elif mode == "oracle":
                print(f"\n{C.BOLD}{C.BLUE}── ORACLE ── "
                      f"{name} ──{C.RESET}")
                print(f"  {C.DIM}5-phase: depth → type → "
                      f"correct → reflect → harvest{C.RESET}")
                with self._temporary_model(
                        self._get_prism_model(
                            "oracle") or "sonnet"):
                    output = self._run_single_prism_streaming(
                        "oracle", content, name,
                        general=general)
                if output and output.strip():
                    self._save_deep_finding(
                        name, "oracle", output)
                    print(f"\n{C.GREEN}Oracle complete"
                          f"{C.RESET}")
                self._session_log.append(
                    operation="oracle",
                    file_name=name, lens="oracle",
                    model=self.session.model,
                    mode="oracle")
            else:
                # Single prism: explicit override, or L12/SDL by input type
                prism_override = parsed.get("prism_override")
                if prism_override:
                    # N13 composition warning: audit-type prisms
                    # on raw code produce near-empty output.
                    # They need L12 output as input, not source.
                    _audit_prisms = (
                        "knowledge_audit", "knowledge_boundary",
                        "l12_complement_adversarial",
                        "l12_synthesis")
                    if prism_override in _audit_prisms:
                        print(f"{C.YELLOW}Note: "
                              f"'{prism_override}' works best "
                              f"on L12 output, not raw code. "
                              f"Consider: /scan {name} gaps "
                              f"(runs L12 first, then audit)"
                              f"{C.RESET}")
                    # Prism-specific warnings (Round 40 findings)
                    if prism_override == "sdl_simulation":
                        print(f"{C.YELLOW}Note: sdl_simulation "
                              f"degrades cross-target (7.0-7.5). "
                              f"Consider 'simulation' for deeper "
                              f"temporal analysis (9.0).{C.RESET}")
                    if (prism_override == "codegen"
                            and "haiku" in (self.session.model or "")):
                        print(f"{C.YELLOW}Note: codegen protocol "
                              f"is stochastic on Haiku (P173). "
                              f"Sonnet recommended.{C.RESET}")
                    # Use optimal model for known prisms, unless user overrode
                    _opt = (self._get_prism_model(prism_override)
                            if not model_override else None)
                    print(f"{C.CYAN}Structural analysis "
                          f"({prism_override}){C.RESET}")
                    with self._temporary_model(_opt):
                        self._run_single_prism_streaming(
                            prism_override, content, name, general=general)
                elif is_file:
                    # L12 optimal model: Sonnet (validated 9.3 avg vs Haiku 8.5)
                    _opt_l12 = ((self._get_prism_model("l12") or "sonnet")
                                if not model_override else None)
                    # C1: Show predictor confidence for transparency
                    _l12_text = self._load_prism("l12") or ""
                    if _l12_text:
                        _p, _f = predict_single_shot(
                            _l12_text, content,
                            _opt_l12 or self.session.model or "sonnet")
                        print(f"{C.CYAN}L12 structural analysis"
                              f" ({_opt_l12 or 'sonnet'})"
                              f" P={_p:.0%}{C.RESET}")
                    else:
                        print(f"{C.CYAN}L12 structural analysis"
                              f" ({_opt_l12 or 'sonnet'}){C.RESET}")
                    with self._temporary_model(_opt_l12):
                        self._run_single_prism_streaming(
                            "l12", content, name, general=general)
                else:
                    _m = self.session.model or ""
                    _sonnet = any(x in _m for x in ("sonnet", "opus"))
                    _prism = "l12_universal" if _sonnet else "deep_scan"
                    _label = "l12_universal" if _sonnet else "SDL"
                    # C1: Show predictor for non-code too
                    _nc_text = self._load_prism(_prism) or ""
                    if _nc_text:
                        _p, _ = predict_single_shot(
                            _nc_text, content,
                            self._get_prism_model(_prism) or "sonnet")
                        print(f"{C.CYAN}{_label} structural analysis"
                              f" P={_p:.0%}{C.RESET}")
                    else:
                        print(f"{C.CYAN}{_label} structural analysis"
                              f"{C.RESET}")
                    self._run_single_prism_streaming(
                        _prism, content, name, general=general)
        if is_file:
            self._suggest_next("scan", {"file": name})

    def _explain_scan(self, content, file_name, general=False):
        """Explain what a scan would do without running it.

        Shows available modes, which prisms each mode uses, estimated
        cost, and a recommendation based on input characteristics.
        """
        # Input characteristics
        lines = content.count('\n') + 1
        words = len(content.split())
        is_code = not general

        # Check for existing KB data
        has_kb = False
        if file_name:
            _kb_stem = self._discover_cache_key(file_name)
            _kb_path = (self.working_dir / ".deep" / "knowledge"
                        / f"{_kb_stem}.json")
            has_kb = _kb_path.exists()

        # Check for existing discover data
        has_discover = False
        if file_name:
            _disc_path = (self.working_dir / ".deep"
                          / f"discover_{self._discover_cache_key(file_name)}.json")
            has_discover = _disc_path.exists()

        # Header
        print(f"\n{C.BOLD}{C.BLUE}── EXPLAIN ── "
              f"{file_name} ──{C.RESET}")
        print(f"  {C.DIM}Input: {'code' if is_code else 'text'}, "
              f"{lines} lines, {words} words"
              f"{', has KB data' if has_kb else ''}"
              f"{', has discover cache' if has_discover else ''}"
              f"{C.RESET}\n")

        # Helper to get model display name
        def _model_label(prism_name):
            m = OPTIMAL_PRISM_MODEL.get(prism_name)
            return m if m else "sonnet"

        # ── Session recommendation ──
        file_ext = file_name.rsplit(".", 1)[-1] if "." in file_name else None
        rec_prism, rec_conf, rec_reason = (None, 0, "")
        if hasattr(self, '_session_log'):
            _yt = self._yield_tracker if hasattr(self, '_yield_tracker') else None
            rec_prism, rec_conf, rec_reason = self._session_log.recommend_prism(
                file_name=file_name, file_ext=file_ext, yield_tracker=_yt)
        if rec_prism and rec_conf > 0:
            conf_pct = int(rec_conf * 100)
            print(f"  {C.GREEN}History recommends:{C.RESET} "
                  f"{rec_prism} ({conf_pct}% confidence, {rec_reason})")
            print()

        # ── Single-shot prediction ──
        _default_prism = "l12" if is_code else "deep_scan"
        _default_text = self._load_prism(_default_prism) or ""
        if _default_text:
            _p_ss, _feats = predict_single_shot(
                _default_text, content, _model_label(_default_prism))
            print(f"  {C.CYAN}P(single-shot):{C.RESET} "
                  f"{_p_ss:.0%} for {_default_prism} on {_model_label(_default_prism)} "
                  f"[imp={_feats['imperative_count']}, "
                  f"code={_feats['code_ratio']:.0%}]")
            print()

        # ── Profile intelligence ──
        _prof_path = self.working_dir / ".deep" / "profile.json"
        if _prof_path.exists():
            try:
                _prof = json.loads(_prof_path.read_text(encoding="utf-8"))
                _scan_n = _prof.get("scan_count", 0)
                _laws = _prof.get("conservation_laws", [])
                _files = _prof.get("files_analyzed", [])
                if _scan_n > 0:
                    print(f"  {C.CYAN}Profile:{C.RESET} "
                          f"{_scan_n} prior scans, "
                          f"{len(_laws)} conservation laws, "
                          f"{len(_files)} files analyzed")
                    if _laws:
                        print(f"    {C.DIM}Latest law: "
                              f"{_laws[-1][:80]}{C.RESET}")
                    print()
            except (ValueError, OSError):
                pass

        # ── Pending hypotheses ──
        _hyp_path = self.working_dir / ".deep" / "hypotheses.json"
        if _hyp_path.exists():
            try:
                _hyps = json.loads(_hyp_path.read_text(encoding="utf-8"))
                _unverified = [h for h in _hyps if not h.get("verified")]
                if _unverified:
                    print(f"  {C.CYAN}Unverified hypotheses:{C.RESET} "
                          f"{len(_unverified)}")
                    for h in _unverified[:3]:
                        print(f"    {C.DIM}- {h['hypothesis'][:80]}"
                              f"{C.RESET}")
                    print(f"    {C.DIM}Verify with: /scan <file> "
                          f"target=\"<hypothesis>\"{C.RESET}")
                    print()
            except (ValueError, OSError):
                pass

        # ── Available modes ──
        print(f"{C.BOLD}Available modes:{C.RESET}\n")

        # 1. Default (single)
        if is_code:
            _l12_model = _model_label("l12")
            print(f"  {C.GREEN}(default){C.RESET}  "
                  f"{C.BOLD}Single L12{C.RESET}")
            print(f"              L12 prism on {_l12_model}. "
                  f"1 call, ~$0.05.")
            print(f"              {C.DIM}Finds: conservation laws, "
                  f"meta-laws, bug table.{C.RESET}")
        else:
            _m = self.session.model or ""
            _is_sonnet = any(x in _m for x in ("sonnet", "opus"))
            _prism = "l12_universal" if _is_sonnet else "deep_scan"
            _pm = _model_label(_prism)
            print(f"  {C.GREEN}(default){C.RESET}  "
                  f"{C.BOLD}Single "
                  f"{'l12_universal' if _is_sonnet else 'SDL'}"
                  f"{C.RESET}")
            print(f"              {_prism} prism on {_pm}. "
                  f"1 call, ~$0.05.")
            print(f"              {C.DIM}Finds: conservation laws, "
                  f"structural properties.{C.RESET}")
        print()

        # 2. full
        print(f"  {C.CYAN}full{C.RESET}        "
              f"{C.BOLD}Full Pipeline{C.RESET}")
        if is_code:
            step_descs = []
            for step in STATIC_CODE_PIPELINE:
                m = _model_label(step["prism"])
                step_descs.append(
                    f"{step['role']} ({step['prism']}, {m})")
            print(f"              "
                  f"{len(STATIC_CODE_PIPELINE)}-step "
                  f"pipeline, ~$0.50.")
            print(f"              {C.DIM}Steps:{C.RESET}")
            for i, desc in enumerate(step_descs, 1):
                chain = STATIC_CODE_PIPELINE[i - 1].get(
                    "chain", False)
                marker = " [chained]" if chain else ""
                print(f"              {C.DIM}  {i}. "
                      f"{desc}{marker}{C.RESET}")
        else:
            print(f"              4-call WHERE/WHEN/WHY pipeline "
                  f"(auto-cooked via COOK_3WAY). ~$0.30.")
            print(f"              {C.DIM}Steps:{C.RESET}")
            print(f"              {C.DIM}  1. Archaeology "
                  f"— WHERE (structural layers){C.RESET}")
            print(f"              {C.DIM}  2. Simulation "
                  f"— WHEN (temporal prediction){C.RESET}")
            print(f"              {C.DIM}  3. Structural "
                  f"— WHY (conservation laws){C.RESET}")
            print(f"              {C.DIM}  4. Synthesis "
                  f"(cross-operation integration){C.RESET}")
        print()

        # 3. 3way
        print(f"  {C.CYAN}3way{C.RESET}        "
              f"{C.BOLD}3-Way Pipeline{C.RESET}")
        print(f"              4-call WHERE/WHEN/WHY + synthesis. "
              f"Auto-cooked from your input. ~$0.30.")
        print(f"              {C.DIM}Cross-operation synthesis is "
              f"inherently adversarial (no dedicated adversarial "
              f"pass needed).{C.RESET}")
        print()

        # 4. behavioral
        print(f"  {C.CYAN}behavioral{C.RESET}  "
              f"{C.BOLD}Behavioral Pipeline{C.RESET}")
        _beh_prisms = [
            ("error_resilience", "ERRORS"),
            ("optimize", "COSTS"),
            ("fix_cascade", "ENTAILMENT"),
            ("identity", "DISPLACEMENT"),
        ]
        print(f"              5-call pipeline "
              f"(4 behavioral + synthesis). ~$0.35.")
        print(f"              {C.DIM}Steps:{C.RESET}")
        for prism_name, role in _beh_prisms:
            m = _model_label(prism_name)
            print(f"              {C.DIM}  - "
                  f"{role} ({prism_name}, {m}){C.RESET}")
        print(f"              {C.DIM}  - SYNTHESIS "
              f"(behavioral_synthesis, "
              f"{_model_label('behavioral_synthesis')})"
              f"{C.RESET}")
        print()

        # 5. meta
        print(f"  {C.CYAN}meta{C.RESET}        "
              f"{C.BOLD}Meta Pipeline{C.RESET}")
        print(f"              2-call: L12 -> claim prism on "
              f"L12 output. ~$0.10.")
        print(f"              {C.DIM}Finds what the analysis "
              f"itself conceals.{C.RESET}")
        print()

        # 6. l12g
        print(f"  {C.CYAN}l12g{C.RESET}        "
              f"{C.BOLD}L12-G (gap-aware){C.RESET}")
        print(f"              1-call: analyze -> audit -> "
              f"self-correct ({_model_label('l12g')}). "
              f"~$0.05.")
        print(f"              {C.DIM}Zero confabulation, same "
              f"cost as L12.{C.RESET}")
        print()

        # 7. oracle
        print(f"  {C.CYAN}oracle{C.RESET}      "
              f"{C.BOLD}Oracle{C.RESET}")
        print(f"              1-call, 5-phase: depth -> type "
              f"-> correct -> reflect -> harvest "
              f"({_model_label('oracle')}). ~$0.07.")
        print(f"              {C.DIM}Highest epistemic "
              f"integrity. Max trust, single-pass.{C.RESET}")
        print()

        # 8. gaps
        print(f"  {C.CYAN}gaps{C.RESET}        "
              f"{C.BOLD}Gap Detection{C.RESET}")
        print(f"              3-call: L12 + knowledge_boundary "
              f"+ knowledge_audit. ~$0.15.")
        print(f"              {C.DIM}Shows what NOT to trust "
              f"in the analysis.{C.RESET}")
        print()

        # 9. verified
        print(f"  {C.CYAN}verified{C.RESET}    "
              f"{C.BOLD}Verified Analysis{C.RESET}")
        print(f"              4-call: L12 -> gap detect -> "
              f"extract -> re-run with corrections. "
              f"~$0.20.")
        print(f"              {C.DIM}Highest accuracy mode. "
              f"Re-runs L12 with verified facts.{C.RESET}")
        print()

        # 10. scout
        print(f"  {C.CYAN}scout{C.RESET}       "
              f"{C.BOLD}Scout{C.RESET}")
        print(f"              2-call: Oracle phases 1-2 -> "
              f"targeted verify on flagged claims. "
              f"~$0.12.")
        print(f"              {C.DIM}Best trust-per-dollar "
              f"after Oracle.{C.RESET}")
        print()

        # 11. discover
        print(f"  {C.CYAN}discover{C.RESET}    "
              f"{C.BOLD}Domain Discovery{C.RESET}")
        print(f"              1-call: brainstorm analytical "
              f"angles. ~$0.03.")
        print(f"              {C.DIM}Follow with 'expand' to "
              f"cook + run on discovered areas.{C.RESET}")
        print()

        # 12. fix (code only)
        if is_code:
            print(f"  {C.CYAN}fix{C.RESET}         "
                  f"{C.BOLD}Fix Loop{C.RESET}")
            print(f"              Scan -> extract bugs -> fix "
                  f"-> re-scan. Interactive.")
            print(f"              {C.DIM}Use 'fix auto' for "
                  f"fully automatic mode.{C.RESET}")
            print()

        # 13. evolve
        print(f"  {C.CYAN}evolve{C.RESET}      "
              f"{C.BOLD}Evolve{C.RESET}")
        print(f"              3-call: recursive meta-cooking "
              f"to generate domain-adapted prism. ~$0.15.")
        print(f"              {C.DIM}Saves evolved prism to "
              f".deep/prisms/.{C.RESET}")
        print()

        # 14. dispute
        print(f"  {C.CYAN}dispute{C.RESET}     "
              f"{C.BOLD}Dispute{C.RESET}")
        _da = "l12 + identity" if is_code else "l12_universal + claim"
        print(f"              3-call: {_da} → disagreement "
              f"synthesis. ~$0.15.")
        print(f"              {C.DIM}Surfaces where orthogonal "
              f"prisms disagree. Much of Full's "
              f"self-correction at 33% cost.{C.RESET}")
        print()

        # 15. reflect
        print(f"  {C.CYAN}reflect{C.RESET}     "
              f"{C.BOLD}Reflect{C.RESET}")
        print(f"              3-call: L12 → claim → constraint "
              f"synthesis with history + learning. ~$0.15.")
        print(f"              {C.DIM}Recurring patterns, "
              f"unexplored dimensions, next best scan.{C.RESET}")
        print()

        # 16. strategist
        print(f"  {C.CYAN}strategist{C.RESET}  "
              f"{C.BOLD}Strategist{C.RESET}")
        print(f"              2-call: plan optimal tool sequence "
              f"for a goal + adversarial critique. ~$0.12.")
        print(f"              {C.DIM}Meta-agent: picks the right "
              f"prisms and modes for your goal.{C.RESET}")
        print()

        # 17. prereq
        print(f"  {C.CYAN}prereq{C.RESET}      "
              f"{C.BOLD}Prerequisites{C.RESET}")
        print(f"              2+ calls: identify knowledge gaps "
              f"→ batch query AgentsKB. ~$0.10+.")
        print(f"              {C.DIM}What do you need to know "
              f"BEFORE analyzing this code?{C.RESET}")
        print()

        # 18. subsystem
        if is_code:
            print(f"  {C.CYAN}subsystem{C.RESET}   "
                  f"{C.BOLD}Subsystem Routing{C.RESET}")
            print(f"              N+2 calls: AST split → "
                  f"per-region prisms → cross-subsystem "
                  f"synthesis. ~$0.15-0.55.")
            print(f"              {C.DIM}Different prism per "
                  f"class/function. Highest coverage.{C.RESET}")
            print()

        # 19. smart
        print(f"  {C.CYAN}smart{C.RESET}       "
              f"{C.BOLD}Smart (adaptive chain){C.RESET}")
        print(f"              5+ steps: prereq → AgentsKB → "
              f"{'subsystem' if is_code else '3way'} → "
              f"dispute → profile.")
        print(f"              {C.DIM}System decides the "
              f"pipeline. Self-improving.{C.RESET}")
        print()

        # 20. verify-claims (shown only for code with prior findings)
        _has_prior = False
        if file_name:
            _fp = (self.working_dir / ".deep" / "findings"
                   / f"{self._discover_cache_key(file_name)}.md")
            _has_prior = _fp.exists()
        if is_code and _has_prior:
            print(f"  {C.CYAN}verify-claims{C.RESET} "
                  f"{C.BOLD}Verify Claims{C.RESET}")
            print(f"              1 call: extract testable "
                  f"claims → generate verification commands. "
                  f"~$0.05.")
            print(f"              {C.DIM}Run after any scan. "
                  f"Tells you what it CAN'T verify.{C.RESET}")
            print()

        # ── Recommendation ──
        print(f"{C.BOLD}Recommendation:{C.RESET}\n")

        if is_code:
            if lines > 500:
                rec_mode = "full"
                rec_reason = (
                    "Large file (>500 lines) benefits from "
                    "multi-prism coverage")
            elif has_kb:
                rec_mode = "(default)"
                rec_reason = (
                    "KB data available — L12 will use "
                    "verified facts for higher accuracy")
            else:
                rec_mode = "(default)"
                rec_reason = (
                    "Standard code file — L12 single scan "
                    "gives 9.3 depth at ~$0.05")
            print(f"  {C.GREEN}{C.BOLD}{rec_mode}{C.RESET}"
                  f" — {rec_reason}")
            if rec_mode == "(default)":
                print(f"  {C.DIM}For deeper analysis: "
                      f"/scan {file_name} full{C.RESET}")
            if not has_kb:
                print(f"  {C.DIM}For higher accuracy: "
                      f"/scan {file_name} verified "
                      f"(builds KB){C.RESET}")
        else:
            rec_mode = "(default)"
            rec_reason = (
                "Text input — single prism gives "
                "structural analysis at minimal cost")
            print(f"  {C.GREEN}{C.BOLD}{rec_mode}{C.RESET}"
                  f" — {rec_reason}")
            print(f"  {C.DIM}For deeper analysis: "
                  f"/scan {file_name} 3way{C.RESET}")

        print()

    def _cmd_expand(self, arg):
        """/expand <indices|*> [single|full] — cook + run prisms on discovered areas.

        Uses active file context from last /scan. Requires prior discover.

        /expand 1,3 single     cook 1 prism per area, run
        /expand 1,3 full       cook pipeline per area, run
        /expand * full         all areas as full prism
        /expand 2-4            prompt single/full per area
        /expand --refresh      re-discover first, then expand
        """
        if not self._active_file:
            print(f"{C.YELLOW}No active file. Run /scan <file> first.{C.RESET}")
            return

        name = self._active_file["name"]
        general = self._active_file["general"]

        # Re-read file content to avoid stale data (file may have changed since /scan)
        file_arg = self._active_file.get("file_arg")
        if file_arg:
            path = self._resolve_file(file_arg)
            if path:
                content = path.read_text(encoding="utf-8", errors="replace")
                self._active_file["content"] = content
            else:
                content = self._active_file["content"]
        else:
            content = self._active_file["content"]

        # Parse expand args: [indices] [single|full] [--refresh]
        refresh = False
        expand_mode = None
        indices_str = None

        if arg:
            if "--refresh" in arg:
                refresh = True
                arg = arg.replace("--refresh", "").strip()
            parts = arg.split()
            for p in parts:
                if p in ("single", "full"):
                    expand_mode = p
                elif p not in ("single", "full"):
                    indices_str = p if not indices_str else indices_str
        self._run_expand(content, name, indices_str=indices_str,
                         expand_mode=expand_mode, general=general,
                         refresh=refresh)

    def _scan_fix_loop(self, content, name, auto=False):
        """Closed-loop: scan → extract context → fix → re-scan → done.

        Runs up to 3 iterations. Stops when no new issues found or
        no fixes approved in a pass.
        """
        deep_dir = self.working_dir / ".deep"
        max_iterations = 3
        prev_issues = []

        for iteration in range(1, max_iterations + 1):
            # ── Phase 1: Scan (re-read file on iterations > 1) ──
            if iteration > 1:
                # Don't clear queued_files on re-reads; they might be needed for later iterations
                fresh_content, _ = self._get_deep_content(name, clear_queued=False)
                if fresh_content:
                    content = fresh_content
                print(f"\n  {C.BOLD}{C.CYAN}── Re-scan (iteration "
                      f"{iteration}/{max_iterations}) ──{C.RESET}\n")

            print(f"{C.CYAN}L12 structural analysis{C.RESET}")
            scan_output = self._run_single_prism_streaming(
                "l12", content, name)

            if not scan_output:
                print(f"{C.YELLOW}Scan produced no output{C.RESET}")
                break

            # ── Phase 2: Extract structural context ──
            structural_context = self._extract_structural_context(
                scan_output)
            if structural_context:
                print(f"  {C.DIM}Structural context extracted "
                      f"({len(structural_context)} chars){C.RESET}")

            # ── Phase 3: Extract issues ──
            issues_path = deep_dir / "issues.json"
            if issues_path.exists():
                issues_path.unlink()

            print(f"  {C.DIM}Extracting issues from findings...{C.RESET}")
            issues = self._heal_extract_from_reports(deep_dir)

            if not issues:
                print(f"{C.GREEN}No issues found.{C.RESET}")
                break

            # On re-scan, only fix genuinely new issues
            if iteration > 1:
                issues = self._diff_issues(prev_issues, issues)
                if not issues:
                    print(f"  {C.GREEN}No new issues — loop "
                          f"complete.{C.RESET}")
                    break
                print(f"  {C.DIM}{len(issues)} new issue(s) "
                      f"to fix{C.RESET}")

            self._heal_save_issues(deep_dir, issues)
            prev_issues.extend(issues)

            # ── Phase 4: Fix each issue with structural context ──
            open_issues = [i for i in issues
                           if i.get("status") != "fixed"]
            if not open_issues:
                print(f"  {C.GREEN}All issues already fixed!{C.RESET}")
                break

            print(f"\n  {C.BOLD}{C.CYAN}FIX{C.RESET}  "
                  f"{len(open_issues)} issue(s)"
                  f"{' (auto)' if auto else ''}\n")

            if auto:
                self._auto_mode = True

            try:
                approved_count = 0
                for idx, issue in enumerate(open_issues, 1):
                    title = issue.get("title", "untitled")
                    print(f"  {C.BOLD}{C.CYAN}── Issue {idx}/"
                          f"{len(open_issues)}: {title} ──"
                          f"{C.RESET}")

                    attempts = 0
                    instructions = ""
                    while attempts < 2:
                        attempts += 1
                        fix_issue = dict(issue)
                        if instructions:
                            fix_issue["action"] = (
                                f"{issue.get('action', '')} "
                                f"User instructions: "
                                f"{instructions}")

                        result, snapshots = self._heal_fix_one(
                            fix_issue,
                            structural_context=structural_context)

                        if result == "approved":
                            approved_count += 1
                            _t = self._resolve_file(
                                fix_issue.get("file", ""))
                            pre_fix = (snapshots.get(str(_t))
                                       if _t else None)
                            verdict = self._heal_verify(
                                issue, pre_fix_snapshot=pre_fix)
                            issue["status"] = verdict
                            break
                        elif result == "rejected":
                            break
                        elif result == "instructed":
                            if auto:
                                break
                            try:
                                instructions = input(
                                    f"  {C.GREEN}Instructions:"
                                    f"{C.RESET} ").strip()
                            except (EOFError, KeyboardInterrupt):
                                print()
                                break
                            if not instructions:
                                break
                            print(f"  {C.DIM}Retrying with "
                                  f"instructions...{C.RESET}")
                    print()

            finally:
                self._auto_mode = False

            # Update issues but preserve original mtimes for drift detection
            self._heal_save_issues(deep_dir, issues, snapshot_mtimes=False)

            # Termination: no fixes approved → stop
            if approved_count == 0:
                print(f"  {C.DIM}No fixes approved — stopping "
                      f"loop.{C.RESET}")
                break

            # Last iteration — don't re-scan
            if iteration == max_iterations:
                print(f"  {C.DIM}Max iterations reached "
                      f"({max_iterations}).{C.RESET}")
                break

            # Ask whether to re-scan (interactive only)
            if not auto:
                try:
                    cont = input(
                        f"  {C.GREEN}Re-scan to verify? "
                        f"(y/n):{C.RESET} ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    print()
                    break
                if cont not in ("y", "yes"):
                    break

        # Final summary
        self._suggest_next("scan", {"file": name})

    # ── OPTIMIZE loop ─────────────────────────────────────────────
    def _run_optimize_loop(self, content, name, goal, general=False,
                           full=False, max_iterations=None,
                           max_domains=None):
        """Autonomous optimization via cooked strategy with convergence.

        Each iteration: cook strategy → Claude executes with tools →
        re-read file → if unchanged, converged. If changed, cook new
        strategy with context about previous work → repeat.

        Single: 1 cooked strategy per iteration.
        Full: N-phase pipeline per iteration.

        Convergence signal: file content unchanged after a pass.
        For text mode (general=True): single pass only (no file).

        Usage:
            /scan file.py optimize="maximize security"
            /scan file.py optimize="security" full max=5
        """
        import time as _time

        cost_before = getattr(self.session, 'total_cost_usd', 0)
        start_time = _time.time()
        max_iters = max_iterations or 5

        mode_label = "Full Prism" if full else "Single Prism"
        print(f"\n{C.BOLD}{C.CYAN}OPTIMIZE: {goal}{C.RESET}")
        print(f"  {C.DIM}Target: {name} | {mode_label} | "
              f"Max iterations: {max_iters}{C.RESET}\n")

        # Build context for cooker
        domain = self._infer_domain(content, name, general)
        constraints_parts = []
        if max_domains:
            constraints_parts.append(
                f"Focus on at most {max_domains} areas")
        constraints = ". ".join(constraints_parts) if constraints_parts \
            else "No constraints \u2014 use your judgment."

        prev_work = ""
        iterations_run = 0

        self._auto_mode = True
        try:
            for iteration in range(1, max_iters + 1):
                iterations_run = iteration
                if iteration > 1:
                    print(f"\n{C.BOLD}{C.BLUE}"
                          f"\u2550\u2550\u2550 Iteration "
                          f"{iteration}/{max_iters} "
                          f"\u2550\u2550\u2550{C.RESET}")

                sample = content[:3000]
                content_before = content

                if full:
                    output = self._optimize_full(
                        content, name, goal, domain,
                        constraints, sample, general,
                        prev_work)
                else:
                    output = self._optimize_single(
                        content, name, goal, domain,
                        constraints, sample, general,
                        prev_work)

                if self._interrupted:
                    break

                # Text mode: single pass (no file to re-check)
                if general:
                    break

                # Re-read file to check for modifications
                fresh, _ = self._get_deep_content(
                    name, clear_queued=False)
                if not fresh or fresh == content_before:
                    if iteration == 1:
                        print(f"\n  {C.GREEN}Complete: "
                              f"no changes needed.{C.RESET}")
                    else:
                        print(f"\n  {C.GREEN}Converged after "
                              f"{iteration} iterations: no "
                              f"further changes.{C.RESET}")
                    break

                # File was modified — accumulate context
                content = fresh
                if output:
                    prev_work += (
                        f"\n\n[Iteration {iteration}]:\n"
                        f"{output[:2000]}")
                print(f"  {C.DIM}File modified \u2014 "
                      f"re-cooking...{C.RESET}")
            else:
                # Loop exhausted without break
                print(f"\n  {C.YELLOW}Reached max iterations "
                      f"({max_iters}).{C.RESET}")
        finally:
            self._auto_mode = False

        # Summary
        elapsed = _time.time() - start_time
        cost_after = getattr(self.session, 'total_cost_usd', 0)
        optimize_cost = cost_after - cost_before
        print(f"\n{C.BOLD}{C.GREEN}\u2550\u2550\u2550 OPTIMIZE complete "
              f"\u2550\u2550\u2550{C.RESET}")
        print(f"  Goal: {goal} ({mode_label})")
        print(f"  Iterations: {iterations_run}")
        print(f"  Time: {elapsed:.0f}s")
        if optimize_cost > 0:
            print(f"  Cost: ${optimize_cost:.4f}")
        print(f"  Findings in .deep/findings/")

        # TRACK: log optimize operation
        self._session_log.append(
            operation="optimize",
            intent=goal,
            file_name=name,
            model=self.session.model,
            mode="full" if full else "single",
            cost_estimate=round(optimize_cost, 6) if optimize_cost > 0 else None,
            duration_sec=elapsed,
        )

    def _optimize_single(self, content, name, goal, domain,
                         constraints, sample, general,
                         prev_work=""):
        """Cook and execute a single optimization strategy.

        Returns output text (for convergence loop context).
        """
        print(f"  {C.CYAN}Cooking optimization strategy...{C.RESET}")
        _opt_intent = (
            f"optimize for: {goal} (agent has tools: Read, Edit, "
            f"Write, Glob, Grep — make changes directly)")
        if constraints and constraints != "none":
            _opt_intent += f" constraints: {constraints}"
        cook_prompt = COOK_UNIVERSAL.format(intent=_opt_intent)
        cooker_msg = f"Goal: {goal}\n\nArtifact ({name}):\n\n{sample}"
        if prev_work:
            cooker_msg += (
                f"\n\nPrevious optimization work (build on this, "
                f"don't repeat):\n{prev_work[:3000]}")
        raw = self._call_model(
            cook_prompt, cooker_msg, timeout=60, model=COOK_MODEL)
        parsed = self._parse_stage_json(raw, "optimize_cook_single")

        if isinstance(parsed, dict) and parsed.get("prompt"):
            strategy = parsed["prompt"]
        else:
            strategy = (
                f"You are an optimization agent. Your goal: {goal}. "
                f"Read the file '{name}', analyze it thoroughly, "
                f"make specific improvements, and verify your changes. "
                f"Be systematic: identify issues, fix them, confirm "
                f"fixes work.")

        print(f"  {C.CYAN}Executing strategy...{C.RESET}\n")

        backend = ClaudeBackend(
            model=self.session.model,
            working_dir=str(self.working_dir),
            system_prompt=strategy,
            tools=True,
        )
        content_label = "input" if general else "source code"
        msg = (f"Optimize this {content_label} for: {goal}\n\n"
               f"File: {name}\n\n{content}")
        output = self._stream_and_capture(backend, msg)

        if output:
            self._save_deep_finding(name, "optimize", output)
        return output or ""

    def _optimize_full(self, content, name, goal, domain,
                       constraints, sample, general,
                       prev_work=""):
        """Cook and execute a multi-phase optimization pipeline.

        Returns accumulated output text (for convergence loop context).
        """
        print(f"  {C.CYAN}Cooking optimization pipeline..."
              f"{C.RESET}")
        _opt_intent = (
            f"optimize for: {goal} (agents have tools: Read, Edit, "
            f"Write, Glob, Grep — each phase makes changes directly)")
        if constraints and constraints != "none":
            _opt_intent += f" constraints: {constraints}"
        cook_prompt = COOK_3WAY.format(
            intent=_opt_intent)
        cooker_msg = (
            f"Generate a 3-way optimization pipeline for: {goal}"
            f"\n\nArtifact ({name}):\n\n{sample}")
        if prev_work:
            cooker_msg += (
                f"\n\nPrevious optimization work (build on this, "
                f"don't repeat):\n{prev_work[:3000]}")
        raw = self._call_model(
            cook_prompt, cooker_msg, timeout=90, model=COOK_MODEL)
        phases = self._parse_stage_json(
            raw, "optimize_cook_full")

        if not isinstance(phases, list) or len(phases) < 2:
            print(f"  {C.YELLOW}Pipeline cook failed \u2014 "
                  f"falling back to single{C.RESET}")
            return self._optimize_single(
                content, name, goal, domain,
                constraints, sample, general,
                prev_work)

        accumulated = ""
        # Filter to valid phase dicts with prompts
        valid_phases = [
            p for p in phases
            if isinstance(p, dict) and p.get("prompt")]
        if not valid_phases:
            print(f"  {C.YELLOW}No valid phases in pipeline "
                  f"\u2014 falling back to single{C.RESET}")
            return self._optimize_single(
                content, name, goal, domain,
                constraints, sample, general,
                prev_work)

        phase_count = len(valid_phases)
        for pi, phase in enumerate(valid_phases, 1):
            phase_name = phase.get("name", f"phase_{pi}")
            phase_prompt = phase["prompt"]

            print(f"\n{C.BOLD}{C.BLUE}\u2500\u2500 Phase {pi}/"
                  f"{phase_count}: {phase_name} "
                  f"\u2500\u2500{C.RESET}")

            # Re-read artifact (may have been modified by
            # previous phase)
            if pi > 1:
                fresh, _ = self._get_deep_content(
                    name, clear_queued=False)
                if fresh:
                    content = fresh

            content_label = "input" if general else "source code"
            msg = (f"Optimize this {content_label} for: "
                   f"{goal}\n\nFile: {name}\n\n{content}")
            if accumulated:
                msg += (f"\n\n--- Previous phases ---\n"
                        f"{accumulated[:5000]}")

            backend = ClaudeBackend(
                model=self.session.model,
                working_dir=str(self.working_dir),
                system_prompt=phase_prompt,
                tools=True,
            )
            output = self._stream_and_capture(backend, msg)

            if output:
                accumulated += (
                    f"\n\n[{phase_name}]:\n"
                    f"{output[:2000]}")
                self._save_deep_finding(
                    name, f"optimize_{phase_name}",
                    output)

            if self._interrupted:
                break

        return accumulated

    def _build_project_map(self, dir_path):
        """Build a compact project summary for project-level discover.

        Returns a string with: file tree + first 5 lines of each file
        (signatures, imports, class names). Keeps it under ~4000 chars
        so the cooker can reason about the whole project cheaply.
        """
        files = self._collect_files(str(dir_path))
        if not files:
            return ""

        parts = [f"# Project: {dir_path.name}\n",
                 f"{len(files)} files\n\n## File tree\n"]

        # File tree with sizes
        for f in files:
            try:
                rel = f.relative_to(dir_path)
            except ValueError:
                rel = f.name
            size = f.stat().st_size
            parts.append(f"  {rel} ({size} bytes)")

        # Sample: first 5 lines of each file (imports, class defs)
        parts.append("\n\n## File signatures\n")
        budget = 3000
        for f in files:
            if budget <= 0:
                parts.append(f"\n... ({len(files)} files total)")
                break
            try:
                rel = f.relative_to(dir_path)
            except ValueError:
                rel = f.name
            try:
                lines = f.read_text(
                    encoding="utf-8", errors="replace"
                ).splitlines()[:5]
                snippet = "\n".join(lines)
                entry = f"\n### {rel}\n```\n{snippet}\n```\n"
                parts.append(entry)
                budget -= len(entry)
            except Exception:
                pass

        return "\n".join(parts)

    def _scan_directory(self, target):
        """Scan all code files in a directory with L12, save findings."""
        files = self._collect_files(target)
        if not files:
            print(f"{C.RED}No files found: {target}{C.RESET}")
            return

        deep_dir = self.working_dir / ".deep" / "findings"
        self._cleanup_old_findings(deep_dir)
        deep_dir.mkdir(parents=True, exist_ok=True)

        print(f"{C.BOLD}Scan: {len(files)} files x L12{C.RESET}")
        print(f"{C.DIM}Saving to .deep/findings/{C.RESET}\n")

        for i, fpath in enumerate(files, 1):
            try:
                content = fpath.read_text(encoding="utf-8", errors="replace")
                print(f"  {C.DIM}[{i}/{len(files)}] {fpath.name}{C.RESET}")
                result = self._run_prism_oneshot("l12", content)
                if result and not result.startswith("["):
                    self._save_deep_finding(fpath.name, "l12", result)
            except Exception as e:
                print(f"  {C.RED}Error: {fpath.name}: {e}{C.RESET}")

        print(f"\n{C.GREEN}Scan complete: {len(files)} files{C.RESET}")
        print(f"  {C.DIM}Findings: .deep/findings/<file>.md{C.RESET}")
        self._suggest_next("scan")

    def _run_full_pipeline(self, content, file_name, general=False):
        """Full Prism: static champion pipeline for code, cooked for general.

        CODE (general=False): 9-step static pipeline using validated champion
        prisms at optimal models. Each prism uses its best model from
        OPTIMAL_PRISM_MODEL. Steps 1-6 are independent structural analysis.
        Step 7 is adversarial (attacks L12 output). Step 8 is synthesis
        (combines all prior outputs).

        GENERAL (general=True): Auto-cooked via COOK_3WAY (WHERE/WHEN/WHY +
        synthesis). Produces 3 orthogonal operations + cross-operation synthesis.
        """
        if general:
            return self._run_full_pipeline_cooked(content, file_name)

        return self._run_full_pipeline_static(content, file_name)

    def _run_full_pipeline_static(self, content, file_name):
        """Static champion pipeline for code: 6 prisms + adversarial + synthesis.

        Uses OPTIMAL_PRISM_MODEL for per-prism model selection.
        User's -m flag is ignored for individual prisms (quality-first default).
        """
        print(f"{C.CYAN}Full Prism: static champion pipeline "
              f"({len(STATIC_CODE_PIPELINE)} steps, optimal models){C.RESET}")

        # Show pipeline structure
        for step in STATIC_CODE_PIPELINE:
            model = self._get_prism_model(step["prism"]) or "sonnet"
            print(f"    {C.GREEN}{step['role']}{C.RESET} "
                  f"({step['prism']}) → {C.DIM}{model}{C.RESET}")

        # Warn when pipeline overrides user's model selection
        user_model = self.session.model
        pipeline_models = set(
            self._get_prism_model(s["prism"]) or "sonnet"
            for s in STATIC_CODE_PIPELINE)
        if user_model not in pipeline_models:
            print(f"  {C.DIM}Note: using {', '.join(sorted(pipeline_models))} "
                  f"instead of {user_model} (optimal for quality){C.RESET}")

        outputs = {}  # keyed by prism name
        output_list = []  # ordered for synthesis

        for step in STATIC_CODE_PIPELINE:
            if self._interrupted:
                break

            prism_name = step["prism"]
            role = step["role"]
            chain = step["chain"]
            optimal_model = self._get_prism_model(prism_name) or "sonnet"

            # A3: Conditional pipeline step — skip if condition not met
            condition = step.get("condition")
            if condition:
                if condition == "has_l12" and "l12" not in outputs:
                    print(f"  {C.DIM}Skipping {role} — "
                          f"L12 output required{C.RESET}")
                    continue
                if condition == "has_security_keywords":
                    _security = any(k in content.lower() for k in
                                    ("auth", "token", "password", "secret",
                                     "permission", "role", "csrf", "xss",
                                     "inject", "sanitiz", "encrypt"))
                    if not _security:
                        print(f"  {C.DIM}Skipping {role} — "
                              f"no security signals{C.RESET}")
                        continue
                if condition == "large_file" and len(content) < 5000:
                    print(f"  {C.DIM}Skipping {role} — "
                          f"file too small ({len(content)} chars){C.RESET}")
                    continue

            # Resolve model: use optimal (dict or frontmatter), mapped through MODEL_MAP
            resolved_model = MODEL_MAP.get(optimal_model, optimal_model)

            prompt = self._load_prism(prism_name)
            if not prompt:
                print(f"  {C.YELLOW}⚠ Prism '{prism_name}' not found — "
                      f"skipping{C.RESET}")
                continue

            # Build message
            if not chain:
                # Independent prism: just source code
                msg = f"Analyze this source code.\n\n{content}"
            elif prism_name == "l12_complement_adversarial":
                # Adversarial: source code + L12 output to attack
                l12_out = outputs.get("l12", "")
                if not l12_out:
                    print(f"  {C.YELLOW}⚠ No L12 output for adversarial — "
                          f"skipping{C.RESET}")
                    continue
                msg = (f"# SOURCE CODE\n\n{content}\n\n---\n\n"
                       f"# ANALYSIS 1\n\n{l12_out}")
            else:
                # Synthesis: source code + all prior outputs
                parts = [f"# SOURCE CODE\n\n{content}"]
                for j, (prev_step, prev_out) in enumerate(output_list):
                    parts.append(
                        f"# ANALYSIS {j + 1}: {prev_step['role']}"
                        f"\n\n{prev_out}")
                msg = "\n\n---\n\n".join(parts)
                if len(msg) > 100_000:
                    msg = msg[:100_000] + "\n\n[... truncated due to size ...]"

            print(f"\n{C.BOLD}{C.BLUE}── {role} ── "
                  f"{file_name} ── {C.DIM}{optimal_model}{C.RESET}")

            output = self._execute_prism(
                system_prompt=prompt,
                message=msg,
                model=optimal_model,
                file_name=file_name,
                prism_name=f"full_{prism_name}",
                intent=f"full:{role.lower()}",
                mode="full_static",
            )

            if output and output.strip() and not self._interrupted:
                outputs[prism_name] = output
                output_list.append((step, output))
            elif not self._interrupted and not output:
                print(f"  {C.YELLOW}⚠ {role} returned empty — "
                      f"continuing{C.RESET}")

        if not output_list:
            return

        # Save combined output
        combined_parts = [f"# Full Pipeline: {file_name}\n"]
        for step, out in output_list:
            combined_parts.append(f"## {step['role']}\n\n{out}")
        combined = "\n\n".join(combined_parts)
        self._save_deep_finding(file_name, "full", combined)

        models_used = set(
            self._get_prism_model(s["prism"]) or "sonnet"
            for s, _ in output_list)
        print(f"\n{C.GREEN}Full Pipeline complete: "
              f"{len(output_list)}/{len(STATIC_CODE_PIPELINE)} steps, "
              f"models: {', '.join(sorted(models_used))}{C.RESET}")
        print(f"  {C.DIM}Use /fix to pick issues, "
              f"or /fix auto to fix all{C.RESET}")

    def _run_full_pipeline_cooked(self, content, file_name):
        """Cooked pipeline for general (non-code) text.

        Auto-cooks via COOK_3WAY (WHERE/WHEN/WHY + synthesis).
        Falls back to single prism if cooking fails.
        """
        domain = self._infer_domain(content, file_name, general=True)
        sample = content[:3000] if len(content) > 3000 else content

        print(f"{C.CYAN}Full Prism (cooked): domain='{domain}'{C.RESET}")

        # Cook the pipeline
        _scan_intent = (
            f"deep structural analysis of: {domain} "
            f"(challenge from within the {domain}'s own "
            f"framework, not code-structural)")
        prompt = COOK_3WAY.format(
            intent=_scan_intent)
        user_input = (
            f"Generate an analysis pipeline for: {domain}\n\n"
            f"Sample artifact:\n\n{sample}")

        print(f"  {C.CYAN}Cooking analysis pipeline...{C.RESET}")
        raw = self._call_model(prompt, user_input, timeout=90,
                               model=COOK_MODEL)

        parsed = self._parse_stage_json(raw, "cook_scan_full")
        if not isinstance(parsed, list) or len(parsed) < 2:
            reason = "no response" if not raw else (
                f"got {type(parsed).__name__}" if parsed is not None
                else "unparseable response")
            print(f"{C.RED}Failed to cook pipeline ({reason}){C.RESET}")
            if raw:
                print(f"  {C.DIM}{raw[:200]}{'...' if len(raw) > 200 else ''}{C.RESET}")
            # Fall back to model-appropriate single prism
            _m = self.session.model or ""
            _sonnet = any(x in _m for x in ("sonnet", "opus"))
            _prism = "l12_universal" if _sonnet else "deep_scan"
            _label = "l12_universal" if _sonnet else "SDL"
            print(f"{C.YELLOW}Falling back to {_label} single pass{C.RESET}")
            self._run_single_prism_streaming(
                _prism, content, file_name, general=True)
            return

        # Show pipeline structure
        prisms = []
        for i, item in enumerate(parsed):
            name = item.get("name", f"pass_{i + 1}")
            name = re.sub(r'[^a-z0-9_]', '_', name.lower())
            text = item.get("prompt", "")
            role = item.get("role", f"pass_{i + 1}")
            if not text:
                continue
            prisms.append({"name": name, "prompt": text, "role": role})
            preview = text[:60] + ("..." if len(text) > 60 else "")
            print(f"    {C.GREEN}{role}{C.RESET} ({name}): "
                  f"{C.DIM}{preview}{C.RESET}")

        if len(prisms) < 2:
            print(f"{C.RED}Need at least 2 passes{C.RESET}")
            return

        # Run the pipeline with chaining
        outputs = []
        for i, prism in enumerate(prisms):
            role = prism.get("role", prism["name"])
            if i == 0:
                msg = f"Analyze this input.\n\n{content}"
            else:
                parts = [f"# ARTIFACT\n\n{content}"]
                for j, prev in enumerate(outputs):
                    prev_role = prisms[j].get(
                        "role", prisms[j]["name"]).upper()
                    parts.append(
                        f"# PASS {j + 1}: {prev_role}"
                        f"\n\n{prev}")
                msg = "\n\n---\n\n".join(parts)
                if len(msg) > 100_000:
                    msg = msg[:100_000] + "\n\n[... truncated due to size ...]"

            output = self._execute_prism(
                system_prompt=prism["prompt"],
                message=msg,
                label=f"{role} ── {file_name}",
                file_name=file_name,
                prism_name=f"full_{prism['name']}",
                intent=f"full_cooked:{role.lower()}",
                mode="full_cooked",
            )

            if output and not self._interrupted:
                outputs.append(output)
            if not output or self._interrupted:
                if not self._interrupted and not output:
                    print(f"  {C.YELLOW}⚠ {role} returned empty — "
                          f"pipeline stopped at pass "
                          f"{i + 1}/{len(prisms)}{C.RESET}")
                break

        if not outputs:
            return

        # Save combined output
        combined_parts = [f"# Full Pipeline: {file_name}\n"]
        for i, (prism, out) in enumerate(zip(prisms, outputs)):
            role = prism.get("role", prism["name"]).upper()
            combined_parts.append(f"## {role}\n\n{out}")
        combined = "\n\n".join(combined_parts)
        self._save_deep_finding(file_name, "full", combined)
        print(f"\n  {C.DIM}Use /fix to pick issues, "
              f"or /fix auto to fix all{C.RESET}")

    def _run_3way_pipeline(self, content, file_name, general=False):
        """3-Way Pipeline: WHERE/WHEN/WHY via 3 operation-specific cooked prisms + synthesis.

        Cooks 3 prompts via COOK_3WAY (archaeology, simulation, structural) plus
        a synthesis prompt. Runs 3 independent analyses, then synthesizes.
        Cross-operation synthesis is inherently adversarial (P196).

        Validated at 9.5 depth on Starlette security (Round 39, P195-P197).
        Works on any domain — cookers customize prompts to the intent.
        """
        domain = self._infer_domain(content, file_name, general=general)
        sample = content[:3000] if len(content) > 3000 else content

        _intent = f"deep structural analysis of: {domain}"
        print(f"{C.CYAN}3-Way Pipeline: WHERE/WHEN/WHY "
              f"(domain='{domain}'){C.RESET}")

        # Cook 4 prompts (3 operations + synthesis)
        cook_prompt = COOK_3WAY.format(intent=_intent)
        user_input = (
            f"Generate a 3-way analysis pipeline for: {domain}\n\n"
            f"Sample artifact:\n\n{sample}")

        print(f"  {C.CYAN}Cooking 3-way pipeline...{C.RESET}")
        _cook_model = COOK_MODEL
        raw = self._call_model(cook_prompt, user_input,
                               model=_cook_model, timeout=120)

        parsed = self._parse_stage_json(raw, "cook_3way")
        if not isinstance(parsed, list) or len(parsed) < 3:
            reason = "no response" if not raw else (
                f"got {type(parsed).__name__}" if parsed is not None
                else "unparseable response")
            print(f"{C.RED}Failed to cook 3-way pipeline "
                  f"({reason}){C.RESET}")
            if raw:
                print(f"  {C.DIM}{raw[:200]}"
                      f"{'...' if len(raw) > 200 else ''}{C.RESET}")
            # Fall back to standard full pipeline
            print(f"{C.YELLOW}Falling back to standard "
                  f"full pipeline{C.RESET}")
            return self._run_full_pipeline(
                content, file_name, general=general)

        # Parse the 4 prompts
        prisms = []
        for i, item in enumerate(parsed):
            name = item.get("name", f"pass_{i + 1}")
            name = re.sub(r'[^a-z0-9_]', '_', name.lower())
            text = item.get("prompt", "")
            role = item.get("role", f"pass_{i + 1}")
            if not text:
                continue
            prisms.append({"name": name, "prompt": text, "role": role})
            preview = text[:60] + ("..." if len(text) > 60 else "")
            print(f"    {C.GREEN}{role}{C.RESET} ({name}): "
                  f"{C.DIM}{preview}{C.RESET}")

        if len(prisms) < 3:
            print(f"{C.RED}Need at least 3 passes for 3-way "
                  f"(got {len(prisms)}){C.RESET}")
            return

        # Separate operations (first 3) from synthesis (last)
        operations = prisms[:3]
        synthesis = prisms[3] if len(prisms) > 3 else None

        # Run 3 operations independently (no chaining)
        op_outputs = []
        for i, op in enumerate(operations):
            if self._interrupted:
                break

            role = op.get("role", op["name"])
            msg = f"Analyze this input.\n\n{content}"

            output = self._execute_prism(
                system_prompt=op["prompt"],
                message=msg,
                label=f"{role} ── {file_name}",
                file_name=file_name,
                prism_name=f"3way_{op['name']}",
                intent=f"3way:{role.lower()}",
                mode="3way",
            )

            if output and not self._interrupted:
                op_outputs.append(output)
            if not output or self._interrupted:
                if not self._interrupted and not output:
                    print(f"  {C.YELLOW}Warning: {role} returned empty — "
                          f"continuing with remaining operations"
                          f"{C.RESET}")
                if self._interrupted:
                    break

        if len(op_outputs) < 2:
            print(f"{C.RED}Need at least 2 operation outputs "
                  f"for synthesis{C.RESET}")
            return

        # Run synthesis (receives all operation outputs)
        if synthesis and not self._interrupted:
            role = synthesis.get("role", "SYNTHESIS")
            parts = [f"# ARTIFACT\n\n{content}"]
            for j, (op, out) in enumerate(
                    zip(operations[:len(op_outputs)], op_outputs)):
                op_role = op.get("role", op["name"]).upper()
                parts.append(f"# ANALYSIS {j + 1}: {op_role}\n\n{out}")
            msg = "\n\n---\n\n".join(parts)
            if len(msg) > 100_000:
                msg = msg[:100_000] + (
                    "\n\n[... truncated due to size ...]")

            # Synthesis uses Sonnet for quality (P195)
            synth_output = self._execute_prism(
                system_prompt=synthesis["prompt"],
                message=msg,
                model="sonnet",
                label=f"{role} ── {file_name}",
                file_name=file_name,
                prism_name="3way_synthesis",
                intent="3way:synthesis",
                mode="3way",
            )

            if synth_output:
                op_outputs.append(synth_output)

        # Save combined output
        all_prisms = operations[:len(op_outputs)]
        if synthesis and len(op_outputs) > len(operations):
            all_prisms.append(synthesis)
        combined_parts = [f"# 3-Way Pipeline: {file_name}\n"]
        for i, (prism, out) in enumerate(
                zip(all_prisms, op_outputs)):
            role = prism.get("role", prism["name"]).upper()
            combined_parts.append(f"## {role}\n\n{out}")
        combined = "\n\n".join(combined_parts)
        self._save_deep_finding(file_name, "3way", combined)

        models_used = {self.session.model or "sonnet"}
        if synthesis and len(op_outputs) > len(operations):
            models_used.add("sonnet")
        print(f"\n{C.GREEN}3-Way Pipeline complete: "
              f"{len(op_outputs)} passes, "
              f"models: {', '.join(sorted(models_used))}{C.RESET}")
        print(f"  {C.DIM}Use /fix to pick issues, "
              f"or /fix auto to fix all{C.RESET}")

    def _run_behavioral_pipeline(self, content, file_name, general=False):
        """Behavioral Pipeline: 4 independent behavioral prisms + synthesis.

        Runs ErrRes, Optim, Evo, API Surface independently on the same input,
        then feeds all 4 outputs into a synthesis prism that finds convergence
        points, blind spots, and a unified conservation law.

        When general=True, uses domain-neutral prism variants where available.
        """
        # Select code-specific or neutral prism variants based on domain
        if general:
            prisms = [
                ("error_resilience", "ERRORS"),
                ("optimize", "COSTS"),
                ("fix_cascade", "ENTAILMENT"),
                ("identity", "DISPLACEMENT"),
            ]
        else:
            prisms = [
                ("error_resilience", "ERRORS"),
                ("optimize", "COSTS"),
                ("fix_cascade", "ENTAILMENT"),
                ("identity", "DISPLACEMENT"),
            ]

        print(f"{C.CYAN}Behavioral Pipeline: "
              f"{'general' if general else 'code'} mode, "
              f"{len(prisms)} prisms + synthesis{C.RESET}")

        # Phase 1: Run all 4 behavioral prisms independently
        # Use optimal model per-prism (same pattern as full pipeline)
        outputs = {}
        for prism_name, role in prisms:
            if self._interrupted:
                break
            with self._temporary_model(self._get_prism_model(prism_name)):
                label = f"{role} ({prism_name}) ── {file_name}"
                output = self._run_single_prism_streaming(
                    prism_name, content, file_name,
                    label=label, general=general,
                    intent=f"behavioral:{role.lower()}")
                if output and output.strip():
                    outputs[role] = output
                elif not self._interrupted:
                    print(f"  {C.YELLOW}⚠ {role} returned empty — "
                          f"skipping{C.RESET}")

        if len(outputs) < 2:
            print(f"{C.RED}Behavioral pipeline needs at least 2 "
                  f"outputs for synthesis (got {len(outputs)}){C.RESET}")
            return

        # Phase 2: Synthesis — feed all outputs to synthesis prism
        print(f"\n{C.CYAN}Synthesis: combining {len(outputs)} "
              f"analyses...{C.RESET}")

        synth_input_parts = []
        for role, out in outputs.items():
            synth_input_parts.append(f"## {role}\n\n{out}")
        synth_content = "\n\n---\n\n".join(synth_input_parts)

        with self._temporary_model(self._get_prism_model("behavioral_synthesis")):
            synth_output = self._run_single_prism_streaming(
                "behavioral_synthesis", synth_content, file_name,
                label=f"SYNTHESIS ── {file_name}",
                general=True,  # synthesis input is analysis text, not code
                intent="behavioral:synthesis")

        # Phase 3: Save combined output
        combined_parts = [f"# Behavioral Pipeline: {file_name}\n"]
        for role, out in outputs.items():
            combined_parts.append(f"## {role}\n\n{out}")
        if synth_output and synth_output.strip():
            combined_parts.append(f"## SYNTHESIS\n\n{synth_output}")
        combined = "\n\n".join(combined_parts)

        self._save_deep_finding(file_name, "behavioral", combined)

        # Summary
        print(f"\n{C.GREEN}Behavioral Pipeline complete: "
              f"{len(outputs)} analyses + "
              f"{'synthesis' if synth_output else 'no synthesis'}"
              f"{C.RESET}")
        print(f"  {C.DIM}Findings: .deep/findings/{C.RESET}")

        # Log the pipeline operation
        self._session_log.append(
            operation="behavioral_pipeline",
            file_name=file_name,
            lens="behavioral",
            model=self.session.model,
            mode="behavioral",
            findings_summary=(
                f"{len(outputs)} prisms: "
                f"{', '.join(outputs.keys())}"),
        )

    def _run_falsify(self, content, file_name, general=False):
        """Falsification pipeline: L12 → extract conservation law → falsify.

        Addresses the structural bias: L12 MUST produce a conservation law
        (it's in the instructions). This pipeline tests whether the law
        found is genuine (specific to this code) or an inevitability
        narrative (could apply to anything).
        """
        # Phase 1: L12 analysis
        print(f"\n{C.BOLD}{C.BLUE}── Phase 1: L12 analysis ── "
              f"{file_name} ──{C.RESET}")
        with self._temporary_model(
                self._get_prism_model("l12") or "sonnet"):
            l12_output = self._run_single_prism_streaming(
                "l12", content, file_name, general=general)

        if not l12_output or not l12_output.strip():
            print(f"{C.RED}L12 returned empty{C.RESET}")
            return

        # Phase 2: Extract conservation law from L12 output
        laws = re.findall(
            r'[Cc]onservation [Ll]aw[:\s]*[`"\']*(.+?)'
            r'[`"\']*(?:\n|$)', l12_output)
        if not laws:
            print(f"{C.YELLOW}No conservation law found in L12 "
                  f"output — nothing to falsify{C.RESET}")
            return

        law_text = laws[0].strip()
        print(f"\n  {C.CYAN}Conservation law found: "
              f"{law_text[:100]}{C.RESET}")

        # Phase 3: Falsify — stress-test the law
        print(f"\n{C.BOLD}{C.BLUE}── Phase 2: Falsification ── "
              f"{file_name} ──{C.RESET}")
        falsify_msg = (
            f"## Conservation Law Under Test\n\n"
            f"**Law:** {law_text}\n\n"
            f"**Source code context:**\n\n{content[:3000]}\n\n"
            f"**Full L12 analysis that produced this law:**\n\n"
            f"{l12_output[:3000]}")

        with self._temporary_model(
                self._get_prism_model("falsify") or "sonnet"):
            falsify_output = self._run_single_prism_streaming(
                "falsify", falsify_msg, file_name,
                label=f"FALSIFY ── {law_text[:60]}",
                general=True,
                intent="falsify")

        if falsify_output:
            # Extract verdict
            verdict_m = re.search(
                r'(VERIFIED|PLAUSIBLE|GENERIC|FALSE)',
                falsify_output)
            if verdict_m:
                verdict = verdict_m.group(1)
                color = (C.GREEN if verdict == "VERIFIED"
                         else C.CYAN if verdict == "PLAUSIBLE"
                         else C.YELLOW if verdict == "GENERIC"
                         else C.RED)
                print(f"\n{color}Verdict: {verdict}{C.RESET}")

            # Save combined
            combined = (
                f"## L12 ANALYSIS\n\n{l12_output}\n\n---\n\n"
                f"## CONSERVATION LAW: {law_text}\n\n---\n\n"
                f"## FALSIFICATION\n\n{falsify_output}")
            self._save_deep_finding(
                file_name, "falsify", combined)

        self._session_log.append(
            operation="falsify",
            file_name=file_name,
            lens="l12+falsify",
            model=self.session.model,
            mode="falsify",
            findings_summary=(
                f"Law: {law_text[:80]}, "
                f"Verdict: {verdict_m.group(1) if verdict_m else '?'}"),
        )

    def _run_meta_pipeline(self, content, file_name, general=False):
        """Meta-analysis: L12 → claim prism → recursive self-analysis.

        P201: claim prism successfully analyzes L12 output,
        producing genuine meta-insights about what the analysis
        itself conceals. Two calls for recursive depth.
        """
        # Phase 1: L12 structural analysis
        print(f"\n{C.BOLD}{C.BLUE}── Phase 1: L12 structural "
              f"analysis ── {file_name} ──{C.RESET}")
        with self._temporary_model(self._get_prism_model("l12") or "sonnet"):
            l12_output = self._run_single_prism_streaming(
                "l12", content, file_name, general=general)

        if not l12_output or not l12_output.strip():
            print(f"{C.RED}L12 returned empty — cannot run "
                  f"meta-analysis{C.RESET}")
            return

        # Phase 2: Claim prism on L12 output (meta-analysis)
        print(f"\n{C.BOLD}{C.BLUE}── Phase 2: Meta-analysis "
              f"(claim prism on L12 output) ── {file_name} ──"
              f"{C.RESET}")
        print(f"  {C.DIM}Analyzing what the analysis itself "
              f"conceals...{C.RESET}")
        with self._temporary_model(self._get_prism_model("claim") or "haiku"):
            meta_output = self._run_single_prism_streaming(
                "claim", l12_output, file_name,
                label=f"META ── {file_name}",
                general=True)  # L12 output is text, not code

        # Save combined output
        combined = (f"## L12 STRUCTURAL ANALYSIS\n\n{l12_output}\n\n"
                    f"---\n\n"
                    f"## META-ANALYSIS (what the analysis conceals)"
                    f"\n\n{meta_output}")
        self._save_deep_finding(file_name, "meta", combined)

        print(f"\n{C.GREEN}Meta pipeline complete: L12 + claim "
              f"(recursive){C.RESET}")
        print(f"  {C.DIM}Findings: .deep/findings/{C.RESET}")

        self._session_log.append(
            operation="meta_pipeline",
            file_name=file_name,
            lens="l12+claim",
            model=self.session.model,
            mode="meta",
            findings_summary=(
                f"L12: {len(l12_output)}w, "
                f"Meta: {len(meta_output) if meta_output else 0}w"),
        )

    def _run_reflect(self, content, file_name, general=False):
        """Reflect: L12 → claim → cross-reference with constraint history.

        B5: Like meta, but adds constraint history and learning memory
        to produce a summary of recurring patterns and unexplored dimensions.
        """
        # Phase 1: L12 structural analysis
        print(f"\n{C.BOLD}{C.BLUE}── Phase 1: L12 structural "
              f"analysis ── {file_name} ──{C.RESET}")
        with self._temporary_model(self._get_prism_model("l12") or "sonnet"):
            l12_output = self._run_single_prism_streaming(
                "l12", content, file_name, general=general)

        if not l12_output or not l12_output.strip():
            print(f"{C.RED}L12 returned empty — cannot run "
                  f"reflect{C.RESET}")
            return

        # Phase 2: Claim prism on L12 output (meta-analysis)
        print(f"\n{C.BOLD}{C.BLUE}── Phase 2: Meta-analysis "
              f"(claim prism on L12 output) ── {file_name} ──"
              f"{C.RESET}")
        with self._temporary_model(self._get_prism_model("claim") or "haiku"):
            meta_output = self._run_single_prism_streaming(
                "claim", l12_output, file_name,
                label=f"META ── {file_name}",
                general=True)

        # Phase 3: Load constraint history and produce constraint summary
        print(f"\n{C.BOLD}{C.BLUE}── Phase 3: Constraint "
              f"synthesis ── {file_name} ──{C.RESET}")
        history_text = ""
        try:
            _hist_path = (self.working_dir / ".deep"
                          / "constraint_history.md")
            if _hist_path.exists():
                _raw = _hist_path.read_text(encoding="utf-8")
                _entries = [b.strip() for b in _raw.split("\n### ")
                            if file_name in b]
                if _entries:
                    history_text = (
                        f"Prior analyses ({len(_entries)} total):\n"
                        + "\n".join(
                            "### " + e for e in _entries[-5:]))
        except (OSError, PermissionError):
            pass

        learning_text = ""
        try:
            import json as _json_ref
            _learn_path = (self.working_dir / ".deep"
                           / "learning.json")
            if _learn_path.exists():
                _data = _json_ref.loads(
                    _learn_path.read_text(encoding="utf-8"))
                _file_events = [
                    e for e in _data
                    if isinstance(e, dict)
                    and file_name in e.get("file", "")]
                if _file_events:
                    learning_text = (
                        f"Learning events ({len(_file_events)}):\n"
                        + "\n".join(
                            f"- [{e.get('type')}] "
                            f"{e.get('issue', e.get('claim', ''))}"
                            for e in _file_events[-10:]))
        except (ValueError, OSError):
            pass

        # Build synthesis input
        synth_input = (
            f"## L12 ANALYSIS\n\n{l12_output}\n\n---\n\n"
            f"## META-ANALYSIS\n\n{meta_output or '(none)'}\n\n")
        if history_text:
            synth_input += f"---\n\n## PRIOR ANALYSES\n\n{history_text}\n\n"
        if learning_text:
            synth_input += f"---\n\n## LEARNING MEMORY\n\n{learning_text}\n\n"

        synth_input += (
            "---\n\n## TASK\n\n"
            "Execute every step. Output the complete analysis.\n\n"
            "## RECURRING PATTERNS\n"
            "What structural properties appear across multiple "
            "prior analyses? Name each with evidence.\n\n"
            "## UNEXPLORED DIMENSIONS\n"
            "Which analytical angles have NOT been covered? "
            "Be specific: name the prism or operation that would "
            "reveal each gap.\n\n"
            "## KNOWN FALSE POSITIVES\n"
            "List patterns that prior scans flagged but the user "
            "rejected as intentional design. Future scans must "
            "avoid these.\n\n"
            "## NEXT BEST SCAN\n"
            "The single most valuable next analytical step for "
            "this code. Which mode, which prism, targeting what "
            "specific structural question?")

        # Sonnet for reflect synthesis. Opus is optimal per grid but
        # times out on large inputs (proven VPS test). Sonnet produces
        # equivalent quality on synthesis tasks ("Ontology Blindness").
        synth_output = self._execute_prism(
            system_prompt=(
                "You are a structural analyst synthesizing "
                "prior analyses into actionable constraints."),
            message=synth_input,
            model="sonnet",
            label=f"CONSTRAINT SYNTHESIS ── {file_name}",
            save=False,
        )

        # Save combined output
        combined = (
            f"## L12 STRUCTURAL ANALYSIS\n\n{l12_output}\n\n"
            f"---\n\n"
            f"## META-ANALYSIS\n\n{meta_output or '(none)'}\n\n"
            f"---\n\n"
            f"## CONSTRAINT SYNTHESIS\n\n"
            f"{synth_output or '(none)'}")
        self._save_deep_finding(file_name, "reflect", combined)

        print(f"\n{C.GREEN}Reflect complete: L12 + meta + "
              f"constraint synthesis{C.RESET}")

        self._session_log.append(
            operation="reflect",
            file_name=file_name,
            lens="l12+claim+synthesis",
            model=self.session.model,
            mode="reflect")

    def _run_dispute(self, content, file_name, general=False):
        """Dispute: run 2 orthogonal prisms, synthesize disagreements.

        B10: Lightweight disagreement committee. Picks 2 prisms that
        maximize divergence, runs both, then synthesizes ONLY where
        they disagree. 3 calls for ~$0.15 — much of Full's
        self-correction at a fraction of the cost.
        """
        # Select 2 orthogonal prisms based on content type
        if general:
            prism_a, prism_b = "l12_universal", "claim"
        else:
            # l12 + identity have highest pairwise uniqueness (10/10)
            prism_a, prism_b = "l12", "identity"

        print(f"\n{C.BOLD}{C.BLUE}── Dispute ── "
              f"{file_name} ──{C.RESET}")
        print(f"  {C.DIM}3-call: {prism_a} vs {prism_b} → "
              f"disagreement synthesis{C.RESET}")

        # Run prism A
        print(f"\n{C.BOLD}Lens A: {prism_a}{C.RESET}")
        with self._temporary_model(
                self._get_prism_model(prism_a) or "sonnet"):
            output_a = self._run_single_prism_streaming(
                prism_a, content, file_name,
                label=f"LENS A ({prism_a}) ── {file_name}",
                general=general)

        # Run prism B
        print(f"\n{C.BOLD}Lens B: {prism_b}{C.RESET}")
        with self._temporary_model(
                self._get_prism_model(prism_b) or "sonnet"):
            output_b = self._run_single_prism_streaming(
                prism_b, content, file_name,
                label=f"LENS B ({prism_b}) ── {file_name}",
                general=general)

        if not output_a or not output_b:
            print(f"{C.RED}One or both prisms returned empty"
                  f"{C.RESET}")
            return

        # Synthesis: focus on disagreements
        # Omit source code — analyses already reference it.
        # Truncate each analysis to avoid context overflow.
        print(f"\n{C.BOLD}{C.BLUE}── Disagreement Synthesis "
              f"── {file_name} ──{C.RESET}")
        # Cap each analysis at ~8000 chars (~2000 words) to stay within
        # context window for synthesis. Full outputs saved to findings.
        _a_trunc = output_a[:8000] if len(output_a) > 8000 else output_a
        _b_trunc = output_b[:8000] if len(output_b) > 8000 else output_b
        synth_input = (
            f"# LENS A: {prism_a}\n\n{_a_trunc}\n\n---\n\n"
            f"# LENS B: {prism_b}\n\n{_b_trunc}")

        # Sonnet for dispute synthesis. Opus times out on 2-analysis
        # inputs (proven: empty synthesis on VPS). Sonnet works.
        synth = self._execute_prism(
            system_prompt=DISPUTE_SYNTHESIS_PROMPT,
            message=synth_input,
            model="sonnet",
            label=f"DISPUTE SYNTHESIS ── {file_name}",
            save=False,
        )

        # Save all outputs
        combined = (
            f"## LENS A: {prism_a}\n\n{output_a}\n\n---\n\n"
            f"## LENS B: {prism_b}\n\n{output_b}\n\n---\n\n"
            f"## DISAGREEMENT SYNTHESIS\n\n{synth or '(empty)'}")
        self._save_deep_finding(file_name, "dispute", combined)

        print(f"\n{C.GREEN}Dispute complete: {prism_a} vs "
              f"{prism_b} → disagreements{C.RESET}")

        self._session_log.append(
            operation="dispute",
            file_name=file_name,
            lens=f"{prism_a}+{prism_b}+synthesis",
            model=self.session.model,
            mode="dispute")

    def _run_evolve(self, content, file_name, general=False):
        """Evolve: auto-generate domain-adapted prism via recursive cooking.

        Runs meta-cooker 3 times, each generation feeding into the next.
        Converges to a domain-specific universal prism. (K16c: autopoietic)
        Saves the evolved prism to .deep/prisms/{file_stem}_evolved.md
        """
        print(f"\n{C.BOLD}{C.BLUE}── Evolve ── "
              f"{file_name} ──{C.RESET}")
        print(f"  {C.DIM}3 generations: cook → cook → cook "
              f"→ save domain-adapted prism{C.RESET}")

        current_input = content[:5000]
        with self._temporary_model(COOK_MODEL):
            for gen in range(1, 4):
                if self._interrupted:
                    break
                print(f"  {C.DIM}Generation {gen}/3...{C.RESET}",
                      end="", flush=True)
                cook_prompt = COOK_UNIVERSAL.format(
                    intent="generate the best possible analytical "
                           "prism for this input")
                raw = self._claude.call(
                    cook_prompt, current_input,
                    model=COOK_MODEL, timeout=120)
                prism_data = _parse_prism_json(raw)
                if prism_data and prism_data.get("prompt"):
                    words = len(prism_data["prompt"].split())
                    name = prism_data.get("name", f"gen{gen}")
                    print(f" {name} ({words}w)")
                    current_input = prism_data["prompt"]
                elif raw and len(raw.strip()) > 50:
                    # Cook returned text but not parseable JSON.
                    # Use the raw text as a prism prompt directly.
                    words = len(raw.split())
                    print(f" raw ({words}w)")
                    current_input = raw.strip()
                else:
                    print(f" {C.YELLOW}cook failed{C.RESET}")
                    break

        if current_input and current_input != content[:5000]:
            # Save the evolved prism
            stem = pathlib.Path(file_name).stem
            prism_dir = self.working_dir / ".deep" / "prisms"
            prism_dir.mkdir(parents=True, exist_ok=True)
            evolved_path = prism_dir / f"{stem}_evolved.md"
            evolved_content = (
                f"---\n"
                f"name: {stem}_evolved\n"
                f"description: Auto-evolved prism for {file_name} "
                f"(3 generations)\n"
                f"optimal_model: sonnet\n"
                f"domain: any\n"
                f"type: structural\n"
                f"---\n"
                f"{current_input}\n")
            evolved_path.write_text(
                evolved_content, encoding="utf-8")
            print(f"\n{C.GREEN}Evolved prism saved: "
                  f"{evolved_path}{C.RESET}")
            print(f"  {C.DIM}Use: /scan {file_name} "
                  f'prism="{stem}_evolved"{C.RESET}')

            # Run the evolved prism on the content
            print(f"\n{C.BOLD}{C.BLUE}── Running evolved prism ──"
                  f"{C.RESET}")
            output = self._run_single_prism_streaming(
                f"{stem}_evolved", content, file_name,
                general=general)
            if output:
                self._save_deep_finding(
                    file_name, "evolved", output)
        else:
            print(f"{C.RED}Evolution failed — no prism "
                  f"produced{C.RESET}")

        self._session_log.append(
            operation="evolve",
            file_name=file_name,
            lens="evolved",
            model=self.session.model,
            mode="evolve",
        )

    def _run_adaptive(self, content, file_name, general=False,
                       budget=None):
        """Adaptive depth: automatically escalate from cheap/fast to deep.

        Stage 1: SDL deep_scan (~$0.01, Haiku) — fast conservation law
        Stage 2: L12 (~$0.05, Sonnet) — if SDL signal is weak
        Stage 3: Full pipeline (~$0.50) — if L12 signal is still weak

        Signal quality = conservation law presence + output depth.
        Stops at first stage that produces sufficient analytical depth.
        Budget (optional): max cost in USD. Skips stages that exceed budget.
        """
        # A2: Cost estimates per stage
        stage_costs = {"deep_scan": 0.02, "l12": 0.06, "full": 0.50}
        spent = 0.0
        stages = [
            ("deep_scan", "SDL Quick Scan", 300),
            ("l12", "L12 Deep", 500),
        ]

        # Check session log for prism recommendation on similar files
        file_ext = file_name.rsplit(".", 1)[-1] if "." in file_name else None
        _yt = self._yield_tracker if hasattr(self, '_yield_tracker') else None
        rec_prism, rec_conf, rec_reason = self._session_log.recommend_prism(
            file_name=file_name, file_ext=file_ext, yield_tracker=_yt)
        if rec_prism and rec_conf >= 0.6 and rec_prism != "deep_scan":
            # History suggests skipping SDL — go straight to recommended prism
            print(f"{C.CYAN}Adaptive depth: history recommends "
                  f"'{rec_prism}' ({rec_reason}){C.RESET}")
            stages = [s for s in stages if s[0] != "deep_scan"]
            if rec_prism == "l12":
                pass  # L12 already in stages
            elif rec_prism not in [s[0] for s in stages]:
                # Insert recommended prism before L12
                stages.insert(0, (rec_prism, f"Recommended: {rec_prism}", 400))
        else:
            print(f"{C.CYAN}Adaptive depth: starting with cheapest "
                  f"analysis...{C.RESET}")

        for i, (prism_name, label, min_words) in enumerate(stages):
            if self._interrupted:
                return

            # A2: Budget check — skip stage if it would exceed budget
            est_cost = stage_costs.get(prism_name, 0.05)
            if budget is not None and spent + est_cost > budget:
                print(f"  {C.YELLOW}Budget limit ${budget:.2f} reached "
                      f"(spent ${spent:.2f}) — stopping{C.RESET}")
                break

            # Tier 1 predictor: show P(single-shot) for transparency
            prism_text = self._load_prism(prism_name) or ""
            model_for_prism = self._get_prism_model(prism_name) or "sonnet"
            p_ss, feats = predict_single_shot(
                prism_text, content, model_for_prism)
            print(f"\n{C.BOLD}{C.BLUE}── Stage {i + 1}: "
                  f"{label} ── {file_name} ──{C.RESET}")
            print(f"  {C.DIM}P(single-shot) = {p_ss:.0%}, "
                  f"est ~${est_cost:.2f} "
                  f"[imp={feats['imperative_count']}, "
                  f"code={feats['code_ratio']:.0%}]{C.RESET}")

            cost_before = self.session.total_cost_usd
            with self._temporary_model(self._get_prism_model(prism_name)):
                output = self._run_single_prism_streaming(
                    prism_name, content, file_name,
                    general=general,
                    intent=f"adaptive:stage{i + 1}")
            spent += self.session.total_cost_usd - cost_before

            if not output or not output.strip():
                print(f"  {C.YELLOW}Stage {i + 1} empty — "
                      f"escalating...{C.RESET}")
                continue

            # Quality signals: conservation law + sufficient depth
            has_law = bool(re.search(
                r'[Cc]onservation\s+[Ll]aw|×\s*.*=\s*constant|'
                r'[Cc]onserved|invariant', output))
            word_count = len(output.split())
            has_depth = word_count >= min_words
            # Structure markers boost confidence but aren't required.
            # Flowing prose analysis (no markdown) is still valid if deep enough.
            has_structure = (
                output.count("##") >= 2
                or output.count("**") >= 4
                or bool(re.search(r'\d+\.\s', output))
            )
            # Sufficient = law + depth. Structure is bonus (raises threshold).
            # Without structure, require 50% more words to compensate.
            if has_structure:
                quality_ok = has_law and has_depth
            else:
                quality_ok = has_law and word_count >= int(min_words * 1.5)

            if quality_ok:
                print(f"\n{C.GREEN}Adaptive: sufficient depth at "
                      f"Stage {i + 1} ({label}) — "
                      f"{word_count}w, conservation law found"
                      f"{C.RESET}")
                self._session_log.append(
                    operation="adaptive",
                    file_name=file_name,
                    lens=prism_name,
                    model=self.session.model,
                    mode="adaptive",
                    findings_summary=(
                        f"Stage {i + 1}/{len(stages) + 1}: "
                        f"{word_count}w, law={'yes' if has_law else 'no'}"),
                )
                return

            print(f"  {C.DIM}Stage {i + 1}: {word_count}w, "
                  f"law={'yes' if has_law else 'no'} — "
                  f"escalating...{C.RESET}")

        # Stage 3: Full pipeline (last resort)
        if not self._interrupted:
            if budget is not None and spent + stage_costs["full"] > budget:
                print(f"  {C.YELLOW}Budget ${budget:.2f} prevents "
                      f"full pipeline (~${stage_costs['full']:.2f}). "
                      f"Spent ${spent:.2f} so far.{C.RESET}")
                return
            print(f"\n{C.BOLD}{C.BLUE}── Stage 3: Full Pipeline ── "
                  f"{file_name} ──{C.RESET}")
            print(f"  {C.DIM}Prior stages insufficient — "
                  f"running full analysis (est ~${stage_costs['full']:.2f})"
                  f"{C.RESET}")
            self._run_full_pipeline(content, file_name, general=general)

    def _run_synthesize(self, content=None, file_name=None, general=False):
        """Cross-session pattern synthesis: aggregate findings across files.

        Reads all .deep/findings/*.md files and runs a synthesis pass
        to detect project-wide patterns that no single-file scan can see:
        repeated anti-patterns, systemic conservation laws, architectural
        issues that span multiple files.
        """
        findings_dir = self.working_dir / ".deep" / "findings"
        if not findings_dir.exists():
            print(f"{C.RED}No findings directory — run /scan first{C.RESET}")
            return

        # Collect all findings
        finding_files = sorted(findings_dir.glob("*.md"))
        if not finding_files:
            print(f"{C.RED}No findings to synthesize — "
                  f"run /scan on some files first{C.RESET}")
            return

        # Build summary of each finding (first 500 words)
        summaries = []
        for fpath in finding_files:
            try:
                text = fpath.read_text(encoding="utf-8")
                words = text.split()[:500]
                summary = " ".join(words)
                if len(words) == 500:
                    summary += "..."
                summaries.append(
                    f"## {fpath.stem}\n\n{summary}")
            except (OSError, UnicodeDecodeError):
                continue

        if len(summaries) < 2:
            print(f"{C.YELLOW}Need findings from at least 2 files "
                  f"for synthesis (have {len(summaries)}){C.RESET}")
            return

        print(f"{C.CYAN}Cross-session synthesis: "
              f"{len(summaries)} findings{C.RESET}")

        synth_prompt = (
            "You are a structural analyst finding patterns that SPAN "
            "multiple files in the same project. You receive summaries "
            "of prior structural analyses.\n\n"
            "Execute every step. Output the complete analysis.\n\n"
            "## CROSS-FILE PATTERNS\n"
            "Which structural properties appear in 2+ files? For each "
            "pattern: which files, what's the shared cause, what "
            "project-wide change would address all instances.\n\n"
            "## PROJECT-WIDE CONSERVATION LAW\n"
            "Derive the conservation law that governs the ENTIRE "
            "project — the trade-off that every file independently "
            "discovers. Name it: A × B = constant.\n\n"
            "## SYSTEMIC RISKS\n"
            "Which findings from individual files combine to create "
            "risks that no single-file analysis could detect? Name "
            "the emergent risk and which files contribute.\n\n"
            "## UNEXPLORED INTERSECTIONS\n"
            "Which pairs of files have NOT been analyzed together but "
            "likely share structural properties based on their "
            "individual findings?")

        synth_content = "\n\n---\n\n".join(summaries)
        if len(synth_content) > 80_000:
            synth_content = (synth_content[:80_000]
                             + "\n\n[... truncated ...]")

        output = self._execute_prism(
            system_prompt=synth_prompt,
            message=synth_content,
            model="sonnet",
            label=f"PROJECT SYNTHESIS ── {len(summaries)} files",
            file_name="project_synthesis",
            prism_name="synthesize",
            intent="synthesize",
            mode="synthesize",
        )

        if output and output.strip():
            print(f"\n{C.GREEN}Synthesis complete: "
                  f"{len(output.split())}w across "
                  f"{len(summaries)} files{C.RESET}")

            # A4: Extract hypotheses that could be verified by re-scanning
            hypotheses = re.findall(
                r'(?:Hypothesis|hypothesis|HYPOTHESIS)[:\s]+(.+?)(?:\n|$)',
                output)
            intersections = re.findall(
                r'(?:should intersect|likely share|analysis would reveal)[:\s]*(.+?)(?:\n|$)',
                output)
            risks = re.findall(
                r'(?:Emergent risk|systemic risk|RISK)[:\s]+(.+?)(?:\n|$)',
                output, re.IGNORECASE)

            verifiable = hypotheses + intersections + risks
            if verifiable:
                print(f"\n  {C.CYAN}Verifiable hypotheses found: "
                      f"{len(verifiable)}{C.RESET}")
                for i, h in enumerate(verifiable[:5], 1):
                    print(f"    {i}. {h[:100].strip()}")
                print(f"  {C.DIM}Run /scan <file> target=\"<hypothesis>\" "
                      f"to verify{C.RESET}")

                # Save hypotheses for future verification
                hyp_path = self.working_dir / ".deep" / "hypotheses.json"
                try:
                    existing = []
                    if hyp_path.exists():
                        existing = json.loads(
                            hyp_path.read_text(encoding="utf-8"))
                    for h in verifiable:
                        existing.append({
                            "hypothesis": h.strip()[:200],
                            "source": "synthesis",
                            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                            "verified": False,
                        })
                    hyp_path.write_text(
                        json.dumps(existing[-50:], indent=2),
                        encoding="utf-8")
                except (OSError, ValueError):
                    pass

    def _run_l12g(self, content, file_name, general=False):
        """L12-G: Gap-aware structural analysis in a single pass.

        Single-call version that combines L12 + knowledge audit +
        self-correction. Produces zero confabulated claims at the
        same cost as standard L12. (P209)
        """
        print(f"\n{C.BOLD}{C.BLUE}── L12-G (gap-aware) ── "
              f"{file_name} ──{C.RESET}")
        print(f"  {C.DIM}Single-pass: analyze → audit → "
              f"self-correct{C.RESET}")

        with self._temporary_model(
                self._get_prism_model("l12g") or "sonnet"):
            output = self._run_single_prism_streaming(
                "l12g", content, file_name, general=general)

        if output and output.strip():
            self._save_deep_finding(file_name, "l12g", output)
            print(f"\n{C.GREEN}L12-G complete: gap-aware, "
                  f"self-corrected{C.RESET}")
        else:
            print(f"{C.RED}L12-G returned empty{C.RESET}")

        self._session_log.append(
            operation="l12g",
            file_name=file_name,
            lens="l12g",
            model=self.session.model,
            mode="l12g",
        )

    def _run_gaps_only(self, content, file_name, general=False):
        """Gaps: Run knowledge_boundary + knowledge_audit on L12 output.

        Shows what the standard L12 analysis can't verify from source alone.
        Does NOT re-run L12 — just identifies knowledge gaps.
        """
        print(f"\n{C.BOLD}{C.BLUE}── Gap Detection ── "
              f"{file_name} ──{C.RESET}")

        # Phase 1: L12 analysis
        print(f"  {C.DIM}Phase 1: L12 structural analysis...{C.RESET}")
        with self._temporary_model(
                self._get_prism_model("l12") or "sonnet"):
            l12_output = self._run_single_prism_streaming(
                "l12", content, file_name, general=general)
        if not l12_output or not l12_output.strip():
            print(f"{C.RED}L12 returned empty — cannot detect "
                  f"gaps{C.RESET}")
            return

        # Phase 2: Knowledge boundary (classification)
        print(f"\n  {C.DIM}Phase 2: Knowledge boundary "
              f"(classifying claims)...{C.RESET}")
        with self._temporary_model(
                self._get_prism_model(
                    "knowledge_boundary") or "sonnet"):
            boundary_output = self._run_single_prism_streaming(
                "knowledge_boundary", l12_output, file_name,
                label=f"KNOWLEDGE BOUNDARY ── {file_name}",
                general=True)

        # Phase 3: Knowledge audit (adversarial)
        print(f"\n  {C.DIM}Phase 3: Knowledge audit "
              f"(attacking claims)...{C.RESET}")
        with self._temporary_model(
                self._get_prism_model(
                    "knowledge_audit") or "sonnet"):
            audit_output = self._run_single_prism_streaming(
                "knowledge_audit", l12_output, file_name,
                label=f"KNOWLEDGE AUDIT ── {file_name}",
                general=True)

        # Save combined output
        combined = (
            f"## L12 STRUCTURAL ANALYSIS\n\n{l12_output}\n\n"
            f"---\n\n"
            f"## KNOWLEDGE BOUNDARY (claim classification)"
            f"\n\n{boundary_output or '(empty)'}\n\n"
            f"---\n\n"
            f"## KNOWLEDGE AUDIT (confabulation detection)"
            f"\n\n{audit_output or '(empty)'}")
        self._save_deep_finding(file_name, "gaps", combined)

        print(f"\n{C.GREEN}Gap detection complete: L12 + "
              f"boundary + audit{C.RESET}")
        print(f"  {C.DIM}Findings: .deep/findings/{C.RESET}")

        # J10: Extract gaps and save to persistent KB
        # Same pattern as _run_verified_pipeline but without re-analysis
        if boundary_output or audit_output:
            gap_input = (f"{boundary_output or ''}\n\n---\n\n"
                         f"{audit_output or ''}")
            try:
                gap_prompt = self._load_intent(
                    "gap_extract_v2",
                    "Extract every knowledge gap as a JSON array. "
                    "For each: claim, type, fill_source, query, "
                    "risk, impact, confidence.")
                with self._temporary_model("haiku"):
                    gap_json = self._claude.call(
                        gap_prompt, gap_input,
                        model="haiku", timeout=60)
                if gap_json:
                    self._save_gaps_to_kb(file_name, gap_json)
            except Exception:
                pass

        self._session_log.append(
            operation="gaps",
            file_name=file_name,
            lens="l12+boundary+audit",
            model=self.session.model,
            mode="gaps",
        )

    def _save_gaps_to_kb(self, file_name, gap_json):
        """J10: Save extracted gaps to persistent knowledge base.

        Shared helper used by both gaps and verified pipelines.
        Merges new entries with existing KB, deduplicates by claim.
        """
        try:
            import json as _json_kb_save
            import time as _time_kb_save
            _kb_stem = self._discover_cache_key(file_name)
            _kb_dir = self.working_dir / ".deep" / "knowledge"
            _kb_dir.mkdir(parents=True, exist_ok=True)
            _kb_path = _kb_dir / f"{_kb_stem}.json"

            _gaps_raw = gap_json
            if "```json" in _gaps_raw:
                _gaps_raw = _gaps_raw.split("```json")[1].split("```")[0]
            try:
                _gaps = _json_kb_save.loads(_gaps_raw)
            except (ValueError, TypeError):
                _gaps = []

            if isinstance(_gaps, list):
                _now = _time_kb_save.time()
                _ttl_map = {
                    "API_DOCS": 7 * 86400,
                    "CVE_DB": 30 * 86400,
                    "CHANGELOG": 7 * 86400,
                    "COMMUNITY": 30 * 86400,
                    "BENCHMARK": 90 * 86400,
                    "MARKET": 7 * 86400,
                }
                _kb_entries = []
                for g in _gaps:
                    if isinstance(g, dict) and g.get("claim"):
                        _src = g.get("fill_source", "")
                        _ttl = _ttl_map.get(_src, 30 * 86400)
                        _kb_entries.append({
                            "claim": g["claim"],
                            "type": g.get("tier", g.get("type", "?")),
                            "confidence": g.get("confidence", 0.5),
                            "source": _src,
                            "verified": False,
                            "date": _now,
                            "expires": _now + _ttl,
                        })
                if _kb_entries:
                    # Load existing, deduplicate by claim text
                    _existing = []
                    if _kb_path.exists():
                        try:
                            _existing = _json_kb_save.loads(
                                _kb_path.read_text(encoding="utf-8"))
                        except (ValueError, TypeError):
                            _existing = []
                    _existing_claims = {
                        e.get("claim", "") for e in _existing
                        if isinstance(e, dict)}
                    _new = [e for e in _kb_entries
                            if e["claim"] not in _existing_claims]
                    if _new:
                        _existing.extend(_new)
                        # Cap at 500 entries per file
                        if len(_existing) > 500:
                            _existing = _existing[-500:]
                        _kb_path.write_text(
                            _json_kb_save.dumps(
                                _existing, indent=2),
                            encoding="utf-8")
                        print(f"  {C.DIM}Saved {len(_new)} "
                              f"facts to .deep/knowledge/"
                              f"{_kb_stem}.json{C.RESET}")
        except Exception:
            pass  # KB save is best-effort

    def _fill_gaps_agentskb(self, gap_json):
        """J7: Fill KNOWLEDGE gaps via AgentsKB REST API.

        Queries agentskb.com (free, no auth) for gaps with fill_source
        in (API_DOCS, COMMUNITY, BENCHMARK). Returns list of
        {claim, answer, source, confidence} for successfully filled gaps.
        """
        import json as _json_fill
        import urllib.request
        import urllib.error

        # Parse gap JSON
        _raw = gap_json
        if "```json" in _raw:
            _raw = _raw.split("```json")[1].split("```")[0]
        try:
            gaps = _json_fill.loads(_raw)
        except (ValueError, TypeError):
            return []

        if not isinstance(gaps, list):
            return []

        # Filter to fillable gaps
        fillable_sources = {"API_DOCS", "COMMUNITY", "BENCHMARK",
                            "CHANGELOG"}
        fillable = [g for g in gaps
                    if isinstance(g, dict)
                    and g.get("fill_source") in fillable_sources
                    and g.get("query")]

        if not fillable:
            return []

        filled = []
        api_url = "https://agentskb-api.agentskb.com/api/free/ask"

        for gap in fillable[:5]:  # Cap at 5 to avoid rate limits
            query = gap["query"]
            try:
                req_data = _json_fill.dumps({
                    "question": query
                }).encode("utf-8")
                req = urllib.request.Request(
                    api_url,
                    data=req_data,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "Prism/1.0",
                        "Accept": "application/json",
                    },
                    method="POST")
                with urllib.request.urlopen(req, timeout=15) as resp:
                    result = _json_fill.loads(
                        resp.read().decode("utf-8"))
                    answer = result.get("answer", "")
                    conf = result.get("confidence") or 0
                    match = result.get("match_score") or 0
                    sources = result.get("sources", [])
                    # Accept if answer exists and either confidence
                    # or match_score is above threshold
                    if answer and (conf >= 0.7 or match >= 0.7):
                        filled.append({
                            "claim": gap.get("claim", query),
                            "answer": answer,
                            "source": (sources[0]
                                       if sources else "agentskb"),
                            "confidence": conf,
                        })
                        print(f"    {C.GREEN}Filled: "
                              f"{query[:60]}{C.RESET}")
                    else:
                        print(f"    {C.DIM}No match: "
                              f"{query[:60]}{C.RESET}")
            except (urllib.error.URLError, urllib.error.HTTPError,
                    OSError, ValueError, KeyError) as e:
                print(f"    {C.DIM}Skip: {query[:40]} "
                      f"({type(e).__name__}){C.RESET}")
                continue

        return filled

    def _batch_query_agentskb(self, questions):
        """Query AgentsKB batch endpoint with up to 100 questions.

        Returns list of {question, answer, sources, match_score}
        for questions that got answers. Skips unanswered.
        Uses /api/free/ask-batch (up to 20 per call).
        """
        import json as _json_batch
        import urllib.request
        import urllib.error

        if not questions:
            return []

        api_url = ("https://agentskb-api.agentskb.com"
                   "/api/free/ask-batch")
        results = []

        # Batch in groups of 20 (API limit per call)
        for i in range(0, len(questions), 20):
            batch = questions[i:i + 20]
            try:
                req_data = _json_batch.dumps({
                    "questions": batch
                }).encode("utf-8")
                req = urllib.request.Request(
                    api_url,
                    data=req_data,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "Prism/1.0",
                    },
                    method="POST")
                with urllib.request.urlopen(
                        req, timeout=30) as resp:
                    data = _json_batch.loads(
                        resp.read().decode("utf-8"))
                    answers = data.get("answers", [])
                    for a in answers:
                        if (isinstance(a, dict)
                                and a.get("answer")
                                and a.get("answer") != "No answer found"):
                            results.append({
                                "question": a.get("question", ""),
                                "answer": a["answer"],
                                "sources": a.get("sources", []),
                                "match_score": a.get(
                                    "match_score", 0),
                            })
            except (urllib.error.URLError,
                    urllib.error.HTTPError,
                    OSError, ValueError) as e:
                print(f"  {C.DIM}Batch {i//20 + 1} "
                      f"failed: {type(e).__name__}{C.RESET}")
                # Fall back to individual queries
                for q in batch:
                    single = self._fill_gaps_agentskb(
                        _json_batch.dumps([{
                            "claim": q, "fill_source": "API_DOCS",
                            "query": q, "confidence": 0.3}]))
                    for s in single:
                        results.append({
                            "question": q,
                            "answer": s["answer"],
                            "sources": [s["source"]],
                            "match_score": s.get(
                                "confidence", 0),
                        })

        return results

    def _run_smart(self, content, file_name, general=False):
        """Smart: adaptive chain engine that composes modes automatically.

        The system decides the pipeline based on input characteristics:
        1. Prereq scan → identify knowledge gaps
        2. AgentsKB batch fill → get verified facts
        3. Inject facts → analyze with subsystem or L12
        4. Dispute on richest finding → self-correct
        5. Save profile + KB + learning
        """
        print(f"\n{C.BOLD}{C.BLUE}══ SMART ANALYSIS ══ "
              f"{file_name} ══{C.RESET}")
        print(f"  {C.DIM}Adaptive pipeline: the system "
              f"decides each step.{C.RESET}")

        is_code = not general

        # ── Step 1: Prereq — what do we need to know? ──
        print(f"\n{C.BOLD}Step 1: Knowledge prerequisites"
              f"{C.RESET}")
        # When analyzing code, frame prereq as "what do I need
        # to know to ANALYZE this code?" not "what task is this?"
        if is_code:
            _prereq_input = (
                f"TASK: Perform a deep structural analysis "
                f"of {file_name}. Identify conservation laws, "
                f"hidden trade-offs, and bugs.\n\n"
                f"CODE TO ANALYZE:\n{content[:3000]}")
        else:
            _prereq_input = content
        with self._temporary_model(
                self._get_prism_model("prereq") or "sonnet"):
            prereq_output = self._run_single_prism_streaming(
                "prereq", _prereq_input, file_name, general=True)

        # Extract questions (reuse prereq's extraction logic)
        _questions = self._extract_questions_from_prereq(
            prereq_output) if prereq_output else []

        # ── Step 2: AgentsKB fill — get verified facts ──
        verified_context = ""
        if _questions:
            print(f"\n{C.BOLD}Step 2: Querying AgentsKB "
                  f"({len(_questions)} questions){C.RESET}")
            _answered = self._batch_query_agentskb(_questions)
            if _answered:
                verified_context = (
                    "<verified_knowledge source=\"KB-FACT\">\n"
                    "Deterministic facts from AgentsKB "
                    "(ground truth, not analysis):\n"
                    + "\n".join(
                        f"- [KB-FACT] {a['question']}: "
                        f"{a['answer']}"
                        for a in _answered)
                    + "\n</verified_knowledge>\n\n")
                print(f"  {C.DIM}Filled "
                      f"{len(_answered)}/"
                      f"{len(_questions)} gaps{C.RESET}")
            else:
                print(f"  {C.DIM}No gaps filled{C.RESET}")
        else:
            print(f"\n{C.BOLD}Step 2: Skipped "
                  f"(no questions extracted){C.RESET}")

        # Inject verified facts into content
        enriched_content = verified_context + content

        if self._interrupted:
            return

        # ── Step 3: Analyze — subsystem or L12 ──
        if is_code:
            subsystems = _split_into_subsystems(
                content, file_name)
            if len(subsystems) > 1:
                print(f"\n{C.BOLD}Step 3: Subsystem analysis "
                      f"({len(subsystems)} regions){C.RESET}")
                # Run subsystem with enriched content
                self._run_subsystem(
                    enriched_content, file_name,
                    general=False)
            else:
                print(f"\n{C.BOLD}Step 3: L12 structural "
                      f"analysis{C.RESET}")
                with self._temporary_model(
                        self._get_prism_model(
                            "l12") or "sonnet"):
                    self._run_single_prism_streaming(
                        "l12", enriched_content, file_name,
                        general=False)
        else:
            print(f"\n{C.BOLD}Step 3: 3-way analysis "
                  f"(text input){C.RESET}")
            self._run_3way_pipeline(
                enriched_content, file_name, general=True)

        if self._interrupted:
            return

        # ── Step 4: Dispute — self-correct (adaptive) ──
        # Load findings from step 3 and decide if dispute is needed.
        # If a conservation law was found, analysis converged — dispute
        # adds correction but less value. If NO law found, dispute is
        # more critical (something may have gone wrong).
        _stem = self._discover_cache_key(file_name)
        _findings_path = (self.working_dir / ".deep"
                          / "findings" / f"{_stem}.md")
        _step3_output = ""
        if _findings_path.exists():
            _step3_output = _findings_path.read_text(
                encoding="utf-8", errors="replace")

        _has_law = (_step3_output
                    and ("conservation law" in _step3_output.lower()
                         or "= constant" in _step3_output.lower()))

        if _step3_output and len(_step3_output) > 200:
            if _has_law:
                print(f"\n{C.BOLD}Step 4: Dispute — "
                      f"self-correction (conservation law "
                      f"found, verifying){C.RESET}")
            else:
                print(f"\n{C.BOLD}Step 4: Dispute — "
                      f"self-correction (no conservation law "
                      f"found, critical check){C.RESET}")
            self._run_dispute(
                enriched_content, file_name,
                general=general)
        else:
            print(f"\n{C.BOLD}Step 4: Skipped "
                  f"(insufficient findings){C.RESET}")

        if self._interrupted:
            return

        # ── Step 5: Save profile + seed knowledge ──
        print(f"\n{C.BOLD}Step 5: Updating codebase "
              f"profile + seeding knowledge{C.RESET}")
        self._update_profile(file_name, prereq_output,
                             _step3_output)
        self._extract_and_queue_knowledge(
            file_name, _step3_output)

        print(f"\n{C.GREEN}══ Smart analysis complete ══"
              f"{C.RESET}")
        print(f"  {C.DIM}Steps: prereq → AgentsKB "
              f"({len(_questions)} questions) → "
              f"{'subsystem' if is_code else '3way'} → "
              f"dispute → profile{C.RESET}")

        # Convergence detection: check if this scan's conservation
        # law matches prior scans. If so, analysis has converged —
        # additional scans add breadth, not depth.
        try:
            import json as _json_conv
            _prof_path = (self.working_dir / ".deep"
                          / "profile.json")
            if _prof_path.exists():
                _prof = _json_conv.loads(
                    _prof_path.read_text(encoding="utf-8"))
                _scan_n = _prof.get("scan_count", 0)
                _laws = _prof.get("conservation_laws", [])
                if _scan_n >= 3 and _laws:
                    print(f"\n{C.BOLD}Convergence check:"
                          f"{C.RESET}")
                    print(f"  {C.DIM}Scan #{_scan_n}. "
                          f"Conservation law: "
                          f"{_laws[-1][:80]}{C.RESET}")
                    if _scan_n >= 5:
                        print(f"  {C.YELLOW}Analysis has likely "
                              f"converged after {_scan_n} "
                              f"scans. Additional scans add "
                              f"breadth, not depth. Consider "
                              f"dispute or reflect for "
                              f"self-correction.{C.RESET}")
        except Exception:
            pass

        self._session_log.append(
            operation="smart",
            file_name=file_name,
            lens="prereq+agentskb+analysis+dispute",
            model=self.session.model,
            mode="smart")

    def _update_profile(self, file_name, prereq_output,
                        analysis_output):
        """D: Update persistent codebase profile from analysis.

        Extracts patterns, conservation laws, and structural
        facts. Accumulates across scans in .deep/profile.json.
        """
        import json as _json_prof
        import datetime as _dt_prof

        _prof_path = self.working_dir / ".deep" / "profile.json"
        _prof_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing profile
        profile = {
            "patterns": [],
            "conservation_laws": [],
            "known_facts": [],
            "scan_count": 0,
            "files_analyzed": [],
            "last_updated": "",
        }
        if _prof_path.exists():
            try:
                profile = _json_prof.loads(
                    _prof_path.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                pass

        # Update metadata
        profile["scan_count"] = profile.get(
            "scan_count", 0) + 1
        profile["last_updated"] = (
            _dt_prof.datetime.now().strftime("%Y-%m-%d %H:%M"))
        _files = profile.get("files_analyzed", [])
        if file_name not in _files:
            _files.append(file_name)
            profile["files_analyzed"] = _files[-20:]

        # Extract conservation laws from analysis — STRICT.
        # Only accept strings that look like actual formulas:
        # must contain × or "x" operator and = sign.
        # Prevents: labels, questions, partial sentences.
        if analysis_output:
            import re as _re_prof
            _laws = _re_prof.findall(
                r'[Cc]onservation [Ll]aw[:\s]*[`"\']*(.+?)'
                r'[`"\']*(?:\n|$)',
                analysis_output)
            _reject = {"none", "n/a", "not found", "unclear",
                       "conceals", "breaks down", "pattern",
                       "cycles", "the conservation"}
            _existing_laws = set(
                profile.get("conservation_laws", []))
            for law in _laws[:5]:
                _clean = law.strip().strip("*`\"'")
                _lower = _clean.lower()
                if (_clean
                        and 15 < len(_clean) < 150
                        and ("=" in _clean or "×" in _clean)
                        and not any(r in _lower
                                    for r in _reject)
                        and _clean not in _existing_laws):
                    _existing_laws.add(_clean)
            # Keep only recent laws — codebases evolve.
            # Old laws from 50 scans ago may not apply.
            profile["conservation_laws"] = list(
                _existing_laws)[-5:]

        # Extract patterns from prereq domains
        if prereq_output:
            import re as _re_prof2
            _domains = _re_prof2.findall(
                r'^\d+\.\s+\*\*(.+?)\*\*',
                prereq_output, _re_prof2.MULTILINE)
            _existing = set(profile.get("patterns", []))
            for d in _domains[:10]:
                if d not in _existing:
                    _existing.add(d)
            profile["patterns"] = list(_existing)[-15:]

        # Merge known facts from KB
        _kb_stem = self._discover_cache_key(file_name)
        _kb_path = (self.working_dir / ".deep" / "knowledge"
                    / f"{_kb_stem}.json")
        if _kb_path.exists():
            try:
                _kb = _json_prof.loads(
                    _kb_path.read_text(encoding="utf-8"))
                _existing_facts = set(
                    profile.get("known_facts", []))
                for entry in _kb[:20]:
                    if isinstance(entry, dict):
                        fact = entry.get("claim", "")
                        if (fact and len(fact) > 10
                                and fact not in _existing_facts):
                            _existing_facts.add(fact)
                profile["known_facts"] = list(
                    _existing_facts)[-30:]
            except (ValueError, OSError):
                pass

        # Save
        try:
            _prof_path.write_text(
                _json_prof.dumps(profile, indent=2,
                                 ensure_ascii=False),
                encoding="utf-8")
            print(f"  {C.DIM}Profile: {profile['scan_count']} "
                  f"scans, {len(profile.get('patterns', []))} "
                  f"patterns, "
                  f"{len(profile.get('conservation_laws', []))} "
                  f"laws{C.RESET}")
        except (OSError, PermissionError):
            pass

    # E: Cross-project knowledge — proven conservation laws by domain
    # From 41 rounds of research across Starlette, Click, Tenacity
    CROSS_PROJECT_LAWS = {
        "web framework": (
            "flexibility x predictability = constant "
            "(more flexible routing = less predictable dispatch)"),
        "routing": (
            "API ergonomics x internal complexity = constant "
            "(clean external API = complex internal state)"),
        "cli": (
            "decorator expressiveness x invocation transparency = "
            "constant (richer decorators = harder to trace execution)"),
        "retry": (
            "resilience x resource consumption = constant "
            "(more retry = more resource pressure)"),
        "async": (
            "concurrency x state isolation = constant "
            "(more concurrent = harder to isolate state)"),
        "middleware": (
            "composability x debuggability = constant "
            "(more composable middleware = harder to trace request flow)"),
        "state": (
            "mutability x predictability = constant "
            "(mutable state = unpredictable behavior)"),
    }

    def _get_cross_project_context(self, content, file_name):
        """E: Detect domain from content, return relevant cross-project laws."""
        _lower = content[:3000].lower()
        relevant = []
        for domain, law in self.CROSS_PROJECT_LAWS.items():
            # Simple keyword matching
            if domain in _lower or domain.replace(" ", "_") in _lower:
                relevant.append(f"- {domain}: {law}")
            elif (domain == "web framework"
                  and any(k in _lower for k in
                          ["route", "request", "response",
                           "middleware", "handler", "endpoint"])):
                relevant.append(f"- {domain}: {law}")
            elif (domain == "async"
                  and any(k in _lower for k in
                          ["async", "await", "asyncio",
                           "coroutine", "event_loop"])):
                relevant.append(f"- {domain}: {law}")
            elif (domain == "retry"
                  and any(k in _lower for k in
                          ["retry", "backoff", "resilience",
                           "circuit", "timeout"])):
                relevant.append(f"- {domain}: {law}")
        return relevant[:3]  # Max 3 relevant laws

    def _extract_and_queue_knowledge(self, file_name,
                                      analysis_output):
        """B: Extract structural facts from analysis, queue for AgentsKB.

        Saves to .deep/seed_queue/ as JSON Q&As. These are facts
        the analysis discovered that should become permanent knowledge.
        When AgentsKB has a seeding API, this queue can be flushed.
        """
        if not analysis_output or len(analysis_output) < 200:
            return

        import json as _json_seed
        import re as _re_seed

        # Extract conservation laws — ONLY from labeled sections.
        # Reject vague matches like "conservation law: none found"
        # or "the conservation law breaks down when..."
        qas = []
        _laws = _re_seed.findall(
            r'[Cc]onservation [Ll]aw[:\s]*["\']?(.+?)["\']?'
            r'(?:\n|$)',
            analysis_output)
        _reject = {"none", "n/a", "not found", "unclear",
                   "breaks down", "does not", "doesn't"}
        for law in _laws[:3]:
            _clean = law.strip().strip("*`")
            _lower = _clean.lower()
            if (_clean and len(_clean) > 15
                    and len(_clean) < 200
                    and not any(r in _lower for r in _reject)
                    and ("=" in _clean or "×" in _clean
                         or " x " in _lower)):
                qas.append({
                    "question": (f"What is the structural "
                                 f"conservation law of "
                                 f"{file_name}?"),
                    "answer": _clean,
                    "topic": "code-analysis",
                    "type": "explanation",
                    "source": f"prism-analysis:{file_name}",
                })

        # Extract structural findings (bug patterns, design facts)
        _findings = _re_seed.findall(
            r'(?:STRUCTURAL|structural)[:\s]+(.+?)(?:\n|$)',
            analysis_output)
        for f in _findings[:5]:
            _clean = f.strip().strip("*`")
            if _clean and len(_clean) > 20:
                qas.append({
                    "question": (f"What structural property "
                                 f"does {file_name} have?"),
                    "answer": _clean,
                    "topic": "code-analysis",
                    "type": "fact",
                    "source": f"prism-analysis:{file_name}",
                })

        if not qas:
            return

        # Save to seed queue
        try:
            _queue_dir = (self.working_dir / ".deep"
                          / "seed_queue")
            _queue_dir.mkdir(parents=True, exist_ok=True)
            _stem = self._discover_cache_key(file_name)
            _queue_path = _queue_dir / f"{_stem}.json"

            _existing = []
            if _queue_path.exists():
                try:
                    _existing = _json_seed.loads(
                        _queue_path.read_text(
                            encoding="utf-8"))
                except (ValueError, OSError):
                    _existing = []

            # Dedup by question
            _existing_q = {e.get("question", "")
                           for e in _existing}
            _new = [q for q in qas
                    if q["question"] not in _existing_q]
            if _new:
                _existing.extend(_new)
                # Cap at 50 per file
                if len(_existing) > 50:
                    _existing = _existing[-50:]
                _queue_path.write_text(
                    _json_seed.dumps(
                        _existing, indent=2,
                        ensure_ascii=False),
                    encoding="utf-8")
                print(f"  {C.DIM}Queued {len(_new)} Q&As "
                      f"for AgentsKB seeding{C.RESET}")

                # Also save extracted facts to local KB
                # so the SAME project benefits immediately.
                _kb_stem = self._discover_cache_key(file_name)
                _kb_dir = (self.working_dir / ".deep"
                           / "knowledge")
                _kb_dir.mkdir(parents=True, exist_ok=True)
                _kb_path = _kb_dir / f"{_kb_stem}.json"
                import time as _time_seed
                _now = _time_seed.time()
                _kb_new = []
                for q in _new:
                    _kb_new.append({
                        "claim": q.get("answer", q["question"]),
                        "type": "STRUCTURAL",
                        "confidence": 0.8,
                        "source": f"prism:{file_name}",
                        "verified": True,
                        "date": _now,
                        "expires": _now + 90 * 86400,
                    })
                if _kb_new:
                    _kb_existing = []
                    if _kb_path.exists():
                        try:
                            _kb_existing = _json_seed.loads(
                                _kb_path.read_text(
                                    encoding="utf-8"))
                        except (ValueError, OSError):
                            _kb_existing = []
                    _kb_claims = {e.get("claim", "")
                                  for e in _kb_existing}
                    _kb_truly_new = [
                        e for e in _kb_new
                        if e["claim"] not in _kb_claims]
                    if _kb_truly_new:
                        _kb_existing.extend(_kb_truly_new)
                        if len(_kb_existing) > 500:
                            _kb_existing = _kb_existing[-500:]
                        _kb_path.write_text(
                            _json_seed.dumps(
                                _kb_existing, indent=2),
                            encoding="utf-8")
        except (OSError, PermissionError):
            pass

    def _run_subsystem(self, content, file_name, general=False):
        """B2: Sub-artifact targeting — different prisms per subsystem.

        Phase 1: AST split into classes/functions.
        Phase 2: Calibration call assigns optimal prism per subsystem.
        Phase 3: Parallel execution with per-subsystem prism.
        Phase 4: Cross-subsystem synthesis.
        """
        if general:
            print(f"{C.YELLOW}Subsystem mode requires code, "
                  f"not text input.{C.RESET}")
            return

        # Phase 1: Split
        print(f"\n{C.BOLD}{C.BLUE}── Subsystem Analysis ── "
              f"{file_name} ──{C.RESET}")
        subsystems = _split_into_subsystems(content, file_name)
        if len(subsystems) <= 1:
            print(f"  {C.YELLOW}File has {len(subsystems)} "
                  f"subsystem(s) — falling back to L12.{C.RESET}")
            self._run_single_prism_streaming(
                "l12", content, file_name, general=False)
            return

        print(f"  {C.DIM}Split into {len(subsystems)} "
              f"subsystems:{C.RESET}")
        for s in subsystems:
            lines = s["end_line"] - s["start_line"] + 1
            print(f"    {s['name']} ({s['kind']}, "
                  f"{lines} lines)")

        # Phase 2: Calibrate — assign prisms
        print(f"\n{C.BOLD}Phase 2: Assigning prisms{C.RESET}")
        # Build prism catalog from OPTIMAL_PRISM_MODEL
        _exclude = {"writer", "writer_critique",
                     "writer_synthesis", "behavioral_synthesis",
                     "l12_complement_adversarial",
                     "l12_synthesis", "l12_universal",
                     "arc_code", "codegen", "prereq"}
        _catalog_lines = []
        for pname in sorted(OPTIMAL_PRISM_MODEL.keys()):
            if pname in _exclude:
                continue
            # Load first line of prism description
            _p = self._load_prism(pname)
            if _p:
                _desc = _p.split("\n")[0][:80] if _p else ""
                _catalog_lines.append(
                    f"- {pname}: {_desc}")
        _catalog = "\n".join(_catalog_lines)

        _summaries = "\n".join(
            f"- {s['name']} ({s['kind']}, "
            f"{s['end_line'] - s['start_line'] + 1} lines): "
            f"{s['content'][:100].strip()}"
            for s in subsystems)

        _cal_prompt = CALIBRATE_SUBSYSTEM_PROMPT.format(
            prism_catalog=_catalog,
            subsystem_summaries=_summaries)

        with self._temporary_model("sonnet"):
            _cal_raw = self._claude.call(
                _cal_prompt, "Assign prisms.",
                model="sonnet", timeout=30)

        # Parse assignments
        import json as _json_sub
        assignments = {}
        if _cal_raw:
            try:
                _raw = _cal_raw
                if "```json" in _raw:
                    _raw = _raw.split("```json")[1].split(
                        "```")[0]
                _parsed = _json_sub.loads(_raw)
                for a in _parsed.get("assignments", []):
                    assignments[a["subsystem"]] = a["prism"]
            except (ValueError, TypeError, KeyError):
                pass

        # Fallback: L12 for unassigned
        for s in subsystems:
            if s["name"] not in assignments:
                assignments[s["name"]] = "l12"

        for name, prism in assignments.items():
            print(f"    {name} → {prism}")

        # Phase 3: Execute per-subsystem
        print(f"\n{C.BOLD}Phase 3: Running "
              f"{len(subsystems)} analyses{C.RESET}")
        outputs = []
        _other_names = ", ".join(
            s["name"] for s in subsystems)

        for s in subsystems:
            if self._interrupted:
                break
            prism_name = assignments.get(s["name"], "l12")

            # Context header
            _header = (
                f"# SUBSYSTEM: {s['name']} "
                f"(lines {s['start_line']}-{s['end_line']} "
                f"of {file_name})\n"
                f"# OTHER SUBSYSTEMS: {_other_names}\n\n")

            with self._temporary_model(
                    self._get_prism_model(
                        prism_name) or "sonnet"):
                output = self._run_single_prism_streaming(
                    prism_name, _header + s["content"],
                    file_name,
                    label=(f"{s['name']} ({prism_name}) "
                           f"── {file_name}"),
                    general=False)
            if output:
                outputs.append({
                    "subsystem": s["name"],
                    "prism": prism_name,
                    "output": output,
                })

        if not outputs:
            print(f"{C.RED}No subsystem outputs{C.RESET}")
            return

        # Phase 4: Synthesis
        print(f"\n{C.BOLD}Phase 4: Cross-subsystem "
              f"synthesis{C.RESET}")
        _sub_outputs = "\n\n---\n\n".join(
            f"## SUBSYSTEM: {o['subsystem']} "
            f"(via {o['prism']})\n\n{o['output']}"
            for o in outputs)
        _synth_prompt = SUBSYSTEM_SYNTHESIS_PROMPT.format(
            n=len(outputs),
            subsystem_outputs=_sub_outputs)

        # Sonnet for subsystem synthesis. Opus times out on
        # large multi-subsystem inputs.
        synth = self._execute_prism(
            system_prompt=_synth_prompt,
            message="Synthesize cross-subsystem findings.",
            model="sonnet",
            label=f"CROSS-SUBSYSTEM SYNTHESIS ── {file_name}",
            save=False,
        )

        # Save all
        combined = _sub_outputs
        if synth:
            combined += (f"\n\n---\n\n"
                         f"## CROSS-SUBSYSTEM SYNTHESIS"
                         f"\n\n{synth}")
        self._save_deep_finding(
            file_name, "subsystem", combined)

        print(f"\n{C.GREEN}Subsystem analysis complete: "
              f"{len(outputs)} subsystems + synthesis"
              f"{C.RESET}")

        self._session_log.append(
            operation="subsystem",
            file_name=file_name,
            lens="+".join(
                o["prism"] for o in outputs) + "+synthesis",
            model=self.session.model,
            mode="subsystem",
            findings_summary=(
                f"{len(outputs)} subsystems: "
                + ", ".join(
                    f"{o['subsystem']}({o['prism']})"
                    for o in outputs)),
        )

    @staticmethod
    def _extract_questions_with_tiers(prereq_output):
        """Extract questions WITH tier tags from prereq output.

        Returns list of (question, tier) tuples where tier is
        'T1', 'T2', 'T3', or None. T1 = verifiable from docs,
        T2 = needs composition, T3 = needs runtime context.
        """
        import re as _re_tier
        if not prereq_output:
            return []

        results = []
        _tag_pat = (r'(?:\s*\[(?:HIGH|MEDIUM|LOW|FACT|REFERENCE|'
                    r'TROUBLESHOOTING|METHODOLOGY|EXPLANATION|'
                    r'DECISION|T1|T2|T3)\])*')

        for line in prereq_output.split("\n"):
            line = line.strip()
            # Match numbered or bullet items
            m = _re_tier.match(
                r'^\d+\.\s*(.+)$|^[-*]\s*(.+)$', line)
            if not m:
                continue
            text = (m.group(1) or m.group(2)).strip()
            if "?" not in text or len(text) < 15:
                continue

            # Extract tier
            tier = None
            tier_m = _re_tier.search(r'\[(T[123])\]', text)
            if tier_m:
                tier = tier_m.group(1)
                text = text.replace(
                    tier_m.group(0), "").strip()

            # Strip other tags
            text = _re_tier.sub(
                r'\[(?:HIGH|MEDIUM|LOW|FACT|REFERENCE|'
                r'TROUBLESHOOTING|METHODOLOGY|EXPLANATION|'
                r'DECISION)\]', "", text).strip().strip("*")

            if text and len(text) > 15:
                results.append((text, tier))

        # Dedup
        seen = set()
        unique = []
        for q, t in results:
            lower = q.lower()
            if lower not in seen:
                seen.add(lower)
                unique.append((q, t))
        return unique[:50]

    @staticmethod
    def _extract_questions_from_prereq(prereq_output):
        """Extract atomic questions from prereq prism output.

        Shared by _run_prereq and _run_smart. Returns plain
        question strings (strips tier tags).
        """
        tiered = PrismREPL._extract_questions_with_tiers(
            prereq_output)
        return [q for q, t in tiered]
        for q in questions:
            lower = q.lower()
            if lower not in seen:
                seen.add(lower)
                unique.append(q)
        return unique[:50]

    def _run_prereq(self, content, file_name, general=False):
        """Prereq: identify knowledge prerequisites for a task.

        Runs prereq prism → extracts atomic questions → batch queries
        AgentsKB → returns task + knowledge context.
        """
        print(f"\n{C.BOLD}{C.BLUE}── Prerequisites ── "
              f"{file_name} ──{C.RESET}")
        print(f"  {C.DIM}Phase 1: Identify knowledge gaps. "
              f"Phase 2: Batch query AgentsKB.{C.RESET}")

        # Phase 1: Run prereq prism
        print(f"\n{C.BOLD}Phase 1: Knowledge prerequisite "
              f"scan{C.RESET}")
        with self._temporary_model(
                self._get_prism_model("prereq") or "sonnet"):
            prereq_output = self._run_single_prism_streaming(
                "prereq", content, file_name, general=True)

        if not prereq_output or not prereq_output.strip():
            print(f"{C.RED}Prereq scan returned empty{C.RESET}")
            return

        # Phase 2: Extract questions from output
        print(f"\n{C.BOLD}Phase 2: Extracting atomic "
              f"questions{C.RESET}")
        _tiered = self._extract_questions_with_tiers(
            prereq_output)
        _questions = [q for q, t in _tiered]

        # Report tier distribution
        _t1 = [q for q, t in _tiered if t == "T1"]
        _t2 = [q for q, t in _tiered if t == "T2"]
        _t3 = [q for q, t in _tiered if t == "T3"]
        _untagged = [q for q, t in _tiered if t is None]
        print(f"  {C.DIM}Found {len(_questions)} questions"
              f"{C.RESET}")
        if _t1 or _t2 or _t3:
            print(f"  {C.DIM}  T1 (verifiable): {len(_t1)}"
                  f"  T2 (composite): {len(_t2)}"
                  f"  T3 (frontier): {len(_t3)}"
                  f"  untagged: {len(_untagged)}{C.RESET}")
        if _t3:
            print(f"  {C.YELLOW}T3 questions are "
                  f"confabulation risk zones — models "
                  f"will guess answers for these."
                  f"{C.RESET}")

        if not _questions:
            print(f"  {C.YELLOW}No questions extracted."
                  f"{C.RESET}")
            self._save_deep_finding(
                file_name, "prereq", prereq_output)
            return

        # Phase 3: Batch query AgentsKB
        # Prioritize T1 questions (highest hit rate)
        _query_order = (_t1 + _untagged + _t2)[:30]
        if not _query_order:
            _query_order = _questions[:30]

        print(f"\n{C.BOLD}Phase 3: Querying AgentsKB "
              f"({len(_query_order)} questions, "
              f"T1-priority){C.RESET}")
        _answered = self._batch_query_agentskb(
            _query_order)
        _answered_count = len(_answered)
        _total = len(_questions)
        _ratio = (_answered_count / len(_query_order) * 100
                  if _query_order else 0)
        print(f"  {C.DIM}Answered: {_answered_count}/"
              f"{len(_query_order)} ({_ratio:.0f}%)"
              f"{C.RESET}")
        if _ratio < 20:
            print(f"  {C.YELLOW}Low coverage ({_ratio:.0f}%)"
                  f" — this tech stack may not be in "
                  f"AgentsKB yet.{C.RESET}")

        # Build knowledge context
        _context_parts = []
        for a in _answered:
            _context_parts.append(
                f"Q: {a['question']}\n"
                f"A: {a['answer']}\n"
                f"Source: {', '.join(a.get('sources', ['agentskb']))}")
        _knowledge = "\n\n".join(_context_parts)

        _unanswered = [
            q for q in _questions
            if q not in {a["question"] for a in _answered}]

        # Save combined output with tier breakdown
        _tier_summary = ""
        if _t1 or _t2 or _t3:
            _tier_summary = (
                f"\n\n## TIER BREAKDOWN\n"
                f"- T1 (verifiable): {len(_t1)} questions\n"
                f"- T2 (composite): {len(_t2)} questions\n"
                f"- T3 (frontier/confabulation risk): "
                f"{len(_t3)} questions\n"
                f"- Answer ratio: {_ratio:.0f}% "
                f"({_answered_count}/{len(_query_order)})\n")
            if _t3:
                _tier_summary += (
                    "\nT3 CONFABULATION RISKS:\n"
                    + "\n".join(f"- {q}" for q in _t3[:10])
                    + "\n")

        combined = (
            f"## PREREQUISITE SCAN\n\n{prereq_output}\n\n"
            f"---\n\n"
            f"## KNOWLEDGE BASE ANSWERS "
            f"({_answered_count}/{_total})\n\n"
            f"{_knowledge or '(no answers found)'}\n\n"
            f"---\n\n"
            f"## UNANSWERED ({len(_unanswered)})\n\n"
            + ("\n".join(f"- {q}" for q in _unanswered)
               if _unanswered else "(all answered)")
            + _tier_summary)
        self._save_deep_finding(
            file_name, "prereq", combined)

        print(f"\n{C.GREEN}Prereq complete: "
              f"{_answered_count}/{_total} questions "
              f"answered{C.RESET}")
        if _unanswered:
            print(f"  {C.YELLOW}{len(_unanswered)} "
                  f"unanswered — these need manual "
                  f"research{C.RESET}")

        self._session_log.append(
            operation="prereq",
            file_name=file_name,
            lens="prereq+agentskb",
            model=self.session.model,
            mode="prereq",
            findings_summary=(
                f"{_answered_count}/{_total} answered"),
        )

    def _run_verified_pipeline(self, content, file_name,
                               general=False):
        """Verified: Full gap detection + re-analysis pipeline.

        L12 → boundary + audit → extract gaps → display →
        re-run L12 with verified facts for corrected output.
        4 Sonnet calls. Highest accuracy mode. (P212)
        """
        print(f"\n{C.BOLD}{C.BLUE}── Verified Analysis ── "
              f"{file_name} ──{C.RESET}")
        print(f"  {C.DIM}4-step: L12 → gap detect → extract → "
              f"re-analyze with corrections{C.RESET}")

        # Step 1: Run gaps pipeline (L12 + boundary + audit)
        # Reuse gaps logic inline to keep outputs accessible
        l12_model = self._get_prism_model("l12") or "sonnet"

        # L12
        print(f"\n{C.BOLD}Step 1/4: L12 structural analysis"
              f"{C.RESET}")
        with self._temporary_model(l12_model):
            l12_output = self._run_single_prism_streaming(
                "l12", content, file_name, general=general)
        if not l12_output or not l12_output.strip():
            print(f"{C.RED}L12 returned empty{C.RESET}")
            return

        # Boundary + Audit on L12 output
        print(f"\n{C.BOLD}Step 2/4: Gap detection "
              f"(boundary + audit){C.RESET}")
        with self._temporary_model(
                self._get_prism_model(
                    "knowledge_boundary") or "sonnet"):
            boundary = self._run_single_prism_streaming(
                "knowledge_boundary", l12_output, file_name,
                label=f"BOUNDARY ── {file_name}", general=True)

        with self._temporary_model(
                self._get_prism_model(
                    "knowledge_audit") or "sonnet"):
            audit = self._run_single_prism_streaming(
                "knowledge_audit", l12_output, file_name,
                label=f"AUDIT ── {file_name}", general=True)

        # Step 3: Extract gaps as structured list
        print(f"\n{C.BOLD}Step 3/4: Extracting knowledge gaps"
              f"{C.RESET}")
        gap_input = (f"{boundary or ''}\n\n---\n\n"
                     f"{audit or ''}")
        gap_prompt = self._load_intent(
            "gap_extract_v2",
            "Extract every knowledge gap as a JSON array. "
            "For each: claim, type, fill_source, query, "
            "risk, impact, confidence.")
        with self._temporary_model("haiku"):
            gap_json = self._claude.call(
                gap_prompt, gap_input, model="haiku", timeout=60)

        if gap_json:
            # Print JSON so -o tee captures gap data
            print(gap_json, flush=True)
            print(f"  {C.DIM}Gaps extracted: "
                  f"{gap_json.count('claim')}"
                  f" knowledge gaps found{C.RESET}")

        # Step 3b: J7 — Fill gaps via AgentsKB (free, no auth)
        _agentskb_facts = ""
        if gap_json:
            print(f"\n{C.BOLD}Step 3b: Filling gaps via "
                  f"AgentsKB{C.RESET}")
            _filled = self._fill_gaps_agentskb(gap_json)
            if _filled:
                _agentskb_facts = "\n".join(
                    f"- VERIFIED: {f['claim']} → {f['answer']} "
                    f"[source: {f['source']}]"
                    for f in _filled)
                print(f"  {C.DIM}Filled {len(_filled)} gaps "
                      f"via AgentsKB{C.RESET}")
            else:
                print(f"  {C.DIM}No gaps filled (topics "
                      f"not covered){C.RESET}")

        # Step 4: Re-run L12 with gap context + filled facts
        print(f"\n{C.BOLD}Step 4/4: Re-analysis with gap "
              f"awareness{C.RESET}")
        _facts_section = gap_json or "No gaps extracted."
        if _agentskb_facts:
            _facts_section += (
                "\n\nVERIFIED FACTS (from AgentsKB — "
                "treat as authoritative):\n"
                + _agentskb_facts)
        verified_context = (
            "<verified_knowledge source=\"GAP-ANALYSIS\">\n"
            "Knowledge gaps detected in initial analysis. "
            "Items marked [KB-FACT] are ground truth. "
            "Unresolved gaps: verify from source or mark "
            "UNVERIFIABLE.\n\n"
            f"{_facts_section}\n"
            "</verified_knowledge>\n\n"
            f"{content}")
        with self._temporary_model(l12_model):
            verified_output = self._run_single_prism_streaming(
                "l12", verified_context, file_name,
                label=f"VERIFIED ── {file_name}",
                general=general)

        # Save all outputs
        combined = (
            f"## INITIAL L12 ANALYSIS\n\n{l12_output}\n\n"
            f"---\n\n"
            f"## KNOWLEDGE GAPS DETECTED\n\n"
            f"### Boundary\n\n{boundary or '(empty)'}\n\n"
            f"### Audit\n\n{audit or '(empty)'}\n\n"
            f"### Extracted Gaps\n\n"
            f"```json\n{gap_json or '[]'}\n```\n\n"
            f"---\n\n"
            f"## VERIFIED ANALYSIS (corrected)\n\n"
            f"{verified_output or '(empty)'}")
        self._save_deep_finding(file_name, "verified", combined)

        print(f"\n{C.GREEN}Verified pipeline complete: "
              f"4 steps{C.RESET}")
        print(f"  {C.DIM}Initial: {len(l12_output.split())}w"
              f"{C.RESET}")
        if verified_output:
            print(f"  {C.DIM}Verified: "
                  f"{len(verified_output.split())}w"
                  f"{C.RESET}")
        print(f"  {C.DIM}Findings: .deep/findings/{C.RESET}")

        # J10: Save verified facts to persistent KB (shared helper)
        if gap_json and file_name:
            self._save_gaps_to_kb(file_name, gap_json)

        self._session_log.append(
            operation="verified",
            file_name=file_name,
            lens="l12+boundary+audit+extract+verified",
            model=self.session.model,
            mode="verified",
        )

    def _discover_available_tools(self):
        """Meta: discover available prisms from disk at runtime.

        Reads prisms/ directory, extracts name + description from
        YAML frontmatter. The strategist uses this to know ALL
        available tools without hardcoding. New prisms are
        automatically discovered.
        """
        import re as _re_disc
        prisms_dir = self.working_dir / "prisms"
        if not prisms_dir.exists():
            return ""
        lines = []
        for p in sorted(prisms_dir.glob("*.md")):
            try:
                text = p.read_text(encoding="utf-8",
                                   errors="replace")
                if not text.startswith("---"):
                    continue
                yaml = text.split("---")[1]
                name = _re_disc.search(
                    r'name:\s*(.+)', yaml)
                desc = _re_disc.search(
                    r'description:\s*["\']?(.+?)["\']?\s*$',
                    yaml, _re_disc.MULTILINE)
                model = _re_disc.search(
                    r'optimal_model:\s*(\w+)', yaml)
                if name and desc:
                    _n = name.group(1).strip()
                    _d = desc.group(1).strip()[:100]
                    _m = model.group(1) if model else "?"
                    lines.append(f"- {_n} [{_m}]: {_d}")
            except (OSError, UnicodeDecodeError):
                continue
        return "\n".join(lines) if lines else ""

    def _run_strategist(self, content, file_name, general=False):
        """Strategist: 2-call meta-agent (plan + adversarial critique).

        Call 1: Plan the optimal tool sequence for the goal.
        Call 2: Adversarial critique — find gaps, add conditionals,
                produce revised plan with fallbacks. (P221)
        """
        print(f"\n{C.BOLD}{C.CYAN}── STRATEGIST ── "
              f"{file_name} ──{C.RESET}")

        goal = getattr(self, '_custom_intent', None)
        if not goal:
            goal = (f"Provide the most valuable analytical "
                    f"insight about {file_name}")

        print(f"  {C.DIM}Goal: {goal}{C.RESET}")

        with self._temporary_model("sonnet"):
            # Call 1: Plan
            print(f"\n{C.BOLD}Call 1/2: Strategy planning"
                  f"{C.RESET}")
            strategist_prompt = self._load_prism("strategist")
            if not strategist_prompt:
                print(f"{C.RED}Strategist prism not found"
                      f"{C.RESET}")
                return

            # Meta: strategist discovers its own tools from disk
            # instead of relying only on its static list.
            _discovered = self._discover_available_tools()
            if _discovered:
                strategist_prompt += (
                    "\n\nDISCOVERED TOOLS (auto-detected from "
                    "prisms/ directory — may include tools not "
                    "listed above):\n" + _discovered)
                return

            # Build dynamic context so strategist knows the ACTUAL state
            _dyn_ctx = ""
            try:
                import json as _json_strat
                # Prior scans (from profile)
                _prof_path = (self.working_dir / ".deep"
                              / "profile.json")
                if _prof_path.exists():
                    _prof = _json_strat.loads(
                        _prof_path.read_text(encoding="utf-8"))
                    _sc = _prof.get("scan_count", 0)
                    _laws = _prof.get("conservation_laws", [])
                    _dyn_ctx += (
                        f"\nPRIOR ANALYSIS STATE:\n"
                        f"- {_sc} prior scans on this codebase\n"
                        f"- Conservation laws found: "
                        f"{_laws[:3] if _laws else 'none yet'}\n")
                # False positives (from learning)
                _learn_path = (self.working_dir / ".deep"
                               / "learning.json")
                if _learn_path.exists():
                    _learn = _json_strat.loads(
                        _learn_path.read_text(encoding="utf-8"))
                    _fps = [e for e in _learn
                            if e.get("type") in (
                                "false_positive", "rejected_fix")]
                    if _fps:
                        _dyn_ctx += (
                            f"- Known false positives: "
                            f"{[e.get('issue','') for e in _fps[-3:]]}\n")
                # KB coverage
                _kb_stem = self._discover_cache_key(file_name)
                _kb_path = (self.working_dir / ".deep"
                            / "knowledge" / f"{_kb_stem}.json")
                if _kb_path.exists():
                    _kb = _json_strat.loads(
                        _kb_path.read_text(encoding="utf-8"))
                    _dyn_ctx += (
                        f"- Knowledge base: {len(_kb)} verified "
                        f"facts for this file\n")
            except Exception:
                pass

            plan_input = (
                f"GOAL: {goal}\n\n"
                f"TARGET: {file_name} "
                f"({'non-code text' if general else 'source code'})"
                f"{_dyn_ctx}"
                f"\n\nTARGET PREVIEW (first 2000 chars):\n"
                f"{content[:2000]}")

            plan = self._claude.call(
                strategist_prompt, plan_input,
                model="sonnet", timeout=120)

            if not plan:
                print(f"{C.RED}Strategy planning failed"
                      f"{C.RESET}")
                return

            print(plan, flush=True)

            # Call 2: Adversarial critique (P221)
            print(f"\n{C.BOLD}Call 2/2: Adversarial critique"
                  f"{C.RESET}")
            critique_prompt = (
                "You are an adversarial reviewer of analytical "
                "strategies. Attack the strategy below:\n"
                "1. What steps are wasteful or redundant?\n"
                "2. What is MISSING (synthesis, verification, "
                "fallbacks)?\n"
                "3. What order is wrong? (composition is "
                "non-commutative — L12 must come before audit)\n"
                "4. Are there cheaper alternatives that "
                "achieve the same goal?\n"
                "5. What CONDITIONS should gate each step?\n\n"
                "Then output a REVISED STRATEGY with:\n"
                "- Conditional steps (IF/THEN)\n"
                "- Fallbacks for each step\n"
                "- Synthesis step at the end\n"
                "- Budget estimate\n"
                "For each step, output COMMAND: the exact "
                "prism.py command to run.")
            critique = self._claude.call(
                critique_prompt,
                f"GOAL: {goal}\n\nSTRATEGY:\n{plan}",
                model="sonnet", timeout=120)

            if critique:
                print(critique, flush=True)
                # Use the revised plan for execution
                plan = critique

            combined = (
                f"## INITIAL STRATEGY\n\n{plan}\n\n---\n\n"
                f"## ADVERSARIAL CRITIQUE + REVISED PLAN"
                f"\n\n{critique or '(no critique)'}")
            self._save_deep_finding(
                file_name, "strategist", combined)

            # Phase 2: Extract and execute commands from the plan
            # Look for COMMAND: lines in the plan
            import re as _re_strat
            commands = _re_strat.findall(
                r'COMMAND:\s*(.+?)(?:\n|$)', plan)

            if commands and not self._interrupted:
                print(f"\n{C.BOLD}{C.CYAN}"
                      f"Strategy has {len(commands)} steps. "
                      f"Execute?{C.RESET}")
                if hasattr(self, '_quiet') and self._quiet:
                    execute = True
                else:
                    try:
                        answer = input(
                            f"  [y]es / [n]o / [s]tep-by-step: "
                        ).strip().lower()
                        execute = answer in ('y', 'yes')
                        step_by_step = answer in ('s', 'step')
                    except (EOFError, KeyboardInterrupt):
                        execute = False
                        step_by_step = False

                if execute or step_by_step:
                    for i, cmd in enumerate(commands, 1):
                        if self._interrupted:
                            break
                        cmd = cmd.strip().strip('`')
                        print(f"\n{C.BOLD}Step {i}/"
                              f"{len(commands)}: {cmd}{C.RESET}")

                        # Parse the command and dispatch
                        # Strip the "python3 prism.py --scan" prefix
                        scan_match = _re_strat.search(
                            r'(?:--scan\s+)?(\S+)\s+(single|full|'
                            r'3way|behavioral|meta|verified|l12g|'
                            r'gaps|oracle|scout|evolve)',
                            cmd)
                        if scan_match:
                            _target = scan_match.group(1)
                            _mode = scan_match.group(2)
                            print(f"  {C.DIM}Executing: "
                                  f"/scan {_target} {_mode}"
                                  f"{C.RESET}")
                            self._cmd_scan(
                                f"{file_name} {_mode}")
                        else:
                            print(f"  {C.DIM}Cannot auto-execute:"
                                  f" {cmd}{C.RESET}")

                        if step_by_step and i < len(commands):
                            try:
                                cont = input(
                                    "  Continue? [y/n]: "
                                ).strip().lower()
                                if cont not in ('y', 'yes'):
                                    break
                            except (EOFError, KeyboardInterrupt):
                                break

        print(f"\n{C.GREEN}Strategist complete{C.RESET}")

        self._session_log.append(
            operation="strategist",
            file_name=file_name, lens="strategist",
            model=self.session.model,
            mode="strategist")

    def _run_scout(self, content, file_name, general=False):
        """Scout: Oracle Phases 1-2 → targeted verify on flagged claims.

        2-call pipeline: more depth than Oracle (Phase 1 gets more tokens),
        targeted verification only on KNOWLEDGE/ASSUMED claims.
        Best trust-per-dollar after Oracle. (R-P6)
        """
        print(f"\n{C.BOLD}{C.BLUE}── Scout → Verify ── "
              f"{file_name} ──{C.RESET}")
        print(f"  {C.DIM}2-call: Oracle scout (depth+type) → "
              f"targeted verify (KNOWLEDGE/ASSUMED only)"
              f"{C.RESET}")

        # Call 1: Oracle Phases 1-2 (structural depth + epistemic typing)
        scout_prompt = (
            "You are a structural analyst. Execute these two "
            "phases.\n\n"
            "PHASE 1 — STRUCTURAL DEPTH: Name three properties "
            "this artifact simultaneously claims. Prove they "
            "cannot coexist. Derive the conservation law: "
            "A × B = constant. Name the concealment mechanism. "
            "Engineer an improvement that recreates the problem "
            "deeper.\n\n"
            "PHASE 2 — EPISTEMIC TYPING: For every claim, "
            "classify:\n"
            "- [STRUCTURAL: 1.0] derivable from source alone\n"
            "- [DERIVED: 0.8-0.95] logical consequence\n"
            "- [MEASURED: 0.6-0.8] verifiable by testing\n"
            "- [KNOWLEDGE: 0.3-0.6] requires external data\n"
            "- [ASSUMED: 0.1-0.3] unverifiable assertion\n"
            "Tag each claim inline.")
        print(f"\n{C.BOLD}Call 1/2: Scout (depth + typing)"
              f"{C.RESET}")
        _scout_model = self._get_prism_model("l12") or "sonnet"
        with self._temporary_model(_scout_model):
            scout_output = self._claude.call(
                scout_prompt, content[:30000],
                model=_scout_model, timeout=300)
        # Print so -o tee captures non-streaming output
        if scout_output:
            print(scout_output, flush=True)

        if not scout_output or not scout_output.strip():
            print(f"{C.RED}Scout returned empty{C.RESET}")
            return

        # Call 2: Verify only KNOWLEDGE/ASSUMED claims
        verify_prompt = (
            "The analysis below contains epistemically typed "
            "claims. Focus ONLY on claims tagged [KNOWLEDGE] "
            "or [ASSUMED].\n\n"
            "For each:\n"
            "1. Can you verify it from the source code? "
            "If yes → upgrade to [STRUCTURAL] or [DERIVED].\n"
            "2. If NOT verifiable → mark [UNVERIFIABLE] and "
            "state what external source would verify it.\n"
            "3. If you suspect confabulation → mark [RETRACTED]."
            "\n\nOutput the corrected analysis with updated "
            "tags. Keep all [STRUCTURAL] and [DERIVED] claims "
            "unchanged.")
        print(f"\n{C.BOLD}Call 2/2: Targeted verification"
              f"{C.RESET}")
        with self._temporary_model("haiku"):
            verified = self._claude.call(
                verify_prompt, scout_output[:10000],
                model="haiku", timeout=120)
        # Print so -o tee captures
        if verified:
            print(verified, flush=True)

        # Combine and save
        combined = (
            f"## SCOUT (structural depth + epistemic typing)\n\n"
            f"{scout_output}\n\n---\n\n"
            f"## VERIFICATION (targeted, KNOWLEDGE/ASSUMED "
            f"only)\n\n{verified or '(empty)'}")
        self._save_deep_finding(file_name, "scout", combined)

        # Trust score
        if verified:
            _total_claims = (verified.count("[STRUCTURAL")
                             + verified.count("[DERIVED")
                             + verified.count("[KNOWLEDGE")
                             + verified.count("[ASSUMED")
                             + verified.count("[RETRACTED"))
            _safe = (verified.count("[STRUCTURAL")
                     + verified.count("[DERIVED"))
            if _total_claims > 0:
                _pct = int(100 * _safe / _total_claims)
                print(f"\n{C.BOLD}Trust: {_pct}% "
                      f"source-grounded{C.RESET}")

        print(f"\n{C.GREEN}Scout→Verify complete: "
              f"2 calls{C.RESET}")

        self._session_log.append(
            operation="scout",
            file_name=file_name, lens="scout",
            model=self.session.model, mode="scout")

    @staticmethod
    def _parse_selection(selection_str, max_val):
        """Parse '1,3,5-7' or '*' into sorted list of 1-based ints."""
        if not selection_str or selection_str.strip() == '*':
            return list(range(1, max_val + 1))
        indices = set()
        for part in selection_str.split(','):
            part = part.strip()
            if '-' in part:
                try:
                    start, end = part.split('-', 1)
                    s, e = int(start), int(end)
                    if s > e:
                        s, e = e, s  # Auto-reverse "5-3" → "3-5"
                    for i in range(s, e + 1):
                        if 1 <= i <= max_val:
                            indices.add(i)
                except ValueError:
                    pass
            else:
                try:
                    i = int(part)
                    if 1 <= i <= max_val:
                        indices.add(i)
                except ValueError:
                    pass
        return sorted(indices)

    def _load_cached_pipeline(self, cache_dir):
        """Load cached pipeline prisms from a directory.

        Files named NN_name.md (e.g. 00_primary.md) are loaded in order.
        Returns list of {name, prompt, role, order} dicts, or None.
        """
        if not cache_dir.is_dir():
            return None
        files = sorted(cache_dir.glob("*.md"))
        if len(files) < 2:
            return None
        prisms = []
        for f in files:
            text = f.read_text(encoding="utf-8")
            name = f.stem.split("_", 1)[1] if "_" in f.stem else f.stem
            prisms.append({"name": name, "prompt": text,
                           "role": name, "order": len(prisms)})
        return prisms

    def _run_discover(self, content, file_name, general=False,
                      refresh=False):
        """Discover mode: brainstorm domains, show numbered list, stop.

        1. Detect/infer domain from content
        2. Brainstorm domains (no prism cooking)
        3. Display numbered list with descriptions
        4. Save to self._discover_results + .deep/discover_{stem}.json

        Args:
            refresh: If True, skip cache and force re-discovery.
        """
        domain = self._infer_domain(content, file_name, general,
                                     for_discover=True)
        print(f"{C.CYAN}Discover: artifact type='{domain}'{C.RESET}")

        # Check for cached discover results
        cached = self._load_discover_results(file_name, refresh=refresh)
        if cached:
            print(f"{C.DIM}Using {len(cached)} cached domains{C.RESET}")
            discover = cached
        else:
            sample = content[:3000] if len(content) > 3000 else content
            results = self._discover_domains(domain, sample)
            if not results:
                print(f"{C.RED}Could not discover domains for "
                      f"'{domain}'{C.RESET}")
                return

            # Build discover results
            discover = []
            for item in results:
                discover.append({
                    "name": item["name"],
                    "description": item.get("description", ""),
                    "domain": domain,
                    "type": item.get("type", "structural"),
                })

            self._discover_results = discover
            self._save_discover_results(discover, file_name)

        # Rank domains by historical yield (highest first)
        discover = self._yield_tracker.rank_domains(discover)

        # Display summary table
        print(f"\n{C.BOLD}Discovered {len(discover)} domains:{C.RESET}\n")

        max_name_len = max((len(item['name']) for item in discover), default=12)
        max_desc_len = 60

        # Header
        print(f"  {C.CYAN}{'#':<3}{C.RESET} {C.CYAN}{'Domain':<{max_name_len}}{C.RESET} {C.CYAN}Score{C.RESET} {C.CYAN}Description{C.RESET}")
        print(f"  {C.DIM}{'-' * (3 + 1 + max_name_len + 1 + 5 + 1 + max_desc_len)}{C.RESET}")

        # Rows: sort by yield score (already done by rank_domains above)
        for i, item in enumerate(discover, 1):
            name = item['name'][:max_name_len].ljust(max_name_len)
            desc = item.get('description', '')[:max_desc_len]
            dtype = item.get('type', 'structural')
            yield_score = self._yield_tracker.get_yield_score(item['name'])
            score_str = f"{yield_score:.2f}".rjust(5)
            type_tag = f" {C.YELLOW}[escape]{C.RESET}" if dtype == "escape" else ""
            print(f"  {C.CYAN}{i:<3}{C.RESET} {C.GREEN}{name}{C.RESET}{type_tag} {C.CYAN}{score_str}{C.RESET} {C.DIM}{desc}{C.RESET}")

        print(f"\n{C.BOLD}{C.GREEN}Ready to expand:{C.RESET}")
        print(f"  /expand 1,3 single       cook 1 prism per area, run")
        print(f"  /expand 1,3 full         cook pipeline per area, run")
        print(f"  /expand * full           all areas as full prism")
        print(f"  /expand 2-4              prompt single/full per area")
        print(f"\n  {C.DIM}/scan {file_name} discover full   broader brainstorm (multi-pass){C.RESET}")

        # TRACK: log discover operation
        domain_names = [d["name"] for d in discover]
        self._session_log.append(
            operation="discover",
            file_name=file_name,
            domains=domain_names,
            model=self.session.model,
        )

    def _run_discover_full(self, content, file_name, general=False):
        """Full discover: multi-pass area brainstorming (no analysis).

        1. Cook a brainstorming pipeline (cooker decides passes)
        2. Run each pass, chaining brainstorm outputs
        3. Extract area prisms from the combined brainstorming
        4. Save and display as normal discover results

        Unlike scan full (which does deep analysis), discover full
        only brainstorms WHAT areas/domains exist — including non-obvious
        ones like marketing, teaching value, user psychology, etc.

        Returns True if domains were successfully extracted, False otherwise.
        """
        domain = self._infer_domain(content, file_name, general,
                                     for_discover=True)
        sample = content[:3000] if len(content) > 3000 else content

        print(f"{C.CYAN}Discover Full: "
              f"domain='{domain}'{C.RESET}")

        # Step 1: Cook the brainstorming pipeline
        prompt = COOK_UNIVERSAL_PIPELINE.format(
            intent=f"discover all investigation angles for: "
            f"{domain} — brainstorm domains and perspectives, "
            f"not analysis. Find obvious AND non-obvious angles")
        user_input = (
            f"Generate a brainstorming pipeline to find ALL "
            f"possible domains this artifact could be investigated through.\n\n"
            f"Sample artifact:\n\n{sample}")

        print(f"  {C.CYAN}Cooking brainstorm pipeline..."
              f"{C.RESET}")
        raw = self._call_model(prompt, user_input, timeout=90,
                               model=COOK_MODEL)

        parsed = self._parse_stage_json(
            raw, "cook_discover_full")
        if not isinstance(parsed, list) or len(parsed) < 2:
            reason = "no response" if not raw else (
                f"got {type(parsed).__name__}" if parsed is not None
                else "unparseable response")
            print(f"{C.RED}Failed to cook brainstorm pipeline "
                  f"({reason}){C.RESET}")
            if raw:
                print(f"  {C.DIM}{raw[:200]}{'...' if len(raw) > 200 else ''}{C.RESET}")
            return False

        # Show pipeline structure
        passes = []
        for i, item in enumerate(parsed):
            name = item.get("name", f"pass_{i + 1}")
            name = re.sub(r'[^a-z0-9_]', '_', name.lower())
            text = item.get("prompt", "")
            role = item.get("role", f"pass_{i + 1}")
            if not text:
                continue
            passes.append({"name": name, "prompt": text,
                           "role": role})
            preview = text[:60] + (
                "..." if len(text) > 60 else "")
            print(f"    {C.GREEN}{role}{C.RESET} ({name}): "
                  f"{C.DIM}{preview}{C.RESET}")

        if len(passes) < 2:
            print(f"{C.RED}Need at least 2 passes{C.RESET}")
            return False

        # Step 2: Run brainstorming passes with chaining
        outputs = []
        for i, bp in enumerate(passes):
            role = bp.get("role", bp["name"])
            if i == 0:
                msg = (f"List every possible domain this artifact "
                       f"could be investigated through.\n\n"
                       f"Include BOTH technical domains (architecture, "
                       f"error handling, security, performance) AND "
                       f"non-technical domains (user onboarding, "
                       f"documentation strategy, marketing positioning, "
                       f"competitive differentiation, cost model, "
                       f"team scaling, teaching value, user psychology, "
                       f"accessibility, regulatory implications).\n\n"
                       f"Each domain must be genuinely different — not "
                       f"variations within one.\n\n{sample}")
            else:
                parts = [f"# ARTIFACT\n\n{sample}"]
                for j, prev in enumerate(outputs):
                    prev_role = passes[j].get(
                        "role", passes[j]["name"]).upper()
                    parts.append(
                        f"# BRAINSTORM {j + 1}: {prev_role}"
                        f"\n\n{prev}")
                parts.append(
                    f"# INSTRUCTION\n\n"
                    f"Find domains the previous passes MISSED. "
                    f"Especially look for non-technical angles: "
                    f"UX, product design, business model, "
                    f"documentation, onboarding, psychology, "
                    f"ecosystem integration, community building. "
                    f"Also find cross-domain connections.")
                msg = "\n\n---\n\n".join(parts)

            print(f"\n{C.BOLD}{C.BLUE}── Discover {role} ── "
                  f"{file_name} ──{C.RESET}")
            backend = ClaudeBackend(
                model=self.session.model,
                working_dir=str(self.working_dir),
                system_prompt=bp["prompt"],
                tools=False,
            )
            output = self._stream_and_capture(backend, msg)

            if output and not self._interrupted:
                outputs.append(output)
            if not output or self._interrupted:
                break

        if not outputs:
            return False

        # Step 3: Extract area prisms from brainstorming
        # Cap each pass to avoid token overload on the extraction call
        max_per_pass = 2000
        trimmed = []
        for out in outputs:
            if len(out) > max_per_pass:
                trimmed.append(out[:max_per_pass] + "\n[... truncated]")
            else:
                trimmed.append(out)
        all_brainstorming = "\n\n---\n\n".join(trimmed)

        print(f"\n  {C.CYAN}Extracting domains from "
              f"brainstorming ({len(outputs)} passes)...{C.RESET}")

        extract_prompt = _get_domain_prompt("brainstorming")
        extract_input = (
            f"Extract EVERY domain mentioned in the brainstorming below. "
            f"Preserve the full diversity — technical, business, psychological, "
            f"educational, legal, epistemological, cross-domain, and any others.\n\n"
            f"Brainstorming results:\n\n"
            f"{all_brainstorming}")

        raw_domains = self._call_model(
            extract_prompt, extract_input, timeout=120)
        domain_parsed = self._parse_stage_json(
            raw_domains, "cook_discover_full_domains")

        # Retry with even shorter input if extraction failed
        if not isinstance(domain_parsed, list) and len(outputs) > 3:
            print(f"  {C.YELLOW}Retrying extraction with "
                  f"condensed input...{C.RESET}")
            condensed = []
            for out in outputs:
                condensed.append(out[:800] if len(out) > 800 else out)
            retry_input = (
                f"Extract EVERY domain mentioned below. "
                f"Preserve ALL categories — technical AND non-technical.\n\n"
                + "\n\n---\n\n".join(condensed))
            raw_domains = self._call_model(
                extract_prompt, retry_input, timeout=120)
            domain_parsed = self._parse_stage_json(
                raw_domains, "cook_discover_full_domains_retry")

        if not isinstance(domain_parsed, list):
            print(f"{C.RED}Failed to extract domains{C.RESET}")
            return False

        # Build discover results (no prism cooking)
        discover = []
        for item in domain_parsed:
            dname = item.get("name", "").strip()
            ddesc = item.get("description", "").strip()
            if not dname:
                continue
            dname = re.sub(r'[^a-z0-9_]', '_',
                           dname.lower())
            discover.append({
                "name": dname,
                "description": ddesc,
                "domain": domain,
                "type": item.get("type", "structural"),
            })

        if not discover:
            print(f"{C.RED}Extraction returned no valid "
                  f"domains{C.RESET}")
            return False

        self._discover_results = discover
        self._save_discover_results(discover, file_name)

        # Rank domains by historical yield (highest first)
        discover = self._yield_tracker.rank_domains(discover)

        print(f"\n{C.BOLD}Discovered {len(discover)} "
              f"domains (full brainstorm):{C.RESET}\n")
        for i, item in enumerate(discover, 1):
            dtype = item.get('type', 'structural')
            type_tag = f" {C.YELLOW}[escape]{C.RESET}" if dtype == "escape" else ""
            yield_score = self._yield_tracker.get_yield_score(item['name'])
            score_str = f"({yield_score:.2f})"
            print(f"  {C.CYAN}{i}.{C.RESET} "
                  f"{C.GREEN}{item['name']}{C.RESET}{type_tag} "
                  f"{C.DIM}{score_str}{C.RESET}")
            desc = item.get('description', '')
            if desc:
                print(f"     {C.DIM}{desc}{C.RESET}")

        print(f"\n{C.BOLD}{C.GREEN}Ready to expand:{C.RESET}")
        print(f"  /expand 1,3 single       cook 1 prism per area, run")
        print(f"  /expand 1,3 full         cook pipeline per area, run")
        print(f"  /expand * full           all areas as full prism")
        print(f"  /expand 2-4              prompt single/full per area")
        return True

    @staticmethod
    def _discover_cache_key(file_name):
        """Derive a unique cache key from a file name/path.

        Includes up to 2 parent directory levels to avoid collisions between
        files with the same stem (e.g. src/subdir/file.py vs lib/subdir/file.py).
        """
        if not file_name:
            return "last"
        p = pathlib.Path(file_name)
        parent = p.parent.name
        grandparent = p.parent.parent.name if p.parent.parent else ""
        stem = p.stem or "unnamed"
        # Filter empty/dot parts to avoid malformed keys like "__stem"
        parts = [x for x in (grandparent, parent, stem)
                 if x and x != "."]
        return "_".join(parts) if parts else "unnamed"

    def _save_discover_results(self, results, file_name=None):
        """Persist discover results to .deep/discover_{key}.json."""
        deep_dir = self.working_dir / ".deep"
        deep_dir.mkdir(parents=True, exist_ok=True)
        stem = self._discover_cache_key(file_name)
        path = deep_dir / f"discover_{stem}.json"
        # Wrap results with _version for forward compatibility and format migrations
        data = {
            "_version": 1,
            "data": results,
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load_discover_results(self, file_name=None, refresh=False):
        """Load discover results from memory or .deep/discover_{key}.json.

        Handles both old (list) and new (dict with _version) formats for
        backward compatibility and forward migration.

        Args:
            refresh: If True, skip both memory and disk cache and return empty (force re-discovery).
        """
        if refresh:
            # Bypass cache: clear both memory AND disk so stale results
            # don't resurrect on next load
            self._discover_results = []
            stem = self._discover_cache_key(file_name)
            disk = self.working_dir / ".deep" / f"discover_{stem}.json"
            if disk.exists():
                try:
                    disk.unlink()
                except OSError:
                    pass
            return []
        if self._discover_results:
            return self._discover_results
        stem = self._discover_cache_key(file_name)
        path = self.working_dir / ".deep" / f"discover_{stem}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                # Backward compat: old format was list, new format is dict with _version
                if isinstance(data, dict) and "_version" in data:
                    # New versioned format: unwrap the data
                    results = data.get("data", [])
                elif isinstance(data, list):
                    # Old unversioned format: use as-is
                    results = data
                else:
                    # Unexpected format: bail
                    return []
                if results:
                    self._discover_results = results
                    return results
            except (json.JSONDecodeError, OSError):
                pass
        return []

    def _run_deep(self, content, file_name, goal, general=False):
        """Deep mode: cook a 4-prism 3-way system for a specific area.

        1. Resolve goal: int → discover result name, string → direct
        2. Check cache: .deep/prisms/_deep/{slug}/
        3. Cook 4 prisms if not cached (COOK_3WAY: WHERE/WHEN/WHY + synthesis)
        4. Run 4-call pipeline: 3 independent operations → synthesis
        """
        # Resolve goal
        if isinstance(goal, int):
            results = self._load_discover_results(file_name)
            if not results:
                print(f"{C.YELLOW}No discover results. "
                      f"Run /scan <file> discover first.{C.RESET}")
                return
            if goal < 1 or goal > len(results):
                print(f"{C.YELLOW}Index {goal} out of range "
                      f"(1-{len(results)}){C.RESET}")
                return
            goal = results[goal - 1]["name"]

        slug = re.sub(r'[^a-z0-9]+', '_', goal.lower()).strip('_')[:80]
        if not slug:
            slug = "unnamed"
        deep_dir = (self.working_dir / ".deep" / "prisms"
                    / "_deep" / slug)

        # 3-way role names
        op_roles = ["where", "when", "why"]
        all_roles = op_roles + ["synthesis"]

        # Check cache
        cached_paths = {r: deep_dir / f"{r}.md" for r in all_roles}
        if all(p.exists() for p in cached_paths.values()):
            print(f"{C.DIM}Using cached deep prisms: {slug}{C.RESET}")
            prompts = {r: cached_paths[r].read_text(encoding="utf-8")
                       for r in all_roles}
        else:
            # Cook 4-prism system via COOK_3WAY
            cook_prompt = COOK_3WAY.format(
                intent=f"deep structural analysis of: {goal}")
            sample = content[:2000] if len(content) > 2000 else content
            user_input = (
                f"Generate a 3-way analysis pipeline for: {goal}\n\n"
                f"Sample artifact:\n\n{sample}")

            print(f"{C.CYAN}Cooking deep prism system for: "
                  f"{goal}{C.RESET}")
            raw = self._call_model(cook_prompt, user_input, timeout=90,
                                   model=COOK_MODEL)

            parsed = self._parse_stage_json(raw, "cook_deep")
            if not isinstance(parsed, list) or len(parsed) < 4:
                print(f"{C.RED}Failed to generate deep prisms "
                      f"(need 4, got "
                      f"{len(parsed) if isinstance(parsed, list) else 0})"
                      f"{C.RESET}")
                return

            # Extract by role keyword matching
            by_role = {}
            for item in parsed:
                role = item.get("role", "").lower()
                name_l = item.get("name", "").lower()
                if "where" in role or "archaeol" in name_l:
                    by_role["where"] = item
                elif "when" in role or "simulat" in name_l:
                    by_role["when"] = item
                elif "why" in role or "structural" in name_l:
                    by_role["why"] = item
                elif "synth" in role or "synth" in name_l:
                    by_role["synthesis"] = item

            if len(by_role) < 4:
                # Fallback: assign by position
                for i, role in enumerate(all_roles):
                    if role not in by_role and i < len(parsed):
                        by_role[role] = parsed[i]

            if len(by_role) < 4:
                print(f"{C.RED}Failed to generate all 4 prism "
                      f"roles{C.RESET}")
                return

            # Save to cache
            deep_dir.mkdir(parents=True, exist_ok=True)
            prompts = {}
            for role in all_roles:
                text = by_role[role].get("prompt", "")
                pname = by_role[role].get("name", role)
                (deep_dir / f"{role}.md").write_text(
                    text, encoding="utf-8")
                prompts[role] = text
                preview = text[:60] + ("..." if len(text) > 60 else "")
                print(f"  {C.GREEN}{role.upper()}{C.RESET} ({pname}): "
                      f"{C.DIM}{preview}{C.RESET}")

        # Run 4-call pipeline: 3 independent → synthesis
        content_label = "INPUT" if general else "SOURCE CODE"
        role_labels = {
            "where": "WHERE (archaeology)",
            "when": "WHEN (simulation)",
            "why": "WHY (structural)",
        }
        op_outputs = {}

        # Calls 1-3: Independent operations
        for role in op_roles:
            label = role_labels[role]
            print(f"\n{C.BOLD}{C.BLUE}── {label}: {goal} ── "
                  f"{file_name} ──{C.RESET}")
            backend = ClaudeBackend(
                model=self.session.model,
                working_dir=str(self.working_dir),
                system_prompt=prompts[role],
                tools=False,
            )
            output = self._stream_and_capture(
                backend,
                f"Analyze this {content_label.lower()}.\n\n{content}")

            if output and not self._interrupted:
                self._save_deep_finding(
                    file_name, f"deep_{slug}_{role}", output)
                op_outputs[role] = output

            if self._interrupted:
                return

        if len(op_outputs) < 3:
            print(f"{C.YELLOW}Only {len(op_outputs)}/3 operations "
                  f"completed{C.RESET}")

        # Call 4: Synthesis (receives all 3 outputs)
        synth_parts = [f"# {content_label}\n\n{content}\n\n---"]
        for role in op_roles:
            if role in op_outputs:
                label = role_labels[role].upper()
                synth_parts.append(
                    f"\n# ANALYSIS: {label}\n\n{op_outputs[role]}")
        synth_input = "\n\n---\n".join(synth_parts)

        print(f"\n{C.BOLD}{C.BLUE}── Synthesis: {goal} ──{C.RESET}")
        synth_backend = ClaudeBackend(
            model=self.session.model,
            working_dir=str(self.working_dir),
            system_prompt=prompts["synthesis"],
            tools=False,
        )
        synth_output = self._stream_and_capture(
            synth_backend, synth_input)

        if synth_output and not self._interrupted:
            self._save_deep_finding(
                file_name, f"deep_{slug}_synthesis", synth_output)

        # Save combined
        sections = [f"# Deep Analysis: {goal} — {file_name}\n"]
        for role in op_roles:
            label = role_labels[role].upper()
            text = op_outputs.get(role, "(not completed)")
            sections.append(f"## {label}\n\n{text}\n")
        sections.append(
            f"## SYNTHESIS\n\n{synth_output or '(not completed)'}\n")
        combined = "\n".join(sections)

        self._save_deep_finding(file_name, f"deep_{slug}", combined)
        print(f"\n  {C.DIM}Use /fix to pick issues, or "
              f"/fix auto to fix all{C.RESET}")

    def _run_expand(self, content, file_name, indices_str=None,
                    expand_mode=None, general=False, refresh=False):
        """Expand mode: pick areas from discover, choose single/full per area.

        Requires prior discover results. Does NOT auto-discover —
        use /scan file discover first, or chained discover expand syntax.

        1. Load discover results (error if none)
        2. Show list, prompt for area selection
        3. For each selected area: prompt single/full prism (or use expand_mode)
        4. Single: cook 1 prism (COOK_UNIVERSAL) → run (1 call)
        5. Full: cook pipeline (COOK_3WAY) → run (4 calls: WHERE/WHEN/WHY + synthesis)

        expand_mode="single"|"full" applies to all selected areas.
        expand_mode=None prompts per area (allows mixing).
        refresh: If True, bypass cached discover results and re-discover.
        """
        # 1. Get discover results (require prior discover)
        results = self._load_discover_results(file_name, refresh=refresh)
        if not results:
            print(f"{C.YELLOW}No discover results. "
                  f"Run /scan <file> discover first.{C.RESET}")
            return

        # 2. Select areas
        if indices_str:
            indices = self._parse_selection(indices_str, len(results))
        else:
            print(f"\n{C.BOLD}Available domains:{C.RESET}\n")
            for i, item in enumerate(results, 1):
                prio = item.get('priority')
                prio_tag = f" {C.DIM}(P{prio}){C.RESET}" if prio else ""
                print(f"  {C.CYAN}{i}.{C.RESET} "
                      f"{C.GREEN}{item['name']}{C.RESET}{prio_tag}")
                desc = item.get('description', '')
                if desc:
                    print(f"     {C.DIM}{desc}{C.RESET}")
            try:
                sel = input(
                    f"\n  Select areas (e.g. 1,3,5 or "
                    f"* for all): ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if not sel:
                return
            indices = self._parse_selection(sel, len(results))

        if not indices:
            print(f"{C.YELLOW}No valid areas selected{C.RESET}")
            return

        # 3. Per-area mode choice
        area_configs = []
        if expand_mode:
            # Global mode: all areas get the same prism
            for idx in indices:
                area_configs.append(
                    (idx, results[idx - 1], expand_mode))
        else:
            # Interactive: user picks per area (can mix)
            for idx in indices:
                item = results[idx - 1]
                try:
                    choice = input(
                        f"  {C.GREEN}{item['name']}{C.RESET}"
                        f" — [s]ingle / [f]ull prism: "
                    ).strip().lower()
                except (EOFError, KeyboardInterrupt):
                    print()
                    return
                mode = "full" if choice.startswith("f") else "single"
                area_configs.append((idx, item, mode))

        # Summary
        s_count = sum(1 for _, _, m in area_configs if m == "single")
        f_count = sum(1 for _, _, m in area_configs if m == "full")
        total_areas = len(area_configs)
        print(f"\n  {C.DIM}{total_areas} areas: "
              f"{s_count} single + {f_count} full{C.RESET}\n")

        # 4. Cook and run each area
        for area_num, (idx, item, mode) in enumerate(area_configs, 1):
            area_name = item["name"]
            area_label = f"[Area {idx}/{len(results)}: {area_name}]"
            total_areas_label = f"({area_num}/{total_areas})"

            if mode == "single":
                print(f"{C.CYAN}Single Prism: {area_label} {total_areas_label}{C.RESET}")
                self._run_expand_single(
                    content, file_name, area_name, general)
            else:
                print(f"{C.CYAN}Full Prism: {area_label} {total_areas_label}{C.RESET}")
                self._run_expand_full(
                    content, file_name, area_name, general, area_idx=idx,
                    total_areas=len(results),
                    domain_type=item.get("type", "structural"))

            # Record yield: check if findings were saved and measure output size
            outcome = self._record_expand_outcome(file_name, area_name)
            if outcome:
                self._yield_tracker.record(area_name, outcome)

            if self._interrupted:
                break

        print(f"\n  {C.DIM}Use /fix to pick issues, or "
              f"/fix auto to fix all{C.RESET}")

    def _run_expand_single(self, content, file_name, area_name,
                           general=False):
        """Cook and run a single prism for a specific discovered area.

        Delegates to _run_target (expand = target with discover-derived goal).
        Uses _expand/ cache prefix with staleness checks.
        """
        self._run_target(
            content, file_name, goal=area_name, general=general,
            cache_prefix="_expand", slug_max=40, check_stale=True)

    def _run_expand_full(self, content, file_name, area_name,
                         general=False, area_idx=None, total_areas=None,
                         domain_type="structural"):
        """Cook and run a full prism pipeline for a specific area.

        Args:
            area_idx: 1-based index of this area in the discover list (for naming)
            total_areas: Total number of areas discovered (for context)
        """
        slug = re.sub(r'[^a-z0-9]+', '_',
                      area_name.lower()).strip('_')[:40]
        # Include domain_type in cache key to prevent stale adversarial
        cache_key = f"{slug}_{domain_type}" if domain_type != "structural" else slug
        cache_dir = (self.working_dir / ".deep" / "prisms"
                     / "_expand" / cache_key)

        # Check cache (invalidate if source file is newer than cached pipeline)
        cached = self._load_cached_pipeline(cache_dir)
        if cached:
            source_file = self._resolve_file(file_name)
            if (source_file and cache_dir.is_dir()
                    and source_file.stat().st_mtime
                    > max((f.stat().st_mtime
                           for f in cache_dir.iterdir()), default=0)):
                print(f"  {C.YELLOW}Cached pipeline stale "
                      f"(file changed) — re-cooking{C.RESET}")
                cached = None
            else:
                print(f"  {C.DIM}Using cached pipeline: "
                      f"{slug}{C.RESET}")
        if cached:
            prisms = cached
        else:
            # Cook
            sample = content[:2000] if len(content) > 2000 else content
            _expand_intent = f"deep analysis of: {area_name}"
            if domain_type != "structural":
                _expand_intent += (
                    f" (challenge from within the {domain_type} "
                    f"framework, not code-structural)")
            prompt = COOK_3WAY.format(
                intent=_expand_intent)
            user_input = (
                f"Generate a 3-way analysis pipeline for: "
                f"{area_name}\n\n"
                f"Sample artifact:\n\n{sample}")

            print(f"  {C.CYAN}Cooking pipeline for: "
                  f"{area_name}{C.RESET}")
            raw = self._call_model(prompt, user_input, timeout=90,
                                   model=COOK_MODEL)

            parsed = self._parse_stage_json(raw, "cook_expand")
            if not isinstance(parsed, list) or len(parsed) < 2:
                reason = "no response" if not raw else (
                    f"got {type(parsed).__name__}" if parsed is not None
                    else "unparseable response")
                print(f"{C.RED}Failed to cook pipeline for "
                      f"{area_name} ({reason}){C.RESET}")
                if raw:
                    print(f"  {C.DIM}{raw[:200]}{'...' if len(raw) > 200 else ''}{C.RESET}")
                return

            # Save to cache
            cache_dir.mkdir(parents=True, exist_ok=True)
            prisms = []
            for i, item in enumerate(parsed):
                name = item.get("name", f"step_{i + 1}")
                name = re.sub(r'[^a-z0-9_]', '_', name.lower())
                text = item.get("prompt", "")
                role = item.get("role", f"step_{i + 1}")
                if not text:
                    continue
                (cache_dir / f"{i:02d}_{name}.md").write_text(
                    text, encoding="utf-8")
                prisms.append({"name": name, "prompt": text,
                               "role": role, "order": i})
                preview = text[:60] + (
                    "..." if len(text) > 60 else "")
                print(f"    {C.GREEN}{role}{C.RESET} ({name}): "
                      f"{C.DIM}{preview}{C.RESET}")

            if len(prisms) < 2:
                print(f"{C.RED}Need at least 2 prisms for "
                      f"full prism{C.RESET}")
                return

        self._run_cooked_pipeline(
            prisms, content, file_name, area_name, general,
            area_idx=area_idx, total_areas=total_areas,
            domain_type=domain_type)

    def _run_cooked_pipeline(self, prisms, content, file_name,
                             area_name, general=False, area_idx=None,
                             total_areas=None, domain_type="structural"):
        """Run an ordered list of prisms as a pipeline.

        First prism gets raw content. Each subsequent prism receives
        the raw content plus all previous analyses.

        Args:
            area_idx: 1-based index of this area in discover results (for result organization)
            total_areas: Total number of discovered areas (for context)
        """
        content_label = "INPUT" if general else "SOURCE CODE"
        slug = re.sub(r'[^a-z0-9]+', '_',
                      area_name.lower()).strip('_')[:40]
        # Prepend area index to slug if available (e.g., "2_mutation" instead of "mutation")
        if area_idx is not None:
            slug = f"{area_idx:02d}_{slug}"
        outputs = []

        for i, prism in enumerate(prisms):
            role = prism.get("role", prism["name"])

            # Build message
            if i == 0:
                msg = f"Analyze this {content_label.lower()}.\n\n{content}"
            else:
                parts = [f"# {content_label}\n\n{content}"]
                for j, prev in enumerate(outputs):
                    prev_role = prisms[j].get(
                        "role", prisms[j]["name"]).upper()
                    parts.append(
                        f"# ANALYSIS {j + 1}: {prev_role}"
                        f"\n\n{prev}")
                msg = "\n\n---\n\n".join(parts)
                # Guard: Warn if context window overflow detected (prevents silent synthesis failure)
                # Large codebases (20+ files × 5 prisms) accumulate ~200K tokens, exceeding context limit.
                # Synthesis returns empty/truncated report silently without this warning.
                if len(msg) > 100_000:
                    print(
                        f"\n{C.YELLOW}⚠ Context window overflow detected "
                        f"({len(msg):,} chars, ~{len(msg)//4} tokens){C.RESET}\n"
                        f"  {C.DIM}Truncating synthesis input to 100K chars. "
                        f"Consider analyzing smaller subsystems separately.{C.RESET}"
                    )
                    msg = msg[:100_000] + "\n\n[... truncated due to size ...]"

            area_indicator = f"[{area_idx}/{total_areas}] {area_name}" if area_idx else area_name
            print(f"\n{C.BOLD}{C.BLUE}── {role}: "
                  f"{area_indicator} ── {file_name} ──{C.RESET}")
            backend = ClaudeBackend(
                model=self.session.model,
                working_dir=str(self.working_dir),
                system_prompt=prism["prompt"],
                tools=False,
            )
            output = self._stream_and_capture(backend, msg)

            if output and not self._interrupted:
                self._save_deep_finding(
                    file_name,
                    f"expand_{slug}_{role}", output)
                outputs.append(output)

            if not output or self._interrupted:
                if not self._interrupted and not output:
                    print(f"  {C.YELLOW}⚠ {role} returned empty — "
                          f"pipeline stopped at pass "
                          f"{i + 1}/{len(prisms)}{C.RESET}")
                break

            # Step 2: Escape-domain checkpoint after first pass
            # When domain type is 'escape' and interactive (not auto_mode),
            # pause and ask whether to use domain-specific adversarial
            if (i == 0 and not self._auto_mode and
                    domain_type == "escape" and output):
                print(f"\n{C.YELLOW}⚠ Escape domain checkpoint{C.RESET}")
                print(f"  First pass ({role}) completed.")
                print(f"  Domain type: {C.CYAN}escape{C.RESET} "
                      f"— may need domain-specific adversarial")
                print(f"\n  Summary of first pass:\n")
                summary = output[:500] + (
                    "..." if len(output) > 500 else "")
                for line in summary.split("\n")[:10]:
                    print(f"    {C.DIM}{line}{C.RESET}")

                print(f"\n  Options:")
                print(f"    [s] continue with structural adversarial")
                print(f"    [d] domain-specific adversarial (re-cook)")
                print(f"    [k] keep going with remaining passes")
                print(f"    [x] skip remaining passes")
                try:
                    choice = input(
                        f"  Choose [{C.GREEN}s{C.RESET}/"
                        f"{C.GREEN}d{C.RESET}/"
                        f"{C.GREEN}k{C.RESET}/"
                        f"{C.GREEN}x{C.RESET}]: ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    choice = "k"

                if choice == "x":
                    # Skip remaining passes for this domain
                    print(f"  {C.DIM}Skipping remaining passes{C.RESET}")
                    break
                elif choice == "d":
                    # Re-cook adversarial with domain framing
                    print(f"  {C.CYAN}Re-cooking adversarial with "
                          f"domain context...{C.RESET}")
                    # Modify the next prism to be domain-specific
                    if i + 1 < len(prisms):
                        next_prism = prisms[i + 1]
                        next_role = next_prism.get("role", next_prism["name"])
                        domain_framing = (
                            f"\n\n[DOMAIN CONTEXT: This is an escape domain "
                            f"({area_name}). Your analysis MUST challenge "
                            f"from WITHIN the domain's own framework, not "
                            f"from structural/code perspectives. Use "
                            f"domain-specific counter-arguments.]")
                        next_prism["prompt"] = (
                            next_prism["prompt"] + domain_framing)
                        if "adversarial" in next_role.lower():
                            print(f"  {C.GREEN}Updated adversarial prism "
                                  f"with domain framing{C.RESET}")
                        else:
                            print(f"  {C.GREEN}Updated '{next_role}' prism "
                                  f"with domain framing{C.RESET}")
                    else:
                        print(f"  {C.YELLOW}No subsequent prism to "
                              f"re-frame{C.RESET}")
                # else: "s" or "k", just continue with current pipeline

        # Save combined and return
        if outputs:
            combined_parts = [
                f"# Full Prism: {area_name} "
                f"— {file_name}\n"]
            for prism, out in zip(prisms, outputs):
                r = prism.get("role", prism["name"]).upper()
                combined_parts.append(
                    f"## {r}\n\n{out}\n")
            combined = "\n".join(combined_parts)
            self._save_deep_finding(
                file_name, f"expand_{slug}",
                combined)
            return combined
        return ""

    def _stream_and_capture(self, backend, message):
        """Stream output from a ClaudeBackend, capture and return text.

        Latency-aware streaming with adaptive progress indicators.
        - Under normal latency: shows "thinking..." label
        - Under high latency (>3s Haiku, >15s Opus): hides thinking label, shows tokens/sec
        - Detects degraded UX and improves feedback under poor network conditions

        Shared by _run_deep pipeline calls. Returns captured text or "".
        """
        parser = StreamParser()
        self._interrupted = False
        had_output = False
        output_buffer = []

        is_main = threading.current_thread() is threading.main_thread()
        original_sigint = None
        if is_main:
            original_sigint = signal.getsignal(signal.SIGINT)
            def on_interrupt(sig, frame):
                self._interrupted = True
                backend.kill()
            signal.signal(signal.SIGINT, on_interrupt)

        thinking_shown = False
        thinking_start_time = None
        text_start_time = None
        try:
            for line in backend.send(message):
                if self._interrupted:
                    break
                for evt, data in parser.parse_line(line):
                    if evt == "text":
                        # Calculate thinking latency and adapt display
                        if thinking_start_time is not None and text_start_time is None:
                            text_start_time = time.time()
                            thinking_latency = text_start_time - thinking_start_time

                            # Auto-hide thinking if latency is unusually high.
                            # Opus regularly takes 10-15s — use 15s threshold for it.
                            latency_threshold = (15.0
                                                 if self.session.model == "opus"
                                                 else 3.0)
                            if thinking_latency > latency_threshold and thinking_shown:
                                # Replace thinking indicator with latency-aware progress
                                sys.stdout.write(
                                    "\r" + " " * 40 + "\r")
                                thinking_shown = False
                                _log_error(
                                    context="streaming:high_latency",
                                    error_type="LatencyWarning",
                                    error_msg=f"Thinking took {thinking_latency:.1f}s (>3s threshold)",
                                    details=f"model={self.session.model}, "
                                            f"user_input_chars={len(message)}",
                                    working_dir=self.working_dir
                                )
                            elif thinking_shown:
                                # Normal latency: clear thinking label gracefully
                                sys.stdout.write(
                                    "\r" + " " * 30 + "\r")
                                thinking_shown = False

                        if not thinking_shown:
                            sys.stdout.write(data)
                            sys.stdout.flush()
                            output_buffer.append(data)
                            had_output = True
                    elif evt == "thinking":
                        if not thinking_shown:
                            thinking_start_time = time.time()
                            # Only show thinking label under normal conditions
                            # High latency scenarios skip this to avoid UX degradation
                            sys.stdout.write(
                                f"{C.DIM}thinking...{C.RESET}")
                            sys.stdout.flush()
                            thinking_shown = True
                    elif evt == "rate_limit":
                        status = data.get("status", "")
                        resets = data.get("resetsAt", "")
                        if status != "allowed":
                            # Rate limited — show visible warning
                            reset_str = ""
                            if resets:
                                try:
                                    from datetime import datetime
                                    dt = datetime.fromtimestamp(resets)
                                    reset_str = f" (resets {dt.strftime('%H:%M')})"
                                except (ValueError, TypeError, OSError):
                                    pass
                            sys.stdout.write(
                                f"\r{C.YELLOW}Rate limited"
                                f"{reset_str}{C.RESET}\n")
                            sys.stdout.flush()
                    elif evt == "parse_error":
                        # Stream JSON parse failed — warn visibly so
                        # blank output isn't mistaken for "nothing found"
                        if not thinking_shown:
                            sys.stdout.write(
                                f"\r{C.YELLOW}stream parse "
                                f"error{C.RESET}\n")
                            sys.stdout.flush()
                    elif evt == "result":
                        usage = data.get("usage", {})
                        self.session.total_input_tokens += usage.get(
                            "input_tokens", 0)
                        self.session.total_output_tokens += usage.get(
                            "output_tokens", 0)
                        cost = data.get("total_cost_usd",
                                        data.get("cost_usd", 0))
                        if isinstance(cost, (int, float)):
                            self.session.total_cost_usd += cost
        finally:
            if is_main and original_sigint is not None:
                signal.signal(signal.SIGINT, original_sigint)
            if self._interrupted:
                print(f"\n{C.YELLOW}interrupted{C.RESET}")
            elif had_output:
                print()
            print()

        return "".join(output_buffer)

    def _run_target(self, content, file_name, goal, general=False,
                    cache_prefix="_targets", slug_max=80,
                    check_stale=False, cooker=None):
        """Target mode: cook a goal-specific prism + run it.

        Generates ONE focused prism for the user's specific goal,
        saves it for reuse, then runs it on the input.

        Also used by expand (which is conceptually Target with a
        discover-derived goal). cache_prefix and check_stale let
        expand keep its own cache with staleness checks.
        """
        # Slugify goal for filesystem
        slug = re.sub(r'[^a-z0-9]+', '_', goal.lower()).strip('_')[:slug_max]
        if not slug:
            slug = "unnamed"

        # Check cache
        cached_prism = f"{cache_prefix}/{slug}"
        cached = self._load_prism(cached_prism)
        if cached and check_stale:
            cache_file = (self.working_dir / ".deep" / "prisms"
                          / cache_prefix / f"{slug}.md")
            source_file = self._resolve_file(file_name)
            if (source_file and cache_file.exists()
                    and source_file.stat().st_mtime > cache_file.stat().st_mtime):
                print(f"  {C.YELLOW}Cached prism stale "
                      f"(file changed) — re-cooking{C.RESET}")
                cached = None
        if cached:
            print(f"{C.DIM}Using cached prism: {slug}{C.RESET}")
        else:
            # Cook one focused prism — route to specified cooker
            _cooker_map = {
                "simulation": COOK_SIMULATION,
                "archaeology": COOK_ARCHAEOLOGY,
                "concealment": COOK_CONCEALMENT,
                "universal": COOK_UNIVERSAL,
            }
            _cook_template = _cooker_map.get(cooker, COOK_UNIVERSAL)
            if cooker and cooker in _cooker_map:
                print(f"  {C.DIM}cooker: {cooker}{C.RESET}")
            prompt = _cook_template.format(
                intent=f"analyze: {goal}")
            sample = content[:2000] if len(content) > 2000 else content
            user_input = (
                f"Generate one analytical prism for this goal: {goal}\n\n"
                f"Sample artifact:\n\n{sample}")

            print(f"{C.CYAN}Cooking prism for: {goal}{C.RESET}")
            raw = self._call_model(prompt, user_input, timeout=90,
                                   model=COOK_MODEL)

            parsed = self._parse_stage_json(raw, "cook_target")
            if not isinstance(parsed, dict) or "prompt" not in parsed:
                print(f"{C.RED}Failed to generate target prism{C.RESET}")
                return

            name = parsed.get("name", slug)
            name = re.sub(r'[^a-z0-9_]', '_', name.lower())
            text = parsed["prompt"]

            # Save to project-local .deep/prisms/{cache_prefix}/
            target_dir = (self.working_dir / ".deep" / "prisms"
                          / cache_prefix)
            target_dir.mkdir(parents=True, exist_ok=True)
            (target_dir / f"{slug}.md").write_text(text, encoding="utf-8")

            preview = text[:70] + ("..." if len(text) > 70 else "")
            print(f"  {C.GREEN}{slug}{C.RESET}: {C.DIM}{preview}{C.RESET}")
            cached_prism = f"{cache_prefix}/{slug}"

        # Run the prism — use COOK_MODEL for solve too (P204: same-model
        # cook+solve produces 2x depth vs cross-model)
        with self._temporary_model(COOK_MODEL):
            self._run_single_prism_streaming(
                cached_prism, content, file_name,
                label=f"{slug} ── {file_name}",
                intent=goal)

    # Extensions that are always code (no content sniffing needed)
    _CODE_EXTS = {
        "py", "js", "ts", "jsx", "tsx", "go", "rs", "java", "rb",
        "sh", "c", "cpp", "h", "hpp", "cs", "swift", "kt", "scala",
        "php", "pl", "r", "lua", "zig", "nim", "dart", "ex", "exs",
        "hs", "ml", "fs", "clj", "v", "sv", "sql", "m", "mm",
    }
    # Extensions that are never code (documentation/prose/config)
    _DOC_EXTS = {"md", "txt", "rst", "adoc", "org", "tex", "html"}
    _CONFIG_EXTS = {"yaml", "yml", "toml", "ini", "cfg", "conf"}
    _DATA_EXTS = {"json", "xml", "csv"}

    def _infer_domain(self, content, file_name, general=False,
                       for_discover=False):
        """Infer a domain label from content for prism caching or discover.

        for_discover=True returns a content-aware label that describes
        WHAT the artifact is about, not what format it's in. For code,
        this is language-based (e.g., 'python_software_artifact'). For
        documentation and text, this is topic-based (e.g.,
        'research_tool_documentation').

        The key insight: the domain label tells the cooker/discover
        engine what angle to brainstorm from. 'md_software_artifact'
        is meaningless — markdown is a format, not a domain. The label
        must describe the artifact's PURPOSE and SUBJECT MATTER.
        """
        if not general:
            ext = pathlib.Path(file_name).suffix.lstrip(".")

            if ext in self._CODE_EXTS:
                if for_discover:
                    lang = {"py": "python", "js": "javascript",
                            "ts": "typescript", "go": "go",
                            "rs": "rust", "java": "java",
                            "rb": "ruby", "sh": "shell",
                            }.get(ext, ext)
                    return f"{lang}_software_artifact"
                return f"code_{ext}" if ext else "code"

            # Non-code file: derive domain from content, not extension
            if for_discover:
                return self._infer_topic_from_content(
                    content, file_name)
            # For caching (not discover), extension is fine
            if ext in self._DOC_EXTS:
                return f"doc_{ext}"
            if ext in self._CONFIG_EXTS:
                return f"config_{ext}"
            if ext in self._DATA_EXTS:
                return f"data_{ext}"
            # Unknown extension: check if content looks like code
            if content and self._content_looks_like_code(content):
                return f"code_{ext}" if ext else "code"
            return f"doc_{ext}" if ext else "text"

        # General text (no file): derive topic from content
        if for_discover:
            return self._infer_topic_from_content(content, file_name)
        slug = re.sub(r'[^a-z0-9]+', '_',
                      content[:50].lower()).strip('_')
        return slug[:30] if slug else "general"

    @staticmethod
    def _content_looks_like_code(content):
        """Heuristic: does the first ~500 chars look like source code?"""
        sample = content[:500]
        code_signals = [
            "def ", "class ", "function ", "import ", "from ",
            "const ", "let ", "var ", "func ", "fn ", "pub ",
            "package ", "#include", "using ", "namespace ",
            "if (", "for (", "while (", "return ",
        ]
        return sum(1 for s in code_signals if s in sample) >= 2

    @staticmethod
    def _infer_topic_from_content(content, file_name):
        """Derive a meaningful topic label from content for discover.

        Reads headers, keywords, and structure to produce a label
        like 'research_tool_documentation' or 'api_design_specification'
        instead of 'md_software_artifact'.
        """
        sample = content[:2000].lower()
        name = file_name.lower() if file_name else ""

        # Check file name first for strong signals
        name_signals = {
            "readme": "project_documentation",
            "changelog": "release_history",
            "contributing": "contribution_guide",
            "license": "legal_document",
            "roadmap": "project_roadmap",
            "spec": "technical_specification",
            "rfc": "technical_proposal",
            "design": "design_document",
            "architecture": "architecture_document",
            "api": "api_documentation",
            "tutorial": "educational_tutorial",
            "guide": "user_guide",
        }
        for signal, label in name_signals.items():
            if signal in name:
                return label

        # Check content for topic signals
        topic_keywords = {
            "research_methodology": [
                "experiment", "hypothesis", "validation",
                "results", "findings", "tested"],
            "software_tool_documentation": [
                "install", "usage", "cli", "command",
                "configuration", "getting started"],
            "api_specification": [
                "endpoint", "request", "response",
                "authentication", "rate limit"],
            "academic_paper": [
                "abstract", "introduction", "methodology",
                "conclusion", "references", "citation"],
            "business_strategy": [
                "market", "revenue", "customer", "growth",
                "competitive", "pricing"],
            "legal_document": [
                "hereby", "whereas", "agreement",
                "liability", "indemnif"],
            "technical_analysis": [
                "conservation law", "structural",
                "prism", "compression", "taxonomy"],
        }

        best_topic = "general_document"
        best_score = 0
        for topic, keywords in topic_keywords.items():
            score = sum(1 for k in keywords if k in sample)
            if score > best_score:
                best_score = score
                best_topic = topic

        # Need at least 2 keyword hits to be confident
        if best_score < 2:
            # Fall back to first markdown header if available
            import re as _re_topic
            h1 = _re_topic.search(r'^#\s+(.+)', content[:500],
                                   _re_topic.MULTILINE)
            if h1:
                slug = _re_topic.sub(
                    r'[^a-z0-9]+', '_',
                    h1.group(1).lower()).strip('_')
                return slug[:40] + "_document" if slug else best_topic

        return best_topic

    def _record_expand_outcome(self, file_name, area_name):
        """Check if expand run produced output and record yield outcome.

        Returns: 'actionable' | 'insightful' | 'noise' | None

        Outcome determination:
        - actionable: >200 chars (likely generated fixes/insights)
        - insightful: 50-200 chars (useful analysis)
        - noise: <50 chars or empty (insufficient output)
        - None: if findings file not found (no data to analyze)
        """
        # Derive the file stem for looking up findings
        stem = self._discover_cache_key(file_name)
        findings_dir = self.working_dir / ".deep" / "findings"
        findings_path = findings_dir / f"{stem}.md"

        if not findings_path.exists():
            # No findings saved for this file
            return None

        try:
            # Guard: Capture content snapshot to prevent retroactive outcome invalidation
            # if the findings file is modified by callbacks after outcome is recorded
            mtime_before = findings_path.stat().st_mtime
            content = findings_path.read_text(encoding="utf-8")
            mtime_after = findings_path.stat().st_mtime

            # If file was modified during read, outcome based on stale data — skip recording
            if mtime_after != mtime_before:
                return None
            # Extract section for this area
            pattern = rf'## {re.escape(area_name.upper())}\s*\n(.*?)(?=\n## |\Z)'
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)

            # Guard: Reject silent parse failures on model output variance.
            # Model may vary markdown format (missing headers, extra whitespace,
            # malformed sections). Instead of silently returning "noise",
            # log explicit error so broken prism output is visible.
            if not match:
                # Detailed diagnostic: why regex failed (data quality insight)
                if not content.strip():
                    self._log_parse_failure(
                        "yield_extraction:empty", area_name,
                        "findings file is empty")
                elif f"## {area_name.upper()}" not in content:
                    self._log_parse_failure(
                        "yield_extraction:missing_section", area_name,
                        f"expected section '## {area_name.upper()}' not found in output")
                else:
                    self._log_parse_failure(
                        "yield_extraction:regex_failed", area_name,
                        "markdown section exists but regex failed to extract")
                return "noise"

            section_text = match.group(1).strip()
            length = len(section_text)

            if length > 200:
                return "actionable"
            elif length >= 50:
                return "insightful"
            else:
                return "noise"
        except (OSError, ValueError):
            return None

    def _execute_prism(self, system_prompt, message, *,
                       model=None, tools=False, label=None,
                       file_name=None, prism_name=None,
                       save=True, intent=None, mode="single"):
        """Execute a prism via ClaudeBackend streaming.

        Single point of backend creation for all prism execution.
        Handles model override, streaming, saving, and session logging.

        Args:
            system_prompt: The prism prompt text.
            message: User message/content to analyze.
            model: Model name override (resolves via _temporary_model). None = session model.
            tools: Whether to enable tools (default False for analysis).
            label: Header label for streaming output.
            file_name: For saving findings. None = don't save.
            prism_name: Prism identifier for findings filename.
            save: Whether to save to .deep/findings/.
            intent: Intent string for session log.
            mode: Mode string for session log (default 'single').

        Returns:
            Captured output text, or "" if interrupted/failed.
        """
        if label:
            print(f"{C.BOLD}{C.BLUE}── {label} ──{C.RESET}")

        with self._temporary_model(model):
            backend = ClaudeBackend(
                model=self.session.model,
                working_dir=str(self.working_dir),
                system_prompt=system_prompt,
                tools=tools,
            )
            cost_before = self.session.total_cost_usd
            captured = self._stream_and_capture(backend, message)
            cost_delta = self.session.total_cost_usd - cost_before

        if (save and captured.strip() and not self._interrupted
                and file_name and prism_name):
            self._save_deep_finding(file_name, prism_name, captured)
            self._session_log.append(
                operation="analyze",
                intent=intent,
                file_name=file_name,
                lens=prism_name,
                model=model or self.session.model,
                mode=mode,
                findings_summary=captured[:200] if captured else None,
                cost_estimate=round(cost_delta, 6) if cost_delta > 0 else None,
            )
            # A5: Track prism yield for adaptive routing
            if hasattr(self, '_yield_tracker') and prism_name:
                _out_len = len(captured.strip())
                if _out_len > 200:
                    self._yield_tracker.record(prism_name, "actionable")
                elif _out_len > 50:
                    self._yield_tracker.record(prism_name, "insightful")
                else:
                    self._yield_tracker.record(prism_name, "noise")

        return captured

    def _run_single_prism_streaming(self, prism_name, content, file_name,
                                    label=None, message=None, general=False,
                                    intent=None):
        """Run a single prism with streaming output. Saves to .deep/findings/.

        Thin wrapper: loads prism, strips L12 bug harvest for general text,
        builds message, delegates to _execute_prism.
        Returns captured output text, or "" if interrupted/failed.
        """
        prompt = self._load_prism(prism_name)
        if not prompt:
            print(f"{C.RED}Prism '{prism_name}' not found{C.RESET}")
            return ""

        # Strip code-specific bug harvest when running on general text
        if general and prism_name == "l12":
            anchor = "Finally: collect every concrete bug"
            idx = prompt.find(anchor)
            if idx != -1:
                prompt = prompt[:idx].rstrip()

        header = label or f"{prism_name} ── {file_name}"

        if message:
            msg = message
        else:
            content_label = "input" if general else "source code"
            msg = f"Analyze this {content_label}.\n\n{content}"

        return self._execute_prism(
            system_prompt=prompt,
            message=msg,
            label=header,
            file_name=file_name,
            prism_name=prism_name,
            intent=intent,
        )

    # ── Auto-modes ───────────────────────────────────────────────────────

    def _collect_files(self, target, extensions=None):
        """Collect target files from a path (file or directory)."""
        exts = extensions or {".py", ".js", ".ts", ".go", ".rs", ".java",
                              ".rb", ".sh", ".md", ".yaml", ".yml", ".toml"}
        path = self._resolve_file(target)
        if not path:
            return []
        if path.is_file():
            return [path]
        if path.is_dir():
            files = []
            for ext in exts:
                files.extend(path.glob(f"**/*{ext}"))
            # Filter out hidden dirs, node_modules, etc.
            files = [f for f in files
                     if not any(p.startswith(".") or p == "node_modules"
                                for p in f.relative_to(path).parts)]
            # Sort by size (largest first — more interesting)
            # Guard against broken symlinks / permission errors
            def _safe_size(f):
                try:
                    return f.stat().st_size
                except OSError:
                    return 0
            files.sort(key=_safe_size, reverse=True)
            if len(files) > 20:
                print(f"  {C.YELLOW}Scanning 20/{len(files)} files "
                      f"(largest first, capped){C.RESET}")
            return files[:20]
        return []

    def _call_model(self, system_prompt, user_input, timeout=120,
                    model=None):
        """Model call. Uses model override if given, else session model."""
        # Guard: Log external API calls for error telemetry.
        # Captures model name, input/output sizes, timing, errors.
        # Routes to stderr (warnings) + optional .deep/prism.log for diagnostics.
        # Detects API changes, quota issues, model drift silently.
        use_model = model or self.session.model
        import time as _time_module
        start_time = _time_module.time()
        try:
            result = self._claude.call(system_prompt, user_input,
                                      model=use_model, timeout=timeout)
            elapsed = _time_module.time() - start_time
            _logger.debug(
                f"API call OK: model={use_model} "
                f"prompt_size={len(system_prompt)} "
                f"input_size={len(user_input)} "
                f"output_size={len(result)} "
                f"elapsed={elapsed:.1f}s"
            )
            if "[Error:" in result:
                _logger.warning(
                    f"API call error: model={use_model} "
                    f"error={result[:100]}"
                )
            return result
        except Exception as e:
            elapsed = _time_module.time() - start_time
            _logger.error(
                f"API call exception: model={use_model} "
                f"error={type(e).__name__}: {str(e)[:100]} "
                f"elapsed={elapsed:.1f}s"
            )
            raise

    @staticmethod
    def _cleanup_old_findings(findings_dir, max_age_days=FINDINGS_MAX_AGE_DAYS):
        """Delete *.md files in findings_dir whose mtime is older than max_age_days."""
        if not findings_dir.exists():
            return
        cutoff = time.time() - max_age_days * 86400
        for p in findings_dir.glob("*.md"):
            try:
                if p.stat().st_mtime < cutoff:
                    p.unlink()
            except OSError:
                pass


    # ── Parse helpers ─────────────────────────────────────────────────

    def _log_parse_failure(self, context, raw, error):
        """Append a parse-failure record to .deep/parse_errors.log.

        Falls back to stderr when .deep/ does not yet exist.
        Each record contains: ISO timestamp, context label, error message,
        and a 200-char snippet of the raw model output for debugging.
        """
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
        snippet = (raw or "")[:200].replace("\n", "\\n")
        record = (
            f"[{timestamp}] context={context} error={error!r} "
            f"raw_snippet={snippet!r}\n"
        )
        deep_dir = self.working_dir / ".deep"
        if deep_dir.exists():
            log_path = deep_dir / "parse_errors.log"
            try:
                with log_path.open("a", encoding="utf-8") as fh:
                    fh.write(record)
                return
            except OSError:
                pass
        # Fallback: write to stderr so the failure is never silently swallowed
        print(f"{C.DIM}[parse] {record.rstrip()}{C.RESET}", file=sys.stderr)

    @staticmethod
    def _normalize_issue(issue):
        """Map variant field names to canonical schema before validation.

        Handles common Haiku freestyle output: severity→priority,
        fix/suggested_action→action, location→file, what_breaks→description.
        """
        if not isinstance(issue, dict):
            return issue

        # Field name aliases → canonical name (order matters: prefer
        # more specific sources, check each only if target still absent)
        alias_groups = {
            "action": ["fix", "suggested_fix", "suggested_action",
                       "root_cause"],
            "description": ["what_breaks"],
            "file": ["location"],
            "title": ["name"],
        }
        for dst, srcs in alias_groups.items():
            if dst not in issue or not issue[dst]:
                for src in srcs:
                    if src in issue and issue[src]:
                        issue[dst] = issue[src]
                        break

        # severity → priority mapping
        if "priority" not in issue and "severity" in issue:
            sev = str(issue["severity"]).upper().strip()
            sev_map = {
                "CRITICAL": "P0",
                "HIGH": "P1",
                "IMPORTANT": "P1",
                "MEDIUM": "P2",
                "LOW-MEDIUM": "P2",
                "LOW": "P3",
                "MINOR": "P3",
            }
            issue["priority"] = sev_map.get(sev, "P2")

        # id: accept string IDs like "STRUCT-001" → hash to int
        raw_id = issue.get("id")
        if isinstance(raw_id, str) and not raw_id.isdigit():
            issue["id"] = int(hashlib.md5(raw_id.encode()).hexdigest()[:8], 16) % 1000000

        # location often contains function names, not filenames —
        # preserve as separate 'location' field for fix targeting
        loc = issue.get("file", "")
        if isinstance(loc, str) and loc and "." not in loc:
            # Looks like a function/method reference, not a file
            issue.setdefault("location", loc)
            issue["file"] = "unknown"
        # Also preserve original location if it came from that field
        if "location" in issue and issue.get("file") != "unknown":
            issue.setdefault("location", issue.get("location", ""))

        return issue

    @staticmethod
    def _validate_issue(issue):
        """Validate and normalise a single issue dict.

        Required fields: id (int), priority (P0-P3), title, description, action.
        Optional fields: file, prism — default to "unknown" when absent.

        Returns a cleaned copy on success, or None when a required field is
        missing/invalid so the caller can skip the issue and log the failure.
        """
        if not isinstance(issue, dict):
            return None

        # Work on a copy — don't mutate the caller's dict if validation rejects
        issue = dict(issue)

        # Normalize variant fields first
        issue = PrismREPL._normalize_issue(issue)

        # Normalise optional fields before checking required ones
        issue.setdefault("file", "unknown")
        issue.setdefault("prism", "unknown")
        if not issue["file"]:
            issue["file"] = "unknown"
        if not issue["prism"]:
            issue["prism"] = "unknown"

        # id must be an integer (accept strings that parse cleanly)
        raw_id = issue.get("id")
        if raw_id is None:
            return None
        try:
            issue["id"] = int(raw_id)
        except (TypeError, ValueError):
            return None

        # priority must be one of the four canonical values
        priority = issue.get("priority", "")
        if priority not in ("P0", "P1", "P2", "P3"):
            return None

        # Text fields must be non-empty strings
        for field in ("title", "description", "action"):
            val = issue.get(field)
            if not isinstance(val, str) or not val.strip():
                return None
            issue[field] = val.strip()

        return issue

    # ── Heal command ──────────────────────────────────────────────────

    def _load_extract_prompt(self):
        """Load issue extraction prompt from disk or return fallback.

        Validates that fallback prompt model version matches current model.
        Warns if fallback is used with a different model (quality degradation risk).
        """
        for d in [self.working_dir / ".deep" / "skills", GLOBAL_SKILLS_DIR]:
            p = d / "issue_extract.md"
            if p.exists():
                return p.read_text(encoding="utf-8")

        # Using fallback: validate model version compatibility
        # Compare against short names (haiku/sonnet) since session.model stores short names
        fallback_models = {"haiku", "sonnet"}
        if self.session.model not in fallback_models:
            _log_error(
                context="fallback:model_mismatch",
                error_type="FallbackModelWarning",
                error_msg=f"Fallback prompt tuned for {fallback_models}, using {self.session.model}",
                details="Issue extraction may degrade 15-30%. See metadata in ISSUE_EXTRACT_FALLBACK.",
                working_dir=self.working_dir
            )

        return self._load_intent("issue_extract_fallback", ISSUE_EXTRACT_FALLBACK)

    @staticmethod
    def _unwrap_issues_list(data):
        """Extract a flat list of issue dicts from parsed JSON.

        Handles: bare list, dict with a list-valued key (e.g.
        {"concrete_bugs": [...]}), or nested structure with multiple
        list-valued keys (merges all).
        """
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            # Collect all list-of-dict values (e.g. concrete_bugs,
            # structural_issues) — skip metadata dicts/scalars
            merged = []
            for v in data.values():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    merged.extend(v)
            return merged or None
        return None

    @staticmethod
    def _parse_issues_raw(raw):
        """Strip code fences then parse a JSON issues array.

        Returns ``(issues_list, None)`` on success or ``(None, error_str)``
        on failure so callers can decide whether to retry rather than
        silently swallowing malformed output.
        """
        cleaned = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
        cleaned = re.sub(r'^```\s*$', '', cleaned, flags=re.MULTILINE)
        cleaned = cleaned.strip()
        try:
            parsed = json.loads(cleaned)
            issues = PrismREPL._unwrap_issues_list(parsed)
            if issues is not None:
                return issues, None
            return None, "parsed JSON but found no issue lists"
        except json.JSONDecodeError as exc:
            # Regex fallback: try greedy first (whole array), then
            # non-greedy (first [...]) if greedy grabbed cross-object garbage
            for pat in (r'\[.*\]', r'\[.*?\]'):
                m = re.search(pat, cleaned, re.DOTALL)
                if m:
                    try:
                        parsed = json.loads(m.group())
                        # Validate extracted JSON against schema before returning.
                        # Prevents silent failures where malformed but parseable JSON
                        # is returned without structural validation (20% data loss risk).
                        try:
                            if jsonschema:
                                jsonschema.validate(instance=parsed, schema=ISSUES_SCHEMA)
                            return parsed, None
                        except (jsonschema.ValidationError if jsonschema else Exception) as ve:
                            # Schema violation: treat as parse failure, try next pattern
                            continue
                    except json.JSONDecodeError:
                        continue
            return None, str(exc)

    def _reextract_with_error(self, report_text, error_msg):
        """Ask haiku to re-extract issues, forwarding the previous error.

        Returns the raw model response string, or ``None`` when the call
        itself fails so the caller can fall back gracefully.
        """
        retry_prompt = (
            self._load_intent("issue_extract_fallback", ISSUE_EXTRACT_FALLBACK)
            + f"\n\nPrevious attempt failed: {error_msg}\n"
            "Output a complete, valid JSON array only. "
            "Every issue MUST have: non-null integer id, "
            "P0/P1/P2/P3 priority, non-empty title, description, action."
        )
        raw = self._call_model(retry_prompt, report_text)
        if not raw or raw.startswith("[Error"):
            self._log_parse_failure(
                "extract_issues:retry_call", raw, "empty or error on retry")
            return None
        return raw

    @staticmethod
    def _parse_bug_table(report_text):
        """Parse bug table directly from L12 output. Zero API calls.

        L12 outputs a markdown table like:
        | # | Location | What Breaks | Severity | Fixable? | Prediction |
        Returns list of issue dicts for fixable bugs, or None (no table found).
        """
        lines = report_text.split("\n")
        table_rows = []
        in_table = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("| #") or stripped.startswith("| **#"):
                in_table = True
                continue
            # Fallback: detect bug table by distinctive column keywords
            # (handles model variations like | ID | or | Bug | headers)
            if not in_table and stripped.startswith("|"):
                h = stripped.lower()
                if ("sever" in h or "break" in h or "fixab" in h):
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

        sev_map = {"CRITICAL": "P0", "HIGH": "P1", "MEDIUM": "P2",
                   "LOW": "P3", "VERY LOW": "P3", "NONE": "P3"}

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
                "title": f"#{num}: {what_breaks[:60]}",
                "file": "unknown",
                "location": location,
                "description": what_breaks,
                "action": action,
            })

        if issues:
            print(f"      Parsed bug table: {len(table_rows)} rows, "
                  f"{len(issues)} fixable")
        return issues if issues else None

    def _extract_issues(self, report_text):
        """Parse report text into structured issue list.

        First tries to parse the L12 bug table directly (zero API calls).
        Falls back to model-based extraction if no table found.

        Parse failures are logged to .deep/parse_errors.log and each issue
        is validated against the required schema before being included in
        the result.

        On JSON parse failure or schema violations (e.g. null id), re-extracts
        once with an explicit error message so the model can self-correct.
        If invalid items remain after retry the user is notified visibly so
        /fix is never silently run against an incomplete list.
        """
        # Try bug table first (zero API calls)
        table_issues = self._parse_bug_table(report_text)
        if table_issues:
            # Validate each issue through existing pipeline
            validated = []
            for issue in table_issues:
                cleaned = self._validate_issue(issue)
                if cleaned is not None:
                    cleaned.setdefault("status", "open")
                    validated.append(cleaned)
            if validated:
                print(f"      Extracted {len(validated)} issues from bug table "
                      f"(no API call)")
                return validated

        # Fall back to model-based extraction
        extract_prompt = self._load_extract_prompt()
        raw = self._call_model(extract_prompt, report_text)
        if not raw or raw.startswith("[Error"):
            self._log_parse_failure("extract_issues:call", raw, "empty or error response")
            return []

        # Attempt #1: parse JSON
        issues, parse_err = self._parse_issues_raw(raw)
        if parse_err is not None:
            self._log_parse_failure("extract_issues:primary_parse", raw, parse_err)
            raw = self._reextract_with_error(
                report_text, f"Malformed JSON — {parse_err}")
            if raw is None:
                return []
            issues, parse_err = self._parse_issues_raw(raw)
            if parse_err is not None:
                self._log_parse_failure("extract_issues:retry_parse", raw, parse_err)
            elif not issues:
                self._log_parse_failure("extract_issues:retry_parse", raw, "No issues extracted")
            if parse_err is not None or not issues:
                print(
                    f"  {C.YELLOW}Warning: issue extraction failed "
                    f"(JSON still invalid after retry). "
                    f"See .deep/parse_errors.log{C.RESET}"
                )
                return []

        if not isinstance(issues, list):
            self._log_parse_failure(
                "extract_issues:not_a_list", raw, f"got {type(issues).__name__}")
            return []

        # Guard: Validate entire issues array against schema before processing items.
        # Catches regex fallback partial matches that parse as JSON but contain incomplete
        # objects (id=null, missing fields). On validation failure, re-extract with explicit
        # error feedback so model can self-correct (prevents cascading failures in /heal, /plan).
        try:
            if jsonschema:
                jsonschema.validate(instance=issues, schema=ISSUES_SCHEMA)
        except (jsonschema.ValidationError if jsonschema else Exception) as schema_err:
            # Schema violation detected in parsed output: treat as parse failure
            self._log_parse_failure(
                "extract_issues:schema_invalid",
                raw[:500],
                f"Array structure invalid: {str(schema_err)[:100]}")
            # Retry with Claude, passing the specific schema error for self-correction
            raw = self._reextract_with_error(
                report_text,
                f"JSON structure invalid — {str(schema_err)[:80]}")
            if raw is None:
                return []
            issues, parse_err = self._parse_issues_raw(raw)
            if parse_err is not None:
                self._log_parse_failure("extract_issues:retry_after_schema", raw, parse_err)
                print(
                    f"  {C.YELLOW}Warning: issue extraction failed "
                    f"(schema validation failed after retry). "
                    f"See .deep/parse_errors.log{C.RESET}"
                )
                return []
            if not isinstance(issues, list):
                self._log_parse_failure(
                    "extract_issues:retry_not_list", raw, f"got {type(issues).__name__}")
                return []

        # Validate every issue; collect failures for potential retry
        validated, invalid = [], []
        for idx, issue in enumerate(issues):
            cleaned = self._validate_issue(issue)
            if cleaned is None:
                self._log_parse_failure(
                    f"extract_issues:invalid_item[{idx}]",
                    json.dumps(issue, ensure_ascii=False)[:200],
                    "missing or invalid required field")
                invalid.append(issue)
            else:
                cleaned.setdefault("status", "open")
                validated.append(cleaned)

        # Retry once when schema violations are found (e.g. null IDs)
        if invalid:
            error_msg = (
                f"{len(invalid)} of {len(issues)} issue(s) had missing or null "
                "required fields (id, priority, title, description, or action)"
            )
            self._log_parse_failure("extract_issues:schema_fail", raw, error_msg)
            raw2 = self._reextract_with_error(report_text, error_msg)
            if raw2:
                issues2, parse_err2 = self._parse_issues_raw(raw2)
                if parse_err2 is None and isinstance(issues2, list):
                    validated2, invalid2 = [], []
                    for idx, issue in enumerate(issues2):
                        cleaned = self._validate_issue(issue)
                        if cleaned is None:
                            self._log_parse_failure(
                                f"extract_issues:retry_invalid[{idx}]",
                                json.dumps(issue, ensure_ascii=False)[:200],
                                "missing or invalid required field")
                            invalid2.append(issue)
                        else:
                            cleaned.setdefault("status", "open")
                            validated2.append(cleaned)
                    # Accept retry results when they are at least as good
                    if len(invalid2) < len(invalid):
                        validated, invalid = validated2, invalid2

            if invalid:
                print(
                    f"  {C.YELLOW}Warning: {len(invalid)} issue(s) skipped — "
                    f"missing required fields (id/title/priority). "
                    f"See .deep/parse_errors.log{C.RESET}"
                )

        return validated

    def _heal_pick_issues(self, issues):
        """Display issues grouped by priority, return selected list."""
        priority_colors = {
            "P0": C.RED, "P1": C.YELLOW, "P2": C.CYAN, "P3": C.DIM
        }
        priority_labels = {
            "P0": "Critical", "P1": "Important",
            "P2": "Improvement", "P3": "Monitor"
        }

        # Group by priority
        groups = {}
        for issue in issues:
            p = issue.get("priority", "P2")
            groups.setdefault(p, []).append(issue)

        # Display
        open_ids = []
        for p in ["P0", "P1", "P2", "P3"]:
            if p not in groups:
                continue
            color = priority_colors.get(p, "")
            label = priority_labels.get(p, p)
            print(f"\n  {color}{C.BOLD}{p} {label}{C.RESET}")
            for issue in groups[p]:
                iid = issue.get("id", "?")
                title = issue.get("title", "untitled")
                fname = issue.get("file", "")
                prism_val = issue.get("prism", "")
                status = issue.get("status", "open")
                if status == "fixed":
                    print(f"    {C.DIM}{iid:>2}  [{prism_val:<15}] {fname:<12} "
                          f"[FIXED] {title}{C.RESET}")
                else:
                    print(f"    {color}{iid:>2}{C.RESET}  "
                          f"{C.DIM}[{prism_val:<15}]{C.RESET} "
                          f"{fname:<12} {title}")
                    open_ids.append(iid)
        print()

        if not open_ids:
            print(f"  {C.GREEN}All issues fixed!{C.RESET}")
            return []

        # Parse selection
        for _ in range(3):
            try:
                sel = input(
                    f"  {C.GREEN}Select: number, range (1-3), "
                    f"comma (1,3), all, q{C.RESET}\n  > "
                ).strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                return []

            if sel == "q":
                return []

            if sel == "all":
                return [i for i in issues if i.get("status") != "fixed"]

            # Parse numbers
            selected_ids = set()
            try:
                for part in sel.split(","):
                    part = part.strip()
                    if "-" in part:
                        lo, hi = part.split("-", 1)
                        for n in range(int(lo), int(hi) + 1):
                            selected_ids.add(n)
                    else:
                        selected_ids.add(int(part))
            except ValueError:
                print(f"  {C.YELLOW}Invalid selection. Try again.{C.RESET}")
                continue

            result = [i for i in issues
                      if i.get("id") in selected_ids
                      and i.get("status") != "fixed"]
            if result:
                return result
            print(f"  {C.YELLOW}No open issues matched. Try again.{C.RESET}")

        return []

    @staticmethod
    def _extract_structural_context(findings_text):
        """Extract conservation law + meta-law from L12 output.

        Returns a compact string for injection into fix prompts.
        Graceful: returns "" if nothing found.
        """
        if not findings_text:
            return ""

        parts = []

        # Conservation law: ## Conservation Law, ## 12. CONSERVATION LAW, etc.
        cl_match = re.search(
            r'^##\s+(?:\d+\.\s*)?(?:The\s+)?Conservation\s+Law[^\n]*\n(.*?)(?=\n##\s|\Z)',
            findings_text, re.MULTILINE | re.DOTALL | re.IGNORECASE)
        if cl_match:
            body = cl_match.group(1).strip()
            if len(body) > 300:
                body = body[:300].rsplit(" ", 1)[0] + "..."
            parts.append(f"Conservation law: {body}")

        # Meta-law: ## Meta-Law, ## 15. META-CONSERVATION LAW, ## 16. Meta-Law, etc.
        ml_match = re.search(
            r'^##\s+(?:\d+\.\s*)?(?:The\s+)?Meta[-\s](?:Conservation\s+)?Law[^\n]*\n(.*?)(?=\n##\s|\Z)',
            findings_text, re.MULTILINE | re.DOTALL | re.IGNORECASE)
        if ml_match:
            body = ml_match.group(1).strip()
            if len(body) > 200:
                body = body[:200].rsplit(" ", 1)[0] + "..."
            parts.append(f"Meta-law: {body}")

        return "\n\n".join(parts)

    @staticmethod
    def _diff_issues(old_issues, new_issues):
        """Return issues from new_issues not present in old_issues.

        Compares by (location, description) with fuzzy matching to detect
        rewrites/renames of the same issue. Fuzzy threshold: >0.7 similarity.
        Falls back to exact substring match for performance.
        """
        def _normalize(s):
            """Normalize string for comparison."""
            return s.lower().strip()[:50] if s else ""

        def _similarity(s1, s2):
            """Token-based Jaccard similarity (0-1).

            Uses word tokens instead of character bags to avoid
            false negatives on rephrased descriptions of the same bug.
            'Missing null check in parse_line' vs 'parse_line lacks
            null validation' share tokens {null, parse_line} → match.
            """
            if not s1 or not s2:
                # Both empty = unknown (not identical). Prevents false dedup.
                return 0.0
            s1, s2 = _normalize(s1), _normalize(s2)
            if s1 == s2:
                return 1.0
            # Token-based Jaccard: intersection / union
            t1 = set(re.findall(r'[a-z_][a-z0-9_]*', s1))
            t2 = set(re.findall(r'[a-z_][a-z0-9_]*', s2))
            if not t1 or not t2:
                return 0.0
            intersection = t1 & t2
            union = t1 | t2
            return len(intersection) / len(union)

        def _sig(issue):
            loc = issue.get("location", issue.get("file", ""))
            desc = issue.get("description", "")
            return (loc, _normalize(desc))

        old_sigs = {_sig(i) for i in old_issues}
        result = []
        for new_issue in new_issues:
            new_sig = _sig(new_issue)
            # Exact match first (fast path)
            if new_sig not in old_sigs:
                # Fuzzy match: check if any old issue is >70% similar
                found_similar = False
                for old_issue in old_issues:
                    old_loc = old_issue.get("location", old_issue.get("file", ""))
                    if old_loc == new_sig[0]:  # Same location
                        similarity = _similarity(
                            old_issue.get("description", ""),
                            new_issue.get("description", "")
                        )
                        if similarity > 0.7:
                            found_similar = True
                            break
                if not found_similar:
                    result.append(new_issue)
        return result

    def _heal_fix_one(self, issue, structural_context="", fresh=False):
        """Apply a fix for one issue. Returns 'approved'/'rejected'/'instructed'."""
        fname = issue.get("file", "unknown")
        title = issue.get("title", "")
        desc = issue.get("description", "")
        action = issue.get("action", "")
        location = issue.get("location", "")

        # Extract location from description/action if not provided
        if not location:
            desc_funcs = re.findall(r'(_\w{5,})\(\)', f"{desc} {action}")
            if desc_funcs:
                location = desc_funcs[0]

        # Resolve target file
        target = self._resolve_file(fname) if fname != "unknown" else None
        snapshots = {}

        if target and target.exists():
            try:
                snapshots[str(target)] = target.read_text(
                    encoding="utf-8", errors="replace")
            except (OSError, PermissionError) as e:
                print(f"  {C.YELLOW}Cannot snapshot {fname}: {e}{C.RESET}")

        # Pre-grep: extract relevant code snippet around the location
        snippet = ""
        if target and target.exists() and (location or desc or action):
            snippet = self._heal_grep_context(
                target, location, desc=desc, action=action)

        # Build specific fix message
        fix_msg = (
            f"Fix this specific issue in {fname}:\n\n"
            f"Title: {title}\n"
            f"Description: {desc}\n"
        )
        if location:
            fix_msg += f"Location: {location}\n"
        if action:
            fix_msg += f"Suggested action: {action}\n"
        if snippet:
            fix_msg += (
                f"\nRelevant code (with line numbers):\n"
                f"```\n{snippet}\n```\n"
            )
        if structural_context:
            fix_msg += (
                f"\n## Structural context (from L12 analysis)\n"
                f"{structural_context}\n\n"
                f"This issue is fixable. Do not fight structural "
                f"constraints — work within them.\n"
            )
        fix_msg += (
            "\nLocate the exact method and line before editing. "
            "Make exactly one change: replace a variable or statement, "
            "insert a new block, or add a guard clause. "
            "If this fix requires changes in 3+ locations, fix only the "
            "most critical one. Don't refactor unrelated code."
        )
        if target:
            fix_msg += f"\n\nFile path: {target}"

        self._send_and_stream(fix_msg, fresh=fresh)

        result = self._heal_review_diff(snapshots, issue)
        return result, snapshots

    def _heal_grep_context(self, target, location, context_lines=65,
                           desc="", action=""):
        """Extract code around a function/method name for fix targeting.

        Searches for method definitions first (``def _method``), then
        falls back to identifier matching.  Returns numbered lines
        around the last match (favors overrides/mocks), or "" if not found.

        Accepts desc/action strings to mine additional search terms
        beyond the location field (functions, constants, identifiers).
        """
        try:
            # Guard: Protect file reads from concurrent writes with lock to avoid garbled snippets
            with self._file_io_lock:
                lines = target.read_text(
                    encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return ""

        combined = f"{location} {desc} {action}"

        # Location-specific: match both public and private methods
        search_terms = []
        if location:
            loc_funcs = re.findall(r'(\w{4,})\(\)', location)
            for f in loc_funcs:
                search_terms.append(f"def {f}")
            if not loc_funcs:
                search_terms.append(f"def {location}")
                search_terms.append(location)

        # Extract function/method names from all fields
        funcs = re.findall(r'(_\w{5,})\(\)', combined)
        if not funcs:
            funcs = re.findall(r'(_\w{5,})', location)

        # Definitions first
        for f in funcs[:3]:
            search_terms.append(f"def {f}")

        # ALL_CAPS constants (e.g. ALLOWED_TOOLS)
        caps = re.findall(r'[A-Z][A-Z_]{3,}', combined)
        search_terms.extend(caps[:3])

        # Quoted identifiers from action
        quoted = re.findall(r"'([_a-zA-Z]\w{4,})'", action)
        search_terms.extend(quoted[:2])

        # Snake_case identifiers (long ones only)
        for text in [action, desc]:
            snakes = re.findall(r'[a-z]\w*_\w{3,}', text)
            search_terms.extend(s for s in snakes
                                if len(s) > 7 and s not in search_terms)

        # Session-specific routing
        combined_lower = combined.lower()
        if "session" in combined_lower and any(
                kw in combined_lower
                for kw in ("persist", "migration", "model_name",
                           "schema version")):
            search_terms.insert(0, "def load(")
            search_terms.insert(1, "def save(")

        # Fallback: bare identifiers
        if not search_terms:
            search_terms = [t for t in re.findall(r'\w+', location)
                           if len(t) > 4 and not t[0].isupper()]
        # Final fallback: function names without "def "
        for f in funcs:
            if f not in search_terms:
                search_terms.append(f)

        if not search_terms:
            return ""

        # Dedupe preserving order
        seen = set()
        unique = [t for t in search_terms
                  if t not in seen and not seen.add(t)]

        # Search forwards first for definitions (production code),
        # backwards only as fallback (catches mocks/overrides).
        for term in unique[:8]:
            # Forward pass: prefer first definition
            if term.startswith("def "):
                for i in range(len(lines)):
                    if term in lines[i]:
                        start = max(0, i - 5)
                        end = min(len(lines), i + context_lines)
                        numbered = [f"{n+1:>4}  {lines[n]}"
                                   for n in range(start, end)]
                        return "\n".join(numbered)
            # Non-definition terms: search backwards (last usage)
            for i in range(len(lines) - 1, -1, -1):
                if term in lines[i]:
                    start = max(0, i - 5)
                    end = min(len(lines), i + context_lines)
                    numbered = [f"{n+1:>4}  {lines[n]}"
                               for n in range(start, end)]
                    return "\n".join(numbered)

        # Whole-file fallback for small files
        if len(lines) <= 500:
            return "\n".join(f"{n+1:>4}  {lines[n]}"
                             for n in range(len(lines)))
        return ""

    def _heal_review_diff(self, snapshots, issue):
        """Show diff of changes and get user approval."""
        has_changes = False

        for filepath, original in snapshots.items():
            path = pathlib.Path(filepath)
            if not path.exists():
                continue
            current = path.read_text(encoding="utf-8", errors="replace")
            if current != original:
                has_changes = True
                print(f"\n  {C.BOLD}Changes in {path.name}:{C.RESET}")
                self._show_inline_diff(original, current, path.name)

        # Fallback: check git diff scoped to the issue's file
        if not has_changes:
            try:
                diff_cmd = ["git", "diff"]
                # Scope to specific file to avoid showing unrelated changes
                issue_file = issue.get("file", "")
                resolved = self._resolve_file(issue_file) if issue_file else None
                if resolved and resolved.exists():
                    diff_cmd.append("--")
                    diff_cmd.append(str(resolved))
                result = subprocess.run(
                    diff_cmd, capture_output=True, text=True,
                    encoding="utf-8", cwd=self.working_dir, timeout=10,
                )
                git_diff = result.stdout.strip()
                if git_diff:
                    has_changes = True
                    print(f"\n  {C.BOLD}Changes (git diff):{C.RESET}")
                    lines = git_diff.split("\n")
                    for line in lines[:60]:
                        if line.startswith("+") and not line.startswith("+++"):
                            print(f"  {C.GREEN}{line}{C.RESET}")
                        elif line.startswith("-") and not line.startswith("---"):
                            print(f"  {C.RED}{line}{C.RESET}")
                        elif line.startswith("@@"):
                            print(f"  {C.CYAN}{line}{C.RESET}")
                        else:
                            print(f"  {line}")
                    if len(lines) > 60:
                        print(f"  {C.DIM}... ({len(lines) - 60} more lines){C.RESET}")
            except Exception:
                pass

        if not has_changes:
            print(f"\n  {C.YELLOW}No changes detected{C.RESET}")
            return "rejected"

        # Guard: Verify changes with git diff before approval.
        # Edit tool may claim success but fail silently (permission denied, encoding error).
        # Git diff is authoritative — if empty, tool failed and we must reject.
        try:
            diff_result = subprocess.run(
                ["git", "diff", "--quiet"],
                cwd=self.working_dir, timeout=10,
                capture_output=True
            )
            # --quiet returns 0 if no changes, 1 if changes exist
            if diff_result.returncode == 0:
                # Git diff is empty — no actual changes despite has_changes=True
                print(f"\n  {C.YELLOW}Tool claimed success but git diff is empty. "
                      f"Edit may have failed silently.{C.RESET}")
                return "rejected"
        except Exception:
            # If git diff fails, warn but allow approval (conservative fallback)
            pass

        # B9: Impact prediction before approval (non-auto mode only)
        if not getattr(self, "_auto_mode", False):
            self._predict_fix_impact(snapshots, issue)

        _approval = self._heal_prompt_approval(snapshots)

        # B4 Phase 3: Record learning event from user approval/rejection
        if _approval == "approved":
            self._record_learning("accepted_fix", {
                "issue": issue.get("title", ""),
                "file": issue.get("file", ""),
            })
        elif _approval == "rejected":
            self._record_learning("rejected_fix", {
                "issue": issue.get("title", ""),
                "file": issue.get("file", ""),
            })

        return _approval

    def _predict_fix_impact(self, snapshots, issue):
        """B9: Predict impact of a fix before approval.

        Shows affected functions, edge cases, risk level, and
        preserved invariants. Uses Haiku for speed (~$0.002).
        """
        # Build diff text
        diff_parts = []
        for filepath, original in snapshots.items():
            path = pathlib.Path(filepath)
            if not path.exists():
                continue
            current = path.read_text(encoding="utf-8", errors="replace")
            if current != original:
                orig_lines = original.splitlines(keepends=True)
                curr_lines = current.splitlines(keepends=True)
                diff = list(difflib.unified_diff(
                    orig_lines, curr_lines,
                    fromfile=f"a/{path.name}",
                    tofile=f"b/{path.name}", lineterm=""))
                if diff:
                    diff_parts.append("\n".join(diff[:80]))

        if not diff_parts:
            return

        diff_text = "\n\n".join(diff_parts)
        title = issue.get("title", "unknown issue")

        impact_input = (
            f"## Issue being fixed\n{title}\n\n"
            f"## Diff\n```\n{diff_text}\n```")

        try:
            print(f"\n  {C.DIM}Predicting impact...{C.RESET}",
                  end="", flush=True)
            impact = self._claude.call(
                IMPACT_PREDICT_PROMPT, impact_input,
                model="haiku", timeout=30)
            if impact and impact.strip():
                print()
                print(f"  {C.BOLD}Impact prediction:{C.RESET}")
                for line in impact.strip().split("\n")[:15]:
                    print(f"  {C.DIM}{line}{C.RESET}")
            else:
                print(f" {C.DIM}(no prediction){C.RESET}")
        except Exception:
            print(f" {C.DIM}(skipped){C.RESET}")

    def _show_inline_diff(self, original, current, filename=""):
        """Show colored unified diff."""
        orig_lines = original.splitlines(keepends=True)
        curr_lines = current.splitlines(keepends=True)
        diff = list(difflib.unified_diff(
            orig_lines, curr_lines,
            fromfile=f"a/{filename}", tofile=f"b/{filename}",
            lineterm="",
        ))
        if not diff:
            print(f"  {C.DIM}(no diff){C.RESET}")
            return

        shown = 0
        total = len(diff)
        for line in diff:
            line = line.rstrip("\n")
            if shown >= 60:
                remaining = total - shown
                print(f"  {C.DIM}... ({remaining} more lines) "
                      f"Show full? [y/n]{C.RESET}", end=" ", flush=True)
                try:
                    ans = input().strip().lower()
                except (EOFError, KeyboardInterrupt):
                    print()
                    break
                if ans != "y":
                    break
                shown = 0  # Reset counter for the rest
            if line.startswith("+") and not line.startswith("+++"):
                print(f"  {C.GREEN}{line}{C.RESET}")
            elif line.startswith("-") and not line.startswith("---"):
                print(f"  {C.RED}{line}{C.RESET}")
            elif line.startswith("@@"):
                print(f"  {C.CYAN}{line}{C.RESET}")
            else:
                print(f"  {line}")
            shown += 1

    def _heal_prompt_approval(self, snapshots):
        """Prompt user to approve, reject, or instruct. Returns status string."""
        if getattr(self, "_auto_mode", False):
            print(f"  {C.GREEN}Auto-approved{C.RESET}")
            return "approved"
        print()
        try:
            ans = input(
                f"  {C.BOLD}(y){C.RESET} approve  "
                f"{C.BOLD}(n){C.RESET} discard  "
                f"{C.BOLD}(i){C.RESET} instruct\n  > "
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            self._heal_restore(snapshots)
            return "rejected"

        if ans == "n":
            self._heal_restore(snapshots)
            print(f"  {C.YELLOW}Changes discarded{C.RESET}")
            return "rejected"
        elif ans == "i":
            self._heal_restore(snapshots)
            return "instructed"
        else:
            return "approved"

    def _heal_restore(self, snapshots):
        """Restore files from snapshots."""
        for filepath, content in snapshots.items():
            pathlib.Path(filepath).write_text(content, encoding="utf-8")

    def _heal_verify(self, issue, pre_fix_snapshot=None):
        """Verify a fix: 1 API call + py_compile syntax check."""
        fname = issue.get("file", "unknown")
        target = self._resolve_file(fname)
        if not target or not target.exists():
            return "fixed"

        # Syntax check (zero API cost, no __pycache__ side effects)
        if target.suffix == ".py":
            try:
                import ast
                source = target.read_text(encoding="utf-8", errors="replace")
                ast.parse(source, filename=str(target))
            except SyntaxError as e:
                print(f"  {C.RED}Syntax error: {e}{C.RESET}")
                return "unfixed"
            except (OSError, PermissionError) as e:
                print(f"  {C.YELLOW}Cannot read for syntax check: "
                      f"{e}{C.RESET}")

        # Single API call: issue + current code → verdict
        print(f"  {C.DIM}Verifying fix...{C.RESET}")
        content = target.read_text(encoding="utf-8", errors="replace")
        verify_input = (
            f"ISSUE:\n{issue.get('title', '')}: "
            f"{issue.get('description', '')}\n\n"
            f"CURRENT CODE ({fname}):\n{content[:8000]}"
        )
        output = self._call_model(
            self._load_intent("heal_verify", HEAL_VERIFY_PROMPT),
            verify_input)

        # Parse verdict — default to "unfixed" so timeout/empty output
        # doesn't silently mark issues as fixed
        result = "unfixed"
        if output:
            for line in output.strip().split("\n"):
                upper = line.strip().upper()
                if upper.startswith("VERDICT:"):
                    v = upper.split(":", 1)[1].strip().split()[0]
                    if v in ("FIXED", "PARTIAL", "UNFIXED"):
                        result = v.lower()
                elif upper.startswith("REGRESSION:") and "YES" in upper:
                    detail = ""
                    for dl in output.strip().split("\n"):
                        if dl.strip().upper().startswith("DETAIL:"):
                            detail = dl.split(":", 1)[1].strip()
                    print(f"  {C.YELLOW}Warning: possible regression"
                          f"{' — ' + detail if detail else ''}{C.RESET}")

        color = {"fixed": C.GREEN, "partial": C.YELLOW,
                 "unfixed": C.RED}.get(result, C.DIM)
        print(f"  {color}{result.upper()}{C.RESET}")
        return result

    def _heal_extract_from_reports(self, deep_dir):
        """Extract issues from all available reports in .deep/."""
        all_issues = []
        sources = []

        report_path = deep_dir / "report.md"
        if report_path.exists():
            sources.append(report_path)
        for bp in sorted(deep_dir.glob("brain_*.md")):
            sources.append(bp)
        findings_dir = deep_dir / "findings"
        if findings_dir.is_dir():
            for fp in sorted(findings_dir.glob("*.md")):
                sources.append(fp)

        for src in sources:
            text = src.read_text(encoding="utf-8")
            issues = self._extract_issues(text)
            if issues:
                # Backfill "unknown" file fields from findings filename
                # e.g. findings/prism.md → prism.py
                src_stem = src.stem
                for iss in issues:
                    if iss.get("file") == "unknown" and src_stem != "report":
                        # Try common extensions
                        for ext in (".py", ".js", ".ts", ".go", ".rs"):
                            candidate = self._resolve_file(src_stem + ext)
                            if candidate and candidate.exists():
                                iss["file"] = src_stem + ext
                                break
                print(f"  {C.DIM}Extracted {len(issues)} issues "
                      f"from {src.name}{C.RESET}")
                all_issues.extend(issues)

        # Re-number sequentially and deduplicate by title
        seen = set()
        deduped = []
        for issue in all_issues:
            title = issue.get("title", "").lower().strip()
            if title and title in seen:
                continue
            seen.add(title)
            deduped.append(issue)
        for i, issue in enumerate(deduped, 1):
            issue["id"] = i

        return deduped

    def _cmd_heal(self, arg):
        """/fix [file] [deep] [auto] — interactive fix pipeline with diff review."""
        # Parse modifiers
        deep_mode = False
        auto_mode = False
        file_arg = None
        if arg:
            parts = arg.split()
            modifiers = {"deep", "auto"}
            flags = [p for p in parts if p in modifiers]
            file_parts = [p for p in parts if p not in modifiers]
            deep_mode = "deep" in flags
            auto_mode = "auto" in flags
            file_arg = file_parts[0] if file_parts else None
            if deep_mode and not file_arg:
                print(f"{C.YELLOW}Usage: /fix <file> deep{C.RESET}")
                return

        # Deep mode: always rescan with full prism (3 calls)
        if deep_mode:
            content, name = self._get_deep_content(file_arg)
            if not content:
                print(f"{C.RED}File not found: {file_arg}{C.RESET}")
                return
            self._run_full_pipeline(content, name)
            # Clear cached issues so we re-extract from fresh findings
            issues_path = self.working_dir / ".deep" / "issues.json"
            if issues_path.exists():
                issues_path.unlink()
            arg = name  # fall through to heal with file filter
            file_arg = name

        deep_dir = self.working_dir / ".deep"
        issues_path = deep_dir / "issues.json"

        # Load or extract issues
        issues = []
        if issues_path.exists():
            try:
                data = json.loads(issues_path.read_text(encoding="utf-8"))
                self._ensure_version(data)
                # Migrate old list format to new dict format
                if isinstance(data, list):
                    issues = data
                    migrated = {"_version": 1, "issues": issues,
                                "extracted_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
                    try:
                        issues_path.write_text(
                            json.dumps(migrated, indent=2), encoding="utf-8")
                    except OSError:
                        pass
                    data = migrated
                else:
                    issues = data.get("issues", [])
                extracted_at = None
                if isinstance(data, dict):
                    extracted_at = data.get("extracted_at")
                # Stale check
                if extracted_at:
                    try:
                        ts = time.mktime(time.strptime(
                            extracted_at, "%Y-%m-%dT%H:%M:%S"))
                        age_hours = (time.time() - ts) / 3600
                        if age_hours > 24:
                            print(f"  {C.YELLOW}Issues may be stale "
                                  f"({int(age_hours)}h old). "
                                  f"Re-run /scan?{C.RESET}")
                    except (ValueError, OverflowError):
                        pass
                # File drift check — warn if source files have been
                # manually edited since findings were generated.
                # Store mtimes to check before approval (prevents stale verdicts).
                file_mtimes = (data.get("file_mtimes", {})
                               if isinstance(data, dict) else {})
                self._cached_file_mtimes = file_mtimes  # Store for pre-approval drift detection
                drifted = []
                for _fname, _saved_mtime in file_mtimes.items():
                    _target = self._resolve_file(_fname)
                    if _target and _target.exists():
                        try:
                            if _target.stat().st_mtime > _saved_mtime + 1:
                                drifted.append(_fname)
                        except OSError:
                            pass
                if drifted:
                    print(f"  {C.YELLOW}Warning: {len(drifted)} file(s) "
                          f"modified since findings were generated:{C.RESET}")
                    for _df in drifted:
                        print(f"    {C.DIM}{_df}{C.RESET}")
                    print(f"  {C.YELLOW}Verification may compare against a "
                          f"stale baseline — re-run /scan to refresh."
                          f"{C.RESET}")
            except (json.JSONDecodeError, OSError):
                issues = []

        # No issues found — auto-scan with single prism, then extract
        if not issues and not deep_mode:
            if file_arg:
                content, name = self._get_deep_content(file_arg)
                if not content:
                    print(f"{C.RED}File not found: {file_arg}{C.RESET}")
                    return
                print(f"{C.CYAN}No scan results — running single prism...{C.RESET}")
                self._run_single_prism_streaming("l12", content, name)
            else:
                print(f"{C.YELLOW}No scan results. "
                      f"Specify a file: /fix <file>{C.RESET}")
                return
            # Re-extract from fresh findings
            deep_dir.mkdir(parents=True, exist_ok=True)
            issues_path = deep_dir / "issues.json"
            if issues_path.exists():
                issues_path.unlink()
            print(f"  {C.DIM}Extracting issues from reports...{C.RESET}")
            issues = self._heal_extract_from_reports(deep_dir)
            if not issues:
                print(f"{C.GREEN}No issues found.{C.RESET}")
                return
            self._heal_save_issues(deep_dir, issues)

        # Filter by file if specified — normalize to basename for matching
        if file_arg:
            file_base = pathlib.Path(file_arg).name
            issues = [i for i in issues
                      if file_base in i.get("file", "")
                      or i.get("file", "") in file_arg
                      or pathlib.Path(i.get("file", "")).name == file_base]
            if not issues:
                print(f"{C.YELLOW}No issues for '{file_arg}'{C.RESET}")
                return

        total = len(issues)
        open_count = sum(1 for i in issues if i.get("status") != "fixed")
        print(f"\n  {C.BOLD}{C.CYAN}FIX{C.RESET}  "
              f"{total} issues ({open_count} open)")

        if auto_mode:
            selected = [i for i in issues if i.get("status") != "fixed"]
            if not selected:
                print(f"  {C.GREEN}All issues already fixed!{C.RESET}")
                return
            self._auto_mode = True
            max_passes = 3
        else:
            selected = self._heal_pick_issues(issues)
            if not selected:
                print(f"{C.DIM}Cancelled{C.RESET}")
                return
            self._auto_mode = False
            max_passes = 1

        grand_stats = {"approved": 0, "rejected": 0, "fixed": 0,
                       "partial": 0, "unfixed": 0}

        try:
            for pass_num in range(1, max_passes + 1):
                if pass_num > 1:
                    selected = [i for i in issues
                                if i.get("status") in ("open", "unfixed", "partial")]
                    if not selected:
                        break
                    print(f"\n  {C.BOLD}{C.CYAN}── Pass {pass_num}: "
                          f"retrying {len(selected)} unfixed ──{C.RESET}\n")

                if pass_num == 1:
                    print(f"\n  Fixing {len(selected)} issue(s)"
                          f"{f' (auto, up to {max_passes} passes)' if auto_mode else ''}\n")

                # Guard: Phase-level transaction — collect all state changes in memory.
                # Only write to issues.json after entire phase succeeds. If crash occurs,
                # no partial writes on disk (automatic rollback). Create snapshot of
                # original issue states before phase processes any issues.
                phase_snapshot = json.dumps(
                    [dict(i) for i in issues],
                    default=str)  # Backup for rollback on crash

                stats = {"approved": 0, "rejected": 0, "fixed": 0,
                         "partial": 0, "unfixed": 0}

                for idx, issue in enumerate(selected, 1):
                    title = issue.get("title", "untitled")
                    print(f"  {C.BOLD}{C.CYAN}── Issue {idx}/{len(selected)}: "
                          f"{title} ──{C.RESET}")

                    attempts = 0
                    instructions = ""
                    while attempts < 3:
                        attempts += 1

                        fix_issue = dict(issue)
                        if instructions:
                            fix_issue["action"] = (
                                f"{issue.get('action', '')} "
                                f"User instructions: {instructions}"
                            )

                        result, snapshots = self._heal_fix_one(fix_issue)

                        if result == "approved":
                            stats["approved"] += 1
                            # Guard: Check file drift at approval time to prevent stale verdicts.
                            # If file modified after findings were cached, warn user before approval.
                            _fname = fix_issue.get("file", "unknown")
                            _t = self._resolve_file(_fname)
                            if _t and _t.exists():
                                try:
                                    current_mtime = _t.stat().st_mtime
                                    # Check cached mtime from when findings were extracted
                                    cached_mtimes = getattr(self, "_cached_file_mtimes", {})
                                    cached_mtime = cached_mtimes.get(_fname)
                                    if cached_mtime and current_mtime > cached_mtime + 1:
                                        print(f"  {C.YELLOW}⚠ {_fname} was edited after /scan. "
                                              f"Findings are based on earlier version. "
                                              f"Verify fix applies to CURRENT code.{C.RESET}")
                                except OSError:
                                    pass
                            _t = self._resolve_file(fix_issue.get("file", ""))
                            pre_fix = snapshots.get(str(_t)) if _t else None
                            # Detect manual edits during review: capture mtime at approval,
                            # check if file changed before verification runs.
                            # User may spend 2+ hours reviewing and manually edit code.
                            approval_mtime = None
                            if _t and _t.exists():
                                try:
                                    approval_mtime = _t.stat().st_mtime
                                except OSError:
                                    pass
                            verdict = self._heal_verify(
                                issue, pre_fix_snapshot=pre_fix)
                            # Guard: warn if file was modified after fix approved but before verification.
                            # Verification would compare against stale baseline.
                            if approval_mtime is not None and _t and _t.exists():
                                try:
                                    current_mtime = _t.stat().st_mtime
                                    if current_mtime > approval_mtime + 0.5:  # >500ms diff = modified
                                        print(f"  {C.YELLOW}Warning: {_t.name} modified "
                                              f"after fix approval. Verification baseline may be stale. "
                                              f"Consider /scan to refresh.{C.RESET}")
                                except OSError:
                                    pass
                            stats[verdict] = stats.get(verdict, 0) + 1
                            issue["status"] = verdict
                            break

                        elif result == "rejected":
                            stats["rejected"] += 1
                            break

                        elif result == "instructed":
                            if auto_mode:
                                stats["rejected"] += 1
                                break
                            try:
                                instructions = input(
                                    f"  {C.GREEN}Instructions:{C.RESET} "
                                ).strip()
                            except (EOFError, KeyboardInterrupt):
                                print()
                                stats["rejected"] += 1
                                break
                            if not instructions:
                                stats["rejected"] += 1
                                break
                            print(f"  {C.DIM}Retrying with instructions "
                                  f"(attempt {attempts + 1}/3)...{C.RESET}")
                    print()

                for k in grand_stats:
                    grand_stats[k] += stats.get(k, 0)

                # Update issues but preserve original mtimes for drift detection
                self._heal_save_issues(deep_dir, issues, snapshot_mtimes=False)

                fixed_now = sum(1 for i in issues
                               if i.get("status") == "fixed")
                if auto_mode:
                    print(f"  {C.BOLD}Pass {pass_num}:{C.RESET} "
                          f"{stats.get('fixed', 0)} fixed, "
                          f"{stats.get('unfixed', 0)} unfixed "
                          f"({fixed_now}/{total} total)")
        finally:
            self._auto_mode = False

        # Summary
        print(f"\n  {C.BOLD}Summary:{C.RESET} "
              f"{grand_stats['approved']} approved, "
              f"{grand_stats.get('fixed', 0)} fixed, "
              f"{grand_stats.get('partial', 0)} partial, "
              f"{grand_stats.get('unfixed', 0)} unfixed, "
              f"{grand_stats['rejected']} rejected")
        print()

    def _heal_save_issues(self, deep_dir, issues, snapshot_mtimes=True):
        """Save issues to .deep/issues.json.

        Args:
            snapshot_mtimes: If True, capture current file mtimes as baseline for drift detection.
                           If False (on updates), preserve existing baseline mtimes.
        """
        deep_dir.mkdir(parents=True, exist_ok=True)
        issues_path = deep_dir / "issues.json"

        # Snapshot mtimes ONLY on first save (extraction time), not on updates
        # This allows drift detection to compare against the baseline, not the
        # continuously-updated file state
        file_mtimes = {}
        mtimes_read_ok = False
        if snapshot_mtimes:
            # Capture baseline mtimes for drift detection
            for issue in issues:
                fname = issue.get("file", "")
                if fname and fname not in file_mtimes:
                    target = self._resolve_file(fname)
                    if target and target.exists():
                        try:
                            file_mtimes[fname] = target.stat().st_mtime
                        except OSError:
                            pass
        else:
            # Preserve existing baseline mtimes from previous save.
            # On read failure, skip the mtimes key so existing data is preserved.
            if issues_path.exists():
                try:
                    old_data = json.loads(issues_path.read_text(encoding="utf-8"))
                    # Handle both old (list) and new (dict with _version) formats.
                    # Old unversioned format: plain list. New format: dict with _version.
                    # Prevents silent corruption when upgrading from unversioned sessions.
                    if isinstance(old_data, dict):
                        file_mtimes = old_data.get("file_mtimes", {})
                        mtimes_read_ok = True
                    # else: old_data is list (unversioned format) — no file_mtimes available
                except (json.JSONDecodeError, OSError):
                    pass

        data = {
            "_version": 1,
            "extracted_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "issues": issues,
        }
        # Only write file_mtimes if we have valid data — either freshly
        # captured (snapshot_mtimes=True) or successfully read from disk.
        # Never overwrite existing mtimes with {} on read failure.
        if snapshot_mtimes or mtimes_read_ok:
            data["file_mtimes"] = file_mtimes
        # Write-ahead log (WAL): write to .wal, atomically rename to .json.
        # This prevents corruption when /scan, /heal, /plan, /autopilot write concurrently.
        # Atomic rename ensures readers always see complete file, never partial state.
        wal_path = issues_path.parent / "issues.wal"
        wal_path.write_text(
            json.dumps(data, indent=2), encoding="utf-8")
        wal_path.replace(issues_path)  # Atomic rename on all platforms
        print(f"  {C.DIM}Saved: .deep/issues.json "
              f"({len(issues)} items){C.RESET}")
    def _parse_stage_json(self, raw, stage_name):
        """Parse JSON from a stage response. Returns parsed data or None."""
        if not raw or raw.startswith("[Error"):
            self._log_parse_failure(f"{stage_name}:call", raw, "empty or error")
            return None
        # Strip markdown code fences
        cleaned = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
        cleaned = re.sub(r'^```\s*$', '', cleaned, flags=re.MULTILINE)
        cleaned = cleaned.strip()
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            # Detect specific parse failure types for better diagnostics
            error_msg = "no valid JSON"
            # Check for trailing commas
            if re.search(r',\s*[}\]]', cleaned):
                trailing_line = next(
                    (i+1 for i, line in enumerate(cleaned.split('\n'))
                     if re.search(r',\s*[}\]]', line)), None)
                error_msg = f"Trailing comma on line {trailing_line}" if trailing_line else "Trailing comma detected"
            # Check for JSON5 unquoted keys
            elif re.search(r'[{\s,]\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', cleaned):
                error_msg = "Expected JSON, got JSON5 (unquoted keys)"
            # Check for single quotes instead of double quotes
            elif re.search(r"'[^']*'", cleaned) and not re.search(r'"[^"]*"', cleaned):
                error_msg = "Expected JSON, got JSON5 (single quotes)"
            # Check for JSON comments
            elif re.search(r'//|/\*|\*/', cleaned):
                error_msg = "JSON comments detected (// or /* */)"

            # Fallback: find JSON array or object anywhere.
            # Greedy arrays first (captures nested brackets correctly).
            # Then greedy objects, then non-greedy fallbacks.
            parsed = None
            for pattern in (r'\[.*\]', r'\{.*\}',
                            r'\[.*?\]', r'\{.*?\}'):
                m = re.search(pattern, cleaned, re.DOTALL)
                if m:
                    try:
                        parsed = json.loads(m.group())
                        break
                    except json.JSONDecodeError:
                        continue
            if parsed is None:
                self._log_parse_failure(f"{stage_name}:parse", raw[:500], error_msg)
                return None

        # Unwrap dict-wrapped lists: model sometimes returns {"result": [...]}
        # instead of bare [...]. Extract the first list-of-dicts value.
        if isinstance(parsed, dict):
            for v in parsed.values():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    return v
        return parsed

    # ── Message building ─────────────────────────────────────────────────

    def _build_message(self, user_input):
        """Prepend queued file contents to user input.

        Structural context (prism findings) goes into the system prompt
        via _enriched_system_prompt, NOT here. This keeps the user message
        clean — just the files and the request.
        """
        parts = []
        for fpath in self.queued_files:
            try:
                content = fpath.read_text(encoding="utf-8", errors="replace")
                parts.append(f"<file path=\"{fpath}\">\n{content}\n</file>")
            except Exception as e:
                print(f"  {C.YELLOW}Cannot read {fpath}: {e}{C.RESET}")
        parts.append(user_input)
        return "\n\n".join(parts)

    # ── Streaming ────────────────────────────────────────────────────────

    def _clear_thinking_line(self):
        """Guard: Clear 'thinking...' line only if stdout is a TTY.

        When stdout is redirected to a file, cursor control codes (\r) create garbage.
        This guard ensures cursor mutations only occur in interactive terminals.
        """
        if sys.stdout.isatty():
            sys.stdout.write("\r" + " " * 30 + "\r")

    def _send_and_stream(self, message, fresh=False):
        """Send message to Claude and stream the response to stdout.

        Validates session consistency before each send: if a previous turn caused
        a session ID change (network hiccup / expiry), the user must explicitly
        acknowledge the divergence before we continue.
        """
        if self._session_diverged:
            if getattr(self, "_auto_mode", False):
                # Auto mode: skip interactive confirmation to avoid deadlock
                self._session_diverged = False
                self._session_transition_log.clear()
            elif not self._confirm_session_diverged():
                return  # User declined to continue in a diverged context

        # Use enriched system prompt if prism analysis was injected,
        # otherwise fall back to base system prompt.
        active_prompt = getattr(self, '_enriched_system_prompt', None)
        if active_prompt:
            self._enriched_system_prompt = None  # one-shot, reset after use
        base = active_prompt or self.system_prompt
        # Prepend active prism if set via /prism <prism>.
        # Skip if enriched prompt is set (implies /fix or /scan context — prism
        # would conflict with the analysis-specific system prompt).
        if self._active_prism_prompt and active_prompt:
            print(f"  {C.DIM}(prism '{self._active_prism_name}' skipped — "
                  f"using analysis context){C.RESET}")
        elif self._active_prism_prompt:
            base = self._active_prism_prompt + "\n\n" + base
        self.backend = ClaudeBackend(
            model=self.session.model,
            working_dir=str(self.working_dir),
            session_id=None if fresh else self.session.session_id,
            system_prompt=base,
        )
        parser = StreamParser()
        self._interrupted = False
        had_output = False
        thinking_shown = False
        tools_used = set()

        is_main = threading.current_thread() is threading.main_thread()
        original_sigint = None
        if is_main:
            original_sigint = signal.getsignal(signal.SIGINT)

            def on_interrupt(sig, frame):
                self._interrupted = True
                if self.backend:
                    self.backend.kill()

            signal.signal(signal.SIGINT, on_interrupt)

        try:
            for line in self.backend.send(message):
                if self._interrupted:
                    break

                for evt, data in parser.parse_line(line):
                    if evt == "text":
                        if thinking_shown:
                            self._clear_thinking_line()
                            thinking_shown = False
                        sys.stdout.write(data)
                        sys.stdout.flush()
                        had_output = True

                    elif evt == "thinking":
                        if not thinking_shown:
                            sys.stdout.write(f"{C.DIM}thinking...{C.RESET}")
                            sys.stdout.flush()
                            thinking_shown = True

                    elif evt == "parse_error":
                        if thinking_shown:
                            sys.stdout.write("\r" + " " * 30 + "\r")
                            thinking_shown = False
                        sys.stdout.write(
                            f"{C.YELLOW}stream parse "
                            f"error{C.RESET}\n")
                        sys.stdout.flush()

                    elif evt == "rate_limit":
                        status = data.get("status", "")
                        resets = data.get("resetsAt", "")
                        if status != "allowed":
                            reset_str = ""
                            if resets:
                                try:
                                    from datetime import datetime
                                    dt = datetime.fromtimestamp(resets)
                                    reset_str = f" (resets {dt.strftime('%H:%M')})"
                                except (ValueError, TypeError, OSError):
                                    pass
                            if thinking_shown:
                                sys.stdout.write("\r" + " " * 30 + "\r")
                                thinking_shown = False
                            print(f"{C.YELLOW}Rate limited"
                                  f"{reset_str}{C.RESET}")

                    elif evt == "tool_use":
                        if thinking_shown:
                            sys.stdout.write("\r" + " " * 30 + "\r")
                            thinking_shown = False
                        if had_output:
                            print()
                            had_output = False
                        tools_used.add(data)
                        print(f"  {C.MAGENTA}[{data}]{C.RESET}")

                    elif evt == "result":
                        self._handle_result(data)

        except Exception as e:
            print(f"\n{C.RED}Error: {e}{C.RESET}")

        finally:
            if is_main and original_sigint is not None:
                signal.signal(signal.SIGINT, original_sigint)
            if thinking_shown:
                sys.stdout.write("\r" + " " * 30 + "\r")
            if self._interrupted:
                print(f"\n{C.YELLOW}interrupted{C.RESET}")
            elif had_output:
                print()  # Final newline after text
            self._post_response_hint(tools_used)
            print()  # Blank line before next prompt

    # ── Session integrity ─────────────────────────────────────────────────

    def _on_session_transition(self, old_sid, new_sid):
        """Handle an unexpected session ID change: log it, warn the user, set diverged flag."""
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        entry = {
            "timestamp": ts,
            "old_session_id": old_sid,
            "new_session_id": new_sid,
            "turn": self.session.turn_count,
        }
        self._session_transition_log.append(entry)
        if len(self._session_transition_log) > 100:
            self._session_transition_log = self._session_transition_log[-100:]
        self._pending_session_id = new_sid  # Hold new ID until user confirms
        self._session_diverged = True
        self._write_transition_log(entry)

        # Immediate visible warning (printed mid-stream before the result line)
        print(f"\n{C.RED}{C.BOLD}⚠  SESSION ID CHANGED{C.RESET}")
        print(f"  {C.RED}Previous: ...{old_sid[-16:]}{C.RESET}")
        print(f"  {C.RED}New:      ...{new_sid[-16:]}{C.RESET}")
        print(f"  {C.YELLOW}Context from turns 1–{self.session.turn_count} "
              f"may be lost (network hiccup or session expiry).{C.RESET}")
        print(f"  {C.DIM}Transition logged to .deep/session_transitions.log{C.RESET}")

    def _write_transition_log(self, entry):
        """Append a session transition record to .deep/session_transitions.log."""
        try:
            deep_dir = self.working_dir / ".deep"
            deep_dir.mkdir(parents=True, exist_ok=True)
            log_path = deep_dir / "session_transitions.log"
            with open(log_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry) + "\n")
        except OSError:
            pass  # Non-fatal: log write failure should not break the REPL

    def _confirm_session_diverged(self):
        """Gate for session-diverged state: warn and require explicit user acknowledgment.

        Returns True to proceed, False to abort the pending send.
        Clears the diverged flag on acknowledgment so the gate fires only once per
        transition unless another divergence occurs.
        """
        transitions = len(self._session_transition_log)
        print(f"\n{C.RED}{C.BOLD}⚠  SESSION CONTEXT DIVERGED{C.RESET}")
        print(f"  {C.YELLOW}{transitions} session transition(s) detected "
              f"since turn {self._session_transition_log[0]['turn'] if transitions else '?'}.{C.RESET}")
        print(f"  {C.YELLOW}Claude may not remember your earlier turns.{C.RESET}")
        print(f"  {C.DIM}Options: /clear to start fresh | "
              f"/load <name> to restore a saved checkpoint{C.RESET}")
        try:
            ack = input(
                f"  {C.GREEN}Continue in diverged context? [y/N]:{C.RESET} "
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return False
        if ack == "y":
            # Apply pending session ID now that user has confirmed
            if hasattr(self, '_pending_session_id') and self._pending_session_id:
                self.session.session_id = self._pending_session_id
                self._pending_session_id = None
            self._session_diverged = False  # Cleared — user explicitly acknowledged
            self._session_transition_log = []  # Reset log so count doesn't accumulate
            print(f"  {C.DIM}Continuing. Consider /save to checkpoint the current session.{C.RESET}\n")
            return True
        print(f"  {C.YELLOW}Aborted. Use /clear or /load to restore context.{C.RESET}\n")
        return False

    def _handle_result(self, data):
        """Extract session_id, usage, and cost from the result event.

        Detects session ID changes (old non-None → new different non-None) that
        indicate a reconnect or network hiccup, and triggers the divergence workflow.
        """
        sid = data.get("session_id")
        if sid:
            old_sid = self.session.session_id
            if old_sid and sid != old_sid:
                # Session ID changed mid-conversation — context may be lost
                self._on_session_transition(old_sid, sid)
            else:
                # Only update session ID if no divergence detected — user must confirm first
                self.session.session_id = sid

        usage = data.get("usage", {})
        cost = data.get("total_cost_usd", data.get("cost_usd", 0))

        # Guard: Protect compound assignment operations with lock — += is not atomic
        with self._session_lock:
            self.session.total_input_tokens += usage.get("input_tokens", 0)
            self.session.total_output_tokens += usage.get("output_tokens", 0)
            if isinstance(cost, (int, float)):
                self.session.total_cost_usd += cost
            self.session.turn_count += 1


# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Prism - structural analysis through cognitive prisms",
    )
    ap.add_argument("-m", "--model", default="sonnet",
                    choices=["haiku", "sonnet", "opus"],
                    help="model (default: sonnet; use haiku for ~5x cheaper)")
    ap.add_argument("-d", "--dir", default=".",
                    help="working directory (default: cwd)")
    ap.add_argument("-r", "--resume", default=None, metavar="SESSION",
                    help="resume a saved session")
    ap.add_argument("--review", default=None, metavar="PATH",
                    help="non-interactive review: run prisms, output report")
    ap.add_argument("--cook", default=None, nargs="?", const="__pipe__",
                    metavar="MESSAGE",
                    help="cook a prism for a message (non-interactive)")
    ap.add_argument("--solve", default=None, nargs="?", const="__pipe__",
                    metavar="MESSAGE",
                    help="cook + solve through prism (non-interactive)")
    ap.add_argument("--vanilla", default=None, nargs="?",
                    const="__pipe__", metavar="MESSAGE",
                    help="solve without cooking (baseline)")
    ap.add_argument("--isolate", action="store_true",
                    help="ignore project context (CLAUDE.md, .deep/), "
                         "use only piped input")
    ap.add_argument("--scan", default=None, metavar="PATH",
                    help="non-interactive /scan (supports all modes)")
    ap.add_argument("mode", nargs="?", default=None,
                    help="mode for --solve (single/full) or --scan "
                         "(full/discover/nuclear/dfxf/...)")
    ap.add_argument("--context", nargs="*", metavar="FILE",
                    help="include file contents as context")
    ap.add_argument("--extract", action="store_true",
                    help="extract answer from response (integer)")
    ap.add_argument("--use-prism", default=None, metavar="PROMPT",
                    dest="use_prism",
                    help="use pre-cooked prism prompt (skip cooking)")
    ap.add_argument("--prism-file", default=None, metavar="FILE",
                    dest="prism_file",
                    help="use prism from JSON file (output of --cook --json)")
    ap.add_argument("--verify", default=None, metavar="FILE",
                    help="convergence loop: re-cook until output matches "
                    "expected answer from FILE (max 3 iterations)")
    ap.add_argument("--max-verify", default=3, type=int,
                    dest="max_verify", metavar="N",
                    help="max verify iterations (default: 3)")
    ap.add_argument("--calibrate", default=None, nargs="?",
                    const="__pipe__", metavar="MESSAGE",
                    help="classify input and output K-report")
    ap.add_argument("--auto", default=None, nargs="?",
                    const="__pipe__", metavar="MESSAGE",
                    help="calibrate input, auto-route to optimal "
                         "mode and model")
    ap.add_argument("--deep-calibrate", action="store_true",
                    dest="deep_calibrate",
                    help="use deep calibration (strategic analysis "
                         "of input before routing, smarter but "
                         "costs an extra solve call)")
    ap.add_argument("--factory", default=None, metavar="GOAL",
                    help="design a new 3-step prism for GOAL using "
                         "Sonnet (saves to prisms/factory/). "
                         "Use - to pipe the goal from stdin.")
    ap.add_argument("--extract-lens", default=None, nargs="?",
                    const="__pipe__", metavar="FILE",
                    dest="extract_lens",
                    help="extract a reusable 3-step prism from existing "
                         "analysis output (pipe analysis or give FILE). "
                         "Content-driven: distills ops Sonnet actually used.")
    ap.add_argument("--intent", default=None, metavar="GOAL",
                    help="custom analytical direction for cook step "
                         "(same concept as target= in /scan)")
    ap.add_argument("--cooker", default=None, metavar="NAME",
                    help="override cooker template (e.g. simulation, "
                         "archaeology, concealment). Used with target= or 3way.")
    ap.add_argument("--validate", action="store_true",
                    help="post-hoc quality check: score output depth "
                         "and actionability (EVALUATE primitive)")
    ap.add_argument("--models", action="store_true",
                    help="show current model routing: MODEL_MAP, "
                         "COOK_MODEL, OPTIMAL_PRISM_MODEL")
    ap.add_argument("--history", nargs="?", const=20, type=int,
                    default=None, metavar="N",
                    help="show recent session log entries (default: 20)")
    ap.add_argument("--effort", default=None,
                    choices=["low", "medium", "high", "max"],
                    help="reasoning effort level (passed to claude CLI)")
    ap.add_argument("--budget", default=None, type=float, metavar="USD",
                    help="max cost budget for adaptive mode (e.g. --budget 0.10)")
    ap.add_argument("--append-system", action="store_true",
                    dest="append_system",
                    help="append system prompt to built-in (vs replace)")
    ap.add_argument("--pipe", action="store_true",
                    help="read message from stdin")
    ap.add_argument("-o", "--output", default=None, metavar="FILE",
                    help="write output to file (default: stdout)")
    ap.add_argument("--prism", default=None,
                    help="comma-separated prisms for review (default: all)")
    ap.add_argument("--json", action="store_true", dest="json_output",
                    help="output as JSON")
    ap.add_argument("-q", "--quiet", action="store_true",
                    help="skip prompts and confirmations")
    ap.add_argument("--trust", action="store_true",
                    help="oracle mode: 5-phase self-aware analysis "
                         "(depth + typing + correction + reflection + harvest). "
                         "Maximizes trust over impressiveness.")
    ap.add_argument("--explain", action="store_true",
                    help="explain what a scan would do without running it: "
                         "show available modes, prisms, models, and costs")
    ap.add_argument("--provenance", action="store_true",
                    help="post-process: add source attribution per "
                         "finding (source:line_N, derivation, "
                         "external, assumption). Uses Haiku.")
    ap.add_argument("--confidence", action="store_true",
                    help="post-process: tag claims by specificity → "
                         "estimated confidence (HIGH/MED/LOW/UNVERIFIED). "
                         "Uses Haiku, ~$0.002 extra.")
    ap.add_argument("--depth", default=None,
                    choices=["shallow", "standard", "deep", "exhaustive"],
                    help="aspiration level: shallow (quick list), "
                         "standard (L12), deep (L12-G self-correcting), "
                         "exhaustive (verified pipeline)")
    args = ap.parse_args()

    # ── Resolve working directory (--isolate uses temp dir) ──────────
    if getattr(args, "isolate", False):
        import tempfile as _tf
        _isolate_dir = _tf.mkdtemp(prefix="prism_isolate_")
        args.dir = _isolate_dir
    _working_dir = pathlib.Path(args.dir).resolve()

    # ── --history: show session log ─────────────────────────────────
    if args.history is not None:
        _log = SessionLog(args.dir)
        print(_log.summary(limit=args.history))
        sys.exit(0)

    # ── --models: show current model routing ─────────────────────
    if getattr(args, 'models', False):
        config_path = pathlib.Path.home() / ".prism" / "models.json"
        config_note = (f"  config: {config_path}"
                       if config_path.exists()
                       else f"  config: (none — create {config_path} to override)")
        print("MODEL ROUTING")
        print(config_note)
        for name in ("haiku", "sonnet", "opus"):
            default = _DEFAULT_MODEL_MAP.get(name, "?")
            current = MODEL_MAP.get(name, "?")
            marker = " (overridden)" if current != default else ""
            print(f"  {name:8s} → {current}{marker}")
        print(f"  cook     → {COOK_MODEL}")
        print(f"  default  → {args.model}")
        print()
        print(f"OPTIMAL PRISM MODELS ({len(OPTIMAL_PRISM_MODEL)} prisms)")
        by_model = {}
        for prism, model in sorted(OPTIMAL_PRISM_MODEL.items()):
            by_model.setdefault(model, []).append(prism)
        for model in ("sonnet", "opus", "haiku"):
            prisms = by_model.get(model, [])
            if prisms:
                print(f"  {model} ({len(prisms)}): {', '.join(prisms)}")
        sys.exit(0)

    # ── Shared helpers ───────────────────────────────────────────────

    def _build_message(base, context_files=None):
        """Append --context file contents to the message."""
        msg = base
        if context_files:
            for fpath in context_files:
                p = pathlib.Path(fpath)
                if p.exists():
                    content = p.read_text(encoding="utf-8",
                                          errors="replace")
                    msg += (f"\n\n<file path=\"{p}\">"
                            f"\n{content}\n</file>")
                else:
                    print(f"Warning: {fpath} not found, skipping",
                          file=sys.stderr)
        return msg

    def _save_cli_finding(working_dir, label, prism_name, output):
        """Save a finding from CLI mode to .deep/findings/.

        Mirrors PrismREPL._save_deep_finding for non-interactive paths.
        """
        if not output or len(output.strip()) < 50:
            return
        slug = re.sub(r'[^a-z0-9]+', '_', label.lower()).strip('_')[:80]
        findings_dir = pathlib.Path(working_dir) / ".deep" / "findings"
        findings_dir.mkdir(parents=True, exist_ok=True)
        findings_path = findings_dir / f"{slug}.md"

        section_header = f"## {prism_name.upper()}"
        new_section = f"{section_header}\n\n{output.strip()}\n\n"

        if findings_path.exists():
            existing = findings_path.read_text(encoding="utf-8")
            pattern = rf'## {re.escape(prism_name.upper())}\s*\n.*?(?=\n## |\Z)'
            if re.search(pattern, existing, re.DOTALL):
                updated = re.sub(pattern, new_section.strip(), existing,
                                 count=1, flags=re.DOTALL)
            else:
                updated = existing.rstrip() + "\n\n" + new_section
            findings_path.write_text(updated, encoding="utf-8")
        else:
            findings_path.write_text(
                f"# Findings: {label}\n\n{new_section}",
                encoding="utf-8")

    def _read_pipe():
        """Read message from stdin (for --pipe)."""
        if sys.stdin.isatty():
            print("Error: --pipe requires piped input",
                  file=sys.stderr)
            sys.exit(1)
        text = sys.stdin.read().strip()
        # Windows stdin can produce surrogate characters — clean them
        return text.encode("utf-8", errors="replace").decode("utf-8")

    def _parse_prism_json(raw):
        """Parse a single prism {name, prompt} from model output."""
        if not raw or raw.startswith("[Error"):
            return None
        cleaned = re.sub(r'^```(?:json)?\s*', '', raw,
                         flags=re.MULTILINE)
        cleaned = re.sub(r'^```\s*$', '', cleaned,
                         flags=re.MULTILINE).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            m = re.search(r'\{[^{}]*"prompt"[^{}]*\}', cleaned,
                          re.DOTALL)
            if m:
                try:
                    return json.loads(m.group())
                except json.JSONDecodeError:
                    pass
        return None

    def _validate_sdl_lens(prompt_text):
        """Validate a factory-generated SDL lens for structural correctness.

        Returns (is_valid: bool, issues: list[str]).

        Checks:
        - First line is the canonical opener
        - Exactly 3 ## Step sections
        - Word count in 80-260 range
        """
        issues = []
        lines = prompt_text.strip().split("\n")
        first_line = lines[0].strip() if lines else ""
        if not first_line.startswith("Execute every step below"):
            issues.append(
                f"missing opener — first line is: '{first_line[:60]}'")
        steps = re.findall(r"^## Step", prompt_text, re.MULTILINE)
        if len(steps) != 3:
            issues.append(
                f"expected 3 ## Step sections, found {len(steps)}")
        word_count = len(prompt_text.split())
        if word_count < 80:
            issues.append(
                f"too short ({word_count} words, minimum 80)")
        elif word_count > 260:
            issues.append(
                f"too long ({word_count} words, maximum 260)")
        return len(issues) == 0, issues

    def _parse_pipeline_json(raw):
        """Parse a pipeline [{name, prompt, role}, ...] from output."""
        if not raw or raw.startswith("[Error"):
            return []
        cleaned = re.sub(r'^```(?:json)?\s*', '', raw,
                         flags=re.MULTILINE)
        cleaned = re.sub(r'^```\s*$', '', cleaned,
                         flags=re.MULTILINE).strip()
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            parsed = None
            for pat in (r'\[.*\]', r'\[.*?\]'):
                m = re.search(pat, cleaned, re.DOTALL)
                if m:
                    try:
                        parsed = json.loads(m.group())
                        break
                    except json.JSONDecodeError:
                        continue
            if parsed is None:
                return []
        if not isinstance(parsed, list):
            return []
        prisms = []
        for item in parsed:
            text = item.get("prompt", "")
            role = item.get("role", item.get("name", "pass"))
            name = item.get("name", role)
            if text:
                prisms.append({"prompt": text, "role": role,
                               "name": name})
        return prisms

    def _parse_calibrate_output(raw):
        """Parse calibrate K-report JSON. Returns dict with defaults on failure."""
        defaults = {
            "content_type": "unknown",
            "domain": "unknown",
            "structural_density": "medium",
            "novelty": "medium",
            "k_estimate": 0.5,
            "recommended_mode": "solve",
            "recommended_model": "haiku",
            "rationale": "calibrate parse failed, defaulting to single solve",
        }
        if not raw or raw.startswith("[Error"):
            return defaults
        # Try parsing JSON (direct, code block, or brace extraction)
        for candidate in [
            raw.strip(),
            re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE).strip(),
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
        # Extract first JSON object from text
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

    def _extract_answer(text):
        """Extract integer answer (0-999) from response text."""
        if not text:
            return None
        for p in [r'answer is[:\s]*\**\s*(\d+)',
                  r'boxed.(\d+).',
                  r'\*\*(\d+)\*\*\s*$']:
            m = re.search(p, text, re.I | re.M)
            if m:
                val = int(m.group(1))
                if 0 <= val <= 999:
                    return val
        nums = re.findall(r'\b(\d+)\b', text)
        if nums:
            val = int(nums[-1])
            if 0 <= val <= 999:
                return val
        return None

    def _output(result, response_text, args):
        """Handle output: --json, --extract, or plain text."""
        if args.extract:
            extracted = _extract_answer(response_text)
            if args.json_output:
                result["extracted"] = extracted
                print(json.dumps(result, ensure_ascii=False), flush=True)
            else:
                print(extracted if extracted is not None else "null",
                      flush=True)
        elif args.json_output:
            print(json.dumps(result, ensure_ascii=False), flush=True)
        else:
            print(response_text, flush=True)

    # ── Shared: session history context for calibrate ─────────────
    def _session_context():
        """Load session log summary for calibrate (informational only)."""
        log = SessionLog(args.dir)
        summary = log.summary(limit=10)
        if summary == "  (no operations logged)":
            return ""
        return (f"\n\n<exploration_history>\n"
                f"Previous operations in this project "
                f"(informational only — do NOT change your routing "
                f"based on this, just be aware of what was explored):\n"
                f"{summary}\n"
                f"</exploration_history>")

    # ── --calibrate: classify input and output K-report ─────────────
    if args.calibrate is not None:
        claude = ClaudeInterface(_working_dir, effort=getattr(args, 'effort', None))
        message = args.calibrate if args.calibrate != "__pipe__" else None
        if not message:
            message = _read_pipe()
        message = _build_message(message, args.context)
        message += _session_context()

        _cal_deep = getattr(args, "deep_calibrate", False)
        _cal_prompt = (CALIBRATE_DEEP_PROMPT if _cal_deep
                       else CALIBRATE_PROMPT)
        _cal_model = "sonnet" if _cal_deep else "haiku"
        _cal_label = ("deep calibrating" if _cal_deep
                      else "calibrating")

        if not args.json_output:
            print(f"{_cal_label}...", end="", flush=True,
                  file=sys.stderr)

        cal_response = claude.call(
            _cal_prompt, message[:30000],
            model=_cal_model, timeout=180)
        k_report = _parse_calibrate_output(cal_response)

        if not args.json_output:
            print(" done", file=sys.stderr)

        if args.json_output:
            print(json.dumps(k_report, indent=2))
        else:
            # Show strategic analysis if deep calibrate
            analysis = k_report.get("analysis")
            if analysis:
                print(f"analysis: {analysis}")
            ct = k_report.get("content_type", "?")
            domain = k_report.get("domain", "?")
            density = k_report.get("structural_density", "?")
            novelty = k_report.get("novelty", "?")
            k = k_report.get("k_estimate", "?")
            mode = k_report.get("recommended_mode", "solve")
            model = k_report.get("recommended_model", "haiku")
            rationale = k_report.get("rationale", "")
            strategy = k_report.get("strategy", {})
            print(f"content:  {ct} ({domain})")
            print(f"density:  {density}   novelty: {novelty}"
                  f"   K: {k}")
            print(f"\u2192 mode:   {mode}")
            print(f"\u2192 model:  {model}")
            if strategy:
                hints = []
                runs = strategy.get("parallel_runs", 1)
                if runs and runs > 1:
                    hints.append(f"pass@{runs}")
                if strategy.get("use_vps"):
                    hints.append("use VPS")
                cook = strategy.get("cook_model")
                if cook and cook != "haiku":
                    hints.append(f"cook with {cook}")
                lens = strategy.get("existing_lens")
                if lens:
                    hints.append(f"lens: {lens}")
                # Suggest factory when no existing lens + high novelty
                if not lens and novelty == "high":
                    hints.append(
                        "new lens: --factory \"<goal>\"")
                if hints:
                    print(f"\u2192 strategy: {', '.join(hints)}")
            if rationale:
                print(f"\u2192 reason: {rationale}")

        # TRACK: log calibrate operation
        _log = SessionLog(args.dir)
        _log.append(
            operation="calibrate",
            model=_cal_model,
            k_report=k_report,
            cost_estimate=claude.last_cost,
        )
        sys.exit(0)

    # ── --auto: calibrate → route → execute ──────────────────────────
    if args.auto is not None:
        claude_cal = ClaudeInterface(_working_dir)
        auto_msg = args.auto if args.auto != "__pipe__" else None
        if not auto_msg:
            auto_msg = _read_pipe()
        auto_msg = _build_message(auto_msg, args.context)

        _cal_deep = getattr(args, "deep_calibrate", False)
        _cal_prompt = (CALIBRATE_DEEP_PROMPT if _cal_deep
                       else CALIBRATE_PROMPT)
        _cal_model = "sonnet" if _cal_deep else "haiku"
        _cal_label = ("deep calibrating" if _cal_deep
                      else "calibrating")

        if not args.json_output:
            print(f"{_cal_label}...", end="", flush=True,
                  file=sys.stderr)

        _cal_msg = auto_msg + _session_context()
        cal_response = claude_cal.call(
            _cal_prompt, _cal_msg[:30000],
            model=_cal_model, timeout=180)
        k_report = _parse_calibrate_output(cal_response)

        rec_mode = k_report.get("recommended_mode", "solve")
        rec_model = k_report.get("recommended_model", "haiku")

        # User -m flag overrides calibrate recommendation
        _model_explicitly_set = any(
            a in sys.argv for a in ["-m", "--model"])
        if not _model_explicitly_set:
            args.model = rec_model

        if not args.json_output:
            ct = k_report.get("content_type", "?")
            domain = k_report.get("domain", "?")
            k = k_report.get("k_estimate", "?")
            strategy = k_report.get("strategy", {})
            hints = []
            runs = strategy.get("parallel_runs", 1)
            if runs and runs > 1:
                hints.append(f"pass@{runs}")
            if strategy.get("use_vps"):
                hints.append("VPS")
            cook = strategy.get("cook_model")
            if cook and cook != "haiku":
                hints.append(f"cook:{cook}")
            lens = strategy.get("existing_lens")
            if lens:
                hints.append(f"lens:{lens}")
            custom = strategy.get("custom_intent")
            if custom:
                hints.append("custom intent")
            hint_str = (" [" + ", ".join(hints) + "]"
                        if hints else "")
            print(f" {ct}/{domain} K={k} \u2192 {rec_mode} "
                  f"({args.model}){hint_str}", file=sys.stderr)
            # Show strategic analysis if deep calibrate
            analysis = k_report.get("analysis")
            if analysis:
                print(f"  analysis: {analysis}",
                      file=sys.stderr)

        # TRACK: log auto-calibrate operation
        _log = SessionLog(args.dir)
        _log.append(
            operation="auto",
            model=_cal_model,
            k_report=k_report,
            cost_estimate=claude_cal.last_cost,
        )

        # Store K-report for output enrichment
        args._k_report = k_report
        # Prevent double-appending context
        args.context = None
        # Mark as auto-provided to skip mode reinterpretation
        args._auto_provided = True

        # Route to appropriate handler
        if rec_mode == "vanilla":
            args.vanilla = auto_msg
            # Fall through to vanilla handler
        else:
            args.solve = auto_msg
            args.mode = ("full" if rec_mode == "solve_full"
                         else "single")
            # Pass custom intent from deep calibrate
            # to the solve handler's cook step
            custom_intent = (k_report.get("strategy", {})
                             .get("custom_intent"))
            if custom_intent:
                args._custom_intent = custom_intent
            # Wire cook_model hint — use different model for cooking
            # Validate against known models to prevent unexpected costs
            _cook_model = (k_report.get("strategy", {})
                           .get("cook_model"))
            if _cook_model and _cook_model in MODEL_MAP:
                args._cook_model = _cook_model
            # Wire existing_lens hint — skip cooking, use file
            # Security: only allow paths under prisms/ directory
            _lens = (k_report.get("strategy", {})
                     .get("existing_lens"))
            if _lens and not args.prism_file and not args.use_prism:
                # Strip path separators — lens must be a simple filename
                _lens_clean = pathlib.Path(_lens).name
                if _lens_clean:
                    lp = _working_dir / "prisms" / _lens_clean
                    if (lp.exists()
                            and lp.resolve().is_relative_to(
                                (_working_dir / "prisms").resolve())):
                        args.prism_file = str(lp)
            # Fall through to solve handler

    # ── --cook: atomic prism cooking ──────────────────────────────────
    if args.cook is not None:
        claude = ClaudeInterface(_working_dir, effort=getattr(args, 'effort', None))
        message = args.cook if args.cook != "__pipe__" else None
        if not message:
            message = _read_pipe()
        if not message:
            print("Error: no message provided", file=sys.stderr)
            sys.exit(1)
        message = _build_message(message, args.context)

        cook_prompt = COOK_UNIVERSAL.format(
            intent="analyze this deeply — find hidden assumptions "
            "and structural properties")
        raw = claude.call(cook_prompt, message[:30000],
                          model=args.model, timeout=300,
                          append_system=getattr(args, 'append_system', False))

        parsed = _parse_prism_json(raw)
        if parsed and parsed.get("prompt"):
            if args.json_output:
                print(json.dumps(parsed, ensure_ascii=False))
            else:
                print(f"Prism: {parsed.get('name', 'cooked')}")
                print(f"Prompt: {parsed['prompt']}")
        else:
            print("Cook failed — no prism generated", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)

    # ── --factory: design a new 3-step SDL lens ───────────────────────
    if getattr(args, "factory", None) is not None:
        goal = args.factory.strip()
        if not goal or goal == "-":
            goal = _read_pipe().strip()
        if not goal:
            print("Error: --factory requires a GOAL string",
                  file=sys.stderr)
            sys.exit(1)

        # Load SDL reference text (strip YAML frontmatter)
        sdl_path = PRISM_DIR / "deep_scan.md"
        if sdl_path.exists():
            sdl_raw = sdl_path.read_text(encoding="utf-8")
            if sdl_raw.startswith("---"):
                end = sdl_raw.find("---", 3)
                sdl_text = (sdl_raw[end + 3:].lstrip("\n")
                            if end > 0 else sdl_raw)
            else:
                sdl_text = sdl_raw
        else:
            sdl_text = ("(SDL reference not found — "
                        "design from first principles)")

        # Build portfolio constraint — tell Sonnet what's already covered
        portfolio_names = [
            p.stem for p in PRISM_DIR.glob("*.md")
            if not p.stem.startswith("l12")
        ]
        if portfolio_names:
            portfolio_constraint = (
                "8. Your lens MUST also find something DIFFERENT from "
                "these existing portfolio prisms: "
                f"{', '.join(portfolio_names)}. "
                "Each prism in the portfolio covers a distinct structural "
                "property — yours must add a genuinely new angle.\n"
            )
        else:
            portfolio_constraint = ""

        # Analysis-first mode: Sonnet performs the analysis SDL cannot (PART 1),
        # then encodes what it just did as a lens (PART 2). Lens is a byproduct.
        # Origin: SDL was generated when Sonnet did extended L12 analysis, NOT when
        # asked to "design a lens." Replicating that structure here.
        # With SDL example (.deep/sdl_example.txt): calibrated to actual SDL output gaps.
        # Without SDL example: falls back to goal-spec analysis (same 2-part structure).
        sdl_example_path = _working_dir / ".deep" / "sdl_example.txt"
        sdl_output = ""
        if sdl_example_path.exists():
            sdl_output = sdl_example_path.read_text(encoding="utf-8").strip()

        if sdl_output:
            factory_template = COOK_SDL_FACTORY
            factory_mode = "analysis_first"
        else:
            factory_template = COOK_SDL_FACTORY_GOAL
            factory_mode = "analysis_fallback"

        if not args.json_output:
            mode_label = ("analysis-first/calibrated" if factory_mode == "analysis_first"
                          else "analysis-fallback (run SDL first for calibrated mode)")
            print(f"designing prism [{mode_label}]: {goal[:50]}...",
                  end="", flush=True, file=sys.stderr)

        # Use str.replace to avoid KeyError on { } in dynamic values
        cook_prompt = (factory_template
                       .replace("{sdl_reference}", sdl_text)
                       .replace("{sdl_output}", sdl_output)
                       .replace("{goal}", goal)
                       .replace("{portfolio_constraint}",
                                portfolio_constraint))
        claude = ClaudeInterface(_working_dir, effort=getattr(args, 'effort', None))
        raw = claude.call(cook_prompt, goal,
                          model="sonnet", timeout=300)
        parsed = _parse_prism_json(raw)

        if not parsed or not parsed.get("prompt"):
            if not args.json_output:
                print(" failed", file=sys.stderr)
                print(f"Raw output:\n{raw[:500]}",
                      file=sys.stderr)
            else:
                print(json.dumps(
                    {"error": "factory failed", "raw": raw[:500]}))
            sys.exit(1)

        lens_name = re.sub(
            r"[^\w]", "_",
            parsed.get("name", "factory_lens")).strip("_")
        lens_text = parsed["prompt"].strip()

        # Compress stage: if design step produced >220 words, compress separately.
        # Separating design from compression lets each be optimized independently.
        if len(lens_text.split()) > 220:
            if not args.json_output:
                print(f"\n  compressing ({len(lens_text.split())}w → target 180w)...",
                      end="", flush=True, file=sys.stderr)
            compress_prompt = (COMPRESS_LENS
                               .replace("{name}", lens_name)
                               .replace("{lens_text}", lens_text))
            raw2 = claude.call(compress_prompt, lens_text,
                               model="sonnet", timeout=120)
            parsed2 = _parse_prism_json(raw2)
            if parsed2 and parsed2.get("prompt"):
                lens_text = parsed2["prompt"].strip()
                if not args.json_output:
                    print(f" {len(lens_text.split())}w", file=sys.stderr)

        is_valid, issues = _validate_sdl_lens(lens_text)
        word_count = len(lens_text.split())
        # Carry over B3 metadata fields if present
        if factory_mode == "b3":
            parsed["operation"] = parsed.get("operation", "")
            parsed["blind_spot"] = parsed.get("blind_spot", "")

        # Save to prisms/factory/
        factory_dir = PRISM_DIR / "factory"
        factory_dir.mkdir(exist_ok=True)
        today = time.strftime("%Y-%m-%d")
        goal_yaml = goal.replace('"', "'").replace("\n", " ")[:120]
        blind_spot_yaml = (parsed.get("blind_spot", "")
                           .replace('"', "'").replace("\n", " ")[:120])
        mode_note = (f"B3 blind-spot mode. blind_spot: {blind_spot_yaml}"
                     if factory_mode == "b3"
                     else "goal-spec mode (no SDL example available)")
        metadata = (
            f"---\n"
            f"calibration_date: {today}\n"
            f"model_versions: [\"{MODEL_MAP.get('sonnet', 'claude-sonnet-4-6')}\"]\n"
            f"quality_baseline: null\n"
            f"origin: \"factory:{factory_mode} — goal: {goal_yaml}\"\n"
            f"notes: \"{mode_note}. "
            f"{word_count}w, 3-step. Validate before production use.\"\n"
            f"validation_passed: "
            f"{'true' if is_valid else 'false'}\n"
            f"---\n"
        )
        save_path = factory_dir / f"{lens_name}.md"
        save_path.write_text(
            metadata + lens_text + "\n", encoding="utf-8")

        if args.json_output:
            print(json.dumps({
                **parsed,
                "name": lens_name,
                "factory_mode": factory_mode,
                "saved_to": str(save_path),
                "valid": is_valid,
                "issues": issues,
                "word_count": word_count,
            }, indent=2, ensure_ascii=False))
        else:
            print(" done", file=sys.stderr)
            if factory_mode == "analysis_first":
                op = parsed.get("operation", "")
                bs = parsed.get("blind_spot", "")
                if op:
                    print(f"base finds:  {op[:80]}")
                if bs:
                    print(f"found gap:   {bs[:80]}")
            print(f"prism:       factory/{lens_name}")
            print(f"words:       {word_count}  |  valid: {is_valid}")
            if issues:
                for iss in issues:
                    print(f"  \u26a0  {iss}")
            print(f"saved:       prisms/factory/{lens_name}.md")
            print(f"\nUse it:      --use-prism 'factory/{lens_name}'")
            if factory_mode == "analysis_fallback":
                print(f"\nTip: save a scan output to .deep/sdl_example.txt "
                      f"for calibrated (analysis-first) mode on next run")

        # TRACK: log factory operation
        _log = SessionLog(args.dir)
        _log.append(
            operation="factory",
            model="sonnet",
            lens_name=lens_name,
            goal=goal,
            valid=is_valid,
            word_count=word_count,
        )
        sys.exit(0)

    # ── --extract-lens: content-driven lens discovery ─────────────────
    # Distills a reusable 3-step lens from an existing analysis output.
    # Content-driven counterpart to --factory (goal-driven).
    # Operations extracted are ones Sonnet ACTUALLY used — not designed.
    if getattr(args, "extract_lens", None) is not None:
        src = args.extract_lens
        if src == "__pipe__":
            analysis_text = _read_pipe().strip()
        else:
            p = pathlib.Path(src)
            if not p.exists():
                print(f"Error: file not found: {src}",
                      file=sys.stderr)
                sys.exit(1)
            analysis_text = p.read_text(encoding="utf-8").strip()
        if not analysis_text:
            print("Error: --extract-lens requires analysis input (pipe or give FILE)",
                  file=sys.stderr)
            sys.exit(1)

        portfolio_names = [
            p.stem for p in PRISM_DIR.glob("*.md")
            if not p.stem.startswith("l12")
        ]
        portfolio_constraint = ""
        if portfolio_names:
            portfolio_constraint = (
                "8. Your lens MUST also find something DIFFERENT from "
                "these existing portfolio prisms: "
                f"{', '.join(portfolio_names)}. "
                "Each covers a distinct structural property — "
                "yours must add a genuinely new angle.\n"
            )
        cook_prompt = (COOK_LENS_DISCOVER
                       .replace("{portfolio_constraint}",
                                portfolio_constraint)
                       .replace("{analysis}", analysis_text[:20000]))
        claude = ClaudeInterface(_working_dir, effort=getattr(args, 'effort', None))

        if not args.json_output:
            preview = analysis_text[:60].replace("\n", " ")
            print(f"extracting prism from: {preview}...",
                  end="", flush=True, file=sys.stderr)

        raw = claude.call(cook_prompt, analysis_text[:20000],
                          model="sonnet", timeout=300)
        parsed = _parse_prism_json(raw)

        if not parsed or not parsed.get("prompt"):
            if not args.json_output:
                print(" failed", file=sys.stderr)
                print(f"Raw output:\n{raw[:500]}", file=sys.stderr)
            else:
                print(json.dumps(
                    {"error": "extract failed", "raw": raw[:500]}))
            sys.exit(1)

        lens_name = re.sub(
            r"[^\w]", "_",
            parsed.get("name", "extracted_lens")).strip("_")
        lens_text = parsed["prompt"].strip()
        is_valid, issues = _validate_sdl_lens(lens_text)
        word_count = len(lens_text.split())

        # Content-driven lenses save to prisms/factory/extracted/
        # to distinguish from goal-driven factory lenses.
        # Validated ones can be promoted to prisms/ manually.
        extracted_dir = PRISM_DIR / "factory" / "extracted"
        extracted_dir.mkdir(parents=True, exist_ok=True)
        today = time.strftime("%Y-%m-%d")
        src_label = (pathlib.Path(src).name
                     if src != "__pipe__" else "stdin")
        metadata = (
            f"---\n"
            f"calibration_date: {today}\n"
            f"model_versions: [\"{MODEL_MAP.get('sonnet', 'claude-sonnet-4-6')}\"]\n"
            f"quality_baseline: null\n"
            f"origin: \"extract:sonnet — source: {src_label}\"\n"
            f"notes: \"Content-driven extraction. {word_count}w, "
            f"3-step. Ops distilled from actual Sonnet analysis. "
            f"Validate on Haiku before promoting to prisms/.\"\n"
            f"validation_passed: "
            f"{'true' if is_valid else 'false'}\n"
            f"---\n"
        )
        save_path = extracted_dir / f"{lens_name}.md"
        save_path.write_text(
            metadata + lens_text + "\n", encoding="utf-8")

        if args.json_output:
            print(json.dumps({
                **parsed,
                "name": lens_name,
                "saved_to": str(save_path),
                "valid": is_valid,
                "issues": issues,
                "word_count": word_count,
                "origin": "content-driven extraction",
            }, indent=2, ensure_ascii=False))
        else:
            print(" done", file=sys.stderr)
            print(f"prism:    factory/extracted/{lens_name}")
            print(f"words:    {word_count}  |  valid: {is_valid}")
            if issues:
                for iss in issues:
                    print(f"  \u26a0  {iss}")
            print(f"saved:    prisms/factory/extracted/{lens_name}.md")
            print(f"\nValidate: cat target.py | python prism.py --solve "
                  f"--use-prism 'factory/extracted/{lens_name}' -m haiku")
            print(f"Promote:  mv prisms/factory/extracted/{lens_name}.md"
                  f" prisms/{lens_name}.md")

        # TRACK: log extract-lens operation
        _log = SessionLog(args.dir)
        _log.append(
            operation="extract_lens",
            model="sonnet",
            lens_name=lens_name,
            source=src_label,
            valid=is_valid,
            word_count=word_count,
        )
        sys.exit(0)

    # ── --vanilla: solve without cooking (baseline) ──────────────────
    if args.vanilla is not None:
        claude = ClaudeInterface(_working_dir, effort=getattr(args, 'effort', None))
        message = args.vanilla if args.vanilla != "__pipe__" else None
        if not message:
            message = _read_pipe()
        message = _build_message(message, args.context)

        response = claude.call(SYSTEM_PROMPT_FALLBACK, message,
                               model=args.model, timeout=300)
        result = {"mode": "vanilla", "response": response}
        if getattr(args, '_k_report', None):
            result["calibrate"] = args._k_report
        _output(result, response, args)
        sys.exit(0)

    # ── --solve: cook + solve (single or full) ───────────────────────
    if args.solve is not None:
        # Wire -o output file (same tee pattern as --scan)
        _solve_outfile = getattr(args, 'output', None)
        _solve_orig_stdout = sys.stdout
        _solve_outf = None
        if _solve_outfile:
            _solve_outf = open(_solve_outfile, "w", encoding="utf-8")

            class _SolveTee:
                def __init__(self, *targets):
                    self._targets = targets
                def write(self, data):
                    for t in self._targets:
                        t.write(data)
                def flush(self):
                    for t in self._targets:
                        t.flush()
                def isatty(self):
                    return False
            sys.stdout = _SolveTee(_solve_orig_stdout, _solve_outf)

        claude = ClaudeInterface(_working_dir, effort=getattr(args, 'effort', None))
        # Handle --solve full / --solve single (argparse grabs mode)
        # Skip reinterpretation when --auto already set the message
        if (args.solve in ("full", "single")
                and not getattr(args, '_auto_provided', False)):
            if not args.mode:
                args.mode = args.solve
            args.solve = "__pipe__"
        message = args.solve if args.solve != "__pipe__" else None
        if not message:
            message = _read_pipe()
        message = _build_message(message, args.context)

        # Wire --intent to _custom_intent (same concept as target= in /scan)
        if getattr(args, 'intent', None) and not getattr(args, '_custom_intent', None):
            args._custom_intent = args.intent

        solve_mode = args.mode or "single"

        # Load verify expected output if --verify given
        verify_expected = None
        if args.verify:
            vf = pathlib.Path(args.verify)
            if not vf.exists():
                print(f"Error: verify file {args.verify} not found",
                      file=sys.stderr)
                sys.exit(1)
            verify_expected = vf.read_text(
                encoding="utf-8").strip()
            if not verify_expected:
                print(f"Error: verify file {args.verify} is empty",
                      file=sys.stderr)
                sys.exit(1)

        # Check for pre-cooked prism
        pre_prism = None
        if args.use_prism:
            # If it's a file path, read the file contents
            _up = pathlib.Path(args.use_prism)
            if _up.exists() and _up.is_file():
                _up_content = _up.read_text(
                    encoding="utf-8", errors="replace")
                # Strip YAML frontmatter if present
                if _up_content.startswith("---"):
                    _end = _up_content.find("---", 3)
                    if _end > 0:
                        _up_content = _up_content[
                            _end + 3:].lstrip("\n")
                pre_prism = {
                    "prompt": _up_content,
                    "name": _up.stem}
            else:
                pre_prism = {
                    "prompt": args.use_prism,
                    "name": "provided"}
        elif args.prism_file:
            lf = pathlib.Path(args.prism_file)
            if not lf.exists():
                print(f"Error: {args.prism_file} not found",
                      file=sys.stderr)
                sys.exit(1)
            try:
                pre_prism = json.loads(
                    lf.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                print(f"Error: invalid JSON in {args.prism_file}",
                      file=sys.stderr)
                sys.exit(1)

        # ── Verify helper: compare response to expected ───────
        def _verify_match(response_text, expected_text):
            """Compare response to expected. Returns (match, details).

            Tries exact match first. If both look like grids
            (multi-line, space-separated numbers), uses cell accuracy.
            """
            if not response_text:
                return False, "empty response"
            resp = response_text.strip()
            exp = expected_text.strip()

            # Exact match
            if resp == exp:
                return True, "exact match"

            # Grid-aware comparison: both multi-line, digits+spaces
            def _parse_grid(text):
                rows = []
                for line in text.strip().split("\n"):
                    line = line.strip()
                    if not line or any(
                            c.isalpha() for c in
                            line.replace("x", "")):
                        continue
                    try:
                        row = [int(x) for x in line.split()]
                        if row and len(row) > 1:
                            rows.append(row)
                    except ValueError:
                        continue
                return rows

            pred_grid = _parse_grid(resp)
            exp_grid = _parse_grid(exp)

            if pred_grid and exp_grid:
                # Cell accuracy
                if pred_grid == exp_grid:
                    return True, "grid exact match"
                c = t = 0
                for i in range(min(len(pred_grid), len(exp_grid))):
                    for j in range(min(len(pred_grid[i]),
                                       len(exp_grid[i]))):
                        t += 1
                        if pred_grid[i][j] == exp_grid[i][j]:
                            c += 1
                t += (abs(len(pred_grid) - len(exp_grid))
                      * (len(exp_grid[0]) if exp_grid else 0))
                acc = c / t if t else 0
                return False, (
                    f"grid mismatch: {acc:.1%} cell accuracy, "
                    f"{len(pred_grid)} rows vs {len(exp_grid)} "
                    f"expected")

            # Line-by-line diff summary
            resp_lines = resp.split("\n")
            exp_lines = exp.split("\n")
            diff_count = 0
            for i in range(min(len(resp_lines), len(exp_lines))):
                if resp_lines[i] != exp_lines[i]:
                    diff_count += 1
            diff_count += abs(len(resp_lines) - len(exp_lines))
            return False, (
                f"text mismatch: {diff_count} lines differ, "
                f"{len(resp_lines)} lines vs {len(exp_lines)} "
                f"expected")

        # ── Classify cook output ─────────────────────────────
        def _classify_cook_output(raw, expected=None):
            """Classify cook output as lens, answer, or empty.

            Returns (kind, data):
              ("lens", parsed_dict) — valid prism JSON
              ("answer", raw_text)  — raw output matches expected
              ("empty", None)       — garbage or unparseable
            """
            parsed = _parse_prism_json(raw)
            if parsed and parsed.get("prompt"):
                return "lens", parsed
            # If we have expected output, check if cook solved directly
            if expected and raw and not raw.startswith("[Error"):
                match, _details = _verify_match(raw, expected)
                if match:
                    return "answer", raw
            return "empty", None

        # ── Determine max iterations ──────────────────────────
        max_verify = args.max_verify if verify_expected else 1

        # Cook model: auto may set _cook_model; else use COOK_MODEL constant
        # (P73: cook model is the dominant pipeline variable)
        _cook_model = getattr(args, '_cook_model', None) or COOK_MODEL

        verify_context = ""  # accumulated error context
        final_result = None
        final_response = ""

        for verify_iter in range(1, max_verify + 1):
            # Reset per-iteration state
            final_response = ""
            final_result = None

            if verify_expected and not args.json_output:
                print(f"--- verify iteration {verify_iter}/"
                      f"{max_verify} ---", file=sys.stderr)

            # Build intent with verify context for re-cooking
            # Use custom intent from deep calibrate if available
            _custom = getattr(args, '_custom_intent', None)
            _solve_intent = (_custom if _custom else
                "respond to this message — find the optimal "
                "approach and execute it")
            _solve_pipeline_intent = (_custom if _custom else
                "respond thoroughly — multiple passes that "
                "deepen, challenge, and synthesize")
            if verify_context:
                _solve_intent += (
                    f". PREVIOUS ATTEMPT FAILED: {verify_context}")
                _solve_pipeline_intent += (
                    f". PREVIOUS ATTEMPT FAILED: {verify_context}")

            if solve_mode == "full":
                # ── Full prism: cook pipeline, chain passes ──────
                if not args.json_output:
                    print("cooking pipeline...", end="",
                          flush=True, file=sys.stderr)
                cook_prompt = COOK_3WAY.format(
                    intent=_solve_pipeline_intent)
                raw = claude.call(cook_prompt, message[:30000],
                                  model=_cook_model, timeout=300)
                prisms = _parse_pipeline_json(raw)

                if len(prisms) < 2:
                    # Pipeline parse failed — classify raw output
                    kind, data = _classify_cook_output(
                        raw, verify_expected)
                    if kind == "answer":
                        # Cook solved directly
                        if not args.json_output:
                            print(" solved directly",
                                  file=sys.stderr)
                        final_response = raw
                        final_result = {
                            "mode": "full",
                            "pipeline": [],
                            "passes": [],
                            "response": raw,
                            "prism_source": "cook_direct",
                        }
                        _save_cli_finding(
                            args.dir, "solve_full",
                            "full_cook_direct", raw)
                        # Skip pipeline — go to verify
                    elif kind == "lens":
                        # Got single lens instead of pipeline —
                        # use it as a single-pass solve
                        if not args.json_output:
                            print(f" single prism: "
                                  f"{data.get('name', 'cooked')}",
                                  file=sys.stderr)
                        resp = claude.call(
                            data["prompt"], message,
                            model=args.model, timeout=300)
                        final_response = resp or ""
                        final_result = {
                            "mode": "full",
                            "pipeline": [data],
                            "passes": [{"role": "single",
                                        "response": resp}],
                            "response": resp,
                            "prism_source": "cooked_single",
                        }
                        if resp and not resp.startswith("[Error"):
                            _save_cli_finding(
                                args.dir, "solve_full",
                                "full_single_fallback", resp)
                    else:
                        if not args.json_output:
                            print(" failed", file=sys.stderr)
                        if verify_iter == max_verify:
                            print("Pipeline cook failed",
                                  file=sys.stderr)
                            sys.exit(1)
                        verify_context = "pipeline cook failed"
                        continue

                if not final_response:
                    roles = ", ".join(p["role"] for p in prisms)
                    if not args.json_output:
                        print(f" {roles}", file=sys.stderr)

                    # Run chained pipeline
                    completed = []
                    for i, prism in enumerate(prisms):
                        if i == 0:
                            msg = message
                        else:
                            parts = [
                                f"# USER REQUEST\n\n{message}"]
                            for j, (prev_prism, prev_out) in (
                                    enumerate(completed)):
                                prev_role = (
                                    prev_prism["role"].upper())
                                parts.append(
                                    f"# PASS {j + 1}: "
                                    f"{prev_role}"
                                    f"\n\n{prev_out}")
                            msg = "\n\n---\n\n".join(parts)

                        resp = claude.call(prism["prompt"], msg,
                                           model=args.model,
                                           timeout=300)
                        if resp and not resp.startswith("[Error"):
                            completed.append((prism, resp))
                            _save_cli_finding(
                                args.dir, "solve_full",
                                f"full_{prism['name']}", resp)
                            if not args.json_output:
                                print(f"  pass {i + 1}/"
                                      f"{len(prisms)}: "
                                      f"{prism['role']}",
                                      file=sys.stderr)
                        else:
                            if not args.json_output:
                                reason = (
                                    "empty response"
                                    if not resp else
                                    (resp[:120] + "..."
                                     if len(resp) > 120
                                     else resp))
                                print(f"  pass {i + 1}/"
                                      f"{len(prisms)}: "
                                      f"{prism['role']} FAILED "
                                      f"({reason})",
                                      file=sys.stderr)

                    if completed:
                        combined_parts = [
                            "# Full Pipeline (--solve full)\n"]
                        for prism, out in completed:
                            role = prism.get(
                                "role", prism["name"]).upper()
                            combined_parts.append(
                                f"## {role}\n\n{out}")
                        combined = "\n\n".join(combined_parts)
                        _save_cli_finding(
                            args.dir, "solve_full",
                            "full", combined)
                    else:
                        combined = ""

                    final_response = combined
                    final_result = {
                        "mode": "full",
                        "pipeline": [
                            {"name": p["name"],
                             "role": p["role"],
                             "prompt": p["prompt"]}
                            for p in prisms],
                        "passes": [
                            {"role": prism["role"],
                             "response": out}
                            for prism, out in completed],
                        "response": combined,
                    }

            else:
                # ── Single prism: cook 1 prism, solve ─────────────
                if pre_prism and verify_iter == 1:
                    prism_prompt = pre_prism["prompt"]
                    prism_name = pre_prism.get("name", "provided")
                    prism_source = "provided"
                    if not args.json_output:
                        print(f"prism: {prism_name}",
                              file=sys.stderr)
                else:
                    # Detect grid puzzle input → route to ARC cooker
                    _is_arc = _is_grid_puzzle(message)
                    if _is_arc:
                        if not args.json_output:
                            print("grid puzzle detected",
                                  file=sys.stderr)
                        cook_prompt = COOK_ARC.format(
                            intent=_solve_intent)
                        # Parse training pairs for verification
                        _arc_train = _parse_arc_training(message)
                        _arc_max = getattr(args, 'max_verify', 3) or 3
                        # ARC solve with training verify loop
                        _arc_grid, response, _arc_att, _arc_acc = (
                            _arc_solve_with_verify(
                                claude, cook_prompt, message,
                                _arc_train, model=args.model,
                                timeout=300, effort=None,
                                max_attempts=_arc_max,
                                quiet=args.json_output,
                                append_system=getattr(
                                    args, 'append_system', False)))
                        if not args.json_output:
                            print(f"  arc: {_arc_att} attempts, "
                                  f"train={_arc_acc:.0%}",
                                  file=sys.stderr)
                        if response and not response.startswith(
                                "[Error"):
                            _save_cli_finding(
                                args.dir, "solve_single",
                                "single_arc", response)
                        final_response = response
                        final_result = {
                            "mode": "single",
                            "prism_name": "arc_solver",
                            "prism_prompt": cook_prompt,
                            "prism_source": "arc_auto",
                            "response": response,
                            "arc_attempts": _arc_att,
                            "arc_train_acc": _arc_acc,
                        }
                    else:
                        if not args.json_output:
                            print("cooking...", end="", flush=True,
                                  file=sys.stderr)
                        cook_prompt = COOK_UNIVERSAL.format(
                            intent=_solve_intent)
                        raw = claude.call(cook_prompt, message[:30000],
                                          model=_cook_model, timeout=300)

                    if not _is_arc:
                        kind, data = _classify_cook_output(
                            raw, verify_expected)

                    if not _is_arc and kind == "answer":
                        # Cook solved directly — use as answer
                        if not args.json_output:
                            print(" solved directly",
                                  file=sys.stderr)
                        final_response = raw
                        final_result = {
                            "mode": "single",
                            "prism_name": "cook_direct",
                            "prism_prompt": cook_prompt,
                            "prism_source": "cook_direct",
                            "response": raw,
                        }
                        # Skip solve — go straight to verify
                        _save_cli_finding(
                            args.dir, "solve_single",
                            "single_cook_direct", raw)
                        # Jump to verify (continue handles it)

                    elif not _is_arc and kind == "lens":
                        prism_prompt = data["prompt"]
                        prism_name = data.get("name", "cooked")
                        prism_source = "cooked"
                        if not args.json_output:
                            print(f" {prism_name}",
                                  file=sys.stderr)
                    elif not _is_arc:
                        if not args.json_output:
                            print(" failed", file=sys.stderr)
                        print("Cook failed — solving vanilla",
                              file=sys.stderr)
                        prism_prompt = SYSTEM_PROMPT_FALLBACK
                        prism_name = "fallback"
                        prism_source = "fallback"

                # Solve step (skip if cook already answered)
                if not final_response:
                    response = claude.call(prism_prompt, message,
                                           model=args.model,
                                           timeout=300,
                                           append_system=getattr(
                                               args, 'append_system', False))
                    if response and not response.startswith(
                            "[Error"):
                        _save_cli_finding(
                            args.dir, "solve_single",
                            f"single_{prism_name}", response)
                    final_response = response
                    final_result = {
                        "mode": "single",
                        "prism_name": prism_name,
                        "prism_prompt": prism_prompt,
                        "prism_source": prism_source,
                        "response": response,
                    }

            # ── Verify check ──────────────────────────────────
            if not verify_expected:
                break  # no verify — single iteration

            match, details = _verify_match(
                final_response, verify_expected)
            if not args.json_output:
                if match:
                    print(f"  VERIFY: {details}",
                          file=sys.stderr)
                else:
                    print(f"  VERIFY FAILED: {details}",
                          file=sys.stderr)

            if match:
                if final_result:
                    final_result["verify"] = {
                        "match": True,
                        "details": details,
                        "iteration": verify_iter,
                    }
                break

            if verify_iter < max_verify:
                # Accumulate error context for re-cooking
                verify_context = (
                    f"{details}. The model produced:\n"
                    f"{final_response[:1000]}\n"
                    f"Expected:\n{verify_expected[:1000]}")
                # Force re-cooking on next iteration
                pre_prism = None
            else:
                if final_result:
                    final_result["verify"] = {
                        "match": False,
                        "details": details,
                        "iteration": verify_iter,
                    }

        # Output final result — enrich with K-report if from --auto
        if getattr(args, '_k_report', None) and final_result:
            final_result["calibrate"] = args._k_report

        # ── --validate: post-hoc quality score (EVALUATE) ──────
        # Capture solve cost before validate call overwrites last_cost
        _solve_cost = claude.last_cost
        validation = None
        if args.validate and final_response and len(final_response) > 100:
            if not args.json_output:
                print("validating...", end="", flush=True,
                      file=sys.stderr)
            val_raw = claude.call(
                VALIDATE_PROMPT,
                final_response[:10000],
                model="haiku", timeout=60)
            try:
                # Try JSON parse (direct, code-block stripped)
                val_clean = re.sub(r'^```(?:json)?\s*', '', val_raw,
                                   flags=re.MULTILINE)
                val_clean = re.sub(r'^```\s*$', '', val_clean,
                                   flags=re.MULTILINE).strip()
                validation = json.loads(val_clean)
            except (json.JSONDecodeError, TypeError):
                m = re.search(r'\{[^{}]*\}', val_raw or "", re.DOTALL)
                if m:
                    try:
                        validation = json.loads(m.group(0))
                    except json.JSONDecodeError:
                        pass
            if validation and not args.json_output:
                d = validation.get("depth", "?")
                a = validation.get("actionability", "?")
                o = validation.get("overall", "?")
                strongest = validation.get("strongest", "")
                weakest = validation.get("weakest", "")
                print(f" depth={d} action={a} overall={o}",
                      file=sys.stderr)
                if strongest:
                    print(f"  + {strongest}", file=sys.stderr)
                if weakest:
                    print(f"  - {weakest}", file=sys.stderr)
            elif not args.json_output:
                print(" parse failed", file=sys.stderr)

        if validation and final_result:
            final_result["validation"] = validation

        # TRACK: log the solve operation
        _log = SessionLog(args.dir)
        _log.append(
            operation="solve",
            intent=getattr(args, '_custom_intent', None),
            model=args.model,
            mode=solve_mode,
            k_report=getattr(args, '_k_report', None),
            findings_summary=(final_response[:200]
                              if final_response else None),
            cost_estimate=_solve_cost,
        )

        _output(final_result or {}, final_response, args)
        # Clean up -o tee if active
        if _solve_outf:
            sys.stdout = _solve_orig_stdout
            _solve_outf.close()
        sys.exit(0)

    # ── --scan: non-interactive /scan ────────────────────────────────
    if args.scan:
        scan_arg = args.scan
        # --pipe: replace "-" with stdin content for text-mode scan
        if (getattr(args, 'pipe', False)
                and scan_arg.strip().startswith("-")):
            _stdin_text = sys.stdin.read().strip()
            if _stdin_text:
                # Replace leading "-" with quoted stdin content
                scan_arg = (f'"{_stdin_text}"'
                            + scan_arg.strip()[1:])
        # Wire --explain to explain mode (B12)
        if getattr(args, 'explain', False):
            args.mode = "explain"
        # Wire --trust to oracle mode (R-P1)
        if getattr(args, 'trust', False):
            args.mode = "oracle"
        # Wire --depth to scan mode (P2: aspiration level control)
        _depth = getattr(args, 'depth', None)
        if _depth:
            _depth_map = {
                "shallow": None,  # handled separately below
                "standard": None,  # default L12
                "deep": "l12g",
                "exhaustive": "verified",
            }
            _depth_mode = _depth_map.get(_depth)
            if _depth_mode:
                args.mode = _depth_mode
            elif _depth == "shallow":
                # Override system prompt with shallow aspiration
                args.use_prism = (
                    "List the 5 most important structural findings "
                    "about this code. For each, name what it conceals.")
        if args.mode:
            scan_arg += " " + args.mode
        # Wire --intent into target= syntax so it works with --scan
        if getattr(args, 'intent', None) and 'target=' not in scan_arg:
            scan_arg += f' target="{args.intent}"'
        # Wire --budget into budget= syntax for adaptive mode
        if getattr(args, 'budget', None) and 'budget=' not in scan_arg:
            scan_arg += f' budget={args.budget}'
        # Wire --cooker into cooker= syntax
        if getattr(args, 'cooker', None) and 'cooker=' not in scan_arg:
            scan_arg += f' cooker="{args.cooker}"'
        # Wire --use-prism into prism= syntax (or raw prompt override)
        if getattr(args, 'use_prism', None) and 'prism=' not in scan_arg:
            _prism_val = args.use_prism
            # If it looks like a prism name (single token, no spaces/newlines),
            # inject as prism="name" for _parse_scan_args to pick up.
            # Otherwise treat as raw prompt text — store on REPL instance.
            if (len(_prism_val) < 80
                    and '\n' not in _prism_val
                    and ' ' not in _prism_val):
                scan_arg += f' prism="{_prism_val}"'
            else:
                # Full prompt text — use sentinel name; _load_prism checks it
                scan_arg += ' prism="__cli__"'
        repl = PrismREPL(
            model=args.model,
            working_dir=args.dir,
            quiet=True,
            effort=args.effort,
        )
        # Set raw prism prompt if --use-prism contained full text
        if getattr(args, 'use_prism', None):
            _prism_val = args.use_prism
            if not (len(_prism_val) < 80
                    and '\n' not in _prism_val
                    and ' ' not in _prism_val):
                repl._cli_prism_prompt = _prism_val
        # Wire --context: set context files for _cmd_scan to pick up
        if getattr(args, 'context', None):
            repl._cli_context_files = args.context
        # Nuclear uses Opus — warn unless --quiet or non-interactive
        if "nuclear" in scan_arg and not args.quiet:
            if sys.stdin.isatty():
                print("WARNING: nuclear uses Opus model (higher cost)",
                      file=sys.stderr)
                try:
                    ack = input("Continue? [y/N]: ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    sys.exit(1)
                if ack != "y":
                    sys.exit(1)
            else:
                print("WARNING: nuclear uses Opus model (higher cost)",
                      file=sys.stderr)
        # Wire --output: capture stdout to file
        _output_file = getattr(args, 'output', None)
        if _output_file:
            _orig_stdout = sys.stdout
            try:
                _outf = open(_output_file, "w", encoding="utf-8")
                # Tee: write to both file and original stdout
                class _Tee:
                    def __init__(self, *targets):
                        self._targets = targets
                    def write(self, data):
                        for t in self._targets:
                            t.write(data)
                    def flush(self):
                        for t in self._targets:
                            t.flush()
                    # Proxy isatty so streaming doesn't break
                    def isatty(self):
                        return False
                sys.stdout = _Tee(_orig_stdout, _outf)
                repl._cmd_scan(scan_arg)
            finally:
                sys.stdout = _orig_stdout
                _outf.close()
        else:
            repl._cmd_scan(scan_arg)

        # P1: --confidence post-processing
        if getattr(args, 'confidence', False):
            _conf_prompt = (
                "For each claim in the analysis below, append one of "
                "these tags based ONLY on claim type (do NOT verify):\n"
                "[HIGH-CONF] = structural observation derivable from "
                "source (patterns, control flow, architecture)\n"
                "[MED-CONF] = derived conclusion requiring reasoning "
                "(conservation laws, impossibility proofs)\n"
                "[LOW-CONF] = specific factual claim (API names, line "
                "numbers, performance metrics)\n"
                "[UNVERIFIED] = claim about external world (best "
                "practices, deprecation, design intent)\n"
                "Output the analysis with tags appended to each claim.")
            # Find the latest findings file
            _findings_dir = (pathlib.Path(args.dir).resolve()
                             / ".deep" / "findings")
            _latest = None
            if _findings_dir.exists():
                _mds = sorted(_findings_dir.glob("*.md"),
                              key=lambda p: p.stat().st_mtime,
                              reverse=True)
                if _mds:
                    _latest = _mds[0]
            if _latest:
                _text = _latest.read_text(encoding="utf-8",
                                          errors="replace")
                if _text and len(_text) > 100:
                    print(f"\n{C.DIM}Annotating confidence levels..."
                          f"{C.RESET}", file=sys.stderr)
                    _ci = ClaudeInterface(args.dir)
                    _annotated = _ci.call(
                        _conf_prompt, _text[:10000],
                        model="haiku", timeout=60)
                    if _annotated and not _annotated.startswith(
                            "[Error"):
                        # Save annotated version
                        _conf_path = _latest.with_suffix(
                            ".confidence.md")
                        _conf_path.write_text(
                            _annotated, encoding="utf-8")
                        print(f"{C.GREEN}Confidence annotations "
                              f"saved to {_conf_path.name}"
                              f"{C.RESET}", file=sys.stderr)
                        # Print summary
                        _h = _annotated.count("[HIGH-CONF]")
                        _m = _annotated.count("[MED-CONF]")
                        _l = _annotated.count("[LOW-CONF]")
                        _u = _annotated.count("[UNVERIFIED]")
                        print(f"  {C.DIM}HIGH={_h} MED={_m} "
                              f"LOW={_l} UNVERIFIED={_u}"
                              f"{C.RESET}", file=sys.stderr)

        # R-P5: Auto confabulation check on standard L12
        # Runs after every scan that isn't already self-correcting
        _scan_mode_rp5 = getattr(args, 'mode', None) or ''
        _is_selfcorrecting = (_scan_mode_rp5 in
                              ('oracle', 'l12g', 'verified',
                               'scout', 'gaps')
                              or getattr(args, 'trust', False))
        if not _is_selfcorrecting:
            _findings_dir_rp5 = (pathlib.Path(args.dir).resolve()
                                 / ".deep" / "findings")
            if _findings_dir_rp5.exists():
                _mds_rp5 = sorted(
                    _findings_dir_rp5.glob("*.md"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True)
                if _mds_rp5:
                    _text_rp5 = _mds_rp5[0].read_text(
                        encoding="utf-8", errors="replace")
                    # Quick regex check for confabulation markers
                    import re as _re_rp5
                    _suspicious = []
                    # Pattern 1: specific API not in common stdlib
                    for _m in _re_rp5.finditer(
                            r'`?(\w+\.\w+Lock|\w+\.\w+Pool'
                            r'|\w+\.\w+Manager)`?',
                            _text_rp5):
                        _suspicious.append(_m.group(0))
                    # Pattern 2: very specific line numbers
                    _lineref_count = len(_re_rp5.findall(
                        r'line[s]?\s+\d{3,}', _text_rp5))
                    if _suspicious or _lineref_count > 5:
                        print(f"\n{C.YELLOW}Confabulation "
                              f"warning:{C.RESET} "
                              f"{len(_suspicious)} suspicious "
                              f"API refs, {_lineref_count} "
                              f"high line numbers. "
                              f"Use --trust or oracle mode "
                              f"for verified output.",
                              file=sys.stderr)

        # K1b: --provenance post-processing
        if getattr(args, 'provenance', False):
            _prov_prompt = (
                "For each finding in the analysis below, append "
                "a provenance tag:\n"
                "[PROV: source:line_N] = directly visible in "
                "source code at line N\n"
                "[PROV: derivation:from_finding_N] = logically "
                "derived from another finding\n"
                "[PROV: external:source_name] = requires "
                "external verification\n"
                "[PROV: assumption] = analyst's assumption, "
                "no source\n"
                "Output the analysis with provenance tags.")
            _findings_dir = (pathlib.Path(args.dir).resolve()
                             / ".deep" / "findings")
            _latest = None
            if _findings_dir.exists():
                _mds = sorted(_findings_dir.glob("*.md"),
                              key=lambda p: p.stat().st_mtime,
                              reverse=True)
                if _mds:
                    _latest = _mds[0]
            if _latest:
                _text = _latest.read_text(encoding="utf-8",
                                          errors="replace")
                if _text and len(_text) > 100:
                    print(f"\n{C.DIM}Adding provenance..."
                          f"{C.RESET}", file=sys.stderr)
                    _ci = ClaudeInterface(args.dir)
                    _prov = _ci.call(
                        _prov_prompt, _text[:10000],
                        model="haiku", timeout=60)
                    if _prov and not _prov.startswith("[Error"):
                        _prov_path = _latest.with_suffix(
                            ".provenance.md")
                        _prov_path.write_text(
                            _prov, encoding="utf-8")
                        _src = _prov.count("[PROV: source")
                        _der = _prov.count("[PROV: derivation")
                        _ext = _prov.count("[PROV: external")
                        _asm = _prov.count("[PROV: assumption")
                        print(f"{C.GREEN}Provenance saved to "
                              f"{_prov_path.name}{C.RESET}",
                              file=sys.stderr)
                        print(f"  {C.DIM}source={_src} "
                              f"derived={_der} external={_ext}"
                              f" assumption={_asm}{C.RESET}",
                              file=sys.stderr)

        # R-P2: Trust score summary (for oracle/l12g/knowledge_typed modes)
        _scan_mode = getattr(args, 'mode', None) or ''
        if (_scan_mode in ('oracle', 'l12g')
                or getattr(args, 'trust', False)
                or getattr(args, 'confidence', False)):
            _findings_dir = (pathlib.Path(args.dir).resolve()
                             / ".deep" / "findings")
            _latest = None
            if _findings_dir.exists():
                _mds = sorted(_findings_dir.glob("*.md"),
                              key=lambda p: p.stat().st_mtime,
                              reverse=True)
                if _mds:
                    _latest = _mds[0]
            if _latest:
                _text = _latest.read_text(encoding="utf-8",
                                          errors="replace")
                # Count epistemic tags
                _s = _text.count("[STRUCTURAL")
                _d = _text.count("[DERIVED")
                _m = _text.count("[MEASURED")
                _k = _text.count("[KNOWLEDGE")
                _a = _text.count("[ASSUMED")
                _r = _text.count("RETRACTED")
                _v = _text.count("[VERIFY:")
                _total = _s + _d + _m + _k + _a
                if _total > 0:
                    _pct = int(100 * (_s + _d) / _total)
                    print(f"\n{C.BOLD}Trust: {_pct}% "
                          f"source-grounded{C.RESET} "
                          f"({_s}S {_d}D {_m}M {_k}K {_a}A"
                          f"{f' {_r} retracted' if _r else ''}"
                          f")", file=sys.stderr)

        sys.exit(0)

    if args.review:
        repl = PrismREPL(
            model=args.model,
            working_dir=args.dir,
            quiet=args.quiet,
            effort=args.effort,
        )
        prisms = args.prism.split(",") if args.prism else None
        code = repl.review(
            path=args.review,
            prisms=prisms,
            json_output=args.json_output,
            output_file=args.output,
        )
        sys.exit(code)

    repl = PrismREPL(
        model=args.model,
        working_dir=args.dir,
        resume_session=args.resume,
        quiet=args.quiet,
        effort=args.effort,
    )
    repl.run()


if __name__ == "__main__":
    main()

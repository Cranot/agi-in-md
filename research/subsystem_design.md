# Sub-Artifact Targeting: Design Document

## Problem

`/scan file` runs ONE prism on the ENTIRE file. Full Prism runs N prisms on the ENTIRE file. Both treat the file as atomic. But a 400-line file with 3 classes has 3 subsystems with different structural properties. L12 finds one conservation law for the whole file — it cannot find that ClassA has a trust problem while ClassB has a coupling problem. Sub-artifact targeting assigns different prisms to different parts for COVERAGE, not scaling (P198 proved L12 handles 2700 lines).

## Command Surface

```
/scan file subsystem                    — auto-split, auto-assign prisms
/scan file subsystem prisms=l12,identity,optimize   — auto-split, user picks prism set
/scan file subsystem map="ClassA:l12,ClassB:identity"  — user maps prisms to names
```

Subsystem mode is a peer of `full`, `3way`, `behavioral` — a trailing keyword parsed in `_parse_scan_args`.

## Architecture: 4 Phases

### Phase 1: Split

Extract subsystem boundaries from the source file. Output: list of `{name, start_line, end_line, kind, content}`.

**Python files**: Use `ast.parse` (already imported in prism.py for syntax checking). Walk top-level nodes:
- `ast.ClassDef` — one subsystem per class (includes all methods)
- `ast.FunctionDef` / `ast.AsyncFunctionDef` — top-level functions
- Module-level code between classes/functions — grouped as `"module_setup"` if >5 lines

**Other languages**: Regex heuristic. Scan for class/function definition patterns:
- `class Foo` / `def foo` / `function foo` / `func foo` / `fn foo` / `pub fn foo`
- `export class` / `export function` / `export default`
- Fall back to equal-size chunks (~100 lines each) if no definitions found

**Minimum subsystem size**: 10 lines. Subsystems below this merge into their nearest neighbor. **Maximum subsystems**: 8. Beyond 8, merge the smallest pairs until at 8 (cost control: 8+1 = 9 calls max).

Implementation: `_split_into_subsystems(content, filename) -> list[dict]`. Pure function, zero API calls.

### Phase 2: Assign Prisms

Each subsystem gets exactly one prism. Three assignment strategies:

**Auto-assign (default)**: Use a single calibration API call. Send all subsystem names + first 5 lines of each to the model. Prompt returns a JSON mapping of subsystem name to prism name. The calibration prompt includes the full prism catalog with one-line descriptions (from YAML frontmatter). Cost: 1 API call on Sonnet.

Calibration prompt template (`CALIBRATE_SUBSYSTEM_PROMPT`):
```
You are assigning analytical prisms to code subsystems. Each prism reveals different structural properties. Assign the BEST prism for each subsystem — maximize diversity (avoid assigning the same prism twice unless the subsystems are structurally identical).

AVAILABLE PRISMS:
{prism_catalog}

SUBSYSTEMS:
{subsystem_summaries}

Output JSON: {"assignments": [{"subsystem": "name", "prism": "prism_name", "rationale": "5 words"}]}
```

The prism catalog is built from `OPTIMAL_PRISM_MODEL` keys filtered to code-relevant prisms (exclude `writer*`, `behavioral_synthesis`, `l12_universal`, `arc_code`). ~25 prisms. Each entry: name + first line of description from YAML header.

**User prism set** (`prisms=l12,identity,optimize`): Round-robin assignment from the provided list. Subsystem 0 gets prism 0, subsystem 1 gets prism 1, etc., wrapping if fewer prisms than subsystems.

**User map** (`map="ClassName:prism,ClassName2:prism2"`): Exact assignment. Unmatched subsystems get L12 as fallback. Names matched by substring (case-insensitive) so `"Auth:claim"` matches `class AuthMiddleware`.

### Phase 3: Execute

Run each (subsystem, prism) pair through `_call_model` with the prism as system prompt and the subsystem content as input. Each call uses `OPTIMAL_PRISM_MODEL` for model selection.

**Context injection**: Each subsystem call receives a header:
```
# SUBSYSTEM: {name} (lines {start}-{end} of {filename})
# FULL FILE CONTEXT: {other_subsystem_names_and_line_ranges}

{subsystem_content}
```

This gives the model awareness that the subsystem exists within a larger file without sending the full file (which would defeat the purpose of splitting). Cross-references are visible through the context header.

**Parallelism**: All subsystem calls are independent. Use `ThreadPoolExecutor(max_workers=3)` like the existing pipeline. Sequential fallback if `--no-parallel` is set.

### Phase 4: Synthesize

One final API call combines all subsystem outputs into a cross-subsystem analysis. Uses Opus (like `l12_synthesis`).

Synthesis prompt template (`SUBSYSTEM_SYNTHESIS_PROMPT`):
```
Execute every step below. Output the complete analysis.

You received {N} structural analyses, each examining a different subsystem of the same file through a different analytical prism.

{for each: "## SUBSYSTEM: {name} (via {prism})\n{output}"}

## CROSS-SUBSYSTEM FINDINGS
What structural properties span MULTIPLE subsystems? Name coupling patterns, shared assumptions, dependency chains that no single-subsystem analysis could find.

## CROSS-SUBSYSTEM BUGS
What bugs exist BETWEEN subsystems? (ClassA assumes X, ClassB violates X.) These are invisible to single-subsystem analysis.

## FILE-LEVEL CONSERVATION LAW
Each subsystem analysis found local properties. What is the conservation law of the WHOLE file that governs how these subsystems relate? Name it: A x B = constant.

## COVERAGE MAP
For each subsystem: what the assigned prism found, and what a DIFFERENT prism would have found. Identify the biggest remaining blind spot.
```

## Cost Model

| Component | Calls | Model | Cost/call |
|-----------|-------|-------|-----------|
| Calibration | 1 | Sonnet | ~$0.02 |
| Subsystem analysis | N (max 8) | Per-prism optimal | ~$0.03-0.05 |
| Synthesis | 1 | Opus | ~$0.10 |
| **Total** | **N+2** | | **$0.15-0.55** |

Compare: Full Prism = 9 calls, ~$0.50. Subsystem mode at 4 subsystems = 6 calls, ~$0.30. Comparable cost, orthogonal coverage.

## When NOT to Use

- **Files under 100 lines** — one subsystem, no benefit. Print warning and fall back to single L12.
- **Files with 1 class / 1 function** — nothing to split. Fall back to single.
- **Non-code input** — text/reasoning has no structural subsystems. Block with error message.
- **Already using Full Prism** — subsystem and full are complementary but not composable in one command. Run separately.

## Cross-Subsystem Dependencies

The synthesis pass handles these explicitly. The "CROSS-SUBSYSTEM BUGS" section is designed to catch bugs caused by interface mismatches between subsystems. The context header in Phase 3 gives each prism awareness of neighboring subsystems without the full content.

Known limitation: if a bug in ClassA is caused by ClassB's internals (not just its interface), subsystem mode may miss it. The synthesis prompt asks for this but depends on the quality of individual outputs. This is acceptable because `/scan file` (whole-file L12) catches these — subsystem mode is complementary, not a replacement.

## Implementation Plan

1. Add `_split_into_subsystems()` — pure function, ~60 lines
2. Add `CALIBRATE_SUBSYSTEM_PROMPT` and `SUBSYSTEM_SYNTHESIS_PROMPT` — constants
3. Add `_scan_subsystem()` — orchestrator method, ~80 lines
4. Add `"subsystem"` to `_parse_scan_args` trailing keywords
5. Wire into `_cmd_scan` dispatch
6. Add 3 tests: split correctness, parse args, end-to-end mock

Total: ~200 lines of code + 2 prompt templates. No changes to existing modes.

## Open Questions

1. **Should subsystem mode compose with target?** (`/scan file subsystem target="security"`) — each subsystem analyzed through the lens of a security goal. Defer until base mode is validated.
2. **Should we cache splits?** Split is pure + fast (AST parse < 10ms). No cache needed.
3. **Should synthesis receive the original full file?** Pro: can verify cross-subsystem claims. Con: doubles input tokens. Decision: include full file only if total length < 2000 lines.

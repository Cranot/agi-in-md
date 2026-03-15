# Dynamic System Roadmap

## Current state (Mar 2, 2026)

Already dynamic:
- **Lenses**: config-driven, discoverable via `/engine discover`, `.deep/lenses/` override, `_get_lenses()` reads config fresh every call
- **Pipeline engine**: self-assembling (`/plan` discovers stages, cooks prompts via B6, topo-sorts, runs parallel tiers)
- **Config layer**: `.deep/config.json`, live reads, no restart needed, `_config_set()` for runtime changes
- **Rules/memory**: sources, compact threshold, max rules, code extensions all config-driven
- **Hot reload**: `/reload` swaps `self.__class__` — all methods rebind, instance state preserved
- **Intents**: loadable from `intents/` dir, cookable via B6 if missing

Fixed kernel (should stay fixed):
- REPL loop (read input -> dispatch -> output)
- Subprocess backend (ClaudeBackend talks to `claude -p`)
- Config layer (reads `.deep/config.json`)
- Cook mechanism (B6 meta-cooker)
- Intent/skill system (load from disk, cook if missing)

---

## #1 — Model Routing (HIGH IMPACT)

### The problem
`_call_haiku()` is a method name that hardcodes every analytical call to haiku. 15+ places in the code use it. Lenses are proven at 9-9.5 on haiku, but:
- The engine can never decide "this task needs sonnet" (e.g., complex synthesis)
- User can't add a local model or a new model family
- `/model opus` changes the chat model but analytical calls ignore it
- `/heal` has its own hardcoded switch: `if model == "haiku": model = "sonnet"`
- `/autopilot` hardcodes sonnet for fix work

### What "smart" looks like
- Config key `analysis_model` (default: haiku) — the model used for all lens/cook/discover calls
- Config key `fix_model` (default: sonnet) — the model used for code fixes
- The engine could self-tune: if analysis scores consistently low, try a different model
- Method rename: `_call_haiku()` -> `_call_analysis()` reading from config
- `/heal`'s auto-upgrade becomes: use `fix_model` from config, not hardcoded "sonnet"

### Implications
- Cost changes: sonnet is ~10x haiku, opus is ~30x. Model routing = cost routing
- Quality changes: haiku is proven for analysis, sonnet for fixes. But this was tested with specific lenses — new cooked lenses might work differently
- The "model as config" idea lets the engine experiment: try haiku, if score < threshold, retry on sonnet
- Could track model-task performance in `.deep/model_stats.json`

### Open questions
- Should the engine be allowed to auto-escalate? (haiku -> sonnet -> opus based on score)
- Per-command model? (`analysis_model`, `fix_model`, `cook_model`, `synth_model`)
- Per-lens model? (some lenses might work better on opus)
- Budget awareness? (don't escalate if cost limit reached)

---

## #2 — Command Registry (HIGH IMPACT)

### The problem
21 commands in a hardcoded `if/elif` chain in `_handle_command()`. `/reload` can update existing command methods but can't add new ones. Can't remove or remap commands without code edits.

### What "smart" looks like
- Replace if/elif with a dict: `self._commands = {"/deep": self._cmd_deep, ...}`
- Init populates from defaults, but config or plugins can add/override
- `/reload` automatically picks up new `_cmd_*` methods
- Could even cook new commands: "I need a /benchmark command" -> engine writes the method -> `/reload` -> it exists
- Help text as metadata on each command entry

### Implications
- Commands become first-class objects with metadata (name, help, category)
- Plugin system becomes trivial: drop a .py file in `.deep/commands/`, `/reload` picks it up
- The engine could generate commands for the specific project
- Risk: command naming conflicts, security (arbitrary code exec via cooked commands)

### Design
```python
# In __init__:
self._commands = {}
self._register_builtin_commands()

# Registry:
def _register_command(self, name, handler, help_text="", category="core"):
    self._commands[name] = {"handler": handler, "help": help_text, "category": category}

# Dispatch:
def _handle_command(self, cmd, arg):
    entry = self._commands.get(cmd)
    if entry:
        entry["handler"](arg)
    else:
        print(f"Unknown command: {cmd}")
```

---

## #3 — Prompt Templates from Disk (HIGH IMPACT)

### The problem
24 prompt constants hardcoded in code (lines 68-280). Changes require code edits + restart. The intent system already solves this for 6 prompts — but the other 18 don't use it.

### What "smart" looks like
- Every prompt constant has an intent-file equivalent
- Load order: `.deep/prompts/{name}.md` -> `intents/{name}.md` -> hardcoded constant
- The engine can rewrite its own prompts by writing to `.deep/prompts/`
- B6 can re-cook any prompt that scores poorly
- Prompt versioning: hash in manifest, invalidate on B6 update (already built for skills)

### Implications
- Users can customize any prompt without touching code
- The engine's self-improvement loop extends to ALL prompts, not just lenses
- Existing `_load_intent()` method already does most of this — just needs to cover all 24 constants
- Risk: bad prompt rewrites could break parsing (JSON schema prompts are fragile)

### What stays as constants
- The constants become FALLBACKS only (same pattern as B6 cooker -> fallback)
- They're the "factory defaults" that work if everything else fails

---

## #4 — Workflow as Data (HIGH IMPACT)

### The problem
Each command has rigid step sequences:
- `/brain`: 9 hardcoded steps (discover dimensions -> pick -> cook skill -> cook lens -> run 6 lenses -> synthesize -> rate -> retry -> save)
- `/scan`: 3 passes (run lenses -> synthesize per-file -> synthesize report)
- `/plan` fallback: 5 fixed stages (filemap -> sizing -> deps -> group -> spec)
- `/heal`: 4 steps (extract -> pick -> fix -> verify)
- `/autopilot`: load rules -> discover -> fix -> evolve
- `/target`: 6 fixed steps

### What "smart" looks like
- Each workflow is described as a stage list (same shape as pipeline engine stages)
- The pipeline engine runs ANY workflow, not just `/plan`
- `/brain` becomes: `_pipeline_run(goal="deep codebase analysis", ...)`
- New workflows can be defined in `.deep/workflows/brain.json` without code
- The engine could discover optimal workflow for a given goal

### Implications
- Massive code reduction: 6 command methods (500+ lines each) -> 6 workflow definitions + 1 engine
- The engine already has: stage discovery, topo sort, parallel tiers, batch cooking, merge
- Risk: some workflows have interactive steps (user picks dimension in /brain) — engine needs to handle "pause for input" stages
- Risk: error handling differs per workflow — generic engine might lose specificity

### What stays as code
- Interactive steps (user prompts, menus) — these are UI, not data
- The pipeline engine itself
- Output display formatting

---

## #5 — Path Centralization (MEDIUM)

### The problem
`.deep/` appears 80+ times across the code. File paths are scattered:
- `.deep/findings/`, `.deep/skills/`, `.deep/lenses/`, `.deep/config.json`
- `.deep/report.md`, `.deep/issues.json`, `.deep/plan.json`, `.deep/plan.md`
- `.deep/rules.md`, `.deep/user_rules.md`, `.deep/learnings.md`
- `.deep/brain_*.md`, `.deep/target.json`, `.deep/autopilot_log.md`
- `~/.lite_sessions/`, `~/.lite_skills/`

### What "smart" looks like
```python
PATHS = {
    "deep": ".deep",
    "findings": ".deep/findings",
    "skills": ".deep/skills",
    "lenses": ".deep/lenses",
    "config": ".deep/config.json",
    "report": ".deep/report.md",
    "issues": ".deep/issues.json",
    "plan_json": ".deep/plan.json",
    "plan_md": ".deep/plan.md",
    "rules": ".deep/rules.md",
    "sessions": "~/.lite_sessions",
    "global_skills": "~/.lite_skills",
}
```
- All references use `self._path("findings")` instead of hardcoded strings
- Config can override any path
- Enables: project-specific deep dirs, shared team skills, CI-friendly paths

### Implications
- Clean but not a capability unlock
- Would make testing much easier (inject temp paths)
- Migration: 80+ edits, high risk of missing one

---

## #6 — Priority/Sizing Schemas (MEDIUM)

### The problem
P0-P3 appears in 6+ places. S/M/L in 6+ places. Both define colors, labels, distributions, timeout mappings.

### What "smart" looks like
```python
DEFAULT_CONFIG = {
    ...
    "priorities": ["P0", "P1", "P2", "P3"],
    "priority_labels": {"P0": "Critical", "P1": "Important", "P2": "Normal", "P3": "Low"},
    "sizes": {"S": 180, "M": 360, "L": 600},
}
```

### Implications
- Projects could use their own priority system
- But P0-P3 and S/M/L are near-universal
- Risk: changing mid-project would corrupt existing issues.json
- Probably not worth the complexity

---

## What NOT to make dynamic

These are infrastructure that should stay fixed:
- Display column widths, retry counts, truncation limits (UX details)
- Timeout values (tuned to API latency, not domain-specific)
- `.deep/` directory name itself (would break everything)
- Color mappings (cosmetic)
- JSON field names for issues/plans (changing mid-session corrupts data)
- Progress bar width (cosmetic)
- Character sets for parsing (e.g., strip "0123456789.-) *#")
- File extensions (.md for findings, .json for data)

---

## Implementation priority

1. ~~**#1 Model routing**~~ — DONE (Mar 2, 2026). 7 roles, auto/fast/quality, router cache, backward compat aliases.
2. ~~**#2 Command registry**~~ — DONE (Mar 2, 2026). Dict dispatch, 10 cmd wrappers, auto-help from metadata.
3. ~~**#3 Prompts from disk**~~ — DONE (Mar 2, 2026). 3-tier load for all 26 prompts, `/engine prompts`.
4. ~~**#4 Workflow as data**~~ — DONE (Mar 2, 2026). Generic engine + `/scan` converted + `/workflow` cmd. /brain and /heal not yet converted.
5. **#5 Path centralization** — Open. Mechanical refactor, ~1 hour. Clean but not exciting.
6. **#6 Priority schemas** — Skip. Not worth the complexity.

**Also completed (Mar 2, 2026):**
- CLI abstraction (ClaudeInterface wraps all subprocess calls)
- State versioning (_version on all JSON files)
- --review mode (non-interactive CLI for CI)

---

## The vision

Minimum fixed kernel: REPL loop + subprocess backend + config layer + cook mechanism + pipeline engine.

Everything else self-assembles:
- Commands = registered dynamically, discoverable
- Prompts = loaded from disk, cooked if missing, rewritten if scoring poorly
- Workflows = stage lists run by the pipeline engine
- Models = config-driven, engine can self-tune
- Lenses = already dynamic
- Rules = already config-driven

The tool becomes: **a thin shell that discovers what it needs to do, cooks the prompts to do it, and runs them through a generic engine.**

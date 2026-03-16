# Full Prism Catalog

50 prism files total: 41 production + 3 pipeline-internal + 6 variants. Every prism is usable standalone via `/prism <name>` in chat or `--system-prompt-file prisms/<name>.md` with the Claude CLI.

**Score** = AI-evaluated depth on real production code (Starlette, Click, Tenacity). **Model** = empirically best model, auto-selected by `prism.py`. Per-call cost on a ~300 line file: Haiku ~$0.01, Sonnet ~$0.05, Opus ~$0.07.

---

## Structural Analysis — what the code IS

| Prism | What It Does | Score | Model | Used In |
|-------|-------------|-------|-------|---------|
| **l12** | Impossibility trilemma → recursive construction → conservation law → meta-law → concrete bugs with severity | **9.8** | Sonnet | Default `/scan`, Full pipeline |
| **l12_universal** | L12 compressed to 73 words — domain-universal, always single-shot on any input | 9.0 | Sonnet | Reasoning/text analysis |
| **deep_scan** | Traces where information is destroyed, laundered, or silently transformed across boundaries | 9.0 | Opus | Full pipeline |
| **identity** | What the code claims to be vs what it does — revalues "flaws" as necessary costs of impossible goals | **9.5** | Sonnet | Full + Behavioral pipelines |
| **fix_cascade** | Why fixes fail: each fix entails new requirements that recreate the original problem deeper | 9.0 | Opus | Full + Behavioral pipelines |
| **sdl_abstraction** | Detects implementation details bleeding through abstraction boundaries | 8.5 | Haiku | `/prism` targeted analysis |

## Performance & Cost — what the code COSTS

| Prism | What It Does | Score | Model | Used In |
|-------|-------------|-------|-------|---------|
| **optimize** | Traces critical path → separates safe fixes (reduce work) from unsafe ones (skip work) → conservation law | **9.5** | Sonnet | Full + Behavioral pipelines |
| **error_resilience** | Maps corruption cascade chains: silent exits, deferred failures, state corruption propagation | 9.0 | Sonnet | Full + Behavioral pipelines |
| **evidence_cost** | Finds where skipped validation causes both runtime errors AND wasted computation | 9.0 | Sonnet | `/prism` targeted analysis |

## API & Contracts — what the code PROMISES

| Prism | What It Does | Score | Model | Used In |
|-------|-------------|-------|-------|---------|
| **api_surface** | Classifies naming lies: functions that narrow, widen, or misdirect callers about what they actually do | **9.5** | Sonnet | API design review |
| **evolution** | Extracts implicit data contracts that corrupt silently when schemas mutate | **9.5** | Sonnet | API design review |
| **fidelity** | Detects documentation-code drift: help text that contradicts behavior, stale comments, dead config | 8.5 | Sonnet | Full pipeline |
| **contract** | Finds implementations that silently violate their own interfaces | 9.0 | Haiku | `/prism` targeted analysis |

## Security & Trust — where the code is VULNERABLE

| Prism | What It Does | Score | Model | Used In |
|-------|-------------|-------|-------|---------|
| **security_v1** | Inverts trust assumptions → builds exploit chains → derives trust boundary conservation laws | 8.5 | Haiku | Security audit |
| **sdl_trust** | Maps trust topology: authority assumed but never enforced, privilege escalation paths | 9.0 | Haiku | Security audit |

## Temporal — what WILL break

| Prism | What It Does | Score | Model | Used In |
|-------|-------------|-------|-------|---------|
| **simulation** | Runs code forward through maintenance cycles: performance shortcuts, knowledge loss, patch debt | 8.5 | Sonnet | Temporal deep-dive, 3-Way |
| **sdl_simulation** | 3-step temporal fragility scanner — Haiku-optimized, always single-shot | 7.0-7.5 | Haiku | Quick temporal scan (degrades cross-target, P199) |
| **archaeology** | Digs through structural layers: dead patterns, vestigial structures, fault lines between design eras | 8.5 | Sonnet | Temporal deep-dive, 3-Way |
| **cultivation** | Plants hypothetical requirements and watches what grows, dies, or mutates | 8.5 | Sonnet | Perturbation analysis |
| **degradation** | Projects decay timelines — what breaks just by waiting, no new problems needed | 8.8 | Haiku | `/prism` targeted analysis |
| **sdl_coupling** | Detects ordering bugs, stale caches, TOCTOU gaps, timing assumptions | 9.0 | Haiku | `/prism` targeted analysis |

## Hygiene & Completeness — what's MISSING

| Prism | What It Does | Score | Model | Used In |
|-------|-------------|-------|-------|---------|
| **testability_v1** | Finds untestable dependencies, isolation costs, derives testability conservation law | 8.0 | Haiku | Test architecture review |
| **audit_code** | Cross-references all declaration surfaces: features wired but undocumented, declared but unwired | 9.0 | Haiku | Wiring audit |
| **reachability** | Finds dead code, phantom config, zombie overrides, unreachable branches | 7.5 | Sonnet | Code hygiene |
| **state_audit** | Traces state lifecycle: orphaned persistence, assumed state, cache-source divergence | 8.5 | Sonnet | State management review |

## Universal — works on ANY input (code, reasoning, business, research, creative)

| Prism | What It Does | Score | Model | Used In |
|-------|-------------|-------|-------|---------|
| **pedagogy** | Finds what breaks when patterns are copied to new contexts — transfer corruption | 9.0 | Haiku | Any domain analysis |
| **claim** | Inverts embedded assumptions: what if the thing everyone accepts is actually false? | 9.0 | Haiku | Any domain analysis |
| **scarcity** | Derives what's preserved across ALL possible designs — the structural invariant | 9.0 | Haiku | Any domain analysis |
| **rejected_paths** | Traces what moves between visible and hidden when you choose one path over another | 9.0 | Haiku | Any domain analysis |

## Writing — 3-step pipeline: `writer` → `writer_critique` → `writer_synthesis`

| Prism | What It Does | Score | Model | Used In |
|-------|-------------|-------|-------|---------|
| **writer** | Rewrites into high-converting developer landing pages | 8.9 | Sonnet | Writer pipeline step 1 |
| **writer_critique** | Finds structural weaknesses and missed opportunities in the rewrite | 8.9 | Opus | Writer pipeline step 2 |
| **writer_synthesis** | Takes original + rewrite + critique → definitive version | 8.9 | Opus | Writer pipeline step 3 |

## Knowledge Gap Detection — what the analysis CAN'T KNOW (Round 41)

| Prism | What It Does | Score | Model | Used In |
|-------|-------------|-------|-------|---------|
| **oracle** | 5-phase: depth → epistemic typing → self-correction → reflexive diagnosis → harvest. Maximum trust. | 9 | Sonnet | `/scan file oracle`, `--trust` |
| **l12g** | L12 + self-audit + self-correction in single pass. Zero confabulation in 90% of runs. | 9 (v2 rubric) | Sonnet | `/scan file l12g`, `--depth deep` |
| **knowledge_boundary** | Classifies claims: STRUCTURAL / CONTEXTUAL / TEMPORAL / ASSUMED. Maps fill mechanisms. | **9.3** | Sonnet | `/scan file gaps`, verified pipeline |
| **knowledge_audit** | Adversarial confabulation detection. Attacks factual claims, finds what's confabulated. | ~7.5 | Sonnet | `/scan file gaps`, verified pipeline |
| **knowledge_typed** | Knowledge<T>: every finding carries Type / Confidence / Provenance / Falsifiable / If-wrong. | 7 | Sonnet | `/scan file prism=knowledge_typed` |
| **strategist** | Meta-agent: knows all 50 prisms + 20 modes. Plans optimal tool sequence for any goal. 2-call (plan + adversarial critique). | — | Sonnet | `/scan file strategist` |
| **prereq** | Knowledge prerequisite scanner: identifies what you need to know BEFORE a task. Outputs atomic questions for AgentsKB batch query. | — | Sonnet | `/scan "task" prereq` |
| **verify_claims** | Extracts testable claims from analysis, generates verification commands. Tells you what it CAN'T verify. | — | Sonnet | `/scan file verify-claims` |

## Code Generation (not analysis — different cognitive operation)

| Prism | What It Does | Score | Model | Used In |
|-------|-------------|-------|-------|---------|
| **codegen** | Decompose → design API-first → predict failure modes → implement | — | Sonnet | `/prism codegen` |

---

## Pipeline-Internal Prisms

These are used automatically by pipelines — not invoked directly:

| Prism | Used By |
|-------|---------|
| **l12_complement_adversarial** | Full pipeline adversarial pass |
| **l12_synthesis** | Full pipeline synthesis pass |
| **behavioral_synthesis** | Behavioral pipeline synthesis |

## Variant/Archive Prisms

These are alternative versions of production prisms — for experimentation or specific edge cases:

| Prism | Variant Of | Notes |
|-------|-----------|-------|
| **api_surface_neutral.md** | api_surface | Domain-neutral vocabulary |
| **error_resilience_70w.md** | error_resilience | 70w compressed — Round 40 found avg 7.0 cross-target (below threshold, P202) |
| **error_resilience_compact.md** | error_resilience | Compact variant |
| **error_resilience_neutral.md** | error_resilience | Domain-neutral vocabulary |
| **evolution_neutral.md** | evolution | Domain-neutral vocabulary |
| **arc_code.md** | — | ARC-AGI specific (niche domain) |

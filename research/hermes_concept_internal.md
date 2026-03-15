# Super Hermes — Concept Overview (Internal)

## The Core Insight

Every AI coding tool does the same thing: you give it code, it gives you a surface-level review. Pay more for a fancier model, get a slightly better-written version of the same observations.

We proved (40 rounds, 1,000+ experiments) that the model isn't the bottleneck — the thinking structure is. A 332-word markdown prompt that tells the model HOW to think produces deeper analysis from the cheapest model than the most expensive model gets freestyle. The prompt is the dominant variable.

## What We Built

**Prisms** = structured analytical programs. 33 proven ones, each finding different things.

**The cooker** = writes NEW prisms on the fly. Reads your code, generates a custom analytical program. No two analyses are the same.

**Super Hermes** = 4 Hermes Agent skills:
- `/prism-scan` — cook a lens, execute it, find structural trade-offs + constraint footer
- `/prism-full` — multi-pass pipeline where later passes attack earlier ones
- `/prism-discover` — brainstorm all possible analysis angles
- `/prism-reflect` — analyze code, then analyze what your OWN analysis missed, produce constraint report

**Growth mechanism** = `/prism-reflect` saves constraint reports to `.prism-history.md`. Next `/prism-scan` reads that history and adjusts its lens to cover past gaps. Agent gets smarter per-project.

## What Makes This Different

Other agents promise to do everything. Ours tells you what it CAN'T do. "An agent that knows what it can't see is an agent you can trust."

## What We Have vs What We Want

| Have (built) | Want (roadmap) |
|---|---|
| 4 skills running in Hermes | Validated across model sizes (7B→70B) |
| 5 proven prisms from 1K experiments | Community-contributed prism library |
| .prism-history.md persistence | Cross-project learning, intelligent pruning |
| Dynamic lens cooking | Lens quality tracking + best-lens caching |
| Constraint transparency report | /prism-fix action loop (scan → patch → re-scan) |
| 40 rounds research backing | Hermes-native benchmarks |

## The Honest Gap

Growth mechanism is real but minimal (append-only file). "Grows with you" is architecturally sound but needs more implementation to be fully convincing. We haven't validated across small models (7B). The skills work via prompt instructions, not executable code.

## The Core Bet

Constraint transparency > capability theater. Trust compounds.

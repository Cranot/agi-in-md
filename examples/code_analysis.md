# Example: L12 Prism on Starlette Routing (333 lines)

**Command:** `/scan routing.py` (or `python prism.py --scan routing.py`)

## What vanilla produces

> "The session handling is tightly coupled to cookie semantics. Consider decoupling them."

One sentence. Names a pattern. Depth: 7/10.

## What L12 produces

The L12 prism tells the model to: make a claim, have three experts attack it, name what the code hides, build an improvement, watch it break, derive the inescapable trade-off.

### The Three Experts

**Expert A (Defense):** The mutation in `Mount.url_path_for` is intentional — the `path_params` dict is "used up" by URL resolution. Efficient, documented.

**Expert B (Attack):** You've understated the problem. The "restore" writes to `remaining_params` (a NEW dict), not `path_params`. The caller's dict is left corrupted with `path=""`. But worse: `None` is treated as both "not provided" and a valid pass-through value.

**Expert C (Probes):** Both of you assume `path_params` is "caller-owned data." But `**path_params` creates a NEW dict at each call site. The mutation affects the new dict, not the caller's original. The code *accidentally* works because of a language feature, not by design.

### The Conservation Law

> `Flexibility of coordination x Decidability of behavior = constant`

The more flexible your routing composition (mounts, middleware, wildcards), the less you can predict what the system will do at runtime. This isn't a bug — it's a structural impossibility. Every routing framework that gains expressiveness loses determinism.

### The Bug Table (excerpt)

| # | Bug | Severity | Fixable? |
|---|-----|----------|----------|
| 1 | `Mount.url_path_for` mutates caller dict | HIGH | Structural |
| 3 | `Match.PARTIAL` first-match-wins is nondeterministic | MEDIUM | Fixable |
| 7 | `NoMatchFound` loses context (which routes tried) | MEDIUM | Fixable |
| 11 | `assert` in production path optimized away | HIGH | Fixable |

**Full output:** 2,610 words, 15 bugs found, conservation law + meta-law derived. Cost: ~$0.05.

---

*This is a real output from Round 40 testing. Full file: `output/vps_validation/A1_sdl_vs_l12/l12_starlette.md`*

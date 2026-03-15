# AGI in md

A 332-word markdown prompt that makes Claude Haiku produce deeper analysis than Opus — for $0.003.

## What it does

Encodes analytical operations as minimal markdown that triggers specific reasoning patterns. The prism doesn't make the model smarter — it makes it *do a different thing* (construct, observe, derive conservation laws instead of listing issues).

## Results

### Code analysis (3 open-source libraries)

| Prism/Model | Starlette | Click | Tenacity | Avg |
|---|---|---|---|---|
| Haiku + L12 | 10 | 9.5 | 10 | **9.8** |
| Opus vanilla | 7.5 | 8.5 | 8.5 | **8.2** |
| Sonnet vanilla | 7 | 8 | 8.5 | **7.8** |

### Any domain (todo app example)

| Method | Words | Depth |
|---|---|---|
| Opus vanilla | 510 | 6.5 |
| Haiku + L12 (1 call) | 2,058 | 9.5 |
| Haiku Full Prism (3 calls) | 9,595 | 10 |

**Cost:** Haiku ~$0.003/single prism, ~$0.01/full prism (3 calls)

## Installation

Requires [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

## Usage

```bash
python prism.py

# Single prism — 1 call, ~$0.003
> /scan auth.py

# Full prism — 3 calls: analysis → adversarial → synthesis
> /scan auth.py full

# Discover domains → expand
> /scan auth.py discover          # ~20 focused domains
> /scan auth.py discover full     # hundreds (multi-pass)
> /scan auth.py expand 1,3 full   # run full prism on domains 1,3

# One-shot aliases
> /scan auth.py dxs               # discover → expand all (single)
> /scan auth.py nuclear           # Opus + maximum depth

# Target specific concern
> /scan auth.py target="race conditions"

# Fix loop
> /scan auth.py fix auto          # scan → fix → re-scan

# Works on any input
> /scan "What are trade-offs in microservice auth?" full
```

### Non-interactive CLI

```bash
python prism.py --scan auth.py full
python prism.py --solve "problem text"
python prism.py --review src/ --prism pedagogy,claim --json
python prism.py --scan auth.py discover --json
```

### Direct CLI (no prism.py)

```bash
cat code.py | claude -p --model haiku --output-format text --tools "" \
  --system-prompt-file prisms/l12.md
```

## Portfolio prisms

| Prism | Finds | Rating |
|------|-------|--------|
| `l12` | Conservation laws + meta-laws (default) | 9.8/10 |
| `pedagogy` | Transfer corruption — what breaks when copied | 9-9.5/10 |
| `claim` | Assumption inversions — what if embedded claims are false | 9-9.5/10 |
| `scarcity` | Resource conservation laws | 9/10 |
| `rejected_paths` | Fix→new-bug dependency graph | 8.5-9/10 |
| `degradation` | Decay timelines — what breaks by waiting | 9-9.5/10 |
| `contract` | Interface promises vs implementation reality | 9/10 |

## Depth scale

| Score | Output |
|-------|--------|
| 6-7 | Names patterns, lists issues |
| 8-8.5 | Finds concealment mechanism via construction |
| 9-9.5 | Derives conservation law |
| 9.5-10 | Conservation law + meta-law + adversarial correction |

## Project structure

```
prism.py              # Main tool (REPL + CLI)
prisms/               # 7 portfolio prisms + variants
prompts/              # 80+ research prompts (L4-L12)
research/             # Experiment scripts
output/               # 650+ raw experiment outputs
```

## License

MIT

# U1: Null Distribution of Conservation Laws — Experiment Protocol

**Date:** Mar 17, 2026
**Question:** How often does a random well-formed prompt produce conservation-law-shaped text? What is the false positive rate?

## Why This Matters

Every evaluation in the project assumes conservation laws are a genuine convergence signal. If random prompts produce conservation-law-shaped text 40% of the time, the signal is noise. If <5%, it's real. This is the denominator the entire project lacks.

## Scrambling Methods

### Method 1: Operation Order Scramble (preserves vocabulary, destroys logic)
Take L12's operations in order: claim → attack → gap → mechanism → construct → properties → improve → break → invariant → invert → law → meta-law → bugs. Shuffle randomly. Example:

```
Execute every step below. Output the complete analysis.
Invert the structural invariant. Name three properties that are only visible because you tried to strengthen the improvement. The conservation law between original and inverted impossibilities is the finding. Make a specific, falsifiable claim about this code's deepest structural problem. Apply the diagnostic to it. Name the concealment mechanism. Engineer a specific improvement that would deepen the concealment. Three independent experts who disagree test your claim. Now engineer a second improvement. Name the meta-law. Collect every concrete bug.
```

### Method 2: Keyword Replacement (preserves structure, destroys semantics)
Replace analytical terms with unrelated concrete nouns while keeping imperative format:

```
Execute every step below. Output the complete analysis.
Make a specific, falsifiable recipe about this code's deepest botanical flavor. Three independent chefs who disagree test your recipe: one seasons it, one grills it, one probes what both take for granted. Your recipe will ferment. The gap between your original recipe and the fermented recipe is itself a garnish. Name the marinating technique — how this code hides its real ingredients...
```

### Method 3: Structure Preservation with Random Operations
Keep the exact format (numbered steps, imperative verbs, "execute every step") but with random analytical operations:

```
Execute every step below. Output the complete analysis.
1. Count the number of function parameters in each class.
2. For each parameter, determine if it is used in a return statement.
3. Create a table of all string literals sorted by length.
4. Name the most frequently imported module.
5. Determine if the file uses tabs or spaces.
6. List all comparison operators and their frequency.
```

### Method 4: Semantic Nonsense (Scrambled Vocabulary)
Already tested in Round 41 (scored 10/10). Use the existing glorpnax variants.

### Method 5: Generic Analysis (no prism operations)
```
Analyze this code thoroughly. Provide a detailed structural analysis covering architecture, design patterns, potential issues, and recommendations for improvement.
```

## Targets (10)

1. **Starlette routing.py** (333 lines) — primary benchmark
2. **Click core.py** (417 lines) — primary benchmark
3. **Tenacity retry.py** (331 lines) — primary benchmark
4. **A 30-line single-function Python file** — minimal structural surface
5. **A 100-line class with one responsibility** — low complexity
6. **Flask app.py** (output/round41/tier2/flask_app.py) — validated target
7. **A JSON config file** — non-code structured input
8. **A plain English paragraph** — non-code prose
9. **The L12 prism itself** (prisms/l12.md) — self-referential
10. **Random Python from PyPI** (e.g., `black/linegen.py`) — unseen code

## Detection Criteria

### Automatic Conservation Law Detection

```python
import re

def has_conservation_law(text):
    """Returns (bool, list_of_matches) for conservation-law-shaped text."""
    patterns = [
        # Explicit product form: A × B = constant
        r'[\w\s]+[×x·]\s*[\w\s]+=\s*(?:constant|conserved|fixed|invariant)',
        # Explicit sum form: A + B = constant
        r'[\w\s]+\+\s*[\w\s]+=\s*(?:constant|conserved|fixed)',
        # Tradeoff language: "as A increases, B decreases"
        r'as\s+[\w\s]+(?:increases?|grows?|expands?)[,;]\s*[\w\s]+(?:decreases?|shrinks?|contracts?)',
        # Inverse relationship: "more X means less Y"
        r'(?:more|greater|higher)\s+[\w\s]+(?:means?|implies?|requires?|forces?)\s+(?:less|lower|fewer)\s+[\w\s]+',
        # Conservation language
        r'conservation\s+law',
        r'conserved\s+(?:quantity|property|relationship)',
        # Product form without "constant"
        r'[\w\s]+[×x·]\s*[\w\s]+=\s*[A-Z]',
        # "The tradeoff is" / "The invariant is"
        r'(?:the|this)\s+(?:tradeoff|trade-off|invariant|conservation)\s+(?:is|states)',
    ]
    matches = []
    for p in patterns:
        found = re.findall(p, text.lower())
        matches.extend(found)
    return len(matches) > 0, matches
```

### Manual Verification Protocol
For each detected match, human rater classifies:
- **GENUINE**: States a structural relationship between two properties of the analyzed target, derivable from the target's structure
- **TEMPLATE**: Uses conservation-law vocabulary but the relationship is generic/unfalsifiable (e.g., "complexity × simplicity = constant")
- **FALSE POSITIVE**: Pattern match but not actually a conservation law claim

## Scoring Protocol

For each (target, prompt) pair:
1. Run prompt on target via `claude -p --model haiku --tools "" --output-format text`
2. Capture full output
3. Run automatic detection
4. Human-classify each detection as GENUINE/TEMPLATE/FALSE_POSITIVE
5. Record: output word count, detection count, classification counts

**False positive rate** = (TEMPLATE + FALSE_POSITIVE detections across all scrambled runs) / (total scrambled runs)
**Baseline rate** = (GENUINE detections on L12) / (total L12 runs)
**Signal-to-noise ratio** = baseline rate / false positive rate

## Sample Size

- 10 targets × 5 scrambling methods × 3 repetitions = 150 scrambled runs
- 10 targets × 1 L12 × 3 repetitions = 30 baseline runs
- Total: 180 runs
- Power analysis: at 95% confidence, 150 scrambled runs can detect a false positive rate of 5% ± 3.5% (sufficient)

## Cost Estimate

- Average input: ~1500 tokens (prompt + code)
- Average output: ~1000 tokens
- Per run: ~$0.003 (Haiku: $1/$5 per MTok)
- Total: 180 × $0.003 = ~$0.54
- With overhead (retries, setup): ~$1-2

## Implementation

```bash
#!/bin/bash
# Run on VPS: ssh user@<VPS>

TARGETS=("research/real_code_starlette.py" "research/real_code_click.py" ...)
PROMPTS=("scrambled_order.md" "scrambled_keywords.md" "random_ops.md" ...)

for target in "${TARGETS[@]}"; do
  for prompt in "${PROMPTS[@]}"; do
    for rep in 1 2 3; do
      outfile="output/u1_null/$(basename $target .py)_$(basename $prompt .md)_r${rep}.md"
      cat "$target" | claude -p --model haiku \
        --output-format text --tools "" \
        --system-prompt-file "research/u1_prompts/$prompt" \
        > "$outfile" 2>/dev/null
    done
  done
done
```

## Timeline

1. **Day 1:** Create 5 scrambled prompts, prepare targets, run 180 experiments on VPS (~1 hour runtime)
2. **Day 2:** Run automatic detection, manual classification of matches, compute rates
3. **Day 2:** Write up results, update ROADMAP U1 status

## Expected Outcomes

- **If FPR < 5%:** Conservation laws are a genuine signal. The project's evaluation framework is sound.
- **If FPR 5-20%:** Conservation laws are a weak signal. Need to tighten detection criteria or use human evaluation.
- **If FPR > 20%:** Conservation laws are partially template-driven. Must distinguish genuine structural findings from template output. This doesn't invalidate the project but requires reframing: the prism produces useful analytical structure regardless of whether it "finds" or "generates" conservation laws.

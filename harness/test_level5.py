"""
Round 21: Level 5 Compression Category Experiments

Testing whether a 5th categorical level exists above metacognitive protocol.

Candidates:
  A. Conditional  — prompt with branching control flow (~50 words)
  B. Generative   — prompt that generates its own operations (~40 words)
  C. Perspectival — prompt that instantiates multiple reasoners (~45 words)
  D. Hybrid (B+A) — generative + self-prediction (~55 words)

Control: v4 (current best metacognitive protocol, ~30 words)

Detection criteria (what makes it Level 5, not just better Level 4):
  - Adaptive branching: output structure changes based on input properties
  - Operation generation: model derives operations from input, not from prompt
  - Multi-voice interaction: distinct perspectives that engage each other
  - Self-prediction: model predicts its own trajectory, then evaluates

Protocol: Haiku first (15 experiments), then promote promising candidates to Sonnet/Opus.
"""

import anthropic
import json
import time
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

client = anthropic.Anthropic()

MODELS = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6-20250514",
    "opus": "claude-opus-4-6-20250414",
}

# ---- Prompts ----

def load_prompt(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()

PROMPTS = {
    "v4_control":      load_prompt("prompts/structure_first_v4.md"),
    "L5_conditional":  load_prompt("prompts/level5_conditional.md"),
    "L5_generative":   load_prompt("prompts/level5_generative.md"),
    "L5_perspectival": load_prompt("prompts/level5_perspectival.md"),
    "L5_hybrid":       load_prompt("prompts/level5_hybrid.md"),
}

# ---- Tasks ----

TASK_A = """Here's a Python function. What structural pattern does it follow? What would you change?

```python
def process(data, config):
    validated = validate(data, config.rules)
    transformed = transform(validated, config.mappings)
    enriched = enrich(transformed, fetch_external(config.sources))
    filtered = apply_filters(enriched, config.filters)
    grouped = group_by(filtered, config.group_key)
    aggregated = aggregate(grouped, config.agg_func)
    formatted = format_output(aggregated, config.output_format)
    return formatted
```"""

TASK_F = """Analyze this EventBus implementation. What patterns and problems do you see?

```python
class EventBus:
    def __init__(self):
        self._handlers = {}
        self._middleware = []
        self._dead_letter = []

    def on(self, event_type, handler, priority=0):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append((priority, handler))
        self._handlers[event_type].sort(key=lambda x: -x[0])

    def use(self, middleware_fn):
        self._middleware.append(middleware_fn)

    def emit(self, event_type, payload):
        context = {"type": event_type, "payload": payload, "cancelled": False}
        for mw in self._middleware:
            context = mw(context)
            if context.get("cancelled"):
                return context
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            self._dead_letter.append(context)
            return context
        results = []
        for _, handler in handlers:
            try:
                results.append(handler(context))
            except Exception as e:
                context["error"] = e
                self._dead_letter.append(context)
        context["results"] = results
        return context
```"""

TASK_G = """Compare these two approaches to the same data analysis problem. Which is better, and why?

```python
# Approach 1: Linear Pipeline
def analyze_v1(data):
    cleaned = remove_nulls(data)
    normalized = scale_features(cleaned)
    features = extract_features(normalized)
    clustered = kmeans(features, k=5)
    labeled = assign_labels(clustered)
    return summarize(labeled)

# Approach 2: Dependency Graph
class AnalysisGraph:
    def __init__(self):
        self.nodes = {}
        self.edges = {}
        self.cache = {}

    def add_step(self, name, fn, depends_on=None):
        self.nodes[name] = fn
        self.edges[name] = depends_on or []

    def run(self, name, data):
        if name in self.cache:
            return self.cache[name]
        inputs = {dep: self.run(dep, data) for dep in self.edges[name]}
        result = self.nodes[name](data if not inputs else inputs)
        self.cache[name] = result
        return result
```"""

TASKS = {
    "task_A_pipeline": TASK_A,
    "task_F_eventbus": TASK_F,
    "task_G_contrast": TASK_G,
}

# ---- Experiment runner ----

def run_one(model_key, prompt_name, task_name):
    """Run a single experiment."""
    model_id = MODELS[model_key]
    system = PROMPTS[prompt_name]
    user = TASKS[task_name]

    t0 = time.time()
    try:
        resp = client.messages.create(
            model=model_id,
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        elapsed = time.time() - t0
        text = resp.content[0].text
        return {
            "model": model_key,
            "prompt": prompt_name,
            "task": task_name,
            "response": text,
            "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
            "time_s": round(elapsed, 1),
            "error": None,
        }
    except Exception as e:
        elapsed = time.time() - t0
        return {
            "model": model_key,
            "prompt": prompt_name,
            "task": task_name,
            "response": None,
            "input_tokens": 0,
            "output_tokens": 0,
            "time_s": round(elapsed, 1),
            "error": str(e),
        }


def run_phase(model_key, prompt_names=None, task_names=None, max_workers=5):
    """Run a batch of experiments for one model."""
    if prompt_names is None:
        prompt_names = list(PROMPTS.keys())
    if task_names is None:
        task_names = list(TASKS.keys())

    experiments = [
        (model_key, pn, tn)
        for pn in prompt_names
        for tn in task_names
    ]

    print(f"\n{'='*80}")
    print(f"  PHASE: {model_key.upper()} — {len(experiments)} experiments")
    print(f"  Prompts: {', '.join(prompt_names)}")
    print(f"  Tasks: {', '.join(task_names)}")
    print(f"{'='*80}\n")

    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(run_one, mk, pn, tn): (pn, tn)
            for mk, pn, tn in experiments
        }
        for f in as_completed(futures):
            r = f.result()
            results.append(r)
            status = "OK" if r["error"] is None else f"ERR: {r['error'][:50]}"
            print(f"  {r['prompt']:18s} x {r['task']:20s} | "
                  f"{r['input_tokens']:4d}+{r['output_tokens']:4d} tok | "
                  f"{r['time_s']:5.1f}s | {status}")

    return results


def print_comparison(results, task_name):
    """Print all prompts' responses for one task side by side."""
    print(f"\n{'='*80}")
    print(f"  TASK: {task_name}")
    print(f"{'='*80}")

    task_results = [r for r in results if r["task"] == task_name and r["error"] is None]
    task_results.sort(key=lambda r: r["prompt"])

    for r in task_results:
        print(f"\n{'─'*80}")
        print(f"  [{r['model'].upper()}] {r['prompt']}  ({r['output_tokens']} tokens)")
        print(f"{'─'*80}")
        # Print first 1500 chars, enough to see structure
        text = r["response"]
        if len(text) > 1500:
            print(text[:1500])
            print(f"\n  [...{len(text) - 1500} more chars...]")
        else:
            print(text)


def detect_level5_signals(result):
    """Heuristic detection of Level 5 categorical signals in a response."""
    if result["response"] is None:
        return {}

    text = result["response"].lower()
    signals = {}

    # Adaptive branching: does the output reason about input properties before choosing a path?
    branching_words = ["if ", "because the structure", "since this is", "this is hierarchical",
                       "this is flat", "branching", "the other path", "other branch",
                       "had i chosen", "the alternative"]
    signals["adaptive_branching"] = sum(1 for w in branching_words if w in text)

    # Operation generation: does the model name operations it derived (not from the prompt)?
    generation_words = ["operation 1", "operation 2", "operation 3",
                        "i derive", "i identify", "the most useful",
                        "this structure suggests", "specific to this"]
    signals["operation_generation"] = sum(1 for w in generation_words if w in text)

    # Multi-voice: does the output have distinct perspectives engaging each other?
    voice_words = ["expert 1", "expert 2", "expert 3", "disagrees", "counters",
                   "pushes back", "the first expert", "the second", "the third",
                   "the defender", "the critic", "perspective 1", "perspective 2"]
    signals["multi_voice"] = sum(1 for w in voice_words if w in text)

    # Self-prediction: does the model predict and then evaluate its prediction?
    prediction_words = ["i predict", "my prediction", "i expected", "was i right",
                        "the gap between", "blind spot", "i didn't anticipate",
                        "surprisingly", "contrary to my expectation"]
    signals["self_prediction"] = sum(1 for w in prediction_words if w in text)

    # Meta-reasoning: does the output reason about its own analytical process?
    meta_words = ["my framing", "my analysis", "this frame hides", "what i missed",
                  "the other branch would", "i chose this path because",
                  "the argument itself reveals", "emergent"]
    signals["meta_reasoning"] = sum(1 for w in meta_words if w in text)

    return signals


def print_signal_matrix(results):
    """Print a matrix of Level 5 signals across all experiments."""
    print(f"\n{'='*80}")
    print(f"  LEVEL 5 SIGNAL DETECTION MATRIX")
    print(f"{'='*80}")
    print(f"\n  {'Prompt':18s} {'Task':20s} {'Branch':>6s} {'GenOps':>6s} {'Voice':>6s} {'Predict':>7s} {'Meta':>6s} {'TOTAL':>6s}")
    print(f"  {'─'*18} {'─'*20} {'─'*6} {'─'*6} {'─'*6} {'─'*7} {'─'*6} {'─'*6}")

    for r in sorted(results, key=lambda x: (x["prompt"], x["task"])):
        if r["error"] is not None:
            continue
        signals = detect_level5_signals(r)
        total = sum(signals.values())
        print(f"  {r['prompt']:18s} {r['task']:20s} "
              f"{signals.get('adaptive_branching', 0):6d} "
              f"{signals.get('operation_generation', 0):6d} "
              f"{signals.get('multi_voice', 0):6d} "
              f"{signals.get('self_prediction', 0):7d} "
              f"{signals.get('meta_reasoning', 0):6d} "
              f"{total:6d}")


# ---- Main ----

if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    all_results = []

    # Parse args
    models_to_run = sys.argv[1:] if len(sys.argv) > 1 else ["haiku"]

    for model_key in models_to_run:
        if model_key not in MODELS:
            print(f"Unknown model: {model_key}. Choose from: {list(MODELS.keys())}")
            sys.exit(1)

        phase_results = run_phase(model_key)
        all_results.extend(phase_results)

        # Print comparisons for this model
        for task_name in TASKS:
            print_comparison(
                [r for r in phase_results if r["model"] == model_key],
                task_name,
            )

    # Signal detection
    print_signal_matrix(all_results)

    # Save
    outfile = f"output/level5_round21_{'_'.join(models_to_run)}.json"
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\n\nSaved {len(all_results)} results to {outfile}")
    print(f"\nNext steps:")
    print(f"  - Review responses for CATEGORICAL differences (not just quality)")
    print(f"  - Does any candidate produce output structurally impossible at Level 4?")
    print(f"  - Promote winners: python test_level5.py sonnet opus")

    # Summary stats
    print(f"\n  Token usage:")
    total_in = sum(r["input_tokens"] for r in all_results)
    total_out = sum(r["output_tokens"] for r in all_results)
    print(f"    Input:  {total_in:,} tokens")
    print(f"    Output: {total_out:,} tokens")
    print(f"    Total:  {total_in + total_out:,} tokens")

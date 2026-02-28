#!/bin/bash
# AGI in md — Experiment Runner
# Run from /tmp to avoid CLAUDE.md auto-loading
# Usage: bash run.sh [haiku|sonnet|opus] [task_A|task_H|task_D1|all] [prompt_name|all]
#
# Examples:
#   bash run.sh sonnet task_H L8_generative_v2  # Best prompt (L8) on code task
#   bash run.sh opus task_D1 L8_generative_v2   # L8 on domain task
#   bash run.sh sonnet task_H L7_diagnostic     # L7 on code task
#   bash run.sh opus task_H L7_relay_mechanism  # Relay experiment

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT_DIR="$PROJECT_DIR/output/round25"
mkdir -p "$OUTPUT_DIR"

MODEL="${1:-haiku}"
TASK_FILTER="${2:-all}"
PROMPT_FILTER="${3:-all}"

# ---- Code Tasks ----

TASK_A='Here'\''s a Python function. What structural pattern does it follow? What would you change?

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
```'

TASK_F='Analyze this EventBus implementation. What patterns and problems do you see?

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
```'

TASK_G='Compare these two approaches to the same data analysis problem. Which is better, and why?

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
```'

TASK_H='Analyze this auth middleware chain. What structural patterns and problems do you see?

```python
class AuthMiddleware:
    def __init__(self):
        self._chain = []
        self._bypass_routes = set()
        self._role_cache = {}

    def add(self, checker_fn, scope="all"):
        self._chain.append({"fn": checker_fn, "scope": scope})

    def bypass(self, route):
        self._bypass_routes.add(route)

    def authenticate(self, request):
        if request.path in self._bypass_routes:
            request.user = {"role": "anonymous", "permissions": []}
            return request

        context = {"request": request, "identity": None, "claims": {}}

        for checker in self._chain:
            if checker["scope"] != "all" and checker["scope"] != request.method:
                continue
            result = checker["fn"](context)
            if result.get("denied"):
                return {"status": 403, "error": result["reason"]}
            context["claims"].update(result.get("claims", {}))
            if result.get("identity"):
                context["identity"] = result["identity"]

        if context["identity"] is None:
            return {"status": 401, "error": "No identity established"}

        cache_key = context["identity"]["id"]
        if cache_key in self._role_cache:
            context["claims"]["roles"] = self._role_cache[cache_key]
        else:
            roles = fetch_roles(context["identity"])
            self._role_cache[cache_key] = roles
            context["claims"]["roles"] = roles

        request.user = {**context["identity"], **context["claims"]}
        return request
```'

TASK_I='Analyze this state machine implementation. What structural patterns and problems do you see?

```python
class StateMachine:
    def __init__(self, initial_state):
        self._state = initial_state
        self._transitions = {}
        self._guards = {}
        self._on_enter = {}
        self._on_exit = {}
        self._history = []

    def add_transition(self, from_state, event, to_state):
        key = (from_state, event)
        self._transitions[key] = to_state

    def add_guard(self, from_state, event, guard_fn):
        self._guards[(from_state, event)] = guard_fn

    def on_enter(self, state, callback):
        self._on_enter[state] = callback

    def on_exit(self, state, callback):
        self._on_exit[state] = callback

    def send(self, event, data=None):
        key = (self._state, event)
        if key not in self._transitions:
            return {"ok": False, "error": f"No transition for {event} in {self._state}"}

        guard = self._guards.get(key)
        if guard and not guard(data):
            return {"ok": False, "error": "Guard rejected transition"}

        old_state = self._state
        new_state = self._transitions[key]

        exit_cb = self._on_exit.get(old_state)
        if exit_cb:
            exit_cb(old_state, event, data)

        self._state = new_state
        self._history.append({"from": old_state, "to": new_state, "event": event})

        enter_cb = self._on_enter.get(new_state)
        if enter_cb:
            enter_cb(new_state, event, data)

        return {"ok": True, "from": old_state, "to": new_state}
```'

TASK_J='Analyze this repository pattern with query builder. What structural patterns and problems do you see?

```python
class Repository:
    def __init__(self, db, table_name):
        self._db = db
        self._table = table_name
        self._soft_delete = True
        self._hooks = {"before_save": [], "after_save": [], "before_delete": []}

    def find(self, **filters):
        query = f"SELECT * FROM {self._table}"
        conditions = []
        params = []
        if self._soft_delete:
            conditions.append("deleted_at IS NULL")
        for col, val in filters.items():
            if isinstance(val, list):
                placeholders = ",".join(["?"] * len(val))
                conditions.append(f"{col} IN ({placeholders})")
                params.extend(val)
            elif val is None:
                conditions.append(f"{col} IS NULL")
            else:
                conditions.append(f"{col} = ?")
                params.append(val)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        return self._db.execute(query, params)

    def save(self, entity):
        for hook in self._hooks["before_save"]:
            entity = hook(entity)
        if entity.get("id"):
            cols = [f"{k} = ?" for k in entity if k != "id"]
            query = f"UPDATE {self._table} SET {','.join(cols)} WHERE id = ?"
            params = [v for k, v in entity.items() if k != "id"] + [entity["id"]]
        else:
            cols = list(entity.keys())
            placeholders = ",".join(["?"] * len(cols))
            query = f"INSERT INTO {self._table} ({','.join(cols)}) VALUES ({placeholders})"
            params = list(entity.values())
        result = self._db.execute(query, params)
        for hook in self._hooks["after_save"]:
            hook(entity, result)
        return result

    def delete(self, entity_id):
        for hook in self._hooks["before_delete"]:
            hook(entity_id)
        if self._soft_delete:
            return self._db.execute(
                f"UPDATE {self._table} SET deleted_at = NOW() WHERE id = ?", [entity_id]
            )
        return self._db.execute(f"DELETE FROM {self._table} WHERE id = ?", [entity_id])
```'

TASK_K='Analyze this retry mechanism with circuit breaker. What structural patterns and problems do you see?

```python
import time, random

class CircuitBreaker:
    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"

    def __init__(self, failure_threshold=5, reset_timeout=30, half_open_max=3):
        self._state = self.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._half_open_max = half_open_max
        self._last_failure_time = None

    def execute(self, fn, *args, **kwargs):
        if self._state == self.OPEN:
            if time.time() - self._last_failure_time > self._reset_timeout:
                self._state = self.HALF_OPEN
                self._success_count = 0
            else:
                raise Exception("Circuit is open")

        try:
            result = self._retry_with_backoff(fn, *args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _retry_with_backoff(self, fn, *args, max_retries=3, base_delay=1, **kwargs):
        for attempt in range(max_retries):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                time.sleep(delay)

    def _on_success(self):
        if self._state == self.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self._half_open_max:
                self._state = self.CLOSED
                self._failure_count = 0
        else:
            self._failure_count = 0

    def _on_failure(self):
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self._failure_threshold:
            self._state = self.OPEN
```'

TASK_L='Analyze this plugin system with lifecycle hooks. What structural patterns and problems do you see?

```python
class PluginManager:
    def __init__(self):
        self._plugins = {}
        self._hooks = {}
        self._load_order = []
        self._started = False

    def register(self, name, plugin, depends_on=None):
        if self._started:
            raise RuntimeError("Cannot register after start")
        self._plugins[name] = {
            "instance": plugin,
            "depends_on": depends_on or [],
            "state": "registered",
        }

    def start(self):
        self._started = True
        order = self._resolve_order()
        self._load_order = order
        for name in order:
            plugin = self._plugins[name]
            if hasattr(plugin["instance"], "on_init"):
                plugin["instance"].on_init(self._get_api(name))
            plugin["state"] = "initialized"
        for name in order:
            plugin = self._plugins[name]
            if hasattr(plugin["instance"], "on_start"):
                plugin["instance"].on_start()
            plugin["state"] = "started"

    def stop(self):
        for name in reversed(self._load_order):
            plugin = self._plugins[name]
            if hasattr(plugin["instance"], "on_stop"):
                try:
                    plugin["instance"].on_stop()
                except Exception:
                    pass
            plugin["state"] = "stopped"
        self._started = False

    def hook(self, hook_name, callback, plugin_name=None):
        if hook_name not in self._hooks:
            self._hooks[hook_name] = []
        self._hooks[hook_name].append({"fn": callback, "plugin": plugin_name})

    def trigger(self, hook_name, *args):
        results = []
        for entry in self._hooks.get(hook_name, []):
            results.append(entry["fn"](*args))
        return results

    def _resolve_order(self):
        visited, order = set(), []
        def visit(name):
            if name in visited:
                return
            visited.add(name)
            for dep in self._plugins[name]["depends_on"]:
                visit(dep)
            order.append(name)
        for name in self._plugins:
            visit(name)
        return order

    def _get_api(self, plugin_name):
        return {"hook": self.hook, "trigger": self.trigger, "get_plugin": lambda n: self._plugins[n]["instance"]}
```'

TASK_M='Analyze this LRU cache with TTL eviction. What structural patterns and problems do you see?

```python
import time
from collections import OrderedDict

class LRUCache:
    def __init__(self, capacity=100, default_ttl=300):
        self._capacity = capacity
        self._default_ttl = default_ttl
        self._store = OrderedDict()
        self._ttls = {}
        self._stats = {"hits": 0, "misses": 0, "evictions": 0}

    def get(self, key):
        self._evict_expired()
        if key in self._store:
            self._store.move_to_end(key)
            self._stats["hits"] += 1
            return self._store[key]
        self._stats["misses"] += 1
        return None

    def put(self, key, value, ttl=None):
        self._evict_expired()
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = value
        self._ttls[key] = time.time() + (ttl or self._default_ttl)
        while len(self._store) > self._capacity:
            evicted_key, _ = self._store.popitem(last=False)
            del self._ttls[evicted_key]
            self._stats["evictions"] += 1

    def delete(self, key):
        if key in self._store:
            del self._store[key]
            del self._ttls[key]
            return True
        return False

    def _evict_expired(self):
        now = time.time()
        expired = [k for k, exp in self._ttls.items() if exp <= now]
        for key in expired:
            del self._store[key]
            del self._ttls[key]
            self._stats["evictions"] += 1

    def stats(self):
        return {**self._stats, "size": len(self._store), "capacity": self._capacity,
                "hit_rate": self._stats["hits"] / max(1, self._stats["hits"] + self._stats["misses"])}
```'

TASK_N='Analyze this config parser with env/file/defaults merge. What structural patterns and problems do you see?

```python
import os, json

class Config:
    def __init__(self, defaults=None):
        self._layers = []
        self._resolved = None
        if defaults:
            self._layers.append({"source": "defaults", "data": defaults, "priority": 0})

    def load_file(self, path, required=True):
        try:
            with open(path) as f:
                data = json.load(f)
            self._layers.append({"source": f"file:{path}", "data": data, "priority": 10})
            self._resolved = None
        except FileNotFoundError:
            if required:
                raise
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {path}: {e}")

    def load_env(self, prefix="APP_", mapping=None):
        data = {}
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower()
                if mapping and config_key in mapping:
                    config_key = mapping[config_key]
                data[config_key] = self._coerce(value)
        if data:
            self._layers.append({"source": "env", "data": data, "priority": 20})
            self._resolved = None

    def get(self, key, default=None):
        resolved = self._resolve()
        keys = key.split(".")
        current = resolved
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        return current

    def _resolve(self):
        if self._resolved is not None:
            return self._resolved
        self._resolved = {}
        for layer in sorted(self._layers, key=lambda l: l["priority"]):
            self._deep_merge(self._resolved, layer["data"])
        return self._resolved

    def _deep_merge(self, base, override):
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def _coerce(self, value):
        if value.lower() in ("true", "false"):
            return value.lower() == "true"
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value
```'

# ---- Domain Tasks ----

TASK_D1='Analyze this contract clause. What structural patterns and problems do you see?

NON-COMPETITION AGREEMENT: During the Term and for a period of twenty-four (24) months following termination for any reason, Employee shall not, directly or indirectly, engage in, own, manage, operate, consult for, or be employed by any business that competes with the Company'\''s core products within any geographic market where the Company has active customers, EXCEPT that: (a) Employee may hold up to 2% of publicly traded securities; (b) Employee may engage in academic research and publication provided no proprietary information is disclosed; (c) in the event of involuntary termination without cause, the restricted period shall be reduced to twelve (12) months, PROVIDED THAT the Company continues to pay Employee'\''s base salary during such period; (d) the Company may, at its sole discretion, waive any portion of this restriction upon written notice. The parties agree that any breach shall cause irreparable harm and that the Company shall be entitled to injunctive relief without bond, in addition to all other remedies available at law or equity. Employee acknowledges that this restriction is reasonable in scope, duration, and geographic reach.'

TASK_D2='Analyze this clinical case. What structural patterns and problems do you see?

CASE PRESENTATION: 47-year-old female, BMI 31, presents with 3-month history of progressive fatigue, intermittent joint pain (bilateral hands, worse in morning, improving with activity), and unexplained weight loss of 8kg. Lab results: ESR 42mm/hr (elevated), CRP 2.8mg/dL (elevated), ANA titer 1:160 (positive, speckled pattern), RF negative, anti-CCP negative, TSH 3.2 (normal), fasting glucose 98mg/dL, CBC unremarkable except mild anemia (Hb 11.2). Physical exam: no synovitis, no rash, mild bilateral hand tenderness at MCP joints without swelling, Raynaud phenomenon noted in cold office. Family history significant for mother with Sjogren syndrome and maternal aunt with lupus. Patient reports increased stress at work, poor sleep quality (4-5 hours), and recently started intermittent fasting. Currently takes only a daily multivitamin and occasional ibuprofen.'

TASK_D3='Analyze this experimental design. What structural patterns and problems do you see?

STUDY: "Effect of Cognitive Load on Moral Judgment Under Time Pressure." Participants (N=120, university students aged 18-25) randomized into 4 conditions: (1) low cognitive load + no time pressure, (2) low load + time pressure (15 seconds per dilemma), (3) high cognitive load (memorize 7-digit number) + no time pressure, (4) high load + time pressure. Each participant evaluates 12 moral dilemmas (6 personal, 6 impersonal, randomized order) on a 7-point Likert scale from "completely unacceptable" to "completely acceptable." Predicted: high load + time pressure increases utilitarian responses to personal dilemmas. Exclusion criteria: philosophy or psychology majors, prior exposure to trolley problems. Analysis plan: 2x2 ANOVA with dilemma type as repeated measure, Bonferroni correction for multiple comparisons. Secondary analysis: response time as covariate, self-reported confidence ratings. IRB approved. Power analysis based on Cohen'\''s d=0.5 suggests 30 per cell is adequate.'

TASK_D4='Analyze this deployment scenario. What structural patterns and problems do you see?

SCENARIO: A hospital is deploying an AI triage system in their emergency department. The system analyzes patient vitals, chief complaint text, and waiting room camera feeds (posture, movement patterns, facial grimacing) to assign acuity levels 1-5. Training data: 50,000 historical ED visits with attending physician triage scores as ground truth. Validation showed: overall accuracy 87%, but sub-group analysis reveals 91% accuracy for patients aged 20-50, 79% for patients over 70, and 72% for pediatric patients. The system also shows 6% lower accuracy for patients who present without a companion versus those accompanied, and 4% lower for non-English chief complaints processed through auto-translation. The hospital plans to deploy in "advisory mode" (nurse sees AI suggestion + confidence score before making their own decision). Hospital administration projects $2.1M annual savings from optimized staffing and reduced over-triage. The vendor'\''s contract includes a clause stating the hospital assumes liability for clinical decisions, and the algorithm is proprietary (no model card, no feature importance disclosure). The nurses'\'' union has not been consulted.'

# ---- Creative/Aesthetic Domain Tasks ----

TASK_D5='Analyze this short story opening. What structural patterns and problems do you see?

The morning light fell through the kitchen window the way it always had, buttering the countertops with the same indifferent gold. Sarah poured her coffee slowly, deliberately, the way you do when you have finally made peace with something.

She had spent three months learning to let go. The therapist had been right about the stages — she had felt each one, recognized them as they arrived like familiar strangers. Now she was here, on the other side, and the coffee tasted exactly the way coffee should taste when you are no longer waiting for someone to walk through the door.

She checked her phone. Nothing. Good. She checked it again.

The garden needed attention. She had let it go wild during the worst of it, but now the roses were asserting themselves, climbing the trellis with an urgency that felt personal. She would tend to them today. She would put on her gloves and cut back the dead growth and that would be the metaphor she needed.

She caught herself rehearsing how she would describe this moment to David, editing the details to sound more resolved than she felt. But David was the reason she was standing here, so she stopped. She poured the coffee down the sink and started again.'

TASK_D6='Analyze this poem. What structural patterns and problems do you see?

The Cartographer'\''s Confession

I have mapped the territories of your absence —
each room a contour line descending
toward the sea-level of before.

The kitchen holds its breath at 40 meters.
The hallway drops precipitously
where your coat hook keeps its vigil.

I triangulate from fixed points:
the coffee cup you left (unwashed, positioned
north-northwest of grief),
the dog-eared Rilke on the nightstand
(elevation: sleepless),
the impression in the mattress
that I chart but cannot fill.

My legend lists the symbols:
dotted lines for paths you took,
solid lines for paths I wished.
But here is the confession, love —
cartographers do not make the land.
I have measured everything except
the distance I invented.'

TASK_D7='Analyze these composition notes. What structural patterns and problems do you see?

COMPOSITION NOTES: "Still Life with Fugue" — for string quartet, approximately 8 minutes.

Opening (mm. 1-24): Viola introduces the principal theme in D minor — a descending chromatic line (D-C#-C-B-Bb) harmonized in open fifths by the cello. The theme'\''s contour evokes a lament bass. Second violin enters with a tonal answer at the dominant (A minor), while the first violin sustains a pedal D above, creating tension between the fugal imitation below and the static harmony above.

Development (mm. 25-72): The theme fragments and migrates through all four voices. At m. 40, the piece modulates to F major (relative major) via a pivot chord (Dm to Dm/F to F), and the mood shifts from lament to what the program notes describe as "acceptance." The descending chromatic line is inverted (ascending) to signify transformation. At m. 56, all four voices converge on a unison A before dispersing into independent contrapuntal lines.

Climax (mm. 73-96): The original descending theme returns in augmentation (half notes) in the cello while the upper voices play rapid sixteenth-note figurations derived from the inverted theme. The key centers shift every two bars (F-G-Ab-Bb-C) in whole-tone ascent. Dynamic marking: fff.

Resolution (mm. 97-112): The piece returns to D minor. The viola restates the opening theme exactly, but now accompanied by sustained major-seventh chords (Dmaj7, Cmaj7, Bbmaj7) in the other voices, creating what the composer calls "nostalgia as dissonance." Final bar: unison D, ppp, with fermata.'

TASK_D8='Analyze this brand redesign brief. What structural patterns and problems do you see?

BRAND REDESIGN BRIEF

Client: Thornfield and Associates (boutique financial advisory, est. 1987). Objective: Modernize brand identity while preserving heritage trust signals. Current brand: Serif logotype (Garamond), navy/gold palette, tagline "Steadfast Counsel Since 1987." Client reports younger HNW prospects (30-45) perceive the brand as "dated" and "stuffy."

Design direction: Primary typeface: Cerebri Sans (geometric sans-serif) for "contemporary sophistication." Secondary typeface: Playfair Display (high-contrast serif) for "heritage moments." Color: Shift from navy (#1B2A4A) to charcoal (#2D2D2D) as primary, retain gold (#C5A572) as accent. Logo: Abstract monogram "T and A" replacing the full wordmark, in Cerebri Sans. Photography: Black-and-white portraiture of advisors, candid rather than posed, "to signal authenticity." Tagline: Replace "Steadfast Counsel Since 1987" with "Wealth, Considered." — removing the founding date to "avoid aging the brand." Digital: Website redesign with scroll-based storytelling, animated data visualizations, chatbot for initial client intake. Collateral: Shift from linen-textured printed materials to digital-first PDFs with interactive charts.

Rationale: "We want to attract the next generation without alienating existing clients. The redesign balances modernity with gravitas."'

# ---- Run one experiment ----

run_experiment() {
    local prompt_name="$1"
    local prompt_file="$2"
    local task_name="$3"
    local task_text="$4"
    local model="$5"
    local outfile="$OUTPUT_DIR/${model}_${prompt_name}_${task_name}.md"

    echo "  Running: $model / $prompt_name / $task_name ..."

    local system_prompt
    system_prompt=$(cat "$prompt_file")

    local start_time=$SECONDS
    cd /tmp
    CLAUDECODE= claude -p \
        --model "$model" \
        --tools "" \
        --system-prompt "$system_prompt" \
        "$task_text" > "$outfile" 2>/dev/null
    local elapsed=$(( SECONDS - start_time ))
    cd - > /dev/null

    echo "    -> Done (${elapsed}s) -> $(wc -l < "$outfile") lines -> $outfile"
}

# ---- Prompt files ----

declare -A PROMPTS
PROMPTS[v4_control]="$PROJECT_DIR/prompts/structure_first_v4.md"
PROMPTS[L5_conditional]="$PROJECT_DIR/prompts/level5_conditional.md"
PROMPTS[L5_generative]="$PROJECT_DIR/prompts/level5_generative.md"
PROMPTS[L5_perspectival]="$PROJECT_DIR/prompts/level5_perspectival.md"
PROMPTS[L5_hybrid]="$PROJECT_DIR/prompts/level5_hybrid.md"
PROMPTS[L5_combined]="$PROJECT_DIR/prompts/level5_combined.md"
PROMPTS[L6_falsifiable]="$PROJECT_DIR/prompts/level6_falsifiable.md"
PROMPTS[L6_orthogonal]="$PROJECT_DIR/prompts/level6_orthogonal.md"
PROMPTS[L7_recursive]="$PROJECT_DIR/prompts/level7_recursive.md"
PROMPTS[L7_metacausal]="$PROJECT_DIR/prompts/level7_metacausal.md"
PROMPTS[L7_contradictory]="$PROJECT_DIR/prompts/level7_contradictory.md"
PROMPTS[L7_diagnostic]="$PROJECT_DIR/prompts/level7_diagnostic_gap.md"
PROMPTS[L7_relay_mechanism]="$PROJECT_DIR/prompts/level7_relay_mechanism.md"
PROMPTS[L8_recursive_meta]="$PROJECT_DIR/prompts/level8_recursive_meta.md"
PROMPTS[L8_mechanism_dialectic]="$PROJECT_DIR/prompts/level8_mechanism_dialectic.md"
PROMPTS[L8_generative]="$PROJECT_DIR/prompts/level8_generative.md"
PROMPTS[L8_generative_v2]="$PROJECT_DIR/prompts/level8_generative_v2.md"
PROMPTS[L8_relay_construction]="$PROJECT_DIR/prompts/level8_relay_construction.md"
PROMPTS[L9_resilience]="$PROJECT_DIR/prompts/level9_resilience.md"
PROMPTS[L9_counter_construction]="$PROJECT_DIR/prompts/level9_counter_construction.md"
PROMPTS[L9_recursive_construction]="$PROJECT_DIR/prompts/level9_recursive_construction.md"
PROMPTS[L9_combined_BC]="$PROJECT_DIR/prompts/level9_combined_BC.md"
PROMPTS[L10_category_dissolution]="$PROJECT_DIR/prompts/level10_category_dissolution.md"
PROMPTS[L10_third_construction]="$PROJECT_DIR/prompts/level10_third_construction.md"
PROMPTS[L10_double_recursion]="$PROJECT_DIR/prompts/level10_double_recursion.md"
PROMPTS[L11_constraint_escape]="$PROJECT_DIR/prompts/level11_constraint_escape.md"
PROMPTS[L11_acceptance_design]="$PROJECT_DIR/prompts/level11_acceptance_design.md"
PROMPTS[L11_conservation_law]="$PROJECT_DIR/prompts/level11_conservation_law.md"

declare -A TASK_TEXTS
# Code tasks
TASK_TEXTS[task_A]="$TASK_A"
TASK_TEXTS[task_F]="$TASK_F"
TASK_TEXTS[task_G]="$TASK_G"
TASK_TEXTS[task_H]="$TASK_H"
TASK_TEXTS[task_I]="$TASK_I"
TASK_TEXTS[task_J]="$TASK_J"
TASK_TEXTS[task_K]="$TASK_K"
TASK_TEXTS[task_L]="$TASK_L"
TASK_TEXTS[task_M]="$TASK_M"
TASK_TEXTS[task_N]="$TASK_N"
# Domain tasks
TASK_TEXTS[task_D1]="$TASK_D1"
TASK_TEXTS[task_D2]="$TASK_D2"
TASK_TEXTS[task_D3]="$TASK_D3"
TASK_TEXTS[task_D4]="$TASK_D4"
# Creative/aesthetic tasks
TASK_TEXTS[task_D5]="$TASK_D5"
TASK_TEXTS[task_D6]="$TASK_D6"
TASK_TEXTS[task_D7]="$TASK_D7"
TASK_TEXTS[task_D8]="$TASK_D8"

# ---- Filter and run ----

echo "========================================"
echo " AGI in md — Experiment Runner"
echo " Model: $MODEL"
echo " Task filter: $TASK_FILTER"
echo " Prompt filter: $PROMPT_FILTER"
echo "========================================"
echo ""

PROMPT_KEYS=(v4_control L5_conditional L5_generative L5_perspectival L5_hybrid L5_combined L6_falsifiable L6_orthogonal L7_recursive L7_metacausal L7_contradictory L7_diagnostic L7_relay_mechanism L8_recursive_meta L8_mechanism_dialectic L8_generative L8_generative_v2 L8_relay_construction L9_resilience L9_counter_construction L9_recursive_construction L9_combined_BC L10_category_dissolution L10_third_construction L10_double_recursion L11_constraint_escape L11_acceptance_design L11_conservation_law)
TASK_KEYS=(task_A task_F task_G task_H task_I task_J task_K task_L task_M task_N task_D1 task_D2 task_D3 task_D4 task_D5 task_D6 task_D7 task_D8)

count=0
for pname in "${PROMPT_KEYS[@]}"; do
    if [[ "$PROMPT_FILTER" != "all" && "$PROMPT_FILTER" != "$pname" ]]; then
        continue
    fi
    for tname in "${TASK_KEYS[@]}"; do
        if [[ "$TASK_FILTER" != "all" && "$TASK_FILTER" != "$tname" ]]; then
            continue
        fi
        run_experiment "$pname" "${PROMPTS[$pname]}" "$tname" "${TASK_TEXTS[$tname]}" "$MODEL"
        count=$((count + 1))
    done
done

echo ""
echo "========================================"
echo " Completed $count experiments"
echo " Results in: $OUTPUT_DIR/"
echo "========================================"
echo ""
echo " Examples:"
echo "   bash run.sh sonnet task_H L8_generative_v2"
echo "   bash run.sh opus task_D1 L8_generative_v2"
echo "   bash run.sh sonnet task_H L7_diagnostic"

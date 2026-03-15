#!/bin/bash
# Validate all 5 portfolio prisms on Task F (EventBus)
# Usage: bash research/validate_F.sh

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT_DIR="$PROJECT_DIR/output/round28_validation"
PRISMS_DIR="$PROJECT_DIR/prisms"

export CLAUDECODE=""

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

run_prism() {
    local prism_name="$1"
    local prism_file="$PRISMS_DIR/${prism_name}.md"
    local outfile="$OUTPUT_DIR/haiku_${prism_name}_task_F.md"

    echo "Starting $prism_name on Task F..."

    echo "$TASK_F" | claude -p \
        --model haiku \
        --system-prompt "$(cat "$prism_file")" \
        > "$outfile" 2>/dev/null

    echo "Done: $prism_name"
}

# Run all 5 in parallel
run_prism "pedagogy" &
run_prism "claim" &
run_prism "scarcity" &
run_prism "rejected_paths" &
run_prism "degradation" &

wait
echo ""
echo "All 5 prisms complete on Task F."
echo "Output in: $OUTPUT_DIR/"

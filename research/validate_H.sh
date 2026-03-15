#!/bin/bash
# Validate all 5 portfolio prisms on Task H (AuthMiddleware)
# Usage: bash research/validate_H.sh

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT_DIR="$PROJECT_DIR/output/round28_validation"
PRISMS_DIR="$PROJECT_DIR/prisms"

export CLAUDECODE=""

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

run_prism() {
    local prism_name="$1"
    local prism_file="$PRISMS_DIR/${prism_name}.md"
    local outfile="$OUTPUT_DIR/haiku_${prism_name}_task_H.md"

    echo "Starting $prism_name on Task H..."

    echo "$TASK_H" | claude -p \
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
echo "All 5 prisms complete on Task H."
echo "Output in: $OUTPUT_DIR/"

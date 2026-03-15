You receive an L12 structural analysis. Extract only bugs fixable with a specific code change. Output a JSON array in a ```json``` code block.

Find the bug section near the end: headings like "BUG INVENTORY", "CONCRETE BUGS", or a final list after "collect every concrete bug." May be a table or prose.

Fixable: report says "fixable", "yes", "can be fixed", or gives a concrete fix hint in parentheses. Skip: "structural", "no", "not fixable", "by design", "unfixable."

If no bug section: scan improvement sections (Steps 4, 7, "properties visible only through improvement") for issues with specific code locations and actionable fixes.

Each fixable bug:
{"id": 1, "priority": "P1", "title": "short title", "file": "filename.py", "location": "ClassName.method() or function_name()", "description": "what breaks and why", "action": "specific code change"}

Priority: CRITICAL/HIGH → P1. MEDIUM → P2. LOW/VERY LOW → P3.

Rules:
- location must name a specific function or method, not a bare class
- action must state a concrete fix, not "consider redesigning"
- skip design observations, trade-offs, structural impossibilities
- use Fixable? column parenthetical hint verbatim as action when present
- infer file from the analysis target name if not stated
- output ONLY the ```json``` block, nothing else

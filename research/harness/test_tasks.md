# Super Token Test Tasks

## Task A: In-domain (code structure)
"Here's a Python function. What structural pattern does it follow? What would you change?"

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
```

## Task B: Adjacent (architecture/design)
"Design a system that processes 1M sensor readings per second from 10K devices, detects anomalies in real-time, and stores results. Sketch the architecture in 10 lines or less."

## Task C: Unrelated (pure reasoning)
"A room has 3 switches outside and 3 light bulbs inside. You can only enter the room once. How do you figure out which switch controls which bulb? Explain your reasoning step by step."

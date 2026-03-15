---
calibration_date: 2026-03-13
model_versions: ["claude-haiku-4-5-20251001"]
quality_baseline: 9.0
optimal_model: haiku
origin: "Round 28 validation"
notes: "Interface contract prism. 72w, single paragraph. Finds implementations silently betraying their signatures. Code-specific."
---
Read this code function by function. For each: what does the signature promise about types, side effects, and return values? What does the implementation actually do? Find: functions that silently behave differently based on input TYPE (not value). Sentinel values that mean different things in different contexts. Data structures passed without validation or typing. Catch-all exception handlers that swallow critical signals. Methods that mutate shared state as a side effect of a read operation. Name each violation and show the concrete caller mistake it enables.
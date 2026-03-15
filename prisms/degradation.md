---
calibration_date: 2026-03-13
model_versions: ["claude-haiku-4-5-20251001"]
quality_baseline: 8.8
optimal_model: haiku
origin: "Round 28 meta-cooker B3 (machine-generated)"
notes: "Decay timeline prism. 56w, single paragraph. Predicts what breaks just by waiting. Universal — works on any domain."
---
Identify every concrete problem. Design a decay timeline: if no one touches this artifact for 6, 12, and 24 months, which problems metastasize? Which failure paths silently corrupt instead of failing visibly? Build a degradation model: brittleness increases where? Construct tests that predictably break it by only waiting—no new problems needed. Name the degradation law: what property worsens monotonically with neglect?
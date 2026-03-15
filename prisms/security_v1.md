---
calibration_date: 2026-03-13
model_versions: ["claude-haiku-4-5-20251001"]
quality_baseline: 8.5
optimal_model: haiku
origin: "VPS Mar 13 sweep, scored R38"
notes: "Security prism. ~130w, 3-step SDL. Trust Map → Exploit Chain → Trust Boundary. Code-specific."
---
Execute every step below. Output the complete analysis.

## Step 1: The Trust Map
Trace every point where this code receives input from outside its boundary — function parameters, environment variables, configuration, user data, or other modules. For each entry point: what does the code assume about the input? Which assumptions are checked and which are trusted implicitly?

## Step 2: The Exploit Chain
For each unchecked assumption: what specific malicious input would violate it? Trace the damage path — where does the bad input flow, what does it corrupt, and what is the worst outcome? Classify: injection (input becomes code/command), escalation (input bypasses access control), or corruption (input breaks internal state). Continue for each unchecked trust point.

## Step 3: The Trust Boundary
Name the design decision that determines where trust is verified and where it's assumed. State the conservation law: what two security properties does this design trade off? Output a table: Entry Point | Assumption | Checked? | Exploit | Classification | Trust Decision.

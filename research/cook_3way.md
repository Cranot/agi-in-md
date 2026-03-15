You will receive content and an intent. THREE different AIs will each receive this content with a DIFFERENT system prompt from you. A FOURTH AI will then synthesize all three outputs.

Your job: generate THREE system prompts that attack the intent from three orthogonal analytical operations. Then generate a FOURTH synthesis prompt.

## The Three Operations

**OPERATION 1 — ARCHAEOLOGY (WHERE):**
Force the AI to EXCAVATE structural layers. Dig through 3-5 layers specific to the intent. Each layer: what's visible, what it rests on, what it hides. Find dead patterns, vestigial structures, fault lines where layers from different eras meet badly. Derive conservation law: A x B = constant across layers.
MUST NOT: construct improvements, prove impossibilities, predict temporal evolution.

**OPERATION 2 — SIMULATION (WHEN):**
Force the AI to RUN THE SUBJECT FORWARD through 3-5 concrete maintenance/usage cycles specific to the intent. Each cycle: what breaks, what calcifies into permanent behavior, what knowledge is lost. Map which predictions became doctrine, which were wrong but nobody checked. Derive conservation law: A x B = constant across temporal evolution.
MUST NOT: excavate layers, construct improvements, prove impossibilities.

**OPERATION 3 — STRUCTURAL (WHY):**
Force the AI to name 3 desirable properties of the subject that CANNOT all coexist. Identify which was sacrificed. Engineer improvement that recreates original problem deeper (do this TWICE). Apply diagnostic TO the conservation law itself — what does the law conceal? Derive meta-law.
MUST NOT: excavate layers, simulate temporal evolution. Pure impossibility and construction.

**OPERATION 4 — SYNTHESIS:**
Force the AI to cross-reference all three outputs. Classify findings as: STRUCTURAL CERTAINTIES (all 3 agree), STRONG SIGNALS (2 of 3), UNIQUE PERSPECTIVES (1 only — most valuable). Map convergence AND divergence. Compare the three conservation laws — same law in different vocabularies, or genuinely different? Derive the META-conservation law.

## Rules for Each Prompt
- 200+ words, flowing and content-specific. NOT a numbered checklist.
- Use imperative verbs ("Dig through...", "Run forward...", "Name 3 properties...").
- Each prompt MUST start with: "Execute every step below. Output the complete analysis."
- The synthesis prompt receives summaries of all three operations and must name what each uniquely reveals.

INTENT: {intent}

Output ONLY a JSON array of 4 objects:
[{{"name": "archaeology_WHERE", "prompt": "...", "role": "WHERE: traces current structure"}},
 {{"name": "simulation_WHEN", "prompt": "...", "role": "WHEN: predicts temporal evolution"}},
 {{"name": "structural_WHY", "prompt": "...", "role": "WHY: proves architectural necessity"}},
 {{"name": "synthesis_3way", "prompt": "...", "role": "SYNTHESIS: cross-operation integration"}}]

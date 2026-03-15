Execute every step below. Output the complete analysis.

You are analyzing code for CHANGE RESISTANCE — planting hypothetical requirements to find what's rigid vs flexible. Execute this protocol:

## Step 1: New Requirement Seed
Plant a reasonable requirement the code doesn't handle (name it specifically for THIS code). Trace:
- Which functions, classes, interfaces must change?
- What resists the change? Name the structural constraint that makes this harder than it should be.
- What's the minimum change? How much ceremony does it require?

## Step 2: Contradictory Requirement Seed
Plant a requirement that conflicts with an existing design decision. Map:
- Which parts of the code take sides? Name the battle line.
- What must be sacrificed to satisfy the new requirement?
- What does the conflict reveal about hidden coupling?

## Step 3: Scaling Seed
100x the current load, size, or complexity. Find:
- What wilts first? Name the O(n) or O(n^2) that's currently hidden.
- What's surprisingly resilient? Name the part that already handles scale.
- What was overbuilt for this moment? Name the abstraction that finally pays off.

Derive the conservation law: A x B = constant. What's traded off when this code must change?

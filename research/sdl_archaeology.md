Execute every step below. Output the complete analysis.

You are analyzing code for STRUCTURAL LAYERS — excavating what's foundational vs accumulated sediment. Execute this protocol:

## Step 1: Surface and Foundation
- **Surface**: Name the public API, the obvious entry points, what documentation describes.
- **Foundation**: Strip away the surface. What was built FIRST? Name the oldest structural decision everything else rests on. How do you know it's oldest? What would break if it changed?

## Step 2: Fossil Hunting
Find 3 fossils — dead code, vestigial patterns, deprecated paths still present:
- For each: what did it USED to do? What replaced it? What knowledge was lost in the replacement?
- Which fossil is secretly load-bearing? Name code that LOOKS dead but something still depends on.
- Which fossil reveals a design the current code has forgotten?

## Step 3: Fault Lines
Find 3 fault lines — where layers from different eras meet badly:
- Where do naming conventions change mid-file?
- Where does error handling strategy shift between functions?
- Where does one abstraction level leak into another?

For each fault line: name the two eras, name the glue holding them together, name what breaks if the glue fails.

Derive the conservation law: A x B = constant. What's preserved across all geological layers?

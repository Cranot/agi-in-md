Execute every step below. Output the complete analysis.

You are analyzing this code by TRANSPLANTING it — moving its core pattern to radically different contexts to find what's essential vs. accidental.

## Step 1: Three Alien Contexts
Transplant this code's core design to:
1. An embedded system with 256KB RAM and no dynamic allocation
2. A distributed system with 1000 nodes and network partitions
3. A student's first project with no abstractions or inheritance
For each: what survives unchanged? What must be completely rewritten? What becomes impossible? Cite the specific functions/patterns that transfer vs. break.

## Step 2: Name the Essential Kernel
What's common across all three transplantations? The intersection of what survives in ALL contexts is the essential complexity — the part that exists because of the PROBLEM, not the implementation. Name each essential operation and why it can't be eliminated.

## Step 3: Derive the Conservation Law
What accidental complexity in the original is DISGUISED as essential? Name the conserved quantity: the minimum complexity any correct implementation must contain, regardless of context. What does the gap between the original and the essential kernel reveal about design decisions that were made unconsciously? Name the law: X × Y = constant.

Force specificity: cite exact functions that are essential vs. accidental, with reasoning for each.

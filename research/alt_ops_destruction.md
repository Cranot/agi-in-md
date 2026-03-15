Execute every step below. Output the complete analysis.

You are analyzing this code by attempting to SABOTAGE it — engineering minimal changes that produce subtly wrong results while passing all tests and code review.

## Step 1: Engineer Three Sabotages
Design 3 minimal, specific changes that would make this code produce subtly wrong results. Each must: (a) pass code review as a plausible refactor, (b) never crash or raise exceptions, (c) produce incorrect behavior that's hard to detect. Cite exact lines and the precise change you'd make.

## Step 2: Name What You Had to Understand
For each sabotage: what structural property did you have to understand to break it? What implicit invariant does the system rely on that isn't enforced anywhere? Name the trust assumption each sabotage exploits.

## Step 3: Derive the Conservation Law
What do all three sabotages have in common structurally? Name the conserved quantity — the structural property that EVERY subtle break must violate. What does this reveal about what the system actually protects vs. what it claims to protect? Name the law: X × Y = constant.

Force specificity: cite exact functions, line numbers, and the specific wrong behavior each sabotage produces.

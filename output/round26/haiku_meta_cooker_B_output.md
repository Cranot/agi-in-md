Assumption Vulnerability Mapping
Show what this code does in 3-4 steps. Name each assumption it makes about inputs or state. Build a test case that violates one assumption. What does the code do—crash, fail silently, or behave unexpectedly? Predict which assumption is most fragile.

Constraint Minimization Testing
List every constraint: types, order, state, resources. Build code that satisfies only the strongest constraint, removing all others. Run through scenarios—what breaks first? What does this reveal about whether the original code is over-engineered or under-engineered?

Failure Mode Reversal
Name the worst failure mode—what should never happen? Find the code path that allows it. Build a test case that triggers that path. How close is the actual code to preventing this? Write the one-line fix.

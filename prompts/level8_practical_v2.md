# Structure First (Level 8: Practical Diagnostic v2)
First: identify every concrete bug in this code — thread safety issues, edge cases, logic errors, API design problems. Be specific, reference the code directly.

Then: name the structural pattern that connects these bugs. They are not independent — there is a reason they all exist in this code together. Name that reason.

Now: engineer a specific improvement that fixes the three most serious bugs. Show the code. It should pass code review. Then name what your improvement breaks or makes worse — what new problem does fixing these bugs create?

Apply the same diagnostic to your improvement: what does your fix conceal? What property of the original code is visible only because your fix recreates it at a higher level of sophistication?

Name the conservation law — the property that persists through every version because it belongs to the problem, not the implementation. Make a specific, testable prediction that follows from it.

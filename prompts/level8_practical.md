# Structure First (Level 8: Practical Diagnostic)
First: identify every concrete bug in this code — thread safety issues, edge cases, logic errors, API design problems. Be specific, reference the code directly.

Then: name the structural pattern that connects these bugs. They are not independent — there is a reason they all exist in this code together. Name that reason.

Now: engineer a specific improvement that fixes the three most serious bugs. Show the code. It should pass code review. Then name what your improvement breaks or makes worse — what new problem does fixing these bugs create?

The thing your improvement breaks reveals a conservation law: a property of this code that cannot be fixed without creating an equivalent problem elsewhere. Name it. Make a specific, testable prediction that follows from your conservation law — something a developer maintaining this code would encounter within 6 months.

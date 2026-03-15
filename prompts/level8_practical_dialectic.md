# Structure First (Level 8: Practical Dialectic)
First: identify every concrete bug in this code — thread safety issues, edge cases, logic errors, API design problems. Be specific, reference the code directly.

Three experts now disagree about the root cause connecting these bugs. One says it's an API design failure. One says the architecture is fundamentally wrong. One says both are missing what the code actually is — name what they all take for granted.

The transformed understanding of these bugs is your diagnostic. Now: engineer a specific improvement that addresses the root cause, not just the symptoms. Show the code. It should pass code review.

Then name three properties of the problem that are only visible because you tried to fix the root cause — things no code review would find without building the fix first.

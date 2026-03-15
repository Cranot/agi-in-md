# Structure First (Level 8: Evolution)
First: identify every concrete bug in this code.

Now simulate three rounds of maintenance by different developers:

Round 1: A junior developer fixes the most obvious bug. Show the patch. What new bug does their fix introduce?

Round 2: A senior developer reviews the junior's fix and the remaining issues. They refactor. Show the refactored code. What does the senior miss because the junior's fix obscured it?

Round 3: An incident occurs in production. The on-call engineer adds a hotfix. What was the incident, and why couldn't the senior's refactor prevent it?

Name the property of this code that survives all three rounds of maintenance. Why can't three competent developers eliminate it?

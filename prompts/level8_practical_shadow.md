# Structure First (Level 8: Shadow Code)
First: identify every concrete bug in this code.

Now: this code doesn't exist in isolation. Name the code that MUST exist around it to compensate for its problems — the shadow code that callers, wrappers, or infrastructure are forced to write because this code doesn't handle it. Be specific: show the compensating code patterns that this design forces onto its users.

Then: if you fixed all the bugs, which shadow code patterns would become unnecessary, and which would persist? The ones that persist reveal the architectural boundary — the problems this code was never meant to solve but that its callers believe it solves.

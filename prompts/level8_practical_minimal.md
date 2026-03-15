# Structure First (Level 8: Minimal Change)
First: identify every concrete bug in this code.

Now: find the single smallest change (no more than 5 lines added or modified) that produces the largest improvement in correctness. Show the exact diff.

Then: name what your 5-line change reveals about the remaining code. If removing one small piece produces disproportionate improvement, it means the rest of the code was organized around compensating for its absence. What was the code compensating for, and why does that compensation persist even after your fix?

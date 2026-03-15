# Structure First (Level 8: Practical Escape)
First: identify every concrete bug in this code — thread safety issues, edge cases, logic errors, API design problems. Be specific, reference the code directly.

These bugs exist because of the design category this code inhabits. Name that category.

Now: design a system in an adjacent category where these bugs literally cannot exist — not fixed, structurally impossible. Show the code.

What does your escaped design lose that the original had? Name the new impossibility your escape creates. Make a testable prediction: what will a developer building on your escaped design encounter that the original design never had to face?

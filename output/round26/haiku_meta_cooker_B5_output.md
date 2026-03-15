**Blind Spot 1: Root Causes (Looking Backward)**
First: identify every concrete bug. Then trace backward: for each bug, what design decision or constraint made it inevitable? Build a dependency map showing (decision → constraint → bug). Predict: which bugs are symptoms, not root causes? Test: remove the root decision; do three bugs vanish together?

**Blind Spot 2: Bug Interdependencies (Coupling)**
First: identify every concrete bug. Build a conflict matrix: can each pair of bugs be fixed independently, or does fixing one block the other? Write: which bugs are load-bearing—their fixes enable other fixes? Which are parasitic—they hide because other bugs exist? Test: bugs fixed in wrong order fails; right order succeeds?

**Blind Spot 3: Silent Degradation (Inaction Over Time)**
First: identify every concrete bug. Design a decay timeline: if no one touches this code for 6/12/24 months, which bugs metastasize? Which error paths silently corrupt data instead of failing? Build a degradation model: brittleness increases where? Test: predictably break the system by only waiting—no new bugs needed.

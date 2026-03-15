# Opus Vanilla

Input: What fundamental trade-off is baked into every todo app architecture? Not a preference or a design choice — a genuine impossibility where having property A structurally prevents having property B, regardless of how clever the implementation is.

---

**Task granularity vs. list usability.** And it's not a spectrum — it's a genuine impossibility.

**Property A: Every item is immediately actionable** (no hidden sub-tasks, no ambiguity about what "done" means).

**Property B: The list is cognitively manageable** (you can scan it, prioritize across it, and maintain it without the maintenance itself becoming work).

Why these are structurally opposed: actionability *requires* decomposition. "Redesign the auth system" isn't actionable — it contains dozens of hidden decisions. But decomposing it into actionable atoms ("read current middleware," "list permission edge cases," "draft new role schema"...) increases list size, and list size destroys the ability to see the whole, prioritize across items, and maintain the list. At some point the cost of managing the list exceeds the cost of just doing the work.

**Every todo app architecture picks a side:**
- **Flat lists** (Apple Reminders, plain text): manageable but not actionable. Items are vague commitments that require re-decomposition at execution time.
- **Hierarchical/nested** (Notion, Workflowy): actionable but unmanageable. The structure that makes items precise also makes the system itself a project to maintain.
- **Kanban/status boards** (Trello): dodge the trade-off by making *flow* visible instead of *content* — but each card still faces the same dilemma internally.

No architecture resolves this because the impossibility isn't in the tool — it's in the nature of tasks themselves. A task description is a prediction about future work. Making predictions precise enough to act on requires information you only get by doing the work. The representation that would make every item unambiguous requires the knowledge that completing the item would produce.

That's why every todo system eventually becomes either a graveyard of vague intentions or a second job to maintain.

**PROMPT 1: Dependency Propagation Chain**

TASK: Trace outward from circuit breaker into calling code. CONSTRUCT: Show 3 different call-site patterns this code FORCES into its callers. BUILD: For each pattern, write the adapter/wrapper code necessary to work safely around the bug. FIND: What property must all three adapters share? What does that conserved property reveal about the bug's systemic cost the isolated analysis misses?

---

**PROMPT 2: Implicit Contract Extraction**

TASK: Extract undocumented contracts from code usage. CONSTRUCT: Find 3 real call sites using this code. Document the implicit precondition each assumes—never stated in docstrings. BUILD: Write a test violating one precondition. Capture the failure. FIND: Which precondition violation is "catastrophically silent" (wrong output, not error)? How many developers would make that assumption reading this code?

---

**PROMPT 3: Architectural Constraint Propagation**

TASK: Map this code's design assumptions forward into future architecture. CONSTRUCT: Design ONE feature that becomes impossible because this code exists. Design the alternative: what feature becomes mandatory? BUILD: Write pseudocode for both—feature-that-won't-work and feature-that-must-exist. FIND: How does accepting this impossible constraint redistribute coupling in the broader system? Where does complexity migrate?

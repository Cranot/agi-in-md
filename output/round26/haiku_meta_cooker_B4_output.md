**Prompt 1: Implicit Contracts**
"Identify implicit contracts: preconditions callers must satisfy, postconditions code guarantees—neither documented. Design a caller that violates each contract invisibly. Show which violations corrupt state silently, which fail visibly. Engineer enforcement: add validation. Show code. Which violations become detectable? Which impossible? Each enforcement creates a new implicit contract. Name it. What reasonable caller violates it?"

**Prompt 2: Ownership and Lifecycle**
"Trace resource ownership at every code point: allocator, owner, user, deallocator. Find implicit ownership transfers. Design what happens if two owners exist or ownership vanishes. Show the code paths. Which deadlocks emerge? Engineer explicit ownership semantics: show code markers for transfer points. What lifecycle guarantee becomes impossible that wasn't before? What becomes possible? Name the ownership conservation law."

**Prompt 3: Observability Blindness**
"Separate observable state from hidden state. For each hidden element, show how concurrent changes corrupt it invisibly. Design full observability: instrument all state transitions. Show code. What ordering assumptions fail under instrumentation? What race conditions become impossible to trigger? What timing properties become untestable? Name the observability paradox: what can instrumenting reveal that testing cannot?"

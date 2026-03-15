A system prompt scored 9.5/10 analyzing a circuit breaker. Here is what it found:

FOUND: Race conditions, undefined HALF_OPEN failure path, retry-in-circuit-breaker contradiction, exception swallowing, failure count persistence. Named "Visibility Inversion Theorem" — fixing race conditions creates invisible performance degradation. Built alternative system taking all rejected design paths. Mapped which bugs migrate between visible and hidden.

MISSED (confirmed by comparing against 3 other 9/10 analyses):
1. What the code ASSUMES will never run out (scarcities: atomicity, monotonic time, semantic information, time-windowed history)
2. The implicit contracts between code and callers (9 undocumented preconditions, each enforcement creates new contract)
3. What happens to bugs over TIME without anyone touching the code (6→12→24 month decay, oscillation loops, recovery becomes impossible)

The 9.5 sees the code's PRESENT state deeply. The 9/10s each see one dimension the 9.5 is blind to. But ALL FOUR share a blind spot: they analyze the code as an ISOLATED artifact. None traces how the code's design decisions propagate OUTWARD — into the codebase that wraps it, into the mental models of developers who maintain it, into the architecture that grows around its assumptions.

Design THREE prompts. Each must find something ALL FOUR missed. Each must include a construction step (build something, show code). Under 80 words each. Output only the prompts.
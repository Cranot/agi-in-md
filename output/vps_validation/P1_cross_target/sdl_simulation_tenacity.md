# SDL-Simulation Analysis: Tenacity Retry Library

## Step 1: New Developer Cycle
**Assumption Violation**: Developers will misunderstand `retry_with()` as creating independent retry strategies when it actually shares statistics via the wrapped function's attribute. They'll modify shared statistics unknowingly.

**Silent Breakage**: The `statistics` dictionary accumulation in `BaseRetrying` will silently grow until it hits the 100-item limit and clears, losing historical data without warning.

**Copy-Paste Trap**: The `copy()` method's `_unset` pattern looks like a template for configuration inheritance, but its specific handling of `_unset` as a sentinel value makes it dangerous to generalize elsewhere in the codebase.

## Step 2: Knowledge Loss Cycle
**Cargo Cult Decisions**:
1. The `iter_state` contextvar pattern - preserved without understanding its purpose in handling retry iteration state across async boundaries
2. The `AttemptManager` context manager pattern - copied for other resource management without understanding its specific retry state integration
3. The action queue pattern in `_post_retry_check_actions` - preserved as a template without understanding its specific retry flow control logic

**Unfixable Bug**: The coupling between statistics clearing and attempt number tracking in `begin()` will eventually cause silent data loss when statistics grow beyond the 100-item limit, requiring knowledge of the internal implementation details to debug.

**Permanent Temporary Code**: The `RetrySignal` exception class, originally intended for internal retry control, will become a public API as developers discover it and use it for inter-component communication, despite being marked as "not a real exception."

## Step 3: Calcification Map
**Internal Dependency**: The `_iter_state_var` contextvar has become an implicit contract for retry state management, making it impossible to refactor the iteration logic without breaking consumers who depend on this global state access.

**Performance Assumption**: The `statistics` dictionary is treated as lightweight memory storage without considering that it accumulates across retry attempts, eventually becoming a memory leak in long-running processes.

**Happy Error Path**: The `RetryError` exception handling path has become the normal operation flow for successful retries, with the `reraise` flag creating a confusing inversion where error handling is the primary execution path.

## Conservation Law: A x B = constant
As the Tenacity library ages, **code clarity** is traded for **flexibility**. The library's powerful retry composition capabilities come at the cost of increasingly complex internal state management and implicit contracts that become harder to understand and maintain over time.

# Structural Layer Analysis: Starlette Routing

## Step 1: Surface and Foundation

**Surface**: The public API consists of:
- `Route` class for individual HTTP route handlers
- `Mount` class for sub-application mounting with path delegation
- `Router` class for route composition and dispatch
- `request_response` decorator for converting synchronous functions to async
- `compile_path` function for path pattern compilation

**Foundation**: The oldest structural decision is the `BaseRoute` abstract base class. It defines the fundamental interface (`.matches()`, `.url_path_for()`, `.handle()`, `__call__()`) that all routing mechanisms must implement. This is the bedrock - everything else builds on this pattern. If this changed, the entire routing system would collapse.

## Step 2: Fossil Hunting

**Fossil 1**: `request_response` decorator
- **What it used to do**: Convert synchronous functions to async handlers using `run_in_threadpool`
- **What replaced it**: The modern async/await pattern throughout the codebase
- **Knowledge lost**: The distinction between sync and async handlers has blurred, making performance implications less visible
- **Load-bearing status**: Still used for legacy function-based endpoints, but most modern code bypasses it

**Fossil 2**: `NoMatchFound` exception and its parameter validation
- **What it used to do**: Detailed error messages with parameter names when URL generation failed
- **What replaced it**: Simpler exception handling with generic "No route exists" messages
- **Knowledge lost**: The debugging context of which specific parameters were missing
- **Load-bearing status**: Actually load-bearing - the exception is still thrown in `url_path_for` methods and propagates through the Router

**Fossil 3**: The `Match` enum (NONE/PARTIAL/FULL)
- **What it used to do**: Provided nuanced matching results for partial route overlaps
- **What replaced it**: Boolean-like match results with more direct boolean logic in handlers
- **Knowledge lost**: The semantic clarity of partial vs full matching is now embedded in conditional logic
- **Load-bearing status**: Secretly load-bearing - the Router still uses PARTIAL matches for fallback routing

## Step 3: Fault Lines

**Fault Line 1**: Function-based vs class-based routing eras
- **Era 1**: Early Starlette with function-based endpoints requiring `request_response` wrapper
- **Era 2**: Modern ASGI applications with built-in async support
- **Glue**: The `request_response` decorator in the `Route.__init__` method
- **What breaks if glue fails**: Legacy synchronous endpoints would fail to execute

**Fault Line 2**: Mount routing vs direct routing conventions
- **Era 1**: Direct path matching in `Route.matches()` with simple regex
- **Era 2**: Mount point delegation with complex path parameter handling in `Mount.matches()`
- **Glue**: The `path_regex` compilation and `child_scope` pattern propagation
- **What breaks if glue fails**: Mount points would lose parameter passing to sub-apps

**Fault Line 3**: URL generation strategies
- **Era 1**: Simple string replacement in `replace_params()`
- **Era 2**: Complex recursive URL building in `Mount.url_path_for()` with nested route support
- **Glue**: The `NoMatchFound` exception propagation and parameter validation
- **What breaks if glue fails**: URL generation would fail for mounted applications

## Conservation Law: A × B = constant

The preserved constant across all geological layers is **routing consistency**. The system maintains:

**A (Interface Stability)**: The `BaseRoute` abstract interface has remained stable despite internal implementation changes
**B (Behavioral Predictability)**: Route matching and URL generation behavior remains consistent across different routing mechanisms

The product A × B = routing consistency remains constant. Even as internal implementations evolved (from function-based to class-based, simple regex to complex pattern matching), the external contract and predictable behavior have been preserved.

First: Starlette's routing system conceals a fundamental structural impossibility - it claims to be both **declarative** (routes defined statically) and **dynamic** (runtime parameter extraction and transformation), but these properties are mutually exclusive in a system that must handle both static compilation and dynamic runtime matching with perfect correctness. The routing system cannot simultaneously guarantee compile-time path correctness and runtime parameter conversion safety without introducing a third property that gets sacrificed.

Three experts test this claim:

**Defender (Route Designer)**: "The system IS declarative and dynamic! Routes are defined statically via decorators and class instantiation (declarative), while runtime parameter extraction happens in `matches()` and `url_path_for()` (dynamic). The system maintains correctness through `compile_path()` which validates parameter names at construction and `param_convertors` which ensure type safety at runtime. The design achieves both properties through careful separation of concerns."

**Attacker (Systems Thinker)**: "This claim fails on the simplest test: `url_path_for(name, **path_params)` requires runtime parameter validation against statically defined routes. When `NoMatchFound` is raised because parameters don't match, you've broken declarativity - the declaration wasn't actually complete! You've created a system where static route definitions are conditional on runtime parameter validation, making your declarative foundation fundamentally dynamic. This creates an information gap where route definitions exist in multiple states: compiled, validated, and executed."

**Prober (Philosopher of Systems)**: "Both experts assume 'correctness' means the same thing. What if we reframe: the system sacrifices **composability**? Every route contains embedded knowledge about its own parameter structure (`param_convertors`, `path_regex`), preventing true composition. When you nest Mount routes, each level duplicates parameter validation logic. The system isn't declarative OR dynamic - it's **replicative**. And what about the silent assumption that routes are fixed? What if routes needed to be runtime-creatable while maintaining compile-time safety? That would require a third property - **reconfigurability** - which is currently impossible because your parameter converters are frozen at construction."

**Transformed Claim**: Starlette's routing system cannot achieve **compile-time path safety**, **runtime parameter flexibility**, and **true composability** simultaneously. The system sacrifices composability by embedding route-specific parameter validation logic in each route instance, preventing hierarchical route composition without information duplication.

**Concealment Mechanism**: The system hides its structural problems through **information laundering** - compile-time path regex generation and runtime parameter conversion appear as separate concerns, but they're actually coupled through the `param_convertors` dictionary. This coupling creates a dependency between static compilation and runtime execution that violates the open-closed principle.

**Applied Diagnostic**: Look at `compile_path()` - it generates both regex patterns AND parameter convertors, but these two things have different lifecycles. The regex pattern belongs to the static route definition, while the convertors belong to runtime execution. By coupling them, the system prevents independent evolution of path matching and parameter conversion.

**Improvement to Deepen Concealment**: Introduce a "parameter validation cache" in `Router.url_path_for()` that stores validation results for parameter patterns. This would make the system appear more efficient while actually making the composition problem worse - now the coupling includes caching logic across route boundaries.

**Three Properties Revealed by Strengthening**:
1. **Path Parameter Entanglement**: The coupling between path regex and parameter convertors creates a web of dependencies where changing a parameter type requires recompiling the entire route hierarchy
2. **Information Duplication Cascade**: Every route must duplicate validation logic for its segment, creating exponential complexity growth in nested routing scenarios
3. **Runtime-Static State Pollution**: The system's runtime state (`path_params`, `child_scope`) contains information that should belong to the static route definition, making composition impossible without polluting clean abstractions

**Conservation Law**: `Information Purity × Composability = constant`
The routing system maintains information purity by keeping all parameter validation logic within each route (no external dependencies), but this prevents true composability. When you try to achieve composability (as in Mount's route resolution), you must sacrifice information purity by duplicating validation logic across boundaries.

## Claim

**The deepest structural problem: `scope` mutation is the real routing protocol, and the `(Match, child_scope)` return type is functional theater that conceals it.**

`matches()` looks like a pure predicate — takes a scope, returns a value, no visible side effects. But every caller in the codebase unconditionally follows it with `scope.update(child_scope)`. The "return value" is always a deferred mutation. The functional signature is a costume worn by an imperative protocol.

---

## Three Experts

### Defender
The `(Match, child_scope)` pattern is correct and intentional. `Router.app` demonstrates exactly why: it calls `matches()` on *multiple routes* before committing to any scope mutation. The deferred-update pattern is what allows safe backtracking — you accumulate a `partial_scope` and only apply it after exhausting full matches. This *is* functional separation; the mutation is committed deliberately at the decision point, not scattered throughout.

### Attacker
The defender's own example proves the claim. Look at `BaseRoute.__call__`:

```python
match, child_scope = self.matches(scope)
if match == Match.NONE:
    return
scope.update(child_scope)      # ← commits even on PARTIAL
await self.handle(scope, receive, send)
```

A `PARTIAL` match (wrong method) still mutates scope before `handle()` returns a 405. The scope is now permanently modified with a wrong-method match's state — `endpoint`, `path_params` — even though the request was rejected. The mutation isn't committed "deliberately at the decision point." It's committed *whenever the match isn't NONE*. The `Router.app` careful handling and `BaseRoute.__call__` incautious handling are *inconsistent*, which only happens when there's no actual contract governing when mutation is permitted.

### Prober
Both experts assume the mutation is the problem to be solved. But what do they both take for granted? That `scope` *could* be made immutable if the design were better. It cannot. ASGI's entire middleware chain holds a reference to the **same dict object** — downstream middlewares that already have `scope` in their closure would not see updates to a new dict. `scope.update()` is not a design flaw; it's a load-bearing ASGI contract. So the question is not "why is scope mutated?" but "why does `matches()` pretend it isn't?"

---

## Transformation

**Original claim:** `(Match, child_scope)` is functional theater hiding inevitable mutation.

**Transformed claim:** The system cannot separate route resolution from scope mutation because ASGI's reference semantics make mutation *constitutive* of the routing protocol, not incidental to it. The functional interface is not just theatrical — it's actively misleading, because it implies that `matches()` could be called idempotently or in any order, when actually the *sequence* and *selection* of which `scope.update()` commits defines what the request *is* downstream.

**The gap:** The original claim was about aesthetics (false purity). The transformed claim is structural: the design has encoded a sequential, stateful commitment protocol into an interface that looks declarative, and this mismatch is what produces the two specific failures the Attacker and Prober found.

---

## The Concealment Mechanism

**Nominal isolation of concerns.** The codebase names things as if they belong to separate phases:

| Name | Implied phase | Actual role |
|---|---|---|
| `matches()` | Query only | Constructs the state diff that will become the request context |
| `child_scope` | Return value | Deferred mutation payload |
| `handle()` | Execution only | Re-checks routing constraints (method) that `matches()` already evaluated |
| `Match.PARTIAL` | Routing state | Encodes HTTP 405 semantics inside a path-matching type |

Each name reassures the reader that concerns are separated. The `match` result looks like a type-safe enum. The `child_scope` looks like a value. But `PARTIAL` simultaneously means "prefix matched, path unresolved" (for `Mount`) and "path matched, method wrong" (for `Route`). The enum value has two incompatible semantics depending on which class emits it — and `Mount.matches()` *never* returns `PARTIAL`, which means method-negotiation silently stops working through mounted sub-routers.

---

## The Improvement That Deepens Concealment

Replace the `(Match, dict)` tuple with a frozen `MatchResult` dataclass. This passes review easily — named fields, type annotations, encapsulated logic:

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class MatchResult:
    match: Match
    scope_updates: dict[str, Any] = field(default_factory=dict)

    def apply(self, scope: dict) -> None:
        """Commit this match result into the active request scope."""
        scope.update(self.scope_updates)

    @classmethod
    def none(cls) -> "MatchResult":
        return cls(match=Match.NONE)

    @classmethod  
    def partial(cls, **updates) -> "MatchResult":
        return cls(match=Match.PARTIAL, scope_updates=updates)

    @classmethod
    def full(cls, **updates) -> "MatchResult":
        return cls(match=Match.FULL, scope_updates=updates)
```

Update `BaseRoute.__call__` and `Router.app` to use it:

```python
# BaseRoute.__call__
result = self.matches(scope)
if result.match == Match.NONE:
    ...
    return
result.apply(scope)           # ← explicit commit, reads as intentional
await self.handle(scope, receive, send)
```

**Why this passes code review:**
- `frozen=True` signals immutability ✓
- Named `scope_updates` instead of anonymous `child_scope` ✓  
- `.apply()` makes the commit explicit and findable ✓
- Classmethods are self-documenting ✓
- Straightforward refactor, no behavioral change ✓

**Why it deepens concealment:** `frozen=True` now actively misleads. The dataclass *is* immutable — but calling `.apply(scope)` mutates the scope that every other component in the ASGI chain holds a reference to. The immutability guarantee is precisely backwards: the carrier is frozen, the target is not. The word `scope_updates` sounds like a pure value describing a patch, not a deferred side effect. The `.apply()` method normalizes mutation as a deliberate API rather than exposing it as an unavoidable constraint.

---

## Three Properties Only Visible Because We Tried to Strengthen It

**1. The mutation cannot be made optional.** When strengthening, the obvious next step is to make `apply()` return a *new* dict instead of mutating: `return {**scope, **self.scope_updates}`. This immediately breaks ASGI — the entire middleware stack holds references to the original `scope` object, so replacement instead of update silently breaks exception handlers, tracing middleware, and anything that captured `scope` before the router ran. You discover that `scope.update()` is not a design smell to be cleaned — it's the *protocol*. The improvement reveals that the mutation was load-bearing all along.

**2. `scope_updates` is not a diff — it contains the execution target.** When writing the `full()` classmethod and documenting `scope_updates`, you notice that `child_scope` always includes `"endpoint"` — the callable that will execute the request. A "scope update" is carrying both routing metadata *and* the execution handle in an untyped dict. Naming it `scope_updates` implies it's a patch to request context. But it's actually a partially-constructed execution context. The improvement, by naming the field clearly, makes the category error visible: routing context and execution context are co-mingled in a single untyped dict with no schema.

**3. The first-partial-wins policy is a hidden invariant with no representation.** When you try to compose two `MatchResult` objects — say, two routes both return `PARTIAL` — there's no principled way to merge them. Which endpoint wins? Which path params dominate? `Router.app` encodes the answer silently: `if match == Match.PARTIAL and partial is None`. The `and partial is None` clause is a first-one-wins policy with zero documentation, no type enforcement, and no composability. Building `MatchResult` with a `frozen` dataclass invites you to think about composition, which immediately reveals that the policy is baked into imperative loop ordering, not expressed in any interface. The 404/405 discrimination mechanism — the entire reason `PARTIAL` exists — depends on an undocumented, un-typed, first-match policy that the improved design makes structurally incoherent.

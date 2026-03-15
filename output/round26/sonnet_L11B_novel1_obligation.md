## Analysis: ObligationLedger

---

## The Claim

**Deepest structural problem**: `forgive()` violates the cascade invariant that `_cascade_up` establishes throughout the rest of the system. When `fulfill()` reduces a child's amount to zero, it calls `_cascade_up`, which propagates completion upward. When `forgive()` marks a child fulfilled, it does not — leaving parents with `amount == 0` and `fulfilled == False`: zombie obligations.

Trace:
```python
create(A, C, 100)   # oid=0, amount=100
delegate(0, B, 1.0) # oid=0 amount→0, oid=1 amount=100
forgive(1)          # oid=1 fulfilled=True
                    # oid=0: amount=0, fulfilled=False  ← ghost
```

This is falsifiable: `_cascade_up` would have fulfilled oid=0 here (amount==0, all children fulfilled), but `forgive` never calls it.

---

## Three Experts

**Defender**: The claim is correct. `forgive` and `fulfill` are supposed to be symmetric completion paths. Adding `_cascade_up(oid)` at the end of `forgive` closes the gap. The cascade invariant is clearly documented by the structure of `fulfill` itself.

**Attacker**: The cascade bug is a surface symptom. The deeper problem is that `fulfilled` is overloaded — it means "amount reduced to zero by payment," "administratively discharged regardless of amount," and "children covered the full obligation." These are distinct events. Fixing the cascade call treats them as identical, which deepens the underlying confusion.

**Prober**: Both of you assume cascade propagation is the right semantic. But the prober asks: what does it *mean* for a parent obligation to be fulfilled when its child was forgiven rather than paid? If A delegates to B and B's obligation is forgiven, is A's obligation truly discharged or merely papered over? Both of you take for granted that `fulfilled` has a single canonical meaning across all paths. It doesn't. The cascade invariant has no coherent definition to violate or maintain.

---

## The Transformed Claim

**Original**: `forgive()` fails to call `_cascade_up`, leaving zombie obligations.

**Transformed**: `fulfilled` bundles three distinct completion events — payment, administrative discharge, and structural delegation-completion — into a single boolean, so the cascade logic has no coherent invariant to maintain or violate. The zombie obligation is one symptom; the semantic ambiguity is the disease.

**Diagnostic gap**: I started with a mechanical fix (add one line) and arrived at a semantic collapse (no canonical meaning of done). The mechanical fix was concealing the real problem.

---

## The Concealment Mechanism

**How this code hides its real problems**: The cascade creates the appearance of automated consistency. When it works (full delegation + payment), reviewers observe the system maintaining invariants and conclude the model is sound. The cascade's *presence* conceals that `fulfilled` has no canonical semantics — it gets set True through three divergent paths with no unifying meaning.

The `liability()` double-count is concealed by naming: "shadow liability" sounds like sophisticated accounting, making the addition of direct + delegated look intentional rather than incoherent.

---

## Improvement 1: Deepen the Concealment

Add cascade propagation to `forgive` — the obvious "fix":

```python
def forgive(self, oid):
    self._obligations[oid]["fulfilled"] = True
    for child_id in self._chains.get(oid, []):
        self.forgive(child_id)
    self._cascade_up(oid)  # added
```

**Why it passes review**: Fixes the zombie obligation bug. Symmetric with `fulfill`. Clean recursion. Every senior engineer reviewing this says "yes, that's what was missing."

**Why it deepens concealment**: Now `forgive` and `fulfill` use identical cascade machinery, creating the illusion that all completion paths share the same semantic model. Reviewers see convergent behavior and stop asking what `fulfilled` means. The semantic ambiguity is now *structurally invisible* — all paths look the same from outside.

**Three properties only visible because I tried to strengthen it**:

1. `_cascade_up` embeds a numerical check (`parent["amount"] == 0`) inside a structural check (all children fulfilled). These conditions have independent semantics — numerical zero and structural completion aren't the same thing — but the cascade collapses them into one test, with no invariant stating they should co-occur.

2. `fulfilled` is now set to `True` by a function that sets `amount` to zero *implicitly* (forgive doesn't touch amount) and by one that sets it explicitly (fulfill). A future reader checking `if ob["fulfilled"]` cannot know which path triggered it or what the amount field means.

3. The forgive recursion descends the tree top-down; cascade_up ascends bottom-up. They traverse the same structure in opposite directions without shared state, meaning a partially-forgiven subtree can trigger cascade checks on nodes whose siblings are mid-mutation.

---

## Improvement 2: Contradicts the First

Remove automatic cascade entirely. Make fulfillment explicit:

```python
def fulfill(self, oid, amount):
    ob = self._obligations[oid]
    ob["amount"] = max(0, ob["amount"] - amount)
    if ob["amount"] == 0:
        ob["fulfilled"] = True
        # Caller must explicitly fulfill parent if appropriate
```

**Why it passes review**: "Explicit is better than implicit." "Financial ledgers must be auditable — hidden state changes are a compliance risk." "Cascade was causing non-obvious state mutations across multiple obligations." Every engineer who's debugged a distributed financial system will nod.

**Why it contradicts the first**: Improvement 1 extended cascade (more implicit propagation). Improvement 2 removes cascade (full explicitness). Both are defensible. Both improve the code in isolation.

---

## The Structural Conflict

Both improvements are legitimate. The conflict they name:

**Cascade completeness vs. cascade transparency.**

- Improvement 1: delegation trees have implicit obligations; when children complete, parents should complete — consistency requires automatic propagation
- Improvement 2: financial state changes must be explicit and auditable — automation obscures the audit trail

The structural conflict exists because the data model has no way to distinguish *implicit fulfillment* (a parent covered by its children) from *explicit fulfillment* (a parent paid directly). Any cascade policy that resolves this must choose one semantic as primary. But both are valid in different use cases of the same ledger.

---

## Improvement 3: Resolves the Conflict

Make cascade an explicit parameter — satisfy both requirements simultaneously:

```python
def fulfill(self, oid, amount, *, cascade=True):
    ob = self._obligations[oid]
    ob["amount"] = max(0, ob["amount"] - amount)
    if ob["amount"] == 0:
        ob["fulfilled"] = True
        if cascade:
            self._cascade_up(oid)

def forgive(self, oid, *, cascade=True):
    self._obligations[oid]["fulfilled"] = True
    for child_id in self._chains.get(oid, []):
        self.forgive(child_id, cascade=cascade)
    if cascade:
        self._cascade_up(oid)
```

**Why it passes review**: Explicit over implicit, with a safe default. Audit use cases can pass `cascade=False`. Automated use cases use the default. The API accommodates both semantics. Pythonically idiomatic.

**How it fails**: The parameter doesn't resolve the conflict — it *relocates* it into every call site. Every caller must now decide what "fulfilled" means in their context, but the data model records no record of how an obligation became fulfilled. Two obligations both marked `fulfilled=True` may have arrived there through cascade (implicit completion) or explicit payment, but the ledger is identical in both cases. The conflict was pushed upward and made invisible, not resolved.

Moreover, `cascade=True` is the default, which means every casual caller inherits the original semantic ambiguity. The parameter creates *apparent* flexibility while actually making the problem worse: now there are two kinds of fulfilled obligations in the same ledger with no distinguishing mark.

---

## What the Failure Reveals

The parameter-based resolution assumed the conflict was about *policy* — choosing between cascade and no-cascade. The failure reveals the conflict is about *representation*: the data model stores obligations as independent nodes with a parent pointer, but the domain requires tree-level invariants that no node-level operation can encode.

"Fulfilled" at the node level is trying to simultaneously represent:
- This node's amount is zero (numerical)
- This node's entire subtree is complete (structural)  
- This node was administratively discharged (semantic)

No cascade policy resolves this because the problem is in what the boolean `fulfilled` is being asked to mean, not in when it gets set. The design space is not "find the right cascade" — it is "choose a richer representation."

---

## Fourth Construction: Accept the Topology

The topology: obligation trees require tree-level invariants that cannot be expressed as node-level operations. The feasible point: separate obligation identity from obligation state, model completion reasons explicitly, and distinguish direct from delegated amounts at the data level.

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

class CompletionReason(Enum):
    PAYMENT   = "payment"
    FORGIVEN  = "forgiven"
    DELEGATED = "delegated"  # all children complete

@dataclass
class Obligation:
    oid: int
    from_entity: str
    to_entity: str
    direct_amount: float        # amount held here, not delegated
    parent_id: Optional[int]
    completion_reason: Optional[CompletionReason] = None

    @property
    def fulfilled(self) -> bool:
        return self.completion_reason is not None

class ObligationLedger:
    def __init__(self):
        self._obligations: dict[int, Obligation] = {}
        self._children: dict[int, list[int]] = {}
        self._counter = 0

    def create(self, from_entity, to_entity, amount) -> int:
        oid = self._counter; self._counter += 1
        self._obligations[oid] = Obligation(
            oid=oid, from_entity=from_entity,
            to_entity=to_entity, direct_amount=amount, parent_id=None
        )
        return oid

    def delegate(self, oid, new_responsible, fraction=1.0) -> int:
        orig = self._obligations[oid]
        split = orig.direct_amount * fraction
        orig.direct_amount -= split
        new_id = self.create(new_responsible, orig.to_entity, split)
        self._obligations[new_id].parent_id = oid
        self._children.setdefault(oid, []).append(new_id)
        return new_id

    def _subtree_complete(self, oid) -> bool:
        ob = self._obligations[oid]
        if ob.direct_amount > 0:
            return False
        return all(
            self._subtree_complete(c)
            for c in self._children.get(oid, [])
        )

    def _try_cascade(self, oid):
        ob = self._obligations[oid]
        if ob.fulfilled:
            return
        if self._subtree_complete(oid):
            ob.completion_reason = CompletionReason.DELEGATED
            if ob.parent_id is not None:
                self._try_cascade(ob.parent_id)

    def fulfill(self, oid, amount):
        ob = self._obligations[oid]
        ob.direct_amount = max(0.0, ob.direct_amount - amount)
        if ob.direct_amount == 0 and self._subtree_complete(oid):
            ob.completion_reason = CompletionReason.PAYMENT
            if ob.parent_id is not None:
                self._try_cascade(ob.parent_id)

    def forgive(self, oid):
        ob = self._obligations[oid]
        ob.direct_amount = 0.0
        ob.completion_reason = CompletionReason.FORGIVEN
        for child_id in self._children.get(oid, []):
            self.forgive(child_id)
        if ob.parent_id is not None:
            self._try_cascade(ob.parent_id)

    def direct_liability(self, entity) -> float:
        """What entity owes personally on obligations it holds directly."""
        return sum(
            ob.direct_amount for ob in self._obligations.values()
            if ob.from_entity == entity and not ob.fulfilled
        )

    def contingent_liability(self, entity) -> float:
        """What entity may owe if its delegatees default."""
        return sum(
            self._obligations[cid].direct_amount
            for oid, ob in self._obligations.items()
            if ob.from_entity == entity
            for cid in self._children.get(oid, [])
            if not self._obligations[cid].fulfilled
        )
```

---

## What It Sacrifices

1. **Single `liability()` call**: callers must now decide whether to combine `direct_liability` and `contingent_liability` — the original's convenience is gone
2. **Simplicity**: the dataclass + enum model is less ad-hoc extensible than plain dicts; adding fields requires schema changes
3. **Performance**: `_subtree_complete` is O(subtree size) on every fulfill/forgive; the original's cascade was O(depth)

---

## What Was Never a Flaw

The original's `liability()` combined direct and shadow into one number. This looked like a double-counting bug. It was not.

It was a domain encoding: *when you delegate an obligation, your risk exposure is the full amount, not just your residual direct share*. If A delegates 80 to B and B defaults, A may be on the hook for 100 — that's the point of guarantee structures. The original code expressed this as `direct + shadow = total exposure`, which is a legitimate and common risk accounting model.

The redesign's separation into `direct_liability` and `contingent_liability` is cleaner as a data model but sacrifices the domain clarity of a single exposure figure.

The original wasn't failing to distinguish direct from contingent — it was asserting that for purposes of risk assessment, *they are the same exposure*. The "flaw" was the cost of attempting the impossible: a single ledger that simultaneously serves as a payment tracker (direct), a contingent risk calculator (shadow), and a delegation registry (tree) — three systems with genuinely different accounting semantics. The original code wasn't broken. It was paying the only price available for refusing to choose which system it was.

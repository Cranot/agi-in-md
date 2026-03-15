## Structural Analysis: ObligationLedger

---

### The Claim

**The deepest structural problem**: `amount` encodes two semantically distinct zero-states — debt transferred via delegation and debt discharged via payment — making the cascade fulfillment logic unsound and preventing any correct accounting of contingent versus direct liability.

Falsifiable form: *There exists an obligation tree where `_cascade_up` marks a parent `fulfilled=True` even though no payment event has occurred against that parent, and `liability()` produces a value inconsistent with the economic state.*

Demonstration:
```python
ledger = ObligationLedger()
oid = ledger.create("A", "C", 100)

# After this, parent.amount = 0, parent.fulfilled = False
child = ledger.delegate(oid, "B", 1.0)

# fulfill() reduces amount by 0, max(0, 0-0)=0, triggers fulfilled=True
ledger.fulfill(oid, 0)

# Parent is now "fulfilled" — but child still has amount=100 and is unfulfilled.
# The cascade fired on a delegation-zero, not a payment-zero.
print(ledger._obligations[oid]["fulfilled"])  # True — unsound
print(ledger._obligations[child]["fulfilled"])  # False — debt still outstanding
```

A second construction exposes the liability double-counting:
```python
oid = ledger.create("A", "C", 100)
child = ledger.delegate(oid, "B", 0.5)   # parent.amount = 50, child.amount = 50

# direct = 50 (A's remaining obligation)
# shadow = 50 (child's amount, indexed by parent's from=A)
# Total = 100: correct as maximum exposure
# — but "direct" and "shadow" are computed from the same original debt
# through different accounting paths with no documented semantic distinction
print(ledger.liability("A"))  # 100, but what does this mean?
```

---

### Three Experts

**A (Defender)**: Confirmed. `delegate()` and `fulfill()` both mutate `amount`. The cascade predicate `parent["amount"] == 0` cannot distinguish delegation-zero from payment-zero. This is why `fulfill(oid, 0)` marks a fully-delegated obligation as paid when nothing was paid.

**B (Attacker)**: Wrong frame. The `amount` conflation is a symptom. The real problem is that obligation records are simultaneously *leaf payment nodes* and *aggregate tree containers*. A parent obligation shouldn't "know" it has children or cascade its own fulfillment — that responsibility belongs to a separate tree-query layer. Fix the role confusion and the amount conflation goes away automatically.

**C (Prober)**: Both of you are assuming that "fulfilled" has a coherent cross-entity definition. What triggers fulfillment? `fulfill()` triggers it via payment, `_cascade_up` via child completion, `forgive()` by decree. But who has authority to declare an obligation closed? The creditor never participates. The concealment deeper than both of your claims: *the code has no model of valid state transitions* — only mutating current state.

**Transformation**: The claim shifts from *what* (a conflated field) to *how* (an absent state machine). The gap between original claim and transformed claim is this: I described a data problem, but the experts converged on a process problem. The data problem is real but secondary — fixing the field won't fix the missing process model.

---

### The Concealment Mechanism: Value Collapse

Multiple independent state dimensions — original amount, delegated amount, paid amount, forgiven amount — are collapsed into a single mutable `amount` field plus a single `fulfilled` boolean. This hides:

1. How any current state was reached
2. Whether `amount == 0` means discharged or transferred
3. Whether `fulfilled == True` was set by payment, cascade, forgiveness, or a `fulfill(oid, 0)` call on a delegation-zero

The cascade logic, the liability calculation, and `forgive()` all operate on collapsed state, making their correctness impossible to verify from the record alone.

---

### Improvement That Deepens Concealment

Add explicit fulfillment reason tracking — a legitimate code review improvement:

```python
def fulfill(self, oid, amount):
    ob = self._obligations[oid]
    ob["amount"] = max(0, ob["amount"] - amount)
    if ob["amount"] == 0:
        ob["fulfilled"] = True
        ob["fulfilled_by"] = "payment"          # ← appears to add auditability
        self._cascade_up(oid)

def _cascade_up(self, oid):
    ob = self._obligations[oid]
    if ob["parent"] is None:
        return
    children = self._chains.get(ob["parent"], [])
    if all(self._obligations[c]["fulfilled"] for c in children):
        parent = self._obligations[ob["parent"]]
        if parent["amount"] == 0:
            parent["fulfilled"] = True
            parent["fulfilled_by"] = "cascade"  # ← appears to distinguish cause
            self._cascade_up(ob["parent"])

def forgive(self, oid):
    self._obligations[oid]["fulfilled"] = True
    self._obligations[oid]["fulfilled_by"] = "forgiven"  # ← appears to be thorough
    for child_id in self._chains.get(oid, []):
        self.forgive(child_id)
```

This passes code review because it appears to add auditability. It introduces no breaking changes. It looks like enhanced bookkeeping that a senior reviewer would praise.

What it actually does: it adds write-once metadata disconnected from all logic. `fulfilled_by` is never read by `_cascade_up`, `liability()`, or `forgive()`. The cascade still checks `parent["amount"] == 0` — which still fires on delegation-zero. The improvement deepens concealment by making the reader believe the system properly distinguishes state transitions, while the logic remains unchanged.

---

### Three Properties Visible Because We Tried to Strengthen

**1. The cascade predicate is reason-blind even when reasons exist.**
With `fulfilled_by` explicit, we can now see clearly that `_cascade_up` checks `parent["amount"] == 0` — not `parent["fulfilled_by"] == "payment"`. Adding the field revealed that the predicate never needed it. The cascade's unsoundness isn't a missing field; it's a wrong predicate.

**2. Forgiveness and payment produce incompatible state combinations.**
`forgive()` sets `fulfilled=True` without touching `amount`. A forgiven obligation with `amount=50` now has `fulfilled_by="forgiven"` — visibly inconsistent. The field makes explicit that these are different operations producing semantically different `fulfilled` states, but treated identically downstream.

**3. The state machine has incoherent transitions.**
With `fulfilled_by` exposed, we can enumerate what should be impossible: `fulfilled_by="cascade"` on a parent whose direct obligation was never paid, only delegated away. This state is reachable, produces no error, and propagates up the chain. The improvement made the incoherence *legible* without making it *fixable*.

---

### Diagnostic on the Improvement

**What the improvement conceals**: It creates the appearance of a proper audit trail. A reader seeing `fulfilled_by` thinks "this system tracks how obligations close." They will not investigate further.

**What property of the original problem is visible precisely because the improvement recreates it**: The cascade marks `fulfilled_by = "cascade"` on a parent obligation whose own direct debt was never discharged — only shuffled to children. With the reason field explicit, it's now clear that the cascade is not "propagating fulfillment upward" but rather "asserting fulfillment by inference from children, without verifying the parent's own obligations." This is the same error as before, now labeled.

---

### Second Improvement

Address the recreated property: separate `delegated_out` from `paid`, so `remaining` is computable without relying on a mutated `amount`:

```python
def create(self, from_entity, to_entity, amount):
    oid = self._counter; self._counter += 1
    self._obligations[oid] = {
        "from": from_entity, "to": to_entity,
        "original": amount,
        "delegated_out": 0.0,   # ← structural transfer
        "paid": 0.0,            # ← economic discharge
        "parent": None, "fulfilled": False
    }
    return oid

def _remaining(self, oid):
    ob = self._obligations[oid]
    return ob["original"] - ob["delegated_out"] - ob["paid"]

def delegate(self, oid, new_responsible, fraction=1.0):
    orig = self._obligations[oid]
    split = self._remaining(oid) * fraction
    orig["delegated_out"] += split              # ← no longer mutates amount
    new_id = self.create(new_responsible, orig["to"], split)
    self._obligations[new_id]["parent"] = oid
    self._chains.setdefault(oid, []).append(new_id)
    return new_id

def fulfill(self, oid, amount):
    ob = self._obligations[oid]
    ob["paid"] = min(ob["paid"] + amount, self._remaining(oid) + ob["paid"])
    if self._remaining(oid) == 0:
        ob["fulfilled"] = True
        self._cascade_up(oid)

def _cascade_up(self, oid):
    ob = self._obligations[oid]
    if ob["parent"] is None:
        return
    children = self._chains.get(ob["parent"], [])
    if all(self._obligations[c]["fulfilled"] for c in children):
        parent = self._obligations[ob["parent"]]
        if self._remaining(ob["parent"]) == 0:  # now unambiguous: paid, not delegated
            parent["fulfilled"] = True
            self._cascade_up(ob["parent"])
```

Applying the diagnostic: this fixes the specific delegation-zero bug. But it recreates the invariant in a new form. The three mutable fields `original`, `delegated_out`, `paid` must always satisfy `delegated_out + paid ≤ original`. This constraint is enforced nowhere. A caller can call `delegate()` multiple times past the remaining amount (negative remaining), and `_remaining()` returns a negative number that propagates silently. The state machine problem returns: there's still no model of valid transitions, only fields that are supposed to be consistent.

Additionally, `forgive()` still doesn't interact with any of these fields — it sets `fulfilled=True` while `_remaining()` may return a positive number. The mutable-record system now has three sources of truth for "is this obligation closed": `fulfilled`, `_remaining() == 0`, and the forgiven path. These can contradict each other.

---

### The Structural Invariant

Through every improvement, this property persists:

> **In any mutable-record obligation system, reading the state of an obligation node cannot distinguish between state reached by payment and state reached by delegation — because both operations write to the same record and the record does not preserve its own transition history.**

This is a property of the *design category*, not the implementation. Adding fields adds dimensions but not history. Adding reasons adds labels but not causal structure. The invariant is:

**Any system that computes "is this obligation closed?" from the current values of obligation records rather than from the sequence of operations that produced those values must either (a) treat payment and delegation as equivalent state-reduction operations, losing the ability to verify cascade correctness, or (b) maintain derived fields that can go out of sync, trading one class of bug for another.**

---

### Category Boundary

The invariant defines a boundary between:

- **Category A — State-based obligation ledgers**: Obligations are records with current field values. All improvements stay here: flat records, records + audit metadata, records + derived fields, records + reason tags. All share the invariant.

- **Category B — Event-sourced obligation ledgers**: Obligations have no mutable state. The system is a log of immutable events. State is a query over event history, not a stored value. The invariant dissolves because there *is* no `amount` field to mutate — there are only event types with different semantics.

---

### Design in the Adjacent Category

```python
from dataclasses import dataclass, field
from typing import List, Optional
from decimal import Decimal
from enum import Enum
import uuid

class EK(Enum):
    CREATED   = "CREATED"
    DELEGATED = "DELEGATED"
    PAYMENT   = "PAYMENT"
    FORGIVEN  = "FORGIVEN"

@dataclass(frozen=True)
class OblEvent:
    eid:    str
    oid:    str
    kind:   EK
    amount: Decimal
    meta:   dict = field(default_factory=dict)

class ObligationLedger:
    def __init__(self):
        self._log: List[OblEvent] = []

    # ── Write side: append-only ──────────────────────────────────────────────

    def create(self, frm: str, to: str, amount: Decimal) -> str:
        oid = str(uuid.uuid4())
        self._log.append(OblEvent(str(uuid.uuid4()), oid, EK.CREATED, amount,
                                  {"from": frm, "to": to}))
        return oid

    def delegate(self, oid: str, new_responsible: str, fraction: Decimal) -> str:
        split = self._remaining(oid) * fraction
        if split <= 0:
            raise ValueError("Cannot delegate non-positive amount")
        new_oid = str(uuid.uuid4())
        to = self._origin_meta(oid)["to"]
        self._log.append(OblEvent(str(uuid.uuid4()), new_oid, EK.DELEGATED, split,
                                  {"from": new_responsible, "to": to, "parent": oid}))
        return new_oid

    def fulfill(self, oid: str, amount: Decimal):
        self._log.append(OblEvent(str(uuid.uuid4()), oid, EK.PAYMENT, amount, {}))

    def forgive(self, oid: str):
        self._log.append(OblEvent(str(uuid.uuid4()), oid, EK.FORGIVEN, Decimal(0), {}))
        for child in self._children(oid):
            self.forgive(child)

    # ── Read side: computed from log ─────────────────────────────────────────

    def _origin_meta(self, oid: str) -> dict:
        return next(e.meta for e in self._log
                    if e.oid == oid and e.kind in (EK.CREATED, EK.DELEGATED))

    def _original_amount(self, oid: str) -> Decimal:
        return next(e.amount for e in self._log
                    if e.oid == oid and e.kind in (EK.CREATED, EK.DELEGATED))

    def _children(self, oid: str) -> List[str]:
        return [e.oid for e in self._log
                if e.kind == EK.DELEGATED and e.meta.get("parent") == oid]

    def _delegated_out(self, oid: str) -> Decimal:
        return sum(self._original_amount(c) for c in self._children(oid))

    def _paid(self, oid: str) -> Decimal:
        return sum(e.amount for e in self._log
                   if e.oid == oid and e.kind == EK.PAYMENT)

    def _remaining(self, oid: str) -> Decimal:
        return self._original_amount(oid) - self._delegated_out(oid) - self._paid(oid)

    def _forgiven(self, oid: str) -> bool:
        return any(e.oid == oid and e.kind == EK.FORGIVEN for e in self._log)

    def is_fulfilled(self, oid: str) -> bool:
        if self._forgiven(oid):
            return True
        remaining = self._remaining(oid)
        if remaining < 0:
            raise ValueError(f"{oid}: over-committed by {-remaining}")
        if remaining > 0:
            return False
        # remaining == 0: either fully paid or fully delegated — now check children
        return all(self.is_fulfilled(c) for c in self._children(oid))

    def liability(self, entity: str) -> Decimal:
        owned = {e.oid for e in self._log
                 if e.kind in (EK.CREATED, EK.DELEGATED)
                 and e.meta.get("from") == entity}
        return sum(self._remaining(oid) for oid in owned
                   if not self.is_fulfilled(oid))
```

**How this succeeds where every improvement failed**:

| Problem | Category A fate | Category B resolution |
|---|---|---|
| Delegation-zero vs payment-zero | Indistinguishable in `amount` | `_delegated_out` and `_paid` are separate event streams; `_remaining` is unambiguous |
| Cascade unsoundness | Predicate fires on wrong zero | `is_fulfilled()` is a recursive query, not a triggered mutation; it recomputes correctly on every call |
| Forgiveness + amount inconsistency | `fulfilled=True`, `amount > 0` coexist | `_forgiven` is an independent event check; `is_fulfilled()` short-circuits before amount math |
| History destruction | Mutation overwrites prior state | The log is append-only; any past state is replayable |
| Missing state machine | No enforcement of valid transitions | Invalid states are detectable: `_remaining() < 0` raises; `is_fulfilled()` is definitionally correct |

The `liability()` function no longer double-counts: it asks "what does this entity directly owe that remains unfulfilled?" Children are not separately summed — their fulfillment status is incorporated into `is_fulfilled()` of the parent.

---

### The New Impossibility

The adjacent category makes trivial what was impossible, and makes impossible what was trivial:

**What dissolves**: Knowing *why* an obligation is in any state. The event log answers every auditing question: what was the original amount, when was it delegated, how much was paid, in what order.

**What becomes impossible**:

1. **O(1) state reads.** `is_fulfilled(oid)` is O(events × tree_depth). `liability(entity)` is O(all_events). The original system read current state in O(1).

2. **Bounded memory for settled obligations.** The log grows monotonically. Fulfilling an obligation *adds* a PAYMENT event; it never removes anything. A Category A system could in principle archive fulfilled obligations. Category B cannot compact without sacrificing its core invariant.

3. **Efficient cross-entity aggregation.** "Total outstanding liability across all entities" requires scanning every event for every obligation. With high event volume, this becomes a separate indexing problem — and any index that caches computed state is a mutable record system layered on top of the event log, recreating Category A's problems under Category B's roof.

4. **Snapshot consistency without timestamps.** The original system had no concept of time, but its reads were instantaneously consistent. Category B requires explicit time-ordering on events to answer "what was the state at T?" — a new requirement that didn't exist in the original problem.

---

### The Finding

**The trade-off between old and new impossibilities is the real design decision this code never made.**

**Category A's impossibility**: You cannot know why an obligation is in its current state. The cascade logic is unsound because it operates on a predicate (`amount == 0`) that conflates two distinct operations. Every improvement adds metadata to make this visible but cannot fix it, because fixing it requires preserving the history that mutation destroys.

**Category B's impossibility**: You cannot efficiently query current state. Every read is a replay. Every aggregate is a scan. Fixing this reintroduces cached mutable state — and with it, Category A's problems.

**The diagnostic**: `ObligationLedger` is not a buggy implementation of a correct design. It is a correct implementation of a design that cannot express the problem it is trying to solve. The bugs — unsound cascade, undocumented liability semantics, forgiveness inconsistency — are not fixable within Category A because they are expressions of Category A's structural limit: *a record's current value cannot contain the information needed to verify how it became that value.*

The code hides this by making the cascade look automatic and correct (it fires; it runs; it sets flags; nothing throws), while being logically unsound in precisely the cases — delegation followed by selective fulfillment — that the system exists to handle.

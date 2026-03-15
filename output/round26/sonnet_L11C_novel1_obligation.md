# Structural Analysis: ObligationLedger

---

## I. The Falsifiable Claim

**The code's deepest structural problem:** `liability()` adds shadow amounts for obligations that were already arithmetically transferred away from the delegator, creating mandatory double-counting of every delegated obligation — not as an edge case, but as the invariant result of any delegation event.

Falsifiable test: Create entity A owing 1000. Delegate 100% to B. Assert `liability(A) + liability(B) == 1000`. It will return 2000.

```python
ledger = ObligationLedger()
oid = ledger.create("A", "X", 1000)
ledger.delegate(oid, "B", fraction=1.0)

# After delegation:
# A's obligation: from=A, amount=0, fulfilled=False
# B's obligation: from=B, amount=1000, fulfilled=False
# parent chain: A's_oid -> [B's_oid]

print(ledger.liability("A"))  # direct=0, shadow=1000 → returns 1000
print(ledger.liability("B"))  # direct=1000, shadow=0 → returns 1000
# Sum: 2000 for a 1000 obligation
```

The double-count is structural, not incidental. `delegate()` reduces the parent's amount (modeling transfer). `liability()` then adds the children's amounts back as shadow (modeling guaranty). These are two different economic models operating simultaneously on the same data.

---

## II. Three Expert Voices

**Defender:** The shadow is intentional guaranty accounting. If B fails to pay, A remains exposed as original obligor. The cascade mechanism in `_cascade_up()` correctly zeroes out A's liability when B fulfills. The double-count resolves at settlement; during the interim it represents *contingent* maximum exposure, which is what risk managers actually want.

**Attacker:** The defender's reading breaks on partial delegation. Delegate 50% to B: A.amount = 500, B.amount = 500. `liability(A)` = direct(500) + shadow(500) = 1000. A's shadow is B's amount, which B also carries as direct. Now no settlement path resolves this without both B *and* A separately fulfilling — but `fulfill(A_oid, 500)` sets A.fulfilled=True with B still outstanding. The cascade logic requires `parent["amount"] == 0` as a precondition for marking parent fulfilled — but it doesn't require the *shadow* to be 0. There is no mechanism that actually unifies the two models. The "it resolves at settlement" claim is false for the partial case.

**Prober:** Both of you are arguing about whether the double-count is a bug or a feature. You both assume `liability()` is *trying* to measure something real. But notice what neither of you has asked: what does delegation *mean* in this system? Is it a legal transfer (new party, extinguished original)? A sub-contracting (original party retains, new party assists)? A guaranty (new party is primary, original party backstops)? The code has no answer. `delegate()` is named like a transfer. `liability()` is implemented like a guaranty. `_cascade_up()` is a hybrid. The claim that there's a *bug* takes for granted that there's a *correct* answer the code is failing to reach.

---

## III. Claim Transformation

**Original claim:** double-counting bug in `liability()`  
**Transformed claim:** the code implements three irreconcilable economic models of delegation (transfer, guaranty, sub-contracting) simultaneously, with no commitment to any. The double-count is a symptom; the pathology is **semantic vacuum** — the ledger tracks obligation instances without knowing what obligations *are*.

**The diagnostic gap:** Moving from "arithmetic error" to "missing semantic model" reveals that fixing the arithmetic cannot fix the problem, because the correct arithmetic depends on which model you're implementing, and that choice is not in the code.

---

## IV. Concealment Mechanism: Structural Arithmetic Coherence

Every individual method is locally consistent:
- `delegate()` correctly reduces amounts
- `fulfill()` correctly decrements and flags
- `_cascade_up()` correctly propagates given its premises
- `_chains` correctly links parent to children

The code *looks* right because numbers are conserved at the method level. Only end-to-end scenario tracing reveals the contradiction. A code reviewer reading any single method will find no error. The deception: **local arithmetic coherence substitutes for global semantic integrity.** The system appears to *know* what it's doing because it never makes a math error, even while having no idea what it's actually modeling.

---

## V. Improvement I — Deepens the Concealment

Add an explicit `delegation_type` parameter. This looks like it addresses the semantic vacuum by naming it:

```python
class ObligationLedger:
    def __init__(self):
        self._obligations = {}
        self._counter = 0
        self._chains = {}

    def create(self, from_entity, to_entity, amount):
        oid = self._counter; self._counter += 1
        self._obligations[oid] = {
            "from": from_entity, "to": to_entity,
            "amount": amount, "parent": None,
            "fulfilled": False, "delegation_type": None
        }
        return oid

    def delegate(self, oid, new_responsible, fraction=1.0,
                 delegation_type="transfer"):
        """
        delegation_type: 'transfer' (delegator extinguished) or
                         'guarantee' (delegator backstops)
        """
        orig = self._obligations[oid]
        split = orig["amount"] * fraction
        orig["amount"] -= split
        new_id = self.create(new_responsible, orig["to"], split)
        self._obligations[new_id]["parent"] = oid
        self._obligations[new_id]["delegation_type"] = delegation_type
        self._chains.setdefault(oid, []).append(new_id)
        return new_id

    def liability(self, entity):
        direct = sum(
            o["amount"] for o in self._obligations.values()
            if o["from"] == entity and not o["fulfilled"]
        )
        # Shadow only applies to guarantee delegations
        shadow = sum(
            self._obligations[cid]["amount"]
            for pid, children in self._chains.items()
            if self._obligations[pid]["from"] == entity
            for cid in children
            if not self._obligations[cid]["fulfilled"]
            and self._obligations[cid].get("delegation_type") == "guarantee"
        )
        return direct + shadow

    def fulfill(self, oid, amount):
        ob = self._obligations[oid]
        ob["amount"] = max(0, ob["amount"] - amount)
        if ob["amount"] == 0:
            ob["fulfilled"] = True
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
                self._cascade_up(ob["parent"])

    def forgive(self, oid):
        self._obligations[oid]["fulfilled"] = True
        for child_id in self._chains.get(oid, []):
            self.forgive(child_id)
```

This passes code review. The docstring explains the distinction. The shadow calculation correctly excludes transfers. The double-count for transfers disappears.

---

## VI. Three Properties Visible Because We Tried To Strengthen

**1. `delegation_type` is an assertion, not a constraint.** The parameter is caller-supplied metadata with no validation against economic reality. Nothing prevents `delegate(oid, B, 1.0, "transfer")` followed by `delegate(oid, C, 0.5, "guarantee")` on the *same obligation* — mixing models on one record. The field labels the model but does not enforce it.

**2. `_cascade_up()` is semantically coherent only with the guaranty model.** For a "transfer" delegation, the parent should be *replaced*, not *reduced to 0 and kept*. `_cascade_up()` marks the parent fulfilled when children fulfill — which only makes sense if the parent is a guarantor waiting to be released. For true transfers, the parent obligation should not exist at all after delegation. By keeping the parent record with amount=0, the code structurally commits to guaranty semantics even when `delegation_type="transfer"`.

**3. The shadow liability calculation is always derivable from the chain graph.** Shadow is not additional information; it's a re-traversal of data already in `_chains`. The need for a separate `shadow` variable reveals that `direct` alone is sometimes wrong — which means the fundamental accounting unit (`direct`) is unreliable. Shadow exists to patch direct. The patch reveals the wound.

---

## VII. Diagnostic Applied to Improvement I

**What Improvement I conceals:** That the semantic split (transfer vs. guarantee) must be enforced by the *chain of custody structure*, not by a string parameter. The string creates the illusion of a semantic model while the object structure underneath encodes exactly one model (guaranty, via parent links and cascade).

**What property of the original problem is visible because Improvement I recreates it:** `_cascade_up()` still runs identically regardless of `delegation_type`. For "transfer" delegations, the cascade is meaningless — the parent is already amount=0 before any child fulfills, so `_cascade_up()` will mark it fulfilled the moment the first (and only) child fulfills — which happens to be correct numerically but is *conceptually wrong* (a transferred obligation should not need "cascade fulfillment"; it is extinguished at the moment of transfer). **The original problem — no defined semantics for delegation — is recreated in the gap between the `delegation_type` label and the `_cascade_up()` behavior.**

---

## VIII. Improvement II

Address the recreated property: make `_cascade_up()` semantics depend on `delegation_type`, and make "transfer" actually extinguish the parent record at delegation time:

```python
def delegate(self, oid, new_responsible, fraction=1.0,
             delegation_type="transfer"):
    orig = self._obligations[oid]
    split = orig["amount"] * fraction
    orig["amount"] -= split
    new_id = self.create(new_responsible, orig["to"], split)
    self._obligations[new_id]["parent"] = oid
    self._obligations[new_id]["delegation_type"] = delegation_type
    self._chains.setdefault(oid, []).append(new_id)

    # For full transfers: immediately extinguish the parent
    if delegation_type == "transfer" and orig["amount"] == 0:
        orig["fulfilled"] = True  # Extinguish at delegation, not at settlement

    return new_id

def _cascade_up(self, oid):
    ob = self._obligations[oid]
    if ob["parent"] is None:
        return
    parent_id = ob["parent"]
    parent = self._obligations[parent_id]
    children = self._chains.get(parent_id, [])

    if ob.get("delegation_type") == "transfer":
        # Transfer: parent is already extinguished. Cascade is a no-op.
        # Child fulfillment does not affect parent state.
        return
    else:
        # Guarantee: parent is released when all children are fulfilled
        # and parent has no direct remaining amount
        if all(self._obligations[c]["fulfilled"] for c in children):
            if parent["amount"] == 0:
                parent["fulfilled"] = True
                self._cascade_up(parent_id)
```

Apply diagnostic to Improvement II:

**What Improvement II conceals:** That immutably extinguishing the parent record at delegation time makes it impossible to reconstruct the delegation chain for audit purposes. If you query the history of obligation `oid` after a transfer, you find a fulfilled record with no explanation of why it was fulfilled without ever having `fulfill()` called on it. The audit trail is destroyed by the very act of making accounting correct.

**What property of the original problem is visible because Improvement II recreates it:** The original code kept all obligation records alive to maintain audit lineage, which corrupted the accounting. Improvement II makes accounting correct by marking parents fulfilled at delegation time — which recreates the original problem in inverted form: **correct accounting requires destroying the audit record; correct auditing requires preserving the record that corrupts accounting.** The property is now visible as a *binary*: you must choose which to corrupt.

---

## IX. The Structural Invariant

**The invariant:** Every obligation, once created, persists as a record in the ledger. Delegation, fulfillment, and forgiveness change an obligation's *state* but never its *existence*. The ledger is an append-only structure where records can be marked but never replaced or consumed.

This invariant persists through every improvement:
- Improvement I: adds a field (`delegation_type`), still keeps all records
- Improvement II: marks parent fulfilled at delegation time, still keeps all records

The invariant is present because obligation records serve two purposes simultaneously: they are **accounting entries** (their `amount` contributes to liability totals) and **audit nodes** (their `parent` field preserves provenance). A record cannot be deleted without destroying the audit graph. A record cannot be kept without potentially corrupting the accounting total.

---

## X. Invert the Invariant

**Design where the invariant is trivially satisfied:** Obligations have no persistent identity. Delegation *consumes* the original and *emits* replacements. Obligations are flows, not objects.

```python
class FlowLedger:
    """Obligations are flows: delegation consumes and replaces."""
    def __init__(self):
        self._active = {}   # oid -> {from, to, amount}
        self._counter = 0

    def create(self, from_entity, to_entity, amount):
        oid = self._counter; self._counter += 1
        self._active[oid] = {
            "from": from_entity, "to": to_entity, "amount": amount
        }
        return oid

    def delegate(self, oid, new_responsible, fraction=1.0):
        """Consumes the original obligation; emits delegated + remainder."""
        orig = self._active.pop(oid)   # ← consumed, not modified
        delegated_amount = orig["amount"] * fraction
        remaining_amount = orig["amount"] * (1 - fraction)
        new_oid = self.create(new_responsible, orig["to"], delegated_amount)
        remainder_oid = (
            self.create(orig["from"], orig["to"], remaining_amount)
            if remaining_amount > 0 else None
        )
        return new_oid, remainder_oid

    def fulfill(self, oid, amount):
        ob = self._active[oid]
        ob["amount"] = max(0, ob["amount"] - amount)
        if ob["amount"] == 0:
            del self._active[oid]   # ← consumed at completion

    def liability(self, entity):
        # Trivially correct: no shadow, no parent chains, no double-count
        return sum(o["amount"] for o in self._active.values()
                   if o["from"] == entity)
```

`liability()` is now trivially correct. There is no double-counting because there are no parent records. There is no semantic ambiguity because delegation has exactly one meaning: replacement. The impossible property (simultaneously correct accounting + correct audit) is resolved for accounting.

---

## XI. The New Impossibility

**The FlowLedger makes it impossible to answer any provenance question:**

- "Who originally created this obligation?" — The original record is gone.
- "Has this obligation been delegated, and to whom?" — There are no links; old ids are dead.
- "What is A's total exposure including obligations A delegated to others?" — No chain exists to traverse.
- "When B's fulfillment is disputed, who is ultimately responsible?" — The chain of custody is destroyed at delegation time.
- **Regulatory compliance requiring audit trails is structurally impossible.**

The new impossibility is not merely "we don't have logs" — it's deeper. The obligation `oid` returned by `delegate()` is a *new* obligation with *no relationship* to the old one in the data model. From the ledger's perspective, the two obligations are as unrelated as any two arbitrary obligations. You cannot reconstruct that they are the same economic commitment in different hands.

---

## XII. The Conservation Law

**The Law:** *The information content required to make obligation provenance auditable is the same information content that, when present in the obligation record, makes obligation accounting overcomplete.*

Stated as a conservation principle:

> **Provenance information and accounting correctness are not trade-offs in obligation ledgers — they are conjugate variables. Increasing the precision of one necessarily introduces indeterminacy in the other, and this is a property of the representation space, not of the implementation.**

The original ledger contains full provenance (parent links, shadow chains) and has overcomplete accounting (double-counting). The FlowLedger has exact accounting and zero provenance. Every intermediate design — including Improvements I and II — either localizes the error to a synchronization problem, a caller responsibility problem, or a consistency window, but cannot eliminate it.

---

## XIII. What a Senior Engineer Would Not Already Know

A senior engineer would say: "Yes, of course, there's a trade-off between audit trail richness and accounting simplicity. Use an event log for audit, a position ledger for accounting."

**What the conservation law reveals that goes beyond this:**

The trade-off is not between *systems* (audit log vs. position ledger) — it is between *object identity and quantity*. An obligation record needs to answer two incommensurable questions simultaneously:

1. **What is this obligation?** (identity: provenance, chain of custody, original creator, delegation history)
2. **How much is this obligation?** (quantity: current amount, current responsible party)

These questions require different notions of "sameness." For identity, the obligation delegated from A→B is the *same* obligation — it is one economic commitment traveling through hands. For quantity, the obligation on A's books and the obligation on B's books are *different* entries — they cannot both contribute to total exposure without double-counting.

**No single record type can be simultaneously the unit of identity and the unit of quantity.** The original code uses one record type for both. The FlowLedger uses one record type for quantity alone. The conservation law says: any system that tries to unify them will need a consistency protocol, and that protocol is itself the site of the impossibility.

---

## XIV. Prediction About a Third Design

The natural third design separates concerns: an **event log** records all delegation/fulfillment events for audit; a **position ledger** records current exposures for accounting. They are kept in sync by a transaction.

**The conservation law predicts:** The third design does not eliminate the impossibility — it *migrates* it to the synchronization boundary. Specifically:

- The event log and position ledger will be inconsistent during every write window (event written, position not yet updated). Any query spanning that window returns incorrect data.
- To prevent incorrect queries, you need either: (a) synchronous writes (the event log write blocks until the position update commits — the position ledger becomes a bottleneck and a failure domain), or (b) eventual consistency (there exists a window where liability queries are wrong by design), or (c) a consensus protocol (which introduces a new single point of failure).

**The specific prediction:** The third design will introduce a concept like "pending obligations" — obligations that have been recorded in the event log but not yet settled in the position ledger. The system will need to add "pending" to its semantic model. The "pending" state is the original double-counting, renamed and scheduled: the same obligation existing in two places simultaneously, for a bounded time window rather than permanently.

**The impossibility is conserved.** It is not solved by separation of concerns; it is deferred to the synchronization protocol and re-emerges as a consistency problem wearing the clothes of an infrastructure problem. A senior engineer would build the event log + position ledger and consider the problem solved. The conservation law predicts they will open a ticket six months later about "stale liability calculations during high-delegation-volume periods."

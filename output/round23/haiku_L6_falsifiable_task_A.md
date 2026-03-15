# Falsifiable Hypothesis

**The code's deepest structural problem: It chains configuration lookup with data transformation, making configuration contracts invisible and preventing any stage from being independently testable, replaceable, or reasoned about without executing the entire pipeline.**

More specifically: Every function call reaches into `config` for *its own* requirements, but there's no declared contract saying *which keys each step needs*. This makes it impossible to know if `config` is complete, or if you could reorder/skip/parallelize steps.

---

## Three Independent Tests

### **Expert 1 (DEFENDER) ✓ Agrees**
*"You've identified the real coupling. Look:*
- *To unit test `enrich()`, I must mock `config.sources`—but the signature doesn't tell me this dependency exists.*
- *If I want to skip enrichment, I can't pass a modified pipeline; I'd have to refactor the entire function.*
- *The linearity isn't the problem—it's that configuration requirements are **scattered and implicit**. This is a variant of the Service Locator anti-pattern.*
- *A better structure would make each stage declare: `enrich(data) → data`, with configuration injected at composition time, not lookup time."*

### **Expert 2 (ATTACKER) ✗ Rejects Claim**
*"No. The structural problem is the lack of **error propagation boundaries**, not configuration coupling. Here's why:*
- *If `validate()` succeeds but `transform()` fails 3 steps in, where does the error originate? Unclear.*
- *The linearity is actually a strength—it's a proven pattern (Unix pipes, functional composition). The problem is there's no error handling between steps.*
- *Configuration coupling is a red herring. Compare this to well-designed frameworks (Airflow, dbt) that also hide config lookup, but they work fine because they have proper error handling and step boundaries.*
- *Your 'testability' concern? Mock the whole pipeline or use integration tests. Not all code needs unit test decomposition."*

### **Expert 3 (PROBER) ⸺ Questions Both**
*"Wait. You both assume the purpose of this code. Let me ask:*

1. *Your claim assumes we want 'independent testability.' But what if this code is intentionally a thin orchestrator—a script, not a library? Then coupling doesn't matter.*

2. *You (Defender) say configuration should be "declared." But doesn't making config explicit **increase verbosity** without benefit if there's only one pipeline?*

3. *You (Attacker) emphasize error handling. But is a TypeError from missing `config.sources` actually different in severity than a TypeError from a bad argument? Maybe the real issue is: **who owns responsibility for the contract**—the caller or the function?*

4. *The deepest assumption you're both making: that this function should be flexible/reusable. But what if it's intentionally static? What if the real problem is that it's **not documenting its actual constraints**?"*

---

## How the Argument Transformed My Claim

| | Original | After Argument |
|---|---|---|
| **Diagnosis** | Configuration coupling prevents testability | Configuration *requirements are undeclared* (a documentation/contract problem) |
| **Root Cause** | Sequential structure | Coupling of *responsibility* (caller/callee don't share a contract) |
| **Real Problem** | Missing modularity | Missing **invariants**—no doc saying "this needs `config.sources`" or "this errors if data < 5 records" |

**What I now know:** The code has three fixable problems, but they're *not the same*:
1. **If reusability is the goal** → Extract configuration injection
2. **If error clarity is the goal** → Add error handling boundaries  
3. **If maintainability is the goal** → Add docstrings declaring what each stage requires/guarantees

The "deepest" problem depends on *context I initially assumed but didn't state*.

**My revised claim:** "This code's structural problem is **unstated contract ambiguity, not sequentiality**—any refactor that doesn't clarify what each stage requires from config will fail regardless of pattern."

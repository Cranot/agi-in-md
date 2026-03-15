# Conservation Law Analysis: Click Parameter Resolution

## Initial Claim

**Click's parameter resolution system creates an illusion of clear hierarchy while actually distributing authority across six incommensurable sources, making the system's real source-of-truth unknowable without tracing multiple fallback chains.**

More precisely: the code presents parameters as having one authoritative value (`ctx.params[name]`), but that value could have come from COMMANDLINE, ENVIRONMENT, DEFAULT_MAP, DEFAULT, callback transformation, or parent inheritance. The system captures source information in `ParameterSource` enum and stores it, but then immediately collapses all sources into the same flat namespace—making the source invisible at the exact moment it matters most.

---

## Three-Voice Dialectic (Testing the Claim)

**Defender:** "This distribution is Click's strength. Different sources serve different purposes. `ParameterSource` enum is explicit about priority. Context inheritance lets subcommands inherit parent configuration. Callbacks allow post-processing. This flexibility is necessary—it's how real CLI applications work. Senior engineers understand this."

**Attacker:** "No. The source information is captured *and then discarded*. Look at `handle_parse_result`: it gets `(value, source)` from `consume_value()`, stores source in `ctx.set_parameter_source()`, but then immediately collapses both into `ctx.params[name]`. The source metadata exists but is made invisible. And callbacks transform values without the parameter knowing. The code doesn't just distribute authority—it hides where authority actually lives. This isn't flexibility; it's opacity pretending to be simplicity."

**Prober:** "You're both focusing on knowledge vs. ignorance. But the real issue is *identity*. When a value comes from ENVIRONMENT instead of COMMANDLINE, is it the same parameter? If a callback modifies it, is it still the same value? The code treats all sources as interchangeable by collapsing them into one namespace. But they're not interchangeable—you can't convert ENVIRONMENT back to COMMANDLINE. The code hides the fact that it's making fundamentally different things indistinguishable."

**Gap:** The original claim focused on traceability (epistemological problem). The attacker revealed that source information is captured but discarded (a transparency problem). The prober exposed the structural issue: **source identity and parameter identity are being collapsed without admission that something is lost.**

---

## Concealment Mechanism: "Source Collapse"

The concealment works through three simultaneous operations:

1. **Create the appearance of explicit source management:** `ParameterSource` enum exists, sources are tracked, `set_parameter_source()` is called
2. **Make source information structurally irrelevant:** Everything goes into `ctx.params`, a flat dict where all parameters look identical regardless of origin
3. **Hide the incompatibility at the boundary:** The moment `handle_parse_result` finishes, source information is separated from value. Downstream code never sees both together.

The mechanism is necessary because Click wants to claim it supports "proper parameter resolution" (multiple sources, clear priority) without admitting the philosophical problem: these sources are *incommensurable*. You cannot reconstruct an ENVIRONMENT-sourced value as if it were COMMANDLINE, yet the code treats them as equivalent once merged.

---

## First Improvement: Transparent Parameter Tracing

**Proposed addition:**

```python
class Context:
    def get_parameter_with_source(self, name):
        """Expose parameter value with its resolution source."""
        value = self.params.get(name)
        source = getattr(self, '_parameter_sources', {}).get(name)
        return value, source
    
    def get_parameter_chain(self, name):
        """Show full resolution chain across parent contexts."""
        chain = []
        ctx = self
        while ctx is not None:
            if name in ctx.params:
                source = getattr(ctx, '_parameter_sources', {}).get(name, 'unknown')
                chain.append({
                    'context': ctx.info_name or 'root',
                    'source': source,
                    'value': ctx.params[name]
                })
            ctx = ctx.parent
        return chain
```

This looks like a solution. "Now you can trace where parameters come from!" But it **deepens the concealment** because:

- It creates the *illusion* of traceability without enabling actual understanding
- It suggests the problem *is solvable locally* when the issue is architectural
- It hides the fact that source information exists only at one moment (resolution time) and cannot be preserved as a persistent property
- It makes developers think they understand the system while looking at a *snapshot*, not a process

---

## Three Properties Revealed by Attempting Improvement

By building the tracing method, we discover:

**Property A: Source information is ephemeral.**
Source can only be known at the moment of `handle_parse_result`. After resolution completes, the "source" is already lost. You can store it in `_parameter_sources`, but what you're storing is *metadata about a moment in time*, not an invariant property of the parameter. If the parameter is later modified by a callback, the source reference becomes invalid. The tracing method reveals that source identity and value identity have become orthogonal—they don't stay synchronized.

**Property B: Source collapse is irreversible.** 
Once COMMANDLINE, ENVIRONMENT, and DEFAULT are all in `ctx.params[name]`, they become indistinguishable. Adding `_parameter_sources` just creates a parallel metadata dict that can diverge. The tracing method reveals that the code is solving a *representation problem* (where did it come from?) while hiding a *transformation problem* (what happened to it?). You can add as much metadata as you want; you still can't tell whether DEFAULT → modified-by-callback is equivalent to COMMANDLINE.

**Property C: Authority distribution is irreversible by design.**
The flexibility to support six different sources isn't accidental—it's central to Click's feature set. But the tracing method reveals that you cannot have flexible source support *and* unified parameter semantics simultaneously. Every framework solves this by choosing: either (a) support one source (COMMANDLINE wins, defaults stored separately), or (b) merge multiple sources but accept that you lose information. Click tries both at once and hides the contradiction.

---

## Second Improvement: Apply Diagnostic to the Tracing Method

What does the tracing method itself conceal?

The method makes developers think they can "understand parameter flow" by calling it. But it hides:

- **Callback transformations are invisible.** `get_parameter_chain()` shows you the source, not what the callback did to the value. You see COMMANDLINE → ["value1"], but you don't see if a callback then changed it to "value2" and why.

- **Source is a label, not a contract.** Knowing a parameter came from ENVIRONMENT doesn't tell you whether that ENVIRONMENT value *should* override COMMANDLINE, or whether it's subject to the same validation rules. Some sources are supposed to be authoritative; others are fallbacks. The method collapses that distinction.

- **Inheritance chains are incomplete.** `get_parameter_chain()` walks parent contexts, but it doesn't show you which parent *actually owns* the parameter. In a multi-level group/subcommand structure, a parameter could exist in 3+ parent contexts with different sources at each level. The chain doesn't tell you which one "wins."

The second improvement reveals that the original problem isn't solved by adding transparency—it's solved by adding **contracts**. A parameter should declare what it accepts:

```python
class Parameter:
    def __init__(self, ..., source_contract=None, ...):
        # source_contract defines which sources can modify this parameter
        self.source_contract = source_contract or {
            'commandline': True,      # COMMANDLINE can set this
            'environment': False,     # ENVIRONMENT cannot
            'default_map': False,
            'callback': False,
        }
```

---

## The Structural Invariant

Applying the same diagnostic to both improvements (tracing + contracts), we find the invariant that persists:

**"In Click, the act of unifying parameter sources requires hiding source identity. You must choose: either parameters know where they came from (sources remain separate, namespace is fragmented), or parameters are unified (sources are hidden, identity is lost). You cannot have both."**

Or more technically:

**Number of distinct sources × number of transformation points ≥ namespace unification cost**

In Click:
- 6 sources (COMMANDLINE, ENVIRONMENT, DEFAULT_MAP, DEFAULT, prompt, callback)
- 3 transformation stages (consume_value, type_cast_value, callback)
- 1 unified namespace (ctx.params)

This creates an impossible equation. The code solves it by silently choosing: *unify the namespace and accept that source identity is lost*.

---

## Inversion: Design Where Source Becomes Trivial

**Inverted design:** What if each parameter explicitly declared "I only care about COMMANDLINE"?

```python
class Parameter:
    def __init__(self, ..., accepts_source=ParameterSource.COMMANDLINE, ...):
        self.accepts_source = accepts_source
    
    def consume_value(self, ctx, opts):
        value, source = self._resolution_chain(ctx, opts)
        # NEW: reject values from unwanted sources
        if source != self.accepts_source and value is not UNSET:
            # This parameter doesn't accept this source
            raise ValueError(f"Parameter {self.name} does not accept {source}")
        return value, source
```

Now source doesn't need to be hidden—it's explicit in the parameter's declaration. Subcommands inherit parameters that only accept COMMANDLINE. Environment variables don't mysteriously affect values. Callbacks are explicit transformations, not hidden side effects.

---

## New Impossibility Created by Inversion

But this inversion creates a new impossibility:

**"If every parameter explicitly declares which sources it accepts, you cannot have a parameter that different subcommands want to configure differently. Parent context's ENVIRONMENT setting can't override child parameter's COMMANDLINE-only declaration without breaking the declaration's meaning. And you lose Click's flexibility—the whole point of DEFAULT_MAP and context inheritance is that different subcommands can have different default sources."**

---

## The Conservation Law

**Conservation Law of Parameter Autonomy:**

"In CLI parameter systems, **source flexibility and value determinism are inversely conserved.** The more sources a parameter can accept (source flexibility), the less you can know about where its final value came from (value determinism decreases). Conversely, the more you constrain a parameter to one authoritative source (value determinism), the less flexible your CLI architecture becomes. You cannot have a system where parameters accept unlimited sources *and* you can trace exactly where each parameter's value originated—attempting to gain one requires sacrificing the other."

**Mathematical form:** 
```
source_flexibility × value_traceability = constant
```

Or in inverted form:
```
parameter_autonomy + source_opacity = constant
```

---

## What This Reveals

**A senior engineer wouldn't know this:**
Most CLI frameworks solve this problem by choosing one approach and hiding the other. Unix tools typically choose: *COMMANDLINE is canonical, defaults are stored separately, environment variables are a special case*. This avoids the problem entirely.

Click's innovation was to try to support multiple equal sources—making DEFAULT_MAP as first-class as COMMANDLINE. But this innovation *necessarily* creates the information loss. The source collapse isn't a bug in Click's implementation; it's a necessary consequence of Click's design choice to be source-agnostic.

**What the law predicts about a third design:**

A framework that attempted to support:
1. Multiple sources with equal priority (like Click)
2. Full traceability of where each value came from (unlike Click)
3. Automatic inheritance of parameter configuration across command hierarchies (like Click)
4. Callbacks that can transform values without losing source information

...would discover that **callbacks are themselves a source, and they create source-identity problems that can't be resolved.** If a callback sees a COMMANDLINE value and transforms it, is the result still "from COMMANDLINE"? A value modified by a callback is neither the original source nor a new source—it's a hybrid that breaks any source-tracking system. 

The conservation law would reassert itself: you'd have to choose whether callbacks preserve source identity (and thus constrain what callbacks can do) or whether callbacks create a new source-category (and thus make source tracking even more complex). Either way, the tradeoff persists.

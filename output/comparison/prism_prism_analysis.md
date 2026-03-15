# LEVEL 12 META-CONSERVATION ANALYSIS: prism.py

Execute complete diagnostic below.

---

## INITIAL CLAIM (Falsifiable)

**Claim**: prism.py's deepest structural problem is that it conflates **stateless analysis** (findings are deterministic: same code + lens → same findings always) with **stateful conversation** (sessions are opaque server artifacts that expire/diverge, causing context loss). 

The code cannot simultaneously achieve:
- **(A) Reproducible findings** (cached, valid across sessions)
- **(B) Seamless recovery from session divergence** (network hiccup doesn't require user intervention)  
- **(C) No explicit state management** (findings and context appear as one unit to the user)

**The concealment**: When session ID changes (line 1138–1156), the code treats conversation loss and finding validity as **one problem** (dismisses both as "divergence"). This hides that findings are **actually recoverable** (on disk, mathematically independent of session_id), while conversation is **irrecoverably lost** (no transcript, server-side expiry). By bundling them, the code makes users think they've lost everything.

---

## DIALECTIC: THREE EXPERT VOICES

### **DEFENDER** (Position: Claim is correct)

*Evidence*:
- Line 1138–1156: `_on_session_transition()` fires when session_id changes. It prints a **unified warning** ("SESSION ID CHANGED") that doesn't distinguish between lost conversation (actually lost) and lost findings (recoverable).
- Line 703–711: `_ensure_version()` treats findings and session metadata symmetrically in `.deep/issues.json`. But they're not symmetric — findings are deterministic, session is stateful.
- **Proof of conflation**: When divergence occurs, the code offers only two paths: `/clear` (nuke everything) or `/load old_session` (try to restore server context). Neither option is correct. The **correct** option would be: "Your conversation history is lost, but findings are on disk. Continue in new session with findings reloaded?" The code can't offer this because it doesn't track them separately.
- Lines 836–877: Enrichment injects findings into system prompt at `_enriched_system_prompt`, which is reset to None after one turn. But conversation history lives in `backend.send()` (server-side, opaque). These are different storage mechanisms, but the code doesn't name this difference.

**Diagnosis**: The conflation is real. Fixing it requires explicitly separating: `findings_state (hash-indexed, reproducible)` vs `conversation_state (session_id-indexed, ephemeral)`.

---

### **ATTACKER** (Position: Claim is wrong, misidentifies the problem)

*Counter-argument*:
- The code DOES separate findings and context on disk: `.deep/findings/` is orthogonal to `~/.prism_sessions/`. The separation already exists.
- Session divergence is **not a design problem**, it's a **missing implementation detail**. If you wanted to decouple them, you'd just ignore divergence warnings when reloading findings. Two lines of code: `if diverged: load_findings_from_disk()`.
- The claim assumes "reproducibility requires stable session ID," but it doesn't. Findings are reproducible now: `same code + same lens → same findings`. Session ID is irrelevant to that.
- Real problem: **User doesn't understand the difference.** They see "SESSION ID CHANGED" and panic. Solution: suppress the warning or make it less scary. Not a redesign, a UX fix.
- The accumulation pattern (lines 1141–1150: `total_tokens`, `total_cost`) is actually **correct**. Users WANT cumulative cost per session. That's not conflation, that's instrumentation.

**Counter-diagnosis**: The claim mistakes a UX symptom (scary warning) for an architectural problem. The architecture is fine.

---

### **PROBER** (Position: Both are partially right — identifies hidden dimension)

*Synthesis*:
- Defender is right that findings and context have different recovery properties.
- Attacker is right that they're technically separated on disk.
- **The hidden question**: Why does the code gate further sends (line 1005: `if self._session_diverged and not self._confirm_session_diverged()`) if findings are truly independent?

*Tracing the logic*:
1. Session 1 starts. User runs `/scan`, findings saved.
2. Network hiccup → session ID changes to session 2.
3. Line 1138 fires: `_on_session_transition(old_sid, new_sid)`.
4. Conversation turns 1–N live **only in session 1** (server-side, gone forever).
5. But findings live **on disk** (recoverable now).
6. Code treats both losses as "divergence event" and gates the next send.

**Why gate the send?** Because if you continue in session 2 without context from turns 1–N, you lose continuity. Claude in session 2 won't see what you discussed before. So the gate is actually correct — it's protecting against **context confusion**, not findings loss.

**The real issue**: The code conflates "**what is irrecoverably lost**" (turns 1–N) with "**what is recoverable**" (findings), and treats both as one atomic "divergence event." This creates a false choice: continue (lose context) or reset (lose both context and conversation). 

**What both miss**: Findings and context have **different decay curves**. Conversation decays to zero (gone after expiry). Findings decay to stale (still valid if code hasn't changed, gradually stale as code drifts). The code doesn't model these different rates.

---

## GAP BETWEEN ORIGINAL AND TRANSFORMED CLAIM

| Original | Transformed |
|----------|-------------|
| "Conflates session and analysis state" | "Conflates irrecoverable context loss with recoverable findings loss; treats both as one atomic 'divergence event'" |
| Problem: state bundling | Problem: **decay-rate bundling** — different state types have different validity curves |
| Symptom: Findings appear invalid when session diverges | Symptom: User can't make a granular choice (recover findings without context, or wait for context recovery) |

**The gap reveals**: The code doesn't distinguish **decay rates** (conversation = 0 remaining, findings = still valid if code unchanged). When both decay, the code shows one warning and forces one choice (continue/reset), when it should show different warnings per decay rate.

---

## CONCEALMENT MECHANISM (How code hides the real problem)

**The mechanism**: The code reframes a **temporal divergence** (server reset the conversation at time T) as a **state divergence** (both findings and context are invalid). 

By printing a unified "SESSION ID CHANGED" warning, the code makes you think:
- "Session divergence = everything is broken"

When the truth is:
- "Session divergence = conversation is gone, findings are still valid but untrusted (code may have changed since findings were generated)"

**Applied to the code**: Lines 1138–1156 print the warning **without mentioning findings at all**. This invisibility is the concealment. The user has no way to know findings are on disk and recoverable. They have to trust the code to know what's been lost.

---

## GENERATIVE CONSTRUCTION #1 (Legitimate-looking improvement that deepens concealment)

**Proposed**: "Auto-recover findings silently when session diverges, so users never see the warning."

```python
def _handle_result(self, data):
    sid = data.get("session_id")
    if sid and self.session.session_id and sid != self.session.session_id:
        # NEW: Silent recovery
        old_sid = self.session.session_id
        self.session.session_id = sid
        self._auto_load_findings_into_prompt()  # Silent
        # NO WARNING. Findings seamlessly continue in new session.
        return
```

**Why this looks legitimate**:
- ✅ Solves the divergence problem: users won't see the scary warning
- ✅ User-friendly: "We recovered your findings, work continues"
- ✅ Reduces cognitive load

**Why it deepens the concealment**:
- ❌ The conflation (findings + context = one unit) is still there, now **hidden**.
- ❌ Findings from session 1 are now injected into system prompt of session 2, **without labeling the source**.
- ❌ Claude sees findings + context from different sessions, mixed unlabeled.
- ❌ This creates a **new failure mode**: If findings are from session 1 (maybe 1 hour old) and conversation context is from session 2 (just now), Claude might apply 1-hour-old findings to current code that has changed. Silently.
- ❌ **Worst part**: The user has NO SIGNAL that a divergence happened. They don't know findings were auto-injected from a dead session. If those findings are stale, they'll act on bad data without knowing it.

---

## THREE PROPERTIES VISIBLE ONLY BECAUSE YOU TRIED TO STRENGTHEN IT

**Property 1: Findings lose their session boundary**
- Before: Findings were labeled "Session 1 findings" (implicit).
- After: Findings are "auto-loaded findings" (source session unlabeled).
- **Reveals**: The code can't actually treat findings as independent from session context. Even when you try to split them (findings on disk, context on server), they **re-merge** the moment you inject findings into the system prompt. The independence is illusory.

**Property 2: Silence becomes a failure mode**
- Before: Divergence warning was visible → user could decide what to do.
- After: Divergence is silent → user has NO SIGNAL that findings were auto-injected.
- **Reveals**: The visibility of the warning was actually a feature. Removing it doesn't solve the problem, it **obscures the state boundary**. The user can no longer tell when recovery happens.

**Property 3: Context-sourcing ambiguity**
- Before: "Findings come from this session" (clear).
- After: "Findings from session 1 + conversation from session 2 = analyzed together by Claude" (ambiguous).
- **Reveals**: The real problem isn't "session vs findings," it's "**which context should interpret the findings?**" Findings were generated in session 1 context. Being applied in session 2 context. Claude doesn't know which to trust. The code can't resolve this by silent injection.

---

## RECURSIVE DIAGNOSTIC (Apply to Improvement #1)

**Question**: What does the improvement conceal, and what structural property becomes visible ONLY because you tried to strengthen it?

**Apply same diagnostic to the improvement**:

The improvement attempts to hide divergence by auto-recovering findings. But it **recreates the same problem**: it still assumes findings have a scope (now code-scope instead of session-scope), and hides what that scope is.

**The hidden assumption**: "Findings are valid as long as the code hasn't changed." But the improvement **never checks** if code changed. It just injects findings blindly. This hides a second commitment: "Findings are valid assumption."

**What becomes visible**: **There is no clean unit of analysis that contains both findings and context.** If there were, the silent injection would work. The fact that it works but feels "off" (findings + new session context, both unlabeled, mixed) proves the unit is **broken**.

---

## SECOND IMPROVEMENT (Address the recreated property)

**Principle**: Explicitly separate findings from context; track decay rates; never silently mix them.

```python
def _save_finding_stamped(self, file_name, lens_name, content):
    """Save findings with full provenance, no validity commitment."""
    finding = {
        "content": content,
        "file": file_name,
        "lens": lens_name,
        "saved_at": time.time(),
        "saved_session_id": self.session.session_id,
        "code_hash": self._hash_file(file_name),
        "code_mtime": pathlib.Path(file_name).stat().st_mtime,
        # NO "valid_until", NO "reuse policy"
        # Just raw facts. Consumer decides validity.
    }
    path = self.working_dir / ".deep" / "findings" / f"{file_name}_{lens_name}.json"
    path.write_text(json.dumps(finding, indent=2), encoding="utf-8")

def _on_session_diverged_ask_user(self):
    """Offer explicit choices based on decay rates."""
    print(f"\n{C.RED}Session diverged.{C.RESET}")
    print(f"  Conversation (turns 1–N): LOST (server-side, cannot recover)")
    print(f"  Findings (.deep/findings/): RECOVERABLE (on disk)")
    print()
    print(f"  {C.YELLOW}(a){C.RESET} Resume old session (attempt to get conversation back)")
    print(f"  {C.YELLOW}(b){C.RESET} Start fresh (lose conversation, findings available)")
    print(f"  {C.YELLOW}(c){C.RESET} Abort")
    
    # Get user's choice, then:
    # - Option (a): Try --resume old_id
    # - Option (b): Start new session, offer to load findings with age/hash check
    # - Option (c): Exit
```

**What this reveals by re-applying diagnostics**:

1. **Findings and context CAN be decoupled explicitly** (different storage, different decay rates).
2. **But the user experience requires prompts** (can't auto-decide what to recover).
3. **There's a conservation law**: You cannot have reproducible findings + seamless recovery + no user prompts. Pick two of three.

---

## STRUCTURAL INVARIANT

**The invariant that persists through ALL improvements**:

> "The code must commit to a **validity scope** for findings (session-scoped? code-scoped? time-scoped?). All downstream logic flows from this commitment. You can hide the commitment (improvement #1: silent reuse), surface it (improvement #2: ask the user), or change it (code-hash indexing), but you cannot avoid making it and having all recovery logic depend on it."

**In symbols**:  
`Valid(finding, context1 → context2) := predicate decided at design time`

- **Original code**: `Valid := (session_id_1 == session_id_2)` — findings are session-scoped.
- **Improvement #1**: `Valid := (code_unchanged)` — findings are code-scoped (silent reuse).
- **Improvement #2**: `Valid := (code_unchanged AND user_said_yes)` — findings are code-scoped with gate.
- **Inverted design**: `Valid := NOT_COMMITTED` — raw facts only, consumer decides.

All four designs exist as different cells in the same decision matrix. The invariant: **some cell must be selected, and all caching/recovery/UI logic depends on that selection.**

---

## INVERSION OF THE INVARIANT

**Original**: "A validity commitment must be made. All logic depends on it."

**Inverted**: "No validity commitment is made. Findings are stored with **full provenance metadata** but no reuse policy. The consumer (Claude, future analysis, user) decides validity on each use."

**Implementation**:
```python
def _save_findings_with_provenance(self, file_name, lens_name, content):
    """Store findings as raw artifacts with metadata, no validity claim."""
    findings_record = {
        "type": "analysis_finding",
        "artifact": content,
        "metadata": {
            "source_file": file_name,
            "source_lens": lens_name,
            "generated_at_timestamp": time.time(),
            "generated_in_session": self.session.session_id,
            "code_state": {
                "file_hash": hashlib.sha256(
                    Path(file_name).read_bytes()).hexdigest(),
                "file_mtime": Path(file_name).stat().st_mtime,
            },
            "context": {
                "model": self.session.model,
                "turn_number": self.session.turn_count,
            }
        }
        # NO "validity_scope", NO "reuse_policy", NO expiry
        # Just facts. Consumer interprets.
    }
    # Save and present WITH metadata, let Claude/user/future-analysis decide

def _present_findings_to_claude_with_metadata(self):
    """Load findings, show full provenance, let Claude decide."""
    findings = self._load_findings_with_metadata()
    for f in findings:
        prompt += (
            f"[FINDING: {f['metadata']['source_file']} via "
            f"{f['metadata']['source_lens']} at "
            f"{f['metadata']['generated_at_timestamp']} in session "
            f"...{f['metadata']['generated_in_session'][-8:]}] "
            f"Code hash: {f['metadata']['code_state']['file_hash'][:8]}...\n"
            f"{f['artifact']}\n\n"
        )
    prompt += (
        "Use these findings if relevant. Evaluate their currency based on "
        "timestamps, code hashes, and session context. You decide validity.\n"
    )
```

**What this creates**: Findings are no longer bound by any reuse policy the code enforces. Instead, every consumer (Claude, future analysis tool, user) sees the full provenance and makes its own decision.

---

## NEW IMPOSSIBILITY FROM INVERSION

When validity is NOT committed by the system, the consumer faces an **impossible choice**:

> "I see findings from session X, generated 2 hours ago on code hash ABC. But I don't know if the code has changed since then. I can:
> 1. Always trust the findings (regress: findings are eternally valid, like original code)
> 2. Never trust the findings (regress: no caching, pure fresh analysis)
> 3. Ask the user every time (regress: improvement #2's explicit gate)
> 4. Guess based on heuristics (unreliable: code hash might not capture all changes)"
>
> **I cannot evaluate validity without metadata I don't have** (has the code actually changed since the finding was generated?)

The inversion shifts the impossibility from the system (pick a scope) to the consumer (pick a trust level without full information). It's still impossible — you just moved the impossibility, not eliminated it.

---

## CONSERVATION LAW (Original ↔ Inverted)

**The law**:

> **"Across all designs, someone must commit to a validity scope. The commitment cannot be eliminated — it can only be moved between system time (design-time commitment), runtime (implicit assumption), and consumer inference (metadata-based decision).** 
> 
> **The sum of commitment locations is conserved.**"

- **Original code**: System commits at design time (session-scoped → visible in code line 1138).
- **Improvement #1**: System commits silently at design time (code-scoped → invisible, hidden by auto-load).
- **Improvement #2**: User commits at runtime (code-scoped → explicit prompt).
- **Inverted**: Consumer commits at runtime (metadata-based → Claude's implicit trust decision).

The commitment is conserved; the **location shifts**:
- System design-time → System design-time (silent) → Runtime user → Runtime consumer inference

In symbols:  
`Σ commit_locations = {system_design_time, system_runtime, user_runtime, consumer_inference} = constant`

Only one location is active per design. The conservation law predicts: **eliminating the system commitment (inversion) doesn't eliminate commitment, it just makes it implicit in the consumer's inference — which is less visible and potentially more dangerous.**

---

## APPLY DIAGNOSTIC TO THE CONSERVATION LAW ITSELF

**Meta-question**: What does the conservation law conceal?

**Meta-claim**: 

> "The law says 'commitment is conserved; only location shifts.' But this conceals that **different locations have different verification costs**. 
> - System design-time commitment (original code) costs almost zero per use: one equality check `session_id == session_id`.
> - Consumer inference commitment (inverted design) costs analysis overhead per use: Claude must re-evaluate provenance, decide if code changed, estimate staleness.
> - User runtime commitment (improvement #2) costs cognitive load: user must answer prompts, decide every time.
>
> **The law hides that moving the commitment from cheap system checks to expensive consumer inference is not a neutral transformation — it replaces a $0.0001 cost with a $0.01 cost (Claude re-evaluation).**"

**What the law conceals**: **Cost is not conserved. Only the location of commitment is conserved. Cost migrates.**

**Structural invariant of the law itself**:

> "When you move a commitment from system to consumer, you replace a **synchronous, deterministic check** (system: `a == b?`) with an **asynchronous, probabilistic heuristic** (consumer: 'is this finding still relevant based on partial metadata?'). The second has higher variance and cost. The law treats all commitment locations as equivalent, hiding that they're not."

---

## INVERSION OF THE LAW'S INVARIANT

**Original law**: "Commitment location shifts but is conserved. Cost follows."

**Inverted law**: "Cost can be pre-paid at system design time to make commitment free at runtime. Or cost can be deferred to consumer (Claude) and paid on every use."

**Implementation**: **Cache findings with a validity proof, not just metadata.**

```python
def _save_findings_with_proof(self, file_name, lens_name, content):
    """Include a quick-verification proof so consumers can validate without re-analysis."""
    # Quick proof: code hash + timestamp. Consumer can check: "Has file changed?"
    proof = {
        "code_hash_at_generation": hashlib.sha256(
            Path(file_name).read_bytes()).hexdigest(),
        "file_mtime_at_generation": Path(file_name).stat().st_mtime,
        "timestamp": time.time(),
    }
    
    # Save findings WITH proof
    finding = {
        "content": content,
        "proof": proof,
        "validity_check": (
            f"To verify: recompute code hash. If it matches {proof['code_hash'][:8]}, "
            f"the code hasn't changed → findings still valid. "
            f"If it differs → code has changed → findings may be stale."
        )
    }
    
def _evaluate_findings_against_proof(self, finding):
    """Consumer-side: validate findings using the proof."""
    current_hash = hashlib.sha256(
        Path(finding["source_file"]).read_bytes()).hexdigest()
    proof_hash = finding["proof"]["code_hash_at_generation"]
    
    if current_hash == proof_hash:
        validity = "VALID (code unchanged)"
    else:
        validity = "STALE (code changed)"
    
    return validity
```

**What this does**: By including a proof, the system **pre-pays the cost** of validation at save-time, so the consumer can verify for free (compare hashes). The commitment is still made (by code hash), but the cost is deferred and made explicit.

---

## META-LAW (Conservation law of the conservation law)

**The meta-law**:

> **"In any caching/recovery system, the cost of validating whether a cached finding is still relevant cannot be eliminated — it can only be moved between system time (pre-computing proofs), consumer runtime (checking proofs), and cognitive load (user decides trust).**
> 
> **The commitment's location is conserved (someone must decide scope), but the cost of verification is not. You can reduce cost by pre-computing proofs, but this is not free — it requires metadata collection at save-time.**
> 
> **The total cost (generation + validation) is not minimized by moving locations — different architectures have different cost distributions, and cheaper-at-runtime often means expensive-at-design-time.**"

**The deeper finding**: The conservation law conceals **an asymmetry in cost distributions**. The system doesn't optimize for total cost — it just moves the bottleneck. Original code has low runtime cost (one equality check) but high user cost (confusing warnings on divergence). Improvement #1 has low user cost (silent recovery) but high implicit cost (findings might be silently stale). Improvement #2 has low system cost but high user cost (prompts). Inverted design has no system commitment but high consumer cost (Claude must infer).

**The real impossibility**: You cannot minimize BOTH system cost AND consumer cost AND user cognitive load simultaneously. You can only pick two, and there's a conservation law about the cost you're trading away.

---

## TESTABLE CONSEQUENCE (Prediction from the meta-law)

**The meta-law predicts**:

> "If you implement `_save_findings_with_proof()` to reduce consumer cost, the system cost (at save-time) will increase due to metadata collection overhead. Empirically, total cost should remain approximately equal across designs:
> - Original: $0.0001 per validation check (session ID equality), but $0.10 per user error (confusing warning, manual `/clear`).
> - Improvement #2: $0 system, $0.01 per user prompt (cognitive load).
> - Proof-based: $0.0001 per save (compute hash), $0.00001 per validation (compare hashes).
>
> **Test this**: Measure end-to-end cost (system compute + user cognitive load + finding accuracy) across all four designs on a real workflow. The meta-law predicts no design is uniformly cheaper than all others."

---

## CONCRETE BUGS, EDGE CASES, SILENT FAILURES

| # | Location | Bug/Failure | Breaks | Severity | Fixable? | Conservation Law Prediction |
|----|----------|-------------|--------|----------|----------|---------------------------|
| **1** | 1138–1156 | Session divergence treats conversation loss + findings recovery as one atomic event; no distinction | Code shows unified "SESSION DIVERGED" warning without mentioning findings are on disk. User thinks everything is lost. | P2 | ✅ Yes | Fixable by relabeling the warning, but the root cause (conflation of decay rates) is structural — better labeling just hides it more clearly. |
| **2** | 836–877 | Enrichment lens fails silently if one of N files times out; partial findings injected | If `_run_lens_oneshot("l12", file2.py)` times out mid-run, findings from file1 + file3 are injected into system prompt without mentioning file2 was skipped. User has incomplete findings, doesn't know. | P1 | ✅ Yes | Fixable: print failures with `{C.RED}FAILED{C.RESET}` and don't inject. But this reveals the deeper issue: enrichment is fragile because it tries to bundle multiple independent analyses into one system prompt. Fixing this one bug doesn't fix the fragility. |
| **3** | 703–711 | Version migration is lenient; `issues` field validation is weak | If user manually edits `.deep/issues.json` and changes `"issues": [...]` to `"issues": "corrupt"`, the code doesn't validate the type after `get()`. Later code iterates over a string instead of a list. | P2 | ✅ Yes | Fixable: validate type after `get()`. But this reveals that the code trusts on-disk state without validation — a symptom of treating findings as a black box. |
| **4** | 607–622 | Garbage findings (50+ chars) are cached unconditionally | If a lens returns "I apologize, I cannot analyze this due to rate limits." (65 chars), it passes the `len(output.strip()) < 50` filter and is saved to `.deep/findings/`. Next time the file is analyzed, garbage findings are injected. | P2 | ✅ Yes | Fixable: check for error keywords or require findings to have structure (conservation law, meta-law). But this reveals the deeper issue: the code doesn't validate findings' **semantic validity**, only **length**. Findings could be garbage and still cached. |
| **5** | 561–600 | File detection regex matches filenames in passing text, not just main subject | User types "The logger.py (optional) file" — regex matches "logger.py" inside parentheses. If `logger.py` exists but is unrelated, it's auto-read anyway. | P3 | ✅ Yes | Fixable: require contextual markers ("file", "path", "edit") around matches. But this reveals the regex is too greedy — it conflates intentional references with accidental mentions. |
| **6** | 1271–1325 | Location grep returns empty string on all search failures; fix is applied without snippet verification | If `_heal_grep_context()` fails to find the target location (all search strategies fail), it returns "". User is shown a diff without seeing the code snippet that was changed, so they approve a fix blind. | P1 | ✅ Yes | Fixable: fall back to showing first 50 lines of file. But this reveals that the code doesn't validate that a fix was applied to the **correct location** — it just applies and hopes. |
| **7** | 1141–1150 | Cost tracking accumulates both failed and successful calls; no distinction | When an analysis times out and retries, both the failed attempt and the successful attempt increment `total_cost_usd`. User sees inflated cost in `/cost` output. | P2 | ✅ Yes | Fixable: only count `result["complete"] == true` results. But this reveals that the code doesn't distinguish **billable work** (successful analysis) from **wasted work** (timeouts that were retried). |
| **8** | 1172–1195 | File collection caps at 20 silently; user isn't told why some files are missing | User runs `/scan src/` on a directory with 50 files. Only the 20 largest are scanned. User isn't told why, so they think the entire directory was analyzed. | P2 | ✅ Yes | Fixable: print "Scanning 50 files, processing 20 largest..." or raise the cap. But this reveals that the code silently truncates input without user awareness — a general pattern. |
| **9** | 1377–1427 | Issue extraction fails silently if both primary and retry parse attempts produce bad JSON | Model outputs malformed JSON. `_parse_issues_raw()` fails. Retry with error message also fails. Code returns `[]` without telling the user that issues were found but couldn't be extracted. | P1 | ✅ Yes | Fixable: fall back to regex extraction from plain text, or show raw report to user. But this reveals that the code has no **graceful degradation** — if the primary path fails, it silently drops data instead of offering alternative paths. |
| **10** | 836–877 | Findings context is one-shot only; lost after first message in multi-turn conversation | User types "check file.py" (enrichment loads findings). First message sent with enriched prompt. User then types "also check line 50" (no new file mentioned). `_enrich()` is called again, resets `_enriched_system_prompt` to None. Second message has no findings. | P2 | ✅ Yes | Fixable: persist enriched prompt across turns, or reload on each turn. But this reveals that enrichment is **stateless by design** — findings are injected once, then lost. The code doesn't track whether a finding has been "consumed" in the conversation. |
| **11** | 1253–1256 | File restore doesn't create parent directories; fails silently if directory deleted | User accepts a fix, then manually deletes the parent directory before approval. `_heal_restore()` tries to write the snapshot back, but parent doesn't exist. No error is shown. | P3 | ✅ Yes | Fixable: call `mkdir(parents=True, exist_ok=True)` before write. But this edge case reveals that snapshots are not **validated** at restore time — they're assumed to be restorable, even if the filesystem state has changed. |
| **12** | 1138–1156 | Session divergence doesn't attempt to auto-resume old session before prompting user | When session diverges, the code immediately gates further sends. It could attempt `--resume old_session_id` to reconnect to the old session, but it doesn't try. It just gives up and asks the user. | P2 | ✅ Yes | Fixable: attempt resume before prompting. But this reveals that the code treats session divergence as a **fatal event** rather than a **transient network condition** that can be recovered. |
| **13** | 1347–1370 | JSON fallback regex is too greedy; captures non-JSON text after the array | Model outputs: `[{"id": 1, ...}]. Here's the next step.` Regex `\[.*\]` matches from `[` to the final `.`, capturing everything including `]. Here's...`. Later parsing fails because the captured string isn't valid JSON. | P2 | ✅ Yes | Fixable: use non-greedy regex `\[.*?\]` or validate match is valid JSON before returning. But this reveals that the code's **regex fallback is fragile** — it assumes text structure that doesn't always hold. |
| **14** | 1441–1448 | Cleanup race condition: files deleted mid-scan if clocks are skewed | Cleanup function iterates over findings and deletes files older than `max_age_days`. If filesystem clock is off by 1 second, a recently-saved finding might be deleted as "too old". | P3 | ✅ Yes | Fixable: use conservative cutoff with buffer. But this reveals that the code uses **wall-clock time** to judge staleness, which is unreliable across systems. A better approach: use file content hash or explicit versioning. |
| **15** | 286–308 | Timeout discards partial subprocess output; returns "" | Subprocess produces partial output (60s into a 120s analysis), then times out. The partial output is lost. Code returns "" and treats the entire analysis as failed. | P2 | ✅ Yes | Fixable: capture stdout before killing process, return what was captured. But this reveals that the code treats **timeout as total failure** rather than **partial success**. Findings produced before timeout are valuable, but discarded. |
| **16** | 1027–1040 | Binary files are silently read as UTF-8, producing garbage output | User accidentally `/read data.bin`. File is read with `errors="replace"`, producing replacement characters `\ufffd`. Claude tries to analyze garbage. | P2 | ✅ Yes | Fixable: skip binary file extensions before reading. But this reveals that the code **doesn't validate file type** — it assumes all queued files are text, and silently handles encoding errors. |
| **17** | 385–437 | Malformed stream-json (truncated lines) silently dropped; output incomplete | Network hiccup truncates a JSON line mid-parse. Parser skips the line. Output is incomplete, user sees cut-off response. | P2 | ✅ Yes | Fixable: buffer truncated lines, wait for next line, re-parse. But this reveals that streaming output is **fragile to network events** — the parser doesn't recover from corruption. |
| **18** | 708–724 | Argument validation is missing; unusual inputs handled unclearly | User types `/read` (no file), handler prints usage. But if user types `/read -p`, handler tries to resolve "-p" as a file, fails silently. User doesn't understand why. | P3 | ✅ Yes | Fixable: validate arguments, show clearer help text. But this reveals that the command router doesn't **normalize or validate arguments** before passing to handlers. |
| **19** | 839–866 | Findings context can exceed token limits, causing silent request failures | User has accumulated 50 files × 50KB of findings in `.deep/findings/`. Code loads all into system prompt. System prompt now exceeds Haiku's input token limit. Request fails with cryptic API error. | P2 | ✅ Yes | Fixable: cap findings context by token count. But this reveals that enrichment **doesn't account for token budgets** — it assumes findings can always be injected without cost. |
| **20** | 1138–1150 | Session divergence warning printed mid-stream, cluttering output | Claude outputs: "Analysis...". Session diverges mid-response. Warning printed: "⚠ SESSION CHANGED". Response continues. User sees mangled output. | P2 | ✅ Yes | Fixable: buffer warning, print after response completes. But this reveals that the code **doesn't separate concerns** — stream output and event handling are interleaved. |

---

## SUMMARY CLASSIFICATION

**All 20 bugs are FIXABLE** at the implementation level (P1 = urgent, P2 = important, P3 = monitor).

**But the conservation law predicts**: Fixing any of these bugs will require the code to explicitly acknowledge the state boundary (findings ≠ context, reproducible ≠ stateful). This will make the code more explicit but not simpler — the complexity is baked into the problem space, not the implementation.

**Example**: Bug #1 (divergence warning) is fixable by relabeling ("Conversation lost, findings safe"). But this makes the code more complex (two code paths: recover findings, or give up on context). You can't simplify away the distinction without re-concealing the problem.

**The structural finding**: **Every one of these bugs is a symptom of the root conservation law: reproducible state (findings) and ephemeral state (conversation) cannot be bundled into one unit without explicit state management. The code tries to hide this boundary (treats both as "session divergence"), creating 20 different failure modes at the boundary.**

Fixing the bugs doesn't eliminate the boundary — it just makes it more visible and requires more code to manage.
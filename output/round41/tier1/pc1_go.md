# L12 Structural Analysis: RateLimiter

## PHASE 1 — STRUCTURAL ANALYSIS

### Three Properties Claimed

1. **Thread-safety** — mutex protects all state access
2. **Temporal accuracy** — precise token refill based on elapsed time
3. **Fairness** — requests compete equally for available tokens

### Impossibility Proof

Thread-safety + temporal accuracy **contradicts** fairness under load:

- **Contention pattern**: High concurrency → threads queue on mutex → each waits for predecessor's critical section
- **Time drift**: Thread A captures `now`, computes refill, decrements. Thread B (queued) captures `now` (later), but its `lastTime` was updated by A to A's `now`. Thread B's elapsed time is **artificially compressed**.
- **Skewed distribution**: Early threads see full refill windows; later threads see truncated windows → later threads get fewer refill tokens despite identical call timing

**The three properties cannot coexist** because mutex serialization corrupts the temporal baseline each caller observes.

### Conservation Law

```
Throughput Fairness × Lock Contention = Constant
```

Higher concurrency → more contention → more temporal distortion → less fairness. The algorithm "works" but redistributes rate-limiting burden onto late-arriving threads.

### Concealment Mechanism

The mutex hides the **serialization artifact** inside `now := time.Now()`. Each caller believes it observes "current" time, but `lastTime` is a **shared mutable anchor** that each caller moves for the next. The algorithm appears fair because each call executes identical code, but the shared state creates **implicit temporal coupling** between otherwise independent callers.

### Improvement That Recreates the Problem

**Fix**: Per-caller time tracking with global token pool:

```go
type Caller struct { lastTime time.Time }
type RateLimiter struct {
    mu      sync.Mutex
    callers map[int64]*Caller
    tokens  float64
    // ...
}
```

**Deeper problem**: Now you've distributed the time anchor, but introduced:
1. **Memory unbounded** — callers never removed
2. **Caller identity problem** — how to identify callers fairly?
3. **New conservation law**: `Memory × Fairness = Constant`

The "improvement" recreates the original trade-off (accuracy vs. resources) at a deeper layer.

---

## PHASE 2 — KNOWLEDGE AUDIT

| Claim | Classification | Confidence | Notes |
|-------|----------------|------------|-------|
| Mutex provides thread-safety | **STRUCTURAL** | 1.0 | `sync.Mutex` + Lock/Unlock visible in source |
| Token bucket algorithm present | **STRUCTURAL** | 1.0 | `tokens`, `rate`, `max`, refill logic all visible |
| `lastTime` shared between callers | **STRUCTURAL** | 1.0 | Single `lastTime` field on shared struct |
| High contention → temporal drift | **STRUCTURAL** | 0.85 | Derivable from mutex + shared `lastTime` + `now` capture pattern |
| Later threads see truncated windows | **STRUCTURAL** | 0.80 | Logical consequence of serialization + shared anchor |
| This causes unfairness | **CONTEXTUAL** | 0.70 | Depends on actual contention level, request patterns |
| Per-caller tracking would fix it | **CONFABULATED** | 0.45 | Not verified; introduces new problems I haven't proven |

---

## PHASE 3 — SELF-CORRECTION

### Confidence < 0.5 Revision

**"Per-caller tracking would fix it"** — **UNVERIFIABLE** from source alone. Removed from conclusions. The fix direction is speculative; the actual impossibility proof stands without it.

### Corrected Defect Table

| Location | Defect | Severity | Type | Confidence |
|----------|--------|----------|------|------------|
| L22-25 | `lastTime` updated to caller's `now` even when tokens insufficient | Low | Fixable | 1.0 |
| L20-26 | Shared `lastTime` creates temporal coupling between serialized callers | Medium | Structural | 0.85 |
| L18-26 | No distinction between "tokens available" and "tokens fair to claim" | Medium | Structural | 0.80 |
| L9 | No `TryLock` or timeout — blocked callers wait indefinitely | Low | Fixable | 1.0 |

### Verified Conservation Law

```
Serialized Refill × Concurrent Callers = Temporal Distortion
```

**Meta-observation**: The code's simplicity (one mutex, one time anchor) **is** the concealment. A more complex implementation would make the trade-off visible; this one hides it in the interaction between `sync.Mutex` and `time.Now()`.

---

## Final Output

**Conservation Law**: `Throughput Fairness × Lock Contention = Constant`

**Verified Defects**:
1. Shared `lastTime` creates temporal coupling (STRUCTURAL, 0.85)
2. Token-insufficient calls still advance `lastTime` (STRUCTURAL, 1.0)
3. No contention bounds — unbounded wait (STRUCTURAL, 1.0)
4. Fairness undefined under serialization (STRUCTURAL, 0.80)

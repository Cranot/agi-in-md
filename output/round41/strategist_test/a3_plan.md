## Strategy

**1. Goal:** Find ALL security vulnerabilities in Starlette routing.py, classify by severity, and prioritize fixes by risk/effort ratio.

**2. Constraints:**
- Budget: Standard (~$0.10-0.25 acceptable)
- Trust level: HIGH (security vulnerabilities must be real, not false positives)
- Domain: Python web framework routing code (authentication/authorization-adjacent)

**3. Optimal sequence:**
1. **L12 scan** — Immediate structural depth + bug detection (1 call, ~$0.05)
2. **Claim prism** — Security-adjacent code, assumption inversion finds vulnerabilities (validated 9.5/10 on AuthMiddleware)
3. **Optional: SDL trust** — Trust topology for security boundary analysis if needed

Let me execute:

---

## Execution Plan

### Step 1: L12 Structural Analysis
**COMMAND:** `/scan` with L12 prism on the routing code
**EXPECTED OUTPUT:** Conservation law + structural defects + bug table with severity
**DECISION POINT:** If security vulnerabilities found, proceed to claim prism for deeper inversion. If only structural issues, may skip step 2.

### Step 2: Claim Prism (Security Focus)
**COMMAND:** `/scan` with claim prism, targeting security assumptions
**EXPECTED OUTPUT:** Inverted assumptions exposing attack vectors
**DECISION POINT:** Cross-reference with L12 findings. Unique findings = proceed to synthesis.

---

Executing now:

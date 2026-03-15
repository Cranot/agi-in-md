**Adversarial Review:**

1. **No file specified.** Strategy references "Starlette routing.py" but no path provided. First step should be locating the file.

2. **Step 2 is unconditional when it should be conditional.** Running claim prism blindly wastes $0.05 if L12 finds nothing security-relevant.

3. **Missing synthesis.** Two prisms = two separate outputs. No step to merge/deduplicate findings.

4. **SDL trust shouldn't be optional for security.** Trust topology is critical for authorization bypass analysis.

5. **No fix loop.** Goal says "recommend fix order" but no `/scan fix` to validate fixes work.

6. **Missing adversarial pass.** Security findings need stress-testing before trusting them.

**REVISED STRATEGY:**

```
1. Locate and read the target file (establish scope)
2. L12 scan → assess security relevance of findings
   IF security issues found:
3. Claim prism → assumption inversion
4. SDL trust → trust boundary analysis  
5. Synthesis → merge, dedupe, rank by severity
6. Adversarial pass → stress-test top 3 vulnerabilities
   OUTPUT: prioritized fix list with effort/risk ratios
```

**Cost:** ~$0.15-0.20 for full pipeline, $0.05 if L12 finds nothing security-relevant.

---

Now, I need the actual file to execute. Where is `routing.py` located? Or should I search for it?

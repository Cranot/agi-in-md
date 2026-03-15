# README Critique: AGI in md

## Overview
Strong voice, compelling hook, real swagger. The "dare" section is excellent — it's memorable and creates a binary test for the reader. Preserve all of that energy. The issues are structural: credibility gaps, missing practical details, and a weak close that doesn't match the strong opening.

---

## Structural Weaknesses

### 1. Comparison boxes at top lack provenance
**Location:** Lines 9-31 (the Opus vs Haiku comparison boxes)

**Problem:** The opening hook shows specific outputs ("HTTP cookie deletion semantics...") but gives zero context. What code was analyzed? What question was asked? Was this cherry-picked? A scanning reader sees "proof" but has no way to verify it's representative.

**Fix:** Add a small caption: "Analyzing Starlette's session middleware with `/scan`" or similar. Name the input so readers can reproduce it.

---

### 2. Install section is incomplete
**Location:** Lines 62-70 (Install section)

**Problem:** 
- `python prism.py` — does this start a REPL? Print help? What happens?
- "Requires Claude Code" — what IS Claude Code? CLI tool? API? VS Code extension?
- No Python version requirement
- No dependency list (requests? anthropic SDK?)
- No API key setup instructions

**Fix:** 
```bash
# Requirements
Python 3.9+
Claude Code CLI (npm install -g @anthropic/claude-code)
ANTHROPIC_API_KEY environment variable

# Install
git clone https://github.com/your-repo/agi-in-md.git
cd agi-in-md
python prism.py  # Starts interactive REPL
```

---

### 3. Repository URL is placeholder
**Location:** Line 64

**Problem:** `https://github.com/your-repo/agi-in-md.git` is obviously a placeholder. Ship-blocking issue.

**Fix:** Update before publishing or remove the clone command and just say "Clone this repo."

---

### 4. "Depth" metric undefined
**Location:** Lines 34-39 (The Numbers table) and throughout

**Problem:** "9.8 avg vs 8.2 avg" — what IS depth? Who scores it? Is it AI-evaluated? Human? The FAQ mentions "AI-evaluated" but by the time a skeptical reader gets there, they've already seen the claim 10 times.

**Fix:** Add a one-liner near The Numbers: "Depth scored by Claude Opus blind evaluation against a 10-point rubric (see `research/scoring.md`)." Link to methodology.

---

### 5. "Cooked prism" term appears without definition
**Location:** Line 166 (AIME results table)

**Problem:** "Haiku + cooked prism" — the term "cooked" isn't defined anywhere. Reader assumes it means "custom-generated" but shouldn't have to guess.

**Fix:** Either define it inline ("cooked = auto-generated for this domain") or link to where the cooker is explained.

---

### 6. No full example output
**Location:** Missing entirely

**Problem:** The README claims depth 9.8 output but never SHOWS what that looks like. Readers want to see: input → prism → full output. The comparison boxes are excerpts, not complete analyses.

**Fix:** Add a section "What L12 Output Looks Like" with:
- A 20-line code snippet
- The complete `/scan` output
- Let readers judge the depth themselves

---

### 7. What IS this? — unclear until halfway through
**Location:** Lines 72-85 (How It Works)

**Problem:** The README opens with results, not with the product. A scanning reader reaches line 60 before understanding this is "a markdown file used as a system prompt." The reveal should come earlier.

**Fix:** Add one sentence after the hook, before The Dare:
> "A **cognitive prism** is a 332-word system prompt that routes models through a 12-step analytical pipeline. This repo contains 7 production prisms + the tooling to use them."

---

### 8. Closing is weak
**Location:** Lines 197-217 (What's Next + License)

**Problem:** The README opens with swagger ("close this repo and keep overpaying") but ends with a dry roadmap and "MIT." No final push. No call to action. The energy dissipates.

**Fix:** Add a closing paragraph that matches the opening:
> **Stop paying for depth. Start prompting for it.**
> 
> Clone the repo. Run `/scan` on your hardest code. If L12 doesn't surprise you, delete it and keep your workflow. But if it does — the prisms are MIT licensed. Use them anywhere.

---

### 9. FAQ answer on model support is weak
**Location:** Line 184 ("Does it work on other models?")

**Problem:** "Tested on Claude only. GPT-4o, Gemini, Llama testing is planned." This is fine, but the README's entire claim rests on Haiku vs Opus. If a reader uses GPT-4, they have no idea if this works.

**Fix:** Be specific about uncertainty: "Unknown. The construction operation is model-agnostic in theory, but prism wording was tuned on Claude. If you test on other models, open an issue with results."

---

### 10. No link to the actual prism file
**Location:** Throughout

**Problem:** The README references "332 words" and "l12.md" multiple times but never links directly to the file. Curious readers want to SEE the prompt.

**Fix:** Link `prisms/l12.md` explicitly: "See [prisms/l12.md](prisms/l12.md) for the full L12 prism."

---

## Missed Opportunities

### 1. No "When This Fails" section
Adding a limitations section would actually strengthen credibility. When does L12 produce shallow output? What kinds of code/questions don't benefit? One paragraph on boundaries makes the claims more trustworthy.

### 2. No single-command try
A reader who's curious but lazy has no way to try this without cloning. Consider:
- A web demo link
- A single curl command against a public endpoint
- A GitHub Codespaces button

### 3. "The Dare" could be more actionable
"The Dare" is great marketing, but make it more concrete: "Run `/scan` on any file over 100 lines. If the output doesn't teach you something new about your own code, close the tab."

### 4. No contributor appeal
For a research-adjacent project, there's no ask for help. "Want to test on GPT-4? Open a PR with results." would cost nothing and might attract contributors.

### 5. Project structure section is buried
The structure section (lines 191-199) is useful for understanding what you're cloning, but it's near the end. Consider moving it up or integrating it into Install.

---

## Summary

| Issue Type | Count |
|------------|-------|
| Credibility gaps | 3 (comparison provenance, depth metric undefined, no full output) |
| Missing practical info | 4 (install requirements, API setup, what prism.py does, repo URL) |
| Unclear terminology | 2 ("cooked prism", what the product IS) |
| Weak close | 1 |
| Missed conversion opportunities | 5 |

**Priority fixes:**
1. Add provenance to the opening comparison boxes
2. Complete the install section with actual requirements
3. Show one complete example output
4. Rewrite the closing to match the opening energy
5. Define "depth" earlier, not buried in FAQ

The voice is strong. The structural gaps are fixable in 30 minutes.

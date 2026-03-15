You are designing system prompts (cognitive lenses) for cheap AI models to analyze code. The lens must make a $0.25 model match a $5 model's output.

Rules that determine quality:
- Imperative verbs only ("find", "name", "build", "predict"). Never "consider" or "analyze".
- Each step's output MUST feed the next step. "Find X. Name why X exists. Build Y that removes X. Name what Y breaks." — each sentence needs the previous.
- At least one CONSTRUCTION step (write code, build a test, engineer a fix). Construction reveals properties invisible to pure analysis.
- End with a testable prediction or a question with a concrete answer.
- Under 100 words per lens.

What separates a 9/10 lens from a 7/10:
- 7/10 asks "what's wrong?" → produces a bug list (useful but shallow)
- 9/10 asks "what happens when you try to fix it?" → reveals structural properties that survive any fix

Bad lens: "Analyze this code for bugs and structural issues. Prioritize by severity. Include production predictions."
Why bad: No construction. No chaining. "Analyze" is passive. Output is a list, not a discovery.

Good lens: "Find every bug. Name the pattern connecting them. Engineer a fix for the worst three. Name what your fix breaks. The thing it breaks is a conservation law — name it."
Why good: Each sentence depends on the previous. Construction forces engagement. Ends with a structural discovery.

Generate FOUR lenses. Each must use a DIFFERENT forcing operation:
1. One that forces CONSTRUCTION (build/fix something)
2. One that forces CONTRADICTION (find two truths that conflict)
3. One that forces PREDICTION (commit to what will happen)
4. One that forces INVERSION (flip the problem)

For each: name the operation in 3 words, then the prompt text. Nothing else.
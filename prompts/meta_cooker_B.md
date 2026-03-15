You are designing cognitive lenses — system prompts that change how AI models frame code analysis problems.

The best lenses share these properties:
- They use imperative verbs ("find", "name", "show", "predict")
- They force a sequence of operations where each step's output feeds the next
- They include at least one construction step (build/fix something) because construction reveals properties that pure analysis cannot
- They end with a prediction or testable claim
- They are under 120 words

The lens will be given to a small, cheap AI model analyzing code. The goal is maximum insight per dollar — the output should match or exceed what a vanilla large model produces.

Generate THREE different lenses, each using a different analytical angle. For each lens, name the angle in 3 words, then give the prompt text. No explanation beyond the angle name.
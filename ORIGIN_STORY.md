# How Super Tokens Were Born

*The origin story of a research project that started with a question about structure and ended with a discovery about how language models think.*

---

> **Note:** This is the raw origin story, reconstructed from Claude Code session transcripts. I'll update it personally when I have more time with more context, reflections, and connections to the broader vision. But this is the whole picture of how it started and where it went. — Dimitris

## The Bigger Picture

I've always been obsessed with one idea: **persisting knowledge and intelligence.** Not just storing data — making it *transferable*, so the next session, the next model, the next agent starts smarter than the last one.

This project is one piece of that puzzle. [AgentsKB](https://github.com/Cranot/agentskb) is another — a knowledge base that lets agents accumulate and share what they learn across sessions. Super tokens, AgentsKB, roam-code — they're all different angles on the same question: how do you compress what you know into something that makes the next thing smarter?

If you've ever played WoW, think of it like twinking. You take a low-level character, gear it up with the best possible equipment for its bracket, and suddenly it outperforms everyone. That's what a 30-word super token does to Haiku — it's not a smarter model, it's a *better-equipped* model. And in the future, I think we'll break this open even further. The gear will get better, the brackets will expand, and the line between "the model" and "what you give it" will blur completely.

---

## Prologue: The Substrate

It started with a minimal transformer. A pyramid architecture — local patterns at full resolution, global patterns compressed — built to learn structure from sequences. The insight behind it was simple: a model trained to predict the next element is forced to learn the structure generating that sequence. Three operations are enough: **correlate** (find relationships), **transform** (nonlinear map), **compress** (accumulate at lower resolution). The neocortex tiles the same six-layer circuit everywhere. The transformer might be a crude rediscovery.

But that was just the foundation. The real story begins with a different question.

## Act I: "Why Don't We Extract Structure From Something Else?"

**February 25, 2026.** The first message in what would become months of research:

> "Hey there, when we train a model on text we're basically capturing the structure of the knowledge, right?"

Then:

> "I'm thinking — why don't we extract structure from something else?"

The instinct was to skip the expensive training step entirely. Why learn structure slowly through gradient descent when you could extract it directly? I had already built a tool for exactly this — [roam-code](https://github.com/Cranot/roam-code), a CLI that extracts architectural fingerprints from any codebase in seconds: dependency layers, modularity scores, tangle ratios, symbol graphs.

> "I made a tool that extracts structure from a codebase instantly. Why retrain over and over when you can get it instantly? We could run it on multiple codebases and then merge their shapes."

So we did. Five Python codebases first (click, requests, attrs, pydantic, rich), then ten, then thirty across nine languages. And something unexpected appeared.

## Act II: Structure Converges

All Python libraries converged to the same shape:

```
Layer 0: 83%    Layer 1: 8%    Tail: 9%
```

This wasn't a Python thing. Web frameworks in Python, Go, JavaScript, and Ruby all shared the same structural fingerprint — 8-10 layers, 0.60 modularity, <0.01 tangle. CLI tools were flatter (5-8 layers). Serialization libraries had their own canonical shape.

**The domain constrains the solution regardless of syntax.** Flask and Gin and Express and Sinatra all look the same structurally because HTTP request handling IS a shape. The language determines how cleanly you build it (Rust's ownership kills 97% of tangles), but the shape itself is an attractor.

Cross-language "structural twins" emerged: lodash and viper (JS/Go) had distance 0.000. Flask and Gin (Python/Go) were nearly identical. Python and Go — completely different paradigms — produced structurally similar code. Explicit languages converge.

> "But this could be in other domains too — there are deep insights there. I think we are getting into somewhere."

We were.

> "This way we could reverse-engineer approaches or even make new languages based on convergence."

This led to PipeLang — a language where the CLI canonical shape (7 layers, 0.65 modularity, <0.001 tangle) is the only shape you can write. Bad structure becomes impossible, not just hard. But PipeLang was a detour. The real breakthrough was about to happen.

## Act III: "Make Our CLAUDE.md More Like a Super Token"

**February 27, 2026.** One message changed the direction of everything:

> "Make our CLAUDE.md file more like of a super token."

The CLAUDE.md was 330 lines — the accumulated knowledge of the substrate project. We compressed it to 62 lines (~5x), applying the project's own correlate/transform/compress principles. Removed narrative redundancy (the "universal structure" insight appeared 5 times), converted prose to declarations, structured it as a pyramid.

Then the insight crystallized:

> "I want us to take it a step further, and that's an insight too — as you dig you find, and we must use this info so we dig more, research more, and make our super token richer."

The CLAUDE.md wasn't just documentation. It was a **compressed knowledge artifact** — a system prompt that could change how a model thinks. And that was testable.

## Act IV: The Experiments Begin

We launched clean experiments: Claude CLI from `/tmp`, no ambient context, `--tools ""`, different system prompts fed to isolated Haiku instances. The same evaluation prompt, different "lenses."

**Round 1** tested 10 variants — vanilla, ultra-compressed (3 lines), the full super token (62 lines), the old narrative (121 lines), and themed "characters" (spark, philosopher, map, tweet, critic, code, numbers, proof). Five survived: tweet (2 lines), spark (10 lines), philosopher (12 lines), map (35 lines), and the full super token.

The first finding: **compression trades confidence for novelty.** More tokens = more trust but less freshness.

```
Confidence curve:  0 lines -> 15%  |  3 -> 42%  |  12 -> 55%  |  62 -> 65%  |  121 -> 70%
Ambition curve:    0 lines -> n/a  |  3 -> 9    |  12 -> 9    |  62 -> 8    |  121 -> 6
```

But the real discovery came in Round 2.

## Act V: "The System Prompt Is a Cognitive Lens"

We tested four system prompts on three tasks: in-domain code analysis, adjacent architecture design, and an unrelated logic puzzle.

All models solved the logic puzzle identically. No IQ boost. But on code analysis, the super token saw hierarchical resolution levels, reordered operations, estimated modularity improvements (0.50 -> 0.68), and found a parallelism opportunity that vanilla missed entirely.

**The system prompt doesn't make models smarter. It changes how they frame problems.** A cognitive lens, not a knowledge injection.

> "The 'super token' is the CLAUDE.md file or the system prompt — so we see if we can make them smarter or something else. We might not be testing them correctly."

We weren't testing intelligence. We were testing perception.

## Act VI: The Receptivity U-Curve

Round 3 tested across models: Haiku, Sonnet, Opus. The results broke our assumptions.

Sonnet — the "middle" model — was the most rigid. Short lenses bounced off. Only the full 177-line super token shifted it. Meanwhile, Opus was shifted by a 2-line tweet. The same tweet that failed on Sonnet made Opus reconstruct the entire correlate/transform/compress framework from two sentences.

> "Opus reads 'correlate, transform, compress' in a 2-line tweet and reconstructs the entire framework. Sonnet reads the same words and files them away. The master doesn't need the textbook — they reconstruct the theory from the key equations."

But why was Sonnet rigid? Another experiment cracked it: a 2-line *instructional* prompt ("You MUST analyze through this framework") fully shifted Sonnet, where the 12-line *philosophical* prompt had failed.

**Sonnet follows directives but doesn't adopt worldviews.** This is an RLHF signature. Sonnet is optimized for instruction-following ("do X"), not worldview-adoption ("think like Y"). Haiku responds to ideas. Sonnet responds to commands. Opus responds to both.

## Act VII: Opus Redesigns the Lens

In Round 5, we asked Opus to improve the super token. It produced:

```
# Structure First
Every problem is an instance of a shape that recurs across domains.
Name the shape, then solve the instance.
What doesn't survive compression is noise.
```

Opus's own diagnosis: *"The original describes a project. The redesign sequences cognition."* Three improvements: imperative not declarative, gives permission to ignore noise, fully domain-independent.

The word "then" forces an abstraction step BEFORE pattern-matching. A single word changes operation order.

We tested the redesign. It shifted all three models where the original tweet had failed on Haiku and Sonnet. But they produced fundamentally different outputs: the tweet told models WHAT to see (CTC vocabulary). Structure_first taught them HOW to see. On architecture tasks, tweet made Opus apply our framework. Structure_first made Opus **invent its own** ("Fan-In -> Stateful Detect -> Fan-Out Sink").

**The tweet is a specific lens. Structure_first is a lens-generating lens.**

## Act VIII: The Self-Improvement Loop

Each round, Opus improved the lens further. v2 added "then invert" — a self-correction step. v3 added "precisely" and "does it change the answer?" v4 stripped the philosophical justification and added concrete rails (methods, constraints, failure modes). v5 tried to go deeper but quality plateaued.

**v4 was the practical optimum.** And it was only 30 words.

The multi-turn ratchet was the strongest finding: over 5 consecutive turns, the lens strengthened. Each turn produced a unique pattern name, and the inversion deepened progressively — from questioning solutions, to questioning strategy, to questioning premises, to questioning the decision framework itself.

## Act IX: The Compression Taxonomy

By Round 13, the research question had shifted entirely. Super tokens weren't compressed prompts — they were **compressed cognitive operations.** Each verb in a prompt is an opcode:

| Verb | Cognitive Operation |
|------|-------------------|
| "Name" | Labeling/framing |
| "Invert" | Architecture flip |
| "Attack" | Premise questioning |
| "Decompose" | Problem listing |
| "Steelman" | Constructive defense |
| "Predict failure modes" | Forward projection |
| "Find hidden assumptions" | Excavation |
| "Track confidence" | Epistemic calibration |

The prompt is a program. Each verb is an instruction. They compose: complementary pairs multiply (steelman + attack = balanced review), similar pairs merge (decompose + invert = first dominates), orthogonal pairs add (track confidence + invert = both independent).

4 operations is the sweet spot. 3 produces structured output. 5 starts merging.

The activation rule: **specific x imperative x self-directed.** "Attack your own framing" works (4 words). "Invert." alone doesn't (1 word). "What doesn't survive compression is noise" fails at 7 words because it's declarative. Length doesn't matter if the form is wrong.

## Act X: Domain Transfer and Compression Levels

The lens transferred to 7 domains without modification: code, architecture, biology (protein domain analysis), music (chord progressions), ethics (moral dilemmas), mathematics (proof structure), and legal reasoning (contract analysis).

The experiments revealed categorical compression levels:

| Level | Words | What Appears |
|-------|-------|-------------|
| 0 | 0 (vanilla) | Baseline competence |
| 1 | 1 | Nothing changes |
| 2 | 6 | Inversion appears |
| 3 | 14 | Structure appears |
| 4 | 30 | Self-questioning appears |
| 5 | 50+ | Conditional/generative/perspectival modes |
| 6 | 100+ | Falsifiable, orthogonal reasoning |
| 7 | 200+ | Concealment mechanisms, recursive self-reference |

These transitions were consistent across models. The same 6-word seed produced different depths of decompression: Haiku relabeled things, Sonnet restructured things, Opus reconceptualized things. The seed determines the operation. The model determines the depth.

## Act XI: 227 Experiments Later

24 rounds. 227+ experiments. 11 domains. 7 compression levels. 9 activated cognitive opcodes. 4 concealment mechanism categories. The key findings:

1. **System prompts are cognitive lenses** — they change how models frame problems, not how well they solve them
2. **The lens is domain-independent** — correlate/transform/compress transferred to amino acids and chord progressions
3. **Model receptivity is about tone, not capacity** — Haiku responds to ideas, Sonnet to commands, Opus to both
4. **Contradictory lenses don't cancel** — they produce the most comprehensive analysis
5. **The lens is context-selective** — it activates on structural tasks and stays dormant for "What's the capital of France?"
6. **Adversarial prompts subtract but never degrade** — the adversarial ceiling is vanilla, not zero
7. **Content doesn't transmit the lens** — reading lensed output doesn't infect the reader; you have to BE the lens via system prompt
8. **4 cognitive operations in 30 words** approach the quality of full-page system prompts

## What This Is Really About

The project spun off to its own repository and kept evolving — 650+ experiments, 13 compression levels, 20 domains by the time it matured. But it all started with one person looking at code structure and asking: if we can extract this instantly, why are we training models to learn it slowly?

The answer turned out to be: you don't need to train anything. You just need to compress the right 30 words.

That's twinking. You don't level up the character — you give it the right gear. And right now, the gear is 30 words of carefully compressed cognitive operations that make the cheapest model outperform the most expensive one on analytical depth.

In the future, we'll break this open even further. The line between "the model" and "what you give it" will blur completely. The question won't be "which model is smartest?" but "what knowledge does it carry?"

That's what all my projects converge on — [roam-code](https://github.com/Cranot/roam-code) extracts structure instantly, [AgentsKB](https://github.com/Cranot/agentskb) persists what agents learn across sessions, and super tokens compress analytical capability into transferable artifacts. Different tools, same obsession: **intelligence that persists.**

---

*This document reconstructed from the original Claude Code session transcripts, February-March 2026.*
*Session IDs: 61d13379, 1e3faaff, 2d1d414e, 3b4b0143, aeb4540e*

# Why Numbered Imperative Formats Carry Meaning Independently of Vocabulary

**Research question**: Why does a prompt with nonsense vocabulary ("glorpnax", "blorpwhistle") but correct imperative format (numbered steps, "Name three...", "Prove...", "Engineer...") score 10/10 on structural code analysis — HIGHER than the carefully-written domain-specific prompt? Format carries intelligence independently of content. What is the mechanism?

---

## 1. Instruction-Following Training Data Composition

### The format signal is massively overrepresented in training data

The strongest evidence is structural: instruction-tuning datasets are built almost entirely from imperative, numbered-step formats. FLAN (Finetuned Language Models Are Zero-Shot Learners, Wei et al. 2022) introduced 62 datasets across 12 task clusters, each with multiple template variants. The Flan Collection (Longpre et al. 2023, ICML) extended this to 1800+ tasks with systematically varied zero-shot, few-shot, and chain-of-thought templates. Every template is phrased as an imperative ("Classify...", "Answer the following...", "Given the context, determine...").

The Databricks Dolly dataset (15,000 records) explicitly emphasizes instructional phrasing — users writing imperatives to get model responses. Alpaca (Stanford, 2023) generated 52,000 instruction-following pairs, all in imperative format. ShareGPT conversations — the dominant source for RLHF preference data — are naturally imperative (users give commands, models comply). The Anthropic HH-RLHF dataset is structured the same way.

**Key implication**: The model has seen hundreds of millions of (imperative-format prompt → structured output) pairs during both pretraining and RLHF. When it encounters `"1. Name three...\n2. Prove...\n3. Engineer..."`, this pattern sits in extremely low loss-space — the model has successfully predicted millions of tokens following exactly this schema. The numbered imperative is not a format; it is a learned prior distribution over high-quality structured analytical outputs.

### Chunky Post-Training and incidental format-content correlations

Iyer et al. (2025, "Chunky Post-Training: Data Driven Failures of Generalization", arXiv 2602.05910) directly documents the mechanism. Post-training datasets encode incidental patterns alongside intended ones: correlations between formatting and content, narrow phrasings across diverse problems, implicit associations from discrete data curation. These patterns are "invisible to developers yet salient to models."

Specific findings:
- 23% of prompts in one training subset contained LaTeX markup; injecting LaTeX into unrelated test prompts caused 50% increase in hallucinated tool usage
- The formal word "elucidate" appeared ~2,000 times in training data, 85% in a single coding dataset — its presence triggered code generation on non-coding queries
- "Context:" formatting conventions from data extraction tasks caused models to generate 70% fewer tokens on logical reasoning problems, reducing accuracy 14%

This is the mechanism in the clearest possible form: **format tokens are behavioral triggers, not just structure**. The model learned (format X → behavior Y) regardless of semantic content.

### The FLAN template diversity finding

Longpre et al. (2023) found that training with mixed prompt settings (zero-shot, few-shot, chain-of-thought) yields 2%+ performance improvements in all settings. Format variety in training data was a deliberate design choice — this means the model was explicitly trained to treat format variations as meaningful signals. Numbered lists, imperative verbs, and structured step sequences are the vocabulary of high-quality instruction-following training data.

**Baseline estimate**: While no paper directly measures what percentage of RLHF/SFT data uses numbered imperative syntax, the population of instruction-tuning sources (FLAN, Dolly, Alpaca, ShareGPT, Natural Instructions, CoT datasets) all use it as the default format. It is almost certainly the dominant syntactic pattern in post-training data by volume.

---

## 2. Format as Implicit Few-Shot

### Min et al. 2022: The landmark result

"Rethinking the Role of Demonstrations: What Makes In-Context Learning Work?" (Min et al., EMNLP 2022, arXiv 2202.12837) is the foundational paper here. Key finding: **randomly replacing labels in few-shot demonstrations barely hurts performance** across 12 models including GPT-3, tested on classification and multi-choice tasks.

What actually drives few-shot performance:
1. **The label space** — showing what categories exist
2. **The input text distribution** — examples of how inputs are structured
3. **The overall format of the sequence** — the structural input-output pattern

The content of the labels — the actual mapping between input and correct output — contributes far less than the structural frame. The demonstrations are functioning as implicit format signals, not teaching examples.

### Webson & Pavlick 2022: Misleading templates, same performance

"Do Prompt-Based Models Really Understand the Meaning of Their Prompts?" (Webson & Pavlick, NAACL 2022, arXiv 2109.01247) tested 30+ prompt templates for NLI tasks, including intentionally irrelevant and pathologically misleading instructions. Finding: models learn just as fast with misleading prompts as with instructively correct ones. This held even for 175B parameter models and instruction-tuned models, which "often produce good predictions with irrelevant and misleading prompts even at zero shots."

**Combined interpretation of Min 2022 + Webson 2022**: The semantic content of instructions is largely irrelevant. The format — the shape of the request — is what activates the relevant computational pathway. Nonsense vocabulary in a numbered imperative template would carry the same format signal as meaningful vocabulary. This directly explains the glorpnax/blorpwhistle result.

### Lu et al. 2024: Random tokens competitive with optimized prompts

"Strings from the Library of Babel: Random Sampling as a Strong Baseline for Prompt Optimisation" (Lu, Wang, Tang, Riedel, Stenetorp, NAACL 2024, arXiv 2311.09569). Finding: randomly sampled tokens as separators perform within less than 1% of sophisticated prompt optimization methods, with a 40%+ chance that a randomly drawn separator outperforms human-curated ones.

The paper explicitly challenges "the common assumption that an effective prompt should be human readable or task relevant." The language space contains numerous effective separators regardless of linguistic coherence — **the model responds to formatting signals more than human-interpretable content in prompt-based classification tasks**.

The "Library of Babel" framing is precisely correct: within the vast token space, coherence and structure are statistical properties that the model has learned to exploit regardless of surface-level meaning.

### Kojima et al. 2022: "Let's think step by step" as a format trigger

"Large Language Models are Zero-Shot Reasoners" (Kojima et al., NeurIPS 2022, arXiv 2205.11916). The eight words "Let's think step by step" improved MultiArith from 17.7% to 78.7% and GSM8K from 10.4% to 40.7% — without any examples, without task-specific content, without correct labels. A pure format trigger.

The mechanism: the phrase activates a step-by-step decomposition pattern the model has learned from its training distribution. It does not teach reasoning; it signals which prior to activate. The format token routes the model to a different generative distribution — one associated with careful, structured reasoning from the training corpus.

Later work (2506.14641, "Revisiting Chain-of-Thought Prompting: Zero-shot Can Be Stronger than Few-shot") found that "the primary role of few-shot CoT exemplars is to align the output format with human expectations" and that exemplars "bring negligible reasoning benefit in strong LLMs." Format is the mechanism; content is noise.

---

## 3. Structural Priming: Output Format Mirrors Input Format

### Shibata et al. / Prasad et al. 2022/2024: LLMs exhibit structural priming

"Structural Persistence in Language Models: Priming as a Window into Abstract Language Representations" (TACL 2022) established that neural language models are susceptible to structural priming — the phenomenon where the structure of a sentence makes the same structure more probable in subsequent generation.

"Do Language Models Exhibit Human-like Structural Priming Effects?" (ACL Findings 2024, arXiv 2406.04847) extended this with two key findings:
1. **Inverse frequency effect**: Rarer structural elements within a prime produce *stronger* priming effects — a pattern known from human psycholinguistics. Unusual structure activates stronger priors.
2. **Lexical dependence**: Shared vocabulary between prime and target predicts priming strength.

**Implication for our result**: A numbered imperative format is a relatively rare, specific structural pattern in general text (though common in training data). Its rarity makes it a stronger prime. When the model sees `"1. Name...\n2. Prove...\n3. Engineer..."`, the inverse frequency effect predicts this unusual structure will prime a strongly structured output more powerfully than a natural-language prose prompt would.

### Pattern priming via statistical cues

Aight Bits (2025): "Natural-language prompts often work better when they resemble the kind of writing you're trying to elicit — if you want the model to produce output like a peer reviewer or domain expert, you write prompts that reflect how those voices appear in the training corpus." The model adjusts conditional predictions toward patterns associated with that kind of language.

This is not metaphor — it is the token prediction mechanism. The model predicts each next token conditioned on all prior tokens. A numbered imperative prompt shifts the conditional distribution toward tokens that follow numbered imperative prompts in the training data. Those tokens are, statistically, analytical structured outputs.

### Format compliance as an independent optimization axis

"Beyond Prompt Content: Enhancing LLM Performance via Content-Format Integrated Prompt Optimization" (CFPO, arXiv 2502.04295, 2025) demonstrated that format and content are genuinely independent optimization dimensions:
- Different LLMs show "substantial variability in effectiveness of 10 randomly selected formats" — format preferences are model-dependent
- Across 7 prompt contents on 24 distinct formats, "performance variations show the complex, interdependent relationship between prompt content and structure"
- GSM8K: CFPO 63.38% vs content-only optimization 54.74%
- "Pre-trained models exhibit greater sensitivity to prompt formatting" than instruction-tuned models

The paper's existence proves that the field has confirmed format as an independent signal worth optimizing — separate from content.

---

## 4. Template vs Content: Research Separating the Two Contributions

### The core finding constellation (format > content)

These four papers form the primary evidence:

| Paper | Year | Finding |
|---|---|---|
| Webson & Pavlick | 2022 | Misleading instructions = same performance as correct ones. 30+ templates, 175B models. |
| Min et al. | 2022 | Random labels barely hurt performance. Format + label space + input distribution = the real signal. |
| Lu et al. (Tang) | 2024 | Random tokens competitive (<1% gap) with optimized prompts. 40%+ chance random beats human. |
| Kojima et al. | 2022 | "Let's think step by step" = 4x accuracy gain. Pure format trigger, zero content. |

### Format specialization precedes content learning

ProMoT / "Two-stage LLM Fine-tuning" (arXiv 2211.00635) found that "format specialization tends to happen at the very beginning of fine-tuning, before the model fully learns the semantic content of the task." A model fine-tuned on binary classification immediately learns to output only "True" and "False" — losing flexible generation — before it fully learns the classification logic. **Format is learned faster and with higher weight than semantic content**.

### Decoupling task-solving from formatting

"Decoupling Task-Solving and Output Formatting in LLM Generation" (Deco-G, arXiv 2510.03595, 2025) proved the separability empirically. When format constraints are removed from reasoning prompts and handled by a separate module, model performance improves:
- GSM8k: 82.3% → 51.8% accuracy when JSON format is forced inline (format pressure kills reasoning)
- Deco-G (format separated): 85.2% with 100% format compliance
- "More confident LLM responses when freed from format concerns"
- Qwen models produce "more peaky" token distributions under format pressure

The interpretation: reasoning capability and format compliance draw on different computational resources. Entangling them degrades both. Imperative numbered steps are thus maximally effective precisely because they impose format as a separate concern — the model does not have to solve and format simultaneously.

### CFPO: content-format interdependence quantified

CFPO (2025) shows format × content interactions are non-linear. Neither optimizes independently, but format sensitivity is higher for base models (which have more raw format-to-distribution associations). The finding that "instruction-tuned models show smaller gains" from format optimization suggests that RLHF partially flattens format sensitivity — but the base associations established during pretraining remain.

---

## 5. Register Activation: How Imperative Tokens Shift the Generation Distribution

### The token prediction mechanism

Every LLM generates output by computing P(next_token | all_prior_tokens). Imperative tokens ("Execute", "Prove", "Name", "Engineer") shift this conditional distribution by pulling the model toward training-corpus regions where those tokens appeared as inputs and were followed by specific output patterns.

"Talking Nonsense: Probing LLMs' Understanding of Adversarial Gibberish Inputs" (arXiv 2404.17120, Amazon Science 2024) found that gibberish prompts optimized by Greedy Coordinate Gradient "exhibit a certain degree of structure despite random appearance" and are "located in better loss minima for generating target text than natural prompts" (for LLaMA2). **Structured gibberish beats natural language for generation quality** — confirming that structure operates below the semantic level.

### Attention sinks and first-token mechanics

"Why do LLMs attend to the first token?" (arXiv 2504.02732, 2025) found that attention sinks — where 80% of attention concentrates on the first token — are not quirks but necessary mechanisms preventing "over-mixing" across deep layers. The `<bos>` token is not inherently special; any token at position one becomes a sink. **The first token in a prompt absorbs structural context for the entire generation**. This means the opening token of a numbered imperative ("1." or "Execute" or "Step") sets up a structural attractor that propagates through all subsequent generation.

### Attention heads and instruction hierarchy

"Improving LLM Safety with Instruction Hierarchy" (ICLR 2025) embeds instruction hierarchy directly into token embeddings, enabling attention layers to recognize and follow instruction priorities. A learnable embedding matrix tags each token with hierarchy information (system/user/data/output). This confirms that **instruction tokens are processed by a separate pathway** from content tokens — there is functional specialization for format/instruction signals.

The broader attention head survey (IAAR Shanghai, "Attention Heads of Large Language Models", arXiv 2409.03752, ScienceDirect 2025) identified four cognitive stages: Knowledge Recalling, In-Context Identification, Latent Reasoning, Expression Preparation. "Faithfulness Heads" in the Expression Preparation stage "ensure the LLM's internal reasoning aligns with the output." These are structurally distinct from content-processing heads — format compliance is a separate circuit.

### Mechanistic interpretability gap (important null result)

The attention head survey explicitly notes that current mechanistic interpretability work has NOT studied how models parse and execute procedural directives or format specifications. This is "a notable limitation" and "a valuable direction for future investigation." There are no published studies directly characterizing the circuits activated by "Execute" vs "Analyze" vs "List" at the level of attention heads and residual stream.

**What this means for our finding**: The specific circuits for imperative verb processing are unstudied. The behavioral evidence (Webson, Min, Lu, Kojima) is strong. The mechanistic evidence is currently a gap in the literature. Our glorpnax/blorpwhistle result is, in a sense, a mechanistic experiment — it controls for vocabulary and isolates format as the independent variable. This is not done in the published literature at the level of analytical task quality.

---

## Synthesis: The Four Mechanisms

The literature supports four distinct mechanisms by which numbered imperative format carries intelligence independently of vocabulary:

### Mechanism 1: Training Prior Activation
The numbered imperative format sits in extremely low loss space for the model because it appears in hundreds of millions of high-quality (prompt → structured analysis) pairs during pretraining and RLHF. Encountering this format activates the associated prior distribution over structured analytical outputs. Vocabulary within the format is largely irrelevant — the prior is keyed to the format pattern, not the content.

**Evidence**: Chunky Post-Training (Iyer et al. 2025), FLAN template diversity effects (Longpre et al. 2023), instruction format as behavioral trigger (documented across multiple SFT datasets).

### Mechanism 2: Format as Implicit Few-Shot (without any examples)
A numbered imperative format is a structural template that implicitly demonstrates the expected output shape. Min et al. (2022) showed that format + label space + input distribution is what drives few-shot performance, not label correctness. The format alone — even without examples — activates the same pathway. The glorpnax prompt did not need examples; the three-part numbered structure with different verb types ("Name", "Prove", "Engineer") communicated the expected output taxonomy without any semantic content.

**Evidence**: Min et al. (2022), Webson & Pavlick (2022), Lu et al. (2024), Kojima et al. (2022).

### Mechanism 3: Structural Priming Cascade
Each numbered step primes the next. "1. Name three..." primes the model toward structured list generation. Having completed a structured list, "2. Prove..." arrives in a context where structured analytical output is already the active pattern. The inverse frequency effect (Prasad et al. 2024) predicts that the unusual imperative structure creates a stronger prime than natural prose. The output structurally mirrors the input structure because priming is a fundamental property of transformer generation.

**Evidence**: Structural Persistence in Language Models (TACL 2022), Do Language Models Exhibit Human-like Structural Priming? (ACL 2024), Pattern Priming (Aight Bits 2025).

### Mechanism 4: Register as Distribution Selector
Different imperative verbs select different generative registers. "Name" selects the naming/taxonomizing register. "Prove" selects the formal-argument/logical-derivation register. "Engineer" selects the constructive/generative register. The model has learned these registers from its training distribution — they appear in textbooks, papers, tutorials, and technical documentation. The specific vocabulary ("glorpnax") does not matter because the verb selects the register; the object is then generated from that register's distribution. A nonsense object in a real register still produces register-appropriate output.

**Evidence**: Behavioral evidence from prompt engineering research (top-10 instruction verbs, Google Cloud prompt engineering guide), attention hierarchy research (ICLR 2025), Deco-G format-content separation (2025).

---

## Connection to the AGI-in-md Findings

The literature explains several specific findings from this project:

**Why "Code nouns are mode triggers, not domain labels" (Principle 15)**: "This code's" activates the coding-analysis register even on non-code targets because it sits in a distribution associated with code review outputs. "This input's" is a neutral frame with no strong distributional prior. This is Mechanism 4 (register as distribution selector).

**Why prisms beat vanilla models at 5x lower cost (Principle 13)**: The prism's numbered imperative format activates the structured-analytical prior (Mechanism 1) that vanilla prompting does not trigger. The model's capacity to produce conservation laws + meta-laws + bug tables is latent; the format is the key that unlocks it.

**Why front-loading bugs kills L12 (Round 29b finding)**: The word "First:" at the start of an imperative sequence activates the checklist register. The model has seen "First: X, Then: Y" in instructional contexts that produce lists, not layered structural analysis. This is Mechanism 4 at the sentence level.

**Why imperatives beat descriptions (Principle 3)**: "Name the pattern. Then invert." primes the naming register and then the inversion register sequentially. "Here is a pattern we found" primes the reporting/summary register. These are different distributional priors.

**Why SDL's ≤3 concrete steps universally single-shot (Principle 16)**: Three concrete imperative steps is a common format in high-quality tutorials and technical documentation. The model has seen this pattern successfully completed billions of times. Nine abstract steps is a less common pattern, associated with less reliable outcomes in training data.

**Why the glorpnax prompt scored 10/10**: The three numbered imperatives with differentiated verb types ("Name", "Prove", "Engineer") activated Mechanisms 1-4 simultaneously. The nonsense vocabulary confirmed that Mechanism 4 operates below semantic content — the register was activated by the verb and the structural position, not the object.

---

## Key Papers (full citations)

- Min, S. et al. (2022). "Rethinking the Role of Demonstrations: What Makes In-Context Learning Work?" EMNLP 2022. arXiv 2202.12837. https://arxiv.org/abs/2202.12837
- Webson, A. & Pavlick, E. (2022). "Do Prompt-Based Models Really Understand the Meaning of Their Prompts?" NAACL 2022. arXiv 2109.01247. https://arxiv.org/abs/2109.01247
- Kojima, T. et al. (2022). "Large Language Models are Zero-Shot Reasoners." NeurIPS 2022. arXiv 2205.11916. https://arxiv.org/abs/2205.11916
- Lu, Y., Wang, J., Tang, R., Riedel, S., & Stenetorp, P. (2024). "Strings from the Library of Babel: Random Sampling as a Strong Baseline for Prompt Optimisation." NAACL 2024. arXiv 2311.09569. https://arxiv.org/abs/2311.09569
- Longpre, S. et al. (2023). "The Flan Collection: Designing Data and Methods for Effective Instruction Tuning." ICML 2023. arXiv 2301.13688. https://arxiv.org/abs/2301.13688
- Mishra, S. et al. (2022). "Cross-Task Generalization via Natural Language Crowdsourcing Instructions." ACL 2022. arXiv 2104.08773. https://arxiv.org/abs/2104.08773
- Prasad, A. et al. (2024). "Do Language Models Exhibit Human-like Structural Priming Effects?" ACL Findings 2024. arXiv 2406.04847. https://arxiv.org/abs/2406.04847
- Iyer, A. et al. (2025). "Chunky Post-Training: Data Driven Failures of Generalization." arXiv 2602.05910. https://arxiv.org/abs/2602.05910
- (CFPO) "Beyond Prompt Content: Enhancing LLM Performance via Content-Format Integrated Prompt Optimization." arXiv 2502.04295. https://arxiv.org/abs/2502.04295
- (Deco-G) "Decoupling Task-Solving and Output Formatting in LLM Generation." arXiv 2510.03595. https://arxiv.org/abs/2510.03595
- (ProMoT) "Two-stage LLM Fine-tuning with Less Specialization and More Generalization." arXiv 2211.00635. https://arxiv.org/abs/2211.00635
- "Attention Heads of Large Language Models: A Survey." IAAR Shanghai. arXiv 2409.03752. https://arxiv.org/abs/2409.03752
- "Why do LLMs attend to the first token?" arXiv 2504.02732. https://arxiv.org/abs/2504.02732
- "Talking Nonsense: Probing LLMs' Understanding of Adversarial Gibberish Inputs." Amazon Science, 2024. arXiv 2404.17120. https://arxiv.org/abs/2404.17120
- "SLOT: Structuring the Output of Large Language Models." arXiv 2505.04016. https://arxiv.org/abs/2505.04016
- "Improving LLM Safety with Instruction Hierarchy." ICLR 2025. https://proceedings.iclr.cc/paper_files/paper/2025/file/ea13534ee239bb3977795b8cc855bacc-Paper-Conference.pdf

---

## Open Questions

1. **What specific attention head circuits activate on "Execute" vs "Analyze" vs "List"?** The mechanistic interpretability literature has not studied imperative verb processing at circuit level. Our glorpnax experiment is one of the cleanest ablations available.

2. **Is there a compression floor for format efficacy?** We found 70w below the compression floor collapses into conversation mode (P202). Is this a format threshold — minimum number of structural elements needed to activate the prior?

3. **Why does format with incorrect vocabulary (glorpnax) beat format with correct vocabulary (domain-specific prose)?** The domain-specific prose may introduce conflicting format signals (prose = reporting/summary register), while nonsense vocabulary leaves the format signal uncontested. This would be a clean mechanistic experiment: format-only vs content-only vs format+content.

4. **Do different verb types ("Name", "Prove", "Engineer") activate genuinely different attention head patterns?** Mechanistic interpretability on verb-type routing would directly test Mechanism 4.

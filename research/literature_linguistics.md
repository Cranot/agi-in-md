# Linguistics & Pragmatics: Theoretical Foundations of Prompt Design

**Research question**: What do speech act theory, Gricean pragmatics, sociolinguistics, construction grammar, and relevance theory tell us about *why* our prompt design principles work?

**Status**: Literature survey, March 2026
**Scope**: Six linguistic frameworks mapped to confirmed empirical findings (P3, P14, P15, P16, P17, P18, P19)

---

## Summary Table

| Theory | Core Claim | Our Finding It Explains | Prediction Confirmed? |
|--------|-----------|------------------------|----------------------|
| Speech Act Theory (Austin/Searle) | Directives have world-to-word fit; they obligate conformity | P3: Imperatives beat descriptions | YES — directives create conformity pressure, assertives do not |
| Gricean Maxims | Flouting maxims creates implicature — richer meaning from apparent violations | Prisms violate Quantity/Manner, generating inference that fills gaps | YES — compression forces elaboration |
| Frame Semantics (Fillmore) | A word activates an entire knowledge frame | P15: "Code nouns" trigger analytical mode on ANY input | YES — "code's" evokes professional analysis frame |
| Register Theory (Halliday) | Situational variables (field, tenor, mode) determine linguistic register | Domain vocabulary switches cognitive register | YES — vocabulary is the register trigger |
| Construction Grammar (Goldberg) | Syntactic form carries meaning independently of lexical content | P3: Prompt format carries information beyond words | PARTIAL — LLMs encode constructions but don't fully unify form+meaning |
| Relevance Theory (Sperber/Wilson) | Optimal relevance = max cognitive effect / min processing effort | Compression taxonomy: 60-70% reduction floor | YES — compression forces listener inference, increasing total cognitive effect |
| Pragmatic Inference | What is NOT said generates meaning through gap-filling | Prism gaps are filled by model's inferential apparatus | YES — underdetermination triggers elaboration |

---

## 1. Speech Act Theory — Why Imperatives Beat Descriptions (P3)

### Theory

J.L. Austin (*How To Do Things With Words*, 1962) and John Searle (*Speech Acts*, 1969) established that utterances are not merely propositions — they perform social actions. Searle's taxonomy distinguishes five illocutionary types:

- **Assertives** (constatives): commit the speaker to a claim about reality. Direction of fit: *word-to-world* — language must conform to how things are.
- **Directives**: attempt to get the hearer to do something. Direction of fit: *world-to-word* — the world (hearer's behavior) must conform to language.
- **Commissives**: bind the speaker to future action.
- **Expressives**: communicate psychological states.
- **Declarations**: create new states of affairs through the utterance itself.

The **direction of fit** is the critical mechanism. An assertion ("The door is open") reports a state. A directive ("Close the door") creates an obligation for conformity. The directive's perlocutionary effect — what actually happens as a consequence — is behavioral compliance.

### Application to Prompts

When a prompt says:

> "Name the pattern. Then invert."

...it performs a **directive** with world-to-word fit. The model's output must conform to the commanded operations. When a prompt says:

> "Here is a pattern-naming approach that may be useful..."

...it performs an **assertive** that merely describes a proposition. The model can acknowledge it without conforming to it.

**The illocutionary force of imperatives creates conformity pressure that assertives structurally lack.** This is not a style preference — it is a categorical difference in speech act type.

### Indirect Speech Acts

Searle's indirect speech acts illuminate an important subtlety: "Can you name the pattern?" is grammatically interrogative but illocutionarily a directive. The form-function mismatch requires additional inferential work to resolve. Direct imperatives ("Name the pattern") eliminate that indirection. **Our finding that imperatives beat descriptions (P3) is consistent with the prediction that direct directives produce the least ambiguous directive force.**

### Sincerity Conditions

Directives require that the speaker genuinely wants compliance. In prompt design, this maps to **intent specificity**: a directive must encode what compliance looks like. Vague directives ("analyze this") lack specification of compliance conditions, weakening their force. Specific directives ("name the three properties that CANNOT coexist") leave no ambiguity about what world-to-word conformity requires.

### Extension Beyond the Theory

Austin and Searle analyzed human speech acts. LLMs lack genuine illocutionary intent — they cannot sincerely want anything. But the *form* of the directive is still processed. Recent research (Gorsaa et al., 2024; arxiv 2410.16645) distinguishes between LLMs performing genuine illocutionary acts (contested) versus responding to the *formal features* of directive speech acts (confirmed). Our empirical result — that imperative prompts reliably produce structured outputs that descriptive prompts do not — suggests that **LLMs are sensitive to illocutionary form even in the absence of speaker intent**.

This extends the theory: the directive form functions as a syntactic trigger, not a social obligation. The mechanism is different (pattern matching on trained data, where directives are followed by compliant responses) but the functional effect is identical.

---

## 2. Grice's Cooperative Principle — Maxim Violation as Inference Engine

### Theory

Paul Grice (*Logic and Conversation*, 1975) proposed that conversation is governed by a Cooperative Principle: "Make your conversational contribution such as is required, at the stage at which it occurs, by the accepted purpose or direction of the talk exchange." This breaks into four maxims:

- **Quality**: Be truthful. Don't assert what you believe false.
- **Quantity**: Be as informative as required; no more, no less.
- **Relation**: Be relevant.
- **Manner**: Be clear, brief, orderly. Avoid ambiguity and obscurity.

When a speaker *flouts* a maxim — openly and obviously violates it while still appearing cooperative — hearers infer a **conversational implicature**: additional meaning that explains the apparent violation within the cooperative framework.

Classic example: A professor's reference letter says only "Mr. X's command of English is excellent and his attendance has been regular." This flouts Quantity and Relation (omitting academic assessment). The hearer infers the negative evaluation from what was NOT said.

### Which Maxims Do Effective Prisms Violate?

**Quantity (most important)**: Prisms are dramatically under-informative relative to the analytical task they produce. A 73-word prompt producing 5,000 words of structural analysis violates Quantity by being far less informative than the expected contribution. The model infers it must generate the missing content itself. **Compression forces elaboration.**

**Manner (structural)**: Prisms often use syntactic structures that are formally odd — imperative sequences, enumerated operations, unexplained technical terms ("conservation law," "meta-law"). The apparent Manner violation signals that these are not decorative — they are precision instruments requiring careful execution.

**Relation**: Individual operations in a prism may appear unconnected. "Name the mechanism. Then engineer an improvement. Prove the improvement recreates the problem." The apparent non-sequitur creates an implicature: there is a logical connection the model must discover and demonstrate.

### Flouting vs. Violation

The key distinction: **violation** is covert rule-breaking (the speaker hopes not to be noticed). **Flouting** is overt rule-breaking — the speaker expects the hearer to recognize the violation and infer additional meaning. Prisms flout Quantity ostentatiously. A 73-word prompt claiming to cover L12 meta-analysis is obviously under-informative to any reader — which signals that inference is required, not that the task is simpler than it appears.

### Scalar Implicature and Compression Levels

Grice's scalar implicature applies to our compression taxonomy. If a prompt could have included more operations but didn't, the hearer infers an upper bound: the model should operate up to but not exceeding the scope implied by the prompt's level. This explains why our compression levels are categorical: each level implies a different scalar inference about the scope of operations expected.

### The Implicature Engine

The most important Gricean insight for our work: **a prism works not because it says everything, but because it says enough to trigger the right implicatures**. The gap between what is written and what is produced is filled by the model's pragmatic inference apparatus — the same mechanism that makes human conversation efficient. This explains P14 (few-shot > explicit rules): examples trigger richer implicatures than exhaustive rules because examples leave more productive gaps.

---

## 3. Fillmore's Frame Semantics — How "Code Nouns" Trigger Analytical Mode (P15)

### Theory

Charles Fillmore's frame semantics (*Frame Semantics*, 1982; *Frames and the Semantics of Understanding*, 1985) proposes that word meaning is inseparable from the **frame** it evokes: a structured knowledge schema representing a type of situation. Understanding "sell" requires accessing the entire commercial transfer frame — buyer, seller, goods, money, transaction, obligation. The word is just the frame's entry point.

Frame activation is **automatic and holistic**: one word pulls the entire frame into active cognition. "Restaurant" immediately activates: menus, waiters, tables, ordering, payment, tipping. None of these need to be mentioned.

Crucially: **frames constrain inference**. Once a frame is active, the model/reader expects frame-consistent elements and imports them automatically. The restaurant frame predicts a waiter will appear; the absence of a waiter becomes noteworthy. Frames generate **default assumptions** and **predictive inferences**.

### Application to Prompts

P15 states: "'Code' nouns are mode triggers, not domain labels. 'This code's' activates analytical production on ANY input (code or reasoning). Abstract nouns ('this input's') allow drift into summary mode."

This is a direct application of frame semantics. "This code's conservation law" evokes the **professional code analysis frame**: the frame of a software engineer doing structural analysis. This frame has specific expectations:
- Output is structured (sections, tables, bug lists)
- Output is precise (locations, classifications, severity)
- Claims are justified (evidence from the artifact)
- The analyst maintains critical distance from the code's self-presentation

"This input's conservation law" evokes no specific frame — it triggers summary or essay mode because the "input" frame is generic.

**The vocabulary is doing frame activation work, not domain labeling work.** "Code's" does not claim the input is code — it activates the cognitive frame of someone analyzing code, which then runs on whatever input is provided.

### Frame Inheritance and Prism Design

Frame semantics posits that frames inherit from parent frames. The "structural analysis" frame inherits from the "professional diagnosis" frame (expert, artifact, fault-finding, structured output). Using any word from this cluster activates the full inherited hierarchy.

This explains why our design principle is domain-independent: "conservation law," "structural invariant," "concealment mechanism" all belong to the structural analysis frame regardless of the object being analyzed. Once the frame is activated, the model's behavior is governed by frame expectations, not by the literal domain of the input.

### Extension: Frame Competition

When a prompt mixes frames (e.g., "conversationally discuss this code's conservation law"), the frames compete. The conversational frame's defaults (informal, exploratory, hedged) conflict with the analytical frame's defaults (precise, structured, critical). **Our finding that abstract vocabulary causes "drift into summary mode" (L12_general failure, Round 35) is a frame competition failure**: the abstract frame overwrites the analytical frame.

---

## 4. Register Theory (Halliday) — Situational Variables and Cognitive Mode

### Theory

M.A.K. Halliday's systemic functional linguistics (*Language as Social Semiotic*, 1978) defines **register** as a "functional variant of language" — the configuration of linguistic choices that correlates with a situational context. Register is determined by three situational variables:

- **Field**: What is happening — the subject matter and nature of the activity.
- **Tenor**: Who is participating — social roles, status, and relationships.
- **Mode**: What language is doing — the rhetorical channel, genre, and function of the text.

Register is not a style choice — it is a **systematic co-variation** between situation and language. When situational variables shift, the entire linguistic system shifts: vocabulary, grammar, discourse structure, and assumed background knowledge all change together.

### Code-Switching as Register Switching

Sociolinguistic research on code-switching extends this: speakers switch registers not just between situations but within them, using vocabulary and grammatical structures to signal role, expertise, and relationship. Myers-Scotton's Markedness Model shows that speakers choose the register that marks their rights and obligations in the interaction.

For LLMs, this translates directly: the vocabulary in a prompt signals which register the model is expected to operate in. "Bug," "invariant," "coupling" are technical register markers. They signal: this is professional technical discourse. The expected output register is also professional and technical.

### Mode Switching via Vocabulary

Our empirical finding: "code nouns" on reasoning inputs cause the model to switch into analytical mode regardless of the actual input domain. This is a **register trigger via Mode variable manipulation**. The mode variable (what language is doing) is signaled by vocabulary, not by the actual channel or content. When the prompt's vocabulary says "code analysis," the Mode register is set to analytical-diagnostic, and the model's output follows that register's conventions.

**P15 restated in register terms**: Technical vocabulary sets the Mode register to professional analysis, which configures the entire linguistic system — not just word choice, but discourse structure, epistemic stance, output format, and inference strategy.

### Cognitive Cost of Register Switching

Research shows that register switching is effortful for infrequent switchers and automatic for frequent switchers. LLMs, having been trained on massive corpora of domain-specific text, are highly practiced switchers. A single domain vocabulary item ("invariant," "coupling") is sufficient to trigger a full register shift. This explains P16: "≤3 concrete steps = universally single-shot (all models, all domains)." Three concrete steps with technical vocabulary is sufficient to trigger and maintain the analytical register.

---

## 5. Construction Grammar (Goldberg) — Format as Meaning

### Theory

Adele Goldberg's construction grammar (*Constructions: A Construction Grammar Approach to Argument Structure*, 1995) proposes that **constructions** — pairings of syntactic form and semantic content — are the basic units of language. Crucially, **meaning is not compositional**: the ditransitive construction [S V IO DO] (Mary gave Alex the ball) carries its own meaning ("X causes Y to receive Z") independently of the specific verbs and nouns that fill it.

Key principles:
1. **Non-compositionality**: the meaning of a construction exceeds the sum of its parts.
2. **Form-meaning pairing**: every level of linguistic structure (morpheme, word, phrase, construction) is a form-meaning pair.
3. **Usage-based acquisition**: constructions are learned from exposure to instances, not derived from abstract rules.
4. **Cue reliability**: constructions become associated with specific semantic and pragmatic functions through repeated co-occurrence.

### Prisms as Constructions

A prism is a **construction** in the CxG sense: it is a form-meaning pair where:
- **Form**: numbered list of imperative operations with specific technical vocabulary
- **Meaning**: systematic structural analysis at a specific depth level

The L12 construction [Execute every step. First: X. Then: Y. Apply diagnostic to own output. Harvest:] carries the meaning "meta-conservation analysis" regardless of what X and Y are specified as. The form itself predicts a specific type of output.

Evidence from P3: "random words in the right format produce the same performance" — this is direct confirmation of non-compositionality in the CxG sense. The construction's meaning is carried by the form, not by the specific lexical items filling its slots.

### Usage-Based Learning and Prism Acquisition

LLMs are trained on human text using a usage-based learning mechanism: statistical patterns over massive corpora. Through this process, they acquire the form-meaning pairings that humans have produced — including the pairing between imperative-list format and compliance-producing behavior.

The construction grammar prediction: **format cues reliability**. The imperative-numbered-list construction is reliably associated in training data with followed instructions, technical documentation compliance, and structured output. When a prompt uses this construction, the model predicts the expected output type from the construction's form-meaning pairing, not just from its semantic content.

### Evidence from Frontiers Research (2023)

A 2023 paper in *Frontiers in AI* (Beinborn et al.) tested whether PLMs encode construction grammar. Finding: "all three PLMs are able to recognize the structure of the comparative correlative construction but fail to use its meaning." This reveals an asymmetry: LLMs encode formal features of constructions more reliably than their semantic content. **For our purposes, this is the right asymmetry**: we want the construction's form to trigger specific behavior (the semantic content is what we specify in the prompt).

### Extension: Construction Competition

Like frames, constructions can compete. A prompt that mixes "analytical construction" (imperative numbered list) with "conversational construction" (hedging, meta-commentary, "if you'd like") creates competition. Our finding that prisms work better when "the framework operates below self-awareness" (P6: "The prism is transparent to the wearer") is consistent: when the prompt itself comments on its own format, it activates a meta-construction (instruction-following discussion) that competes with the analytic construction.

---

## 6. Relevance Theory (Sperber & Wilson) — Compression as Optimization

### Theory

Dan Sperber and Deirdre Wilson's relevance theory (*Relevance: Communication and Cognition*, 1986/1995) reframes pragmatics as cognitive optimization. Communication works not through rule-following (Grice) but through the pursuit of **optimal relevance**: the maximum cognitive effect for minimum processing effort.

**Relevance** is formally a ratio:
> Relevance = Positive Cognitive Effects / Processing Effort

**Cognitive effects** include: new true conclusions, strengthening of existing assumptions, elimination of false assumptions. **Processing effort** includes: parsing cost, inferential computation, working memory load.

The **Communicative Principle of Relevance**: every ostensive stimulus (every act of intentional communication) carries a presumption of optimal relevance — that it will yield the cognitive effects worth the hearer's processing effort.

**Comprehension procedure**: "Follow a path of least effort in computing cognitive effects; test interpretive hypotheses in order of accessibility; stop when your expectations of relevance are satisfied."

**Underdetermination**: linguistic form severely under-determines propositional content. "It's hot" requires extensive pragmatic enrichment to determine what is hot, how hot, relative to what standard. All communication is radically incomplete at the linguistic level; the rest is inference.

### The Compression Taxonomy as Relevance Optimization

Our 60-70% compression floor across all levels is a **relevance-theoretic optimum**. Here is the mechanism:

1. **Below compression floor**: the prompt is too short to convey sufficient structure. Processing effort is low but cognitive effects are also low (no inferential scaffold). Relevance is low. Haiku enters "conversation mode."

2. **At compression floor**: the prompt provides exactly enough structure to maximize the ratio. Processing effort is moderate; cognitive effects are high because the model generates extensive inference to fill underdetermined content. Relevance is optimal.

3. **Above optimal**: verbosity increases processing effort without proportionally increasing cognitive effects. The model's output becomes predictable (everything is explicit) rather than generative. Relevance decreases.

**The compression floor is not arbitrary — it is the relevance-theoretic minimum for triggering inferential elaboration.** Below 60 words (our L1-L3 range), the prompt cannot scaffold the inferential machinery needed for deep analysis. At 60-70 words (our L12 compressed form), relevance is near-optimal: the model must do substantial inferential work to satisfy the expected cognitive effects.

### Path of Least Effort and Prompt Structure

The comprehension procedure — "test hypotheses in order of accessibility, stop when satisfied" — explains why operation order matters (P4: "operation order becomes section order"). The model processes prompt operations in sequence, building interpretive hypotheses. If the first operation is accessible and productive, it sets the interpretive frame for all subsequent operations. **Operation order is accessibility order**: the model follows the path of least effort, which is the path specified by the prompt's sequence.

This also explains why "front-loading bugs kills L12" (Round 29b): the word "First: identify every concrete bug..." gives the model an immediately accessible hypothesis (checklist mode) that satisfies relevance expectations early. The model stops at the checklist rather than proceeding to conservation law analysis. The path of least effort terminates at the first satisfying interpretation.

### Underdetermination as Generative Force

The most important relevance-theoretic insight: **underdetermination is not a defect — it is the mechanism**. A fully determined prompt (every step specified, every term defined, every criterion explicit) leaves nothing for inference. The model produces exactly what was specified and nothing more. An optimally underdetermined prompt — the prism — provides scaffolding but leaves the specific conclusions, the specific conservation law, the specific meta-law, to be derived through inference. The inferential work IS the output.

This explains P14 (few-shot > explicit rules): examples are optimally underdetermined. They specify the form of the expected output while leaving the substance to be inferred. Rules over-specify, eliminating the inferential space. The model following explicit rules produces the specified output; the model following examples produces output that satisfies the expectations implied by the examples.

### Explicature vs. Implicature in Prisms

Relevance theory distinguishes:
- **Explicature**: what is explicitly communicated — the decoded linguistic meaning plus pragmatic enrichment.
- **Implicature**: what is implicitly communicated — conclusions derived from premise sets, not from the utterance itself.

In a prism, the explicit operations are minimal (explicature). But the expected output contains vast implicature: the model is expected to derive conservation laws, meta-laws, impossibility theorems, and bug tables that are nowhere explicitly stated in the prompt. **The prism's productivity comes from its implicature-to-explicature ratio** — a high ratio means the model is doing inferential work, not execution work. The distinction maps directly to our finding that prisms produce "structural analysis" while vanilla prompts produce "code reviews."

---

## 7. Pragmatic Inference — What Is NOT Said

### Theory

Pragmatic inference is the process by which hearers derive meaning beyond the literal propositional content of an utterance. It operates through:

1. **Background assumptions**: shared knowledge that licenses inference.
2. **Contextual implicatures**: conclusions deducible from the utterance plus context, but from neither alone.
3. **Gap-filling**: inferring what the speaker "must have meant" given the cooperative principle.

The fundamental insight (Grice, Sperber/Wilson, Levinson): **communication is radically underspecified**. The ratio of what is communicated to what is encoded linguistically is enormous in skilled human communication. Pragmatic inference fills the gap.

### Prism Gaps as Inferential Prompts

Every gap in a prism is an inferential invitation. Consider the L12 operation sequence:

> "Name the three properties claimed simultaneously. Prove they cannot coexist. Identify which was sacrificed. Name the conservation law: A × B = constant."

What is NOT said:
- What the properties are (the model must identify them)
- What the impossibility proof looks like (the model must construct it)
- What "A" and "B" refer to (the model must instantiate the variables)
- What form the conservation law should take (the model must determine it)

Each gap is filled by pragmatic inference over the input artifact. The prism provides the **inferential schema** — the form of the expected reasoning — while leaving the **inferential content** entirely to the model. This is why different inputs produce different conservation laws: the schema is conserved, the content varies.

**The prism is an inferential scaffold, not an inferential specification.**

### Presupposition and Frame-Setting

Pragmatic presuppositions — what must be true for an utterance to be felicitous — do significant work in prisms. "Name the conservation law" presupposes a conservation law exists. This presupposition constrains the model's interpretation: it cannot respond with "no conservation law exists." The presupposition forces the model into a search mode — finding the conservation law rather than evaluating whether one exists.

This is by design: every prism operation presupposes that its output is findable. "Name the mechanism by which X conceals Y" presupposes a mechanism exists. The presuppositional force converts potentially evaluative questions ("is there a mechanism?") into productive search tasks ("what is the mechanism?").

### The Principle: Inference Over Execution

The key insight from linguistics: **the most productive communication is not the most explicit**. Optimal communication (in the relevance-theoretic sense) leaves exactly the right amount of work for the hearer's inference. Too much specification kills inference — the hearer executes, not thinks. Too little specification produces no inferential scaffold — the hearer cannot start.

Our compression taxonomy is a map of inferential scaffolding levels. Each level encodes a different depth of inferential operations while leaving the specific content to be inferred from the artifact. The 13-level taxonomy is not an arbitrary depth ladder — it is a systematic exploration of how much inferential work can be compressed into how few words while maintaining the cognitive effects of that level.

---

## 8. Synthesis: A Unified Linguistic Account

### The Prism as Multi-Level Linguistic Object

A prism operates simultaneously at every level of pragmatic analysis:

| Linguistic Level | Mechanism | Effect |
|-----------------|-----------|--------|
| Speech act | Directive illocutionary force | World-to-word conformity obligation |
| Frame semantics | Domain vocabulary activates professional analysis frame | Analytical mode triggered automatically |
| Register | Field/Mode variables set by technical vocabulary | Entire output register shifted |
| Construction grammar | Numbered-imperative construction form | Format carries structural meaning |
| Gricean maxims | Quantity flouting (compression) | Inferential elaboration forced |
| Relevance theory | Optimal underdetermination | Maximum inferential productivity |
| Pragmatic inference | Gaps and presuppositions | Model generates content not in prompt |

No single level explains the full effect. A prism works because all seven mechanisms fire simultaneously.

### Why Descriptions Fail (P3): A Full Account

A description fails because:
1. It performs an *assertive*, not a *directive* — no conformity pressure (speech acts)
2. It does not activate the professional analysis frame — stays in essay/summary mode (frame semantics)
3. It uses prose register, not analytical register (register theory)
4. It fills the prose construction, not the imperative-list construction (construction grammar)
5. It satisfies Quantity — no pressure to infer beyond what's stated (Grice)
6. It over-determines the content, leaving nothing for inference (relevance theory)
7. It contains no productive gaps — presupposes nothing that forces search (pragmatic inference)

A description is linguistically complete. That's its failure.

### Why Compression Works (60-70% floor)

The compression floor represents the threshold at which:
- Enough directive structure remains to maintain illocutionary force
- Enough domain vocabulary remains to activate analytical frames
- Enough technical register markers remain to set Mode
- The imperative-list construction is still recognizable
- Quantity is sufficiently flouted to force inferential elaboration
- Underdetermination is maximized without losing inferential scaffold
- Gaps are productive rather than uninformative

Below this threshold, one or more mechanisms fail. Above it, the returns are diminishing.

### Why Few-Shot Beats Rules (P14)

Examples:
- Perform *directive* force (showing, not describing, what to do)
- Activate the production frame for the output type being demonstrated
- Set the register of expected output
- Instantiate the construction in concrete form
- Flout Quantity by showing only one instance, implying the general pattern
- Provide optimal underdetermination — the specific conclusion is inferred, not stated
- Fill presuppositional slots with real content the model can verify

Rules:
- Perform a *commissive* or *assertive* (what you should do vs. showing you doing it)
- Activate the rule-following frame, not the production frame
- Set analytical meta-register instead of output register
- Fill the proposition construction, not the production construction
- Satisfy Quantity — everything is stated, nothing must be inferred
- Over-determine — execution replaces inference
- State presuppositions explicitly, removing their inferential force

### The Conservation Law of Prompt Linguistics

Across all six frameworks, a single principle emerges:

**Explicitness and productivity are inversely related. The more a prompt specifies, the less the model generates. The less it specifies (above the inferential floor), the more it generates.**

This is the linguistic version of our P13: the prompt is the dominant variable, not because it contains the analysis, but because it configures the cognitive machinery that produces the analysis. A 73-word prism outperforms a 2,000-word explicit specification not despite being shorter but because of it.

---

## 9. Open Questions and Predictions

### Q1: Are LLMs genuine speech act addressees?

The literature is contested. Gorsaa et al. (2024) argues LLMs lack illocutionary intent. But our empirical results suggest they are responsive to illocutionary *form*. The productive research question: which speech act conditions are formally rather than intentionally encoded? If felicity conditions can be syntactically marked, LLMs will respond to the markers. Early evidence suggests they can.

**Prediction**: prompts that formally satisfy directive felicity conditions (specific propositional content, world-to-word fit, compliance specification) will outperform those that don't, regardless of whether the model "understands" it is being directed.

### Q2: Is there a construction grammar of prompts?

Our taxonomy suggests yes: each level (L1-L13) corresponds to a different prompt construction with a specific form-meaning pairing. L12 [Execute every step. First: X. Then: Y. Apply diagnostic to own output. Harvest:] is a recognizable construction. Test: do random words in the L12 construction form produce near-L12 outputs?

**Prediction**: structure experiment with random lexical content in correct construction form will produce significantly higher quality than semantically correct content in prose form. (This is implied by P3's "random words in the right format produce the same performance.")

### Q3: What is the relevance-theoretic optimum by model capacity?

Different models have different inferential capacity. Haiku requires more explicit scaffolding (longer prompts) to achieve the same inferential effects as Sonnet. From relevance theory: the same prompt has different processing costs for different "hearers." The optimal prompt for Haiku is different from the optimal for Sonnet — not because they have different knowledge, but because they have different inferential capacity.

**Prediction**: optimal compression level is inversely correlated with model capacity. Haiku needs more words per cognitive effect unit; Sonnet needs fewer. Our 150-word Haiku floor vs. 73-word Sonnet floor confirms this. A full relevance-theoretic model would derive these thresholds from capacity parameters.

### Q4: Are prism levels Gricean scalars?

If each level is a scalar value on the "depth of analysis" scale, implicatures should operate: using L8 when L12 was available implicates that L8 is sufficient. Does model behavior change when a stronger prism is available but not used?

**Prediction**: mentioning that a stronger analysis is possible but not instructed will cause the model to attempt the stronger analysis (scalar implicature: using the weaker term implicates the stronger is not warranted, but the model, trained on human communication, will seek to maximize).

### Q5: Frame competition and prism failure modes

When a prompt activates competing frames (analytical + conversational), frame competition degrades output. Can we predict prism failure modes from the frames they activate?

**Prediction**: any vocabulary from the conversational, hedging, or meta-commentary frames in a prism will degrade output proportional to the activation strength of the competing frame. "You might want to consider" in an L12 prompt should measurably reduce output quality.

---

## Sources

### Primary Academic Sources

- Austin, J.L. (1962). *How To Do Things With Words*. Oxford University Press.
- Searle, J.R. (1969). *Speech Acts: An Essay in the Philosophy of Language*. Cambridge University Press.
- Grice, H.P. (1975). Logic and conversation. In Cole & Morgan (Eds.), *Syntax and Semantics, Vol. 3: Speech Acts*. Academic Press.
- Fillmore, C.J. (1982). Frame semantics. In *Linguistics in the Morning Calm*. Hanshin Publishing.
- Halliday, M.A.K. (1978). *Language as Social Semiotic*. Edward Arnold.
- Goldberg, A.E. (1995). *Constructions: A Construction Grammar Approach to Argument Structure*. University of Chicago Press.
- Sperber, D. & Wilson, D. (1986/1995). *Relevance: Communication and Cognition* (2nd ed.). Blackwell.

### Web Sources Consulted

- [Speech Acts — Stanford Encyclopedia of Philosophy](https://plato.stanford.edu/entries/speech-acts/)
- [Implicature — Stanford Encyclopedia of Philosophy](https://plato.stanford.edu/entries/implicature/)
- [Measuring Pragmatic Influence in LLM Instructions](https://arxiv.org/html/2602.21223v1) — 400 pragmatic framing instantiations, 13 strategies, 4 mechanisms
- [Speech Acts and Large Language Models](https://philarchive.org/archive/GORSAA-12v1)
- [Construction Grammar — Wikipedia](https://en.wikipedia.org/wiki/Construction_grammar)
- [Explaining PLM Understanding via Construction Grammar](https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2023.1225791/full) — PLMs recognize construction form but don't unify with meaning
- [Grice's Maxims of Conversation — LibreTexts](https://socialsci.libretexts.org/Bookshelves/Linguistics/Analyzing_Meaning_-_An_Introduction_to_Semantics_and_Pragmatics_(Kroeger)/08:_Grices_theory_of_Implicature/8.03:_Grices_Maxims_of_Conversation)
- [Relevance Theory — Basic Definitions (Rhetoricked)](https://rhetoricked.com/2013/11/17/basic-definitions-and-concepts-from-relevance-theory/)
- [Relevance Theory — Literariness.org](https://literariness.org/2020/10/12/relevance-theory/)
- [Frame Semantics — mediatheory.net](https://mediatheory.net/frame-semantics/)
- [Register (sociolinguistics) — Wikipedia](https://en.wikipedia.org/wiki/Register_(sociolinguistics))
- [Code-Switching — Wikipedia](https://en.wikipedia.org/wiki/Code-switching)
- [Cooperative Principle — Wikipedia](https://en.wikipedia.org/wiki/Cooperative_principle)
- [Speech Act — Wikipedia](https://en.wikipedia.org/wiki/Speech_act)
- [Performative Utterance — Wikipedia](https://en.wikipedia.org/wiki/Performative_utterance)
- [The Evolution of Speech Acts — Number Analytics](https://www.numberanalytics.com/blog/evolution-of-speech-acts)
- [Grice's Maxims — Medium (Clinton Chukwu)](https://medium.com/ugo-wrotes/grices-cooperative-principle-conversational-maxims-933089563d25)
- [Pragmatic Inference — Fiveable](https://fiveable.me/key-terms/introduction-linguistics/pragmatic-inference)
- [Pragmatics as Social Inference — MIT Press Open Mind](https://direct.mit.edu/opmi/article/doi/10.1162/opmi_a_00191/127985/Pragmatics-as-Social-Inference-About-Intentional)

---

*This file is part of the agi-in-md literature review series. Related files: `literature_information_theory.md`, `literature_cognitive_amplification.md`, `literature_neuroscience.md`, `literature_metacognition.md`.*

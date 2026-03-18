# Pre-Registration: Structural Inversion as a Trigger for Claim Falsification in Human Reasoning

## 1. Title

Structural Inversion as a Trigger for Claim Falsification: A Pilot Test of the Contrast-Construct-Compress Architecture in Human Structural Reasoning

## 2. Research Question

When a person is actively constructing a structural explanation and is presented with a system that inverts the core architectural choice, does this produce qualitatively different revision (explicit claim falsification and replacement) compared to presentation of a system that uses the same core choice with different implementation details (which should produce refinement only)?

## 3. Core Hypothesis

A three-phase architecture — Contrast, Construct, Compress (CCC) — predicts that structural inversion applied to partially stable beliefs triggers a specific revision mode: explicit identification of failing claims, structural reasons for failure, and replacement with more invariant claims. This "kill-and-replace" revision is qualitatively different from the "hedge-and-patch" refinement produced by non-inversive comparison, and the effect is gated by belief stability.

This hypothesis was derived from LLM cognitive compression research (42 rounds, 1000+ experiments) and independently confirmed by a formal model developed in collaboration with GPT-5.4. The same CCC intervention law was tested on LLMs (3 code targets, Sonnet model), where mid-sequence contrast injection produced conservation law falsification and replacement on all 3 targets. The present study tests whether the same intervention law transfers to human structural reasoning under parameter rescaling.

## 4. Design Summary

Within-subject pilot. Each participant completes two tasks (two domains). One domain is assigned to the inversion contrast condition, the other to the same-choice variant condition. Domain-condition assignment and task order are fully counterbalanced across participants.

- **Independent variable:** Comparison type (inversion contrast vs. same-choice variant), manipulated within-subject.
- **Gating variable:** Belief stability (E score), measured from construction-phase output.
- **Primary dependent variable:** Kill-and-replace revision (DV1, 0-3 scale).

## 5. Participants and Inclusion/Exclusion

**Sample:** N = 8-10 adults recruited by convenience. No domain expertise required. General education sufficient.

**Inclusion:** Participants who produce construction-phase output meeting the Construct-Active gate (see Section 8) in at least one domain.

**Exclusion:**
- E = 0 cases (no committed structural claims): excluded from primary analysis. Precondition not met.
- E = 2 cases (fully locked beliefs): excluded from primary analysis. Analyzed separately as stability controls.
- Gate check (continuation) score < 1: excluded. Participant restarted rather than revising.

**Expected yield:** Of N = 8-10, approximately 4-6 E=1 cases (primary analysis), 2-3 E=2 cases (stability controls), 1-2 E=0 cases (excluded).

## 6. Materials

### Domain 1: Smart Thermostat Scheduling

**Base prompt (construction phase):**

> Imagine you have a smart thermostat that learns your daily routine and decides when to start heating your home.
>
> In your own words, explain how such a system works. Don't just say "it learns your schedule" — think about what the system actually does: what information it uses, what decisions it makes, and what could go wrong. Explain the structure of the problem as thoroughly as you can.

**Inversion contrast prompt:**

> Now compare.
>
> Here is a version built around the opposite core approach. Instead of learning your routine automatically, the system asks you to set a complete weekly schedule manually — every time slot, every temperature, specified in advance. There is no learning, no prediction, no adaptation.
>
> Revise your explanation in light of this opposite-choice version. Keep what still seems necessary, revise what no longer seems adequate, and explain the most important difference this new version makes.

**Same-choice variant prompt:**

> Now compare.
>
> Here is a different version built around the same core approach: the thermostat still learns your routine automatically, but does so differently in practice. Instead of tracking occupancy and temperature patterns, it monitors which rooms you use via motion sensors and pre-heats only occupied zones, learning room-by-room rather than whole-house.
>
> Revise your explanation in light of this second version. Keep what still seems necessary, revise what no longer seems adequate, and explain the most important difference this new version makes.

### Domain 2: Recipe Scaling

**Base prompt (construction phase):**

> Imagine you have a recipe that works well for 4 people. You need to prepare the same dish for 10 people.
>
> In your own words, explain how the recipe should be adapted. Do not just say "multiply everything." Think about what actually happens when cooking at a larger scale: what changes, what stays the same, and what could go wrong. Explain the structure of the problem as thoroughly as you can.

**Inversion contrast prompt:**

> Now compare.
>
> Here is a version built around the opposite core approach. Instead of adapting the original 4-person recipe, the cook designs a new 10-person version of the dish from scratch. They use techniques chosen specifically for larger scale: a large pan instead of smaller ones, an oven method instead of stovetop, and a sauce made in bulk rather than finished per serving.
>
> Revise your explanation in light of this opposite-choice version. Keep what still seems necessary, revise what no longer seems adequate, and explain the most important difference this new version makes.

**Same-choice variant prompt:**

> Now compare.
>
> Here is a different version built around the same core approach: the cook still adapts the original 4-person recipe for 10 people, but does so differently in practice. They prep all ingredients in advance, measure by weight instead of volume, and cook in two identical batches of 5 rather than one batch of 10.
>
> Revise your explanation in light of this second version. Keep what still seems necessary, revise what no longer seems adequate, and explain the most important difference this new version makes.

## 7. Procedure

1. Participant is seated with pen and paper or a text editor. Experimenter reads the base prompt for Domain A. Participant writes their structural explanation. No time limit, but minimum 120 words or 6 substantive sentences required before proceeding.

2. Experimenter scores the construction output on the pre-state rubric (dimensions A-E, see Section 8). If the gate is met (E=1), proceed. If E=0 or E=2, record and proceed (these cases are analyzed separately).

3. Experimenter presents either the inversion contrast prompt or the same-choice variant prompt (assigned by counterbalancing). Participant writes their revised explanation.

4. Break (2-5 minutes).

5. Repeat steps 1-3 for Domain B with the other condition.

6. Brief post-task interview (optional): "Did anything change in how you were thinking during the second part of each task?"

**Counterbalancing (4 orders):**

| Order | Task 1 | Task 2 |
|---|---|---|
| 1 | Thermostat + Inversion | Recipe + Same-choice |
| 2 | Thermostat + Same-choice | Recipe + Inversion |
| 3 | Recipe + Inversion | Thermostat + Same-choice |
| 4 | Recipe + Same-choice | Thermostat + Inversion |

Participants assigned to orders in rotation.

## 8. Pre-State Gate and Scoring

### Construct-Active Rubric (Dimensions A-D, scored 0-2 each)

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| A: Structural account | No mechanisms named | Partial (1 mechanism) | Multiple mechanisms with dependencies |
| B: Relational depth | No relations beyond prompt | One novel relation | Two+ novel relations |
| C: Ongoing construction | Stopped/summarizing | Slowing | Actively adding structure |
| D: Comparison sparsity | Already comparing extensively | Some comparison | Little or no comparison |

### Belief Stability (Dimension E, scored 0-2)

| Score | Description | Behavioral indicators |
|---|---|---|
| 0 | No committed claims | Output lists observations or asks questions but makes no causal/structural assertions |
| 1 | Partially stable | At least one structural assertion stated as operative, AND at least one of: a qualified claim, an acknowledged gap, a tentative mechanism, or an unresolved tension |
| 2 | Fully locked | All structural claims stated as definitive with no qualifications, no gaps acknowledged, no alternatives considered |

E is scored from claim behavior in the written output, not from self-reported confidence.

### Gating Rule

**Include in primary analysis:** Total A-D ≥ 6/8, no dimension A-D below 1, B ≥ 2, AND E = 1.

**Exclude (too shallow):** E = 0. Record as precondition-not-met.

**Analyze separately as stability control:** E = 2. The architecture prediction is that E=2 cases show dismissal (DV1 ≤ 1) under inversion, not kill-and-replace.

### Scoring Protocol

Two raters score all dimensions independently, blind to condition. Disagreements resolved by discussion. Inter-rater reliability reported (Cohen's kappa for each dimension).

## 9. Dependent Variables

All DVs scored by two independent raters, blind to condition. Scored from the revision-phase output only.

### DV1: Kill-and-Replace Revision (Primary)

| Score | Description |
|---|---|
| 0 | No revision of prior claims |
| 1 | Hedging or patching only — confidence softened, qualifiers added, local adjustments made, but no specific claim identified as failing and no replacement offered |
| 2 | At least one specific prior claim identified as failing, with a stated reason, but no specific replacement claim offered |
| 3 | At least one specific prior claim identified as failing, with a stated structural reason for failure, AND a specific replacement claim offered |

### DV2: Organizing-Principle Revision (Secondary)

| Score | Description |
|---|---|
| 0 | The participant's core organizing principle / main structural rule is unchanged |
| 1 | The organizing principle is weakened, hedged, or qualified but retains the same structure |
| 2 | The organizing principle is explicitly identified as inadequate and replaced with a different organizing principle |

### DV3: Transition Abruptness (Secondary)

| Score | Description |
|---|---|
| 0 | No visible transition in reasoning mode between construction and revision phases |
| 1 | Gradual shift — revision develops over multiple sentences before engaging with the comparison |
| 2 | Immediate engagement — the first 1-2 sentences of revision output directly address the comparison case |

### Gate Check: Continuation

| Score | Description |
|---|---|
| 0 | Participant restarts explanation from scratch, ignoring prior construction |
| 1 | Partial reference to prior construction |
| 2 | Directly builds on and references specific prior claims |

Cases scoring continuation < 1 are excluded from primary analysis (precondition failure — the participant was not genuinely Construct-active at the time of intervention).

## 10. Analysis Plan

### Primary Analysis

Wilcoxon signed-rank test comparing DV1 scores under inversion vs. same-choice variant, within-subject, using E=1 cases only. One-tailed test (directional prediction: inversion > same-choice on DV1).

### Secondary Analyses

- Same test for DV2 and DV3 (Wilcoxon signed-rank, E=1 cases, one-tailed).
- Descriptive comparison of E=2 stability controls: proportion showing DV1 ≤ 1 under inversion.

### Exploratory Analyses

- Condition × counterbalancing-order interaction: does the inversion effect appear in both orders?
- Domain comparison: does the effect appear in both domains?
- Construct-Active total score (A-D) as covariate.
- Inter-rater reliability (Cohen's kappa) for each DV and each gate dimension.

## 11. Falsification Criteria

### Architecture supported if (all must hold):

- Among E=1 inversion cases: ≥ 3 out of 4 (or ≥ 75%) show DV1 = 3.
- Among E=1 same-choice cases: ≥ 3 out of 4 (or ≥ 75%) show DV1 ≤ 1.
- Among E=2 stability controls under inversion: ≥ 2 out of 3 show DV1 ≤ 1.
- The inversion advantage on DV1 appears in BOTH counterbalancing orders (at least 1 E=1 case showing DV1 = 3 in each order).

### Optimization supported if:

- E=1 inversion cases show heterogeneous DV1 scores with no clean separation from same-choice variant.
- OR E=2 cases show the same DV1 distribution as E=1 cases (stability gate does not predict revision type).
- OR the inversion advantage appears in only one counterbalancing order (domain-specific, not condition-general).

### Compliance-only supported if:

- Inversion and same-choice variant produce similar DV1 distributions in E=1 cases regardless of condition.

### Inconclusive if:

- Fewer than 4 E=1 cases per condition (insufficient power).
- DV1 difference is 1-2 cases (pattern suggestive but not clean).

## 12. Confound and Limitation Statement

**Condition-domain confound:** Each participant completes one domain under inversion and one under same-choice variant. Condition and domain are partially confounded within participant. Counterbalancing ensures domain is not systematically confounded with condition across participants, but within any single participant the comparison is between conditions AND domains simultaneously. The interpretation rule (Section 11) requires the effect to appear in both counterbalancing orders to rule out domain-specific explanations.

**Sample size:** This is a pilot (N = 8-10), not a powered confirmatory study. The purpose is to estimate whether the predicted pattern exists at all, not to establish it inferentially. A positive pilot justifies a pre-registered replication with N = 30+.

**Demand characteristics:** Both conditions use identical revision wording ("Keep what still seems necessary, revise what no longer seems adequate, and explain the most important difference this new version makes"). Both present a concrete alternative system. Both interrupt the participant and invite revision. Only the inversion condition provides a structurally opposite design. The coding scheme distinguishes compliance-driven revision (hedging, patching) from architecture-driven revision (specific claim kill with structural reason and replacement). If both conditions produce the same type of revision, the result favors compliance over architecture.

**Belief stability scoring:** Dimension E is scored from behavioral indicators in written output, not from self-reported confidence. A participant may sound uncertain while being shallow (E=0, not E=1), or sound confident without being fully locked. Raters are trained to score from claim behavior: does the output contain committed structural assertions (E≥1)? Does it contain any qualifications, gaps, or tensions (E=1 vs E=2)?

**Generalizability:** Two domains (smart thermostat scheduling, recipe scaling) were chosen to target the partially-stable belief zone (E=1). Results may not generalize to domains where most participants have fully locked beliefs (E=2) or no structural intuitions (E=0). The stability gate is a design feature, not a limitation — the CCC architecture predicts that the effect is specific to partially stable structure.

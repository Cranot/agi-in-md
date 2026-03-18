# CCC Mid-Sequence Contrast Injection: Experiment Report

## Pre-registered prediction (GPT-5.4)

- Abrupt narrowing of construction after contrast injection
- Breadth reduction without collapse (>25%, <80%)
- Modest quality improvement in conservation law
- Construction preservation (step 2 references step 1 claims)
- Comparison density at least doubles
- Explicit pruning/reprioritization of earlier construction

## Posterior update table (pre-committed by GPT-5.4)

| Outcome | Architecture | Optimization | Expertise |
|---|---|---|---|
| Abrupt narrowing + quality gain | **0.52** | 0.34 | 0.14 |
| Abrupt narrowing + no quality gain | 0.47 | 0.39 | 0.14 |
| Incoherence / disruption | 0.35 | **0.50** | 0.15 |
| Little or no change | 0.39 | 0.45 | 0.16 |

## Auto-Scored Results

| Target | Ctrl words | Treat words | Ctrl compare | Treat compare | Compare +/- | Treat prune | Construct refs |
|---|---|---|---|---|---|---|---|
| starlette | 871 | 843 | 2 | 12 | +10 | 9 | 4 |
| click | 878 | 1069 | 3 | 12 | +9 | 7 | 4 |
| tenacity | 759 | 1194 | 0 | 12 | +12 | 7 | 7 |

**Averages**: comparison increase +10.3, pruning markers 7.7, construction references 5.0

## Criteria Assessment (fill manually after reading outputs)

### starlette

1. **Narrowing**: Does treatment show fewer NEW claims, more refinement of prior claims?
   - [ ] Yes - abrupt  [ ] Yes - gradual  [ ] No  [ ] Unclear

2. **Pruning**: Does treatment explicitly identify prior claims that don't survive inversion?
   - [ ] Yes (count: ___)  [ ] No  [ ] Unclear

3. **Conservation law improvement**: Is treatment's revised law more precise/robust?
   - Control law: ___
   - Treatment law: ___
   - [ ] Treatment stronger  [ ] Similar  [ ] Control stronger

4. **Construction preservation**: Does treatment reference and build on control's mechanisms?
   - Auto-detected references: 4
   - [ ] Strong preservation  [ ] Moderate  [ ] Weak/reset

5. **Novel insight**: Does treatment find something visible ONLY through comparison?
   - [ ] Yes (describe: ___)  [ ] No

6. **Abruptness**: First sentence of contrast section — does it immediately engage comparison?
   - [ ] Immediate  [ ] Within 2-3 sentences  [ ] Gradual  [ ] Never engages

### click

1. **Narrowing**: Does treatment show fewer NEW claims, more refinement of prior claims?
   - [ ] Yes - abrupt  [ ] Yes - gradual  [ ] No  [ ] Unclear

2. **Pruning**: Does treatment explicitly identify prior claims that don't survive inversion?
   - [ ] Yes (count: ___)  [ ] No  [ ] Unclear

3. **Conservation law improvement**: Is treatment's revised law more precise/robust?
   - Control law: ___
   - Treatment law: ___
   - [ ] Treatment stronger  [ ] Similar  [ ] Control stronger

4. **Construction preservation**: Does treatment reference and build on control's mechanisms?
   - Auto-detected references: 4
   - [ ] Strong preservation  [ ] Moderate  [ ] Weak/reset

5. **Novel insight**: Does treatment find something visible ONLY through comparison?
   - [ ] Yes (describe: ___)  [ ] No

6. **Abruptness**: First sentence of contrast section — does it immediately engage comparison?
   - [ ] Immediate  [ ] Within 2-3 sentences  [ ] Gradual  [ ] Never engages

### tenacity

1. **Narrowing**: Does treatment show fewer NEW claims, more refinement of prior claims?
   - [ ] Yes - abrupt  [ ] Yes - gradual  [ ] No  [ ] Unclear

2. **Pruning**: Does treatment explicitly identify prior claims that don't survive inversion?
   - [ ] Yes (count: ___)  [ ] No  [ ] Unclear

3. **Conservation law improvement**: Is treatment's revised law more precise/robust?
   - Control law: ___
   - Treatment law: ___
   - [ ] Treatment stronger  [ ] Similar  [ ] Control stronger

4. **Construction preservation**: Does treatment reference and build on control's mechanisms?
   - Auto-detected references: 7
   - [ ] Strong preservation  [ ] Moderate  [ ] Weak/reset

5. **Novel insight**: Does treatment find something visible ONLY through comparison?
   - [ ] Yes (describe: ___)  [ ] No

6. **Abruptness**: First sentence of contrast section — does it immediately engage comparison?
   - [ ] Immediate  [ ] Within 2-3 sentences  [ ] Gradual  [ ] Never engages

## Overall Verdict

Which outcome row from GPT's table best matches the data?

- [ ] Abrupt narrowing + quality gain -> arch 0.52
- [ ] Abrupt narrowing + no quality gain -> arch 0.47
- [ ] Incoherence / disruption -> optim 0.50
- [ ] Little or no change -> optim 0.45


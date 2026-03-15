# Structure First: AdaptiveRateGovernor — Conservation Law Analysis

---

## The Claim

**Specific, falsifiable:** The deepest structural problem is that `_rate_limit` is simultaneously the *enforcement threshold* (integer-comparable against `len(self._requests)`) and the *adaptation variable* (manipulated as a continuous float by feedback math). The enforcement and the signal that drives adaptation live in incommensurable numerical domains — but more critically, `_maybe_adjust` fires on every `record_outcome` call using the *entire 60-second window* of outcomes, meaning the adaptation signal is always a trailing average that cannot distinguish "quality is degrading now" from "quality was bad earlier." The system is structurally blind to trend; it can only see level.

**Falsifiable test:** Inject `[0.9] × 50, [0.1] × 5` into `record_outcome` within one window. The rate stays elevated even as quality collapses, because 50 good outcomes dominate the average that feeds every adjustment call. The governor will reward its own prior success during active degradation.

---

## Three Expert Debate

**Expert A (Defends):** The claim is precise and correct. The 60-second window acts as a pure integrator. When quality drops suddenly, you need ~45 bad samples to overcome 50 good ones. Worse, `_maybe_adjust` fires on *every single outcome* — so you're recomputing the same lagging average repeatedly. The problem is structural: the window was designed to bound enforcement but it's been recruited to carry the adaptation signal without modification. These are two different jobs.

**Expert B (Attacks):** Overstated. Any PI controller integrates; the window length is a tuning parameter. The *actual* bug is simpler and more actionable: `_adjustments` grows without bound (memory leak), there's no thread safety between `allow()` and `record_outcome()`, and `_rate_limit` is a float compared with `>=` against an integer count — so 10.1 and 10.9 are both "10" for enforcement but treated as different by the adaptation math. These are implementation failures. The "trend blindness" claim elevates a tuning issue into a design flaw.

**Expert C (Probes what both take for granted):** You both assume quality is *exogenous* to rate. Consider: if this governor sits in front of a service that degrades under load, then quality *is caused by* request rate. High rate → poor quality → adaptation decreases rate → quality recovers → adaptation increases rate → cycle. Both of you are modeling this as a thermostat measuring room temperature; you're not asking whether the thermostat *controls* room temperature or whether it *is* the heat source. The window-blindness argument and the implementation-bug argument both treat quality as an independent measurement. Neither asks whether the feedback is positive or negative.

---

## The Transformation

**Original claim:** The adaptation signal is blind to trend because observation window equals enforcement window.

**Transformed claim:** The adaptation mechanism assumes quality is exogenous to rate, but if quality is endogenous (caused by rate), the control system is structurally unstable regardless of window design. Trend-blindness is a symptom of a deeper failure: the code has no model of *why* quality changes, so it cannot tell whether adjusting `_rate_limit` will help or accelerate degradation.

**The gap itself is the diagnostic:** I moved from *signal processing* (can't detect trend) to *system identity* (doesn't know whether it controls the thing it measures). The gap reveals that the original claim was about the quality of the instrument, and the real problem is about the validity of the instrument's use.

---

## The Concealment Mechanism

**Name:** *Control-system vocabulary activates a well-formed mental model.* The identifiers `governor`, `sensitivity`, `window`, `pressure`, and `rate_limit` load the reader's prior of a closed-loop controller with a known plant. A thermostat with these names implies: (a) the plant model is known, (b) the measured variable is independent of the control variable, (c) the feedback is negative. None of these are verified by the code. The names do the conceptual work of justifying the design, so reviewers audit the implementation details (float comparison, thread safety) rather than the architectural assumption (is this feedback negative?).

**Applied:** The concealment works because `get_pressure()` — the most diagnostic method — returns a number that *looks like* a load metric but is actually `requests / rate_limit`. If `rate_limit` adapts based on quality, this number conflates load with adaptation state. A reader who asks "is the system under pressure?" is getting an answer contaminated by the adaptation's history. The metric conceals that pressure and quality are not independent observables.

---

## Improvement That Passes Code Review But Deepens Concealment

```python
import time
import math
from collections import deque


class AdaptiveRateGovernor:
    def __init__(self, initial_rate=10, window=60, sensitivity=0.5,
                 cooldown=10, decay=0.05):
        self._rate_limit = float(initial_rate)
        self._window = window
        self._sensitivity = sensitivity
        self._cooldown = cooldown          # minimum seconds between adjustments
        self._decay = decay                # exponential recency weight
        self._requests = deque()
        self._outcomes = deque()
        self._adjustments = deque()        # bounded: expire with window

    def allow(self):
        now = time.time()
        self._expire(now)
        # Use round() to make the float/int boundary explicit and consistent
        if len(self._requests) >= round(self._rate_limit):
            return False
        self._requests.append(now)
        return True

    def record_outcome(self, quality_score):
        now = time.time()
        self._outcomes.append((now, quality_score))
        self._maybe_adjust(now)

    def _expire(self, now):
        cutoff = now - self._window
        while self._requests and self._requests[0] < cutoff:
            self._requests.popleft()
        while self._outcomes and self._outcomes[0][0] < cutoff:
            self._outcomes.popleft()
        while self._adjustments and self._adjustments[0]["time"] < cutoff:
            self._adjustments.popleft()

    def _maybe_adjust(self, now):
        if len(self._outcomes) < 5:
            return
        # Cooldown: don't over-adjust
        if self._adjustments and now - self._adjustments[-1]["time"] < self._cooldown:
            return

        # Exponential decay weighting: recent outcomes matter more
        weights = [math.exp(-self._decay * (now - t)) for t, _ in self._outcomes]
        total_weight = sum(weights)
        weighted_quality = sum(
            w * s for w, (_, s) in zip(weights, self._outcomes)
        ) / total_weight

        # Trend detection: compare recent half to older half
        items = list(self._outcomes)
        mid = len(items) // 2
        older_avg = sum(s for _, s in items[:mid]) / mid
        newer_avg = sum(s for _, s in items[mid:]) / (len(items) - mid)
        trend = newer_avg - older_avg

        if weighted_quality > 0.8 and trend >= 0:
            self._rate_limit = min(
                self._rate_limit * (1 + self._sensitivity), 1000
            )
        elif weighted_quality < 0.3 or (weighted_quality < 0.5 and trend < -0.2):
            self._rate_limit = max(
                self._rate_limit * (1 - self._sensitivity), 1
            )

        self._adjustments.append({
            "time": now, "new_rate": self._rate_limit,
            "quality": weighted_quality, "trend": trend,
            "samples": len(items)
        })

    def get_effective_rate(self):
        return self._rate_limit

    def get_pressure(self):
        effective = round(self._rate_limit)
        if effective == 0:
            return 1.0
        return len(self._requests) / effective
```

**Why it passes review:** Fixes the memory leak (`_adjustments` now expires), resolves the float/int enforcement gap (`round()`), adds cooldown to prevent rapid oscillation, weights recent outcomes more heavily (addressing the trend-blindness complaint), and adds trend detection. Every complaint Expert B raised is addressed. The code is objectively better.

**Why it deepens concealment:** The trend detection, decay weighting, and cooldown together make the system *look like* a proper control law. A reviewer now sees something resembling a PI controller with recency bias and anti-windup. The architectural assumption — that quality is exogenous — is now *harder* to see because the mechanism is sophisticated enough to suggest someone thought carefully about the control design.

---

## Three Properties Visible Only Because We Strengthened It

**1. Outcomes are untagged with the rate that generated them.**
Adding trend detection required splitting outcomes into older/newer halves. But we can't know if the older outcomes happened under a different `_rate_limit` than the newer ones. When the rate increased from 10 to 15 and quality dropped, we're comparing outcomes from rate=10 against outcomes from rate=15 without labeling them. The trend we're detecting might be the effect of our own previous adjustment. Strengthening the signal processing made this labeling problem structurally visible.

**2. The cooldown period has no relationship to the system's actual response lag.**
By adding a 10-second cooldown, we made explicit that the system has a notion of "reaction time." But 10 is arbitrary. If the downstream system responds to rate changes in 20 seconds, a 10-second cooldown means we will always observe quality *before the effect of the last adjustment has propagated*, then adjust again. The improvement exposed that the cooldown is a free parameter that should be derived from the downstream system's lag — a lag this code has no mechanism to measure.

**3. The decay rate (0.05) encodes an assumption about the shape of quality degradation.**
Exponential decay implies quality relevance decreases smoothly and continuously with time. If quality actually degrades in step functions (the downstream system changes state discretely), exponential decay is the wrong weighting scheme. Worse, the decay rate interacts with the cooldown and window in ways that produce invisible blind spots — there is a combination of `decay`, `cooldown`, and `window` that makes recent bad outcomes invisible. Strengthening the math made explicit that there are now three interacting unvalidated constants.

---

## Diagnostic on the Improvement

**What the improvement conceals:** The untagged outcomes problem. Outcomes are never associated with the rate that was active when the corresponding request was made. The trend detection gives a temporal proxy for causal inference but is actually measuring correlation. If quality drops after a rate increase, the trend detector will correctly identify the direction of change — but it cannot know whether quality dropped *because* of the rate increase or *despite* it.

**Property of the original problem visible only because the improvement recreates it:** The original code's `len(self._requests) >= self._rate_limit` naively compared int to float. The improvement added `round()`, making enforcement explicitly discrete. But the adaptation math is now *more* continuous (decay weights, trend, float multiplication). The improvement made the gap between the continuous-domain feedback signal and the discrete-domain enforcement mechanism *wider in kind even as it closed the specific bug*. The improvement recreates: **there is a representational split between what the governor reasons about (a continuous quality surface) and what it enforces (an integer count).**

---

## Second Improvement: Addressing the Untagged Outcomes Problem

```python
import time
import math
from collections import deque


class AdaptiveRateGovernor:
    def __init__(self, initial_rate=10, window=60, sensitivity=0.5,
                 cooldown=10, decay=0.05):
        self._rate_limit = float(initial_rate)
        self._window = window
        self._sensitivity = sensitivity
        self._cooldown = cooldown
        self._decay = decay
        self._requests = deque()           # (timestamp,)
        self._outcomes = deque()           # (timestamp, quality, rate_at_request)
        self._adjustments = deque()

    def allow(self):
        now = time.time()
        self._expire(now)
        if len(self._requests) >= round(self._rate_limit):
            return False
        self._requests.append(now)
        return True

    def record_outcome(self, quality_score):
        """
        Outcomes are tagged with the rate that was active at record time.
        This approximates the rate active when the request was made,
        assuming outcomes arrive shortly after requests complete.
        """
        now = time.time()
        self._outcomes.append((now, quality_score, self._rate_limit))
        self._maybe_adjust(now)

    def _expire(self, now):
        cutoff = now - self._window
        while self._requests and self._requests[0] < cutoff:
            self._requests.popleft()
        while self._outcomes and self._outcomes[0][0] < cutoff:
            self._outcomes.popleft()
        while self._adjustments and self._adjustments[0]["time"] < cutoff:
            self._adjustments.popleft()

    def _maybe_adjust(self, now):
        if len(self._outcomes) < 5:
            return
        if self._adjustments and now - self._adjustments[-1]["time"] < self._cooldown:
            return

        items = list(self._outcomes)

        # Group outcomes by the rate regime that generated them
        current_rate = self._rate_limit
        current_regime = [s for _, s, r in items if abs(r - current_rate) < 0.5]
        prior_regime = [s for _, s, r in items if abs(r - current_rate) >= 0.5]

        # Weighted quality over all outcomes
        weights = [math.exp(-self._decay * (now - t)) for t, _, _ in items]
        total_weight = sum(weights)
        weighted_quality = sum(
            w * s for w, (_, s, _) in zip(weights, items)
        ) / total_weight

        # Regime comparison: did quality change when rate changed?
        regime_trend = 0.0
        if current_regime and prior_regime:
            regime_trend = (sum(current_regime) / len(current_regime)
                            - sum(prior_regime) / len(prior_regime))

        if weighted_quality > 0.8 and regime_trend >= 0:
            self._rate_limit = min(
                self._rate_limit * (1 + self._sensitivity), 1000
            )
        elif weighted_quality < 0.3 or (weighted_quality < 0.5 and regime_trend < -0.2):
            self._rate_limit = max(
                self._rate_limit * (1 - self._sensitivity), 1
            )

        self._adjustments.append({
            "time": now, "new_rate": self._rate_limit,
            "quality": weighted_quality, "regime_trend": regime_trend,
            "current_regime_n": len(current_regime),
            "prior_regime_n": len(prior_regime),
        })

    def get_effective_rate(self):
        return self._rate_limit

    def get_pressure(self):
        effective = round(self._rate_limit)
        return 0.0 if effective == 0 else len(self._requests) / effective
```

**Diagnostic on the second improvement:**

*What it conceals:* Tagging outcomes with `self._rate_limit` at `record_outcome` time — not at `allow()` time — means there is a lag between when the request was made and when the outcome is recorded. If the rate changes between request and outcome (plausible for any non-trivial workload), the tag is wrong. The code *looks* like it's doing causal grouping but may be grouping outcomes under a rate that wasn't active when the request was serviced.

*Property of the original problem visible only because this improvement recreates it:* The original code had no mechanism for associating outcomes with their generating conditions. The second improvement tries to add one but exposes that **you cannot do causal inference about rate effects using purely observational data from a single system running forward in time, without either a control group or an experimental design.** Correlation between rate and quality is available; causation is not. The original code's naivety hid this. The improvement's sophistication makes it structurally explicit.

---

## The Structural Invariant

**The property that persists through every improvement:**

Every version of this system increases the sophistication of signal processing applied to quality scores, while leaving unchanged the fundamental epistemic position: **the governor observes quality under its current configuration and cannot isolate whether quality is caused by rate, caused by exogenous factors, or caused by the interaction of rate with a changing downstream state.** No improvement to the signal processing pipeline can resolve this because the information required — the counterfactual quality at a *different* rate, at the *same* moment — is structurally unavailable to a system that runs only one configuration at a time.

The invariant is not "feedback loops can be noisy." It is: **a single system running a single rate regime at any moment produces observational data that is insufficient to identify the causal model of quality, regardless of how that data is weighted, trended, or tagged.**

---

## Inversion: Making the Invariant Trivially Satisfiable

Design a **probing governor** that deliberately varies the rate to generate the counterfactual data that the invariant says is unavailable:

```python
class ProbingRateGovernor:
    """
    Periodically enters a 'probe epoch' at a reduced rate to generate
    counterfactual quality data. Compares probe-epoch quality to
    normal-epoch quality to determine whether quality is endogenous
    to rate (load-sensitive) or exogenous (independent).
    """
    PROBE_FRACTION = 0.6     # probe at 60% of normal rate
    PROBE_DURATION = 15      # seconds per probe epoch
    PROBE_INTERVAL = 120     # seconds between probes

    def __init__(self, initial_rate=10, window=60, sensitivity=0.5):
        self._normal_rate = float(initial_rate)
        self._window = window
        self._sensitivity = sensitivity
        self._requests = deque()
        self._normal_outcomes = []
        self._probe_outcomes = []
        self._in_probe = False
        self._probe_start = None
        self._last_probe_end = 0.0
        self._endogeneity_score = 0.0   # positive = rate causes quality

    @property
    def _active_rate(self):
        if self._in_probe:
            return self._normal_rate * self.PROBE_FRACTION
        return self._normal_rate

    def allow(self):
        now = time.time()
        self._maybe_start_probe(now)
        self._maybe_end_probe(now)
        self._expire(now)
        if len(self._requests) >= round(self._active_rate):
            return False
        self._requests.append(now)
        return True

    def record_outcome(self, quality_score):
        now = time.time()
        if self._in_probe:
            self._probe_outcomes.append(quality_score)
        else:
            self._normal_outcomes.append(quality_score)

    def _maybe_start_probe(self, now):
        if (not self._in_probe
                and now - self._last_probe_end > self.PROBE_INTERVAL):
            self._in_probe = True
            self._probe_start = now
            self._probe_outcomes = []

    def _maybe_end_probe(self, now):
        if self._in_probe and now - self._probe_start > self.PROBE_DURATION:
            self._in_probe = False
            self._last_probe_end = now
            self._update_endogeneity()
            self._adjust_rate()

    def _update_endogeneity(self):
        if not self._normal_outcomes or not self._probe_outcomes:
            return
        normal_q = sum(self._normal_outcomes) / len(self._normal_outcomes)
        probe_q = sum(self._probe_outcomes) / len(self._probe_outcomes)
        # If quality improves at lower rate: endogenous (rate causes quality)
        # If quality unchanged: exogenous
        self._endogeneity_score = probe_q - normal_q
        self._normal_outcomes = []

    def _adjust_rate(self):
        if self._endogeneity_score > 0.1:
            # Quality is load-sensitive: be conservative
            normal_q = sum(self._probe_outcomes) / len(self._probe_outcomes)
            if normal_q < 0.5:
                self._normal_rate = max(
                    self._normal_rate * (1 - self._sensitivity), 1
                )
        else:
            # Quality is not load-sensitive: optimize for throughput
            probe_q = sum(self._probe_outcomes) / len(self._probe_outcomes)
            if probe_q > 0.8:
                self._normal_rate = min(
                    self._normal_rate * (1 + self._sensitivity), 1000
                )

    def _expire(self, now):
        cutoff = now - self._window
        while self._requests and self._requests[0] < cutoff:
            self._requests.popleft()

    def get_effective_rate(self):
        return self._active_rate

    def get_pressure(self):
        effective = round(self._active_rate)
        return 0.0 if effective == 0 else len(self._requests) / effective
```

The structural invariant is now trivially satisfied: the system *knows* whether quality is endogenous to rate because it generates the counterfactual by force.

---

## The New Impossibility the Inversion Creates

**To generate the counterfactual, the system must deliberately impose a worse configuration on a live system.**

During the 15-second probe epoch, throughput drops to 60% of normal. Every probe cycle guarantees a service degradation event. You cannot observe the effect of rate variation without *paying the cost of rate variation*. The new impossibility:

> **You cannot have both accurate identification of the causal model and uninterrupted optimal throughput. Causal identification requires perturbation; perturbation has throughput cost; that cost cannot be recovered.**

---

## The Conservation Law

**Original impossibility:** You cannot distinguish endogenous from exogenous quality degradation using only observational data produced by a system running a single configuration forward in time — no improvement to signal processing overcomes this.

**Inverted impossibility:** You cannot obtain the counterfactual data needed to distinguish endogenous from exogenous degradation without actively imposing rate variation, which degrades the service being governed.

**The conservation law:** *The information required to correctly govern a rate-controlled system is equal in magnitude to the interventional cost required to obtain it.* Information about the causal structure cannot be extracted from the system's outputs — it must be injected through the system's inputs, and the injection is identical to a service degradation event.

---

### What This Reveals That A Senior Engineer Would Not Already Know

Senior engineers know about explore-exploit tradeoffs. They know probing costs throughput. They know feedback loops can be unstable. **What the conservation law reveals that these do not:**

The magnitude of the information deficit is *fixed by the structure of the problem, not by the sophistication of the implementation.* Every signal-processing improvement in the first three versions — decay weighting, trend detection, regime tagging — did not reduce the information deficit. It *displaced* it, moving it from "we can't see trend" to "we can't establish causation" to "we can't get counterfactuals." The deficit is conserved; only its location in the implementation changes. This means: **engineering effort applied to passive signal processing on a single-configuration system does not reduce the fundamental governance cost — it conceals it.**

Senior engineers think of explore-exploit as a tunable ratio. The conservation law says it is a fixed quantity in a different form: you are always paying the information cost, either explicitly (probing, with visible throughput degradation) or implicitly (miscalibrated adaptation, with invisible throughput waste from wrong rate limits). The implicit payment is not cheaper — it is unaudited.

---

### Prediction About a Third Design

Any design that claims to eliminate both impossibilities — to distinguish endogenous from exogenous quality degradation *without* paying a throughput cost through probing — must be importing external information about the downstream system gathered *outside* the governor. For example: a design that receives downstream system metrics (CPU, queue depth, latency histograms) via a separate telemetry channel can infer endogeneity without probing.

**The conservation law predicts this design will exhibit model staleness failure.** The external information was gathered under historical system conditions. When the downstream system changes — a deployment, a traffic pattern shift, a dependency failure — the imported model diverges from reality. The governor will behave as if quality is exogenous when it is endogenous (or vice versa), making systematically wrong rate decisions. Detecting this divergence requires... comparing the model's predictions against actual outcomes across different rate configurations. Which is probing.

**The prediction:** Every design that eliminates the visible throughput cost of probing by importing external system knowledge will develop a *model recalibration problem* — a periodic need to validate the external model against live system behavior — that is structurally identical to probing, just deferred and renamed. The conservation law is not defeated by external telemetry; the cost migrates to the telemetry validation cycle. The law predicts this migration with precision: the information cost appears wherever the boundary between "what we know about the downstream system" and "what is currently true about the downstream system" is treated as stable when it is not.

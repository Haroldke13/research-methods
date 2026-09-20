"""Test selection and sample-size planning.

WRITTEN TO FILL A GAP, 2026-09-20. analysis.py imports two names:

    recommend_test(outcome_type=, predictor_type=, sparse_expected_counts=)
        -> an object, because the caller does `recommendation.to_dict()`
    estimate_two_group_sample_size(**study["sample_size"])
        -> called with effect_size, alpha, power, ratio from the study spec

WHY THIS IS SEPARATE FROM analysis.py
-------------------------------------
analysis.py runs whatever test it runs and reports the number. This module
records WHY that test was the right one, in a form that travels with the
result. In a methods framework the justification is the deliverable: a
p-value with no stated reason for the test behind it is not reviewable, and
a reviewer's first question is always "why this test and not another".

So every recommendation carries its assumptions and the alternative that
would apply if they failed, and analysis.py embeds that under
"recommended_method" alongside the figure it produced.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any

from scipy import stats

__all__ = ["TestRecommendation", "recommend_test",
           "estimate_two_group_sample_size"]


@dataclass(frozen=True)
class TestRecommendation:
    method: str
    rationale: str
    assumptions: tuple[str, ...] = ()
    alternative: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["assumptions"] = list(self.assumptions)
        return data


def recommend_test(*,
                   outcome_type: str,
                   predictor_type: str,
                   paired: bool = False,
                   sparse_expected_counts: bool = False,
                   normality_ok: bool = True,
                   equal_variance: bool = False) -> TestRecommendation:
    """Name the appropriate test, and say what it assumes.

    Only the combinations analysis.py can actually produce are enumerated;
    anything else returns an explicit "no recommendation" rather than a
    guess, because a wrong test name asserted confidently is worse than an
    absent one.
    """
    outcome = (outcome_type or "").lower()
    predictor = (predictor_type or "").lower()
    categorical = {"binary", "categorical"}

    # ── contingency: categorical outcome by categorical predictor ────────
    if outcome in categorical and predictor in categorical:
        if sparse_expected_counts and outcome == "binary" and predictor == "binary":
            return TestRecommendation(
                method="Fisher's exact test",
                rationale=("At least one expected cell count is below 5, so the "
                           "chi-squared approximation is unreliable on a 2x2 table."),
                assumptions=("Independent observations",
                             "Fixed margins interpretation of the odds ratio"),
                alternative="Chi-squared test once expected counts reach 5.",
            )
        if sparse_expected_counts:
            return TestRecommendation(
                method="Chi-squared test (sparse — interpret with caution)",
                rationale=("Expected counts below 5 are present but the table is "
                           "larger than 2x2, where Fisher's exact test is costly "
                           "and rarely reported."),
                assumptions=("Independent observations",
                             "Expected counts of at least 5 in most cells"),
                alternative="Collapse sparse categories, or use an exact test.",
            )
        return TestRecommendation(
            method="Chi-squared test of independence",
            rationale="Both variables are categorical and expected counts are adequate.",
            assumptions=("Independent observations",
                         "Expected count of at least 5 in each cell"),
            alternative="Fisher's exact test if expected counts fall below 5.",
        )

    # ── continuous outcome by categorical predictor ──────────────────────
    if outcome == "continuous" and predictor in categorical:
        if paired:
            return TestRecommendation(
                method="Paired t-test" if normality_ok else "Wilcoxon signed-rank test",
                rationale=("Observations are paired, so the within-pair difference "
                           "is the unit of analysis."),
                assumptions=(("Differences are approximately normal",)
                             if normality_ok else ("Differences are symmetric",)),
                alternative=("Wilcoxon signed-rank test" if normality_ok
                             else "Paired t-test if normality holds"),
            )
        if not normality_ok:
            return TestRecommendation(
                method="Mann-Whitney U test",
                rationale=("A normality check failed, so a rank-based comparison "
                           "avoids relying on the mean."),
                assumptions=("Independent groups",
                             "Similar distribution shape for a median interpretation"),
                alternative="Welch's t-test if the departure from normality is mild "
                            "and the sample is large.",
            )
        return TestRecommendation(
            method="Welch's t-test" if not equal_variance else "Student's t-test",
            rationale=("Two independent groups with an approximately normal "
                       "continuous outcome. Welch's is the default because equal "
                       "variance is an assumption worth not making."),
            assumptions=("Independent groups", "Approximately normal outcome"),
            alternative="Mann-Whitney U test if normality fails.",
        )

    # ── continuous by continuous ─────────────────────────────────────────
    if outcome == "continuous" and predictor == "continuous":
        return TestRecommendation(
            method="Pearson correlation" if normality_ok else "Spearman correlation",
            rationale="Both variables are continuous.",
            assumptions=(("Linear association", "Approximately normal margins")
                         if normality_ok else ("Monotonic association",)),
            alternative=("Spearman correlation" if normality_ok
                         else "Pearson correlation if normality holds"),
        )

    if outcome == "binary" and predictor == "continuous":
        return TestRecommendation(
            method="Logistic regression",
            rationale="A binary outcome modelled on a continuous predictor.",
            assumptions=("Independent observations",
                         "Linearity on the log-odds scale"),
            alternative="Categorise the predictor and use a chi-squared test, "
                        "accepting the loss of information.",
        )

    return TestRecommendation(
        method="No recommendation",
        rationale=(f"No rule is defined for outcome_type={outcome_type!r} with "
                   f"predictor_type={predictor_type!r}; state the choice manually."),
    )


def estimate_two_group_sample_size(effect_size: float,
                                   alpha: float = 0.05,
                                   power: float = 0.80,
                                   ratio: float = 1.0,
                                   two_sided: bool = True) -> dict[str, Any]:
    """Per-group n for comparing two means, from a standardised effect size.

    Normal approximation:

        n1 = (z(1-alpha/2) + z(power))^2 * (1 + 1/ratio) / d^2
        n2 = n1 * ratio

    Reported as the normal approximation on purpose: the exact
    noncentral-t solution differs by about one participant at conventional
    power, and quoting a figure to a precision the design assumptions do not
    support would be false confidence. The assumed effect size is echoed
    back because it, not the arithmetic, is what the number rests on.
    """
    if effect_size is None or float(effect_size) == 0:
        raise ValueError("effect_size must be non-zero to plan a sample size.")
    if not 0 < alpha < 1:
        raise ValueError("alpha must be between 0 and 1.")
    if not 0 < power < 1:
        raise ValueError("power must be between 0 and 1.")
    if ratio <= 0:
        raise ValueError("ratio must be positive.")

    d = abs(float(effect_size))
    z_alpha = stats.norm.ppf(1 - alpha / 2 if two_sided else 1 - alpha)
    z_beta = stats.norm.ppf(power)

    n1 = ((z_alpha + z_beta) ** 2) * (1 + 1 / ratio) / (d ** 2)
    n1 = int(math.ceil(n1))
    n2 = int(math.ceil(n1 * ratio))

    return {
        "method": "Normal approximation for a two-group comparison of means",
        "effect_size": d,
        "effect_size_label": "Cohen's d",
        "alpha": float(alpha),
        "power": float(power),
        "ratio": float(ratio),
        "sided": "two-sided" if two_sided else "one-sided",
        "n_group_1": n1,
        "n_group_2": n2,
        "n_total": n1 + n2,
        "note": ("Assumes the stated standardised effect is the smallest "
                 "difference worth detecting. Inflate for expected attrition; "
                 "this figure is analysable participants, not recruited ones."),
    }

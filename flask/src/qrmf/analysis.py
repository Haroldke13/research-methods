"""Executable statistical analysis engine for declared quantitative research plans."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm

from .methodology import estimate_two_group_sample_size, recommend_test
from .quality import assess_data_quality
from .reporting import write_json, write_markdown_report, write_summary_csv


def load_spec(spec: str | Path | dict[str, Any]) -> dict[str, Any]:
    if isinstance(spec, dict):
        return spec
    return json.loads(Path(spec).read_text(encoding="utf-8"))


def _complete(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    return df[cols].dropna().copy()


def _normal_enough(series: pd.Series, alpha: float) -> tuple[bool, float | None]:
    x = pd.to_numeric(series, errors="coerce").dropna()
    if len(x) < 3:
        return False, None
    if len(x) > 5000:
        x = x.sample(5000, random_state=2026)
    p = float(stats.shapiro(x).pvalue)
    return p >= alpha, p


def _hedges_g(a: np.ndarray, b: np.ndarray) -> float:
    n1, n2 = len(a), len(b)
    if n1 < 2 or n2 < 2:
        return float("nan")
    s1, s2 = np.var(a, ddof=1), np.var(b, ddof=1)
    pooled = math.sqrt(((n1 - 1) * s1 + (n2 - 1) * s2) / (n1 + n2 - 2))
    if pooled == 0:
        return 0.0
    d = (np.mean(a) - np.mean(b)) / pooled
    correction = 1 - (3 / (4 * (n1 + n2) - 9))
    return float(d * correction)


def _welch_ci(a: np.ndarray, b: np.ndarray, alpha: float) -> tuple[float, float, float]:
    mean_diff = float(np.mean(a) - np.mean(b))
    v1, v2 = np.var(a, ddof=1) / len(a), np.var(b, ddof=1) / len(b)
    se = math.sqrt(v1 + v2)
    if se == 0:
        return mean_diff, mean_diff, mean_diff
    df = (v1 + v2) ** 2 / ((v1**2) / (len(a) - 1) + (v2**2) / (len(b) - 1))
    tcrit = float(stats.t.ppf(1 - alpha / 2, df))
    return mean_diff, mean_diff - tcrit * se, mean_diff + tcrit * se


def _interpret(p: float, alpha: float, estimate_text: str) -> str:
    if p < alpha:
        return f"At alpha={alpha}, the analysis provides evidence against the null model; {estimate_text} Report the estimate and interval, not the p-value alone."
    return f"At alpha={alpha}, the analysis does not provide sufficient evidence to reject the null model; {estimate_text} Absence of statistical significance is not evidence of no meaningful effect."


def _group_difference(df: pd.DataFrame, job: dict[str, Any], alpha: float) -> dict[str, Any]:
    outcome, group = job["outcome"], job["group"]
    data = _complete(df, [outcome, group])
    levels = sorted(data[group].astype(str).unique().tolist())
    if len(levels) < 2:
        raise ValueError(f"{job['id']}: grouping variable must contain at least two observed groups")

    if len(levels) == 2:
        a = pd.to_numeric(data.loc[data[group].astype(str) == levels[0], outcome], errors="coerce").dropna().to_numpy()
        b = pd.to_numeric(data.loc[data[group].astype(str) == levels[1], outcome], errors="coerce").dropna().to_numpy()
        if min(len(a), len(b)) < 2:
            raise ValueError(f"{job['id']}: each group needs at least two usable observations")

        normal_a, shapiro_a = _normal_enough(pd.Series(a), alpha)
        normal_b, shapiro_b = _normal_enough(pd.Series(b), alpha)
        method_pref = job.get("method", "auto")
        use_parametric = method_pref == "welch_t" or (method_pref == "auto" and (normal_a and normal_b or min(len(a), len(b)) >= 30))

        if use_parametric:
            test = stats.ttest_ind(a, b, equal_var=False)
            estimate, low, high = _welch_ci(a, b, alpha)
            method = "Welch independent-samples t-test"
            stat = float(test.statistic)
            p = float(test.pvalue)
        else:
            test = stats.mannwhitneyu(a, b, alternative="two-sided")
            estimate = float(np.median(a) - np.median(b))
            low = high = float("nan")
            method = "Mann-Whitney U test"
            stat = float(test.statistic)
            p = float(test.pvalue)

        result = {
            "id": job["id"],
            "question": job.get("question", "Group difference"),
            "kind": "group_difference",
            "method": method,
            "n": int(len(a) + len(b)),
            "groups": {levels[0]: int(len(a)), levels[1]: int(len(b))},
            "group_summaries": {
                levels[0]: {"mean": float(np.mean(a)), "sd": float(np.std(a, ddof=1)), "median": float(np.median(a))},
                levels[1]: {"mean": float(np.mean(b)), "sd": float(np.std(b, ddof=1)), "median": float(np.median(b))},
            },
            "estimate": estimate,
            "confidence_interval_95": [low, high],
            "statistic": stat,
            "p_value": p,
            "effect_size": {"name": "Hedges g", "value": _hedges_g(a, b)},
            "assumption_checks": {
                "shapiro_p": {levels[0]: shapiro_a, levels[1]: shapiro_b},
                "normality_flag": {levels[0]: normal_a, levels[1]: normal_b},
                "note": "Normality tests are diagnostics, not automatic deletion or transformation rules.",
            },
        }
        direction = f"the {levels[0]} minus {levels[1]} location estimate is {estimate:.3f}."
        result["interpretation"] = _interpret(p, alpha, direction)
        return result

    arrays = [
        pd.to_numeric(data.loc[data[group].astype(str) == level, outcome], errors="coerce").dropna().to_numpy()
        for level in levels
    ]
    if any(len(x) < 2 for x in arrays):
        raise ValueError(f"{job['id']}: each group needs at least two usable observations")
    test = stats.kruskal(*arrays)
    p = float(test.pvalue)
    return {
        "id": job["id"],
        "question": job.get("question", "Group difference"),
        "kind": "group_difference",
        "method": "Kruskal-Wallis test",
        "n": int(sum(len(x) for x in arrays)),
        "statistic": float(test.statistic),
        "p_value": p,
        "interpretation": _interpret(p, alpha, "At least one group distribution may differ if the null is rejected."),
    }


def _association(df: pd.DataFrame, job: dict[str, Any], alpha: float) -> dict[str, Any]:
    x, y = job["x"], job["y"]
    data = _complete(df, [x, y])
    x_type = job.get("x_type", "categorical")
    y_type = job.get("y_type", "categorical")

    if x_type == "continuous" and y_type == "continuous":
        a = pd.to_numeric(data[x], errors="coerce")
        b = pd.to_numeric(data[y], errors="coerce")
        valid = a.notna() & b.notna()
        a, b = a[valid], b[valid]
        method_pref = job.get("method", "auto")
        normal = _normal_enough(a, alpha)[0] and _normal_enough(b, alpha)[0]
        if method_pref == "spearman" or (method_pref == "auto" and not normal):
            test = stats.spearmanr(a, b)
            method = "Spearman rank correlation"
        else:
            test = stats.pearsonr(a, b)
            method = "Pearson correlation"
        p = float(test.pvalue)
        r = float(test.statistic)
        return {
            "id": job["id"],
            "question": job.get("question", "Association"),
            "kind": "association",
            "method": method,
            "n": int(len(a)),
            "estimate": r,
            "statistic": r,
            "p_value": p,
            "effect_size": {"name": "correlation", "value": r},
            "interpretation": _interpret(p, alpha, f"The estimated monotonic/linear association is {r:.3f}."),
        }

    table = pd.crosstab(data[x], data[y])
    chi2, chi_p, dof, expected = stats.chi2_contingency(table)
    sparse = bool((expected < 5).any())
    recommendation = recommend_test(
        outcome_type="binary" if table.shape[1] == 2 else "categorical",
        predictor_type="binary" if table.shape[0] == 2 else "categorical",
        sparse_expected_counts=sparse,
    )
    if table.shape == (2, 2) and sparse:
        odds_ratio, p = stats.fisher_exact(table.to_numpy())
        method = "Fisher's exact test"
        statistic = float(odds_ratio)
        estimate = float(odds_ratio)
        effect = {"name": "odds ratio", "value": float(odds_ratio)}
    else:
        p = float(chi_p)
        method = "Pearson chi-square test of independence"
        statistic = float(chi2)
        n = table.to_numpy().sum()
        denom = max(1, min(table.shape[0] - 1, table.shape[1] - 1))
        cramers_v = math.sqrt(float(chi2) / (float(n) * denom))
        estimate = cramers_v
        effect = {"name": "Cramer's V", "value": cramers_v}

    return {
        "id": job["id"],
        "question": job.get("question", "Association"),
        "kind": "association",
        "method": method,
        "recommended_method": recommendation.to_dict(),
        "n": int(len(data)),
        "estimate": estimate,
        "statistic": statistic,
        "p_value": float(p),
        "effect_size": effect,
        "contingency_table": table.astype(int).to_dict(),
        "expected_count_min": float(np.min(expected)),
        "interpretation": _interpret(float(p), alpha, "Association does not by itself establish causation."),
    }


def _prepare_model_matrix(data: pd.DataFrame, predictors: list[str]) -> pd.DataFrame:
    x = pd.get_dummies(data[predictors], drop_first=True, dtype=float)
    for col in x.columns:
        x[col] = pd.to_numeric(x[col], errors="coerce")
    return sm.add_constant(x, has_constant="add")


def _linear_regression(df: pd.DataFrame, job: dict[str, Any], alpha: float) -> dict[str, Any]:
    outcome = job["outcome"]
    predictors = job["predictors"]
    data = _complete(df, [outcome, *predictors])
    y = pd.to_numeric(data[outcome], errors="coerce")
    x = _prepare_model_matrix(data, predictors)
    valid = y.notna() & x.notna().all(axis=1)
    y, x = y.loc[valid], x.loc[valid]
    if len(y) <= x.shape[1]:
        raise ValueError(f"{job['id']}: insufficient complete observations for regression")
    fit = sm.OLS(y, x).fit(cov_type="HC3")
    ci = fit.conf_int(alpha=alpha)
    coefficients = {
        name: {
            "estimate": float(fit.params[name]),
            "std_error_hc3": float(fit.bse[name]),
            "p_value": float(fit.pvalues[name]),
            "ci_low": float(ci.loc[name, 0]),
            "ci_high": float(ci.loc[name, 1]),
        }
        for name in x.columns
    }
    return {
        "id": job["id"],
        "question": job.get("question", "Adjusted continuous-outcome model"),
        "kind": "linear_regression",
        "method": "OLS multiple linear regression with HC3 robust standard errors",
        "n": int(fit.nobs),
        "coefficients": coefficients,
        "model_fit": {"r_squared": float(fit.rsquared), "adjusted_r_squared": float(fit.rsquared_adj)},
        "interpretation": "Coefficients are conditional associations given the included covariates. Causal interpretation requires a design/identification argument beyond regression adjustment.",
    }


def _logistic_regression(df: pd.DataFrame, job: dict[str, Any], alpha: float) -> dict[str, Any]:
    outcome = job["outcome"]
    predictors = job["predictors"]
    data = _complete(df, [outcome, *predictors])
    y = pd.to_numeric(data[outcome], errors="coerce")
    if not set(y.dropna().unique()).issubset({0, 1}):
        raise ValueError(f"{job['id']}: logistic outcome must be coded 0/1")
    x = _prepare_model_matrix(data, predictors)
    valid = y.notna() & x.notna().all(axis=1)
    y, x = y.loc[valid], x.loc[valid]
    fit = sm.Logit(y, x).fit(disp=False)
    ci = fit.conf_int(alpha=alpha)
    coefficients = {
        name: {
            "log_odds": float(fit.params[name]),
            "odds_ratio": float(np.exp(fit.params[name])),
            "p_value": float(fit.pvalues[name]),
            "or_ci_low": float(np.exp(ci.loc[name, 0])),
            "or_ci_high": float(np.exp(ci.loc[name, 1])),
        }
        for name in x.columns
    }
    return {
        "id": job["id"],
        "question": job.get("question", "Adjusted binary-outcome model"),
        "kind": "logistic_regression",
        "method": "Binary logistic regression",
        "n": int(fit.nobs),
        "coefficients": coefficients,
        "model_fit": {"pseudo_r_squared_mcfadden": float(fit.prsquared), "aic": float(fit.aic)},
        "interpretation": "Odds ratios are adjusted associations conditional on model specification; they do not alone establish causation.",
    }


def _plot_primary(df: pd.DataFrame, spec: dict[str, Any], output_dir: Path) -> str | None:
    primary = next((x for x in spec.get("analyses", []) if x.get("kind") == "group_difference"), None)
    if not primary:
        return None
    outcome, group = primary["outcome"], primary["group"]
    data = _complete(df, [outcome, group])
    levels = sorted(data[group].astype(str).unique())
    arrays = [pd.to_numeric(data.loc[data[group].astype(str) == level, outcome], errors="coerce").dropna() for level in levels]
    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    ax.boxplot(arrays, tick_labels=levels, showmeans=True)
    ax.set_title(f"{outcome} by {group}")
    ax.set_xlabel(group)
    ax.set_ylabel(outcome)
    fig.tight_layout()
    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    target = figure_dir / "outcome_by_group.png"
    fig.savefig(target, dpi=150)
    plt.close(fig)
    return str(target.name)


def run_analysis(
    data_path: str | Path,
    spec: str | Path | dict[str, Any],
    output_dir: str | Path,
) -> dict[str, Any]:
    """Run a declared analysis plan and write JSON/Markdown/CSV evidence artifacts."""
    data_path = Path(data_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    study = load_spec(spec)
    df = pd.read_csv(data_path)
    alpha = float(study.get("alpha", 0.05))

    quality = assess_data_quality(df, study)
    results: list[dict[str, Any]] = []
    for job in study.get("analyses", []):
        kind = job.get("kind")
        if kind == "group_difference":
            results.append(_group_difference(df, job, alpha))
        elif kind == "association":
            results.append(_association(df, job, alpha))
        elif kind == "linear_regression":
            results.append(_linear_regression(df, job, alpha))
        elif kind == "logistic_regression":
            results.append(_logistic_regression(df, job, alpha))
        else:
            raise ValueError(f"Unknown analysis kind: {kind}")

    sample_size_plan = None
    if study.get("sample_size"):
        sample_size_plan = estimate_two_group_sample_size(**study["sample_size"])

    result: dict[str, Any] = {
        "study": study,
        "input": {"data_file": data_path.name, "rows": int(len(df))},
        "quality": quality,
        "sample_size_plan": sample_size_plan,
        "analyses": results,
        "figure": _plot_primary(df, study, output_dir),
    }
    write_json(result, output_dir / "analysis_results.json")
    write_markdown_report(result, output_dir / "analysis_report.md")
    write_summary_csv(result, output_dir / "analysis_summary.csv")
    return result
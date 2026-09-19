import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from qrmf.analysis import run_analysis


def _fixture_df(seed=7):
    rng = np.random.default_rng(seed)
    n = 80
    group = np.array(["control"] * 40 + ["intervention"] * 40)
    baseline = rng.normal(50, 8, n)
    age = rng.integers(20, 60, n)
    y = 15 + 0.6 * baseline - 0.05 * age + (group == "intervention") * 5 + rng.normal(0, 5, n)
    responder = (y > np.median(y)).astype(int)
    return pd.DataFrame({
        "participant_id": [f"p{i}" for i in range(n)],
        "group": group,
        "age": age,
        "baseline_score": baseline,
        "outcome_score": y,
        "responder": responder,
    })


def _spec():
    return {
        "title": "test",
        "research_question": "test question",
        "id_column": "participant_id",
        "alpha": 0.05,
        "sample_size": {"effect_size": 0.5, "alpha": 0.05, "power": 0.8, "ratio": 1},
        "analyses": [
            {"id": "primary", "kind": "group_difference", "outcome": "outcome_score", "group": "group", "method": "welch_t"},
            {"id": "response", "kind": "association", "x": "group", "y": "responder", "x_type": "categorical", "y_type": "binary"},
            {"id": "adjusted", "kind": "linear_regression", "outcome": "outcome_score", "predictors": ["group", "baseline_score", "age"]},
        ],
    }


def test_end_to_end_analysis_writes_evidence(tmp_path: Path):
    data_path = tmp_path / "data.csv"
    _fixture_df().to_csv(data_path, index=False)
    out = tmp_path / "out"
    result = run_analysis(data_path, _spec(), out)
    assert len(result["analyses"]) == 3
    assert result["quality"]["quality_gate_passed"] is True
    assert (out / "analysis_results.json").is_file()
    assert (out / "analysis_report.md").is_file()
    assert (out / "analysis_summary.csv").is_file()
    payload = json.loads((out / "analysis_results.json").read_text())
    assert payload["analyses"][0]["method"] == "Welch independent-samples t-test"
    assert payload["sample_size_plan"]["total_n"] == 128


def test_missing_analysis_column_fails_cleanly(tmp_path: Path):
    df = _fixture_df().drop(columns=["outcome_score"])
    data_path = tmp_path / "bad.csv"
    df.to_csv(data_path, index=False)
    with pytest.raises(ValueError, match="outcome_score"):
        run_analysis(data_path, _spec(), tmp_path / "out")


def test_unknown_analysis_kind_fails(tmp_path: Path):
    data_path = tmp_path / "data.csv"
    _fixture_df().to_csv(data_path, index=False)
    spec = _spec()
    spec["analyses"] = [{"id": "x", "kind": "survival"}]
    with pytest.raises(ValueError, match="Unknown analysis kind"):
        run_analysis(data_path, spec, tmp_path / "out")


def test_logistic_regression_runs_with_binary_outcome(tmp_path: Path):
    data_path = tmp_path / "data.csv"
    _fixture_df().to_csv(data_path, index=False)
    spec = _spec()
    spec["analyses"] = [{
        "id": "logit",
        "kind": "logistic_regression",
        "outcome": "responder",
        "predictors": ["group", "baseline_score", "age"],
    }]
    result = run_analysis(data_path, spec, tmp_path / "out")
    model = result["analyses"][0]
    assert model["method"] == "Binary logistic regression"
    assert "group_intervention" in model["coefficients"]
    assert model["coefficients"]["group_intervention"]["odds_ratio"] > 0


def test_logistic_rejects_non_binary_outcome(tmp_path: Path):
    df = _fixture_df()
    df.loc[0, "responder"] = 2
    data_path = tmp_path / "bad_binary.csv"
    df.to_csv(data_path, index=False)
    spec = _spec()
    spec["analyses"] = [{
        "id": "logit",
        "kind": "logistic_regression",
        "outcome": "responder",
        "predictors": ["group", "baseline_score"],
    }]
    with pytest.raises(ValueError, match="coded 0/1"):
        run_analysis(data_path, spec, tmp_path / "out")
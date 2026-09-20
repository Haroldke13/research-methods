"""Data-quality assessment, run before any test is applied.

WRITTEN TO FILL A GAP, 2026-09-20. analysis.py calls
`assess_data_quality(df, study)` once, before the analyses, and embeds the
returned mapping under result["quality"].

WHY IT RUNS FIRST AND WHY IT ONLY REPORTS
-----------------------------------------
Every finding downstream is conditional on the data being what the spec
says it is. Duplicated participant ids inflate significance; a column that
is constant cannot be a predictor; 40% missingness under complete-case
analysis silently changes who the result is about.

It reports and does not mutate. Dropping or imputing rows here would change
the analysis set invisibly, and the spec's own missing_policy is what
decides that. Flags, not fixes.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

__all__ = ["assess_data_quality", "MISSING_WARN", "MISSING_ALERT"]

MISSING_WARN = 0.05      # 5% missing in a column is worth a mention
MISSING_ALERT = 0.20     # 20% changes who the conclusion is about


def _columns_used(study: dict[str, Any]) -> list[str]:
    """Only the columns the spec actually analyses; unused columns are noise."""
    used: list[str] = []
    for job in study.get("analyses", []) or []:
        for key in ("outcome", "group", "x", "y"):
            value = job.get(key)
            if isinstance(value, str):
                used.append(value)
        for predictor in job.get("predictors", []) or []:
            if isinstance(predictor, str):
                used.append(predictor)
    id_column = study.get("id_column")
    if isinstance(id_column, str):
        used.append(id_column)
    seen: set[str] = set()
    return [c for c in used if not (c in seen or seen.add(c))]


def assess_data_quality(df: pd.DataFrame, study: dict[str, Any]) -> dict[str, Any]:
    rows = int(len(df))
    findings: list[str] = []

    declared = _columns_used(study)
    missing_columns = [c for c in declared if c not in df.columns]
    if missing_columns:
        findings.append(
            "Columns named in the study spec are absent from the data: "
            + ", ".join(missing_columns)
        )

    present = [c for c in declared if c in df.columns]
    missingness: dict[str, dict[str, Any]] = {}
    for column in present:
        n_missing = int(df[column].isna().sum())
        share = (n_missing / rows) if rows else 0.0
        missingness[column] = {
            "missing": n_missing,
            "share": round(share, 4),
            "level": ("alert" if share >= MISSING_ALERT
                      else "warn" if share >= MISSING_WARN else "ok"),
        }
        if share >= MISSING_ALERT:
            findings.append(
                f"{column} is {share:.0%} missing. Under "
                f"{study.get('missing_policy', 'complete-case')} analysis the "
                f"result describes the subset with data, which may not be the "
                f"population of interest."
            )
        elif share >= MISSING_WARN:
            findings.append(f"{column} is {share:.0%} missing.")

    # Duplicate identifiers: the failure that most often inflates significance,
    # because it silently doubles the apparent sample.
    duplicate_ids = 0
    id_column = study.get("id_column")
    if isinstance(id_column, str) and id_column in df.columns:
        duplicate_ids = int(df[id_column].duplicated().sum())
        if duplicate_ids:
            findings.append(
                f"{duplicate_ids} duplicated value(s) in {id_column}. Each row "
                f"is assumed to be one independent participant; duplicates break "
                f"that and narrow every confidence interval."
            )

    constant_columns = [c for c in present if df[c].nunique(dropna=True) <= 1]
    if constant_columns:
        findings.append(
            "Constant column(s) carry no information and cannot act as a "
            "predictor: " + ", ".join(constant_columns)
        )

    complete_case_rows = int(df[present].dropna().shape[0]) if present else rows

    return {
        "rows": rows,
        "columns": int(df.shape[1]),
        "columns_analysed": present,
        "columns_missing_from_data": missing_columns,
        "missingness": missingness,
        "duplicate_ids": duplicate_ids,
        "constant_columns": constant_columns,
        "complete_case_rows": complete_case_rows,
        "complete_case_share": round(complete_case_rows / rows, 4) if rows else 0.0,
        "findings": findings,
        "clean": not findings,
    }

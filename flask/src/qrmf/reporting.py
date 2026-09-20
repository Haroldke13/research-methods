"""Writing the analysis out: JSON, Markdown and a summary CSV.

WRITTEN TO FILL A GAP, 2026-09-20. analysis.py calls three writers at the
end of run_analysis, each taking (result, path).

The three formats exist for three readers, which is why none of them is
dropped: JSON for the API route and any re-analysis, Markdown for the
human write-up, CSV for the one-row-per-analysis table that goes into a
supervisor's spreadsheet.

Every format carries the data-quality findings. A results table that omits
"18% of the outcome column was missing" is not a shorter report, it is a
different and more flattering one.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

__all__ = ["write_json", "write_markdown_report", "write_summary_csv",
           "SUMMARY_COLUMNS"]

SUMMARY_COLUMNS = ("id", "question", "kind", "method", "n", "estimate",
                   "ci_low", "ci_high", "statistic", "p_value",
                   "effect_size_name", "effect_size_value", "interpretation")


def _plain(value: Any) -> Any:
    """Make numpy/pandas scalars JSON-safe, and NaN explicit.

    json.dumps(float('nan')) emits a bare NaN, which is invalid JSON and
    which the browser's JSON.parse rejects - so the API route would return
    200 with a body no client could read. Null is the honest encoding of a
    statistic that does not exist.
    """
    if value is None:
        return None
    if isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return None if (math.isnan(value) or math.isinf(value)) else value
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    for attr in ("item", "tolist"):          # numpy scalars and arrays
        if hasattr(value, attr):
            try:
                return _plain(getattr(value, attr)())
            except Exception:
                break
    return str(value)


def write_json(result: dict[str, Any], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(_plain(result), indent=2), encoding="utf-8")
    return target


def _fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return "—"
        if 0 < abs(value) < 1e-4:
            return f"{value:.2e}"
        return f"{value:.{digits}g}"
    return str(value)


def write_markdown_report(result: dict[str, Any], path: str | Path) -> Path:
    study = result.get("study", {}) or {}
    quality = result.get("quality", {}) or {}
    out: list[str] = []
    add = out.append

    add(f"# {study.get('title', 'Analysis report')}")
    add("")
    add("> Synthetic practice data. Not a finding about any real population.")
    add("")
    if study.get("research_question"):
        add(f"**Research question.** {study['research_question']}")
        add("")
    for label, key in (("Design", "design"), ("Alpha", "alpha"),
                       ("Missing-data policy", "missing_policy"),
                       ("Multiplicity", "multiplicity_policy")):
        if study.get(key):
            add(f"- **{label}:** {study[key]}")
    source = result.get("input", {}) or {}
    add(f"- **Data:** {source.get('data_file', '—')} "
        f"({source.get('rows', '—')} rows)")
    add("")

    add("## Data quality")
    if quality.get("clean"):
        add("No data-quality findings.")
    else:
        for finding in quality.get("findings", []):
            add(f"- {finding}")
    add("")
    add(f"Complete cases across analysed columns: "
        f"{quality.get('complete_case_rows', '—')} of {quality.get('rows', '—')}.")
    add("")

    plan = result.get("sample_size_plan")
    if plan:
        add("## Sample-size plan")
        add(f"{plan.get('n_group_1', '—')} and {plan.get('n_group_2', '—')} "
            f"participants ({plan.get('n_total', '—')} total) for "
            f"{plan.get('effect_size_label', 'effect')} = "
            f"{plan.get('effect_size', '—')} at {plan.get('power', '—')} power, "
            f"alpha {plan.get('alpha', '—')}, {plan.get('sided', '')}.")
        if plan.get("note"):
            add("")
            add(f"*{plan['note']}*")
        add("")

    add("## Analyses")
    for item in result.get("analyses", []) or []:
        add("")
        add(f"### {item.get('id', 'analysis')}")
        if item.get("question"):
            add(f"*{item['question']}*")
            add("")
        add(f"- **Method:** {item.get('method', '—')}")
        add(f"- **n:** {_fmt(item.get('n'))}")
        if item.get("estimate") is not None:
            ci = ""
            if item.get("ci_low") is not None and item.get("ci_high") is not None:
                ci = f" (95% CI {_fmt(item['ci_low'])} to {_fmt(item['ci_high'])})"
            add(f"- **Estimate:** {_fmt(item['estimate'])}{ci}")
        add(f"- **Statistic:** {_fmt(item.get('statistic'))}")
        add(f"- **p:** {_fmt(item.get('p_value'))}")
        effect = item.get("effect_size") or {}
        if effect:
            add(f"- **Effect size:** {effect.get('name', '—')} = "
                f"{_fmt(effect.get('value'))}")
        recommended = item.get("recommended_method") or {}
        if recommended:
            add(f"- **Why this test:** {recommended.get('rationale', '—')}")
            if recommended.get("assumptions"):
                add(f"- **Assumes:** {'; '.join(recommended['assumptions'])}")
            if recommended.get("alternative"):
                add(f"- **Otherwise:** {recommended['alternative']}")
        checks = item.get("assumption_checks") or {}
        if checks:
            add(f"- **Assumption checks:** " +
                ", ".join(f"{k}={_fmt(v)}" for k, v in checks.items()))
        if item.get("interpretation"):
            add("")
            add(item["interpretation"])

    if result.get("figure"):
        add("")
        add("## Figure")
        add(f"![Primary comparison]({Path(str(result['figure'])).name})")
    add("")

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(out), encoding="utf-8")
    return target


def write_summary_csv(result: dict[str, Any], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(SUMMARY_COLUMNS)
        for item in result.get("analyses", []) or []:
            effect = item.get("effect_size") or {}
            row = {
                "id": item.get("id", ""),
                "question": item.get("question", ""),
                "kind": item.get("kind", ""),
                "method": item.get("method", ""),
                "n": item.get("n"),
                "estimate": item.get("estimate"),
                "ci_low": item.get("ci_low"),
                "ci_high": item.get("ci_high"),
                "statistic": item.get("statistic"),
                "p_value": item.get("p_value"),
                "effect_size_name": effect.get("name", ""),
                "effect_size_value": effect.get("value"),
                "interpretation": item.get("interpretation", ""),
            }
            writer.writerow([_fmt(_plain(row[c])) if isinstance(row[c], float)
                             else ("" if row[c] is None else _plain(row[c]))
                             for c in SUMMARY_COLUMNS])
    return target

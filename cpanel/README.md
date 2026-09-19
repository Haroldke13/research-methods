# Quantitative Research Methodology Framework

A GitHub-ready Python/Flask project for quantitative research design support, data-quality validation, statistical testing, effect estimation, interpretation, and reproducible academic reporting.

## What it solves

The project addresses a practical research-methodology gap: a research question must be translated into a defensible analysis plan, then executed consistently and reported without disconnects between the design, statistical code, and narrative output.

It provides:

- a documented methodology framework;
- a transparent statistical-test recommendation utility;
- two-group sample-size planning;
- required-column, duplicate, missingness, and outlier diagnostics;
- executable group comparisons, categorical association, correlation, linear regression, and logistic regression;
- effect sizes, confidence intervals, p-values, and model diagnostics;
- JSON, CSV, Markdown, and figure outputs generated from one run;
- a Flask frontend for current evidence plus local CSV/spec analysis;
- seeded synthetic demo data generated with Faker/NumPy;
- automated tests and repository validation;
- portfolio and client-handoff documentation.

## Evidence status

`data/demo_study.csv` is **synthetic** and generated from `scripts/generate_demo_data.py`. It contains no real participant information. Numerical findings in `outputs/` demonstrate the software workflow only and must not be presented as field, clinical, program, or client results.

## Repository structure

```text
.
├── app.py
├── requirements.txt
├── .env.example
├── data/
│   ├── demo_study.csv
│   └── demo_study_spec.json
├── docs/
│   ├── ANALYSIS_DECISION_LOG_TEMPLATE.md
│   ├── QA_AND_REPRODUCIBILITY.md
│   └── QUANTITATIVE_RESEARCH_FRAMEWORK.md
├── outputs/
│   ├── analysis_report.md
│   ├── analysis_results.json
│   ├── analysis_summary.csv
│   └── figures/outcome_by_group.png
├── portfolio/
│   ├── CASE_STUDY.md
│   ├── CLIENT_HANDOFF.md
│   ├── PROJECT_SUMMARY.md
│   ├── RESULTS.md
│   └── TECHNICAL_OVERVIEW.md
├── scripts/
│   ├── generate_demo_data.py
│   ├── run_demo.py
│   └── validate_repo.py
├── src/qrmf/
│   ├── __init__.py
│   ├── analysis.py
│   ├── methodology.py
│   ├── quality.py
│   └── reporting.py
├── static/css/styles.css
├── templates/
│   ├── analyze.html
│   ├── base.html
│   ├── error.html
│   ├── index.html
│   └── run_result.html
└── tests/
    ├── conftest.py
    ├── test_analysis.py
    ├── test_app.py
    ├── test_methodology.py
    └── test_quality.py
```

## Prerequisites

- Python 3.10+
- pip

No external API or paid service is required.

## Installation

```bash
git clone <repository-url>
cd quant_research_methodology_framework
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env          # Windows PowerShell: Copy-Item .env.example .env
```

Set a local `SECRET_KEY` before using the upload interface beyond a throwaway development session.

## Reproduce the demo

```bash
python scripts/run_demo.py
```

This regenerates the deterministic synthetic CSV and then writes:

- `outputs/analysis_results.json`
- `outputs/analysis_report.md`
- `outputs/analysis_summary.csv`
- `outputs/figures/outcome_by_group.png`

## Run tests

```bash
pytest -q
```

Core statistical tests require pandas, NumPy, SciPy, statsmodels, Matplotlib, Faker, and pytest. Flask-specific route tests use `pytest.importorskip("flask")`, so they are skipped rather than reported as passed when Flask is unavailable.

## Validate repository consistency

```bash
python scripts/validate_repo.py
```

This checks required repository paths and parses project Python/JSON files for syntax validity.

## Run the Flask application

```bash
python app.py
```

Open `http://127.0.0.1:5000`.

The home page displays the actual generated evidence in `outputs/`. The **Analyze CSV** page accepts a CSV and a JSON study specification. Each uploaded run is stored under `runtime/<run_id>/`; `runtime/` is ignored by Git, and the result page provides a deletion action.

## Input expectations

The analysis engine reads ordinary CSV files. The JSON study specification declares required variables and analyses. Supported job kinds are:

- `group_difference`
- `association`
- `linear_regression`
- `logistic_regression`

See `data/demo_study_spec.json` for a complete working example.

### Example group comparison

```json
{
  "id": "primary_group_difference",
  "kind": "group_difference",
  "outcome": "outcome_score",
  "group": "group",
  "method": "auto"
}
```

### Example adjusted model

```json
{
  "id": "adjusted_outcome_model",
  "kind": "linear_regression",
  "outcome": "outcome_score",
  "predictors": ["group", "baseline_score", "age"]
}
```

## Statistical interpretation

The implementation deliberately separates statistical evidence from causal claims. Observational regressions are reported as adjusted associations. P-values are accompanied by effect estimates/intervals where implemented, and non-significance is not translated into “no effect.”

See `docs/QUANTITATIVE_RESEARCH_FRAMEWORK.md` for the complete decision framework.

## Data protection and retention

The demo data are synthetic. For client/confidential data, deploy only in an environment approved for the relevant data classification. The development Flask app is local-first and does not transmit uploads to an external API. Uploaded runs remain in `runtime/` until the user deletes them; production deployments should add authentication, encryption, audit logs, and an automated retention policy.

## Limitations

This repository does not yet implement:

- multilevel/mixed-effects models;
- complex survey design weights/strata/PSUs;
- survival/time-to-event models;
- longitudinal repeated-measures models;
- multiple imputation;
- equivalence/non-inferiority testing;
- causal estimators such as IPW/g-formula/matching;
- Bayesian workflows;
- automated APA/journal-specific document formatting.

Those are study-design extensions, not safe assumptions to add without the client's protocol and data structure.

## Deployment considerations

For internal production deployment:

- run Flask behind a production WSGI server and reverse proxy;
- disable debug mode;
- use a strong secret key;
- authenticate users;
- enforce upload limits and approved MIME/content scanning;
- move runtime data to encrypted managed storage if persistence is required;
- add scheduled retention/deletion;
- capture package versions in a lockfile or container image;
- validate statistical methods against the final protocol before publication.

## License

The repository includes an MIT license for the generated code. If delivered under a client contract with different IP terms, replace the license before publication or handoff.
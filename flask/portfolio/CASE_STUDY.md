# Case Study — Reproducible Quantitative Research Methodology

## Problem

A research client needs more than a list of statistical tests. They need a defensible framework connecting research design, data validation, statistical testing, interpretation, and academic reporting, while keeping the workflow reproducible enough for review.

## Approach

The project implements a JSON-based study specification and a Python analysis engine. The specification captures the research question, design controls, alpha, missing-data policy, sample-size parameters, and named analyses. Before inference, the engine verifies required columns and reports duplicate IDs, missingness, and numerical outlier flags. It then executes the declared methods and writes a single evidence object that feeds JSON, CSV, Markdown, a diagnostic figure, and the Flask interface.

The bundled demonstration uses 180 seeded synthetic records. The primary analysis is an independent two-group outcome comparison, accompanied by a categorical responder analysis and an adjusted linear regression with HC3 robust standard errors. A conventional two-group power calculation for Cohen's d=0.50, alpha=.05, 80% power yields a planning target of 64 participants per group (128 total) before attrition or design-effect inflation. That number is produced by the implemented calculation and is not a client outcome.

## Demonstration results produced by the repository

The reproducible synthetic run generated 180 rows, with 3 intentionally missing follow-up outcomes, leaving 177 complete cases for the primary continuous outcome analyses. The primary Welch comparison estimated control minus intervention at **-6.6962 points** (95% CI **-9.3402 to -4.0523**), with **Hedges' g=-0.7472** and **p=1.40e-06**. The responder association produced **Cramer's V=0.1218, p=0.1022**. In the HC3-adjusted linear model, the intervention indicator coefficient was **5.9220 points** (95% CI **3.9178 to 7.9262**, p=6.98e-09), with model **R²=0.5077**. These values are generated evidence from synthetic data only; they are not client or population findings.

## Quality controls

The workflow separates declared design decisions from observed results, labels synthetic evidence, exposes assumption diagnostics, includes effect sizes and confidence intervals, and fails explicitly when required columns or analysis kinds are invalid. Runtime Flask uploads are isolated from Git-tracked data and can be deleted per run.

## Validation

Automated tests cover test-selection logic, power planning, data-quality failures, end-to-end artifact generation, missing-column failures, and unsupported analysis kinds. Flask route tests are included and run when Flask is installed. Repository validation checks required paths and parses Python/JSON syntax.

## Honest limits

This version does not implement multilevel/mixed models, complex survey weighting, survival analysis, repeated-measures models, multiple imputation, causal estimators, equivalence/non-inferiority designs, or automated journal-specific formatting. Those should be added only when required by the client's actual study design. The demonstration does not claim real-world efficacy or client impact because its data are synthetic.
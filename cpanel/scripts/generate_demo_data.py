#!/usr/bin/env python3
"""Generate a deterministic synthetic dataset for demonstration and tests."""

from pathlib import Path
import sys

import numpy as np
import pandas as pd
from faker import Faker

ROOT = Path(__file__).resolve().parents[1]


def generate(n: int = 180, seed: int = 20260918) -> pd.DataFrame:
    fake = Faker()
    fake.seed_instance(seed)
    rng = np.random.default_rng(seed)

    group = rng.choice(["control", "intervention"], size=n, p=[0.5, 0.5])
    age = np.clip(rng.normal(35, 9, size=n).round(), 18, 65).astype(int)
    baseline = rng.normal(50, 10, size=n)
    site = rng.choice(["Site A", "Site B", "Site C"], size=n, p=[0.4, 0.35, 0.25])
    treatment_effect = np.where(group == "intervention", 5.0, 0.0)
    outcome = 18 + 0.58 * baseline - 0.08 * age + treatment_effect + rng.normal(0, 7, size=n)
    logit = -3.1 + 0.06 * outcome + np.where(group == "intervention", 0.35, 0)
    prob = 1 / (1 + np.exp(-logit))
    responder = rng.binomial(1, prob)

    df = pd.DataFrame(
        {
            "participant_id": [f"SYN-{fake.unique.random_int(min=100000, max=999999)}" for _ in range(n)],
            "group": group,
            "age": age,
            "site": site,
            "baseline_score": baseline.round(2),
            "outcome_score": outcome.round(2),
            "responder": responder,
        }
    )

    # Deliberately introduce a small amount of missingness to exercise the declared
    # complete-case workflow. No real person is represented.
    miss_idx = rng.choice(df.index, size=max(3, n // 50), replace=False)
    df.loc[miss_idx, "outcome_score"] = np.nan
    return df


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "demo_study.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    df = generate()
    df.to_csv(target, index=False)
    print(f"Wrote {len(df)} synthetic rows to {target}")


if __name__ == "__main__":
    main()
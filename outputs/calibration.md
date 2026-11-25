# Calibration against a known zero effect

Each of 1,000 independently simulated cohorts has 100 surgeries per mesh. MESH-A has 25 high-risk patients and MESH-B has 75. Low-risk patients have a 10% 365-day recurrence probability and high-risk patients have a 30% probability with either mesh. The true within-risk and standardized mesh effects are both zero. The different risk mixes produce an expected crude B minus A difference of +10 percentage points.

Each cohort is analyzed twice. First every outcome is observed. Then 50% of MESH-B recurrences and 90% of all other cases are observed in expectation. This second analysis uses cases with observed outcomes and recalculates pooled risk weights from retained cases. Both analyses use the main estimator’s minimum of five cases per mesh in each retained stratum.

| Follow-up | Mean crude B − A | Mean adjusted B − A (bias vs zero) | Monte Carlo SE of adjusted mean |
|---|---:|---:|---:|
| Complete | +10.04 pp | +0.03 pp | 0.20 pp |
| Outcome-dependent | +0.71 pp | -7.23 pp | 0.19 pp |

Risk adjustment can correct the engineered case-mix imbalance. When ascertainment selects against recurrences in one mesh, adjustment for preoperative risk leaves selection bias. The Monte Carlo standard error measures variability of the simulated mean across repetitions. The observation probabilities here are assumptions chosen to illustrate the mechanism.

Run `python3 -m examples.calibration` from the repository root (seed 314159).

"""Calibrate standardized recurrence differences against a simulated null effect."""

from collections import defaultdict
from random import Random
from math import sqrt
from statistics import mean, stdev

from surgical.analysis import pooled_strata, standardized_means

SEED = 314159
REPETITIONS = 1_000
# Stratum, operation counts (A, B), and true event probability under *either* mesh.
RISK_MIX = (("low", (75, 25), 0.10), ("high", (25, 75), 0.30))


def simulate(rng: Random):
    complete = defaultdict(lambda: ([], []))
    observed = defaultdict(lambda: ([], []))
    for risk, counts, probability in RISK_MIX:
        for arm, n in enumerate(counts):
            for _ in range(n):
                outcome = int(rng.random() < probability)
                complete[risk][arm].append(outcome)
                follow_up = 0.50 if arm == 1 and outcome else 0.90
                if rng.random() < follow_up:
                    observed[risk][arm].append(outcome)
    return complete, observed


def differences(cells):
    groups = [[v for arms in cells.values() for v in arms[g]] for g in (0, 1)]
    crude = mean(groups[1]) - mean(groups[0])
    overlap = [cell for cell in pooled_strata(cells) if cell.weight]
    if not overlap:
        raise ValueError("no retained stratum in simulated cohort")
    adjusted_a, adjusted_b = standardized_means(overlap)
    return 100 * crude, 100 * (adjusted_b - adjusted_a)


def experiment():
    rng = Random(SEED)
    results = {"Complete": [], "Outcome-dependent": []}
    for _ in range(REPETITIONS):
        complete, observed = simulate(rng)
        results["Complete"].append(differences(complete))
        results["Outcome-dependent"].append(differences(observed))
    return results


def render(results):
    lines = [
        "# Calibration against a known zero effect", "",
        f"Each of {REPETITIONS:,} independently simulated cohorts has 100 surgeries per mesh. "
        "MESH-A has 25 high-risk patients and MESH-B has 75. Low-risk patients have a 10% "
        "365-day recurrence probability and high-risk patients have a 30% probability with either mesh. "
        "The true within-risk and standardized mesh effects are both zero. The different risk mixes "
        "produce an expected crude B minus A difference of +10 percentage points.", "",
        "Each cohort is analyzed twice. First every outcome is observed. Then 50% of MESH-B "
        "recurrences and 90% of all other cases are observed in expectation. This second analysis "
        "uses cases with observed outcomes and recalculates pooled risk weights from retained cases. "
        "Both analyses use the main estimator’s minimum of five cases per mesh in each retained stratum.", "",
        "| Follow-up | Mean crude B − A | Mean adjusted B − A (bias vs zero) | Monte Carlo SE of adjusted mean |",
        "|---|---:|---:|---:|",
    ]
    for label, pairs in results.items():
        crude, adjusted = zip(*pairs)
        mcse = stdev(adjusted) / sqrt(len(adjusted))
        lines.append(f"| {label} | {mean(crude):+.2f} pp | {mean(adjusted):+.2f} pp | {mcse:.2f} pp |")
    lines += [
        "", "Risk adjustment can correct the engineered case-mix imbalance. When ascertainment selects "
        "against recurrences in one mesh, adjustment for preoperative risk leaves selection bias. "
        "The Monte Carlo standard error measures variability of the simulated mean across repetitions. "
        "The observation probabilities here are assumptions chosen to illustrate the mechanism.", "",
        f"Run `python3 -m examples.calibration` from the repository root (seed {SEED}).", "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print(render(experiment()), end="")

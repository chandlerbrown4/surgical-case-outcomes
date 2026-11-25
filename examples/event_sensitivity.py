"""Show how changing one or two observed outcomes shifts the adjusted estimate."""

from dataclasses import dataclass
from pathlib import Path

from surgical.analysis import Case, build_cases, compare
from surgical.fixture import GROUPS, make_fixture
from surgical.prices import load_catalog

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Change:
    case_id: str
    arm: int
    observed: int
    effect: float  # Change in standardized B minus A risk, in probability units.


def summarize(cases: list[Case]) -> tuple[float, list[Change]]:
    comparison = compare(cases, lambda case: case.outcome)
    if comparison.adjusted is None:
        raise ValueError("recurrence analysis has no overlapping strata")
    retained = {cell.name: cell for cell in comparison.strata if cell.weight}
    changes = []
    for case in cases:
        outcome = case.outcome
        cell = retained.get(case.stratum)
        if outcome is None or cell is None:
            continue
        arm = GROUPS.index(case.surgery.mesh)
        # Crossing 0→1 adds 1/n to the group risk in this stratum.
        group_change = (1 - 2 * outcome) / len(cell.values[arm])
        effect = cell.weight * group_change * (-1 if arm == 0 else 1)
        changes.append(Change(case.surgery.case_id, arm, outcome, effect))
    return comparison.adjusted.difference, changes


def render(baseline: float, changes: list[Change]) -> str:
    denominators = [sum(change.arm == g for change in changes) for g in range(2)]
    events = [sum(c.observed for c in changes if c.arm == g) for g in range(2)]
    lines = [
        "# Sensitivity to one or two recurrence classifications", "",
        "This uses the 365-day recurrence analysis of fictional ventral hernia repairs. "
        "Each hypothetical change flips one observed binary outcome. All patients, preoperative "
        "strata and pooled standardization weights stay fixed. The table gives the lowest and "
        "highest attainable adjusted MESH-B minus MESH-A differences at each number of changes.", "",
        "| Changed cases | Hypothetical records (recurrence 0/1) | MESH-A events / cases | "
        "MESH-B events / cases | Adjusted difference | Shift from baseline |",
        "|---|---|---:|---:|---:|---:|",
    ]

    def append(label: str, altered: list[Change]) -> None:
        counts = events.copy()
        for change in altered:
            counts[change.arm] += 1 - 2 * change.observed
        shift = sum(c.effect for c in altered)
        names = ", ".join(f"{c.case_id} ({c.observed}→{1 - c.observed})" for c in altered)
        lines.append(f"| {label} | {names or 'Recorded outcomes'} | {counts[0]}/{denominators[0]} "
                     f"| {counts[1]}/{denominators[1]} | {(baseline + shift)*100:+.1f} pp "
                     f"| {shift*100:+.1f} pp |")

    append("0", [])
    for n in (1, 2):
        # Contributions add because the eligible groups and weights do not change.
        for direction, sign in (("lowest", 1), ("highest", -1)):
            ordered = sorted(changes, key=lambda c: (sign * c.effect, c.case_id))
            append(f"{n}, {direction}", ordered[:n])
    lines += [
        "", "The case IDs identify one way to reach each extreme. When effects tie, "
        "the first IDs in sort order are shown. These ranges measure sensitivity to "
        "record classification. The [bootstrap intervals](report.md#recurrence-through-day-365) "
        "address sampling uncertainty.", "",
        "Reproduce from the repository root with `python3 -m examples.event_sensitivity`.", "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    catalog = load_catalog(ROOT / "data/device_prices.csv")
    result = render(*summarize(build_cases(make_fixture(), catalog)))
    print(result, end="")

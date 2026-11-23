"""Build one row per case and compare groups within common preoperative strata."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from random import Random
from statistics import mean, quantiles
from typing import Callable

from .fixture import AS_OF, GROUPS, OTHER_COST_CATEGORIES, WINDOW_DAYS, Fixture, Implant, Surgery
from .prices import Catalog, Price
from .validation import validate_implants


@dataclass(frozen=True)
class MatchedLine:
    implant: Implant
    service_date: date
    price: Price | None

    @property
    def extended_cents(self) -> int | None:
        if self.price is None:
            return None
        return self.implant.quantity_each * self.price.cents


@dataclass(frozen=True)
class Case:
    surgery: Surgery
    stratum: str | None
    prior_repair: bool | None
    defect_cm: int | None
    diabetes_status: str
    observed_through: date | None
    diagnosed_on: date | None
    line_items: list[MatchedLine]
    other_cost_cents: int
    missing_other_cost_categories: tuple[str, ...]
    exclusion: str
    cost_status: str
    outcome_status: str

    @property
    def outcome_deadline(self) -> date:
        return self.surgery.service_date + timedelta(days=WINDOW_DAYS)

    @property
    def known_recurrence(self) -> bool:
        return (
            self.diagnosed_on is not None
            and self.surgery.service_date <= self.diagnosed_on <= self.outcome_deadline
        )

    @property
    def total_cents(self) -> int | None:
        extensions = [line.extended_cents for line in self.line_items]
        if self.missing_other_cost_categories or not extensions or None in extensions:
            return None
        return self.other_cost_cents + sum(amount for amount in extensions if amount is not None)

    @property
    def cost(self) -> float | None:
        if self.cost_status == "included" and self.total_cents is not None:
            return self.total_cents / 100
        return None

    @property
    def outcome(self) -> int | None:
        if self.outcome_status != "included":
            return None
        return int(self.known_recurrence)


def build_cases(data: Fixture, catalog: Catalog) -> list[Case]:
    validate_implants(data)
    surgeries = {case.case_id: case for case in data.surgeries}
    lines = defaultdict(list)
    for implant in data.implants:
        service_date = surgeries[implant.case_id].service_date
        price = catalog.match(implant.device_id, service_date)
        lines[implant.case_id].append(MatchedLine(implant, service_date, price))

    other_costs = defaultdict(list)
    for cost in data.other_costs:
        other_costs[cost.case_id].append(cost)

    cases = []
    for surgery in data.surgeries:
        key = surgery.case_id
        preoperative = data.preoperative.get(key)
        follow_up = data.follow_up.get(key)
        recurrence = data.recurrences.get(key)
        if recurrence is not None and recurrence.diagnosed_on < surgery.service_date:
            raise ValueError(f"{key}: recurrence diagnosis precedes index surgery")
        observed = min(follow_up.observed_through, AS_OF) if follow_up else None
        diagnosed = recurrence.diagnosed_on if recurrence and recurrence.diagnosed_on <= AS_OF else None
        deadline = surgery.service_date + timedelta(days=WINDOW_DAYS)

        exclusion = ""
        if surgery.procedure != "elective ventral hernia repair":
            exclusion = "outside procedure scope"
        elif preoperative is None:
            exclusion = "missing preoperative factors"
        elif preoperative.diabetes is None:
            exclusion = "unknown preoperative diabetes status"

        categories = {cost.category for cost in other_costs[key]}
        missing_costs = tuple(category for category in OTHER_COST_CATEGORIES
                              if category not in categories)
        cost_status = exclusion or "included"
        if not exclusion:
            if not lines[key] or any(line.price is None for line in lines[key]):
                cost_status = "unpriced implant lines"
            elif missing_costs:
                cost_status = "missing other cost components"

        outcome_status = exclusion or "included"
        if not exclusion:
            if deadline > AS_OF:
                outcome_status = "window not mature"
            elif observed is None:
                outcome_status = "no follow-up record"
            elif observed < deadline:
                outcome_status = "follow-up short of 365 days"

        cases.append(Case(
            surgery, preoperative.stratum if preoperative else None,
            preoperative.prior_repair if preoperative else None,
            preoperative.defect_cm if preoperative else None,
            preoperative.diabetes_status if preoperative else "unknown",
            observed, diagnosed, lines[key], sum(cost.cents for cost in other_costs[key]), missing_costs,
            exclusion, cost_status, outcome_status,
        ))
    return cases


MIN_PER_GROUP = 5
BOOTSTRAP_REPLICATES = 5000


@dataclass(frozen=True)
class Stratum:
    name: str
    values: tuple[list[float], list[float]]
    weight: float


@dataclass(frozen=True)
class Estimate:
    groups: tuple[float, float]
    interval: tuple[float, float]

    @property
    def difference(self) -> float:
        return self.groups[1] - self.groups[0]


@dataclass(frozen=True)
class Comparison:
    strata: list[Stratum]
    values: tuple[list[float], list[float]]
    crude: Estimate | None
    overlap_crude: Estimate | None
    adjusted: Estimate | None


def estimate(cells: list[Stratum]) -> Estimate | None:
    if not cells or not all(all(cell.values) for cell in cells):
        return None
    groups = tuple(sum(cell.weight * mean(cell.values[g]) for cell in cells) for g in range(2))
    rng = Random(527)
    differences = [
        sum(cell.weight * (
            mean(rng.choices(cell.values[1], k=len(cell.values[1])))
            - mean(rng.choices(cell.values[0], k=len(cell.values[0])))
        ) for cell in cells)
        for _ in range(BOOTSTRAP_REPLICATES)
    ]
    cut_points = quantiles(differences, n=40, method="inclusive")
    interval = (cut_points[0], cut_points[-1])
    return Estimate(groups, interval)


def compare(cases: list[Case], measure: Callable[[Case], float | None]) -> Comparison:
    by_stratum = defaultdict(lambda: ([], []))
    totals = ([], [])
    for case in cases:
        value = measure(case)
        if value is not None and case.stratum is not None:
            group = GROUPS.index(case.surgery.mesh)
            by_stratum[case.stratum][group].append(value)
            totals[group].append(value)

    def in_overlap(cells):
        return min(map(len, cells)) >= MIN_PER_GROUP

    target_size = sum(sum(map(len, cells)) for cells in by_stratum.values() if in_overlap(cells))
    strata = [
        Stratum(name, cells, sum(map(len, cells)) / target_size if in_overlap(cells) else 0)
        for name, cells in sorted(by_stratum.items())
    ]
    overlap = [cell for cell in strata if cell.weight]
    overlap_values = tuple([value for cell in overlap for value in cell.values[g]] for g in range(2))
    return Comparison(
        strata, totals, estimate([Stratum("All", totals, 1)]),
        estimate([Stratum("Overlap", overlap_values, 1)]),
        estimate(overlap),
    )

"""Audit coded eligibility and potential one-to-one matches in the fictional inguinal series."""

import csv
from collections import defaultdict
from dataclasses import asdict, dataclass, fields
from datetime import date
from pathlib import Path

from .fixture import GROUPS
from .prices import Catalog

PROCEDURE = "Elective laparoscopic inguinal repair"
INCLUDED = "eligible initial repair"


def read_rows(path: Path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def screen(label: str, diagnoses: set[str], procedures: set[str]) -> str:
    if label != PROCEDURE:
        return "outside procedure scope"
    if "K40.91" in diagnoses or "49651" in procedures:
        return "excluded recurrent repair"
    if diagnoses == {"K40.90"} and procedures == {"49650"}:
        return INCLUDED
    return "review missing or unsupported coding"


def observed_return(row) -> int | None:
    if row is None:
        return None
    through = int(row["observed_through_day"])
    event = int(row["inpatient_return_day"]) if row["inpatient_return_day"] else None
    if through < 0 or (event is not None and not 1 <= event <= through):
        raise ValueError(f"Invalid follow-up for {row['case_id']}")
    if event is not None and event <= 30:
        return 1
    return 0 if through >= 30 else None


@dataclass(frozen=True)
class Repair:
    case_id: str
    account_id: str
    service_date: date
    operative_label: str
    surgeon: str
    side: str
    mesh: str
    diagnosis_codes: str
    repair_codes: str
    coding_status: str
    unit_price_cents: int | None
    return_30d: int | None


def load_repairs(folder: Path, catalog: Catalog) -> list[Repair]:
    claims = defaultdict(list)
    for row in read_rows(folder / "billing.csv"):
        claims[row["account_id"], date.fromisoformat(row["service_date"])].append(row)
    follow_up = {}
    for row in read_rows(folder / "follow_up.csv"):
        key = row["case_id"]
        if key in follow_up:
            raise ValueError(f"Duplicate follow-up row for {key}")
        follow_up[key] = row

    cases = []
    seen_cases = set()
    seen_visits = set()
    for op in read_rows(folder / "operations.csv"):
        key = op["case_id"]
        day = date.fromisoformat(op["service_date"])
        visit = op["account_id"], day
        if key in seen_cases or visit in seen_visits:
            raise ValueError(f"Ambiguous operation for {key}")
        seen_cases.add(key)
        seen_visits.add(visit)
        if op["mesh"] not in GROUPS or not op["surgeon"] or op["side"] not in {"left", "right"}:
            raise ValueError(f"Invalid matching fields for {key}")
        diagnoses = {row["diagnosis_code"] for row in claims[visit]}
        procedures = {row["repair_code"] for row in claims[visit]}
        status = screen(op["operative_label"], diagnoses, procedures)
        price = catalog.match(op["mesh"], day)
        cases.append(Repair(key, op["account_id"], day, op["operative_label"], op["surgeon"],
                            op["side"], op["mesh"], " | ".join(sorted(diagnoses)),
                            " | ".join(sorted(procedures)), status, price.cents if price else None,
                            observed_return(follow_up.get(key))))
    if follow_up.keys() - seen_cases:
        raise ValueError("Follow-up refers to an unknown case")
    return cases


@dataclass(frozen=True)
class MatchGroup:
    surgeon: str
    side: str
    eligible: tuple[int, int]
    priced: tuple[int, int]
    observed: tuple[int, int]
    events: tuple[int, int]

    def event_bounds(self, arm: int) -> tuple[int, int]:
        """Fewest and most returns selectable in a maximum-size complete pairing."""
        pairs = min(self.observed)
        events = self.events[arm]
        non_events = self.observed[arm] - events
        return max(0, pairs - non_events), min(pairs, events)


def group_repairs(cases: list[Repair]) -> list[MatchGroup]:
    groups = defaultdict(lambda: ([], []))
    for case in cases:
        if case.coding_status == INCLUDED:
            groups[case.surgeon, case.side][GROUPS.index(case.mesh)].append(case)
    result = []
    for (surgeon, side), arms in sorted(groups.items()):
        priced = tuple([r for r in arm if r.unit_price_cents is not None] for arm in arms)
        observed = tuple([r for r in arm if r.return_30d is not None] for arm in priced)
        result.append(MatchGroup(surgeon, side, tuple(map(len, arms)), tuple(map(len, priced)),
                                 tuple(map(len, observed)),
                                 tuple(sum(r.return_30d for r in arm) for arm in observed)))
    return result


def write_matching_review(folder: Path, data: Path, catalog: Catalog) -> None:
    cases = load_repairs(data, catalog)
    with (folder / "coded_cases.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=[f.name for f in fields(Repair)], lineterminator="\n")
        writer.writeheader()
        writer.writerows(asdict(case) for case in cases)

    groups = group_repairs(cases)
    example = next(c for c in cases if c.case_id == "G19")
    lines = [
        "# Which inguinal repairs can be compared?",
        "",
        f"These {len(cases)} fictional operations each represent a different patient at one fictional "
        "hospital. All procedures were outpatient, with discharge on the surgery date.",
        "",
        "## A routine label hides a recurrent repair",
        "",
        f"The operative label for **{example.case_id}** reads “{example.operative_label}”. "
        f"Account {example.account_id} on {example.service_date} carries ICD-10-CM {example.diagnosis_codes} "
        f"and CPT {example.repair_codes}. The screen records **{example.coding_status}**. "
        f"The label admits {sum(c.operative_label == PROCEDURE for c in cases)} candidates. "
        f"Same-day billing evidence retains {sum(c.coding_status == INCLUDED for c in cases)}.",
        "",
        "This fixture screens for initial repairs using CPT 49650 and diagnosis K40.90. "
        "Either recurrent code (49651 or K40.91) excludes the operation. Other code combinations "
        "require review. Billing rows join on account and service date. G01 has a later billing "
        "row on the same account, so only its index-date codes enter the screen.",
        "",
        "## How much follow-up do the comparable patients have?",
        "",
        "Match within each surgeon and operated side. Each patient received one implant. "
        "A dated catalog price is required for the price column. The final column also requires "
        "a recorded inpatient return on days 1–30 or observation through day 30. "
        "A missing or short event-free record has unknown return status.",
        "",
        "| Surgeon | Side | Eligible A / B | Potential pairs | Both priced | Both priced with 30-day outcome |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for g in groups:
        lines.append(f"| {g.surgeon} | {g.side} | {g.eligible[0]} / {g.eligible[1]} | "
                     f"{min(g.eligible)} | {min(g.priced)} | {min(g.observed)} |")
    totals = [sum(min(getattr(g, field)) for g in groups) for field in ("eligible", "priced", "observed")]
    lines.extend(["", f"The smaller arm sets the maximum number of one-to-one pairs in each group. "
                  f"Together the groups support **{totals[0]}** eligible pairs, **{totals[1]}** priced pairs "
                  f"and **{totals[2]}** pairs with both a price and an observable 30-day outcome.", "",
                  "| Mesh | Observed returns / priced patients in shared follow-up groups | "
                  "Possible returns among selected pairs |", "|---|---:|---:|"])
    shared = [g for g in groups if min(g.observed) > 0]
    for arm, name in enumerate(GROUPS):
        low = sum(g.event_bounds(arm)[0] for g in shared)
        high = sum(g.event_bounds(arm)[1] for g in shared)
        lines.append(f"| {name} | {sum(g.events[arm] for g in shared)} / "
                     f"{sum(g.observed[arm] for g in shared)} | {low}–{high} |")
    lines.extend(["", "G04 has a documented inpatient return on day 8. The range counts how many "
                  "observed events could enter a maximum-size pairing, allowing any eligible choice "
                  "within each group. No individual pairs have been assigned.",
                  "", "The [case audit](coded_cases.csv) shows the codes, price and outcome used for each patient.",
                  ""])
    (folder / "matching_review.md").write_text("\n".join(lines), encoding="utf-8")

"""Invent the linked source records for the portfolio demonstration."""

from dataclasses import dataclass
from datetime import date, timedelta

AS_OF = date(2026, 11, 23)
GROUPS = ("MESH-A", "MESH-B")
WINDOW_DAYS = 365
PACK_CASE = "S001"
PACK_PRICE_CENTS = 72_000
PACK_EACHES = 6
OTHER_COST_CATEGORIES = ("OR labor and room", "Anesthesia and other supplies")


@dataclass(frozen=True)
class Surgery:
    case_id: str
    patient_id: str
    service_date: date
    procedure: str
    mesh: str


@dataclass(frozen=True)
class Preoperative:
    case_id: str
    prior_repair: bool
    defect_cm: int
    diabetes: bool | None

    @property
    def diabetes_status(self) -> str:
        if self.diabetes is None:
            return "unknown"
        return "yes" if self.diabetes else "no"

    @property
    def surgical_stratum(self) -> str:
        if self.prior_repair and self.defect_cm >= 8:
            return "Prior repair, ≥8 cm"
        if self.prior_repair or self.defect_cm >= 5:
            return "Prior repair or ≥5 cm"
        return "No prior repair, <5 cm"

    @property
    def stratum(self) -> str | None:
        if self.diabetes is None:
            return None
        return f"{self.surgical_stratum} · diabetes {self.diabetes_status}"


@dataclass(frozen=True)
class Implant:
    line_id: str
    case_id: str
    device_id: str
    quantity_each: int


@dataclass(frozen=True)
class OtherCost:
    case_id: str
    category: str
    cents: int


@dataclass(frozen=True)
class FollowUp:
    case_id: str
    observed_through: date


@dataclass(frozen=True)
class Recurrence:
    case_id: str
    diagnosed_on: date


@dataclass
class Fixture:
    surgeries: list[Surgery]
    preoperative: dict[str, Preoperative]
    implants: list[Implant]
    other_costs: list[OtherCost]
    follow_up: dict[str, FollowUp]
    recurrences: dict[str, Recurrence]


def make_fixture() -> Fixture:
    data = Fixture([], {}, [], [], {}, {})

    def add(mesh, prior_repair, defect_cm, *, diabetes=False, recurrence_day=None,
            follow_up_days=385, service_date=None, procedure="elective ventral hernia repair",
            has_preoperative=True, extra_implant=None):
        number = len(data.surgeries) + 1
        case_id = f"S{number:03d}"
        service_date = service_date or date(2025, 1, 1) + timedelta(days=(number * 17) % 303)
        data.surgeries.append(Surgery(case_id, f"P{number:03d}", service_date, procedure, mesh))
        if has_preoperative:
            data.preoperative[case_id] = Preoperative(case_id, prior_repair, defect_cm, diabetes)
        data.implants.extend([
            Implant(f"{case_id}-1", case_id, mesh, 1),
            Implant(f"{case_id}-2", case_id, "FIX-1", 1 + number % 3),
        ])
        if extra_implant:
            data.implants.append(Implant(f"{case_id}-3", case_id, extra_implant, 1))
        amounts = (310_000 + 4_750 * defect_cm + 850 * (number % 9),
                   88_000 + 1_150 * (number % 11))
        data.other_costs.extend(OtherCost(case_id, category, cents)
                                for category, cents in zip(OTHER_COST_CATEGORIES, amounts))
        if follow_up_days is not None:
            data.follow_up[case_id] = FollowUp(case_id, service_date + timedelta(days=follow_up_days))
        if recurrence_day is not None:
            data.recurrences[case_id] = Recurrence(case_id, service_date + timedelta(days=recurrence_day))

    # Predeclared cell sizes and event counts make differences in case mix inspectable.
    for mesh, prior, defect, size, events, diabetes_pattern in (
        ("MESH-A", False, 3, 40, 4, (True, False, False, False, False)),
        ("MESH-A", True, 6, 12, 4, (True, False)),
        ("MESH-B", False, 3, 12, 1, (True, False)),
        ("MESH-B", True, 6, 36, 9, (True, True, False)),
        ("MESH-B", True, 9, 6, 3, (True,)),
    ):
        for index in range(size):
            recurrence_day = 365 if not index and events else 110 + index * 19
            if index >= events:
                recurrence_day = 366 if index == events else None
            diabetes = diabetes_pattern[index % len(diabetes_pattern)]
            add(mesh, prior, defect, diabetes=diabetes, recurrence_day=recurrence_day,
                extra_implant="FIX-UNLISTED" if mesh == "MESH-A" and index == 10 and not prior else None)

    add("MESH-A", False, 4, follow_up_days=200, recurrence_day=140)
    add("MESH-B", True, 6, follow_up_days=210)
    add("MESH-B", True, 6, follow_up_days=None)
    add("MESH-A", False, 3, service_date=date(2026, 7, 1), follow_up_days=100)
    add("MESH-A", False, 3, has_preoperative=False)
    add("MESH-B", True, 6, procedure="emergency ventral hernia repair")
    add("MESH-A", False, 3, diabetes=None)
    return data

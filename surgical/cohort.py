"""Load one synthetic index surgery per patient from the portable JSON format."""

import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

from .fixture import (
    GROUPS, OTHER_COST_CATEGORIES, WINDOW_DAYS, Fixture, FollowUp, Implant,
    OtherCost, Preoperative, Recurrence, Surgery,
)
from .prices import iso_date


def fields(record, required, optional=()):
    if not isinstance(record, dict):
        raise ValueError("expected an object")
    missing = set(required) - record.keys()
    unknown = record.keys() - set(required) - set(optional)
    if missing:
        raise ValueError("missing field(s): " + ", ".join(sorted(missing)))
    if unknown:
        raise ValueError("unknown field(s): " + ", ".join(sorted(unknown)))


def label(value, name):
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{name} must be a nonempty string without surrounding whitespace")
    return value


def integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def day(value, name):
    try:
        return iso_date(value)
    except (ValueError, TypeError):
        raise ValueError(f"{name} must be a date in YYYY-MM-DD format") from None


def distinct_fields(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f"duplicate JSON field: {key}")
        obj[key] = value
    return obj


def add_case(data, record, case_ids, patient_ids):
    fields(record, ("case_id", "patient_id", "service_date", "procedure", "mesh", "implants",
                    "other_cost_cents"), ("preoperative", "observed_through", "diagnosed_on"))
    case_id = label(record["case_id"], "case_id")
    patient_id = label(record["patient_id"], "patient_id")
    if case_id in case_ids or patient_id in patient_ids:
        raise ValueError("case_id and patient_id must each be unique in this cohort")
    case_ids.add(case_id)
    patient_ids.add(patient_id)
    service_date = day(record["service_date"], "service_date")
    if service_date > data.as_of:
        raise ValueError("service_date falls after the cohort cutoff")
    if date.max - service_date < timedelta(days=WINDOW_DAYS):
        raise ValueError("service_date leaves no representable 365-day endpoint")
    mesh = record["mesh"]
    if mesh not in GROUPS:
        raise ValueError(f"mesh must be one of {', '.join(GROUPS)}")
    data.surgeries.append(Surgery(case_id, patient_id, service_date,
                                  label(record["procedure"], "procedure"), mesh))
    preop = record.get("preoperative")
    if preop is not None:
        fields(preop, ("prior_repair", "defect_cm", "diabetes"))
        if type(preop["prior_repair"]) is not bool:
            raise ValueError("prior_repair must be true or false")
        if preop["diabetes"] is not None and type(preop["diabetes"]) is not bool:
            raise ValueError("diabetes must be true, false, or null")
        data.preoperative[case_id] = Preoperative(
            case_id, preop["prior_repair"], integer(preop["defect_cm"], "defect_cm", 1),
            preop["diabetes"],
        )

    if not isinstance(record["implants"], list):
        raise ValueError("implants must be an array")
    for line in record["implants"]:
        fields(line, ("line_id", "device_id", "quantity_each"))
        data.implants.append(Implant(
            label(line["line_id"], "line_id"), case_id, label(line["device_id"], "device_id"),
            integer(line["quantity_each"], "quantity_each", 1),
        ))
    costs = record["other_cost_cents"]
    fields(costs, (), OTHER_COST_CATEGORIES)
    for category, amount in costs.items():
        data.other_costs.append(OtherCost(case_id, category, integer(amount, category)))

    for name, records, cls in (("observed_through", data.follow_up, FollowUp),
                               ("diagnosed_on", data.recurrences, Recurrence)):
        if record.get(name) is not None:
            when = day(record[name], name)
            if when < service_date or when > data.as_of:
                raise ValueError(f"{name} must be between service_date and as_of")
            records[case_id] = cls(case_id, when)


def load_cohort(path: Path) -> tuple[Fixture, str]:
    raw = path.read_bytes()
    source = json.loads(raw.decode("utf-8"), object_pairs_hook=distinct_fields)
    fields(source, ("as_of", "cases"))
    if not isinstance(source["cases"], list) or not source["cases"]:
        raise ValueError("cases must be a nonempty array")
    data = Fixture([], {}, [], [], {}, {}, day(source["as_of"], "as_of"))
    case_ids = set()
    patient_ids = set()
    for index, record in enumerate(source["cases"], start=1):
        try:
            add_case(data, record, case_ids, patient_ids)
        except ValueError as exc:
            raise ValueError(f"case {index}: {exc}") from exc
    return data, hashlib.sha256(raw).hexdigest()

"""Check the joins that assign implant costs and mesh exposure to a surgery."""

from collections import defaultdict

from .fixture import GROUPS, Fixture


def validate_implants(data: Fixture) -> None:
    case_ids = {case.case_id for case in data.surgeries}
    if len(case_ids) != len(data.surgeries):
        raise ValueError("duplicate case ID in the surgical record")

    keys = set()
    exposures = defaultdict(set)
    for line in data.implants:
        key = line.case_id, line.line_id
        if line.case_id not in case_ids:
            raise ValueError(f"{line.line_id}: unknown case {line.case_id}")
        if key in keys:
            raise ValueError(f"{line.case_id}: duplicate implant line {line.line_id}")
        if type(line.quantity_each) is not int or line.quantity_each < 1:
            raise ValueError(f"{line.line_id}: expected a positive integer implant quantity")
        keys.add(key)
        if line.device_id in GROUPS:
            exposures[line.case_id].add(line.device_id)

    for case in data.surgeries:
        if exposures[case.case_id] != {case.mesh}:
            raise ValueError(f"{case.case_id}: mesh group disagrees with the implanted devices")

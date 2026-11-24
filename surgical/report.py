"""Render the reviewer report and export case and line-level audit records."""

import csv
from collections import Counter
from pathlib import Path

from .analysis import BOOTSTRAP_REPLICATES, MIN_PER_GROUP, Case, Comparison
from .fixture import AS_OF, GROUPS, PACK_CASE, PACK_EACHES, PACK_PRICE_CENTS, Fixture


def usd(dollars):
    return f"${dollars:,.2f}"


def overlap_counts(comparison: Comparison) -> tuple[int, int]:
    return tuple(sum(len(cell.values[g]) for cell in comparison.strata if cell.weight)
                 for g in range(2))


def estimates_table(comparison: Comparison, is_cost: bool) -> str:
    def format_value(value, difference=False):
        if is_cost:
            return f"{'−' if value < 0 else '+' if difference else ''}{usd(abs(value))}"
        return f"{value * 100:+.1f} pp" if difference else f"{value:.1%}"

    rows = [
        "| Population and estimate | A n | B n | MESH-A | MESH-B | B − A | 95% bootstrap interval |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    retained = overlap_counts(comparison)
    for label, item, (a, b) in (
        ("All eligible, crude", comparison.crude, tuple(map(len, comparison.values))),
        ("Overlap only, crude", comparison.overlap_crude, retained),
        ("Overlap only, standardized", comparison.adjusted, retained),
    ):
        if item is None:
            rows.append(f"| {label} | {a} | {b} | — | — | — | — |")
            continue
        first, second = map(format_value, item.groups)
        diff = format_value(item.difference, difference=True)
        low, high = (format_value(value, difference=True) for value in item.interval)
        rows.append(f"| {label} | {a} | {b} | {first} | {second} | {diff} | {low} to {high} |")
    return "\n".join(rows)


def strata_table(comparison: Comparison, is_cost: bool) -> str:
    label = "n and mean cost" if is_cost else "events / n"
    rows = [
        f"| Surgical risk and preoperative diabetes | A {label} | B {label} | Pooled overlap weight |",
        "|---|---:|---:|---:|",
    ]
    for cell in comparison.strata:
        if is_cost:
            values = [f"{len(group)} · {usd(sum(group) / len(group))}" if group else "0 · —"
                      for group in cell.values]
        else:
            values = [f"{sum(group)}/{len(group)}" for group in cell.values]
        rows.append(f"| {cell.name} | {values[0]} | {values[1]} | {cell.weight:.1%} |")
    return "\n".join(rows) if comparison.strata else "No eligible cases."


def overlap_loss_table(cost: Comparison, recurrence: Comparison) -> str:
    rows = [
        "| Endpoint | MESH-A eligible → overlap | MESH-B eligible → overlap | A outside overlap | B outside overlap |",
        "|---|---:|---:|---:|---:|",
    ]
    for label, comparison in (("Index cost", cost), ("Recurrence", recurrence)):
        a, b = map(len, comparison.values)
        kept_a, kept_b = overlap_counts(comparison)
        rows.append(f"| {label} | {a} → {kept_a} | {b} → {kept_b} | {a - kept_a} | {b - kept_b} |")
    return "\n".join(rows)


def cohort_table(cases: list[Case], attribute: str) -> str:
    counts = Counter((getattr(case, attribute), case.surgery.mesh) for case in cases)
    statuses = sorted({status for status, _ in counts}, key=lambda s: (s != "included", s))
    rows = ["| Status | MESH-A | MESH-B |", "|---|---:|---:|"]
    rows.extend(f"| {status.capitalize()} | {counts[status, GROUPS[0]]} | {counts[status, GROUPS[1]]} |"
                for status in statuses)
    return "\n".join(rows)


def follow_up_bounds(cases: list[Case]) -> str:
    rows = [
        "| Mesh | Mature n | Known events with complete follow-up | Additional known events | Unknown | Risk bounds |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for mesh in GROUPS:
        mature = [case for case in cases if case.surgery.mesh == mesh
                  and not case.exclusion and case.outcome_deadline <= AS_OF]
        complete_events = sum(case.outcome == 1 for case in mature)
        additional_events = sum(case.outcome is None and case.known_recurrence for case in mature)
        unknown = sum(case.outcome is None and not case.known_recurrence for case in mature)
        known = complete_events + additional_events
        bounds = (f"{known / len(mature):.1%} to {(known + unknown) / len(mature):.1%}"
                  if mature else "—")
        rows.append(f"| {mesh} | {len(mature)} | {complete_events} | {additional_events} | {unknown} | {bounds} |")
    return "\n".join(rows)


def pack_example(cases: list[Case]) -> str:
    case = next(case for case in cases if case.surgery.case_id == PACK_CASE)
    mesh = next(line for line in case.line_items if line.implant.device_id == "MESH-A")
    base = (
        f"In the standalone pack example, a pack of {PACK_EACHES} MESH-A implants costs "
        f"{usd(PACK_PRICE_CENTS / 100)}, or {usd(PACK_PRICE_CENTS / PACK_EACHES / 100)} per implant. "
        f"Case {PACK_CASE} ({case.surgery.service_date}) used {mesh.implant.quantity_each}. "
        "The error scenario treats the pack price as the per-implant price on that one line."
    )
    if mesh.price is None or case.total_cents is None:
        return base + " This input leaves the case unpriced, so the case-level comparison is unavailable."
    matched = case.total_cents
    overstated = mesh.implant.quantity_each * (PACK_PRICE_CENTS - mesh.price.cents)
    return (
        base + f" The matched row (CSV line {mesh.price.row}) prices each implant at "
        f"{usd(mesh.price.cents / 100)}. Holding other lines and case costs fixed, "
        f"the matched total is **{usd(matched / 100)}** and the erroneous total is "
        f"**{usd((matched + overstated) / 100)}** "
        f"(change {overstated / 100:+,.2f} USD)."
    )


def write_csv(path: Path, header, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def write_outputs(folder: Path, price_file: str, digest: str, cases: list[Case], data: Fixture,
                  cost: Comparison, recurrence: Comparison) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    write_csv(folder / "case_audit.csv", (
        "case_id", "patient_id", "service_date", "procedure", "mesh", "prior_repair", "defect_cm",
        "preoperative_stratum", "observed_through_as_of", "diagnosed_on_as_of", "outcome_deadline",
        "scope_exclusion", "cost_status", "outcome_status", "implant_line_count",
        "unmatched_implant_line_count", "other_cost_cents", "missing_other_cost_categories",
        "case_total_cents", "recurrence_by_day_365", "preoperative_diabetes",
    ), (
        (s.case_id, s.patient_id, s.service_date, s.procedure, s.mesh, case.prior_repair,
         case.defect_cm, case.stratum, case.observed_through, case.diagnosed_on,
         case.outcome_deadline, case.exclusion, case.cost_status,
         case.outcome_status, len(case.line_items), sum(line.price is None for line in case.line_items),
         case.other_cost_cents, " | ".join(case.missing_other_cost_categories),
         case.total_cents, case.outcome, case.diabetes_status)
        for case in cases for s in [case.surgery]
    ))
    write_csv(folder / "implant_lineage.csv", (
        "case_id", "line_id", "service_date", "device_id", "quantity_each", "status",
        "price_csv_line", "effective_from", "effective_to_exclusive", "unit_price_cents",
        "currency", "price_source", "extended_cents",
    ), (
        (line.implant.case_id, line.implant.line_id, line.service_date, line.implant.device_id,
         line.implant.quantity_each, "matched" if price else "unmatched",
         price.row if price else None, price.start if price else None, price.end if price else None,
         price.cents if price else None, "USD" if price else None, price.source if price else None,
         line.extended_cents)
        for case in cases for line in case.line_items for price in [line.price]
    ))
    write_csv(folder / "other_cost_lines.csv", ("case_id", "category", "cost_cents"), (
        (line.case_id, line.category, line.cents) for line in data.other_costs
    ))

    missing = [case for case in cases if case.cost_status == "unpriced implant lines"]
    missing_summary = ", ".join(case.surgery.case_id for case in missing[:8])
    if len(missing) > 8:
        missing_summary += f", and {len(missing) - 8} more"
    if missing:
        missing_summary = f"Unpriced eligible cases include {missing_summary}. "
    report = f"""# Surgical case cost and outcomes

**Synthetic elective ventral hernia repair cohort · {len(cases)} index surgeries · Data cutoff {AS_OF}**

The comparison asks how recorded index surgery cost and 365-day recurrence differ between
two fictional mesh groups when both are evaluated on the same mix of measured preoperative factors.

The [companion coding and matching example](matching_review.md) follows a separate fictional
inguinal repair series from an operative label through billing evidence and 30-day follow-up.

## Index surgery cost

Cost combines matched implant purchase prices and recorded operating room, anesthesia and
other supply costs. The analysis covers the index surgery and uses no billed charges.
It omits overhead beyond the modeled items, later care, and payer reimbursement.

{estimates_table(cost, is_cost=True)}

{strata_table(cost, is_cost=True)}

A case needs an effective-date price for every implant line and both modeled other cost
components (OR labor and room, and anesthesia and other supplies). {missing_summary}See the
[case audit](case_audit.csv) and [implant lineage](implant_lineage.csv) for all affected records.
Price completeness does not determine recurrence eligibility.

## Recurrence through day 365

An event is a recorded diagnosis from the index date (day 0) through postoperative day 365, inclusive. Eligible cases have a
mature window at the cutoff and documented observation through day 365. This rule applies
to cases with early recorded events too. Recurrence after day 365 counts as zero for this endpoint.
Missing or short follow-up can bias complete-case estimates.

{estimates_table(recurrence, is_cost=False)}

{strata_table(recurrence, is_cost=False)}

### Sensitivity to incomplete follow-up

For cases with a mature window, an observed in-window recurrence establishes an event
even with shorter follow-up. The lower bound sets every remaining unknown to no recurrence.
The upper bound sets every unknown to recurrence. These are crude missing-outcome bounds
conditional on the recorded data, without adjustment or sampling uncertainty.

{follow_up_bounds(cases)}

## Cohort accounting

Each case has one status per endpoint. The elective procedure and preoperative factors
filters precede endpoint-specific eligibility checks. Patients need a documented yes or no
for preoperative diabetes. Unknown status excludes a case from both comparisons. Counts
below start from all index cases.

### Cost status

{cohort_table(cases, "cost_status")}

### Recurrence status

{cohort_table(cases, "outcome_status")}

## Standardization and precision

Each stratum combines documented preoperative diabetes status with a surgical risk category.
Assign risk categories in order of precedence. First assign cases with prior repair and a
defect of at least 8 cm. Next assign remaining cases with prior repair or a defect of at
least 5 cm. The last category contains all remaining cases.
Each endpoint keeps joint strata with at least {MIN_PER_GROUP} eligible cases in each group.

{overlap_loss_table(cost, recurrence)}

For each group, multiply its stratum estimates by the pooled eligible case shares in the retained
strata and sum. Both mesh groups use the same target proportions for each combination of
diabetes status and surgical risk. The overlap crude rows show the comparison before
reweighting those same cases. Zero-weight strata fall outside the adjusted population.
Differences use unrounded estimates.

The 95% percentile intervals use {BOOTSTRAP_REPLICATES:,} case-level resamples within each
group, also within each retained stratum for the standardized estimate. Standardization
weights are held fixed. Sparse events can make these intervals unstable or too narrow,
especially in cells with zero events. The adjusted results describe associations in the
overlap cohort. Diabetes is the sole comorbidity captured in the fixture. Other health
differences and informative follow-up may bias estimates. This invented sample cannot
establish clinical or purchasing performance.

## Pack-price error

{pack_example(cases)}

## Reproducing the audit

- Catalog file: `{price_file}`
- SHA-256: `{digest}`
- A match requires the same device and a service date in the half-open effective interval.
  Multiply USD cents per each by quantity, then sum extensions and the other cost lines per case.
- [Implant lineage](implant_lineage.csv) links each implant to the price CSV line, effective dates
  and source. Blank price fields denote unmatched lines or open interval ends, as indicated by status.
- [Other cost lines](other_cost_lines.csv) retain the source cost categories.
- [Case audit](case_audit.csv) records eligibility, totals and outcome inputs. A blank total means
  a complete case cost is unavailable. Other cost cents sum the recorded components,
  and the audit lists any required categories that are absent. A blank endpoint means
  the case was excluded from the primary recurrence comparison.
"""
    (folder / "report.md").write_text(report, encoding="utf-8")

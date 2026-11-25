# Run a different synthetic cohort

From the repository root, run the three-case example with Python 3.11 or newer.

```sh
python3 -m surgical --cohort data/alternate_cohort.json
```

Open `build/cohort/report.md` and `build/cohort/case_audit.csv`. Case ALT-1 uses two
MESH-A devices at $120 each. Its $2,200 in other recorded costs brings the case
total to $2,440. ALT-3 has an unpriced supply and 64 days of follow-up. Each
endpoint therefore marks its own reason for exclusion. The remaining two
surgeries permit a crude comparison. No stratum reaches the five-per-group
threshold for standardization.

Use `--prices PATH` for an independent device price CSV and `--output DIR` to
select a results directory. The report identifies its input files and hashes.
The companion inguinal coding example always uses the separate series in
`data/matching/`. The pack-price illustration belongs to the built-in cohort.

## File contract

[The complete example](../data/alternate_cohort.json) is UTF-8 JSON. The root
object has an `as_of` date and a nonempty `cases` array. Each case represents a
different fictional patient’s index surgery. Use calendar dates in `YYYY-MM-DD`
format and submit only information recorded by the cutoff.

| Field | Meaning |
|---|---|
| `case_id`, `patient_id` | Unique, nonempty strings within their respective fields. |
| `service_date`, `procedure` | Date of surgery and procedure label. The comparison admits `elective ventral hernia repair`. Other labels receive a scope exclusion. |
| `mesh` | `MESH-A` or `MESH-B`. The implant lines must support the declared group. |
| `implants` | Array of objects with a case-unique `line_id`, `device_id`, and positive integer `quantity_each`. Other devices can contribute cost. |
| `other_cost_cents` | Object with nonnegative integer USD cents for each recorded component. Recognized keys are `OR labor and room` and `Anesthesia and other supplies`. Omit a missing category to flag incomplete cost. An explicit zero is a recorded amount. |
| `preoperative` | Optional object with boolean `prior_repair`, positive whole-centimeter `defect_cm`, and boolean or null `diabetes`. Missing factors and unknown diabetes have explicit exclusion reasons. |
| `observed_through` | Optional last documented date of observation, from surgery through the cutoff. Omit or use null when follow-up is unavailable. |
| `diagnosed_on` | Optional date of the first recorded recurrence, from surgery through the cutoff. The primary endpoint applies the 365-day observation rule to both groups. |

The CLI rejects unknown fields, repeated JSON keys, incompatible implant groups,
duplicate lines, invalid units, and dates outside the analysis contract before
writing a report. Accepted cases with incomplete price, component cost, baseline
or follow-up evidence appear in the audit.

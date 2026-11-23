# Surgical case cost and outcomes

**Synthetic elective ventral hernia repair cohort · 113 index surgeries · Data cutoff 2026-11-23**

The comparison asks how recorded index surgery cost and 365-day recurrence differ between
two fictional mesh groups when both are evaluated on the same mix of measured preoperative factors.

## Index surgery cost

Cost combines matched implant purchase prices and recorded operating room, anesthesia and
other supply costs. The analysis covers the index surgery and uses no billed charges.
It omits overhead beyond the modeled items, later care, and payer reimbursement.

| Population and estimate | A n | B n | MESH-A | MESH-B | B − A | 95% bootstrap interval |
|---|---:|---:|---:|---:|---:|---:|
| All eligible, crude | 53 | 56 | $4,412.36 | $4,560.65 | +$148.29 | +$116.25 to +$181.23 |
| Overlap only, crude | 53 | 50 | $4,412.36 | $4,541.47 | +$129.11 | +$98.00 to +$159.08 |
| Overlap only, standardized | 53 | 50 | $4,451.32 | $4,503.17 | +$51.86 | +$29.09 to +$75.32 |

| Surgical risk and preoperative diabetes | A n and mean cost | B n and mean cost | Pooled overlap weight |
|---|---:|---:|---:|
| No prior repair, <5 cm · diabetes no | 34 · $4,378.43 | 6 · $4,436.33 | 38.8% |
| No prior repair, <5 cm · diabetes yes | 7 · $4,377.86 | 6 · $4,430.58 | 12.6% |
| Prior repair or ≥5 cm · diabetes no | 6 · $4,528.08 | 14 · $4,574.43 | 19.4% |
| Prior repair or ≥5 cm · diabetes yes | 6 · $4,529.17 | 24 · $4,576.25 | 29.1% |
| Prior repair, ≥8 cm · diabetes yes | 0 · — | 6 · $4,720.50 | 0.0% |

A case needs an effective-date price for every implant line and both modeled other cost
components (OR labor and room, and anesthesia and other supplies). Unpriced eligible cases include S011. See the
[case audit](case_audit.csv) and [implant lineage](implant_lineage.csv) for all affected records.
Price completeness does not determine recurrence eligibility.

## Recurrence through day 365

An event is a recorded diagnosis from the index date (day 0) through postoperative day 365, inclusive. Eligible cases have a
mature window at the cutoff and documented observation through day 365. This rule applies
to cases with early recorded events too. Recurrence after day 365 counts as zero for this endpoint.
Missing or short follow-up can bias complete-case estimates.

| Population and estimate | A n | B n | MESH-A | MESH-B | B − A | 95% bootstrap interval |
|---|---:|---:|---:|---:|---:|---:|
| All eligible, crude | 52 | 54 | 15.4% | 24.1% | +8.7 pp | -6.3 pp to +23.7 pp |
| Overlap only, crude | 52 | 48 | 15.4% | 20.8% | +5.4 pp | -10.4 pp to +21.3 pp |
| Overlap only, standardized | 52 | 48 | 21.3% | 14.3% | -7.0 pp | -23.6 pp to +9.1 pp |

| Surgical risk and preoperative diabetes | A events / n | B events / n | Pooled overlap weight |
|---|---:|---:|---:|
| No prior repair, <5 cm · diabetes no | 3/32 | 0/6 | 38.0% |
| No prior repair, <5 cm · diabetes yes | 1/8 | 1/6 | 14.0% |
| Prior repair or ≥5 cm · diabetes no | 2/6 | 3/12 | 18.0% |
| Prior repair or ≥5 cm · diabetes yes | 2/6 | 6/24 | 30.0% |
| Prior repair, ≥8 cm · diabetes yes | 0/0 | 3/6 | 0.0% |

### Sensitivity to incomplete follow-up

For cases with a mature window, an observed in-window recurrence establishes an event
even with shorter follow-up. The lower bound sets every remaining unknown to no recurrence.
The upper bound sets every unknown to recurrence. These are crude missing-outcome bounds
conditional on the recorded data, without adjustment or sampling uncertainty.

| Mesh | Mature n | Known events with complete follow-up | Additional known events | Unknown | Risk bounds |
|---|---:|---:|---:|---:|---:|
| MESH-A | 53 | 8 | 1 | 0 | 17.0% to 17.0% |
| MESH-B | 56 | 13 | 0 | 2 | 23.2% to 26.8% |

## Cohort accounting

Each case has one status per endpoint. The elective procedure and preoperative factors
filters precede endpoint-specific eligibility checks. Patients need a documented yes or no
for preoperative diabetes. Unknown status excludes a case from both comparisons. Counts
below start from all index cases.

### Cost status

| Status | MESH-A | MESH-B |
|---|---:|---:|
| Included | 53 | 56 |
| Missing preoperative factors | 1 | 0 |
| Outside procedure scope | 0 | 1 |
| Unknown preoperative diabetes status | 1 | 0 |
| Unpriced implant lines | 1 | 0 |

### Recurrence status

| Status | MESH-A | MESH-B |
|---|---:|---:|
| Included | 52 | 54 |
| Follow-up short of 365 days | 1 | 1 |
| Missing preoperative factors | 1 | 0 |
| No follow-up record | 0 | 1 |
| Outside procedure scope | 0 | 1 |
| Unknown preoperative diabetes status | 1 | 0 |
| Window not mature | 1 | 0 |

## Standardization and precision

Each stratum combines documented preoperative diabetes status with a surgical risk category.
Assign risk categories in order of precedence. First assign cases with prior repair and a
defect of at least 8 cm. Next assign remaining cases with prior repair or a defect of at
least 5 cm. The last category contains all remaining cases.
Each endpoint keeps joint strata with at least 5 eligible cases in each group.

| Endpoint | MESH-A eligible → overlap | MESH-B eligible → overlap | A outside overlap | B outside overlap |
|---|---:|---:|---:|---:|
| Index cost | 53 → 53 | 56 → 50 | 0 | 6 |
| Recurrence | 52 → 52 | 54 → 48 | 0 | 6 |

For each group, multiply its stratum estimates by the pooled eligible case shares in the retained
strata and sum. Both mesh groups use the same target proportions for each combination of
diabetes status and surgical risk. The overlap crude rows show the comparison before
reweighting those same cases. Zero-weight strata fall outside the adjusted population.
Differences use unrounded estimates.

The 95% percentile intervals use 5,000 case-level resamples within each
group, also within each retained stratum for the standardized estimate. Standardization
weights are held fixed. Sparse events can make these intervals unstable or too narrow,
especially in cells with zero events. The adjusted results describe associations in the
overlap cohort. Diabetes is the sole comorbidity captured in the fixture. Other health
differences and informative follow-up may bias estimates. This invented sample cannot
establish clinical or purchasing performance.

## Pack-price error

In the synthetic invoice, a pack of 6 MESH-A implants costs $720.00, or $120.00 per implant. Case S001 (2025-01-18) used 1. The error scenario treats the pack price as the per-implant price on that one line. The matched row (CSV line 2) prices each implant at $120.00. Holding other lines and case costs fixed, the matched total is **$4,304.50** and the erroneous total is **$4,904.50** (change +600.00 USD).

## Reproducing the audit

- Catalog file: `device_prices.csv`
- SHA-256: `193bef97f97a51c2d1257d9a23682dd287a014ce4ecaace6fce8ec59cd2f3886`
- A match requires the same device and a service date in the half-open effective interval.
  Multiply USD cents per each by quantity, then sum extensions and the other cost lines per case.
- [Implant lineage](implant_lineage.csv) links each implant to the price CSV line, effective dates
  and source. Blank price fields denote unmatched lines or open interval ends, as indicated by status.
- [Other cost lines](other_cost_lines.csv) retain the source cost categories.
- [Case audit](case_audit.csv) records eligibility, totals and outcome inputs. A blank total means
  a complete case cost is unavailable. Other cost cents sum the recorded components,
  and the audit lists any required categories that are absent. A blank endpoint means
  the case was excluded from the primary recurrence comparison.

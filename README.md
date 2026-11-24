# Surgical case cost and outcomes

A reproducible comparison of two fictional meshes in 113 invented ventral hernia repairs. Trace an implant from its purchase price to the case total, then see how cost and recurrence estimates change when the mesh groups have a comparable mix of patients. A second, independent series of 19 fictional inguinal repairs demonstrates coded eligibility and 30-day follow-up.

## Follow a purchase price into the operating room

One box of six MESH-A implants goes from **$720 to $726** on synthetic PO-100. The associated invoice, INV-380, goes from **$120 to $121 per implant**. The purchasing reconciler exports the revised price as 12,100 cents per implant. Case S001 uses one implant, so its total goes from **$4,304.50 to $4,305.50**. Across the ventral series, exactly **55 of 113 case totals** increase by $1. [Baseline implant lines](outputs/implant_lineage.csv) · [Case totals](outputs/case_audit.csv)

With `hospital-purchasing-reconciliation` checked out beside this repository, run the walkthrough from here:

```sh
python3 examples/check_purchasing_handoff.py
```

The script changes temporary copies of the PO, its replay and the invoice. It runs the purchasing reconciler, verifies the source references in the exported price evidence, and passes the catalog to the surgical CLI. It checks every case against its implanted quantity. Use `--purchasing PATH` for a different checkout location. [Walkthrough code](examples/check_purchasing_handoff.py)

Once both repositories are public under the same GitHub owner, **Actions → Verify demo → Run workflow** runs the handoff as well as the surgical tests. Pushes and pull requests run the standalone surgical checks.

## Two cases worth inspecting

- **G19 looks like an initial repair on the operating list.** Its label matches the other 18 operations. The diagnosis and procedure codes on the same account and date both identify a recurrent repair. Excluding G19 reduces the number of potential same-surgeon, same-side pairs from seven to six. [Operative rows](data/matching/operations.csv) · [Billing rows](data/matching/billing.csv) · [Case-level decisions](outputs/coded_cases.csv)
- **G04 returned to hospital on day 8.** Six potential pairs become five with prices on both sides and three with both prices and observable 30-day outcomes. In G04’s group, three MESH-B patients could match one MESH-A patient. One MESH-B patient returned. A one-to-one pairing can contain zero or one return depending on who is chosen. [Follow-up records](data/matching/follow_up.csv) · [Group counts and event bounds](outputs/matching_review.md)

## Run

From this directory, with Python 3.11 or newer and no third-party packages:

```sh
python3 -m surgical
python3 -m surgical --prices /path/to/device_prices.csv --output /path/to/results
python3 -m unittest discover -s tests
```

The default run recreates the checked-in files in [outputs](outputs/).
Set `--output` to keep a custom-price run alongside them.

## Ventral repair costs and 365-day recurrence

![Crude and standardized differences in index surgery cost and recurrence for the synthetic ventral repair cohort](docs/case-comparison.png)

The [demo report](outputs/report.md) shows that MESH-B costs **$148.29 more
per case** in the crude comparison and **$51.86 more** after standardizing
for documented preoperative diabetes and surgical risk within the overlap cohort.
The recurrence difference moves from **+8.7 percentage points** crude to **−7.0 points**
standardized, with a wide interval of **−23.6 to +9.1 points**. The report also bounds crude recurrence risk across
all mature cases, accounting for a known event in a case with short follow-up.
The adjusted comparisons describe
associations under the synthetic design. Unknown diabetes status excludes one case from
both comparisons. Retained strata have at least five eligible cases per group,
which leaves six MESH-B cases outside overlap for both endpoints.

The [implant lineage](outputs/implant_lineage.csv) traces quantity, price row,
effective dates and extended cents for each implant. It shows why case S011
has no total cost while remaining eligible for recurrence. The [other cost
lines](outputs/other_cost_lines.csv) and [case audit](outputs/case_audit.csv)
reconstruct the case totals and analysis denominators. Case S001 illustrates
a **$600.00 overstatement** when a six-pack price is copied into a
per-implant field.

## Price input contract

The included [device_prices.csv](data/device_prices.csv) has the exact UTF-8 header:

```csv
device_id,effective_from,effective_to,unit_price_cents,currency,price_source
```

A row applies from its ISO date `effective_from` through the day before
`effective_to`. Leave the end blank for an open interval. Use integer USD
cents per implant and a populated source. Adjacent intervals are valid.
Overlapping intervals or malformed prices stop the run before output is written.
An uncovered device or date leaves its implant line and case total unpriced.
The demo includes MESH-A at $120.00 each and MESH-B at $175.00 each, both
effective January 1, 2025 with source `reconciled_invoice`.

[Fixture source](surgical/fixture.py) contains the independently invented
source records. [Analysis](surgical/analysis.py) defines case eligibility and
aggregation, pooled direct standardization, and fixed-seed bootstrap intervals.

The optional [figure script](examples/plot_comparison.py) redraws the README chart from the analysis. With Matplotlib installed, run `python3 -m examples.plot_comparison` from this directory.

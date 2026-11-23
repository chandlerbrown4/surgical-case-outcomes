# Surgical case cost and outcomes

A reproducible portfolio demo using 113 invented ventral hernia repair cases.
It links implant purchase prices, other index-case costs, preoperative factors,
follow-up and recurrence to compare two fictional mesh groups.

![Crude and standardized differences in index surgery cost and recurrence for the synthetic cohort](docs/case-comparison.png)

## Run

From this directory, with Python 3.11 or newer and no third-party packages:

```sh
python3 -m surgical
python3 -m surgical --prices /path/to/device_prices.csv --output /path/to/results
python3 -m unittest discover -s tests
```

The default run recreates the checked-in files in [outputs](outputs/).
Set `--output` to keep a custom-price run alongside them.

With the purchasing project checked out as a sibling, run the live catalog
handoff and repricing check with `python3 examples/check_purchasing_handoff.py`.
It accepts `--purchasing PATH` for a different checkout location.

## Start with the report

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

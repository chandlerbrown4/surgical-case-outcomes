"""Run the demo without external dependencies."""

import argparse
import csv
from pathlib import Path

from .analysis import build_cases, compare
from .cohort import load_cohort
from .fixture import make_fixture
from .matching import write_matching_review
from .prices import load_catalog
from .report import write_outputs

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prices", type=Path, default=ROOT / "data/device_prices.csv")
    parser.add_argument("--cohort", type=Path, help="local synthetic cohort JSON")
    parser.add_argument("--output", type=Path, help="directory for the report and audit tables")
    args = parser.parse_args()

    try:
        catalog = load_catalog(args.prices)
    except (OSError, ValueError, csv.Error) as exc:
        parser.exit(2, f"Price input error: {exc}\n")

    try:
        data, cohort_digest = load_cohort(args.cohort) if args.cohort else (make_fixture(), None)
        cases = build_cases(data, catalog)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Cohort input error: {exc}\n")

    output = args.output or (ROOT / "build/cohort" if args.cohort else ROOT / "outputs")
    cost = compare(cases, lambda case: case.cost)
    recurrence = compare(cases, lambda case: case.outcome)
    write_outputs(output, args.prices.name, catalog.sha256, cases, data, cost, recurrence,
                  cohort_file=args.cohort.name if args.cohort else None, cohort_sha256=cohort_digest)
    write_matching_review(output, ROOT / "data" / "matching", catalog)
    print(f"Surgical case analysis written to {output.resolve() / 'report.md'}")


if __name__ == "__main__":
    main()

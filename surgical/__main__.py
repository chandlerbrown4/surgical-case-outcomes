"""Run the demo without external dependencies."""

import argparse
import csv
from pathlib import Path

from .analysis import build_cases, compare
from .fixture import make_fixture
from .matching import write_matching_review
from .prices import load_catalog
from .report import write_outputs

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prices", type=Path, default=ROOT / "data/device_prices.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs")
    args = parser.parse_args()

    try:
        catalog = load_catalog(args.prices)
    except (OSError, ValueError, csv.Error) as exc:
        parser.exit(2, f"Price input error: {exc}\n")

    data = make_fixture()
    cases = build_cases(data, catalog)
    cost = compare(cases, lambda case: case.cost)
    recurrence = compare(cases, lambda case: case.outcome)
    write_outputs(args.output, args.prices.name, catalog.sha256, cases, data, cost, recurrence)
    write_matching_review(args.output, ROOT / "data" / "matching", catalog)
    print(f"Surgical case analysis written to {args.output.resolve() / 'report.md'}")


if __name__ == "__main__":
    main()

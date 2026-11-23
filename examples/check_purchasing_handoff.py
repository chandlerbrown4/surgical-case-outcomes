"""Exercise the purchasing and surgical CLIs together using only temporary outputs."""

import argparse
import csv
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

SURGICAL = Path(__file__).resolve().parents[1]


def run(repo, module, *args):
    subprocess.run([sys.executable, "-m", module, *args], cwd=repo, check=True)


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def cases(output):
    return {row["case_id"]: row for row in read_csv(output / "case_audit.csv")}


def check(purchasing, work):
    prices = work / "purchasing" / "device_prices.csv"
    run(purchasing, "purchasing", "--output", prices.parent)
    baseline_dir = work / "baseline"
    run(SURGICAL, "surgical", "--prices", prices, "--output", baseline_dir)
    baseline = cases(baseline_dir)

    # Both the standalone demo and the live handoff should reproduce the case audit.
    standalone_dir = work / "standalone"
    run(SURGICAL, "surgical", "--output", standalone_dir)
    if not baseline or baseline != cases(standalone_dir):
        raise ValueError("Live purchasing prices did not reproduce the standalone case audit")

    repriced = work / "price_change.csv"
    catalog = read_csv(prices)
    for row in catalog:
        if row["device_id"] == "MESH-A":
            row["unit_price_cents"] = str(int(row["unit_price_cents"]) + 100)
    with repriced.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=catalog[0].keys())
        writer.writeheader()
        writer.writerows(catalog)

    quantities = {}
    for line in read_csv(baseline_dir / "implant_lineage.csv"):
        if line["device_id"] == "MESH-A":
            case_id = line["case_id"]
            quantities[case_id] = quantities.get(case_id, 0) + int(line["quantity_each"])
    changed_dir = work / "repriced"
    run(SURGICAL, "surgical", "--prices", repriced, "--output", changed_dir)
    changed = cases(changed_dir)
    if changed.keys() != baseline.keys():
        raise ValueError("A price change altered case membership")
    affected = 0
    for case_id, before in baseline.items():
        expected = before.copy()
        if before["case_total_cents"] and quantities.get(case_id):
            delta = 100 * quantities[case_id]
            expected["case_total_cents"] = str(int(before["case_total_cents"]) + delta)
            affected += 1
        if changed[case_id] != expected:
            raise ValueError(f"Unexpected change in the case audit for {case_id}")
    if not affected:
        raise ValueError("The price change did not reach any fully costed MESH-A cases")
    print(f"Verified {len(baseline)} case records. A $1 per-unit increase repriced {affected} cases.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--purchasing", type=Path,
                        default=SURGICAL.parent / "hospital-purchasing-reconciliation",
                        help="path to a checkout of the purchasing project")
    args = parser.parse_args()
    with TemporaryDirectory() as directory:
        check(args.purchasing.resolve(), Path(directory))

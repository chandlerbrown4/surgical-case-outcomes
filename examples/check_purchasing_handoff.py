"""Exercise the purchasing and surgical CLIs together using only temporary outputs."""

import argparse
import csv
import shutil
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


def change_source_rate(path, event_id, rate):
    rows = read_csv(path)
    id_column, rate_column = ("event_id", "unit_price") if "event_id" in rows[0] else ("record_id", "price")
    matches = [row for row in rows if row[id_column] == event_id]
    if len(matches) != 1:
        raise ValueError(f"Expected one purchasing fixture row for {event_id}")
    matches[0][rate_column] = rate
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


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

    fixture = work / "fixtures"
    shutil.copytree(purchasing / "fixtures", fixture)
    initial = fixture / "01_initial"
    change_source_rate(initial / "po_lines.csv", "P-A", "726.00")
    # P-A is also replayed under the second batch's alternate headers.
    change_source_rate(fixture / "02_followup" / "po_lines.csv", "P-A", "726")
    change_source_rate(initial / "invoices.csv", "I-A1", "121.00")
    revised_purchases = work / "changed_purchasing"
    run(purchasing, "purchasing", initial, fixture / "02_followup", "--mappings", fixture,
        "--output", revised_purchases)
    repriced = revised_purchases / "device_prices.csv"
    expected_catalog = read_csv(prices)
    mesh_rows = [row for row in expected_catalog if row["device_id"] == "MESH-A"]
    if len(mesh_rows) != 1 or mesh_rows[0]["unit_price_cents"] != "12000":
        raise ValueError("Expected a baseline MESH-A price of $120.00")
    mesh_rows[0]["unit_price_cents"] = "12100"
    if read_csv(repriced) != expected_catalog:
        raise ValueError("Reconciled catalog did not reflect the source price change")
    evidence = [row for row in read_csv(revised_purchases / "device_price_evidence.csv")
                if row["device_id"] == "MESH-A"]
    if len(evidence) != 1 or (evidence[0]["po_event_id"], evidence[0]["invoice_event_id"]) != ("P-A", "I-A1"):
        raise ValueError("Repriced catalog lost its source PO or invoice")

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
    print("PO-100 (six per box): $720.00 -> $726.00. INV-380 and exported MESH-A: $120.00 -> $121.00 each.")
    old = int(baseline["S001"]["case_total_cents"])
    new = int(changed["S001"]["case_total_cents"])
    print(f"S001 total: ${old / 100:,.2f} -> ${new / 100:,.2f}.")
    if affected != 55 or (old, new) != (430450, 430550):
        raise ValueError("Case totals differ from the published synthetic walkthrough")
    print(f"Verified {len(baseline)} case records. A $1 per-unit increase repriced {affected} cases.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--purchasing", type=Path,
                        default=SURGICAL.parent / "hospital-purchasing-reconciliation",
                        help="path to a checkout of the purchasing project")
    args = parser.parse_args()
    with TemporaryDirectory() as directory:
        check(args.purchasing.resolve(), Path(directory))

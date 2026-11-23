import csv
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from fractions import Fraction
from pathlib import Path

from surgical.analysis import build_cases, compare
from surgical.fixture import OTHER_COST_CATEGORIES, Recurrence, make_fixture
from surgical.prices import HEADER, load_catalog

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "data/device_prices.csv"


def read_rows(path):
    with path.open(encoding="utf-8", newline="") as data:
        return list(csv.DictReader(data))


class CatalogTests(unittest.TestCase):
    def test_half_open_match_and_price_lineage(self):
        catalog = load_catalog(DEMO)
        self.assertIsNone(catalog.match("FIX-1", date(2024, 12, 31)))
        june = catalog.match("FIX-1", date(2025, 6, 30))
        july = catalog.match("FIX-1", date(2025, 7, 1))
        self.assertEqual((june.cents, june.row), (2100, 4))
        self.assertEqual((july.cents, july.row), (2400, 5))
        self.assertIsNone(catalog.match("FIX-UNLISTED", date(2025, 7, 1)))
        self.assertEqual(catalog.match("MESH-B", date(2026, 11, 23)).source,
                         "reconciled_invoice")

    def test_invalid_catalogs(self):
        base = "MESH-A,2025-01-01,,12000,USD,reconciled_invoice"
        records = [
            base + "\nMESH-A,2024-12-31,2025-01-02,10,USD,prior",
            base + "\n" + base,
            base.replace("12000", "120.00"),
            base.replace("12000", "-1"),
            base.replace("USD", "CAD"),
            base.replace("2025-01-01", "20250101"),
            base.replace("2025-01-01,,", "2025-01-01,2025-01-01,"),
            base.replace("reconciled_invoice", ""),
        ]
        with tempfile.TemporaryDirectory() as folder:
            price_path = Path(folder) / "device_prices.csv"
            for content in records:
                with self.subTest(content=content):
                    price_path.write_text(",".join(HEADER) + "\n" + content + "\n", encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_catalog(price_path)
            price_path.write_text("wrong,header\n" + base + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "expected header"):
                load_catalog(price_path)


class AnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = build_cases(make_fixture(), load_catalog(DEMO))
        cls.by_id = {case.surgery.case_id: case for case in cls.cases}

    def test_pack_case_and_unpriced_case(self):
        pack = self.by_id["S001"]
        self.assertEqual([line.extended_cents for line in pack.line_items], [12000, 4200])
        self.assertEqual(pack.other_cost_cents, 414250)
        self.assertEqual(pack.total_cents, 430450)
        missing = self.by_id["S011"]
        self.assertIsNone(missing.total_cents)
        self.assertEqual(missing.cost_status, "unpriced implant lines")
        self.assertEqual(missing.outcome, 0)

    def test_outcome_window_and_scope(self):
        self.assertEqual(self.by_id["S001"].outcome, 1)  # Diagnosed on day 365.
        self.assertEqual(self.by_id["S005"].outcome, 0)  # Diagnosed on day 366.
        cases = [self.by_id[f"S{number}"] for number in range(107, 113)]
        self.assertEqual([case.outcome_status for case in cases], [
            "follow-up short of 365 days", "follow-up short of 365 days", "no follow-up record",
            "window not mature", "missing preoperative factors", "outside procedure scope",
        ])
        self.assertIsNotNone(cases[0].diagnosed_on)
        self.assertIsNone(cases[0].outcome)

    def test_unknown_diabetes_excludes_both_comparisons(self):
        case = self.by_id["S113"]
        self.assertEqual(case.diabetes_status, "unknown")
        self.assertIsNone(case.stratum)
        self.assertEqual(case.cost_status, "unknown preoperative diabetes status")
        self.assertEqual(case.outcome_status, case.cost_status)
        self.assertIsNotNone(case.total_cents)
        self.assertIsNone(case.cost)
        self.assertIsNone(case.outcome)

    def test_recurrence_on_index_date_is_included_and_earlier_dates_rejected(self):
        data = make_fixture()
        case_id = "S001"
        service_date = data.surgeries[0].service_date
        catalog = load_catalog(DEMO)
        data.recurrences[case_id] = Recurrence(case_id, service_date)
        self.assertEqual(build_cases(data, catalog)[0].outcome, 1)

        data.recurrences[case_id] = Recurrence(case_id, service_date - timedelta(days=1))
        with self.assertRaisesRegex(ValueError, "S001: recurrence diagnosis precedes index surgery"):
            build_cases(data, catalog)

    def test_required_other_cost_components(self):
        catalog = load_catalog(DEMO)
        for removed in ((OTHER_COST_CATEGORIES[0],), (OTHER_COST_CATEGORIES[1],),
                        OTHER_COST_CATEGORIES):
            with self.subTest(removed=removed):
                data = make_fixture()
                data.other_costs = [
                    line for line in data.other_costs
                    if line.case_id != "S001" or line.category not in removed
                ]
                case = build_cases(data, catalog)[0]
                self.assertEqual(case.missing_other_cost_categories, removed)
                self.assertEqual(case.cost_status, "missing other cost components")
                self.assertTrue(all(line.price is not None for line in case.line_items))
                self.assertIsNone(case.total_cents)
                self.assertIsNone(case.cost)
                self.assertEqual(case.outcome, 1)

    def test_standardized_point_estimates(self):
        comparison = compare(self.cases, lambda case: case.outcome)
        self.assertEqual(tuple(map(len, comparison.values)), (52, 54))
        self.assertAlmostEqual(comparison.crude.difference, Fraction(13, 54) - Fraction(8, 52))
        # Recompute from the joint diabetes/surgical-risk denominators.
        weights = [Fraction(n, 100) for n in (38, 14, 18, 30)]
        a_rates = [Fraction(3, 32), Fraction(1, 8), Fraction(2, 6), Fraction(2, 6)]
        b_rates = [Fraction(0, 6), Fraction(1, 6), Fraction(3, 12), Fraction(6, 24)]
        a = sum(weight * rate for weight, rate in zip(weights, a_rates))
        b = sum(weight * rate for weight, rate in zip(weights, b_rates))
        self.assertAlmostEqual(comparison.adjusted.difference, b - a)
        self.assertEqual([cell.weight for cell in comparison.strata], [.38, .14, .18, .30, 0])
        self.assertEqual(tuple(map(len, comparison.strata[-1].values)), (0, 6))
        lo, hi = comparison.adjusted.interval
        self.assertLess(lo, 0)
        self.assertGreater(hi, 0)


class DemoTests(unittest.TestCase):
    def run_demo(self, output, *args):
        return subprocess.run(
            [sys.executable, "-m", "surgical", "--output", str(output), *args],
            cwd=ROOT, capture_output=True, text=True, check=True,
        )

    def test_default_demo_is_reproducible_and_reconciles(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            self.run_demo(output)
            for path in output.iterdir():
                self.assertEqual(path.read_bytes(), (ROOT / "outputs" / path.name).read_bytes())
            report = (output / "report.md").read_text(encoding="utf-8")
            self.assertIn("| MESH-A | 53 | 8 | 1 | 0 | 17.0% to 17.0% |", report)
            self.assertIn("| MESH-B | 56 | 13 | 0 | 2 | 23.2% to 26.8% |", report)
            self.assertIn("a pack of 6 MESH-A implants costs $720.00", report)
            self.assertIn("**$4,904.50** (change +600.00 USD)", report)
            lines = read_rows(output / "implant_lineage.csv")
            costs = read_rows(output / "other_cost_lines.csv")
            cases = read_rows(output / "case_audit.csv")
            self.assertEqual(len(cases), 113)
            self.assertEqual(len(lines), 227)
            self.assertEqual({row["preoperative_diabetes"] for row in cases}, {"yes", "no", "unknown"})
            self.assertIn("| Index cost | 53 → 53 | 56 → 50 | 0 | 6 |", report)
            self.assertIn("| Recurrence | 52 → 52 | 54 → 48 | 0 | 6 |", report)
            case_costs = {}
            for case in cases:
                key = case["case_id"]
                implant_costs = [line["extended_cents"] for line in lines if line["case_id"] == key]
                other_costs = [int(line["cost_cents"]) for line in costs if line["case_id"] == key]
                if "" in implant_costs:
                    self.assertEqual(case["case_total_cents"], "")
                    continue
                total = sum(map(int, implant_costs)) + sum(other_costs)
                self.assertEqual(int(case["case_total_cents"]), total)
                case_costs[key] = total
            self.assertEqual(case_costs["S001"], 430450)

    def test_explicit_catalog_changes_case_costs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            price_path = root / "device_prices.csv"
            price_path.write_text(DEMO.read_text(encoding="utf-8").replace("12000", "12100"),
                                  encoding="utf-8")
            output = root / "run"
            self.run_demo(output, "--prices", str(price_path))
            first = read_rows(output / "case_audit.csv")[0]
            self.assertEqual(first["case_total_cents"], "430550")
            self.assertEqual(first["recurrence_by_day_365"], "1")

    def test_shared_input_with_only_required_demo_devices(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            price_path = root / "device_prices.csv"
            price_path.write_bytes(b"\n".join(DEMO.read_bytes().splitlines()[:3]) + b"\n")
            output = root / "run"
            self.run_demo(output, "--prices", str(price_path))
            cases = read_rows(output / "case_audit.csv")
            self.assertEqual(sum(row["cost_status"] == "unpriced implant lines" for row in cases), 110)
            self.assertEqual(sum(row["outcome_status"] == "included" for row in cases), 106)
            self.assertIn("case-level comparison is unavailable", (output / "report.md").read_text())


if __name__ == "__main__":
    unittest.main()

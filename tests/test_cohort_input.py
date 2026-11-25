import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from surgical.cohort import load_cohort


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "data/alternate_cohort.json"


class CohortInputTests(unittest.TestCase):
    def test_cli_uses_external_cohort_costs_dates_and_denominators(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            subprocess.run([sys.executable, "-m", "surgical", "--cohort", str(EXAMPLE),
                            "--output", str(output)], cwd=ROOT, check=True, capture_output=True)
            with (output / "case_audit.csv").open(newline="", encoding="utf-8") as stream:
                first, second, third = csv.DictReader(stream)
            self.assertEqual((first["case_id"], first["case_total_cents"]), ("ALT-1", "244000"))
            self.assertEqual(second["recurrence_by_day_365"], "1")
            self.assertEqual(third["cost_status"], "unpriced implant lines")
            self.assertEqual(third["outcome_status"], "follow-up short of 365 days")
            report = (output / "report.md").read_text(encoding="utf-8")
            self.assertIn("3 index surgeries · Data cutoff 2026-03-01", report)
            self.assertIn(hashlib.sha256(EXAMPLE.read_bytes()).hexdigest(), report)
            self.assertIn("No stratum has at least 5 eligible cases", report)
            self.assertIn("crude interval is unavailable", report)
            self.assertNotIn("S001", report)

    def test_input_cutoff_controls_maturity_and_sensitivity_denominators(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            records = json.loads(EXAMPLE.read_text(encoding="utf-8"))
            records["cases"] = records["cases"][:1]
            records["as_of"] = records["cases"][0]["observed_through"] = "2025-03-10"
            path = root / "early-cutoff.json"
            path.write_text(json.dumps(records), encoding="utf-8")
            output = root / "results"
            subprocess.run([sys.executable, "-m", "surgical", "--cohort", str(path),
                            "--output", str(output)], cwd=ROOT, capture_output=True, check=True)
            with (output / "case_audit.csv").open(newline="", encoding="utf-8") as stream:
                case = next(csv.DictReader(stream))
            self.assertEqual(case["outcome_status"], "window not mature")
            self.assertIn("| MESH-A | 0 | 0 | 0 | 0 | — |",
                          (output / "report.md").read_text(encoding="utf-8"))

    def test_rejects_broken_link_before_writing_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            records = json.loads(EXAMPLE.read_text(encoding="utf-8"))
            records["cases"][0]["implants"][0]["device_id"] = "MESH-B"
            path = root / "incoherent.json"
            path.write_text(json.dumps(records), encoding="utf-8")
            output = root / "results"
            proc = subprocess.run([sys.executable, "-m", "surgical", "--cohort", str(path),
                                   "--output", str(output)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("Cohort input error: ALT-1: mesh group disagrees", proc.stderr)
            self.assertNotIn("Traceback", proc.stderr)
            self.assertFalse(output.exists())

    def test_rejects_malformed_or_ambiguous_records_with_location(self):
        examples = [
            ("service_date", "2025-02-30", "service_date"),
            ("diagnosed_on", "2024-01-01", "diagnosed_on"),
            ("observed_through", "2027-01-01", "as_of"),
            ("patient_id", "FIC-1", "unique"),
            ("other_cost_cents", {"OR labor and room": -2}, "integer"),
            ("extra_feld", 8, "unknown field"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            for key, value, message in examples:
                with self.subTest(field=key):
                    sample = json.loads(EXAMPLE.read_text(encoding="utf-8"))
                    sample["cases"][1][key] = value
                    path.write_text(json.dumps(sample), encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, f"case 2: .*{message}"):
                        load_cohort(path)

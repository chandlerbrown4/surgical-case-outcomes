from pathlib import Path
from statistics import mean
import unittest

from examples.calibration import REPETITIONS, differences, experiment, render

ROOT = Path(__file__).resolve().parents[1]


class CalibrationTests(unittest.TestCase):
    def test_exact_conditional_null_with_different_risk_mix(self):
        cells = {
            "low": ([1] * 6 + [0] * 54, [1] * 2 + [0] * 18),
            "high": ([1] * 6 + [0] * 14, [1] * 18 + [0] * 42),
        }
        crude, standardized = differences(cells)
        self.assertAlmostEqual(crude, 10.0)
        self.assertAlmostEqual(standardized, 0.0)

    def test_repeatable_calibration_evidence(self):
        results = experiment()
        self.assertTrue(all(len(pairs) == REPETITIONS for pairs in results.values()))
        self.assertLess(abs(mean(adjusted for _, adjusted in results["Complete"])), 1.0)
        self.assertLess(mean(adjusted for _, adjusted in results["Outcome-dependent"]), -5.0)
        self.assertEqual(render(results), (ROOT / "outputs/calibration.md").read_text())

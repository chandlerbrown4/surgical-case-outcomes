from pathlib import Path
import unittest

from examples.event_sensitivity import render, summarize
from surgical.analysis import build_cases, compare
from surgical.fixture import make_fixture
from surgical.prices import load_catalog

ROOT = Path(__file__).resolve().parents[1]


class EventSensitivityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = build_cases(make_fixture(), load_catalog(ROOT / "data/device_prices.csv"))
        cls.baseline, cls.changes = summarize(cls.cases)

    def test_counts_and_one_or_two_event_changes(self):
        for arm, n, events in [(0, 52, 8), (1, 48, 10)]:
            records = [change for change in self.changes if change.arm == arm]
            self.assertEqual(len(records), n)
            self.assertEqual(sum(change.observed for change in records), events)

        # The six non-diabetic MESH-B cases in the small-defect group have 38% target weight.
        for ids in ({"S054"}, {"S054", "S056"}):
            delta = len(ids) * 0.38 / 6
            rerun = compare(self.cases, lambda c: 1 if c.surgery.case_id in ids else c.outcome)
            self.assertEqual(sum(rerun.values[1]), 13 + len(ids))  # Includes nonoverlap strata.
            self.assertAlmostEqual(rerun.adjusted.difference - self.baseline, delta)
            self.assertAlmostEqual(sum(c.effect for c in self.changes if c.case_id in ids), delta)

    def test_published_bounds(self):
        ranked = sorted(c.effect for c in self.changes)
        self.assertAlmostEqual(sum(ranked[:2]), -0.10)
        self.assertAlmostEqual(sum(ranked[-2:]), 2 * 0.38 / 6)
        published = (ROOT / "outputs/event_sensitivity.md").read_text()
        self.assertEqual(render(self.baseline, self.changes), published)

import unittest
from dataclasses import replace
from itertools import combinations
from pathlib import Path

from surgical.matching import INCLUDED, PROCEDURE, group_repairs, load_repairs, observed_return, screen
from surgical.prices import Catalog, load_catalog

DATA = Path(__file__).resolve().parents[1] / "data"


class MatchingExamples(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = load_repairs(DATA / "matching", load_catalog(DATA / "device_prices.csv"))

    def test_routine_label_and_coded_recurrence(self):
        by_id = {r.case_id: r for r in self.cases}
        ordinary, recurrent = by_id["G01"], by_id["G19"]
        self.assertEqual(ordinary.operative_label, recurrent.operative_label)
        self.assertEqual((ordinary.diagnosis_codes, ordinary.repair_codes, ordinary.coding_status),
                         ("K40.90", "49650", INCLUDED))
        self.assertEqual((recurrent.diagnosis_codes, recurrent.repair_codes, recurrent.coding_status),
                         ("K40.91", "49651", "excluded recurrent repair"))
        for dx, cpt in [({"K40.91"}, {"49650"}), ({"K40.90"}, {"49650", "49651"})]:
            self.assertEqual(screen(PROCEDURE, dx, cpt), "excluded recurrent repair")
        self.assertEqual(screen(PROCEDURE, set(), {"49650"}), "review missing or unsupported coding")
        # A label-only screen creates a spurious seventh pair in the Birch/right stratum.
        unchecked = [replace(r, coding_status=INCLUDED) for r in self.cases]
        self.assertEqual(sum(min(g.eligible) for g in group_repairs(unchecked)), 7)

    def test_pair_capacity_and_actual_event_denominators(self):
        groups = group_repairs(self.cases)
        self.assertEqual(sum(min(g.eligible) for g in groups), 6)
        self.assertEqual(sum(min(g.priced) for g in groups), 5)
        self.assertEqual(sum(min(g.observed) for g in groups), 3)
        shared = [g for g in groups if min(g.observed)]
        for arm, expected in enumerate(((0, 3), (1, 5))):
            self.assertEqual((sum(g.events[arm] for g in shared), sum(g.observed[arm] for g in shared)), expected)
        for g in groups:
            for arm in (0, 1):
                # Enumerate actual choices of patients to check the analytic bounds.
                outcomes = [1] * g.events[arm] + [0] * (g.observed[arm] - g.events[arm])
                counts = [sum(choice) for choice in combinations(outcomes, min(g.observed))]
                self.assertEqual(g.event_bounds(arm), (min(counts), max(counts)))
        cedar = next(g for g in shared if (g.surgeon, g.side) == ("Cedar", "right"))
        self.assertEqual((cedar.observed, cedar.event_bounds(1)), ((1, 3), (0, 1)))

    def test_day_30_and_incomplete_observation(self):
        def outcome(through, event):
            return observed_return({"case_id": "demo", "observed_through_day": through, "inpatient_return_day": event})
        self.assertEqual(outcome("30", "30"), 1)
        self.assertEqual(outcome("31", "31"), 0)
        self.assertEqual(outcome("8", "8"), 1)
        self.assertIsNone(outcome("29", ""))
        self.assertIsNone(observed_return(None))
        with self.assertRaises(ValueError):
            outcome("8", "10")

    def test_missing_prices_keep_observed_events(self):
        cases = load_repairs(DATA / "matching", Catalog({}, "test"))
        groups = group_repairs(cases)
        self.assertEqual(sum(min(g.eligible) for g in groups), 6)
        self.assertEqual(sum(min(g.observed) for g in groups), 0)
        self.assertEqual(next(r for r in cases if r.case_id == "G04").return_30d, 1)

"""Z1.9 variables acceptance-sampling calculator tests.

The k/n TABLE CELLS are transcribed and pending verification against a controlled
ANSI/ASQ Z1.9 copy (see the module disclaimer); these tests lock the *mechanism*
(plan lookup wiring + the x̄/s vs k decision math), which is correct regardless of
the exact table values.
"""
from django.test import SimpleTestCase

from Tracker.services.qms.acceptance_sampling import (
    compute_sample_plan,
    evaluate_variables,
)


class Z19PlanDerivationTests(SimpleTestCase):
    def test_z19_plan_wiring(self):
        # lot 120, level II → code letter F → n=10, k=1.72 (encoded table).
        sp = compute_sample_plan(lot_size=120, aql=1.0, inspection_level="II", strategy="Z19")
        self.assertEqual(sp.strategy, "Z19")
        self.assertEqual(sp.method, "K_SINGLE")
        self.assertEqual(sp.sample_size, 10)
        self.assertAlmostEqual(sp.k, 1.72)

    def test_z19_caps_at_lot_size(self):
        sp = compute_sample_plan(lot_size=4, aql=2.5, inspection_level="II", strategy="Z19")
        self.assertLessEqual(sp.sample_size, 4)

    def test_z19_untabulated_cell_raises(self):
        # Code letter B has no 0.65 AQL column → explicit error, no silent guess.
        with self.assertRaises(ValueError):
            compute_sample_plan(lot_size=5, aql=0.65, inspection_level="I", strategy="Z19")


class EvaluateVariablesTests(SimpleTestCase):
    def test_zero_spread_within_limit_accepts(self):
        r = evaluate_variables(values=[10, 10, 10, 10, 10], usl=12, k=1.53)
        self.assertEqual(r["s"], 0.0)
        self.assertTrue(r["accept"])

    def test_zero_spread_out_of_limit_rejects(self):
        r = evaluate_variables(values=[13, 13, 13], usl=12, k=1.53)
        self.assertFalse(r["accept"])

    def test_upper_limit_index_clears_k_accepts(self):
        # mean 10, s≈0.7071, USL 12 → QU≈2.83 ≥ 1.53 → accept
        r = evaluate_variables(values=[9, 10, 11, 10, 10], usl=12, k=1.53)
        self.assertAlmostEqual(r["mean"], 10.0)
        self.assertAlmostEqual(r["s"], 0.7071, places=3)
        self.assertGreater(r["q_u"], 1.53)
        self.assertTrue(r["accept"])

    def test_upper_limit_index_below_k_rejects(self):
        # mean 10, s≈0.7071, USL 10.5 → QU≈0.707 < 1.53 → reject (even though every
        # individual reading is within spec — the variables hallmark).
        r = evaluate_variables(values=[9, 10, 11, 10, 10], usl=10.5, k=1.53)
        self.assertLess(r["q_u"], 1.53)
        self.assertFalse(r["accept"])

    def test_double_limit_requires_both(self):
        # mean 10, s≈0.7071. USL 12 (QU≈2.83 ok), LSL 9.5 (QL≈0.707 < k) → reject.
        r = evaluate_variables(values=[9, 10, 11, 10, 10], usl=12, lsl=9.5, k=1.53)
        self.assertFalse(r["accept"])

    def test_needs_a_limit(self):
        with self.assertRaises(ValueError):
            evaluate_variables(values=[1, 2, 3], k=1.5)

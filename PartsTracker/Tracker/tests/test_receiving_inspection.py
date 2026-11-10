"""Tests for Phase 1 receiving inspection (purchased material, Flow A).

Receiving inspection is a RECEIVING Step node: characteristics = the step's
required_measurements; acceptance sampling = the step's SamplingRuleSet resolved
by supplier; the inspection is recorded as QualityReports(material_lot, step).
"""
import datetime
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import SimpleTestCase

from Tracker.tests.base import TenantTestCase
from Tracker.services.qms.acceptance_sampling import SamplePlan, compute_sample_plan
from Tracker.services.mes import inventory
from Tracker.services.qms import receiving_inspection


class AcceptanceSamplingTests(SimpleTestCase):
    """The Phase-1 stub contract — locks the DTO + signature for the Phase-2 swap."""

    def test_returns_sample_plan_dto(self):
        sp = compute_sample_plan(lot_size=100, aql=1.0, inspection_level="II",
                                 severity="NORMAL", strategy="C0")
        self.assertIsInstance(sp, SamplePlan)
        self.assertEqual(sp.accept_number, 0)        # C=0
        self.assertEqual(sp.reject_number, 1)
        self.assertGreaterEqual(sp.sample_size, 1)

    def test_sample_size_never_exceeds_lot(self):
        sp = compute_sample_plan(lot_size=3, aql=1.0, inspection_level="II",
                                 severity="NORMAL", strategy="C0")
        self.assertLessEqual(sp.sample_size, 3)

    def test_negative_lot_rejected(self):
        with self.assertRaises(ValueError):
            compute_sample_plan(lot_size=-1, aql=1.0, inspection_level="II",
                                severity="NORMAL", strategy="C0")

    def test_c0_is_always_zero_accept(self):
        for lot, aql in ((100, 1.0), (1000, 2.5), (40, 0.65)):
            sp = compute_sample_plan(lot_size=lot, aql=aql, inspection_level="II",
                                     severity="NORMAL", strategy="C0")
            self.assertEqual((sp.accept_number, sp.reject_number), (0, 1))

    def test_z14_code_letter_anchor(self):
        # Lot 1000, level II → code J (n=80); AQL 1.0 → Ac=2, Re=3 (canonical Z1.4).
        sp = compute_sample_plan(lot_size=1000, aql=1.0, inspection_level="II",
                                 severity="NORMAL", strategy="Z14")
        self.assertEqual((sp.sample_size, sp.accept_number, sp.reject_number), (80, 2, 3))

    def test_z14_single_sampling_re_is_ac_plus_one(self):
        sp = compute_sample_plan(lot_size=500, aql=2.5, inspection_level="II",
                                 severity="NORMAL", strategy="Z14")  # code H, n=50
        self.assertEqual(sp.sample_size, 50)
        self.assertEqual(sp.reject_number, sp.accept_number + 1)

    def test_aql_snaps_to_standard_series(self):
        # A non-standard AQL (0.8) snaps up to 1.0.
        sp = compute_sample_plan(lot_size=1000, aql=0.8, inspection_level="II",
                                 severity="NORMAL", strategy="Z14")
        self.assertEqual(sp.accept_number, 2)  # same as AQL 1.0 at J

    # ── Z1.4 arrow-following (MIL-STD-105E Table II-A), verified 2026-07-06 ──
    def test_z14_up_arrow_follows_to_smaller_plan(self):
        # Lot 20000, level II → code M; M@6.5 is an UP arrow → follow up to L@6.5
        # (n=200, Ac=21). The OLD bug flattened this to Ac=21 at M's n=315.
        sp = compute_sample_plan(lot_size=20000, aql=6.5, inspection_level="II",
                                 severity="NORMAL", strategy="Z14")
        self.assertEqual((sp.sample_size, sp.accept_number, sp.reject_number), (200, 21, 22))

    def test_z14_no_bogus_ac21_at_top_right(self):
        # Regression: N@4.0 and N@6.5 were a bogus Ac=21; they're UP arrows now.
        # Lot 200000 level II → code N. N@4.0 ↑ → M@4.0 (n=315, Ac=21).
        sp = compute_sample_plan(lot_size=200000, aql=4.0, inspection_level="II",
                                 severity="NORMAL", strategy="Z14")
        self.assertEqual(sp.sample_size, 315)      # followed the arrow (not N's 500)
        self.assertEqual(sp.accept_number, 21)

    def test_z14_down_arrow_follows_to_larger_plan(self):
        # Lot 20, level II → code C; C@0.65 is a DOWN arrow → follow down to F@0.65
        # (n=20, Ac=0). (n clamped by the lot of 20.)
        sp = compute_sample_plan(lot_size=20, aql=0.65, inspection_level="II",
                                 severity="NORMAL", strategy="Z14")
        self.assertEqual((sp.sample_size, sp.accept_number), (20, 0))

    # ── Z1.4 severity switching (Tables II-B tightened / II-C reduced) ──
    # Values per the MIL-STD-105E tables as transcribed 2026-11-10. The earlier goldens
    # here (tightened H@2.5 = 5, L@6.5 = 41) pinned a misread table that made
    # tightened LOOSER than normal.
    def test_z14_tightened_is_stricter(self):
        # Lot 500 level II → code H. Normal H@2.5 = Ac 3; Tightened H@2.5 = Ac 2
        # (same n=50, Re=Ac+1). Tightened accepts on FEWER defectives.
        normal = compute_sample_plan(lot_size=500, aql=2.5, inspection_level="II",
                                     severity="NORMAL", strategy="Z14")
        tight = compute_sample_plan(lot_size=500, aql=2.5, inspection_level="II",
                                    severity="TIGHTENED", strategy="Z14")
        self.assertEqual((normal.sample_size, normal.accept_number), (50, 3))
        self.assertEqual((tight.sample_size, tight.accept_number, tight.reject_number), (50, 2, 3))

    def test_z14_tightened_never_looser_than_normal(self):
        # Every code letter, every AQL: at the same lot, tightened never accepts on more
        # defectives than normal with a sample no larger.
        from Tracker.services.qms.acceptance_sampling import STANDARD_AQLS, _CODE_LETTERS
        for lot_max, _ in _CODE_LETTERS[:-1]:
            for aql in STANDARD_AQLS:
                for level in ("I", "II", "III"):
                    kw = dict(lot_size=lot_max, aql=aql, inspection_level=level, strategy="Z14")
                    normal = compute_sample_plan(severity="NORMAL", **kw)
                    tight = compute_sample_plan(severity="TIGHTENED", **kw)
                    if tight.sample_size <= normal.sample_size:
                        self.assertLessEqual(tight.accept_number, normal.accept_number,
                                             (lot_max, aql, level))

    def test_z14_tightened_up_arrow(self):
        # Lot 20000 level II → code M; tightened M@6.5 ↑ → L@6.5 (n=200, Ac=18).
        sp = compute_sample_plan(lot_size=20000, aql=6.5, inspection_level="II",
                                 severity="TIGHTENED", strategy="Z14")
        self.assertEqual((sp.sample_size, sp.accept_number, sp.reject_number), (200, 18, 19))

    def test_z14_every_offered_aql_has_a_plan(self):
        # N4: the tables stopped at AQL 0.65–6.5 and rows C–N, so AQL 0.10–0.40 / 10,
        # or a cell arrowing to row A/B, raised and the lot was never inspected.
        from Tracker.services.qms.acceptance_sampling import STANDARD_AQLS, _CODE_LETTERS
        lots = [2, 8] + [lot_max for lot_max, _ in _CODE_LETTERS[:-1]] + [1_000_000]
        for severity in ("NORMAL", "TIGHTENED", "REDUCED"):
            for aql in STANDARD_AQLS:
                for level in ("I", "II", "III"):
                    for lot in lots:
                        sp = compute_sample_plan(lot_size=lot, aql=aql, inspection_level=level,
                                                 severity=severity, strategy="Z14")
                        self.assertLessEqual(sp.sample_size, lot)
                        self.assertLess(sp.accept_number, sp.reject_number)

    def test_z14_cells_that_used_to_raise(self):
        # Lot 25 level II → C; C@4.0 ↑ → B@4.0 (n=3, Ac 0). B wasn't tabulated.
        sp = compute_sample_plan(lot_size=25, aql=4.0, inspection_level="II",
                                 severity="NORMAL", strategy="Z14")
        self.assertEqual((sp.sample_size, sp.accept_number, sp.reject_number), (3, 0, 1))
        # Lot 1000 level II → J; J@0.15 = Ac 0 (n=80).
        sp = compute_sample_plan(lot_size=1000, aql=0.15, inspection_level="II",
                                 severity="NORMAL", strategy="Z14")
        self.assertEqual((sp.sample_size, sp.accept_number), (80, 0))
        # Lot 1000 level II → J; J@10 = Ac 14 (n=80).
        sp = compute_sample_plan(lot_size=1000, aql=10.0, inspection_level="II",
                                 severity="NORMAL", strategy="Z14")
        self.assertEqual((sp.sample_size, sp.accept_number), (80, 14))

    def test_z14_normal_e_at_2_5_is_a_down_arrow(self):
        # Lot 90 level II → E. E@2.5 is ↓ (was misread ↑) → F@2.5 (n=20, Ac 1).
        sp = compute_sample_plan(lot_size=90, aql=2.5, inspection_level="II",
                                 severity="NORMAL", strategy="Z14")
        self.assertEqual((sp.sample_size, sp.accept_number), (20, 1))

    def test_z14_reduced_smaller_sample_and_gap(self):
        # Lot 500 level II → code H. Reduced uses a SMALLER sample (n=20 vs 50) and
        # H@2.5 = (Ac 1, Re 4) — Re is NOT Ac+1 (the accept/reject gap).
        sp = compute_sample_plan(lot_size=500, aql=2.5, inspection_level="II",
                                 severity="REDUCED", strategy="Z14")
        self.assertEqual((sp.sample_size, sp.accept_number, sp.reject_number), (20, 1, 4))
        self.assertGreater(sp.reject_number, sp.accept_number + 1)  # the gap exists

    def test_z19_k_verified_cells(self):
        # Z1.9 std-dev method, normal. Lot 80 level II → code E (n=7); E@1.0 k=1.62
        # (the E row was wrong before the 2026-07-06 audit).
        sp = compute_sample_plan(lot_size=80, aql=1.0, inspection_level="II",
                                 severity="NORMAL", strategy="Z19")
        self.assertEqual(sp.sample_size, 7)
        self.assertAlmostEqual(sp.k, 1.62)
        # Lot 150 level II → code F (n=10); F@1.0 k=1.72.
        sp2 = compute_sample_plan(lot_size=150, aql=1.0, inspection_level="II",
                                  severity="NORMAL", strategy="Z19")
        self.assertEqual((sp2.sample_size, sp2.k), (10, 1.72))

    def test_z19_high_letters_fail_closed(self):
        # Large lot → high code letter (K+), which is intentionally NOT tabulated
        # (pending verified Z1.9-2003 values). We fail closed with an actionable
        # message rather than return a borrowed/approximate k.
        with self.assertRaises(ValueError):
            compute_sample_plan(lot_size=3000, aql=1.0, inspection_level="II",
                                severity="NORMAL", strategy="Z19")


class _ReceivingFixtureMixin:
    """Builds a part type + RECEIVING step (with a characteristic + sampling ruleset)."""

    def _make_lot(self, status="RECEIVED", qty="100"):
        from Tracker.models import MaterialLot
        return MaterialLot.objects.create(
            tenant=self.tenant_a, lot_number=f"LOT-{status}-{qty}",
            received_date=datetime.date(2026, 1, 1), received_by=self.user_a,
            quantity=Decimal(qty), quantity_remaining=Decimal(qty),
            unit_of_measure="EA", status=status, material_type=self.part_type,
        )

    def _build_fixtures(self):
        from Tracker.models import (
            PartTypes, Steps, MeasurementDefinition, StepMeasurementRequirement,
            SamplingRuleSet, SamplingRule,
        )
        self.part_type = PartTypes.objects.create(tenant=self.tenant_a, name="Gear")
        self.recv_step = Steps.objects.create(
            tenant=self.tenant_a, name="Receiving Inspection",
            part_type=self.part_type, step_type="RECEIVING")
        self.char = MeasurementDefinition.objects.create(
            tenant=self.tenant_a, step=self.recv_step, label="Visual", type="PASS_FAIL")
        StepMeasurementRequirement.objects.get_or_create(step=self.recv_step, measurement=self.char)
        self.ruleset = SamplingRuleSet.objects.create(
            tenant=self.tenant_a, part_type=self.part_type, step=self.recv_step, supplier=None,
            name="Receiving C=0", active=True, aql=Decimal("1.0"),
            inspection_level="II", severity="NORMAL", strategy="C0")
        SamplingRule.objects.create(
            tenant=self.tenant_a, ruleset=self.ruleset, rule_type="C_ZERO", order=1)


class InventoryServiceTests(_ReceivingFixtureMixin, TenantTestCase):
    def setUp(self):
        super().setUp()
        self._build_fixtures()

    def test_awaiting_then_accept(self):
        lot = self._make_lot()
        inventory.mark_awaiting_inspection(lot)
        self.assertEqual(lot.status, "AWAITING_INSPECTION")
        inventory.mark_lot_accepted(lot)
        self.assertEqual(lot.status, "ACCEPTED")

    def test_reject_path(self):
        lot = self._make_lot()
        inventory.mark_awaiting_inspection(lot)
        inventory.mark_lot_rejected(lot)
        self.assertEqual(lot.status, "REJECTED")

    def test_bad_source_state_raises(self):
        lot = self._make_lot()  # RECEIVED
        with self.assertRaises(ValueError):
            inventory.mark_lot_accepted(lot)


class ReceivingResolutionTests(_ReceivingFixtureMixin, TenantTestCase):
    def setUp(self):
        super().setUp()
        self._build_fixtures()

    def test_resolves_receiving_step(self):
        self.assertEqual(receiving_inspection.resolve_receiving_step(self.part_type), self.recv_step)

    def test_supplier_specific_ruleset_wins(self):
        from Tracker.models import Companies, SamplingRuleSet, SamplingRule
        supplier = Companies.objects.create(tenant=self.tenant_a, name="Acme", description="")
        sup_rs = SamplingRuleSet.objects.create(
            tenant=self.tenant_a, part_type=self.part_type, step=self.recv_step, supplier=supplier,
            name="Acme tightened", active=True, aql=Decimal("0.65"),
            inspection_level="III", severity="TIGHTENED", strategy="C0")
        SamplingRule.objects.create(tenant=self.tenant_a, ruleset=sup_rs, rule_type="C_ZERO", order=1)
        # Supplier match wins over the supplier=None default.
        self.assertEqual(receiving_inspection.resolve_sampling_ruleset(self.recv_step, supplier), sup_rs)
        # No supplier → falls back to the default.
        self.assertEqual(receiving_inspection.resolve_sampling_ruleset(self.recv_step, None), self.ruleset)


class ReceivingFlowTests(_ReceivingFixtureMixin, TenantTestCase):
    def setUp(self):
        super().setUp()
        self._build_fixtures()

    def test_open_creates_report_and_moves_lot(self):
        lot = self._make_lot()
        report = receiving_inspection.open_inspection(lot, self.user_a)
        self.assertEqual(report.material_lot_id, lot.id)
        self.assertEqual(report.step_id, self.recv_step.id)
        self.assertEqual(report.status, "PENDING")
        self.assertIsNotNone(report.sample_size)
        self.assertEqual(report.accept_number, 0)
        lot.refresh_from_db()
        self.assertEqual(lot.status, "AWAITING_INSPECTION")
        self.assertTrue(report.personnel_links.filter(role="INSPECTOR").exists())
        # The inspector is also who detected — what lists of failures read.
        self.assertEqual(report.detected_by_id,
                         report.personnel_links.get(role="INSPECTOR").user_id)

    def test_open_without_receiving_step_raises(self):
        from Tracker.models import PartTypes, MaterialLot
        other_pt = PartTypes.objects.create(tenant=self.tenant_a, name="Bracket")
        lot = MaterialLot.objects.create(
            tenant=self.tenant_a, lot_number="LOT-NO-STEP", received_date=datetime.date(2026, 1, 1),
            received_by=self.user_a, quantity=Decimal("10"), quantity_remaining=Decimal("10"),
            unit_of_measure="EA", status="RECEIVED", material_type=other_pt)
        with self.assertRaises(ValueError):
            receiving_inspection.open_inspection(lot, self.user_a)

    def test_record_pass_then_accept(self):
        lot = self._make_lot()
        report = receiving_inspection.open_inspection(lot, self.user_a)
        receiving_inspection.record_inspection(
            report, [{"definition": str(self.char.id), "value_pass_fail": "PASS"}], self.user_a)
        report.refresh_from_db()
        self.assertEqual(report.status, "PASS")
        receiving_inspection.accept(report, self.user_a)
        lot.refresh_from_db()
        self.assertEqual(lot.status, "ACCEPTED")

    def test_record_fail_sets_fail(self):
        lot = self._make_lot()
        report = receiving_inspection.open_inspection(lot, self.user_a)
        receiving_inspection.record_inspection(
            report, [{"definition": str(self.char.id), "value_pass_fail": "FAIL"}], self.user_a)
        report.refresh_from_db()
        self.assertEqual(report.status, "FAIL")

    def test_a_failed_lot_cannot_be_accepted(self):
        """A failed inspection is rejected; use-as-is is the disposition's decision."""
        lot = self._make_lot()
        report = receiving_inspection.open_inspection(lot, self.user_a)
        receiving_inspection.record_inspection(
            report, [{"definition": str(self.char.id), "value_pass_fail": "FAIL"}], self.user_a)
        report.refresh_from_db()
        with self.assertRaisesMessage(ValueError, "failed its inspection"):
            receiving_inspection.accept(report, self.user_a)
        lot.refresh_from_db()
        self.assertNotEqual(lot.status, "ACCEPTED")

    def test_a_bulk_tally_counts_alongside_captured_readings(self):
        """Readings captured in the DWI and the review's tally of the sample: the larger
        decides. Readings alone used to win, dropping a tally of other defects."""
        lot = self._make_lot()
        report = receiving_inspection.open_inspection(lot, self.user_a)
        receiving_inspection.record_inspection(
            report, [{"definition": str(self.char.id), "value_pass_fail": "PASS"}], self.user_a)
        receiving_inspection.record_bulk(report, 1, self.user_a)
        report.refresh_from_db()
        self.assertEqual(report.status, "FAIL")   # 1 ≥ Re (C=0), though the reading passed

    def test_reject_moves_lot(self):
        lot = self._make_lot()
        report = receiving_inspection.open_inspection(lot, self.user_a)
        receiving_inspection.reject(report, self.user_a)
        lot.refresh_from_db()
        self.assertEqual(lot.status, "REJECTED")

    def test_reduced_gap_lot_is_accepted(self):
        # Reduced plan with an accept/reject gap (Ac=1, Re=4): 2 defectives lands in
        # the gap → the lot is ACCEPTED (the switching engine reverts to normal).
        lot = self._make_lot(qty="500")
        report = receiving_inspection.open_inspection(lot, self.user_a)
        report.sample_size, report.accept_number, report.reject_number = 20, 1, 4
        report.save(update_fields=["sample_size", "accept_number", "reject_number"])
        receiving_inspection.record_bulk(report, defectives_found=2, user=self.user_a)
        report.refresh_from_db()
        self.assertEqual(report.status, "PASS")

    def test_route_received_with_step_opens_inspection(self):
        lot = self._make_lot()  # part_type has a RECEIVING step (fixture)
        receiving_inspection.route_received_lot(lot, self.user_a)
        lot.refresh_from_db()
        self.assertEqual(lot.status, "AWAITING_INSPECTION")
        self.assertIsNotNone(receiving_inspection.receiving_execution(lot))

    def test_routed_at_receipt_the_inspector_is_who_records_not_who_received(self):
        """Routed at receipt by the clerk, the inspection names nobody; the inspector who
        records on it is its inspector and detector (docs-session review 2026-11-04)."""
        from Tracker.models import User
        inspector = User.objects.create_user(username="insp_a", email="insp_a@tenant-a.com",
                                             password="x", tenant=self.tenant_a)
        lot = self._make_lot()
        report = receiving_inspection.route_received_lot(lot, self.user_a)  # the clerk
        self.assertIsNone(report.detected_by_id)
        self.assertFalse(report.personnel_links.exists())
        self.assertIsNone(receiving_inspection.receiving_execution(lot).assigned_to_id)

        receiving_inspection.record_inspection(
            report, [{"definition": str(self.char.id), "value_pass_fail": "FAIL"}], inspector)
        report.refresh_from_db()
        self.assertEqual(report.detected_by_id, inspector.id)
        self.assertEqual(report.primary_detector, inspector)
        self.assertEqual(report.personnel_links.get(role="INSPECTOR").user_id, inspector.id)
        # A second recorder doesn't take it over.
        receiving_inspection.record_inspection(
            report, [{"definition": str(self.char.id), "value_pass_fail": "FAIL"}], self.user_a)
        report.refresh_from_db()
        self.assertEqual(report.detected_by_id, inspector.id)

    def test_per_unit_all_pass_accepts(self):
        lot = self._make_lot(qty="3")  # small sample
        report = receiving_inspection.open_inspection(lot, self.user_a)
        n = report.sample_size
        units = [{"sample_number": i + 1,
                  "measurements": [{"definition": str(self.char.id), "value_pass_fail": "PASS"}]}
                 for i in range(n)]
        receiving_inspection.record_sample_units(report, units, self.user_a)
        report.refresh_from_db()
        self.assertEqual(report.status, "PASS")

    def test_per_unit_one_defective_fails_c0(self):
        lot = self._make_lot(qty="3")
        report = receiving_inspection.open_inspection(lot, self.user_a)
        # One defective unit → C=0 (Re=1) rejects immediately, before all n recorded.
        receiving_inspection.record_sample_units(
            report, [{"sample_number": 1,
                      "measurements": [{"definition": str(self.char.id), "value_pass_fail": "FAIL"}]}],
            self.user_a)
        report.refresh_from_db()
        self.assertEqual(report.status, "FAIL")

    def test_per_unit_partial_sample_is_pending(self):
        lot = self._make_lot(qty="3")
        report = receiving_inspection.open_inspection(lot, self.user_a)
        # Only 1 of n units recorded, in-spec → still PENDING (not enough sampled).
        receiving_inspection.record_sample_units(
            report, [{"sample_number": 1,
                      "measurements": [{"definition": str(self.char.id), "value_pass_fail": "PASS"}]}],
            self.user_a)
        report.refresh_from_db()
        self.assertEqual(report.status, "PENDING")

    def test_bulk_zero_defectives_accepts(self):
        lot = self._make_lot()
        report = receiving_inspection.open_inspection(lot, self.user_a)
        receiving_inspection.record_bulk(report, 0, self.user_a)
        report.refresh_from_db()
        self.assertEqual(report.status, "PASS")   # bulk assumes full sample inspected; 0 ≤ Ac

    def test_bulk_one_defective_fails_c0(self):
        lot = self._make_lot()
        report = receiving_inspection.open_inspection(lot, self.user_a)
        receiving_inspection.record_bulk(report, 1, self.user_a)
        report.refresh_from_db()
        self.assertEqual(report.status, "FAIL")   # 1 ≥ Re (C=0)

    def test_route_received_without_step_dock_to_stock(self):
        from Tracker.models import PartTypes, MaterialLot
        no_step_pt = PartTypes.objects.create(tenant=self.tenant_a, name="Washer")
        lot = MaterialLot.objects.create(
            tenant=self.tenant_a, lot_number="LOT-WASHER", material_type=no_step_pt,
            received_date=datetime.date(2026, 1, 1), received_by=self.user_a,
            quantity=Decimal("500"), quantity_remaining=Decimal("500"),
            unit_of_measure="EA", status="RECEIVED")
        receiving_inspection.route_received_lot(lot, self.user_a)
        lot.refresh_from_db()
        self.assertEqual(lot.status, "ACCEPTED")  # dock-to-stock, no inspection required

    def test_qr_constraint_rejects_both_subjects(self):
        from Tracker.models import QualityReports, Parts
        lot = self._make_lot()
        part = Parts.objects.create(tenant=self.tenant_a, ERP_id="P-1")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                QualityReports.objects.create(
                    tenant=self.tenant_a, part=part, material_lot=lot, status="PENDING")


class ReceivingDwiExecutionTests(_ReceivingFixtureMixin, TenantTestCase):
    """The receiving inspection runs as a StepExecution whose polymorphic subject
    is the MaterialLot, so the DWI substep runtime + inline capture apply."""

    def setUp(self):
        super().setUp()
        self._build_fixtures()

    def test_open_creates_lot_step_execution(self):
        from Tracker.models import StepExecution
        lot = self._make_lot()
        receiving_inspection.open_inspection(lot, self.user_a)
        ex = receiving_inspection.receiving_execution(lot)
        self.assertIsNotNone(ex)
        self.assertEqual(ex.step_id, self.recv_step.id)
        self.assertEqual(ex.subject, lot)            # polymorphic subject resolves to the lot
        self.assertIsNone(ex.subject_work_order)     # receiving precedes production
        self.assertIsNone(ex.part_id)
        self.assertEqual(ex.status, "IN_PROGRESS")

    def test_step_execution_allows_no_part(self):
        # A subject-less-FK execution is allowed: a lot rides the polymorphic subject
        # fields. (The part-XOR-core half of this check went when cores became parts —
        # a core's execution is on its part, so there is no second FK to exclude.)
        from Tracker.models import StepExecution
        StepExecution.objects.create(tenant=self.tenant_a, step=self.recv_step)  # ok

    def test_inline_capture_promotes_to_lot_quality_report(self):
        """A DWI MeasurementInput capture on a lot execution lands on the lot's
        receiving QualityReports (not a part QR)."""
        from Tracker.models import Substep, StepExecutionMeasurement
        from Tracker.services.qms.inline_capture import record_dwi_measurement
        lot = self._make_lot()
        report = receiving_inspection.open_inspection(lot, self.user_a)
        ex = receiving_inspection.receiving_execution(lot)
        substep = Substep.objects.create(
            tenant=self.tenant_a, step=self.recv_step, title="Inspect",
            order=1, is_inspection_point=True)

        sem = record_dwi_measurement(
            step_execution=ex, substep=substep, measurement_definition=self.char,
            value_string="PASS", recorded_by=self.user_a)

        self.assertIsInstance(sem, StepExecutionMeasurement)
        # Promoted onto the SAME lot report opened above (one report per lot inspection).
        report.refresh_from_db()
        self.assertEqual(report.measurements.count(), 1)
        self.assertEqual(report.material_lot_id, lot.id)

    def test_a_failing_reading_on_a_lot_fails_its_report(self):
        """An out-of-spec reading turns the lot's report FAIL. The FAIL consequences
        are part-scoped (sampling state, quarantine); the lot report has no part, and
        dereferencing it was a 500 on every failing receiving reading (walk 2026-10-20)."""
        from Tracker.models import Substep
        from Tracker.services.qms.inline_capture import record_dwi_measurement
        lot = self._make_lot()
        report = receiving_inspection.open_inspection(lot, self.user_a)
        substep = Substep.objects.create(
            tenant=self.tenant_a, step=self.recv_step, title="Inspect",
            order=1, is_inspection_point=True)
        record_dwi_measurement(
            step_execution=receiving_inspection.receiving_execution(lot), substep=substep,
            measurement_definition=self.char, value_string="FAIL", recorded_by=self.user_a)
        report.refresh_from_db()
        self.assertEqual(report.status, "FAIL")

    def test_accept_finalizes_execution(self):
        lot = self._make_lot()
        report = receiving_inspection.open_inspection(lot, self.user_a)
        report.status = "PASS"  # the sample's verdict (an unfinished one can't be accepted)
        report.save(update_fields=["status"])
        receiving_inspection.accept(report, self.user_a)
        ex = receiving_inspection.receiving_execution(lot)  # only open ones
        self.assertIsNone(ex)  # finalized → no longer "open"


class SupplierQualityTests(_ReceivingFixtureMixin, TenantTestCase):
    """SQM: scorecard rollup + SCAR (supplier-tagged CAPA)."""

    def setUp(self):
        super().setUp()
        self._build_fixtures()
        from Tracker.models import Companies
        self.supplier = Companies.objects.create(tenant=self.tenant_a, name="Acme Castings", description="")

    def _lot(self, suffix, status, *, coc=False, promised=None, received=datetime.date(2026, 1, 2)):
        from Tracker.models import MaterialLot
        return MaterialLot.objects.create(
            tenant=self.tenant_a, lot_number=f"SC-{suffix}", material_type=self.part_type,
            supplier=self.supplier, received_date=received, received_by=self.user_a,
            quantity=Decimal("100"), quantity_remaining=Decimal("100"), unit_of_measure="EA",
            status=status, promised_date=promised,
            certificate_of_conformance=("coc.pdf" if coc else ""),
        )

    def test_scorecard_rollup(self):
        from Tracker.services.qms.supplier_scorecard import compute_supplier_scorecard
        # accepted, on-time, with CoC
        self._lot("1", "ACCEPTED", coc=True, received=datetime.date(2026, 1, 1), promised=datetime.date(2026, 1, 2))
        # rejected, late (received after promised), no CoC
        self._lot("2", "REJECTED", received=datetime.date(2026, 1, 5), promised=datetime.date(2026, 1, 3))
        # still received (not inspected), no promised date
        self._lot("3", "RECEIVED")

        sc = compute_supplier_scorecard(self.supplier)
        self.assertEqual(sc.lots_received, 3)
        self.assertEqual(sc.lots_accepted, 1)
        self.assertEqual(sc.lots_rejected, 1)
        self.assertEqual(sc.lots_inspected, 2)
        self.assertAlmostEqual(sc.reject_rate, 0.5)
        self.assertAlmostEqual(sc.coc_compliance, 1 / 3)
        self.assertEqual(sc.promised_lots, 2)
        self.assertAlmostEqual(sc.on_time_rate, 0.5)   # 1 on-time of 2 with a promised date
        self.assertEqual(sc.open_scar_count, 0)

    def test_scorecard_counts_the_outcome_not_where_the_lot_is_now(self):
        """An accepted lot goes on to IN_USE / CONSUMED, a rejected one to RETURNED or
        (by its disposition) SCRAPPED; they stay accepted / rejected (hunt 2026-11-05)."""
        from Tracker.models import QuarantineDisposition
        from Tracker.services.qms.supplier_scorecard import compute_supplier_scorecard
        self._lot("U", "IN_USE")
        self._lot("C", "CONSUMED")
        self._lot("R", "RETURNED")
        scrapped = self._lot("S", "SCRAPPED")
        QuarantineDisposition.objects.create(tenant=self.tenant_a, material_lot=scrapped,
                                             quantity=Decimal("100"), disposition_type="SCRAP")
        sc = compute_supplier_scorecard(self.supplier)
        self.assertEqual((sc.lots_accepted, sc.lots_rejected, sc.lots_inspected), (2, 2, 4))
        self.assertAlmostEqual(sc.reject_rate, 0.5)

    def test_open_scar_is_supplier_capa_and_counts(self):
        from Tracker.services.qms.scar import open_scar
        from Tracker.services.qms.supplier_scorecard import compute_supplier_scorecard
        from Tracker.models import CAPA
        capa = open_scar(supplier=self.supplier, problem_statement="Out-of-spec bore.",
                         severity="MAJOR", user=self.user_a)
        self.assertEqual(capa.capa_type, "SUPPLIER")
        self.assertEqual(capa.supplier_id, self.supplier.id)
        self.assertEqual(capa.status, "OPEN")
        self.assertEqual(compute_supplier_scorecard(self.supplier).open_scar_count, 1)
        # Closing it drops it from the open count.
        capa.status = "CLOSED"; capa.save(update_fields=["status"])
        self.assertEqual(compute_supplier_scorecard(self.supplier).open_scar_count, 0)

    def test_open_scar_for_lot_links_report(self):
        from Tracker.services.qms.scar import open_scar_for_lot
        lot = self._lot("rej", "RECEIVED")
        report = receiving_inspection.open_inspection(lot, self.user_a)
        receiving_inspection.reject(report, self.user_a)
        capa = open_scar_for_lot(lot, user=self.user_a)
        self.assertEqual(capa.supplier_id, self.supplier.id)
        self.assertIn(report, capa.quality_reports.all())
        # One open SCAR per lot: a second raise returns the first.
        self.assertEqual(open_scar_for_lot(lot, user=self.user_a).id, capa.id)
        # Closed, a recurrence is a new SCAR.
        capa.status = "CLOSED"; capa.save(update_fields=["status"])
        self.assertNotEqual(open_scar_for_lot(lot, user=self.user_a).id, capa.id)


class DefectiveCountGateTests(_ReceivingFixtureMixin, TenantTestCase):
    """DEFECTIVE_COUNT for a lot must count defective sampled *units* from the
    report's per-unit MeasurementResults. Regression: the DWI unit-by-unit path
    never writes material_lot.defectives_found, so the old gate read that field
    and under-counted."""

    def setUp(self):
        super().setUp()
        self._build_fixtures()
        self.ruleset.gate_metric = "DEFECTIVE_COUNT"
        self.ruleset.gate_threshold = 2
        self.ruleset.save()

    def _fail_unit(self, sn):
        return {"sample_number": sn,
                "measurements": [{"definition": str(self.char.id), "value_pass_fail": "FAIL"}]}

    def test_counts_defective_units_not_reports(self):
        from Tracker.services.qms.quality_gate import _compute_metric
        lot = self._make_lot(qty="50")
        report = receiving_inspection.open_inspection(lot, self.user_a)
        # Two defective units recorded on a single report — the lot field stays 0.
        receiving_inspection.record_sample_units(
            report, [self._fail_unit(1), self._fail_unit(2)], self.user_a)

        metric = _compute_metric(self.ruleset, work_order=None, material_lot=lot)
        self.assertEqual(metric, Decimal(2))  # units, not the 1 the FAIL-report count would give

    def test_bulk_defectives_found_still_counted(self):
        from Tracker.services.qms.quality_gate import _compute_metric
        lot = self._make_lot(qty="50")
        report = receiving_inspection.open_inspection(lot, self.user_a)
        receiving_inspection.record_bulk(report, defectives_found=3, user=self.user_a)

        metric = _compute_metric(self.ruleset, work_order=None, material_lot=lot)
        self.assertEqual(metric, Decimal(3))

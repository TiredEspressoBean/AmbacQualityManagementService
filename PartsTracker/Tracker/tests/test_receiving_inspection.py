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

    # ── Z1.4 severity switching (Tables II-B tightened / II-C reduced), 2026-07-07 ──
    def test_z14_tightened_is_stricter(self):
        # Lot 500 level II → code H. Normal H@2.5 = Ac 3; Tightened H@2.5 = Ac 5
        # (same n=50, Re=Ac+1). Tightened accepts on FEWER defectives per its ladder.
        normal = compute_sample_plan(lot_size=500, aql=2.5, inspection_level="II",
                                     severity="NORMAL", strategy="Z14")
        tight = compute_sample_plan(lot_size=500, aql=2.5, inspection_level="II",
                                    severity="TIGHTENED", strategy="Z14")
        self.assertEqual((normal.sample_size, normal.accept_number), (50, 3))
        self.assertEqual((tight.sample_size, tight.accept_number, tight.reject_number), (50, 5, 6))

    def test_z14_tightened_up_arrow(self):
        # Lot 20000 level II → code M; tightened M@6.5 ↑ → L@6.5 (n=200, Ac=41).
        sp = compute_sample_plan(lot_size=20000, aql=6.5, inspection_level="II",
                                 severity="TIGHTENED", strategy="Z14")
        self.assertEqual((sp.sample_size, sp.accept_number, sp.reject_number), (200, 41, 42))

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

    def test_step_execution_allows_no_part_or_core(self):
        # The relaxed constraint permits a subject-less-FK execution (lot rides the
        # polymorphic fields). Both part+core set is still rejected.
        from Tracker.models import StepExecution, Parts, Core
        StepExecution.objects.create(tenant=self.tenant_a, step=self.recv_step)  # ok
        part = Parts.objects.create(tenant=self.tenant_a, ERP_id="P-2")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                core = Core.objects.create(
                    tenant=self.tenant_a, core_number="C-1", core_type=self.part_type,
                    received_by=self.user_a, received_date=datetime.date(2026, 1, 1))
                StepExecution.objects.create(
                    tenant=self.tenant_a, step=self.recv_step, part=part, core=core)

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

    def test_accept_finalizes_execution(self):
        lot = self._make_lot()
        report = receiving_inspection.open_inspection(lot, self.user_a)
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

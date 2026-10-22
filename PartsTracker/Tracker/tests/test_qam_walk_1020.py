"""QA Manager walk findings (2026-10-20) that have no better home."""
from datetime import timedelta

from django.utils import timezone

from Tracker.models import (
    CalibrationRecord, Companies, EquipmentType, Equipments, MaterialLot, PartTypes,
    QualityReports, QuarantineDisposition, SamplingRule, SamplingRuleSet, Steps,
)
from Tracker.tests.base import TenantTestCase


class _Api(TenantTestCase):
    perms = ['full_tenant_access']

    def setUp(self):
        super().setUp()
        self.grant_tenant_permissions(self.user_a, self.tenant_a, self.perms)
        self.authenticate_as(self.user_a, self.tenant_a)


class CalibrationFailedBucketTests(_Api):
    perms = ['view_calibrationrecord', 'full_tenant_access']

    def test_a_failed_gauge_is_its_own_bucket(self):
        """A gauge whose latest calibration failed sat in no bucket, so the dashboard's
        counts didn't add up."""
        gauge_type = EquipmentType.objects.create(tenant=self.tenant_a, name="Micrometer",
                                                  requires_calibration=True)
        today = timezone.now().date()
        for name, result, due in (("MIC-1", "PASS", today + timedelta(days=200)),
                                  ("MIC-2", "FAIL", today + timedelta(days=200))):
            eq = Equipments.objects.create(tenant=self.tenant_a, name=name, equipment_type=gauge_type)
            CalibrationRecord.objects.create(tenant=self.tenant_a, equipment=eq, calibration_date=today,
                                             due_date=due, result=result)
        stats = self.client.get("/api/CalibrationRecords/stats/").json()
        self.assertEqual((stats["current_calibrations"], stats["failed"], stats["overdue"]), (1, 1, 0))

    def test_only_the_latest_calibration_counts(self):
        """Sweep 2026-10-22: the viewset's base queryset lacked latest_per_equipment, so
        every record counted — an older one with a later due date made an overdue gauge
        read current, and the buckets summed past the equipment count."""
        gauge_type = EquipmentType.objects.create(tenant=self.tenant_a, name="Torque wrench",
                                                  requires_calibration=True)
        today = timezone.now().date()
        eq = Equipments.objects.create(tenant=self.tenant_a, name="TW-25", equipment_type=gauge_type)
        CalibrationRecord.objects.create(tenant=self.tenant_a, equipment=eq, result="PASS",
                                         calibration_date=today - timedelta(days=100),
                                         due_date=today + timedelta(days=100))
        CalibrationRecord.objects.create(tenant=self.tenant_a, equipment=eq, result="PASS",
                                         calibration_date=today - timedelta(days=30),
                                         due_date=today - timedelta(days=5))
        stats = self.client.get("/api/CalibrationRecords/stats/").json()
        self.assertEqual((stats["total_equipment"], stats["current_calibrations"],
                          stats["overdue"], stats["failed"]), (1, 0, 1, 0))
        overdue = self.client.get("/api/CalibrationRecords/overdue/").json()
        rows = overdue["results"] if isinstance(overdue, dict) else overdue
        self.assertEqual(len(rows), 1)


class SupplyingCompaniesTests(_Api):
    perms = ['view_companies', 'full_tenant_access']

    def test_only_companies_that_supply_something(self):
        """is_supplier defaults to true, so the scorecard listed customers and the
        tenant's own company as unqualified suppliers."""
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Seal")
        supplier = Companies.objects.create(tenant=self.tenant_a, name="Great Lakes")
        customer = Companies.objects.create(tenant=self.tenant_a, name="Midwest Fleet")
        MaterialLot.objects.create(tenant=self.tenant_a, lot_number="L-1", supplier=supplier,
                                   material_type=pt, quantity=1, quantity_remaining=1,
                                   received_date=timezone.now().date(), unit_of_measure="EA")
        names = {c["name"] for c in self.client.get("/api/Companies/", {"supplying": "true"}).json()["results"]}
        self.assertIn(supplier.name, names)
        self.assertNotIn(customer.name, names)


class SamplingRuleEditTests(_Api):
    perms = ['view_samplingrule', 'change_samplingrule', 'delete_samplingrule', 'view_samplingruleset',
             'full_tenant_access']

    def test_an_edit_is_one_audit_entry(self):
        """The walk saw two identical audit entries per rule edit."""
        from auditlog.models import LogEntry
        from django.contrib.contenttypes.models import ContentType
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Body")
        step = Steps.objects.create(tenant=self.tenant_a, name="Body Inspection", part_type=pt)
        rs = SamplingRuleSet.objects.create(tenant=self.tenant_a, part_type=pt, step=step, name="Standard")
        rule = SamplingRule.objects.create(tenant=self.tenant_a, ruleset=rs, rule_type="EVERY_NTH_PART",
                                           value=4, order=1)
        ct = ContentType.objects.get_for_model(SamplingRule)
        before = LogEntry.objects.filter(content_type=ct, object_pk=str(rule.pk)).count()
        resp = self.client.patch(f"/api/Sampling-rules/{rule.id}/", {"value": 2}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(LogEntry.objects.filter(content_type=ct, object_pk=str(rule.pk)).count(), before + 1)

    def test_the_rule_set_history_includes_its_rules(self):
        """Tightening every 4th → every 2nd is a rule change; the set's History said
        "No recorded changes" (user decision 2026-10-20: include its rules)."""
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Body")
        step = Steps.objects.create(tenant=self.tenant_a, name="Body Inspection", part_type=pt)
        rs = SamplingRuleSet.objects.create(tenant=self.tenant_a, part_type=pt, step=step, name="Standard")
        rule = SamplingRule.objects.create(tenant=self.tenant_a, ruleset=rs, rule_type="EVERY_NTH_PART",
                                           value=4, order=1)
        self.client.patch(f"/api/Sampling-rules/{rule.id}/", {"value": 2}, format="json")
        self.client.delete(f"/api/Sampling-rules/{rule.id}/")
        history = self.client.get(f"/api/Sampling-rule-sets/{rs.id}/rule-history/").json()
        changed = [h for h in history if h["action"] == "changed" and "value" in h["changes"]]
        self.assertTrue(changed, history)
        self.assertEqual([str(v) for v in changed[0]["changes"]["value"]], ["4", "2"])
        self.assertEqual(changed[0]["rule_type"], "EVERY_NTH_PART")
        self.assertTrue(any(h["action"] in ("removed", "changed") and h["rule_id"] == str(rule.id)
                            for h in history))


class DispositionDescriptionTests(TenantTestCase):

    def test_the_description_names_every_report_once_captures_are_in(self):
        """A step's captures land after its report first goes FAIL, so the description
        written then said only the step; a joining report never made it in."""
        from Tracker.models import MeasurementDefinition, MeasurementResult, Parts
        from Tracker.services.qms.disposition import refresh_disposition_description
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Body")
        step = Steps.objects.create(tenant=self.tenant_a, name="Body Inspection", part_type=pt)
        part = Parts.objects.create(tenant=self.tenant_a, ERP_id="B-1", part_type=pt, step=step)
        visual = QualityReports.objects.create(tenant=self.tenant_a, part=part, step=step, status="FAIL",
                                               description="Burr on the seat")
        disp = QuarantineDisposition.objects.get(quality_reports=visual)
        bore = MeasurementDefinition.objects.create(tenant=self.tenant_a, label="Bore", type="NUMERIC",
                                                    unit="mm", nominal=4.0, upper_tol=0.005, lower_tol=0.005,
                                                    step=step)
        measured = QualityReports.objects.create(tenant=self.tenant_a, part=part, step=step, status="PENDING")
        MeasurementResult.objects.create(tenant=self.tenant_a, report=measured, definition=bore,
                                         value_numeric=4.007)
        disp.quality_reports.add(measured)
        disp.description = "Failed Body Inspection"
        disp.save(update_fields=["description"])
        refresh_disposition_description(disp)
        disp.refresh_from_db()
        self.assertEqual(disp.description,
                         "Failed Body Inspection: Burr on the seat, Bore 4.007 mm (limits 3.995–4.005)")


class BenchFindingTests(TenantTestCase):

    def test_the_latest_applied_finding_without_its_stamp(self):
        """The R1 dialog showed the scrap consequence ("not recovered"), then the whole
        notes; what the customer decides on is the bench finding."""
        from types import SimpleNamespace
        from Tracker.services.reman.rebuild import _bench_note
        hc = SimpleNamespace(condition_notes=(
            "Normal tip wear at teardown.\n"
            "Finding applied (Sarah C., 2026-10-20 16:02): grade B → SCRAP. "
            "Hairline crack at the needle guide, found under magnification after cleaning."))
        self.assertEqual(_bench_note(hc),
                         "Hairline crack at the needle guide, found under magnification after cleaning.")
        self.assertEqual(_bench_note(SimpleNamespace(condition_notes="Normal tip wear")), "Normal tip wear")


class CompleteStepWaitingOnTheLotTests(TenantTestCase):

    def test_a_finished_unit_is_told_it_waits_for_named_lot_mates(self):
        """Blocked with an empty reason left the operator unable to tell whether the
        step was recorded (Operator walk 2026-10-20)."""
        from Tracker.tests.test_advancement_engine import _build_lot, _complete_substeps_for_part
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Injector", ID_prefix="INJ")
        lot = _build_lot(tenant=self.tenant_a, user=self.user_a, part_type=pt, num_parts=2,
                         wo_erp_id="WO-OPS-T")
        done, waiting = lot["parts"]
        _complete_substeps_for_part(tenant=self.tenant_a, user=self.user_a, part=done,
                                    substeps=lot["substeps_by_step"][0])
        self.grant_tenant_permissions(self.user_a, self.tenant_a,
                                      ['view_parts', 'add_parts', 'change_parts', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        resp = self.client.post(f"/api/Parts/{done.id}/complete_step/")
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(body["status"], "blocked", body)
        self.assertIn(f"{done.ERP_id} is recorded", body["reason"])
        self.assertIn(waiting.ERP_id, body["reason"])


class FirstStartAssignsTests(TenantTestCase):

    def test_starting_an_unstarted_part_assigns_the_starter(self):
        """A first start (no execution yet) left assigned_to empty: no operator on the
        traveler, and the qualified-operator gate could refuse done work."""
        from Tracker.models import Parts, StepExecution, WorkOrder
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Body")
        step = Steps.objects.create(tenant=self.tenant_a, name="Machining", part_type=pt)
        wo = WorkOrder.objects.create(tenant=self.tenant_a, ERP_id="WO-FS-1", quantity=1)
        part = Parts.objects.create(tenant=self.tenant_a, ERP_id="FS-1", part_type=pt, work_order=wo,
                                    step=step, part_status="PENDING")
        self.grant_tenant_permissions(self.user_a, self.tenant_a,
                                      ['add_stepexecution', 'view_stepexecution', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        resp = self.client.post("/api/StepExecutions/", {
            "part": str(part.id), "step": str(step.id), "status": "IN_PROGRESS", "visit_number": 1},
            format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(StepExecution.objects.get(part=part, step=step).assigned_to_id, self.user_a.id)


class OperatorSendToReworkTests(_Api):
    """Sending a part to rework from WO control asks why and opens the NCR QA sees; if
    QA got there first, their disposition stands and the operator's report joins it
    (user decisions 2026-10-21)."""
    perms = ['view_parts', 'change_parts', 'full_tenant_access']

    def setUp(self):
        super().setUp()
        from Tracker.models import Parts, WorkOrder
        self.pt = PartTypes.objects.create(tenant=self.tenant_a, name="Body")
        self.step = Steps.objects.create(tenant=self.tenant_a, name="Machining", part_type=self.pt)
        self.rework = Steps.objects.create(tenant=self.tenant_a, name="Rework", part_type=self.pt,
                                           step_type="REWORK")
        wo = WorkOrder.objects.create(tenant=self.tenant_a, ERP_id="WO-RW-1", quantity=2)
        self.part = Parts.objects.create(tenant=self.tenant_a, ERP_id="RW-1", part_type=self.pt,
                                         work_order=wo, step=self.step, part_status="IN_PROGRESS")

    def test_it_opens_an_unassigned_rework_disposition_with_the_reason(self):
        from Tracker.services.qms.disposition import record_operator_rework
        disp = record_operator_rework(self.part, self.user_a, "Burr on the seat face")
        self.assertEqual((disp.assigned_to_id, disp.disposition_type), (None, "REWORK"))
        report, = disp.quality_reports.all()
        self.assertEqual((report.status, report.step_id, report.detected_by_id),
                         ("FAIL", self.step.id, self.user_a.id))
        self.assertIn("Burr on the seat face", report.description)
        self.assertEqual(QuarantineDisposition.objects.filter(part=self.part).count(), 1)
        self.part.refresh_from_db()
        self.assertNotEqual(self.part.part_status, "QUARANTINED")   # it goes on to rework

    def test_qa_got_there_first_so_their_disposition_stands(self):
        from Tracker.services.qms.disposition import record_operator_rework
        qa_report = QualityReports.objects.create(tenant=self.tenant_a, part=self.part, step=self.step,
                                                  status="FAIL", description="QA: seat out of round")
        qa_disp = QuarantineDisposition.objects.get(quality_reports=qa_report)
        disp = record_operator_rework(self.part, self.user_a, "Burr on the seat face")
        self.assertEqual(disp.pk, qa_disp.pk)
        self.assertEqual(QuarantineDisposition.objects.filter(part=self.part).count(), 1)
        self.assertEqual(disp.quality_reports.count(), 2)

    def test_the_reason_is_required_and_a_bare_step_move_into_rework_is_refused(self):
        resp = self.client.post(f"/api/Parts/{self.part.id}/split_from_lot/",
                                {"reason": "rework", "rework_target_step_id": str(self.rework.id)}, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)
        resp = self.client.patch(f"/api/Parts/{self.part.id}/", {"step": str(self.rework.id)}, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("Send it to rework", resp.content.decode())


class HeldUnitsNotLoadableTests(_Api):
    perms = ['view_batchexecution', 'add_batchexecution', 'full_tenant_access']

    def test_a_held_unit_cant_go_into_a_load(self):
        """Sealing a load would carry a held unit past its hold (a core awaiting the
        customer's answer) — Operator walk 2026-10-21."""
        from Tracker.models import Parts, WorkOrder
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Core")
        step = Steps.objects.create(tenant=self.tenant_a, name="Cleaning", part_type=pt)
        wo = WorkOrder.objects.create(tenant=self.tenant_a, ERP_id="WO-LD-1", quantity=2)
        ok = Parts.objects.create(tenant=self.tenant_a, ERP_id="CORE-OK", part_type=pt, work_order=wo,
                                  step=step, part_status="IN_PROGRESS")
        held = Parts.objects.create(tenant=self.tenant_a, ERP_id="CORE-HELD", part_type=pt, work_order=wo,
                                    step=step, part_status="ON_HOLD")
        body = {"work_order": str(wo.id), "step": str(step.id), "parts": [str(ok.id), str(held.id)]}
        resp = self.client.post("/api/BatchExecutions/", body, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("CORE-HELD", resp.content.decode())
        body["parts"] = [str(ok.id)]
        self.assertEqual(self.client.post("/api/BatchExecutions/", body, format="json").status_code, 201)


class ReCaptureAfterVoidTests(TenantTestCase):
    """A substep voided and captured again: the new reading is the next version of the
    old, which stays on file (unscoped) but no longer counts (user decision 2026-10-21).
    It held two Body OD readings, 6.004 voided and 6.003, on one PASS report."""

    def test_the_re_capture_supersedes_the_voided_reading(self):
        from Tracker.models import (
            MeasurementDefinition, MeasurementResult, StepExecutionMeasurement, SubstepCompletion)
        from Tracker.services.qms.inline_capture import record_dwi_measurement
        from Tracker.tests.test_advancement_engine import _build_lot
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Body", ID_prefix="BOD")
        lot = _build_lot(tenant=self.tenant_a, user=self.user_a, part_type=pt, wo_erp_id="WO-RC-1")
        ex, substep = lot["execs"][0], lot["substeps_by_step"][0][0]
        substep.is_inspection_point = True
        substep.save(update_fields=["is_inspection_point"])
        od = MeasurementDefinition.objects.create(tenant=self.tenant_a, label="Body OD", type="NUMERIC",
                                                  unit="mm", nominal=6.0, upper_tol=0.01, lower_tol=0.01,
                                                  step=substep.step)
        record_dwi_measurement(step_execution=ex, substep=substep, measurement_definition=od,
                               value=6.004, recorded_by=self.user_a)
        SubstepCompletion.objects.create(tenant=self.tenant_a, step_execution=ex, substep=substep,
                                         completed_by=self.user_a, is_voided=True)
        record_dwi_measurement(step_execution=ex, substep=substep, measurement_definition=od,
                               value=6.003, recorded_by=self.user_a)

        current = list(StepExecutionMeasurement.objects.filter(step_execution=ex, measurement_definition=od))
        self.assertEqual([float(m.value) for m in current], [6.003])
        self.assertEqual(float(current[0].previous_version.value), 6.004)
        self.assertEqual(StepExecutionMeasurement.unscoped.filter(step_execution=ex, measurement_definition=od).count(), 2)
        report = MeasurementResult.objects.get(definition=od).report
        self.assertEqual([r.value_numeric for r in report.measurements.all()], [6.003])
        self.assertEqual(MeasurementResult.unscoped.filter(report=report).count(), 2)

    def test_a_first_capture_appends_as_before(self):
        from Tracker.models import MeasurementDefinition, StepExecutionMeasurement
        from Tracker.services.qms.inline_capture import record_dwi_measurement
        from Tracker.tests.test_advancement_engine import _build_lot
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Body2", ID_prefix="BOE")
        lot = _build_lot(tenant=self.tenant_a, user=self.user_a, part_type=pt, wo_erp_id="WO-RC-2")
        ex, substep = lot["execs"][0], lot["substeps_by_step"][0][0]
        od = MeasurementDefinition.objects.create(tenant=self.tenant_a, label="OD", type="NUMERIC",
                                                  nominal=6.0, upper_tol=0.01, lower_tol=0.01, step=substep.step)
        for v in (6.004, 6.003):
            record_dwi_measurement(step_execution=ex, substep=substep, measurement_definition=od,
                                   value=v, recorded_by=self.user_a)
        self.assertEqual(StepExecutionMeasurement.objects.filter(step_execution=ex).count(), 2)


class StagedPartIsWaitingNotMovedTests(TenantTestCase):

    def test_a_staged_part_names_its_held_lot_mate_and_the_split(self):
        """The toast said "1 part moved" for a part only staged behind a held lot-mate
        (Operator walk 2026-10-21). Lock-step stays (user): the lot waits; the message
        names who and the way out."""
        from Tracker.models import Parts
        from Tracker.services.mes.advancement import try_advance_lot
        from Tracker.tests.test_advancement_engine import _build_lot, _complete_substeps_for_part
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Core", ID_prefix="COR")
        lot = _build_lot(tenant=self.tenant_a, user=self.user_a, part_type=pt, num_parts=2,
                         wo_erp_id="WO-ST-1")
        step = lot["steps"][0]
        # Per-part path (as a batch step takes): parts advance individually, but this
        # step's lot moves together (requires_batch_completion).
        Steps.objects.filter(pk=step.pk).update(requires_batch_completion=True,
                                                part_advancement_mode='PER_PART')
        step.refresh_from_db()
        done, held = lot["parts"]
        Parts.objects.filter(pk=held.pk).update(part_status="ON_HOLD")
        _complete_substeps_for_part(tenant=self.tenant_a, user=self.user_a, part=done,
                                    substeps=lot["substeps_by_step"][0])
        result = try_advance_lot(work_order_id=str(lot["wo"].id), step_id=str(step.id),
                                 tenant_id=str(self.tenant_a.id), operator=self.user_a)
        self.assertNotIn(str(done.id), result.parts_advanced)
        msg = " ".join(result.blockers_by_part.get(str(done.id), []))
        self.assertIn(held.ERP_id, msg)
        self.assertIn("Split it from the lot", msg)

    def test_splitting_the_held_part_off_moves_the_lot_on(self):
        """"Split it from the lot to let the rest move" has to be true: the part staged
        behind the held one moves once it's split off (Operator walk 2026-10-21)."""
        from Tracker.models import Parts
        from Tracker.services.mes.advancement import try_advance_lot
        from Tracker.services.mes.work_order import move_staged_lots_on, split_work_order
        from Tracker.tests.test_advancement_engine import _build_lot, _complete_substeps_for_part
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Core2", ID_prefix="CRB")
        lot = _build_lot(tenant=self.tenant_a, user=self.user_a, part_type=pt, num_parts=2,
                         wo_erp_id="WO-ST-2")
        step = lot["steps"][0]
        Steps.objects.filter(pk=step.pk).update(requires_batch_completion=True,
                                                part_advancement_mode='PER_PART')
        done, held = lot["parts"]
        Parts.objects.filter(pk=held.pk).update(part_status="ON_HOLD")
        _complete_substeps_for_part(tenant=self.tenant_a, user=self.user_a, part=done,
                                    substeps=lot["substeps_by_step"][0])
        try_advance_lot(work_order_id=str(lot["wo"].id), step_id=str(step.id),
                        tenant_id=str(self.tenant_a.id), operator=self.user_a)
        done.refresh_from_db()
        self.assertEqual((done.step_id, done.part_status), (step.id, "READY_FOR_NEXT_STEP"))
        split_work_order(lot["wo"], "OPERATION", self.user_a, "WO-ST-2-A", part_ids=[str(held.id)])
        moved = move_staged_lots_on(lot["wo"], self.user_a)
        done.refresh_from_db()
        self.assertNotEqual(done.step_id, step.id)
        self.assertEqual([m[0] for m in moved], [done.ERP_id])


class SweepFixes1022Tests(_Api):
    """Known-catches sweep, 2026-10-22."""
    perms = ['view_companies', 'view_orders', 'change_orders', 'add_orderviewer', 'full_tenant_access']

    def test_customer_property_does_not_make_a_customer_a_supplier(self):
        customer = Companies.objects.create(tenant=self.tenant_a, name="Midwest Fleet",
                                            is_customer=True)
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Their part")
        MaterialLot.objects.create(tenant=self.tenant_a, lot_number="CUST-1", supplier=customer,
                                   owner=customer, material_type=pt, quantity=1,
                                   quantity_remaining=1, received_date=timezone.now().date(),
                                   unit_of_measure="EA")
        names = {c["name"] for c in self.client.get("/api/Companies/", {"supplying": "true"}).json()["results"]}
        self.assertNotIn(customer.name, names)

    def test_a_customer_invite_is_a_portal_user_with_a_pending_invitation(self):
        from Tracker.models import Orders, User, UserInvitation
        company = Companies.objects.create(tenant=self.tenant_a, name="Great Lakes Diesel",
                                           is_customer=True)
        order = Orders.objects.create(tenant=self.tenant_a, name="ORD-INV", company=company,
                                      customer=self.user_a)
        resp = self.client.post(f"/api/TrackerOrders/{order.id}/invite/",
                                {"email": "buyer@gld.test"}, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        u = User.objects.get(email="buyer@gld.test")
        self.assertEqual((u.user_type, u.parent_company_id, u.is_active, u.has_usable_password()),
                         ("PORTAL", company.id, True, False))
        self.assertTrue(UserInvitation.objects.filter(user=u, accepted_at__isnull=True).exists())

    def test_the_matrix_lists_people_with_training_at_stake(self):
        from Tracker.models import TrainingRecord, TrainingType, User
        from Tracker.services.training import build_training_matrix
        tt = TrainingType.objects.create(tenant=self.tenant_a, name="Wash")
        op = User.objects.create(tenant=self.tenant_a, username="op@x.test", email="op@x.test",
                                 user_type="INTERNAL")
        User.objects.create(tenant=self.tenant_a, username="buyer@x.test", email="buyer@x.test",
                            user_type="INTERNAL")
        TrainingRecord.objects.create(tenant=self.tenant_a, user=op, training_type=tt,
                                      completed_date=timezone.now().date(), level=3)
        matrix = build_training_matrix(self.tenant_a)
        rows = matrix.get("operators") or matrix.get("users") or matrix.get("rows") or []
        emails = {r.get("email") or r.get("name") for r in rows}
        ids = {str(r.get("id") or r.get("user_id")) for r in rows}
        self.assertIn(str(op.id), ids)
        self.assertFalse(any("buyer" in str(e) for e in emails))


class PersonAccessHistoryTests(_Api):
    perms = ['view_user', 'full_tenant_access']

    def test_role_grants_removals_and_suspension_show_on_the_person(self):
        """Administrator walk: they live on UserRole / TenantMembership, so the person's
        own History read "No recorded changes"."""
        from auditlog.context import set_actor
        from Tracker.models import User, UserRole
        from Tracker.services.core.tenant_membership import suspend_membership
        from Tracker.services.core.user import add_user_to_tenant_group
        dave = User.objects.create(tenant=self.tenant_a, username="dave@x.test",
                                   email="dave@x.test", user_type="INTERNAL")
        with set_actor(self.user_a):
            add_user_to_tenant_group(dave, "Operator", tenant=self.tenant_a, granted_by=self.user_a)
            UserRole.objects.filter(user=dave).delete()
            suspend_membership(dave, self.tenant_a, by=self.user_a)
        rows = self.client.get(f"/api/User/{dave.id}/access-history/").json()
        seen = {(r["content_type_name"].lower().replace(" ", ""), r["action"]) for r in rows}
        self.assertIn(("userrole", 0), seen)      # granted
        self.assertIn(("userrole", 2), seen)      # removed
        self.assertIn(("tenantmembership", 1), seen)  # suspended

    def test_never_invited_is_not_a_pending_invite(self):
        from Tracker.models import User
        u = User.objects.create(tenant=self.tenant_a, username="seeded@x.test",
                                email="seeded@x.test", user_type="INTERNAL")
        row = self.client.get(f"/api/User/{u.id}/").json()
        self.assertIsNone(row["invitation_state"])

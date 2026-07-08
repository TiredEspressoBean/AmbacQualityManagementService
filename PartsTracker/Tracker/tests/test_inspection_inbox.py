"""The QA inspector's task inbox (services.qms.inspection_inbox + endpoint).

One flat list across FPI / receiving / OSP / in-process, with the sampling
answer, severity badge, resume progress, blocked reasons, and type counts.
"""
import datetime
from decimal import Decimal

from Tracker.tests.base import TenantTestCase
from Tracker.models import (
    Companies, FPIRecord, MaterialLot, MeasurementResult, Parts, PartTypes,
    Processes, QualityReports, SamplingRuleSet, SamplingSeverityState, Steps,
    WorkOrder, WorkOrderStatus,
)
from Tracker.services.qms.inspection_inbox import build_inbox


class InspectionInboxTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.supplier = Companies.objects.create(tenant=self.tenant_a, name="Acme Machining", description="")
        self.part_type = PartTypes.objects.create(tenant=self.tenant_a, name="Nozzle")
        # Standalone RECEIVING step (a RIP) for the part type → plan + severity resolve.
        self.receiving_step = Steps.objects.create(
            tenant=self.tenant_a, name="Receiving — Nozzle",
            part_type=self.part_type, step_type="RECEIVING")
        self.ruleset = SamplingRuleSet.objects.create(
            tenant=self.tenant_a, part_type=self.part_type, step=self.receiving_step,
            supplier=self.supplier, name="Receiving Z1.4", active=True,
            aql=Decimal("1.0"), inspection_level="II", severity="NORMAL", strategy="Z14")

    def _lot(self, n="LOT-001", status="AWAITING_INSPECTION", hold=""):
        return MaterialLot.objects.create(
            tenant=self.tenant_a, lot_number=n,
            received_date=datetime.date.today(), received_by=self.user_a,
            quantity=Decimal("500"), quantity_remaining=Decimal("500"),
            unit_of_measure="EA", status=status, hold_reason=hold,
            material_type=self.part_type, supplier=self.supplier)

    def test_receiving_row_carries_plan_and_severity(self):
        SamplingSeverityState.objects.create(
            tenant=self.tenant_a, step=self.receiving_step, supplier=self.supplier,
            severity="TIGHTENED", consecutive_accepts=2,
            recent_outcomes=["R", "R", "A", "A"])
        self._lot()

        inbox = build_inbox()
        rows = [r for r in inbox["rows"] if r["type"] == "receiving"]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertIn("Lot LOT-001", row["title"])
        self.assertEqual(row["detail"], "Acme Machining")
        # The sampling ANSWER, not the tables (tightened plan for lot size 500).
        self.assertRegex(row["plan"], r"^n=\d+ · Ac \d+$")
        self.assertEqual(row["severity"]["severity"], "TIGHTENED")
        self.assertEqual(row["severity"]["accepts_needed"], 3)
        self.assertEqual(row["severity"]["rejects_in_window"], 2)
        self.assertIsNone(row["blocked_reason"])

    def test_blocked_lot_sinks_but_stays_counted(self):
        self._lot(n="LOT-HELD", status="QUARANTINE", hold="SUPPLIER_UNQUALIFIED")

        inbox = build_inbox()
        rows = [r for r in inbox["rows"] if r["type"] == "receiving"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["blocked_reason"], "SUPPLIER_UNQUALIFIED")
        self.assertIsNone(rows[0]["plan"])
        self.assertEqual(rows[0]["due_tone"], "gray")
        self.assertEqual(inbox["blocked"], 1)
        self.assertEqual(inbox["counts"]["receiving"]["count"], 1)

    def test_resume_progress_from_per_unit_results(self):
        lot = self._lot()
        report = QualityReports.objects.create(
            tenant=self.tenant_a, material_lot=lot, step=self.receiving_step,
            status="PENDING", sample_size=13, accept_number=1, reject_number=2,
            detected_by=self.user_a)
        from Tracker.models import MeasurementDefinition
        definition = MeasurementDefinition.objects.create(
            tenant=self.tenant_a, step=self.receiving_step, label="Bore",
            type="NUMERIC", unit="mm",
            nominal=Decimal("1.0"), upper_tol=Decimal("0.1"), lower_tol=Decimal("0.1"))
        for i in range(1, 8):
            MeasurementResult.objects.create(
                tenant=self.tenant_a, report=report, definition=definition,
                sample_number=i, value_numeric=Decimal("1.0"), is_within_spec=True,
                created_by=self.user_a)

        inbox = build_inbox()
        row = [r for r in inbox["rows"] if r["type"] == "receiving"][0]
        self.assertEqual(row["resume"], "7 of 13 samples")

    def test_in_process_groups_by_operation(self):
        process = Processes.objects.create(tenant=self.tenant_a, name="Injector", part_type=self.part_type)
        step = Steps.objects.create(
            tenant=self.tenant_a, name="Nozzle Inspection", part_type=self.part_type, step_type="TASK")
        wo = WorkOrder.objects.create(
            tenant=self.tenant_a, ERP_id="WO-2026-01",
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=3, process=process,
            expected_completion=datetime.date.today() + datetime.timedelta(days=1))
        for i in range(3):
            Parts.objects.create(
                tenant=self.tenant_a, ERP_id=f"P-{i}", part_type=self.part_type,
                work_order=wo, step=step)

        # Parts.save() recomputes requires_sampling from sampling rules; set it
        # via update() so the fixture states the fact the inbox reads.
        Parts.objects.filter(work_order=wo).update(requires_sampling=True)

        inbox = build_inbox()
        rows = [r for r in inbox["rows"] if r["type"] == "in_process"]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["title"], "Nozzle Inspection · 3 pcs")
        self.assertEqual(row["wo"], "WO-2026-01")
        self.assertEqual(row["quantity"], 3)
        self.assertEqual(row["due_tone"], "orange")  # WO due within 2 days

    def test_fpi_rows_sort_first_and_are_red(self):
        self._lot()
        process = Processes.objects.create(tenant=self.tenant_a, name="Injector", part_type=self.part_type)
        step = Steps.objects.create(
            tenant=self.tenant_a, name="Final Test", part_type=self.part_type, step_type="TASK")
        wo = WorkOrder.objects.create(
            tenant=self.tenant_a, ERP_id="WO-2026-02",
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=1, process=process)
        FPIRecord.objects.create(
            tenant=self.tenant_a, work_order=wo, step=step,
            part_type=self.part_type, status="PENDING")

        inbox = build_inbox()
        self.assertEqual(inbox["rows"][0]["type"], "fpi")
        self.assertEqual(inbox["rows"][0]["due_tone"], "red")
        self.assertEqual(inbox["counts"]["fpi"]["count"], 1)

    def test_endpoint_returns_payload(self):
        from rest_framework.test import APIClient
        self._lot()
        client = APIClient()
        client.force_authenticate(user=self.user_a)
        client.credentials(HTTP_X_TENANT_ID=str(self.tenant_a.id))

        response = client.get('/api/InspectionInbox/')
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body["total"], len(body["rows"]))
        self.assertIn("receiving", body["counts"])

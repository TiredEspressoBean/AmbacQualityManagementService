"""The FPI buy-off shows the first piece's readings (QA Inspector walk, 2026-10-20).

The dialog asked QA to attest "the first piece conforms" with only a Notes box: the
readings existed (StepExecutionMeasurement) but no buy-off surface showed them. The
FPI record now carries them.
"""
from decimal import Decimal

from Tracker.models import (
    FPIRecord, FPIStatus, MeasurementDefinition, Parts, PartTypes, StepExecution,
    StepExecutionMeasurement, Steps, WorkOrder,
)
from Tracker.tests.base import TenantTestCase


class FirstPieceReadingsTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Injector")
        self.step = Steps.objects.create(tenant=self.tenant_a, name="Flow test", part_type=pt)
        wo = WorkOrder.objects.create(tenant=self.tenant_a, ERP_id="WO-FPIR-1", quantity=2)
        self.part = Parts.objects.create(tenant=self.tenant_a, ERP_id="FPIR-1", part_type=pt,
                                         work_order=wo, step=self.step, part_status="IN_PROGRESS")
        self.fpi = FPIRecord.objects.create(tenant=self.tenant_a, work_order=wo, step=self.step,
                                            part_type=pt, status=FPIStatus.PENDING,
                                            designated_part=self.part)
        ex = StepExecution.objects.create(tenant=self.tenant_a, part=self.part, step=self.step,
                                          visit_number=1, status="IN_PROGRESS")
        angle = MeasurementDefinition.objects.create(
            tenant=self.tenant_a, label="Spray angle", type="NUMERIC", unit="deg",
            nominal=15.0, upper_tol=1.0, lower_tol=1.0, step=self.step)
        StepExecutionMeasurement.objects.create(
            tenant=self.tenant_a, step_execution=ex, measurement_definition=angle,
            value=Decimal("15.0"), recorded_by=self.user_a)
        self.grant_tenant_permissions(self.user_a, self.tenant_a, ['view_fpirecord', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)

    def test_the_record_carries_the_first_pieces_readings(self):
        resp = self.client.get(f"/api/FPIRecords/{self.fpi.id}/")
        self.assertEqual(resp.status_code, 200, resp.content)
        row, = resp.json()["first_piece_readings"]
        self.assertEqual(row["label"], "Spray angle")
        self.assertEqual(Decimal(row["value"]), Decimal("15.0"))
        self.assertEqual((Decimal(row["lower_limit"]), Decimal(row["upper_limit"])),
                         (Decimal("14"), Decimal("16")))
        self.assertTrue(row["within_spec"])

    def test_no_designated_piece_means_no_readings(self):
        FPIRecord.objects.filter(pk=self.fpi.pk).update(designated_part=None)
        resp = self.client.get(f"/api/FPIRecords/{self.fpi.id}/")
        self.assertEqual(resp.json()["first_piece_readings"], [])


class FailedFirstPieceTests(FirstPieceReadingsTests):
    """A failed first piece is nonconforming product (user decision 2026-10-20): a FAIL
    report on it, quarantine, an unassigned disposition — and the FPI's reason as the
    description. Also: who signed the first piece is on the record, so the dialog can
    say before the click that they can't buy it off."""

    def test_failing_the_first_piece_quarantines_it_and_opens_a_disposition(self):
        from Tracker.models import QuarantineDisposition
        from Tracker.services.qms.fpi import fail_fpi
        fail_fpi(self.fpi, self.user_a, notes="Spray pattern skewed — setup off")
        self.fpi.refresh_from_db()
        self.part.refresh_from_db()
        self.assertEqual(self.part.part_status, "QUARANTINED")
        self.assertEqual(self.fpi.quality_report.status, "FAIL")
        disp = QuarantineDisposition.objects.get(quality_reports=self.fpi.quality_report)
        self.assertIsNone(disp.assigned_to_id)
        self.assertIn("Spray pattern skewed", disp.description)

    def test_the_record_lists_who_signed_the_first_piece(self):
        from Tracker.models import StepExecution, SubstepCompletion, Substep
        ex = StepExecution.objects.get(part=self.part, step=self.step)
        sub = Substep.objects.create(tenant=self.tenant_a, step=self.step, order=0, title="Inspect",
                                     body_blocks={"type": "doc", "content": []})
        SubstepCompletion.objects.create(tenant=self.tenant_a, step_execution=ex, substep=sub,
                                         completed_by=self.user_a)
        resp = self.client.get(f"/api/FPIRecords/{self.fpi.id}/")
        self.assertEqual(resp.json()["first_piece_signer_ids"], [self.user_a.id])

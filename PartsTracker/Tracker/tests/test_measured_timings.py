"""Measured step timings, per aspect (2026-11-03): setup and per-piece time fitted from
runs of different lot sizes, cycle per load from batch loads, hold time left out, and
the scheduler reading each measured aspect only where the authored one is unset."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from Tracker.models import (
    BatchExecution, OptimizationConfig, Parts, PartTypes, Processes, StepExecution, Steps,
    StepTiming, Tenant, WorkOrder, WorkOrderHold, WorkOrderStatus,
)
from Tracker.services.scheduling import data
from Tracker.services.scheduling.measured import compare_step_timings, measure_step_timings
from Tracker.tests.base import TenantContextMixin


class MeasuredTimingTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Measure", slug="measured-timings", tier="PRO")
        self.set_tenant_context(self.tenant)
        self.user = get_user_model().objects.create_user(
            username="mt-admin", email="mt@c.test", password="x", tenant=self.tenant,
            is_staff=True, is_superuser=True)
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Injector")
        self.process = Processes.objects.create(tenant=self.tenant, name="P", part_type=self.pt)
        self.step = Steps.objects.create(tenant=self.tenant, part_type=self.pt, name="Lap", step_type="TASK")
        self.wash = Steps.objects.create(tenant=self.tenant, part_type=self.pt, name="Wash", step_type="TASK")
        self.t0 = timezone.now() - timedelta(days=30)
        self._n = 0

    def _run(self, pieces, minutes, step=None, start=None):
        """One work order of `pieces` parts through the step lock-step, taking `minutes`."""
        self._n += 1
        start = start or self.t0 + timedelta(hours=self._n * 10)
        wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id=f"WO-M{self._n}", workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=pieces, process=self.process)
        for i in range(pieces):
            part = Parts.objects.create(tenant=self.tenant, ERP_id=f"P-M{self._n}-{i}",
                                        part_type=self.pt, work_order=wo, step=step or self.step)
            ex = StepExecution.objects.create(tenant=self.tenant, part=part, step=step or self.step,
                                              visit_number=1, status="COMPLETED")
            StepExecution.objects.filter(pk=ex.pk).update(
                started_at=start, exited_at=start + timedelta(minutes=minutes))
        return wo, start

    def test_setup_and_per_piece_are_fitted_from_lot_sizes(self):
        for n in (2, 2, 4, 4, 6, 8, 8, 10):
            self._run(n, 20 + 3 * n)
        m = measure_step_timings(self.tenant)[self.step.id]
        self.assertEqual((m.method, m.runs, m.pieces), ("fit", 8, 44))
        self.assertAlmostEqual(m.setup_minutes, 20, places=1)
        self.assertAlmostEqual(m.per_piece_minutes, 3, places=1)
        t = data.get_step_timings(self.tenant)[self.step.id]
        self.assertEqual((t.cycle_source, t.setup_source), ("measured", "measured"))
        self.assertAlmostEqual(t.setup_minutes, 20, places=1)

    def test_alike_lot_sizes_fall_back_to_the_average_per_piece_and_say_so(self):
        for _ in range(8):
            self._run(4, 32)
        m = measure_step_timings(self.tenant)[self.step.id]
        self.assertEqual(m.method, "average")
        self.assertIsNone(m.setup_minutes)
        self.assertAlmostEqual(m.per_piece_minutes, 8, places=1)
        self.assertIn("too alike", m.note)
        self.assertEqual(data.get_step_timings(self.tenant)[self.step.id].setup_source, "none")

    def test_hold_time_is_left_out(self):
        for _ in range(4):
            self._run(1, 10)
        wo, start = self._run(1, 70)  # 60 of its 70 minutes were on hold
        WorkOrderHold.objects.create(tenant=self.tenant, work_order=wo, reason="QUALITY",
                                     placed_by=self.user, placed_at=start + timedelta(minutes=5),
                                     cleared_at=start + timedelta(minutes=65))
        m = measure_step_timings(self.tenant)[self.step.id]
        self.assertAlmostEqual(m.per_piece_minutes, 10, places=1)

    def _batch_step(self):
        from Tracker.models import Substep, SubstepScope
        Substep.objects.create(tenant=self.tenant, step=self.wash, title="Bath temp", order=1,
                               scope=SubstepScope.BATCH)

    def test_a_batch_step_measures_cycle_seal_to_complete_and_load_start_to_seal(self):
        self._batch_step()
        wo = None
        for _ in range(6):
            wo, _ = self._run(3, 40, step=self.wash)  # per-part records: never a per-piece figure
        for i in range(5):
            b = BatchExecution.objects.create(tenant=self.tenant, work_order=wo, step=self.wash,
                                              started_by=self.user)
            start = self.t0 + timedelta(days=1, hours=i * 3)
            BatchExecution.objects.filter(pk=b.pk).update(
                started_at=start, sealed_at=start + timedelta(minutes=15),
                completed_at=start + timedelta(minutes=105))
        # A load still loading, and one sealed and running: neither has finished a cycle.
        BatchExecution.objects.create(tenant=self.tenant, work_order=wo, step=self.wash,
                                      started_by=self.user)
        running = BatchExecution.objects.create(tenant=self.tenant, work_order=wo, step=self.wash,
                                                started_by=self.user)
        BatchExecution.objects.filter(pk=running.pk).update(sealed_at=timezone.now())
        m = measure_step_timings(self.tenant)[self.wash.id]
        self.assertEqual((m.method, m.loads, m.cycle_per_load_minutes, m.load_per_load_minutes),
                         ("batch", 5, 90, 15))
        self.assertIsNone(m.per_piece_minutes)
        t = data.get_step_timings(self.tenant)[self.wash.id]
        self.assertEqual((t.cycle_time_minutes, t.cycle_source), (90, "measured"))
        StepTiming.objects.create(tenant=self.tenant, step=self.wash, cycle_time_minutes=85)
        row = next(r for r in compare_step_timings(self.tenant) if r.step_id == self.wash.id)
        self.assertFalse(row.cycle_drift, "compared per load: 90 against 85 is inside 25%")

    def test_a_batch_step_without_enough_loads_does_not_fall_back_to_per_piece(self):
        self._batch_step()
        for _ in range(6):
            self._run(3, 40, step=self.wash)
        m = measure_step_timings(self.tenant)[self.wash.id]
        self.assertEqual((m.method, m.per_piece_minutes, m.cycle_per_load_minutes), ("batch", None, None))
        self.assertIn("per load", m.note)
        self.assertNotEqual(data.get_step_timings(self.tenant)[self.wash.id].cycle_source, "measured")

    def test_authored_wins_and_drift_is_flagged_past_the_setting(self):
        for _ in range(5):
            self._run(1, 10)
        StepTiming.objects.create(tenant=self.tenant, step=self.step, cycle_time_minutes=6)
        t = data.get_step_timings(self.tenant)[self.step.id]
        self.assertEqual((t.cycle_time_minutes, t.cycle_source), (6, "timing"))
        row = next(r for r in compare_step_timings(self.tenant) if r.step_id == self.step.id)
        self.assertEqual((row.cycle_in_use, row.cycle_drift), ("authored", True))
        OptimizationConfig.objects.create(tenant=self.tenant, timing_drift_pct=0)
        row = next(r for r in compare_step_timings(self.tenant) if r.step_id == self.step.id)
        self.assertFalse(row.cycle_drift, "0 turns the flag off")

    def test_the_endpoint_lists_measured_beside_in_use(self):
        for _ in range(5):
            self._run(1, 10)
        client = APIClient()
        client.force_authenticate(user=self.user)
        client.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        r = client.get("/api/StepTimings/measured/", {"step": str(self.step.id)})
        self.assertEqual(r.status_code, 200, r.content)
        [row] = r.json()
        self.assertEqual((row["runs"], row["per_piece_minutes"], row["cycle_in_use"]),
                         (5, 10.0, "measured"))
        self.assertIsNone(row["setup_minutes"])

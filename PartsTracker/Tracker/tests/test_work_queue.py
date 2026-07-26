"""Work-queue endpoint tests — the operator home's aggregate.

Covers grain, ranking, the held→blocked bucket, null-part exclusion, tenant
isolation, and API permission gating.
"""
from django.utils import timezone

from Tracker.models import (
    PartTypes, Processes, Steps, ProcessStep, WorkOrder, Parts, StepExecution,
    WorkOrderHold, WorkOrderHoldReason, WorkCenter, WorkCenterKind,
)
from Tracker.models.mes_lite import WorkOrderStatus
from Tracker.tests.base import TenantTestCase


class WorkQueueApiTests(TenantTestCase):
    """Uses TenantTestCase's tenant_a fixture; builds fresh WO/step per test."""

    def setUp(self):
        super().setUp()
        self.grant_tenant_permissions(
            self.user_a, self.tenant_a, ["view_workorder", "full_tenant_access"]
        )

    # --- helpers ------------------------------------------------------------

    def _make_wo(self, *, erp="WO-Q-1", priority=3, tenant=None, expected_completion=None):
        tenant = tenant or self.tenant_a
        pt = PartTypes.objects.create(tenant=tenant, name=f"PT-{erp}")
        proc = Processes.objects.create(tenant=tenant, name=f"P-{erp}", part_type=pt)
        return pt, proc, WorkOrder.objects.create(
            tenant=tenant, ERP_id=erp, priority=priority, quantity=1,
            workorder_status=WorkOrderStatus.IN_PROGRESS, process=proc,
            expected_completion=expected_completion,
        )

    def _step(self, *, name, part_type, tenant=None):
        tenant = tenant or self.tenant_a
        return Steps.objects.create(
            tenant=tenant, part_type=part_type, name=name, step_type="TASK",
        )

    def _part_at_step(self, *, wo, part_type, step, erp, tenant=None, entered_at=None):
        tenant = tenant or self.tenant_a
        p = Parts.objects.create(
            tenant=tenant, ERP_id=erp, part_type=part_type, work_order=wo, step=step,
        )
        StepExecution.objects.create(
            tenant=tenant, part=p, step=step, status="IN_PROGRESS",
            entered_at=entered_at or timezone.now(),
        )
        return p

    def _get(self, params=None):
        self.authenticate_as(self.user_a, self.tenant_a)
        return self.client.get("/api/WorkQueue/", params or {})

    # --- grain / basic shape -----------------------------------------------

    def test_grain_is_wo_by_step_with_qty(self):
        pt, proc, wo = self._make_wo(erp="WO-Q-A")
        s_heat = self._step(name="Heat Treat", part_type=pt)
        s_test = self._step(name="Flow Test", part_type=pt)
        # 3 parts at Heat Treat, 2 parts at Flow Test.
        for i in range(3):
            self._part_at_step(wo=wo, part_type=pt, step=s_heat, erp=f"P-H-{i}")
        for i in range(2):
            self._part_at_step(wo=wo, part_type=pt, step=s_test, erp=f"P-T-{i}")

        resp = self._get()
        self.assertEqual(resp.status_code, 200)
        results = resp.data["results"]
        by_step = {r["step_name"]: r for r in results}
        self.assertEqual(len(results), 2, results)
        self.assertEqual(by_step["Heat Treat"]["qty_ready"], 3)
        self.assertEqual(by_step["Flow Test"]["qty_ready"], 2)
        # And the row exposes the WO id + ERP id.
        self.assertEqual(by_step["Heat Treat"]["work_order_erp_id"], "WO-Q-A")
        self.assertEqual(by_step["Heat Treat"]["readiness"], "ready")

    def test_ranking_priority_wins(self):
        pt_a, proc_a, urgent = self._make_wo(erp="WO-URG", priority=1)  # Urgent
        pt_b, proc_b, low = self._make_wo(erp="WO-LOW", priority=4)     # Low
        s_urg = self._step(name="A", part_type=pt_a)
        s_low = self._step(name="B", part_type=pt_b)
        self._part_at_step(wo=urgent, part_type=pt_a, step=s_urg, erp="P-U")
        self._part_at_step(wo=low, part_type=pt_b, step=s_low, erp="P-L")

        results = self._get().data["results"]
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["work_order_erp_id"], "WO-URG")
        self.assertEqual(results[1]["work_order_erp_id"], "WO-LOW")

    # --- held → blocked bucket ---------------------------------------------

    def test_held_wo_marked_blocked_and_sinks(self):
        pt_r, _, ready = self._make_wo(erp="WO-READY", priority=3)
        pt_h, _, held = self._make_wo(erp="WO-HELD", priority=1)  # would rank first...
        WorkOrderHold.objects.create(
            tenant=self.tenant_a, work_order=held,
            reason=WorkOrderHoldReason.OTHER, notes="test hold",
        )
        s_r = self._step(name="A", part_type=pt_r)
        s_h = self._step(name="B", part_type=pt_h)
        self._part_at_step(wo=ready, part_type=pt_r, step=s_r, erp="P-R")
        self._part_at_step(wo=held, part_type=pt_h, step=s_h, erp="P-H")

        results = self._get().data["results"]
        self.assertEqual(len(results), 2)
        # Ready floats above the higher-priority held row.
        self.assertEqual(results[0]["work_order_erp_id"], "WO-READY")
        self.assertEqual(results[0]["readiness"], "ready")
        self.assertEqual(results[1]["work_order_erp_id"], "WO-HELD")
        self.assertEqual(results[1]["readiness"], "blocked")
        self.assertTrue(results[1]["is_held"])

    def test_cleared_hold_does_not_block(self):
        pt, _, wo = self._make_wo(erp="WO-CLEARED")
        s = self._step(name="A", part_type=pt)
        WorkOrderHold.objects.create(
            tenant=self.tenant_a, work_order=wo,
            reason=WorkOrderHoldReason.OTHER, cleared_at=timezone.now(),
        )
        self._part_at_step(wo=wo, part_type=pt, step=s, erp="P-1")

        row = self._get().data["results"][0]
        self.assertEqual(row["readiness"], "ready")
        self.assertFalse(row["is_held"])

    def test_readiness_filter(self):
        pt_r, _, ready = self._make_wo(erp="WO-R")
        pt_h, _, held = self._make_wo(erp="WO-H")
        WorkOrderHold.objects.create(
            tenant=self.tenant_a, work_order=held, reason=WorkOrderHoldReason.OTHER,
        )
        s_r = self._step(name="A", part_type=pt_r)
        s_h = self._step(name="B", part_type=pt_h)
        self._part_at_step(wo=ready, part_type=pt_r, step=s_r, erp="P-R")
        self._part_at_step(wo=held, part_type=pt_h, step=s_h, erp="P-H")

        only_ready = self._get({"readiness": "ready"}).data["results"]
        only_blocked = self._get({"readiness": "blocked"}).data["results"]
        self.assertEqual(len(only_ready), 1)
        self.assertEqual(only_ready[0]["work_order_erp_id"], "WO-R")
        self.assertEqual(len(only_blocked), 1)
        self.assertEqual(only_blocked[0]["work_order_erp_id"], "WO-H")

    # --- null-part exclusion + tenant isolation + perm ----------------------

    def test_null_part_execution_excluded(self):
        # A "receiving-style" open execution with no part must not appear.
        pt, _, wo = self._make_wo(erp="WO-R2")
        s = self._step(name="Receiving", part_type=pt)
        StepExecution.objects.create(
            tenant=self.tenant_a, part=None, step=s, status="IN_PROGRESS",
            entered_at=timezone.now(),
        )
        # A real part+step pair for the same WO/step to prove the row shows up.
        self._part_at_step(wo=wo, part_type=pt, step=s, erp="P-real")

        row = self._get().data["results"][0]
        self.assertEqual(row["qty_ready"], 1)  # not 2 — the null-part exec is excluded

    def test_tenant_isolation(self):
        # Build a row on tenant_b; auth'd as tenant_a → row does not appear.
        pt, _, wo = self._make_wo(erp="WO-B", tenant=self.tenant_b)
        s = self._step(name="A", part_type=pt, tenant=self.tenant_b)
        self._part_at_step(
            wo=wo, part_type=pt, step=s, erp="P-b", tenant=self.tenant_b,
        )
        results = self._get().data["results"]
        self.assertNotIn("WO-B", [r["work_order_erp_id"] for r in results])

    def test_requires_authentication(self):
        # No authenticate_as → anonymous request.
        resp = self.client.get("/api/WorkQueue/")
        self.assertIn(resp.status_code, (401, 403))

    # --- work-center filters ------------------------------------------------

    def _wc(self, code, kind):
        return WorkCenter.objects.create(
            tenant=self.tenant_a, code=code, name=code, kind=kind,
        )

    def test_kind_filter_scopes_surface(self):
        """?kind=PRODUCTION returns only rows whose step's WC is production;
        the INSPECTION WC's row is filtered out even though its step is TASK."""
        prod_wc = self._wc("PROD-T", WorkCenterKind.PRODUCTION)
        insp_wc = self._wc("INSP-T", WorkCenterKind.INSPECTION)

        pt, _, wo = self._make_wo(erp="WO-K")
        s_prod = self._step(name="Assembly", part_type=pt)
        s_prod.work_center = prod_wc
        s_prod.save()
        s_insp = self._step(name="Final Check", part_type=pt)
        s_insp.work_center = insp_wc
        s_insp.save()
        self._part_at_step(wo=wo, part_type=pt, step=s_prod, erp="P-a")
        self._part_at_step(wo=wo, part_type=pt, step=s_insp, erp="P-b")

        prod_rows = self._get({"kind": "PRODUCTION"}).data["results"]
        self.assertEqual(len(prod_rows), 1)
        self.assertEqual(prod_rows[0]["step_name"], "Assembly")
        self.assertEqual(prod_rows[0]["work_center_kind"], "PRODUCTION")

        insp_rows = self._get({"kind": "INSPECTION"}).data["results"]
        self.assertEqual(len(insp_rows), 1)
        self.assertEqual(insp_rows[0]["step_name"], "Final Check")

    def test_work_center_id_filter(self):
        wc_a = self._wc("A", WorkCenterKind.PRODUCTION)
        wc_b = self._wc("B", WorkCenterKind.PRODUCTION)

        pt, _, wo = self._make_wo(erp="WO-WCI")
        s_a = self._step(name="At A", part_type=pt); s_a.work_center = wc_a; s_a.save()
        s_b = self._step(name="At B", part_type=pt); s_b.work_center = wc_b; s_b.save()
        self._part_at_step(wo=wo, part_type=pt, step=s_a, erp="P-A")
        self._part_at_step(wo=wo, part_type=pt, step=s_b, erp="P-B")

        only_a = self._get({"work_center": str(wc_a.id)}).data["results"]
        self.assertEqual(len(only_a), 1)
        self.assertEqual(only_a[0]["step_name"], "At A")

        # __in filter — comma-separated ids
        both = self._get({"work_center__in": f"{wc_a.id},{wc_b.id}"}).data["results"]
        self.assertEqual(len(both), 2)

    def test_unmapped_step_dropped_by_kind_filter(self):
        """Steps with no work_center don't leak into a kind-filtered surface,
        but do show up in the unfiltered feed."""
        pt, _, wo = self._make_wo(erp="WO-UM")
        s = self._step(name="Unmapped", part_type=pt)  # no work_center
        self._part_at_step(wo=wo, part_type=pt, step=s, erp="P-um")

        with_filter = self._get({"kind": "PRODUCTION"}).data["results"]
        self.assertEqual(len(with_filter), 0)

        no_filter = self._get().data["results"]
        self.assertEqual(len(no_filter), 1)
        self.assertIsNone(no_filter[0]["work_center"])
        self.assertIsNone(no_filter[0]["work_center_kind"])

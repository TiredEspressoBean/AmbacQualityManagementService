"""Step.part_advancement_mode: PER_PART vs COHORT (all-or-none) advancement.

On non-batch steps, `try_advance_lot` historically used all-or-none cohort
cohesion — one blocked part held the whole cohort. That's correct for
shared-context steps (a heat treat load moves together) but wrong for
per-part QA-decision steps (Nozzle Inspection, Flow Testing, Final Test)
where each part is inspected individually and should advance on its own
outcome.

The new `part_advancement_mode` field on Steps lets a step opt into
per-part advancement without breaking the classic cohort semantics for
steps that legitimately need them.
"""
from django.contrib.auth import get_user_model

from Tracker.models import (
    PartTypes, Parts, PartsStatus, Processes, ProcessStep,
    StepExecution, Steps, Tenant, WorkOrder, WorkOrderStatus,
)
from Tracker.services.mes.advancement import try_advance_lot
from Tracker.tests.base import TenantContextMixin, VectorTestCase


class PartAdvancementModeTests(TenantContextMixin, VectorTestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(
            name="Adv Mode", slug="adv-mode", tier="PRO",
        )
        self.set_tenant_context(self.tenant)
        User = get_user_model()
        self.user = User.objects.create_user(
            username="adv-op", email="adv@op.test", password="x", tenant=self.tenant,
        )
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Widget")
        self.process = Processes.objects.create(
            tenant=self.tenant, name="P-ADV", part_type=self.pt,
        )
        self.dest = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Dest", step_type="TASK",
        )
        # step1 will be swapped between COHORT and PER_PART per test.
        # block_on_quarantine=True gives us a straightforward way to have a
        # QUARANTINED part become a hard-blocker in the cohort.
        self.wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-ADV-1",
            workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=2, process=self.process,
        )

    def _make_step(self, mode):
        s = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name=f"Step-{mode}",
            step_type="TASK", block_on_quarantine=True,
            part_advancement_mode=mode,
        )
        ProcessStep.objects.create(process=self.process, step=s, order=1)
        ProcessStep.objects.create(process=self.process, step=self.dest, order=2)
        return s

    def _make_part(self, step, erp, quarantined=False):
        p = Parts.objects.create(
            tenant=self.tenant, ERP_id=erp, part_type=self.pt,
            work_order=self.wo, step=step,
            part_status=PartsStatus.QUARANTINED if quarantined else PartsStatus.IN_PROGRESS,
        )
        StepExecution.objects.create(
            tenant=self.tenant, part=p, step=step, visit_number=1,
            status="IN_PROGRESS",
            training_authorization={'authorized': True, 'missing': [], 'verified': []},
        )
        return p

    def _advance(self, step):
        return try_advance_lot(
            work_order_id=str(self.wo.id), step_id=str(step.id),
            tenant_id=str(self.tenant.id), operator=self.user,
        )

    # ----- COHORT (default) -----

    def test_cohort_mode_one_blocked_holds_all(self):
        """Classic lot cohesion: one quarantined part → all wait."""
        step = self._make_step('COHORT')
        p_ok = self._make_part(step, 'P-OK', quarantined=False)
        p_qtn = self._make_part(step, 'P-QTN', quarantined=True)

        result = self._advance(step)
        self.assertEqual(result.status, 'blocked')
        self.assertEqual(result.parts_advanced, [])  # neither advanced
        # p_ok wasn't personally blocked, but the cohort's all-or-none rule
        # holds it because p_qtn is quarantined.
        self.assertIn(str(p_qtn.id), result.blockers_by_part)

    def test_cohort_mode_all_clear_advances_all(self):
        """Happy path for COHORT: no blockers → whole cohort advances together."""
        step = self._make_step('COHORT')
        p1 = self._make_part(step, 'P-1')
        p2 = self._make_part(step, 'P-2')

        result = self._advance(step)
        self.assertEqual(result.status, 'advanced')
        self.assertEqual(set(result.parts_advanced), {str(p1.id), str(p2.id)})

    # ----- PER_PART -----

    def test_per_part_mode_one_blocked_others_advance(self):
        """PER_PART: a quarantined part is held, but the passing part
        advances on its own. This is the whole reason for the mode —
        individually-inspected QA steps shouldn't wait for a failed part."""
        step = self._make_step('PER_PART')
        p_ok = self._make_part(step, 'PP-OK')
        p_qtn = self._make_part(step, 'PP-QTN', quarantined=True)

        result = self._advance(step)
        self.assertEqual(result.status, 'advanced')  # something moved
        self.assertEqual(result.parts_advanced, [str(p_ok.id)])
        # p_qtn stayed put, with its own blocker recorded.
        self.assertIn(str(p_qtn.id), result.blockers_by_part)
        self.assertNotIn(str(p_ok.id), result.blockers_by_part)

        # Verify the parts' actual state
        p_ok.refresh_from_db()
        p_qtn.refresh_from_db()
        self.assertEqual(p_ok.step, self.dest)  # advanced
        self.assertEqual(p_qtn.step, step)      # held

    def test_per_part_mode_all_blocked_reports_blocked(self):
        """PER_PART with every part blocked → status blocked, no advances."""
        step = self._make_step('PER_PART')
        p1 = self._make_part(step, 'PPB-1', quarantined=True)
        p2 = self._make_part(step, 'PPB-2', quarantined=True)

        result = self._advance(step)
        self.assertEqual(result.status, 'blocked')
        self.assertEqual(result.parts_advanced, [])
        self.assertIn(str(p1.id), result.blockers_by_part)
        self.assertIn(str(p2.id), result.blockers_by_part)

    def test_per_part_mode_all_clear_advances_all(self):
        """PER_PART with no blockers → all advance (same net result as COHORT
        for the happy path)."""
        step = self._make_step('PER_PART')
        p1 = self._make_part(step, 'PPC-1')
        p2 = self._make_part(step, 'PPC-2')

        result = self._advance(step)
        self.assertEqual(result.status, 'advanced')
        self.assertEqual(set(result.parts_advanced), {str(p1.id), str(p2.id)})

    def test_default_is_cohort(self):
        """New steps default to COHORT — backward-compat with existing
        installations that expect all-or-none semantics."""
        step = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Default-Step",
            step_type="TASK",
        )
        self.assertEqual(step.part_advancement_mode, 'COHORT')

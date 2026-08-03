"""advance_part_step must preserve HELD lifecycle statuses on step transition.

Prior behavior: `advance_part_step` unconditionally set `part_status =
IN_PROGRESS` on every step transition (also COMPLETED at a terminal step and
READY_FOR_NEXT_STEP for batch-completion holds). That silently "healed"
QUARANTINED and REWORK_NEEDED/REWORK_IN_PROGRESS parts as they walked
through the process — a QUARANTINED part at a step with
block_on_quarantine=False would advance and become IN_PROGRESS, defeating
the block_on_quarantine gate at every subsequent step.

Held statuses (QUARANTINED, REWORK_NEEDED, REWORK_IN_PROGRESS) mark
lifecycle state set by the disposition cascade or the rework routing;
only those mechanisms should clear them. A step transition alone must not.
"""
from django.contrib.auth import get_user_model

from Tracker.models import (
    PartTypes, Parts, PartsStatus, Processes, ProcessStep,
    StepExecution, Steps, Tenant, WorkOrder, WorkOrderStatus,
)
from Tracker.services.mes.parts import advance_part_step
from Tracker.tests.base import TenantContextMixin, VectorTestCase


class AdvancePartStepPreservesHeldStatusTests(TenantContextMixin, VectorTestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(
            name="Hold Preserve", slug="hold-preserve", tier="PRO",
        )
        self.set_tenant_context(self.tenant)
        User = get_user_model()
        self.user = User.objects.create_user(
            username="hp-op", email="hp@op.test", password="x", tenant=self.tenant,
        )
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Widget")
        self.process = Processes.objects.create(
            tenant=self.tenant, name="P-HP", part_type=self.pt,
        )
        self.step_a = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="A", step_type="TASK",
            # block_on_quarantine=False (default) — this is exactly the shape
            # that exposed the bug: gate lets a quarantined part leave, but
            # the transition then clobbered the quarantine.
        )
        self.step_b = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="B", step_type="TASK",
        )
        self.terminal = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Done", step_type="TASK",
            is_terminal=True, terminal_status='completed',
        )
        self.batch_step = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Batch", step_type="TASK",
            requires_batch_completion=True,
        )
        ProcessStep.objects.create(process=self.process, step=self.step_a, order=1)
        ProcessStep.objects.create(process=self.process, step=self.step_b, order=2)
        ProcessStep.objects.create(process=self.process, step=self.batch_step, order=3)
        ProcessStep.objects.create(process=self.process, step=self.terminal, order=4)
        self.wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-HP-1",
            workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=1, process=self.process,
        )

    def _make_part(self, erp, step, status):
        p = Parts.objects.create(
            tenant=self.tenant, ERP_id=erp, part_type=self.pt,
            work_order=self.wo, step=step, part_status=status,
        )
        StepExecution.objects.create(
            tenant=self.tenant, part=p, step=step, visit_number=1,
            status="IN_PROGRESS",
            training_authorization={'authorized': True, 'missing': [], 'verified': []},
        )
        return p

    def test_step_transition_preserves_quarantined_status(self):
        """The core bug: QUARANTINED part advances step_a → step_b (source
        allows it because block_on_quarantine=False), but must NOT be
        silently marked IN_PROGRESS by the transition. Its quarantine hold
        follows it."""
        p = self._make_part('P-HP-Q', self.step_a, PartsStatus.QUARANTINED)
        advance_part_step(p, operator=self.user, skip_gate_check=True)
        p.refresh_from_db()
        self.assertEqual(p.step, self.step_b, 'part physically routed to next step')
        self.assertEqual(p.part_status, PartsStatus.QUARANTINED,
                         'quarantine hold must survive the step transition')

    def test_step_transition_preserves_rework_needed(self):
        p = self._make_part('P-HP-RN', self.step_a, PartsStatus.REWORK_NEEDED)
        advance_part_step(p, operator=self.user, skip_gate_check=True)
        p.refresh_from_db()
        self.assertEqual(p.step, self.step_b)
        self.assertEqual(p.part_status, PartsStatus.REWORK_NEEDED)

    def test_step_transition_preserves_rework_in_progress(self):
        p = self._make_part('P-HP-RIP', self.step_a, PartsStatus.REWORK_IN_PROGRESS)
        advance_part_step(p, operator=self.user, skip_gate_check=True)
        p.refresh_from_db()
        self.assertEqual(p.step, self.step_b)
        self.assertEqual(p.part_status, PartsStatus.REWORK_IN_PROGRESS)

    def test_step_transition_still_sets_in_progress_for_workable_statuses(self):
        """Regression guard: the guard must not over-apply. A PENDING or
        AWAITING_QA part should still get IN_PROGRESS on the transition,
        since that's the intended workable state on the destination step."""
        for status in (PartsStatus.PENDING, PartsStatus.AWAITING_QA,
                       PartsStatus.READY_FOR_NEXT_STEP):
            p = self._make_part(f'P-HP-{status}', self.step_a, status)
            advance_part_step(p, operator=self.user, skip_gate_check=True)
            p.refresh_from_db()
            self.assertEqual(p.part_status, PartsStatus.IN_PROGRESS,
                             f'{status} should transition to IN_PROGRESS')

    def test_terminal_step_preserves_quarantined(self):
        """A QUARANTINED part reaching a terminal step must not be silently
        marked COMPLETED. Only an explicit SCRAP disposition should
        terminalize a quarantined part."""
        p = self._make_part('P-HP-TQ', self.terminal, PartsStatus.QUARANTINED)
        advance_part_step(p, operator=self.user, skip_gate_check=True)
        p.refresh_from_db()
        self.assertEqual(p.part_status, PartsStatus.QUARANTINED,
                         'terminal step must not clear the quarantine hold')

    def test_terminal_step_still_completes_workable_parts(self):
        p = self._make_part('P-HP-TW', self.terminal, PartsStatus.IN_PROGRESS)
        advance_part_step(p, operator=self.user, skip_gate_check=True)
        p.refresh_from_db()
        self.assertEqual(p.part_status, PartsStatus.COMPLETED)

    def test_batch_completion_preserves_quarantined(self):
        """A QUARANTINED part in a batch step must not be marked
        READY_FOR_NEXT_STEP by the batch-completion staging path."""
        p = self._make_part('P-HP-BQ', self.batch_step, PartsStatus.QUARANTINED)
        advance_part_step(p, operator=self.user, skip_gate_check=True)
        p.refresh_from_db()
        self.assertEqual(p.part_status, PartsStatus.QUARANTINED,
                         'batch-completion staging must not clear the quarantine hold')

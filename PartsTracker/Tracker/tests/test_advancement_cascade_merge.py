"""try_advance_lot cascade result merging.

When the engine advances parts through a pass-through step and cascades into
the next step, the top-level `LotAdvanceResult` must reflect the FULL walk
— every part that advanced (cohort or split) and every blocker that any
cascade level encountered. Prior to this fix only `parts_advanced` was
merged, silently dropping split-part advances and every cascade-level
blocker. That left callers unable to explain why a part didn't move
further than it did.
"""
from django.contrib.auth import get_user_model

from Tracker.models import (
    PartTypes, Parts, PartsStatus, Processes, ProcessStep,
    StepExecution, Steps, Tenant, WorkOrder, WorkOrderStatus,
)
from Tracker.services.mes.advancement import try_advance_lot
from Tracker.tests.base import TenantContextMixin, VectorTestCase


class CascadeMergeTests(TenantContextMixin, VectorTestCase):
    """Two-step cascade shapes exercising the merge points."""

    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(
            name="Cascade Merge", slug="cascade-merge", tier="PRO",
        )
        self.set_tenant_context(self.tenant)
        User = get_user_model()
        self.user = User.objects.create_user(
            username="cm-op", email="cm@op.test", password="x", tenant=self.tenant,
        )
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Widget")
        self.process = Processes.objects.create(
            tenant=self.tenant, name="P-CM", part_type=self.pt,
        )
        # Chain: step_a → step_b → step_c
        # step_a is a pass-through (no gates), so the cascade fires after it.
        # step_b is a MANUAL decision point — every part that reaches it hits
        # the "manual decision required" early-return blocker, without
        # depending on part-status (which advance_part_step normalizes to
        # IN_PROGRESS on every transition, silently clobbering QUARANTINED).
        # That normalization is a separate real issue tracked elsewhere; this
        # test focuses only on the cascade-result-merging contract.
        self.step_a = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="A", step_type="TASK",
        )
        self.step_b = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="B", step_type="DECISION",
            is_decision_point=True, decision_type='MANUAL',
        )
        self.step_c = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="C", step_type="TASK",
        )
        ProcessStep.objects.create(process=self.process, step=self.step_a, order=1)
        ProcessStep.objects.create(process=self.process, step=self.step_b, order=2)
        ProcessStep.objects.create(process=self.process, step=self.step_c, order=3)
        self.wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-CM-1",
            workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=2, process=self.process,
        )

    def _make_part(self, erp, step, quarantined=False):
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

    def test_cascade_merges_blockers_from_downstream_step(self):
        """Two parts advance through step_a; step_b is a MANUAL decision
        point so both hit its "manual decision required" blocker on the
        cascade. The top-level result must carry:
          - both parts in `parts_advanced` (they advanced past step_a)
          - both parts' step_b blockers in `blockers_by_part`.
        Before the fix, the step_b blockers were dropped by the cascade —
        the caller only saw the advance, none of the reasons things
        stopped moving further."""
        p1 = self._make_part('P-CM-1', self.step_a)
        p2 = self._make_part('P-CM-2', self.step_a)

        result = self._advance(self.step_a)

        self.assertEqual(result.status, 'advanced', 'parts advanced past step_a')
        # Both parts advanced past step_a
        self.assertIn(str(p1.id), result.parts_advanced)
        self.assertIn(str(p2.id), result.parts_advanced)
        # Both parts now at step_b, blocked by the manual-decision gate.
        p1.refresh_from_db()
        p2.refresh_from_db()
        self.assertEqual(p1.step, self.step_b, 'p1 stopped at step_b')
        self.assertEqual(p2.step, self.step_b, 'p2 stopped at step_b')
        # The cascade-level blockers must surface — this is the merge contract.
        self.assertIn(str(p1.id), result.blockers_by_part,
                      "cascade-step blocker for p1 was dropped from the top-level result")
        self.assertIn(str(p2.id), result.blockers_by_part,
                      "cascade-step blocker for p2 was dropped from the top-level result")
        self.assertTrue(any('Manual decision' in b for b in result.blockers_by_part[str(p1.id)]))

    def test_cascade_merges_split_parts_blocked(self):
        """A split part advances through step_a via the split-path; the
        cascade tries step_b, which blocks it (via MANUAL decision here).
        Since step_b's early-return path puts every part in blockers_by_part
        (not split_parts_blocked — the early-return doesn't distinguish),
        we verify the merge picks it up regardless of which collection
        the downstream step uses. The important guarantee: nothing is
        dropped."""
        p_split = self._make_part('P-CM-SPL', self.step_a)
        p_split.split_from_cohort = True
        p_split.save(update_fields=['split_from_cohort'])

        result = self._advance(self.step_a)

        # Split part advances via the split path at step_a.
        self.assertEqual(result.status, 'advanced')
        self.assertIn(str(p_split.id), result.split_parts_advanced)
        # Blocker surfaces via the merge — could be in either collection
        # depending on which downstream code path handled it (MANUAL early-
        # return uses blockers_by_part for all parts including splits).
        p_split.refresh_from_db()
        self.assertEqual(p_split.step, self.step_b, 'split part stopped at step_b')
        merged = {**result.blockers_by_part, **result.split_parts_blocked}
        self.assertIn(str(p_split.id), merged,
                      "cascade-step blocker for split part was dropped from the top-level result")

    def test_status_stays_advanced_when_cascade_only_adds_blockers(self):
        """If step_a advances parts and step_b blocks them, top-level status
        must remain 'advanced' (top-level advance is real progress). Only
        when nothing advanced anywhere should status be 'blocked'."""
        self._make_part('P-STAT-1', self.step_a)
        self._make_part('P-STAT-2', self.step_a)

        result = self._advance(self.step_a)
        self.assertEqual(result.status, 'advanced',
                         "cascade blockers must not flip status from 'advanced' to 'blocked'")
        # But blockers ARE recorded — that's the merge contract.
        self.assertTrue(result.blockers_by_part,
                        "cascade blockers must merge into the top-level result")

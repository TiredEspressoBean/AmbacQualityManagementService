"""
Terminal-step PENDING sampling blocker + `reconcile_pending_decisions`.

Services under test:
- `Tracker.services.dwi.advancement_gate.substep_completion_blockers`
  (the terminal-step PENDING branch added in the latest engine work).
- `Tracker.services.dwi.sampling_decisions.reconcile_pending_decisions`.
"""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase

from Tracker.models import (
    Parts,
    PartTypes,
    Processes,
    ProcessStatus,
    ProcessStep,
    SamplingDecision,
    SamplingOutcome,
    SamplingRule,
    SamplingRuleSet,
    StepExecution,
    Steps,
    Substep,
    SubstepScope,
    Tenant,
    WorkOrder,
    WorkOrderStatus,
)
from Tracker.models.mes_standard import SamplingRuleType
from Tracker.services.dwi.advancement_gate import substep_completion_blockers
from Tracker.services.dwi.sampling_decisions import reconcile_pending_decisions
from Tracker.utils.tenant_context import (
    reset_current_tenant,
    set_current_tenant_id,
)

User = get_user_model()


class DwiSamplingPendingBase(TestCase):
    """Shared fixture: tenant, user, part_type, process, work order, two
    steps (non-terminal and terminal), one SAMPLED substep on each, and a
    pair of parts at each step with active StepExecutions.

    Sampling rules are created lazily by individual tests so each can pick
    the rule_type that matches its assertion.
    """

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(
            name="DWI Pending Shop", slug="dwi-pending-shop",
        )
        cls._class_cv_token = set_current_tenant_id(cls.tenant.id)
        cls.user = User.objects.create_user(
            username="dpend_user",
            email="dpend@test.com",
            password="testpass",
            tenant=cls.tenant,
        )
        cls.part_type = PartTypes.objects.create(
            name="Widget", ID_prefix="WDG", tenant=cls.tenant,
        )
        cls.process = Processes.objects.create(
            name="Pending Process",
            part_type=cls.part_type,
            tenant=cls.tenant,
            status=ProcessStatus.APPROVED,
        )
        cls.step_normal = Steps.objects.create(
            name="Normal", part_type=cls.part_type, tenant=cls.tenant,
            is_terminal=False,
        )
        cls.step_terminal = Steps.objects.create(
            name="Terminal", part_type=cls.part_type, tenant=cls.tenant,
            is_terminal=True,
        )
        ProcessStep.objects.create(
            process=cls.process, step=cls.step_normal, order=0,
        )
        ProcessStep.objects.create(
            process=cls.process, step=cls.step_terminal, order=1,
        )

        cls.work_order = WorkOrder.objects.create(
            tenant=cls.tenant,
            ERP_id="WO-DPEND-001",
            workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=2,
            process=cls.process,
        )

        # Two parts: one at the non-terminal step, one at the terminal step.
        cls.part_normal = Parts.objects.create(
            tenant=cls.tenant,
            ERP_id="DPEND-P1",
            part_type=cls.part_type,
            work_order=cls.work_order,
            step=cls.step_normal,
        )
        cls.part_terminal = Parts.objects.create(
            tenant=cls.tenant,
            ERP_id="DPEND-P2",
            part_type=cls.part_type,
            work_order=cls.work_order,
            step=cls.step_terminal,
        )
        cls.exec_normal = StepExecution.objects.create(
            tenant=cls.tenant,
            part=cls.part_normal,
            step=cls.step_normal,
            visit_number=1,
            status='IN_PROGRESS',
        )
        cls.exec_terminal = StepExecution.objects.create(
            tenant=cls.tenant,
            part=cls.part_terminal,
            step=cls.step_terminal,
            visit_number=1,
            status='IN_PROGRESS',
        )

    @classmethod
    def tearDownClass(cls):
        token = getattr(cls, '_class_cv_token', None)
        if token is not None:
            try:
                reset_current_tenant(token)
            except (LookupError, ValueError):
                pass
        super().tearDownClass()

    # --- helpers ---------------------------------------------------------

    def _make_ruleset_and_rule(self, *, step, rule_type, value):
        ruleset = SamplingRuleSet.objects.create(
            tenant=self.tenant,
            part_type=self.part_type,
            process=self.process,
            step=step,
            name=f"RS-{rule_type}-{value}",
            active=True,
        )
        rule = SamplingRule.objects.create(
            tenant=self.tenant,
            ruleset=ruleset,
            rule_type=rule_type,
            value=value,
            order=0,
        )
        return ruleset, rule

    def _make_sampled_substep(self, *, step, sampling_rule=None, order=0):
        return Substep.objects.create(
            tenant=self.tenant,
            step=step,
            order=order,
            title=f"S-{step.id}-{order}",
            scope=SubstepScope.SAMPLED,
            sampling_rule=sampling_rule,
        )


# ============================================================================
# substep_completion_blockers — terminal-step PENDING branch
# ============================================================================


class TerminalPendingBlockerTests(DwiSamplingPendingBase):
    """`substep_completion_blockers` terminal-step PENDING branch."""

    TERMINAL_TEXT = "pending sampling"  # case-insensitive substring

    def _has_terminal_pending_blocker(self, blockers):
        return any(self.TERMINAL_TEXT in b.lower() for b in blockers)

    def test_non_terminal_step_pending_decision_no_terminal_blocker(self):
        # PENDING decision on the *non-terminal* step. The gate must not
        # emit the terminal-PENDING blocker for this step.
        _, rule = self._make_ruleset_and_rule(
            step=self.step_normal,
            rule_type=SamplingRuleType.LAST_N_PARTS, value=1,
        )
        substep = self._make_sampled_substep(
            step=self.step_normal, sampling_rule=rule,
        )
        SamplingDecision.objects.create(
            tenant=self.tenant,
            step_execution=self.exec_normal,
            substep=substep,
            outcome=SamplingOutcome.PENDING,
        )
        blockers = substep_completion_blockers(
            self.step_normal, self.exec_normal, self.work_order,
        )
        self.assertFalse(
            self._has_terminal_pending_blocker(blockers),
            f"Did not expect terminal-PENDING blocker on non-terminal step; got {blockers!r}",
        )

    def test_terminal_step_live_pending_decision_blocks(self):
        _, rule = self._make_ruleset_and_rule(
            step=self.step_terminal,
            rule_type=SamplingRuleType.LAST_N_PARTS, value=1,
        )
        substep = self._make_sampled_substep(
            step=self.step_terminal, sampling_rule=rule,
        )
        SamplingDecision.objects.create(
            tenant=self.tenant,
            step_execution=self.exec_terminal,
            substep=substep,
            outcome=SamplingOutcome.PENDING,
        )
        blockers = substep_completion_blockers(
            self.step_terminal, self.exec_terminal, self.work_order,
        )
        self.assertTrue(
            self._has_terminal_pending_blocker(blockers),
            f"Expected terminal-PENDING blocker; got {blockers!r}",
        )

    def test_terminal_step_superseded_pending_no_blocker(self):
        _, rule = self._make_ruleset_and_rule(
            step=self.step_terminal,
            rule_type=SamplingRuleType.LAST_N_PARTS, value=1,
        )
        substep = self._make_sampled_substep(
            step=self.step_terminal, sampling_rule=rule,
        )
        old = SamplingDecision.objects.create(
            tenant=self.tenant,
            step_execution=self.exec_terminal,
            substep=substep,
            outcome=SamplingOutcome.PENDING,
        )
        # Two-phase supersession to satisfy the
        # dwi_samplingdecision_live_uniq partial unique index — see the
        # matching pattern in reconcile_pending_decisions.
        old.superseded_by_id = old.id
        old.save(update_fields=['superseded_by'])
        new = SamplingDecision.objects.create(
            tenant=self.tenant,
            step_execution=self.exec_terminal,
            substep=substep,
            outcome=SamplingOutcome.DESELECTED,
        )
        old.superseded_by = new
        old.save(update_fields=['superseded_by'])

        blockers = substep_completion_blockers(
            self.step_terminal, self.exec_terminal, self.work_order,
        )
        self.assertFalse(
            self._has_terminal_pending_blocker(blockers),
            f"Did not expect terminal-PENDING blocker after supersession; got {blockers!r}",
        )


# ============================================================================
# reconcile_pending_decisions
# ============================================================================


class ReconcilePendingDecisionsTests(DwiSamplingPendingBase):
    """`reconcile_pending_decisions` rewrites live PENDING rows."""

    def test_noop_when_no_pending(self):
        summary = reconcile_pending_decisions(self.work_order)
        self.assertEqual(summary['reconciled'], 0)
        self.assertEqual(summary['now_selected'], 0)
        self.assertEqual(summary['now_deselected'], 0)
        self.assertEqual(summary['still_pending'], 0)

    def test_pending_resolves_to_deselected(self):
        # FIRST_N_PARTS value=1 — only part #1 in cohort is SELECTED.
        # part_terminal (created after part_normal, larger UUIDv7 id) is
        # cohort position 2 → DESELECTED.
        _, rule = self._make_ruleset_and_rule(
            step=self.step_terminal,
            rule_type=SamplingRuleType.FIRST_N_PARTS, value=1,
        )
        substep = self._make_sampled_substep(
            step=self.step_terminal, sampling_rule=rule,
        )
        pending = SamplingDecision.objects.create(
            tenant=self.tenant,
            step_execution=self.exec_terminal,  # part_terminal = position 2
            substep=substep,
            outcome=SamplingOutcome.PENDING,
        )

        summary = reconcile_pending_decisions(self.work_order)
        self.assertEqual(summary['reconciled'], 1)
        self.assertEqual(summary['now_deselected'], 1)
        self.assertEqual(summary['now_selected'], 0)

        pending.refresh_from_db()
        self.assertIsNotNone(pending.superseded_by_id)
        new_decision = SamplingDecision.objects.get(id=pending.superseded_by_id)
        self.assertEqual(new_decision.outcome, SamplingOutcome.DESELECTED)

    def test_pending_resolves_to_selected(self):
        # FIRST_N_PARTS value=5 — every part in the 2-part cohort is in.
        _, rule = self._make_ruleset_and_rule(
            step=self.step_terminal,
            rule_type=SamplingRuleType.FIRST_N_PARTS, value=5,
        )
        substep = self._make_sampled_substep(
            step=self.step_terminal, sampling_rule=rule,
        )
        pending = SamplingDecision.objects.create(
            tenant=self.tenant,
            step_execution=self.exec_terminal,
            substep=substep,
            outcome=SamplingOutcome.PENDING,
        )

        summary = reconcile_pending_decisions(self.work_order)
        self.assertEqual(summary['reconciled'], 1)
        self.assertEqual(summary['now_selected'], 1)
        self.assertEqual(summary['now_deselected'], 0)

        pending.refresh_from_db()
        self.assertIsNotNone(pending.superseded_by_id)
        new_decision = SamplingDecision.objects.get(id=pending.superseded_by_id)
        self.assertEqual(new_decision.outcome, SamplingOutcome.SELECTED)

    def test_scope_to_one_step(self):
        # PENDING decisions on both steps; reconcile with step=step_normal
        # should leave the terminal-step PENDING untouched.
        _, rule_norm = self._make_ruleset_and_rule(
            step=self.step_normal,
            rule_type=SamplingRuleType.FIRST_N_PARTS, value=5,
        )
        sub_norm = self._make_sampled_substep(
            step=self.step_normal, sampling_rule=rule_norm,
        )
        pending_norm = SamplingDecision.objects.create(
            tenant=self.tenant,
            step_execution=self.exec_normal,
            substep=sub_norm,
            outcome=SamplingOutcome.PENDING,
        )

        _, rule_term = self._make_ruleset_and_rule(
            step=self.step_terminal,
            rule_type=SamplingRuleType.FIRST_N_PARTS, value=5,
        )
        sub_term = self._make_sampled_substep(
            step=self.step_terminal, sampling_rule=rule_term,
        )
        pending_term = SamplingDecision.objects.create(
            tenant=self.tenant,
            step_execution=self.exec_terminal,
            substep=sub_term,
            outcome=SamplingOutcome.PENDING,
        )

        summary = reconcile_pending_decisions(
            self.work_order, step=self.step_normal,
        )
        self.assertEqual(summary['reconciled'], 1)

        pending_norm.refresh_from_db()
        pending_term.refresh_from_db()
        # Normal-step PENDING was reconciled.
        self.assertIsNotNone(pending_norm.superseded_by_id)
        # Terminal-step PENDING was left alone.
        self.assertIsNone(pending_term.superseded_by_id)
        self.assertEqual(pending_term.outcome, SamplingOutcome.PENDING)

"""
Tests for the lot-cohesion advancement engine.

Service under test: `Tracker.services.mes.advancement.try_advance_lot`.

Covers:
- Single-part advance through a gate-clear step.
- Cohort all-or-none advancement (lot cohesion invariant).
- Cohort blocked by one missing completion (none advance).
- Split parts evaluated independently of cohort.
- Bounded synchronous cascade through pass-through steps (cap = 10).
- Terminal step halting the cascade.
- Idempotent re-call (no-op when nothing to do).

Maps to sandbox cases 1, 2, 3, 5, 15, 16, 18, 20 in
`scratch_advancement_gate.py`.
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
    StepEdge,
    EdgeType,
    StepExecution,
    Steps,
    Substep,
    SubstepCompletion,
    SubstepScope,
    Tenant,
    WorkOrder,
    WorkOrderStatus,
)
from Tracker.services.mes.advancement import (
    _MAX_CASCADE_DEPTH,
    try_advance_lot,
)
from Tracker.utils.tenant_context import (
    reset_current_tenant,
    set_current_tenant_id,
)

User = get_user_model()


# ============================================================================
# Helpers
# ============================================================================


def _build_lot(
    *,
    tenant,
    user,
    part_type,
    num_steps: int = 2,
    num_parts: int = 1,
    substeps_per_step: int = 1,
    substeps_override: dict[int, int] | None = None,
    terminal_last: bool = False,
    process_name: str | None = None,
    wo_erp_id: str | None = None,
):
    """Build a complete process with N steps wired by DEFAULT edges, plus a
    WorkOrder with `num_parts` parts at step 0. Each step gets
    `substeps_per_step` non-optional non-critical SAMPLED substeps. Returns
    a dict with everything tests need to assert against.

    The last step is marked terminal only when `terminal_last=True`.
    """
    process = Processes.objects.create(
        name=process_name or f"Proc-{wo_erp_id or 'X'}",
        part_type=part_type,
        tenant=tenant,
        status=ProcessStatus.APPROVED,
    )
    steps = []
    for i in range(num_steps):
        is_last_terminal = terminal_last and i == num_steps - 1
        step = Steps.objects.create(
            name=f"Step-{i}",
            part_type=part_type,
            tenant=tenant,
            is_terminal=is_last_terminal,
        )
        ProcessStep.objects.create(process=process, step=step, order=i)
        steps.append(step)

    # Wire DEFAULT edges between consecutive steps.
    for i in range(num_steps - 1):
        StepEdge.objects.create(
            process=process,
            from_step=steps[i],
            to_step=steps[i + 1],
            edge_type=EdgeType.DEFAULT,
        )

    # Add substeps to each step. Track per-step substep lists for callers.
    substeps_by_step: dict[int, list[Substep]] = {}
    for i, step in enumerate(steps):
        substeps_by_step[i] = []
        count = (
            substeps_override.get(i, substeps_per_step)
            if substeps_override is not None
            else substeps_per_step
        )
        for j in range(count):
            s = Substep.objects.create(
                tenant=tenant,
                step=step,
                order=j,
                title=f"S{i}.{j}",
                scope=SubstepScope.SAMPLED,
            )
            substeps_by_step[i].append(s)

    wo = WorkOrder.objects.create(
        tenant=tenant,
        ERP_id=wo_erp_id or "WO-ADV-001",
        workorder_status=WorkOrderStatus.IN_PROGRESS,
        quantity=num_parts,
        process=process,
    )

    parts = []
    execs = []
    for k in range(num_parts):
        p = Parts.objects.create(
            tenant=tenant,
            ERP_id=f"PT-{wo_erp_id or 'WO'}-{k}",
            part_type=part_type,
            work_order=wo,
            step=steps[0],
        )
        se = StepExecution.objects.create(
            tenant=tenant,
            part=p,
            step=steps[0],
            visit_number=1,
            status='IN_PROGRESS',
        )
        parts.append(p)
        execs.append(se)

    return {
        'process': process,
        'steps': steps,
        'substeps_by_step': substeps_by_step,
        'wo': wo,
        'parts': parts,
        'execs': execs,
    }


def _complete_substeps_for_part(
    *,
    tenant,
    user,
    part,
    substeps,
):
    """Create non-voided SubstepCompletion rows for the given part's current
    StepExecution covering the provided substeps."""
    se = StepExecution.get_current_execution(part)
    assert se is not None, "Part has no active StepExecution"
    for s in substeps:
        SubstepCompletion.objects.create(
            tenant=tenant,
            step_execution=se,
            substep=s,
            completed_by=user,
        )


# ============================================================================
# Base
# ============================================================================


class AdvancementEngineBase(TestCase):
    """Shared per-class tenant + user + part_type."""

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name="Adv Shop", slug="adv-shop")
        cls._class_cv_token = set_current_tenant_id(cls.tenant.id)
        cls.user = User.objects.create_user(
            username="adv_user",
            email="adv@test.com",
            password="testpass",
            tenant=cls.tenant,
        )
        cls.part_type = PartTypes.objects.create(
            name="Widget",
            ID_prefix="WDG",
            tenant=cls.tenant,
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


# ============================================================================
# Group 1 — try_advance_lot core + cascade
# ============================================================================


class TryAdvanceLotTests(AdvancementEngineBase):
    """Direct unit tests for `try_advance_lot`."""

    # --- Case 1: sandbox #1 ---------------------------------------------
    def test_single_part_gate_clear_advances(self):
        lot = _build_lot(
            tenant=self.tenant, user=self.user, part_type=self.part_type,
            num_steps=2, num_parts=1, substeps_per_step=1,
            wo_erp_id="WO-SINGLE",
        )
        part = lot['parts'][0]
        step_a, step_b = lot['steps']
        _complete_substeps_for_part(
            tenant=self.tenant, user=self.user, part=part,
            substeps=lot['substeps_by_step'][0],
        )
        result = try_advance_lot(
            work_order_id=str(lot['wo'].id),
            step_id=str(step_a.id),
            tenant_id=str(self.tenant.id),
            operator=self.user,
        )
        self.assertEqual(result.status, 'advanced')
        self.assertIn(str(part.id), result.parts_advanced)
        part.refresh_from_db()
        self.assertEqual(part.step_id, step_b.id)

    # --- Case 2: sandbox #1 cohort ---------------------------------------
    def test_cohort_all_gate_clear_advances_together(self):
        lot = _build_lot(
            tenant=self.tenant, user=self.user, part_type=self.part_type,
            num_steps=2, num_parts=3, substeps_per_step=1,
            wo_erp_id="WO-COHORT",
        )
        step_a, step_b = lot['steps']
        subs = lot['substeps_by_step'][0]
        for p in lot['parts']:
            _complete_substeps_for_part(
                tenant=self.tenant, user=self.user, part=p, substeps=subs,
            )
        result = try_advance_lot(
            work_order_id=str(lot['wo'].id),
            step_id=str(step_a.id),
            tenant_id=str(self.tenant.id),
            operator=self.user,
        )
        self.assertEqual(result.status, 'advanced')
        self.assertEqual(len(result.parts_advanced), 3)
        for p in lot['parts']:
            p.refresh_from_db()
            self.assertEqual(p.step_id, step_b.id)

    # --- Case 3: sandbox #2 cohort with hold-out -------------------------
    def test_cohort_one_blocker_blocks_all(self):
        lot = _build_lot(
            tenant=self.tenant, user=self.user, part_type=self.part_type,
            num_steps=2, num_parts=3, substeps_per_step=1,
            wo_erp_id="WO-BLOCK",
        )
        step_a, step_b = lot['steps']
        subs = lot['substeps_by_step'][0]
        # Only complete substeps for parts 0 and 1; part 2 stays blocked.
        for p in lot['parts'][:2]:
            _complete_substeps_for_part(
                tenant=self.tenant, user=self.user, part=p, substeps=subs,
            )
        result = try_advance_lot(
            work_order_id=str(lot['wo'].id),
            step_id=str(step_a.id),
            tenant_id=str(self.tenant.id),
            operator=self.user,
        )
        self.assertEqual(result.status, 'blocked')
        blocked_part_id = str(lot['parts'][2].id)
        self.assertIn(blocked_part_id, result.blockers_by_part)
        # Lot-cohesion: complete parts must still be at step_a.
        for p in lot['parts']:
            p.refresh_from_db()
            self.assertEqual(p.step_id, step_a.id)

    # --- Case 4: split independence (sandbox #4) -------------------------
    def test_split_part_advances_solo_without_cohort(self):
        lot = _build_lot(
            tenant=self.tenant, user=self.user, part_type=self.part_type,
            num_steps=2, num_parts=3, substeps_per_step=1,
            wo_erp_id="WO-SPLIT",
        )
        step_a, step_b = lot['steps']
        subs = lot['substeps_by_step'][0]
        # Split part 0 (no completions on others — cohort would be blocked).
        from Tracker.services.mes.splits import split_part_from_lot
        from Tracker.models import PartSplitReason
        # First, satisfy the splittee's gate.
        split_target = lot['parts'][0]
        _complete_substeps_for_part(
            tenant=self.tenant, user=self.user, part=split_target,
            substeps=subs,
        )
        split_part_from_lot(
            part=split_target,
            reason=PartSplitReason.QUARANTINE.value,
            user=self.user,
        )
        # `split_part_from_lot` already calls `try_advance_lot` synchronously;
        # the split part should have advanced. Cohort (parts 1, 2) should
        # remain at step A (no completions).
        split_target.refresh_from_db()
        self.assertEqual(split_target.step_id, step_b.id)
        for p in lot['parts'][1:]:
            p.refresh_from_db()
            self.assertEqual(p.step_id, step_a.id)

    # --- Case 5: pass-through cascade (sandbox #5) -----------------------
    def test_pass_through_step_cascades(self):
        # A -> B(no substeps, non-terminal) -> C
        lot = _build_lot(
            tenant=self.tenant, user=self.user, part_type=self.part_type,
            num_steps=3, num_parts=1, substeps_per_step=1,
            # Step B is a pass-through: no substeps.
            substeps_override={1: 0},
            wo_erp_id="WO-CASCADE",
        )
        step_a, step_b, step_c = lot['steps']
        part = lot['parts'][0]
        _complete_substeps_for_part(
            tenant=self.tenant, user=self.user, part=part,
            substeps=lot['substeps_by_step'][0],
        )
        result = try_advance_lot(
            work_order_id=str(lot['wo'].id),
            step_id=str(step_a.id),
            tenant_id=str(self.tenant.id),
            operator=self.user,
        )
        self.assertEqual(result.status, 'advanced')
        part.refresh_from_db()
        # Should have landed past pass-through B into C.
        self.assertEqual(part.step_id, step_c.id)

    # --- Case 6: cascade depth cap ---------------------------------------
    def test_cascade_depth_cap(self):
        """Build a long chain of pass-through steps; the engine must stop at
        cap=10 even if more pass-throughs remain."""
        # 1 active step (Step-0 with one substep) plus a long chain of
        # pass-throughs. Make sure the chain is longer than the cap so we
        # observe truncation.
        chain_length = _MAX_CASCADE_DEPTH + 3  # pass-throughs after Step-0
        total_steps = chain_length + 1  # +1 for Step-0
        # Step 0 has 1 substep; all downstream steps are pass-throughs.
        override = {i: 0 for i in range(1, total_steps)}
        lot = _build_lot(
            tenant=self.tenant, user=self.user, part_type=self.part_type,
            num_steps=total_steps, num_parts=1, substeps_per_step=1,
            substeps_override=override,
            wo_erp_id="WO-CAP",
        )
        steps = lot['steps']
        part = lot['parts'][0]
        _complete_substeps_for_part(
            tenant=self.tenant, user=self.user, part=part,
            substeps=lot['substeps_by_step'][0],
        )
        result = try_advance_lot(
            work_order_id=str(lot['wo'].id),
            step_id=str(steps[0].id),
            tenant_id=str(self.tenant.id),
            operator=self.user,
        )
        self.assertEqual(result.status, 'advanced')
        part.refresh_from_db()
        # Depth budget: the initial call (_depth=0) advances once; the
        # recursive cascade runs while _depth < 10, so at most 10 more
        # advances. Total advances <= 11. Final landing step index <=
        # 11 (steps[11]) or earlier if chain is shorter.
        # Index of the final step:
        final_index = next(
            i for i, s in enumerate(steps) if s.id == part.step_id
        )
        # Initial advance from step 0 -> step 1 (=depth 0). Then cascade
        # while depth < 10 → 10 additional hops max. So final_index <= 11.
        self.assertLessEqual(final_index, 11)
        # And we should not have reached the last step — chain is longer
        # than the cap.
        self.assertLess(final_index, total_steps - 1)

    # --- Case 7: terminal step halts the cascade (sandbox #18) -----------
    def test_terminal_next_step_halts_cascade(self):
        lot = _build_lot(
            tenant=self.tenant, user=self.user, part_type=self.part_type,
            num_steps=2, num_parts=1, substeps_per_step=1,
            substeps_override={1: 0},
            terminal_last=True,
            wo_erp_id="WO-TERMINAL",
        )
        step_a, step_b = lot['steps']
        part = lot['parts'][0]
        _complete_substeps_for_part(
            tenant=self.tenant, user=self.user, part=part,
            substeps=lot['substeps_by_step'][0],
        )
        result = try_advance_lot(
            work_order_id=str(lot['wo'].id),
            step_id=str(step_a.id),
            tenant_id=str(self.tenant.id),
            operator=self.user,
        )
        self.assertEqual(result.status, 'advanced')
        part.refresh_from_db()
        # The part should have landed at terminal step_b and stopped (not
        # cascaded). terminal-step parts get their step_id stamped at B
        # (advance_part_step marks completed when next_step is None).
        self.assertEqual(part.step_id, step_b.id)

    # --- Case 8: idempotency ---------------------------------------------
    def test_idempotent_second_call_is_noop(self):
        lot = _build_lot(
            tenant=self.tenant, user=self.user, part_type=self.part_type,
            num_steps=2, num_parts=2, substeps_per_step=1,
            wo_erp_id="WO-IDEM",
        )
        step_a, step_b = lot['steps']
        subs = lot['substeps_by_step'][0]
        for p in lot['parts']:
            _complete_substeps_for_part(
                tenant=self.tenant, user=self.user, part=p, substeps=subs,
            )
        first = try_advance_lot(
            work_order_id=str(lot['wo'].id),
            step_id=str(step_a.id),
            tenant_id=str(self.tenant.id),
            operator=self.user,
        )
        self.assertEqual(first.status, 'advanced')
        # Second call against the now-empty (WO, step_a) — no parts at A.
        second = try_advance_lot(
            work_order_id=str(lot['wo'].id),
            step_id=str(step_a.id),
            tenant_id=str(self.tenant.id),
            operator=self.user,
        )
        self.assertEqual(second.status, 'noop')
        self.assertEqual(second.parts_advanced, [])
        # Parts still all at B.
        for p in lot['parts']:
            p.refresh_from_db()
            self.assertEqual(p.step_id, step_b.id)

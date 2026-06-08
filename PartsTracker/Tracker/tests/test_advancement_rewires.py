"""
Tests for the synchronous re-wires that drive `try_advance_lot` from
state-changing services (splits, override approval, batch seal).

Each test asserts that "the part moved in the same call" — deep edge
cases for the engine itself live in `test_advancement_engine.py`.
"""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase

from Tracker.models import (
    BatchExecution,
    BlockType,
    OverrideStatus,
    PartSplitReason,
    Parts,
    PartTypes,
    Processes,
    ProcessStatus,
    ProcessStep,
    StepEdge,
    EdgeType,
    StepExecution,
    StepOverride,
    Steps,
    Substep,
    SubstepCompletion,
    SubstepScope,
    Tenant,
    WorkOrder,
    WorkOrderStatus,
)
from Tracker.services.mes.splits import split_part_from_lot
from Tracker.services.mes.step_override import approve_step_override
from Tracker.services.dwi.batch_lifecycle import seal_batch
from Tracker.tests.test_advancement_engine import (
    _build_lot,
    _complete_substeps_for_part,
)
from Tracker.utils.tenant_context import (
    reset_current_tenant,
    set_current_tenant_id,
)

User = get_user_model()


class AdvancementRewiresBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name="Rewire Shop", slug="rewire-shop")
        cls._class_cv_token = set_current_tenant_id(cls.tenant.id)
        cls.user = User.objects.create_user(
            username="rw_user", email="rw@test.com",
            password="testpass", tenant=cls.tenant,
        )
        cls.part_type = PartTypes.objects.create(
            name="Widget", ID_prefix="WDG", tenant=cls.tenant,
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


class SplitRewireTests(AdvancementRewiresBase):
    """`split_part_from_lot` synchronously re-fires advancement."""

    def test_split_unblocks_remaining_cohort(self):
        # 3 parts, only parts 1 and 2 have completions. Part 0 holds the lot.
        # Splitting part 0 should immediately unblock the cohort and advance
        # parts 1 and 2 in the same call.
        lot = _build_lot(
            tenant=self.tenant, user=self.user, part_type=self.part_type,
            num_steps=2, num_parts=3, substeps_per_step=1,
            wo_erp_id="WO-SPLIT-UNBLOCK",
        )
        step_a, step_b = lot['steps']
        subs = lot['substeps_by_step'][0]
        # Complete substeps for parts 1 and 2 only.
        for p in lot['parts'][1:]:
            _complete_substeps_for_part(
                tenant=self.tenant, user=self.user, part=p, substeps=subs,
            )
        # Split part 0 (the blocker).
        split_part_from_lot(
            part=lot['parts'][0],
            reason=PartSplitReason.QUARANTINE.value,
            user=self.user,
        )
        # Remaining cohort should have advanced synchronously inside
        # `split_part_from_lot`.
        for p in lot['parts'][1:]:
            p.refresh_from_db()
            self.assertEqual(p.step_id, step_b.id)
        # The split part itself stayed at step A (no completions; gate
        # blocks it for solo evaluation too).
        lot['parts'][0].refresh_from_db()
        self.assertEqual(lot['parts'][0].step_id, step_a.id)


class StepOverrideRewireTests(AdvancementRewiresBase):
    """`approve_step_override` synchronously re-fires advancement."""

    def test_override_approval_triggers_advance(self):
        # Single-part lot, gate is blocked by an out-of-spec measurement.
        # We approximate the "gate-blocked" condition by approving an
        # override that clears the underlying blocker, then assert the
        # part moves forward in the same call.
        #
        # Setup: step A has `requires_qa_signoff=True` (no signoff →
        # advancement blocked). A pending override of type QA_SIGNOFF is
        # approved → gate clears → part advances.
        lot = _build_lot(
            tenant=self.tenant, user=self.user, part_type=self.part_type,
            num_steps=2, num_parts=1, substeps_per_step=0,
            wo_erp_id="WO-OVR",
        )
        step_a, step_b = lot['steps']
        # Add the QA-signoff blocker condition.
        step_a.requires_qa_signoff = True
        step_a.save(update_fields=['requires_qa_signoff'])
        part = lot['parts'][0]
        se = StepExecution.get_current_execution(part)

        override = StepOverride.objects.create(
            tenant=self.tenant,
            step_execution=se,
            block_type=BlockType.QA_SIGNOFF,
            requested_by=self.user,
            reason="bypass for test",
            status=OverrideStatus.PENDING,
        )
        approve_step_override(override, self.user)

        part.refresh_from_db()
        self.assertEqual(part.step_id, step_b.id)


class BatchSealRewireTests(AdvancementRewiresBase):
    """`seal_batch` synchronously re-fires advancement."""

    def test_batch_seal_advances_cohort(self):
        # Step A has one BATCH-scope substep. We don't bother with
        # SAMPLED substeps on step A (substeps_per_step=0 baseline; add
        # a single BATCH substep below).
        lot = _build_lot(
            tenant=self.tenant, user=self.user, part_type=self.part_type,
            num_steps=2, num_parts=2, substeps_per_step=0,
            wo_erp_id="WO-BATCH",
        )
        step_a, step_b = lot['steps']
        # Create a BATCH-scope substep on step A.
        batch_sub = Substep.objects.create(
            tenant=self.tenant,
            step=step_a,
            order=0,
            title="Wash cycle",
            scope=SubstepScope.BATCH,
        )
        # Create a BatchExecution with the two parts.
        batch = BatchExecution.objects.create(
            tenant=self.tenant,
            work_order=lot['wo'],
            step=step_a,
            started_by=self.user,
        )
        batch.parts.set(lot['parts'])
        # Record the batch substep completion (against the batch).
        SubstepCompletion.objects.create(
            tenant=self.tenant,
            batch_execution=batch,
            substep=batch_sub,
            completed_by=self.user,
        )

        seal_batch(batch=batch, user=self.user)

        # Parts should have advanced synchronously to step B.
        for p in lot['parts']:
            p.refresh_from_db()
            self.assertEqual(p.step_id, step_b.id)

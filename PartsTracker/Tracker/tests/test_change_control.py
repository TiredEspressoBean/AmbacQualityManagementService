"""
Tests for Change Control services — PCR / PCO / PCN lifecycle.

Coverage:
  - Sequencing: format, per-tenant / per-type / per-year isolation, concurrency.
  - Impact analysis: in-flight filter, snapshot shape.
  - PCR: submit / approve / reject / cancel state machine, validation gates.
  - PCO: create-from-PCR (SIMPLIFIED + REGULATED), author, approve,
         separation-of-duties, implement (all disposition variants),
         cancel.
  - PCN: auto-create + auto-release in SIMPLIFIED, DRAFT in REGULATED,
         release with separation-of-duties, close with evidence.
  - Constraints: one open PCR per target_process (serial constraint).
"""
from __future__ import annotations

from uuid import uuid4

from Tracker.models import (
    ApprovalTemplate,
    Approval_Type,
    ArtifactSequence,
    Companies,
    Orders,
    OrdersStatus,
    PartTypes,
    ProcessChangeMigrationDisposition,
    ProcessChangeNotice,
    ProcessChangeOrder,
    ProcessChangeRequest,
    Processes,
    ProcessStatus,
    ProcessStep,
    Steps,
    WorkOrder,
    WorkOrderStatus,
)
from Tracker.services.change_control import (
    ChangeControlMode,
    approve_pcr,
    approve_pco,
    author_pco,
    cancel_pco,
    cancel_pcr,
    close_pcn,
    create_pco_from_approved_pcr,
    create_pcn_from_implemented_pco,
    implement_pco,
    list_affected_workorders,
    mark_pco_approved,
    next_artifact_number,
    reject_pcr,
    release_pcn,
    snapshot_affected_workorders,
    submit_pcr,
)
from Tracker.tests.base import TenantTestCase


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_approved_process(tenant, user, part_type, *, name='Injector Assembly'):
    """Build a minimal APPROVED Process with one ProcessStep + one Step."""
    process = Processes.objects.create(
        name=name,
        part_type=part_type,
        status=ProcessStatus.APPROVED,
        approved_by=user,
    )
    step = Steps.objects.create(
        name='Final Inspection',
        part_type=part_type,
        pass_threshold=1.0,
    )
    ProcessStep.objects.create(
        process=process, step=step, order=1, is_entry_point=True,
    )
    return process, step


def _make_workorder(tenant, process, *, status=WorkOrderStatus.IN_PROGRESS, erp='WO-001'):
    """Create a minimal WorkOrder pinned to a specific process version."""
    company = Companies.objects.create(name=f'Cust-{erp}')
    order = Orders.objects.create(
        name=f'Order-{erp}',
        company=company,
        order_status=OrdersStatus.IN_PROGRESS,
    )
    return WorkOrder.objects.create(
        ERP_id=erp,
        related_order=order,
        process=process,
        workorder_status=status,
        quantity=1,
    )


def _make_pcr_template(tenant):
    # Tenant signal seeds PCR_APPROVAL via defaults_service. Reuse the
    # existing row instead of creating a duplicate (unique constraint on
    # tenant + template_name).
    tpl, _ = ApprovalTemplate.objects.get_or_create(
        tenant=tenant,
        approval_type=Approval_Type.PCR_APPROVAL,
        defaults={'template_name': 'PCR Approval'},
    )
    return tpl


def _make_pco_template(tenant):
    tpl, _ = ApprovalTemplate.objects.get_or_create(
        tenant=tenant,
        approval_type=Approval_Type.PCO_APPROVAL,
        defaults={'template_name': 'PCO Approval'},
    )
    return tpl


def _make_pcn_template(tenant):
    return ApprovalTemplate.objects.create(
        tenant=tenant,
        template_name='PCN Release',
        approval_type=Approval_Type.PCN_RELEASE,
    )


def _make_pcr(tenant, user, target_process, *, title='Tighten Step 4 tolerance'):
    return ProcessChangeRequest.objects.create(
        tenant=tenant,
        artifact_number=next_artifact_number(
            tenant_id=tenant.id, artifact_type='PCR',
        ),
        target_process=target_process,
        title=title,
        proposed_change='Reduce Step 4 tolerance from ±0.005 to ±0.003.',
        justification='Customer-requested per quality issue ticket.',
        risk_analysis='Tighter tolerance reduces yield ~2%; customer accepts.',
        created_by=user,
    )


# ---------------------------------------------------------------------------
# Sequencing
# ---------------------------------------------------------------------------

class ArtifactSequenceTestCase(TenantTestCase):
    """Sequencing service: format, isolation, monotonicity."""

    def test_format_is_type_year_seq_4(self):
        n = next_artifact_number(
            tenant_id=self.tenant_a.id, artifact_type='PCR', year=2026,
        )
        self.assertEqual(n, 'PCR-2026-0001')

    def test_increments_within_same_tenant_type_year(self):
        a = next_artifact_number(
            tenant_id=self.tenant_a.id, artifact_type='PCR', year=2026,
        )
        b = next_artifact_number(
            tenant_id=self.tenant_a.id, artifact_type='PCR', year=2026,
        )
        self.assertEqual(a, 'PCR-2026-0001')
        self.assertEqual(b, 'PCR-2026-0002')

    def test_separate_sequences_per_artifact_type(self):
        pcr = next_artifact_number(
            tenant_id=self.tenant_a.id, artifact_type='PCR', year=2026,
        )
        pco = next_artifact_number(
            tenant_id=self.tenant_a.id, artifact_type='PCO', year=2026,
        )
        pcn = next_artifact_number(
            tenant_id=self.tenant_a.id, artifact_type='PCN', year=2026,
        )
        self.assertEqual(pcr, 'PCR-2026-0001')
        self.assertEqual(pco, 'PCO-2026-0001')
        self.assertEqual(pcn, 'PCN-2026-0001')

    def test_separate_sequences_per_tenant(self):
        a = next_artifact_number(
            tenant_id=self.tenant_a.id, artifact_type='PCR', year=2026,
        )
        b = next_artifact_number(
            tenant_id=self.tenant_b.id, artifact_type='PCR', year=2026,
        )
        # Same number across tenants — correct, not a bug.
        self.assertEqual(a, 'PCR-2026-0001')
        self.assertEqual(b, 'PCR-2026-0001')

    def test_separate_sequences_per_year(self):
        a_2026 = next_artifact_number(
            tenant_id=self.tenant_a.id, artifact_type='PCR', year=2026,
        )
        a_2027 = next_artifact_number(
            tenant_id=self.tenant_a.id, artifact_type='PCR', year=2027,
        )
        self.assertEqual(a_2026, 'PCR-2026-0001')
        self.assertEqual(a_2027, 'PCR-2027-0001')

    def test_artifact_type_required(self):
        with self.assertRaises(ValueError):
            next_artifact_number(
                tenant_id=self.tenant_a.id, artifact_type='', year=2026,
            )


# ---------------------------------------------------------------------------
# Impact analysis
# ---------------------------------------------------------------------------

class ImpactAnalysisTestCase(TenantTestCase):
    """snapshot_affected_workorders / list_affected_workorders behavior."""

    def setUp(self):
        super().setUp()
        self.part_type = PartTypes.objects.create(name='PT', ID_prefix='PT-')
        self.process, _ = _make_approved_process(
            self.tenant_a, self.user_a, self.part_type,
        )

    def test_includes_in_flight_statuses(self):
        wo_pending = _make_workorder(
            self.tenant_a, self.process, status=WorkOrderStatus.PENDING, erp='P',
        )
        wo_running = _make_workorder(
            self.tenant_a, self.process, status=WorkOrderStatus.IN_PROGRESS, erp='R',
        )
        wo_hold = _make_workorder(
            self.tenant_a, self.process, status=WorkOrderStatus.ON_HOLD, erp='H',
        )

        ids = {w.id for w in list_affected_workorders(self.process)}
        self.assertEqual(ids, {wo_pending.id, wo_running.id, wo_hold.id})

    def test_excludes_completed_and_cancelled(self):
        _make_workorder(
            self.tenant_a, self.process, status=WorkOrderStatus.IN_PROGRESS, erp='R',
        )
        _make_workorder(
            self.tenant_a, self.process, status=WorkOrderStatus.COMPLETED, erp='C',
        )
        _make_workorder(
            self.tenant_a, self.process, status=WorkOrderStatus.CANCELLED, erp='X',
        )

        snapshot = snapshot_affected_workorders(self.process)
        self.assertEqual(len(snapshot), 1)
        self.assertEqual(snapshot[0]['erp_id'], 'R')

    def test_snapshot_is_json_safe(self):
        _make_workorder(self.tenant_a, self.process, erp='ERP-001')
        snapshot = snapshot_affected_workorders(self.process)
        entry = snapshot[0]
        self.assertIsInstance(entry['wo_id'], str)
        self.assertEqual(entry['erp_id'], 'ERP-001')
        self.assertIn(entry['status'], WorkOrderStatus.values)


# ---------------------------------------------------------------------------
# PCR lifecycle
# ---------------------------------------------------------------------------

class PcrLifecycleTestCase(TenantTestCase):
    """ProcessChangeRequest state machine."""

    def setUp(self):
        super().setUp()
        self.part_type = PartTypes.objects.create(name='PT', ID_prefix='PT-')
        self.process, _ = _make_approved_process(
            self.tenant_a, self.user_a, self.part_type,
        )
        _make_pcr_template(self.tenant_a)
        self.pcr = _make_pcr(self.tenant_a, self.user_a, self.process)

    def test_submit_happy_path(self):
        approval_request = submit_pcr(self.pcr, user=self.user_a)
        self.pcr.refresh_from_db()

        self.assertEqual(self.pcr.status, ProcessChangeRequest.Status.SUBMITTED)
        self.assertIsNotNone(self.pcr.submitted_at)
        self.assertEqual(self.pcr.submitted_by, self.user_a)
        self.assertEqual(self.pcr.baseline_version_id, self.process.id)
        self.assertEqual(approval_request.tenant, self.tenant_a)

    def test_submit_snapshots_in_flight_workorders(self):
        wo = _make_workorder(self.tenant_a, self.process, erp='WO-1')
        submit_pcr(self.pcr, user=self.user_a)
        self.pcr.refresh_from_db()

        self.assertEqual(len(self.pcr.affected_workorders_snapshot), 1)
        self.assertEqual(
            self.pcr.affected_workorders_snapshot[0]['wo_id'],
            str(wo.id),
        )

    def test_submit_rejects_wrong_status(self):
        self.pcr.status = ProcessChangeRequest.Status.SUBMITTED
        self.pcr.save(update_fields=['status'])
        with self.assertRaises(ValueError):
            submit_pcr(self.pcr, user=self.user_a)

    def test_submit_rejects_missing_required_fields(self):
        self.pcr.justification = ''
        self.pcr.save(update_fields=['justification'])
        with self.assertRaises(ValueError) as ctx:
            submit_pcr(self.pcr, user=self.user_a)
        self.assertIn('justification', str(ctx.exception))

    def test_submit_rejects_missing_template(self):
        ApprovalTemplate.objects.filter(
            approval_type=Approval_Type.PCR_APPROVAL,
        ).delete()
        with self.assertRaises(ValueError) as ctx:
            submit_pcr(self.pcr, user=self.user_a)
        self.assertIn('PCR_APPROVAL', str(ctx.exception))

    def test_approve_creates_pco_simplified_auto_approved(self):
        submit_pcr(self.pcr, user=self.user_a)
        pco = approve_pcr(
            self.pcr, user=self.user_a, mode=ChangeControlMode.SIMPLIFIED,
        )
        self.pcr.refresh_from_db()

        self.assertEqual(self.pcr.status, ProcessChangeRequest.Status.APPROVED)
        self.assertEqual(pco.status, ProcessChangeOrder.Status.APPROVED)
        self.assertIsNotNone(pco.draft_process_version)
        self.assertEqual(pco.draft_process_version.previous_version, self.process)

    def test_approve_creates_pco_regulated_draft(self):
        _make_pco_template(self.tenant_a)
        submit_pcr(self.pcr, user=self.user_a)
        pco = approve_pcr(
            self.pcr, user=self.user_a, mode=ChangeControlMode.REGULATED,
        )
        self.assertEqual(pco.status, ProcessChangeOrder.Status.DRAFT)

    def test_approve_rejects_wrong_status(self):
        with self.assertRaises(ValueError):
            approve_pcr(self.pcr, user=self.user_a)

    def test_reject_terminates_with_reason(self):
        submit_pcr(self.pcr, user=self.user_a)
        reject_pcr(self.pcr, user=self.user_a, reason='Out of scope.')
        self.pcr.refresh_from_db()

        self.assertEqual(self.pcr.status, ProcessChangeRequest.Status.REJECTED)
        self.assertEqual(self.pcr.rejected_reason, 'Out of scope.')

    def test_reject_requires_reason(self):
        submit_pcr(self.pcr, user=self.user_a)
        with self.assertRaises(ValueError):
            reject_pcr(self.pcr, user=self.user_a, reason='')

    def test_cancel_pre_approval_only(self):
        cancel_pcr(self.pcr, user=self.user_a)
        self.pcr.refresh_from_db()
        self.assertEqual(self.pcr.status, ProcessChangeRequest.Status.CANCELLED)

    def test_cancel_after_approval_rejected(self):
        submit_pcr(self.pcr, user=self.user_a)
        approve_pcr(self.pcr, user=self.user_a)
        with self.assertRaises(ValueError):
            cancel_pcr(self.pcr, user=self.user_a)


# ---------------------------------------------------------------------------
# Serial constraint — one open PCR per target_process
# ---------------------------------------------------------------------------

class PcrParallelOpenTestCase(TenantTestCase):
    """Multiple open PCRs against the same target_process are permitted.

    Conflicts between concurrent drafts are resolved at approval time
    by the rebase service, not by a database constraint.
    """

    def setUp(self):
        super().setUp()
        self.part_type = PartTypes.objects.create(name='PT', ID_prefix='PT-')
        self.process, _ = _make_approved_process(
            self.tenant_a, self.user_a, self.part_type,
        )
        _make_pcr_template(self.tenant_a)

    def test_second_open_pcr_allowed(self):
        first = _make_pcr(self.tenant_a, self.user_a, self.process, title='First')
        second = _make_pcr(self.tenant_a, self.user_a, self.process, title='Second')
        self.assertNotEqual(first.id, second.id)
        self.assertEqual(first.target_process, second.target_process)

    def test_new_pcr_after_rejection_allowed(self):
        first = _make_pcr(self.tenant_a, self.user_a, self.process, title='First')
        submit_pcr(first, user=self.user_a)
        reject_pcr(first, user=self.user_a, reason='Out of scope.')

        # Rejected is terminal — new PCR against same process is fine.
        second = _make_pcr(
            self.tenant_a, self.user_a, self.process, title='Second',
        )
        self.assertEqual(second.target_process, self.process)


# ---------------------------------------------------------------------------
# Rebase + conflict detection at approval (multi-PCR)
# ---------------------------------------------------------------------------

class PcrRebaseTestCase(TenantTestCase):
    """Two PCRs against the same process: the second is rebased onto the
    first's approved version at approval time, with conflict detection
    on overlapping field changes.

    The rebase scenarios require real draft Process versions with their
    own Steps — built via `propose_process_change` so the fork chain is
    populated (target → draft, with `previous_version` linking back).
    """

    def setUp(self):
        super().setUp()
        self.part_type = PartTypes.objects.create(name='PT', ID_prefix='PT-')
        # Build a baseline APPROVED process with 2 steps so we have
        # somewhere to place disjoint edits.
        self.baseline = Processes.objects.create(
            name='Injector Reman',
            part_type=self.part_type,
            status=ProcessStatus.APPROVED,
            approved_by=self.user_a,
            is_current_version=True,
        )
        self.cleaning = Steps.objects.create(
            name='Cleaning', part_type=self.part_type,
            pass_threshold=1.0,
        )
        self.milling = Steps.objects.create(
            name='Milling', part_type=self.part_type,
            pass_threshold=1.0,
        )
        ProcessStep.objects.create(
            process=self.baseline, step=self.cleaning, order=1,
        )
        ProcessStep.objects.create(
            process=self.baseline, step=self.milling, order=2,
        )
        _make_pcr_template(self.tenant_a)
        _make_pco_template(self.tenant_a)

    def _propose(self, *, title):
        from Tracker.services.change_control.process_change import (
            propose_process_change,
        )
        pcr, draft = propose_process_change(
            self.baseline,
            user=self.user_a,
            title=title,
            proposed_change='Edit',
            justification='Quality issue',
            risk_analysis='Low',
        )
        return pcr, draft

    def _edit_step_on_draft(self, draft, step_identity, **field_overrides):
        """Mimic an engineer's PCR-DRAFT step edit — versions the Step
        on the draft via the canonical service so the junction flips."""
        from Tracker.services.mes.steps import create_new_step_version
        ps = ProcessStep.objects.filter(
            process=draft, step__identity_id=step_identity,
        ).first()
        create_new_step_version(
            ps.step, user=self.user_a,
            change_description='Test edit',
            process=draft,
            **field_overrides,
        )

    def _approve_and_implement(self, pcr):
        """Drive a PCR all the way through implementation — only after
        `implement_pco` runs does the PCR's draft become the new
        APPROVED Process. Until then, the baseline hasn't shifted."""
        submit_pcr(pcr, user=self.user_a)
        pco = approve_pcr(pcr, user=self.user_a, mode=ChangeControlMode.SIMPLIFIED)
        implement_pco(
            pco, user=self.user_b,  # SoD: implementer != approver
            migration_disposition=ProcessChangeMigrationDisposition.KEEP_ALL,
            mode=ChangeControlMode.SIMPLIFIED,
        )

    def test_disjoint_edits_both_approve_cleanly(self):
        # PCR-A edits Cleaning.description; PCR-B edits Milling.description.
        # Different steps → no overlap. PCR-A implements (new baseline),
        # then PCR-B rebases onto the new baseline and approves.
        cleaning_identity = self.cleaning.identity_id
        milling_identity = self.milling.identity_id

        pcr_a, draft_a = self._propose(title='PCR-A')
        self._edit_step_on_draft(
            draft_a, cleaning_identity, description='Updated cleaning notes',
        )
        pcr_b, draft_b = self._propose(title='PCR-B')
        self._edit_step_on_draft(
            draft_b, milling_identity, description='Updated milling notes',
        )

        self._approve_and_implement(pcr_a)
        # PCR-A's draft is now the new APPROVED baseline.

        submit_pcr(pcr_b, user=self.user_a)
        # Rebase should detect no overlap and lift PCR-B's intent onto
        # the new baseline silently.
        approve_pcr(pcr_b, user=self.user_a, mode=ChangeControlMode.SIMPLIFIED)

        pcr_b.refresh_from_db()
        self.assertEqual(pcr_b.status, ProcessChangeRequest.Status.APPROVED)

    def test_overlapping_edits_block_second_approval(self):
        # Both PCRs edit Cleaning.description. PCR-A implements first;
        # PCR-B's approval surfaces a RebaseConflict because the same
        # field was modified by both.
        from Tracker.services.change_control.process_change import (
            PcrRebaseConflict,
        )
        cleaning_identity = self.cleaning.identity_id

        pcr_a, draft_a = self._propose(title='PCR-A')
        self._edit_step_on_draft(
            draft_a, cleaning_identity, description='Cleaning A',
        )
        pcr_b, draft_b = self._propose(title='PCR-B')
        self._edit_step_on_draft(
            draft_b, cleaning_identity, description='Cleaning B',
        )

        self._approve_and_implement(pcr_a)

        submit_pcr(pcr_b, user=self.user_a)
        with self.assertRaises(PcrRebaseConflict) as ctx:
            approve_pcr(pcr_b, user=self.user_a, mode=ChangeControlMode.SIMPLIFIED)

        conflict = ctx.exception.conflict
        self.assertEqual(len(conflict.conflicts), 1)
        c = conflict.conflicts[0]
        self.assertEqual(c.step_identity_id, str(cleaning_identity))
        self.assertEqual(c.field, 'description')

    def test_single_pcr_approves_with_no_rebase(self):
        # Sanity: when there's nothing to rebase against, approval is
        # the normal flow. Refresh-from-db inside approve_pcr was the
        # subtle gotcha during implementation.
        pcr, _ = self._propose(title='Single')
        submit_pcr(pcr, user=self.user_a)
        approve_pcr(pcr, user=self.user_a, mode=ChangeControlMode.SIMPLIFIED)

        pcr.refresh_from_db()
        self.assertEqual(pcr.status, ProcessChangeRequest.Status.APPROVED)

    def test_approved_sibling_blocks_second_approval_pre_implement(self):
        # The Maria/Jen story: PCR-A and PCR-B both fork from the same
        # baseline and edit Cleaning.description differently. PCR-A
        # approves (no rebase needed — baseline hasn't shifted). Then
        # PCR-B comes up for approval BEFORE PCR-A's PCO has been
        # implemented. Without the approved-sibling check this used to
        # sail through, leaving the implementation order to silently
        # decide whose value won. With it, PCR-B's approval raises
        # `PcrRebaseConflict` against the sibling's intended diff so a
        # human reconciles before either ships.
        from Tracker.services.change_control.process_change import (
            PcrRebaseConflict,
        )
        cleaning_identity = self.cleaning.identity_id

        pcr_a, draft_a = self._propose(title='PCR-A')
        self._edit_step_on_draft(
            draft_a, cleaning_identity, description='Cleaning A intent',
        )
        pcr_b, draft_b = self._propose(title='PCR-B')
        self._edit_step_on_draft(
            draft_b, cleaning_identity, description='Cleaning B intent',
        )

        # Approve PCR-A only — do NOT implement. This is the gap the
        # earlier rebase code missed: baseline is still v1, no shift
        # has happened in the version chain.
        submit_pcr(pcr_a, user=self.user_a)
        approve_pcr(pcr_a, user=self.user_a, mode=ChangeControlMode.SIMPLIFIED)
        pcr_a.refresh_from_db()
        self.assertEqual(pcr_a.status, ProcessChangeRequest.Status.APPROVED)

        submit_pcr(pcr_b, user=self.user_a)
        with self.assertRaises(PcrRebaseConflict) as ctx:
            approve_pcr(pcr_b, user=self.user_a, mode=ChangeControlMode.SIMPLIFIED)

        conflict = ctx.exception.conflict
        self.assertEqual(len(conflict.conflicts), 1)
        c = conflict.conflicts[0]
        self.assertEqual(c.step_identity_id, str(cleaning_identity))
        self.assertEqual(c.field, 'description')
        # The sibling's intent value is what the dialog surfaces as
        # "current approved" — points the approver at the other PCR's
        # claim so they can reconcile.
        self.assertEqual(c.intent_value, 'Cleaning B intent')
        self.assertEqual(c.approved_value, 'Cleaning A intent')

    def test_approved_sibling_with_disjoint_edits_does_not_block(self):
        # PCR-A and PCR-B both forked from the same baseline but edit
        # *different* steps. The approved-sibling check should be a
        # no-op since intents don't overlap — both must approve cleanly
        # to preserve the multi-PCR-per-baseline design.
        pcr_a, draft_a = self._propose(title='PCR-A')
        self._edit_step_on_draft(
            draft_a, self.cleaning.identity_id, description='Cleaning A',
        )
        pcr_b, draft_b = self._propose(title='PCR-B')
        self._edit_step_on_draft(
            draft_b, self.milling.identity_id, description='Milling B',
        )

        submit_pcr(pcr_a, user=self.user_a)
        approve_pcr(pcr_a, user=self.user_a, mode=ChangeControlMode.SIMPLIFIED)

        submit_pcr(pcr_b, user=self.user_a)
        approve_pcr(pcr_b, user=self.user_a, mode=ChangeControlMode.SIMPLIFIED)

        pcr_b.refresh_from_db()
        self.assertEqual(pcr_b.status, ProcessChangeRequest.Status.APPROVED)


# ---------------------------------------------------------------------------
# PCO lifecycle
# ---------------------------------------------------------------------------

class PcoLifecycleTestCase(TenantTestCase):
    """ProcessChangeOrder state machine and Pattern C version creation."""

    def setUp(self):
        super().setUp()
        self.part_type = PartTypes.objects.create(name='PT', ID_prefix='PT-')
        self.process, _ = _make_approved_process(
            self.tenant_a, self.user_a, self.part_type,
        )
        _make_pcr_template(self.tenant_a)
        _make_pco_template(self.tenant_a)
        self.pcr = _make_pcr(self.tenant_a, self.user_a, self.process)
        submit_pcr(self.pcr, user=self.user_a)

    def test_create_pco_creates_draft_version(self):
        pco = approve_pcr(
            self.pcr, user=self.user_a, mode=ChangeControlMode.SIMPLIFIED,
        )
        self.assertIsNotNone(pco.draft_process_version)
        self.assertEqual(pco.draft_process_version.status, ProcessStatus.DRAFT)
        self.assertEqual(pco.draft_process_version.previous_version, self.process)

    def test_create_pco_duplicate_rejected(self):
        approve_pcr(self.pcr, user=self.user_a)
        with self.assertRaises(ValueError):
            create_pco_from_approved_pcr(self.pcr, user=self.user_a)

    def test_author_pco_updates_fields(self):
        pco = approve_pcr(
            self.pcr, user=self.user_a, mode=ChangeControlMode.REGULATED,
        )
        from datetime import date
        author_pco(
            pco, user=self.user_a,
            implementation_plan='Custom plan.',
            effective_date=date(2026, 6, 1),
        )
        pco.refresh_from_db()
        self.assertEqual(pco.implementation_plan, 'Custom plan.')
        self.assertEqual(pco.effective_date, date(2026, 6, 1))

    def test_author_pco_rejects_non_draft(self):
        pco = approve_pcr(
            self.pcr, user=self.user_a, mode=ChangeControlMode.SIMPLIFIED,
        )
        # SIMPLIFIED auto-approves so PCO is APPROVED, not DRAFT
        with self.assertRaises(ValueError):
            author_pco(pco, user=self.user_a, implementation_plan='x')

    def test_approve_pco_requires_implementation_plan(self):
        pco = approve_pcr(
            self.pcr, user=self.user_a, mode=ChangeControlMode.REGULATED,
        )
        pco.implementation_plan = ''
        pco.save(update_fields=['implementation_plan'])
        with self.assertRaises(ValueError):
            approve_pco(pco, user=self.user_b)

    def test_mark_pco_approved_separation_of_duties(self):
        pco = approve_pcr(
            self.pcr, user=self.user_a, mode=ChangeControlMode.REGULATED,
        )
        # user_a created the PCO; cannot also approve it.
        with self.assertRaises(ValueError) as ctx:
            mark_pco_approved(pco, user=self.user_a)
        self.assertIn('Separation of duties', str(ctx.exception))

    def test_mark_pco_approved_different_user_succeeds(self):
        pco = approve_pcr(
            self.pcr, user=self.user_a, mode=ChangeControlMode.REGULATED,
        )
        # Make user_b a member of tenant_a so they can sign in this tenant.
        self.user_b.tenant = self.tenant_a
        self.user_b.save(update_fields=['tenant'])

        mark_pco_approved(pco, user=self.user_b)
        pco.refresh_from_db()
        self.assertEqual(pco.status, ProcessChangeOrder.Status.APPROVED)
        self.assertEqual(pco.approved_by, self.user_b)

    def test_cancel_pco_pre_implementation_only(self):
        pco = approve_pcr(self.pcr, user=self.user_a)
        cancel_pco(pco, user=self.user_a)
        pco.refresh_from_db()
        self.assertEqual(pco.status, ProcessChangeOrder.Status.CANCELLED)


# ---------------------------------------------------------------------------
# implement_pco — the heavy hitter (Path A migrations + PCN creation)
# ---------------------------------------------------------------------------

class ImplementPcoTestCase(TenantTestCase):
    """PCO implementation: approve_process on DRAFT + WO migrations + PCN."""

    def setUp(self):
        super().setUp()
        self.part_type = PartTypes.objects.create(name='PT', ID_prefix='PT-')
        self.process, _ = _make_approved_process(
            self.tenant_a, self.user_a, self.part_type,
        )
        _make_pcr_template(self.tenant_a)
        _make_pco_template(self.tenant_a)
        _make_pcn_template(self.tenant_a)

        self.wo1 = _make_workorder(self.tenant_a, self.process, erp='WO-1')
        self.wo2 = _make_workorder(self.tenant_a, self.process, erp='WO-2')
        self.wo3 = _make_workorder(self.tenant_a, self.process, erp='WO-3')

        self.pcr = _make_pcr(self.tenant_a, self.user_a, self.process)
        submit_pcr(self.pcr, user=self.user_a)
        self.pco = approve_pcr(
            self.pcr, user=self.user_a, mode=ChangeControlMode.SIMPLIFIED,
        )
        self.draft_version = self.pco.draft_process_version

    def test_implement_migrate_all(self):
        pcn = implement_pco(
            self.pco, user=self.user_a,
            migration_disposition=ProcessChangeMigrationDisposition.MIGRATE_ALL,
            migration_reason='Critical safety update.',
            mode=ChangeControlMode.SIMPLIFIED,
        )
        self.pco.refresh_from_db()

        # PCO finalized
        self.assertEqual(self.pco.status, ProcessChangeOrder.Status.IMPLEMENTED)
        self.assertEqual(
            self.pco.migration_disposition,
            ProcessChangeMigrationDisposition.MIGRATE_ALL,
        )
        self.assertEqual(len(self.pco.migrated_workorder_ids), 3)

        # All WOs migrated
        for wo in (self.wo1, self.wo2, self.wo3):
            wo.refresh_from_db()
            self.assertEqual(wo.process_id, self.draft_version.id)

        # DRAFT version flipped to APPROVED
        self.draft_version.refresh_from_db()
        self.assertEqual(self.draft_version.status, ProcessStatus.APPROVED)

        # PCN auto-released in SIMPLIFIED mode
        self.assertEqual(pcn.status, ProcessChangeNotice.Status.RELEASED)

    def test_implement_keep_all(self):
        implement_pco(
            self.pco, user=self.user_a,
            migration_disposition=ProcessChangeMigrationDisposition.KEEP_ALL,
            mode=ChangeControlMode.SIMPLIFIED,
        )
        self.pco.refresh_from_db()

        self.assertEqual(len(self.pco.migrated_workorder_ids), 0)
        for wo in (self.wo1, self.wo2, self.wo3):
            wo.refresh_from_db()
            self.assertEqual(wo.process_id, self.process.id)

    def test_implement_migrate_selected(self):
        implement_pco(
            self.pco, user=self.user_a,
            migration_disposition=ProcessChangeMigrationDisposition.MIGRATE_SELECTED,
            selected_workorder_ids=[self.wo1.id, self.wo3.id],
            mode=ChangeControlMode.SIMPLIFIED,
        )
        self.pco.refresh_from_db()

        self.assertEqual(len(self.pco.migrated_workorder_ids), 2)

        self.wo1.refresh_from_db()
        self.wo2.refresh_from_db()
        self.wo3.refresh_from_db()
        self.assertEqual(self.wo1.process_id, self.draft_version.id)
        self.assertEqual(self.wo2.process_id, self.process.id)  # unchanged
        self.assertEqual(self.wo3.process_id, self.draft_version.id)

    def test_implement_migrate_selected_requires_ids(self):
        with self.assertRaises(ValueError):
            implement_pco(
                self.pco, user=self.user_a,
                migration_disposition=ProcessChangeMigrationDisposition.MIGRATE_SELECTED,
                selected_workorder_ids=None,
            )

    def test_implement_pending_disposition_rejected(self):
        with self.assertRaises(ValueError):
            implement_pco(
                self.pco, user=self.user_a,
                migration_disposition=ProcessChangeMigrationDisposition.PENDING,
            )

    def test_implement_invalid_disposition_rejected(self):
        with self.assertRaises(ValueError):
            implement_pco(
                self.pco, user=self.user_a,
                migration_disposition='NOT_A_REAL_VALUE',
            )

    def test_implement_creates_pcn(self):
        pcn = implement_pco(
            self.pco, user=self.user_a,
            migration_disposition=ProcessChangeMigrationDisposition.KEEP_ALL,
            mode=ChangeControlMode.SIMPLIFIED,
        )
        self.assertEqual(pcn.order, self.pco)
        self.assertTrue(pcn.artifact_number.startswith('PCN-'))


# ---------------------------------------------------------------------------
# PCN lifecycle
# ---------------------------------------------------------------------------

class PcnLifecycleTestCase(TenantTestCase):
    """ProcessChangeNotice release + closure."""

    def setUp(self):
        super().setUp()
        self.part_type = PartTypes.objects.create(name='PT', ID_prefix='PT-')
        self.process, _ = _make_approved_process(
            self.tenant_a, self.user_a, self.part_type,
        )
        _make_pcr_template(self.tenant_a)
        _make_pco_template(self.tenant_a)
        _make_pcn_template(self.tenant_a)

        self.pcr = _make_pcr(self.tenant_a, self.user_a, self.process)
        submit_pcr(self.pcr, user=self.user_a)

    def test_pcn_auto_released_in_simplified(self):
        pco = approve_pcr(
            self.pcr, user=self.user_a, mode=ChangeControlMode.SIMPLIFIED,
        )
        pcn = implement_pco(
            pco, user=self.user_a,
            migration_disposition=ProcessChangeMigrationDisposition.KEEP_ALL,
            mode=ChangeControlMode.SIMPLIFIED,
        )
        self.assertEqual(pcn.status, ProcessChangeNotice.Status.RELEASED)
        self.assertEqual(pcn.released_by, self.user_a)

    def test_pcn_draft_in_regulated(self):
        # Move user_b into tenant_a so they can act as the PCO approver.
        self.user_b.tenant = self.tenant_a
        self.user_b.save(update_fields=['tenant'])

        pco = approve_pcr(
            self.pcr, user=self.user_a, mode=ChangeControlMode.REGULATED,
        )
        mark_pco_approved(pco, user=self.user_b)
        pcn = implement_pco(
            pco, user=self.user_a,
            migration_disposition=ProcessChangeMigrationDisposition.KEEP_ALL,
            mode=ChangeControlMode.REGULATED,
        )
        self.assertEqual(pcn.status, ProcessChangeNotice.Status.DRAFT)

    def test_release_pcn_separation_of_duties(self):
        # Set up REGULATED end-to-end with PCO approver = user_b.
        self.user_b.tenant = self.tenant_a
        self.user_b.save(update_fields=['tenant'])

        pco = approve_pcr(
            self.pcr, user=self.user_a, mode=ChangeControlMode.REGULATED,
        )
        mark_pco_approved(pco, user=self.user_b)
        pcn = implement_pco(
            pco, user=self.user_a,
            migration_disposition=ProcessChangeMigrationDisposition.KEEP_ALL,
            mode=ChangeControlMode.REGULATED,
        )

        # user_b approved the PCO; cannot also release the PCN.
        with self.assertRaises(ValueError) as ctx:
            release_pcn(pcn, user=self.user_b)
        self.assertIn('Separation of duties', str(ctx.exception))

    def test_release_pcn_different_user_succeeds(self):
        self.user_b.tenant = self.tenant_a
        self.user_b.save(update_fields=['tenant'])

        pco = approve_pcr(
            self.pcr, user=self.user_a, mode=ChangeControlMode.REGULATED,
        )
        mark_pco_approved(pco, user=self.user_b)
        pcn = implement_pco(
            pco, user=self.user_a,
            migration_disposition=ProcessChangeMigrationDisposition.KEEP_ALL,
            mode=ChangeControlMode.REGULATED,
        )

        # user_a (who didn't approve the PCO) releases the PCN.
        release_pcn(pcn, user=self.user_a)
        pcn.refresh_from_db()
        self.assertEqual(pcn.status, ProcessChangeNotice.Status.RELEASED)

    def test_close_pcn_requires_evidence(self):
        pco = approve_pcr(
            self.pcr, user=self.user_a, mode=ChangeControlMode.SIMPLIFIED,
        )
        pcn = implement_pco(
            pco, user=self.user_a,
            migration_disposition=ProcessChangeMigrationDisposition.KEEP_ALL,
            mode=ChangeControlMode.SIMPLIFIED,
        )
        with self.assertRaises(ValueError):
            close_pcn(pcn, user=self.user_a, closure_evidence='')

    def test_close_pcn_finalizes(self):
        pco = approve_pcr(
            self.pcr, user=self.user_a, mode=ChangeControlMode.SIMPLIFIED,
        )
        pcn = implement_pco(
            pco, user=self.user_a,
            migration_disposition=ProcessChangeMigrationDisposition.KEEP_ALL,
            mode=ChangeControlMode.SIMPLIFIED,
        )
        close_pcn(
            pcn, user=self.user_a,
            closure_evidence='Effectiveness verified at 30-day review.',
        )
        pcn.refresh_from_db()
        self.assertEqual(pcn.status, ProcessChangeNotice.Status.CLOSED)
        self.assertIsNotNone(pcn.closed_at)
        self.assertEqual(pcn.closed_by, self.user_a)

    def test_close_pcn_rejects_non_released(self):
        pco = approve_pcr(
            self.pcr, user=self.user_a, mode=ChangeControlMode.REGULATED,
        )
        # Need user_b as approver
        self.user_b.tenant = self.tenant_a
        self.user_b.save(update_fields=['tenant'])
        mark_pco_approved(pco, user=self.user_b)
        pcn = implement_pco(
            pco, user=self.user_a,
            migration_disposition=ProcessChangeMigrationDisposition.KEEP_ALL,
            mode=ChangeControlMode.REGULATED,
        )
        # PCN is in DRAFT, not RELEASED — close should fail.
        with self.assertRaises(ValueError):
            close_pcn(pcn, user=self.user_a, closure_evidence='x')
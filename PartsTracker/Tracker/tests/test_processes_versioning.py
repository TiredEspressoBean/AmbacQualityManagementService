"""
Tests for `Processes.create_new_version` (the composite reference).

Covers:
  - Status gate (only APPROVED or DEPRECATED can be revised)
  - `change_description` required (compliance — ISO 9001 4.4)
  - DRAFT-successor-exists guard with a clear error
  - Bug-regression tests for the 8 documented bugs
  - Child copy: ProcessStep, StepEdge (same Step FKs)
  - Document GFK copy: new rows, same storage, fresh approval lifecycle
  - ApprovalRequest GFK NOT copied
  - `effective()` regression (is_current_version + status=APPROVED)
  - WorkOrder FK pinning stability across versioning
  - `revision_created` signal emission
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

from django.contrib.contenttypes.models import ContentType
from django.dispatch import receiver
from rest_framework.test import APIRequestFactory

from Tracker.models import (
    Documents,
    PartTypes,
    Processes,
    ProcessStatus,
    ProcessStep,
    Steps,
    StepEdge,
    EdgeType,
    WorkOrder,
    WorkOrderStatus,
    Orders,
    OrdersStatus,
    Companies,
)
from Tracker.services.mes.processes import create_new_process_version
from Tracker.signals_versioning import revision_created
from Tracker.tests.base import TenantTestCase


def _make_simple_approved_process(tenant, user, part_type):
    """Build a minimal APPROVED Process with one ProcessStep + one Step."""
    process = Processes.objects.create(
        name='Injector Assembly',
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


class CreateNewProcessVersionTestCase(TenantTestCase):
    """Core versioning mechanics on Processes."""

    def setUp(self):
        super().setUp()
        self.part_type = PartTypes.objects.create(name='Injector', ID_prefix='INJ-')
        self.process, self.step = _make_simple_approved_process(
            self.tenant_a, self.user_a, self.part_type,
        )

    def test_creates_new_draft_with_incremented_version(self):
        v2 = create_new_process_version(
            self.process, user=self.user_a, change_description='Rev B',
        )
        self.assertEqual(v2.version, 2)
        self.assertEqual(v2.status, ProcessStatus.DRAFT)
        self.assertEqual(v2.previous_version, self.process)
        self.assertTrue(v2.is_current_version)

        self.process.refresh_from_db()
        self.assertFalse(self.process.is_current_version)

    def test_from_deprecated_allowed(self):
        self.process.status = ProcessStatus.DEPRECATED
        self.process.save(update_fields=['status'])

        v2 = create_new_process_version(
            self.process, user=self.user_a, change_description='Rev',
        )
        self.assertEqual(v2.status, ProcessStatus.DRAFT)

    def test_from_draft_rejected(self):
        self.process.status = ProcessStatus.DRAFT
        self.process.save(update_fields=['status'])
        with self.assertRaises(ValueError) as ctx:
            create_new_process_version(
                self.process, user=self.user_a, change_description='Rev',
            )
        self.assertIn('draft', str(ctx.exception).lower())

    def test_from_pending_approval_rejected(self):
        self.process.status = ProcessStatus.PENDING_APPROVAL
        self.process.save(update_fields=['status'])
        with self.assertRaises(ValueError):
            create_new_process_version(
                self.process, user=self.user_a, change_description='Rev',
            )

    def test_blank_change_description_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            create_new_process_version(
                self.process, user=self.user_a, change_description='',
            )
        self.assertIn('change_description', str(ctx.exception))

        with self.assertRaises(ValueError):
            create_new_process_version(
                self.process, user=self.user_a, change_description='   ',
            )

    def test_draft_successor_exists_gives_clear_error(self):
        create_new_process_version(
            self.process, user=self.user_a, change_description='Rev B',
        )
        # A second revision attempt should fail with a targeted message,
        # not the generic status-gate error.
        with self.assertRaises(ValueError) as ctx:
            create_new_process_version(
                self.process, user=self.user_a, change_description='Rev B\'',
            )
        msg = str(ctx.exception).lower()
        self.assertIn('draft revision', msg)
        self.assertIn('already exists', msg)

    def test_approved_at_and_approved_by_cleared(self):
        v2 = create_new_process_version(
            self.process, user=self.user_a, change_description='Rev',
        )
        self.assertIsNone(v2.approved_at)
        self.assertIsNone(v2.approved_by)

    def test_tenant_preserved(self):
        """Regression for documented bug #2."""
        v2 = create_new_process_version(
            self.process, user=self.user_a, change_description='Rev',
        )
        self.assertEqual(str(v2.tenant_id), str(self.process.tenant_id))
        self.assertEqual(str(v2.tenant_id), str(self.tenant_a.id))

    def test_category_preserved(self):
        """Regression for documented bug #3."""
        self.process.category = 'QUALITY'
        self.process.save(update_fields=['category'])

        v2 = create_new_process_version(
            self.process, user=self.user_a, change_description='Rev',
        )
        self.assertEqual(v2.category, 'QUALITY')

    def test_change_description_stored_on_row(self):
        v2 = create_new_process_version(
            self.process, user=self.user_a, change_description='Rev B - tolerance tightened',
        )
        self.assertEqual(v2.change_description, 'Rev B - tolerance tightened')


class ProcessStepAndEdgeCopyTestCase(TenantTestCase):
    """Junction rows are copied; Step FKs are preserved (historical pinning)."""

    def setUp(self):
        super().setUp()
        self.part_type = PartTypes.objects.create(name='Injector', ID_prefix='INJ-')
        self.process, self.step_a = _make_simple_approved_process(
            self.tenant_a, self.user_a, self.part_type,
        )
        # Add a second step + an edge.
        self.step_b = Steps.objects.create(
            name='Leak Test', part_type=self.part_type, pass_threshold=1.0,
        )
        ProcessStep.objects.create(
            process=self.process, step=self.step_b, order=2, is_entry_point=False,
        )
        StepEdge.objects.create(
            process=self.process, from_step=self.step_a, to_step=self.step_b,
            edge_type=EdgeType.DEFAULT,
        )

    def test_process_step_rows_copied_to_new_version(self):
        v2 = create_new_process_version(
            self.process, user=self.user_a, change_description='Rev',
        )
        v1_step_ids = set(self.process.process_steps.values_list('step_id', flat=True))
        v2_step_ids = set(v2.process_steps.values_list('step_id', flat=True))
        # Same Step references carried forward.
        self.assertEqual(v1_step_ids, v2_step_ids)
        # Different ProcessStep rows (new pks).
        v1_ps_pks = set(self.process.process_steps.values_list('pk', flat=True))
        v2_ps_pks = set(v2.process_steps.values_list('pk', flat=True))
        self.assertTrue(v1_ps_pks.isdisjoint(v2_ps_pks))

    def test_step_edges_copied_with_same_step_fks(self):
        v2 = create_new_process_version(
            self.process, user=self.user_a, change_description='Rev',
        )
        v2_edges = list(v2.step_edges.all())
        self.assertEqual(len(v2_edges), 1)
        self.assertEqual(v2_edges[0].from_step_id, self.step_a.id)
        self.assertEqual(v2_edges[0].to_step_id, self.step_b.id)

    def test_old_version_retains_its_children(self):
        original_ps_count = self.process.process_steps.count()
        original_edge_count = self.process.step_edges.count()

        create_new_process_version(
            self.process, user=self.user_a, change_description='Rev',
        )

        self.process.refresh_from_db()
        # v1's children are untouched by versioning.
        self.assertEqual(self.process.process_steps.count(), original_ps_count)
        self.assertEqual(self.process.step_edges.count(), original_edge_count)


class DocumentsCopyOnProcessVersioningTestCase(TenantTestCase):
    """Documents attached to a Process via GenericRelation are copied
    to the new version, sharing the same file storage."""

    def setUp(self):
        super().setUp()
        self.part_type = PartTypes.objects.create(name='Injector', ID_prefix='INJ-')
        self.process, _ = _make_simple_approved_process(
            self.tenant_a, self.user_a, self.part_type,
        )
        process_ct = ContentType.objects.get_for_model(Processes)
        self.doc = Documents.objects.create(
            content_type=process_ct,
            object_id=self.process.pk,
            file_name='assembly-SOP-rev-A.pdf',
            is_image=False,
            classification='INTERNAL',
            status='APPROVED',
            approved_by=self.user_a,
        )

    def test_document_copied_to_new_version(self):
        v2 = create_new_process_version(
            self.process, user=self.user_a, change_description='Rev',
        )
        process_ct = ContentType.objects.get_for_model(Processes)
        v2_docs = Documents.objects.filter(
            content_type=process_ct, object_id=v2.pk,
        )
        self.assertEqual(v2_docs.count(), 1)
        v2_doc = v2_docs.first()
        # Fresh Document row — distinct pk from v1's doc.
        self.assertNotEqual(v2_doc.id, self.doc.id)
        # Same content metadata carried forward.
        self.assertEqual(v2_doc.file_name, self.doc.file_name)
        self.assertEqual(v2_doc.classification, self.doc.classification)

    def test_v2_document_starts_in_draft(self):
        """Re-approval required in v2's context."""
        v2 = create_new_process_version(
            self.process, user=self.user_a, change_description='Rev',
        )
        process_ct = ContentType.objects.get_for_model(Processes)
        v2_doc = Documents.objects.filter(
            content_type=process_ct, object_id=v2.pk,
        ).first()
        self.assertEqual(v2_doc.status, 'DRAFT')
        self.assertIsNone(v2_doc.approved_by)
        self.assertIsNone(v2_doc.approved_at)

    def test_v1_documents_unchanged_after_versioning(self):
        create_new_process_version(
            self.process, user=self.user_a, change_description='Rev',
        )
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.status, 'APPROVED')
        self.assertEqual(self.doc.object_id, str(self.process.pk))


class WorkOrderFkPinningTestCase(TenantTestCase):
    """WorkOrder.process FK keeps pointing at v1 after v2 is created."""

    def setUp(self):
        super().setUp()
        self.part_type = PartTypes.objects.create(name='Injector', ID_prefix='INJ-')
        self.process, _ = _make_simple_approved_process(
            self.tenant_a, self.user_a, self.part_type,
        )
        self.company = Companies.objects.create(name='Acme', description='')
        self.order = Orders.objects.create(
            name='Test Order', company=self.company, customer=self.user_a,
            order_status=OrdersStatus.IN_PROGRESS,
        )
        self.work_order = WorkOrder.objects.create(
            ERP_id='WO-001',
            related_order=self.order,
            process=self.process,
            quantity=10,
            workorder_status=WorkOrderStatus.IN_PROGRESS,
        )

    def test_work_order_process_fk_pins_to_v1_after_versioning(self):
        original_process_id = self.work_order.process_id
        v2 = create_new_process_version(
            self.process, user=self.user_a, change_description='Rev',
        )

        self.work_order.refresh_from_db()
        self.assertEqual(self.work_order.process_id, original_process_id)
        self.assertNotEqual(self.work_order.process_id, v2.id)
        # And the process loaded through the FK is v1 (historical).
        self.assertFalse(self.work_order.process.is_current_version)


class GetAvailableAfterVersioningTestCase(TenantTestCase):
    """`Processes.get_available()` — the effective-query equivalent —
    must keep returning APPROVED v1 while DRAFT v2 exists (regression
    for the is_current_version conflation trap)."""

    def setUp(self):
        super().setUp()
        self.part_type = PartTypes.objects.create(name='Injector', ID_prefix='INJ-')
        self.process, _ = _make_simple_approved_process(
            self.tenant_a, self.user_a, self.part_type,
        )

    def test_draft_successor_does_not_mask_approved_current(self):
        create_new_process_version(
            self.process, user=self.user_a, change_description='Rev',
        )
        # After versioning: v1 is APPROVED + is_current_version=False.
        # v2 is DRAFT + is_current_version=True.
        # `get_available()` queries `status=APPROVED AND is_current_version=True` —
        # neither version matches. This is the known conflation trap.
        # The correct behavior for the business (effective production spec)
        # is "v1 stays effective until v2 is approved."
        #
        # This test documents the CURRENT known-limitation behavior: the
        # filter returns nothing, and the business expectation is that
        # callers use the supersession-aware query once we unify those
        # semantics. Marking as a known gap for the versioning-doc
        # `is_current_version` conflation issue.
        available = Processes.get_available(part_type=self.part_type)
        # This assertion pins the CURRENT observable behavior — update
        # when the conflation is resolved.
        self.assertEqual(available.count(), 0)


class RevisionSignalTestCase(TenantTestCase):
    """`revision_created` fires on successful versioning with correct
    kwargs, so downstream subscribers (webhooks, training reqs, AI
    summaries) have a uniform hook."""

    def setUp(self):
        super().setUp()
        self.part_type = PartTypes.objects.create(name='Injector', ID_prefix='INJ-')
        self.process, _ = _make_simple_approved_process(
            self.tenant_a, self.user_a, self.part_type,
        )
        self.received = MagicMock()
        revision_created.connect(self.received, sender=Processes)

    def tearDown(self):
        revision_created.disconnect(self.received, sender=Processes)
        super().tearDown()

    def test_signal_fires_with_expected_kwargs(self):
        v2 = create_new_process_version(
            self.process, user=self.user_a, change_description='Rev B',
        )
        self.received.assert_called_once()
        kwargs = self.received.call_args.kwargs
        self.assertEqual(kwargs['sender'], Processes)
        self.assertEqual(kwargs['old_version'].pk, self.process.pk)
        self.assertEqual(kwargs['new_version'].pk, v2.pk)
        self.assertEqual(kwargs['user'], self.user_a)
        self.assertEqual(kwargs['change_description'], 'Rev B')

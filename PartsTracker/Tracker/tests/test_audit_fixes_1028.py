"""Product bugs the 2026-10-28 docs audit found.

- Reported: a document's status moves by PATCH. It doesn't — the approval lock in the
  base viewset refuses it; pinned here so it stays that way.
- A document under review could still be revised (revise is an action, outside the
  approval lock), and a revision's file skipped the upload checks.
- classify_documents gated nothing. Changing an existing document's level now needs
  it; the level chosen at upload stays anyone's (decided 2026-10-28).
- MaterialLotViewSet declared action_permissions twice, so the second dict replaced
  the first and release_hold, move, chase and the rest fell back to CRUD gates.
- No product flow put a part on its order, so a real order's page showed no parts.
"""
import uuid

from django.core.files.uploadedfile import SimpleUploadedFile

from Tracker.models import Documents, Orders, Parts, PartTypes, Steps, WorkOrder
from Tracker.tests.base import TenantTestCase


class DocumentControlTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        self.doc = Documents.objects.create(
            tenant=self.tenant_a, file_name="WI-9002 Grind", classification="INTERNAL",
            status="DRAFT", file=SimpleUploadedFile("wi.pdf", b"%PDF-1.4 test"),
            uploaded_by=self.user_a)

    def _as(self, perms):
        self.grant_tenant_permissions(self.user_a, self.tenant_a, perms + ['full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)

    def _patch(self, body):
        return self.client.patch(f"/api/Documents/{self.doc.id}/", body, format="json")

    def test_status_cannot_be_written_by_patch(self):
        self._as(['view_documents', 'change_documents'])
        r = self._patch({"status": "APPROVED"})
        self.assertEqual(r.status_code, 400, r.content)
        self.assertEqual(r.json()["code"], "approval_locked")
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.status, "DRAFT")

    def test_a_document_under_review_cannot_be_revised(self):
        Documents.objects.filter(pk=self.doc.pk).update(status="UNDER_REVIEW")
        self._as(['view_documents', 'add_documents', 'change_documents'])
        r = self.client.post(f"/api/Documents/{self.doc.id}/revise/",
                             {"change_justification": "new torque"}, format="json")
        self.assertEqual(r.status_code, 400, r.content)

    def test_a_revision_file_is_validated_like_an_upload(self):
        Documents.objects.filter(pk=self.doc.pk).update(status="RELEASED")
        self._as(['view_documents', 'add_documents', 'change_documents'])
        r = self.client.post(f"/api/Documents/{self.doc.id}/revise/", {
            "change_justification": "new torque",
            "file": SimpleUploadedFile("evil.exe", b"MZ"),
        }, format="multipart")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("file", r.json())

    def test_changing_classification_needs_classify_documents(self):
        self._as(['view_documents', 'change_documents'])
        r = self._patch({"classification": "PUBLIC"})
        self.assertEqual(r.status_code, 403, r.content)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.classification, "INTERNAL")

    def test_a_classifier_changes_it(self):
        self._as(['view_documents', 'change_documents', 'classify_documents'])
        r = self._patch({"classification": "PUBLIC"})
        self.assertEqual(r.status_code, 200, r.content)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.classification, "PUBLIC")

    def test_resending_the_same_level_is_not_a_change(self):
        self._as(['view_documents', 'change_documents'])
        r = self._patch({"classification": "INTERNAL", "file_name": "renamed"})
        self.assertEqual(r.status_code, 200, r.content)

    def test_an_upload_picks_its_level_without_classify(self):
        self._as(['view_documents', 'add_documents'])
        r = self.client.post("/api/Documents/", {
            "file": SimpleUploadedFile("a.pdf", b"%PDF-1.4"), "file_name": "a.pdf",
            "classification": "CONFIDENTIAL",
        }, format="multipart")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["classification"], "CONFIDENTIAL")


class MaterialLotActionGateTests(TenantTestCase):
    """Permission is checked before the lot is looked up, so an unknown id answers 403
    when the gate refuses and 404 when it lets the request through."""

    def _post(self, perms, action):
        self.grant_tenant_permissions(self.user_a, self.tenant_a, perms + ['full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        return self.client.post(f"/api/MaterialLots/{uuid.uuid4()}/{action}/", {}, format="json")

    def test_releasing_a_hold_needs_approve_disposition(self):
        r = self._post(['view_materiallot', 'change_materiallot', 'add_materiallot'], 'release-hold')
        self.assertEqual(r.status_code, 403, r.content)

    def test_approve_disposition_passes_the_release_gate(self):
        r = self._post(['view_materiallot', 'add_materiallot', 'approve_disposition'], 'release-hold')
        self.assertEqual(r.status_code, 404, r.content)

    def test_moving_a_lot_needs_change_materiallot(self):
        r = self._post(['view_materiallot', 'add_materiallot'], 'move')
        self.assertEqual(r.status_code, 403, r.content)

    def test_the_inspection_gates_still_apply(self):
        r = self._post(['view_materiallot', 'add_materiallot'], 'raise_scar')
        self.assertEqual(r.status_code, 403, r.content)

    def test_every_listed_action_is_gated(self):
        from Tracker.viewsets.mes_standard import MaterialLotViewSet
        gates = MaterialLotViewSet.action_permissions
        for name in ('release_hold', 'adjust_quantity', 'correct_receipt', 'reopen_remainder',
                     'correct_source', 'confirm_whole_lot_reject', 'reject_remainder',
                     'ship_back', 'cancel_expected', 'move', 'chase',
                     'accept', 'reject', 'extend_shelf_life', 'raise_scar'):
            self.assertIn(name, gates)


class PartsOnTheirOrderTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        self.order = Orders.objects.create(tenant=self.tenant_a, name="ORD-1", order_status="PENDING")
        self.other = Orders.objects.create(tenant=self.tenant_a, name="ORD-2", order_status="PENDING")
        self.pt = PartTypes.objects.create(tenant=self.tenant_a, name="Injector", ID_prefix="INJ")
        self.step = Steps.objects.create(tenant=self.tenant_a, name="Machining", part_type=self.pt)
        self.wo = WorkOrder.objects.create(tenant=self.tenant_a, ERP_id="WO-1", quantity=3,
                                           related_order=self.order)

    def test_parts_created_for_a_work_order_are_on_its_order(self):
        from Tracker.services.mes.work_order import create_parts_batch
        parts = create_parts_batch(self.wo, self.pt, self.step)
        self.assertEqual(len(parts), 3)
        self.assertEqual(set(p.order_id for p in parts), {self.order.id})
        self.assertEqual(self.order.parts.count(), 3)

    def test_parts_follow_their_work_order_to_another_order(self):
        from Tracker.services.mes.work_order import create_parts_batch, parts_follow_order
        parts = create_parts_batch(self.wo, self.pt, self.step)
        # One part was put on another order on purpose; it stays there.
        Parts.objects.filter(pk=parts[0].pk).update(order=self.other)
        third = Orders.objects.create(tenant=self.tenant_a, name="ORD-3", order_status="PENDING")
        old = self.wo.related_order_id
        self.wo.related_order = third
        self.wo.save()
        self.assertEqual(parts_follow_order(self.wo, old), 2)
        self.assertEqual(third.parts.count(), 2)
        self.assertEqual(Parts.objects.get(pk=parts[0].pk).order_id, self.other.id)

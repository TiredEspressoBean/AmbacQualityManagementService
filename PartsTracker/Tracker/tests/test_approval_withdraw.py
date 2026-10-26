"""Taking back an approval answer or request while it is still open (user decisions
2026-10-26).

- Corrections #17: an approver changes or withdraws their own response while the request
  is pending; the withdrawn answer and the reason stay on record.
- Walk #46: the requester withdraws a pending request with a reason; a document under
  review goes back to draft so it can be edited and submitted again.
"""
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError

from Tracker.models import (
    ApprovalDecision, ApprovalRequest, Approval_Status_Type, Approval_Type, Documents,
    RecordEdit, Tenant,
)
from Tracker.services.core.approval import (
    add_approver, submit_approval_response, withdraw_approval_request, withdraw_response,
)
from Tracker.tests.base import TenantContextMixin, VectorTestCase


class ApprovalWithdrawTests(TenantContextMixin, VectorTestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Withdraw", slug="approval-withdraw", tier="PRO")
        self.set_tenant_context(self.tenant)
        U = get_user_model()
        self.lisa = U.objects.create_user(username="lisa-w", email="l@w.test", password="x", tenant=self.tenant)
        self.ann = U.objects.create_user(username="ann-w", email="a@w.test", password="x", tenant=self.tenant)
        self.bob = U.objects.create_user(username="bob-w", email="b@w.test", password="x", tenant=self.tenant)
        self.doc = Documents.objects.create(tenant=self.tenant, file_name="WI-9.pdf", status="UNDER_REVIEW")
        self.ar = ApprovalRequest.objects.create(
            tenant=self.tenant, approval_number="APR-W-1", approval_type=Approval_Type.DOCUMENT_RELEASE,
            requested_by=self.lisa, content_type=ContentType.objects.get_for_model(Documents),
            object_id=str(self.doc.pk))
        add_approver(self.ar, self.ann, is_required=True)
        add_approver(self.ar, self.bob, is_required=True)

    def test_an_approver_withdraws_and_answers_again_while_it_is_open(self):
        response = submit_approval_response(self.ar, self.ann, ApprovalDecision.APPROVED)
        self.ar.refresh_from_db()
        self.assertEqual(self.ar.status, Approval_Status_Type.PENDING)  # Bob still to answer
        with self.assertRaises(ValidationError):
            withdraw_response(response, self.ann, "")
        with self.assertRaises(PermissionDenied):
            withdraw_response(response, self.bob, "not mine")
        withdraw_response(response, self.ann, "Approved the wrong revision")
        response.refresh_from_db()
        self.assertEqual(response.decision, ApprovalDecision.WITHDRAWN)
        self.assertIn(self.ann, self.ar.get_pending_approvers())
        edit = RecordEdit.objects.get(object_id=response.id, field_name="decision")
        self.assertEqual((edit.old_value, edit.reason), ("APPROVED", "Approved the wrong revision"))
        # Answering again uses the same row; the request closes on the new answer.
        again = submit_approval_response(self.ar, self.ann, ApprovalDecision.REJECTED,
                                         comments="Section 4 wrong")
        self.assertEqual(again.pk, response.pk)
        # The row shows the change, not only the latest answer.
        from Tracker.serializers.core import ApprovalResponseSerializer
        seen = [(c["old_value"], c["new_value"]) for c in ApprovalResponseSerializer(again).data["corrections"]]
        self.assertEqual(seen, [("APPROVED", "WITHDRAWN"), ("WITHDRAWN", "REJECTED")])
        self.ar.refresh_from_db()
        self.assertEqual(self.ar.status, Approval_Status_Type.REJECTED)
        with self.assertRaises(ValidationError):
            withdraw_response(again, self.ann, "too late")

    def test_the_requester_withdraws_a_pending_request(self):
        with self.assertRaises(PermissionDenied):
            withdraw_approval_request(self.ar, self.ann, "not mine")
        with self.assertRaises(ValidationError):
            withdraw_approval_request(self.ar, self.lisa, " ")
        withdraw_approval_request(self.ar, self.lisa, "Wrong classification; fixing it")
        self.ar.refresh_from_db()
        self.doc.refresh_from_db()
        self.assertEqual(self.ar.status, Approval_Status_Type.CANCELLED)
        self.assertEqual(self.doc.status, "DRAFT")
        self.assertTrue(RecordEdit.objects.filter(object_id=self.ar.id,
                                                  reason="Wrong classification; fixing it").exists())
        with self.assertRaises(ValueError):
            withdraw_approval_request(self.ar, self.lisa, "again")

"""Claiming group-routed approvals (the "available to claim" queue).

A GroupApproverAssignment means "any member may respond" — which in practice
means requests rot while every member assumes someone else has them. `claim`
converts shared eligibility into individual ownership; `claimable` lists what
the current user could claim.
"""
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection
from rest_framework.test import APIClient
from unittest import skipIf

from Tracker.models import (
    ApprovalRequest, ApprovalResponse, ApproverAssignment,
    ApproverAssignmentSource, GroupApproverAssignment, Tenant,
    TenantGroup, UserRole,
)
from Tracker.services.core.approval import claim_approval, claimable_approvals
from Tracker.tests.base import VectorTestCase, TenantContextMixin


def is_vector_extension_available():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            return cursor.fetchone() is not None
    except Exception:
        return False


User = get_user_model()


@skipIf(not is_vector_extension_available(), "Vector extension not available")
class ApprovalClaimTestCase(TenantContextMixin, VectorTestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Claim Tenant", slug="claim-tenant")
        self.set_tenant_context(self.tenant)

        self.member = User.objects.create_user(
            username='qa_member', email='member@example.com',
            password='testpass', tenant=self.tenant,
        )
        self.other_member = User.objects.create_user(
            username='qa_member2', email='member2@example.com',
            password='testpass', tenant=self.tenant,
        )
        self.outsider = User.objects.create_user(
            username='outsider', email='outsider@example.com',
            password='testpass', tenant=self.tenant,
        )

        self.qa_group = TenantGroup.objects.create(
            tenant=self.tenant, name="QA", description="QA group", is_custom=True,
        )
        UserRole.objects.create(user=self.member, group=self.qa_group)
        UserRole.objects.create(user=self.other_member, group=self.qa_group)

    def _group_routed_request(self, **overrides):
        """A PENDING approval routed only to the QA group."""
        fields = dict(
            tenant=self.tenant,
            approval_number=ApprovalRequest.generate_approval_number(tenant=self.tenant),
            approval_type='CAPA_APPROVAL',
            requested_by=self.outsider,
        )
        fields.update(overrides)
        request = ApprovalRequest.objects.create(**fields)
        GroupApproverAssignment.objects.create(
            approval_request=request, group=self.qa_group,
        )
        return request

    # -- service ------------------------------------------------------------

    def test_claim_creates_owned_assignment(self):
        request = self._group_routed_request()
        assignment = claim_approval(request, self.member)

        self.assertEqual(assignment.user, self.member)
        self.assertTrue(assignment.is_required)
        self.assertEqual(assignment.assignment_source, ApproverAssignmentSource.CLAIMED)
        self.assertEqual(assignment.assigned_by, self.member)

    def test_non_member_cannot_claim(self):
        request = self._group_routed_request()
        with self.assertRaises(PermissionDenied):
            claim_approval(request, self.outsider)

    def test_already_claimed_rejects_second_claim(self):
        request = self._group_routed_request()
        claim_approval(request, self.member)
        with self.assertRaises(ValidationError):
            claim_approval(request, self.other_member)

    def test_individually_assigned_request_not_claimable(self):
        request = self._group_routed_request()
        ApproverAssignment.objects.create(
            approval_request=request, user=self.other_member, is_required=True,
        )
        with self.assertRaises(ValidationError):
            claim_approval(request, self.member)

    def test_non_pending_not_claimable(self):
        request = self._group_routed_request(status='APPROVED')
        with self.assertRaises(ValidationError):
            claim_approval(request, self.member)

    def test_claimable_filter(self):
        request = self._group_routed_request()
        base = ApprovalRequest.objects.all()

        self.assertIn(request, claimable_approvals(base, self.member))
        self.assertNotIn(request, claimable_approvals(base, self.outsider))

        claim_approval(request, self.member)
        self.assertNotIn(request, claimable_approvals(base, self.other_member))

    def test_claimer_approval_completes_request(self):
        """After a claim, the claimer's APPROVED response completes the
        ALL_REQUIRED request (they became its sole required approver)."""
        request = self._group_routed_request()
        claim_approval(request, self.member)

        ApprovalResponse.submit_response(
            approval_request=request, approver=self.member, decision='APPROVED',
        )
        request.refresh_from_db()
        self.assertEqual(request.status, 'APPROVED')

    # -- API ----------------------------------------------------------------

    def _client_for(self, user, perms):
        from django.contrib.auth.models import Permission

        group = TenantGroup.objects.create(
            tenant=self.tenant, name=f"perms_{user.username}", is_custom=True,
        )
        group.permissions.add(*Permission.objects.filter(codename__in=perms))
        UserRole.objects.create(user=user, group=group)

        client = APIClient()
        client.force_authenticate(user=user)
        client.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        return client

    def test_claimable_endpoint_and_claim_flow(self):
        request = self._group_routed_request()
        client = self._client_for(
            self.member, ['view_approvalrequest', 'respond_to_approval', 'full_tenant_access'],
        )

        listed = client.get('/api/ApprovalRequests/claimable/')
        self.assertEqual(listed.status_code, 200)
        payload = listed.json()
        rows = payload.get('results', payload)
        self.assertIn(str(request.id), [str(r['id']) for r in rows])

        claimed = client.post(f'/api/ApprovalRequests/{request.id}/claim/')
        self.assertEqual(claimed.status_code, 200, claimed.content)
        self.assertTrue(
            ApproverAssignment.objects.filter(
                approval_request=request, user=self.member,
                assignment_source=ApproverAssignmentSource.CLAIMED,
            ).exists()
        )

        # Claimed → gone from everyone's claimable queue.
        relisted = client.get('/api/ApprovalRequests/claimable/')
        payload = relisted.json()
        rows = payload.get('results', payload)
        self.assertNotIn(str(request.id), [str(r['id']) for r in rows])

    def test_claim_requires_group_membership_via_api(self):
        request = self._group_routed_request()
        client = self._client_for(
            self.outsider, ['view_approvalrequest', 'respond_to_approval', 'full_tenant_access'],
        )
        response = client.post(f'/api/ApprovalRequests/{request.id}/claim/')
        self.assertEqual(response.status_code, 403)

    def test_double_claim_via_api_is_400(self):
        request = self._group_routed_request()
        claim_approval(request, self.member)
        client = self._client_for(
            self.other_member, ['view_approvalrequest', 'respond_to_approval', 'full_tenant_access'],
        )
        response = client.post(f'/api/ApprovalRequests/{request.id}/claim/')
        self.assertEqual(response.status_code, 400)

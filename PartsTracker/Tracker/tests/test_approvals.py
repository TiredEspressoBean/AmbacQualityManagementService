from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django.db import connection
from rest_framework.test import APIClient
from rest_framework import status
from unittest import skipIf
from Tracker.models import (
    ApprovalTemplate, ApprovalRequest, ApprovalResponse,
    Documents, CAPA
)
from Tracker.tests.base import VectorTestCase

def is_vector_extension_available():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            return cursor.fetchone() is not None
    except Exception:
        return False

User = get_user_model()

@skipIf(not is_vector_extension_available(), "Vector extension not available")
class ApprovalTemplateTestCase(VectorTestCase):
    def setUp(self):
        # Create users
        self.qa_manager = User.objects.create_user(
            username='qa_manager',
            email='qa@example.com',
            password='testpass',
            is_staff=True
        )
        self.doc_controller = User.objects.create_user(
            username='doc_controller',
            email='doc@example.com',
            password='testpass'
        )
        self.engineer = User.objects.create_user(
            username='engineer',
            email='eng@example.com',
            password='testpass'
        )

    def test_template_creation(self):
        """Test creating an approval template"""
        template, _ = ApprovalTemplate.objects.update_or_create(
            approval_type="DOCUMENT_RELEASE",
            defaults={
                "template_name": "Document Release",
                "approval_flow_type": "ALL_REQUIRED",
                "approval_sequence": "PARALLEL",
                "default_due_days": 5,
                "escalation_days": 3,
                "escalate_to": self.qa_manager,
                "delegation_policy": "OPTIONAL"
            }
        )
        template.default_approvers.set([self.qa_manager, self.doc_controller])

        self.assertEqual(template.template_name, "Document Release")
        self.assertEqual(template.default_approvers.count(), 2)
        self.assertEqual(template.default_due_days, 5)

    def test_template_threshold_flow(self):
        """Test template with threshold approval flow"""
        template, _ = ApprovalTemplate.objects.update_or_create(
            approval_type="ECO",
            defaults={
                "template_name": "Engineering Change",
                "approval_flow_type": "THRESHOLD",
                "approval_sequence": "PARALLEL",
                "default_threshold": 2,
                "default_due_days": 10
            }
        )
        template.default_approvers.set([self.qa_manager, self.doc_controller, self.engineer])

        self.assertEqual(template.approval_flow_type, "THRESHOLD")
        self.assertEqual(template.default_threshold, 2)
        self.assertEqual(template.default_approvers.count(), 3)


@skipIf(not is_vector_extension_available(), "Vector extension not available")
class ApprovalRequestTestCase(VectorTestCase):
    def setUp(self):
        # Create users
        self.requester = User.objects.create_user(
            username='requester',
            email='requester@example.com',
            password='testpass'
        )
        self.approver1 = User.objects.create_user(
            username='approver1',
            email='approver1@example.com',
            password='testpass'
        )
        self.approver2 = User.objects.create_user(
            username='approver2',
            email='approver2@example.com',
            password='testpass'
        )

        # Create template
        self.template, _ = ApprovalTemplate.objects.update_or_create(
            approval_type="DOCUMENT_RELEASE",
            defaults={
                "template_name": "Document Release",
                "approval_flow_type": "ALL_REQUIRED",
                "approval_sequence": "PARALLEL",
                "default_due_days": 5,
                "escalation_days": 3,
                "escalate_to": self.approver1
            }
        )
        self.template.default_approvers.set([self.approver1, self.approver2])

        # Create a document
        self.document = Documents.objects.create(
            file_name="test_doc.pdf",
            uploaded_by=self.requester,
            status="DRAFT"
        )

    def test_create_approval_from_template(self):
        """Test creating approval request from template"""
        approval = ApprovalRequest.create_from_template(
            content_object=self.document,
            template=self.template,
            requested_by=self.requester,
            reason="Test approval"
        )

        self.assertIsNotNone(approval.approval_number)
        self.assertTrue(approval.approval_number.startswith('APR-'))
        self.assertEqual(approval.status, 'PENDING')
        self.assertEqual(approval.requested_by, self.requester)
        self.assertEqual(approval.required_approvers.count(), 2)
        self.assertEqual(approval.flow_type, "ALL_REQUIRED")
        self.assertIsNotNone(approval.due_date)

    def test_approval_number_generation(self):
        """Test unique approval number generation"""
        approval1 = ApprovalRequest.create_from_template(
            content_object=self.document,
            template=self.template,
            requested_by=self.requester
        )

        doc2 = Documents.objects.create(
            file_name="test_doc2.pdf",
            uploaded_by=self.requester
        )
        approval2 = ApprovalRequest.create_from_template(
            content_object=doc2,
            template=self.template,
            requested_by=self.requester
        )

        self.assertNotEqual(approval1.approval_number, approval2.approval_number)
        self.assertTrue(approval1.approval_number < approval2.approval_number)

    def test_get_pending_approvers(self):
        """Test getting list of pending approvers"""
        approval = ApprovalRequest.create_from_template(
            content_object=self.document,
            template=self.template,
            requested_by=self.requester
        )

        pending = approval.get_pending_approvers()
        self.assertEqual(len(pending), 2)
        self.assertIn(self.approver1, pending)
        self.assertIn(self.approver2, pending)

    def test_check_approval_status_all_required(self):
        """Test status check with ALL_REQUIRED flow"""
        approval = ApprovalRequest.create_from_template(
            content_object=self.document,
            template=self.template,
            requested_by=self.requester
        )

        # Initially pending
        new_status, pending = approval.check_approval_status()
        self.assertEqual(new_status, 'PENDING')
        self.assertEqual(len(pending), 2)

        # One approves
        ApprovalResponse.submit_response(
            approval_request=approval,
            approver=self.approver1,
            decision='APPROVED',
            comments="Looks good"
        )

        new_status, pending = approval.check_approval_status()
        self.assertEqual(new_status, 'PENDING')
        self.assertEqual(len(pending), 1)

        # Second approves
        ApprovalResponse.submit_response(
            approval_request=approval,
            approver=self.approver2,
            decision='APPROVED',
            comments="Approved"
        )

        new_status, pending = approval.check_approval_status()
        self.assertEqual(new_status, 'APPROVED')
        self.assertEqual(len(pending), 0)

    def test_rejection_blocks_approval(self):
        """Test that any rejection changes status to REJECTED"""
        approval = ApprovalRequest.create_from_template(
            content_object=self.document,
            template=self.template,
            requested_by=self.requester
        )

        # One rejects
        ApprovalResponse.submit_response(
            approval_request=approval,
            approver=self.approver1,
            decision='REJECTED',
            comments="Needs revision"
        )

        new_status, pending = approval.check_approval_status()
        self.assertEqual(new_status, 'REJECTED')

    def test_threshold_approval_flow(self):
        """Test approval with THRESHOLD flow type"""
        # Create template with threshold
        threshold_template, _ = ApprovalTemplate.objects.update_or_create(
            approval_type="ECO",
            defaults={
                "template_name": "Engineering Review",
                "approval_flow_type": "THRESHOLD",
                "approval_sequence": "PARALLEL",
                "default_threshold": 2,
                "default_due_days": 10
            }
        )

        approver3 = User.objects.create_user(
            username='approver3',
            email='approver3@example.com',
            password='testpass'
        )
        threshold_template.default_approvers.add(self.approver1, self.approver2, approver3)

        approval = ApprovalRequest.create_from_template(
            content_object=self.document,
            template=threshold_template,
            requested_by=self.requester
        )

        self.assertEqual(approval.threshold, 2)
        self.assertEqual(approval.required_approvers.count(), 3)

        # First approval
        ApprovalResponse.submit_response(
            approval_request=approval,
            approver=self.approver1,
            decision='APPROVED'
        )

        new_status, pending = approval.check_approval_status()
        self.assertEqual(new_status, 'PENDING')

        # Second approval - should reach threshold
        ApprovalResponse.submit_response(
            approval_request=approval,
            approver=self.approver2,
            decision='APPROVED'
        )

        new_status, pending = approval.check_approval_status()
        self.assertEqual(new_status, 'APPROVED')

    def test_is_overdue(self):
        """Test overdue detection"""
        approval = ApprovalRequest.create_from_template(
            content_object=self.document,
            template=self.template,
            requested_by=self.requester
        )

        # Not overdue initially
        self.assertFalse(approval.is_overdue())

        # Set due date in the past
        approval.due_date = timezone.now() - timedelta(days=1)
        approval.save()

        self.assertTrue(approval.is_overdue())

        # Completed approvals are never overdue
        approval.status = 'APPROVED'
        approval.completed_at = timezone.now()
        approval.save()

        self.assertFalse(approval.is_overdue())


@skipIf(not is_vector_extension_available(), "Vector extension not available")
class ApprovalResponseTestCase(VectorTestCase):
    def setUp(self):
        self.requester = User.objects.create_user(
            username='requester',
            email='requester@example.com',
            password='testpass'
        )
        self.approver = User.objects.create_user(
            username='approver',
            email='approver@example.com',
            password='testpass'
        )

        template, _ = ApprovalTemplate.objects.update_or_create(
            approval_type="DOCUMENT_RELEASE",
            defaults={
                "template_name": "Test Template",
                "approval_flow_type": "ALL_REQUIRED",
                "approval_sequence": "PARALLEL",
                "default_due_days": 5
            }
        )
        template.default_approvers.set([self.approver])

        self.document = Documents.objects.create(
            file_name="test.pdf",
            uploaded_by=self.requester
        )

        self.approval = ApprovalRequest.create_from_template(
            content_object=self.document,
            template=template,
            requested_by=self.requester
        )

    def test_submit_response(self):
        """Test submitting an approval response"""
        response = ApprovalResponse.submit_response(
            approval_request=self.approval,
            approver=self.approver,
            decision='APPROVED',
            comments="Looks good",
            password="testpass"
        )

        self.assertEqual(response.decision, 'APPROVED')
        self.assertEqual(response.approver, self.approver)
        self.assertIsNotNone(response.decision_date)
        self.assertEqual(response.comments, "Looks good")
        self.assertIsNotNone(response.verified_at)
        self.assertEqual(response.verification_method, 'PASSWORD')

    def test_duplicate_response_prevention(self):
        """Test that approvers can't respond twice"""
        ApprovalResponse.submit_response(
            approval_request=self.approval,
            approver=self.approver,
            decision='APPROVED'
        )

        with self.assertRaises(Exception):
            ApprovalResponse.submit_response(
                approval_request=self.approval,
                approver=self.approver,
                decision='APPROVED'
            )

    def test_unauthorized_approver(self):
        """Test that non-approvers can't respond"""
        unauthorized = User.objects.create_user(
            username='unauthorized',
            email='unauth@example.com',
            password='testpass'
        )

        with self.assertRaises(Exception):
            ApprovalResponse.submit_response(
                approval_request=self.approval,
                approver=unauthorized,
                decision='APPROVED'
            )

    def test_password_verification(self):
        """Test password verification on response"""
        # Wrong password should fail
        with self.assertRaises(Exception):
            ApprovalResponse.submit_response(
                approval_request=self.approval,
                approver=self.approver,
                decision='APPROVED',
                password="wrongpassword"
            )

        # Correct password should work
        response = ApprovalResponse.submit_response(
            approval_request=self.approval,
            approver=self.approver,
            decision='APPROVED',
            password="testpass"
        )

        self.assertEqual(response.verification_method, 'PASSWORD')
        self.assertIsNotNone(response.verified_at)


@skipIf(not is_vector_extension_available(), "Vector extension not available")
class DocumentApprovalIntegrationTestCase(VectorTestCase):
    def setUp(self):
        from Tracker.models import Tenant

        # Create tenant for multi-tenancy
        self.tenant = Tenant.objects.create(
            name="Doc Approval Tenant",
            slug="doc-approval-tenant",
            tier="pro"
        )

        self.user = User.objects.create_user(
            username='docuser',
            email='docuser@example.com',
            password='testpass',
            is_superuser=True,  # Required to access documents via API
            tenant=self.tenant,
            us_person=True  # For ITAR access
        )
        self.approver = User.objects.create_user(
            username='approver',
            email='approver@example.com',
            password='testpass',
            tenant=self.tenant
        )

        # Create approval template with tenant
        self.template, _ = ApprovalTemplate.objects.update_or_create(
            approval_type="DOCUMENT_RELEASE",
            tenant=self.tenant,
            defaults={
                "template_name": "Document Release",
                "approval_flow_type": "ALL_REQUIRED",
                "approval_sequence": "PARALLEL",
                "default_due_days": 5
            }
        )
        self.template.default_approvers.set([self.approver])

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))

    def test_document_submit_for_approval(self):
        """Test submitting document for approval"""
        document = Documents.objects.create(
            file_name="test_doc.pdf",
            uploaded_by=self.user,
            status="DRAFT",
            tenant=self.tenant
        )

        approval = document.submit_for_approval(self.user)

        # Check approval was created
        self.assertIsNotNone(approval)
        self.assertEqual(approval.content_object, document)
        self.assertEqual(approval.requested_by, self.user)

        # Check document status changed
        document.refresh_from_db()
        self.assertEqual(document.status, "UNDER_REVIEW")

    def test_cannot_submit_non_draft_document(self):
        """Test that only DRAFT documents can be submitted"""
        document = Documents.objects.create(
            file_name="approved_doc.pdf",
            uploaded_by=self.user,
            status="APPROVED",
            tenant=self.tenant
        )

        with self.assertRaises(ValueError):
            document.submit_for_approval(self.user)

    def test_document_approval_workflow_integration(self):
        """Test full document approval workflow"""
        # Create document
        document = Documents.objects.create(
            file_name="workflow_test.pdf",
            uploaded_by=self.user,
            status="DRAFT",
            tenant=self.tenant
        )

        # Submit for approval
        approval = document.submit_for_approval(self.user)
        self.assertEqual(document.status, "UNDER_REVIEW")

        # Approver approves
        ApprovalResponse.submit_response(
            approval_request=approval,
            approver=self.approver,
            decision='APPROVED',
            comments="Approved"
        )

        # Update approval status
        approval.update_status()
        approval.refresh_from_db()

        self.assertEqual(approval.status, 'APPROVED')
        self.assertIsNotNone(approval.completed_at)
        # Note: ApprovalRequest doesn't have completed_by field, only completed_at

    def test_document_approval_api_endpoint(self):
        """Test document submit-for-approval API endpoint"""
        document = Documents.objects.create(
            file_name="api_test.pdf",
            uploaded_by=self.user,
            status="DRAFT",
            tenant=self.tenant
        )

        response = self.client.post(
            f'/api/Documents/{document.id}/submit-for-approval/'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertIn('approval_number', response.data)

        # Verify document status changed
        document.refresh_from_db()
        self.assertEqual(document.status, "UNDER_REVIEW")


@skipIf(not is_vector_extension_available(), "Vector extension not available")
class SelfApprovalValidationTestCase(VectorTestCase):
    """Test self-approval validation logic"""

    def setUp(self):
        self.requester = User.objects.create_user(
            username='requester',
            email='requester@example.com',
            password='testpass'
        )
        self.approver = User.objects.create_user(
            username='approver',
            email='approver@example.com',
            password='testpass'
        )

        # Template with self-approval disabled (default)
        self.template_no_self, _ = ApprovalTemplate.objects.update_or_create(
            approval_type="DOCUMENT_RELEASE",
            defaults={
                "template_name": "Document Release",
                "approval_flow_type": "ALL_REQUIRED",
                "approval_sequence": "PARALLEL",
                "default_due_days": 5,
                "allow_self_approval": False
            }
        )
        self.template_no_self.default_approvers.set([self.requester, self.approver])

        # Template with self-approval enabled
        self.template_allow_self, _ = ApprovalTemplate.objects.update_or_create(
            approval_type="ECO",
            defaults={
                "template_name": "Emergency Release",
                "approval_flow_type": "ALL_REQUIRED",
                "approval_sequence": "PARALLEL",
                "default_due_days": 1,
                "allow_self_approval": True
            }
        )
        self.template_allow_self.default_approvers.set([self.requester, self.approver])

        self.document = Documents.objects.create(
            file_name="test.pdf",
            uploaded_by=self.requester,
            status="DRAFT"
        )

    def test_self_approval_blocked_by_default(self):
        """Test that self-approval is blocked when template disallows it"""
        approval = ApprovalRequest.create_from_template(
            content_object=self.document,
            template=self.template_no_self,
            requested_by=self.requester
        )

        # Requester tries to approve their own request
        with self.assertRaises(Exception) as cm:
            ApprovalResponse.submit_response(
                approval_request=approval,
                approver=self.requester,
                decision='APPROVED'
            )

        self.assertIn("Self-approval is not permitted", str(cm.exception))

    def test_self_approval_allowed_with_justification(self):
        """Test that self-approval works when template allows it and justification provided"""
        approval = ApprovalRequest.create_from_template(
            content_object=self.document,
            template=self.template_allow_self,
            requested_by=self.requester
        )

        # Requester approves with justification
        response = ApprovalResponse.submit_response(
            approval_request=approval,
            approver=self.requester,
            decision='APPROVED',
            comments="Emergency approval - primary approver unavailable due to vacation"
        )

        self.assertEqual(response.approver, self.requester)
        self.assertEqual(response.decision, 'APPROVED')
        self.assertTrue(response.self_approved)
        self.assertIsNotNone(response.comments)

    def test_self_approval_requires_justification(self):
        """Test that self-approval requires minimum 10 character justification"""
        approval = ApprovalRequest.create_from_template(
            content_object=self.document,
            template=self.template_allow_self,
            requested_by=self.requester
        )

        # Too short justification
        with self.assertRaises(Exception) as cm:
            ApprovalResponse.submit_response(
                approval_request=approval,
                approver=self.requester,
                decision='APPROVED',
                comments="OK"
            )

        self.assertIn("Justification required", str(cm.exception))
        self.assertIn("minimum 10 characters", str(cm.exception))

    def test_self_approval_no_justification(self):
        """Test that self-approval fails without justification"""
        approval = ApprovalRequest.create_from_template(
            content_object=self.document,
            template=self.template_allow_self,
            requested_by=self.requester
        )

        # No justification
        with self.assertRaises(Exception) as cm:
            ApprovalResponse.submit_response(
                approval_request=approval,
                approver=self.requester,
                decision='APPROVED'
            )

        self.assertIn("Justification required", str(cm.exception))

    def test_other_user_approval_not_affected(self):
        """Test that different user approval works normally"""
        approval = ApprovalRequest.create_from_template(
            content_object=self.document,
            template=self.template_no_self,
            requested_by=self.requester
        )

        # Different user approves - should work fine
        response = ApprovalResponse.submit_response(
            approval_request=approval,
            approver=self.approver,
            decision='APPROVED'
        )

        self.assertEqual(response.approver, self.approver)
        self.assertEqual(response.decision, 'APPROVED')
        self.assertFalse(response.self_approved)

    def test_self_approved_flag_set_correctly(self):
        """Test that self_approved flag is set correctly"""
        approval = ApprovalRequest.create_from_template(
            content_object=self.document,
            template=self.template_allow_self,
            requested_by=self.requester
        )

        # Self-approval
        response1 = ApprovalResponse.submit_response(
            approval_request=approval,
            approver=self.requester,
            decision='APPROVED',
            comments="Emergency self-approval with justification here"
        )
        self.assertTrue(response1.self_approved)

        # Other user approval
        approval2 = ApprovalRequest.create_from_template(
            content_object=self.document,
            template=self.template_allow_self,
            requested_by=self.requester
        )
        response2 = ApprovalResponse.submit_response(
            approval_request=approval2,
            approver=self.approver,
            decision='APPROVED'
        )
        self.assertFalse(response2.self_approved)

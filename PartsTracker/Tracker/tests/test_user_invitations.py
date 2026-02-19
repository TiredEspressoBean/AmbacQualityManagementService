from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django.db import connection
from rest_framework.test import APIClient
from rest_framework import status
from unittest import skipIf
from Tracker.models import UserInvitation, NotificationTask, Tenant, TenantGroup, UserRole
from Tracker.tests.base import VectorTestCase
from django.contrib.auth.models import Permission

def is_vector_extension_available():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            return cursor.fetchone() is not None
    except Exception:
        return False

User = get_user_model()

@skipIf(not is_vector_extension_available(), "Vector extension not available")
class UserInvitationTestCase(VectorTestCase):
    def setUp(self):
        # Create tenant for multi-tenancy
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant",
            tier="pro"
        )

        # Create a staff user who can send invitations
        self.staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='staffpassword',
            is_staff=True,
            tenant=self.tenant
        )

        # Create TenantGroup with required permissions
        self.admin_group = TenantGroup.objects.create(
            tenant=self.tenant,
            name="Admin",
            description="Admin group with all permissions",
            is_custom=False
        )

        # Grant all permissions to admin group
        all_perms = Permission.objects.all()
        self.admin_group.permissions.add(*all_perms)

        # Link staff user to admin group
        UserRole.objects.create(user=self.staff_user, group=self.admin_group)

        # Create a user to be invited (in same tenant)
        self.invited_user = User.objects.create_user(
            username='inviteduser',
            email='invited@example.com',
            password='temporarypassword',
            is_active=False,
            tenant=self.tenant
        )

        # Create API client for testing with tenant header
        self.client = APIClient()
        self.client.force_authenticate(user=self.staff_user)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))

    def test_invitation_creation(self):
        """Test creating a user invitation"""
        invitation_data = {
            'user_id': self.invited_user.id
        }

        response = self.client.post('/api/User/send-invitation/', invitation_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('invitation_id', response.data)

        invitation = UserInvitation.objects.get(id=response.data['invitation_id'])

        self.assertEqual(invitation.user, self.invited_user)
        self.assertEqual(invitation.invited_by, self.staff_user)
        self.assertIsNotNone(invitation.token)
        self.assertTrue(invitation.expires_at > timezone.now())

    def test_token_validation(self):
        """Test validating an invitation token"""
        # Create an invitation first
        invitation = UserInvitation.objects.create(
            user=self.invited_user,
            invited_by=self.staff_user,
            token=UserInvitation.generate_token(),
            expires_at=timezone.now() + timedelta(days=7)
        )

        # Test valid token
        response = self.client.post('/api/UserInvitations/validate-token/', {'token': invitation.token})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['valid'])
        self.assertEqual(response.data['user_email'], self.invited_user.email)

    def test_expired_token_validation(self):
        """Test validating an expired invitation token"""
        # Create an expired invitation
        invitation = UserInvitation.objects.create(
            user=self.invited_user,
            invited_by=self.staff_user,
            token=UserInvitation.generate_token(),
            expires_at=timezone.now() - timedelta(days=1)  # Already expired
        )

        # Test expired token
        response = self.client.post('/api/UserInvitations/validate-token/', {'token': invitation.token})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['valid'])
        self.assertTrue(response.data['expired'])

    def test_invitation_acceptance(self):
        """Test accepting an invitation and creating user account"""
        # Create a valid invitation
        invitation = UserInvitation.objects.create(
            user=self.invited_user,
            invited_by=self.staff_user,
            token=UserInvitation.generate_token(),
            expires_at=timezone.now() + timedelta(days=7)
        )

        # Data for accepting invitation
        acceptance_data = {
            'token': invitation.token,
            'password': 'NewSecurePassword123!',
            'opt_in_notifications': True
        }

        # Use unauthenticated client for public endpoint
        client = APIClient()
        response = client.post('/api/UserInvitations/accept/', acceptance_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Reload invitation and user
        invitation.refresh_from_db()
        self.invited_user.refresh_from_db()

        # Check user is now active
        self.assertTrue(self.invited_user.is_active)

        # Check invitation was marked as accepted
        self.assertIsNotNone(invitation.accepted_at)
        self.assertIsNotNone(invitation.accepted_ip_address)

        # Check notification preference was created if opted in
        notification_exists = NotificationTask.objects.filter(
            recipient=self.invited_user,
            notification_type='WEEKLY_REPORT'
        ).exists()
        self.assertTrue(notification_exists)

    def test_duplicate_invitation_prevention(self):
        """Test that a user cannot be invited multiple times with active invitations"""
        # Create first invitation
        first_invitation = UserInvitation.objects.create(
            user=self.invited_user,
            invited_by=self.staff_user,
            token=UserInvitation.generate_token(),
            expires_at=timezone.now() + timedelta(days=7)
        )

        # Try to create another invitation
        response = self.client.post('/api/User/send-invitation/', {'user_id': self.invited_user.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already has a pending invitation", str(response.data))

    def test_resend_invitation(self):
        """Test resending an invitation"""
        # Create initial invitation
        initial_invitation = UserInvitation.objects.create(
            user=self.invited_user,
            invited_by=self.staff_user,
            token=UserInvitation.generate_token(),
            expires_at=timezone.now() + timedelta(days=7)
        )

        # Resend invitation
        response = self.client.post('/api/UserInvitations/resend/', {'invitation_id': initial_invitation.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check a new invitation was created
        new_invitation = UserInvitation.objects.filter(
            user=self.invited_user
        ).exclude(id=initial_invitation.id).first()

        self.assertIsNotNone(new_invitation)
        self.assertNotEqual(new_invitation.token, initial_invitation.token)
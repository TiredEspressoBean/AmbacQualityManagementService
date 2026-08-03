"""Formally raising a CAPA (POST /api/capa/) now requires initiate_capa
on top of the CRUD add_capa gate.

Prior behavior: any staff role with add_capa (i.e., everyone via
STAFF_OPERATIONAL_WRITE) could POST a new CAPA. That's not aligned with
AS9100 QMS practice — a formal CAPA is a governance-heavy record and its
initiation should sit with QA / supervisors, not the floor.

Fix: CAPAViewSet declares action_permissions = {'create': ['initiate_capa']},
which the TenantModelPermissions permission class layers additively on top
of the raw add_capa CRUD gate. QA Inspector, QA Manager, Production Manager,
Shift Lead, and Tenant Admin retain initiate_capa; Operator does not.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APIClient

from Tracker.models import CAPA, Tenant, TenantGroup, UserRole
from Tracker.tests.base import TenantContextMixin, VectorTestCase


class InitiateCapaGateTests(TenantContextMixin, VectorTestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(
            name="Capa Gate", slug="capa-gate", tier="PRO",
        )
        self.set_tenant_context(self.tenant)
        User = get_user_model()
        self.user = User.objects.create_user(
            username="capa-gate-user", email="cg@user.test", password="x",
            tenant=self.tenant,
        )

        ct = ContentType.objects.get_for_model(CAPA)
        self.add_capa = Permission.objects.get(codename='add_capa', content_type=ct)
        self.initiate_capa = Permission.objects.get(codename='initiate_capa', content_type=ct)
        # full_tenant_access is required for the queryset filtering; grant it
        # to every test user so the 403 we're checking is the CAPA-gate 403,
        # not the object-scoping 403.
        self.full_tenant_access = Permission.objects.get(codename='full_tenant_access')

    def _grant(self, *perms):
        """Put the user in a TenantGroup carrying the given perms."""
        group = TenantGroup.objects.create(
            tenant=self.tenant, name=f'perms-{len(perms)}', is_custom=True,
        )
        group.permissions.add(*perms, self.full_tenant_access)
        UserRole.objects.create(user=self.user, group=group)

    def _post_capa(self):
        client = APIClient()
        client.force_authenticate(user=self.user)
        client.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        return client.post('/api/CAPAs/', {
            'problem_statement': 'Test CAPA for gate check',
            'capa_type': 'CORRECTIVE',
            'severity': 'MINOR',
            'approval_required': False,
            'approval_status': 'NOT_REQUIRED',
        }, format='json')

    def test_add_capa_alone_is_no_longer_enough(self):
        """The behavior change: pre-fix a user with add_capa (via
        STAFF_OPERATIONAL_WRITE) could POST. Post-fix, they need
        initiate_capa too."""
        self._grant(self.add_capa)
        resp = self._post_capa()
        self.assertEqual(resp.status_code, 403,
                         f'expected 403, got {resp.status_code}: {resp.content!r}')

    def test_both_perms_grants_creation(self):
        self._grant(self.add_capa, self.initiate_capa)
        resp = self._post_capa()
        self.assertIn(resp.status_code, (201, 200),
                      f'expected 2xx, got {resp.status_code}: {resp.content!r}')

    def test_initiate_capa_alone_is_not_enough(self):
        """The CRUD gate still fires — initiate_capa layers on top of
        add_capa, doesn't replace it."""
        self._grant(self.initiate_capa)
        resp = self._post_capa()
        self.assertEqual(resp.status_code, 403,
                         f'expected 403, got {resp.status_code}: {resp.content!r}')

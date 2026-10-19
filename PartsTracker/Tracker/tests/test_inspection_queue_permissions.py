"""The inspection queues are gated by role, not just by being logged in.

IncomingInspection and InspectionInbox declared `permission_classes = [IsAuthenticated]`,
which REPLACES the default stack (IsAuthenticated + TenantAccessPermission +
TenantModelPermissions) rather than adding to it — so any logged-in account, a
customer's included, read supplier names, quarantined lots and FPI records. They're
plain ViewSets with no queryset, so the CRUD gate has no model to name; the gate is
`action_permissions`. Tenant isolation was never affected (.objects auto-scopes).
"""
from django.contrib.auth.models import Permission

from Tracker.models import TenantGroup, User, UserRole
from Tracker.tests.base import TenantTestCase

STAFF_PERMS = ('view_materiallot', 'view_outsideprocessshipment', 'view_fpirecord',
               'view_stepexecution', 'view_qualityreports', 'full_tenant_access')
CUSTOMER_PERMS = ('view_qualityreports',)  # what the Customer preset holds of these

ENDPOINTS = ('/api/IncomingInspection/', '/api/InspectionInbox/',
             '/api/InspectionInbox/qa-signoffs/')


class InspectionQueuePermissionTests(TenantTestCase):

    def _user(self, name, codenames):
        user = User.objects.create_user(username=name, email=f'{name}@x.test',
                                        password='x', tenant=self.tenant_a)
        group = TenantGroup.objects.create(tenant=self.tenant_a, name=name, is_custom=True)
        group.permissions.add(*Permission.objects.filter(codename__in=codenames))
        UserRole.objects.create(user=user, group=group)
        user.clear_permission_cache(self.tenant_a)
        return user

    def test_a_customer_account_is_refused_every_queue(self):
        self.authenticate_as(self._user('cust', CUSTOMER_PERMS), self.tenant_a)
        for url in ENDPOINTS:
            r = self.client.get(url)
            self.assertEqual(r.status_code, 403, f'{url}: {r.status_code}')

    def test_staff_holding_the_views_reads_every_queue(self):
        self.authenticate_as(self._user('qa', STAFF_PERMS), self.tenant_a)
        for url in ENDPOINTS:
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200, f'{url}: {r.status_code} {r.content[:200]}')

    def test_the_incoming_queue_needs_only_the_lot_and_shipment_views(self):
        """Receiving reads the incoming queue; it shouldn't need QA's FPI view."""
        self.authenticate_as(
            self._user('recv', ('view_materiallot', 'view_outsideprocessshipment',
                                'full_tenant_access')), self.tenant_a)
        self.assertEqual(self.client.get('/api/IncomingInspection/').status_code, 200)
        self.assertEqual(self.client.get('/api/InspectionInbox/').status_code, 403)

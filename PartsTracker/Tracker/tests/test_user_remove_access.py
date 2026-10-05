"""Removing a user from a tenant (2026-10-05) suspends their membership there — it
never deletes the account. A hard delete took their approval signatures, training
records and every other tenant's membership with it (CASCADE)."""
from datetime import date

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from Tracker.utils.tenant_context import reset_current_tenant, set_current_tenant_id

User = get_user_model()


class RemoveUserAccessTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        from Tracker.models import Tenant, TrainingRecord, TrainingType
        cls.tenant = Tenant.objects.create(name="Remove", slug="remove-user-1005")
        token = set_current_tenant_id(cls.tenant.id)
        try:
            cls.admin = User.objects.create_user(username="ru-admin", email="ru-admin@x.test",
                                                 password="x", tenant=cls.tenant, is_staff=True)
            cls.admin.is_superuser = True
            cls.admin.save(update_fields=["is_superuser"])
            cls.kim = User.objects.create_user(username="ru-kim", email="ru-kim@x.test",
                                               password="x", tenant=cls.tenant)
            tt = TrainingType.objects.create(tenant=cls.tenant, name="Torque")
            cls.record = TrainingRecord.objects.create(
                tenant=cls.tenant, user=cls.kim, training_type=tt, completed_date=date(2026, 9, 1))
        finally:
            reset_current_tenant(token)

    def setUp(self):
        self.client.force_authenticate(user=self.admin)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        self._token = set_current_tenant_id(self.tenant.id)

    def tearDown(self):
        reset_current_tenant(self._token)

    def test_removing_a_user_suspends_them_and_keeps_their_records(self):
        from Tracker.models import TenantMembership, TrainingRecord
        resp = self.client.delete(f"/api/User/{self.kim.id}/")
        self.assertIn(resp.status_code, (200, 204), resp.content)
        self.assertTrue(User.objects.filter(pk=self.kim.id).exists())
        self.assertTrue(TrainingRecord.objects.filter(pk=self.record.id).exists())
        membership = TenantMembership.objects.get(user=self.kim, tenant=self.tenant)
        self.assertEqual(membership.status, TenantMembership.Status.SUSPENDED)

    def test_you_cant_remove_yourself(self):
        self.assertEqual(self.client.delete(f"/api/User/{self.admin.id}/").status_code, 400)

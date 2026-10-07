"""The bulk part actions, exercised over HTTP rather than through the service.

These three endpoints were silently no-ops for every API caller: ids arrive from JSON
as **strings**, `_load_parts_scoped` keyed its result by **UUID**, and so every lookup
missed. Django coerces either form for the `id__in` query, so the rows were always
fetched — they just could never be found again, and the actions answered HTTP 200 with
`{"ok": false, "error": "Part not found"}` for parts that plainly existed.

Nothing caught it because every existing test calls the services directly with
`part.id` (an ORM `UUID`), which is the one input shape that worked. The bug lived
entirely at the HTTP boundary, so these tests live there too.
"""
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from Tracker.utils.tenant_context import reset_current_tenant, set_current_tenant_id

User = get_user_model()


class BulkPartActionsApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth.models import Permission
        from Tracker.models import (
            Companies, Orders, OrdersStatus, Parts, PartsStatus, Tenant, TenantGroup, UserRole,
        )
        cls.tenant = Tenant.objects.create(name="Bulk", slug="bulk-part-actions")
        token = set_current_tenant_id(cls.tenant.id)
        try:
            cls.user = User.objects.create_user(
                username="bulk-op", email="op@bulk.test", password="x", tenant=cls.tenant)
            # A supervisor who may act on parts — the bulk bar's audience. Granted
            # explicitly rather than via superuser, so these tests still exercise the
            # real permission path (POST on a Parts action → add/change_parts).
            group = TenantGroup.objects.create(
                tenant=cls.tenant, name="BulkOps", description="bulk action tests",
                is_custom=True)
            group.permissions.add(*Permission.objects.filter(
                codename__in=["view_parts", "add_parts", "change_parts"]))
            UserRole.objects.create(user=cls.user, group=group)
            cls.company = Companies.objects.create(tenant=cls.tenant, name="Acme")
            cls.order = Orders.objects.create(
                tenant=cls.tenant, name="ORD-BULK", company=cls.company,
                order_status=OrdersStatus.IN_PROGRESS)
            cls.part = Parts.objects.create(
                tenant=cls.tenant, ERP_id="P-BULK-1", work_order=None, order=cls.order,
                part_status=PartsStatus.IN_PROGRESS)
        finally:
            reset_current_tenant(token)

    def setUp(self):
        from django.core.cache import cache
        cache.delete(f"user_{self.user.id}_tenant_{self.tenant.id}_perms")
        self.client.force_authenticate(user=self.user)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        self._token = set_current_tenant_id(self.tenant.id)

    def tearDown(self):
        reset_current_tenant(self._token)

    def test_bulk_set_status_finds_the_part_when_the_id_arrives_as_a_string(self):
        """The regression: a string id must resolve to the part, not 'Part not found'."""
        from Tracker.models import PartsStatus

        res = self.client.post(
            "/api/Parts/bulk_set_status/",
            {"ids": [str(self.part.id)], "status": PartsStatus.QUARANTINED},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        [row] = res.json()["results"]
        self.assertTrue(row["ok"], f"expected the part to be found, got {row!r}")
        self.assertNotIn("error", row)

        # The point of the endpoint: it actually wrote.
        self.part.refresh_from_db()
        self.assertEqual(self.part.part_status, PartsStatus.QUARANTINED)

    def test_a_genuinely_absent_id_still_reports_part_not_found(self):
        """The error path must survive the fix — a real miss still reads as a miss."""
        import uuid

        res = self.client.post(
            "/api/Parts/bulk_set_status/",
            {"ids": [str(uuid.uuid4())], "status": "QUARANTINED"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        [row] = res.json()["results"]
        self.assertFalse(row["ok"])
        self.assertEqual(row["error"], "Part not found")

    def test_bulk_increment_resolves_a_string_id(self):
        """Shares `_load_parts_scoped`, so it shared the bug. It may legitimately fail to
        advance (no step/process here) — what must not happen is 'Part not found'."""
        res = self.client.post(
            "/api/Parts/bulk_increment/", {"ids": [str(self.part.id)]}, format="json")
        self.assertEqual(res.status_code, 200)
        [row] = res.json()["results"]
        self.assertNotEqual(row.get("error"), "Part not found")

    def test_bulk_rollback_resolves_a_string_id(self):
        """Same helper, same bug. Rollback may refuse on its own merits; it must not
        refuse because it couldn't find a part that exists."""
        res = self.client.post(
            "/api/Parts/bulk_rollback/", {"ids": [str(self.part.id)]}, format="json")
        self.assertEqual(res.status_code, 200)
        [row] = res.json()["results"]
        self.assertNotEqual(row.get("error"), "Part not found")

    def test_service_callers_passing_uuids_still_work(self):
        """The fix keys by `str(id)`; the in-process callers that pass ORM `UUID`s — and
        which were the only ones ever working — must keep working."""
        from Tracker.models import PartsStatus
        from Tracker.services.mes.parts import bulk_set_status

        [result] = bulk_set_status(
            tenant_id=self.tenant.id, part_ids=[self.part.id],
            new_status=PartsStatus.ON_HOLD, operator=self.user)
        self.assertTrue(result.ok, f"UUID caller regressed: {result.error!r}")

        self.part.refresh_from_db()
        self.assertEqual(self.part.part_status, PartsStatus.ON_HOLD)

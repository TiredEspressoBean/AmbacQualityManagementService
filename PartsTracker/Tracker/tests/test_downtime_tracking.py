"""`EquipmentType.track_downtime` — the per-type opt-out is enforced on the API.

Downtime cannot be raised against equipment whose type does not track it; equipment
with no type, and events against a work centre alone, are unaffected.
"""
from django.utils import timezone
from rest_framework.test import APITestCase

from Tracker.models import DowntimeEvent, Equipments, EquipmentType, Tenant, User
from Tracker.utils.tenant_context import reset_current_tenant, set_current_tenant_id


class TrackDowntimeTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name="Downtime shop", slug="downtime-shop")
        token = set_current_tenant_id(cls.tenant.id)
        try:
            cls.user = User.objects.create_user(
                username="downtime-admin", email="downtime@example.com", password="x",
                tenant=cls.tenant, is_staff=True)
            cls.user.is_superuser = True
            cls.user.save(update_fields=["is_superuser"])
            lathe = EquipmentType.objects.create(tenant=cls.tenant, name="CNC Lathe",
                                                 track_downtime=True)
            gauge = EquipmentType.objects.create(tenant=cls.tenant, name="Handheld Gauge",
                                                 track_downtime=False)
            cls.lathe_1 = Equipments.objects.create(tenant=cls.tenant, name="Lathe 1",
                                                    equipment_type=lathe)
            cls.caliper = Equipments.objects.create(tenant=cls.tenant, name="Caliper 7",
                                                    equipment_type=gauge)
            cls.untyped = Equipments.objects.create(tenant=cls.tenant, name="Old press",
                                                    equipment_type=None)
        finally:
            reset_current_tenant(token)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        self._token = set_current_tenant_id(self.tenant.id)

    def tearDown(self):
        reset_current_tenant(self._token)

    def _raise(self, equipment):
        return self.client.post("/api/DowntimeEvents/", {
            "equipment": str(equipment.id), "category": "UNPLANNED",
            "reason": "Stopped", "start_time": timezone.now().isoformat(),
        }, format="json")

    def test_a_tracked_type_takes_downtime(self):
        r = self._raise(self.lathe_1)
        self.assertEqual(r.status_code, 201, r.content)

    def test_an_untracked_type_is_refused(self):
        r = self._raise(self.caliper)
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("does not track downtime", str(r.json()["equipment"]))
        self.assertFalse(DowntimeEvent.objects.filter(equipment=self.caliper).exists())

    def test_equipment_with_no_type_takes_downtime(self):
        r = self._raise(self.untyped)
        self.assertEqual(r.status_code, 201, r.content)

    def test_an_edit_cannot_move_an_event_onto_untracked_equipment(self):
        event_id = self._raise(self.lathe_1).json()["id"]
        r = self.client.patch(f"/api/DowntimeEvents/{event_id}/",
                              {"equipment": str(self.caliper.id)}, format="json")
        self.assertEqual(r.status_code, 400, r.content)


class DowntimeSummaryTests(APITestCase):
    """The downtime Pareto: lost hours by category and machine, clipped to the period,
    with an open event counting up to now."""

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name="Pareto shop", slug="pareto-shop")
        token = set_current_tenant_id(cls.tenant.id)
        try:
            cls.user = User.objects.create_user(
                username="pareto-admin", email="pareto@example.com", password="x",
                tenant=cls.tenant, is_staff=True)
            cls.user.is_superuser = True
            cls.user.save(update_fields=["is_superuser"])
            lathe = EquipmentType.objects.create(tenant=cls.tenant, name="Lathe")
            cls.l1 = Equipments.objects.create(tenant=cls.tenant, name="Lathe 1", equipment_type=lathe)
            cls.l2 = Equipments.objects.create(tenant=cls.tenant, name="Lathe 2", equipment_type=lathe)
            now = timezone.now()
            hours = timezone.timedelta(hours=1)

            def ev(eq, cat, start, end):
                DowntimeEvent.objects.create(
                    tenant=cls.tenant, equipment=eq, category=cat, reason="x",
                    start_time=start, end_time=end, reported_by=cls.user)
            ev(cls.l1, "UNPLANNED", now - 5 * hours, now - 2 * hours)          # 3 h
            ev(cls.l1, "CHANGEOVER", now - 10 * hours, now - 9 * hours)         # 1 h
            ev(cls.l2, "UNPLANNED", now - 1 * hours, None)                      # open: ~1 h
            # Started 40 days ago, ended 29 days ago: only its last day is in a 30-day window.
            ev(cls.l2, "PLANNED", now - timezone.timedelta(days=40), now - timezone.timedelta(days=29))
        finally:
            reset_current_tenant(token)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        self._token = set_current_tenant_id(self.tenant.id)

    def tearDown(self):
        reset_current_tenant(self._token)

    def test_hours_by_category_and_machine_largest_first(self):
        r = self.client.get("/api/DowntimeEvents/summary/?days=30")
        self.assertEqual(r.status_code, 200, r.content)
        body = r.json()
        cats = {c["key"]: c for c in body["by_category"]}
        self.assertAlmostEqual(cats["UNPLANNED"]["hours"], 4.0, delta=0.05)  # 3 + open ~1
        self.assertAlmostEqual(cats["CHANGEOVER"]["hours"], 1.0, delta=0.01)
        self.assertAlmostEqual(cats["PLANNED"]["hours"], 24.0, delta=0.05)    # clipped to 1 day
        self.assertEqual([c["key"] for c in body["by_category"]],
                         ["PLANNED", "UNPLANNED", "CHANGEOVER"])
        self.assertEqual(body["open_events"], 1)
        machines = {m["label"]: m for m in body["by_equipment"]}
        self.assertAlmostEqual(machines["Lathe 1"]["hours"], 4.0, delta=0.01)
        self.assertEqual(machines["Lathe 2"]["events"], 2)

    def test_a_shorter_period_drops_older_events(self):
        body = self.client.get("/api/DowntimeEvents/summary/?days=1").json()
        self.assertNotIn("PLANNED", [c["key"] for c in body["by_category"]])
        self.assertEqual(body["total_events"], 3)

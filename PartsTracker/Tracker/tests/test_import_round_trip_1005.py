"""An exported file imports back unchanged (2026-10-05), found by uploading a filled
master workbook in the browser: calendar times shifted by the plant's UTC offset, FKs
an importer had no lookup for failed, and matched-but-unchanged rows were counted as
updates."""
import io
from datetime import datetime, timezone as dt_tz

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from Tracker.utils.tenant_context import reset_current_tenant, set_current_tenant_id

User = get_user_model()


class ImportRoundTripTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        from Tracker.models import Tenant
        cls.tenant = Tenant.objects.create(name="Round trip", slug="round-trip-1005",
                                           default_timezone="America/New_York")
        token = set_current_tenant_id(cls.tenant.id)
        try:
            cls.admin = User.objects.create_user(username="rt-admin", email="rt-admin@x.test",
                                                 password="x", tenant=cls.tenant, is_staff=True)
            cls.admin.is_superuser = True
            cls.admin.save(update_fields=["is_superuser"])
        finally:
            reset_current_tenant(token)

    def setUp(self):
        self.client.force_authenticate(user=self.admin)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        self._token = set_current_tenant_id(self.tenant.id)

    def tearDown(self):
        reset_current_tenant(self._token)

    def _import(self, endpoint, csv_text):
        f = io.BytesIO(csv_text.encode("utf-8"))
        f.name = "rows.csv"
        resp = self.client.post(f"/api/{endpoint}/import/", {"file": f, "mode": "upsert"},
                                format="multipart")
        self.assertEqual(resp.status_code, 207, resp.content)
        return resp.json()

    def test_a_closure_time_is_read_on_the_plants_clock(self):
        from Tracker.models import PlantCalendarException
        self._import("PlantCalendarExceptions",
                     "name,kind,start_time,end_time\nLabor Day,HOLIDAY,2026-09-07 00:00:00,2026-09-07 23:59:00\n")
        closure = PlantCalendarException.objects.get(name="Labor Day")
        # Midnight in New York is 04:00 UTC — not midnight UTC (8 pm the day before).
        self.assertEqual(closure.start_time, datetime(2026, 9, 7, 4, 0, tzinfo=dt_tz.utc))

    def test_an_unchanged_row_is_no_change_not_an_update(self):
        from Tracker.models import Companies
        Companies.objects.create(tenant=self.tenant, name="Acme", description="x")
        body = self._import("Companies", "name,description\nAcme,x\n")
        self.assertEqual((body["summary"]["updated"], body["summary"]["unchanged"]), (0, 1), body)

    def test_an_fk_the_importer_has_no_lookup_for_is_read_by_id(self):
        # A part type's disassembly process: the part-type importer has no lookup for it,
        # so an exported ID used to reach the model as text and fail.
        from Tracker.models import PartTypes, Processes
        pump = PartTypes.objects.create(tenant=self.tenant, name="Pump")
        process = Processes.objects.create(tenant=self.tenant, name="Teardown", part_type=pump)
        body = self._import("PartTypes", f"name,default_disassembly_process\nPump,{process.id}\n")
        self.assertEqual(body["summary"]["errors"], 0, body)
        # The disassembly process is part of the part's definition, so setting it versions
        # the part: the current version carries it.
        current = PartTypes.objects.get(name="Pump", is_current_version=True)
        self.assertEqual(current.default_disassembly_process_id, process.id)

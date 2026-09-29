"""Go-live history: training records and material lots loaded as a migration batch
(Tracker/services/core/migration_import.py)."""
import io
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from Tracker.utils.tenant_context import reset_current_tenant, set_current_tenant_id

User = get_user_model()


class MigrationImportTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        from Tracker.models import Companies, Material, PartTypes, Tenant, TrainingType
        cls.tenant = Tenant.objects.create(name="Go-live", slug="go-live")
        token = set_current_tenant_id(cls.tenant.id)
        try:
            cls.loader = User.objects.create_user(username="loader", email="loader@x.test",
                                                  password="x", tenant=cls.tenant, is_staff=True)
            cls.checker = User.objects.create_user(username="checker", email="checker@x.test",
                                                   password="x", tenant=cls.tenant, is_staff=True)
            for u in (cls.loader, cls.checker):
                u.is_superuser = True
                u.save(update_fields=["is_superuser"])
            cls.operator = User.objects.create_user(username="op", email="op@x.test",
                                                    password="x", tenant=cls.tenant)
            cls.cmm = TrainingType.objects.create(tenant=cls.tenant, name="CMM Operation")
            cls.acme = Companies.objects.create(tenant=cls.tenant, name="Acme")
            cls.seal = Material.objects.create(tenant=cls.tenant, name="Seal", part_number="S-1")
            cls.bracket = PartTypes.objects.create(tenant=cls.tenant, name="Bracket")
        finally:
            reset_current_tenant(token)

    def setUp(self):
        self.client.force_authenticate(user=self.loader)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        self._token = set_current_tenant_id(self.tenant.id)

    def tearDown(self):
        reset_current_tenant(self._token)

    def _load(self, kind, text, source="Legacy HR"):
        f = io.BytesIO(text.encode("utf-8"))
        f.name = "history.csv"
        r = self.client.post("/api/MigrationBatches/import/",
                             {"file": f, "kind": kind, "source_system": source},
                             format="multipart")
        self.assertEqual(r.status_code, 207, r.content[:1000])
        return r.json()

    def test_training_history_loads_and_qualifies_straight_away(self):
        from Tracker.models import TrainingRecord
        body = self._load("TRAINING_RECORDS",
                          "user,training_type,completed_date,source_reference\n"
                          f"op@x.test,CMM Operation,{date.today() - timedelta(days=30)},HR cert #4471\n")
        self.assertEqual(body["summary"]["created"], 1, body)
        rec = TrainingRecord.objects.get(user=self.operator)
        self.assertEqual(rec.source_reference, "HR cert #4471")
        self.assertEqual(str(rec.migration_batch_id), body["batch"]["id"])
        self.assertEqual(body["batch"]["row_count"], 1)

    def test_training_history_must_name_its_source(self):
        body = self._load("TRAINING_RECORDS", "user,training_type,completed_date\n"
                                              f"op@x.test,CMM Operation,{date.today()}\n")
        self.assertEqual(body["summary"]["errors"], 1, body)
        self.assertIn("source_reference", str(body["results"]))

    def test_the_same_training_twice_is_refused(self):
        row = f"op@x.test,CMM Operation,{date.today()},HR #1\n"
        self._load("TRAINING_RECORDS", "user,training_type,completed_date,source_reference\n" + row)
        body = self._load("TRAINING_RECORDS",
                          "user,training_type,completed_date,source_reference\n" + row)
        self.assertEqual(body["summary"]["errors"], 1, body)

    def test_traceable_stock_is_accepted_and_untraceable_is_quarantined(self):
        from Tracker.models import MaterialLot
        body = self._load("MATERIAL_LOTS",
                          "lot_number,material,supplier,supplier_lot_number,quantity\n"
                          "L-1,Seal,Acme,ACME-778,40\n"
                          "L-2,Seal,Acme,,10\n", source="Old ERP")
        self.assertEqual(body["summary"]["created"], 2, body)
        self.assertEqual(MaterialLot.objects.get(lot_number="L-1").status, "ACCEPTED")
        held = MaterialLot.objects.get(lot_number="L-2")
        self.assertEqual(held.status, "QUARANTINE")
        self.assertEqual(held.hold_reason, "MIGRATED_UNTRACEABLE")
        self.assertIn("supplier lot number or certificate", str(body["results"]))
        self.assertEqual(held.received_by_id, self.loader.id)

    def test_a_lot_number_already_here_is_refused(self):
        self._load("MATERIAL_LOTS", "lot_number,material,quantity,source_reference\nL-9,Seal,5,C#1\n")
        body = self._load("MATERIAL_LOTS",
                          "lot_number,material,quantity,source_reference\nL-9,Seal,5,C#1\n")
        self.assertEqual(body["summary"]["errors"], 1, body)

    def test_a_batch_is_verified_once_by_someone_else(self):
        body = self._load("TRAINING_RECORDS",
                          "user,training_type,completed_date,source_reference\n"
                          f"op@x.test,CMM Operation,{date.today()},HR #2\n")
        url = f"/api/MigrationBatches/{body['batch']['id']}/verify/"
        self.assertEqual(self.client.post(url, {}, format="json").status_code, 400)  # the loader
        self.client.force_authenticate(user=self.checker)
        r = self.client.post(url, {"notes": "Sampled 10 of 10"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(r.json()["is_verified"])
        self.assertEqual(self.client.post(url, {}, format="json").status_code, 400)  # only once

    def test_a_batch_names_its_source_system(self):
        f = io.BytesIO(b"user,training_type,completed_date,source_reference\n")
        f.name = "h.csv"
        r = self.client.post("/api/MigrationBatches/import/",
                             {"file": f, "kind": "TRAINING_RECORDS", "source_system": ""},
                             format="multipart")
        self.assertEqual(r.status_code, 400, r.content)

    def test_the_template_lists_the_columns(self):
        r = self.client.get("/api/MigrationBatches/template/?kind=MATERIAL_LOTS")
        self.assertEqual(r.status_code, 200)
        self.assertIn("lot_number", r.content.decode("utf-8-sig"))

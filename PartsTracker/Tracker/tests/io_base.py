"""Shared base for spreadsheet import/export tests.

Every model with import and export gets, at least:

- a create from a small hand-written CSV (the columns a person would type),
- a refused row (a reference that names nothing, or an ambiguous one),
- `assert_round_trips()`: export the model, import that file unchanged, and require
  0 errors, 0 creates and NO change to any row — which is what proves the export
  writes every column in a form the import reads back.

See test_io_examples.py for the two worked examples (Material, Fixture).
"""
import io
import json

from rest_framework.test import APITestCase

from Tracker.models import Tenant, User
from Tracker.utils.tenant_context import reset_current_tenant, set_current_tenant_id


class ImportExportTestCase(APITestCase):
    """A tenant, a superuser signed in to it, and helpers over the real endpoints."""

    endpoint = None  # e.g. "Materials" — the router prefix
    tenant_slug = None  # unique per test class

    @classmethod
    def setUpTestData(cls):
        slug = cls.tenant_slug or cls.__name__.lower()
        cls.tenant = Tenant.objects.create(name=f"{slug} shop", slug=slug)
        token = set_current_tenant_id(cls.tenant.id)
        try:
            cls.user = User.objects.create_user(
                username=f"{slug}-admin", email=f"{slug}@example.com", password="x",
                tenant=cls.tenant, is_staff=True)
            cls.user.is_superuser = True
            cls.user.save(update_fields=["is_superuser"])
            cls.build_fixtures()
        finally:
            reset_current_tenant(token)

    @classmethod
    def build_fixtures(cls):
        """Create the rows the tests need (tenant context is set)."""

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        self._token = set_current_tenant_id(self.tenant.id)

    def tearDown(self):
        reset_current_tenant(self._token)

    # --- endpoints --------------------------------------------------------------------

    def import_csv(self, content: str, mode: str = "upsert", mapping=None):
        """POST a CSV to /import/ and return the parsed JSON body."""
        return self.import_file(content.encode("utf-8"), "import.csv", mode, mapping)

    def import_file(self, content: bytes, name: str, mode: str = "upsert", mapping=None):
        f = io.BytesIO(content)
        f.name = name
        data = {"file": f, "mode": mode}
        if mapping is not None:
            data["column_mapping"] = json.dumps(mapping)
        r = self.client.post(f"/api/{self.endpoint}/import/", data, format="multipart")
        self.assertIn(r.status_code, (200, 207), r.content[:2000])
        return r.json()

    def export(self, fmt: str = "xlsx") -> bytes:
        r = self.client.get(f"/api/{self.endpoint}/export/{fmt}/")
        self.assertEqual(r.status_code, 200, r.content[:2000])
        return r.content

    # --- assertions -------------------------------------------------------------------

    def assert_row_errors(self, body, n=1, mentions=None):
        self.assertEqual(body["summary"]["errors"], n, body)
        if mentions:
            self.assertIn(mentions, json.dumps(body["results"]), body)

    def snapshot(self, model):
        """Every row of `model` in this tenant: its column values and M2M sets."""
        rows = {}
        for obj in model.objects.all():  # tenant-safe: .objects auto-scopes to the tenant set in setUp
            values = {f.attname: getattr(obj, f.attname) for f in model._meta.concrete_fields
                      if f.name not in ("updated_at",)}
            for m2m in model._meta.many_to_many:
                values[m2m.name] = sorted(str(pk) for pk in
                                          getattr(obj, m2m.name).values_list("pk", flat=True))
            rows[obj.pk] = values
        return rows

    def assert_round_trips(self, model, fmt: str = "xlsx"):
        """Export → import that file unchanged → nothing changes."""
        self.maxDiff = None
        before = self.snapshot(model)
        self.assertTrue(before, "round trip needs at least one row to export")
        body = self.import_file(self.export(fmt), f"export.{fmt}", mode="update")
        self.assertEqual(body["summary"]["errors"], 0, body)
        self.assertEqual(body["summary"]["created"], 0, body)
        # A versioned model exports its current versions only.
        exported = len(before)
        if getattr(model, "_is_versioned", False):
            exported = sum(1 for row in before.values() if row.get("is_current_version"))
        self.assertEqual(body["summary"]["updated"], exported, body)
        self.assertEqual(self.snapshot(model), before)

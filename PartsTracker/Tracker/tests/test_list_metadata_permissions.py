"""`/metadata/` reports each model's permission codenames.

The editor list shell uses these to hide New/Edit/Delete buttons a user's role can't
act on. The point of deriving them server-side from `model._meta.model_name` — rather
than mapping them in the frontend — is that they cannot drift from what
`TenantModelPermissions` actually enforces: both read the same model name.

So the test that matters is the correspondence one: whatever the endpoint advertises
must be a codename that really exists for that model.
"""
from django.contrib.auth.models import Permission

from Tracker.tests.base import TenantTestCase


class ListMetadataPermissionsTests(TenantTestCase):
    # A few list endpoints across the app's areas, with the model each is backed by.
    ENDPOINTS = [
        ("/api/WorkOrders/metadata/", "workorder"),
        ("/api/Parts/metadata/", "parts"),
        ("/api/Equipment/metadata/", "equipments"),
    ]

    def test_metadata_advertises_the_four_codenames_for_its_model(self):
        self.authenticate_superuser(self.tenant_a)
        for url, model_name in self.ENDPOINTS:
            with self.subTest(url=url):
                r = self.client.get(url)
                self.assertEqual(r.status_code, 200)
                perms = r.data["permissions"]
                self.assertEqual(perms, {
                    "add": f"add_{model_name}",
                    "change": f"change_{model_name}",
                    "delete": f"delete_{model_name}",
                    "view": f"view_{model_name}",
                })

    def test_advertised_codenames_actually_exist(self):
        """The whole point of deriving these from the model: a codename the UI gates
        on must be a real permission, or the gate silently hides the button forever."""
        self.authenticate_superuser(self.tenant_a)
        for url, _ in self.ENDPOINTS:
            with self.subTest(url=url):
                perms = self.client.get(url).data["permissions"]
                for codename in perms.values():
                    self.assertTrue(
                        Permission.objects.filter(codename=codename).exists(),
                        f"{codename} is advertised by {url} but no such permission exists",
                    )

    def test_metadata_still_serves_its_original_payload(self):
        """Permissions are an addition — the search/filter/ordering hints the shell
        already depends on must be untouched."""
        self.authenticate_superuser(self.tenant_a)
        r = self.client.get("/api/WorkOrders/metadata/")
        for key in ("search_fields", "search_fields_display", "ordering_fields",
                    "ordering_fields_display", "filterset_fields", "filters"):
            self.assertIn(key, r.data)

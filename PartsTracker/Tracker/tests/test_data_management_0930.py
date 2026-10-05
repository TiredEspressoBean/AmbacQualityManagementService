"""API fixes made building the Data Management section (2026-09-30)."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from Tracker.utils.tenant_context import reset_current_tenant, set_current_tenant_id

User = get_user_model()


class DataManagementApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        from Tracker.models import LifeLimitDefinition, PartTypes, Tenant
        cls.tenant = Tenant.objects.create(name="Data management", slug="data-management-0930")
        token = set_current_tenant_id(cls.tenant.id)
        try:
            cls.user = User.objects.create_user(username="dm", email="dm@x.test", password="x",
                                                tenant=cls.tenant, is_staff=True)
            cls.user.is_superuser = True
            cls.user.save(update_fields=["is_superuser"])
            cls.core = PartTypes.objects.create(tenant=cls.tenant, name="Injector core")
            cls.nozzle = PartTypes.objects.create(tenant=cls.tenant, name="Nozzle")
            cls.cycles = LifeLimitDefinition.objects.create(
                tenant=cls.tenant, name="Cycles", unit="cycles", unit_label="Cycles",
                hard_limit=Decimal(1000))
        finally:
            reset_current_tenant(token)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        self._token = set_current_tenant_id(self.tenant.id)

    def tearDown(self):
        reset_current_tenant(self._token)

    def test_a_removed_teardown_line_can_be_added_again(self):
        """The (core, component) key stayed on the archived line, so the part type
        form's teardown panel could never add a removed component back."""
        from Tracker.models import DisassemblyBOMLine
        url = "/api/DisassemblyBOMLines/"
        body = {"core_type": str(self.core.id), "component_type": str(self.nozzle.id),
                "expected_qty": 4, "expected_fallout_rate": "0.10", "line_number": 1}
        first = self.client.post(url, body, format="json")
        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(self.client.delete(f"{url}{first.json()['id']}/").status_code, 204)

        again = self.client.post(url, {**body, "expected_qty": 2}, format="json")
        self.assertEqual(again.status_code, 201, again.content)
        live = DisassemblyBOMLine.objects.filter(
            core_type=self.core, component_type=self.nozzle, archived=False, is_current_version=True)
        self.assertEqual(live.count(), 1)
        self.assertEqual(live.get().expected_qty, 2)

    def test_the_definitions_list_is_current_versions_only(self):
        """Each revision is a row; the list showed one per revision, so a definition
        edited twice appeared three times in the list and the part type picker."""
        url = "/api/LifeLimitDefinitions/"
        edit = self.client.patch(f"{url}{self.cycles.id}/", {"hard_limit": "1200"}, format="json")
        self.assertEqual(edit.status_code, 200, edit.content)
        rows = self.client.get(url).json()["results"]
        self.assertEqual([r["name"] for r in rows], ["Cycles"])
        self.assertEqual(Decimal(rows[0]["hard_limit"]), Decimal(1200))

    def test_shifts_and_definitions_describe_their_lists(self):
        for url in ("/api/Shifts/metadata/", "/api/LifeLimitDefinitions/metadata/"):
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200, (url, resp.content))
            self.assertIn("ordering_fields", resp.json())

    def test_a_milestone_template_can_be_renamed_and_made_the_default(self):
        """Every content edit needed a change description the API had no field for, so
        the milestones page couldn't rename a template; flipping the default versioned it."""
        from Tracker.models import MilestoneTemplate
        url = "/api/MilestoneTemplates/"
        made = self.client.post(url, {"name": "Standard"}, format="json")
        self.assertEqual(made.status_code, 201, made.content)
        tid = made.json()["id"]

        renamed = self.client.patch(f"{url}{tid}/", {"name": "Standard repair"}, format="json")
        self.assertEqual(renamed.status_code, 200, renamed.content)
        current = MilestoneTemplate.objects.get(pk=renamed.json()["id"])
        self.assertEqual(current.name, "Standard repair")
        self.assertEqual(current.version, 2)

        flipped = self.client.patch(f"{url}{current.id}/", {"is_default": True}, format="json")
        self.assertEqual(flipped.status_code, 200, flipped.content)
        self.assertEqual(flipped.json()["id"], str(current.id))  # a setting, not a new revision
        self.assertTrue(MilestoneTemplate.objects.get(pk=current.id).is_default)
        listed = self.client.get(url).json()
        self.assertEqual([t["name"] for t in listed], ["Standard repair"])  # not one per revision

    def test_a_step_names_the_processes_that_share_it(self):
        """Editors send a step's content edits to its process; they find the process here."""
        from Tracker.models import Processes, ProcessStep, Steps
        proc = Processes.objects.create(tenant=self.tenant, name="Injector reman", part_type=self.core)
        copy = Processes.objects.create(tenant=self.tenant, name="Injector reman copy", part_type=self.core)
        step = Steps.objects.create(tenant=self.tenant, name="Flow test", part_type=self.core)
        ProcessStep.objects.create(process=proc, step=step, order=1)
        ProcessStep.objects.create(process=copy, step=step, order=1)
        loose = Steps.objects.create(tenant=self.tenant, name="Loose", part_type=self.core)

        shared = self.client.get(f"/api/Steps/{step.id}/").json()["processes"]
        self.assertEqual(sorted(p["name"] for p in shared), ["Injector reman", "Injector reman copy"])
        self.assertEqual(self.client.get(f"/api/Steps/{loose.id}/").json()["processes"], [])

    def test_version_history_lists_every_revision_oldest_first(self):
        url = "/api/LifeLimitDefinitions/"
        v2 = self.client.patch(f"{url}{self.cycles.id}/",
                               {"hard_limit": "1500", "change_description": "Supplier data"}, format="json").json()
        chain = self.client.get(f"{url}{v2['id']}/version-history/").json()
        self.assertEqual([(r["version"], r["is_current_version"]) for r in chain], [(1, False), (2, True)])

    def test_an_archived_setup_row_shows_as_archived_and_can_be_restored(self):
        """The list page restores a deleted row by PATCHing `archived` — which the
        serializer has to expose, and the detail route has to reach."""
        from Tracker.models import Equipments, Steps
        step = Steps.objects.create(tenant=self.tenant, name="Grind", part_type=self.core)
        machine = Equipments.objects.create(tenant=self.tenant, name="Grinder")
        url = "/api/StepEquipmentAffinities/"
        made = self.client.post(url, {"step": str(step.id), "equipment": str(machine.id)}, format="json")
        self.assertEqual(made.status_code, 201, made.content)
        aid = made.json()["id"]
        self.assertEqual(self.client.delete(f"{url}{aid}/").status_code, 204)

        listed = self.client.get(f"{url}?include_archived=true").json()["results"]
        self.assertEqual([(r["id"], r["archived"]) for r in listed], [(aid, True)])
        back = self.client.patch(f"{url}{aid}/?include_archived=true", {"archived": False}, format="json")
        self.assertEqual(back.status_code, 200, back.content)
        self.assertEqual([r["id"] for r in self.client.get(url).json()["results"]], [aid])

    def test_receiving_an_expected_lot_records_where_it_went(self):
        from datetime import date, timedelta
        from Tracker.models import Material, MaterialLot
        from Tracker.services.mes.locations import seed_location
        from Tracker.services.mes.material_lot import record_expected_receipt
        seed_location(self.tenant, "Rack 4")
        lot = record_expected_receipt(tenant=self.tenant, material=Material.objects.create(tenant=self.tenant, name="Seal"),
                                      quantity=Decimal(10), promised_date=date.today() + timedelta(days=3))
        resp = self.client.post(f"/api/MaterialLots/{lot.id}/receive/",
                                {"lot_number": "SUP-9", "storage_location": " Rack 4 "}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(MaterialLot.objects.get(pk=lot.pk).storage_location, "Rack 4")

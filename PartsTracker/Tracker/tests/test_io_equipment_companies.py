"""Import/export for Equipment, Equipment types and Companies.

All three are versioned, and their API edits route through `apply_versioned_update`:
a content edit makes a new version, an edit limited to the serializer's
non-versioning fields (archive, an equipment's status and scheduling toggles, a
company's commercial defaults) saves in place. The import does the same — see
`VersionedLikeTheAPIImport` in Tracker/viewsets/core.py.
"""
import datetime

from Tracker.tests.io_base import ImportExportTestCase


class EquipmentImportExportTests(ImportExportTestCase):
    endpoint = "Equipment"
    tenant_slug = "io-equipment"

    @classmethod
    def build_fixtures(cls):
        from Tracker.models import Equipments, EquipmentType, Shift, StorageLocation
        cls.mill = EquipmentType.objects.create(tenant=cls.tenant, name="CNC Mill")
        # A machine's location is a record; an import names one that exists.
        cls.locs = {n: StorageLocation.objects.create(tenant=cls.tenant, name=n)
                    for n in ("Machine Shop", "Bay 7", "Tool Crib")}
        cls.day = Shift.objects.create(tenant=cls.tenant, name="Day", code="DAY",
                                       start_time=datetime.time(6), end_time=datetime.time(14))
        cls.vf2 = Equipments.objects.create(
            tenant=cls.tenant, name="Haas VF-2", serial_number="SN-100",
            equipment_type=cls.mill, location=cls.locs["Machine Shop"], manufacturer="Haas",
            model_number="VF-2", is_schedulable=True, runs_unattended=False,
            batch_capacity=1, notes="Bay 3")
        # Not in the API, so neither imported nor exported: the round trip must leave it.
        cls.vf2.operating_shifts.set([cls.day])
        Equipments.objects.create(tenant=cls.tenant, name="Caliper", equipment_type=None)

    def test_a_typed_csv_creates_equipment(self):
        from Tracker.models import Equipments
        body = self.import_csv(
            "name,serial_number,equipment_type,location\n"
            "Haas VF-4,SN-300,CNC Mill,Machine Shop\n", mode="create")
        self.assertEqual(body["summary"]["created"], 1, body)
        eq = Equipments.objects.get(serial_number="SN-300")
        self.assertEqual(eq.equipment_type_id, self.mill.id)

    def test_a_row_is_matched_on_its_serial_number_and_a_content_edit_versions(self):
        from Tracker.models import Equipments
        body = self.import_csv("serial_number,location\nSN-100,Bay 7\n", mode="update")
        self.assertEqual(body["summary"]["updated"], 1, body)
        current = Equipments.objects.get(serial_number="SN-100", is_current_version=True)
        self.assertEqual(current.location.name, "Bay 7")
        self.assertEqual(current.version, 2)
        self.vf2.refresh_from_db()
        self.assertFalse(self.vf2.is_current_version)
        self.assertEqual(self.vf2.location.name, "Machine Shop")

    def test_a_status_edit_saves_in_place(self):
        # status is operational, not content — the API saves it without a new version.
        from Tracker.models import Equipments
        body = self.import_csv("serial_number,status\nSN-100,IN_MAINTENANCE\n", mode="update")
        self.assertEqual(body["summary"]["updated"], 1, body)
        self.vf2.refresh_from_db()
        self.assertEqual(self.vf2.status, "IN_MAINTENANCE")
        self.assertEqual(self.vf2.version, 1)
        self.assertTrue(self.vf2.is_current_version)
        self.assertEqual(Equipments.objects.filter(serial_number="SN-100").count(), 1)

    def test_a_row_without_a_serial_number_is_matched_on_its_name(self):
        body = self.import_csv("name,location\nCaliper,Tool Crib\n", mode="update")
        self.assertEqual(body["summary"]["updated"], 1, body)

    def test_a_type_that_names_nothing_is_refused(self):
        body = self.import_csv("name,equipment_type\nLathe 1,Lathe\n", mode="create")
        self.assert_row_errors(body, mentions="No Equipment Type matches")

    def test_an_export_imports_back_unchanged(self):
        from Tracker.models import Equipments
        self.assert_round_trips(Equipments)

    def test_a_csv_export_imports_back_unchanged(self):
        from Tracker.models import Equipments
        self.assert_round_trips(Equipments, fmt="csv")


class EquipmentTypeImportExportTests(ImportExportTestCase):
    endpoint = "Equipment-types"
    tenant_slug = "io-equipment-type"

    @classmethod
    def build_fixtures(cls):
        from Tracker.models import EquipmentType
        cls.cmm = EquipmentType.objects.create(
            tenant=cls.tenant, name="CMM", description="Coordinate measuring machine",
            requires_calibration=True, default_calibration_interval_days=365,
            is_portable=False, track_downtime=True)
        EquipmentType.objects.create(tenant=cls.tenant, name="Caliper", is_portable=True)

    def test_a_typed_csv_creates_equipment_types(self):
        from Tracker.models import EquipmentType
        body = self.import_csv(
            "name,requires_calibration,default_calibration_interval_days\n"
            "Torque wrench,yes,180\n", mode="create")
        self.assertEqual(body["summary"]["created"], 1, body)
        t = EquipmentType.objects.get(name="Torque wrench")
        self.assertTrue(t.requires_calibration)
        self.assertEqual(t.default_calibration_interval_days, 180)

    def test_a_row_is_matched_on_its_name_and_the_edit_versions(self):
        from Tracker.models import EquipmentType
        body = self.import_csv("name,default_calibration_interval_days\nCMM,180\n",
                               mode="update")
        self.assertEqual(body["summary"]["updated"], 1, body)
        current = EquipmentType.objects.get(name="CMM", is_current_version=True)
        self.assertEqual(current.default_calibration_interval_days, 180)
        self.assertEqual(current.version, 2)

    def test_a_create_of_an_existing_name_is_refused(self):
        body = self.import_csv("name\nCMM\n", mode="create")
        self.assert_row_errors(body, mentions="already exists")

    def test_an_export_imports_back_unchanged(self):
        from Tracker.models import EquipmentType
        self.assert_round_trips(EquipmentType)


class CompanyImportExportTests(ImportExportTestCase):
    endpoint = "Companies"
    tenant_slug = "io-company"

    @classmethod
    def build_fixtures(cls):
        from Tracker.models import Companies
        cls.parker = Companies.objects.create(
            tenant=cls.tenant, name="Parker Seals", description="O-ring supplier",
            hubspot_api_id="HS-1", default_outside_process_turnaround_days=10,
            default_core_fulfilment_mode="EXCHANGE")
        # Two current companies with one name: a name alone can't say which.
        Companies.objects.create(tenant=cls.tenant, name="Twin Co", description="East")
        Companies.objects.create(tenant=cls.tenant, name="Twin Co", description="West")

    def test_a_typed_csv_creates_companies(self):
        from Tracker.models import Companies
        body = self.import_csv("name,description\nAcme Castings,Foundry\n", mode="create")
        self.assertEqual(body["summary"]["created"], 1, body)
        self.assertEqual(Companies.objects.get(name="Acme Castings").description, "Foundry")

    def test_a_row_is_matched_on_its_name_and_a_content_edit_versions(self):
        from Tracker.models import Companies
        body = self.import_csv("name,description\nParker Seals,Seals and O-rings\n",
                               mode="update")
        self.assertEqual(body["summary"]["updated"], 1, body)
        current = Companies.objects.get(name="Parker Seals", is_current_version=True)
        self.assertEqual(current.description, "Seals and O-rings")
        self.assertEqual(current.version, 2)

    def test_a_turnaround_edit_saves_in_place(self):
        # A commercial default, not a qualification fact: the API doesn't version it.
        body = self.import_csv(
            "name,default_outside_process_turnaround_days\nParker Seals,14\n", mode="update")
        self.assertEqual(body["summary"]["updated"], 1, body)
        self.parker.refresh_from_db()
        self.assertEqual(self.parker.default_outside_process_turnaround_days, 14)
        self.assertEqual(self.parker.version, 1)

    def test_a_name_two_companies_share_is_refused(self):
        body = self.import_csv("name,description\nTwin Co,North\n", mode="update")
        self.assert_row_errors(body, mentions="more than one")

    def test_an_export_imports_back_unchanged(self):
        from Tracker.models import Companies
        self.assert_round_trips(Companies)

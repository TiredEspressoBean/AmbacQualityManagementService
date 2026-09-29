"""BOM import: one sheet of lines, the file replaces each BOM's lines, and an import only
ever makes a DRAFT (Tracker/services/mes/bom_import.py)."""
from decimal import Decimal

from Tracker.tests.io_base import ImportExportTestCase


class BomImportTests(ImportExportTestCase):
    endpoint = "BOMLines"
    tenant_slug = "io-bom"

    @classmethod
    def build_fixtures(cls):
        from Tracker.models import BOM, BOMLine, Material, PartTypes
        cls.injector = PartTypes.objects.create(tenant=cls.tenant, name="Injector")
        cls.nozzle = PartTypes.objects.create(tenant=cls.tenant, name="Nozzle")
        cls.oring = Material.objects.create(tenant=cls.tenant, name="O-ring", part_number="OR-1")
        cls.released = BOM.objects.create(tenant=cls.tenant, part_type=cls.injector,
                                          revision="A", bom_type="ASSEMBLY", status="RELEASED")
        BOMLine.objects.create(tenant=cls.tenant, bom=cls.released, component_type=cls.nozzle,
                               quantity=Decimal(1), source="MAKE", line_number=1)
        BOMLine.objects.create(tenant=cls.tenant, bom=cls.released, material=cls.oring,
                               quantity=Decimal(2), source="BUY", line_number=2)

    def _current(self, part_type):
        from Tracker.models import BOM
        return BOM.objects.get(part_type=part_type, is_current_version=True, archived=False)

    def test_a_changed_released_bom_becomes_a_new_draft_revision(self):
        body = self.import_csv(
            "part_type,revision,line_number,component_type,material,quantity,source\n"
            "Injector,B,1,Nozzle,,1,MAKE\n"
            "Injector,B,2,,O-ring,4,BUY\n")
        self.assertEqual(body["summary"]["errors"], 0, body)
        draft = self._current(self.injector)
        self.assertEqual((draft.status, draft.revision), ("DRAFT", "B"))
        self.assertEqual(draft.lines.filter(archived=False).count(), 2)
        self.assertEqual(draft.lines.get(material=self.oring, archived=False).quantity,
                         Decimal(4))
        self.released.refresh_from_db()
        self.assertEqual(self.released.status, "RELEASED")  # still in force until release
        self.assertEqual(self.released.lines.filter(archived=False).count(), 2)

    def test_replace_removes_lines_the_file_leaves_out(self):
        self.import_csv("part_type,revision,component_type,quantity,source\n"
                        "Injector,B,Nozzle,1,MAKE\n")
        self.assertEqual(self._current(self.injector).lines.filter(archived=False).count(), 1)

    def test_an_unchanged_file_changes_nothing(self):
        from Tracker.models import BOM
        body = self.import_csv(
            "part_type,revision,line_number,component_type,material,quantity,source\n"
            "Injector,A,1,Nozzle,,1,MAKE\n"
            "Injector,A,2,,O-ring,2,BUY\n")
        self.assertEqual(body["summary"]["errors"], 0, body)
        self.assertIn("No change", str(body["results"]))
        self.assertEqual(BOM.objects.filter(part_type=self.injector).count(), 1)

    def test_a_new_part_gets_a_new_draft_bom(self):
        from Tracker.models import PartTypes
        pump = PartTypes.objects.create(tenant=self.tenant, name="Pump")
        body = self.import_csv("part_type,revision,material,quantity\nPump,A,O-ring,6\n")
        self.assertEqual(body["summary"]["created"], 1, body)
        bom = self._current(pump)
        self.assertEqual((bom.status, bom.revision), ("DRAFT", "A"))

    def test_one_bad_line_fails_its_whole_bom_only(self):
        from Tracker.models import BOM, PartTypes
        pump = PartTypes.objects.create(tenant=self.tenant, name="Pump")
        body = self.import_csv(
            "part_type,revision,component_type,material,quantity\n"
            "Injector,B,Nozzle,,1\n"
            "Injector,B,Nothing Such,,1\n"
            "Pump,A,,O-ring,3\n")
        self.assertEqual(body["summary"]["errors"], 2, body)       # both Injector rows
        self.assertIn("Nothing Such", str(body["results"]))
        self.assertEqual(self._current(self.injector).status, "RELEASED")  # untouched
        self.assertTrue(BOM.objects.filter(part_type=pump).exists())      # the other BOM landed

    def test_a_line_the_edit_form_would_refuse_is_refused(self):
        """Lines are validated by the API's BOMLineSerializer: a raw material can't be MAKE."""
        body = self.import_csv("part_type,revision,material,quantity,source\n"
                               "Injector,B,O-ring,1,MAKE\n")
        self.assert_row_errors(body, mentions="made in-house")

    def test_an_export_imports_back_unchanged(self):
        from Tracker.models import BOM
        body = self.import_file(self.export("xlsx"), "bom.xlsx")
        self.assertEqual(body["summary"]["errors"], 0, body)
        self.assertIn("No change", str(body["results"]))
        self.assertEqual(BOM.objects.filter(part_type=self.injector).count(), 1)

    def test_the_template_offers_the_parent_columns(self):
        header = self.client.get(f"/api/{self.endpoint}/import-template/csv/").content.decode(
            "utf-8-sig").splitlines()[0]
        for col in ("part_type", "revision", "component_type", "quantity"):
            self.assertIn(col, header)

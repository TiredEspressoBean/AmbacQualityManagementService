"""Milestone template import: one sheet of milestones, the file replaces each template's
milestones, and a changed template gets a new version through the model's own revise
path (Tracker/services/mes/milestone_import.py)."""
from Tracker.tests.io_base import ImportExportTestCase

HEADER = "template,display_order,name,customer_display_name,is_active\n"


class MilestoneImportTests(ImportExportTestCase):
    endpoint = "Milestones"
    tenant_slug = "io-milestone"

    @classmethod
    def build_fixtures(cls):
        from Tracker.models import Milestone, MilestoneTemplate
        cls.standard = MilestoneTemplate.objects.create(tenant=cls.tenant, name="Standard")
        for order, name, active in ((1, "PO Received", True), (2, "Production", True),
                                    (3, "Shipped", False)):
            Milestone.objects.create(tenant=cls.tenant, template=cls.standard, name=name,
                                     display_order=order, is_active=active)

    def _current(self, name="Standard"):
        from Tracker.models import MilestoneTemplate
        return MilestoneTemplate.objects.get(name=name, is_current_version=True)

    def _milestones(self, template):
        return list(template.milestones.filter(archived=False).order_by("display_order")
                    .values_list("display_order", "name", "is_active"))

    def _same_file(self):
        return HEADER + ("Standard,1,PO Received,,true\n"
                         "Standard,2,Production,,true\n"
                         "Standard,3,Shipped,,false\n")

    def test_a_changed_template_gets_a_new_version(self):
        body = self.import_csv(HEADER + "Standard,1,PO Received,,true\n"
                                        "Standard,2,Engineering,Design,true\n"
                                        "Standard,3,Production,,true\n")
        self.assertEqual(body["summary"]["errors"], 0, body)
        v2 = self._current()
        self.assertEqual(v2.version, 2)
        self.assertEqual(v2.previous_version_id, self.standard.id)
        self.assertEqual(self._milestones(v2), [(1, "PO Received", True),
                                                (2, "Engineering", True),
                                                (3, "Production", True)])
        self.assertEqual(v2.milestones.get(display_order=2).customer_display_name, "Design")
        # v1 keeps its milestones — orders already under way are pinned to them.
        self.assertEqual(self._milestones(self.standard), [(1, "PO Received", True),
                                                           (2, "Production", True),
                                                           (3, "Shipped", False)])

    def test_replace_removes_milestones_the_file_leaves_out(self):
        self.import_csv(HEADER + "Standard,1,PO Received,,true\n")
        self.assertEqual(self._milestones(self._current()), [(1, "PO Received", True)])

    def test_an_unchanged_file_changes_nothing(self):
        from Tracker.models import MilestoneTemplate
        body = self.import_csv(self._same_file())
        self.assertEqual(body["summary"]["errors"], 0, body)
        self.assertIn("No change", str(body["results"]))
        self.assertEqual(MilestoneTemplate.objects.filter(name="Standard").count(), 1)

    def test_a_new_template_is_created(self):
        body = self.import_csv(HEADER + "Repair,1,Received,,true\nRepair,2,Closed,,false\n")
        self.assertEqual(body["summary"]["created"], 2, body)
        self.assertEqual(self._milestones(self._current("Repair")),
                         [(1, "Received", True), (2, "Closed", False)])

    def test_one_bad_milestone_fails_its_whole_template_only(self):
        """Milestones are validated by the API's MilestoneSerializer: a name over 100
        characters is refused, and with it that template's other rows."""
        from Tracker.models import MilestoneTemplate
        body = self.import_csv(HEADER + "Standard,1,PO Received,,true\n"
                                        f"Standard,2,{'x' * 101},,true\n"
                                        "Repair,1,Received,,true\n")
        self.assertEqual(body["summary"]["errors"], 2, body)
        self.assertIn("100 characters", str(body["results"]))
        self.assertEqual(MilestoneTemplate.objects.filter(name="Standard").count(), 1)
        self.assertTrue(MilestoneTemplate.objects.filter(name="Repair").exists())

    def test_two_rows_at_one_position_are_refused(self):
        body = self.import_csv(HEADER + "Standard,1,PO Received,,true\n"
                                        "Standard,1,Production,,true\n")
        self.assertEqual(body["summary"]["errors"], 2, body)
        self.assertIn("display order 1", str(body["results"]))

    def test_an_export_writes_only_current_templates(self):
        self.import_csv(HEADER + "Standard,1,Kickoff,,true\n")  # v2; v1 stays behind
        text = self.export("csv").decode("utf-8-sig")
        self.assertIn("Kickoff", text)
        self.assertNotIn("Shipped", text)

    def test_an_export_imports_back_unchanged(self):
        from Tracker.models import Milestone, MilestoneTemplate
        before = self.snapshot(Milestone)
        body = self.import_file(self.export("xlsx"), "milestones.xlsx")
        self.assertEqual(body["summary"]["errors"], 0, body)
        self.assertEqual(body["summary"]["created"], 0, body)
        self.assertIn("No change", str(body["results"]))
        self.assertEqual(MilestoneTemplate.objects.filter(name="Standard").count(), 1)
        self.assertEqual(self.snapshot(Milestone), before)

    def test_a_csv_export_imports_back_unchanged(self):
        from Tracker.models import MilestoneTemplate
        body = self.import_file(self.export("csv"), "milestones.csv")
        self.assertEqual(body["summary"]["errors"], 0, body)
        self.assertIn("No change", str(body["results"]))
        self.assertEqual(MilestoneTemplate.objects.filter(name="Standard").count(), 1)

    def test_the_template_offers_the_parent_column(self):
        header = self.client.get(f"/api/{self.endpoint}/import-template/csv/").content.decode(
            "utf-8-sig").splitlines()[0]
        for col in ("template", "display_order", "name"):
            self.assertIn(col, header)

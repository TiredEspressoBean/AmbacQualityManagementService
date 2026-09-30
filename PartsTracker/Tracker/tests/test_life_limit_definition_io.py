"""Life limit definitions import and export one row per definition; a content edit from a
file versions the definition the way the API's PATCH does. (Its part-type links import
on PartTypeLifeLimits — see test_io_quality_reference.)"""
from Tracker.tests.io_base import ImportExportTestCase


class LifeLimitDefinitionImportExportTests(ImportExportTestCase):
    endpoint = "LifeLimitDefinitions"
    tenant_slug = "io-lifelimitdef"

    @classmethod
    def build_fixtures(cls):
        from Tracker.models import LifeLimitDefinition
        cls.cycles = LifeLimitDefinition.objects.create(
            tenant=cls.tenant, name="Flight Cycles", unit="cycles", unit_label="Cycles",
            hard_limit="20000")
        cls.shelf = LifeLimitDefinition.objects.create(
            tenant=cls.tenant, name="Shelf Life", unit="days", unit_label="Days",
            is_calendar_based=True, hard_limit="365")

    def test_a_typed_csv_creates_a_definition(self):
        from Tracker.models import LifeLimitDefinition
        body = self.import_csv("name,unit,unit_label,soft_limit,hard_limit\n"
                               "Shot Count,shots,Shots,400000,500000\n", mode="create")
        self.assertEqual(body["summary"]["created"], 1, body)
        self.assertEqual(LifeLimitDefinition.objects.get(name="Shot Count").hard_limit, 500000)

    def test_a_changed_limit_makes_a_new_version(self):
        from Tracker.models import LifeLimitDefinition
        body = self.import_csv("name,hard_limit\nFlight Cycles,25000\n", mode="update")
        self.assertEqual(body["summary"]["updated"], 1, body)
        current = LifeLimitDefinition.objects.get(name="Flight Cycles", is_current_version=True)
        self.assertEqual((current.version, current.hard_limit), (2, 25000))
        self.cycles.refresh_from_db()
        self.assertEqual((self.cycles.is_current_version, self.cycles.hard_limit),
                         (False, 20000))

    def test_an_export_imports_back_unchanged(self):
        from Tracker.models import LifeLimitDefinition
        self.assert_round_trips(LifeLimitDefinition)

    def test_a_csv_export_imports_back_unchanged(self):
        from Tracker.models import LifeLimitDefinition
        self.assert_round_trips(LifeLimitDefinition, fmt="csv")

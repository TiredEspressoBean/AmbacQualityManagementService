"""Import/export for Material and Fixture — the worked examples.

Material is the simple case: plain columns and one FK found by name. Fixture adds a
many-to-many of steps, written `Process > Step; Process > Step`. Every other model's
import/export tests follow this shape (see io_base.py).
"""
from Tracker.tests.io_base import ImportExportTestCase


class MaterialImportExportTests(ImportExportTestCase):
    endpoint = "Materials"
    tenant_slug = "io-material"

    @classmethod
    def build_fixtures(cls):
        from Tracker.models import Companies, Material
        cls.supplier = Companies.objects.create(tenant=cls.tenant, name="Parker Seals")
        Material.objects.create(tenant=cls.tenant, name="O-ring 2-114", part_number="OR-114",
                                preferred_supplier=cls.supplier)

    def test_a_typed_csv_creates_materials(self):
        from Tracker.models import Material
        body = self.import_csv(
            "name,part_number,unit_of_measure,preferred_supplier\n"
            "Seal kit,SK-1,EA,Parker Seals\n", mode="create")
        self.assertEqual(body["summary"]["created"], 1, body)
        m = Material.objects.get(part_number="SK-1")
        self.assertEqual(m.preferred_supplier_id, self.supplier.id)

    def test_a_row_is_matched_on_its_part_number(self):
        from Tracker.models import Material
        body = self.import_csv("part_number,description\nOR-114,Nitrile 70\n", mode="update")
        self.assertEqual(body["summary"]["updated"], 1, body)
        self.assertEqual(Material.objects.get(part_number="OR-114").description, "Nitrile 70")

    def test_a_supplier_that_names_nothing_is_refused(self):
        body = self.import_csv("name,preferred_supplier\nWasher,Nobody Inc\n", mode="create")
        self.assert_row_errors(body, mentions="Nobody Inc")

    def test_an_export_imports_back_unchanged(self):
        from Tracker.models import Material
        self.assert_round_trips(Material)

    def test_a_large_import_runs_in_the_background(self):
        """100+ rows go to Celery by import path. An importer built on the viewset has
        none, so the task used to answer "Invalid serializer" for every such import."""
        import io
        from unittest import mock
        from Tracker.models import Material
        from Tracker.tasks import process_import_task
        from Tracker.viewsets.mixins.csv_import import BACKGROUND_IMPORT_THRESHOLD
        rows = "\n".join(f"Bulk {i},BK-{i}" for i in range(BACKGROUND_IMPORT_THRESHOLD))
        f = io.BytesIO(("name,part_number\n" + rows).encode("utf-8"))
        f.name = "big.csv"
        queued = {}

        def capture(args=None, kwargs=None, **_):
            queued.update(args=args or (), kwargs=kwargs or {})
            return mock.Mock(id="t1")

        with mock.patch.object(process_import_task, "apply_async", side_effect=capture), \
                self.captureOnCommitCallbacks(execute=True):
            r = self.client.post("/api/Materials/import/", {"file": f, "mode": "create"},
                                 format="multipart")
        self.assertEqual(r.status_code, 202, r.content[:500])
        result = process_import_task.apply(args=queued["args"], kwargs=queued["kwargs"]).get()
        self.assertNotEqual(result.get("status"), "error", result)
        self.assertEqual(Material.objects.filter(name__startswith="Bulk ").count(),
                         BACKGROUND_IMPORT_THRESHOLD)


class FixtureImportExportTests(ImportExportTestCase):
    endpoint = "Fixtures"
    tenant_slug = "io-fixture"

    @classmethod
    def build_fixtures(cls):
        from Tracker.models import Fixture, PartTypes, Processes, ProcessStep, Steps
        pt = PartTypes.objects.create(tenant=cls.tenant, name="Pump")
        cls.steps = {}
        # "Drill" is in both processes: only `Process > Step` says which.
        for pname in ("Pump Build", "Pump Repair"):
            proc = Processes.objects.create(tenant=cls.tenant, name=pname, part_type=pt,
                                            status="APPROVED")
            for i, sname in enumerate(("Drill", "Tap"), start=1):
                st = Steps.objects.create(tenant=cls.tenant, part_type=pt, name=sname)
                ProcessStep.objects.create(process=proc, step=st, order=i)
                cls.steps[(pname, sname)] = st
        jig = Fixture.objects.create(tenant=cls.tenant, name="Drill jig", quantity=2)
        jig.steps.set([cls.steps[("Pump Build", "Drill")], cls.steps[("Pump Repair", "Tap")]])

    def test_steps_are_named_with_their_process(self):
        from Tracker.models import Fixture
        body = self.import_csv(
            'name,quantity,steps\n"Tap guide",1,"Pump Build > Tap; Pump Repair > Drill"\n',
            mode="create")
        self.assertEqual(body["summary"]["created"], 1, body)
        got = set(Fixture.objects.get(name="Tap guide").steps.values_list("id", flat=True))
        self.assertEqual(got, {self.steps[("Pump Build", "Tap")].id,
                               self.steps[("Pump Repair", "Drill")].id})

    def test_a_bare_step_name_in_two_processes_is_refused(self):
        body = self.import_csv("name,steps\nAmbiguous,Drill\n", mode="create")
        self.assert_row_errors(body, mentions="Name it with its process")

    def test_a_deleted_fixture_no_longer_constrains_the_schedule(self):
        """The scheduling settings' Remove button archives a fixture; the solver read
        archived fixtures too, so a removed jig still serialized its steps."""
        from Tracker.models import Fixture
        from Tracker.services.scheduling.data import get_fixture_availability
        jig = Fixture.objects.get(name="Drill jig")
        self.assertIn(jig.id, get_fixture_availability(self.tenant))
        self.assertEqual(self.client.delete(f"/api/Fixtures/{jig.id}/").status_code, 204)
        self.assertNotIn(jig.id, get_fixture_availability(self.tenant))

    def test_the_export_writes_the_steps_as_it_reads_them(self):
        csv_text = self.export("csv").decode("utf-8-sig")
        self.assertIn("Pump Build > Drill; Pump Repair > Tap", csv_text)

    def test_an_export_imports_back_unchanged(self):
        from Tracker.models import Fixture
        self.assert_round_trips(Fixture)

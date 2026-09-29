"""CRUD + import/export for the scheduler's setup data: StepTiming,
StepEquipmentAffinity and WorkCenterChangeover.

Steps are named `Process > Step` ("Drill" is in both processes below, so a bare name is
ambiguous); machines by serial number or name. Each table is keyed on its unique
combination: the step; the step + machine; the machine + from step + to step.
"""
from Tracker.tests.io_base import ImportExportTestCase


def _build_routing(cls):
    """Two processes that both have a "Drill" and a "Tap" step, and two machines."""
    from Tracker.models import Equipments, PartTypes, Processes, ProcessStep, Steps
    pt = PartTypes.objects.create(tenant=cls.tenant, name="Pump")
    cls.steps = {}
    for pname in ("Pump Build", "Pump Repair"):
        proc = Processes.objects.create(tenant=cls.tenant, name=pname, part_type=pt,
                                        status="APPROVED")
        for i, sname in enumerate(("Drill", "Tap"), start=1):
            st = Steps.objects.create(tenant=cls.tenant, part_type=pt, name=sname)
            ProcessStep.objects.create(process=proc, step=st, order=i)
            cls.steps[(pname, sname)] = st
    cls.mill1 = Equipments.objects.create(tenant=cls.tenant, name="Mill 1", serial_number="SN-001")
    cls.mill2 = Equipments.objects.create(tenant=cls.tenant, name="Mill 2")


def _rows(body):
    return body["results"] if isinstance(body, dict) and "results" in body else body


class StepTimingImportExportTests(ImportExportTestCase):
    endpoint = "StepTimings"
    tenant_slug = "io-steptiming"

    @classmethod
    def build_fixtures(cls):
        from Tracker.models import StepTiming
        _build_routing(cls)
        StepTiming.objects.create(
            tenant=cls.tenant, step=cls.steps[("Pump Build", "Drill")], setup_minutes=15,
            cycle_time_minutes=2.5, load_unload_per_piece=0.5, attention_type="load_unload",
            external_setup_minutes=5)

    def test_the_api_lists_and_creates_timings(self):
        from Tracker.models import StepTiming
        r = self.client.post(f"/api/{self.endpoint}/", {
            "step": str(self.steps[("Pump Build", "Tap")].id), "cycle_time_minutes": 1.5,
        }, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(
            StepTiming.objects.get(step=self.steps[("Pump Build", "Tap")]).cycle_time_minutes, 1.5)
        r = self.client.get(f"/api/{self.endpoint}/")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(len(_rows(r.json())), 2)

    def test_a_typed_csv_creates_timings(self):
        from Tracker.models import StepTiming
        body = self.import_csv(
            "step,setup_minutes,cycle_time_minutes,attention_type\n"
            "Pump Repair > Tap,10,3,full\n", mode="create")
        self.assertEqual(body["summary"]["created"], 1, body)
        t = StepTiming.objects.get(step=self.steps[("Pump Repair", "Tap")])
        self.assertEqual((t.setup_minutes, t.cycle_time_minutes), (10, 3))

    def test_a_row_is_matched_on_its_step(self):
        from Tracker.models import StepTiming
        body = self.import_csv("step,cycle_time_minutes\nPump Build > Drill,4\n", mode="update")
        self.assertEqual(body["summary"]["updated"], 1, body)
        t = StepTiming.objects.get(step=self.steps[("Pump Build", "Drill")])
        self.assertEqual(t.cycle_time_minutes, 4)
        self.assertEqual(t.setup_minutes, 15)  # untouched column kept

    def test_a_bare_step_name_in_two_processes_is_refused(self):
        body = self.import_csv("step,cycle_time_minutes\nTap,1\n", mode="create")
        self.assert_row_errors(body, mentions="Name it with its process")

    def test_an_export_imports_back_unchanged(self):
        from Tracker.models import StepTiming
        self.assert_round_trips(StepTiming)
        self.assert_round_trips(StepTiming, fmt="csv")


class StepEquipmentAffinityImportExportTests(ImportExportTestCase):
    endpoint = "StepEquipmentAffinities"
    tenant_slug = "io-stepaffinity"

    @classmethod
    def build_fixtures(cls):
        from Tracker.models import StepEquipmentAffinity
        _build_routing(cls)
        StepEquipmentAffinity.objects.create(
            tenant=cls.tenant, step=cls.steps[("Pump Build", "Drill")], equipment=cls.mill1,
            affinity="preferred", cycle_time_override=2.0)

    def test_the_api_lists_and_creates_affinities(self):
        from Tracker.models import StepEquipmentAffinity
        r = self.client.post(f"/api/{self.endpoint}/", {
            "step": str(self.steps[("Pump Build", "Drill")].id),
            "equipment": str(self.mill2.id), "affinity": "eligible",
        }, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertTrue(StepEquipmentAffinity.objects.filter(equipment=self.mill2).exists())
        r = self.client.get(f"/api/{self.endpoint}/")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(len(_rows(r.json())), 2)

    def test_a_typed_csv_creates_affinities(self):
        from Tracker.models import StepEquipmentAffinity
        # A machine by serial number, and one by name.
        body = self.import_csv(
            "step,equipment,affinity\n"
            "Pump Repair > Drill,SN-001,dialed_in\n"
            "Pump Repair > Drill,Mill 2,eligible\n", mode="create")
        self.assertEqual(body["summary"]["created"], 2, body)
        step = self.steps[("Pump Repair", "Drill")]
        got = dict(StepEquipmentAffinity.objects.filter(step=step)
                   .values_list("equipment_id", "affinity"))
        self.assertEqual(got, {self.mill1.id: "dialed_in", self.mill2.id: "eligible"})

    def test_a_row_is_matched_on_step_and_machine(self):
        from Tracker.models import StepEquipmentAffinity
        body = self.import_csv(
            "step,equipment,affinity\nPump Build > Drill,Mill 1,dialed_in\n", mode="update")
        self.assertEqual(body["summary"]["updated"], 1, body)
        a = StepEquipmentAffinity.objects.get(step=self.steps[("Pump Build", "Drill")],
                                              equipment=self.mill1)
        self.assertEqual(a.affinity, "dialed_in")
        self.assertEqual(a.cycle_time_override, 2.0)

    def test_a_machine_that_names_nothing_is_refused(self):
        body = self.import_csv(
            "step,equipment\nPump Build > Tap,Lathe 9\n", mode="create")
        self.assert_row_errors(body, mentions="Lathe 9")

    def test_a_deleted_eligibility_can_be_added_back(self):
        """DELETE archives the row, which still holds its (step, machine) key — adding
        it back used to be refused as a duplicate. Now it revives the same row."""
        from Tracker.models import StepEquipmentAffinity
        step = self.steps[("Pump Build", "Drill")]
        row = StepEquipmentAffinity.objects.get(step=step, equipment=self.mill1)
        self.assertEqual(self.client.delete(f"/api/{self.endpoint}/{row.id}/").status_code, 204)
        r = self.client.post(f"/api/{self.endpoint}/", {
            "step": str(step.id), "equipment": str(self.mill1.id), "affinity": "dialed_in",
        }, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        row.refresh_from_db()
        self.assertFalse(row.archived)
        self.assertEqual(row.affinity, "dialed_in")
        self.assertEqual(StepEquipmentAffinity.unscoped.filter(  # tenant-safe: narrowed to this tenant's step
            step=step, equipment=self.mill1).count(), 1)

    def test_a_deleted_eligibility_is_not_read_by_the_scheduler(self):
        from Tracker.models import StepEquipmentAffinity
        from Tracker.services.scheduling.data import get_step_equipment_affinities
        step = self.steps[("Pump Build", "Drill")]

        def machines():
            return {a.equipment_id for a in get_step_equipment_affinities(self.tenant).get(step.id, [])}

        self.assertIn(self.mill1.id, machines())
        StepEquipmentAffinity.objects.get(step=step, equipment=self.mill1).delete()
        self.assertNotIn(self.mill1.id, machines())

    def test_an_export_imports_back_unchanged(self):
        from Tracker.models import StepEquipmentAffinity
        self.assert_round_trips(StepEquipmentAffinity)
        self.assert_round_trips(StepEquipmentAffinity, fmt="csv")


class WorkCenterChangeoverDeleteTests(ImportExportTestCase):
    """A deleted changeover stops adding setup time, and an import can add it back."""
    endpoint = "WorkCenterChangeovers"
    tenant_slug = "io-changeover-delete"

    @classmethod
    def build_fixtures(cls):
        from Tracker.models import WorkCenterChangeover
        _build_routing(cls)
        cls.cell = WorkCenterChangeover.objects.create(
            tenant=cls.tenant, equipment=cls.mill1,
            from_step=cls.steps[("Pump Build", "Drill")],
            to_step=cls.steps[("Pump Repair", "Drill")], changeover_minutes=30)

    def test_a_deleted_changeover_is_not_in_the_matrix(self):
        from Tracker.services.scheduling.data import get_changeover_matrix
        key = (self.mill1.id, self.cell.from_step_id, self.cell.to_step_id)
        self.assertIn(key, get_changeover_matrix(self.tenant))
        self.assertEqual(self.client.delete(f"/api/{self.endpoint}/{self.cell.id}/").status_code, 204)
        self.assertNotIn(key, get_changeover_matrix(self.tenant))

    def test_an_import_adds_a_deleted_changeover_back(self):
        from Tracker.services.scheduling.data import get_changeover_matrix
        self.cell.delete()
        body = self.import_csv(
            "equipment,from_step,to_step,changeover_minutes\n"
            "Mill 1,Pump Build > Drill,Pump Repair > Drill,45\n", mode="create")
        self.assertEqual(body["summary"]["errors"], 0, body)
        self.cell.refresh_from_db()
        self.assertFalse(self.cell.archived)
        self.assertEqual(self.cell.changeover_minutes, 45)
        key = (self.mill1.id, self.cell.from_step_id, self.cell.to_step_id)
        self.assertEqual(get_changeover_matrix(self.tenant)[key], 45)


class WorkCenterChangeoverImportExportTests(ImportExportTestCase):
    endpoint = "WorkCenterChangeovers"
    tenant_slug = "io-changeover"

    @classmethod
    def build_fixtures(cls):
        from Tracker.models import WorkCenterChangeover
        _build_routing(cls)
        WorkCenterChangeover.objects.create(
            tenant=cls.tenant, equipment=cls.mill1,
            from_step=cls.steps[("Pump Build", "Drill")],
            to_step=cls.steps[("Pump Repair", "Drill")], changeover_minutes=30)

    def test_the_api_lists_and_creates_changeovers(self):
        from Tracker.models import WorkCenterChangeover
        r = self.client.post(f"/api/{self.endpoint}/", {
            "equipment": str(self.mill2.id),
            "from_step": str(self.steps[("Pump Build", "Tap")].id),
            "to_step": str(self.steps[("Pump Build", "Drill")].id),
            "changeover_minutes": 12,
        }, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertTrue(WorkCenterChangeover.objects.filter(equipment=self.mill2).exists())
        r = self.client.get(f"/api/{self.endpoint}/")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(len(_rows(r.json())), 2)

    def test_a_typed_csv_creates_changeovers(self):
        from Tracker.models import WorkCenterChangeover
        body = self.import_csv(
            "equipment,from_step,to_step,changeover_minutes\n"
            "Mill 2,Pump Build > Tap,Pump Repair > Tap,45\n", mode="create")
        self.assertEqual(body["summary"]["created"], 1, body)
        c = WorkCenterChangeover.objects.get(equipment=self.mill2)
        self.assertEqual(c.from_step_id, self.steps[("Pump Build", "Tap")].id)
        self.assertEqual(c.to_step_id, self.steps[("Pump Repair", "Tap")].id)
        self.assertEqual(c.changeover_minutes, 45)

    def test_a_row_is_matched_on_machine_and_both_steps(self):
        from Tracker.models import WorkCenterChangeover
        body = self.import_csv(
            "equipment,from_step,to_step,changeover_minutes\n"
            "SN-001,Pump Build > Drill,Pump Repair > Drill,20\n", mode="update")
        self.assertEqual(body["summary"]["updated"], 1, body)
        self.assertEqual(WorkCenterChangeover.objects.get(equipment=self.mill1)
                         .changeover_minutes, 20)

    def test_a_bare_step_name_in_two_processes_is_refused(self):
        body = self.import_csv(
            "equipment,from_step,to_step,changeover_minutes\n"
            "Mill 2,Drill,Pump Build > Tap,5\n", mode="create")
        self.assert_row_errors(body, mentions="Name it with its process")

    def test_an_export_imports_back_unchanged(self):
        from Tracker.models import WorkCenterChangeover
        self.assert_round_trips(WorkCenterChangeover)
        self.assert_round_trips(WorkCenterChangeover, fmt="csv")

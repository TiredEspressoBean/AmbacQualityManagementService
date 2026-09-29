"""Import/export for WorkCenter and Shift — both versioned.

WorkCenter: matched on `code`; `equipment` is a `; ` list of names. An import edits the
way `WorkCenterSerializer.update` does — a content edit versions, a placement/planning
edit (equipment, is_constraint, is_critical) saves in place.

Shift: matched on `code`; every edit versions (as `ShiftViewSet.perform_update` does).
Breaks are written `12:00-12:30; 15:00-15:15`.

Both round trips also prove the unchanged import forked NO new version: the snapshot
covers every row, superseded versions included.
"""
import datetime as dt
from decimal import Decimal

from Tracker.tests.io_base import ImportExportTestCase


class WorkCenterImportExportTests(ImportExportTestCase):
    endpoint = "WorkCenters"
    tenant_slug = "io-workcenter"

    @classmethod
    def build_fixtures(cls):
        from Tracker.models import Equipments, WorkCenter
        cls.mill = Equipments.objects.create(tenant=cls.tenant, name="Haas VF-2")
        cls.lathe = Equipments.objects.create(tenant=cls.tenant, name="Okuma LB3000")
        wc = WorkCenter.objects.create(
            tenant=cls.tenant, name="Machining cell", code="MC1", description="Bay 3",
            default_efficiency=Decimal("92.30"), cost_center="CC-10", is_constraint=True)
        wc.equipment.set([cls.mill, cls.lathe])
        WorkCenter.objects.create(tenant=cls.tenant, name="Final inspection", code="QA1",
                                  kind="INSPECTION")

    def test_a_typed_csv_creates_work_centers(self):
        from Tracker.models import WorkCenter
        body = self.import_csv(
            'name,code,capacity_units,equipment\n'
            '"Turning","TC1","hours","Okuma LB3000; Haas VF-2"\n', mode="create")
        self.assertEqual(body["summary"]["created"], 1, body)
        wc = WorkCenter.objects.get(code="TC1")
        self.assertEqual(set(wc.equipment.values_list("id", flat=True)),
                         {self.mill.id, self.lathe.id})

    def test_a_content_edit_matched_on_code_versions_it(self):
        from Tracker.models import WorkCenter
        body = self.import_csv("code,name\nMC1,Machining cell A\n", mode="update")
        self.assertEqual(body["summary"]["updated"], 1, body)
        self.assertEqual(WorkCenter.objects.filter(code="MC1").count(), 2)
        current = WorkCenter.objects.get(code="MC1", is_current_version=True)
        self.assertEqual(current.name, "Machining cell A")
        # The new version keeps its equipment.
        self.assertEqual(current.equipment.count(), 2)

    def test_a_planning_edit_saves_in_place(self):
        from Tracker.models import WorkCenter
        body = self.import_csv("code,is_critical,equipment\nQA1,true,Haas VF-2\n",
                               mode="update")
        self.assertEqual(body["summary"]["updated"], 1, body)
        self.assertEqual(WorkCenter.objects.filter(code="QA1").count(), 1)
        wc = WorkCenter.objects.get(code="QA1")
        self.assertTrue(wc.is_critical)
        self.assertEqual(list(wc.equipment.values_list("id", flat=True)), [self.mill.id])

    def test_equipment_that_names_nothing_is_refused(self):
        body = self.import_csv("name,code,equipment\nPaint,PB1,Nonexistent booth\n",
                               mode="create")
        self.assert_row_errors(body, mentions="Nonexistent booth")

    def test_an_export_imports_back_unchanged(self):
        from Tracker.models import WorkCenter
        self.assert_round_trips(WorkCenter)
        self.assert_round_trips(WorkCenter, fmt="csv")


class ShiftImportExportTests(ImportExportTestCase):
    endpoint = "Shifts"
    tenant_slug = "io-shift"

    @classmethod
    def build_fixtures(cls):
        from Tracker.models import Shift
        Shift.objects.create(
            tenant=cls.tenant, name="Day", code="DAY", start_time=dt.time(6, 0),
            end_time=dt.time(14, 30), days_of_week="0,1,2,3,4",
            break_windows=[{"start": "09:00", "end": "09:15"},
                           {"start": "12:00", "end": "12:30"}])
        Shift.objects.create(
            tenant=cls.tenant, name="Weekend", code="WKD", start_time=dt.time(7, 0),
            end_time=dt.time(15, 0), days_of_week="5,6", is_active=False)

    def test_a_typed_csv_creates_shifts(self):
        from Tracker.models import Shift
        body = self.import_csv(
            'name,code,start_time,end_time,days_of_week,break_windows\n'
            'Night,NGT,22:00,06:00,"0,1,2,3",01:00-01:30; 03:00-03:15\n', mode="create")
        self.assertEqual(body["summary"]["created"], 1, body)
        s = Shift.objects.get(code="NGT")
        self.assertEqual(s.start_time, dt.time(22, 0))
        self.assertEqual(s.days_of_week, "0,1,2,3")
        self.assertEqual(s.break_windows, [{"start": "01:00", "end": "01:30"},
                                           {"start": "03:00", "end": "03:15"}])

    def test_an_edit_matched_on_code_creates_a_new_version(self):
        from Tracker.models import Shift
        body = self.import_csv("code,end_time\nDAY,15:00\n", mode="update")
        self.assertEqual(body["summary"]["updated"], 1, body)
        self.assertEqual(Shift.objects.filter(code="DAY").count(), 2)
        current = Shift.objects.get(code="DAY", is_current_version=True)
        self.assertEqual(current.end_time, dt.time(15, 0))
        self.assertEqual(current.version, 2)

    def test_a_break_that_cannot_be_read_is_refused(self):
        body = self.import_csv("name,code,start_time,end_time,break_windows\n"
                               "Swing,SWG,14:00,22:00,lunch\n", mode="create")
        self.assert_row_errors(body, mentions="lunch")

    def test_a_break_the_api_refuses_is_refused(self):
        # start after end: ShiftSerializer.validate_break_windows refuses it.
        body = self.import_csv("code,break_windows\nDAY,12:30-12:00\n", mode="update")
        self.assert_row_errors(body, mentions="start must be before end")

    def test_the_export_writes_breaks_as_it_reads_them(self):
        csv_text = self.export("csv").decode("utf-8-sig")
        self.assertIn("09:00-09:15; 12:00-12:30", csv_text)

    def test_an_export_imports_back_unchanged_with_no_new_version(self):
        from Tracker.models import Shift
        versions = sorted(Shift.objects.values_list("code", "version"))
        self.assert_round_trips(Shift)
        self.assert_round_trips(Shift, fmt="csv")
        self.assertEqual(sorted(Shift.objects.values_list("code", "version")), versions)

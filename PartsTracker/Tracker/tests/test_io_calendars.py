"""Import/export for the scheduler's calendar entries: plant closures, labor blocks and
overtime windows.

They share one importer (`_CalendarImportSerializer` in viewsets/scheduling.py) that
reads date-times and times of day as a CSV writes them, and `days_of_week` as the
model's own comma-joined day numbers (`0,2,4`, 0=Monday). Each is round-tripped in both
formats: a CSV's date-times are text, an xlsx's are cells.
"""
from datetime import date, datetime, time, timezone as dt_tz

from Tracker.tests.io_base import ImportExportTestCase


def _utc(*args):
    return datetime(*args, tzinfo=dt_tz.utc)


class PlantCalendarExceptionImportExportTests(ImportExportTestCase):
    endpoint = "PlantCalendarExceptions"
    tenant_slug = "io-plant-cal"

    @classmethod
    def build_fixtures(cls):
        from Tracker.models import PlantCalendarException
        cls.xmas = PlantCalendarException.objects.create(
            tenant=cls.tenant, name="Christmas", kind="HOLIDAY", recurrence="YEARLY",
            start_time=_utc(2026, 12, 24), end_time=_utc(2026, 12, 27))
        PlantCalendarException.objects.create(
            tenant=cls.tenant, name="Summer shutdown", kind="SHUTDOWN",
            start_time=_utc(2026, 7, 6, 6, 30), end_time=_utc(2026, 7, 18, 18),
            is_active=False)

    def test_a_typed_csv_creates_a_closure_with_its_times(self):
        from Tracker.models import PlantCalendarException
        body = self.import_csv(
            "name,kind,start_time,end_time\n"
            "Stock-take,INVENTORY,2026-10-30 12:00,2026-10-31 08:00\n", mode="create")
        self.assertEqual(body["summary"]["created"], 1, body)
        c = PlantCalendarException.objects.get(name="Stock-take")  # tenant-safe: auto-scoped in setUp
        self.assertEqual(c.start_time, _utc(2026, 10, 30, 12))
        self.assertEqual(c.end_time, _utc(2026, 10, 31, 8))

    def test_a_row_is_matched_on_its_name_and_start(self):
        from Tracker.models import PlantCalendarException
        body = self.import_csv(
            "name,start_time,end_time\nChristmas,2026-12-24 00:00:00,2026-12-29 00:00:00\n",
            mode="update")
        self.assertEqual(body["summary"]["updated"], 1, body)
        self.xmas.refresh_from_db()
        self.assertEqual(self.xmas.end_time, _utc(2026, 12, 29))
        self.assertEqual(PlantCalendarException.objects.count(), 2)  # tenant-safe: auto-scoped

    def test_an_end_before_the_start_is_refused(self):
        body = self.import_csv(
            "name,start_time,end_time\nBackwards,2026-11-02 08:00,2026-11-01 08:00\n",
            mode="create")
        self.assert_row_errors(body, mentions="End must be after start")

    def test_an_export_imports_back_unchanged(self):
        from Tracker.models import PlantCalendarException
        self.assert_round_trips(PlantCalendarException)
        self.assert_round_trips(PlantCalendarException, fmt="csv")


class LaborCalendarBlockImportExportTests(ImportExportTestCase):
    endpoint = "LaborCalendarBlocks"
    tenant_slug = "io-labor-cal"

    @classmethod
    def build_fixtures(cls):
        from Tracker.models import LaborCalendarBlock, User
        cls.op = User.objects.create_user(
            username="io-lab-op", email="op@io-lab.test", password="x", tenant=cls.tenant)
        cls.pto = LaborCalendarBlock.objects.create(
            tenant=cls.tenant, user=cls.op, kind="PTO", recurrence="ONCE",
            start_time=_utc(2026, 11, 2, 7), end_time=_utc(2026, 11, 6, 17), reason="Vacation")
        # Company-wide (no person), weekly: the all-hands.
        LaborCalendarBlock.objects.create(
            tenant=cls.tenant, kind="MEETING", recurrence="WEEKLY", days_of_week="0",
            window_start=time(9), window_end=time(9, 30), reason="All-hands")
        # A person's weekly block, several days.
        LaborCalendarBlock.objects.create(
            tenant=cls.tenant, user=cls.op, kind="TRAINING", recurrence="WEEKLY",
            days_of_week="1,3", window_start=time(14), window_end=time(15, 15))

    def test_a_typed_csv_creates_blocks_naming_the_person_by_email(self):
        from Tracker.models import LaborCalendarBlock
        body = self.import_csv(
            "user,kind,recurrence,start_time,end_time,days_of_week,window_start,window_end\n"
            "op@io-lab.test,SICK,ONCE,2026-10-12 06:00,2026-10-12 18:00,,,\n"
            ",BREAK,WEEKLY,,,0; 2; 4,10:00,10:15\n", mode="create")
        self.assertEqual(body["summary"]["created"], 2, body)
        sick = LaborCalendarBlock.objects.get(kind="SICK")  # tenant-safe: auto-scoped
        self.assertEqual(sick.user_id, self.op.id)
        self.assertEqual(sick.start_time, _utc(2026, 10, 12, 6))
        brk = LaborCalendarBlock.objects.get(kind="BREAK")  # tenant-safe: auto-scoped
        self.assertIsNone(brk.user_id)
        self.assertEqual(brk.days_of_week, "0,2,4")
        self.assertEqual((brk.window_start, brk.window_end), (time(10), time(10, 15)))

    def test_a_row_is_matched_on_person_kind_and_start(self):
        body = self.import_csv(
            "user,kind,start_time,reason\nop@io-lab.test,PTO,2026-11-02 07:00,Honeymoon\n",
            mode="update")
        self.assertEqual(body["summary"]["updated"], 1, body)
        self.pto.refresh_from_db()
        self.assertEqual(self.pto.reason, "Honeymoon")

    def test_a_person_who_is_not_here_is_refused(self):
        body = self.import_csv(
            "user,kind,start_time,end_time\nnobody@else.test,PTO,2026-11-02 07:00,"
            "2026-11-03 07:00\n", mode="create")
        self.assert_row_errors(body, mentions="nobody@else.test")

    def test_a_day_that_is_not_a_day_is_refused(self):
        body = self.import_csv(
            "kind,recurrence,days_of_week,window_start,window_end\n"
            "BREAK,WEEKLY,\"Mon,Wed\",10:00,10:15\n", mode="create")
        self.assert_row_errors(body, mentions="Not a day number")

    def test_the_export_names_the_person_by_email(self):
        csv_text = self.export("csv").decode("utf-8-sig")
        self.assertIn("op@io-lab.test", csv_text)

    def test_an_export_imports_back_unchanged(self):
        from Tracker.models import LaborCalendarBlock
        self.assert_round_trips(LaborCalendarBlock)
        self.assert_round_trips(LaborCalendarBlock, fmt="csv")


class OvertimeWindowImportExportTests(ImportExportTestCase):
    endpoint = "OvertimeWindows"
    tenant_slug = "io-overtime"

    @classmethod
    def build_fixtures(cls):
        from Tracker.models import OvertimeWindow, Shift
        cls.day = Shift.objects.create(
            tenant=cls.tenant, name="Day Shift", code="DAY",
            start_time=time(6), end_time=time(14, 30))
        cls.night = Shift.objects.create(
            tenant=cls.tenant, name="Night Shift", code="NGT",
            start_time=time(22), end_time=time(6))
        cls.saturday = OvertimeWindow.objects.create(
            tenant=cls.tenant, shift=cls.day, recurrence="ONCE",
            start_date=date(2026, 10, 3), end_date=date(2026, 10, 3), reason="Catch-up")
        OvertimeWindow.objects.create(
            tenant=cls.tenant, shift=cls.night, recurrence="WEEKLY", days_of_week="5,6")

    def test_a_typed_csv_creates_windows_naming_the_shift_by_code_or_name(self):
        from Tracker.models import OvertimeWindow
        body = self.import_csv(
            "shift,recurrence,start_date,end_date,days_of_week\n"
            "NGT,ONCE,2026-10-10,2026-10-11,\n"
            "Day Shift,WEEKLY,,,5\n", mode="create")
        self.assertEqual(body["summary"]["created"], 2, body)
        once = OvertimeWindow.objects.get(start_date=date(2026, 10, 10))  # tenant-safe: auto-scoped
        self.assertEqual(once.shift_id, self.night.id)
        weekly = OvertimeWindow.objects.get(shift=self.day, recurrence="WEEKLY")  # tenant-safe: auto-scoped
        self.assertEqual(weekly.days_of_week, "5")

    def test_a_row_is_matched_on_its_shift_and_first_date(self):
        body = self.import_csv(
            "shift,start_date,end_date\nDAY,2026-10-03,2026-10-04\n", mode="update")
        self.assertEqual(body["summary"]["updated"], 1, body)
        self.saturday.refresh_from_db()
        self.assertEqual(self.saturday.end_date, date(2026, 10, 4))

    def test_a_shift_that_names_nothing_is_refused(self):
        body = self.import_csv(
            "shift,recurrence,days_of_week\nSwing Shift,WEEKLY,6\n", mode="create")
        self.assert_row_errors(body, mentions="Swing Shift")

    def test_a_new_shift_version_is_the_one_matched(self):
        from Tracker.models import OvertimeWindow
        # A Shift edit makes a new version and re-points its windows (see
        # services.mes.shifts); by name, the import finds the current version.
        new = self.day.create_new_version(user=self.user, end_time=time(15))
        self.saturday.refresh_from_db()
        self.assertEqual(self.saturday.shift_id, new.id)
        body = self.import_csv(
            "shift,recurrence,days_of_week\nDay Shift,WEEKLY,4\n", mode="create")
        self.assertEqual(body["summary"]["created"], 1, body)
        self.assertEqual(
            OvertimeWindow.objects.get(days_of_week="4").shift_id, new.id)  # tenant-safe: auto-scoped
        self.assert_round_trips(OvertimeWindow)

    def test_an_export_imports_back_unchanged(self):
        from Tracker.models import OvertimeWindow
        self.assert_round_trips(OvertimeWindow)
        self.assert_round_trips(OvertimeWindow, fmt="csv")

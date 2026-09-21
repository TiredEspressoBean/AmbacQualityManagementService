"""Shift windows are wall-clock time on the shop floor, not on the server.

Resolved against `Tenant.default_timezone`, which already existed and was already
editable in organization settings — nothing had ever consulted it when expanding shifts.

"We start at six" means six on the clock on the wall. Windows were built with
`timezone.make_aware`, which uses `settings.TIME_ZONE` — correct only when the server
happens to share the plant's zone. With the server on UTC and the shop on US Eastern,
a 06:00-18:00 shift was emitted as 06:00-18:00Z and rendered as 02:00-14:00 local: the
Gantt shaded the wrong hours, and near midnight the wrong DAY.
"""
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.test import TestCase
from django.utils import timezone

from Tracker.models import Shift, Tenant
from Tracker.services.scheduling.data import get_working_windows, plant_tz
from Tracker.tests.base import TenantContextMixin

EASTERN = ZoneInfo("America/New_York")


class PlantTimezoneTests(TenantContextMixin, TestCase):

    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(
            name="TZ", slug="tz-shop", tier="PRO", default_timezone="America/New_York")
        self.set_tenant_context(self.tenant)
        Shift.objects.create(
            tenant=self.tenant, code="DAY", name="Day",
            start_time=time(6, 0), end_time=time(18, 0),
            days_of_week="0,1,2,3,4", is_active=True)

    def _windows(self, start, end):
        return get_working_windows(self.tenant, start, end)

    def test_the_shift_starts_at_six_on_the_plants_clock(self):
        """The bug, stated directly. 06:00 Eastern is 10:00 UTC in summer — not 06:00Z."""
        # A Wednesday in July, well inside DST.
        start = datetime(2026, 7, 1, 0, 0, tzinfo=EASTERN)
        windows = self._windows(start, start + timedelta(days=1))

        self.assertEqual(len(windows), 1)
        w_start, w_end = windows[0]
        self.assertEqual(timezone.localtime(w_start, EASTERN).hour, 6)
        self.assertEqual(timezone.localtime(w_end, EASTERN).hour, 18)
        # And in absolute terms that is 10:00-22:00Z, not 06:00-18:00Z.
        self.assertEqual(w_start.astimezone(ZoneInfo("UTC")).hour, 10)

    def test_the_hours_hold_across_a_dst_change(self):
        """Built with the zone attached rather than a fixed offset, so zoneinfo resolves
        the offset for that wall time. A shift does not drift an hour in November."""
        winter = datetime(2026, 1, 14, 0, 0, tzinfo=EASTERN)   # a Wednesday, EST
        summer = datetime(2026, 7, 15, 0, 0, tzinfo=EASTERN)   # a Wednesday, EDT

        for day in (winter, summer):
            w_start, _ = self._windows(day, day + timedelta(days=1))[0]
            self.assertEqual(timezone.localtime(w_start, EASTERN).hour, 6, day)

        # The UTC offsets genuinely differ — proving the test isn't vacuous.
        w_winter, _ = self._windows(winter, winter + timedelta(days=1))[0]
        w_summer, _ = self._windows(summer, summer + timedelta(days=1))[0]
        self.assertNotEqual(w_winter.astimezone(ZoneInfo("UTC")).hour,
                            w_summer.astimezone(ZoneInfo("UTC")).hour)

    def test_a_weekday_shift_does_not_leak_onto_the_weekend(self):
        """The day-boundary half. The loop used to walk UTC dates, so for a shop behind
        UTC the plant's Friday evening is already Saturday in UTC — and a Mon-Fri shift
        could be expanded onto a day the shop is closed."""
        # Saturday 2026-07-04 through Sunday, plant-local.
        sat = datetime(2026, 7, 4, 0, 0, tzinfo=EASTERN)
        self.assertEqual(self._windows(sat, sat + timedelta(days=2)), [])

    def test_a_utc_plant_is_unchanged(self):
        """The fallback has to be exactly the old behaviour for a shop on UTC."""
        utc_tenant = Tenant.objects.create(
            name="UTC", slug="utc-shop", tier="PRO", default_timezone="UTC")
        self.set_tenant_context(utc_tenant)
        Shift.objects.create(
            tenant=utc_tenant, code="DAY", name="Day",
            start_time=time(6, 0), end_time=time(18, 0),
            days_of_week="0,1,2,3,4", is_active=True)

        start = datetime(2026, 7, 1, 0, 0, tzinfo=ZoneInfo("UTC"))
        w_start, _ = get_working_windows(utc_tenant, start, start + timedelta(days=1))[0]
        self.assertEqual(w_start.astimezone(ZoneInfo("UTC")).hour, 6)

    def test_an_unknown_zone_falls_back_instead_of_raising(self):
        """A bad string on one tenant must not take the scheduler down for everyone."""
        self.tenant.default_timezone = "Mars/Olympus_Mons"
        self.tenant.save(update_fields=['default_timezone'])
        self.assertIsNotNone(plant_tz(self.tenant))

        start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self._windows(start, start + timedelta(days=3))   # must not raise

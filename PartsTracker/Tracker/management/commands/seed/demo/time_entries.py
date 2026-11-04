"""Demo seeder for labor time entries (the clock / timesheet history).

Gives the Operator Hours screen (payroll's read) and the labor_hours report a
realistic prior work week: for each shop-floor user (Operator / Shift Lead
groups), each workday gets the clock state machine's shape —
  SHIFT   07:00–11:30 and 12:00–15:30  (attendance, split around lunch)
  LUNCH   11:30–12:00
Attendance only: direct (job) hours are derived from the step records, never clocked
(services/mes/labor_report.py), so no PRODUCTION entries — the demo shows what a real
shop gets.
Deterministic per (user, day) and idempotent via get_or_create on
(tenant, user, entry_type, start_time).
"""
from datetime import datetime, timedelta

from django.utils import timezone

from Tracker.models import TimeEntry, User

from ..base import BaseSeeder

_FLOOR_GROUPS = ("Operator", "Shift Lead")


class DemoTimeEntrySeeder(BaseSeeder):
    """Seeds a prior work week of SHIFT/BREAK/LUNCH entries for floor staff."""

    def seed(self):
        self.log("Creating demo labor time entries (prior work week)...")
        # The plant's clock, not the server's: a shift or a closure is on the wall
        # clock where the work happens (services/core/clock).
        from Tracker.services.core.clock import plant_tz, tenant_today
        tz = plant_tz(self.tenant)
        today = tenant_today(self.tenant)

        floor_users = [
            u for u in User.objects.filter(tenant=self.tenant)
            if set(u.get_tenant_group_names(tenant=self.tenant) or []) & set(_FLOOR_GROUPS)
        ]
        if not floor_users:
            self.log("  Warning: no floor users, skipping time entries", warning=True)
            return {'entries': 0}

        # The 5 most recent weekdays up to and including yesterday (today stays
        # clean so a live clock-in demo isn't tangled with seeded history).
        days: list = []
        d = today - timedelta(days=1)
        while len(days) < 5:
            if d.weekday() < 5:  # Mon–Fri
                days.append(d)
            d -= timedelta(days=1)

        def at(day, hh, mm):
            return timezone.make_aware(datetime(day.year, day.month, day.day, hh, mm), tz)

        # The seeder owns the seeded window: wipe prior seeded entries for these
        # users/days so a reseed with a different punch shape can't double-count.
        TimeEntry.objects.filter(
            tenant=self.tenant, user__in=floor_users,
            start_time__gte=at(days[-1], 0, 0),
            start_time__lt=at(days[0] + timedelta(days=1), 0, 0),
        ).delete()

        created = 0

        def entry(user, etype, start, end):
            nonlocal created
            _, was_created = TimeEntry.objects.get_or_create(
                tenant=self.tenant, user=user, entry_type=etype, start_time=start,
                defaults={'end_time': end},
            )
            created += int(was_created)

        for idx, user in enumerate(sorted(floor_users, key=lambda u: u.username)):
            for di, day in enumerate(days):
                # One user is out one day (PTO-shaped gap keeps totals uneven).
                if idx == 1 and di == 3:
                    continue
                # Attendance split around the shift's standing breaks (the clock
                # state machine's shape): 09:00 facility break + 12:00 lunch,
                # matching Shift.break_windows seeded in scheduling.py.
                entry(user, 'SHIFT', at(day, 7, 0), at(day, 9, 0))
                entry(user, 'BREAK', at(day, 9, 0), at(day, 9, 15))
                entry(user, 'SHIFT', at(day, 9, 15), at(day, 12, 0))
                entry(user, 'LUNCH', at(day, 12, 0), at(day, 12, 30))
                entry(user, 'SHIFT', at(day, 12, 30), at(day, 15, 30))

        created += self._live_floor_today(at, today)

        self.log(f"  Time entries: {created} created for {len(floor_users)} floor users over {len(days)} days")
        return {'entries': created, 'users': len(floor_users)}

    def _live_floor_today(self, at, today) -> int:
        """Who is on the floor right now — so a supervisor's Work in progress shows the
        difference between work whose holder is here and work left by someone who isn't
        ("Off the clock"). Casey (the shift lead) is on shift and on a break: a break
        still counts as on the clock, so her own open work isn't flagged. Mike and Dave
        are deliberately NOT clocked in: the Operator track starts with Mike clocking
        in, and the Shift Lead track has Dave off sick — his unfinished work is the
        off-the-clock case. Open entries only; today otherwise stays clean."""
        now = timezone.now()
        shift_start = min(at(today, 7, 0), now - timedelta(hours=1))
        live = 0
        for email, on_break in (("casey.dual@demo.ambac.com", True),):
            user = User.objects.filter(tenant=self.tenant, email=email).first()
            if user is None:
                continue
            TimeEntry.objects.filter(tenant=self.tenant, user=user,
                                     start_time__gte=at(today, 0, 0)).delete()
            if on_break:
                # The clock's shape: a break closes the shift segment and opens a BREAK.
                break_start = now - timedelta(minutes=10)
                TimeEntry.objects.create(tenant=self.tenant, user=user, entry_type='SHIFT',
                                         start_time=shift_start, end_time=break_start)
                TimeEntry.objects.create(tenant=self.tenant, user=user, entry_type='BREAK',
                                         start_time=break_start, end_time=None)
                live += 2
            else:
                TimeEntry.objects.create(tenant=self.tenant, user=user, entry_type='SHIFT',
                                         start_time=shift_start, end_time=None)
                live += 1
        return live

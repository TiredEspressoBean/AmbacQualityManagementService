"""Demo seeder for labor time entries (the clock / timesheet history).

Gives the Operator Hours screen (payroll's read) and the labor_hours report a
realistic prior work week: for each shop-floor user (Operator / Shift Lead
groups), each workday gets the clock state machine's shape —
  SHIFT   07:00–11:30 and 12:00–15:30  (attendance, split around lunch)
  LUNCH   11:30–12:00
  PRODUCTION blocks inside the shift    (time clocked onto live WOs at the
                                         user's primary station's steps)
Deterministic per (user, day) and idempotent via get_or_create on
(tenant, user, entry_type, start_time).
"""
from datetime import datetime, timedelta

from django.utils import timezone

from Tracker.models import TimeEntry, User, WorkOrder

from ..base import BaseSeeder

_FLOOR_GROUPS = ("Operator", "Shift Lead")


class DemoTimeEntrySeeder(BaseSeeder):
    """Seeds a prior work week of SHIFT/LUNCH/PRODUCTION entries for floor staff."""

    def seed(self):
        self.log("Creating demo labor time entries (prior work week)...")
        tz = timezone.get_current_timezone()
        today = timezone.localdate()

        floor_users = [
            u for u in User.objects.filter(tenant=self.tenant)
            if set(u.get_tenant_group_names(tenant=self.tenant) or []) & set(_FLOOR_GROUPS)
        ]
        live_wos = list(
            WorkOrder.objects.filter(tenant=self.tenant, workorder_status='IN_PROGRESS')
            .select_related('process')[:6]
        )
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

        def entry(user, etype, start, end, **ctx):
            nonlocal created
            _, was_created = TimeEntry.objects.get_or_create(
                tenant=self.tenant, user=user, entry_type=etype, start_time=start,
                defaults={'end_time': end, **ctx},
            )
            created += int(was_created)

        for idx, user in enumerate(sorted(floor_users, key=lambda u: u.username)):
            # A user's primary station steps drive the PRODUCTION context.
            membership = user.work_center_memberships.filter(is_primary=True).first()
            wc = membership.work_center if membership else None
            step = wc.steps.filter(is_current_version=True).first() if wc else None
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
                # Direct time: production blocks on live jobs (~realistic
                # utilization), staggered per user/day.
                if live_wos:
                    wo_a = live_wos[(idx + di) % len(live_wos)]
                    wo_b = live_wos[(idx + di + 1) % len(live_wos)]
                    entry(user, 'PRODUCTION', at(day, 7, 15), at(day, 8, 55),
                          work_order=wo_a, step=step, work_center=wc)
                    entry(user, 'PRODUCTION', at(day, 9, 20), at(day, 11, 45),
                          work_order=wo_a, step=step, work_center=wc)
                    entry(user, 'PRODUCTION', at(day, 12, 40), at(day, 14, 30 + (idx % 3) * 10),
                          work_order=wo_b, step=step, work_center=wc)

        self.log(f"  Time entries: {created} created for {len(floor_users)} floor users over {len(days)} days")
        return {'entries': created, 'users': len(floor_users)}

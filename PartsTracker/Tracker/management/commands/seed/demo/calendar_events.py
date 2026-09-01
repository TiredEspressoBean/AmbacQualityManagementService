"""Demo seeder for scheduling-calendar events.

Populates the three calendar surfaces the solver honors (and the
/production/calendar page renders):
  - PlantCalendarException — plant-wide closures (holiday / shutdown / inventory)
  - LaborCalendarBlock     — operator-only non-working time (PTO, training,
                             a weekly all-hands, a recurring morning BREAK)
  - OvertimeWindow         — additive time (a catch-up Saturday running the shift)

Dates are anchored to "today" so the events stay inside the solve horizon on any
reseed: the holiday lands next Monday, PTO this Friday, overtime this Saturday.
Idempotent via get_or_create on stable natural keys.
"""
from datetime import datetime, timedelta

from django.utils import timezone

from Tracker.models import (
    LaborCalendarBlock, OvertimeWindow, PlantCalendarException, Shift, User,
)

from ..base import BaseSeeder


class DemoCalendarSeeder(BaseSeeder):
    """Seeds plant closures, labor blocks, and an overtime window."""

    def seed(self):
        self.log("Creating demo calendar events (closures / labor blocks / overtime)...")
        tz = timezone.get_current_timezone()
        today = timezone.localdate()

        def aware(d, hh=0, mm=0):
            return timezone.make_aware(datetime(d.year, d.month, d.day, hh, mm), tz)

        def next_weekday(from_day, weekday):  # weekday: 0=Mon..6=Sun, strictly after from_day
            delta = (weekday - from_day.weekday() - 1) % 7 + 1
            return from_day + timedelta(days=delta)

        created = {'closures': 0, 'blocks': 0, 'overtime': 0}

        # --- Plant closures -------------------------------------------------
        next_monday = next_weekday(today, 0)
        for name, kind, recurrence, start, end in (
            # Next Monday off — lands inside the solve horizon so the Gantt
            # visibly flows work around it. Yearly, like a fixed-date holiday.
            ("Labor Day", 'HOLIDAY', 'YEARLY',
             aware(next_monday), aware(next_monday, 23, 59)),
            # The winter shutdown — the classic multi-day yearly closure.
            ("Winter Shutdown", 'SHUTDOWN', 'YEARLY',
             aware(today.replace(month=12, day=24)),
             aware(today.replace(month=12, day=31), 23, 59)),
            # One-off stock-take day about a month out.
            ("Quarterly Inventory Count", 'INVENTORY', 'ONCE',
             aware(next_monday + timedelta(days=23)),
             aware(next_monday + timedelta(days=23), 23, 59)),
        ):
            _, was_created = PlantCalendarException.objects.get_or_create(
                tenant=self.tenant, name=name,
                defaults={'kind': kind, 'recurrence': recurrence,
                          'start_time': start, 'end_time': end},
            )
            created['closures'] += int(was_created)

        # --- Labor blocks ---------------------------------------------------
        users = {u.username.split('@')[0]: u for u in User.objects.filter(tenant=self.tenant)}
        dave = users.get('dave.wilson')
        mike = users.get('mike.ops')
        this_friday = next_weekday(today - timedelta(days=1), 4)

        # NOTE: the facility-wide daily break (09:00) and lunch are NOT calendar
        # blocks — standing breaks are a property of the Shift (break_windows,
        # seeded in scheduling.py). The calendar's BREAK kind stays reserved for
        # genuinely ad-hoc/extra break blocks.
        LaborCalendarBlock.objects.filter(  # migrate old reseeds that had it here
            tenant=self.tenant, user=None, kind='BREAK',
            reason="Morning stretch break").delete()

        blocks = [
            # Whole-company weekly all-hands (user=null = everyone).
            dict(user=None, kind='MEETING', recurrence='WEEKLY', days_of_week='0',
                 window_start='07:00', window_end='07:30',
                 reason="Monday production all-hands"),
        ]
        if dave:
            blocks.append(dict(user=dave, kind='PTO', recurrence='ONCE',
                               start_time=aware(this_friday),
                               end_time=aware(this_friday, 23, 59),
                               reason="Vacation day"))
        if mike:
            training_day = next_weekday(today, 2)  # next Wednesday
            blocks.append(dict(user=mike, kind='TRAINING', recurrence='ONCE',
                               start_time=aware(training_day, 13, 0),
                               end_time=aware(training_day, 15, 0),
                               reason="Forklift recertification"))
        for b in blocks:
            _, was_created = LaborCalendarBlock.objects.get_or_create(
                tenant=self.tenant, user=b.get('user'), kind=b['kind'],
                recurrence=b['recurrence'], reason=b['reason'],
                defaults={k: v for k, v in b.items()
                          if k not in ('user', 'kind', 'recurrence', 'reason')},
            )
            created['blocks'] += int(was_created)

        # --- Overtime -------------------------------------------------------
        shift = Shift.objects.filter(tenant=self.tenant, is_active=True).first()
        if shift:
            this_saturday = next_weekday(today - timedelta(days=1), 5)
            _, was_created = OvertimeWindow.objects.get_or_create(
                tenant=self.tenant, shift=shift, recurrence='ONCE',
                start_date=this_saturday,
                defaults={'end_date': this_saturday,
                          'reason': "Catch-up Saturday — late work orders"},
            )
            created['overtime'] += int(was_created)

        self.log(f"  Calendar events: {created}")
        return created

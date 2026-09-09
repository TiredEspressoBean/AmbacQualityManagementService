"""`regroup_batch` — direct-manipulation Gantt merge / break.

Merge rejoins the WO+step cohort: it UNPINS the parts (so the solver batches them) and
snaps them onto the cohort's slot for an immediate collapse. Break lays the parts out in
their own sequential slots and PINS them (separate fixed bars). Both apply immediately and
mark the schedule stale; the solver batches only the *unpinned* cohort.
"""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from Tracker.models import (
    Equipments,
    Parts,
    PartTypes,
    Processes,
    ProcessStatus,
    ProcessStep,
    ScheduledTask,
    ScheduleResult,
    Steps,
    Tenant,
)
from Tracker.services.mes.work_order import plan_work_order
from Tracker.services.scheduling.manual_move import regroup_batch
from Tracker.tests.base import TenantContextMixin


class RegroupBatchTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="RG", slug="regroup", tier="PRO")
        self.set_tenant_context(self.tenant)
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Nz", ID_prefix="NZ")
        # APPROVED, not the model default of DRAFT: `plan_work_order` only releases
        # work against an approved routing.
        self.process = Processes.objects.create(
            tenant=self.tenant, name="Line", part_type=self.pt,
            status=ProcessStatus.APPROVED)
        self.step = Steps.objects.create(tenant=self.tenant, part_type=self.pt, name="Op1")
        ProcessStep.objects.create(process=self.process, step=self.step, order=1)
        self.machine = Equipments.objects.create(tenant=self.tenant, name="CNC-1")
        self.wo = plan_work_order(tenant=self.tenant, process=self.process, quantity=3)
        self.parts = list(Parts.objects.filter(work_order=self.wo).order_by("ERP_id"))
        now = timezone.now().replace(microsecond=0)
        self.sched = ScheduleResult.objects.create(
            tenant=self.tenant, horizon_start=now, horizon_end=now + timedelta(days=2),
            is_active=True, is_stale=False)
        # One task per part, all in one lot at the same slot (a ×3 cell).
        self.tasks = [
            ScheduledTask.objects.create(
                tenant=self.tenant, schedule=self.sched, part=p, step=self.step,
                machine=self.machine, start_time=now, end_time=now + timedelta(hours=1))
            for p in self.parts
        ]

    def _refresh_parts(self):
        return list(Parts.objects.filter(work_order=self.wo).order_by("ERP_id"))

    def test_break_staggers_and_pins(self):
        n = regroup_batch(self.tasks, merge=False)
        self.assertEqual(n, 3)
        tasks = list(ScheduledTask.objects.filter(schedule=self.sched).order_by("start_time"))
        self.assertTrue(all(t.is_pinned for t in tasks), "broken parts are pinned in place")
        # laid out sequentially (no two share a start) so they render as separate bars
        starts = [t.start_time for t in tasks]
        self.assertEqual(len(set(starts)), 3)

    def test_merge_aligns_and_unpins(self):
        # first break (pins apart), then merge back → rejoin the cohort
        regroup_batch(self.tasks, merge=False)
        fresh = list(ScheduledTask.objects.filter(schedule=self.sched))
        n = regroup_batch(fresh, merge=True)
        self.assertEqual(n, 3)
        tasks = list(ScheduledTask.objects.filter(schedule=self.sched))
        self.assertEqual(len({t.start_time for t in tasks}), 1, "collapsed onto one start")
        self.assertEqual(len({t.machine_id for t in tasks}), 1, "all on one machine")
        # merge hands the parts back to the solver (unpinned), which batches the cohort
        self.assertTrue(all(not t.is_pinned for t in tasks))

    def test_merge_snaps_to_existing_cohort_slot(self):
        # one part stays as the unpinned cohort; the other two are broken off, then merged
        # back — they should snap onto the cohort part's slot (not their own).
        cohort_task = self.tasks[0]
        broken = self.tasks[1:]
        regroup_batch(broken, merge=False)  # pin the two away
        regroup_batch(list(ScheduledTask.objects.filter(schedule=self.sched, id__in=[t.id for t in broken])), merge=True)
        cohort_task.refresh_from_db()
        for t in ScheduledTask.objects.filter(schedule=self.sched, id__in=[t.id for t in broken]):
            self.assertEqual(t.start_time, cohort_task.start_time, "snapped to cohort slot")
            self.assertFalse(t.is_pinned)

    def test_merge_sizes_batch_setup_plus_ncycle(self):
        from Tracker.models import StepTiming
        StepTiming.objects.create(
            tenant=self.tenant, step=self.step, setup_minutes=10, cycle_time_minutes=5)
        regroup_batch(self.tasks, merge=True)  # 3 parts → one lot
        for t in ScheduledTask.objects.filter(schedule=self.sched):
            # one setup + 3×cycle = 10 + 15 = 25 min
            self.assertEqual(t.end_time - t.start_time, timedelta(minutes=25))

    def test_break_sizes_each_part_setup_plus_cycle(self):
        from Tracker.models import StepTiming
        StepTiming.objects.create(
            tenant=self.tenant, step=self.step, setup_minutes=10, cycle_time_minutes=5)
        regroup_batch(self.tasks, merge=False)  # each part its own lot
        durs = [(t.end_time - t.start_time) for t in ScheduledTask.objects.filter(schedule=self.sched)]
        self.assertTrue(all(d == timedelta(minutes=15) for d in durs))  # setup + 1×cycle

    def test_marks_schedule_stale(self):
        self.sched.is_stale = False
        self.sched.save(update_fields=["is_stale"])
        regroup_batch(self.tasks, merge=False)
        self.sched.refresh_from_db()
        self.assertTrue(self.sched.is_stale)

    def test_cores_skipped_no_parts(self):
        # a task list with no part-backed tasks changes nothing
        self.assertEqual(regroup_batch([], merge=True), 0)

    def test_mixed_selection_merges_each_wo_separately(self):
        # A second work order on the same step, at a DIFFERENT slot. Selecting parts
        # from both WOs and merging must collapse each WO onto its own slot — never
        # combine parts across work orders.
        wo2 = plan_work_order(tenant=self.tenant, process=self.process, quantity=2)
        parts2 = list(Parts.objects.filter(work_order=wo2).order_by("ERP_id"))
        later = self.tasks[0].start_time + timedelta(hours=5)
        tasks2 = [
            ScheduledTask.objects.create(
                tenant=self.tenant, schedule=self.sched, part=p, step=self.step,
                machine=self.machine, start_time=later, end_time=later + timedelta(hours=1))
            for p in parts2
        ]
        # break both cohorts apart so they're at distinct, pinned slots
        regroup_batch(self.tasks + tasks2, merge=False)
        # now merge a selection spanning BOTH work orders
        fresh = list(ScheduledTask.objects.filter(schedule=self.sched))
        n = regroup_batch(fresh, merge=True)
        self.assertEqual(n, 5)  # 3 + 2

        def _starts(wo):
            return {
                t.start_time
                for t in ScheduledTask.objects.filter(schedule=self.sched, part__work_order=wo)
            }

        # each WO collapses to a single shared start...
        self.assertEqual(len(_starts(self.wo)), 1)
        self.assertEqual(len(_starts(wo2)), 1)
        # ...and the two WOs do NOT share a slot (not merged across work orders)
        self.assertNotEqual(_starts(self.wo), _starts(wo2))

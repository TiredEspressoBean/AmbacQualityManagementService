"""Direct labour hours derived from step executions (user decision 2026-10-29, option 1).

Merged not summed (lock-step lots), clipped to attendance (SHIFT minus breaks), shared
across concurrent work orders, attributed to the claimant, rework separated, and hold /
outside-processing time left out. Plus the endpoints that read it.
"""
from datetime import timedelta

from django.utils import timezone

from Tracker.models import (
    EdgeType, OutsideProcessShipment, PartTypes, Parts, Processes, ProcessStep, StepEdge,
    StepExecution, StepTiming, Steps, TimeEntry, WorkOrder, WorkOrderHold,
)
from Tracker.services.mes.labor_report import allocate, operator_hours, work_order_labor
from Tracker.tests.base import TenantTestCase

H = 3600.0


class _Base(TenantTestCase):

    def setUp(self):
        super().setUp()
        t = self.tenant_a
        # Yesterday 06:00 UTC: entirely in the past, so nothing is capped at now.
        self.day = (timezone.now() - timedelta(days=1)).replace(hour=6, minute=0, second=0,
                                                                microsecond=0)
        self.pt = PartTypes.objects.create(tenant=t, name="Body", ID_prefix="B")
        self.step = Steps.objects.create(tenant=t, part_type=self.pt, name="Turn", step_type="TASK")
        self.wo_a = WorkOrder.objects.create(tenant=t, ERP_id="WO-A", quantity=3)
        self.wo_b = WorkOrder.objects.create(tenant=t, ERP_id="WO-B", quantity=1)
        self._n = 0

    def at(self, h, m=0):
        return self.day + timedelta(hours=h - 6, minutes=m)

    def shift(self, start, end, user=None, kind="SHIFT"):
        TimeEntry.objects.create(tenant=self.tenant_a, user=user or self.user_a, entry_type=kind,
                                 start_time=start, end_time=end)

    def execution(self, wo, start, end, user=None, completed_by=None, visit=1, step=None, **kw):
        self._n += 1
        part = Parts.objects.create(tenant=self.tenant_a, ERP_id=f"B-{self._n}", part_type=self.pt,
                                    work_order=wo, step=step or self.step)
        return StepExecution.objects.create(
            tenant=self.tenant_a, part=part, step=step or self.step, visit_number=visit,
            status="COMPLETED" if end else "IN_PROGRESS", started_at=start, exited_at=end,
            assigned_to=user if user is not False else None, completed_by=completed_by, **kw)

    def alloc(self, user=None):
        return allocate(self.tenant_a, self.at(0), self.at(23))[(user or self.user_a).id]


class AllocationTests(_Base):

    def test_a_lock_step_lot_is_merged_not_multiplied(self):
        self.shift(self.at(7), self.at(15))
        for _ in range(3):
            self.execution(self.wo_a, self.at(8), self.at(10), user=self.user_a)
        a = self.alloc()
        self.assertAlmostEqual(a['direct'] / H, 2.0)
        self.assertAlmostEqual(a['by_wo'][self.wo_a.id][0] / H, 2.0)

    def test_direct_is_clipped_to_the_shift_minus_breaks(self):
        self.shift(self.at(8), self.at(12))
        self.shift(self.at(10), self.at(10, 30), kind="BREAK")
        self.execution(self.wo_a, self.at(9), self.at(13), user=self.user_a)
        a = self.alloc()
        self.assertAlmostEqual(a['on_shift'] / H, 3.5)
        # 9-10 and 10:30-12; 12-13 is off the clock.
        self.assertAlmostEqual(a['direct'] / H, 2.5)

    def test_no_clock_in_means_no_direct_time(self):
        self.execution(self.wo_a, self.at(8), self.at(10), user=self.user_a)
        a = self.alloc()
        self.assertEqual((a['on_shift'], a['direct']), (0.0, 0.0))

    def test_the_claimant_gets_the_time_and_the_completer_is_the_fallback(self):
        self.shift(self.at(7), self.at(15))
        self.shift(self.at(7), self.at(15), user=self.user_b)
        # Claimed by A, finished by B (a handover): A's.
        self.execution(self.wo_a, self.at(8), self.at(9), user=self.user_a, completed_by=self.user_b)
        # Nobody claimed it; B completed it: B's.
        self.execution(self.wo_b, self.at(10), self.at(11), user=False, completed_by=self.user_b)
        result = allocate(self.tenant_a, self.at(0), self.at(23))
        self.assertAlmostEqual(result[self.user_a.id]['direct'] / H, 1.0)
        self.assertAlmostEqual(result[self.user_b.id]['direct'] / H, 1.0)
        self.assertIn(self.wo_b.id, result[self.user_b.id]['by_wo'])

    def test_concurrent_work_orders_share_the_time_by_parts(self):
        self.shift(self.at(7), self.at(15))
        self.execution(self.wo_a, self.at(8), self.at(11), user=self.user_a)
        self.execution(self.wo_a, self.at(8), self.at(11), user=self.user_a)
        self.execution(self.wo_b, self.at(8), self.at(11), user=self.user_a)
        a = self.alloc()
        self.assertAlmostEqual(a['direct'] / H, 3.0)
        self.assertAlmostEqual(a['by_wo'][self.wo_a.id][0] / H, 2.0)
        self.assertAlmostEqual(a['by_wo'][self.wo_b.id][0] / H, 1.0)

    def test_revisits_and_rework_steps_are_rework(self):
        self.shift(self.at(7), self.at(15))
        rework_step = Steps.objects.create(tenant=self.tenant_a, part_type=self.pt, name="Rework",
                                           step_type="REWORK")
        self.execution(self.wo_a, self.at(8), self.at(9), user=self.user_a)
        self.execution(self.wo_a, self.at(9), self.at(10), user=self.user_a, visit=2)
        self.execution(self.wo_a, self.at(10), self.at(11), user=self.user_a, step=rework_step)
        a = self.alloc()
        self.assertAlmostEqual(a['direct'] / H, 3.0)
        self.assertAlmostEqual(a['rework'] / H, 2.0)

    def test_hold_and_outside_processing_time_is_left_out(self):
        self.shift(self.at(7), self.at(17))
        self.execution(self.wo_a, self.at(8), self.at(12), user=self.user_a)
        WorkOrderHold.objects.create(tenant=self.tenant_a, work_order=self.wo_a, reason="QUALITY",
                                     placed_at=self.at(9), cleared_at=self.at(10))
        from Tracker.models import Companies
        vendor = Companies.objects.create(tenant=self.tenant_a, name="Apex Plating", is_supplier=True)
        shipment = OutsideProcessShipment.objects.create(tenant=self.tenant_a, step=self.step,
                                                         work_order=self.wo_b, supplier=vendor)
        OutsideProcessShipment.objects.filter(pk=shipment.pk).update(
            shipped_at=self.at(13), returned_at=self.at(15))
        self.execution(self.wo_b, self.at(12), self.at(16), user=self.user_a,
                       outside_process_shipment=shipment)
        a = self.alloc()
        self.assertAlmostEqual(a['by_wo'][self.wo_a.id][0] / H, 3.0)
        self.assertAlmostEqual(a['by_wo'][self.wo_b.id][0] / H, 2.0)

    def test_a_voided_hold_does_not_exclude(self):
        self.shift(self.at(7), self.at(15))
        self.execution(self.wo_a, self.at(8), self.at(10), user=self.user_a)
        WorkOrderHold.objects.create(tenant=self.tenant_a, work_order=self.wo_a, reason="QUALITY",
                                     placed_at=self.at(8), cleared_at=self.at(9), is_voided=True)
        self.assertAlmostEqual(self.alloc()['direct'] / H, 2.0)

    def test_a_step_left_running_stops_counting_at_the_next_clock_out(self):
        # Clocked out at 15:00 with the step still open; back in the next day.
        self.shift(self.at(7), self.at(15))
        self.shift(self.at(7) + timedelta(days=1), self.at(15) + timedelta(days=1))
        self.execution(self.wo_a, self.at(9), None, user=self.user_a)
        a = allocate(self.tenant_a, self.at(0), self.at(23) + timedelta(days=1))[self.user_a.id]
        self.assertAlmostEqual(a['direct'] / H, 6.0)   # 9:00-15:00 on day one only

    def test_a_break_is_not_a_clock_out(self):
        # The clock closes SHIFT for a break and reopens it after.
        self.shift(self.at(7), self.at(10))
        self.shift(self.at(10), self.at(10, 15), kind="BREAK")
        self.shift(self.at(10, 15), self.at(15))
        self.execution(self.wo_a, self.at(9), None, user=self.user_a)
        a = allocate(self.tenant_a, self.at(0), self.at(23))[self.user_a.id]
        self.assertAlmostEqual(a['direct'] / H, 5.75)  # 9:00-15:00 less the break

    def test_operator_hours_rows_carry_rework_and_unallocated(self):
        self.shift(self.at(7), self.at(15))
        self.execution(self.wo_a, self.at(8), self.at(10), user=self.user_a, visit=2)
        [row] = [r for r in operator_hours(self.tenant_a, self.at(0), self.at(23))
                 if r['user_id'] == self.user_a.id]
        self.assertEqual((row['on_shift_hours'], row['direct_hours'], row['rework_hours'],
                          row['unallocated_hours']), (8.0, 2.0, 2.0, 6.0))


class WorkOrderLaborTests(_Base):

    def test_actuals_per_operator_and_planned_from_the_route_standards(self):
        t = self.tenant_a
        process = Processes.objects.create(tenant=t, name="P", part_type=self.pt)
        second = Steps.objects.create(tenant=t, part_type=self.pt, name="Grind", step_type="TASK")
        ProcessStep.objects.create(process=process, step=self.step, order=1, is_entry_point=True)
        ProcessStep.objects.create(process=process, step=second, order=2)
        StepEdge.objects.create(process=process, from_step=self.step, to_step=second,
                                edge_type=EdgeType.DEFAULT)
        StepTiming.objects.create(tenant=t, step=self.step, setup_minutes=30, cycle_time_minutes=10)
        WorkOrder.objects.filter(pk=self.wo_a.pk).update(process=process)
        self.wo_a.refresh_from_db()
        self.shift(self.at(7), self.at(15))
        self.execution(self.wo_a, self.at(8), self.at(9, 30), user=self.user_a)

        out = work_order_labor(self.wo_a)
        self.assertEqual(out['direct_hours'], 1.5)
        self.assertEqual(out['rows'][0]['user_id'], self.user_a.id)
        # 30 setup + 10 × 3 pieces, full attention = 60 min; Grind has no standard.
        self.assertEqual(out['planned_hours'], 1.0)

    def test_no_standards_means_no_plan(self):
        self.assertIsNone(work_order_labor(self.wo_b)['planned_hours'])


class EndpointTests(_Base):

    def test_work_order_hours_and_its_export(self):
        self.shift(self.at(7), self.at(15))
        self.execution(self.wo_a, self.at(8), self.at(10), user=self.user_a)
        self.grant_tenant_permissions(self.user_a, self.tenant_a,
                                      ['view_scheduleresult', 'export_data', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        day = self.at(8).date().isoformat()
        r = self.client.get('/api/Schedules/work_order_hours/', {'start': day, 'end': day})
        self.assertEqual(r.status_code, 200, r.content)
        [row] = r.json()['rows']
        self.assertEqual((row['work_order'], row['direct_hours']), ('WO-A', 2.0))
        r = self.client.get('/api/Schedules/work_order_hours/export/csv/', {'start': day, 'end': day})
        self.assertEqual(r.status_code, 200)
        self.assertIn('WO-A', r.content.decode('utf-8-sig'))

    def test_the_export_needs_export_data(self):
        self.grant_tenant_permissions(self.user_a, self.tenant_a,
                                      ['view_scheduleresult', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        r = self.client.get('/api/Schedules/work_order_hours/export/xlsx/')
        self.assertEqual(r.status_code, 403)

    def test_my_hours_is_the_signed_in_persons_week(self):
        now = timezone.now()
        TimeEntry.objects.create(tenant=self.tenant_a, user=self.user_a, entry_type="SHIFT",
                                 start_time=now - timedelta(hours=2), end_time=now - timedelta(hours=1))
        self.grant_tenant_permissions(self.user_a, self.tenant_a, ['view_timeentry', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        r = self.client.get('/api/TimeEntries/my_hours/')
        self.assertEqual(r.status_code, 200, r.content)
        body = r.json()
        # The entry may straddle the plant week's start on a Monday small hours; at most 1 h.
        self.assertLessEqual(body['on_shift_hours'], 1.0)
        self.assertLessEqual(body['awaiting_approval'], 1)
        self.assertEqual(body['direct_hours'], 0.0)

    def test_work_order_labor_endpoint(self):
        self.grant_tenant_permissions(self.user_a, self.tenant_a,
                                      ['view_workorder', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        r = self.client.get(f'/api/WorkOrders/{self.wo_a.id}/labor/')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()['rows'], [])

    def test_the_approval_list_can_ask_for_attendance_only(self):
        self.shift(self.at(7), self.at(9))
        self.shift(self.at(9), self.at(9, 15), kind="BREAK")
        self.shift(self.at(9, 15), self.at(10), kind="PRODUCTION")
        self.grant_tenant_permissions(self.user_a, self.tenant_a, ['view_timeentry', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        r = self.client.get('/api/TimeEntries/?entry_type__in=SHIFT&entry_type__in=BREAK&entry_type__in=LUNCH')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(sorted(e['entry_type'] for e in r.json()['results']), ['BREAK', 'SHIFT'])

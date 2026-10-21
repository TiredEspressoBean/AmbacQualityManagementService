"""Production Manager exhibits: the plan the rest of the shop works to.

- Every active work order is released, the way a planner releases one
  (release_work_order), with an override reason only where readiness blocks it.
  Work on an unreleased order is invisible to the operator queue's unstarted rows,
  and no planner starts work they haven't released.
- ORD-2024-0051: a customer order with a dated demand line and no work orders yet,
  for the Production Manager to promise, turn into work orders and release.
- Three downtime events this week, on three machines and three causes.
- A solved schedule, so every track opens with a live plan.

Runs last: it releases what the other seeders made, and solves over all of it.
"""
from datetime import timedelta

from django.utils import timezone

from ..base import BaseSeeder

NEW_ORDER = 'ORD-2024-0051'
NEW_ORDER_QTY = 6
NEW_ORDER_DUE_DAYS = 21

# (equipment, category, reason, description, starts days/hours ago, lasts hours)
DOWNTIME = [
    ('CNC Lathe HL-1', 'UNPLANNED', 'Spindle drive fault',
     'Drive tripped on overload mid-cycle; maintenance replaced the drive fuse.', 2, 3.5),
    ('Cylindrical Grinder GR-1', 'CHANGEOVER', 'Wheel change and dress',
     'Changed to the finer wheel for the seat bore and dressed it.', 1, 1.25),
    ('Flow Test Stand #2', 'PLANNED', 'Seal change',
     'Planned seal change on the stand; flow calibration on Stand #1 only until done.', 0, 3.0),
]

SOLVE_SECONDS = 30


class DemoPlanningSeeder(BaseSeeder):
    def __init__(self, stdout, style, tenant, scale='small'):
        super().__init__(stdout, style, scale=scale)
        self.tenant = tenant
        self.today = timezone.now()

    def seed(self, users):
        self.log("Seeding the plan (releases, a new order, downtime, a solve)...")
        by_email = (users or {}).get('by_email', {})
        # The planner releases work; the production manager if there's no planner.
        self.planner = (by_email.get('sam.plan@demo.ambac.com')
                        or by_email.get('jennifer.mgr@demo.ambac.com'))
        self.lead = by_email.get('casey.dual@demo.ambac.com')
        result = {
            'released': self._release_active_work(),
            'new_order': self._new_order(),
            'downtime': self._downtime(),
        }
        result['schedule'] = self._solve()
        return result

    def _release_active_work(self):
        from Tracker.models import WorkOrder
        from Tracker.services.mes.release import ReleaseBlocked, release_work_order
        released = 0
        for wo in (WorkOrder.objects.filter(tenant=self.tenant, released_at__isnull=True)
                   .exclude(workorder_status__in=['COMPLETED', 'CANCELLED'])):
            try:
                release_work_order(wo, self.planner)
            except ReleaseBlocked as e:
                release_work_order(wo, self.planner, override_reason=(
                    f"Released for production when the job was started. "
                    f"Readiness at release: {e}")[:500])
            # Released when it was opened, not at seed time.
            WorkOrder.objects.filter(pk=wo.pk).update(released_at=wo.created_at)
            released += 1
        self.log(f"  Released {released} active work order(s)")
        return released

    def _new_order(self):
        from Tracker.models import Companies, OrderLine, OrderLineStatus, Orders, OrdersStatus, PartTypes
        customer = Companies.objects.filter(tenant=self.tenant, name='Great Lakes Diesel').first()
        part_type = PartTypes.objects.filter(tenant=self.tenant, name='Common Rail Injector').first()
        if customer is None or part_type is None:
            self.log("  Warning: no customer or part type for the new order; skipping.", warning=True)
            return None
        due = (self.today + timedelta(days=NEW_ORDER_DUE_DAYS)).date()
        order, _ = Orders.objects.update_or_create(
            tenant=self.tenant, order_number=NEW_ORDER,
            defaults={'name': f'Great Lakes injectors - {NEW_ORDER_QTY} units',
                      'company': customer, 'order_status': OrdersStatus.PENDING,
                      'estimated_completion': due},
        )
        OrderLine.objects.update_or_create(
            tenant=self.tenant, order=order, line_number=1,
            defaults={'part_type': part_type, 'quantity': NEW_ORDER_QTY, 'due_date': due,
                      'status': OrderLineStatus.OPEN,
                      'notes': 'New common rail injectors, built new.'},
        )
        self.log(f"  {NEW_ORDER}: {NEW_ORDER_QTY} injectors due {due}, no work orders yet")
        return order

    def _downtime(self):
        from Tracker.models import DowntimeEvent, Equipments
        made = []
        for name, category, reason, description, days_ago, hours in DOWNTIME:
            eq = Equipments.objects.filter(tenant=self.tenant, name=name).first()
            if eq is None:
                continue
            start = (self.today - timedelta(days=days_ago)).replace(hour=7, minute=30, second=0, microsecond=0)
            event, _ = DowntimeEvent.objects.update_or_create(
                tenant=self.tenant, equipment=eq, reason=reason,
                defaults={'category': category, 'description': description,
                          'start_time': start, 'end_time': start + timedelta(hours=hours),
                          'reported_by': self.lead, 'resolved_by': self.lead},
            )
            made.append(event)
        self.log(f"  {len(made)} downtime event(s)")
        return made

    def _solve(self):
        from Tracker.services.scheduling.preflight import LaborInfeasible
        from Tracker.services.scheduling.solver import solve_schedule
        try:
            result = solve_schedule(self.tenant, time_limit_seconds=SOLVE_SECONDS)
        except LaborInfeasible as e:
            self.log(f"  Warning: no schedule solved: {e}", warning=True)
            return None
        self.log(f"  Schedule solved: {result.solver_status}")
        return result

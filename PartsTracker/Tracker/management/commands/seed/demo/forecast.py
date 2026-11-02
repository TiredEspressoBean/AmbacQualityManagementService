"""
The demand outlook exhibit: a two-year volume forecast, a tentative deal and an
overdue order line, built for the training tracks that read the outlook.

Without a forecast, firm work in the demo is all due within the month, so every
later month of Capacity Planning reads 0%. Everything here is relative to the day
the seed runs: the forecast starts THIS month and runs 24 months.

What each track needs to find, and what provides it:

  Planner — the forecast grid, this month muted by the demand time fence, a month
    whose forecast an RFI deal uses up, and a tight month in the default 12-month
    view. PROFILE below, and ORD-2027-RFI-FLEET.
  Production Manager — "Could we take this order?": a modest order inside a forecast
    month answers "already forecast"; a large one answers no, with what fills the
    months and the earliest month it fits. Capacity in the 12-month view runs from
    under 60% to one month over capacity, which sits BEFORE the forecast peak
    because load lands in the run-up to each due date.
  Purchasing — the material outlook export: the forecast runs the injector's bought
    parts short at different times, so one order-by date is already past and the
    others fall over the next few months.
  Shipping — the Ship lane's Overdue group: ORD-2024-0053, a firm line a few days
    past due with no work started.

Holidays move capacity, so the exact percentages shift with the month the seed runs
in; training text describes the shape, not the numbers.

Through the services: set_forecast (the path the grid and sheet import use); the
two orders are plain demand records, as the order form writes them.
"""
from __future__ import annotations

from datetime import date, timedelta

from django.db import transaction
from django.utils import timezone

from Tracker.models import OrderLine, Orders, OrdersStatus, PartTypes

from ..base import BaseSeeder

PART_TYPE = 'Common Rail Injector'
# Units a month, starting THIS month (index 0, inside the demand time fence).
# Tuned on the demo crew (about 1.8 crew hours an injector): the first year puts
# every capacity band in the 12-month view, with the peak's run-up over capacity;
# the second year runs tight without going over.
PROFILE = [150, 150, 170, 190, 210, 250, 300, 350, 380, 350, 280, 220,
           200, 210, 230, 250, 280, 320, 360, 420, 340, 290, 240, 210]

RFI_ORDER = 'ORD-2027-RFI-FLEET'
RFI_CUSTOMER = 'Midwest Fleet Services'
RFI_MONTH = 4          # index into PROFILE: the fifth month, its forecast partly claimed
RFI_QUANTITY = 60

OVERDUE_ORDER = 'ORD-2024-0053'
OVERDUE_CUSTOMER = 'Great Lakes Diesel'
OVERDUE_QUANTITY = 8
OVERDUE_DAYS = 6       # due this many days ago, nothing started


class DemoForecastSeeder(BaseSeeder):
    """Seeds the volume forecast, one tentative (RFI) deal and one overdue line."""

    def __init__(self, stdout, style, tenant, scale='small'):
        super().__init__(stdout, style, scale=scale)
        self.tenant = tenant

    def seed(self, companies):
        from Tracker.services.planning.forecast import add_months, month_start, set_forecast

        self.log("Seeding the demand outlook exhibit...")
        part_type = (PartTypes.objects
                     .filter(tenant=self.tenant, name=PART_TYPE, is_current_version=True).first())
        if part_type is None:
            self.log(f"  Warning: {PART_TYPE} missing; no forecast.", warning=True)
            return {}

        today = timezone.localdate()
        first = month_start(today)
        with transaction.atomic():
            for i, quantity in enumerate(PROFILE):
                set_forecast(tenant=self.tenant, part_type=part_type,
                             month=add_months(first, i), quantity=quantity)
            rfi_due = add_months(first, RFI_MONTH).replace(day=20)
            rfi = self._order(companies, RFI_CUSTOMER, RFI_ORDER, OrdersStatus.RFI,
                              'Midwest Fleet — 2027 injector program (quoted)',
                              part_type, RFI_QUANTITY, rfi_due, 'Quoted; awaiting the customer PO.')
            late_due = today - timedelta(days=OVERDUE_DAYS)
            late = self._order(companies, OVERDUE_CUSTOMER, OVERDUE_ORDER, OrdersStatus.PENDING,
                               'Great Lakes Diesel — replacement injectors',
                               part_type, OVERDUE_QUANTITY, late_due,
                               'Promised for last week; not yet planned.')

        self.log(f"  {PART_TYPE}: {len(PROFILE)} months from {first:%Y-%m}, "
                 f"{min(PROFILE)}-{max(PROFILE)} a month")
        if rfi is not None:
            self.log(f"  {RFI_ORDER}: tentative, {RFI_QUANTITY} due {rfi_due:%Y-%m-%d}")
        if late is not None:
            self.log(f"  {OVERDUE_ORDER}: {OVERDUE_QUANTITY} due {late_due:%Y-%m-%d}, overdue, not started")
        return {'months': len(PROFILE), 'first': first, 'rfi_order': rfi, 'overdue_order': late}

    def _order(self, companies, customer_name, number, status, name, part_type,
               quantity, due: date, notes: str):
        customer = next((c for c in (companies or []) if c.name == customer_name), None)
        if customer is None:
            self.log(f"  Warning: {customer_name} missing; no {number}.", warning=True)
            return None
        order, _ = Orders.objects.update_or_create(
            tenant=self.tenant, order_number=number,
            defaults={'name': name, 'company': customer, 'order_status': status,
                      'estimated_completion': due},
        )
        OrderLine.objects.update_or_create(
            tenant=self.tenant, order=order, line_number=1,
            defaults={'part_type': part_type, 'quantity': quantity, 'due_date': due,
                      'status': 'OPEN', 'notes': notes},
        )
        return order

"""Service- and task-layer "today" is the plant's day (Tenant.default_timezone), not UTC.

Every case runs at 01:30 UTC on 11 Mar 2026 — 21:30 on 10 Mar in New York (EDT). The
plant (tenant_a) is on New York time, so its "today" is 10 Mar; tenant_b stays on UTC,
where it is already 11 Mar — the control that shows the day is resolved per tenant
(from the RECORD's tenant, not the ContextVar, which points at tenant_a throughout).

One test per behaviour class: expiry, default stamp, due/overdue, date range — and the
cross-tenant beat tasks, which must judge each row on its own plant's clock.
"""
from datetime import date, datetime, timezone as dt_tz
from types import SimpleNamespace
from unittest import mock

from Tracker.tests.base import TenantTestCase
from Tracker.models import Companies, PartTypes, SupplierQualification
from Tracker.models.core import ApprovalRequest
from Tracker.models.qms import CAPA, CapaStatus
from Tracker.services.qms import supplier_qualification as sq
from Tracker.utils.tenant_context import tenant_context

EVENING = datetime(2026, 3, 11, 1, 30, tzinfo=dt_tz.utc)  # 21:30 in New York, 10 Mar
PLANT_DAY = date(2026, 3, 10)
UTC_DAY = date(2026, 3, 11)


def at_evening():
    return mock.patch('django.utils.timezone.now', return_value=EVENING)


class PlantClockServiceTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.tenant_a.default_timezone = 'America/New_York'
        self.tenant_a.save()
        self.tenant_b.default_timezone = 'UTC'
        self.tenant_b.save()

    # --- helpers --------------------------------------------------------------

    def _qualification(self, tenant, *, expiry_date, effective_date=date(2020, 1, 1), grant=True):
        self._n = getattr(self, '_n', 0) + 1
        with tenant_context(str(tenant.id)):
            supplier = Companies.objects.create(tenant=tenant, name=f"Supplier {self._n}",
                                                description="")
            part_type = PartTypes.objects.create(tenant=tenant, name=f"Gear {self._n}")
            q = sq.open_qualification(supplier=supplier, part_type=part_type, basis="AUDIT")
            if grant:
                sq.grant(q, effective_date=effective_date, expiry_date=expiry_date)
        return q, supplier, part_type

    # --- expiry ---------------------------------------------------------------

    def test_qualification_expiring_today_still_qualifies_in_the_evening(self):
        _, supplier, part_type = self._qualification(self.tenant_a, expiry_date=PLANT_DAY)
        _, supplier_b, part_type_b = self._qualification(self.tenant_b, expiry_date=PLANT_DAY)

        with at_evening():
            self.assertTrue(sq.is_supplier_qualified(supplier=supplier, part_type=part_type))
            status = sq.resolve_status(supplier=supplier, part_type=part_type)
            self.assertEqual(status.days_to_expiry, 0)

            # Control: on a UTC plant the same expiry date has already passed.
            with tenant_context(str(self.tenant_b.id)):
                self.assertFalse(sq.is_supplier_qualified(supplier=supplier_b, part_type=part_type_b))

    def test_expire_task_judges_each_row_on_its_own_plant_day(self):
        from Tracker.tasks import expire_supplier_qualifications
        q_today, _, _ = self._qualification(self.tenant_a, expiry_date=PLANT_DAY)
        q_yesterday, _, _ = self._qualification(self.tenant_a, expiry_date=date(2026, 3, 9))
        q_utc, _, _ = self._qualification(self.tenant_b, expiry_date=PLANT_DAY)

        with at_evening():
            result = expire_supplier_qualifications()

        self.assertEqual(result['expired'], 2)
        self.assertEqual(SupplierQualification.all_tenants.get(pk=q_today.pk).status, 'APPROVED')
        self.assertEqual(SupplierQualification.all_tenants.get(pk=q_yesterday.pk).status, 'EXPIRED')
        # The ContextVar says tenant_a (New York) — the UTC plant's row expired anyway.
        self.assertEqual(SupplierQualification.all_tenants.get(pk=q_utc.pk).status, 'EXPIRED')

    # --- default stamp --------------------------------------------------------

    def test_grant_stamps_the_plant_day_as_effective(self):
        q, _, _ = self._qualification(self.tenant_a, expiry_date=None, grant=False)
        q_b, _, _ = self._qualification(self.tenant_b, expiry_date=None, grant=False)

        with at_evening():
            sq.grant(q)
            with tenant_context(str(self.tenant_b.id)):
                sq.grant(q_b)

        self.assertEqual(q.effective_date, PLANT_DAY)
        self.assertEqual(q_b.effective_date, UTC_DAY)

    # --- due / overdue --------------------------------------------------------

    def test_notification_contexts_count_days_on_the_plant_clock(self):
        from Tracker.notifications.handlers import (
            build_approval_escalation_context, build_capa_context,
        )
        # 22:00 UTC on 10 Mar = 18:00 in New York — earlier the same plant day.
        due_at = datetime(2026, 3, 10, 22, 0, tzinfo=dt_tz.utc)

        with at_evening():
            ctx = build_capa_context(SimpleNamespace(
                related_object=CAPA(tenant=self.tenant_a, status=CapaStatus.OPEN, due_date=PLANT_DAY),
                recipient=None, attempt_count=0))
            self.assertEqual((ctx['days_until_due'], ctx['is_overdue']), (0, False))

            ctx = build_approval_escalation_context(SimpleNamespace(
                related_object=ApprovalRequest(tenant=self.tenant_a, due_date=due_at),
                recipient=None))
            self.assertEqual(ctx['days_overdue'], 0)

            # Control: a UTC plant has rolled over.
            ctx = build_capa_context(SimpleNamespace(
                related_object=CAPA(tenant=self.tenant_b, status=CapaStatus.OPEN, due_date=PLANT_DAY),
                recipient=None, attempt_count=0))
            self.assertEqual((ctx['days_until_due'], ctx['is_overdue']), (-1, True))

            ctx = build_approval_escalation_context(SimpleNamespace(
                related_object=ApprovalRequest(tenant=self.tenant_b, due_date=due_at),
                recipient=None))
            self.assertEqual(ctx['days_overdue'], 1)

    # --- date range -----------------------------------------------------------

    def test_expiring_reminder_window_starts_on_the_plant_day(self):
        from Tracker.tasks import notify_expiring_qualifications
        self._qualification(self.tenant_a, expiry_date=PLANT_DAY)   # expires today: remind
        self._qualification(self.tenant_b, expiry_date=PLANT_DAY)   # expired yesterday: don't

        with at_evening():
            result = notify_expiring_qualifications()

        self.assertEqual(result['notified'], 1)

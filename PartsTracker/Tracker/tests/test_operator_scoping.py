"""Shop-floor operator scoping + labor-hours reporting.

- The scheduler treats only users in a shop-floor group (Operator / Shift Lead) as
  dispatchable operators, so admins/office staff aren't scheduled — with a fallback to
  the internal+shift roster when no one is grouped yet.
- The labor-hours report sums TimeEntry per operator (on-shift vs direct).
"""
from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from Tracker.models import Shift, TenantGroup, Tenant, TimeEntry, UserRole
from Tracker.services.scheduling import data as sched_data
from Tracker.services.mes.labor_report import operator_hours
from Tracker.tests.base import TenantContextMixin


class OperatorGroupGateTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="OG", slug="op-group", tier="PRO")
        self.set_tenant_context(self.tenant)
        User = get_user_model()
        self.shift = Shift.objects.create(
            tenant=self.tenant, name="Day", code="DAY",
            start_time=time(6, 0), end_time=time(18, 0),
            days_of_week="0,1,2,3,4,5,6", is_active=True)
        self.op1 = User.objects.create_user(
            username="op1", email="op1@c.test", password="x",
            tenant=self.tenant, user_type="INTERNAL", default_shift=self.shift)
        self.op2 = User.objects.create_user(
            username="op2", email="op2@c.test", password="x",
            tenant=self.tenant, user_type="INTERNAL", default_shift=self.shift)

    def _make_operator(self, user):
        grp, _ = TenantGroup.objects.get_or_create(tenant=self.tenant, name="Operator")
        UserRole.objects.create(user=user, group=grp)

    def test_fallback_includes_all_when_none_grouped(self):
        ids = {o.user_id for o in sched_data.get_dispatchable_operators(self.tenant)}
        self.assertIn(self.op1.id, ids)
        self.assertIn(self.op2.id, ids)

    def test_group_gate_excludes_non_operators(self):
        self._make_operator(self.op1)  # only op1 is in the Operator group
        ids = {o.user_id for o in sched_data.get_dispatchable_operators(self.tenant)}
        self.assertIn(self.op1.id, ids)
        self.assertNotIn(self.op2.id, ids)

    def test_shift_windows_gated_to_operators(self):
        self._make_operator(self.op1)
        horizon = sched_data.get_schedule_horizon(self.tenant)
        w = sched_data.get_operator_shift_windows(self.tenant, horizon)
        self.assertIn(self.op1.id, w)
        self.assertNotIn(self.op2.id, w)


class OperatorHoursReportTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="LH", slug="labor-hours", tier="PRO")
        self.set_tenant_context(self.tenant)
        User = get_user_model()
        self.op = User.objects.create_user(
            username="lhop", email="lhop@c.test", password="x",
            tenant=self.tenant, user_type="INTERNAL")
        grp, _ = TenantGroup.objects.get_or_create(tenant=self.tenant, name="Operator")
        UserRole.objects.create(user=self.op, group=grp)

    def _entry(self, user, kind, start, hours):
        return TimeEntry.objects.create(
            tenant=self.tenant, user=user, entry_type=kind,
            start_time=start, end_time=start + timedelta(hours=hours))

    def test_on_shift_and_direct_hours(self):
        base = timezone.now() - timedelta(days=1)
        self._entry(self.op, "SHIFT", base, 8)
        self._entry(self.op, "PRODUCTION", base + timedelta(hours=1), 3)
        self._entry(self.op, "BREAK", base + timedelta(hours=4), 0.5)  # excluded
        rows = operator_hours(self.tenant, base - timedelta(days=1), timezone.now())
        row = next(r for r in rows if r['user_id'] == self.op.id)
        self.assertAlmostEqual(row['on_shift_hours'], 8, delta=0.1)
        self.assertAlmostEqual(row['direct_hours'], 3, delta=0.1)

    def test_non_operator_excluded(self):
        User = get_user_model()
        other = User.objects.create_user(
            username="office", email="office@c.test", password="x",
            tenant=self.tenant, user_type="INTERNAL")  # not in a shop-floor group
        base = timezone.now() - timedelta(days=1)
        self._entry(other, "SHIFT", base, 8)
        rows = operator_hours(self.tenant, base - timedelta(days=1), timezone.now())
        self.assertFalse(any(r['user_id'] == other.id for r in rows))

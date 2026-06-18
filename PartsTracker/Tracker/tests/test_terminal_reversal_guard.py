"""Tests for the terminal-status reversal guard (Phase 0d).

Leaving a terminal status (especially SCRAPPED) must not be a casual status
change. `bulk_set_status` / `rollback_part_step` block it unless an elevated
caller passes `allow_terminal_exit=True`.
"""
from django.contrib.auth import get_user_model

from Tracker.models import (
    Companies,
    Orders,
    OrdersStatus,
    Parts,
    PartsStatus,
    Tenant,
)
from Tracker.services.mes.parts import bulk_set_status
from Tracker.tests.base import TenantContextMixin, VectorTestCase


class TerminalReversalGuardTests(TenantContextMixin, VectorTestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(
            name="Term Guard", slug="term-guard", tier="PRO"
        )
        self.set_tenant_context(self.tenant)
        User = get_user_model()
        self.operator = User.objects.create_user(
            username="term-op", email="op@term.test", password="x", tenant=self.tenant,
        )
        self.company = Companies.objects.create(tenant=self.tenant, name="Acme")
        self.order = Orders.objects.create(
            tenant=self.tenant,
            name="ORD-TG",
            company=self.company,
            order_status=OrdersStatus.IN_PROGRESS,
        )

    def _scrapped_part(self, erp):
        return Parts.objects.create(
            tenant=self.tenant, ERP_id=erp, work_order=None, order=self.order,
            part_status=PartsStatus.SCRAPPED,
        )

    def test_cannot_un_scrap_without_elevated_permission(self):
        part = self._scrapped_part("P-SCRAP1")
        results = bulk_set_status(
            tenant_id=self.tenant.id,
            part_ids=[part.id],
            new_status=PartsStatus.IN_PROGRESS,
            operator=self.operator,
        )
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].ok)
        self.assertIn("terminal", (results[0].error or "").lower())

        part.refresh_from_db()
        self.assertEqual(part.part_status, PartsStatus.SCRAPPED)  # unchanged

    def test_elevated_caller_may_reverse_terminal(self):
        part = self._scrapped_part("P-SCRAP2")
        results = bulk_set_status(
            tenant_id=self.tenant.id,
            part_ids=[part.id],
            new_status=PartsStatus.IN_PROGRESS,
            operator=self.operator,
            allow_terminal_exit=True,
        )
        self.assertTrue(results[0].ok)

        part.refresh_from_db()
        self.assertEqual(part.part_status, PartsStatus.IN_PROGRESS)

    def test_non_terminal_status_change_is_unaffected(self):
        """A normal (non-terminal) status change still works without the flag."""
        part = Parts.objects.create(
            tenant=self.tenant, ERP_id="P-NORMAL", work_order=None, order=self.order,
            part_status=PartsStatus.PENDING,
        )
        results = bulk_set_status(
            tenant_id=self.tenant.id,
            part_ids=[part.id],
            new_status=PartsStatus.IN_PROGRESS,
            operator=self.operator,
        )
        self.assertTrue(results[0].ok)
        part.refresh_from_db()
        self.assertEqual(part.part_status, PartsStatus.IN_PROGRESS)

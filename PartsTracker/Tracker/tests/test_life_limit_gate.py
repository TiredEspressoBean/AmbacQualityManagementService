"""Life-limit gate in the advancement engine.

A part carrying a `LifeTracking` record past its hard limit (EXPIRED /
`is_blocked`) must not advance. The gate reads the LIVE `is_blocked` property, so
calendar-based shelf-life expiries are caught even when the cached status is
stale. Release is a formal, audited limit extension (`apply_override`), not a
`StepOverride`. Scope is the part's own tracking (installed-component life is a
later enhancement). Mirrors the FPI-gate test setup (`test_fpi_gate.py`).
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from Tracker.models import (
    PartTypes,
    Parts,
    Processes,
    ProcessStep,
    StepExecution,
    Steps,
    Tenant,
    WorkOrder,
    WorkOrderStatus,
)
from Tracker.models.life_tracking import LifeLimitDefinition, LifeTracking
from Tracker.services.mes.advancement import try_advance_lot
from Tracker.tests.base import TenantContextMixin


class LifeLimitGateTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Life", slug="life-gate", tier="PRO")
        self.set_tenant_context(self.tenant)
        User = get_user_model()
        self.user = User.objects.create_user(
            username="op-life", email="life@c.test", password="x", tenant=self.tenant,
        )
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Nozzle")
        self.process = Processes.objects.create(tenant=self.tenant, name="P", part_type=self.pt)
        # step1 is the gated origin; step2 is the destination.
        self.step1 = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Op1", step_type="TASK",
        )
        self.step2 = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Op2", step_type="TASK",
        )
        ProcessStep.objects.create(process=self.process, step=self.step1, order=1)
        ProcessStep.objects.create(process=self.process, step=self.step2, order=2)
        self.wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-LIFE-1",
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=1, process=self.process,
        )
        self.part = Parts.objects.create(
            tenant=self.tenant, ERP_id="P-LIFE-1", part_type=self.pt,
            work_order=self.wo, step=self.step1,
        )
        StepExecution.objects.create(
            tenant=self.tenant, part=self.part, step=self.step1, visit_number=1, status="IN_PROGRESS",
        )
        self.cycles_def = LifeLimitDefinition.objects.create(
            tenant=self.tenant, name="Injection Cycles", unit="cycles",
            unit_label="Cycles", is_calendar_based=False, hard_limit=Decimal("1000000"),
        )
        self.shelf_def = LifeLimitDefinition.objects.create(
            tenant=self.tenant, name="Shelf Life", unit="days",
            unit_label="Days", is_calendar_based=True, hard_limit=Decimal("365"),
        )

    def _advance(self):
        return try_advance_lot(
            work_order_id=str(self.wo.id), step_id=str(self.step1.id),
            tenant_id=str(self.tenant.id), operator=self.user,
        )

    def _life_blocked(self, result):
        return any(
            "Life limit exceeded" in b
            for lst in result.blockers_by_part.values() for b in lst
        )

    def test_advances_when_within_limit(self):
        LifeTracking.for_object(self.part, self.cycles_def, accumulated=Decimal("500000"))
        result = self._advance()
        self.assertEqual(result.status, "advanced")
        self.part.refresh_from_db()
        self.assertEqual(self.part.step_id, self.step2.id)

    def test_no_gate_without_life_tracking(self):
        # Baseline: a part with no life tracking is unaffected by the gate.
        result = self._advance()
        self.assertEqual(result.status, "advanced")
        self.assertFalse(self._life_blocked(result))

    def test_blocked_when_accumulated_limit_exceeded(self):
        LifeTracking.for_object(self.part, self.cycles_def, accumulated=Decimal("1000001"))
        result = self._advance()
        self.assertEqual(result.status, "blocked")
        self.assertTrue(self._life_blocked(result))
        self.part.refresh_from_db()
        self.assertEqual(self.part.step_id, self.step1.id, "expired part must not leave the step")

    def test_blocked_when_calendar_shelf_life_expired_despite_stale_cache(self):
        # Reference date 400 days ago > 365-day hard limit → live is_blocked True.
        tracking, _ = LifeTracking.for_object(
            self.part, self.shelf_def,
            reference_date=timezone.now().date() - timedelta(days=400),
        )
        # Force a stale cache (as if saved while still within limit): the gate
        # must NOT rely on cached_status.
        LifeTracking.objects.filter(pk=tracking.pk).update(cached_status="OK")
        result = self._advance()
        self.assertEqual(result.status, "blocked")
        self.assertTrue(self._life_blocked(result))

    def test_limit_extension_override_unblocks(self):
        tracking, _ = LifeTracking.for_object(
            self.part, self.cycles_def, accumulated=Decimal("1000001"),
        )
        # Domain-correct release: extend the hard limit (audited) — not a StepOverride.
        tracking.apply_override(
            hard_limit=Decimal("1200000"), reason="Engineering extension", approved_by=self.user,
        )
        result = self._advance()
        self.assertEqual(result.status, "advanced")
        self.part.refresh_from_db()
        self.assertEqual(self.part.step_id, self.step2.id)

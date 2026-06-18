"""Concurrency guard for the advancement engine.

The engine moves parts off a (WO, step) by reading the cohort, gating it, then
advancing. Without a lock, two simultaneous movers (operator complete_step, a
batch seal, the async advance_lot_task, reactive events) both read the same
stale snapshot and both advance — duplicating StepExecution / traveler rows and
double-advancing the lot, with no uniqueness constraint to catch it.

`_evaluate_and_advance` now takes SELECT ... FOR UPDATE on the cohort rows
(held across gate + advance by the caller's transaction), so the second mover
blocks, re-reads the post-move state, and no-ops.

Uses TransactionTestCase + real threads: select_for_update only serializes
across *committed* connections, which a transaction-wrapped TestCase can't
exercise.
"""
import threading
import time
from unittest import mock

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TransactionTestCase

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
import Tracker.services.mes.parts as parts_module
from Tracker.services.mes.advancement import try_advance_lot
from Tracker.tests.base import TenantContextMixin


class AdvancementConcurrencyTests(TenantContextMixin, TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Conc", slug="conc-adv", tier="PRO")
        self.set_tenant_context(self.tenant)
        User = get_user_model()
        self.user = User.objects.create_user(
            username="op-conc", email="cc@c.test", password="x", tenant=self.tenant,
        )
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Widget")
        self.process = Processes.objects.create(tenant=self.tenant, name="P", part_type=self.pt)
        self.step1 = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Op1", step_type="TASK",
        )
        self.step2 = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Op2", step_type="TASK",
        )
        ProcessStep.objects.create(process=self.process, step=self.step1, order=1)
        ProcessStep.objects.create(process=self.process, step=self.step2, order=2)
        self.wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-CC-1",
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=1, process=self.process,
        )
        self.part = Parts.objects.create(
            tenant=self.tenant, ERP_id="P-CC-1", part_type=self.pt,
            work_order=self.wo, step=self.step1,
        )
        StepExecution.objects.create(
            tenant=self.tenant, part=self.part, step=self.step1, visit_number=1, status="IN_PROGRESS",
        )

    def test_concurrent_advances_move_part_exactly_once(self):
        wo_id, step_id, ten_id = str(self.wo.id), str(self.step1.id), str(self.tenant.id)
        barrier = threading.Barrier(2)
        errors: list[Exception] = []

        real_advance = parts_module.advance_part_step

        def slow_advance(*args, **kwargs):
            # Widen the gate→advance window. An UNLOCKED engine would let the
            # second mover read the still-at-step1 snapshot during this sleep
            # and double-advance; the lock makes the second mover block here.
            time.sleep(0.4)
            return real_advance(*args, **kwargs)

        def worker():
            try:
                barrier.wait(timeout=10)
                try_advance_lot(
                    work_order_id=wo_id, step_id=step_id, tenant_id=ten_id, operator=self.user,
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)
            finally:
                connection.close()

        with mock.patch.object(parts_module, "advance_part_step", side_effect=slow_advance):
            t1 = threading.Thread(target=worker)
            t2 = threading.Thread(target=worker)
            t1.start()
            t2.start()
            t1.join(timeout=20)
            t2.join(timeout=20)

        self.assertEqual(errors, [], f"worker errors: {errors}")
        # Exactly one advance happened — the lock serialized the two movers and
        # the second saw the moved state and no-op'd. Without the lock this is 2.
        self.assertEqual(
            StepExecution.objects.filter(part=self.part, step=self.step2).count(),
            1,
            "expected exactly one StepExecution at step2 (no duplicate advance)",
        )
        self.part.refresh_from_db()
        self.assertEqual(self.part.step_id, self.step2.id)

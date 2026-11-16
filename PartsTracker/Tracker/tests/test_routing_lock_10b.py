"""10b (user rulings 2026-11-16): a step's machines and the pooled tooling it needs are
controlled content.

- On a step an approved process owns they change only through a process change; the
  API, delete and import refuse, a draft's own copy is edited freely.
- The setup workbook may load machine eligibility onto approved processes' steps while
  the tenant has started no work — and the write is marked in the audit log.
- Each tracked tooling pool a step needs must have an item in service and within life,
  or the start is refused naming the pool; an untracked pool never refuses.
- The process change's diff shows machine and tooling changes.
"""
from decimal import Decimal

from Tracker.models import (
    Equipments, EquipmentType, Fixture, Parts, PartTypes, Processes, ProcessStep,
    StepEquipmentAffinity, StepExecution, Steps, WorkOrder,
)
from Tracker.models.life_tracking import LifeLimitDefinition
from Tracker.services.mes.gates import StartRefused
from Tracker.services.mes.lifecycle import start_execution
from Tracker.services.mes.step_gates import FLOOR_GATES, set_step_gates
from Tracker.tests.base import TenantTestCase


class RoutingLockTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        t = self.tenant_a
        self.pt = PartTypes.objects.create(tenant=t, name="Body")
        self.process = Processes.objects.create(tenant=t, name="Body line", part_type=self.pt,
                                                status="APPROVED")
        self.step = Steps.objects.create(tenant=t, name="Press", part_type=self.pt)
        ProcessStep.objects.create(process=self.process, step=self.step, order=1)
        self.press = Equipments.objects.create(tenant=t, name="Press 1")
        self.authenticate_superuser(self.tenant_a)

    # --- the lock -----------------------------------------------------------
    def test_an_approved_processs_step_doesnt_take_a_machine_over_the_api(self):
        r = self.client.post("/api/StepEquipmentAffinities/", {
            "step": str(self.step.id), "equipment": str(self.press.id), "affinity": "preferred",
        }, format="json")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("through a process change", str(r.data))
        self.assertFalse(StepEquipmentAffinity.objects.filter(step=self.step).exists())

    def test_a_drafts_step_takes_one(self):
        Processes.objects.filter(pk=self.process.pk).update(status="DRAFT")
        r = self.client.post("/api/StepEquipmentAffinities/", {
            "step": str(self.step.id), "equipment": str(self.press.id), "affinity": "preferred",
        }, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertIs(r.json()["step_locked"], False)

    def test_removing_a_machine_from_an_approved_step_is_refused(self):
        aff = StepEquipmentAffinity.objects.create(tenant=self.tenant_a, step=self.step,
                                                   equipment=self.press, affinity="preferred")
        r = self.client.delete(f"/api/StepEquipmentAffinities/{aff.id}/")
        self.assertEqual(r.status_code, 400, r.content)
        aff.refresh_from_db()
        self.assertFalse(aff.archived)

    def test_the_setup_workbook_may_load_before_any_work_starts_and_says_so(self):
        from django.core.exceptions import ValidationError
        from auditlog.models import LogEntry
        from Tracker.services.change_control.routing_lock import (
            assert_step_routing_editable, setup_load,
        )
        with setup_load():
            self.assertTrue(assert_step_routing_editable(self.step))   # went ahead, under the exception
            aff = StepEquipmentAffinity.objects.create(tenant=self.tenant_a, step=self.step,
                                                       equipment=self.press, affinity="preferred")
        entry = LogEntry.objects.get_for_object(aff).first()
        self.assertEqual((entry.additional_data or {}).get("source"), "Loaded by the setup workbook")
        with self.assertRaises(ValidationError):
            assert_step_routing_editable(self.step)   # outside the workbook: refused
        # Once anything has been worked, the exception is gone.
        wo = WorkOrder.objects.create(tenant=self.tenant_a, ERP_id="WO-LIVE", quantity=1,
                                      workorder_status="IN_PROGRESS", process=self.process)
        part = Parts.objects.create(tenant=self.tenant_a, ERP_id="LIVE-1", part_type=self.pt,
                                    work_order=wo, step=self.step)
        from django.utils import timezone
        StepExecution.objects.create(tenant=self.tenant_a, part=part, step=self.step,
                                     status="IN_PROGRESS", started_at=timezone.now())
        with setup_load(), self.assertRaises(ValidationError):
            assert_step_routing_editable(self.step)

    def test_tooling_changes_on_an_approved_process_through_a_process_change(self):
        shims = Fixture.objects.create(tenant=self.tenant_a, name="Shim kit", quantity=2)
        r = self.client.patch(f"/api/Steps/{self.step.id}/?process={self.process.id}",
                              {"required_tooling": [str(shims.id)]}, format="json")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("through a process change", str(r.data))

    # --- the gate: each needed pool has a usable item --------------------------
    def _pool_step(self):
        die_type = EquipmentType.objects.create(tenant=self.tenant_a, name="Collet chuck")
        LifeLimitDefinition.objects.create(tenant=self.tenant_a, name="Chuck cycles", unit="parts",
                                           unit_label="Parts", hard_limit=Decimal(1),
                                           equipment_type=die_type)
        chuck = Equipments.objects.create(tenant=self.tenant_a, name="Chuck A", equipment_type=die_type)
        pool = Fixture.objects.create(tenant=self.tenant_a, name="Collet chucks", equipment_type=die_type)
        self.step.required_tooling.add(pool)
        set_step_gates(self.step, [{'gate': g} for g in FLOOR_GATES] + [{'gate': 'tool_life'}])
        wo = WorkOrder.objects.create(tenant=self.tenant_a, ERP_id="WO-POOL", quantity=2,
                                      workorder_status="IN_PROGRESS")
        visits = [StepExecution.objects.create(
            tenant=self.tenant_a, step=self.step, visit_number=1, status="PENDING",
            part=Parts.objects.create(tenant=self.tenant_a, ERP_id=f"POOL-{i}", part_type=self.pt,
                                      work_order=wo, step=self.step, part_status="IN_PROGRESS"))
            for i in range(2)]
        return chuck, visits

    def test_a_needed_pool_with_nothing_usable_refuses_naming_it(self):
        from Tracker.models.qms import StepExecutionEquipment
        chuck, visits = self._pool_step()
        start_execution(visits[0], self.user_a)   # Chuck A runs it — and reaches its limit
        self.assertTrue(StepExecutionEquipment.objects.filter(
            step_execution=visits[0], equipment=chuck).exists())
        with self.assertRaises(StartRefused) as ctx:
            start_execution(StepExecution.objects.get(pk=visits[1].pk), self.user_a)
        self.assertIn("None of Collet chucks is usable", " ".join(ctx.exception.messages))

    def test_an_untracked_pool_never_refuses(self):
        prog = Fixture.objects.create(tenant=self.tenant_a, name="NC program 12", quantity=0)
        self.step.required_tooling.add(prog)
        from Tracker.services.life_tracking.tool_life import start_refusals
        self.assertEqual(start_refusals(Steps.objects.get(pk=self.step.pk)), [])

    # --- the diff ---------------------------------------------------------------
    def test_the_process_change_shows_machine_and_tooling_changes(self):
        from Tracker.services.change_control.diff import _diff_routing
        shims = Fixture.objects.create(tenant=self.tenant_a, name="Shim kit", quantity=2)
        other = Steps.objects.create(tenant=self.tenant_a, name="Press", part_type=self.pt)
        StepEquipmentAffinity.objects.create(tenant=self.tenant_a, step=other, equipment=self.press,
                                             affinity="preferred")
        other.required_tooling.add(shims)
        changes = _diff_routing(self.step, other)
        self.assertEqual(changes["machines"], {"from": "none", "to": "Press 1 (preferred)"})
        self.assertEqual(changes["tooling"], {"from": "none", "to": "Shim kit"})

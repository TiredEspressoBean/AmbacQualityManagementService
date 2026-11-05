"""A failed batch load's disposition reaches the load's parts.

A failed batch cycle quarantines the load's members and opens ONE disposition for the
load (part null). Deciding it did nothing to the members — every one stayed held until
changed by hand. Now the decision applies to the whole load, or to the held parts QA
chooses in the decide dialog (user decision 2026-11-05); each chosen part gets its own
disposition, decided like any part's, and the parts not chosen stay held.
"""
from Tracker.models import (
    BatchExecution, Parts, PartsStatus, PartTypes, Processes, ProcessStep,
    QualityReports, QuarantineDisposition, Steps, Substep, WorkOrder, WorkOrderStatus,
)
from Tracker.tests.base import TenantTestCase


class LoadDispositionTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        t = self.tenant_a
        self.pt = PartTypes.objects.create(tenant=t, name="Shaft")
        self.process = Processes.objects.create(tenant=t, name="P", part_type=self.pt,
                                                status="APPROVED")
        self.wash = Steps.objects.create(tenant=t, part_type=self.pt, name="Wash", step_type="TASK")
        self.rework = Steps.objects.create(tenant=t, part_type=self.pt, name="Rework",
                                           step_type="REWORK")
        ProcessStep.objects.create(process=self.process, step=self.wash, order=1)
        ProcessStep.objects.create(process=self.process, step=self.rework, order=2)
        # A rework step re-inspects (2d): without an inspection point nothing routes there.
        Substep.objects.create(tenant=t, step=self.rework, order=0, title="Re-inspect rework",
                               is_inspection_point=True)
        self.wo = WorkOrder.objects.create(
            tenant=t, ERP_id="WO-LOAD", workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=4, process=self.process)
        self.parts = [
            Parts.objects.create(tenant=t, ERP_id=f"P-{i}", part_type=self.pt, work_order=self.wo,
                                 step=self.wash, part_status=PartsStatus.IN_PROGRESS)
            for i in range(3)
        ]
        # One already past the step: never held, never offered.
        self.done = Parts.objects.create(tenant=t, ERP_id="P-DONE", part_type=self.pt,
                                         work_order=self.wo, step=self.wash,
                                         part_status=PartsStatus.COMPLETED)
        self.batch = BatchExecution.objects.create(tenant=t, work_order=self.wo, step=self.wash,
                                                   started_by=self.user_a)
        self.batch.parts.set(self.parts + [self.done])
        QualityReports.objects.create(tenant=t, batch_execution=self.batch, step=self.wash,
                                      status="FAIL", description="cycle fail",
                                      detected_by=self.user_a)
        self.load = QuarantineDisposition.objects.get(batch_execution=self.batch, part__isnull=True)
        self.authenticate_superuser(self.tenant_a)

    def _decide(self, disposition_type, parts=None, **extra):
        body = {"disposition_type": disposition_type, **extra}
        if parts is not None:
            body["parts"] = [str(p.id) for p in parts]
        return self.client.post(f"/api/QuarantineDispositions/{self.load.id}/decide/", body,
                                format="json")

    def _status(self, part):
        part.refresh_from_db()
        return part.part_status

    def test_the_failed_cycle_holds_the_load(self):
        self.assertEqual([self._status(p) for p in self.parts], [PartsStatus.QUARANTINED] * 3)
        self.assertEqual(self._status(self.done), PartsStatus.COMPLETED)

    def test_a_whole_load_decision_reaches_every_held_part(self):
        r = self._decide("SCRAP")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual([self._status(p) for p in self.parts], [PartsStatus.SCRAPPED] * 3)
        self.assertEqual(self._status(self.done), PartsStatus.COMPLETED)  # not touched
        self.load.refresh_from_db()
        self.assertEqual(self.load.disposition_type, "SCRAP")
        self.assertEqual(self.load.decision_authorized_by_id, self.superuser.id)
        own = QuarantineDisposition.objects.filter(load_disposition=self.load)
        self.assertFalse(own.filter(batch_execution__isnull=False).exists())  # a part's, not a load's
        self.assertEqual(sorted(own.values_list("part__ERP_id", flat=True)), ["P-0", "P-1", "P-2"])
        self.assertTrue(all(d.disposition_type == "SCRAP" and d.decision_authorized_by_id
                            for d in own))

    def test_chosen_parts_are_decided_and_the_rest_stay_held(self):
        r = self._decide("SCRAP", parts=[self.parts[0]])
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self._status(self.parts[0]), PartsStatus.SCRAPPED)
        self.assertEqual([self._status(p) for p in self.parts[1:]], [PartsStatus.QUARANTINED] * 2)
        self.load.refresh_from_db()
        self.assertEqual((self.load.disposition_type or "", self.load.current_state), ("", "IN_PROGRESS"))
        self.assertIn("Scrap for P-0", self.load.resolution_notes)
        members = {m["erp_id"]: m for m in r.json()["affected_parts"]}
        self.assertFalse(members["P-0"]["awaiting_decision"])
        self.assertEqual(members["P-0"]["disposition_type"], "SCRAP")
        self.assertTrue(members["P-1"]["awaiting_decision"])
        self.assertFalse(members["P-DONE"]["awaiting_decision"])
        self.assertIn("2 held part(s) in the load still need a decision",
                      self.load.get_completion_blockers())

        # The rest, with a different decision — a load decided in parts.
        r = self._decide("USE_AS_IS", parts=self.parts[1:], customer_approval_reference="DEV-7")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual([self._status(p) for p in self.parts[1:]], [PartsStatus.IN_PROGRESS] * 2)
        self.load.refresh_from_db()
        blockers = self.load.get_completion_blockers()
        self.assertFalse(any("still need a decision" in b for b in blockers))
        self.assertTrue(any("part disposition(s) from this load are still open" in b for b in blockers))

    def test_rework_sends_each_chosen_part_to_the_rework_step(self):
        r = self._decide("REWORK", parts=self.parts[:2])
        self.assertEqual(r.status_code, 200, r.content)
        for p in self.parts[:2]:
            p.refresh_from_db()
            self.assertEqual(p.step_id, self.rework.id)
        self.assertEqual(self._status(self.parts[2]), PartsStatus.QUARANTINED)

    def test_only_parts_waiting_for_the_decision_can_be_chosen(self):
        r = self._decide("SCRAP", parts=[self.done])  # never held
        self.assertEqual(r.status_code, 400, r.content)
        self._decide("SCRAP", parts=[self.parts[0]])
        r = self._decide("SCRAP", parts=[self.parts[0]])  # already decided
        self.assertEqual(r.status_code, 400, r.content)
        self.assertEqual(self._status(self.parts[1]), PartsStatus.QUARANTINED)

    def test_nothing_left_to_decide_is_refused(self):
        self._decide("SCRAP")
        r = self._decide("SCRAP")
        self.assertEqual(r.status_code, 400, r.content)

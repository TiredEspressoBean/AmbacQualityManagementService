"""A failed batch load is one NCR over its parts, each with its own decision.

A failed batch cycle quarantines the load's members and raises ONE NCR for the load
(batch_execution set), with a disposition for each held part (user ruling 2026-11-17:
the load-parent disposition went away). QA decides the NCR for every part still waiting,
or for the parts chosen in the decide dialog (user decision 2026-11-05); each part's
decision is its own disposition's, and the parts not chosen stay held.
"""
from Tracker.models import (
    NCR, BatchExecution, Parts, PartsStatus, PartTypes, Processes, ProcessStep,
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
        self.report = QualityReports.objects.create(
            tenant=t, batch_execution=self.batch, step=self.wash, status="FAIL",
            description="cycle fail", detected_by=self.user_a)
        self.ncr = NCR.objects.get(batch_execution=self.batch)
        self.authenticate_superuser(self.tenant_a)

    def _decide(self, disposition_type, parts=None, **extra):
        body = {"disposition_type": disposition_type, **extra}
        if parts is not None:
            body["parts"] = [str(p.id) for p in parts]
        return self.client.post(f"/api/NCRs/{self.ncr.id}/decide/", body, format="json")

    def _status(self, part):
        part.refresh_from_db()
        return part.part_status

    def test_the_failed_cycle_holds_the_load_under_one_ncr(self):
        self.assertEqual([self._status(p) for p in self.parts], [PartsStatus.QUARANTINED] * 3)
        self.assertEqual(self._status(self.done), PartsStatus.COMPLETED)
        self.report.refresh_from_db()
        self.assertEqual(self.report.ncr_id, self.ncr.id)
        own = QuarantineDisposition.objects.filter(ncr=self.ncr)
        self.assertEqual(sorted(own.values_list("part__ERP_id", flat=True)), ["P-0", "P-1", "P-2"])
        self.assertTrue(all(not d.disposition_type for d in own))
        self.assertIn("3 held, 1 already past this step", self.ncr.description)

    def test_a_decision_for_all_reaches_every_held_part(self):
        r = self._decide("SCRAP")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual([self._status(p) for p in self.parts], [PartsStatus.SCRAPPED] * 3)
        self.assertEqual(self._status(self.done), PartsStatus.COMPLETED)  # not touched
        own = QuarantineDisposition.objects.filter(ncr=self.ncr)
        self.assertTrue(all(d.disposition_type == "SCRAP" and d.decision_authorized_by_id
                            for d in own))

    def test_chosen_parts_are_decided_and_the_rest_stay_held(self):
        r = self._decide("SCRAP", parts=[self.parts[0]])
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self._status(self.parts[0]), PartsStatus.SCRAPPED)
        self.assertEqual([self._status(p) for p in self.parts[1:]], [PartsStatus.QUARANTINED] * 2)
        members = {m["erp_id"]: m for m in r.json()["members"]}
        self.assertFalse(members["P-0"]["awaiting_decision"])
        self.assertEqual(members["P-0"]["disposition_type"], "SCRAP")
        self.assertTrue(members["P-1"]["awaiting_decision"])
        self.assertFalse(members["P-DONE"]["held"])
        self.assertFalse(members["P-DONE"]["awaiting_decision"])

        # The rest, with a different decision — a load decided in parts.
        r = self._decide("USE_AS_IS", parts=self.parts[1:], customer_approval_reference="DEV-7")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual([self._status(p) for p in self.parts[1:]], [PartsStatus.IN_PROGRESS] * 2)

    def test_the_ncr_closes_with_its_last_decision(self):
        from Tracker.services.qms.disposition import complete_disposition_resolution
        from Tracker.services.qms.ncr import record_containment
        record_containment(self.ncr, action="Load held on the rack.", user=self.superuser)
        self._decide("SCRAP")
        own = list(QuarantineDisposition.objects.filter(ncr=self.ncr))
        for d in own[:-1]:
            complete_disposition_resolution(d, self.superuser)
            self.ncr.refresh_from_db()
            self.assertEqual(self.ncr.state, "OPEN")
        complete_disposition_resolution(own[-1], self.superuser)
        self.ncr.refresh_from_db()
        self.assertEqual(self.ncr.state, "CLOSED")
        self.assertIsNotNone(self.ncr.closed_at)

    def test_containment_is_the_ncrs_and_blocks_closing_a_decision(self):
        from Tracker.services.qms.disposition import complete_disposition_resolution
        self._decide("SCRAP")
        d = QuarantineDisposition.objects.filter(ncr=self.ncr).first()
        with self.assertRaisesMessage(ValueError, f"Containment action required on {self.ncr.ncr_number}"):
            complete_disposition_resolution(d, self.superuser)

    def test_rework_sends_each_chosen_part_to_the_rework_step(self):
        r = self._decide("REWORK", parts=self.parts[:2])
        self.assertEqual(r.status_code, 200, r.content)
        for p in self.parts[:2]:
            p.refresh_from_db()
            self.assertEqual(p.step_id, self.rework.id)
        self.assertEqual(self._status(self.parts[2]), PartsStatus.QUARANTINED)

    def test_only_parts_waiting_for_a_decision_can_be_chosen(self):
        r = self._decide("SCRAP", parts=[self.done])  # never held
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("still waiting for a decision", r.json()["detail"])
        self._decide("SCRAP", parts=[self.parts[0]])
        r = self._decide("SCRAP", parts=[self.parts[0]])  # already decided
        self.assertEqual(r.status_code, 400, r.content)
        self.assertEqual(self._status(self.parts[1]), PartsStatus.QUARANTINED)

    def test_nothing_left_to_decide_is_refused(self):
        self._decide("SCRAP")
        r = self._decide("SCRAP")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("already has a decision", r.json()["detail"])

    def test_a_second_failing_report_joins_the_load_ncr(self):
        second = QualityReports.objects.create(
            tenant=self.tenant_a, batch_execution=self.batch, step=self.wash, status="FAIL",
            description="second check", detected_by=self.user_a)
        second.refresh_from_db()
        self.assertEqual(second.ncr_id, self.ncr.id)
        self.assertEqual(NCR.objects.filter(batch_execution=self.batch).count(), 1)
        self.assertEqual(QuarantineDisposition.objects.filter(ncr=self.ncr).count(), 3)

    def test_a_load_already_past_the_step_is_decided_for_the_record(self):
        """Every part had left the step: none is held, each gets a decision for the
        record, and the NCR says they were past the step (walk 2026-11-18)."""
        from Tracker.services.qms.ncr import members
        t = self.tenant_a
        gone = [Parts.objects.create(tenant=t, ERP_id=f"G-{i}", part_type=self.pt, work_order=self.wo,
                                     step=self.wash, part_status=PartsStatus.COMPLETED) for i in range(2)]
        batch = BatchExecution.objects.create(tenant=t, work_order=self.wo, step=self.wash,
                                              started_by=self.user_a)
        batch.parts.set(gone)
        QualityReports.objects.create(tenant=t, batch_execution=batch, step=self.wash, status="FAIL",
                                      description="late find", detected_by=self.user_a)
        ncr = NCR.objects.get(batch_execution=batch)
        rows = members(ncr)
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r["disposition_id"] and not r["held"] for r in rows))
        self.assertEqual([self._status(p) for p in gone], [PartsStatus.COMPLETED] * 2)


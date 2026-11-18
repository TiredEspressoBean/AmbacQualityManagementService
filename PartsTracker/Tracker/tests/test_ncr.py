"""The NCR as its own record (user ruling 2026-11-17).

One rule: every failed inspection record belongs to an NCR, whichever path created it;
a single part's failure is an NCR with one part, a repeat failure joins the part's open
NCR, and parts are grouped only where the event is one (a load, a first-piece run, a
person's pick). The NCR holds what is wrong; each part's decision is its disposition.
"""
from datetime import date

from Tracker.models import (
    CAPA, NCR, FPIRecord, Parts, PartsStatus, PartTypes, Processes, ProcessStep,
    QualityReports, QuarantineDisposition, Steps, WorkOrder, WorkOrderStatus,
)
from Tracker.tests.base import TenantTestCase


class _Shop(TenantTestCase):
    def setUp(self):
        super().setUp()
        t = self.tenant_a
        self.pt = PartTypes.objects.create(tenant=t, name="Body")
        self.process = Processes.objects.create(tenant=t, name="P", part_type=self.pt,
                                                status="APPROVED")
        self.step = Steps.objects.create(tenant=t, part_type=self.pt, name="Bore", step_type="TASK")
        ProcessStep.objects.create(process=self.process, step=self.step, order=1)
        self.wo = WorkOrder.objects.create(tenant=t, ERP_id="WO-NCR", quantity=4, process=self.process,
                                           workorder_status=WorkOrderStatus.IN_PROGRESS)
        self.parts = [Parts.objects.create(tenant=t, ERP_id=f"B-{i}", part_type=self.pt,
                                           work_order=self.wo, step=self.step,
                                           part_status=PartsStatus.IN_PROGRESS)
                      for i in range(4)]
        self.authenticate_superuser(self.tenant_a)

    def _fail(self, part, **kw):
        return QualityReports.objects.create(tenant=self.tenant_a, part=part, step=part.step,
                                             status="FAIL", detected_by=self.user_a, **kw)

    def _ncr_of(self, report):
        report.refresh_from_db()
        return report.ncr


class EveryFailureIsOnAnNcrTests(_Shop):
    """Each creation path leaves no failed record without an NCR."""

    def tearDown(self):
        try:
            orphans = QualityReports.objects.filter(status="FAIL", ncr__isnull=True)
            self.assertFalse(orphans.exists(),
                             f"failed records with no NCR: {list(orphans.values_list('description', flat=True))}")
            self.assertFalse(QuarantineDisposition.objects.filter(ncr__isnull=True).exists(),
                             "a disposition outside any NCR")
        finally:
            super().tearDown()  # resets the tenant context even when the check fails

    def test_a_failed_report(self):
        ncr = self._ncr_of(self._fail(self.parts[0], description="bore oversize"))
        self.assertIsNotNone(ncr)
        self.assertTrue(ncr.ncr_number.startswith("NCR-"))
        self.assertEqual(ncr.description, "Failed quality report: bore oversize")
        d = QuarantineDisposition.objects.get(part=self.parts[0])
        self.assertEqual(d.ncr_id, ncr.id)

    def test_a_hand_filed_report_through_the_api(self):
        r = self.client.post("/api/QualityReports/", {
            "part": str(self.parts[0].id), "step": str(self.step.id), "status": "FAIL",
            "description": "chip on seat", "detected_by": self.user_a.id}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertIsNotNone(QualityReports.objects.get(pk=r.json()["id"]).ncr_id)

    def test_operator_rework(self):
        from Tracker.services.qms.disposition import record_operator_rework
        d = record_operator_rework(self.parts[0], self.user_a, "burr on the bore")
        self.assertIsNotNone(d.ncr_id)
        self.assertEqual(d.ncr.description, "Sent to rework at Bore: burr on the bore")

    def test_mrb_escalation(self):
        from Tracker.services.qms.mrb import open_for_escalation
        d = open_for_escalation(self.parts[0], capped_step=self.step, visits=3)
        self.assertIsNotNone(d.ncr_id)
        self.assertIn("Visit cap reached", d.resolution_notes)

    def test_first_piece_run_with_several_bad_pieces_is_one_ncr(self):
        from Tracker.services.qms.fpi import fail_fpi
        fpi = FPIRecord.objects.create(tenant=self.tenant_a, work_order=self.wo, step=self.step,
                                       part_type=self.pt, designated_part=self.parts[0], status="PENDING")
        fpi.first_piece_parts.set(self.parts[:2])
        fail_fpi(fpi, self.user_b, notes="bore oversize", bad_part_ids=[p.id for p in self.parts[:2]])
        ncrs = set(QualityReports.objects.filter(part__in=self.parts[:2], status="FAIL")
                   .values_list("ncr_id", flat=True))
        self.assertEqual(len(ncrs), 1)
        ncr = NCR.objects.get(pk=ncrs.pop())
        self.assertEqual(ncr.dispositions.count(), 2)

    def test_raised_by_a_person_over_parts_they_pick(self):
        r = self.client.post("/api/NCRs/", {"parts": [str(p.id) for p in self.parts[:3]],
                                            "description": "Wrong bar stock", "severity": "CRITICAL"},
                             format="json")
        self.assertEqual(r.status_code, 201, r.content)
        ncr = NCR.objects.get(pk=r.json()["id"])
        self.assertEqual((ncr.description, ncr.severity, ncr.step_id, ncr.work_order_id),
                         ("Wrong bar stock", "CRITICAL", self.step.id, self.wo.id))
        self.assertEqual(sorted(m["erp_id"] for m in r.json()["members"]), ["B-0", "B-1", "B-2"])
        self.assertEqual(QualityReports.objects.filter(ncr=ncr, status="FAIL").count(), 3)
        for p in self.parts[:3]:
            p.refresh_from_db()
            self.assertEqual(p.part_status, PartsStatus.QUARANTINED)

    def test_parts_added_to_an_open_ncr(self):
        ncr = self._ncr_of(self._fail(self.parts[0]))
        r = self.client.post(f"/api/NCRs/{ncr.id}/add-parts/",
                             {"parts": [str(self.parts[1].id)], "reason": "same setup"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(sorted(m["erp_id"] for m in r.json()["members"]), ["B-0", "B-1"])
        r = self.client.post(f"/api/NCRs/{ncr.id}/add-parts/", {"parts": [str(self.parts[1].id)]},
                             format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["detail"], f"Already on {ncr.ncr_number}: B-1.")


class LotRejectTests(TenantTestCase):
    def tearDown(self):
        try:
            self.assertFalse(QualityReports.objects.filter(status="FAIL", ncr__isnull=True).exists())
        finally:
            super().tearDown()

    def test_a_rejected_lot_is_decided_under_its_inspections_ncr(self):
        from Tracker.models import Companies, Material, MaterialLot
        from Tracker.services.qms.lot_reject import reject_lot
        from Tracker.services.qms.receiving_inspection import create_standalone_receiving_plan
        self.authenticate_superuser(self.tenant_a)
        acme = Companies.objects.create(tenant=self.tenant_a, name="Acme")
        seal = Material.objects.create(tenant=self.tenant_a, name="Seal", unit_of_measure="EA")
        create_standalone_receiving_plan(seal)
        r = self.client.post("/api/MaterialLots/", {
            "lot_number": "L-1", "material": str(seal.id), "quantity": "100",
            "received_date": str(date.today()), "unit_of_measure": "EA",
            "supplier": str(acme.id)}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        lot = MaterialLot.objects.get(pk=r.json()["id"])
        report = lot.quality_reports.order_by("-created_at").first()
        _, disposition, _ = reject_lot(report, self.superuser, whole_lot=True,
                                       description="Flash on the parting line", severity="MINOR")
        self.assertEqual((disposition.ncr.description, disposition.ncr.severity),
                         ("Flash on the parting line", "MINOR"))
        report.refresh_from_db()
        self.assertEqual(report.ncr_id, disposition.ncr_id)


class RepeatFailureTests(_Shop):
    def test_a_repeat_failure_joins_the_parts_open_ncr(self):
        first = self._ncr_of(self._fail(self.parts[0]))
        second = self._ncr_of(self._fail(self.parts[0], description="again"))
        self.assertEqual(first.id, second.id)

    def test_once_closed_a_new_failure_is_a_new_ncr(self):
        from Tracker.services.qms.disposition import complete_disposition_resolution, decide_disposition
        from Tracker.services.qms.ncr import record_containment
        ncr = self._ncr_of(self._fail(self.parts[0]))
        record_containment(ncr, action="Held.", user=self.superuser)
        d = ncr.dispositions.get()
        decide_disposition(d, disposition_type="SCRAP", authorized_by=self.superuser)
        complete_disposition_resolution(d, self.superuser)
        ncr.refresh_from_db()
        self.assertEqual(ncr.state, "CLOSED")
        self.parts[1].refresh_from_db()
        again = self._ncr_of(self._fail(self.parts[1]))
        self.assertNotEqual(again.id, ncr.id)

    def test_separate_parts_failing_separately_are_separate_ncrs(self):
        a = self._ncr_of(self._fail(self.parts[0]))
        b = self._ncr_of(self._fail(self.parts[1]))
        self.assertNotEqual(a.id, b.id)


class NcrHeaderTests(_Shop):
    def test_severity_may_only_rise_once_anything_is_decided(self):
        from Tracker.services.qms.disposition import decide_disposition
        ncr = self._ncr_of(self._fail(self.parts[0]))
        self.assertEqual(self.client.patch(f"/api/NCRs/{ncr.id}/", {"severity": "MINOR"},
                                           format="json").status_code, 200)
        decide_disposition(ncr.dispositions.get(), disposition_type="SCRAP", authorized_by=self.superuser)
        r = self.client.patch(f"/api/NCRs/{ncr.id}/", {"severity": "MINOR"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)  # unchanged — same value
        r = self.client.patch(f"/api/NCRs/{ncr.id}/", {"severity": "CRITICAL"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        r = self.client.patch(f"/api/NCRs/{ncr.id}/", {"severity": "MINOR"}, format="json")
        self.assertEqual(r.status_code, 400, r.content)

    def test_the_disposition_form_writes_the_ncrs_header(self):
        ncr = self._ncr_of(self._fail(self.parts[0]))
        d = ncr.dispositions.get()
        r = self.client.patch(f"/api/QuarantineDispositions/{d.id}/", {
            "containment_action": "Segregated.", "containment_completed": True,
            "description": "Bore 4.007"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        ncr.refresh_from_db()
        self.assertEqual((ncr.containment_action, ncr.description), ("Segregated.", "Bore 4.007"))
        self.assertIsNotNone(ncr.containment_completed_at)
        self.assertEqual(r.json()["ncr_number"], ncr.ncr_number)

    def test_containment_complete_needs_an_action(self):
        ncr = self._ncr_of(self._fail(self.parts[0]))
        r = self.client.post(f"/api/NCRs/{ncr.id}/containment-complete/", format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["detail"], "Describe the containment action before marking it complete.")


class CapaLinkTests(_Shop):
    def test_capa_decision_is_recorded_on_the_ncr(self):
        ncr = self._ncr_of(self._fail(self.parts[0]))
        r = self.client.post(f"/api/NCRs/{ncr.id}/capa-decision/",
                             {"decision": "NOT_REQUIRED", "note": "One-off"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        ncr.refresh_from_db()
        self.assertEqual(ncr.capa_decision, "NOT_REQUIRED")
        listed = self.client.get("/api/NCRs/?capa_decision__isnull=true").json()["results"]
        self.assertNotIn(str(ncr.id), [n["id"] for n in listed])

    def test_a_capa_from_a_report_links_and_promotes_its_ncr(self):
        from Tracker.services.qms.capa_decision import stamp_promoted
        report = self._fail(self.parts[0])
        ncr = self._ncr_of(report)
        self.client.post(f"/api/NCRs/{ncr.id}/add-parts/", {"parts": [str(self.parts[1].id)]},
                         format="json")
        capa = CAPA.objects.create(tenant=self.tenant_a, capa_type="CORRECTIVE", severity="MAJOR",
                                   problem_statement="Bores oversize", initiated_by=self.superuser,
                                   capa_number="CAPA-T-1")
        capa.quality_reports.add(report)
        stamp_promoted(capa, self.superuser)
        ncr.refresh_from_db()
        self.assertEqual(ncr.capa_decision, "PROMOTED")
        self.assertIn(ncr, capa.ncrs.all())
        body = self.client.get(f"/api/CAPAs/{capa.id}/").json()
        self.assertEqual(sorted(body["affected_part_ids"]),
                         sorted(str(p.id) for p in self.parts[:2]))


class NcrOpenedTests(_Shop):
    def test_sent_once_per_ncr_naming_its_parts(self):
        from unittest import mock
        with mock.patch("Tracker.services.core.notifications.emit") as emit:
            with self.captureOnCommitCallbacks(execute=True):
                self.client.post("/api/NCRs/", {"parts": [str(p.id) for p in self.parts[:3]],
                                                "description": "Wrong bar stock"}, format="json")
        sent = [c for c in emit.call_args_list if c.args[0] == "ncr.opened"]
        self.assertEqual(len(sent), 1)
        payload = sent[0].kwargs["payload"]
        self.assertEqual((payload.part_number, payload.part_count, payload.part_id), ("3 parts", 3, None))
        self.assertTrue(payload.ncr_number.startswith("NCR-"))


class NcrPermissionSplitTests(_Shop):
    """User ruling 2026-11-17: raising and adding parts is add_ncr (anyone who can flag a
    problem); the header and containment are change_ncr (leads and QA)."""

    def setUp(self):
        super().setUp()
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            'full_tenant_access', 'view_ncr', 'add_ncr', 'view_parts',
            'view_quarantinedisposition', 'change_quarantinedisposition'])
        self.authenticate_as(self.user_a, self.tenant_a)

    def test_a_flagger_raises_and_adds_parts(self):
        r = self.client.post("/api/NCRs/", {"parts": [str(self.parts[0].id)], "description": "Chatter"},
                             format="json")
        self.assertEqual(r.status_code, 201, r.content)
        r = self.client.post(f"/api/NCRs/{r.json()['id']}/add-parts/", {"parts": [str(self.parts[1].id)]},
                             format="json")
        self.assertEqual(r.status_code, 200, r.content)

    def test_but_not_the_header_or_containment(self):
        ncr = self._ncr_of(self._fail(self.parts[0]))
        self.assertEqual(self.client.patch(f"/api/NCRs/{ncr.id}/", {"severity": "CRITICAL"},
                                           format="json").status_code, 403)
        self.assertEqual(self.client.post(f"/api/NCRs/{ncr.id}/containment-complete/",
                                          format="json").status_code, 403)
        # Not through the disposition either.
        d = ncr.dispositions.get()
        r = self.client.patch(f"/api/QuarantineDispositions/{d.id}/", {"severity": "CRITICAL"}, format="json")
        self.assertEqual(r.status_code, 403, r.content)
        self.assertIn("edited by a lead or QA", r.json()["detail"])
        # A form echoing the header back unchanged is not an edit.
        r = self.client.patch(f"/api/QuarantineDispositions/{d.id}/",
                              {"severity": ncr.severity, "resolution_notes": "note"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)

    def test_the_presets_split_it(self):
        from Tracker.presets import GROUP_PRESETS
        def has(key, perm):
            return perm in GROUP_PRESETS[key]['permissions']
        for key in ('operator', 'qa_inspector', 'shift_lead'):
            self.assertTrue(has(key, 'add_ncr'), key)
        self.assertFalse(has('operator', 'change_ncr'))
        for key in ('qa_inspector', 'qa_manager', 'shift_lead', 'production_manager', 'tenant_admin'):
            self.assertTrue(has(key, 'change_ncr'), key)

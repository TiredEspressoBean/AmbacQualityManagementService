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
        self.assertEqual(ncr.description, "Failed inspection: bore oversize")
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
        # Worded as every other refusal of a lower severity.
        self.assertIn(f"{ncr.ncr_number} is Critical", str(r.content.decode()))
        self.assertIn("its severity may only be raised.", r.content.decode())

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


class NcrCreateDispositionHeaderTests(_Shop):
    """A disposition opened by someone without change_ncr can't write an NCR's
    containment — its text alone would clear the Major/Critical close gate."""

    def test_containment_on_a_new_disposition_needs_change_ncr(self):
        from django.contrib.auth import get_user_model
        operator = get_user_model().objects.create_user(
            username="ncr-op", email="ncr-op@t.test", password="x", tenant=self.tenant_a)
        self.grant_tenant_permissions(operator, self.tenant_a, [
            'full_tenant_access', 'view_quarantinedisposition', 'add_quarantinedisposition', 'add_ncr'])
        self.authenticate_as(operator, self.tenant_a)
        report = self._fail(self.parts[0])
        ncr = self._ncr_of(report)
        r = self.client.post("/api/QuarantineDispositions/", {
            "part": str(self.parts[0].id), "quality_reports": [str(report.id)],
            "containment_action": "segregated"}, format="json")
        # Refused, not silently dropped (merged review P1#5).
        self.assertEqual(r.status_code, 403, r.content)
        ncr.refresh_from_db()
        self.assertEqual(ncr.containment_action, "")

    def test_containment_complete_on_a_closed_ncr_is_refused(self):
        from Tracker.services.qms.ncr import record_containment_complete
        ncr = self._ncr_of(self._fail(self.parts[0]))
        NCR.objects.filter(pk=ncr.pk).update(state="CLOSED", containment_action="held")
        ncr.refresh_from_db()
        with self.assertRaisesMessage(ValueError, "is closed"):
            record_containment_complete(ncr, self.user_a)


class ReviewFixesTests(_Shop):
    """Edge cases the 2026-11-17 review found."""

    def test_a_part_done_with_a_load_ncr_doesnt_rejoin_it(self):
        from Tracker.services.qms.ncr import open_ncr_for_part, record_containment
        from Tracker.services.qms.disposition import complete_disposition_resolution, decide_disposition
        r = self.client.post("/api/NCRs/", {"parts": [str(p.id) for p in self.parts[:2]],
                                            "description": "Wrong bar"}, format="json")
        ncr = NCR.objects.get(pk=r.json()["id"])
        record_containment(ncr, action="Held.", user=self.superuser)
        mine = ncr.dispositions.get(part=self.parts[0])
        decide_disposition(mine, disposition_type="SCRAP", authorized_by=self.superuser)
        complete_disposition_resolution(mine, self.superuser)
        ncr.refresh_from_db()
        self.assertEqual(ncr.state, "OPEN")              # its sibling still waits
        self.assertIsNone(open_ncr_for_part(self.parts[0]))  # but it's done with this one
        self.assertEqual(open_ncr_for_part(self.parts[1]), ncr)

    def test_severity_rises_with_the_findings_until_a_decision(self):
        from Tracker.models import QualityErrorsList, QualityReportDefect
        from Tracker.services.qms.ncr import refresh_description
        report = self._fail(self.parts[0])
        ncr = self._ncr_of(report)
        self.assertEqual(ncr.severity, "MAJOR")
        err = QualityErrorsList.objects.create(tenant=self.tenant_a, error_name="Crack")
        QualityReportDefect.objects.create(report=report, error_type=err, severity="CRITICAL")
        refresh_description(ncr)
        ncr.refresh_from_db()
        self.assertEqual(ncr.severity, "CRITICAL")

    def test_an_ncr_with_nothing_decided_closes_when_its_failure_is_withdrawn(self):
        from Tracker.services.qms.ncr import raise_ncr, sync_state
        report = QualityReports.objects.create(tenant=self.tenant_a, status="PENDING",
                                               detected_by=self.user_a)
        ncr = raise_ncr(tenant=self.tenant_a, description="Lot sample", reports=[report])
        QualityReports.objects.filter(pk=report.pk).update(status="FAIL")
        sync_state(ncr.id)
        ncr.refresh_from_db()
        self.assertEqual(ncr.state, "OPEN")
        QualityReports.objects.filter(pk=report.pk).update(status="PASS")
        sync_state(ncr.id)
        ncr.refresh_from_db()
        self.assertEqual(ncr.state, "CLOSED")


class NcrDocumentLinkTests(_Shop):
    """A document can be filed under, or attached to, an NCR — by someone who may view
    NCRs (user ruling 2026-11-18). Containment evidence is the same thing: a document
    filed under the NCR."""

    def _upload(self, ncr):
        from django.contrib.contenttypes.models import ContentType
        from django.core.files.uploadedfile import SimpleUploadedFile
        return self.client.post("/api/Documents/", {
            "file": SimpleUploadedFile("tag.pdf", b"%PDF-1.4"), "file_name": "tag.pdf",
            "classification": "INTERNAL",
            "content_type": ContentType.objects.get_for_model(NCR).id, "object_id": str(ncr.id),
        }, format="multipart")

    def _as(self, perms):
        from django.contrib.auth import get_user_model
        u = get_user_model().objects.create_user(username=f"doc-{len(perms)}", email=f"doc{len(perms)}@t.test",
                                                 password="x", tenant=self.tenant_a)
        self.grant_tenant_permissions(u, self.tenant_a, ['full_tenant_access', 'view_documents',
                                                         'add_documents', *perms])
        self.authenticate_as(u, self.tenant_a)

    def test_filing_a_document_under_an_ncr_needs_view_ncr(self):
        ncr = self._ncr_of(self._fail(self.parts[0]))
        self._as([])
        r = self._upload(ncr)
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("can't view", str(r.json()))
        self._as(['view_ncr'])
        r = self._upload(ncr)
        self.assertEqual(r.status_code, 201, r.content)
        listed = self.client.get(f"/api/Documents/?content_type={r.json()['content_type']}&object_id={ncr.id}")
        self.assertEqual([d["id"] for d in listed.json()["results"]], [r.json()["id"]])



class P1IntegrityTests(_Shop):
    """The 2026-11-18 merged review, P1 (data integrity)."""

    def _close(self, ncr):
        from Tracker.services.qms.disposition import complete_disposition_resolution, decide_disposition
        from Tracker.services.qms.ncr import record_containment
        record_containment(ncr, action="Held.", user=self.superuser)
        for d in ncr.dispositions.all():
            decide_disposition(d, disposition_type="SCRAP", authorized_by=self.superuser)
            complete_disposition_resolution(d, self.superuser)
        ncr.refresh_from_db()
        self.assertEqual(ncr.state, "CLOSED")

    def test_voiding_a_fail_after_its_ncr_closed_raises_nothing(self):
        from django.utils import timezone
        report = self._fail(self.parts[0])
        ncr = self._ncr_of(report)
        self._close(ncr)
        report.superseded_at = timezone.now()
        report.save()
        report.refresh_from_db()
        self.assertEqual(report.ncr_id, ncr.id)
        self.assertEqual(NCR.objects.filter(tenant=self.tenant_a).count(), 1)

    def test_a_resave_of_a_failed_record_doesnt_move_it(self):
        report = self._fail(self.parts[0])
        ncr = self._ncr_of(report)
        self._close(ncr)
        report.description = "re-saved"
        report.save()
        report.refresh_from_db()
        self.assertEqual(report.ncr_id, ncr.id)

    def test_rollback_settles_only_undecided_decisions(self):
        from Tracker.services.mes.parts import _settle_dispositions_on_rollback
        from Tracker.services.qms.disposition import decide_disposition
        ncr = self._ncr_of(self._fail(self.parts[0]))
        d = ncr.dispositions.get()
        decide_disposition(d, disposition_type="REWORK", authorized_by=self.superuser)
        _settle_dispositions_on_rollback(self.parts[0], self.superuser, self.step, self.step, "back")
        d.refresh_from_db()
        self.assertEqual((d.disposition_type, d.current_state), ("REWORK", "IN_PROGRESS"))

    def test_mrb_adopts_the_undecided_decision_not_an_older_decided_one(self):
        from Tracker.services.qms.disposition import decide_disposition
        from Tracker.services.qms.mrb import open_for_failure
        from Tracker.tests.base import make_disposition
        old = make_disposition(tenant=self.tenant_a, part=self.parts[0], step=self.step)
        decide_disposition(old, disposition_type="REWORK", authorized_by=self.superuser)
        new = make_disposition(tenant=self.tenant_a, part=self.parts[0], step=self.step)
        self.assertEqual(open_for_failure(self.parts[0], failed_step=self.step).pk, new.pk)

    def test_the_one_header_rule(self):
        from Tracker.services.qms.disposition import decide_disposition
        from Tracker.services.qms.ncr import HeaderRefused, write_header
        ncr = self._ncr_of(self._fail(self.parts[0]))
        # Still being raised: the raiser says what's wrong, even below the MAJOR default.
        write_header(ncr, {"description": "Chatter", "severity": "MINOR"}, self.user_a)
        ncr.refresh_from_db()
        self.assertEqual((ncr.description, ncr.severity, ncr.header_by_hand), ("Chatter", "MINOR", True))
        # Written by hand now: change_ncr's, refused without it — not dropped.
        with self.assertRaises(HeaderRefused):
            write_header(ncr, {"description": "Other"}, self.user_a)
        # Containment is always change_ncr's.
        other = self._ncr_of(self._fail(self.parts[1]))
        with self.assertRaises(HeaderRefused):
            write_header(other, {"containment_action": "held"}, self.user_a)
        # Written by hand but nothing decided: still being judged, so it can come down.
        write_header(ncr, {"severity": "CRITICAL"}, self.superuser)
        write_header(ncr, {"severity": "MINOR"}, self.superuser)
        ncr.refresh_from_db()
        self.assertEqual(ncr.severity, "MINOR")
        # Never lowered once decided.
        decide_disposition(other.dispositions.get(), disposition_type="SCRAP", authorized_by=self.superuser)
        with self.assertRaisesMessage(ValueError, "may only be raised"):
            write_header(other, {"severity": "MINOR"}, self.superuser)

    def test_severity_follows_the_findings_down_too(self):
        from Tracker.models import QualityErrorsList, QualityReportDefect
        from Tracker.services.qms.ncr import refresh_description
        report = self._fail(self.parts[0])
        ncr = self._ncr_of(report)
        self.assertEqual(ncr.severity, "MAJOR")
        err = QualityErrorsList.objects.create(tenant=self.tenant_a, error_name="Scuff")
        QualityReportDefect.objects.create(report=report, error_type=err, severity="MINOR")
        refresh_description(ncr)
        ncr.refresh_from_db()
        self.assertEqual(ncr.severity, "MINOR")

    def test_a_record_only_decision_holds_nothing(self):
        from Tracker.services.qms.nonconformance import undecided_disposition
        from Tracker.tests.base import make_disposition
        make_disposition(tenant=self.tenant_a, part=self.parts[0], step=self.step, held=False)
        self.assertIsNone(undecided_disposition(self.parts[0]))

    def test_an_ncr_whose_decisions_were_all_removed_closes(self):
        from Tracker.services.qms.ncr import sync_state
        ncr = self._ncr_of(self._fail(self.parts[0]))
        ncr.dispositions.update(archived=True)
        sync_state(ncr.id)
        ncr.refresh_from_db()
        self.assertEqual(ncr.state, "CLOSED")

    def test_linking_ncrs_on_a_capa_needs_initiate_capa_and_unlinking_undecides(self):
        from Tracker.models import CAPA
        ncr = self._ncr_of(self._fail(self.parts[0]))
        capa = CAPA.objects.create(tenant=self.tenant_a, capa_type="CORRECTIVE", severity="MINOR",
                                   problem_statement="x", initiated_by=self.superuser, capa_number="CAPA-L-1")
        from django.contrib.auth import get_user_model
        helper = get_user_model().objects.create_user(username="capa-helper", email="ch@t.test",
                                                      password="x", tenant=self.tenant_a)
        self.grant_tenant_permissions(helper, self.tenant_a, ['full_tenant_access', 'view_capa', 'change_capa'])
        self.authenticate_as(helper, self.tenant_a)
        r = self.client.patch(f"/api/CAPAs/{capa.id}/", {"ncrs": [str(ncr.id)]}, format="json")
        self.assertEqual(r.status_code, 403, r.content)
        self.authenticate_superuser(self.tenant_a)
        self.assertEqual(self.client.patch(f"/api/CAPAs/{capa.id}/", {"ncrs": [str(ncr.id)]},
                                           format="json").status_code, 200)
        ncr.refresh_from_db()
        self.assertEqual(ncr.capa_decision, "PROMOTED")
        self.assertEqual(self.client.patch(f"/api/CAPAs/{capa.id}/", {"ncrs": []},
                                           format="json").status_code, 200)
        ncr.refresh_from_db()
        self.assertIsNone(ncr.capa_decision)


class CombineNcrsTests(_Shop):
    """Combine NCRs (user go 2026-11-18)."""

    def test_combining_moves_the_decisions_and_records_and_closes_the_others(self):
        from Tracker.models import QualityErrorsList, QualityReportDefect
        a = self._ncr_of(self._fail(self.parts[0]))
        b_report = self._fail(self.parts[1])
        b = self._ncr_of(b_report)
        NCR.objects.filter(pk=b.pk).update(severity="CRITICAL", containment_action="Segregated B")
        r = self.client.post("/api/NCRs/combine/", {"into": str(a.id), "ncrs": [str(b.id)]}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        a.refresh_from_db(); b.refresh_from_db()
        self.assertEqual(QuarantineDisposition.objects.filter(ncr=a).count(), 2)
        self.assertEqual(QualityReports.objects.filter(ncr=a).count(), 2)
        self.assertEqual((a.severity, a.containment_action), ("CRITICAL", "Segregated B"))
        self.assertEqual((b.state, b.combined_into_id), ("CLOSED", a.id))
        self.assertEqual([n["ncr_number"] for n in r.json()["combined_from"]], [b.ncr_number])

    def test_only_open_ncrs_combine_and_change_ncr_is_needed(self):
        a = self._ncr_of(self._fail(self.parts[0]))
        b = self._ncr_of(self._fail(self.parts[1]))
        NCR.objects.filter(pk=b.pk).update(state="CLOSED")
        r = self.client.post("/api/NCRs/combine/", {"into": str(a.id), "ncrs": [str(b.id)]}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Only open NCRs can be combined", r.json()["detail"])
        self.grant_tenant_permissions(self.user_a, self.tenant_a, ['full_tenant_access', 'view_ncr', 'add_ncr'])
        self.authenticate_as(self.user_a, self.tenant_a)
        r = self.client.post("/api/NCRs/combine/", {"into": str(a.id), "ncrs": [str(b.id)]}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_adding_a_part_already_on_another_open_ncr_offers_combine(self):
        a = self._ncr_of(self._fail(self.parts[0]))
        b = self._ncr_of(self._fail(self.parts[1]))
        r = self.client.post(f"/api/NCRs/{a.id}/add-parts/", {"parts": [str(self.parts[1].id)]}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["detail"], f"B-1 is on {b.ncr_number}: combine instead.")

    def test_appended_containment_says_whose_it_was(self):
        from django.utils import timezone
        a = self._ncr_of(self._fail(self.parts[0]))
        b = self._ncr_of(self._fail(self.parts[1]))
        NCR.objects.filter(pk=a.pk).update(containment_action="Segregated A",
                                           containment_completed_at=timezone.now(),
                                           containment_completed_by=self.superuser)
        NCR.objects.filter(pk=b.pk).update(containment_action="Segregated B",
                                           containment_completed_at=timezone.now(),
                                           containment_completed_by=self.user_a)
        r = self.client.post("/api/NCRs/combine/", {"into": str(a.id), "ncrs": [str(b.id)]}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        a.refresh_from_db()
        first, appended = a.containment_action.split("\n")
        self.assertEqual(first, "Segregated A")
        self.assertTrue(appended.startswith(f"From {b.ncr_number} ({self.user_a.display_name}, "), appended)
        self.assertTrue(appended.endswith("): Segregated B"), appended)
        self.assertEqual(a.containment_completed_by_id, self.superuser.id)

    def test_a_combined_ncr_has_no_capa_decision_of_its_own(self):
        a = self._ncr_of(self._fail(self.parts[0]))
        b = self._ncr_of(self._fail(self.parts[1]))
        self.client.post("/api/NCRs/combine/", {"into": str(a.id), "ncrs": [str(b.id)]}, format="json")
        r = self.client.get("/api/NCRs/", {"capa_decision__isnull": "true", "combined_into__isnull": "true"})
        self.assertEqual([n["id"] for n in r.json()["results"]], [str(a.id)])
        r = self.client.post(f"/api/NCRs/{b.id}/capa-decision/", {"decision": "NOT_REQUIRED", "note": "x"},
                             format="json")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("its CAPA decision is made there", r.json()["detail"])


class P2FixesTests(_Shop):
    """NCR fix batch, P2 (2026-11-18)."""

    def test_a_refusal_while_deciding_several_names_the_part(self):
        # Not a nonconformance needs each finding voided first: none was, so the
        # first part refuses, by name, and nothing is recorded.
        ncr = self._ncr_of(self._fail(self.parts[0]))
        self.client.post(f"/api/NCRs/{ncr.id}/add-parts/", {"parts": [str(self.parts[1].id)]}, format="json")
        r = self.client.post(f"/api/NCRs/{ncr.id}/decide/",
                             {"disposition_type": "NOT_NONCONFORMANCE", "all": True}, format="json")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertRegex(r.json()["detail"], r"^B-[01]: The finding still stands")
        self.assertFalse(ncr.dispositions.exclude(disposition_type="").exists())

    def test_parts_load_by_id_in_one_request(self):
        r = self.client.get("/api/Parts/", {"id__in": [str(self.parts[0].id), str(self.parts[2].id)]})
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(sorted(p["ERP_id"] for p in r.json()["results"]), ["B-0", "B-2"])

    def test_the_employee_picker_searches_the_server(self):
        from django.contrib.auth import get_user_model
        get_user_model().objects.filter(pk=self.user_a.pk).update(first_name="Zelda", user_type="INTERNAL")
        r = self.client.get("/api/Employees-Options/", {"search": "zeld"})
        self.assertEqual(r.status_code, 200, r.content)
        self.assertIn(self.user_a.id, [u["id"] for u in r.json()["results"]])

    def test_the_dashboards_old_ncr_link_lists_what_it_counted(self):
        from datetime import timedelta
        from django.utils import timezone
        ncr = self._ncr_of(self._fail(self.parts[0]))
        NCR.objects.filter(pk=ncr.pk).update(created_at=timezone.now() - timedelta(days=10))
        self._ncr_of(self._fail(self.parts[1]))  # new: not counted
        r = self.client.get("/api/dashboard/needs-attention/")
        item = next(i for i in r.json()["data"] if i["type"] == "ncr")
        self.assertEqual(item["count"], 1)
        listed = self.client.get("/api/NCRs/", item["linkParams"]).json()["results"]
        self.assertEqual([n["id"] for n in listed], [str(ncr.id)])


class P3FixesTests(_Shop):
    """NCR fix batch, P3 (2026-11-18)."""

    def test_severity_comes_down_by_hand_until_something_is_decided(self):
        # One rule for PATCH and the header path: either way until decided, then up only.
        from Tracker.services.qms.disposition import decide_disposition
        ncr = self._ncr_of(self._fail(self.parts[0]))
        self.client.patch(f"/api/NCRs/{ncr.id}/", {"severity": "CRITICAL"}, format="json")
        r = self.client.patch(f"/api/NCRs/{ncr.id}/", {"severity": "MINOR"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        decide_disposition(ncr.dispositions.get(), disposition_type="SCRAP", authorized_by=self.superuser)
        r = self.client.patch(f"/api/NCRs/{ncr.id}/", {"severity": "MAJOR"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        r = self.client.patch(f"/api/NCRs/{ncr.id}/", {"severity": "MINOR"}, format="json")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn(f"{ncr.ncr_number} is Major; its severity may only be raised.", r.content.decode())

    def test_linked_capas_read_by_number(self):
        from Tracker.models import CAPA
        ncr = self._ncr_of(self._fail(self.parts[0]))
        capa = CAPA.objects.create(tenant=self.tenant_a, capa_number="CAPA-T-1", capa_type="CORRECTIVE",
                                   severity="MAJOR", problem_statement="x", initiated_by=self.superuser)
        capa.ncrs.add(ncr)
        r = self.client.get(f"/api/NCRs/{ncr.id}/")
        self.assertEqual(r.json()["capa_refs"], [{"id": str(capa.id), "capa_number": "CAPA-T-1"}])

    def test_home_quarantine_counts_agree(self):
        from Tracker.models import Parts
        Parts.objects.filter(pk=self.parts[0].pk).update(part_status="QUARANTINED")
        Parts.objects.filter(pk=self.parts[1].pk).update(part_status="REWORK_NEEDED")
        kpis = self.client.get("/api/dashboard/kpis/").json()
        item = next(i for i in self.client.get("/api/dashboard/needs-attention/").json()["data"]
                    if i["type"] == "quarantine")
        self.assertEqual((kpis["parts_in_quarantine"], item["count"]), (1, 1))
        self.assertEqual(item["link"], "/production/dispositions")


class NcrOwnerTests(_Shop):
    """NCR owner and closing from the NCR (user go 2026-11-18)."""

    def test_taking_an_ncr_takes_its_open_decisions(self):
        ncr = self._ncr_of(self._fail(self.parts[0]))
        self.client.post(f"/api/NCRs/{ncr.id}/add-parts/", {"parts": [str(self.parts[1].id)]}, format="json")
        r = self.client.post(f"/api/NCRs/{ncr.id}/assign/", {"assigned_to": self.user_a.id}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["assigned_to"], self.user_a.id)
        self.assertEqual(set(ncr.dispositions.values_list("assigned_to_id", flat=True)), {self.user_a.id})
        # Back to the queue: its decisions too.
        self.client.post(f"/api/NCRs/{ncr.id}/assign/", {"assigned_to": None}, format="json")
        self.assertEqual(set(ncr.dispositions.values_list("assigned_to_id", flat=True)), {None})

    def test_a_failure_joining_an_owned_ncr_is_the_owners(self):
        ncr = self._ncr_of(self._fail(self.parts[0]))
        self.client.post(f"/api/NCRs/{ncr.id}/assign/", {"assigned_to": self.user_a.id}, format="json")
        self.client.post(f"/api/NCRs/{ncr.id}/add-parts/", {"parts": [str(self.parts[2].id)]}, format="json")
        added = ncr.dispositions.get(part=self.parts[2])
        self.assertEqual(added.assigned_to_id, self.user_a.id)

    def test_taking_the_only_decision_takes_an_unowned_ncr(self):
        ncr = self._ncr_of(self._fail(self.parts[0]))
        d = ncr.dispositions.get()
        d.assigned_to = self.user_a
        d.save(update_fields=["assigned_to"])
        ncr.refresh_from_db()
        self.assertEqual(ncr.assigned_to_id, self.user_a.id)

    def test_the_queue_is_one_row_per_ncr(self):
        from Tracker.services.qms.ncr import add_parts
        ncr = self._ncr_of(self._fail(self.parts[0]))
        add_parts(ncr, [self.parts[1]], user=self.user_a)  # no take perm: stays in the queue
        r = self.client.get("/api/NCRs/", {"assigned_to__isnull": "true", "state": "OPEN"})
        self.assertEqual([n["id"] for n in r.json()["results"]], [str(ncr.id)])
        self.assertEqual(r.json()["results"][0]["todo"]["awaiting_decision"], 2)

    def test_close_decided_is_all_or_nothing(self):
        from Tracker.services.qms.disposition import decide_disposition
        ncr = self._ncr_of(self._fail(self.parts[0]))  # MAJOR: containment needed to close
        self.client.post(f"/api/NCRs/{ncr.id}/add-parts/", {"parts": [str(self.parts[1].id)]}, format="json")
        for d in ncr.dispositions.all():
            decide_disposition(d, disposition_type="SCRAP", authorized_by=self.superuser)
        r = self.client.get(f"/api/NCRs/{ncr.id}/")
        self.assertTrue(r.json()["todo"]["containment_needed"])
        r = self.client.post(f"/api/NCRs/{ncr.id}/close-decided/")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("None closed", r.json()["detail"])
        self.assertIn("B-0:", r.json()["detail"])
        self.assertFalse(ncr.dispositions.filter(current_state="CLOSED").exists())
        from Tracker.services.qms.ncr import record_containment
        record_containment(ncr, action="Held on the rack.", user=self.superuser)
        r = self.client.post(f"/api/NCRs/{ncr.id}/close-decided/")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["state"], "CLOSED")

    def test_taking_needs_the_take_permission(self):
        ncr = self._ncr_of(self._fail(self.parts[0]))
        self.grant_tenant_permissions(self.user_a, self.tenant_a, ['full_tenant_access', 'view_ncr'])
        self.authenticate_as(self.user_a, self.tenant_a)
        r = self.client.post(f"/api/NCRs/{ncr.id}/assign/", {"assigned_to": self.user_a.id}, format="json")
        self.assertEqual(r.status_code, 403, r.content)

    def test_a_hand_raised_ncr_is_its_raisers_when_they_may_take_it(self):
        # QA and leads own what they raise; an operator's raise waits in the queue.
        r = self.client.post("/api/NCRs/", {"parts": [str(self.parts[0].id)], "description": "Chatter",
                                            "severity": "MINOR"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["assigned_to"], self.superuser.id)
        # An operator holds the take perm too; owning by raising is QA's and leads' (change_ncr).
        self.grant_tenant_permissions(self.user_a, self.tenant_a, ['full_tenant_access', 'view_ncr', 'add_ncr',
                                                                   'change_quarantinedisposition'])
        self.authenticate_as(self.user_a, self.tenant_a)
        r = self.client.post("/api/NCRs/", {"parts": [str(self.parts[1].id)], "description": "Chatter",
                                            "severity": "MINOR"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertIsNone(r.json()["assigned_to"])

    def test_a_failure_raises_an_unowned_ncr(self):
        self.assertIsNone(self._ncr_of(self._fail(self.parts[0])).assigned_to_id)


class DefectEntryTests(_Shop):
    """Defects on every failed record, one writer (user go 2026-11-18)."""

    def setUp(self):
        super().setUp()
        from Tracker.models import QualityErrorsList
        self.marks = QualityErrorsList.objects.create(tenant=self.tenant_a, error_name="Tool marks",
                                                      part_type=self.pt)
        self.crack = QualityErrorsList.objects.create(tenant=self.tenant_a, error_name="Crack",
                                                      part_type=self.pt)

    def _row(self, et, severity="MINOR", **kw):
        return {"error_type": str(et.id), "severity": severity, "count": 1, **kw}

    def test_a_failed_record_with_a_minor_defect_brings_its_ncr_down(self):
        r = self.client.post("/api/QualityReports/", {
            "part": str(self.parts[0].id), "step": str(self.step.id), "status": "FAIL",
            "description": "Marks", "defect_rows": [self._row(self.marks, location="OD")]}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        report = QualityReports.objects.get(pk=r.json()["id"])
        self.assertEqual([(d.error_type_id, d.severity, d.location) for d in report.defects.all()],
                         [(self.marks.id, "MINOR", "OD")])
        report.ncr.refresh_from_db()
        self.assertEqual(report.ncr.severity, "MINOR")

    def test_a_recorded_result_takes_no_new_defects_on_edit(self):
        report = self._fail(self.parts[0])
        r = self.client.patch(f"/api/QualityReports/{report.id}/", {"defect_rows": [self._row(self.marks)]},
                              format="json")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("A recorded result is final", r.content.decode())
        pending = QualityReports.objects.create(tenant=self.tenant_a, part=self.parts[1], step=self.step,
                                                status="PENDING", detected_by=self.user_a)
        r = self.client.patch(f"/api/QualityReports/{pending.id}/", {"defect_rows": [self._row(self.marks)]},
                              format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(pending.defects.count(), 1)

    def test_raise_ncr_puts_the_defect_on_every_parts_record(self):
        r = self.client.post("/api/NCRs/", {
            "parts": [str(self.parts[0].id), str(self.parts[1].id)], "description": "Marks",
            "severity": "MINOR", "defect_rows": [self._row(self.marks)]}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        reports = QualityReports.objects.filter(ncr_id=r.json()["id"])
        self.assertEqual(sorted(rep.defects.count() for rep in reports), [1, 1])
        self.assertEqual([x["defects"] for x in r.json()["reports"]], [["Tool marks (Minor)"]] * 2)

    def test_a_later_finding_on_an_open_ncr_raises_its_severity(self):
        report = self._fail(self.parts[0])
        ncr = self._ncr_of(report)
        r = self.client.post(f"/api/NCRs/{ncr.id}/add-defects/", {
            "report": str(report.id), "defect_rows": [self._row(self.crack, severity="CRITICAL")]}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["severity"], "CRITICAL")

    def test_a_later_finding_needs_change_ncr_an_open_ncr_and_a_standing_record(self):
        from django.utils import timezone
        report = self._fail(self.parts[0])
        ncr = self._ncr_of(report)
        QualityReports.objects.filter(pk=report.pk).update(superseded_at=timezone.now())
        r = self.client.post(f"/api/NCRs/{ncr.id}/add-defects/", {
            "report": str(report.id), "defect_rows": [self._row(self.marks)]}, format="json")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("was withdrawn", r.json()["detail"])
        self.grant_tenant_permissions(self.user_a, self.tenant_a, ['full_tenant_access', 'view_ncr', 'add_ncr'])
        self.authenticate_as(self.user_a, self.tenant_a)
        r = self.client.post(f"/api/NCRs/{ncr.id}/add-defects/", {
            "report": str(report.id), "defect_rows": [self._row(self.marks)]}, format="json")
        self.assertEqual(r.status_code, 403, r.content)

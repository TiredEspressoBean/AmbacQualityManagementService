"""Approved, and in-approval, records can't be edited through the API (2026-10-12).

The general rule lives in services/core/approval_lock.py and is enforced once in
TenantScopedMixin; these tests cover the rules and the wiring.

- An ApprovalRequest's status, subject and requester were writable by PATCH, and
  every staff role holds change_approvalrequest: anyone could mark a pending
  approval APPROVED with no signature. DELETE cancelled one whatever its state,
  so a decided approval could be erased.
- A PCR stayed editable at every status. An approved PCR could be repointed at a
  different draft process, so implementation would roll out something nobody
  approved while the approval stayed attached.
"""
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from Tracker.models import ApprovalRequest, PartTypes, ProcessChangeRequest, TenantGroup, UserRole
from Tracker.services.change_control.process_change import submit_pcr
from Tracker.tests.base import TenantTestCase
from Tracker.tests.test_change_control import _make_approved_process, _make_pcr, _make_pcr_template

_PERMS = [
    'full_tenant_access',
    'view_processchangerequest', 'change_processchangerequest', 'delete_processchangerequest',
    'view_approvalrequest', 'add_approvalrequest', 'change_approvalrequest', 'delete_approvalrequest',
    'view_processes', 'change_processes', 'delete_processes',
]


class ApprovalLockTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        group = TenantGroup.objects.create(tenant=self.tenant_a, name="Lock testers", is_custom=True)
        group.permissions.add(*Permission.objects.filter(codename__in=_PERMS))
        UserRole.objects.create(user=self.user_a, group=group)
        self.authenticate_as(self.user_a, self.tenant_a)
        part_type = PartTypes.objects.create(name='PT', ID_prefix='PT-')
        self.process, _ = _make_approved_process(self.tenant_a, self.user_a, part_type)
        _make_pcr_template(self.tenant_a)
        self.pcr = _make_pcr(self.tenant_a, self.user_a, self.process)

    def _pcr_url(self):
        return f"/api/process-change-requests/{self.pcr.id}/"

    # -- PCR ------------------------------------------------------------------

    def test_a_draft_pcr_takes_its_narrative_and_nothing_else(self):
        ok = self.client.patch(self._pcr_url(), {"title": "Retitled"}, format="json")
        self.assertEqual(ok.status_code, 200, ok.content)
        repoint = self.client.patch(self._pcr_url(), {"draft_process_version": str(self.process.id)},
                                    format="json")
        self.assertEqual(repoint.status_code, 400)
        self.assertIn("draft_process_version", repoint.json()["detail"])

    def test_a_submitted_pcr_is_locked(self):
        submit_pcr(self.pcr, user=self.user_a)
        edit = self.client.patch(self._pcr_url(), {"title": "Changed after submit"}, format="json")
        self.assertEqual(edit.status_code, 400)
        self.assertIn("awaiting approval", edit.json()["detail"])
        self.assertEqual(self.client.delete(self._pcr_url()).status_code, 400)
        self.pcr.refresh_from_db()
        self.assertNotEqual(self.pcr.title, "Changed after submit")
        self.assertFalse(self.pcr.archived)

    # -- Approval requests ----------------------------------------------------

    def test_an_approval_request_cannot_be_patched_to_approved(self):
        ar = submit_pcr(self.pcr, user=self.user_a)
        r = self.client.patch(f"/api/ApprovalRequests/{ar.id}/", {"status": "APPROVED"}, format="json")
        self.assertEqual(r.status_code, 405)
        ar.refresh_from_db()
        self.assertEqual(ar.status, "PENDING")

    def test_only_a_pending_request_can_be_cancelled(self):
        ar = submit_pcr(self.pcr, user=self.user_a)
        self.assertEqual(self.client.delete(f"/api/ApprovalRequests/{ar.id}/").status_code, 204)
        ar.refresh_from_db()
        self.assertEqual(ar.status, "CANCELLED")
        ApprovalRequest.objects.filter(pk=ar.pk).update(status="APPROVED")
        refused = self.client.delete(f"/api/ApprovalRequests/{ar.id}/")
        self.assertEqual(refused.status_code, 400)
        ar.refresh_from_db()
        self.assertEqual(ar.status, "APPROVED")

    def test_a_new_request_starts_pending_whatever_the_client_says(self):
        r = self.client.post("/api/ApprovalRequests/", {
            "approval_type": "PCR_APPROVAL", "reason": "forged",
            "content_type": ContentType.objects.get_for_model(ProcessChangeRequest).id,
            "object_id": str(self.pcr.id), "status": "APPROVED",
        }, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(ApprovalRequest.objects.get(pk=r.json()["id"]).status, "PENDING")

    # -- The general lock (services/core/approval_lock.py) --------------------

    def test_an_approved_process_cannot_be_edited_or_deleted(self):
        url = f"/api/Processes/{self.process.id}/"
        r = self.client.patch(url, {"name": "Renamed"}, format="json")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertEqual(self.client.delete(url).status_code, 400)


class ApprovalLockRuleTests(TenantTestCase):
    """The rules themselves, on unsaved instances — no approval request involved."""

    def test_a_decision_field_cannot_be_changed_by_an_edit(self):
        from Tracker.models import Documents, Processes, QuarantineDisposition
        from Tracker.services.core.approval_lock import edit_refusal
        self.assertIn("decided through", edit_refusal(Documents(status="UNDER_REVIEW"), {"status": "APPROVED"}))
        self.assertIn("decided through", edit_refusal(Processes(status="DRAFT"), {"status": "APPROVED"}))
        self.assertIn("decided through", edit_refusal(
            QuarantineDisposition(current_state="OPEN", disposition_type="REWORK"), {"disposition_type": "SCRAP"}))
        # Echoing the current value back, as forms do, is not a change.
        self.assertIsNone(edit_refusal(Processes(status="DRAFT", name="P"), {"status": "DRAFT", "name": "Q"}))

    def test_signed_off_records_are_frozen(self):
        from Tracker.models import CAPA, QualityReports, RcaRecord
        from Tracker.services.core.approval_lock import delete_refusal, edit_refusal
        self.assertIsNotNone(edit_refusal(QualityReports(status="FAIL"), {"status": "PASS"}))
        self.assertIsNotNone(edit_refusal(RcaRecord(root_cause_verification_status="VERIFIED"),
                                          {"root_cause_summary": "x"}))
        self.assertIsNotNone(delete_refusal(CAPA(status="CLOSED")))
        self.assertIsNone(edit_refusal(CAPA(status="IN_PROGRESS"), {"due_date": "2030-01-01"}))

    def test_the_registry_names_real_models_and_fields(self):
        from django.apps import apps
        from Tracker.services.core.approval_lock import DECISION_FIELDS, FINAL_WHEN, GO_AHEAD_APPROVALS
        for name in set(FINAL_WHEN) | set(DECISION_FIELDS) | GO_AHEAD_APPROVALS:
            model = apps.get_model("Tracker", name)
            for field in DECISION_FIELDS.get(name, (set(), ""))[0]:
                model._meta.get_field(field)  # raises if the field doesn't exist
            if name in FINAL_WHEN:
                FINAL_WHEN[name][0](model())  # the predicate runs on a blank instance

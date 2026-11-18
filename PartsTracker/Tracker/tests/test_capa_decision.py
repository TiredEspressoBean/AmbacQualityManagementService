"""Recording whether a nonconformance needed a CAPA (2026-10-06; on the NCR since
2026-11-17).

ISO 9001 10.2.1(b) wants the need for action *evaluated*. An NCR nobody promoted used
to look exactly like one nobody had looked at; now:

- a person records No CAPA needed / Deferred on the NCR, with a reason (initiate_capa);
- raising a CAPA from a failed report marks its NCR CAPA raised — the one safe inference;
- nothing is defaulted, and the list can ask for NCRs still undecided.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APIClient

from Tracker.models import CAPA, NCR, QualityReports, Tenant, TenantGroup, UserRole
from Tracker.tests.base import TenantContextMixin, VectorTestCase


class CapaDecisionTests(TenantContextMixin, VectorTestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Capa Decision", slug="capa-decision", tier="PRO")
        self.set_tenant_context(self.tenant)
        User = get_user_model()
        self.user = User.objects.create_user(username="qam", email="qam@x.test", password="x",
                                             tenant=self.tenant)
        self.failed = QualityReports.objects.create(tenant=self.tenant, status="FAIL", description="Burr on bore")
        self.failed.refresh_from_db()
        self.ncr = self.failed.ncr

    def _grant(self, *codenames):
        ct = ContentType.objects.get_for_model(CAPA)
        perms = [Permission.objects.get(codename=c, content_type=ct) for c in codenames]
        perms.append(Permission.objects.get(codename='full_tenant_access'))
        for model, codename in ((QualityReports, 'view_qualityreports'), (NCR, 'view_ncr')):
            perms.append(Permission.objects.get(codename=codename,
                                                content_type=ContentType.objects.get_for_model(model)))
        group = TenantGroup.objects.create(tenant=self.tenant, name=f"g-{len(codenames)}", is_custom=True)
        group.permissions.add(*perms)
        UserRole.objects.create(user=self.user, group=group)

    def _client(self):
        c = APIClient()
        c.force_authenticate(user=self.user)
        c.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        return c

    def _decide(self, decision="NOT_REQUIRED", note="One-off; the disposition covers it."):
        return self._client().post(f"/api/NCRs/{self.ncr.id}/capa-decision/",
                                   {"decision": decision, "note": note}, format="json")

    def _undecided(self):
        return [r["id"] for r in self._client().get("/api/NCRs/?capa_decision__isnull=true").json()["results"]]

    def test_undecided_is_the_default_and_the_list_can_ask_for_it(self):
        self._grant('initiate_capa')
        self.assertIsNone(self.ncr.capa_decision)
        self.assertEqual(self._undecided(), [str(self.ncr.id)])

    def test_a_decision_is_recorded_with_its_reason_and_who(self):
        self._grant('initiate_capa')
        resp = self._decide()
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual((body["capa_decision"], body["capa_decision_note"]),
                         ("NOT_REQUIRED", "One-off; the disposition covers it."))
        self.assertEqual(body["capa_decided_by"], self.user.id)
        self.assertIsNotNone(body["capa_decided_at"])
        self.assertEqual(self._undecided(), [])  # decided, so off the undecided list
        # The report shows its NCR's decision.
        report = self._client().get(f"/api/QualityReports/{self.failed.id}/").json()
        self.assertEqual(report["capa_decision"], "NOT_REQUIRED")

    def test_the_reason_is_required(self):
        self._grant('initiate_capa')
        self.assertEqual(self._decide(note="  ").status_code, 400)
        self.assertEqual(self._decide(decision="PROMOTED").status_code, 400)

    def test_deciding_needs_initiate_capa(self):
        self._grant('add_capa')
        self.assertEqual(self._decide().status_code, 403)

    def test_raising_a_capa_marks_the_ncr_and_overrides_an_earlier_no(self):
        self._grant('initiate_capa', 'add_capa', 'change_capa')
        self._decide(decision="DEFERRED", note="Waiting on the second batch.")
        resp = self._client().post("/api/CAPAs/", {
            "problem_statement": "Burrs recurring", "capa_type": "CORRECTIVE", "severity": "MINOR",
            "approval_required": False, "approval_status": "NOT_REQUIRED",
            "quality_reports": [str(self.failed.id)],
        }, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.ncr.refresh_from_db()
        self.assertEqual(self.ncr.capa_decision, "PROMOTED")
        self.assertIn(resp.json()["capa_number"], self.ncr.capa_decision_note)
        self.assertEqual(resp.json()["ncrs"], [str(self.ncr.id)])
        # Once a CAPA covers it, it can't be talked back down to "not needed".
        self.assertEqual(self._decide().status_code, 400)

    def test_a_deferred_decision_can_be_revisited_on_a_frozen_report(self):
        """The finding is frozen once recorded (the approval lock); the judgement
        about it is not. Deferred means "decide later" — later has to work."""
        self._grant('initiate_capa')
        self.assertEqual(self._decide(decision="DEFERRED", note="Watching for a third.").status_code, 200)
        edit = self._client().patch(f"/api/QualityReports/{self.failed.id}/", {"description": "x"},
                                    format="json")
        self.assertIn(edit.status_code, (400, 403))  # the report itself stays as recorded
        self.assertEqual(self._decide(decision="NOT_REQUIRED", note="Third never came.").status_code, 200)
        self.ncr.refresh_from_db()
        self.assertEqual(self.ncr.capa_decision, "NOT_REQUIRED")

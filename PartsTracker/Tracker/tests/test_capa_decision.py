"""Recording whether a failed quality report needed a CAPA (2026-10-06).

ISO 9001 10.2.1(b) wants the need for action *evaluated*. An NCR nobody promoted used
to look exactly like one nobody had looked at; now:

- a person records No CAPA needed / Deferred, with a reason (initiate_capa);
- raising a CAPA from the report marks it CAPA raised — the one safe inference;
- nothing is defaulted, and the list can ask for failed reports still undecided.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APIClient

from Tracker.models import CAPA, QualityReports, Tenant, TenantGroup, UserRole
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
        self.passed = QualityReports.objects.create(tenant=self.tenant, status="PASS", description="ok")

    def _grant(self, *codenames):
        ct = ContentType.objects.get_for_model(CAPA)
        perms = [Permission.objects.get(codename=c, content_type=ct) for c in codenames]
        perms.append(Permission.objects.get(codename='full_tenant_access'))
        for model in (QualityReports,):
            qct = ContentType.objects.get_for_model(model)
            perms.append(Permission.objects.get(codename='view_qualityreports', content_type=qct))
        group = TenantGroup.objects.create(tenant=self.tenant, name=f"g-{len(codenames)}", is_custom=True)
        group.permissions.add(*perms)
        UserRole.objects.create(user=self.user, group=group)

    def _client(self):
        c = APIClient()
        c.force_authenticate(user=self.user)
        c.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        return c

    def _decide(self, report, decision="NOT_REQUIRED", note="One-off; the disposition covers it."):
        return self._client().post(f"/api/QualityReports/{report.id}/capa-decision/",
                                   {"decision": decision, "note": note}, format="json")

    def test_undecided_is_the_default_and_the_list_can_ask_for_it(self):
        self._grant('initiate_capa')
        self.assertIsNone(self.failed.capa_decision)
        rows = self._client().get("/api/QualityReports/?status=FAIL&capa_decision__isnull=true").json()["results"]
        self.assertEqual([r["id"] for r in rows], [str(self.failed.id)])

    def test_a_decision_is_recorded_with_its_reason_and_who(self):
        self._grant('initiate_capa')
        resp = self._decide(self.failed)
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual((body["capa_decision"], body["capa_decision_note"]),
                         ("NOT_REQUIRED", "One-off; the disposition covers it."))
        self.assertEqual(body["capa_decided_by"], self.user.id)
        self.assertIsNotNone(body["capa_decided_at"])
        rows = self._client().get("/api/QualityReports/?status=FAIL&capa_decision__isnull=true").json()["results"]
        self.assertEqual(rows, [])  # decided, so off the undecided list

    def test_the_reason_is_required_and_only_failures_are_decided(self):
        self._grant('initiate_capa')
        self.assertEqual(self._decide(self.failed, note="  ").status_code, 400)
        resp = self._decide(self.passed)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("failed report", resp.json()["detail"])
        self.assertEqual(self._decide(self.failed, decision="PROMOTED").status_code, 400)

    def test_deciding_needs_initiate_capa(self):
        self._grant('add_capa')
        self.assertEqual(self._decide(self.failed).status_code, 403)

    def test_raising_a_capa_marks_the_report_and_overrides_an_earlier_no(self):
        self._grant('initiate_capa', 'add_capa', 'change_capa')
        self._decide(self.failed, decision="DEFERRED", note="Waiting on the second batch.")
        resp = self._client().post("/api/CAPAs/", {
            "problem_statement": "Burrs recurring", "capa_type": "CORRECTIVE", "severity": "MINOR",
            "approval_required": False, "approval_status": "NOT_REQUIRED",
            "quality_reports": [str(self.failed.id)],
        }, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.failed.refresh_from_db()
        self.assertEqual(self.failed.capa_decision, "PROMOTED")
        self.assertIn(resp.json()["capa_number"], self.failed.capa_decision_note)
        # Once a CAPA covers it, it can't be talked back down to "not needed".
        self.assertEqual(self._decide(self.failed).status_code, 400)

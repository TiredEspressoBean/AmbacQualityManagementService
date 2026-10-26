"""Reviewing supervisor training overrides across parts (GET StepExecutions/training-overrides/).

An override was visible one part at a time; QA and auditors review them across a
period. Gated on view_auditlog — browsing the trail across records."""
import datetime

from Tracker.models import Parts, PartTypes, StepExecution, Steps, WorkOrder
from Tracker.tests.base import TenantTestCase

URL = "/api/StepExecutions/training-overrides/"


class TrainingOverrideReviewTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Injector")
        step = Steps.objects.create(tenant=self.tenant_a, name="Flow test", part_type=pt)
        wo = WorkOrder.objects.create(tenant=self.tenant_a, ERP_id="WO-TOV-1", quantity=2)
        self.parts = [Parts.objects.create(tenant=self.tenant_a, ERP_id=f"TOV-{i}", part_type=pt,
                                           work_order=wo, step=step) for i in range(2)]
        override = {"worker": 1, "worker_name": "Sam Novice", "authorized_by": 2,
                    "authorized_by_name": "Pat Lead", "reason": "Short-handed; Pat watched",
                    "at": "2026-10-10T09:00:00+00:00"}
        overridden = StepExecution.objects.create(
            tenant=self.tenant_a, part=self.parts[0], step=step, visit_number=1, status="IN_PROGRESS",
            training_authorization={"authorized": True, "missing": [{"training": "Flow bench"}],
                                    "verified": [], "override": override})
        # The part reached the step before the override was given (entered_at is auto_now_add).
        StepExecution.objects.filter(pk=overridden.pk).update(
            entered_at=datetime.datetime(2026, 10, 10, 8, 0, tzinfo=datetime.timezone.utc))
        self.overridden = overridden
        StepExecution.objects.create(
            tenant=self.tenant_a, part=self.parts[1], step=step, visit_number=1, status="IN_PROGRESS",
            training_authorization={"authorized": True, "missing": [], "verified": []})

    def _get(self, perms, **params):
        self.grant_tenant_permissions(self.user_a, self.tenant_a, perms + ['full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        return self.client.get(URL, params)

    def test_a_reviewer_sees_only_overridden_starts(self):
        resp = self._get(['view_stepexecution', 'view_auditlog'])
        self.assertEqual(resp.status_code, 200, resp.content)
        row, = resp.json()
        self.assertEqual(row["part_erp_id"], "TOV-0")
        self.assertEqual(row["work_order_erp_id"], "WO-TOV-1")
        self.assertEqual(row["authorized_by_name"], "Pat Lead")
        self.assertEqual(row["worker_name"], "Sam Novice")
        self.assertEqual(row["missing_training"], ["Flow bench"])

    def test_the_period_bounds_the_override_date(self):
        resp = self._get(['view_stepexecution', 'view_auditlog'], since="2026-10-11")
        self.assertEqual(resp.json(), [])
        resp = self.client.get(URL, {"since": "2026-10-01", "until": "2026-10-10"})
        self.assertEqual(len(resp.json()), 1)

    def test_a_line_role_cannot_review_across_parts(self):
        resp = self._get(['view_stepexecution'])
        self.assertEqual(resp.status_code, 403, resp.content)

    def test_an_override_given_wrongly_is_flagged_and_stays(self):
        """Corrections #11 (user decision 2026-10-26): flagged with a reason by the override
        authority; the override itself is untouched; the review shows the flag."""
        from django.contrib.auth import get_user_model
        flag_url = f"/api/StepExecutions/{self.overridden.id}/flag-override/"
        reader = get_user_model().objects.create_user(username="tov-reader", email="r@tov.test",
                                                      password="x", tenant=self.tenant_a)
        self.grant_tenant_permissions(reader, self.tenant_a, ['view_stepexecution', 'full_tenant_access'])
        self.authenticate_as(reader, self.tenant_a)
        self.assertEqual(self.client.post(flag_url, {"reason": "x"}, format="json").status_code, 403)
        resp = self._get(['view_stepexecution', 'view_auditlog', 'override_training_gate'])
        self.assertFalse(resp.json()[0]["flagged"])
        self.assertEqual(self.client.post(flag_url, {"reason": ""}, format="json").status_code, 400)
        ok = self.client.post(flag_url, {"reason": "Cert had lapsed"}, format="json")
        self.assertEqual(ok.status_code, 200, ok.content)
        self.assertEqual(self.client.post(flag_url, {"reason": "again"}, format="json").status_code, 400)
        row, = self.client.get(URL).json()
        self.assertTrue(row["flagged"])
        self.assertEqual(row["flag_reason"], "Cert had lapsed")
        self.assertEqual(row["reason"], "Short-handed; Pat watched")  # the override stands
        self.overridden.refresh_from_db()
        self.assertEqual(self.overridden.training_authorization["override"]["authorized_by_name"], "Pat Lead")

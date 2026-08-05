"""Stage-1 effectiveness-verification create (the plan) must not require the
stage-2 outcome.

Effectiveness verification is two-stage: you define the *plan* (method + success
criteria) first, and record the *outcome* (`effectiveness_result`) later. The
serializer used to expose `effectiveness_result` as a required field, so the
generated zod REQUEST client rejected the plan-create POST
("effectiveness_result is required") — silently, in the browser only,
invisible to backend tests and tsc. Fixed by making it `required=False`
(the model defaults it to INCONCLUSIVE).

This test pins the intended contract server-side: a plan create WITHOUT an
outcome is accepted, and the outcome defaults to INCONCLUSIVE (i.e. "not yet
decided", paired with a null `effectiveness_decided_at`). If someone re-adds
the requirement or drops the model default, this fails.
"""
from Tracker.models import CAPA, CapaType, CapaSeverity, EffectivenessResult
from Tracker.tests.base import TenantTestCase


class CapaVerificationPlanCreateTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.grant_tenant_permissions(
            self.user_a, self.tenant_a,
            ['full_tenant_access', 'view_capa', 'add_capaverification',
             'view_capaverification'],
        )
        self.capa = CAPA.objects.create(
            tenant=self.tenant_a,
            capa_number='CAPA-VP-1',
            problem_statement='Test',
            capa_type=CapaType.PREVENTIVE,
            severity=CapaSeverity.MINOR,
            assigned_to=self.user_a,
        )
        self.authenticate_as(self.user_a, self.tenant_a)

    def test_plan_create_without_outcome_is_accepted(self):
        """The plan-stage POST omits effectiveness_result and must still 201."""
        resp = self.client.post(
            '/api/CapaVerifications/',
            {
                'capa': str(self.capa.id),
                'verification_method': 'Monitor 30 days of receiving.',
                'verification_criteria': 'Zero missing-document holds over 30 days.',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        # Outcome defaults to INCONCLUSIVE ("not yet decided"), not set by stage 1.
        self.assertEqual(resp.data['effectiveness_result'], EffectivenessResult.INCONCLUSIVE)
        self.assertIsNone(resp.data.get('effectiveness_decided_at'))

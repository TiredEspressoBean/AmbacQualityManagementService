"""A repeat-visit rule of Specific Role must name a role (S1 review, 2026-11-11).

- Saved without its role, the rule let anyone through: refused on save.
- A role from another company is refused on save.
- A rule whose role is gone (deleted, SET_NULL) fails closed at start: a supervisor
  authorises, or an engineer fixes the rule.
"""
from django.core.exceptions import ValidationError

from Tracker.models import Parts, PartTypes, StepRequirement, Steps, TenantGroup
from Tracker.services.mes.lifecycle import RevisitRefused, check_revisit_rule
from Tracker.services.mes.step_gates import FLOOR_GATES, set_step_gates
from Tracker.tests.base import TenantTestCase


class RevisitRoleRuleTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        self.pt = PartTypes.objects.create(tenant=self.tenant_a, name="Seat")
        self.step = Steps.objects.create(tenant=self.tenant_a, name="Lap", part_type=self.pt)
        self.role = TenantGroup.objects.create(tenant=self.tenant_a, name="Lapping lead",
                                               description="", is_custom=True)

    def _rows(self, **revisit):
        return [{'gate': g} for g in FLOOR_GATES] + [{'gate': 'revisit_rule', **revisit}]

    def test_a_role_rule_without_its_role_is_refused(self):
        with self.assertRaisesMessage(ValidationError, "needs its role"):
            set_step_gates(self.step, self._rows(revisit_assignment='ROLE'))

    def test_a_role_from_another_company_is_refused(self):
        other = TenantGroup.objects.create(tenant=self.tenant_b, name="Theirs",
                                            description="", is_custom=True)
        with self.assertRaisesMessage(ValidationError, "isn't one of this company's roles"):
            set_step_gates(self.step, self._rows(revisit_assignment='ROLE', revisit_role=other.id))

    def test_the_first_piece_gate_sets_how_its_buy_off_is_signed(self):
        set_step_gates(self.step, [{'gate': g} for g in FLOOR_GATES]
                       + [{'gate': 'first_piece', 'qa_assurance': 'PASSWORD'}])
        step = Steps.objects.get(pk=self.step.pk)
        self.assertEqual(step.first_piece_assurance, 'PASSWORD')
        self.assertEqual(step.qa_signoff_assurance, 'NONE')  # no QA sign-off gate
        # the QA sign-off's, when it asks for more
        set_step_gates(self.step, [{'gate': g} for g in FLOOR_GATES]
                       + [{'gate': 'first_piece'}, {'gate': 'qa_signoff', 'qa_assurance': 'PASSWORD'}])
        self.assertEqual(Steps.objects.get(pk=self.step.pk).first_piece_assurance, 'PASSWORD')

    def test_a_rule_whose_role_is_gone_fails_closed(self):
        set_step_gates(self.step, self._rows(revisit_assignment='ROLE', revisit_role=self.role.id))
        StepRequirement.objects.filter(step=self.step, gate='revisit_rule').update(revisit_role=None)
        step = Steps.objects.get(pk=self.step.pk)
        part = Parts.objects.create(tenant=self.tenant_a, ERP_id="LAP-1", part_type=self.pt, step=step)
        with self.assertRaisesMessage(RevisitRefused, "no longer exists"):
            check_revisit_rule(part, step, self.user_a, visit_number=2)

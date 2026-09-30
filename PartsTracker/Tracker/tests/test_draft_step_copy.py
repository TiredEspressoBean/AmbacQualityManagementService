"""A draft's own copy of a shared step (2026-09-30).

A step row is shared by a process and its later versions, so any version's routing
reads as it was. The step panel's dialogs wrote straight to that row, so a draft's
edit to a measurement, a sampling rule or a training requirement changed the approved
version too; and the graph save forked a new step version on every save. Now a draft
takes one copy of a shared step — with its measurements and sampling rules, which the
fork used to leave behind — and edits that copy in place afterwards.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from Tracker.models import (
    Equipments, MeasurementDefinition, PartTypes, ProcessStatus, ProcessStep, Processes,
    SamplingRuleSet, StepEquipmentAffinity, Steps, TrainingType,
)
from Tracker.models.mes_lite import StepMeasurementRequirement
from Tracker.models.scheduling import StepTiming
from Tracker.services.mes.processes import create_new_process_version, update_process_with_steps
from Tracker.services.mes.steps import step_for_draft
from Tracker.services.training import create_training_requirement
from Tracker.tests.base import TenantTestCase
from Tracker.utils.tenant_context import reset_current_tenant, set_current_tenant_id

User = get_user_model()


def _approved_with_rich_step(tenant, user):
    pt = PartTypes.objects.create(name='Injector', ID_prefix='INJ-')
    process = Processes.objects.create(name='Injector reman', part_type=pt,
                                       status=ProcessStatus.APPROVED, approved_by=user)
    step = Steps.objects.create(name='Flow test', part_type=pt)
    ProcessStep.objects.create(process=process, step=step, order=1, is_entry_point=True)
    md = MeasurementDefinition.objects.create(step=step, label='Flow rate', type='NUMERIC',
                                              nominal=Decimal('12.5'))
    StepMeasurementRequirement.objects.create(step=step, measurement=md, is_mandatory=True)
    SamplingRuleSet.create_with_rules(part_type=pt, process=process, step=step, name='Every 5th',
                                      rules=[{'rule_type': 'EVERY_NTH_PART', 'value': 5, 'order': 1}])
    create_training_requirement(step=step, training_type=TrainingType.objects.create(name='Flow bench'),
                                tenant=tenant)
    StepEquipmentAffinity.objects.create(step=step, equipment=Equipments.objects.create(name='Bench 1'))
    StepTiming.objects.create(step=step, tenant=tenant, cycle_time_minutes=10)
    return process, step


class DraftStepCopyTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.approved, self.step = _approved_with_rich_step(self.tenant_a, self.user_a)
        self.draft = create_new_process_version(self.approved, user=self.user_a, change_description='Rev 2')

    def _draft_step(self):
        return self.draft.process_steps.get().step

    def test_a_draft_gets_one_copy_with_everything_hung_off_the_step(self):
        copy = step_for_draft(self.step, self.draft, user=self.user_a)
        self.assertNotEqual(copy.pk, self.step.pk)
        # The approved version keeps its row; only the draft moved.
        self.assertEqual(self.approved.process_steps.get().step_id, self.step.pk)
        self.assertEqual(self._draft_step().pk, copy.pk)

        md = MeasurementDefinition.objects.get(step=copy)
        self.assertEqual((md.label, md.nominal), ('Flow rate', Decimal('12.5')))
        self.assertEqual(StepMeasurementRequirement.objects.get(step=copy).measurement_id, md.pk)
        self.assertTrue(MeasurementDefinition.objects.filter(step=self.step).exists())

        rs = SamplingRuleSet.objects.get(step=copy, active=True)
        self.assertEqual((rs.process_id, list(rs.rules.values_list('value', flat=True))), (self.draft.pk, [5]))
        self.assertTrue(SamplingRuleSet.objects.filter(step=self.step, active=True).exists())

        self.assertEqual(copy.training_requirements.count(), 1)
        self.assertEqual(StepEquipmentAffinity.objects.filter(step=copy).count(), 1)
        self.assertEqual(StepTiming.objects.get(step=copy).cycle_time_minutes, 10)

    def test_asking_again_returns_the_same_copy(self):
        copy = step_for_draft(self.step, self.draft, user=self.user_a)
        self.assertEqual(step_for_draft(copy, self.draft, user=self.user_a).pk, copy.pk)
        self.assertEqual(Steps.objects.filter(name='Flow test').count(), 2)

    def test_repeated_graph_saves_edit_the_drafts_copy_in_place(self):
        def save(description, cycle):
            update_process_with_steps(self.draft, {
                'nodes': [{'id': str(self._draft_step().pk), 'order': 1, 'is_entry_point': True,
                           'description': description, 'timing': {'cycle_time_minutes': cycle}}],
                'edges': [],
            }, user=None)
            return self._draft_step()

        first = save('Rev 2 wording', 12)
        second = save('Rev 2 wording, again', 14)
        self.assertEqual(first.pk, second.pk)                   # one copy, not one per save
        self.assertEqual(second.description, 'Rev 2 wording, again')
        self.assertEqual(StepTiming.objects.get(step=second).cycle_time_minutes, 14)
        self.step.refresh_from_db()
        self.assertFalse(self.step.description)                # the approved row is untouched
        self.assertEqual(StepTiming.objects.get(step=self.step).cycle_time_minutes, 10)

    def test_a_timing_only_change_no_longer_edits_the_shared_row(self):
        update_process_with_steps(self.draft, {
            'nodes': [{'id': str(self.step.pk), 'order': 1, 'is_entry_point': True,
                       'timing': {'cycle_time_minutes': 20}}],
            'edges': [],
        }, user=None)
        self.assertNotEqual(self._draft_step().pk, self.step.pk)
        self.assertEqual(StepTiming.objects.get(step=self.step).cycle_time_minutes, 10)

    def test_an_unchanged_timing_does_not_copy(self):
        update_process_with_steps(self.draft, {
            'nodes': [{'id': str(self.step.pk), 'order': 1, 'is_entry_point': True,
                       'timing': {'cycle_time_minutes': 10}}],
            'edges': [],
        }, user=None)
        self.assertEqual(self._draft_step().pk, self.step.pk)

    def test_an_approved_process_is_refused(self):
        with self.assertRaises(ValueError):
            step_for_draft(self.step, self.approved, user=self.user_a)


class DraftStepApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        from Tracker.models import Tenant
        cls.tenant = Tenant.objects.create(name="Draft copy", slug="draft-step-copy")
        token = set_current_tenant_id(cls.tenant.id)
        try:
            cls.user = User.objects.create_user(username="dsc", email="dsc@x.test", password="x",
                                                tenant=cls.tenant, is_staff=True)
            cls.user.is_superuser = True
            cls.user.save(update_fields=["is_superuser"])
            cls.approved, cls.step = _approved_with_rich_step(cls.tenant, cls.user)
            cls.draft = create_new_process_version(cls.approved, user=cls.user, change_description='Rev 2')
        finally:
            reset_current_tenant(token)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        self._token = set_current_tenant_id(self.tenant.id)

    def tearDown(self):
        reset_current_tenant(self._token)

    def test_draft_step_copies_once(self):
        url = f"/api/Processes_with_steps/{self.draft.id}/draft-step/"
        first = self.client.post(url, {"step": str(self.step.id)}, format="json")
        self.assertEqual(first.status_code, 200, first.content)
        self.assertTrue(first.json()["copied"])
        again = self.client.post(url, {"step": first.json()["step"]}, format="json").json()
        self.assertEqual((again["step"], again["copied"]), (first.json()["step"], False))

    def test_content_on_a_step_an_approved_version_uses_is_refused(self):
        body = {"label": "Leak", "type": "PASS_FAIL"}
        shared = self.client.post("/api/MeasurementDefinitions/", {**body, "step": str(self.step.id)}, format="json")
        self.assertEqual(shared.status_code, 400, shared.content)
        own = self.client.post(f"/api/Processes_with_steps/{self.draft.id}/draft-step/",
                               {"step": str(self.step.id)}, format="json").json()["step"]
        made = self.client.post("/api/MeasurementDefinitions/", {**body, "step": own}, format="json")
        self.assertEqual(made.status_code, 201, made.content)
        self.assertFalse(MeasurementDefinition.objects.filter(step=self.step, label="Leak").exists())

    def test_sampling_on_a_shared_step_is_refused(self):
        resp = self.client.post(f"/api/Steps/{self.step.id}/update_sampling_rules/",
                                {"rules": [{"rule_type": "EVERY_NTH_PART", "value": 2, "order": 1}]},
                                format="json")
        self.assertEqual(resp.status_code, 400, resp.content)

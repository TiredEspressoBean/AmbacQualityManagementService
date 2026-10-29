"""Editor review fixes (2026-10-29).

- Step sampling is authored with the sampling permissions (QA), not add_steps.
- Editor list pages that had no metadata endpoint now have one, so the page can tell
  who may add or import.
"""
from Tracker.models import PartTypes, Steps
from Tracker.tests.base import TenantTestCase


class StepSamplingGateTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        self.pt = PartTypes.objects.create(tenant=self.tenant_a, name="Body", ID_prefix="B")
        self.step = Steps.objects.create(tenant=self.tenant_a, part_type=self.pt, name="Turn",
                                         step_type="TASK")
        self.url = f"/api/Steps/{self.step.id}/update_sampling_rules/"
        self.body = {"rules": [{"rule_type": "EVERY_NTH_PART", "value": 2, "order": 1}]}

    def test_add_steps_alone_no_longer_authors_sampling(self):
        self.grant_tenant_permissions(self.user_a, self.tenant_a,
                                      ['view_steps', 'add_steps', 'change_steps', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        r = self.client.post(self.url, self.body, format="json")
        self.assertEqual(r.status_code, 403, r.content)

    def test_the_sampling_permissions_author_it_without_add_steps(self):
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            'view_steps', 'add_samplingruleset', 'change_samplingruleset',
            'add_samplingrule', 'change_samplingrule', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        r = self.client.post(self.url, self.body, format="json")
        self.assertEqual(r.status_code, 200, r.content)


class EditorMetadataTests(TenantTestCase):

    def test_former_metadata_less_lists_now_report_their_add_permission(self):
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            'view_repaircode', 'view_materiallot', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        for endpoint, perm in (("RepairCodes", "add_repaircode"), ("MaterialLots", "add_materiallot")):
            r = self.client.get(f"/api/{endpoint}/metadata/")
            self.assertEqual(r.status_code, 200, (endpoint, r.content))
            self.assertEqual(r.json()["permissions"]["add"], perm, endpoint)


class StepApiEditTests(TenantTestCase):
    """D1: a step in a process isn't content-edited through /Steps/ without ?process."""

    def setUp(self):
        super().setUp()
        from Tracker.models import Processes, ProcessStep
        t = self.tenant_a
        self.pt = PartTypes.objects.create(tenant=t, name="Body", ID_prefix="B")
        self.step = Steps.objects.create(tenant=t, part_type=self.pt, name="Turn", step_type="TASK")
        self.process = Processes.objects.create(tenant=t, name="P", part_type=self.pt)
        ProcessStep.objects.create(process=self.process, step=self.step, order=1, is_entry_point=True)
        self.loose = Steps.objects.create(tenant=t, part_type=self.pt, name="Loose", step_type="TASK")
        self.grant_tenant_permissions(self.user_a, t, ['view_steps', 'change_steps', 'full_tenant_access'])
        self.authenticate_as(self.user_a, t)

    def test_content_edit_of_a_step_in_a_process_is_refused(self):
        r = self.client.patch(f"/api/Steps/{self.step.id}/", {"description": "new"}, format="json")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("part of a process", r.content.decode())
        self.assertEqual(Steps.objects.filter(name="Turn").count(), 1)  # no orphan version

    def test_the_operation_number_and_a_loose_step_still_edit(self):
        r = self.client.patch(f"/api/Steps/{self.step.id}/", {"operation_number": "20"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        r = self.client.patch(f"/api/Steps/{self.loose.id}/", {"description": "new"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)


class MasterDataTierTests(TenantTestCase):
    """D7: add/change of companies, equipment types and the defect list is manager-tier."""

    def test_presets(self):
        from Tracker.presets import GROUP_PRESETS
        perms = {'add_companies', 'change_companies', 'add_equipmenttype', 'change_equipmenttype',
                 'add_qualityerrorslist', 'change_qualityerrorslist'}
        for key in ('tenant_admin', 'qa_manager', 'production_manager', 'document_controller'):
            self.assertTrue(perms <= set(GROUP_PRESETS[key]['permissions']), key)
        for key in ('operator', 'shift_lead', 'qa_inspector'):
            self.assertFalse(perms & set(GROUP_PRESETS[key]['permissions']), key)


class DuplicateProcessTests(TenantTestCase):
    """D5: a duplicate carries the process settings, and — the case the review only
    traced — its steps' sampling still applies after the copy's part type changes."""

    def setUp(self):
        super().setUp()
        from Tracker.models import Processes, ProcessStep, SamplingRule, SamplingRuleSet
        t = self.tenant_a
        self.pt = PartTypes.objects.create(tenant=t, name="Body", ID_prefix="B")
        self.other_pt = PartTypes.objects.create(tenant=t, name="Body Mk2", ID_prefix="M")
        self.step = Steps.objects.create(tenant=t, part_type=self.pt, name="Turn", step_type="TASK")
        self.process = Processes.objects.create(tenant=t, name="P", part_type=self.pt,
                                                is_disassembly=True, default_scrap_rate="0.05")
        ProcessStep.objects.create(process=self.process, step=self.step, order=1, is_entry_point=True)
        rs = SamplingRuleSet.objects.create(tenant=t, name="R", part_type=self.pt, process=self.process,
                                            step=self.step, active=True, is_fallback=False)
        SamplingRule.objects.create(tenant=t, ruleset=rs, rule_type='EVERY_NTH_PART', value=1, order=1)

    def test_settings_carry_over(self):
        from Tracker.services.mes.processes import duplicate_process
        copy = duplicate_process(self.process)
        self.assertTrue(copy.is_disassembly)
        self.assertEqual(str(copy.default_scrap_rate), "0.05")
        self.assertEqual(copy.category, self.process.category)

    def test_step_sampling_applies_after_the_copys_part_type_changes(self):
        from Tracker.models import Parts, WorkOrder
        from Tracker.services.mes.processes import duplicate_process
        from Tracker.services.mes.sampling_applier import SamplingFallbackApplier
        copy = duplicate_process(self.process)
        copy.part_type = self.other_pt
        copy.save(update_fields=['part_type'])
        wo = WorkOrder.objects.create(tenant=self.tenant_a, ERP_id="WO-MK2", quantity=1, process=copy)
        part = Parts.objects.create(tenant=self.tenant_a, ERP_id="M-1", part_type=self.other_pt,
                                    work_order=wo, step=self.step)
        self.assertTrue(SamplingFallbackApplier(part=part).evaluate()["requires_sampling"])


class UnreachableSettingsTests(TenantTestCase):
    """D3: settings that had no control are writable through their serializers."""

    def setUp(self):
        super().setUp()
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            'view_equipments', 'change_equipments', 'view_parttypes', 'change_parttypes',
            'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)

    def test_equipment_calibration_overrides_and_shifts(self):
        from datetime import time
        from Tracker.models import Equipments, Shift
        eq = Equipments.objects.create(tenant=self.tenant_a, name="CMM-1")
        day = Shift.objects.create(tenant=self.tenant_a, name="Day", code="D", start_time=time(6),
                                   end_time=time(14), days_of_week="0,1,2,3,4", is_active=True)
        r = self.client.patch(f"/api/Equipment/{eq.id}/", {
            "calibration_interval_days": 90, "requires_calibration_override": True,
            "operating_shifts": [str(day.id)]}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        body = r.json()
        self.assertEqual((body["calibration_interval_days"], body["requires_calibration_override"]), (90, True))
        self.assertEqual(body["operating_shifts"], [str(day.id)])
        row = Equipments.objects.filter(name="CMM-1", is_current_version=True).get()
        self.assertEqual(list(row.operating_shifts.values_list('id', flat=True)), [day.id])

    def test_part_type_can_recover_and_the_disassembly_process_must_be_one(self):
        from Tracker.models import Processes
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Injector", ID_prefix="I")
        build = Processes.objects.create(tenant=self.tenant_a, name="Build", part_type=pt)
        r = self.client.patch(f"/api/PartTypes/{pt.id}/", {"default_disassembly_process": str(build.id)},
                              format="json")
        self.assertEqual(r.status_code, 400, r.content)
        r = self.client.patch(f"/api/PartTypes/{pt.id}/", {"can_recover": True}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(r.json()["can_recover"])


class ApprovalTemplateDeactivationRemovedTests(TenantTestCase):
    """D2: no deactivate / activate on approval templates."""

    def test_the_actions_are_gone(self):
        from django.urls import NoReverseMatch, reverse
        for name in ("ApprovalTemplates-deactivate", "ApprovalTemplates-activate"):
            with self.assertRaises(NoReverseMatch):
                reverse(name, kwargs={"pk": "00000000-0000-0000-0000-000000000000"})

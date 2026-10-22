"""A temporary change reaches in-flight work on every approved version of its chain
(2026-10-21).

After a revision implemented with KEEP_ALL, running jobs stay on the older version. A
deviation raised then ("GR-2 down, grind on GR-1") must still reach them, on their own
version: the drafted version's jobs get the drafted change, an older version's jobs get a
fork of that version carrying the same edit. A version where a step the change touches
differs is listed but refused. See services/change_control/temporary.py.
"""
from datetime import timedelta

from Tracker.models import (
    PartTypes, ProcessChangeMigrationDisposition, Processes, ProcessStatus, ProcessStep,
    StepEdge, WorkOrder,
)
from Tracker.services.change_control import approve_pcr, implement_pco, submit_pcr
from Tracker.services.change_control.process_change import (
    ChangeControlMode, propose_process_change, propose_temporary_extension)
from Tracker.services.change_control.temporary import reach_rows, return_to_baseline
from Tracker.services.core.clock import tenant_today
from Tracker.services.mes.steps import add_step_to_process, create_new_step_version
from Tracker.tests.base import TenantTestCase
from Tracker.tests.test_change_control import (
    _make_pcn_template, _make_pco_template, _make_pcr_template, _make_workorder)

SIMPLE = ChangeControlMode.SIMPLIFIED
# Submitting a PCR requires these.
TEXT = dict(proposed_change='As titled.', justification='Test.', risk_analysis='None.')


class DeviationReachTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        _make_pcr_template(self.tenant_a)
        _make_pco_template(self.tenant_a)
        _make_pcn_template(self.tenant_a)
        self.today = tenant_today(self.tenant_a.id)
        pt = PartTypes.objects.create(name='Injector', ID_prefix='INJ-')
        # v1: Grind → Assemble → Inspect
        self.v1 = Processes.objects.create(name='Injector Build', part_type=pt,
                                           status=ProcessStatus.APPROVED, approved_by=self.user_a)
        self.grind = add_step_to_process(self.v1, order=1, is_entry_point=True, name='Grind')
        self.assemble = add_step_to_process(self.v1, order=2, name='Assemble')
        self.inspect = add_step_to_process(self.v1, order=3, name='Inspect')
        StepEdge.objects.create(process=self.v1, from_step=self.grind, to_step=self.assemble)
        StepEdge.objects.create(process=self.v1, from_step=self.assemble, to_step=self.inspect)
        # A routing ends at a Terminal step, or it can't be approved.
        done = add_step_to_process(self.v1, order=4, name='Done', is_terminal=True)
        StepEdge.objects.create(process=self.v1, from_step=self.inspect, to_step=done)

        # v2 changes Inspect, implemented with KEEP_ALL: v1's work stays on v1.
        self.wo_v1 = _make_workorder(self.tenant_a, self.v1, erp='WO-ON-V1')
        pcr, draft = propose_process_change(self.v1, user=self.user_a, title='Tighter inspection',
                                            **TEXT)
        create_new_step_version(self.inspect, user=self.user_a, process=draft,
                                change_description='Tighter inspection', name='Inspect (tight)')
        self._implement(pcr, ProcessChangeMigrationDisposition.KEEP_ALL)
        self.v2 = Processes.objects.get(pk=draft.pk)
        self.wo_v2 = _make_workorder(self.tenant_a, self.v2, erp='WO-ON-V2')

    def _implement(self, pcr, disposition, selected=()):
        submit_pcr(pcr, user=self.user_a)
        pco = approve_pcr(pcr, user=self.user_a, mode=SIMPLE)
        implement_pco(pco, user=self.user_a, migration_disposition=disposition,
                      selected_workorder_ids=list(selected) or None, mode=SIMPLE)
        pco.refresh_from_db()
        return pco

    def _deviation(self, step, name):
        """A temporary change drafted on v2 that edits `step` (as it is on v2)."""
        pcr, draft = propose_process_change(self.v2, user=self.user_a, title=name, **TEXT)
        on_v2 = ProcessStep.objects.get(process=draft, step__identity_id=step.identity_id).step
        create_new_step_version(on_v2, user=self.user_a, process=draft,
                                change_description=name, name=name)
        pcr.is_temporary = True
        pcr.temporary_until = self.today + timedelta(days=14)
        pcr.save(update_fields=['is_temporary', 'temporary_until'])
        return pcr, draft

    def _approved(self, pcr):
        submit_pcr(pcr, user=self.user_a)
        return approve_pcr(pcr, user=self.user_a, mode=SIMPLE)

    def test_the_picker_lists_work_on_every_approved_version(self):
        pcr, draft = self._deviation(self.grind, 'Grind on GR-1')
        pco = self._approved(pcr)
        rows = {r['erp_id']: r for r in reach_rows(pcr, pco.draft_process_version)}
        self.assertEqual(set(rows), {'WO-ON-V1', 'WO-ON-V2'})
        self.assertEqual((rows['WO-ON-V1']['version'], rows['WO-ON-V2']['version']),
                         (self.v1.version, self.v2.version))
        self.assertTrue(rows['WO-ON-V1']['applies_cleanly'])

    def test_a_version_where_a_touched_step_differs_is_listed_but_not_clean(self):
        pcr, draft = self._deviation(self.inspect, 'Inspect on CMM-2')  # Inspect differs on v1
        pco = self._approved(pcr)
        row = next(r for r in reach_rows(pcr, pco.draft_process_version) if r['erp_id'] == 'WO-ON-V1')
        self.assertFalse(row['applies_cleanly'])
        self.assertIn('Inspect', row['not_clean_reason'])
        with self.assertRaisesMessage(ValueError, "Doesn't apply cleanly"):
            implement_pco(pco, user=self.user_a,
                          migration_disposition=ProcessChangeMigrationDisposition.MIGRATE_SELECTED,
                          selected_workorder_ids=[self.wo_v1.id], mode=SIMPLE)
        self.wo_v1.refresh_from_db()
        self.assertEqual(self.wo_v1.process_id, self.v1.id)   # nothing moved

    def test_each_work_order_gets_the_change_on_its_own_version(self):
        pcr, draft = self._deviation(self.grind, 'Grind on GR-1')
        pco = self._implement(pcr, ProcessChangeMigrationDisposition.MIGRATE_SELECTED,
                              selected=[self.wo_v1.id, self.wo_v2.id])
        self.wo_v1.refresh_from_db()
        self.wo_v2.refresh_from_db()
        self.assertEqual(self.wo_v2.process_id, pco.draft_process_version_id)

        on_v1 = self.wo_v1.process
        self.assertEqual(on_v1.previous_version_id, self.v1.id)
        self.assertTrue(on_v1.is_temporary)
        self.assertEqual(on_v1.temporary_change_id, pcr.id)
        steps = {ps.step.identity_id: ps.step for ps in on_v1.process_steps.select_related('step')}
        drafted = {ps.step.identity_id: ps.step for ps in
                   pco.draft_process_version.process_steps.select_related('step')}
        # The deviation's Grind is the drafted step row itself, shared, never copied…
        self.assertEqual(steps[self.grind.identity_id].id, drafted[self.grind.identity_id].id)
        # …and v1 keeps its own Inspect, not v2's.
        self.assertEqual(steps[self.inspect.identity_id].id, self.inspect.id)
        # The flow is still Grind → Assemble → Inspect → Done.
        self.assertEqual(StepEdge.objects.filter(process=on_v1).count(), 3)

        # Neither base version moved: v2 is still current, v1 still approved.
        self.v2.refresh_from_db()
        self.assertTrue(self.v2.is_current_version)

    def test_moving_back_returns_a_work_order_to_its_own_version(self):
        pcr, draft = self._deviation(self.grind, 'Grind on GR-1')
        self._implement(pcr, ProcessChangeMigrationDisposition.MIGRATE_SELECTED,
                        selected=[self.wo_v1.id])
        wo = WorkOrder.objects.get(pk=self.wo_v1.pk)
        return_to_baseline(wo)
        wo.refresh_from_db()
        self.assertEqual(wo.process_id, self.v1.id)    # v1, not the current v2

    def test_an_extension_moves_every_version_it_is_in_force_on(self):
        pcr, draft = self._deviation(self.grind, 'Grind on GR-1')
        pco = self._implement(pcr, ProcessChangeMigrationDisposition.MIGRATE_SELECTED,
                              selected=[self.wo_v1.id, self.wo_v2.id])
        new_until = self.today + timedelta(days=60)
        ext = propose_temporary_extension(pcr, user=self.user_a, temporary_until=new_until,
                                          justification='GR-2 spindle still on order')
        ext_pco = self._approved(ext)
        implement_pco(ext_pco, user=self.user_a,
                      migration_disposition=ProcessChangeMigrationDisposition.KEEP_ALL, mode=SIMPLE)
        dates = set(Processes.objects.filter(temporary_change=pcr).values_list('temporary_until', flat=True))
        self.assertEqual(dates, {new_until})
        self.assertEqual(Processes.objects.filter(temporary_change=pcr).count(), 2)

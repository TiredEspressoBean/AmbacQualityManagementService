"""Temporary process changes (deviations) through change control.

A temporary change is approved for the work orders it names (MIGRATE_SELECTED) and is
never current: the baseline stays in force for everything else. After its end date
its work can't start or advance until an extension PCR moves the date, or the work
order goes back to the baseline. See services/change_control/temporary.py.
"""
from datetime import timedelta

from django.core.exceptions import ValidationError

from Tracker.models import (
    Parts, PartTypes, ProcessChangeMigrationDisposition, ProcessChangeOrder, Processes,
    StepExecution,
)
from Tracker.services.change_control import approve_pcr, implement_pco, submit_pcr
from Tracker.services.change_control.process_change import (
    ChangeControlMode, propose_temporary_extension)
from Tracker.services.change_control.temporary import (
    assert_in_date, refusal, return_to_baseline)
from Tracker.services.core.clock import tenant_today
from Tracker.tests.base import TenantTestCase
from Tracker.tests.test_change_control import (
    _make_approved_process, _make_pcn_template, _make_pco_template, _make_pcr,
    _make_pcr_template, _make_workorder)


class TemporaryChangeTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        self.part_type = PartTypes.objects.create(name='PT', ID_prefix='PT-')
        self.baseline, _ = _make_approved_process(self.tenant_a, self.user_a, self.part_type)
        _make_pcr_template(self.tenant_a)
        _make_pco_template(self.tenant_a)
        _make_pcn_template(self.tenant_a)
        self.named = _make_workorder(self.tenant_a, self.baseline, erp='WO-DEV-1')
        self.other = _make_workorder(self.tenant_a, self.baseline, erp='WO-DEV-2')
        self.today = tenant_today(self.tenant_a.id)

    def _temporary_pcr(self, until=None):
        pcr = _make_pcr(self.tenant_a, self.user_a, self.baseline, title='Alternate fixture')
        pcr.is_temporary = True
        pcr.temporary_until = until or self.today + timedelta(days=14)
        pcr.save(update_fields=['is_temporary', 'temporary_until'])
        return pcr

    def _implement(self, pcr, disposition=ProcessChangeMigrationDisposition.MIGRATE_SELECTED):
        submit_pcr(pcr, user=self.user_a)
        pco = approve_pcr(pcr, user=self.user_a, mode=ChangeControlMode.SIMPLIFIED)
        implement_pco(pco, user=self.user_a, migration_disposition=disposition,
                      selected_workorder_ids=[self.named.id], mode=ChangeControlMode.SIMPLIFIED)
        pco.refresh_from_db()
        return pco

    def test_the_baseline_stays_current_and_only_the_named_order_moves(self):
        pco = self._implement(self._temporary_pcr())
        temporary = pco.draft_process_version
        temporary.refresh_from_db()
        self.baseline.refresh_from_db()
        self.assertEqual(temporary.status, 'APPROVED')
        self.assertTrue(temporary.is_temporary)
        self.assertFalse(temporary.is_current_version)
        self.assertTrue(self.baseline.is_current_version)
        self.assertFalse(self.baseline.archived)
        self.named.refresh_from_db()
        self.other.refresh_from_db()
        self.assertEqual(self.named.process_id, temporary.id)
        self.assertEqual(self.other.process_id, self.baseline.id)

    def test_keep_all_and_migrate_all_are_refused(self):
        pcr = self._temporary_pcr()
        submit_pcr(pcr, user=self.user_a)
        pco = approve_pcr(pcr, user=self.user_a, mode=ChangeControlMode.SIMPLIFIED)
        for disposition in (ProcessChangeMigrationDisposition.KEEP_ALL,
                            ProcessChangeMigrationDisposition.MIGRATE_ALL):
            with self.assertRaisesMessage(ValueError, "work orders it names"):
                implement_pco(pco, user=self.user_a, migration_disposition=disposition,
                              mode=ChangeControlMode.SIMPLIFIED)
            pco.refresh_from_db()
            self.assertEqual(pco.status, ProcessChangeOrder.Status.APPROVED)

    def test_a_temporary_change_needs_a_future_end_date(self):
        pcr = self._temporary_pcr(until=self.today)
        with self.assertRaisesMessage(ValueError, "must end after today"):
            submit_pcr(pcr, user=self.user_a)

    def test_the_version_history_follows_the_mainline_past_the_deviation(self):
        pco = self._implement(self._temporary_pcr())
        history = [p.pk for p in self.baseline.get_version_history()]
        self.assertNotIn(pco.draft_process_version_id, history)

    def test_work_is_refused_after_the_end_date_and_names_the_change(self):
        pcr = self._temporary_pcr()
        pco = self._implement(pcr)
        temporary = pco.draft_process_version
        self.named.refresh_from_db()
        self.assertIsNone(refusal(self.named))
        Processes.objects.filter(pk=temporary.pk).update(
            temporary_until=self.today - timedelta(days=1))
        self.named.refresh_from_db()
        reason = refusal(self.named)
        self.assertIn(pcr.artifact_number, reason)
        self.assertIn((self.today - timedelta(days=1)).isoformat(), reason)
        with self.assertRaises(ValidationError):
            assert_in_date(self.named)

    def test_an_extension_pcr_moves_the_end_date(self):
        pcr = self._temporary_pcr()
        pco = self._implement(pcr)
        new_until = self.today + timedelta(days=60)
        extension = propose_temporary_extension(pcr, user=self.user_a, temporary_until=new_until,
                                                justification="Supplier fixture still late")
        submit_pcr(extension, user=self.user_a)
        ext_pco = approve_pcr(extension, user=self.user_a, mode=ChangeControlMode.SIMPLIFIED)
        self.assertIsNone(ext_pco.draft_process_version_id)
        implement_pco(ext_pco, user=self.user_a,
                      migration_disposition=ProcessChangeMigrationDisposition.KEEP_ALL,
                      mode=ChangeControlMode.SIMPLIFIED)
        ext_pco.refresh_from_db()
        self.assertEqual(ext_pco.status, ProcessChangeOrder.Status.IMPLEMENTED)
        temporary = Processes.objects.get(pk=pco.draft_process_version_id)
        self.assertEqual(temporary.temporary_until, new_until)

    def test_an_extension_must_end_later(self):
        pcr = self._temporary_pcr(until=self.today + timedelta(days=30))
        self._implement(pcr)
        extension = propose_temporary_extension(
            pcr, user=self.user_a, temporary_until=self.today + timedelta(days=10),
            justification="Fixture still late")
        with self.assertRaisesMessage(ValueError, "must end after"):
            submit_pcr(extension, user=self.user_a)

    def test_a_work_order_returns_to_the_baseline(self):
        pco = self._implement(self._temporary_pcr())
        self.named.refresh_from_db()
        return_to_baseline(self.named)
        self.named.refresh_from_db()
        self.assertEqual(self.named.process_id, self.baseline.id)

    def test_a_temporary_version_cannot_be_chosen_for_a_work_order(self):
        from rest_framework.test import APIClient
        pco = self._implement(self._temporary_pcr())
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            'change_workorder', 'view_workorder', 'full_tenant_access'])
        client = APIClient()
        client.force_authenticate(self.user_a)
        client.credentials(HTTP_X_TENANT_ID=str(self.tenant_a.id))
        resp = client.patch(f"/api/WorkOrders/{self.other.id}/",
                            {"process": str(pco.draft_process_version_id)}, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("temporary change", str(resp.json()))

    def test_a_later_permanent_change_does_not_build_on_the_deviation(self):
        from Tracker.services.change_control.rebase import find_current_approved
        self._implement(self._temporary_pcr())
        self.assertEqual(find_current_approved(self.baseline).pk, self.baseline.pk)

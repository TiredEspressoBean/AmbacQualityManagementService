"""
Quality gate + sampling fallback tests (Phase 2a).

The quality-gate dispatcher (`services/qms/quality_gate.py`) is the single
trigger path. Tighten (CONSECUTIVE_FAILS + TIGHTEN_SAMPLING) replaces the old
fallback_threshold; revert (good run → primary ruleset) is unchanged from
Phase 1. Also covers FAIL_RATE_PCT + HOLD_LOT and DEFECTIVE_COUNT + RAISE_CAPA_SCAR.
"""
from django.contrib.auth import get_user_model

from Tracker.tests.base import TenantTestCase
from Tracker.models import (
    PartTypes, Processes, Steps, ProcessStep, Orders, OrdersStatus,
    WorkOrder, WorkOrderStatus, Parts, PartsStatus,
    SamplingRuleSet, SamplingRule, SamplingTriggerState, StepGateFiring,
    QualityReports, CAPA,
)
from Tracker.services.qms.quality_gate import evaluate_step_gate
from Tracker.services.mes.sampling import update_sampling_trigger_state

User = get_user_model()


class QualityGateTestCase(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username='gate_op', email='op@example.com', password='pw'
        )
        self.part_type = PartTypes.objects.create(
            name='Gate Widget', ID_prefix='GW', ERP_id='GW-001'
        )
        self.process = Processes.objects.create(name='Gate Process', part_type=self.part_type)
        self.step = Steps.objects.create(
            name='Inspect', part_type=self.part_type, description='inspection step'
        )
        ProcessStep.objects.create(process=self.process, step=self.step, order=1)

        self.order = Orders.objects.create(
            name='Order', customer=self.user, order_status=OrdersStatus.IN_PROGRESS
        )
        self.work_order = WorkOrder.objects.create(
            ERP_id='WO-GATE-001', related_order=self.order,
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=50,
        )

        # Fallback (tighten target): 100% sampling, inactive until tripped.
        self.fallback = SamplingRuleSet.objects.create(
            name='Fallback 100%', part_type=self.part_type, process=self.process,
            step=self.step, active=False, is_fallback=True,
        )
        SamplingRule.objects.create(ruleset=self.fallback, rule_type='PERCENTAGE', value=100, order=1)

        # Primary ruleset carrying the gate.
        self.primary = SamplingRuleSet.objects.create(
            name='Primary every-nth', part_type=self.part_type, process=self.process,
            step=self.step, active=True, is_fallback=False,
            fallback_ruleset=self.fallback, fallback_duration=2,
            gate_metric='CONSECUTIVE_FAILS', gate_threshold=2,
            gate_actions=['TIGHTEN_SAMPLING'],
        )
        SamplingRule.objects.create(ruleset=self.primary, rule_type='EVERY_NTH_PART', value=1, order=1)

        self._seq = 0

    # -- helpers ----------------------------------------------------------

    def _make_part(self, status=PartsStatus.IN_PROGRESS):
        self._seq += 1
        return Parts.objects.create(
            ERP_id=f'WO-GATE-001-GW{self._seq:04d}',
            work_order=self.work_order, part_type=self.part_type,
            step=self.step, order=self.order, part_status=status,
        )

    def _report(self, part, status):
        return QualityReports.objects.create(
            part=part, step=self.step, status=status, detected_by=self.user
        )

    def _fire(self, part, qr):
        return evaluate_step_gate(
            ruleset=self.primary, work_order=self.work_order,
            trigger=qr, triggering_part=part, user=self.user,
        )

    def _active_triggers(self):
        return SamplingTriggerState.objects.filter(
            ruleset=self.fallback, work_order=self.work_order, step=self.step, active=True,
        )

    # -- tighten (CONSECUTIVE_FAILS) --------------------------------------

    def test_no_fire_before_threshold(self):
        p1 = self._make_part()
        firing = self._fire(p1, self._report(p1, 'FAIL'))
        self.assertIsNone(firing)
        self.assertFalse(self._active_triggers().exists())
        self.assertFalse(StepGateFiring.objects.exists())

    def test_fires_at_threshold_and_tightens(self):
        p1 = self._make_part()
        self.assertIsNone(self._fire(p1, self._report(p1, 'FAIL')))  # streak 1

        p2 = self._make_part()
        firing = self._fire(p2, self._report(p2, 'FAIL'))  # streak 2 == threshold
        self.assertIsNotNone(firing)
        self.assertEqual(firing.actions_taken, ['TIGHTEN_SAMPLING'])
        self.assertEqual(self._active_triggers().count(), 1)

    def test_pass_resets_streak(self):
        p1 = self._make_part()
        self._report(p1, 'FAIL')
        p2 = self._make_part()
        self._report(p2, 'PASS')  # breaks the run
        p3 = self._make_part()
        firing = self._fire(p3, self._report(p3, 'FAIL'))  # streak back to 1
        self.assertIsNone(firing)

    def test_idempotent_one_firing_per_window(self):
        p1 = self._make_part()
        self._report(p1, 'FAIL')
        p2 = self._make_part()
        first = self._fire(p2, self._report(p2, 'FAIL'))
        self.assertIsNotNone(first)

        p3 = self._make_part()
        again = self._fire(p3, self._report(p3, 'FAIL'))
        self.assertEqual(again.pk, first.pk)
        self.assertEqual(StepGateFiring.objects.count(), 1)
        self.assertEqual(self._active_triggers().count(), 1)

    # -- revert (unchanged Phase 1 behavior) ------------------------------

    def test_revert_after_good_run_restores_primary(self):
        trigger = SamplingTriggerState.objects.create(
            ruleset=self.fallback, work_order=self.work_order, step=self.step,
        )
        in_flight = self._make_part()

        update_sampling_trigger_state(self._make_part(), 'PASS')
        trigger.refresh_from_db()
        self.assertTrue(trigger.active)  # 1 good < 2

        update_sampling_trigger_state(self._make_part(), 'PASS')
        trigger.refresh_from_db()
        self.assertFalse(trigger.active)  # 2 good -> revert

        in_flight.refresh_from_db()
        self.assertEqual(in_flight.sampling_ruleset_id, self.primary.id)

    def test_revert_resets_on_failure(self):
        trigger = SamplingTriggerState.objects.create(
            ruleset=self.fallback, work_order=self.work_order, step=self.step,
        )
        update_sampling_trigger_state(self._make_part(), 'PASS')
        update_sampling_trigger_state(self._make_part(), 'FAIL')  # resets
        update_sampling_trigger_state(self._make_part(), 'PASS')
        trigger.refresh_from_db()
        self.assertTrue(trigger.active)
        self.assertEqual(trigger.success_count, 1)

    # -- other metrics / actions ------------------------------------------

    def test_fail_rate_pct_holds_parts(self):
        self.primary.gate_metric = 'FAIL_RATE_PCT'
        self.primary.gate_threshold = 50
        self.primary.gate_min_sample = 2
        self.primary.gate_actions = ['HOLD_LOT']
        self.primary.save()

        p1 = self._make_part()
        self._report(p1, 'PASS')
        p2 = self._make_part()
        qr = self._report(p2, 'FAIL')  # 1 fail / 2 = 50% == threshold

        firing = self._fire(p2, qr)
        self.assertIsNotNone(firing)
        self.assertEqual(firing.actions_taken, ['HOLD_LOT'])
        # Not-yet-advanced parts at the step are quarantined.
        self.assertTrue(
            Parts.objects.filter(work_order=self.work_order, step=self.step,
                                 part_status=PartsStatus.QUARANTINED).exists()
        )

    def test_fail_rate_pct_respects_min_sample(self):
        self.primary.gate_metric = 'FAIL_RATE_PCT'
        self.primary.gate_threshold = 50
        self.primary.gate_min_sample = 5
        self.primary.gate_actions = ['HOLD_LOT']
        self.primary.save()

        p1 = self._make_part()
        firing = self._fire(p1, self._report(p1, 'FAIL'))  # 100% but only 1 < 5 sample
        self.assertIsNone(firing)

    # -- apply path: tighten_after configures the gate ---------------------

    def test_apply_rules_with_tighten_after_sets_gate(self):
        step2 = Steps.objects.create(name='Inspect2', part_type=self.part_type, description='x')
        ProcessStep.objects.create(process=self.process, step=step2, order=2)
        ruleset = step2.apply_sampling_rules_update(
            rules_data=[{'rule_type': 'EVERY_NTH_PART', 'value': 5, 'order': 1}],
            fallback_rules_data=[{'rule_type': 'PERCENTAGE', 'value': 100, 'order': 1}],
            tighten_after=3,
            user=self.user,
        )
        ruleset.refresh_from_db()
        self.assertEqual(ruleset.gate_metric, 'CONSECUTIVE_FAILS')
        self.assertEqual(int(ruleset.gate_threshold), 3)
        self.assertEqual(ruleset.gate_actions, ['TIGHTEN_SAMPLING'])
        self.assertIsNotNone(ruleset.fallback_ruleset)

    def test_apply_rules_tighten_after_without_fallback_no_gate(self):
        step3 = Steps.objects.create(name='Inspect3', part_type=self.part_type, description='x')
        ProcessStep.objects.create(process=self.process, step=step3, order=3)
        ruleset = step3.apply_sampling_rules_update(
            rules_data=[{'rule_type': 'EVERY_NTH_PART', 'value': 5, 'order': 1}],
            tighten_after=3,  # no fallback ruleset to switch to -> no gate
            user=self.user,
        )
        ruleset.refresh_from_db()
        self.assertEqual(ruleset.gate_metric, '')

    def test_defective_count_raises_corrective_capa(self):
        self.primary.gate_metric = 'DEFECTIVE_COUNT'
        self.primary.gate_threshold = 2
        self.primary.gate_actions = ['RAISE_CAPA_SCAR']
        self.primary.gate_capa_type = 'CORRECTIVE'
        self.primary.save()

        p1 = self._make_part()
        self._report(p1, 'FAIL')
        p2 = self._make_part()
        firing = self._fire(p2, self._report(p2, 'FAIL'))  # 2 defectives == threshold

        self.assertIsNotNone(firing)
        self.assertEqual(firing.actions_taken, ['RAISE_CAPA_SCAR'])
        self.assertIsNotNone(firing.created_capa)
        self.assertEqual(firing.created_capa.capa_type, 'CORRECTIVE')

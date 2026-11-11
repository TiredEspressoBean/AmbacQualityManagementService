"""Step gates become typed StepRequirement rows (user decisions 2026-11-11).

- The data migration reproduces each step's old flags exactly: the floor every step had,
  plus a row per flag that was on (migrations/0302_step_gates_from_flags.py).
- A new step starts with the floor; a new version carries its source's gates.
- The registry follows the rows: a gate the step doesn't carry doesn't apply.
- Gates are edited as the step's whole list, versioned like any content edit, and a
  PCR diff names the gates added, removed or set differently.
"""
import importlib

from django.core.exceptions import ValidationError

from Tracker.models import Parts, PartTypes, StepExecution, StepRequirement, Steps, WorkOrder
from Tracker.services.mes.gates import GateCode, StartContext, floor_blockers
from Tracker.services.mes.step_gates import (
    FLOOR_GATES, set_gates_from_flags, set_step_gates,
)
from Tracker.tests.base import TenantTestCase

migration = importlib.import_module('Tracker.migrations.0302_step_gates_from_flags')

OFF = dict(requires_first_piece_inspection=False, fpi_scope='PER_WORKORDER',
           requires_qa_signoff=False, qa_signoff_assurance='NONE', block_on_quarantine=False,
           block_on_measurement_failure=False, revisit_assignment='ANY', revisit_role_id=None)


def gates_of(rows):
    return {r['gate']: {k: v for k, v in r.items() if k not in ('gate', 'order')} for r in rows}


class MigrationMappingTests(TenantTestCase):
    """The migration function against representative old flag combinations."""

    def test_a_step_with_no_flags_gets_the_floor_only(self):
        self.assertEqual(set(gates_of(migration.rows_for_flags(**OFF))), set(FLOOR_GATES))

    def test_each_flag_becomes_its_own_row_with_its_settings(self):
        rows = gates_of(migration.rows_for_flags(**{
            **OFF, 'requires_first_piece_inspection': True, 'fpi_scope': 'PER_SHIFT',
            'requires_qa_signoff': True, 'qa_signoff_assurance': 'PASSWORD',
            'block_on_quarantine': True, 'block_on_measurement_failure': True}))
        self.assertEqual(rows['first_piece'], {'fpi_scope': 'PER_SHIFT'})
        self.assertEqual(rows['qa_signoff'], {'qa_assurance': 'PASSWORD'})
        self.assertIn('quarantine_hold', rows)
        self.assertIn('measurement_out_of_spec', rows)
        self.assertTrue(set(FLOOR_GATES) <= set(rows))

    def test_the_assurance_and_scope_ride_only_with_their_gate(self):
        """A step with QA sign-off off but a stale PASSWORD assurance (and an FPI scope
        with FPI off) gets neither row: those settings meant nothing without the gate."""
        rows = gates_of(migration.rows_for_flags(**{
            **OFF, 'qa_signoff_assurance': 'PASSWORD', 'fpi_scope': 'PER_EQUIPMENT'}))
        self.assertNotIn('qa_signoff', rows)
        self.assertNotIn('first_piece', rows)

    def test_the_revisit_rule_becomes_a_row_except_any(self):
        self.assertNotIn('revisit_rule', gates_of(migration.rows_for_flags(**OFF)))
        same = gates_of(migration.rows_for_flags(**{**OFF, 'revisit_assignment': 'SAME'}))
        self.assertEqual(same['revisit_rule'], {'revisit_assignment': 'SAME', 'revisit_role_id': None})
        role = gates_of(migration.rows_for_flags(**{**OFF, 'revisit_assignment': 'ROLE',
                                                    'revisit_role_id': 'r-1'}))
        self.assertEqual(role['revisit_rule'], {'revisit_assignment': 'ROLE', 'revisit_role_id': 'r-1'})
        # A DIFFERENT rule carries no role, even if a stale one was set.
        diff = gates_of(migration.rows_for_flags(**{**OFF, 'revisit_assignment': 'different',
                                                    'revisit_role_id': 'r-1'}))
        self.assertEqual(diff['revisit_rule'], {'revisit_assignment': 'DIFFERENT', 'revisit_role_id': None})

    def test_an_unknown_scope_or_assurance_falls_back_to_the_old_default(self):
        rows = gates_of(migration.rows_for_flags(**{
            **OFF, 'requires_first_piece_inspection': True, 'fpi_scope': 'PER_OPERATOR',
            'requires_qa_signoff': True, 'qa_signoff_assurance': ''}))
        self.assertEqual(rows['first_piece'], {'fpi_scope': 'PER_WORKORDER'})
        self.assertEqual(rows['qa_signoff'], {'qa_assurance': 'NONE'})


class StepGateRowTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        self.pt = PartTypes.objects.create(tenant=self.tenant_a, name="Injector")
        self.step = Steps.objects.create(tenant=self.tenant_a, name="Grind", part_type=self.pt)

    def test_a_new_step_starts_with_the_floor(self):
        self.assertEqual(set(self.step.requirements.filter(archived=False).values_list('gate', flat=True)),
                         set(FLOOR_GATES))
        self.assertFalse(self.step.requires_qa_signoff)
        self.assertEqual(self.step.revisit_assignment, 'ANY')

    def test_the_old_flags_read_from_the_rows(self):
        set_gates_from_flags(self.step, requires_qa_signoff=True, qa_signoff_assurance='PASSWORD',
                             requires_first_piece_inspection=True, fpi_scope='PER_EQUIPMENT')
        step = Steps.objects.get(pk=self.step.pk)
        self.assertTrue(step.requires_qa_signoff)
        self.assertEqual(step.qa_signoff_assurance, 'PASSWORD')
        self.assertTrue(step.requires_first_piece_inspection)
        self.assertEqual(step.fpi_scope, 'PER_EQUIPMENT')

    def test_a_gate_is_carried_once(self):
        with self.assertRaises(ValidationError):
            set_step_gates(self.step, [{'gate': 'qa_signoff'}, {'gate': 'qa_signoff'}])

    def test_a_new_version_carries_its_sources_gates(self):
        set_gates_from_flags(self.step, block_on_quarantine=True)
        new = self.step.create_new_version(change_description="test", user=self.user_a)
        self.assertEqual(
            set(new.requirements.filter(archived=False).values_list('gate', flat=True)),
            set(FLOOR_GATES) | {'quarantine_hold'})

    def test_a_gate_the_step_does_not_carry_does_not_apply(self):
        wo = WorkOrder.objects.create(tenant=self.tenant_a, ERP_id="WO-GR-1", quantity=1,
                                      workorder_status="ON_HOLD")
        part = Parts.objects.create(tenant=self.tenant_a, ERP_id="GR-1", part_type=self.pt,
                                    work_order=wo, step=self.step)
        ctx = StartContext(part=part, step=self.step, work_order=wo, operator=None)
        self.assertIn(GateCode.WORK_ORDER_NOT_WORKABLE, [b.code for b in floor_blockers(ctx)])
        set_step_gates(self.step, [{'gate': g} for g in FLOOR_GATES if g != 'work_order_not_workable'])
        step = Steps.objects.get(pk=self.step.pk)
        ctx = StartContext(part=part, step=step, work_order=wo, operator=None)
        self.assertNotIn(GateCode.WORK_ORDER_NOT_WORKABLE, [b.code for b in floor_blockers(ctx)])

    def test_the_pcr_diff_names_gate_changes(self):
        from Tracker.services.change_control.diff import _diff_gates
        new = self.step.create_new_version(change_description="test", user=self.user_a)
        set_gates_from_flags(new, requires_first_piece_inspection=True, fpi_scope='PER_SHIFT')
        changes = _diff_gates(self.step, new)
        self.assertEqual(changes['gate:first_piece'], {'from': 'off', 'to': 'on (Per Shift)'})
        self.assertEqual(set(changes), {'gate:first_piece'})

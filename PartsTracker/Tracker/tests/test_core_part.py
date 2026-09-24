"""A core is a part; "core" is a role it plays. See Documents/CORE_AS_PART_DESIGN.md."""
from django.test import SimpleTestCase

from Tracker.models import Core, PartsStatus
from Tracker.services.mes.parts import HELD_PART_STATUSES, TERMINAL_PART_STATUSES
from Tracker.services.reman.core_part import part_status_for
from Tracker.services.scheduling.data import _UNSCHEDULABLE_PART_STATUSES

STAGES = [value for value, _ in Core.CORE_STATUS_CHOICES]


class StageToPartStatusTests(SimpleTestCase):
    """The part status is derived from the reman stage, so the two cannot disagree —
    and each derived status has to mean the right thing to the machinery that reads
    it: the scheduler, the terminal cascade, the held-status guard."""

    def test_every_stage_has_a_part_status(self):
        """A stage added without a mapping would raise at the first transition into it.
        This names it at test time instead."""
        for stage in STAGES:
            for on_wo in (True, False):
                with self.subTest(stage=stage, on_work_order=on_wo):
                    self.assertIn(part_status_for(stage, on_work_order=on_wo),
                                  PartsStatus.values)

    def test_a_planned_unit_is_schedulable_and_a_banked_one_is_not(self):
        planned = part_status_for('RECEIVED', on_work_order=True)
        banked = part_status_for('RECEIVED', on_work_order=False)
        self.assertNotIn(planned, _UNSCHEDULABLE_PART_STATUSES)
        self.assertIn(banked, _UNSCHEDULABLE_PART_STATUSES)

    def test_a_unit_being_worked_is_schedulable(self):
        for stage in ('IN_DISASSEMBLY', 'IN_REBUILD'):
            with self.subTest(stage=stage):
                self.assertNotIn(part_status_for(stage, on_work_order=True),
                                 _UNSCHEDULABLE_PART_STATUSES)

    def test_a_unit_waiting_on_a_decision_is_neither_scheduled_nor_finished(self):
        """The trap this mapping exists to avoid: CORE_BANKED is terminal, so a
        disassembled repair-and-return unit mapped to it would let the work-order
        cascade close the order before the rebuild. Waiting must be not-terminal AND
        not-schedulable."""
        for stage in ('DISASSEMBLED', 'AWAITING_AUTHORISATION'):
            with self.subTest(stage=stage):
                status = part_status_for(stage, on_work_order=True)
                self.assertNotIn(status, TERMINAL_PART_STATUSES)
                self.assertIn(status, _UNSCHEDULABLE_PART_STATUSES)
                # Not a QA hold either: nothing is wrong with the unit.
                self.assertNotIn(status, HELD_PART_STATUSES)

    def test_every_ending_is_terminal(self):
        for stage in ('REBUILT', 'DECLINED', 'RETURNED', 'RETURNED_UNREPAIRED',
                      'HARVESTED', 'SCRAPPED'):
            with self.subTest(stage=stage):
                self.assertIn(part_status_for(stage, on_work_order=True),
                              TERMINAL_PART_STATUSES)

    def test_a_harvested_unit_is_dismantled_not_scrapped_or_completed(self):
        """Its components are parts of their own now. SCRAPPED would say the unit was
        rejected and COMPLETED that it was built — both wrong, and COMPLETED would
        count it as output."""
        self.assertEqual(part_status_for('HARVESTED', on_work_order=True),
                         PartsStatus.DISMANTLED)

    def test_an_unknown_stage_is_refused_rather_than_guessed(self):
        with self.assertRaises(ValueError):
            part_status_for('SOMETHING_NEW', on_work_order=True)

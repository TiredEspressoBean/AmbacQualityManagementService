"""The first piece as a start gate (user decisions 2026-11-11; services/qms/first_piece.py).

- Until the context's first piece is passed or waived, only its N pieces may start;
  the first gated start opens the PENDING record (the call to QA).
- N is the first-piece gate row's quantity.
- Per Shift context comes from the visit's start, not the clock at check time.
- A failed first piece names its bad parts; FAIL reports land on those only.
- A first piece may be waived before any part is made.
- A declared "New setup" supersedes the pass and re-opens the first piece.
- A Per Equipment load runs on one known machine.
- The work queue reports what can start.
"""
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone

from Tracker.models import (
    FPIRecord, Parts, PartTypes, QualityReports, StepExecution, Steps, WorkOrder,
)
from Tracker.services.mes.gates import GateCode, StartRefused
from Tracker.services.mes.lifecycle import start_execution
from Tracker.services.mes.step_gates import FLOOR_GATES, set_step_gates
from Tracker.tests.base import TenantTestCase


class FirstPieceStartGateTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        t = self.tenant_a
        self.pt = PartTypes.objects.create(tenant=t, name="Body")
        self.step = Steps.objects.create(tenant=t, name="Bore", part_type=self.pt)
        self._gates(quantity=1)
        self.wo = WorkOrder.objects.create(tenant=t, ERP_id="WO-FP-1", quantity=4,
                                           workorder_status="IN_PROGRESS")
        self.parts = [Parts.objects.create(tenant=t, ERP_id=f"FP-{i}", part_type=self.pt,
                                           work_order=self.wo, step=self.step,
                                           part_status="IN_PROGRESS") for i in range(4)]
        self.visits = [StepExecution.objects.create(tenant=t, part=p, step=self.step,
                                                    visit_number=1, status="PENDING")
                       for p in self.parts]

    def _gates(self, quantity=1, scope="PER_WORKORDER"):
        set_step_gates(self.step, [{'gate': g} for g in FLOOR_GATES]
                       + [{'gate': 'first_piece', 'fpi_scope': scope, 'fpi_quantity': quantity}])
        self.step = Steps.objects.get(pk=self.step.pk)

    def _start(self, i):
        v = StepExecution.objects.get(pk=self.visits[i].pk)
        return start_execution(v, self.user_a)

    def _record(self):
        return FPIRecord.objects.get(work_order=self.wo, step=self.step, status="PENDING")

    def test_only_the_first_piece_starts_until_it_is_bought_off(self):
        self._start(0)
        record = self._record()
        self.assertEqual(list(record.first_piece_parts.values_list('ERP_id', flat=True)), ["FP-0"])
        with self.assertRaises(StartRefused) as ctx:
            self._start(1)
        self.assertEqual(ctx.exception.blockers[0].code, GateCode.FIRST_PIECE_PENDING)
        self.assertIn("waiting on its first piece", ctx.exception.messages[0])

    def test_a_first_piece_of_two_lets_two_start(self):
        self._gates(quantity=2)
        self._start(0)
        self._start(1)
        self.assertEqual(self._record().first_piece_parts.count(), 2)
        with self.assertRaises(StartRefused):
            self._start(2)

    def test_the_first_piece_is_bought_off_as_a_whole(self):
        from Tracker.services.qms.first_piece import pieces_missing
        self._gates(quantity=2)
        self._start(0)
        self.assertEqual(pieces_missing(self._record()), 1)  # one nest's piece not made
        self._start(1)
        self.assertEqual(pieces_missing(self._record()), 0)

    def test_after_the_pass_the_rest_start(self):
        self._start(0)
        record = self._record()
        FPIRecord.objects.filter(pk=record.pk).update(status="PASSED")
        self._start(1)
        self._start(2)

    def test_a_waiver_before_any_part_releases_the_run(self):
        from Tracker.services.qms.fpi import start_fpi, waive_fpi
        record, created = start_fpi(self.wo, self.step, self.user_a, for_waiver=True)
        self.assertTrue(created)
        self.assertEqual(record.first_piece_parts.count(), 0)
        waive_fpi(record, self.user_a, "Qualified fixture, identical setup re-run")
        for i in range(3):
            self._start(i)

    def test_a_new_setup_reopens_the_first_piece(self):
        from Tracker.services.qms.first_piece import declare_new_setup
        self._start(0)
        record = self._record()
        FPIRecord.objects.filter(pk=record.pk).update(status="PASSED")
        self._start(1)
        declare_new_setup(step=self.step, work_order=self.wo, user=self.user_a,
                          reason_code='TOOL_CHANGE', reason="Insert worn")
        record.refresh_from_db()
        self.assertEqual(record.status, "SUPERSEDED")
        self._start(2)  # the new first piece
        with self.assertRaises(StartRefused):
            self._start(3)

    def test_parts_made_under_the_old_setup_move_on_after_a_new_setup(self):
        from Tracker.models import QaApproval
        from Tracker.services.mes.gates import GateCode as G, release_blockers
        from Tracker.services.qms.first_piece import declare_new_setup
        self._start(0)
        record = self._record()
        FPIRecord.objects.filter(pk=record.pk).update(status="PASSED")
        QaApproval.objects.create(tenant=self.tenant_a, step=self.step, work_order=self.wo,
                                  fpi_record=record, qa_staff=self.user_b)
        self._start(1)
        declare_new_setup(step=self.step, work_order=self.wo, user=self.user_a,
                          reason_code='OFFSET', reason="Offset moved")
        self._start(2)  # the new first piece

        def holds(i):
            se = StepExecution.objects.get(pk=self.visits[i].pk)
            return {b.code for b in release_blockers(self.step, se, self.wo)} & {G.FIRST_PIECE, G.QA_SIGNOFF}
        self.assertEqual(holds(1), set())  # started under the old setup
        self.assertTrue(holds(2))           # started after: waits for the new first piece

    def test_a_new_setup_needs_a_reason(self):
        from Tracker.services.qms.first_piece import declare_new_setup
        with self.assertRaises(ValidationError):
            declare_new_setup(step=self.step, work_order=self.wo, user=self.user_a,
                              reason_code='OTHER', reason='')

    def test_a_failed_first_piece_names_its_bad_parts(self):
        from Tracker.services.qms.fpi import fail_fpi
        self._gates(quantity=2)
        self._start(0)
        self._start(1)
        record = self._record()
        with self.assertRaises(ValueError):
            fail_fpi(record, self.user_b, notes="bore oversize")  # names no part
        fail_fpi(record, self.user_b, notes="bore oversize", bad_part_ids=[self.parts[1].id])
        failed = set(QualityReports.objects.filter(step=self.step, status="FAIL")
                     .values_list('part__ERP_id', flat=True))
        self.assertEqual(failed, {"FP-1"})

    def test_per_shift_context_is_the_visits_start(self):
        from Tracker.services.qms.fpi_scope import context_for
        self._gates(scope="PER_SHIFT")
        self._start(0)
        yesterday = timezone.now() - timedelta(days=1)
        StepExecution.objects.filter(pk=self.visits[0].pk).update(started_at=yesterday)
        ctx = context_for(self.step, self.wo, part=self.parts[0])
        from Tracker.services.core.clock import plant_tz
        self.assertEqual(ctx.shift_date, yesterday.astimezone(plant_tz(self.tenant_a)).date())

    def test_a_per_equipment_load_runs_on_one_known_machine(self):
        from Tracker.services.dwi.batch_lifecycle import start_load
        self._gates(scope="PER_EQUIPMENT")
        with self.assertRaisesMessage(ValidationError, "machine isn't recorded"):
            start_load(work_order=self.wo, step=self.step, parts=self.parts[:2], user=self.user_a)

    def test_the_queue_says_what_can_start(self):
        self._start(0)
        self.authenticate_superuser(tenant=self.tenant_a)
        resp = self.client.get(f"/api/WorkQueue/?wo={self.wo.id}")
        self.assertEqual(resp.status_code, 200, resp.content)
        rows = resp.json().get('results', resp.json())
        row = next(r for r in rows if r['step'] == str(self.step.id))
        self.assertEqual(row['qty_startable'], 0)
        self.assertEqual(row['readiness'], 'waiting_fpi')

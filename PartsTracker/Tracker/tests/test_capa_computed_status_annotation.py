"""`CAPA.computed_status_annotation()` must agree with `CAPA.computed_status`.

`CAPASerializer.get_status` returns the computed status, so the stored
`status` column is not what any client displays. `filterset_fields` filtered
that stored column, which meant filtering by a status you could see returned
the wrong rows:

    filter status=IN_PROGRESS          -> 1 row, though 5 rows displayed "In Progress"
    filter status=OPEN                 -> rows displaying "In Progress"
    filter status=PENDING_VERIFICATION -> rows displaying "In Progress"

`CAPAFilterSet` now resolves `status` through the SQL annotation. That
introduces a duplication risk — the branch logic exists as both a Python
property and a `Case` expression — so this test pins them together across
every branch. If someone edits one and not the other, this fails.
"""
from django.contrib.auth import get_user_model

from Tracker.models import (
    CAPA, CapaStatus, CapaTasks, CapaTaskStatus, CapaTaskType, CapaVerification,
    RcaRecord, Tenant,
)
from Tracker.tests.base import TenantContextMixin, VectorTestCase


class CapaComputedStatusAnnotationTests(TenantContextMixin, VectorTestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(
            name="Computed", slug="computed-status", tier="PRO",
        )
        self.set_tenant_context(self.tenant)
        User = get_user_model()
        self.user = User.objects.create_user(
            username="cs-user", email="cs@user.test", password="x",
            tenant=self.tenant,
        )

    def _capa(self, number, stored=CapaStatus.OPEN):
        return CAPA.objects.create(
            tenant=self.tenant, capa_number=number, capa_type='CORRECTIVE',
            severity='MINOR', status=stored,
            problem_statement=f'Fixture {number}',
            assigned_to=self.user,
        )

    def _task(self, capa, status):
        return CapaTasks.objects.create(
            tenant=self.tenant, capa=capa, task_type=CapaTaskType.CORRECTIVE,
            description=f'task-{status}', status=status,
        )

    def _rca(self, capa, summary):
        return RcaRecord.objects.create(
            tenant=self.tenant, capa=capa, rca_method='FIVE_WHYS',
            problem_description='desc', root_cause_summary=summary,
            conducted_by=self.user,
        )

    def _annotated(self, capa):
        return (
            CAPA.objects
            .annotate(_cs=CAPA.computed_status_annotation())
            .values_list('_cs', flat=True)
            .get(pk=capa.pk)
        )

    def _assert_agree(self, capa, expected):
        prop = capa.computed_status
        sql = self._annotated(capa)
        self.assertEqual(prop, expected, f'property wrong for {capa.capa_number}')
        self.assertEqual(
            sql, prop,
            f'SQL annotation ({sql}) disagrees with property ({prop}) for '
            f'{capa.capa_number} — the Case expression has drifted from '
            f'computed_status',
        )

    # -- one case per branch ------------------------------------------------

    def test_no_work_is_open(self):
        self._assert_agree(self._capa('C-OPEN'), CapaStatus.OPEN)

    def test_any_task_is_in_progress(self):
        c = self._capa('C-TASK')
        self._task(c, CapaTaskStatus.NOT_STARTED)
        self._assert_agree(c, CapaStatus.IN_PROGRESS)

    def test_rca_only_is_in_progress(self):
        c = self._capa('C-RCA')
        self._rca(c, 'a cause')
        self._assert_agree(c, CapaStatus.IN_PROGRESS)

    def test_all_tasks_done_but_no_rca_is_in_progress(self):
        """The exact shape that broke the two training CAPAs."""
        c = self._capa('C-NORCA', stored=CapaStatus.PENDING_VERIFICATION)
        self._task(c, CapaTaskStatus.COMPLETED)
        self._assert_agree(c, CapaStatus.IN_PROGRESS)

    def test_all_tasks_done_plus_rca_is_pending_verification(self):
        c = self._capa('C-PV')
        self._task(c, CapaTaskStatus.COMPLETED)
        self._rca(c, 'a cause')
        self._assert_agree(c, CapaStatus.PENDING_VERIFICATION)

    def test_one_open_task_blocks_pending_verification(self):
        """The exact shape that broke CAPA-2024-002 — a single unstarted
        tag-along task drops it back to In Progress."""
        c = self._capa('C-ONEOPEN')
        self._task(c, CapaTaskStatus.COMPLETED)
        self._task(c, CapaTaskStatus.NOT_STARTED)
        self._rca(c, 'a cause')
        self._assert_agree(c, CapaStatus.IN_PROGRESS)

    def test_rca_without_summary_does_not_count(self):
        c = self._capa('C-EMPTYRCA')
        self._task(c, CapaTaskStatus.COMPLETED)
        self._rca(c, None)
        self._assert_agree(c, CapaStatus.IN_PROGRESS)

    def test_confirmed_verification_is_closed(self):
        c = self._capa('C-CLOSED')
        self._task(c, CapaTaskStatus.COMPLETED)
        self._rca(c, 'a cause')
        CapaVerification.objects.create(
            tenant=self.tenant, capa=c, verified_by=self.user,
            verification_method='audit', verification_criteria='zero defects',
            effectiveness_result='CONFIRMED',
        )
        self._assert_agree(c, CapaStatus.CLOSED)

    def test_closed_wins_over_open_tasks(self):
        """Verification confirmed short-circuits everything else."""
        c = self._capa('C-CLOSED2')
        self._task(c, CapaTaskStatus.NOT_STARTED)
        CapaVerification.objects.create(
            tenant=self.tenant, capa=c, verified_by=self.user,
            verification_method='audit', verification_criteria='zero defects',
            effectiveness_result='CONFIRMED',
        )
        self._assert_agree(c, CapaStatus.CLOSED)

    def test_unconfirmed_verification_is_not_closed(self):
        c = self._capa('C-NOTEFF')
        self._task(c, CapaTaskStatus.COMPLETED)
        self._rca(c, 'a cause')
        CapaVerification.objects.create(
            tenant=self.tenant, capa=c, verified_by=self.user,
            verification_method='audit', verification_criteria='zero defects',
            effectiveness_result='NOT_EFFECTIVE',
        )
        self._assert_agree(c, CapaStatus.PENDING_VERIFICATION)

    # -- the filter actually uses it ----------------------------------------

    def test_filtering_matches_what_each_row_displays(self):
        """The user-visible symptom: filter by a status and get exactly the
        rows that display it."""
        open_capa = self._capa('F-OPEN')
        in_prog = self._capa('F-INPROG', stored=CapaStatus.CLOSED)
        self._task(in_prog, CapaTaskStatus.NOT_STARTED)
        pending = self._capa('F-PV', stored=CapaStatus.OPEN)
        self._task(pending, CapaTaskStatus.COMPLETED)
        self._rca(pending, 'a cause')

        qs = CAPA.objects.annotate(_cs=CAPA.computed_status_annotation())
        by_status = lambda s: set(
            qs.filter(_cs=s).values_list('capa_number', flat=True))

        self.assertEqual(by_status(CapaStatus.OPEN), {'F-OPEN'})
        self.assertEqual(by_status(CapaStatus.IN_PROGRESS), {'F-INPROG'})
        self.assertEqual(by_status(CapaStatus.PENDING_VERIFICATION), {'F-PV'})
        # Stored values were deliberately wrong on two of the three; the
        # filter must ignore them.
        self.assertEqual(open_capa.status, CapaStatus.OPEN)
        self.assertEqual(in_prog.status, CapaStatus.CLOSED)

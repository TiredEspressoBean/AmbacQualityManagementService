"""Workload Control — order release against capacity norms.

Two of these tests exist because the Workload Control literature says they are the
ways this goes wrong, and both failures are quiet:

- **Premature idleness.** Holding an order back while a resource stands idle loses
  hours that can never be recovered, and the order is late for nothing. A norm is a
  ceiling on commitment, not a reason to starve a resource.
- **Measuring the wrong half.** Order release improves shop-floor metrics while it can
  worsen total delivery, so nothing here should be read as proof the policy is good —
  only that it does what it claims.

The rest pin the seam that lets a constraint-driven policy replace the gate without
touching the walk around it.
"""
from datetime import time as dtime, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from Tracker.models import (
    Equipments, OptimizationConfig, Parts, PartTypes, Processes, ProcessStep, Shift,
    Steps, StepTiming, Tenant, WorkCenter, WorkOrder, WorkOrderStatus,
)
from Tracker.models.scheduling import ReleaseMode, ReleasePolicyChoice
from Tracker.services.planning.workload_control import (
    ConstraintFocusPolicy, ReleasePolicy, build_policy, recommend_release,
)
from Tracker.tests.base import TenantContextMixin


class WorkloadControlTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="WLC", slug="wlc", tier="PRO")
        self.set_tenant_context(self.tenant)
        get_user_model().objects.create_user(
            username="wlc-op", email="wlc@c.test", password="x", tenant=self.tenant,
            default_shift=Shift.objects.create(
                tenant=self.tenant, code="DAY", name="Day", start_time=dtime(8, 0),
                end_time=dtime(16, 0), days_of_week="0,1,2,3,4", is_active=True))
        # Manual release: WLC only means anything when there IS a pool to release from.
        self.config = OptimizationConfig.objects.create(
            tenant=self.tenant, horizon_days=5, release_mode=ReleaseMode.MANUAL)

        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Widget")

        # Each cell gets its OWN single-step process. Sharing one process would make
        # them dependent: with no explicit StepEdges `resolve_route` falls back to
        # ProcessStep.order, so a Cell A order's route would run A→B and legitimately
        # feed Cell B — and "one cell starves while the other is loaded" could never
        # be constructed.
        self.cell_a, self.step_a, self.proc_a = self._cell("Cell A", "A", "Cut", 120)
        self.cell_b, self.step_b, self.proc_b = self._cell("Cell B", "B", "Polish", 120)

    def _cell(self, name, code, step_name, minutes):
        wc = WorkCenter.objects.create(tenant=self.tenant, name=name, code=code)
        eq = Equipments.objects.create(
            tenant=self.tenant, name=f"M-{code}", is_schedulable=True,
            runs_unattended=False)
        wc.equipment.add(eq)
        step = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name=step_name, step_type="TASK",
            work_center=wc)
        StepTiming.objects.create(tenant=self.tenant, step=step,
                                  cycle_time_minutes=minutes)
        process = Processes.objects.create(
            tenant=self.tenant, name=f"P-{code}", part_type=self.pt)
        ProcessStep.objects.create(process=process, step=step, order=1)
        return wc, step, process

    def _wo(self, erp, step, units=1, released=False):
        process = self.proc_a if step == self.step_a else self.proc_b
        wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id=erp, workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=units, process=process,
            expected_completion=timezone.localdate() + timedelta(days=4),
            released_at=timezone.now() if released else None)
        for i in range(units):
            Parts.objects.create(tenant=self.tenant, ERP_id=f"{erp}-P{i}",
                                 part_type=self.pt, work_order=wo, step=step)
        return wo

    # --- the walk ----------------------------------------------------------

    def test_a_small_pool_inside_the_norms_is_all_released(self):
        for i in range(2):
            self._wo(f"WO-S{i}", self.step_a)
        out = recommend_release(self.tenant)
        self.assertEqual(out['held_count'], 0)
        self.assertTrue(all(d['release'] for d in out['decisions']))

    def test_work_beyond_the_norm_is_held_and_names_what_blocked_it(self):
        """A held order must say which resource stopped it — 'not now' with no reason
        is something a planner can only override blindly."""
        self._wo("WO-BIG", self.step_a, units=200)
        for i in range(3):
            self._wo(f"WO-N{i}", self.step_a, units=200)
        out = recommend_release(self.tenant)
        held = [d for d in out['decisions'] if not d['release']]
        self.assertTrue(held)
        self.assertTrue(held[0]['blocking_resource'])
        self.assertIn("norm", held[0]['reason'].lower())

    def test_a_tighter_norm_releases_less(self):
        for i in range(6):
            self._wo(f"WO-T{i}", self.step_a, units=20)
        loose = recommend_release(self.tenant)['released_count']
        self.config.workload_norm_pct = 25
        self.config.save(update_fields=["workload_norm_pct"])
        tight = recommend_release(self.tenant)['released_count']
        self.assertLessEqual(tight, loose)

    def test_resources_report_the_arithmetic_not_just_a_verdict(self):
        self._wo("WO-R", self.step_a)
        row = recommend_release(self.tenant)['resources'][0]
        for key in ('name', 'committed_hours', 'norm_hours', 'capacity_hours'):
            self.assertIn(key, row)

    # --- premature idleness (the documented failure mode) -------------------

    def test_a_starving_resource_is_fed_even_when_the_norm_says_no(self):
        """Cell B has nothing committed. Holding its only work because some OTHER
        resource is at its ceiling would idle Cell B for nothing — hours the shop can
        never get back."""
        self.config.workload_norm_pct = 1   # everything breaches immediately
        self.config.save(update_fields=["workload_norm_pct"])
        self._wo("WO-A-LOAD", self.step_a, units=50)
        self._wo("WO-B-ONLY", self.step_b, units=1)

        out = recommend_release(self.tenant)
        b = next(d for d in out['decisions'] if d['erp_id'] == "WO-B-ONLY")
        self.assertTrue(b['release'], "a starving resource must be fed")
        self.assertIn("idle", b['reason'].lower())

    def test_starvation_release_does_not_flood_the_starving_resource(self):
        """It feeds the resource, it doesn't empty the pool into it — exactly one
        order per starving resource, then the norms apply again."""
        self.config.workload_norm_pct = 1
        self.config.save(update_fields=["workload_norm_pct"])
        for i in range(5):
            self._wo(f"WO-B{i}", self.step_b, units=1)
        out = recommend_release(self.tenant)
        self.assertEqual(out['released_count'], 1)

    # --- the policy seam ---------------------------------------------------

    def test_default_policy_gates_on_every_resource(self):
        policy = build_policy(self.tenant, self.config)
        self.assertIsInstance(policy, ReleasePolicy)
        self.assertEqual(policy.key, 'wlc')
        norms = policy.norms(None, {'a': 100.0, 'b': 50.0})
        self.assertEqual(set(norms), {'a', 'b'})

    def test_constraint_policy_gates_only_on_the_flagged_work_centre(self):
        """The DBR seam: same walk, same starvation rule, different gate."""
        self.cell_b.is_constraint = True
        self.cell_b.save(update_fields=["is_constraint"])
        self.config.release_policy = ReleasePolicyChoice.CONSTRAINT
        self.config.save(update_fields=["release_policy"])

        policy = build_policy(self.tenant, self.config)
        self.assertIsInstance(policy, ConstraintFocusPolicy)
        norms = policy.norms(None, {self.cell_a.id: 100.0, self.cell_b.id: 50.0})
        self.assertEqual(set(norms), {self.cell_b.id})

    def test_constraint_policy_ignores_load_on_unconstrained_resources(self):
        """The point of pacing to the bottleneck: a busy non-constraint must not hold
        work back, because it isn't what governs output."""
        self.cell_b.is_constraint = True
        self.cell_b.save(update_fields=["is_constraint"])
        self.config.release_policy = ReleasePolicyChoice.CONSTRAINT
        self.config.workload_norm_pct = 100
        self.config.save(update_fields=["release_policy", "workload_norm_pct"])

        # Heavy load on Cell A only — under WLC this would gate; under CONSTRAINT it
        # is irrelevant because Cell A doesn't govern output.
        self._wo("WO-A-HEAVY", self.step_a, units=500)
        out = recommend_release(self.tenant)
        a = next(d for d in out['decisions'] if d['erp_id'] == "WO-A-HEAVY")
        self.assertTrue(a['release'])
        self.assertEqual(out['policy'], 'constraint')

    def test_constraint_policy_falls_back_when_no_constraint_is_flagged(self):
        """Gating on nothing would release the whole pool — a misconfiguration must
        not silently disable the control."""
        self.config.release_policy = ReleasePolicyChoice.CONSTRAINT
        self.config.save(update_fields=["release_policy"])
        policy = build_policy(self.tenant, self.config)
        norms = policy.norms(None, {'a': 100.0, 'b': 50.0})
        self.assertEqual(set(norms), {'a', 'b'})

    def test_the_constraint_flag_is_reachable_over_the_api(self):
        """The flag shipped on the model but nowhere else, so the CONSTRAINT policy
        silently behaved like the default — a setting that does nothing is worse than
        no setting. This pins the whole path: PATCH the work centre, and the policy
        gates on it."""
        from Tracker.serializers.mes_standard import WorkCenterSerializer

        self.assertIn('is_constraint', WorkCenterSerializer.Meta.fields)

        ser = WorkCenterSerializer(self.cell_b, data={'is_constraint': True},
                                   partial=True)
        self.assertTrue(ser.is_valid(), ser.errors)
        ser.save()

        self.config.release_policy = ReleasePolicyChoice.CONSTRAINT
        self.config.save(update_fields=["release_policy"])
        policy = build_policy(self.tenant, self.config)
        norms = policy.norms(None, {self.cell_a.id: 100.0, self.cell_b.id: 50.0})
        self.assertEqual(set(norms), {self.cell_b.id})

    def test_marking_a_constraint_does_not_fork_a_work_centre_version(self):
        """It's a planning judgement that changes when you buy a machine or win a
        contract — versioning the work centre each time would bury real configuration
        history under scheduling opinion."""
        from Tracker.serializers.mes_standard import WorkCenterSerializer

        before = self.cell_b.version
        ser = WorkCenterSerializer(self.cell_b, data={'is_constraint': True},
                                   partial=True)
        ser.is_valid(raise_exception=True)
        saved = ser.save()
        self.assertEqual(saved.version, before)
        self.assertTrue(saved.is_constraint)

    # --- no planned lead times -------------------------------------------

    def test_release_is_driven_by_load_not_by_dates(self):
        """Lead time syndrome protection: two identical orders differing ONLY in due
        date must get the same verdict, because nothing here reads a planned lead
        time. If dates started to matter, the inflation loop becomes possible."""
        near = self._wo("WO-NEAR", self.step_a, units=1)
        far = self._wo("WO-FAR", self.step_a, units=1)
        WorkOrder.objects.filter(pk=far.pk).update(
            expected_completion=timezone.localdate() + timedelta(days=900))
        out = recommend_release(self.tenant)
        verdicts = {d['erp_id']: d['release'] for d in out['decisions']}
        self.assertEqual(verdicts[near.ERP_id], verdicts["WO-FAR"])

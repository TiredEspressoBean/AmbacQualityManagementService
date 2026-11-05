"""Freezing and unfreezing SPC limits both need a reason, kept on the baseline (user
decision 2026-10-28). Freezing took none; unfreezing sent a fixed sentence."""
from Tracker.models import MeasurementDefinition, PartTypes, Steps
from Tracker.models.spc import BaselineStatus, ChartType, SPCBaseline
from Tracker.services.mes.spc_baseline import freeze_spc_baseline
from Tracker.tests.base import TenantTestCase


class SpcReasonTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Body", ID_prefix="B-")
        step = Steps.objects.create(tenant=self.tenant_a, name="Measure", part_type=pt)
        self.mdef = MeasurementDefinition.objects.create(
            tenant=self.tenant_a, step=step, label="Bore", type="NUMERIC", unit="mm")
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            'view_spcbaseline', 'add_spcbaseline', 'change_spcbaseline',
            'view_measurementdefinition', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)

    def _body(self, **extra):
        return {"measurement_definition_id": str(self.mdef.id), "chart_type": ChartType.I_MR,
                "subgroup_size": 1, "individual_ucl": "5.3", "individual_cl": "5.0",
                "individual_lcl": "4.7", "mr_ucl": "0.37", "mr_cl": "0.11", "sample_count": 25, **extra}

    def test_a_freeze_needs_a_reason(self):
        r = self.client.post("/api/spc-baselines/freeze/", self._body(), format="json")
        self.assertEqual(r.status_code, 400, r.content)
        r = self.client.post("/api/spc-baselines/freeze/", self._body(freeze_reason="  "), format="json")
        self.assertEqual(r.status_code, 400, r.content)

    def test_the_freeze_reason_is_kept(self):
        r = self.client.post("/api/spc-baselines/freeze/",
                             self._body(freeze_reason="Stable over 25 runs"), format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["freeze_reason"], "Stable over 25 runs")

    def test_an_unfreeze_needs_a_reason_and_keeps_it(self):
        baseline = freeze_spc_baseline({**self._body(freeze_reason="Stable"),
                                        "measurement_definition_id": self.mdef.id}, user=self.user_a)
        r = self.client.post(f"/api/spc-baselines/{baseline.id}/supersede/", {"reason": ""}, format="json")
        self.assertEqual(r.status_code, 400, r.content)
        r = self.client.post(f"/api/spc-baselines/{baseline.id}/supersede/",
                             {"reason": "New supplier changed the process"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        baseline.refresh_from_db()
        self.assertEqual((baseline.status, baseline.superseded_reason),
                         (BaselineStatus.SUPERSEDED, "New supplier changed the process"))

    def test_a_new_freeze_says_why_the_old_one_went(self):
        first = freeze_spc_baseline({**self._body(freeze_reason="Startup"),
                                     "measurement_definition_id": self.mdef.id}, user=self.user_a)
        second = freeze_spc_baseline({**self._body(freeze_reason="After fixture change"),
                                      "measurement_definition_id": self.mdef.id}, user=self.user_a)
        first.refresh_from_db()
        self.assertEqual(first.status, BaselineStatus.SUPERSEDED)
        self.assertEqual(first.superseded_by_id, second.id)
        self.assertEqual(first.superseded_reason, "Replaced by a new baseline: After fixture change")
        self.assertEqual(SPCBaseline.objects.filter(status=BaselineStatus.ACTIVE).count(), 1)

    def test_the_chart_keeps_the_newest_points_when_the_window_holds_more(self):
        """Readings come oldest first; `limit` keeps the newest, not the oldest (hunt
        2026-11-05: [:limit] dropped the latest readings past 500)."""
        import datetime
        from django.utils import timezone
        from Tracker.models import StepExecutionMeasurement
        mdef = MeasurementDefinition.objects.create(
            tenant=self.tenant_a, step=self.mdef.step, label="OD", type="NUMERIC", unit="mm",
            nominal=10, upper_tol=1, lower_tol=1)
        from Tracker.models import Parts, StepExecution
        step = self.mdef.step
        now = timezone.now()
        for days_ago, value in ((3, 10.1), (2, 10.2), (1, 10.3)):
            part = Parts.objects.create(tenant=self.tenant_a, ERP_id=f"B-{days_ago}",
                                        part_type=step.part_type, step=step)
            visit = StepExecution.objects.create(tenant=self.tenant_a, part=part, step=step,
                                                 status="IN_PROGRESS")
            sem = StepExecutionMeasurement.objects.create(
                tenant=self.tenant_a, step_execution=visit, measurement_definition=mdef, value=value,
                recorded_by=self.user_a)
            StepExecutionMeasurement.objects.filter(pk=sem.pk).update(
                recorded_at=now - datetime.timedelta(days=days_ago))
        r = self.client.get("/api/spc/data/", {"measurement_id": str(mdef.id), "limit": 2})
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual([float(p["value"]) for p in r.json()["data_points"]], [10.2, 10.3])

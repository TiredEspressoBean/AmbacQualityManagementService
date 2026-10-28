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

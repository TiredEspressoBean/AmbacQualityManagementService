"""
Tests for the SPCBaseline dual-versioning unification.

Verifies:
- SPCBaseline.create_new_version raises NotImplementedError (vestigial SecureModel
  path is blocked).
- freeze_spc_baseline produces a correctly-shaped ACTIVE baseline row.
- Freezing a second baseline supersedes the first.
"""
from __future__ import annotations

from Tracker.models import SPCBaseline, BaselineStatus, ChartType
from Tracker.services.mes.spc_baseline import freeze_spc_baseline
from Tracker.tests.base import TenantTestCase


class SPCBaselineCreateNewVersionBlockedTestCase(TenantTestCase):
    """create_new_version must raise NotImplementedError on SPCBaseline."""

    def setUp(self):
        super().setUp()
        from Tracker.models import Steps, MeasurementDefinition, PartTypes

        self.part_type = PartTypes.objects.create(
            tenant=self.tenant_a,
            name="Test Part",
            ID_prefix="TP-",
        )
        self.step = Steps.objects.create(
            tenant=self.tenant_a,
            name="Inspect",
            part_type=self.part_type,
        )
        self.mdef = MeasurementDefinition.objects.create(
            tenant=self.tenant_a,
            step=self.step,
            label="Diameter",
            type="NUMERIC",
            unit="mm",
        )
        self.baseline = SPCBaseline.objects.create(
            tenant=self.tenant_a,
            measurement_definition=self.mdef,
            chart_type=ChartType.I_MR,
            subgroup_size=1,
            individual_ucl="10.500000",
            individual_cl="10.000000",
            individual_lcl="9.500000",
            frozen_by=self.user_a,
            status=BaselineStatus.ACTIVE,
        )

    def test_create_new_version_raises(self):
        with self.assertRaises(NotImplementedError):
            self.baseline.create_new_version()


class FreezeSPCBaselineServiceTestCase(TenantTestCase):
    """freeze_spc_baseline creates a correctly-shaped ACTIVE baseline row."""

    def setUp(self):
        super().setUp()
        from Tracker.models import Steps, MeasurementDefinition, PartTypes

        self.part_type = PartTypes.objects.create(
            tenant=self.tenant_a,
            name="Freeze Part",
            ID_prefix="FP-",
        )
        self.step = Steps.objects.create(
            tenant=self.tenant_a,
            name="Measure",
            part_type=self.part_type,
        )
        self.mdef = MeasurementDefinition.objects.create(
            tenant=self.tenant_a,
            step=self.step,
            label="Width",
            type="NUMERIC",
            unit="mm",
        )

    def _i_mr_data(self):
        return {
            "measurement_definition_id": self.mdef.id,
            "chart_type": ChartType.I_MR,
            "subgroup_size": 1,
            "individual_ucl": "5.300000",
            "individual_cl": "5.000000",
            "individual_lcl": "4.700000",
            "mr_ucl": "0.369000",
            "mr_cl": "0.113000",
            "sample_count": 25,
            "notes": "Initial freeze",
        }

    def test_freeze_creates_active_baseline(self):
        baseline = freeze_spc_baseline(self._i_mr_data(), user=self.user_a)

        self.assertIsNotNone(baseline.pk)
        self.assertEqual(baseline.status, BaselineStatus.ACTIVE)
        self.assertEqual(baseline.measurement_definition_id, self.mdef.id)
        self.assertEqual(baseline.chart_type, ChartType.I_MR)
        self.assertEqual(baseline.subgroup_size, 1)
        self.assertEqual(baseline.frozen_by, self.user_a)
        self.assertEqual(baseline.sample_count, 25)
        self.assertEqual(baseline.notes, "Initial freeze")

    def test_freeze_sets_control_limit_fields(self):
        baseline = freeze_spc_baseline(self._i_mr_data(), user=self.user_a)

        self.assertIsNotNone(baseline.individual_ucl)
        self.assertIsNotNone(baseline.individual_cl)
        self.assertIsNotNone(baseline.individual_lcl)
        self.assertIsNotNone(baseline.mr_ucl)
        self.assertIsNotNone(baseline.mr_cl)

    def test_second_freeze_supersedes_first(self):
        first = freeze_spc_baseline(self._i_mr_data(), user=self.user_a)
        self.assertEqual(first.status, BaselineStatus.ACTIVE)

        second = freeze_spc_baseline(self._i_mr_data(), user=self.user_a)
        self.assertEqual(second.status, BaselineStatus.ACTIVE)

        first.refresh_from_db()
        self.assertEqual(first.status, BaselineStatus.SUPERSEDED)

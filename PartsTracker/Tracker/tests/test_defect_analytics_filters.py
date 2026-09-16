"""Cross-facet filtering on the defect-analysis dashboard endpoints.

The /quality/defects page drills down by defect type, process and part type.
Each breakdown is also the control that sets its own filter, so each endpoint
takes every filter EXCEPT its own axis -- filter the Pareto by defect type and
clicking one bar leaves a single bar at 100% with nothing else to click.

The counting is the fragile part, and is what these tests are really for.
`defect-pareto` counts error *instances* through a multi-valued relation, so
adding a filter in a second `.filter()` call makes Django add a second JOIN and
`Count('report_instances')` silently counts the cross-product. When this was
first written that tripled the numbers: filtering to one station reported more
defects for that station than the whole shop had. A filter must never increase
a count, which is the invariant asserted below.
"""
from datetime import timedelta

from django.utils import timezone

from Tracker.models import (
    Parts, PartTypes, Processes, QualityErrorsList, QualityReportDefect,
    QualityReports, Steps, WorkOrder, WorkOrderStatus,
)
from Tracker.tests.base import TenantTestCase


class DefectAnalyticsCrossFacetTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        t = self.tenant_a
        self.pt = PartTypes.objects.create(tenant=t, name="Injector")
        self.other_pt = PartTypes.objects.create(tenant=t, name="Housing")
        process = Processes.objects.create(tenant=t, name="P-DEF", part_type=self.pt)
        self.flow = Steps.objects.create(
            tenant=t, part_type=self.pt, name="Flow Testing", step_type="TASK",
        )
        self.nozzle = Steps.objects.create(
            tenant=t, part_type=self.pt, name="Nozzle Inspection", step_type="TASK",
        )
        wo = WorkOrder.objects.create(
            tenant=t, ERP_id="WO-DEF-1", workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=1, process=process,
        )
        self.err = QualityErrorsList.objects.create(
            tenant=t, error_name="Flow rate out of spec", error_example="x",
        )

        # Three FAIL reports at Flow Testing, each carrying the same defect type.
        # Three is the point: with the duplicate-join bug the count came back as
        # 3x the real number, so a wrong implementation cannot pass by accident.
        self.reports = []
        for i in range(3):
            part = Parts.objects.create(
                tenant=t, ERP_id=f"P-DEF-{i}", part_type=self.pt,
                work_order=wo, step=self.flow,
            )
            r = QualityReports.objects.create(
                tenant=t, part=part, step=self.flow, status="FAIL",
            )
            QualityReportDefect.objects.create(report=r, error_type=self.err)
            self.reports.append(r)

        # One more at a different step, so a process filter has something to exclude.
        other_part = Parts.objects.create(
            tenant=t, ERP_id="P-DEF-OTHER", part_type=self.pt,
            work_order=wo, step=self.nozzle,
        )
        r = QualityReports.objects.create(
            tenant=t, part=other_part, step=self.nozzle, status="FAIL",
        )
        QualityReportDefect.objects.create(report=r, error_type=self.err)

        self.authenticate_as(self.user_a, self.tenant_a)
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            'view_qualityreports', 'view_qualityerrorslist', 'full_tenant_access',
        ])

    def _pareto(self, **params):
        res = self.client.get('/api/dashboard/defect-pareto/', params)
        self.assertEqual(res.status_code, 200, getattr(res, 'data', res))
        return {d['errorType']: d['count'] for d in res.data['data']}

    def test_pareto_filter_does_not_inflate_counts(self):
        """The regression. Filtering must narrow, never multiply."""
        unfiltered = self._pareto(days=30)
        filtered = self._pareto(days=30, process="Flow Testing")

        self.assertEqual(unfiltered["Flow rate out of spec"], 4)
        # Three of the four are at Flow Testing. With the second-JOIN bug this
        # came back as 9 or 12 -- larger than the unfiltered total.
        self.assertEqual(filtered["Flow rate out of spec"], 3)
        self.assertLessEqual(
            filtered["Flow rate out of spec"], unfiltered["Flow rate out of spec"],
            "a filter increased a count, which means the query is joining twice",
        )

    def test_pareto_ignores_its_own_axis(self):
        """Pareto IS the defect_type axis, so it must not filter by it.

        If it did, clicking a bar would leave that one bar at 100% and no way
        to choose another.
        """
        both = self._pareto(days=30, defect_type="Flow rate")
        self.assertEqual(both.get("Flow rate out of spec"), 4)

    def test_part_type_filter_excludes_other_part_types(self):
        self.assertEqual(self._pareto(days=30, part_type="Injector"), {"Flow rate out of spec": 4})
        self.assertEqual(self._pareto(days=30, part_type="Housing"), {})

    def test_quality_rates_defect_type_narrows_only_the_numerator(self):
        """Defect rate must not become 100% the moment you pick a defect type.

        An inspection carries no defect type, so narrowing the denominator to
        "inspections that had this defect" would make every rate 100% by
        construction. defect_type applies to the failure count only.
        """
        res = self.client.get('/api/dashboard/quality-rates/', {
            'days': 30, 'defect_type': "Flow rate",
        })
        self.assertEqual(res.status_code, 200, getattr(res, 'data', res))
        self.assertEqual(res.data['total_inspected'], 4)
        self.assertEqual(res.data['total_failed'], 4)

        scoped = self.client.get('/api/dashboard/quality-rates/', {
            'days': 30, 'process': "Flow Testing",
        })
        # A scoping filter narrows both sides.
        self.assertEqual(scoped.data['total_inspected'], 3)
        self.assertEqual(scoped.data['total_failed'], 3)

    def test_defects_by_process_ignores_its_own_axis(self):
        res = self.client.get('/api/dashboard/defects-by-process/', {
            'days': 30, 'process': "Flow Testing",
        })
        self.assertEqual(res.status_code, 200, getattr(res, 'data', res))
        names = {d['process_name'] for d in res.data['data']}
        self.assertIn("Nozzle Inspection", names,
                      "by-process filtered itself; the other processes must stay clickable")

    def test_defects_by_process_counts_reports_not_defect_rows(self):
        """Filtering on `errors__` joins the defect rows; counts must stay per-report."""
        res = self.client.get('/api/dashboard/defects-by-process/', {
            'days': 30, 'defect_type': "Flow rate",
        })
        counts = {d['process_name']: d['count'] for d in res.data['data']}
        self.assertEqual(counts.get("Flow Testing"), 3)

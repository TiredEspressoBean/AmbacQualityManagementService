"""View- and report-layer "today" is the plant's day (Tenant.default_timezone), not UTC.

Every case runs at 01:30 UTC on 11 Mar 2026 -- 21:30 on 10 Mar in New York (EDT). The
plant (tenant_a) is on New York time, so "today" is 10 Mar; the UTC day is already
11 Mar. tenant_b stays on UTC as the control: it must get 11 Mar, which is what shows
the day is resolved per tenant rather than shifted globally.

One test per behaviour class the viewsets and report adapters compute: an expiry /
due-in-N-days check, a default stamp, a due/overdue filter, a dashboard date range.
"""
from datetime import date, datetime, timedelta, timezone as dt_tz
from unittest import mock

from Tracker.models import (
    BOM, CAPA, CapaStatus, CalibrationRecord, PartTypes, QualityReports,
)
from Tracker.models.mes_standard import EquipmentType, Equipments
from Tracker.tests.base import TenantTestCase

EVENING = datetime(2026, 3, 11, 1, 30, tzinfo=dt_tz.utc)  # 21:30 in New York, 10 Mar
PLANT_DAY = date(2026, 3, 10)
UTC_DAY = date(2026, 3, 11)


def at_evening():
    return mock.patch('django.utils.timezone.now', return_value=EVENING)


def _rows(res):
    """A list endpoint's rows, paginated or not."""
    data = res.data
    return data['results'] if isinstance(data, dict) and 'results' in data else data


class PlantClockViewTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.tenant_a.default_timezone = 'America/New_York'
        self.tenant_a.save()
        self.tenant_b.default_timezone = 'UTC'
        self.tenant_b.save()

    def _as(self, user, tenant, perms):
        self.grant_tenant_permissions(user, tenant, ['full_tenant_access', *perms])
        self.authenticate_as(user, tenant)

    # --- expiry / due-in-N-days ----------------------------------------------

    def _calibrated_gauge(self, tenant, name):
        eq_type = EquipmentType.objects.create(tenant=tenant, name=f"Micrometer {name}",
                                               requires_calibration=True)
        eq = Equipments.objects.create(tenant=tenant, name=name, serial_number=name,
                                       equipment_type=eq_type)
        return CalibrationRecord.objects.create(
            tenant=tenant, equipment=eq,
            calibration_date=PLANT_DAY - timedelta(days=180),
            due_date=PLANT_DAY, result='PASS')

    def test_calibration_due_today_is_not_overdue_in_the_evening(self):
        from Tracker.reports.adapters.calibration_due import CalibrationDueAdapter
        cal_a = self._calibrated_gauge(self.tenant_a, "M-A")
        self.switch_tenant_context(self.tenant_b)
        self._calibrated_gauge(self.tenant_b, "M-B")
        self.switch_tenant_context(self.tenant_a)

        with at_evening():
            # Report: due today on the plant's clock is 0 days out, not -1.
            ctx = CalibrationDueAdapter().build_context({}, self.user_a, self.tenant_a)
            self.assertEqual(ctx.generated_date, PLANT_DAY)
            [item] = ctx.items
            self.assertEqual(item.days_until_due, 0)
            self.assertEqual(ctx.overdue_count, 0)

            # Viewset: the overdue list leaves it out.
            self._as(self.user_a, self.tenant_a, ['view_calibrationrecord'])
            res = self.client.get('/api/CalibrationRecords/overdue/')
            self.assertEqual(res.status_code, 200, getattr(res, 'data', res))
            self.assertNotIn(str(cal_a.id), {str(r['id']) for r in _rows(res)})

            # Control: a UTC plant has rolled over, so the same due date is overdue.
            ctx_b = CalibrationDueAdapter().build_context({}, self.user_b, self.tenant_b)
            self.assertEqual(ctx_b.generated_date, UTC_DAY)
            [item_b] = ctx_b.items
            self.assertEqual(item_b.days_until_due, -1)
            self.assertEqual(ctx_b.overdue_count, 1)

    # --- default stamp ----------------------------------------------------------

    def test_bom_release_stamps_the_plant_day(self):
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Injector")
        bom = BOM.objects.create(tenant=self.tenant_a, part_type=pt, revision='A',
                                 bom_type='ASSEMBLY', status='DRAFT')
        # A POST action is gated on add_ unless it declares its own permission.
        self._as(self.user_a, self.tenant_a, ['view_bom', 'add_bom', 'change_bom'])

        with at_evening():
            res = self.client.post(f'/api/BOMs/{bom.id}/release/')
        self.assertEqual(res.status_code, 200, getattr(res, 'data', res))
        bom.refresh_from_db()
        self.assertEqual(bom.effective_date, PLANT_DAY)

    def test_report_header_prints_the_plant_day(self):
        from Tracker.reports.adapters.labor_hours import LaborHoursAdapter
        params = {'start': PLANT_DAY - timedelta(days=7), 'end': PLANT_DAY}
        with at_evening():
            ctx = LaborHoursAdapter().build_context(params, self.user_a, self.tenant_a)
            ctx_b = LaborHoursAdapter().build_context(params, self.user_b, self.tenant_b)
        self.assertEqual(ctx.generated_date, PLANT_DAY)
        self.assertEqual(ctx_b.generated_date, UTC_DAY)

    # --- due / overdue ----------------------------------------------------------

    def test_capa_due_today_is_not_overdue_in_the_evening(self):
        capa_a = CAPA.objects.create(
            tenant=self.tenant_a, capa_type='CORRECTIVE', problem_statement='due today',
            status=CapaStatus.OPEN, due_date=PLANT_DAY)
        self.switch_tenant_context(self.tenant_b)
        capa_b = CAPA.objects.create(
            tenant=self.tenant_b, capa_type='CORRECTIVE', problem_statement='due today',
            status=CapaStatus.OPEN, due_date=PLANT_DAY)
        self.switch_tenant_context(self.tenant_a)

        with at_evening():
            self._as(self.user_a, self.tenant_a, ['view_capa'])
            res = self.client.get('/api/CAPAs/', {'overdue': 'true'})
            self.assertEqual(res.status_code, 200, getattr(res, 'data', res))
            self.assertNotIn(str(capa_a.id), {r['id'] for r in _rows(res)})

            kpis = self.client.get('/api/dashboard/kpis/')
            self.assertEqual(kpis.status_code, 200, getattr(kpis, 'data', kpis))
            self.assertEqual(kpis.data['overdue_capas'], 0)

            # Control: in a UTC plant the same due date has passed.
            self._as(self.user_b, self.tenant_b, ['view_capa'])
            res_b = self.client.get('/api/CAPAs/', {'overdue': 'true'})
            self.assertEqual(res_b.status_code, 200, getattr(res_b, 'data', res_b))
            self.assertIn(str(capa_b.id), {r['id'] for r in _rows(res_b)})

    # --- dashboard date range ---------------------------------------------------

    def test_fpy_trend_counts_an_evening_report_on_the_plant_day(self):
        with at_evening():
            qa = QualityReports.objects.create(tenant=self.tenant_a, status='PASS')
            self.switch_tenant_context(self.tenant_b)
            qb = QualityReports.objects.create(tenant=self.tenant_b, status='PASS')
            self.switch_tenant_context(self.tenant_a)
            # `created_at`'s default holds the original timezone.now, which the patch
            # doesn't reach — stamp the evening explicitly.
            QualityReports.unscoped.filter(pk__in=[qa.pk, qb.pk]).update(created_at=EVENING)  # tenant-safe: two known pks

            self._as(self.user_a, self.tenant_a, ['view_qualityreports'])
            res = self.client.get('/api/dashboard/fpy-trend/', {'days': 2})
            self.assertEqual(res.status_code, 200, getattr(res, 'data', res))

            self._as(self.user_b, self.tenant_b, ['view_qualityreports'])
            res_b = self.client.get('/api/dashboard/fpy-trend/', {'days': 2})
            self.assertEqual(res_b.status_code, 200, getattr(res_b, 'data', res_b))

        # The range ends on the plant day, and the 21:30 report is counted on it --
        # not dropped as "tomorrow" by a UTC-day bucket.
        self.assertEqual([p['date'] for p in res.data['data']],
                         ['2026-03-09', '2026-03-10'])
        self.assertEqual(res.data['data'][-1]['total'], 1)
        self.assertEqual(res.data['total_inspections'], 1)

        # Control: the UTC plant's range already ends on 11 Mar.
        self.assertEqual([p['date'] for p in res_b.data['data']],
                         ['2026-03-10', '2026-03-11'])
        self.assertEqual(res_b.data['data'][-1]['total'], 1)

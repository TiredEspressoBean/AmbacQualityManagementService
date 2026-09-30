"""Model-layer "today" is the plant's day (Tenant.default_timezone), not UTC.

Every case runs at 01:30 UTC on 11 Mar 2026 — 21:30 on 10 Mar in New York (EDT). The
plant (tenant_a) is on New York time, so "today" is 10 Mar; the UTC day is already
11 Mar. One test per behaviour class: expiry, default stamp, due/overdue, date range.
"""
from datetime import date, datetime, timedelta, timezone as dt_tz
from decimal import Decimal
from unittest import mock

from Tracker.tests.base import TenantTestCase
from Tracker.models.core import Documents
from Tracker.models.qms import (
    CAPA, CapaStatus, CapaTasks, CapaTaskStatus, CalibrationRecord, TrainingRecord,
)
from Tracker.models.mes_standard import EquipmentType, Equipments
from Tracker.models.life_tracking import LifeLimitDefinition, LifeTracking

EVENING = datetime(2026, 3, 11, 1, 30, tzinfo=dt_tz.utc)  # 21:30 in New York, 10 Mar
PLANT_DAY = date(2026, 3, 10)
UTC_DAY = date(2026, 3, 11)


def at_evening():
    return mock.patch('django.utils.timezone.now', return_value=EVENING)


class PlantClockModelTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.tenant_a.default_timezone = 'America/New_York'
        self.tenant_a.save()
        # tenant_b stays on UTC — the control that shows the day really is resolved
        # per tenant, not just shifted globally.

    # --- expiry ---------------------------------------------------------------

    def test_expiring_today_is_still_current_in_the_evening(self):
        with at_evening():
            training = TrainingRecord(tenant=self.tenant_a, expires_date=PLANT_DAY)
            self.assertTrue(training.is_current)
            self.assertEqual(training.status, 'EXPIRING_SOON')

            cal = CalibrationRecord(tenant=self.tenant_a, due_date=PLANT_DAY, result='PASS')
            self.assertTrue(cal.is_current)
            self.assertEqual(cal.status, 'DUE_SOON')
            self.assertEqual(cal.days_until_due, 0)

            doc = Documents(tenant=self.tenant_a, retention_until=PLANT_DAY)
            self.assertFalse(doc.is_past_retention)

            # Control: a UTC plant has already rolled over.
            utc_training = TrainingRecord(tenant=self.tenant_b, expires_date=PLANT_DAY)
            self.assertFalse(utc_training.is_current)
            self.assertEqual(utc_training.status, 'EXPIRED')

    # --- default stamp --------------------------------------------------------

    def test_effective_date_defaults_to_the_plant_day(self):
        with at_evening():
            doc = Documents(tenant=self.tenant_a)
            doc.calculate_compliance_dates()
            self.assertEqual(doc.effective_date, PLANT_DAY)

            utc_doc = Documents(tenant=self.tenant_b)
            utc_doc.calculate_compliance_dates()
            self.assertEqual(utc_doc.effective_date, UTC_DAY)

    # --- due / overdue --------------------------------------------------------

    def test_due_today_is_not_overdue_in_the_evening(self):
        from Tracker.serializers.qms import CapaTasksSerializer
        with at_evening():
            capa = CAPA(tenant=self.tenant_a, status=CapaStatus.OPEN, due_date=PLANT_DAY)
            self.assertFalse(capa.is_overdue())

            task = CapaTasks(tenant=self.tenant_a, status=CapaTaskStatus.NOT_STARTED,
                             due_date=PLANT_DAY)
            self.assertEqual(task.check_overdue(), (False, 0))
            self.assertFalse(CapaTasksSerializer().get_is_overdue(task))

            doc = Documents(tenant=self.tenant_a, review_date=UTC_DAY)
            self.assertFalse(doc.is_due_for_review)
            self.assertEqual(doc.days_until_review, 1)

            # Calendar-based life: days elapsed counted to the plant day.
            shelf = LifeLimitDefinition(tenant=self.tenant_a, name="Shelf", unit="days",
                                        is_calendar_based=True)
            life = LifeTracking(tenant=self.tenant_a, definition=shelf,
                                reference_date=PLANT_DAY - timedelta(days=5))
            self.assertEqual(life.current_value, Decimal(5))

            # Control: in a UTC plant yesterday's due date has passed.
            utc_capa = CAPA(tenant=self.tenant_b, status=CapaStatus.OPEN, due_date=PLANT_DAY)
            self.assertTrue(utc_capa.is_overdue())

    # --- date range (querysets; tenant from the ContextVar) -------------------

    def test_calibration_querysets_use_the_plant_day(self):
        eq_type = EquipmentType.objects.create(tenant=self.tenant_a, name="Micrometer",
                                               requires_calibration=True)
        eq = Equipments.objects.create(tenant=self.tenant_a, name="M-01",
                                       serial_number="M-01", equipment_type=eq_type)
        cal = CalibrationRecord.objects.create(
            tenant=self.tenant_a, equipment=eq,
            calibration_date=PLANT_DAY - timedelta(days=180),
            due_date=PLANT_DAY, result='PASS')

        with at_evening():
            self.assertNotIn(cal, CalibrationRecord.objects.overdue())
            self.assertIn(cal, CalibrationRecord.objects.current())
            self.assertIn(cal, CalibrationRecord.objects.due_soon(within_days=0))
            self.assertNotIn(eq, Equipments.objects.calibration_overdue())
            self.assertIn(eq, Equipments.objects.calibration_due_soon(within_days=0))

            # An explicit tenant wins over the ContextVar (cross-tenant callers).
            self.assertIn(cal, CalibrationRecord.objects.overdue(tenant=self.tenant_b))

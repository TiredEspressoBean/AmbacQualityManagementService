"""
Calibration seed data: Calibration records for equipment.
"""

import random
from datetime import timedelta
from django.utils import timezone

from Tracker.models import CalibrationRecord, Equipments
from .base import BaseSeeder


class CalibrationSeeder(BaseSeeder):
    """
    Seeds calibration-related data.

    Creates:
    - Calibration records for equipment with realistic dates
    - Mix of current, due soon, and overdue calibrations
    - Historical calibration records
    """

    # Calibration labs for realism
    CALIBRATION_LABS = [
        "Precision Calibration Services",
        "National Metrology Lab",
        "QualityTest Inc.",
        "In-House Metrology",
        "AccuCal Laboratories",
        "Midwest Calibration Group",
    ]

    def seed(self, equipment):
        """Create calibration records for all equipment."""
        if not equipment:
            self.log("  No equipment to create calibration records for")
            return

        records_created = 0
        equipment_calibrated = 0

        # Equipment that typically requires calibration
        calibration_keywords = [
            'gauge', 'caliper', 'micrometer', 'cmm', 'flow',
            'torque', 'pressure', 'thermometer', 'scale',
            'indicator', 'meter', 'tester', 'multimeter'
        ]

        for eq in equipment:
            eq_name_lower = eq.name.lower()

            # Check if equipment needs calibration
            needs_calibration = any(kw in eq_name_lower for kw in calibration_keywords)

            # Also check equipment type if available
            if eq.equipment_type:
                type_name_lower = eq.equipment_type.name.lower()
                needs_calibration = needs_calibration or any(kw in type_name_lower for kw in calibration_keywords)

            if not needs_calibration:
                continue

            # Create calibration history (1-3 records)
            num_records = random.randint(1, 3)
            records = self._create_calibration_history(eq, num_records)
            records_created += records
            equipment_calibrated += 1

        self.log(f"Created {records_created} calibration records for {equipment_calibrated} pieces of equipment")

    def _create_calibration_history(self, equipment, num_records):
        """Create calibration history for a single piece of equipment."""
        # Determine calibration interval (typically 6-12 months)
        interval_days = random.choice([180, 270, 365])

        records_created = 0
        current_date = timezone.now().date()

        # Work backwards from current calibration
        for i in range(num_records):
            is_current = (i == 0)

            # Determine calibration date
            if is_current:
                # Current calibration: determine status distribution
                status_roll = random.random()

                if status_roll < 0.70:
                    # 70% - Current (calibrated within interval)
                    days_since = random.randint(30, interval_days - 30)
                    cal_date = current_date - timedelta(days=days_since)
                    due_date = cal_date + timedelta(days=interval_days)
                    result = 'pass'
                elif status_roll < 0.85:
                    # 15% - Due soon (within 30 days)
                    days_until_due = random.randint(5, 25)
                    due_date = current_date + timedelta(days=days_until_due)
                    cal_date = due_date - timedelta(days=interval_days)
                    result = 'pass'
                elif status_roll < 0.95:
                    # 10% - Overdue
                    days_overdue = random.randint(5, 60)
                    due_date = current_date - timedelta(days=days_overdue)
                    cal_date = due_date - timedelta(days=interval_days)
                    result = 'pass'
                else:
                    # 5% - Failed/Limited
                    days_since = random.randint(10, 60)
                    cal_date = current_date - timedelta(days=days_since)
                    due_date = cal_date + timedelta(days=interval_days)
                    result = random.choice(['fail', 'limited'])
            else:
                # Historical calibration (always passed)
                prev_record = CalibrationRecord.objects.filter(
                    equipment=equipment
                ).order_by('calibration_date').first()

                if prev_record:
                    cal_date = prev_record.calibration_date - timedelta(days=interval_days + random.randint(-14, 14))
                    due_date = cal_date + timedelta(days=interval_days)
                else:
                    cal_date = current_date - timedelta(days=(i + 1) * interval_days + random.randint(-14, 14))
                    due_date = cal_date + timedelta(days=interval_days)

                result = 'pass'

            # Select calibration lab
            if random.random() < 0.3:
                performed_by = "In-House Metrology"
            else:
                performed_by = random.choice(self.CALIBRATION_LABS)

            # Generate certificate number
            cert_number = f"CAL-{cal_date.strftime('%Y%m')}-{random.randint(1000, 9999)}"

            # Create notes based on result
            if result == 'pass':
                notes = "All measurements within specification. Equipment approved for use."
            elif result == 'limited':
                notes = "Limited range approved. See restrictions on calibration certificate."
            else:
                notes = "Equipment failed calibration. Removed from service pending repair/replacement."

            CalibrationRecord.objects.create(
                tenant=self.tenant,
                equipment=equipment,
                calibration_date=cal_date,
                due_date=due_date,
                result=result,
                performed_by=performed_by,
                certificate_number=cert_number,
                notes=notes,
            )

            records_created += 1

        return records_created

    def seed_overdue_alerts(self, equipment):
        """
        Create intentionally overdue calibrations for demo purposes.
        This method is separate so it can be called optionally.
        """
        if not equipment:
            return

        # Find equipment without any calibration records (not already seeded)
        uncalibrated = [
            eq for eq in equipment
            if not CalibrationRecord.objects.filter(equipment=eq).exists()
        ]

        if not uncalibrated:
            return

        # Pick 2-3 items to make overdue for demo
        overdue_count = min(3, len(uncalibrated))
        overdue_equipment = random.sample(uncalibrated, overdue_count)

        for eq in overdue_equipment:
            # Create an overdue calibration
            days_overdue = random.randint(15, 90)
            interval_days = 365
            due_date = timezone.now().date() - timedelta(days=days_overdue)
            cal_date = due_date - timedelta(days=interval_days)

            CalibrationRecord.objects.create(
                tenant=self.tenant,
                equipment=eq,
                calibration_date=cal_date,
                due_date=due_date,
                result='pass',
                performed_by=random.choice(self.CALIBRATION_LABS),
                certificate_number=f"CAL-{cal_date.strftime('%Y%m')}-{random.randint(1000, 9999)}",
                notes="CALIBRATION OVERDUE - Requires immediate attention",
            )

        self.log(f"Created {overdue_count} overdue calibration alerts for demo", warning=True)

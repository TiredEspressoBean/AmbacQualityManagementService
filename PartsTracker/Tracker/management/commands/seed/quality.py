"""
Quality seed data: Quality reports, measurements, sampling, dispositions.
"""

import random
import statistics
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone

from Tracker.models import (
    QualityReports, QualityErrorsList, QuarantineDisposition,
    MeasurementResult, EquipmentUsage, MeasurementDefinition,
    SPCBaseline, ChartType, BaselineStatus,
)
from .base import BaseSeeder


class QualitySeeder(BaseSeeder):
    """
    Seeds quality-related data.

    Creates:
    - Quality reports with measurements
    - Quality error lists
    - Quarantine dispositions
    - Equipment usage tracking
    - Historical FPY trend data
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manufacturing_seeder = None  # Set by orchestrator for equipment selection

    def seed(self, orders, users, equipment):
        """Create quality reports for sampled parts across all work orders."""
        total_reports = 0

        for order in orders:
            for work_order in order.related_orders.all():
                # Get sampled parts
                sampled_parts = work_order.parts.filter(requires_sampling=True)

                for part in sampled_parts:
                    if part.step:
                        self.create_quality_report(part, part.step, users, equipment)
                        total_reports += 1

        self.log(f"Created {total_reports} quality reports for sampled parts")

    def seed_historical_fpy(self, part_types, users, equipment):
        """Create realistic historical FPY data."""
        self._create_historical_fpy_trend(part_types, users, equipment)

    def seed_spc_baselines(self, users):
        """Create SPC baselines from existing measurement data."""
        self._create_spc_baselines(users)

    # =========================================================================
    # Quality Reports
    # =========================================================================

    def create_quality_report(self, part, step, users, equipment, timestamp=None):
        """Create quality report for a part with failure clustering."""
        # Select appropriate equipment
        selected_equipment = self._select_equipment_for_step(step, equipment)

        # Get failure rate
        failure_rate = self._get_failure_rate(selected_equipment, step)
        status = "FAIL" if random.random() < failure_rate else "PASS"

        operator = self.get_weighted_employee(users)

        # Add time variation for QA event
        qa_time = timestamp + timedelta(minutes=random.randint(15, 60)) if timestamp else timezone.now()

        qr = QualityReports.objects.create(
            tenant=self.tenant,
            part=part,
            machine=selected_equipment,
            step=step,
            description=f"{step.name} results for {part.ERP_id} - "
                       f"{'measurements completed successfully' if status == 'PASS' else 'issues found during testing'}",
            sampling_method="statistical" if random.random() > 0.3 else "manual",
            status=status,
            detected_by=operator,
        )
        # Add operator (M2M field)
        qr.operators.add(operator)

        # Backdate if timestamp provided
        if timestamp:
            QualityReports.objects.filter(pk=qr.pk).update(created_at=qa_time, updated_at=qa_time)
            self.create_audit_log(QualityReports, qr.id, 'CREATE', qa_time, operator,
                                 {'status': [None, status], 'part': [None, part.ERP_id]})

        # Create equipment usage record
        self._create_equipment_usage(selected_equipment, step, part, qr if status == "FAIL" else None, operator, qa_time)

        # Create error lists and dispositions
        self._create_error_lists_and_dispositions(qr, part.part_type, users, qa_time)

        # Create measurement results
        self._create_measurement_results(qr, step, status, users, qa_time)

        return qr

    def _select_equipment_for_step(self, step, equipment):
        """Select appropriate equipment based on step type."""
        if self.manufacturing_seeder:
            return self.manufacturing_seeder.select_equipment_for_step(step, equipment)
        return random.choice(equipment) if equipment else None

    def _get_failure_rate(self, equipment_piece, step):
        """Get failure rate based on equipment and step."""
        if self.manufacturing_seeder:
            return self.manufacturing_seeder.get_failure_rate(equipment_piece, step)

        # Default failure rate
        base_rate = 0.15
        step_name_lower = step.name.lower()
        if any(kw in step_name_lower for kw in ['inspection', 'qc', 'testing', 'validation']):
            base_rate *= 1.3
        return min(0.50, base_rate)

    def _create_equipment_usage(self, equipment, step, part, error_report, operator, timestamp):
        """Create equipment usage record."""
        if not equipment:
            return

        # Note: EquipmentUsage is an audit record protected by compliance triggers
        # and cannot be backdated. It will use current timestamps.
        EquipmentUsage.objects.create(
            tenant=self.tenant,
            equipment=equipment,
            step=step,
            part=part,
            error_report=error_report,
            operator=operator,
            notes=f"QA inspection on {equipment.name}" + (" - FAILED" if error_report else "")
        )

    def _create_measurement_results(self, qr, step, status, users, timestamp):
        """Create measurement results for a quality report."""
        for measurement_def in step.measurement_definitions.all():
            if measurement_def.type == 'NUMERIC' and measurement_def.nominal:
                if status == "PASS":
                    variance = float(min(measurement_def.upper_tol or 0, measurement_def.lower_tol or 0)) * 0.3
                    value = float(measurement_def.nominal) + random.uniform(-variance, variance)
                    is_within_spec = True
                else:
                    variance = float(max(measurement_def.upper_tol or 0, measurement_def.lower_tol or 0)) * 1.2
                    value = float(measurement_def.nominal) + random.uniform(-variance, variance)
                    is_within_spec = False

                mr = MeasurementResult.objects.create(
                    tenant=self.tenant,
                    report=qr,
                    definition=measurement_def,
                    value_numeric=round(value, 4),
                    is_within_spec=is_within_spec,
                    created_by=self.get_weighted_employee(users)
                )

                if timestamp:
                    MeasurementResult.objects.filter(pk=mr.pk).update(created_at=timestamp, updated_at=timestamp)

    # =========================================================================
    # Error Lists and Dispositions
    # =========================================================================

    def _create_error_lists_and_dispositions(self, quality_report, part_type, users, timestamp=None):
        """Create quality error lists and quarantine dispositions for failed reports."""
        error_types = [
            "Surface scratches detected",
            "Dimensional out of tolerance",
            "Contamination found",
            "Wear patterns excessive",
            "Coating defects present"
        ]

        errors = []
        if quality_report.status == "FAIL":
            for _ in range(random.randint(1, 2)):
                error_name = random.choice(error_types)
                error, created = QualityErrorsList.objects.get_or_create(
                    tenant=self.tenant,
                    error_name=error_name,
                    part_type=part_type,
                    defaults={'error_example': f"Example: {error_name} in {part_type.name}"}
                )
                errors.append(error)

        quality_report.errors.set(errors)

        # Create quarantine disposition for failed reports
        if quality_report.status == "FAIL" and quality_report.part:
            self._create_disposition(quality_report, users, timestamp)

    def _create_disposition(self, quality_report, users, timestamp):
        """Create quarantine disposition for a failed quality report."""
        disposition_types = ['REWORK', 'SCRAP', 'USE_AS_IS', 'RETURN_TO_SUPPLIER']

        disposition_type = random.choices(
            disposition_types,
            weights=[0.5, 0.2, 0.2, 0.1]
        )[0]

        target_state = self._get_disposition_state_by_age(timestamp)

        resolution_time = timestamp + timedelta(days=random.randint(1, 5)) if timestamp and target_state == 'CLOSED' else None

        disposition = QuarantineDisposition.objects.create(
            tenant=self.tenant,
            current_state='IN_PROGRESS',
            disposition_type=disposition_type,
            assigned_to=self.get_weighted_employee(users),
            description=f"Quality failure on {quality_report.part.ERP_id} at {quality_report.step.name}",
            resolution_notes=f"Disposition: {disposition_type}" if target_state == 'CLOSED' else "",
            resolution_completed=(target_state == 'CLOSED'),
            resolution_completed_by=self.get_weighted_employee(users) if target_state == 'CLOSED' else None,
            resolution_completed_at=resolution_time if target_state == 'CLOSED' else None,
            part=quality_report.part,
            step=quality_report.step,
        )

        disposition.quality_reports.add(quality_report)

        if target_state != 'IN_PROGRESS':
            QuarantineDisposition.objects.filter(pk=disposition.pk).update(current_state=target_state)

        if timestamp:
            QuarantineDisposition.objects.filter(pk=disposition.pk).update(
                created_at=timestamp,
                updated_at=resolution_time if target_state == 'CLOSED' else timestamp
            )

    def _get_disposition_state_by_age(self, created_at):
        """Determine disposition state based on age - older issues should be resolved."""
        age_days = (timezone.now() - created_at).days if created_at else 0

        if age_days <= 3:
            weights = [0.30, 0.40, 0.30]  # OPEN, IN_PROGRESS, CLOSED
        elif age_days <= 7:
            weights = [0.10, 0.20, 0.70]
        elif age_days <= 14:
            weights = [0.03, 0.07, 0.90]
        elif age_days <= 30:
            weights = [0.01, 0.02, 0.97]
        else:
            weights = [0.005, 0.005, 0.99]

        return random.choices(['OPEN', 'IN_PROGRESS', 'CLOSED'], weights=weights)[0]

    # =========================================================================
    # Historical FPY Trend
    # =========================================================================

    def _create_historical_fpy_trend(self, part_types, users, equipment):
        """Create realistic historical FPY data that tells a story."""
        import math

        days_of_history = 120  # 4 months of data
        reports_per_day_base = {'small': 8, 'medium': 20, 'large': 50}.get(self.scale, 20)

        # Define events that affect quality
        events = [
            {'day': 20, 'duration': 7, 'depth': 0.12, 'name': 'Equipment calibration issue'},
            {'day': 55, 'duration': 5, 'depth': 0.08, 'name': 'New material batch problem'},
            {'day': 95, 'duration': 6, 'depth': 0.05, 'name': 'New operator training'},
        ]

        base_fpy_start = 0.86
        base_fpy_end = 0.94
        improvement_rate = (base_fpy_end - base_fpy_start) / days_of_history

        for day_offset in range(days_of_history, 0, -1):
            timestamp = timezone.now() - timedelta(days=day_offset)

            # Calculate base FPY with improvement trend
            day_number = days_of_history - day_offset
            base_fpy = base_fpy_start + (improvement_rate * day_number)

            # Apply event impacts
            for event in events:
                if event['day'] <= day_number < event['day'] + event['duration']:
                    progress = (day_number - event['day']) / event['duration']
                    impact = event['depth'] * (1 - progress)  # Recovering
                    base_fpy -= impact

            # Add daily variation and weekly patterns
            day_of_week = timestamp.weekday()
            if day_of_week == 0:  # Monday - slightly worse
                base_fpy -= 0.02
            elif day_of_week == 4:  # Friday - slightly worse
                base_fpy -= 0.015

            # Random daily variation
            base_fpy += random.uniform(-0.03, 0.03)
            base_fpy = max(0.70, min(0.98, base_fpy))

            # Calculate number of reports for this day
            volume_variation = random.uniform(0.7, 1.3)
            reports_today = int(reports_per_day_base * volume_variation)

            # Create reports
            for _ in range(reports_today):
                part_type = random.choice(part_types)
                step = self._get_random_step_for_part_type(part_type)
                if not step:
                    continue

                # Create minimal quality report for historical data
                status = "PASS" if random.random() < base_fpy else "FAIL"
                selected_equipment = random.choice(equipment) if equipment else None
                operator = random.choice(users['employees']) if users.get('employees') else None

                qr = QualityReports.objects.create(
                    tenant=self.tenant,
                    machine=selected_equipment,
                    step=step,
                    description=f"Historical QA at {step.name}",
                    sampling_method="statistical",
                    status=status,
                    detected_by=operator,
                )

                # Backdate
                report_time = timestamp + timedelta(hours=random.randint(6, 18), minutes=random.randint(0, 59))
                QualityReports.objects.filter(pk=qr.pk).update(created_at=report_time, updated_at=report_time)

                # Create measurements for SPC
                self._create_historical_measurements(qr, step, status, report_time, day_number / days_of_history)

        self.log(f"Created {days_of_history} days of historical FPY trend data")

    def _get_random_step_for_part_type(self, part_type):
        """Get a random step for a part type."""
        from Tracker.models import Steps
        steps = list(Steps.objects.filter(part_type=part_type))
        return random.choice(steps) if steps else None

    def _create_historical_measurements(self, qr, step, status, timestamp, progress):
        """Create historical measurements with realistic SPC patterns."""
        for measurement_def in step.measurement_definitions.all():
            if measurement_def.type == 'NUMERIC' and measurement_def.nominal:
                # Base value with process improvement trend
                improvement_factor = 1 - (0.3 * progress)
                base_variance = float(min(measurement_def.upper_tol or 1, measurement_def.lower_tol or 1)) * improvement_factor

                if status == "PASS":
                    base_value = float(measurement_def.nominal) + random.gauss(0, base_variance * 0.3)
                    is_within_spec = True
                else:
                    # Out of spec
                    direction = random.choice([-1, 1])
                    offset = base_variance * random.uniform(1.1, 1.5) * direction
                    base_value = float(measurement_def.nominal) + offset
                    is_within_spec = False

                # Apply Western Electric rule violations for SPC-enabled measurements
                if measurement_def.spc_enabled and random.random() < 0.1:
                    # 10% chance to apply WE rule patterns (simulated across multiple measurements)
                    values = self._generate_western_electric_violations(
                        measurement_def, [base_value], progress
                    )
                    value = values[0] if values else base_value
                else:
                    value = base_value

                MeasurementResult.objects.create(
                    tenant=self.tenant,
                    report=qr,
                    definition=measurement_def,
                    value_numeric=round(value, 4),
                    is_within_spec=is_within_spec,
                )

    # =========================================================================
    # SPC Baselines and Western Electric Rules
    # =========================================================================

    def _create_spc_baselines(self, users):
        """Create SPC baselines from historical measurement data."""
        baselines_created = 0

        # Get all SPC-enabled numeric measurement definitions
        spc_definitions = MeasurementDefinition.objects.filter(
            tenant=self.tenant,
            type='NUMERIC',
            spc_enabled=True
        )

        for measurement_def in spc_definitions:
            # Get last 30 days of measurements
            thirty_days_ago = timezone.now() - timedelta(days=30)
            results = MeasurementResult.objects.filter(
                definition=measurement_def,
                created_at__gte=thirty_days_ago,
                value_numeric__isnull=False
            ).order_by('created_at')

            if results.count() < 25:  # Minimum for baseline
                continue

            values = [float(r.value_numeric) for r in results if r.value_numeric is not None]
            if len(values) < 25:
                continue

            # Calculate statistics
            mean = statistics.mean(values)
            std_dev = statistics.stdev(values) if len(values) > 1 else 0

            # Check if baseline already exists
            existing = SPCBaseline.objects.filter(
                tenant=self.tenant,
                measurement_definition=measurement_def,
                status=BaselineStatus.ACTIVE
            ).first()

            if existing:
                continue

            # Get a QA user for the frozen_by field
            qa_user = self.get_weighted_qa_staff(users) if users else None

            # Create I-MR baseline (individual measurements)
            baseline = SPCBaseline.objects.create(
                tenant=self.tenant,
                measurement_definition=measurement_def,
                chart_type=ChartType.I_MR,
                subgroup_size=1,
                # Individual chart limits
                individual_ucl=Decimal(str(round(mean + 3 * std_dev, 6))),
                individual_cl=Decimal(str(round(mean, 6))),
                individual_lcl=Decimal(str(round(mean - 3 * std_dev, 6))),
                # Moving range limits (using average MR)
                mr_cl=Decimal(str(round(std_dev * 1.128, 6))),  # d2 factor for n=2
                mr_ucl=Decimal(str(round(std_dev * 1.128 * 3.267, 6))),  # D4 factor
                status=BaselineStatus.ACTIVE,
                frozen_by=qa_user,
                sample_count=len(values),
                notes=f"Auto-generated baseline from {len(values)} measurements over 30 days"
            )
            baselines_created += 1

        self.log(f"Created {baselines_created} SPC baselines from historical data")

    def _generate_western_electric_violations(self, measurement_def, base_values, progress):
        """
        Generate measurement patterns that include Western Electric rule violations.

        Western Electric Rules:
        - Rule 1: Single point beyond 3σ (out-of-control)
        - Rule 2: 2 of 3 consecutive points beyond 2σ (same side)
        - Rule 3: 4 of 5 consecutive points beyond 1σ (same side)
        - Rule 4: 8 consecutive points on same side of center (run)
        - Rule 5: 6 consecutive points increasing or decreasing (trend)
        - Rule 6: 14 consecutive points alternating up/down (cycling)
        - Rule 7: 15 consecutive points within 1σ (stratification)

        Args:
            measurement_def: The MeasurementDefinition
            base_values: List of values to potentially modify
            progress: Progress through historical data (0-1) for drift simulation

        Returns:
            Modified list of values with violations injected
        """
        if not base_values or len(base_values) < 20:
            return base_values

        values = list(base_values)
        nominal = float(measurement_def.nominal) if measurement_def.nominal else 0
        tolerance = float(measurement_def.upper_tol or 1)
        sigma = tolerance / 3  # Approximate sigma from tolerance

        # Randomly inject violations based on progress
        # More violations early in history, process stabilizes over time

        violation_probability = 0.15 * (1 - progress * 0.7)  # 15% down to 4.5%

        if random.random() < violation_probability:
            violation_type = random.choice([1, 2, 3, 4, 5, 6, 7])
            start_idx = random.randint(0, max(0, len(values) - 20))

            if violation_type == 1:
                # Rule 1: Single point beyond 3σ
                idx = start_idx
                direction = random.choice([-1, 1])
                values[idx] = nominal + direction * sigma * 3.5

            elif violation_type == 2:
                # Rule 2: 2 of 3 consecutive points beyond 2σ
                direction = random.choice([-1, 1])
                indices = [start_idx, start_idx + 2] if start_idx + 2 < len(values) else [start_idx]
                for idx in indices:
                    if idx < len(values):
                        values[idx] = nominal + direction * sigma * random.uniform(2.1, 2.8)

            elif violation_type == 3:
                # Rule 3: 4 of 5 consecutive points beyond 1σ
                direction = random.choice([-1, 1])
                indices = [start_idx + i for i in [0, 1, 2, 4] if start_idx + i < len(values)]
                for idx in indices:
                    values[idx] = nominal + direction * sigma * random.uniform(1.2, 1.8)

            elif violation_type == 4:
                # Rule 4: 8 consecutive points on same side of center
                direction = random.choice([-1, 1])
                for i in range(8):
                    idx = start_idx + i
                    if idx < len(values):
                        values[idx] = nominal + direction * sigma * random.uniform(0.1, 0.8)

            elif violation_type == 5:
                # Rule 5: 6 consecutive points increasing or decreasing
                direction = random.choice([-1, 1])
                for i in range(6):
                    idx = start_idx + i
                    if idx < len(values):
                        values[idx] = nominal + direction * sigma * (0.2 + 0.2 * i)

            elif violation_type == 6:
                # Rule 6: 14 consecutive points alternating up/down
                for i in range(min(14, len(values) - start_idx)):
                    idx = start_idx + i
                    direction = 1 if i % 2 == 0 else -1
                    values[idx] = nominal + direction * sigma * random.uniform(0.5, 1.0)

            elif violation_type == 7:
                # Rule 7: 15 consecutive points within 1σ (stratification)
                for i in range(min(15, len(values) - start_idx)):
                    idx = start_idx + i
                    values[idx] = nominal + sigma * random.uniform(-0.3, 0.3)

        # Add process drift simulation
        # Mean shifts 0.5σ gradually around day 40-60, then corrects
        drift_start = 0.33  # 33% through history
        drift_end = 0.50  # 50% through history
        correction_end = 0.60  # 60% through history

        if drift_start <= progress < drift_end:
            drift_progress = (progress - drift_start) / (drift_end - drift_start)
            drift_amount = 0.5 * sigma * drift_progress
            values = [v + drift_amount for v in values]
        elif drift_end <= progress < correction_end:
            correction_progress = (progress - drift_end) / (correction_end - drift_end)
            drift_amount = 0.5 * sigma * (1 - correction_progress)
            values = [v + drift_amount for v in values]

        return values

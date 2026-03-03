"""
CAPA seed data: Corrective/Preventive Actions, RCA, tasks, verification.
"""

import random
from collections import Counter
from datetime import timedelta
from django.utils import timezone

from Tracker.models import (
    CAPA, CapaTasks, RcaRecord, FiveWhys, Fishbone, CapaVerification,
    QualityReports, Equipments,
)
from .base import BaseSeeder


class CapaSeeder(BaseSeeder):
    """
    Seeds CAPA-related data.

    Creates:
    - CAPAs from quality failures
    - CAPA tasks (containment, corrective, preventive)
    - Root Cause Analysis (5-Whys, Fishbone) linked to actual failure patterns
    - Verification records
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manufacturing_seeder = None  # Set by orchestrator for equipment access

    def seed(self, users):
        """Create CAPAs from quality failures."""
        config = self.config
        failed_reports = QualityReports.objects.filter(
            tenant=self.tenant,
            status='FAIL'
        )[:config.get('orders', 10)]

        if not failed_reports.exists():
            self.log("  No failed quality reports to create CAPAs from")
            return

        capa_count = 0
        severities = ['CRITICAL', 'MAJOR', 'MINOR']
        severity_weights = [0.1, 0.4, 0.5]
        statuses = ['OPEN', 'IN_PROGRESS', 'PENDING_VERIFICATION', 'CLOSED']
        status_weights = [0.2, 0.3, 0.2, 0.3]

        for qr in failed_reports:
            if not qr.part:
                continue

            severity = random.choices(severities, weights=severity_weights)[0]
            status = random.choices(statuses, weights=status_weights)[0]

            capa = CAPA.objects.create(
                tenant=self.tenant,
                capa_type='CORRECTIVE',
                severity=severity,
                status=status,
                problem_statement=f"Quality failure on {qr.part.ERP_id} - {qr.step.name if qr.step else 'Unknown step'}. "
                                 f"CAPA initiated due to quality failure during {qr.step.name if qr.step else 'inspection'}. "
                                 f"Part {qr.part.ERP_id} failed quality check.",
                immediate_action=f"Quarantine affected part {qr.part.ERP_id} pending investigation.",
                part=qr.part,
                step=qr.step,
                work_order=qr.part.work_order,
                initiated_by=self.get_weighted_qa_staff(users),
                initiated_date=timezone.now().date(),
                assigned_to=random.choice(users['managers']) if users.get('managers') else self.get_weighted_employee(users),
                due_date=timezone.now().date() + timedelta(days=random.randint(14, 60)),
            )
            capa.quality_reports.add(qr)

            # Create tasks
            self._create_tasks(capa, users, status)

            # Create RCA for in-progress or closed CAPAs
            if status in ['IN_PROGRESS', 'PENDING_VERIFICATION', 'CLOSED']:
                self._create_rca(capa, users)

            # Create verification for closed CAPAs
            if status == 'CLOSED':
                self._create_verification(capa, users)

            capa_count += 1

        self.log(f"Created {capa_count} CAPAs with tasks and RCA")

    def _create_tasks(self, capa, users, capa_status):
        """Create realistic CAPA tasks."""
        task_templates = [
            ('CONTAINMENT', 'Containment Action', 'Isolate affected parts and prevent further impact'),
            ('CORRECTIVE', 'Corrective Action', 'Implement fix to address root cause'),
            ('PREVENTIVE', 'Preventive Action', 'Implement controls to prevent recurrence'),
        ]

        for task_type, title, description in task_templates:
            # Task status based on CAPA status
            if capa_status == 'OPEN':
                task_status = 'NOT_STARTED'
            elif capa_status == 'IN_PROGRESS':
                task_status = random.choice(['NOT_STARTED', 'IN_PROGRESS'])
            elif capa_status == 'PENDING_VERIFICATION':
                task_status = random.choice(['IN_PROGRESS', 'COMPLETED'])
            else:  # CLOSED
                task_status = 'COMPLETED'

            assignee = self.get_weighted_employee(users)

            CapaTasks.objects.create(
                tenant=self.tenant,
                capa=capa,
                task_type=task_type,
                description=f"{title} - {description} for {capa.capa_number}",
                assigned_to=assignee,
                status=task_status,
                due_date=capa.due_date - timedelta(days=random.randint(1, 7)) if capa.due_date else None,
                completed_date=timezone.now().date() if task_status == 'COMPLETED' else None,
                completed_by=assignee if task_status == 'COMPLETED' else None,
            )

    def _create_rca(self, capa, users):
        """Create Root Cause Analysis record with 5-Whys or Fishbone linked to actual failures."""
        qa_user = self.get_weighted_qa_staff(users)
        is_verified = capa.status in ['PENDING_VERIFICATION', 'CLOSED']

        # Analyze actual failure patterns from quality reports
        failure_analysis = self._analyze_failure_patterns(capa)

        rca_method = random.choice(['FIVE_WHYS', 'FISHBONE'])

        # Generate root cause summary based on analysis
        root_cause_summary = self._generate_root_cause_summary(failure_analysis, rca_method)

        rca = RcaRecord.objects.create(
            tenant=self.tenant,
            capa=capa,
            rca_method=rca_method,
            problem_description=f"Quality failure investigation for {capa.capa_number}: {failure_analysis['problem_description']}",
            conducted_by=qa_user,
            conducted_date=timezone.now().date(),
            root_cause_summary=root_cause_summary,
            root_cause_verification_status='VERIFIED' if is_verified else 'UNVERIFIED',
            root_cause_verified_at=timezone.now() if is_verified else None,
            root_cause_verified_by=qa_user if is_verified else None,
        )
        rca.quality_reports.set(capa.quality_reports.all())

        if rca_method == 'FIVE_WHYS':
            self._create_realistic_five_whys(rca, failure_analysis)
        elif rca_method == 'FISHBONE':
            self._create_realistic_fishbone(rca, failure_analysis)

    def _analyze_failure_patterns(self, capa):
        """Analyze actual failure patterns from quality reports linked to this CAPA."""
        analysis = {
            'problem_description': '',
            'most_problematic_equipment': None,
            'equipment_name': 'Unknown equipment',
            'most_common_operator': None,
            'operator_name': 'Unknown operator',
            'step_name': 'inspection',
            'failure_count': 0,
            'error_types': [],
            'is_equipment_related': False,
            'is_operator_related': False,
            'is_process_related': False,
        }

        quality_reports = capa.quality_reports.all()
        if not quality_reports.exists():
            analysis['problem_description'] = f"Quality failure at {capa.step.name if capa.step else 'unknown step'}"
            return analysis

        # Count equipment involved in failures
        equipment_failures = Counter()
        operator_failures = Counter()
        error_descriptions = []

        for qr in quality_reports:
            if qr.machine:
                equipment_failures[qr.machine] += 1
            if qr.detected_by:
                operator_failures[qr.detected_by] += 1
            for error in qr.errors.all():
                error_descriptions.append(error.error_name)

        # Find most problematic equipment
        if equipment_failures:
            most_problematic = equipment_failures.most_common(1)[0]
            analysis['most_problematic_equipment'] = most_problematic[0]
            analysis['equipment_name'] = most_problematic[0].name
            analysis['failure_count'] = most_problematic[1]

            # Check if this equipment is in the problematic set
            if self.manufacturing_seeder and hasattr(self.manufacturing_seeder, 'problematic_equipment'):
                if most_problematic[0] in self.manufacturing_seeder.problematic_equipment:
                    analysis['is_equipment_related'] = True

        # Find most common operator on failures
        if operator_failures:
            most_common_op = operator_failures.most_common(1)[0]
            analysis['most_common_operator'] = most_common_op[0]
            analysis['operator_name'] = f"{most_common_op[0].first_name} {most_common_op[0].last_name}"

        # Determine root cause category
        if analysis['is_equipment_related']:
            analysis['problem_description'] = f"Multiple failures detected on {analysis['equipment_name']}"
        elif len(error_descriptions) > 3:
            analysis['problem_description'] = f"Recurring quality issues: {', '.join(set(error_descriptions)[:3])}"
            analysis['is_process_related'] = True
        else:
            analysis['problem_description'] = f"Quality failure at {capa.step.name if capa.step else 'inspection'}"

        analysis['step_name'] = capa.step.name if capa.step else 'inspection'
        analysis['error_types'] = list(set(error_descriptions))

        return analysis

    def _generate_root_cause_summary(self, analysis, rca_method):
        """Generate root cause summary based on failure analysis."""
        if analysis['is_equipment_related']:
            return f"Equipment {analysis['equipment_name']} requires maintenance/calibration - {analysis['failure_count']} failures traced to this unit"
        elif analysis['is_process_related']:
            return f"Process instability at {analysis['step_name']} step - standardization needed"
        else:
            return f"Root cause identified: variation in {analysis['step_name']} process requiring corrective action"

    def _create_realistic_five_whys(self, rca, analysis):
        """Create 5-Whys RCA based on actual failure analysis."""
        if analysis['is_equipment_related']:
            # Equipment-related root cause
            FiveWhys.objects.create(
                tenant=self.tenant,
                rca_record=rca,
                why_1_question=f"Why did parts fail at {analysis['step_name']}?",
                why_1_answer=f"Measurements exceeded tolerance limits when tested on {analysis['equipment_name']}",
                why_2_question=f"Why did {analysis['equipment_name']} produce out-of-tolerance results?",
                why_2_answer=f"{analysis['equipment_name']} calibration had drifted outside acceptable range",
                why_3_question=f"Why had calibration drifted on {analysis['equipment_name']}?",
                why_3_answer="Preventive maintenance interval was exceeded due to high production demand",
                why_4_question="Why was the maintenance interval exceeded?",
                why_4_answer="No automated alerts for calibration due dates; relies on manual tracking",
                why_5_question="Why is calibration tracking manual?",
                why_5_answer="Calibration management system not integrated with production scheduling",
                identified_root_cause=f"Equipment {analysis['equipment_name']} requires shorter calibration interval and automated scheduling",
            )
        elif analysis['is_process_related']:
            # Process-related root cause
            error_list = ', '.join(analysis['error_types'][:2]) if analysis['error_types'] else 'quality defects'
            FiveWhys.objects.create(
                tenant=self.tenant,
                rca_record=rca,
                why_1_question=f"Why are we seeing {error_list}?",
                why_1_answer=f"Process parameters at {analysis['step_name']} step are inconsistent",
                why_2_question="Why are process parameters inconsistent?",
                why_2_answer="Work instructions lack specific parameter ranges for different part variations",
                why_3_question="Why don't work instructions include these parameters?",
                why_3_answer="Original process validation didn't capture all sources of variation",
                why_4_question="Why wasn't variation captured during validation?",
                why_4_answer="Limited sample size during initial process development",
                why_5_question="Why was sample size limited?",
                why_5_answer="Time constraints during product launch phase",
                identified_root_cause="Work instructions require update with specific parameters; revalidation needed with larger sample",
            )
        else:
            # Generic root cause
            FiveWhys.objects.create(
                tenant=self.tenant,
                rca_record=rca,
                why_1_question=f"Why did the part fail {analysis['step_name']}?",
                why_1_answer="Measurement exceeded tolerance limits",
                why_2_question="Why did the measurement exceed limits?",
                why_2_answer="Incoming component variation was higher than expected",
                why_3_question="Why was incoming variation high?",
                why_3_answer="Supplier process capability not verified recently",
                why_4_question="Why wasn't supplier capability verified?",
                why_4_answer="No scheduled supplier audits in quality plan",
                why_5_question="Why aren't supplier audits scheduled?",
                why_5_answer="Quality plan focused on internal processes only",
                identified_root_cause="Implement supplier quality management with periodic capability studies",
            )

    def _create_realistic_fishbone(self, rca, analysis):
        """Create Fishbone (6M) diagram based on actual failure analysis."""
        # Customize causes based on analysis
        if analysis['is_equipment_related']:
            machine_causes = [
                f"{analysis['equipment_name']} calibration drift",
                f"Worn components in {analysis['equipment_name']}",
                "Sensor degradation"
            ]
            primary_cause = f"Equipment issue: {analysis['equipment_name']} requires maintenance"
        else:
            machine_causes = ["Calibration drift", "Worn tooling", "Fixture wear"]
            primary_cause = "Multiple contributing factors identified - see 6M analysis"

        if analysis['most_common_operator']:
            man_causes = [
                f"Training gap for {analysis['operator_name']}",
                "Shift handover communication",
                "Procedure interpretation"
            ]
        else:
            man_causes = ["Operator training gap", "Fatigue during shift", "Procedure compliance"]

        Fishbone.objects.create(
            tenant=self.tenant,
            rca_record=rca,
            problem_statement=f"Quality failure: {analysis['problem_description']}",
            man_causes=man_causes,
            machine_causes=machine_causes,
            material_causes=["Incoming material variance", "Supplier batch variation", "Material storage conditions"],
            method_causes=[f"Work instruction for {analysis['step_name']}", "Process parameter drift", "Inspection sampling"],
            measurement_causes=["Gauge R&R", "Measurement technique", "Environmental factors"],
            environment_causes=["Temperature fluctuation", "Humidity", "Contamination"],
            identified_root_cause=primary_cause,
        )

    def _create_verification(self, capa, users):
        """Create CAPA verification record."""
        qa_user = self.get_weighted_qa_staff(users)

        CapaVerification.objects.create(
            tenant=self.tenant,
            capa=capa,
            verification_method="Review of production data and quality reports post-implementation",
            verification_criteria="Zero recurrence of defect type for 30 days and 200+ parts",
            verified_by=qa_user,
            verification_date=timezone.now().date(),
            effectiveness_result='CONFIRMED',
            effectiveness_decided_at=timezone.now(),
            verification_notes="Verified corrective actions effective. No recurrence observed after implementation.",
        )

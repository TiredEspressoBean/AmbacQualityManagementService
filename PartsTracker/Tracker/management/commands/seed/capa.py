"""
CAPA seed data: Corrective/Preventive Actions, RCA, tasks, verification.
"""

import random
from datetime import timedelta
from django.utils import timezone

from Tracker.models import (
    CAPA, CapaTasks, RcaRecord, FiveWhys, Fishbone, CapaVerification,
    QualityReports,
)
from .base import BaseSeeder


class CapaSeeder(BaseSeeder):
    """
    Seeds CAPA-related data.

    Creates:
    - CAPAs from quality failures
    - CAPA tasks (containment, corrective, preventive)
    - Root Cause Analysis (5-Whys, Fishbone)
    - Verification records
    """

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
        """Create Root Cause Analysis record with 5-Whys or Fishbone."""
        qa_user = self.get_weighted_qa_staff(users)
        is_verified = capa.status in ['PENDING_VERIFICATION', 'CLOSED']

        rca = RcaRecord.objects.create(
            tenant=self.tenant,
            capa=capa,
            rca_method=random.choice(['FIVE_WHYS', 'FISHBONE']),
            problem_description=f"Quality failure investigation for {capa.capa_number}",
            conducted_by=qa_user,
            conducted_date=timezone.now().date(),
            root_cause_summary=f"Root cause identified for {capa.capa_number}",
            root_cause_verification_status='VERIFIED' if is_verified else 'UNVERIFIED',
            root_cause_verified_at=timezone.now() if is_verified else None,
            root_cause_verified_by=qa_user if is_verified else None,
        )
        rca.quality_reports.set(capa.quality_reports.all())

        if rca.rca_method == 'FIVE_WHYS':
            FiveWhys.objects.create(
                tenant=self.tenant,
                rca_record=rca,
                why_1_question="Why did the part fail inspection?",
                why_1_answer="Measurement exceeded tolerance limits",
                why_2_question="Why did the measurement exceed limits?",
                why_2_answer="Equipment calibration had drifted",
                why_3_question="Why had calibration drifted?",
                why_3_answer="Preventive maintenance was overdue",
                why_4_question="Why was maintenance overdue?",
                why_4_answer="Maintenance schedule not followed",
                why_5_question="Why wasn't the schedule followed?",
                why_5_answer="No automated reminder system in place",
                identified_root_cause="Lack of automated calibration tracking and reminders",
            )
        elif rca.rca_method == 'FISHBONE':
            Fishbone.objects.create(
                tenant=self.tenant,
                rca_record=rca,
                problem_statement=f"Quality failure on {capa.capa_number}",
                man_causes=["Operator training gap", "Fatigue during shift"],
                machine_causes=["Calibration drift", "Worn tooling"],
                material_causes=["Incoming material variance", "Supplier batch issue"],
                method_causes=["Outdated work instruction", "Process parameter drift"],
                measurement_causes=["Gauge repeatability", "Environmental factors"],
                environment_causes=["Temperature fluctuation", "Humidity out of spec"],
                identified_root_cause="Multiple contributing factors identified - see 6M analysis",
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

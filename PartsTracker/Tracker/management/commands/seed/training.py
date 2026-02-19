"""
Training seed data: Training types, requirements, and records.
"""

import random
from datetime import timedelta
from django.utils import timezone

from Tracker.models import (
    TrainingType, TrainingRecord, TrainingRequirement,
    Steps, Processes, EquipmentType,
)
from .base import BaseSeeder


class TrainingSeeder(BaseSeeder):
    """
    Seeds training-related data.

    Creates:
    - Training types (Blueprint Reading, CMM Operation, etc.)
    - Training requirements linked to steps/processes/equipment
    - Training records for employees with realistic dates
    """

    # Training type configurations
    TRAINING_TYPES = [
        # (name, description, validity_days)
        ('Blueprint Reading', 'Ability to read and interpret engineering drawings and GD&T', 365 * 2),
        ('CMM Operation', 'Coordinate Measuring Machine programming and operation', 365),
        ('Soldering IPC-A-610', 'IPC-A-610 certified soldering and inspection', 365),
        ('ESD Handling', 'Electrostatic discharge awareness and prevention', 365),
        ('Torque Wrench Certification', 'Proper use of calibrated torque wrenches', 365),
        ('Flow Bench Operation', 'Fuel injector flow testing equipment operation', 365),
        ('Cleaning System Operation', 'Ultrasonic and spray washer operation', 365 * 2),
        ('Visual Inspection', 'Surface defect detection and classification', 365),
        ('Leak Testing', 'Pressure and vacuum leak detection methods', 365),
        ('Safety Orientation', 'General workplace safety and emergency procedures', 365),
        ('Quality System Awareness', 'ISO 9001 / IATF 16949 quality management basics', 365 * 2),
        ('OSHA Forklift', 'Powered industrial truck operation', 365 * 3),
    ]

    def seed(self, users, steps=None, processes=None, equipment_types=None):
        """Run the full training seeding process."""
        training_types = self.create_training_types()
        self.create_training_requirements(training_types, steps, processes, equipment_types)
        self.create_training_records(training_types, users)

    # =========================================================================
    # Training Types
    # =========================================================================

    def create_training_types(self):
        """Create training type definitions."""
        training_types = []

        for name, description, validity_days in self.TRAINING_TYPES:
            training_type, created = TrainingType.objects.get_or_create(
                tenant=self.tenant,
                name=name,
                defaults={
                    'description': description,
                    'validity_period_days': validity_days,
                }
            )
            training_types.append(training_type)

        self.log(f"Created/verified {len(training_types)} training types")
        return training_types

    # =========================================================================
    # Training Requirements
    # =========================================================================

    def create_training_requirements(self, training_types, steps, processes, equipment_types):
        """Create training requirements linking types to work activities."""
        if not training_types:
            return

        requirements_created = 0

        # Map training types by name for easier lookup
        type_map = {t.name: t for t in training_types}

        # Step-level requirements
        if steps:
            requirements_created += self._create_step_requirements(type_map, steps)

        # Equipment type requirements
        if equipment_types:
            requirements_created += self._create_equipment_requirements(type_map, equipment_types)

        self.log(f"Created {requirements_created} training requirements")

    def _create_step_requirements(self, type_map, steps):
        """Create training requirements for specific steps."""
        created = 0
        step_training_map = {
            'inspection': ['Visual Inspection', 'Blueprint Reading'],
            'testing': ['Leak Testing', 'Flow Bench Operation'],
            'measurement': ['CMM Operation', 'Blueprint Reading'],
            'cleaning': ['Cleaning System Operation', 'Safety Orientation'],
            'assembly': ['Torque Wrench Certification', 'Blueprint Reading'],
            'soldering': ['Soldering IPC-A-610', 'ESD Handling'],
            'flow': ['Flow Bench Operation', 'Leak Testing'],
        }

        for step in steps:
            step_name_lower = step.name.lower()

            # Find matching training requirements
            for keyword, trainings in step_training_map.items():
                if keyword in step_name_lower:
                    for training_name in trainings:
                        if training_name in type_map:
                            _, was_created = TrainingRequirement.objects.get_or_create(
                                tenant=self.tenant,
                                training_type=type_map[training_name],
                                step=step,
                                defaults={
                                    'notes': f"Required for {step.name} operations"
                                }
                            )
                            if was_created:
                                created += 1
                    break  # Only match first keyword

        return created

    def _create_equipment_requirements(self, type_map, equipment_types):
        """Create training requirements for equipment types."""
        created = 0
        equipment_training_map = {
            'cmm': ['CMM Operation', 'Blueprint Reading'],
            'coordinate': ['CMM Operation', 'Blueprint Reading'],
            'flow bench': ['Flow Bench Operation'],
            'flow test': ['Flow Bench Operation'],
            'torque': ['Torque Wrench Certification'],
            'ultrasonic': ['Cleaning System Operation'],
            'washer': ['Cleaning System Operation'],
            'forklift': ['OSHA Forklift'],
            'soldering': ['Soldering IPC-A-610', 'ESD Handling'],
        }

        for eq_type in equipment_types:
            eq_name_lower = eq_type.name.lower()

            for keyword, trainings in equipment_training_map.items():
                if keyword in eq_name_lower:
                    for training_name in trainings:
                        if training_name in type_map:
                            _, was_created = TrainingRequirement.objects.get_or_create(
                                tenant=self.tenant,
                                training_type=type_map[training_name],
                                equipment_type=eq_type,
                                defaults={
                                    'notes': f"Required to operate {eq_type.name}"
                                }
                            )
                            if was_created:
                                created += 1
                    break

        return created

    # =========================================================================
    # Training Records
    # =========================================================================

    def create_training_records(self, training_types, users):
        """Create training records for employees."""
        employees = users.get('employees', [])
        if not employees or not training_types:
            return

        # All employees should have Safety Orientation and Quality System Awareness
        mandatory_trainings = [
            t for t in training_types
            if t.name in ['Safety Orientation', 'Quality System Awareness']
        ]

        # Skill-based trainings assigned randomly
        skill_trainings = [
            t for t in training_types
            if t not in mandatory_trainings
        ]

        records_created = 0
        trainers = users.get('managers', employees[:2])

        for employee in employees:
            # All employees get mandatory training
            for training_type in mandatory_trainings:
                records_created += self._create_training_record(
                    employee, training_type, trainers, mandatory=True
                )

            # Assign 2-5 random skill trainings per employee
            num_skills = random.randint(2, min(5, len(skill_trainings)))
            employee_skills = random.sample(skill_trainings, num_skills)

            for training_type in employee_skills:
                records_created += self._create_training_record(
                    employee, training_type, trainers, mandatory=False
                )

        # QA staff get additional specialized training
        qa_staff = users.get('qa_staff', [])
        qa_trainings = [
            t for t in training_types
            if t.name in ['Visual Inspection', 'CMM Operation', 'Blueprint Reading']
        ]

        for qa_user in qa_staff:
            for training_type in qa_trainings:
                records_created += self._create_training_record(
                    qa_user, training_type, trainers, mandatory=True
                )

        self.log(f"Created {records_created} training records")

    def _create_training_record(self, employee, training_type, trainers, mandatory=False):
        """Create a single training record with realistic dates."""
        # Check if record already exists
        existing = TrainingRecord.objects.filter(
            tenant=self.tenant,
            user=employee,
            training_type=training_type
        ).exists()

        if existing:
            return 0

        # Completed date: random within past 2 years
        days_ago = random.randint(30, 730)
        completed_date = timezone.now().date() - timedelta(days=days_ago)

        # Occasional expired training (10% chance for non-mandatory)
        if not mandatory and random.random() < 0.10:
            # Make it expired
            if training_type.validity_period_days:
                days_ago = training_type.validity_period_days + random.randint(30, 180)
                completed_date = timezone.now().date() - timedelta(days=days_ago)

        # Occasional expiring soon (15% chance)
        elif random.random() < 0.15:
            if training_type.validity_period_days:
                # Completed such that it expires within 30 days
                days_until_expire = random.randint(5, 25)
                days_ago = training_type.validity_period_days - days_until_expire
                completed_date = timezone.now().date() - timedelta(days=max(0, days_ago))

        trainer = random.choice(trainers) if trainers else None

        TrainingRecord.objects.create(
            tenant=self.tenant,
            user=employee,
            training_type=training_type,
            completed_date=completed_date,
            trainer=trainer,
            notes=f"{'Initial' if mandatory else 'Skill development'} training completed"
        )

        return 1

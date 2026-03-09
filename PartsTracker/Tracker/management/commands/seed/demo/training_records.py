"""
Demo training records seeder with preset certifications.

Creates training records matching DEMO_DATA_SYSTEM.md:
- Mike Rodriguez: NOZ-CERT expiring in 7 days
- Dave Wilson: FLOW-CERT expired 15 days ago (blocks work)
- Other demo users: Current certifications
"""

from datetime import timedelta
from django.utils import timezone

from Tracker.models import (
    TrainingType, TrainingRecord, TrainingRequirement,
    Steps, EquipmentType, User,
)

from ..base import BaseSeeder


# Demo training requirements - link training types to steps/equipment
DEMO_TRAINING_REQUIREMENTS = [
    # Step-based requirements
    {'training_key': 'FLOW-CERT', 'step_name': 'Flow Testing', 'notes': 'Required per WI-1003'},
    {'training_key': 'NOZ-CERT', 'step_name': 'Nozzle Inspection', 'notes': 'Required per WI-1002'},
    {'training_key': 'ASSEMBLY-CERT', 'step_name': 'Assembly', 'notes': 'Required per WI-1001'},
    {'training_key': 'TORQUE-CERT', 'step_name': 'Assembly', 'notes': 'Torque wrench operation required'},
    # Equipment-based requirements
    {'training_key': 'FLOW-CERT', 'equipment_type_name': 'Flow Bench', 'notes': 'Required for flow test equipment'},
    {'training_key': 'TORQUE-CERT', 'equipment_type_name': 'Torque Tool', 'notes': 'Required for torque wrenches'},
]


# Demo training types - keyed by name since TrainingType has no 'code' field
DEMO_TRAINING_TYPES = [
    {'key': 'NOZ-CERT', 'name': 'Nozzle Inspection Certification', 'validity_days': 365},
    {'key': 'FLOW-CERT', 'name': 'Flow Testing Certification', 'validity_days': 365},
    {'key': 'ASSEMBLY-CERT', 'name': 'Assembly Certification', 'validity_days': 365},
    {'key': 'SAFETY-CERT', 'name': 'Safety Training', 'validity_days': 365},
    {'key': 'TORQUE-CERT', 'name': 'Torque Wrench Certification', 'validity_days': 180},
]

# Demo training records with specific expiry scenarios
DEMO_TRAINING_RECORDS = [
    # Mike Rodriguez - expiring soon
    {
        'user': 'mike.ops@demo.ambac.com',
        'training_type': 'NOZ-CERT',
        'expires_days': 7,  # Expiring in 7 days
        'completed_days_ago': 358,
    },
    {
        'user': 'mike.ops@demo.ambac.com',
        'training_type': 'FLOW-CERT',
        'expires_days': 180,  # Current
        'completed_days_ago': 185,
    },
    {
        'user': 'mike.ops@demo.ambac.com',
        'training_type': 'ASSEMBLY-CERT',
        'expires_days': 200,  # Current
        'completed_days_ago': 165,
    },
    {
        'user': 'mike.ops@demo.ambac.com',
        'training_type': 'SAFETY-CERT',
        'expires_days': 250,  # Current
        'completed_days_ago': 115,
    },
    # Dave Wilson - EXPIRED (blocks work)
    {
        'user': 'dave.wilson@demo.ambac.com',
        'training_type': 'FLOW-CERT',
        'expires_days': -15,  # EXPIRED 15 days ago
        'completed_days_ago': 380,  # Over a year ago
    },
    {
        'user': 'dave.wilson@demo.ambac.com',
        'training_type': 'NOZ-CERT',
        'expires_days': 100,  # Current
        'completed_days_ago': 265,
    },
    {
        'user': 'dave.wilson@demo.ambac.com',
        'training_type': 'SAFETY-CERT',
        'expires_days': 200,  # Current
        'completed_days_ago': 165,
    },
    # Sarah Chen (QA Inspector) - all current
    {
        'user': 'sarah.qa@demo.ambac.com',
        'training_type': 'NOZ-CERT',
        'expires_days': 300,
        'completed_days_ago': 65,
    },
    {
        'user': 'sarah.qa@demo.ambac.com',
        'training_type': 'FLOW-CERT',
        'expires_days': 280,
        'completed_days_ago': 85,
    },
    # Jennifer Walsh (Production Manager) - all current
    {
        'user': 'jennifer.mgr@demo.ambac.com',
        'training_type': 'SAFETY-CERT',
        'expires_days': 320,
        'completed_days_ago': 45,
    },
]


class DemoTrainingRecordsSeeder(BaseSeeder):
    """
    Creates preset training records with expiry scenarios.

    All data is deterministic - same result every time.
    """

    def __init__(self, stdout, style, tenant, scale='small'):
        super().__init__(stdout, style, scale=scale)
        self.tenant = tenant
        self.today = timezone.now().date()

    def seed(self, users):
        """
        Create all demo training data.

        Args:
            users: dict with user lists including by_email lookup

        Returns:
            dict with created training types and records
        """
        self.log("Creating demo training records...")

        result = {
            'training_types': [],
            'training_records': [],
            'training_requirements': [],
        }

        # Create training types
        result['training_types'] = self._create_training_types()

        # Create training requirements (link types to steps/equipment)
        result['training_requirements'] = self._create_training_requirements()

        # Get user lookup
        user_map = users.get('by_email', {})

        # Get training type lookup (by key, which we store in a dict during creation)
        type_map = self._training_type_keys

        # Create training records
        for record_data in DEMO_TRAINING_RECORDS:
            user = user_map.get(record_data['user'])
            training_type = type_map.get(record_data['training_type'])

            if user and training_type:
                record = self._create_training_record(record_data, user, training_type)
                result['training_records'].append(record)

        # Count status distribution
        expired = sum(1 for r in result['training_records'] if r.expires_date < self.today)
        expiring = sum(1 for r in result['training_records']
                      if self.today <= r.expires_date <= self.today + timedelta(days=30))
        current = len(result['training_records']) - expired - expiring

        self.log(f"  Created {len(result['training_types'])} training types")
        self.log(f"  Created {len(result['training_requirements'])} training requirements")
        self.log(f"  Created {len(result['training_records'])} training records")
        self.log(f"    Current: {current}, Expiring soon: {expiring}, Expired: {expired}")

        return result

    def _create_training_requirements(self):
        """Create training requirements linking types to steps/equipment."""
        requirements = []

        # Get lookups
        steps = {s.name: s for s in Steps.objects.filter(tenant=self.tenant)}
        eq_types = {e.name: e for e in EquipmentType.objects.filter(tenant=self.tenant)}

        for req_data in DEMO_TRAINING_REQUIREMENTS:
            training_type = self._training_type_keys.get(req_data['training_key'])
            if not training_type:
                continue

            # Determine target (step or equipment_type)
            step = steps.get(req_data.get('step_name'))
            eq_type = eq_types.get(req_data.get('equipment_type_name'))

            if not step and not eq_type:
                continue

            req, _ = TrainingRequirement.objects.update_or_create(
                tenant=self.tenant,
                training_type=training_type,
                step=step,
                equipment_type=eq_type,
                defaults={
                    'notes': req_data.get('notes', ''),
                }
            )
            requirements.append(req)

        return requirements

    def _create_training_types(self):
        """Create training types."""
        training_types = []
        self._training_type_keys = {}  # Maps key -> TrainingType

        for tt_data in DEMO_TRAINING_TYPES:
            tt, _ = TrainingType.objects.update_or_create(
                tenant=self.tenant,
                name=tt_data['name'],
                defaults={
                    'description': f"Training certification for {tt_data['name'].lower()}",
                    'validity_period_days': tt_data['validity_days'],
                }
            )
            training_types.append(tt)
            self._training_type_keys[tt_data['key']] = tt

        return training_types

    def _create_training_record(self, record_data, user, training_type):
        """Create a training record."""
        completed_date = self.today - timedelta(days=record_data['completed_days_ago'])
        expires_date = self.today + timedelta(days=record_data['expires_days'])

        record, _ = TrainingRecord.objects.update_or_create(
            tenant=self.tenant,
            user=user,
            training_type=training_type,
            defaults={
                'completed_date': completed_date,
                'expires_date': expires_date,
                'notes': 'Demo training record',
            }
        )

        return record

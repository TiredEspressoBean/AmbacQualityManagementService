"""
Demo training records seeder with preset certifications, job roles, and levels.

Creates a deterministic dataset that exercises the whole competency matrix:
- Training types (5 certs)
- Job roles with required-competency profiles (min levels)
- Users assigned to roles
- Training records at varied levels (L1-L4) producing:
    * meets-role vs role gaps (below required level, and expired = level 0)
    * a trainee (L1) and experts (L4)
    * expiring-soon (Mike's NOZ in 7 days) and expired (Dave's FLOW)
    * a single-point-of-failure skill (only one Torque-qualified operator)
"""

from datetime import timedelta
from django.utils import timezone

from Tracker.models import (
    TrainingType, TrainingRecord, TrainingRequirement, JobRole,
    Steps, EquipmentType, User,
)

from ..base import BaseSeeder


# Demo training types - keyed by name since TrainingType has no 'code' field
DEMO_TRAINING_TYPES = [
    {'key': 'NOZ-CERT', 'name': 'Nozzle Inspection Certification', 'validity_days': 365},
    {'key': 'FLOW-CERT', 'name': 'Flow Testing Certification', 'validity_days': 365},
    {'key': 'ASSEMBLY-CERT', 'name': 'Assembly Certification', 'validity_days': 365},
    {'key': 'SAFETY-CERT', 'name': 'Safety Training', 'validity_days': 365},
    {'key': 'TORQUE-CERT', 'name': 'Torque Wrench Certification', 'validity_days': 180},
]

# Operation/equipment-scoped requirements (authorization gate).
DEMO_TRAINING_REQUIREMENTS = [
    {'training_key': 'FLOW-CERT', 'step_name': 'Flow Testing', 'notes': 'Required per WI-1003'},
    {'training_key': 'NOZ-CERT', 'step_name': 'Nozzle Inspection', 'notes': 'Required per WI-1002'},
    {'training_key': 'ASSEMBLY-CERT', 'step_name': 'Assembly', 'notes': 'Required per WI-1001'},
    {'training_key': 'TORQUE-CERT', 'step_name': 'Assembly', 'notes': 'Torque wrench operation required'},
    {'training_key': 'FLOW-CERT', 'equipment_type_name': 'Flow Bench', 'notes': 'Required for flow test equipment'},
    {'training_key': 'TORQUE-CERT', 'equipment_type_name': 'Torque Tool', 'notes': 'Required for torque wrenches'},
]

# Job roles + their required-competency profiles: (training_key, min_level).
DEMO_JOB_ROLES = [
    {'key': 'ASSEMBLER', 'name': 'Assembler',
     'requirements': [('ASSEMBLY-CERT', 3), ('TORQUE-CERT', 3), ('SAFETY-CERT', 2)]},
    {'key': 'FLOW_TECH', 'name': 'Flow Test Technician',
     'requirements': [('FLOW-CERT', 3), ('SAFETY-CERT', 2)]},
    {'key': 'NOZ_INSPECTOR', 'name': 'Nozzle Inspector',
     'requirements': [('NOZ-CERT', 3), ('SAFETY-CERT', 2)]},
    {'key': 'QUALITY_ENG', 'name': 'Quality Engineer',
     'requirements': [('NOZ-CERT', 4), ('FLOW-CERT', 3), ('ASSEMBLY-CERT', 2), ('SAFETY-CERT', 2)]},
]

# User -> job role assignment (by email).
DEMO_USER_ROLES = {
    'mike.ops@demo.ambac.com': 'ASSEMBLER',
    'dave.wilson@demo.ambac.com': 'FLOW_TECH',
    'sarah.qa@demo.ambac.com': 'NOZ_INSPECTOR',
    'maria.qa@demo.ambac.com': 'QUALITY_ENG',
    'jennifer.mgr@demo.ambac.com': 'ASSEMBLER',
}

# Demo training records: level + expiry scenario per (user, cert).
DEMO_TRAINING_RECORDS = [
    # Mike Rodriguez (Assembler) — TORQUE below role req (gap), a trainee cert, NOZ expiring
    {'user': 'mike.ops@demo.ambac.com', 'training_type': 'ASSEMBLY-CERT', 'level': 3, 'expires_days': 200, 'completed_days_ago': 165},
    {'user': 'mike.ops@demo.ambac.com', 'training_type': 'TORQUE-CERT', 'level': 2, 'expires_days': 120, 'completed_days_ago': 60},
    {'user': 'mike.ops@demo.ambac.com', 'training_type': 'SAFETY-CERT', 'level': 3, 'expires_days': 250, 'completed_days_ago': 115},
    {'user': 'mike.ops@demo.ambac.com', 'training_type': 'FLOW-CERT', 'level': 3, 'expires_days': 180, 'completed_days_ago': 185},
    {'user': 'mike.ops@demo.ambac.com', 'training_type': 'NOZ-CERT', 'level': 1, 'expires_days': 7, 'completed_days_ago': 358},
    # Dave Wilson (Flow Test Technician) — FLOW expired => role gap
    {'user': 'dave.wilson@demo.ambac.com', 'training_type': 'FLOW-CERT', 'level': 3, 'expires_days': -15, 'completed_days_ago': 380},
    {'user': 'dave.wilson@demo.ambac.com', 'training_type': 'NOZ-CERT', 'level': 2, 'expires_days': 100, 'completed_days_ago': 265},
    {'user': 'dave.wilson@demo.ambac.com', 'training_type': 'SAFETY-CERT', 'level': 3, 'expires_days': 200, 'completed_days_ago': 165},
    # Sarah Chen (Nozzle Inspector) — meets role, expert on NOZ
    {'user': 'sarah.qa@demo.ambac.com', 'training_type': 'NOZ-CERT', 'level': 4, 'expires_days': 300, 'completed_days_ago': 65},
    {'user': 'sarah.qa@demo.ambac.com', 'training_type': 'FLOW-CERT', 'level': 3, 'expires_days': 280, 'completed_days_ago': 85},
    {'user': 'sarah.qa@demo.ambac.com', 'training_type': 'SAFETY-CERT', 'level': 2, 'expires_days': 320, 'completed_days_ago': 45},
    # Maria Santos (Quality Engineer) — NOZ below required L4 (gap)
    {'user': 'maria.qa@demo.ambac.com', 'training_type': 'NOZ-CERT', 'level': 3, 'expires_days': 260, 'completed_days_ago': 105},
    {'user': 'maria.qa@demo.ambac.com', 'training_type': 'FLOW-CERT', 'level': 3, 'expires_days': 240, 'completed_days_ago': 125},
    {'user': 'maria.qa@demo.ambac.com', 'training_type': 'ASSEMBLY-CERT', 'level': 2, 'expires_days': 300, 'completed_days_ago': 65},
    {'user': 'maria.qa@demo.ambac.com', 'training_type': 'SAFETY-CERT', 'level': 4, 'expires_days': 330, 'completed_days_ago': 35},
    # Jennifer Walsh (Assembler) — meets role, expert on Assembly; 2nd Torque-qualified? No (only L for coverage)
    {'user': 'jennifer.mgr@demo.ambac.com', 'training_type': 'ASSEMBLY-CERT', 'level': 4, 'expires_days': 300, 'completed_days_ago': 60},
    {'user': 'jennifer.mgr@demo.ambac.com', 'training_type': 'TORQUE-CERT', 'level': 3, 'expires_days': 120, 'completed_days_ago': 60},
    {'user': 'jennifer.mgr@demo.ambac.com', 'training_type': 'SAFETY-CERT', 'level': 3, 'expires_days': 320, 'completed_days_ago': 45},
    # Lisa Park (no role) — just safety
    {'user': 'lisa.docs@demo.ambac.com', 'training_type': 'SAFETY-CERT', 'level': 2, 'expires_days': 300, 'completed_days_ago': 65},
]


class DemoTrainingRecordsSeeder(BaseSeeder):
    """Creates the deterministic demo competency dataset (idempotent)."""

    def __init__(self, stdout, style, tenant, scale='small'):
        super().__init__(stdout, style, scale=scale)
        self.tenant = tenant
        self.today = timezone.now().date()

    def seed(self, users):
        """Create all demo training data. `users` is a dict with a 'by_email' map."""
        self.log("Creating demo training data (types, roles, records)...")

        result = {
            'training_types': [],
            'training_requirements': [],
            'job_roles': [],
            'training_records': [],
        }

        result['training_types'] = self._create_training_types()
        result['training_requirements'] = self._create_training_requirements()
        result['job_roles'] = self._create_job_roles()

        user_map = users.get('by_email', {})
        self._assign_user_roles(user_map)

        type_map = self._training_type_keys
        for record_data in DEMO_TRAINING_RECORDS:
            user = user_map.get(record_data['user'])
            training_type = type_map.get(record_data['training_type'])
            if user and training_type:
                result['training_records'].append(
                    self._create_training_record(record_data, user, training_type)
                )

        expired = sum(1 for r in result['training_records'] if r.expires_date and r.expires_date < self.today)
        expiring = sum(1 for r in result['training_records']
                       if r.expires_date and self.today <= r.expires_date <= self.today + timedelta(days=30))
        current = len(result['training_records']) - expired - expiring

        self.log(f"  Created {len(result['training_types'])} training types")
        self.log(f"  Created {len(result['job_roles'])} job roles")
        self.log(f"  Created {len(result['training_requirements'])} training requirements")
        self.log(f"  Created {len(result['training_records'])} training records")
        self.log(f"    Current: {current}, Expiring soon: {expiring}, Expired: {expired}")

        return result

    def _create_training_types(self):
        training_types = []
        self._training_type_keys = {}  # key -> TrainingType
        for tt_data in DEMO_TRAINING_TYPES:
            tt, _ = TrainingType.objects.update_or_create(
                tenant=self.tenant,
                name=tt_data['name'],
                defaults={
                    'description': f"Training certification for {tt_data['name'].lower()}",
                    'validity_period_days': tt_data['validity_days'],
                },
            )
            training_types.append(tt)
            self._training_type_keys[tt_data['key']] = tt
        return training_types

    def _create_training_requirements(self):
        """Operation/equipment-scoped requirements (authorization gate)."""
        requirements = []
        steps = {s.name: s for s in Steps.objects.filter(tenant=self.tenant)}
        eq_types = {e.name: e for e in EquipmentType.objects.filter(tenant=self.tenant)}

        for req_data in DEMO_TRAINING_REQUIREMENTS:
            training_type = self._training_type_keys.get(req_data['training_key'])
            if not training_type:
                continue
            step = steps.get(req_data.get('step_name'))
            eq_type = eq_types.get(req_data.get('equipment_type_name'))
            if not step and not eq_type:
                continue
            req, _ = TrainingRequirement.objects.update_or_create(
                tenant=self.tenant,
                training_type=training_type,
                step=step,
                equipment_type=eq_type,
                defaults={'notes': req_data.get('notes', '')},
            )
            requirements.append(req)
        return requirements

    def _create_job_roles(self):
        """Job roles + their role-scoped required-competency profiles."""
        roles = []
        self._job_role_keys = {}  # key -> JobRole
        for role_data in DEMO_JOB_ROLES:
            role, _ = JobRole.objects.update_or_create(
                tenant=self.tenant,
                name=role_data['name'],
                defaults={
                    'description': f"{role_data['name']} — required-competency profile.",
                    'active': True,
                },
            )
            self._job_role_keys[role_data['key']] = role
            roles.append(role)

            # Role-scoped requirements at their min levels.
            for training_key, min_level in role_data['requirements']:
                training_type = self._training_type_keys.get(training_key)
                if not training_type:
                    continue
                TrainingRequirement.objects.update_or_create(
                    tenant=self.tenant,
                    training_type=training_type,
                    job_role=role,
                    defaults={'min_level': min_level, 'notes': f"Required for {role_data['name']}"},
                )
        return roles

    def _assign_user_roles(self, user_map):
        for email, role_key in DEMO_USER_ROLES.items():
            user = user_map.get(email)
            role = self._job_role_keys.get(role_key)
            if user and role:
                user.job_role = role
                user.save(update_fields=['job_role'])

    def _create_training_record(self, record_data, user, training_type):
        completed_date = self.today - timedelta(days=record_data['completed_days_ago'])
        expires_date = self.today + timedelta(days=record_data['expires_days'])
        record, _ = TrainingRecord.objects.update_or_create(
            tenant=self.tenant,
            user=user,
            training_type=training_type,
            defaults={
                'completed_date': completed_date,
                'expires_date': expires_date,
                'level': record_data.get('level', 3),
                'notes': 'Demo training record',
            },
        )
        return record

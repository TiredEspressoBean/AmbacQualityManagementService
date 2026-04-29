"""
Base seeder class with shared utilities for all seed modules.
"""

import random
from datetime import timedelta
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from faker import Faker

from Tracker.models import (
    Tenant, TenantGroup, UserRole, User,
)
from Tracker.services.core.user import add_user_to_tenant_group


class BaseSeeder:
    """
    Base class for all seed modules.

    Provides shared utilities:
    - Tenant management
    - User activity weighting (80/20 rule)
    - Audit log creation
    - Timestamp helpers
    - Random weighted choices
    """

    def __init__(self, stdout, style, tenant=None, scale='medium'):
        self.stdout = stdout
        self.style = style
        self.fake = Faker()
        self.tenant = tenant
        self.scale = scale

        # Scale configurations
        self.scale_config = {
            'small': {'orders': 10, 'customers': 5, 'employees': 8, 'parts_per_order': (5, 15)},
            'medium': {'orders': 50, 'customers': 15, 'employees': 25, 'parts_per_order': (10, 30)},
            'large': {'orders': 200, 'customers': 40, 'employees': 50, 'parts_per_order': (15, 50)},
        }

        # User activity weights (set via setup_user_activity_weights)
        self.employee_weights = {}
        self.weighted_employees = []
        self.employee_weight_list = []
        self.qa_weights = []
        self.weighted_qa_staff = []

    @property
    def config(self):
        return self.scale_config[self.scale]

    def log(self, message, success=False, warning=False):
        """Helper to write styled output."""
        if success:
            self.stdout.write(self.style.SUCCESS(message))
        elif warning:
            self.stdout.write(self.style.WARNING(message))
        else:
            self.stdout.write(message)

    # =========================================================================
    # Tenant Management
    # =========================================================================

    def create_or_get_tenant(self, slug='ambac', name='AMBAC Manufacturing'):
        """Create or update the tenant for demo data."""
        tenant, created = Tenant.objects.update_or_create(
            slug=slug,
            defaults={
                'name': name,
                'tier': Tenant.Tier.PRO,
                'status': Tenant.Status.ACTIVE,
                'is_active': True,
                'settings': {
                    'industry': 'diesel_remanufacturing',
                    'demo_tenant': True,
                }
            }
        )
        if created:
            self.log(f"Created tenant: {tenant.name} (slug: {tenant.slug})")
        else:
            self.log(f"Using existing tenant: {tenant.name} (updated status/tier)")
        self.tenant = tenant
        return tenant

    def verify_groups_exist(self):
        """Verify required TenantGroups exist for this tenant.

        Tenant groups are auto-seeded by GroupSeeder.seed_for_tenant() on the
        Tenant post_save signal. If any are missing, the tenant likely wasn't
        created through normal channels — run `seed_demo` or recreate the tenant.
        """
        required_groups = [
            'Tenant Admin',
            'QA Manager',
            'QA Inspector',
            'Production Manager',
            'Operator',
            'Document Controller',
            'Customer',
        ]

        missing_groups = []
        for group_name in required_groups:
            if not TenantGroup.objects.filter(name=group_name, tenant=self.tenant).exists():
                missing_groups.append(group_name)

        if missing_groups:
            self.log(
                f"Missing TenantGroups in tenant {self.tenant.slug}: {', '.join(missing_groups)}. "
                "Run 'python manage.py seed_demo' or recreate the tenant to trigger GroupSeeder.",
                warning=True
            )
            return False
        else:
            self.log(f"  Verified {len(required_groups)} TenantGroups exist")
            return True

    def assign_user_to_group(self, user, group_name, granted_by=None):
        """Assign user to a TenantGroup by name within the seeder's tenant."""
        try:
            add_user_to_tenant_group(
                user, group_name, tenant=self.tenant, granted_by=granted_by
            )
        except TenantGroup.DoesNotExist:
            self.log(
                f"  Warning: TenantGroup '{group_name}' not found in tenant",
                warning=True,
            )

    # =========================================================================
    # User Activity Weighting (80/20 Rule)
    # =========================================================================

    def setup_user_activity_weights(self, users):
        """
        Set up 80/20 activity distribution - some users are much more active.
        Top 20% of users do 80% of the work (Pareto principle).
        """
        all_employees = users['employees']
        num_employees = len(all_employees)

        # Create weights using Zipf-like distribution
        weights = []
        for i, user in enumerate(all_employees):
            rank = i + 1
            weight = 1.0 / (rank ** 0.8)  # Slightly flattened Zipf
            weights.append(weight)

        # Normalize weights
        total_weight = sum(weights)
        self.employee_weights = {
            user: weight / total_weight
            for user, weight in zip(all_employees, weights)
        }

        self.weighted_employees = all_employees
        self.employee_weight_list = [self.employee_weights[u] for u in all_employees]

        # Same for QA staff
        qa_staff = users.get('qa_staff', [])
        if qa_staff:
            qa_weights = [1.0 / ((i + 1) ** 0.6) for i in range(len(qa_staff))]
            total_qa = sum(qa_weights)
            self.qa_weights = [w / total_qa for w in qa_weights]
            self.weighted_qa_staff = qa_staff
        else:
            self.qa_weights = []
            self.weighted_qa_staff = []

        # Identify power users for logging
        power_users = all_employees[:max(1, num_employees // 5)]
        power_user_names = [f"{u.first_name} {u.last_name}" for u in power_users[:3]]
        self.log(f"  User activity: power users = {', '.join(power_user_names)}...")

    def get_weighted_employee(self, users):
        """Select an employee using activity-weighted distribution."""
        if self.weighted_employees:
            return random.choices(self.weighted_employees, weights=self.employee_weight_list, k=1)[0]
        return random.choice(users['employees'])

    def get_weighted_qa_staff(self, users):
        """Select QA staff using activity-weighted distribution."""
        if self.weighted_qa_staff:
            return random.choices(self.weighted_qa_staff, weights=self.qa_weights, k=1)[0]
        qa_staff = users.get('qa_staff', users['employees'])
        return random.choice(qa_staff) if qa_staff else random.choice(users['employees'])

    # =========================================================================
    # Audit Log Helpers
    # =========================================================================

    def create_audit_log(self, model_class, obj_id, action, timestamp, actor, changes=None):
        """Create an audit log entry with backdated timestamp."""
        from auditlog.models import LogEntry

        content_type = ContentType.objects.get_for_model(model_class)
        action_map = {'CREATE': 0, 'UPDATE': 1, 'DELETE': 2}

        LogEntry.objects.create(
            content_type=content_type,
            object_pk=str(obj_id),
            object_repr=f"{model_class.__name__} {obj_id}",
            action=action_map.get(action, 1),
            changes=changes or {},
            actor=actor,
            timestamp=timestamp,
        )

    def backdate_object(self, model_class, obj_id, timestamp, actor=None):
        """Update created_at timestamp for an object."""
        model_class.objects.filter(id=obj_id).update(created_at=timestamp)
        if actor:
            self.create_audit_log(model_class, obj_id, 'CREATE', timestamp, actor)

    # =========================================================================
    # Timestamp Helpers
    # =========================================================================

    def calculate_work_order_timestamp(self, order):
        """Calculate realistic work order start time based on order creation."""
        # Work orders typically start 1-5 days after order creation
        days_delay = random.randint(1, 5)
        return order.created_at + timedelta(days=days_delay, hours=random.randint(6, 14))

    def calculate_step_timestamp(self, base_timestamp, step_index, total_steps):
        """Calculate timestamp for a step based on position in workflow."""
        # Each step takes 1-8 hours, spread across working days
        hours_per_step = random.uniform(1, 8)
        total_hours = step_index * hours_per_step
        return base_timestamp + timedelta(hours=total_hours)

    # =========================================================================
    # Random Helpers
    # =========================================================================

    def weighted_choice(self, choices):
        """
        Make a weighted random choice.

        Args:
            choices: List of (item, weight) tuples

        Returns:
            Selected item
        """
        items, weights = zip(*choices)
        return random.choices(items, weights=weights, k=1)[0]

    def random_date_in_range(self, start_days_ago, end_days_ago=0):
        """Get a random date between start_days_ago and end_days_ago."""
        start = timezone.now() - timedelta(days=start_days_ago)
        end = timezone.now() - timedelta(days=end_days_ago)
        delta = end - start
        random_days = random.random() * delta.days
        return start + timedelta(days=random_days)

    # =========================================================================
    # Time-Based Quality Patterns
    # =========================================================================

    def get_shift_quality_modifier(self, timestamp):
        """
        Return quality modifier based on shift.

        First shift (6am-2pm): Baseline (1.0)
        Second shift (2pm-10pm): 3% worse (0.97)
        Third shift (10pm-6am): 6% worse (0.94)

        Returns a multiplier for pass rates (lower = more defects).
        """
        hour = timestamp.hour
        if 6 <= hour < 14:    # First shift
            return 1.0  # Baseline
        elif 14 <= hour < 22:  # Second shift
            return 0.97  # 3% worse
        else:                  # Third shift
            return 0.94  # 6% worse

    def get_equipment_degradation(self, equipment, calibration_records=None):
        """
        Equipment performance degrades as calibration ages.

        Args:
            equipment: The Equipments instance
            calibration_records: Optional queryset/list of calibration records

        Returns:
            Quality modifier (1.0 = normal, lower = worse quality)
        """
        from Tracker.models import CalibrationRecord

        if calibration_records is None:
            # Get most recent calibration for this equipment
            latest = CalibrationRecord.objects.filter(
                equipment=equipment
            ).order_by('-calibration_date').first()
        else:
            # Find record for this equipment
            latest = None
            for record in calibration_records:
                if record.equipment_id == equipment.id:
                    if latest is None or record.calibration_date > latest.calibration_date:
                        latest = record

        if not latest:
            return 1.0  # No calibration data, assume normal

        days_since = (timezone.now().date() - latest.calibration_date).days

        if days_since > 180:
            return 0.90  # 10% worse if calibration overdue
        elif days_since > 150:
            return 0.95  # 5% worse if calibration due soon
        return 1.0

    def get_operator_performance(self, user, training_records=None):
        """
        Operator performance varies based on experience.

        Args:
            user: The User instance
            training_records: Optional queryset/list of training records

        Returns:
            Quality modifier (1.0 = baseline, >1 = better, <1 = worse)
        """
        from Tracker.models import TrainingRecord

        # Calculate experience based on account creation
        if hasattr(user, 'date_joined') and user.date_joined:
            days_since_joined = (timezone.now() - user.date_joined).days
        else:
            days_since_joined = 180  # Assume moderate experience

        # New operators (< 30 days): 15% higher defect rate
        if days_since_joined < 30:
            return 0.85

        # Experienced operators (> 1 year): 10% lower defect rate
        if days_since_joined > 365:
            return 1.10

        # Default: linear interpolation between 30 days and 1 year
        # At 30 days: 0.85, at 365 days: 1.10
        progress = (days_since_joined - 30) / (365 - 30)
        return 0.85 + (0.25 * progress)

    def get_combined_quality_modifier(self, timestamp, equipment=None, operator=None,
                                       calibration_records=None, training_records=None):
        """
        Combine all quality modifiers into a single factor.

        Returns a multiplier for pass rates. Values < 1.0 increase defect likelihood.
        """
        modifier = 1.0

        # Apply shift modifier
        modifier *= self.get_shift_quality_modifier(timestamp)

        # Apply equipment degradation
        if equipment:
            modifier *= self.get_equipment_degradation(equipment, calibration_records)

        # Apply operator performance
        if operator:
            modifier *= self.get_operator_performance(operator, training_records)

        return modifier

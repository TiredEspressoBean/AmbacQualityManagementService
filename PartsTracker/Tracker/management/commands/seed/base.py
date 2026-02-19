"""
Base seeder class with shared utilities for all seed modules.
"""

import random
from datetime import timedelta
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from faker import Faker

from Tracker.models import (
    Tenant, TenantGroup, UserRole, User,
)


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
        """Create or get the tenant for demo data."""
        tenant, created = Tenant.objects.get_or_create(
            slug=slug,
            defaults={
                'name': name,
                'tier': Tenant.Tier.PRO,
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
            self.log(f"Using existing tenant: {tenant.name}")
        self.tenant = tenant
        return tenant

    def verify_groups_exist(self):
        """Verify required groups exist (auto-created via post_migrate signal)."""
        required_groups = [
            'Admin',
            'QA_Manager',
            'QA_Inspector',
            'Production_Manager',
            'Production_Operator',
            'Document_Controller',
            'Customer',
        ]

        missing_groups = []
        for group_name in required_groups:
            if not Group.objects.filter(name=group_name).exists():
                missing_groups.append(group_name)

        if missing_groups:
            self.log(
                f"Missing groups: {', '.join(missing_groups)}. "
                "Run 'python manage.py setup_defaults' to create them.",
                warning=True
            )
            return False
        else:
            self.log(f"  Verified {len(required_groups)} groups exist")
            return True

    def assign_user_to_group(self, user, group, granted_by=None):
        """
        Assign user to a TenantGroup within the tenant context.

        Maps Django Group names to TenantGroup names and creates UserRole.
        """
        # Map Django Group names to TenantGroup names
        group_name_map = {
            'Admin': 'Tenant Admin',
            'QA_Manager': 'QA Manager',
            'QA_Inspector': 'QA Inspector',
            'Production_Manager': 'Production Manager',
            'Production_Operator': 'Operator',
            'Document_Controller': 'Document Controller',
            'Customer': 'Customer',
        }

        tenant_group_name = group_name_map.get(group.name, group.name)

        # Find the TenantGroup in this tenant
        try:
            tenant_group = TenantGroup.objects.get(
                tenant=self.tenant,
                name=tenant_group_name
            )
        except TenantGroup.DoesNotExist:
            self.log(f"  Warning: TenantGroup '{tenant_group_name}' not found in tenant", warning=True)
            return

        # Create UserRole if it doesn't exist
        UserRole.objects.get_or_create(
            user=user,
            group=tenant_group
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

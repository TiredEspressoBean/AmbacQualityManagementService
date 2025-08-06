# Tracker/management/commands/setup_groups.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from Tracker.models import (
    Orders, Parts, Documents, QualityReports, WorkOrder,
    Steps, Processes, PartTypes, Equipments, User, Companies
)


class Command(BaseCommand):
    help = 'Create basic user groups with appropriate permissions'

    def handle(self, *args, **options):
        self.stdout.write('Setting up basic permission groups...')

        # Simple, practical groups
        groups_config = {

            'Customer': {
                'description': 'External customers - view their own orders',
                'permissions': [
                    ('view_orders', Orders),
                    ('view_parts', Parts),
                    ('view_documents', Documents),  # Public only
                ]
            },

            'Operator': {
                'description': 'Production workers - do the work, log quality data',
                'permissions': [
                    ('view_workorder', WorkOrder),
                    ('change_workorder', WorkOrder),
                    ('view_parts', Parts),
                    ('change_parts', Parts),
                    ('add_qualityreports', QualityReports),
                    ('view_qualityreports', QualityReports),
                    ('view_documents', Documents),
                    ('add_documents', Documents),  # Upload photos/reports
                ]
            },

            'Manager': {
                'description': 'Supervisors and managers - can manage orders and processes',
                'permissions': [
                    # Orders and work
                    ('view_orders', Orders),
                    ('add_orders', Orders),
                    ('change_orders', Orders),
                    ('view_workorder', WorkOrder),
                    ('add_workorder', WorkOrder),
                    ('change_workorder', WorkOrder),

                    # Parts and quality
                    ('view_parts', Parts),
                    ('add_parts', Parts),
                    ('change_parts', Parts),
                    ('view_qualityreports', QualityReports),
                    ('add_qualityreports', QualityReports),
                    ('change_qualityreports', QualityReports),

                    # Process setup
                    ('view_processes', Processes),
                    ('add_processes', Processes),
                    ('change_processes', Processes),
                    ('view_steps', Steps),
                    ('add_steps', Steps),
                    ('change_steps', Steps),
                    ('view_parttypes', PartTypes),
                    ('add_parttypes', PartTypes),
                    ('change_parttypes', PartTypes),

                    # Equipment and docs
                    ('view_equipments', Equipments),
                    ('change_equipments', Equipments),
                    ('view_documents', Documents),
                    ('add_documents', Documents),
                    ('change_documents', Documents),

                    # Companies and users
                    ('view_companies', Companies),
                    ('change_companies', Companies),
                    ('view_user', User),
                ]
            },

            'Admin': {
                'description': 'System administrators - full access except superuser functions',
                'permissions': 'all_except_delete'
            }
        }

        # Create groups and assign permissions
        for group_name, config in groups_config.items():
            group, created = Group.objects.get_or_create(name=group_name)

            if config['permissions'] == 'all_except_delete':
                # Admin gets everything except delete permissions
                all_models = [Orders, Parts, Documents, QualityReports, WorkOrder,
                              Steps, Processes, PartTypes, Equipments, User, Companies]
                permissions = []
                for model in all_models:
                    ct = ContentType.objects.get_for_model(model)
                    model_perms = Permission.objects.filter(content_type=ct).exclude(
                        codename__startswith='delete_'
                    )
                    permissions.extend(model_perms)
                group.permissions.set(permissions)
            else:
                # Regular permission assignment
                permissions = []
                for perm_name, model in config['permissions']:
                    try:
                        ct = ContentType.objects.get_for_model(model)
                        perm = Permission.objects.get(codename=perm_name, content_type=ct)
                        permissions.append(perm)
                    except Permission.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f'Permission {perm_name} for {model.__name__} not found')
                        )

                group.permissions.set(permissions)

            status = "Created" if created else "Updated"
            perm_count = group.permissions.count()
            self.stdout.write(
                f'{status} group: {group_name} - {config["description"]} ({perm_count} permissions)'
            )

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('SIMPLE PERMISSION STRUCTURE:')
        self.stdout.write('=' * 60)
        self.stdout.write('Customer  → View their own orders/parts (read-only)')
        self.stdout.write('Operator  → Do production work, log quality data')
        self.stdout.write('Manager   → Manage orders, processes, people')
        self.stdout.write('Admin     → System administration (no delete)')
        self.stdout.write('Superuser → Everything (Django admin)')

        self.stdout.write('\n' + self.style.SUCCESS('Basic permission groups setup complete!'))
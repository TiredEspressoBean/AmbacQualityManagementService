"""
Management command to find and fix enum case mismatches in the database.

Some enum fields may have uppercase values (like "DEFAULT") but the Django/Python
enums expect specific case (like "default"). This causes validation errors.
"""

from django.core.management.base import BaseCommand
from django.db import connection
from Tracker import models as tracker_models


class Command(BaseCommand):
    help = 'Find and fix enum case mismatches in the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without actually fixing',
        )
        parser.add_argument(
            '--tenant',
            type=str,
            help='Only fix data for specific tenant slug (e.g., demo, dev)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        tenant_filter = options.get('tenant')

        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('Enum Case Mismatch Finder and Fixer'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))

        if tenant_filter:
            self.stdout.write(self.style.WARNING(f'Filtering by tenant: {tenant_filter}'))

        self.stdout.write('')

        total_fixed = 0

        # Define enum field checks
        # Format: (Model class, field_name, Enum class)
        checks = [
            # Core
            (tracker_models.Tenant, 'tier', tracker_models.Tenant.Tier),
            (tracker_models.Tenant, 'status', tracker_models.Tenant.Status),

            # MES Lite - EdgeType (the one we know was broken)
            (tracker_models.StepEdge, 'edge_type', tracker_models.EdgeType),

            # MES Lite - Status fields
            (tracker_models.Parts, 'part_status', tracker_models.PartsStatus),
            (tracker_models.Processes, 'status', tracker_models.ProcessStatus),
            (tracker_models.Orders, 'status', tracker_models.OrdersStatus),
            (tracker_models.Orders, 'apqp_stage', tracker_models.APQPStage),
            (tracker_models.WorkOrder, 'status', tracker_models.WorkOrderStatus),
            (tracker_models.WorkOrder, 'priority', tracker_models.WorkOrderPriority),

            # QMS
            (tracker_models.QualityReportDefect, 'severity', tracker_models.DefectSeverity),
            (tracker_models.CAPA, 'capa_type', tracker_models.CapaType),
            (tracker_models.CAPA, 'severity', tracker_models.CapaSeverity),
            (tracker_models.CAPA, 'status', tracker_models.CapaStatus),
            (tracker_models.CapaTasks, 'task_type', tracker_models.CapaTaskType),
            (tracker_models.CapaTasks, 'status', tracker_models.CapaTaskStatus),
            (tracker_models.RcaRecord, 'method', tracker_models.RcaMethod),
            (tracker_models.RcaRecord, 'review_status', tracker_models.RcaReviewStatus),
            (tracker_models.RootCause, 'category', tracker_models.RootCauseCategory),
            (tracker_models.RootCause, 'verification_status', tracker_models.RootCauseVerificationStatus),

            # Equipment
            (tracker_models.Equipments, 'status', tracker_models.EquipmentStatus),

            # Step requirements
            (tracker_models.StepRequirement, 'requirement_type', tracker_models.RequirementType),

            # Additional QMS fields
            (tracker_models.FPIRecord, 'status', tracker_models.FPIStatus),
            (tracker_models.FPIRecord, 'result', tracker_models.FPIResult),
            (tracker_models.StepOverride, 'block_type', tracker_models.BlockType),
            (tracker_models.StepOverride, 'override_status', tracker_models.OverrideStatus),
            (tracker_models.StepRollback, 'reason', tracker_models.RollbackReason),
            (tracker_models.StepRollback, 'status', tracker_models.RollbackStatus),
        ]

        # Process each check
        for Model, field_name, enum_class in checks:
            try:
                fixed = self.check_and_fix_field(
                    Model,
                    field_name,
                    enum_class,
                    dry_run=dry_run,
                    tenant_filter=tenant_filter
                )
                total_fixed += fixed
            except Exception as e:
                model_name = Model.__name__
                self.stdout.write(self.style.ERROR(f'Error checking {model_name}.{field_name}: {str(e)}'))

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 80))
        if dry_run:
            self.stdout.write(self.style.WARNING(f'Would fix {total_fixed} mismatches (dry run)'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Fixed {total_fixed} mismatches'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

    def check_and_fix_field(self, Model, field_name, enum_class, dry_run=False, tenant_filter=None):
        """Check a specific field for case mismatches and fix them."""

        model_name = Model.__name__

        # Get valid enum values (the actual database values, not the labels)
        valid_values = [choice[0] for choice in enum_class.choices]

        # Query all objects
        queryset = Model.objects.all()

        # Filter by tenant if specified
        if tenant_filter and hasattr(Model, 'tenant'):
            try:
                tenant = tracker_models.Tenant.objects.get(slug=tenant_filter)
                queryset = queryset.filter(tenant=tenant)
            except tracker_models.Tenant.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Tenant {tenant_filter} not found'))
                return 0

        # Check if the field exists
        try:
            queryset.model._meta.get_field(field_name)
        except Exception:
            # Field doesn't exist on this model, skip
            return 0

        # Get all distinct values in the field
        try:
            distinct_values = queryset.values_list(field_name, flat=True).distinct()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error querying {model_name}.{field_name}: {str(e)}'))
            return 0

        # Find mismatches
        mismatches = []
        for value in distinct_values:
            if value is None:
                continue

            # For IntegerChoices, values are integers, not strings - skip case checking
            if isinstance(value, int):
                continue

            # Check if value is not in valid values (case sensitive)
            if value not in valid_values:
                # Try to find the correct case version
                value_lower = str(value).lower()
                correct_value = None

                for valid_val in valid_values:
                    if str(valid_val).lower() == value_lower:
                        correct_value = valid_val
                        break

                if correct_value:
                    mismatches.append((value, correct_value))

        if not mismatches:
            return 0

        # Report findings
        self.stdout.write(self.style.WARNING(f'\n{model_name}.{field_name}:'))

        total_fixed = 0
        for wrong_value, correct_value in mismatches:
            count = queryset.filter(**{field_name: wrong_value}).count()
            self.stdout.write(f'  Found {count} records with "{wrong_value}" (should be "{correct_value}")')

            if not dry_run:
                # Fix the records
                updated = queryset.filter(**{field_name: wrong_value}).update(**{field_name: correct_value})
                self.stdout.write(self.style.SUCCESS(f'  [OK] Fixed {updated} records'))
                total_fixed += updated
            else:
                self.stdout.write(self.style.WARNING(f'  Would fix {count} records'))
                total_fixed += count

        return total_fixed

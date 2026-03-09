"""
Seed development tenant with random Faker data.

Generates realistic production data with:
- Weighted user activity (80/20 Zipf distribution)
- Realistic workflow progression (wave-front part movement)
- Shift-based quality modifiers
- Equipment degradation effects based on calibration age
- SPC baseline generation with frozen limits
- RCA methods (5-Whys, Fishbone diagrams)

Usage:
    # Default: small scale with all modules
    python manage.py seed_dev

    # Medium scale
    python manage.py seed_dev --scale medium

    # Specific modules only
    python manage.py seed_dev --modules users manufacturing orders

    # Keep existing data
    python manage.py seed_dev --no-clear

    # Skip historical FPY data (faster)
    python manage.py seed_dev --skip-historical
"""

from auditlog.models import LogEntry
from django.core.management.base import BaseCommand

from Tracker.models import (
    # Core models
    Tenant, TenantGroupMembership,
    Companies, User, PartTypes, Processes, Steps, Orders, Parts, Documents, Equipments,
    EquipmentType, WorkOrder, ExternalAPIOrderIdentifier,
    # Process graph models
    ProcessStep, StepEdge,
    # Quality models
    QualityErrorsList, QualityReports, MeasurementDefinition, MeasurementResult,
    QuarantineDisposition, QaApproval, StepTransitionLog, EquipmentUsage,
    # Sampling models
    SamplingRuleSet, SamplingRule, SamplingTriggerState, SamplingAuditLog, SamplingAnalytics,
    # Workflow execution models
    StepExecution,
    # FPI models
    FPIRecord,
    # CAPA models
    CAPA, CapaTasks, CapaTaskAssignee, RcaRecord, FiveWhys, Fishbone, CapaVerification,
    # Document models
    DocumentType, ApprovalTemplate, ApprovalRequest, ApprovalResponse,
    # 3D model and annotation models
    ThreeDModel, HeatMapAnnotations,
    # Training and Calibration
    TrainingType, TrainingRecord, TrainingRequirement, CalibrationRecord,
    # Reman models
    Core, HarvestedComponent, DisassemblyBOMLine,
    # SPC models
    SPCBaseline,
    # Life tracking models
    LifeLimitDefinition, PartTypeLifeLimit, LifeTracking,
    # Enums
    OrdersStatus,
)

from .seed import (
    BaseSeeder,
    UserSeeder,
    ManufacturingSeeder,
    OrderSeeder,
    QualitySeeder,
    CapaSeeder,
    DocumentSeeder,
    ThreeDModelSeeder,
    TrainingSeeder,
    CalibrationSeeder,
    RemanSeeder,
    LifeTrackingSeeder,
)


class Command(BaseCommand):
    help = "Seed development tenant with random Faker data for testing"

    # Platform admin (never deleted)
    PLATFORM_ADMIN_EMAIL = 'admin@ambac.local'
    PLATFORM_ADMIN_PASSWORD = 'admin'

    # Tenant settings
    TENANT_SLUG = 'dev'
    TENANT_NAME = 'Development'

    def add_arguments(self, parser):
        parser.add_argument(
            '--scale',
            type=str,
            default='small',
            choices=['small', 'medium', 'large'],
            help='Scale of data generation (small=10 orders, medium=50 orders, large=200 orders). Default: small',
        )
        parser.add_argument(
            '--no-clear',
            action='store_true',
            help='Skip clearing existing data (by default, existing data is cleared)',
        )
        parser.add_argument(
            '--skip-historical',
            action='store_true',
            help='Skip generating historical FPY trend data (faster seeding)',
        )
        parser.add_argument(
            '--modules',
            type=str,
            nargs='+',
            choices=['users', 'manufacturing', 'reman', 'life_tracking', 'orders', 'quality', 'capa', 'documents', '3d', 'training', 'calibration', 'all'],
            default=['all'],
            help='Specific modules to run. Default: all',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually doing it',
        )

    def handle(self, *args, **options):
        self.scale = options['scale']
        self.no_clear = options['no_clear']
        self.skip_historical = options['skip_historical']
        self.modules = set(options['modules'])
        self.verbose = options.get('verbosity', 1) >= 2
        self.dry_run = options['dry_run']

        if 'all' in self.modules:
            self.modules = {'users', 'manufacturing', 'reman', 'life_tracking', 'orders', 'quality', 'capa', 'documents', '3d', 'training', 'calibration'}

        self.stdout.write(f"\nSeed Dev - Scale: {self.scale}")
        self.stdout.write(f"  Modules: {', '.join(sorted(self.modules))}")
        self.stdout.write(f"  Clear existing: {not self.no_clear}")

        if self.dry_run:
            self._show_dry_run_plan()
            return

        # Ensure platform admin exists
        self._ensure_platform_admin()

        # Clear existing data unless --no-clear
        if not self.no_clear:
            self._clear_tenant_data()

        # Seed the dev tenant
        self._seed_dev_tenant()

        self.stdout.write(self.style.SUCCESS(f"\nGenerated realistic {self.scale} scale dev data!"))
        self._show_data_summary()

    def _ensure_platform_admin(self):
        """Ensure platform admin exists. This user is never deleted."""
        admin, created = User.objects.get_or_create(
            email=self.PLATFORM_ADMIN_EMAIL,
            defaults={
                'username': self.PLATFORM_ADMIN_EMAIL,
                'first_name': 'Platform',
                'last_name': 'Admin',
                'is_superuser': True,
                'is_staff': True,
                'tenant': None,
            }
        )
        if created:
            admin.set_password(self.PLATFORM_ADMIN_PASSWORD)
            admin.save()
            self.stdout.write(f"  Created platform admin: {self.PLATFORM_ADMIN_EMAIL}")
        elif self.verbose:
            self.stdout.write(f"  Platform admin exists: {self.PLATFORM_ADMIN_EMAIL}")

    def _show_dry_run_plan(self):
        """Show what would be created without doing it."""
        self.stdout.write(self.style.WARNING("\n[DRY RUN] Would perform the following:"))
        if not self.no_clear:
            self.stdout.write("  1. Clear existing dev tenant data")
        self.stdout.write(f"  2. Ensure platform admin: {self.PLATFORM_ADMIN_EMAIL}")
        self.stdout.write(f"  3. Create/get dev tenant with auto-seeded groups, doc types")
        self.stdout.write(f"  4. Create random Faker users ({self.scale} scale)")
        self.stdout.write(f"  5. Run modules: {', '.join(sorted(self.modules))}")

    def _clear_tenant_data(self):
        """Clear existing dev tenant data in dependency order."""
        self.stdout.write(f"Clearing existing {self.TENANT_SLUG} tenant data...")

        # Get the tenant if it exists
        try:
            tenant = Tenant.objects.get(slug=self.TENANT_SLUG)
        except Tenant.DoesNotExist:
            self.stdout.write("  No existing dev tenant to clear")
            return

        # Clear tenant-scoped data in dependency order
        # Most models inherit from SecureModel which has direct 'tenant' FK
        models_to_clear = [
            (TenantGroupMembership, "Tenant group memberships", {'user__tenant': tenant}),
            (LogEntry, "Audit log entries", {}),  # Not tenant-scoped
            (ApprovalResponse, "Approval responses", {'tenant': tenant}),
            (ApprovalRequest, "Approval requests", {'tenant': tenant}),
            (CapaVerification, "CAPA verifications", {'capa__tenant': tenant}),
            (FiveWhys, "Five whys", {'rca_record__capa__tenant': tenant}),
            (Fishbone, "Fishbone diagrams", {'rca_record__capa__tenant': tenant}),
            (RcaRecord, "RCA records", {'capa__tenant': tenant}),
            (CapaTaskAssignee, "CAPA task assignees", {'task__capa__tenant': tenant}),
            (CapaTasks, "CAPA tasks", {'capa__tenant': tenant}),
            (CAPA, "CAPAs", {'tenant': tenant}),
            (TrainingRecord, "Training records", {'tenant': tenant}),
            (TrainingRequirement, "Training requirements", {'tenant': tenant}),
            (TrainingType, "Training types", {'tenant': tenant}),
            (CalibrationRecord, "Calibration records", {'tenant': tenant}),
            (SamplingAnalytics, "Sampling analytics", {'tenant': tenant}),
            (SamplingAuditLog, "Sampling audit logs", {'tenant': tenant}),
            (SamplingTriggerState, "Sampling trigger states", {'tenant': tenant}),
            (SamplingRule, "Sampling rules", {'tenant': tenant}),
            (SamplingRuleSet, "Sampling rule sets", {'tenant': tenant}),
            (MeasurementResult, "Measurement results", {'tenant': tenant}),
            (MeasurementDefinition, "Measurement definitions", {'tenant': tenant}),
            (QaApproval, "QA approvals", {'tenant': tenant}),
            (QuarantineDisposition, "Quarantine dispositions", {'tenant': tenant}),
            (QualityReports, "Quality reports", {'tenant': tenant}),
            (QualityErrorsList, "Quality errors", {'tenant': tenant}),
            (HeatMapAnnotations, "Heatmap annotations", {'tenant': tenant}),
            (ThreeDModel, "3D models", {'tenant': tenant}),
            (StepExecution, "Step executions", {'tenant': tenant}),
            (StepTransitionLog, "Step transition logs", {'tenant': tenant}),
            (EquipmentUsage, "Equipment usage", {'tenant': tenant}),
            (FPIRecord, "FPI records", {'tenant': tenant}),
            (LifeTracking, "Life tracking records", {'tenant': tenant}),
            (PartTypeLifeLimit, "Part type life limits", {'tenant': tenant}),
            (LifeLimitDefinition, "Life limit definitions", {'tenant': tenant}),
            (HarvestedComponent, "Harvested components", {'tenant': tenant}),
            (Core, "Cores", {'tenant': tenant}),
            (DisassemblyBOMLine, "Disassembly BOM lines", {'tenant': tenant}),
            (WorkOrder, "Work orders", {'tenant': tenant}),
            (Parts, "Parts", {'tenant': tenant}),
            (ExternalAPIOrderIdentifier, "External order identifiers", {'tenant': tenant}),
            (Orders, "Orders", {'tenant': tenant}),
            (SPCBaseline, "SPC baselines", {'tenant': tenant}),
            (StepEdge, "Step edges", {'process__tenant': tenant}),
            (ProcessStep, "Process steps", {'process__tenant': tenant}),
            (Steps, "Steps", {'tenant': tenant}),
            (Processes, "Processes", {'tenant': tenant}),
            (Documents, "Documents", {'tenant': tenant}),
            (ApprovalTemplate, "Approval templates", {'tenant': tenant}),
            (DocumentType, "Document types", {'tenant': tenant}),
            (Equipments, "Equipment", {'tenant': tenant}),
            (EquipmentType, "Equipment types", {'tenant': tenant}),
            (PartTypes, "Part types", {'tenant': tenant}),
            (User, "Users", {'tenant': tenant, 'is_superuser': False}),
            (Companies, "Companies", {'tenant': tenant}),
        ]

        for model, name, filters in models_to_clear:
            try:
                qs = model.objects.filter(**filters) if filters else model.objects.all()
                count = qs.count()
                # Use _raw_delete to bypass soft-delete behavior
                if hasattr(qs, '_raw_delete'):
                    qs._raw_delete(qs.db)
                else:
                    qs.delete()
                if count > 0:
                    self.stdout.write(f"  Cleared {count} {name}")
            except Exception as e:
                error_msg = str(e).encode('ascii', 'replace').decode('ascii')
                self.stdout.write(self.style.WARNING(f"  Could not clear {name}: {error_msg[:200]}"))

        # Don't delete tenant - it has auto-seeded doc types/approval templates with protected FKs
        # The tenant will be reused with fresh data
        self.stdout.write(self.style.SUCCESS("  Dev tenant data cleared (tenant preserved for reuse)"))

    def _seed_dev_tenant(self):
        """Seed dev tenant with random Faker data."""
        # Initialize base seeder for shared operations
        base = BaseSeeder(self.stdout, self.style, scale=self.scale)

        # Create or get tenant
        tenant = base.create_or_get_tenant(slug=self.TENANT_SLUG, name=self.TENANT_NAME)

        # Initialize all seeders
        user_seeder = UserSeeder(self.stdout, self.style, tenant=tenant, scale=self.scale)
        manufacturing_seeder = ManufacturingSeeder(self.stdout, self.style, tenant=tenant, scale=self.scale)
        reman_seeder = RemanSeeder(self.stdout, self.style, tenant=tenant, scale=self.scale)
        order_seeder = OrderSeeder(self.stdout, self.style, tenant=tenant, scale=self.scale)
        quality_seeder = QualitySeeder(self.stdout, self.style, tenant=tenant, scale=self.scale)
        capa_seeder = CapaSeeder(self.stdout, self.style, tenant=tenant, scale=self.scale)
        document_seeder = DocumentSeeder(self.stdout, self.style, tenant=tenant, scale=self.scale)
        model_seeder = ThreeDModelSeeder(self.stdout, self.style, tenant=tenant, scale=self.scale)
        training_seeder = TrainingSeeder(self.stdout, self.style, tenant=tenant, scale=self.scale)
        calibration_seeder = CalibrationSeeder(self.stdout, self.style, tenant=tenant, scale=self.scale)
        life_tracking_seeder = LifeTrackingSeeder(self.stdout, self.style, tenant=tenant, scale=self.scale)

        # Cross-link seeders
        order_seeder.manufacturing_seeder = manufacturing_seeder
        quality_seeder.manufacturing_seeder = manufacturing_seeder
        reman_seeder.manufacturing_seeder = manufacturing_seeder
        capa_seeder.manufacturing_seeder = manufacturing_seeder

        # Track created data
        data = {
            'companies': [],
            'users': {},
            'part_types': [],
            'processes': [],
            'equipment': [],
            'equipment_types': [],
            'orders': [],
            'steps': [],
            'cores': [],
            'harvested_components': [],
        }

        # Phase 1: Foundation (Users, Companies)
        if 'users' in self.modules:
            self.stdout.write("\n--- Phase 1: Users and Companies ---")
            result = user_seeder.seed()
            data['companies'] = result['companies']
            data['users'] = result['users']
            data['admin'] = result['admin']

            # Share user activity weights with other seeders
            for seeder in [manufacturing_seeder, order_seeder, quality_seeder, capa_seeder,
                           document_seeder, model_seeder, training_seeder]:
                seeder.employee_weights = user_seeder.employee_weights
                seeder.weighted_employees = user_seeder.weighted_employees
                seeder.employee_weight_list = user_seeder.employee_weight_list
                seeder.qa_weights = user_seeder.qa_weights
                seeder.weighted_qa_staff = user_seeder.weighted_qa_staff
        else:
            data['companies'] = list(Companies.objects.filter(tenant=tenant))
            data['users'] = self._load_existing_users(tenant)

        # Phase 2: Manufacturing Setup
        if 'manufacturing' in self.modules:
            self.stdout.write("\n--- Phase 2: Manufacturing Setup ---")
            result = manufacturing_seeder.seed(data['users'].get('employees', []))
            data['part_types'] = result['part_types']
            data['processes'] = result['processes']
            data['equipment'] = result['equipment']
            data['equipment_types'] = result['equipment_types']
            data['steps'] = list(Steps.objects.filter(tenant=tenant))
        else:
            data['part_types'] = list(PartTypes.objects.filter(tenant=tenant))
            data['equipment'] = list(Equipments.objects.filter(tenant=tenant))
            data['equipment_types'] = list(EquipmentType.objects.filter(tenant=tenant))
            data['steps'] = list(Steps.objects.filter(tenant=tenant))

        # Phase 3: Orders and Workflow
        if 'orders' in self.modules:
            self.stdout.write("\n--- Phase 3: Orders and Workflow ---")
            result = order_seeder.seed(
                data['companies'],
                data['users'],
                data['part_types'],
                data['equipment']
            )
            data['orders'] = result['orders']
        else:
            data['orders'] = list(Orders.objects.filter(tenant=tenant))

        # Phase 3.5: Remanufacturing
        if 'reman' in self.modules:
            self.stdout.write("\n--- Phase 3.5: Remanufacturing Workflow ---")
            reman_seeder.employee_weights = user_seeder.employee_weights
            reman_seeder.weighted_employees = user_seeder.weighted_employees
            reman_seeder.employee_weight_list = user_seeder.employee_weight_list

            result = reman_seeder.seed(
                data['companies'],
                data['users'],
                data['part_types']
            )
            data['cores'] = result.get('cores', [])
            data['harvested_components'] = result.get('harvested_components', [])

            component_types = result.get('component_types', {})
            for comp_type in component_types.values():
                if comp_type not in data['part_types']:
                    data['part_types'].append(comp_type)
        else:
            data['cores'] = list(Core.objects.filter(tenant=tenant))
            data['harvested_components'] = list(HarvestedComponent.objects.filter(tenant=tenant))

        # Phase 3.6: Life Tracking
        if 'life_tracking' in self.modules:
            self.stdout.write("\n--- Phase 3.6: Life Tracking ---")
            life_tracking_seeder.seed(
                data['part_types'],
                cores=data['cores'],
                harvested_components=data['harvested_components']
            )

        # Phase 4: Quality Data
        if 'quality' in self.modules:
            self.stdout.write("\n--- Phase 4: Quality Reports ---")
            quality_seeder.seed(data['orders'], data['users'], data['equipment'])

            if not self.skip_historical:
                self.stdout.write("  Creating historical FPY trend data...")
                quality_seeder.seed_historical_fpy(data['part_types'], data['users'], data['equipment'])
                self.stdout.write("  Creating SPC baselines from historical data...")
                quality_seeder.seed_spc_baselines(data['users'])

        # Phase 5: CAPA
        if 'capa' in self.modules:
            self.stdout.write("\n--- Phase 5: CAPA Data ---")
            capa_seeder.seed(data['users'])

        # Phase 6: Documents
        if 'documents' in self.modules:
            self.stdout.write("\n--- Phase 6: Documents and Approvals ---")
            document_seeder.seed(data['companies'], data['users'])

        # Phase 7: 3D Models
        if '3d' in self.modules:
            self.stdout.write("\n--- Phase 7: 3D Models and Annotations ---")
            model_seeder.seed(data['part_types'], data['users'].get('employees', []))

        # Phase 8: Training
        if 'training' in self.modules:
            self.stdout.write("\n--- Phase 8: Training Records ---")
            training_seeder.seed(
                data['users'],
                steps=data['steps'],
                processes=None,
                equipment_types=data['equipment_types']
            )

        # Phase 9: Calibration
        if 'calibration' in self.modules:
            self.stdout.write("\n--- Phase 9: Calibration Records ---")
            calibration_seeder.seed(data['equipment'])
            calibration_seeder.seed_overdue_alerts(data['equipment'])

        # External API identifiers
        self._create_external_api_identifiers(data['orders'], tenant)

    def _load_existing_users(self, tenant):
        """Load existing users into expected structure."""
        users = {
            'customers': list(User.objects.filter(tenant=tenant, user_type='PORTAL')),
            'employees': list(User.objects.filter(tenant=tenant, user_type='INTERNAL')),
            'managers': [],
            'qa_staff': [],
        }

        for user in users['employees']:
            if user.groups.filter(name__in=['Production_Manager', 'Admin']).exists():
                users['managers'].append(user)
            if user.groups.filter(name__in=['QA_Manager', 'QA_Inspector']).exists():
                users['qa_staff'].append(user)

        return users

    def _create_external_api_identifiers(self, orders, tenant):
        """Create external API stage identifiers (HubSpot pipeline stages)."""
        hubspot_stages = [
            ('New Lead', '12345001', 'default', 1, False),
            ('Qualification', '12345002', 'default', 2, True),
            ('Proposal Sent', '12345003', 'default', 3, True),
            ('Negotiation', '12345004', 'default', 4, True),
            ('Closed Won', '12345005', 'default', 5, False),
            ('Closed Lost', '12345006', 'default', 6, False),
        ]

        created = 0
        for stage_name, api_id, pipeline_id, order, include_in_progress in hubspot_stages:
            _, was_created = ExternalAPIOrderIdentifier.objects.get_or_create(
                tenant=tenant,
                API_id=api_id,
                defaults={
                    'stage_name': stage_name,
                    'pipeline_id': pipeline_id,
                    'display_order': order,
                    'include_in_progress': include_in_progress,
                }
            )
            if was_created:
                created += 1

        if created:
            self.stdout.write(f"Created {created} HubSpot pipeline stage mappings")

    def _show_data_summary(self):
        """Show summary of created data."""
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("DEV TENANT DATA SUMMARY")
        self.stdout.write("=" * 50)

        try:
            tenant = Tenant.objects.get(slug=self.TENANT_SLUG)
        except Tenant.DoesNotExist:
            self.stdout.write("  No dev tenant found")
            return

        summary_items = [
            ("Companies", Companies.objects.filter(tenant=tenant).count()),
            ("Users", User.objects.filter(tenant=tenant).count()),
            ("Part Types", PartTypes.objects.filter(tenant=tenant).count()),
            ("Equipment", Equipments.objects.filter(tenant=tenant).count()),
            ("Orders", Orders.objects.filter(tenant=tenant).count()),
            ("Work Orders", WorkOrder.objects.filter(tenant=tenant).count()),
            ("Parts", Parts.objects.filter(tenant=tenant).count()),
            ("Cores", Core.objects.filter(tenant=tenant).count()),
            ("Quality Reports", QualityReports.objects.filter(tenant=tenant).count()),
            ("CAPAs", CAPA.objects.filter(tenant=tenant).count()),
            ("Documents", Documents.objects.filter(tenant=tenant).count()),
            ("Training Records", TrainingRecord.objects.filter(user__tenant=tenant).count()),
        ]

        for name, count in summary_items:
            if count > 0:
                self.stdout.write(f"{name}: {count}")

        self.stdout.write("=" * 50)

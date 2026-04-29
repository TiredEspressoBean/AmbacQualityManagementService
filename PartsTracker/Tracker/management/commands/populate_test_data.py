"""
Generate realistic production data for diesel fuel injector remanufacturing business.

This command orchestrates the modular seed system to create comprehensive demo data.
Each domain is handled by a specialized seeder module in the `seed/` package.

Supports two modes:
- dev: Random Faker data for development and testing
- demo: Deterministic preset data for sales demos and training (from DEMO_DATA_SYSTEM.md)

Usage:
    # Default: seed both dev and demo tenants with small scale data, clearing existing
    python manage.py populate_test_data

    # Seed only demo tenant with deterministic data
    python manage.py populate_test_data --mode demo

    # Seed only dev tenant with random data, medium scale
    python manage.py populate_test_data --mode dev --scale medium

    # Seed without clearing existing data
    python manage.py populate_test_data --no-clear

    # Preview what would be created without actually doing it
    python manage.py populate_test_data --dry-run

    # Verbose output
    python manage.py populate_test_data -v
"""

from auditlog.models import LogEntry
from django.core.management.base import BaseCommand

from Tracker.models import (
    # Core models
    Tenant,
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
    help = "Generate realistic production data for diesel fuel injector remanufacturing business"

    # Admin users that are never deleted during clear
    PLATFORM_ADMIN_EMAIL = 'admin@ambac.local'
    PLATFORM_ADMIN_PASSWORD = 'admin'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mode',
            type=str,
            default='all',
            choices=['dev', 'demo', 'all'],
            help='Which tenant(s) to seed: dev (random data), demo (deterministic), all (both). Default: all',
        )
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
            help='Specific modules to run. Ignored for demo mode which always runs full scenario. Default: all',
        )
        # Note: Django's BaseCommand already provides -v/--verbosity (0-3)
        # We use verbosity >= 2 for verbose output instead of a separate flag
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually doing it',
        )

    def handle(self, *args, **options):
        self.scale = options['scale']
        self.mode = options['mode']
        self.no_clear = options['no_clear']
        self.skip_historical = options['skip_historical']
        self.modules = set(options['modules'])
        self.verbose = options.get('verbosity', 1) >= 2  # Use Django's built-in verbosity
        self.dry_run = options['dry_run']

        if 'all' in self.modules:
            self.modules = {'users', 'manufacturing', 'reman', 'life_tracking', 'orders', 'quality', 'capa', 'documents', '3d', 'training', 'calibration'}

        # Determine which tenants to seed
        tenants_to_seed = []
        if self.mode in ('dev', 'all'):
            tenants_to_seed.append(('dev', 'Development'))
        if self.mode in ('demo', 'all'):
            tenants_to_seed.append(('demo', 'Demo Company'))

        # Show plan
        self.stdout.write(f"\nPopulate Test Data - Mode: {self.mode}, Scale: {self.scale}")
        self.stdout.write(f"  Tenants: {', '.join(t[0] for t in tenants_to_seed)}")
        if self.mode == 'demo':
            self.stdout.write(f"  Modules: full scenario (--modules ignored for demo mode)")
        else:
            self.stdout.write(f"  Modules: {', '.join(sorted(self.modules))}")
        self.stdout.write(f"  Clear existing: {not self.no_clear}")

        if self.dry_run:
            self.stdout.write(self.style.WARNING("\n[DRY RUN] Would perform the following:"))
            self._show_dry_run_plan(tenants_to_seed)
            return

        # Ensure platform admin exists (never deleted)
        self._ensure_platform_admin()

        # Clear existing data unless --no-clear
        if not self.no_clear:
            self.clear_data()

        # Seed each tenant
        for tenant_slug, tenant_name in tenants_to_seed:
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(f"Seeding tenant: {tenant_name} ({tenant_slug})")
            self.stdout.write('='*60)

            if tenant_slug == 'demo':
                self._seed_demo_tenant(tenant_slug, tenant_name)
            else:
                self._seed_dev_tenant(tenant_slug, tenant_name)

        self.stdout.write(self.style.SUCCESS(f"\nGenerated realistic {self.scale} scale production data!"))
        self.show_data_summary()

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
                'tenant': None,  # Platform-level, not tenant-scoped
            }
        )
        if created:
            admin.set_password(self.PLATFORM_ADMIN_PASSWORD)
            admin.save()
            self.stdout.write(f"  Created platform admin: {self.PLATFORM_ADMIN_EMAIL}")
        elif self.verbose:
            self.stdout.write(f"  Platform admin exists: {self.PLATFORM_ADMIN_EMAIL}")

    def _show_dry_run_plan(self, tenants_to_seed):
        """Show what would be created without actually doing it."""
        if not self.no_clear:
            self.stdout.write("  1. Clear all existing data (except platform admin)")
        self.stdout.write(f"  2. Ensure platform admin: {self.PLATFORM_ADMIN_EMAIL}")

        for tenant_slug, tenant_name in tenants_to_seed:
            self.stdout.write(f"\n  Tenant: {tenant_name} ({tenant_slug})")
            self.stdout.write(f"    - Create tenant with auto-seeded groups, doc types, approval templates")

            if tenant_slug == 'demo':
                self.stdout.write("    - Create preset demo users (one per training role):")
                self.stdout.write("        admin@demo.ambac.com (Alex Demo - Tenant Admin)")
                self.stdout.write("        maria.qa@demo.ambac.com (Maria Santos - QA Manager)")
                self.stdout.write("        sarah.qa@demo.ambac.com (Sarah Chen - QA Inspector)")
                self.stdout.write("        jennifer.mgr@demo.ambac.com (Jennifer Walsh - Production Manager)")
                self.stdout.write("        mike.ops@demo.ambac.com (Mike Rodriguez - Operator)")
                self.stdout.write("        dave.wilson@demo.ambac.com (Dave Wilson - Operator, expired training)")
                self.stdout.write("        lisa.docs@demo.ambac.com (Lisa Park - Document Controller)")
                self.stdout.write("        tom.bradley@midwestfleet.com (Tom Bradley - Customer)")
                self.stdout.write("    - Create demo companies: AMBAC, Midwest Fleet, Great Lakes Diesel, Northern Trucking")
                self.stdout.write("    - Create demo scenario with interconnected orders, quality events, CAPAs")
            else:
                self.stdout.write(f"    - Create random Faker users ({self.scale} scale)")
                self.stdout.write(f"    - Create random companies and business data")
                self.stdout.write(f"    - Modules: {', '.join(sorted(self.modules))}")

    def _seed_demo_tenant(self, tenant_slug, tenant_name):
        """Seed demo tenant with deterministic preset data."""
        from .seed.demo import DemoScenario

        # Initialize base seeder for tenant creation
        base = BaseSeeder(self.stdout, self.style, scale=self.scale)

        # Create or get demo tenant
        tenant = base.create_or_get_tenant(slug=tenant_slug, name=tenant_name)

        # Run demo scenario
        scenario = DemoScenario(self.stdout, self.style, tenant=tenant, scale=self.scale)
        scenario.verbose = self.verbose
        scenario.seed()

    def _seed_dev_tenant(self, tenant_slug, tenant_name):
        """Seed dev tenant with random Faker data."""
        # Initialize base seeder for shared operations
        base = BaseSeeder(self.stdout, self.style, scale=self.scale)

        # Create or get tenant with specified slug/name
        tenant = base.create_or_get_tenant(slug=tenant_slug, name=tenant_name)

        # Initialize all seeders with shared tenant and scale
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

        # Cross-link seeders that need each other's data
        order_seeder.manufacturing_seeder = manufacturing_seeder
        quality_seeder.manufacturing_seeder = manufacturing_seeder
        reman_seeder.manufacturing_seeder = manufacturing_seeder
        capa_seeder.manufacturing_seeder = manufacturing_seeder

        # Track created data for inter-module dependencies
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

        # =====================================================================
        # Phase 1: Foundation (Users, Companies)
        # =====================================================================
        if 'users' in self.modules:
            self.stdout.write("\n--- Phase 1: Users and Companies ---")
            result = user_seeder.seed()
            data['companies'] = result['companies']
            data['users'] = result['users']
            data['admin'] = result['admin']

            # Share user activity weights with other seeders (silently)
            for seeder in [manufacturing_seeder, order_seeder, quality_seeder, capa_seeder,
                           document_seeder, model_seeder, training_seeder]:
                seeder.employee_weights = user_seeder.employee_weights
                seeder.weighted_employees = user_seeder.weighted_employees
                seeder.employee_weight_list = user_seeder.employee_weight_list
                seeder.qa_weights = user_seeder.qa_weights
                seeder.weighted_qa_staff = user_seeder.weighted_qa_staff
        else:
            # Load existing data
            data['companies'] = list(Companies.all_tenants.filter(tenant=tenant))
            data['users'] = self._load_existing_users(tenant)

        # =====================================================================
        # Phase 2: Manufacturing Setup (Part Types, Processes, Equipment)
        # =====================================================================
        if 'manufacturing' in self.modules:
            self.stdout.write("\n--- Phase 2: Manufacturing Setup ---")
            result = manufacturing_seeder.seed(data['users'].get('employees', []))
            data['part_types'] = result['part_types']
            data['processes'] = result['processes']
            data['equipment'] = result['equipment']
            data['equipment_types'] = result['equipment_types']

            # Collect all steps for training requirements
            data['steps'] = list(Steps.all_tenants.filter(tenant=tenant))
        else:
            data['part_types'] = list(PartTypes.all_tenants.filter(tenant=tenant))
            data['equipment'] = list(Equipments.all_tenants.filter(tenant=tenant))
            data['equipment_types'] = list(EquipmentType.all_tenants.filter(tenant=tenant))
            data['steps'] = list(Steps.all_tenants.filter(tenant=tenant))

        # =====================================================================
        # Phase 3: Orders and Workflow
        # =====================================================================
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
            data['orders'] = list(Orders.all_tenants.filter(tenant=tenant))

        # =====================================================================
        # Phase 3.5: Remanufacturing Workflow (Cores, Components)
        # NOTE: Reman runs AFTER orders so work orders exist for production entry
        # =====================================================================
        if 'reman' in self.modules:
            self.stdout.write("\n--- Phase 3.5: Remanufacturing Workflow ---")

            # Share user activity weights with reman seeder
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

            # Add component types to part_types if new ones were created
            component_types = result.get('component_types', {})
            for comp_type in component_types.values():
                if comp_type not in data['part_types']:
                    data['part_types'].append(comp_type)
        else:
            data['cores'] = list(Core.all_tenants.filter(tenant=tenant))
            data['harvested_components'] = list(HarvestedComponent.all_tenants.filter(tenant=tenant))

        # =====================================================================
        # Phase 3.6: Life Tracking (depends on cores and part types)
        # =====================================================================
        if 'life_tracking' in self.modules:
            self.stdout.write("\n--- Phase 3.6: Life Tracking ---")
            life_tracking_seeder.seed(
                data['part_types'],
                cores=data['cores'],
                harvested_components=data['harvested_components']
            )

        # =====================================================================
        # Phase 4: Quality Data
        # =====================================================================
        if 'quality' in self.modules:
            self.stdout.write("\n--- Phase 4: Quality Reports ---")
            quality_seeder.seed(data['orders'], data['users'], data['equipment'])

            if not self.skip_historical:
                self.stdout.write("  Creating historical FPY trend data...")
                quality_seeder.seed_historical_fpy(data['part_types'], data['users'], data['equipment'])

                self.stdout.write("  Creating SPC baselines from historical data...")
                quality_seeder.seed_spc_baselines(data['users'])

        # =====================================================================
        # Phase 5: CAPA (depends on quality failures)
        # =====================================================================
        if 'capa' in self.modules:
            self.stdout.write("\n--- Phase 5: CAPA Data ---")
            capa_seeder.seed(data['users'])

        # =====================================================================
        # Phase 6: Documents and Approvals
        # =====================================================================
        if 'documents' in self.modules:
            self.stdout.write("\n--- Phase 6: Documents and Approvals ---")
            document_seeder.seed(data['companies'], data['users'])

        # =====================================================================
        # Phase 7: 3D Models (depends on parts existing)
        # =====================================================================
        if '3d' in self.modules:
            self.stdout.write("\n--- Phase 7: 3D Models and Annotations ---")
            model_seeder.seed(data['part_types'], data['users'].get('employees', []))

        # =====================================================================
        # Phase 8: Training
        # =====================================================================
        if 'training' in self.modules:
            self.stdout.write("\n--- Phase 8: Training Records ---")
            training_seeder.seed(
                data['users'],
                steps=data['steps'],
                processes=None,  # Not linking to processes for now
                equipment_types=data['equipment_types']
            )

        # =====================================================================
        # Phase 9: Calibration
        # =====================================================================
        if 'calibration' in self.modules:
            self.stdout.write("\n--- Phase 9: Calibration Records ---")
            calibration_seeder.seed(data['equipment'])
            calibration_seeder.seed_overdue_alerts(data['equipment'])

        # =====================================================================
        # Final: External API identifiers and summary
        # =====================================================================
        self._create_external_api_identifiers(data['orders'], tenant)

        self.stdout.write(self.style.SUCCESS(f"\nGenerated realistic {self.scale} scale production data!"))
        self.show_data_summary()

    def _load_existing_users(self, tenant):
        """Load existing users into the expected structure."""
        users = {
            'customers': list(User.objects.filter(tenant=tenant, user_type='PORTAL')),
            'employees': list(User.objects.filter(tenant=tenant, user_type='INTERNAL')),
            'managers': [],
            'qa_staff': [],
        }

        # Separate managers and QA staff
        for user in users['employees']:
            if user.user_roles.filter(group__name__in=['Production Manager', 'Tenant Admin']).exists():
                users['managers'].append(user)
            if user.user_roles.filter(group__name__in=['QA Manager', 'QA Inspector']).exists():
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
            _, was_created = ExternalAPIOrderIdentifier.all_tenants.get_or_create(
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

    def clear_data(self):
        """Clear existing data in dependency order (most dependent first)."""
        self.stdout.write("Clearing existing data...")

        # Order matters - delete dependent models first
        models_to_clear = [
            # Audit/logging
            (LogEntry, "Audit log entries"),
            # Approval workflow
            (ApprovalResponse, "Approval responses"),
            (ApprovalRequest, "Approval requests"),
            # CAPA related
            (CapaVerification, "CAPA verifications"),
            (FiveWhys, "Five whys"),
            (Fishbone, "Fishbone diagrams"),
            (RcaRecord, "RCA records"),
            (CapaTaskAssignee, "CAPA task assignees"),
            (CapaTasks, "CAPA tasks"),
            (CAPA, "CAPAs"),
            # Training and calibration
            (TrainingRecord, "Training records"),
            (TrainingRequirement, "Training requirements"),
            (TrainingType, "Training types"),
            (CalibrationRecord, "Calibration records"),
            # Sampling
            (SamplingAnalytics, "Sampling analytics"),
            (SamplingAuditLog, "Sampling audit logs"),
            (SamplingTriggerState, "Sampling trigger states"),
            (SamplingRule, "Sampling rules"),
            (SamplingRuleSet, "Sampling rule sets"),
            # Quality
            (MeasurementResult, "Measurement results"),
            (MeasurementDefinition, "Measurement definitions"),
            (QaApproval, "QA approvals"),
            (QuarantineDisposition, "Quarantine dispositions"),
            (QualityReports, "Quality reports"),
            (QualityErrorsList, "Quality errors"),
            # 3D models and annotations
            (HeatMapAnnotations, "Heatmap annotations"),
            (ThreeDModel, "3D models"),
            # Work tracking
            (StepExecution, "Step executions"),
            (StepTransitionLog, "Step transition logs"),
            (EquipmentUsage, "Equipment usage"),
            # Life tracking models (before parts/cores they reference)
            (LifeTracking, "Life tracking records"),
            (PartTypeLifeLimit, "Part type life limits"),
            (LifeLimitDefinition, "Life limit definitions"),
            # Reman models (before WorkOrder and Parts)
            (HarvestedComponent, "Harvested components"),
            (Core, "Cores"),
            (DisassemblyBOMLine, "Disassembly BOM lines"),
            (WorkOrder, "Work orders"),
            # Parts and orders
            (Parts, "Parts"),
            (ExternalAPIOrderIdentifier, "External order identifiers"),
            (Orders, "Orders"),
            # Process graph
            (StepEdge, "Step edges"),
            (ProcessStep, "Process steps"),
            (Steps, "Steps"),
            (Processes, "Processes"),
            # Core entities
            (Documents, "Documents"),
            (ApprovalTemplate, "Approval templates"),
            (DocumentType, "Document types"),
            (Equipments, "Equipment"),
            (EquipmentType, "Equipment types"),
            (PartTypes, "Part types"),
            # Users (except superusers) and companies
            (User, "Users (non-superuser)"),
            (Companies, "Companies"),
            # Tenant (last - everything depends on it)
            (Tenant, "Tenants"),
        ]

        for model, name in models_to_clear:
            try:
                if model == User:
                    # Don't delete superusers
                    count = model.objects.filter(is_superuser=False).count()
                    model.objects.filter(is_superuser=False).delete()
                else:
                    mgr = getattr(model, 'all_tenants', model.objects)
                    count = mgr.count()
                    mgr.all().delete()
                if count > 0:
                    self.stdout.write(f"  Cleared {count} {name}")
            except Exception as e:
                # Use ASCII-safe error message to avoid Windows console encoding issues
                error_msg = str(e).encode('ascii', 'replace').decode('ascii')
                self.stdout.write(self.style.WARNING(f"  Could not clear {name}: {error_msg[:500]}"))

        self.stdout.write(self.style.SUCCESS("Data clearing complete"))

    def show_data_summary(self):
        """Show summary of created data."""
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("PRODUCTION DATA SUMMARY")
        self.stdout.write("=" * 50)

        summary_items = [
            ("Companies", Companies),
            ("Users", User),
            ("Part Types", PartTypes),
            ("Equipment", Equipments),
            ("Equipment Types", EquipmentType),
            ("Orders", Orders),
            ("Work Orders", WorkOrder),
            ("Parts", Parts),
            ("Cores", Core),
            ("Harvested Components", HarvestedComponent),
            ("Disassembly BOM Lines", DisassemblyBOMLine),
            ("Life Limit Definitions", LifeLimitDefinition),
            ("Part Type Life Limits", PartTypeLifeLimit),
            ("Life Tracking Records", LifeTracking),
            ("Quality Reports", QualityReports),
            ("Quarantine Dispositions", QuarantineDisposition),
            ("SPC Baselines", SPCBaseline),
            ("CAPAs", CAPA),
            ("CAPA Tasks", CapaTasks),
            ("RCA Records", RcaRecord),
            ("Documents", Documents),
            ("Approval Requests", ApprovalRequest),
            ("Training Types", TrainingType),
            ("Training Records", TrainingRecord),
            ("Calibration Records", CalibrationRecord),
            ("3D Models", ThreeDModel),
            ("Heatmap Annotations", HeatMapAnnotations),
            ("Step Executions", StepExecution),
            ("Step Transition Logs", StepTransitionLog),
            ("Equipment Usage", EquipmentUsage),
            ("Audit Log Entries", LogEntry),
        ]

        for name, model in summary_items:
            mgr = getattr(model, 'all_tenants', model.objects)
            count = mgr.count()
            if count > 0:
                self.stdout.write(f"{name}: {count}")

        self.stdout.write("\nOrder Status Distribution:")
        for status in OrdersStatus.choices:
            count = Orders.all_tenants.filter(order_status=status[0]).count()
            if count > 0:
                self.stdout.write(f"  {status[1]}: {count}")

        self.stdout.write("\nCAPA Status Distribution:")
        for status in ['OPEN', 'IN_PROGRESS', 'PENDING_VERIFICATION', 'CLOSED']:
            count = CAPA.all_tenants.filter(status=status).count()
            if count > 0:
                self.stdout.write(f"  {status}: {count}")

        # Core status distribution
        cores = Core.all_tenants.all()
        if cores.exists():
            self.stdout.write("\nCore Status Distribution:")
            for status, label in Core.CORE_STATUS_CHOICES:
                count = cores.filter(status=status).count()
                if count > 0:
                    self.stdout.write(f"  {label}: {count}")

        # Training status summary
        current = TrainingRecord.all_tenants.all()
        if current.exists():
            from django.utils import timezone
            from datetime import timedelta
            today = timezone.now().date()
            soon_threshold = today + timedelta(days=30)

            expired = sum(1 for r in current if r.expires_date and r.expires_date < today)
            expiring = sum(1 for r in current if r.expires_date and today <= r.expires_date <= soon_threshold)
            active = current.count() - expired - expiring

            self.stdout.write("\nTraining Status:")
            self.stdout.write(f"  Current: {active}")
            self.stdout.write(f"  Expiring Soon: {expiring}")
            self.stdout.write(f"  Expired: {expired}")

        # Calibration status summary
        cal_records = CalibrationRecord.all_tenants.all()
        if cal_records.exists():
            from django.utils import timezone
            from datetime import timedelta
            today = timezone.now().date()
            soon_threshold = today + timedelta(days=30)

            overdue = sum(1 for r in cal_records if r.due_date < today and r.result != 'FAIL')
            due_soon = sum(1 for r in cal_records if today <= r.due_date <= soon_threshold and r.result != 'FAIL')
            failed = sum(1 for r in cal_records if r.result == 'FAIL')

            self.stdout.write("\nCalibration Status:")
            self.stdout.write(f"  Current: {cal_records.count() - overdue - due_soon - failed}")
            self.stdout.write(f"  Due Soon: {due_soon}")
            self.stdout.write(f"  Overdue: {overdue}")
            self.stdout.write(f"  Failed: {failed}")

        self.stdout.write("=" * 50)

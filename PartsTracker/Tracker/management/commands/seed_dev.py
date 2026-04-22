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

from Tracker.utils.tenant_context import tenant_context

from Tracker.models import (
    # Core models
    Tenant, TenantGroupMembership, NotificationTask,
    Companies, User, PartTypes, Processes, Steps, Orders, Parts, Documents, Equipments,
    EquipmentType, WorkOrder, ExternalAPIOrderIdentifier,
    # Process graph models
    ProcessStep, StepEdge,
    # Quality models
    QualityErrorsList, QualityReports, QualityReportDefect, MeasurementDefinition, MeasurementResult,
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

        # Get the tenant if it exists — Tenant is not SecureModel, safe without context
        try:
            tenant = Tenant.objects.get(slug=self.TENANT_SLUG)
        except Tenant.DoesNotExist:
            self.stdout.write("  No existing dev tenant to clear")
            return

        with tenant_context(tenant.id):
            self._clear_tenant_data_inner(tenant)

    def _clear_tenant_data_inner(self, tenant):
        """Inner clear logic, called within an established tenant_context."""
        from django.db import connection

        tenant_id = str(tenant.id)

        # Helper to clear M2M tables via raw SQL (these block FK deletes)
        def clear_m2m_table(table_name, fk_column, source_table):
            """Clear M2M table entries related to tenant data."""
            try:
                with connection.cursor() as cursor:
                    cursor.execute(f'''
                        DELETE FROM "{table_name}"
                        WHERE {fk_column} IN (
                            SELECT id FROM "{source_table}" WHERE tenant_id = %s
                        )
                    ''', [tenant_id])
                    if cursor.rowcount > 0:
                        self.stdout.write(f"  Cleared {cursor.rowcount} {table_name} entries")
            except Exception as e:
                pass  # Table might not exist or have different structure

        # Clear M2M junction tables first (these block FK deletes on main tables)
        m2m_tables = [
            # CAPA M2M tables
            ('Tracker_capa_quality_reports', 'capa_id', 'Tracker_capa'),
            ('Tracker_rcarecord_quality_reports', 'rcarecord_id', 'Tracker_rcarecord'),
            # Quality report M2M tables
            ('Tracker_qualityreports_operators', 'qualityreports_id', 'Tracker_qualityreports'),
            # Quarantine disposition M2M tables (clear from both sides)
            ('Tracker_quarantinedisposition_quality_reports', 'quarantinedisposition_id', 'Tracker_quarantinedisposition'),
            ('Tracker_quarantinedisposition_quality_reports', 'qualityreports_id', 'Tracker_qualityreports'),
            # HeatMap annotation M2M tables
            ('Tracker_heatmapannotations_quality_reports', 'heatmapannotations_id', 'Tracker_heatmapannotations'),
            # Approver assignments
            ('tracker_approver_assignment', 'approval_request_id', 'Tracker_approvalrequest'),
            # User role assignments
            ('tracker_user_role', 'user_id', 'Tracker_user'),
        ]

        for table, fk_col, source in m2m_tables:
            clear_m2m_table(table, fk_col, source)

        # Clear records that reference tenant parts (via raw SQL in batches for speed)
        # These records would block ORM deletes due to FK constraints
        def clear_by_part_fk_batched(table_name, name):
            """Clear records that reference parts from this tenant in batches."""
            total_deleted = 0
            try:
                while True:
                    with connection.cursor() as cursor:
                        cursor.execute(f'''
                            DELETE FROM "{table_name}"
                            WHERE id IN (
                                SELECT t.id FROM "{table_name}" t
                                JOIN "Tracker_parts" p ON t.part_id = p.id
                                WHERE p.tenant_id = %s
                                LIMIT 5000
                            )
                        ''', [tenant_id])
                        if cursor.rowcount == 0:
                            break
                        total_deleted += cursor.rowcount
                if total_deleted > 0:
                    self.stdout.write(f"  Cleared {total_deleted} {name} (by part FK)")
            except Exception as e:
                if total_deleted > 0:
                    self.stdout.write(f"  Cleared {total_deleted} {name} (partial)")

        # Tables with part FK that may have NULL tenant - clear before Parts deletion
        clear_by_part_fk_batched("Tracker_steptransitionlog", "Step transition logs")
        clear_by_part_fk_batched("Tracker_stepexecution", "Step executions")
        clear_by_part_fk_batched("Tracker_samplingauditlog", "Sampling audit logs")

        # Clear tenant-scoped data in dependency order
        # Order matters: clear child tables before parent tables
        # FK constraints require children to be deleted before parents
        models_to_clear = [
            # Audit logs first (not tenant-scoped but references many models)
            (LogEntry, "Audit log entries", {}),
            # Approval workflow (has FK to many models)
            (ApprovalResponse, "Approval responses", {'tenant': tenant}),
            (ApprovalRequest, "Approval requests", {'tenant': tenant}),
            # CAPA hierarchy (deepest children first)
            (CapaVerification, "CAPA verifications", {'capa__tenant': tenant}),
            (FiveWhys, "Five whys", {'rca_record__capa__tenant': tenant}),
            (Fishbone, "Fishbone diagrams", {'rca_record__capa__tenant': tenant}),
            (RcaRecord, "RCA records", {'capa__tenant': tenant}),
            (CapaTaskAssignee, "CAPA task assignees", {'task__capa__tenant': tenant}),
            (CapaTasks, "CAPA tasks", {'capa__tenant': tenant}),
            (CAPA, "CAPAs", {'tenant': tenant}),
            # Training
            (TrainingRecord, "Training records", {'tenant': tenant}),
            (TrainingRequirement, "Training requirements", {'tenant': tenant}),
            (TrainingType, "Training types", {'tenant': tenant}),
            # Calibration
            (CalibrationRecord, "Calibration records", {'tenant': tenant}),
            # Quality: EquipmentUsage has FK to QualityReports, must go first
            (QualityReportDefect, "Quality report defects", {'report__tenant': tenant}),
            (MeasurementResult, "Measurement results", {'tenant': tenant}),
            (MeasurementDefinition, "Measurement definitions", {'tenant': tenant}),
            (QaApproval, "QA approvals", {'tenant': tenant}),
            (EquipmentUsage, "Equipment usage", {'tenant': tenant}),
            # QuarantineDisposition has PROTECT FK to Parts AND Steps - delete by multiple filters
            (QuarantineDisposition, "Quarantine dispositions (by tenant)", {'tenant': tenant}),
            (QuarantineDisposition, "Quarantine dispositions (by part)", {'part__tenant': tenant}),
            (QuarantineDisposition, "Quarantine dispositions (by step)", {'step__tenant': tenant}),
            (QualityReports, "Quality reports", {'tenant': tenant}),
            (QualityErrorsList, "Quality errors", {'tenant': tenant}),
            # 3D Models: HeatMapAnnotations before ThreeDModel (has FK)
            (HeatMapAnnotations, "Heatmap annotations", {'tenant': tenant}),
            (ThreeDModel, "3D models", {'tenant': tenant}),
            # Workflow execution: Records cleared via raw SQL above, this catches any remaining
            (StepExecution, "Step executions", {'tenant': tenant}),
            (StepTransitionLog, "Step transition logs", {'tenant': tenant}),
            (FPIRecord, "FPI records", {'tenant': tenant}),
            # Sampling: SamplingAuditLog cleared via raw SQL above
            (SamplingAnalytics, "Sampling analytics", {'ruleset__tenant': tenant}),
            (SamplingAuditLog, "Sampling audit logs", {'rule__ruleset__tenant': tenant}),
            (SamplingTriggerState, "Sampling trigger states", {'ruleset__tenant': tenant}),
            # Life tracking
            (LifeTracking, "Life tracking records", {'tenant': tenant}),
            (PartTypeLifeLimit, "Part type life limits", {'tenant': tenant}),
            (LifeLimitDefinition, "Life limit definitions", {'tenant': tenant}),
            # Reman
            (HarvestedComponent, "Harvested components", {'tenant': tenant}),
            (Core, "Cores", {'tenant': tenant}),
            (DisassemblyBOMLine, "Disassembly BOM lines", {'tenant': tenant}),
            # Parts/Orders: Parts has FK to SamplingRule, WorkOrder, Orders - delete Parts first
            # Then sampling can be deleted (Parts.sampling_rule FK is gone)
            (Parts, "Parts", {'tenant': tenant}),
            # Sampling: Now that Parts is gone, we can delete sampling models
            # SamplingRule has FK to SamplingRuleSet, so Rule before RuleSet
            (SamplingRule, "Sampling rules", {'ruleset__tenant': tenant}),
            (SamplingRuleSet, "Sampling rule sets", {'tenant': tenant}),
            # WorkOrder and Orders: Now that Parts is gone
            (WorkOrder, "Work orders", {'tenant': tenant}),
            (ExternalAPIOrderIdentifier, "External order identifiers", {'tenant': tenant}),
            (Orders, "Orders", {'tenant': tenant}),
            # SPC
            (SPCBaseline, "SPC baselines", {'tenant': tenant}),
            # Process graph: SamplingRuleSet has FK to Steps and Process, must delete sampling first
            (StepEdge, "Step edges", {'process__tenant': tenant}),
            (ProcessStep, "Process steps", {'process__tenant': tenant}),
            (Steps, "Steps", {'tenant': tenant}),
            (Processes, "Processes", {'tenant': tenant}),
            # Documents - has FK to User via approved_by
            (Documents, "Documents (by tenant)", {'tenant': tenant}),
            (Documents, "Documents (by approver)", {'approved_by__tenant': tenant}),
            (ApprovalTemplate, "Approval templates", {'tenant': tenant}),
            (DocumentType, "Document types", {'tenant': tenant}),
            # Equipment: QualityReports has FK to Equipment, must delete QR first (done above)
            (Equipments, "Equipment", {'tenant': tenant}),
            (EquipmentType, "Equipment types", {'tenant': tenant}),
            # Part types: Parts has FK to PartTypes, must delete Parts first (done above)
            (PartTypes, "Part types", {'tenant': tenant}),
            # Notifications (has FK to User)
            (NotificationTask, "Notification tasks", {'recipient__tenant': tenant}),
            # Users and companies last (referenced by many models)
            (TenantGroupMembership, "Tenant group memberships", {'user__tenant': tenant}),
            (User, "Users", {'tenant': tenant, 'is_superuser': False}),
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

        # Clear parent_company for admin users before deleting Companies
        # (admin users are preserved but their company reference blocks deletion)
        admin_users = User.objects.filter(tenant=tenant, is_superuser=True, parent_company__isnull=False)
        if admin_users.exists():
            admin_users.update(parent_company=None)
            self.stdout.write(f"  Cleared parent_company for {admin_users.count()} admin users")

        # Now delete Companies
        try:
            companies = Companies.objects.filter(tenant=tenant)
            count = companies.count()
            if count > 0:
                companies._raw_delete(companies.db)
                self.stdout.write(f"  Cleared {count} Companies")
        except Exception as e:
            error_msg = str(e).encode('ascii', 'replace').decode('ascii')
            self.stdout.write(self.style.WARNING(f"  Could not clear Companies: {error_msg[:200]}"))

        # Don't delete tenant - it has auto-seeded doc types/approval templates with protected FKs
        # The tenant will be reused with fresh data
        self.stdout.write(self.style.SUCCESS("  Dev tenant data cleared (tenant preserved for reuse)"))

    def _seed_dev_tenant(self):
        """Seed dev tenant with random Faker data."""
        # Initialize base seeder for shared operations
        # Tenant.objects is not SecureModel — safe without context
        base = BaseSeeder(self.stdout, self.style, scale=self.scale)
        tenant = base.create_or_get_tenant(slug=self.TENANT_SLUG, name=self.TENANT_NAME)

        with tenant_context(tenant.id):
            self._seed_dev_tenant_inner(tenant)

    def _seed_dev_tenant_inner(self, tenant):
        """Inner seed logic, called within an established tenant_context."""

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

        with tenant_context(tenant.id):
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

"""
Seed demo tenant with deterministic preset data.

Creates the exact data specified in DEMO_DATA_SYSTEM.md for:
- Sales demos with predictable scenarios
- User training with documented exercises
- Repeatable testing scenarios

Demo accounts (password: demo123):
- admin@demo.ambac.com (Alex Demo - Tenant Admin)
- maria.qa@demo.ambac.com (Maria Santos - QA Manager)
- sarah.qa@demo.ambac.com (Sarah Chen - QA Inspector)
- jennifer.mgr@demo.ambac.com (Jennifer Walsh - Production Manager)
- mike.ops@demo.ambac.com (Mike Rodriguez - Operator)
- dave.wilson@demo.ambac.com (Dave Wilson - Operator, expired training)
- lisa.docs@demo.ambac.com (Lisa Park - Document Controller)
- tom.bradley@midwestfleet.com (Tom Bradley - Customer)

Usage:
    # Default: seed demo tenant
    python manage.py seed_demo

    # Keep existing data
    python manage.py seed_demo --no-clear

    # Preview what would be created
    python manage.py seed_demo --dry-run
"""

from auditlog.models import LogEntry
from django.core.management.base import BaseCommand
from django.db import connection

from Tracker.utils.tenant_context import tenant_context

from Tracker.models import (
    # Core models
    Tenant, UserRole,
    Companies, User, PartTypes, Processes, Steps, Orders, Parts, Documents, Equipments,
    EquipmentType, WorkOrder, ExternalAPIOrderIdentifier,
    # Process graph models
    ProcessStep, StepEdge,
    # Quality models
    QualityErrorsList, QualityReports, MeasurementDefinition, MeasurementResult,
    QuarantineDisposition, QaApproval, StepTransitionLog, EquipmentUsage,
    QualityReportDefect,
    # Sampling models
    SamplingRuleSet, SamplingRule, SamplingTriggerState, SamplingAuditLog, SamplingAnalytics,
    # Workflow execution models
    StepExecution, StepExecutionMeasurement, StepRollback, BatchRollback,
    # FPI models
    FPIRecord,
    # CAPA models
    CAPA, CapaTasks, CapaTaskAssignee, RcaRecord, FiveWhys, Fishbone, CapaVerification,
    # Document models
    DocumentType, ApprovalTemplate, ApprovalRequest, ApprovalResponse,
    ApproverAssignment, GroupApproverAssignment,
    # 3D model and annotation models
    ThreeDModel, HeatMapAnnotations,
    # Training and Calibration
    TrainingType, TrainingRecord, TrainingRequirement, CalibrationRecord,
    # Notifications
    NotificationTask,
    # Reman models
    Core, HarvestedComponent, DisassemblyBOMLine,
    # SPC models
    SPCBaseline,
    # Life tracking models
    LifeLimitDefinition, PartTypeLifeLimit, LifeTracking,
    # Step measurement requirements
    StepMeasurementRequirement,
    # Order viewers
    OrderViewer,
    # DWI (work instructions)
    Substep, SubstepResource, SubstepTranslation,
    SubstepCompletion, SubstepGateCompletion, SubstepResponse,
)

from .seed import BaseSeeder


class Command(BaseCommand):
    help = "Seed demo tenant with deterministic preset data for demos and training"

    # Platform admin (never deleted)
    PLATFORM_ADMIN_EMAIL = 'admin@ambac.local'
    PLATFORM_ADMIN_PASSWORD = 'admin'

    # Tenant settings
    TENANT_SLUG = 'demo'
    TENANT_NAME = 'Demo Company'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-clear',
            action='store_true',
            help='Skip clearing existing data (by default, existing data is cleared)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually doing it',
        )
        parser.add_argument(
            '--scale',
            type=str,
            default='small',
            choices=['small', 'medium', 'large'],
            help='Scale of random data (for fallback seeders). Default: small',
        )

    def handle(self, *args, **options):
        self.no_clear = options['no_clear']
        self.dry_run = options['dry_run']
        self.scale = options['scale']
        self.verbose = options.get('verbosity', 1) >= 2

        self.stdout.write(f"\nSeed Demo - Deterministic preset data")
        self.stdout.write(f"  Clear existing: {not self.no_clear}")

        if self.dry_run:
            self._show_dry_run_plan()
            return

        # Ensure platform admin exists
        self._ensure_platform_admin()

        # Clear existing data unless --no-clear
        if not self.no_clear:
            self._clear_tenant_data()

        # Seed the demo tenant
        self._seed_demo_tenant()

        self.stdout.write(self.style.SUCCESS("\nDemo tenant seeded with deterministic data!"))
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
            self.stdout.write("  1. Clear existing demo tenant data")
        self.stdout.write(f"  2. Ensure platform admin: {self.PLATFORM_ADMIN_EMAIL}")
        self.stdout.write("  3. Create demo tenant with auto-seeded groups, doc types")
        self.stdout.write("\n  Demo Users (password: demo123):")
        self.stdout.write("    - admin@demo.ambac.com (Alex Demo - Tenant Admin)")
        self.stdout.write("    - maria.qa@demo.ambac.com (Maria Santos - QA Manager)")
        self.stdout.write("    - sarah.qa@demo.ambac.com (Sarah Chen - QA Inspector)")
        self.stdout.write("    - jennifer.mgr@demo.ambac.com (Jennifer Walsh - Production Manager)")
        self.stdout.write("    - mike.ops@demo.ambac.com (Mike Rodriguez - Operator)")
        self.stdout.write("    - dave.wilson@demo.ambac.com (Dave Wilson - Operator, expired training)")
        self.stdout.write("    - lisa.docs@demo.ambac.com (Lisa Park - Document Controller)")
        self.stdout.write("    - tom.bradley@midwestfleet.com (Tom Bradley - Customer)")
        self.stdout.write("\n  Demo Companies:")
        self.stdout.write("    - AMBAC International (internal)")
        self.stdout.write("    - Midwest Fleet Services (customer)")
        self.stdout.write("    - Great Lakes Diesel (customer)")
        self.stdout.write("    - Northern Trucking Co (customer)")
        self.stdout.write("\n  Demo Orders:")
        self.stdout.write("    - ORD-2024-0042 (Midwest Fleet, in progress)")
        self.stdout.write("    - ORD-2024-0038 (Great Lakes, completed)")
        self.stdout.write("    - ORD-2024-0048 (Northern Trucking, pending)")
        self.stdout.write("\n  Demo CAPAs:")
        self.stdout.write("    - CAPA-2024-003 (nozzle supplier issue, closed)")
        self.stdout.write("    - CAPA-2024-004 (field return investigation, open)")
        self.stdout.write("    - CAPA-2024-005 (calibration procedure, closed)")
        self.stdout.write("\n  Training Exercises:")
        self.stdout.write("    - TRAIN-001, TRAIN-FPI-001, TRAIN-PM-001 etc.")
        self.stdout.write("    - ASSESS-001, ASSESS-QA-001, ASSESS-PM-001 etc.")

    def _clear_tenant_data(self):
        """Clear existing demo tenant data in dependency order.

        This method handles complex FK relationships including M2M through tables.
        Order is critical - we must clear child tables before parent tables.
        """
        self.stdout.write(f"Clearing existing {self.TENANT_SLUG} tenant data...")

        try:
            tenant = Tenant.objects.get(slug=self.TENANT_SLUG)
        except Tenant.DoesNotExist:
            self.stdout.write("  No existing demo tenant to clear")
            return

        with tenant_context(tenant.id):
            self._clear_tenant_data_inner(tenant)

    def _clear_tenant_data_inner(self, tenant):
        """Wipe the tenant's DATA, preserving auto-provisioned tenant config.

        FK enforcement is disabled for the wipe (`session_replication_role =
        'replica'`), so deletion is order-independent — version self-FK chains
        (Processes/Steps/ApprovalTemplate) and the dense cross-table FK web
        (change-control, batch, material, notifications, …) no longer block it.
        A generic sweep covers every tenant-scoped model automatically, so new
        models can't silently accumulate; non-tenant child tables are cleared by
        join to a tenant-scoped parent. Runs inside an established tenant_context.
        """
        from django.apps import apps
        from django.db import connection, transaction
        from Tracker import models as TM

        tid = str(tenant.id)

        # Auto-provisioned tenant config (created by the tenant-creation signal,
        # NOT recreated by seed_demo) — must survive a data wipe.
        PRESERVE = {
            'Tenant', 'TenantGroup', 'TenantLLMProvider',
            'TenantNotificationBranding', 'TenantNotificationDefault',
            'NotificationTemplate', 'NotificationRule', 'NotificationSchedule',
            'EscalationPolicy', 'EscalationStep', 'ArtifactSequence',
            'IntegrationConfig', 'Facility', 'Shift', 'WorkCenter',
        }

        # Non-tenant child tables, cleared by join to a tenant-scoped parent.
        child_joins = [
            ('ProcessStep', {'process__tenant': tenant}),
            ('StepEdge', {'process__tenant': tenant}),
            ('StepMeasurementRequirement', {'step__tenant': tenant}),
            ('QualityReportDefect', {'report__tenant': tenant}),
            ('QualityReportPersonnel', {'quality_report__tenant': tenant}),
            ('QualityReportEquipment', {'quality_report__tenant': tenant}),
            ('OrderViewer', {'order__tenant': tenant}),
            ('ApproverAssignment', {'approval_request__tenant': tenant}),
            ('GroupApproverAssignment', {'approval_request__tenant': tenant}),
            ('UserRole', {'user__tenant': tenant}),
            ('UserInvitation', {'user__tenant': tenant}),
            ('DocChunk', {'doc__tenant': tenant}),
            ('HubSpotOrderLink', {'order__tenant': tenant}),
            ('HubSpotCompanyLink', {'company__tenant': tenant}),
        ]

        tenant_models = [
            m for m in apps.get_models()
            if m._meta.app_label in ('Tracker', 'integrations')
            and any(f.name == 'tenant' for f in m._meta.local_fields)
            and m._meta.object_name not in PRESERVE
        ]

        def _sql(sql, params, label):
            # Own savepoint so one failed delete can't poison the rest.
            try:
                with transaction.atomic():
                    with connection.cursor() as cur:
                        cur.execute(sql, params)
                        rc = cur.rowcount
                if rc:
                    self.stdout.write(f"  Cleared {rc} {label}")
            except Exception as e:
                msg = str(e).encode('ascii', 'replace').decode('ascii')[:160]
                self.stdout.write(self.style.WARNING(f"  Could not clear {label}: {msg}"))

        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute("SET session_replication_role = 'replica';")
            try:
                # 1) M2M through-tables (need parent ids → before the sweep).
                for m in tenant_models:
                    for f in m._meta.local_many_to_many:
                        through = f.remote_field.through._meta.db_table
                        src = f.m2m_column_name()
                        _sql(
                            f'DELETE FROM "{through}" WHERE "{src}" IN '
                            f'(SELECT id FROM "{m._meta.db_table}" WHERE tenant_id=%s)',
                            [tid], through,
                        )
                # 2) Non-tenant children, by join (parents still present).
                for name, flt in child_joins:
                    Model = getattr(TM, name, None)
                    if Model is None:
                        continue
                    n = 0
                    try:
                        with transaction.atomic():
                            qs = Model.objects.filter(**flt)
                            n = qs.count()
                            if n:
                                qs._raw_delete(qs.db)
                        if n:
                            self.stdout.write(f"  Cleared {n} {name}")
                    except Exception as e:
                        msg = str(e).encode('ascii', 'replace').decode('ascii')[:160]
                        self.stdout.write(self.style.WARNING(f"  Could not clear {name}: {msg}"))
                # 3) Generic tenant-scoped sweep (data only; config preserved).
                for m in tenant_models:
                    _sql(f'DELETE FROM "{m._meta.db_table}" WHERE tenant_id=%s', [tid], m._meta.object_name)
                # 4) Audit log (not tenant-scoped).
                _sql('DELETE FROM "auditlog_logentry";', [], "audit log entries")
                # 5) Null dangling FKs on preserved config that pointed at the
                #    now-deleted demo users/companies.
                for tbl in ('Tracker_notificationrule', 'Tracker_notificationschedule'):
                    for col in ('created_by_id', 'company_id'):
                        try:
                            with transaction.atomic():
                                with connection.cursor() as cur:
                                    cur.execute(f'UPDATE "{tbl}" SET "{col}"=NULL WHERE tenant_id=%s', [tid])
                        except Exception:
                            pass
            finally:
                with connection.cursor() as cur:
                    cur.execute("SET session_replication_role = 'origin';")

        self.stdout.write(self.style.SUCCESS("  Demo tenant data cleared (config preserved)"))

    def _seed_demo_tenant(self):
        """Seed demo tenant with deterministic preset data."""
        from .seed.demo import DemoScenario

        # Initialize base seeder for tenant creation
        # Tenant.objects is not SecureModel — safe without context
        base = BaseSeeder(self.stdout, self.style, scale=self.scale)
        tenant = base.create_or_get_tenant(slug=self.TENANT_SLUG, name=self.TENANT_NAME)

        with tenant_context(tenant.id):
            scenario = DemoScenario(self.stdout, self.style, tenant=tenant, scale=self.scale)
            scenario.verbose = self.verbose
            scenario.seed()

    def _show_data_summary(self):
        """Show summary of created demo data."""
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("DEMO TENANT DATA SUMMARY")
        self.stdout.write("=" * 50)

        try:
            tenant = Tenant.objects.get(slug=self.TENANT_SLUG)
        except Tenant.DoesNotExist:
            self.stdout.write("  No demo tenant found")
            return

        with tenant_context(tenant.id):
            # Demo users (User is not SecureModel, but keep inside context for consistency)
            self.stdout.write("\nDemo Users:")
            demo_emails = [
                'admin@demo.ambac.com',
                'maria.qa@demo.ambac.com',
                'sarah.qa@demo.ambac.com',
                'jennifer.mgr@demo.ambac.com',
                'mike.ops@demo.ambac.com',
                'dave.wilson@demo.ambac.com',
                'lisa.docs@demo.ambac.com',
                'tom.bradley@midwestfleet.com',
            ]
            for email in demo_emails:
                exists = User.objects.filter(email=email).exists()
                status = "OK" if exists else "MISSING"
                self.stdout.write(f"  {email}: {status}")

            # Data counts
            self.stdout.write("\nData Counts:")
            summary_items = [
                ("Companies", Companies.objects.filter(tenant=tenant).count()),
                ("Users", User.objects.filter(tenant=tenant).count()),
                ("Part Types", PartTypes.objects.filter(tenant=tenant).count()),
                ("Equipment", Equipments.objects.filter(tenant=tenant).count()),
                ("Orders", Orders.objects.filter(tenant=tenant).count()),
                ("Work Orders", WorkOrder.objects.filter(tenant=tenant).count()),
                ("Parts", Parts.objects.filter(tenant=tenant).count()),
                ("Step Executions", StepExecution.objects.filter(tenant=tenant).count()),
                ("Step Transitions", StepTransitionLog.objects.filter(tenant=tenant).count()),
                ("Equipment Usage", EquipmentUsage.objects.filter(tenant=tenant).count()),
                ("Quality Reports", QualityReports.objects.filter(tenant=tenant).count()),
                ("Dispositions", QuarantineDisposition.objects.filter(part__tenant=tenant).count()),
                ("CAPAs", CAPA.objects.filter(tenant=tenant).count()),
                ("Documents", Documents.objects.filter(tenant=tenant).count()),
                ("Training Records", TrainingRecord.objects.filter(user__tenant=tenant).count()),
            ]

            for name, count in summary_items:
                self.stdout.write(f"  {name}: {count}")

            # Check for key demo data
            self.stdout.write("\nKey Demo Records:")
            key_orders = ['ORD-2024-0042', 'ORD-2024-0038', 'ORD-2024-0048']
            for order_num in key_orders:
                exists = Orders.objects.filter(tenant=tenant, order_number=order_num).exists()
                status = "OK" if exists else "MISSING"
                self.stdout.write(f"  {order_num}: {status}")

            key_capas = ['CAPA-2024-003', 'CAPA-2024-004', 'CAPA-2024-005']
            for capa_num in key_capas:
                exists = CAPA.objects.filter(tenant=tenant, capa_number=capa_num).exists()
                status = "OK" if exists else "MISSING"
                self.stdout.write(f"  {capa_num}: {status}")

        self.stdout.write("=" * 50)

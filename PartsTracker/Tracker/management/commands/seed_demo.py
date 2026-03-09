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

from Tracker.models import (
    # Core models
    Tenant, TenantGroupMembership, UserRole,
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

        # Helper to safely delete a queryset
        def safe_delete(qs, name):
            try:
                count = qs.count()
                if count == 0:
                    return 0
                # Use _raw_delete to bypass soft-delete behavior
                if hasattr(qs, '_raw_delete'):
                    qs._raw_delete(qs.db)
                else:
                    qs.delete()
                self.stdout.write(f"  Cleared {count} {name}")
                return count
            except Exception as e:
                error_msg = str(e).encode('ascii', 'replace').decode('ascii')
                self.stdout.write(self.style.WARNING(f"  Could not clear {name}: {error_msg[:200]}"))
                return 0

        # Helper to clear M2M through tables via raw SQL using subquery
        # This ensures we catch ALL records, not just ones that exist at query time
        def clear_m2m_table_subquery(table_name, fk_column, parent_table, parent_tenant_column='tenant_id'):
            """Clear M2M table entries where parent record belongs to this tenant."""
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        f'''DELETE FROM "{table_name}"
                            WHERE "{fk_column}" IN (
                                SELECT id FROM "{parent_table}" WHERE "{parent_tenant_column}" = %s
                            )''',
                        [str(tenant.id)]
                    )
                    count = cursor.rowcount
                    if count > 0:
                        self.stdout.write(f"  Cleared {count} {table_name} entries")
                    return count
            except Exception as e:
                error_msg = str(e).encode('ascii', 'replace').decode('ascii')
                self.stdout.write(self.style.WARNING(f"  Could not clear {table_name}: {error_msg[:100]}"))
                return 0

        # Helper to clear M2M through tables via raw SQL (for auto-generated tables)
        def clear_m2m_table(table_name, fk_column, ids):
            if not ids:
                return 0
            try:
                with connection.cursor() as cursor:
                    # Use parameterized query with IN clause
                    placeholders = ','.join(['%s'] * len(ids))
                    cursor.execute(
                        f'DELETE FROM "{table_name}" WHERE "{fk_column}" IN ({placeholders})',
                        list(ids)
                    )
                    count = cursor.rowcount
                    if count > 0:
                        self.stdout.write(f"  Cleared {count} {table_name} entries")
                    return count
            except Exception as e:
                error_msg = str(e).encode('ascii', 'replace').decode('ascii')
                self.stdout.write(self.style.WARNING(f"  Could not clear {table_name}: {error_msg[:100]}"))
                return 0

        # Helper to convert UUIDs to strings for SQL
        def ids_to_str(ids):
            return [str(id) for id in ids]

        # Get IDs for M2M clearing
        demo_users = User.objects.filter(tenant=tenant)
        demo_user_ids = list(demo_users.values_list('id', flat=True))

        # First, clean up orphaned records with NULL tenant that reference demo users
        safe_delete(
            QuarantineDisposition.objects.filter(tenant__isnull=True, assigned_to__in=demo_users),
            "orphaned QuarantineDispositions"
        )
        safe_delete(
            QualityReports.objects.filter(tenant__isnull=True, detected_by__in=demo_users),
            "orphaned QualityReports"
        )
        safe_delete(
            QaApproval.objects.filter(tenant__isnull=True, qa_staff__in=demo_users),
            "orphaned QaApprovals"
        )

        # Clear audit logs (not tenant-scoped)
        safe_delete(LogEntry.objects.all(), "Audit log entries")

        # =====================================================================
        # PHASE 1: Clear M2M through tables and junction tables FIRST
        # These block deletion of their parent models
        # =====================================================================

        # Approval M2M tables (use subquery approach)
        safe_delete(ApproverAssignment.objects.filter(approval_request__tenant=tenant), "Approver assignments")
        safe_delete(GroupApproverAssignment.objects.filter(approval_request__tenant=tenant), "Group approver assignments")

        # CAPA M2M tables (use subquery to catch all records)
        clear_m2m_table_subquery('Tracker_capa_quality_reports', 'capa_id', 'Tracker_capa')
        clear_m2m_table_subquery('Tracker_capa_dispositions', 'capa_id', 'Tracker_capa')

        # RCA M2M tables - RcaRecord doesn't have direct tenant, so use CAPA join
        # For now, use the ID list approach but with fresh IDs
        rca_record_ids = list(RcaRecord.objects.filter(capa__tenant=tenant).values_list('id', flat=True))
        clear_m2m_table('Tracker_rcarecord_quality_reports', 'rcarecord_id', ids_to_str(rca_record_ids))
        clear_m2m_table('Tracker_rcarecord_dispositions', 'rcarecord_id', ids_to_str(rca_record_ids))

        # Quality M2M tables (use subquery to catch all records)
        safe_delete(QualityReportDefect.objects.filter(report__tenant=tenant), "Quality report defects")
        clear_m2m_table_subquery('Tracker_qualityreports_operators', 'qualityreports_id', 'Tracker_qualityreports')

        # Disposition M2M tables (clear by both disposition and quality_report sides)
        clear_m2m_table_subquery('Tracker_quarantinedisposition_quality_reports', 'quarantinedisposition_id', 'Tracker_quarantinedisposition')
        clear_m2m_table_subquery('Tracker_quarantinedisposition_quality_reports', 'qualityreports_id', 'Tracker_qualityreports')

        # HeatMap M2M tables (use subquery)
        clear_m2m_table_subquery('Tracker_heatmapannotations_quality_reports', 'heatmapannotations_id', 'Tracker_heatmapannotations')

        # Sampling M2M tables (use subquery)
        clear_m2m_table_subquery('Tracker_samplingtriggerstate_parts_inspected', 'samplingtriggerstate_id', 'Tracker_samplingtriggerstate')
        clear_m2m_table_subquery('Tracker_samplingtriggerstate_notified_users', 'samplingtriggerstate_id', 'Tracker_samplingtriggerstate')

        # Step M2M tables (use subquery)
        safe_delete(StepMeasurementRequirement.objects.filter(step__tenant=tenant), "Step measurement requirements")
        clear_m2m_table_subquery('Tracker_steps_notification_users', 'steps_id', 'Tracker_steps')

        # Order M2M tables (use subquery)
        safe_delete(OrderViewer.objects.filter(order__tenant=tenant), "Order viewers")

        # BatchRollback M2M tables (use subquery)
        clear_m2m_table_subquery('Tracker_batchrollback_affected_parts', 'batchrollback_id', 'Tracker_batchrollback')
        clear_m2m_table_subquery('Tracker_batchrollback_individual_rollbacks', 'batchrollback_id', 'Tracker_batchrollback')

        # Tenant group memberships (before users)
        safe_delete(TenantGroupMembership.objects.filter(user__tenant=tenant), "Tenant group memberships")

        # =====================================================================
        # PHASE 2: Clear models in proper dependency order
        # =====================================================================

        # Approval workflow (now that M2M tables are cleared)
        safe_delete(ApprovalResponse.objects.filter(tenant=tenant), "Approval responses")
        safe_delete(ApprovalRequest.objects.filter(tenant=tenant), "Approval requests")

        # CAPA hierarchy (deepest first)
        safe_delete(CapaVerification.objects.filter(capa__tenant=tenant), "CAPA verifications")
        safe_delete(FiveWhys.objects.filter(rca_record__capa__tenant=tenant), "Five whys")
        safe_delete(Fishbone.objects.filter(rca_record__capa__tenant=tenant), "Fishbone diagrams")
        safe_delete(RcaRecord.objects.filter(capa__tenant=tenant), "RCA records")
        safe_delete(CapaTaskAssignee.objects.filter(task__capa__tenant=tenant), "CAPA task assignees")
        safe_delete(CapaTasks.objects.filter(capa__tenant=tenant), "CAPA tasks")
        safe_delete(CAPA.objects.filter(tenant=tenant), "CAPAs")

        # Training and calibration
        safe_delete(TrainingRecord.objects.filter(tenant=tenant), "Training records")
        safe_delete(TrainingRequirement.objects.filter(tenant=tenant), "Training requirements")
        safe_delete(TrainingType.objects.filter(tenant=tenant), "Training types")
        safe_delete(CalibrationRecord.objects.filter(tenant=tenant), "Calibration records")

        # Quality (measurement results before definitions)
        # Also clear NULL tenant measurement results that reference demo definitions
        safe_delete(MeasurementResult.objects.filter(tenant=tenant), "Measurement results (tenant)")
        safe_delete(MeasurementResult.objects.filter(definition__tenant=tenant), "Measurement results (by definition)")
        safe_delete(StepExecutionMeasurement.objects.filter(step_execution__tenant=tenant), "Step execution measurements")
        safe_delete(QaApproval.objects.filter(tenant=tenant), "QA approvals")
        # Also clear NULL tenant dispositions that reference demo quality reports through M2M
        safe_delete(QuarantineDisposition.objects.filter(tenant=tenant), "Quarantine dispositions (tenant)")
        safe_delete(QuarantineDisposition.objects.filter(quality_reports__tenant=tenant), "Quarantine dispositions (by QR)")
        safe_delete(QualityReports.objects.filter(tenant=tenant), "Quality reports")
        safe_delete(QualityErrorsList.objects.filter(tenant=tenant), "Quality errors")

        # 3D models (annotations before models)
        safe_delete(HeatMapAnnotations.objects.filter(tenant=tenant), "Heatmap annotations")
        safe_delete(ThreeDModel.objects.filter(tenant=tenant), "3D models")

        # Work tracking (MUST clear before Parts - also clear NULL tenant records)
        safe_delete(StepRollback.objects.filter(tenant=tenant), "Step rollbacks (tenant)")
        safe_delete(StepRollback.objects.filter(part__tenant=tenant), "Step rollbacks (by part)")
        safe_delete(BatchRollback.objects.filter(tenant=tenant), "Batch rollbacks")
        safe_delete(StepExecution.objects.filter(tenant=tenant), "Step executions (tenant)")
        safe_delete(StepExecution.objects.filter(part__tenant=tenant), "Step executions (by part)")
        safe_delete(StepTransitionLog.objects.filter(tenant=tenant), "Step transition logs (tenant)")
        safe_delete(StepTransitionLog.objects.filter(part__tenant=tenant), "Step transition logs (by part)")
        safe_delete(EquipmentUsage.objects.filter(tenant=tenant), "Equipment usage (tenant)")
        safe_delete(EquipmentUsage.objects.filter(part__tenant=tenant), "Equipment usage (by part)")

        # FPI records
        safe_delete(FPIRecord.objects.filter(tenant=tenant), "FPI records")
        safe_delete(FPIRecord.objects.filter(designated_part__tenant=tenant), "FPI records (by part)")

        # Life tracking
        safe_delete(LifeTracking.objects.filter(tenant=tenant), "Life tracking records")
        safe_delete(PartTypeLifeLimit.objects.filter(tenant=tenant), "Part type life limits")
        safe_delete(LifeLimitDefinition.objects.filter(tenant=tenant), "Life limit definitions")

        # Reman
        safe_delete(HarvestedComponent.objects.filter(tenant=tenant), "Harvested components")
        safe_delete(Core.objects.filter(tenant=tenant), "Cores")
        safe_delete(DisassemblyBOMLine.objects.filter(tenant=tenant), "Disassembly BOM lines")

        # Parts and work orders (MUST clear before SamplingRule)
        safe_delete(Parts.objects.filter(tenant=tenant), "Parts")
        safe_delete(WorkOrder.objects.filter(tenant=tenant), "Work orders")

        # Orders (after parts)
        safe_delete(ExternalAPIOrderIdentifier.objects.filter(tenant=tenant), "External order identifiers")
        safe_delete(Orders.objects.filter(tenant=tenant), "Orders")

        # Sampling (AFTER Parts - Parts has FK to SamplingRule)
        # Note: Some records may have NULL tenant but reference demo objects - clear by FK too
        safe_delete(SamplingAnalytics.objects.filter(tenant=tenant), "Sampling analytics")
        safe_delete(SamplingAuditLog.objects.filter(tenant=tenant), "Sampling audit logs (tenant)")
        safe_delete(SamplingAuditLog.objects.filter(rule__tenant=tenant), "Sampling audit logs (by rule)")
        safe_delete(SamplingAuditLog.objects.filter(rule__ruleset__tenant=tenant), "Sampling audit logs (by ruleset)")
        safe_delete(SamplingTriggerState.objects.filter(tenant=tenant), "Sampling trigger states")
        safe_delete(SamplingRule.objects.filter(tenant=tenant), "Sampling rules (tenant)")
        safe_delete(SamplingRule.objects.filter(ruleset__tenant=tenant), "Sampling rules (by ruleset)")
        safe_delete(SamplingRuleSet.objects.filter(tenant=tenant), "Sampling rule sets")

        # Measurement definitions (after sampling rules which might reference them)
        safe_delete(MeasurementDefinition.objects.filter(tenant=tenant), "Measurement definitions")

        # SPC baselines
        safe_delete(SPCBaseline.objects.filter(tenant=tenant), "SPC baselines")

        # Process graph (edges before steps, steps before processes)
        safe_delete(StepEdge.objects.filter(process__tenant=tenant), "Step edges")
        safe_delete(ProcessStep.objects.filter(process__tenant=tenant), "Process steps")
        safe_delete(Steps.objects.filter(tenant=tenant), "Steps")
        safe_delete(Processes.objects.filter(tenant=tenant), "Processes")

        # Documents
        safe_delete(Documents.objects.filter(tenant=tenant), "Documents")
        safe_delete(ApprovalTemplate.objects.filter(tenant=tenant), "Approval templates")
        safe_delete(DocumentType.objects.filter(tenant=tenant), "Document types")

        # Equipment
        safe_delete(Equipments.objects.filter(tenant=tenant), "Equipment")
        safe_delete(EquipmentType.objects.filter(tenant=tenant), "Equipment types")

        # Part types
        safe_delete(PartTypes.objects.filter(tenant=tenant), "Part types")

        # Users and companies (last, as many things reference them)
        # User roles and notifications (must clear before Users)
        safe_delete(NotificationTask.objects.filter(recipient__tenant=tenant), "Notification tasks")
        safe_delete(UserRole.objects.filter(user__tenant=tenant), "User roles")
        safe_delete(User.objects.filter(tenant=tenant, is_superuser=False), "Users")
        safe_delete(Companies.objects.filter(tenant=tenant), "Companies")

        # Don't delete tenant - it has auto-seeded doc types/approval templates with protected FKs
        # The tenant will be reused with fresh data
        self.stdout.write(self.style.SUCCESS("  Demo tenant data cleared (tenant preserved for reuse)"))

    def _seed_demo_tenant(self):
        """Seed demo tenant with deterministic preset data."""
        from .seed.demo import DemoScenario

        # Initialize base seeder for tenant creation
        base = BaseSeeder(self.stdout, self.style, scale=self.scale)

        # Create or get demo tenant
        tenant = base.create_or_get_tenant(slug=self.TENANT_SLUG, name=self.TENANT_NAME)

        # Run demo scenario
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

        # Demo users
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

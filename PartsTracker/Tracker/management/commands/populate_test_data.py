"""
Generate realistic production data for diesel fuel injector remanufacturing business.

This command orchestrates the modular seed system to create comprehensive demo data.
Each domain is handled by a specialized seeder module in the `seed/` package.

Usage:
    python manage.py populate_test_data
    python manage.py populate_test_data --scale small
    python manage.py populate_test_data --scale large --clear-existing
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
    # CAPA models
    CAPA, CapaTasks, RcaRecord, FiveWhys, Fishbone, CapaVerification,
    # Document models
    DocumentType, ApprovalTemplate, ApprovalRequest, ApprovalResponse,
    # 3D model and annotation models
    ThreeDModel, HeatMapAnnotations,
    # Training and Calibration
    TrainingType, TrainingRecord, TrainingRequirement, CalibrationRecord,
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
)


class Command(BaseCommand):
    help = "Generate realistic production data for diesel fuel injector remanufacturing business"

    def add_arguments(self, parser):
        parser.add_argument(
            '--scale',
            type=str,
            default='medium',
            choices=['small', 'medium', 'large'],
            help='Scale of data generation (small=10 orders, medium=50 orders, large=200 orders)',
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing data before generating new data',
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
            choices=['users', 'manufacturing', 'orders', 'quality', 'capa', 'documents', '3d', 'training', 'calibration', 'all'],
            default=['all'],
            help='Specific modules to run (default: all)',
        )

    def handle(self, *args, **options):
        self.scale = options['scale']
        self.clear_existing = options['clear_existing']
        self.skip_historical = options['skip_historical']
        self.modules = set(options['modules'])

        if 'all' in self.modules:
            self.modules = {'users', 'manufacturing', 'orders', 'quality', 'capa', 'documents', '3d', 'training', 'calibration'}

        self.stdout.write(f"Generating {self.scale} scale realistic production data...")
        self.stdout.write(f"  Modules: {', '.join(sorted(self.modules))}")

        if self.clear_existing:
            self.clear_data()

        # Initialize base seeder for shared operations
        base = BaseSeeder(self.stdout, self.style, scale=self.scale)

        # Create or get tenant
        tenant = base.create_or_get_tenant()

        # Initialize all seeders with shared tenant and scale
        user_seeder = UserSeeder(self.stdout, self.style, tenant=tenant, scale=self.scale)
        manufacturing_seeder = ManufacturingSeeder(self.stdout, self.style, tenant=tenant, scale=self.scale)
        order_seeder = OrderSeeder(self.stdout, self.style, tenant=tenant, scale=self.scale)
        quality_seeder = QualitySeeder(self.stdout, self.style, tenant=tenant, scale=self.scale)
        capa_seeder = CapaSeeder(self.stdout, self.style, tenant=tenant, scale=self.scale)
        document_seeder = DocumentSeeder(self.stdout, self.style, tenant=tenant, scale=self.scale)
        model_seeder = ThreeDModelSeeder(self.stdout, self.style, tenant=tenant, scale=self.scale)
        training_seeder = TrainingSeeder(self.stdout, self.style, tenant=tenant, scale=self.scale)
        calibration_seeder = CalibrationSeeder(self.stdout, self.style, tenant=tenant, scale=self.scale)

        # Cross-link seeders that need each other's data
        order_seeder.manufacturing_seeder = manufacturing_seeder
        quality_seeder.manufacturing_seeder = manufacturing_seeder

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
            data['companies'] = list(Companies.objects.filter(tenant=tenant))
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
            data['steps'] = list(Steps.objects.filter(tenant=tenant))
        else:
            data['part_types'] = list(PartTypes.objects.filter(tenant=tenant))
            data['equipment'] = list(Equipments.objects.filter(tenant=tenant))
            data['equipment_types'] = list(EquipmentType.objects.filter(tenant=tenant))
            data['steps'] = list(Steps.objects.filter(tenant=tenant))

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
            data['orders'] = list(Orders.objects.filter(tenant=tenant))

        # =====================================================================
        # Phase 4: Quality Data
        # =====================================================================
        if 'quality' in self.modules:
            self.stdout.write("\n--- Phase 4: Quality Reports ---")
            quality_seeder.seed(data['orders'], data['users'], data['equipment'])

            if not self.skip_historical:
                self.stdout.write("  Creating historical FPY trend data...")
                quality_seeder.seed_historical_fpy(data['part_types'], data['users'], data['equipment'])

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
            'customers': list(User.objects.filter(tenant=tenant, user_type='portal')),
            'employees': list(User.objects.filter(tenant=tenant, user_type='internal')),
            'managers': [],
            'qa_staff': [],
        }

        # Separate managers and QA staff
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

    def clear_data(self):
        """Clear existing data in dependency order (most dependent first)."""
        self.stdout.write("Clearing existing data...")

        # Order matters - delete dependent models first
        models_to_clear = [
            # Tenant group memberships (before users)
            (TenantGroupMembership, "Tenant group memberships"),
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
            (StepTransitionLog, "Step transition logs"),
            (EquipmentUsage, "Equipment usage"),
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
                    count = model.objects.count()
                    model.objects.all().delete()
                if count > 0:
                    self.stdout.write(f"  Cleared {count} {name}")
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  Could not clear {name}: {e}"))

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
            ("Quality Reports", QualityReports),
            ("Quarantine Dispositions", QuarantineDisposition),
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
            ("Step Transition Logs", StepTransitionLog),
            ("Equipment Usage", EquipmentUsage),
            ("Audit Log Entries", LogEntry),
        ]

        for name, model in summary_items:
            count = model.objects.count()
            if count > 0:
                self.stdout.write(f"{name}: {count}")

        self.stdout.write("\nOrder Status Distribution:")
        for status in OrdersStatus.choices:
            count = Orders.objects.filter(order_status=status[0]).count()
            if count > 0:
                self.stdout.write(f"  {status[1]}: {count}")

        self.stdout.write("\nCAPA Status Distribution:")
        for status in ['OPEN', 'IN_PROGRESS', 'PENDING_VERIFICATION', 'CLOSED']:
            count = CAPA.objects.filter(status=status).count()
            if count > 0:
                self.stdout.write(f"  {status}: {count}")

        # Training status summary
        current = TrainingRecord.objects.all()
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
        cal_records = CalibrationRecord.objects.all()
        if cal_records.exists():
            from django.utils import timezone
            from datetime import timedelta
            today = timezone.now().date()
            soon_threshold = today + timedelta(days=30)

            overdue = sum(1 for r in cal_records if r.due_date < today and r.result != 'fail')
            due_soon = sum(1 for r in cal_records if today <= r.due_date <= soon_threshold and r.result != 'fail')
            failed = sum(1 for r in cal_records if r.result == 'fail')

            self.stdout.write("\nCalibration Status:")
            self.stdout.write(f"  Current: {cal_records.count() - overdue - due_soon - failed}")
            self.stdout.write(f"  Due Soon: {due_soon}")
            self.stdout.write(f"  Overdue: {overdue}")
            self.stdout.write(f"  Failed: {failed}")

        self.stdout.write("=" * 50)

import json
import random
from datetime import timedelta, datetime

from auditlog.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker

from Tracker.models import (
    # Core models
    Tenant, TenantGroupMembership, TenantGroup,
    Companies, User, PartTypes, Processes, Steps, Orders, Parts, Documents, Equipments,
    EquipmentType, WorkOrder, ExternalAPIOrderIdentifier,
    # Process graph models
    ProcessStep, StepEdge, EdgeType,
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
    # Enums
    PartsStatus, OrdersStatus, WorkOrderStatus, ClassificationLevel,
    Approval_Type, Approval_Status_Type, ApprovalFlows, ApprovalDecision,
)


class Command(BaseCommand):
    help = "Generate realistic production data for diesel fuel injector remanufacturing business"

    def add_arguments(self, parser):
        parser.add_argument('--scale', type=str, default='medium', choices=['small', 'medium', 'large'],
            help='Scale of data generation (small=10 orders, medium=50 orders, large=200 orders)', )
        parser.add_argument('--clear-existing', action='store_true',
            help='Clear existing data before generating new data', )

    def handle(self, *args, **options):
        self.fake = Faker()
        self.scale = options['scale']
        self.clear_existing = options['clear_existing']

        # Scale configurations
        self.scale_config = {'small': {'orders': 10, 'customers': 5, 'employees': 8, 'parts_per_order': (5, 15)},
            'medium': {'orders': 50, 'customers': 15, 'employees': 25, 'parts_per_order': (10, 30)},
            'large': {'orders': 200, 'customers': 40, 'employees': 50, 'parts_per_order': (15, 50)}}

        config = self.scale_config[self.scale]

        self.stdout.write(f"Generating {self.scale} scale realistic production data...")

        if self.clear_existing:
            self.clear_data()

        # Verify groups exist (auto-created via post_migrate signal)
        self.verify_groups_exist()

        # Create or get tenant (AMBAC Manufacturing is the tenant)
        self.tenant = self.create_or_get_tenant()

        # Create realistic companies
        companies = self.create_realistic_companies()

        # Create users with proper roles
        users = self.create_realistic_users(companies, config)

        # Set up user activity distribution (80/20 rule - some users more active)
        self.setup_user_activity_weights(users)

        # Create manufacturing equipment
        equipment = self.create_manufacturing_equipment()

        # Initialize failure clustering - designate problematic equipment and steps
        self.setup_failure_clustering(equipment)

        # Create realistic part types and processes
        part_types = self.create_injector_part_types_and_processes(users['employees'])

        # Create realistic orders with proper timing
        orders = self.create_realistic_orders(companies, users['customers'], config)

        # Create parts with realistic workflows
        self.create_parts_with_workflows(orders, part_types, users, equipment, config)

        # Create 3D models and annotations for each part type (using benchy model)
        # Note: Must come after parts are created so annotations can link to parts
        self.create_3d_models_and_annotations(part_types, users['employees'])

        # Create historical FPY trend data (realistic curve for demos)
        self.create_historical_fpy_trend(part_types, users, equipment, config)

        # Create CAPA demo data (from quality failures)
        self.create_capa_demo_data(users, config)

        # Create company and order level documents
        self.create_company_documents(companies, users)

        # Create approval workflow demo data
        self.create_approval_workflow_demo(users)

        # Create external API identifiers
        self.create_external_api_identifiers(orders)

        # Create admin if needed
        self.create_admin_user(companies[0])  # Pass AMBAC company

        self.stdout.write(self.style.SUCCESS(f"Generated realistic {self.scale} scale production data!"))
        self.show_data_summary()

    def clear_data(self):
        """Clear existing data in dependency order (most dependent first)"""
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

    def create_linear_process_steps(self, process, step_names, part_type, description_template="{}"):
        """
        Helper to create a linear process with ProcessStep and StepEdge records.

        Args:
            process: The Processes instance
            step_names: List of step names in order
            part_type: PartTypes instance
            description_template: Template for step description (use {} for step name)

        Returns:
            List of created Step instances
        """
        steps = []
        prev_step = None
        for order, step_name in enumerate(step_names, 1):
            is_last = order == len(step_names)
            step = Steps.objects.create(
                tenant=self.tenant,
                name=step_name,
                part_type=part_type,
                description=description_template.format(step_name),
                step_type='terminal' if is_last else ('start' if order == 1 else 'task'),
                is_terminal=is_last,
                terminal_status='completed' if is_last else '',
                min_sampling_rate=0,
            )
            # Link step to process via ProcessStep
            ProcessStep.objects.create(
                process=process,
                step=step,
                order=order,
                is_entry_point=(order == 1)
            )
            # Create edge from previous step
            if prev_step:
                StepEdge.objects.create(
                    process=process,
                    from_step=prev_step,
                    to_step=step,
                    edge_type=EdgeType.DEFAULT
                )
            steps.append(step)
            prev_step = step
            self.create_measurement_definitions_for_step(step)
        return steps

    def verify_groups_exist(self):
        """Verify required groups exist (auto-created via post_migrate signal from setup_defaults)"""
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
            self.stdout.write(self.style.WARNING(
                f"Missing groups: {', '.join(missing_groups)}. "
                "Run 'python manage.py migrate' to auto-create them."
            ))
        else:
            self.stdout.write(f"  Verified {len(required_groups)} groups exist")

    def create_or_get_tenant(self):
        """Create or get the AMBAC tenant for demo data"""
        tenant, created = Tenant.objects.get_or_create(
            slug='ambac',
            defaults={
                'name': 'AMBAC Manufacturing',
                'tier': Tenant.Tier.PRO,
                'is_active': True,
                'settings': {
                    'industry': 'diesel_remanufacturing',
                    'demo_tenant': True,
                }
            }
        )
        if created:
            self.stdout.write(f"Created tenant: {tenant.name} (slug: {tenant.slug})")
        else:
            self.stdout.write(f"Using existing tenant: {tenant.name}")
        return tenant

    def assign_user_to_group(self, user, group, granted_by=None):
        """Assign user to a group within the tenant context"""
        TenantGroupMembership.objects.get_or_create(
            tenant=self.tenant,
            user=user,
            group=group,
            defaults={'granted_by': granted_by}
        )

    def setup_user_activity_weights(self, users):
        """
        Set up 80/20 activity distribution - some users are much more active.
        Top 20% of users do 80% of the work (Pareto principle).
        """
        # Assign activity weights using Zipf-like distribution
        all_employees = users['employees']
        num_employees = len(all_employees)

        # Create weights: first few users get high weights, rest get low
        weights = []
        for i, user in enumerate(all_employees):
            # Zipf distribution: weight = 1 / rank
            rank = i + 1
            weight = 1.0 / (rank ** 0.8)  # Slightly flattened Zipf
            weights.append(weight)

        # Normalize weights
        total_weight = sum(weights)
        self.employee_weights = {
            user: weight / total_weight
            for user, weight in zip(all_employees, weights)
        }

        # Store for use in weighted selection
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
        self.stdout.write(f"  User activity: power users = {', '.join(power_user_names)}...")

    def get_weighted_employee(self, users):
        """Select an employee using activity-weighted distribution."""
        if hasattr(self, 'weighted_employees') and self.weighted_employees:
            return random.choices(self.weighted_employees, weights=self.employee_weight_list, k=1)[0]
        return random.choice(users['employees'])

    def get_weighted_qa_staff(self, users):
        """Select QA staff using activity-weighted distribution."""
        if hasattr(self, 'weighted_qa_staff') and self.weighted_qa_staff:
            return random.choices(self.weighted_qa_staff, weights=self.qa_weights, k=1)[0]
        qa_staff = users.get('qa_staff', users['employees'])
        return random.choice(qa_staff) if qa_staff else random.choice(users['employees'])

    def create_realistic_companies(self):
        """Create realistic diesel industry companies"""
        company_data = [# Internal Company (AMBAC)
            ("AMBAC Manufacturing", "Diesel fuel injector remanufacturing company", "Internal"),

            # Customer Companies
            ("Cummins Engine Company", "Diesel engine manufacturer", "OEM"),
            ("Caterpillar Inc.", "Heavy machinery and engines", "OEM"),
            ("Volvo Group Trucks", "Commercial vehicle manufacturer", "OEM"),
            ("Detroit Diesel Corporation", "Heavy-duty diesel engines", "OEM"),
            ("Navistar International", "Commercial trucks and engines", "OEM"),
            ("TransAmerica Logistics", "Long-haul trucking company", "Fleet"),
            ("Metro Transit Services", "Public transportation authority", "Fleet"),
            ("Construction Solutions LLC", "Heavy equipment contractor", "Fleet"),
            ("Agricultural Services Co.", "Farm equipment services", "Fleet"),
            ("Marine Transport Inc.", "Commercial marine vessels", "Fleet"), ]

        companies = []
        for name, desc, company_type in company_data[:8]:  # Limit based on scale, but always include AMBAC
            company = Companies.objects.create(
                tenant=self.tenant,
                name=name,
                description=f"{desc} - {company_type}",
                hubspot_api_id=f"HS_{company_type}_{len(companies):03d}"
            )
            companies.append(company)

        self.stdout.write(f"Created {len(companies)} realistic companies (including AMBAC)")
        return companies

    def create_realistic_users(self, companies, config):
        """Create realistic users with proper roles and company associations"""
        users = {'customers': [], 'employees': [], 'managers': [], 'qa_staff': []}

        # Get AMBAC company (always first in list)
        ambac_company = companies[0]  # AMBAC Manufacturing

        # Get groups (auto-created via post_migrate signal)
        customer_group = Group.objects.get(name='Customer')
        production_manager_group = Group.objects.get(name='Production_Manager')
        production_operator_group = Group.objects.get(name='Production_Operator')
        qa_manager_group = Group.objects.get(name='QA_Manager')
        qa_inspector_group = Group.objects.get(name='QA_Inspector')
        document_controller_group = Group.objects.get(name='Document_Controller')

        # Create customers from external companies (portal users)
        for i in range(config['customers']):
            company = random.choice(companies[1:])  # Skip AMBAC (internal company)
            first_name = self.fake.first_name()
            last_name = self.fake.last_name()

            # Create realistic email based on company
            company_domain = company.name.lower().replace(' ', '').replace('.', '').replace(',', '')[:15] + '.com'

            user = User.objects.create_user(
                tenant=self.tenant,
                user_type=User.UserType.PORTAL,
                first_name=first_name,
                last_name=last_name,
                username=f"{first_name.lower()}.{last_name.lower()}@{company_domain}",
                password="password123",
                email=f"{first_name.lower()}.{last_name.lower()}@{company_domain}",
                parent_company=company,
                is_active=True
            )
            self.assign_user_to_group(user, customer_group)
            users['customers'].append(user)

        # Production Managers (about 10% of employees) - all work for AMBAC
        manager_count = max(2, config['employees'] // 10)
        for i in range(manager_count):
            first_name = self.fake.first_name()
            last_name = self.fake.last_name()

            user = User.objects.create_user(
                tenant=self.tenant,
                user_type=User.UserType.INTERNAL,
                first_name=first_name,
                last_name=last_name,
                username=f"{first_name.lower()}.{last_name.lower()}",
                password="password123",
                email=f"{first_name.lower()}.{last_name.lower()}@ambacmanufacturing.com",
                parent_company=ambac_company,
                is_staff=True,
                is_active=True
            )
            self.assign_user_to_group(user, production_manager_group)
            users['managers'].append(user)

        # QA Staff (about 15% of employees) - QA Managers and Inspectors
        qa_count = max(2, config['employees'] // 7)
        for i in range(qa_count):
            first_name = self.fake.first_name()
            last_name = self.fake.last_name()

            user = User.objects.create_user(
                tenant=self.tenant,
                user_type=User.UserType.INTERNAL,
                first_name=first_name,
                last_name=last_name,
                username=f"{first_name.lower()}.{last_name.lower()}.qa",
                password="password123",
                email=f"{first_name.lower()}.{last_name.lower()}.qa@ambacmanufacturing.com",
                parent_company=ambac_company,
                is_staff=True,
                is_active=True
            )
            # First QA person is manager, rest are inspectors
            if i == 0:
                self.assign_user_to_group(user, qa_manager_group)
            else:
                self.assign_user_to_group(user, qa_inspector_group)
            users['qa_staff'].append(user)

        # Document Controller (1 person)
        first_name = self.fake.first_name()
        last_name = self.fake.last_name()
        doc_controller = User.objects.create_user(
            tenant=self.tenant,
            user_type=User.UserType.INTERNAL,
            first_name=first_name,
            last_name=last_name,
            username=f"{first_name.lower()}.{last_name.lower()}.doc",
            password="password123",
            email=f"{first_name.lower()}.{last_name.lower()}.doc@ambacmanufacturing.com",
            parent_company=ambac_company,
            is_staff=True,
            is_active=True
        )
        self.assign_user_to_group(doc_controller, document_controller_group)

        # Production Operators (remaining employees) - all work for AMBAC
        operator_count = config['employees'] - manager_count - qa_count - 1  # -1 for doc controller
        for i in range(max(1, operator_count)):
            first_name = self.fake.first_name()
            last_name = self.fake.last_name()

            user = User.objects.create_user(
                tenant=self.tenant,
                user_type=User.UserType.INTERNAL,
                first_name=first_name,
                last_name=last_name,
                username=f"{first_name.lower()}.{last_name.lower()}.op{i}",
                password="password123",
                email=f"{first_name.lower()}.{last_name.lower()}.op@ambacmanufacturing.com",
                parent_company=ambac_company,
                is_active=True
            )
            self.assign_user_to_group(user, production_operator_group)
            users['employees'].append(user)

        # Include managers and QA staff in employees list for general use
        users['employees'].extend(users['managers'])
        users['employees'].extend(users['qa_staff'])
        users['employees'].append(doc_controller)

        self.stdout.write(
            f"Created {len(users['customers'])} customers, "
            f"{len(users['managers'])} managers, "
            f"{len(users['qa_staff'])} QA staff, "
            f"{operator_count} operators"
        )
        return users

    def create_manufacturing_equipment(self):
        """Create realistic diesel injector manufacturing equipment"""
        equipment_data = [# Testing Equipment
            ("Test Bench", ["TB-001", "TB-002", "TB-003", "TB-004"]), ("Flow Test Station", ["FT-001", "FT-002"]),
            ("Pressure Test Rig", ["PT-001", "PT-002"]),

            # Assembly Equipment
            ("Assembly Station", ["AS-001", "AS-002", "AS-003", "AS-004"]),
            ("Disassembly Station", ["DS-001", "DS-002", "DS-003"]),

            # Cleaning Equipment
            ("Ultrasonic Cleaner", ["UC-001", "UC-002"]), ("Parts Washer", ["PW-001", "PW-002", "PW-003"]),

            # Measuring Equipment
            ("CMM Machine", ["CMM-001"]), ("Surface Roughness Tester", ["SRT-001", "SRT-002"]), ]

        equipment = []
        for eq_type_name, equipment_names in equipment_data:
            eq_type, _ = EquipmentType.objects.get_or_create(
                name=eq_type_name,
                defaults={'tenant': self.tenant}
            )
            # Ensure tenant is set even if it existed
            if not eq_type.tenant:
                eq_type.tenant = self.tenant
                eq_type.save()

            for eq_name in equipment_names:
                eq = Equipments.objects.create(tenant=self.tenant, name=eq_name, equipment_type=eq_type)
                equipment.append(eq)

        self.stdout.write(f"Created {len(equipment)} pieces of manufacturing equipment")
        return equipment

    def setup_failure_clustering(self, equipment):
        """
        Designate some equipment as 'problematic' with higher failure rates.
        This creates realistic clustering where certain machines cause more issues.
        """
        # Designate 2-3 pieces of equipment as problematic (higher failure rate)
        self.problematic_equipment = set(random.sample(equipment, min(3, len(equipment))))

        # Group equipment by type for step-appropriate selection
        self.equipment_by_type = {}
        for eq in equipment:
            eq_type = eq.equipment_type.name if eq.equipment_type else 'General'
            if eq_type not in self.equipment_by_type:
                self.equipment_by_type[eq_type] = []
            self.equipment_by_type[eq_type].append(eq)

        problematic_names = [eq.name for eq in self.problematic_equipment]
        self.stdout.write(f"  Failure clustering: problematic equipment = {', '.join(problematic_names)}")

    def select_equipment_for_step(self, step, all_equipment):
        """Select appropriate equipment based on step type."""
        step_name_lower = step.name.lower()

        # Map step keywords to equipment types
        if any(kw in step_name_lower for kw in ['flow', 'testing', 'performance']):
            candidates = self.equipment_by_type.get('Test Bench', []) + self.equipment_by_type.get('Flow Test Station', [])
        elif any(kw in step_name_lower for kw in ['pressure', 'hydraulic']):
            candidates = self.equipment_by_type.get('Pressure Test Rig', []) + self.equipment_by_type.get('Test Bench', [])
        elif any(kw in step_name_lower for kw in ['inspection', 'qc', 'measurement', 'dimensional']):
            candidates = self.equipment_by_type.get('CMM Machine', []) + self.equipment_by_type.get('Surface Roughness Tester', [])
        elif any(kw in step_name_lower for kw in ['assembly', 'reassembly']):
            candidates = self.equipment_by_type.get('Assembly Station', [])
        elif any(kw in step_name_lower for kw in ['disassembly', 'teardown']):
            candidates = self.equipment_by_type.get('Disassembly Station', [])
        elif any(kw in step_name_lower for kw in ['cleaning', 'clean']):
            candidates = self.equipment_by_type.get('Ultrasonic Cleaner', []) + self.equipment_by_type.get('Parts Washer', [])
        else:
            candidates = all_equipment

        return random.choice(candidates) if candidates else random.choice(all_equipment)

    def get_failure_rate(self, equipment_piece, step):
        """Get failure rate based on equipment (problematic = higher rate) and step type."""
        # Base rates
        if equipment_piece in self.problematic_equipment:
            base_rate = 0.35  # 35% failure rate for problematic equipment
        else:
            base_rate = 0.12  # 12% baseline

        # Detection steps (QC/inspection) are better at finding issues
        step_name_lower = step.name.lower()
        if any(kw in step_name_lower for kw in ['inspection', 'qc', 'testing', 'validation', 'verification']):
            base_rate *= 1.3  # 30% more likely to catch issues

        return min(0.50, base_rate)  # Cap at 50%

    def calculate_work_order_timestamp(self, order):
        """Calculate when a work order was created based on order date."""
        # Work orders created 1-3 days after order
        order_date = order.created_at
        offset_hours = random.randint(24, 72)
        return order_date + timedelta(hours=offset_hours)

    def calculate_step_timestamp(self, base_timestamp, step_index, total_steps):
        """Calculate timestamp for a step transition based on progression."""
        # Each step takes 0.5-2 days on average
        hours_per_step = random.randint(12, 48)
        return base_timestamp + timedelta(hours=hours_per_step * step_index)

    def backdate_object(self, model_class, obj_id, timestamp, actor=None):
        """
        Update created_at timestamp and create audit log entry.
        Uses .update() to bypass auto_now_add.
        """
        # Backdate the created_at field
        model_class.objects.filter(pk=obj_id).update(
            created_at=timestamp,
            updated_at=timestamp
        )

        # Create audit log entry
        if actor:
            self.create_audit_log(model_class, obj_id, 'CREATE', timestamp, actor)

    def create_audit_log(self, model_class, obj_id, action, timestamp, actor, changes=None):
        """Create a realistic audit log entry with proper timestamp."""
        content_type = ContentType.objects.get_for_model(model_class)

        try:
            obj = model_class.objects.get(pk=obj_id)
            object_repr = str(obj)
        except model_class.DoesNotExist:
            object_repr = f"{model_class.__name__} (id={obj_id})"

        action_map = {
            'CREATE': LogEntry.Action.CREATE,
            'UPDATE': LogEntry.Action.UPDATE,
            'DELETE': LogEntry.Action.DELETE,
        }

        LogEntry.objects.create(
            content_type=content_type,
            object_pk=str(obj_id),
            object_id=obj_id,
            object_repr=object_repr,
            action=action_map.get(action, LogEntry.Action.UPDATE),
            changes=json.dumps(changes or {}),
            actor=actor,
            timestamp=timestamp
        )

    def create_audit_logs_for_workflow(self, work_order, parts, users, base_timestamp):
        """Create audit logs for a complete workflow with realistic timestamps."""
        # Work order creation log
        wo_actor = random.choice(users.get('managers', users['employees']))
        self.create_audit_log(
            WorkOrder, work_order.id, 'CREATE', base_timestamp, wo_actor,
            {'status': [None, work_order.workorder_status]}
        )

        # Part creation logs (all at once for batch)
        parts_timestamp = base_timestamp + timedelta(minutes=random.randint(5, 30))
        part_actor = self.get_weighted_employee(users)
        for part in parts[:10]:  # Limit to avoid too many logs
            self.create_audit_log(
                Parts, part.id, 'CREATE', parts_timestamp, part_actor,
                {'ERP_id': [None, part.ERP_id], 'step': [None, str(part.step)]}
            )

    def create_injector_part_types_and_processes(self, employees):
        """Create realistic diesel injector part types with manufacturing processes including branching"""
        from Tracker.models import ProcessStatus

        part_types = []

        # Create Common Rail Injector with full branching remanufacturing process
        cri_part_type = PartTypes.objects.create(tenant=self.tenant, name='Common Rail Injector', ID_prefix='CRI')
        part_types.append(cri_part_type)

        # Create the flagship remanufacturing process with full workflow engine features
        reman_process = Processes.objects.create(
            tenant=self.tenant,
            name=f'{cri_part_type.name} - Remanufacturing',
            is_remanufactured=True,
            part_type=cri_part_type,
            is_batch_process=False,
            status=ProcessStatus.APPROVED,  # This is the production process
            approved_at=timezone.now(),
            approved_by=random.choice(employees) if employees else None,
        )

        # Create steps with branching - mirrors the demo data structure
        steps_data = [
            # (name, step_type, is_decision, decision_type, is_terminal, terminal_status, max_visits, requires_qa, sampling_req, sampling_rate, expected_duration)
            ('Receive Core', 'start', False, '', False, '', None, False, False, 0, None),
            ('Disassemble', 'task', False, '', False, '', None, False, False, 0, None),
            ('Clean', 'timer', False, '', False, '', None, False, False, 0, '2h'),
            ('Inspect', 'decision', True, 'qa_result', False, '', None, True, True, 100, None),
            ('Reassemble', 'task', False, '', False, '', None, False, False, 0, None),
            ('Final Test', 'decision', True, 'measurement', False, '', None, True, True, 25, None),
            ('Rework', 'rework', False, '', False, '', 3, False, False, 0, None),
            ('Scrap Decision', 'decision', True, 'manual', False, '', None, False, False, 0, None),
            ('Scrap', 'terminal', False, '', True, 'scrapped', None, False, False, 0, None),
            ('Ship', 'terminal', False, '', True, 'shipped', None, False, False, 0, None),
            ('Return to Supplier', 'terminal', False, '', True, 'returned', None, False, False, 0, None),
        ]

        created_steps = {}
        for order, (name, step_type, is_decision, decision_type, is_terminal, terminal_status,
                    max_visits, requires_qa, sampling_req, sampling_rate, expected_duration) in enumerate(steps_data, 1):
            # Create step node (no process/order - those are in ProcessStep now)
            step = Steps.objects.create(
                tenant=self.tenant,
                name=name,
                part_type=cri_part_type,
                description=f"{name} for Common Rail Injector remanufacturing",
                step_type=step_type,
                is_decision_point=is_decision,
                decision_type=decision_type if is_decision else '',
                is_terminal=is_terminal,
                terminal_status=terminal_status if is_terminal else '',
                max_visits=max_visits,
                requires_qa_signoff=requires_qa,
                sampling_required=sampling_req,
                min_sampling_rate=sampling_rate,
                expected_duration=expected_duration,
            )
            created_steps[name] = step
            # Link step to process with order via ProcessStep junction
            ProcessStep.objects.create(
                process=reman_process,
                step=step,
                order=order,
                is_entry_point=(order == 1)
            )
            self.create_measurement_definitions_for_step(step)

        # Wire up the branching connections via StepEdge
        # Receive Core → Disassemble
        StepEdge.objects.create(process=reman_process, from_step=created_steps['Receive Core'],
                                to_step=created_steps['Disassemble'], edge_type=EdgeType.DEFAULT)

        # Disassemble → Clean
        StepEdge.objects.create(process=reman_process, from_step=created_steps['Disassemble'],
                                to_step=created_steps['Clean'], edge_type=EdgeType.DEFAULT)

        # Clean → Inspect
        StepEdge.objects.create(process=reman_process, from_step=created_steps['Clean'],
                                to_step=created_steps['Inspect'], edge_type=EdgeType.DEFAULT)

        # Inspect: Pass → Reassemble, Fail → Rework
        StepEdge.objects.create(process=reman_process, from_step=created_steps['Inspect'],
                                to_step=created_steps['Reassemble'], edge_type=EdgeType.DEFAULT)
        StepEdge.objects.create(process=reman_process, from_step=created_steps['Inspect'],
                                to_step=created_steps['Rework'], edge_type=EdgeType.ALTERNATE)

        # Reassemble → Final Test
        StepEdge.objects.create(process=reman_process, from_step=created_steps['Reassemble'],
                                to_step=created_steps['Final Test'], edge_type=EdgeType.DEFAULT)

        # Final Test: Pass → Ship, Fail → Rework
        StepEdge.objects.create(process=reman_process, from_step=created_steps['Final Test'],
                                to_step=created_steps['Ship'], edge_type=EdgeType.DEFAULT)
        StepEdge.objects.create(process=reman_process, from_step=created_steps['Final Test'],
                                to_step=created_steps['Rework'], edge_type=EdgeType.ALTERNATE)

        # Rework → back to Inspect, escalates to Scrap Decision after max_visits
        StepEdge.objects.create(process=reman_process, from_step=created_steps['Rework'],
                                to_step=created_steps['Inspect'], edge_type=EdgeType.DEFAULT)
        StepEdge.objects.create(process=reman_process, from_step=created_steps['Rework'],
                                to_step=created_steps['Scrap Decision'], edge_type=EdgeType.ESCALATION)

        # Scrap Decision: Default → Scrap, Alternate → Return to Supplier
        StepEdge.objects.create(process=reman_process, from_step=created_steps['Scrap Decision'],
                                to_step=created_steps['Scrap'], edge_type=EdgeType.DEFAULT)
        StepEdge.objects.create(process=reman_process, from_step=created_steps['Scrap Decision'],
                                to_step=created_steps['Return to Supplier'], edge_type=EdgeType.ALTERNATE)

        # Create a DRAFT process for testing approval workflow
        draft_process = Processes.objects.create(
            tenant=self.tenant,
            name=f'{cri_part_type.name} - New Reman (Draft)',
            is_remanufactured=True,
            part_type=cri_part_type,
            num_steps=6,
            is_batch_process=False,
            status=ProcessStatus.DRAFT,  # Not yet approved
        )

        draft_steps = ['Intake', 'Teardown', 'Clean & Inspect', 'Rebuild', 'Test', 'Package']
        self.create_linear_process_steps(draft_process, draft_steps, cri_part_type, "{} - DRAFT process step")

        # Create a simpler new manufacturing process (linear, no branching)
        new_mfg_process = Processes.objects.create(
            tenant=self.tenant,
            name=f'{cri_part_type.name} - New Manufacturing',
            is_remanufactured=False,
            part_type=cri_part_type,
            num_steps=8,
            is_batch_process=True,
            status=ProcessStatus.APPROVED,
            approved_at=timezone.now(),
            approved_by=random.choice(employees) if employees else None,
        )

        new_mfg_steps = ['Material Receiving', 'Component Fabrication', 'Precision Machining', 'Assembly',
                        'Initial Testing', 'Calibration', 'Flow Testing', 'Final QC']
        self.create_linear_process_steps(new_mfg_process, new_mfg_steps, cri_part_type,
                                         "{} for Common Rail Injector new manufacturing")

        # Create Unit Injector part type with simpler processes
        ui_part_type = PartTypes.objects.create(tenant=self.tenant, name='Unit Injector', ID_prefix='UI')
        part_types.append(ui_part_type)

        for proc_suffix, is_reman, steps_list in [
            ('Remanufacturing', True,
             ['Intake Inspection', 'Disassembly', 'Ultrasonic Cleaning', 'Pressure Testing',
              'Nozzle Replacement', 'Reassembly', 'Electronic Testing', 'Final Validation']),
            ('New Manufacturing', False,
             ['Raw Material Prep', 'Component Manufacturing', 'Quality Inspection', 'Assembly',
              'Electronic Testing', 'Performance Testing', 'Final QC']),
        ]:
            process = Processes.objects.create(
                tenant=self.tenant,
                name=f'{ui_part_type.name} - {proc_suffix}',
                is_remanufactured=is_reman,
                part_type=ui_part_type,
                num_steps=len(steps_list),
                is_batch_process=random.random() < 0.3,
                status=ProcessStatus.APPROVED,
                approved_at=timezone.now(),
                approved_by=random.choice(employees) if employees else None,
            )
            self.create_linear_process_steps(process, steps_list, ui_part_type,
                                             "{} for " + ui_part_type.name)

        # Create HEUI Injector part type
        heui_part_type = PartTypes.objects.create(tenant=self.tenant, name='HEUI Injector', ID_prefix='HEUI')
        part_types.append(heui_part_type)

        for proc_suffix, is_reman, steps_list in [
            ('Remanufacturing', True,
             ['Visual Inspection', 'Teardown', 'Component Cleaning', 'Hydraulic Testing',
              'Electrical Testing', 'Rebuild', 'Performance Testing', 'Quality Verification']),
            ('New Manufacturing', False,
             ['Material Sourcing', 'Component Fabrication', 'Hydraulic Assembly', 'Electrical Assembly',
              'System Testing', 'Final QC']),
        ]:
            process = Processes.objects.create(
                tenant=self.tenant,
                name=f'{heui_part_type.name} - {proc_suffix}',
                is_remanufactured=is_reman,
                part_type=heui_part_type,
                num_steps=len(steps_list),
                is_batch_process=random.random() < 0.3,
                status=ProcessStatus.APPROVED,
                approved_at=timezone.now(),
                approved_by=random.choice(employees) if employees else None,
            )
            self.create_linear_process_steps(process, steps_list, heui_part_type,
                                             "{} for " + heui_part_type.name)

        self.stdout.write(f"Created {len(part_types)} part types with workflow-enabled processes")
        return part_types

    def create_measurement_definitions_for_step(self, step):
        """Create realistic measurement definitions for ALL steps"""
        measurements = []

        # Step-specific measurements
        if 'Flow' in step.name:
            measurements.extend([
                ('Flow Rate', 'NUMERIC', 'mL/min', 850.0, 25.0, 25.0),
                ('Injection Pattern', 'PASS_FAIL', '', None, None, None),
            ])
        elif 'Pressure' in step.name:
            measurements.extend([
                ('Opening Pressure', 'NUMERIC', 'bar', 280.0, 10.0, 10.0),
                ('Closing Pressure', 'NUMERIC', 'bar', 250.0, 15.0, 15.0),
            ])
        elif any(word in step.name for word in ['Inspection', 'QC', 'Testing', 'Validation']):
            measurements.extend([
                ('Overall Length', 'NUMERIC', 'mm', 156.5, 0.1, 0.1),
                ('Surface Finish', 'NUMERIC', 'Ra µm', 0.8, 0.2, 0.2),
            ])
        elif any(word in step.name for word in ['Assembly', 'Disassembly', 'Reassembly']):
            measurements.extend([
                ('Assembly Complete', 'PASS_FAIL', '', None, None, None),
                ('Torque Spec', 'NUMERIC', 'Nm', 45.0, 5.0, 5.0),
            ])
        elif any(word in step.name for word in ['Cleaning', 'Clean']):
            measurements.extend([
                ('Cleanliness Check', 'PASS_FAIL', '', None, None, None),
                ('Contamination Level', 'NUMERIC', 'mg/L', 5.0, 2.0, 2.0),
            ])
        elif any(word in step.name for word in ['Machining', 'Fabrication']):
            measurements.extend([
                ('Dimensional Check', 'NUMERIC', 'mm', 12.5, 0.05, 0.05),
                ('Surface Quality', 'PASS_FAIL', '', None, None, None),
            ])
        elif any(word in step.name for word in ['Calibration', 'Adjustment']):
            measurements.extend([
                ('Calibration Status', 'PASS_FAIL', '', None, None, None),
                ('Tolerance Check', 'NUMERIC', '%', 0.0, 1.0, 1.0),
            ])
        else:
            # Default measurements for any other step type - include numeric for SPC
            measurements.extend([
                ('Process Complete', 'PASS_FAIL', '', None, None, None),
                ('Cycle Time', 'NUMERIC', 'sec', 120.0, 15.0, 15.0),
            ])

        # Create measurement definitions
        for label, type_val, unit, nominal, upper_tol, lower_tol in measurements:
            MeasurementDefinition.objects.create(
                tenant=self.tenant,
                step=step,
                label=label,
                type=type_val,
                unit=unit,
                nominal=nominal,
                upper_tol=upper_tol,
                lower_tol=lower_tol
            )

    def create_realistic_orders(self, companies, customers, config):
        """Create realistic orders with proper status distribution and timing"""
        orders = []

        # Demo-friendly status distribution - more active work, fewer completed
        status_weights = [(OrdersStatus.COMPLETED, 0.15),  # 15% completed
            (OrdersStatus.IN_PROGRESS, 0.35),  # 35% in progress
            (OrdersStatus.PENDING, 0.25),  # 25% pending
            (OrdersStatus.RFI, 0.15),  # 15% RFI
            (OrdersStatus.ON_HOLD, 0.1),  # 10% on hold
            (OrdersStatus.CANCELLED, 0.0),  # 0% cancelled for demo
        ]

        # Generate orders over past 6 months
        start_date = timezone.now().date() - timedelta(days=180)

        for i in range(config['orders']):
            # Determine status using weights
            status = self.weighted_choice(status_weights)

            # Create realistic timing
            order_date = self.fake.date_between(start_date=start_date,
                                                end_date=timezone.now().date() - timedelta(days=7))

            if status == OrdersStatus.COMPLETED:
                completion_offset = random.randint(14, 45)  # 2-6 weeks
                estimated_completion = order_date + timedelta(days=completion_offset - random.randint(0, 3))
            elif status in [OrdersStatus.IN_PROGRESS, OrdersStatus.PENDING]:
                estimated_completion = timezone.now().date() + timedelta(days=random.randint(3, 30))
            else:
                estimated_completion = order_date + timedelta(days=random.randint(14, 60))

            customer = random.choice(customers)
            order_number = f"ORD-{order_date.strftime('%y%m')}-{i + 1:03d}"

            order = Orders.objects.create(
                tenant=self.tenant,
                name=order_number,
                customer=customer,
                company=customer.parent_company,
                order_status=status,
                estimated_completion=estimated_completion,
                customer_note=f"Diesel injector remanufacturing order for {customer.parent_company.name}"
            )

            # Backdate order created_at (auto_now_add ignores explicit values)
            order_timestamp = timezone.make_aware(datetime.combine(order_date, datetime.min.time()))
            Orders.objects.filter(pk=order.pk).update(created_at=order_timestamp, updated_at=order_timestamp)
            order.refresh_from_db()  # Reload to get backdated timestamp

            orders.append(order)

        self.stdout.write(f"Created {config['orders']} orders with realistic status distribution")
        return orders

    def create_parts_with_workflows(self, orders, part_types, users, equipment, config):
        """Create work orders and parts using model methods for proper relationships"""
        total_parts = 0
        total_work_orders = 0

        for order in orders:
            # Determine how many work orders this order should have based on its complexity
            num_work_orders = self.determine_work_orders_for_order(order, config)

            # Select part type and process once per order - all work orders in same order use same part type
            order_part_type = random.choice(part_types)
            order_process = self.select_appropriate_process(order_part_type)

            if not order_process:
                continue

            # Get steps via ProcessStep junction table, ordered by ProcessStep.order
            process_steps = ProcessStep.objects.filter(
                process=order_process
            ).select_related('step').order_by('order')
            order_steps = [ps.step for ps in process_steps]
            if not order_steps:
                continue

            # Create sampling rulesets for this order's part type and process
            self.ensure_sampling_rulesets_exist(order_part_type, order_process, order_steps, users['employees'])

            # Determine target step progression for this order (all work orders will be close to this)
            base_target_step_index = self.get_target_step_index(order_steps, order.order_status)

            for wo_index in range(num_work_orders):
                steps = order_steps

                # Calculate realistic timestamp for this work order (1-3 days after order)
                wo_timestamp = self.calculate_work_order_timestamp(order)

                # Determine work order details based on order
                work_order_details = self.determine_work_order_details(order, order_part_type, order_process, wo_index,
                                                                       config)

                # Create work order using proper status
                work_order = WorkOrder.objects.create(
                    tenant=self.tenant,
                    ERP_id=work_order_details['erp_id'],
                    related_order=order,
                    expected_completion=work_order_details['expected_completion'],
                    quantity=work_order_details['quantity'],
                    workorder_status=work_order_details['status']
                )
                total_work_orders += 1

                # Backdate work order to realistic timestamp
                self.backdate_object(WorkOrder, work_order.id, wo_timestamp,
                                    actor=random.choice(users.get('managers', users['employees'])))

                # Use WorkOrder's create_parts_batch method to generate parts properly
                initial_step = steps[0]
                parts = work_order.create_parts_batch(order_part_type, initial_step, work_order_details['quantity'])

                # Set order reference for parts to match work order's related order
                Parts.objects.filter(id__in=[p.id for p in parts]).update(order=work_order.related_order)

                # Backdate parts to shortly after work order creation
                parts_timestamp = wo_timestamp + timedelta(minutes=random.randint(10, 60))
                Parts.objects.filter(work_order=work_order).update(
                    created_at=parts_timestamp,
                    updated_at=parts_timestamp
                )

                # Use real batch advancement with variation around base target for similar progression
                # Work orders within same order should be close in step progression
                variation = random.randint(-1, 1)  # Allow ±1 step variation within same order
                target_step_index = max(0, min(len(steps) - 1, base_target_step_index + variation))

                # Calculate step transition timestamps
                step_timestamps = []
                for i in range(target_step_index + 1):
                    step_ts = self.calculate_step_timestamp(parts_timestamp, i, len(steps))
                    step_timestamps.append(step_ts)

                self.advance_work_order_batch(work_order, target_step_index)

                # Backdate step transition logs with realistic timestamps
                transition_logs = StepTransitionLog.objects.filter(
                    part__work_order=work_order
                ).order_by('id')
                for i, log in enumerate(transition_logs):
                    if i < len(step_timestamps):
                        StepTransitionLog.objects.filter(pk=log.pk).update(
                            timestamp=step_timestamps[min(i, len(step_timestamps) - 1)]
                        )

                # CRITICAL: ALWAYS ensure sampling is properly evaluated after work order creation
                # This makes it impossible for work orders to have zero sampling parts
                work_order._bulk_evaluate_sampling(work_order.parts.all())

                # Create quality reports for ALL sampled parts (this is what sampling is for)
                # Use the latest step timestamp for QA timing
                qa_timestamp = step_timestamps[-1] if step_timestamps else parts_timestamp
                sampled_parts = work_order.parts.filter(requires_sampling=True)
                for part in sampled_parts:
                    self.create_quality_report_for_part(part, part.step, users, equipment, qa_timestamp)

                # Create comprehensive documents for some sampled parts (20% of parts that require sampling)
                for part in sampled_parts[:max(1, sampled_parts.count() // 5)]:
                    self.create_comprehensive_documents(part, users)

                total_parts += len(parts)

        self.stdout.write(f"Created {total_work_orders} work orders with {total_parts} parts using model methods")

    def determine_work_orders_for_order(self, order, config):
        """Determine how many work orders this order should have"""
        if order.order_status == OrdersStatus.PENDING:
            # Pending orders typically have fewer work orders
            return random.randint(1, 2)
        elif order.order_status == OrdersStatus.RFI:
            # RFI orders might have some work orders started
            return random.randint(1, 2)
        elif order.order_status == OrdersStatus.ON_HOLD:
            # On hold orders have started work orders
            return random.randint(1, 2)
        else:
            # In progress and completed orders have more work orders
            return random.randint(1, 3)

    def select_appropriate_process(self, part_type):
        """Select a process based on part type characteristics"""
        from Tracker.models import ProcessStatus

        # Only select APPROVED processes (exclude DRAFT)
        processes = list(part_type.processes.filter(status=ProcessStatus.APPROVED))
        if not processes:
            return None

        # Prefer remanufacturing processes (they have branching) - 80% of the time
        reman_processes = [p for p in processes if p.is_remanufactured]
        new_processes = [p for p in processes if not p.is_remanufactured]

        if reman_processes and random.random() < 0.8:
            return random.choice(reman_processes)
        elif new_processes:
            return random.choice(new_processes)
        else:
            return random.choice(processes)

    def determine_work_order_details(self, order, part_type, process, wo_index, config):
        """Determine work order details based on order characteristics"""
        # Generate ERP ID
        order_date_str = order.name.split('-')[1] if '-' in order.name else '2501'
        erp_id = f"WO-{order_date_str}-{part_type.ID_prefix}-{wo_index + 1:02d}"

        # Each work order should have at least 25 parts for realistic batch sizes
        quantity = random.randint(25, 60)

        # Expected completion based on order
        if order.estimated_completion:
            # Work orders complete slightly before order
            offset_days = random.randint(-7, -1)
            expected_completion = order.estimated_completion + timedelta(days=offset_days)
        else:
            expected_completion = None

        # Work order status based on order status
        status = self.determine_work_order_status(order.order_status)

        return {'erp_id': erp_id, 'quantity': quantity, 'expected_completion': expected_completion, 'status': status}

    def get_target_step_index(self, steps, order_status):
        """Get target step index based on order status"""
        if order_status == OrdersStatus.COMPLETED:
            return len(steps) - 1  # Last step
        elif order_status == OrdersStatus.IN_PROGRESS:
            return random.randint(len(steps) // 3, len(steps) - 2)  # Middle to near end
        elif order_status == OrdersStatus.PENDING:
            return random.randint(0, len(steps) // 2)  # Early steps
        elif order_status == OrdersStatus.RFI:
            return random.randint(1, len(steps) // 2 + 1)  # Early-middle
        elif order_status == OrdersStatus.ON_HOLD:
            return random.randint(len(steps) // 4, len(steps) * 3 // 4)  # Middle
        else:
            return 0  # First step

    def advance_work_order_batch(self, work_order, target_step_index):
        """
        Advance work order parts through process with realistic branching.

        - Parts at decision points get QA reports created first
        - Some parts fail and route to alternate paths (rework)
        - Parts can loop through rework multiple times
        - Some parts escalate to scrap decision after max_visits
        """
        if target_step_index <= 0:
            return

        parts = list(work_order.parts.all())
        if not parts:
            return

        # Track parts that have completed (reached terminal) vs still active
        completed_parts = set()

        # Process each part individually to allow different paths
        for part in parts:
            visits_at_step = {}  # Track visits per step for this part
            advancement_count = 0
            max_advancements = target_step_index + 10  # Allow extra for rework loops

            while advancement_count < max_advancements:
                part.refresh_from_db()
                current_step = part.step

                if not current_step:
                    break

                # Check if already completed
                if part.part_status in [PartsStatus.COMPLETED, PartsStatus.SCRAPPED, PartsStatus.CANCELLED]:
                    completed_parts.add(part.id)
                    break

                # Track visits to this step
                step_id = current_step.id
                visits_at_step[step_id] = visits_at_step.get(step_id, 0) + 1

                # If this is a decision point, create QA report first
                decision_result = None
                if current_step.is_decision_point and current_step.decision_type == 'qa_result':
                    # Determine pass/fail - use realistic failure rate
                    # Higher failure rate for parts that have been through rework
                    base_fail_rate = 0.15  # 15% base failure rate
                    rework_penalty = 0.05 * (visits_at_step.get(step_id, 1) - 1)  # +5% per revisit
                    fail_rate = min(0.40, base_fail_rate + rework_penalty)

                    passed = random.random() > fail_rate
                    decision_result = 'PASS' if passed else 'FAIL'

                    # Create the QA report that increment_step will look up
                    from Tracker.models import QualityReports
                    qr = QualityReports.objects.create(
                        tenant=self.tenant,
                        part=part,
                        step=current_step,
                        status=decision_result,
                        description=f"QA check at {current_step.name}",
                        sampling_method='statistical',
                    )

                elif current_step.is_decision_point and current_step.decision_type == 'manual':
                    # For manual decisions, randomly choose path
                    decision_result = 'default' if random.random() > 0.3 else 'alternate'

                # Mark part ready and advance
                part.part_status = PartsStatus.READY_FOR_NEXT_STEP
                part.save()

                try:
                    result = part.increment_step(decision_result=decision_result)
                except ValueError as e:
                    # Manual decision required but not provided - use default
                    result = part.increment_step(decision_result='default')

                advancement_count += 1

                if result == "completed":
                    completed_parts.add(part.id)
                    break
                elif result == "marked_ready":
                    break  # Waiting for batch

                # Stop if we've reached the target progression (unless in rework loop)
                part.refresh_from_db()
                if part.step and part.work_order and part.work_order.process:
                    # Get step order from ProcessStep
                    from Tracker.models import ProcessStep
                    ps = ProcessStep.objects.filter(
                        process=part.work_order.process,
                        step=part.step
                    ).first()
                    step_order = ps.order if ps else 0
                    if step_order >= target_step_index:
                        # But allow rework loops to continue
                        if part.step.step_type != 'rework':
                            break

    def ensure_sampling_rulesets_exist(self, part_type, process, steps, employees):
        """Create sampling rulesets for ALL steps"""
        for step in steps:
            ruleset, created = SamplingRuleSet.objects.get_or_create(
                tenant=self.tenant,
                part_type=part_type,
                process=process,
                step=step,
                is_fallback=False,
                defaults={
                    "name": f"QC Rules - {part_type.name} - {step.name}",
                    "origin": "production",
                    "active": True,
                    "created_by": random.choice(employees),
                    "modified_by": random.choice(employees),
                }
            )

            if created:
                # Create realistic sampling rules based on step type
                rule_configs = self.get_realistic_sampling_rules_for_step(step)
                for rule_config in rule_configs:
                    SamplingRule.objects.create(
                        tenant=self.tenant,
                        ruleset=ruleset,
                        rule_type=rule_config['rule_type'],
                        value=rule_config['value'],
                        order=rule_config.get('order', 0),
                        created_by=random.choice(employees),
                        modified_by=random.choice(employees)
                    )

    def get_realistic_sampling_rules_for_step(self, step):
        """Get realistic sampling rules based on step type"""
        step_name = step.name.lower()

        # Different sampling strategies for different step types
        if any(word in step_name for word in ['inspection', 'qc', 'validation', 'final', 'verification']):
            # Critical QA steps - higher sampling rate
            return [{'rule_type': 'every_nth_part', 'value': random.randint(2, 4), 'order': 1}  # Every 2-4 parts
            ]
        elif any(word in step_name for word in
                 ['testing', 'flow', 'pressure', 'hydraulic', 'electronic', 'performance']):
            # Testing steps - moderate sampling
            return [{'rule_type': 'percentage', 'value': random.randint(25, 50), 'order': 1}  # 25-50% of parts
            ]
        elif any(word in step_name for word in ['assessment', 'calibration']):
            # Assessment/calibration steps - moderate sampling
            return [{'rule_type': 'every_nth_part', 'value': random.randint(3, 6), 'order': 1}  # Every 3-6 parts
            ]
        elif any(word in step_name for word in ['assembly', 'reassembly', 'disassembly']):
            # Assembly process steps - light sampling for process verification
            return [{'rule_type': 'every_nth_part', 'value': random.randint(5, 8), 'order': 1}  # Every 5-8 parts
            ]
        elif any(word in step_name for word in ['cleaning', 'replacement', 'teardown', 'rebuild']):
            # Process steps - light sampling
            return [{'rule_type': 'percentage', 'value': random.randint(15, 25), 'order': 1}  # 15-25% of parts
            ]
        else:
            # Default sampling for any other step
            return [{'rule_type': 'every_nth_part', 'value': random.randint(6, 10), 'order': 1}  # Every 6-10 parts
            ]

    def create_quality_report_for_part(self, part, step, users, equipment, timestamp=None):
        """Create quality report for a sampled part with failure clustering and realistic timestamps."""
        # Select appropriate equipment for this step type
        selected_equipment = self.select_equipment_for_step(step, equipment)

        # Get failure rate based on equipment and step (clustering)
        failure_rate = self.get_failure_rate(selected_equipment, step)
        status = "FAIL" if random.random() < failure_rate else "PASS"

        operator = self.get_weighted_employee(users)

        # Add some time variation for the QA event (inspection takes 15-60 minutes)
        qa_time = timestamp + timedelta(minutes=random.randint(15, 60)) if timestamp else None

        qr = QualityReports.objects.create(
            tenant=self.tenant,
            part=part,
            machine=selected_equipment,
            step=step,
            description=f"{step.name} results for {part.ERP_id} - "
                       f"{'measurements completed successfully' if status == 'PASS' else 'issues found during testing'}",
            sampling_method="statistical" if random.random() > 0.3 else "manual",
            status=status
        )
        qr.operators.add(operator)

        # Backdate quality report if timestamp provided
        if qa_time:
            QualityReports.objects.filter(pk=qr.pk).update(created_at=qa_time, updated_at=qa_time)
            # Create audit log for the QA report
            self.create_audit_log(QualityReports, qr.id, 'CREATE', qa_time, operator,
                                 {'status': [None, status], 'part': [None, part.ERP_id]})

        # Create EquipmentUsage record to track this QA event
        eq_usage = EquipmentUsage.objects.create(
            tenant=self.tenant,
            equipment=selected_equipment,
            step=step,
            part=part,
            error_report=qr if status == "FAIL" else None,
            operator=operator,
            notes=f"QA inspection on {selected_equipment.name}" + (" - FAILED" if status == "FAIL" else "")
        )

        # Backdate equipment usage
        if qa_time:
            EquipmentUsage.objects.filter(pk=eq_usage.pk).update(used_at=qa_time, created_at=qa_time, updated_at=qa_time)

        # Create quality error lists and dispositions
        self.create_quality_error_lists_and_dispositions(qr, part.part_type, users, qa_time)

        # Create measurement results for this step
        for measurement_def in step.measurement_definitions.all():
            if measurement_def.type == 'NUMERIC' and measurement_def.nominal:
                if status == "PASS":
                    # Within tolerance
                    variance = float(min(measurement_def.upper_tol or 0, measurement_def.lower_tol or 0)) * 0.3
                    value = float(measurement_def.nominal) + random.uniform(-variance, variance)
                    is_within_spec = True
                else:
                    # Out of spec
                    variance = float(max(measurement_def.upper_tol or 0, measurement_def.lower_tol or 0)) * 1.2
                    value = float(measurement_def.nominal) + random.uniform(-variance, variance)
                    is_within_spec = False

                mr = MeasurementResult.objects.create(
                    tenant=self.tenant,
                    report=qr,
                    definition=measurement_def,
                    value_numeric=round(value, 4),
                    is_within_spec=is_within_spec,
                    created_by=self.get_weighted_employee(users)
                )

                # Backdate measurement result
                if qa_time:
                    MeasurementResult.objects.filter(pk=mr.pk).update(created_at=qa_time, updated_at=qa_time)

    def create_admin_user(self, ambac_company):
        """Create admin user if needed"""
        if not User.objects.filter(username="admin").exists():
            admin_user = User.objects.create_superuser(
                tenant=self.tenant,
                user_type=User.UserType.INTERNAL,
                username="admin",
                email="admin@email.com",
                password="Annoy1ng",
                first_name="Admin",
                last_name="User",
                parent_company=ambac_company
            )
            # Add to Admin group via TenantGroupMembership
            admin_group = Group.objects.get(name='Admin')
            self.assign_user_to_group(admin_user, admin_group)
            self.stdout.write(self.style.SUCCESS("Admin user created: admin / Annoy1ng (AMBAC)"))

    def weighted_choice(self, choices):
        """Select item based on weights"""
        total = sum(weight for choice, weight in choices)
        r = random.uniform(0, total)
        upto = 0
        for choice, weight in choices:
            if upto + weight >= r:
                return choice
            upto += weight
        return choices[-1][0]

    def get_disposition_state_by_age(self, created_at):
        """
        Determine disposition state based on age - older issues should be resolved.
        This creates realistic "steady state" where most historical issues are closed
        and only recent ones remain open.
        """
        age_days = (timezone.now() - created_at).days if created_at else 0

        if age_days <= 3:
            # Recent: mix of states, weighted toward open/in-progress
            weights = [0.30, 0.40, 0.30]  # OPEN, IN_PROGRESS, CLOSED
        elif age_days <= 7:
            # Week old: mostly resolved
            weights = [0.10, 0.20, 0.70]
        elif age_days <= 14:
            # Two weeks: almost all closed
            weights = [0.03, 0.07, 0.90]
        elif age_days <= 30:
            # Month old: rare to still be open
            weights = [0.01, 0.02, 0.97]
        else:
            # Older than a month: exceptional only
            weights = [0.005, 0.005, 0.99]

        return random.choices(['OPEN', 'IN_PROGRESS', 'CLOSED'], weights=weights)[0]

    def show_data_summary(self):
        """Show summary of created data"""
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("PRODUCTION DATA SUMMARY")
        self.stdout.write("=" * 50)
        self.stdout.write(f"Companies: {Companies.objects.count()}")
        self.stdout.write(f"Users: {User.objects.count()}")
        self.stdout.write(f"Part Types: {PartTypes.objects.count()}")
        self.stdout.write(f"Equipment: {Equipments.objects.count()}")
        self.stdout.write(f"Orders: {Orders.objects.count()}")
        self.stdout.write(f"Work Orders: {WorkOrder.objects.count()}")
        self.stdout.write(f"Parts: {Parts.objects.count()}")
        self.stdout.write(f"Quality Reports: {QualityReports.objects.count()}")
        self.stdout.write(f"Quarantine Dispositions: {QuarantineDisposition.objects.count()}")
        self.stdout.write(f"CAPAs: {CAPA.objects.count()}")
        self.stdout.write(f"CAPA Tasks: {CapaTasks.objects.count()}")
        self.stdout.write(f"RCA Records: {RcaRecord.objects.count()}")
        self.stdout.write(f"Documents: {Documents.objects.count()}")
        self.stdout.write(f"Approval Requests: {ApprovalRequest.objects.count()}")
        self.stdout.write(f"Approval Responses: {ApprovalResponse.objects.count()}")
        self.stdout.write(f"Step Transition Logs: {StepTransitionLog.objects.count()}")
        self.stdout.write(f"Equipment Usage: {EquipmentUsage.objects.count()}")
        self.stdout.write(f"Audit Log Entries: {LogEntry.objects.count()}")
        self.stdout.write(f"Sampling Analytics: {SamplingAnalytics.objects.count()}")
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
        self.stdout.write("=" * 50)

    def determine_work_order_status(self, order_status):
        """Map order status to work order status"""
        status_mapping = {OrdersStatus.COMPLETED: WorkOrderStatus.COMPLETED,
            OrdersStatus.IN_PROGRESS: WorkOrderStatus.IN_PROGRESS, OrdersStatus.PENDING: WorkOrderStatus.PENDING,
            OrdersStatus.ON_HOLD: WorkOrderStatus.ON_HOLD, OrdersStatus.CANCELLED: WorkOrderStatus.CANCELLED,
            OrdersStatus.RFI: WorkOrderStatus.WAITING_FOR_OPERATOR, }
        return status_mapping.get(order_status, WorkOrderStatus.PENDING)

    def create_advanced_sampling_data(self, part, users):
        """Create advanced sampling tracking data"""
        # Create sampling audit log if part has sampling data
        if part.sampling_ruleset:
            # Get first rule from the ruleset to create audit log
            first_rule = part.sampling_ruleset.rules.first()
            if first_rule:
                SamplingAuditLog.objects.create(
                    tenant=self.tenant,
                    part=part,
                    rule=first_rule,
                    sampling_decision=part.requires_sampling,
                    ruleset_type='PRIMARY'
                )

        # Create sampling trigger state for work orders
        if part.work_order and part.sampling_ruleset:
            trigger_state, created = SamplingTriggerState.objects.get_or_create(
                tenant=self.tenant,
                ruleset=part.sampling_ruleset,
                work_order=part.work_order,
                step=part.step,
                defaults={
                    'active': part.part_status in [PartsStatus.IN_PROGRESS, PartsStatus.AWAITING_QA],
                    'success_count': random.randint(0, 5) if part.part_status == PartsStatus.COMPLETED else 0,
                    'fail_count': random.randint(0, 2),
                }
            )

            # Add this part to the inspected parts
            trigger_state.parts_inspected.add(part)

        # Create sampling analytics for completed work orders
        if (
                part.work_order and part.sampling_ruleset and part.work_order.workorder_status == WorkOrderStatus.COMPLETED):
            analytics, created = SamplingAnalytics.objects.get_or_create(
                tenant=self.tenant,
                ruleset=part.sampling_ruleset,
                work_order=part.work_order,
                defaults={
                    'parts_sampled': random.randint(1, part.work_order.quantity),
                    'parts_total': part.work_order.quantity,
                    'defects_found': random.randint(0, 2),
                    'actual_sampling_rate': random.uniform(0.1, 0.3),
                    'target_sampling_rate': 0.2,
                    'variance': random.uniform(-0.05, 0.05)
                }
            )

    def create_comprehensive_documents(self, part, users):
        """Create various types of documents with proper DocumentType references"""
        # Map to seeded DocumentTypes (from defaults_service.py)
        doc_configs = [
            # (DocumentType code, classification, is_image, file extension)
            ('IR', ClassificationLevel.INTERNAL, False, 'pdf'),      # Inspection Report
            ('WI', ClassificationLevel.PUBLIC, False, 'pdf'),        # Work Instruction
            ('TR', ClassificationLevel.CONFIDENTIAL, False, 'pdf'),  # Test Report
            ('MTR', ClassificationLevel.INTERNAL, False, 'pdf'),     # Material Test Report
            ('COC', ClassificationLevel.INTERNAL, False, 'pdf'),     # Certificate of Conformance
        ]

        # Create 1-3 documents per part randomly
        num_docs = random.randint(1, 3)
        selected_configs = random.sample(doc_configs, min(num_docs, len(doc_configs)))

        for doc_type_code, classification, is_image, ext in selected_configs:
            # Get the DocumentType (seeded via post_migrate)
            try:
                doc_type = DocumentType.objects.get(code=doc_type_code)
            except DocumentType.DoesNotExist:
                continue  # Skip if document type not seeded yet

            file_name = f"{doc_type_code.lower()}_{part.ERP_id}.{ext}"

            Documents.objects.create(
                tenant=self.tenant,
                document_type=doc_type,
                classification=classification,
                is_image=is_image,
                file_name=file_name,
                file=ContentFile(
                    f"Sample {doc_type.name} for part {part.ERP_id}".encode(),
                    name=file_name
                ),
                uploaded_by=random.choice(users['employees']),
                content_type=ContentType.objects.get_for_model(Parts),
                object_id=part.id,
                status='RELEASED',  # Most production documents are released
            )

    def create_quality_error_lists_and_dispositions(self, quality_report, part_type, users, timestamp=None):
        """Create quality error lists and quarantine dispositions for failed reports"""
        # Create quality error list for this part type if needed
        error_types = ["Surface scratches detected", "Dimensional out of tolerance", "Contamination found",
            "Wear patterns excessive", "Coating defects present"]

        errors = []
        if quality_report.status == "FAIL":
            # Create 1-2 error types for failed reports
            for _ in range(random.randint(1, 2)):
                error_name = random.choice(error_types)
                error, created = QualityErrorsList.objects.get_or_create(
                    tenant=self.tenant,
                    error_name=error_name,
                    part_type=part_type,
                    defaults={'error_example': f"Example: {error_name} in {part_type.name}"}
                )
                errors.append(error)

        quality_report.errors.set(errors)

        # Create quarantine disposition for failed quality reports
        if quality_report.status == "FAIL" and quality_report.part:
            disposition_types = ['REWORK', 'SCRAP', 'USE_AS_IS', 'RETURN_TO_SUPPLIER']

            # Weight towards realistic distribution
            disposition_type = random.choices(
                disposition_types,
                weights=[0.5, 0.2, 0.2, 0.1]  # Most failures get reworked
            )[0]

            # Use time-based closure logic - older dispositions should be closed
            target_state = self.get_disposition_state_by_age(timestamp)

            # Calculate resolution time if closed (1-5 days after failure)
            resolution_time = timestamp + timedelta(days=random.randint(1, 5)) if timestamp and target_state == 'CLOSED' else None

            # Create disposition with IN_PROGRESS state first (to avoid M2M issue on CLOSED validation)
            disposition = QuarantineDisposition.objects.create(
                tenant=self.tenant,
                current_state='IN_PROGRESS',  # Start as IN_PROGRESS, update to CLOSED later if needed
                disposition_type=disposition_type,
                assigned_to=self.get_weighted_employee(users),
                description=f"Quality failure on {quality_report.part.ERP_id} at {quality_report.step.name}",
                resolution_notes=f"Disposition: {disposition_type}" if target_state == 'CLOSED' else "",
                resolution_completed=(target_state == 'CLOSED'),
                resolution_completed_by=self.get_weighted_employee(users) if target_state == 'CLOSED' else None,
                resolution_completed_at=resolution_time if target_state == 'CLOSED' else None,
                part=quality_report.part,
                step=quality_report.step,
            )

            # Add the M2M relationship AFTER the object has an ID
            disposition.quality_reports.add(quality_report)

            # Now update to the target state (including CLOSED if needed)
            if target_state != 'IN_PROGRESS':
                QuarantineDisposition.objects.filter(pk=disposition.pk).update(current_state=target_state)

            # Backdate disposition
            if timestamp:
                QuarantineDisposition.objects.filter(pk=disposition.pk).update(
                    created_at=timestamp,
                    updated_at=resolution_time if target_state == 'CLOSED' else timestamp
                )

    def create_external_api_identifiers(self, orders):
        """Create external API identifiers for orders"""
        # Create some HubSpot stage mappings
        hubspot_stages = ["Initial Contact", "Quote Sent", "Negotiation", "Production", "Quality Check", "Shipped",
            "Completed"]

        for stage in hubspot_stages:
            ExternalAPIOrderIdentifier.objects.get_or_create(
                tenant=self.tenant,
                stage_name=stage,
                defaults={'API_id': f'HS_STAGE_{stage.upper().replace(" ", "_")}'}
            )

    def create_historical_fpy_trend(self, part_types, users, equipment, config):
        """
        Create realistic historical FPY data that tells a story:
        - Starts around 85-88% FPY
        - Gradual improvement to 92-95%
        - 2-3 "events" (equipment issues, material problems) with dips and recovery
        - Daily variation and weekly patterns
        - Enough volume for smooth charts
        """
        import math

        days_of_history = 120  # 4 months of data
        reports_per_day_base = {'small': 8, 'medium': 20, 'large': 50}[self.scale]

        # Get parts and steps to attach reports to
        parts = list(Parts.objects.select_related('step', 'part_type')[:500])
        if not parts:
            self.stdout.write("  No parts available for historical FPY data")
            return

        # Get only steps that have numeric measurement definitions (for SPC data)
        steps_with_numeric = list(Steps.objects.filter(
            measurement_definitions__type='NUMERIC',
            measurement_definitions__nominal__isnull=False
        ).distinct().prefetch_related('measurement_definitions'))

        if not steps_with_numeric:
            self.stdout.write("  No steps with numeric measurements available")
            return

        self.stdout.write(f"  Using {len(steps_with_numeric)} steps with numeric measurements")

        # Define "events" - dips in FPY that recover (equipment failure, bad material batch, etc.)
        # Reduced depths for more realistic stable operation (8-10% failure rate baseline)
        events = [
            {'day': 25, 'duration': 8, 'depth': 0.06, 'name': 'Equipment calibration drift'},
            {'day': 60, 'duration': 5, 'depth': 0.04, 'name': 'Material batch issue'},
            {'day': 95, 'duration': 6, 'depth': 0.05, 'name': 'New operator training'},
        ]

        total_reports = 0
        total_pass = 0

        for day_offset in range(days_of_history, 0, -1):
            report_date = timezone.now() - timedelta(days=day_offset)

            # Base FPY: starts at 90%, improves to 92% over time (stable operation)
            # This gives ~8-10% failure rate, which is realistic for a healthy operation
            progress = 1 - (day_offset / days_of_history)  # 0 to 1
            base_fpy = 0.90 + (progress * 0.02)  # 90% → 92%

            # Add weekly pattern (Monday=lower, mid-week=best, Friday=slightly lower)
            weekday = report_date.weekday()
            weekly_modifier = {
                0: -0.02,   # Monday - ramp up
                1: 0.01,    # Tuesday
                2: 0.02,    # Wednesday - peak
                3: 0.01,    # Thursday
                4: -0.01,   # Friday - slight drop
                5: 0.0,     # Saturday (if any)
                6: 0.0,     # Sunday (if any)
            }.get(weekday, 0)

            # Add event dips (smooth bell curve down and recovery)
            event_modifier = 0
            for event in events:
                event_start = event['day']
                event_end = event_start + event['duration']
                if event_start <= (days_of_history - day_offset) <= event_end:
                    # Position within event (0 to 1)
                    event_progress = ((days_of_history - day_offset) - event_start) / event['duration']
                    # Bell curve: peaks in middle of event
                    event_modifier -= event['depth'] * math.sin(event_progress * math.pi)

            # Add daily noise (small random variation)
            daily_noise = random.uniform(-0.015, 0.015)

            # Calculate final FPY for this day
            target_fpy = max(0.70, min(0.99, base_fpy + weekly_modifier + event_modifier + daily_noise))

            # Vary reports per day (±30%)
            reports_today = int(reports_per_day_base * random.uniform(0.7, 1.3))

            # Skip weekends for some realism (reduced volume)
            if weekday >= 5:
                reports_today = int(reports_today * 0.3)

            # Generate reports for this day
            pass_count = 0
            for i in range(reports_today):
                # Determine pass/fail based on target FPY
                status = "PASS" if random.random() < target_fpy else "FAIL"
                if status == "PASS":
                    pass_count += 1

                # Pick random part and step (spread across ALL steps with numeric measurements)
                part = random.choice(parts)
                step = random.choice(steps_with_numeric)  # Ensure all steps get SPC data
                selected_equipment = random.choice(equipment)
                operator = self.get_weighted_employee(users)

                # Create timestamp with some hour variation (work hours 6am-6pm)
                hour = random.randint(6, 18)
                minute = random.randint(0, 59)
                qa_time = report_date.replace(hour=hour, minute=minute, second=random.randint(0, 59))

                # Create quality report
                qr = QualityReports.objects.create(
                    tenant=self.tenant,
                    part=part,
                    machine=selected_equipment,
                    step=step,
                    description=f"Historical QA data - {step.name}",
                    sampling_method="statistical",
                    status=status
                )
                qr.operators.add(operator)

                # Backdate to historical date
                QualityReports.objects.filter(pk=qr.pk).update(
                    created_at=qa_time,
                    updated_at=qa_time
                )

                # Create measurement results for SPC data
                self.create_historical_measurements(qr, step, status, qa_time, progress)

                # Create errors and dispositions for failures
                if status == "FAIL":
                    self.create_quality_error_lists_and_dispositions(qr, part.part_type, users, qa_time)

            total_reports += reports_today
            total_pass += pass_count

        actual_fpy = (total_pass / total_reports * 100) if total_reports > 0 else 0
        self.stdout.write(
            f"Created {total_reports} historical quality reports over {days_of_history} days "
            f"(overall FPY: {actual_fpy:.1f}%)"
        )

    def create_historical_measurements(self, qr, step, status, qa_time, progress):
        """
        Create measurement results for SPC charts with realistic process behavior:
        - Process centering improves over time (less bias from nominal)
        - Process variation reduces over time (tighter distribution)
        - Failed parts have measurements outside tolerance
        """
        for measurement_def in step.measurement_definitions.all():
            if measurement_def.type != 'NUMERIC' or not measurement_def.nominal:
                continue

            nominal = float(measurement_def.nominal)
            upper_tol = float(measurement_def.upper_tol or 0)
            lower_tol = float(measurement_def.lower_tol or 0)
            tol_range = upper_tol + abs(lower_tol)

            if tol_range == 0:
                continue

            if status == "PASS":
                # Process improves over time:
                # - Early: centered at nominal + small bias, wider spread (uses 60% of tolerance)
                # - Late: centered at nominal, tighter spread (uses 30% of tolerance)
                bias = (1 - progress) * tol_range * 0.1 * random.choice([-1, 1])  # Bias reduces over time
                spread = tol_range * (0.3 + (1 - progress) * 0.3)  # 60% → 30% of tolerance

                value = nominal + bias + random.gauss(0, spread / 3)  # 3-sigma within spread

                # Clamp to within tolerance (it's a PASS)
                usl = nominal + upper_tol
                lsl = nominal - abs(lower_tol)
                value = max(lsl + 0.001, min(usl - 0.001, value))
            else:
                # FAIL: measurement outside tolerance
                if random.random() < 0.5:
                    # Above USL
                    value = nominal + upper_tol + random.uniform(0.01, tol_range * 0.3)
                else:
                    # Below LSL
                    value = nominal - abs(lower_tol) - random.uniform(0.01, tol_range * 0.3)

            mr = MeasurementResult.objects.create(
                tenant=self.tenant,
                report=qr,
                definition=measurement_def,
                value_numeric=round(value, 4),
                value_pass_fail="PASS" if status == "PASS" else "FAIL",
                is_within_spec=(status == "PASS"),
            )

            # Backdate
            if qa_time:
                MeasurementResult.objects.filter(pk=mr.pk).update(
                    created_at=qa_time,
                    updated_at=qa_time
                )

    def create_capa_demo_data(self, users, config):
        """Create CAPA records from quality failures with full RCA workflow"""
        # Get quality reports that failed - these will trigger CAPAs
        failed_reports = QualityReports.objects.filter(status='FAIL')[:config.get('orders', 10)]

        if not failed_reports.exists():
            self.stdout.write("  No failed quality reports to create CAPAs from")
            return

        capa_count = 0
        severities = ['CRITICAL', 'MAJOR', 'MINOR']
        severity_weights = [0.1, 0.4, 0.5]  # Most are minor/major
        statuses = ['OPEN', 'IN_PROGRESS', 'PENDING_VERIFICATION', 'CLOSED']
        status_weights = [0.2, 0.3, 0.2, 0.3]

        for qr in failed_reports:
            if not qr.part:
                continue

            severity = random.choices(severities, weights=severity_weights)[0]
            status = random.choices(statuses, weights=status_weights)[0]

            # Create CAPA
            capa = CAPA.objects.create(
                tenant=self.tenant,
                capa_type='CORRECTIVE',
                severity=severity,
                status=status,
                problem_statement=f"Quality failure on {qr.part.ERP_id} - {qr.step.name if qr.step else 'Unknown step'}. "
                                 f"CAPA initiated due to quality failure during {qr.step.name if qr.step else 'inspection'}. "
                                 f"Part {qr.part.ERP_id} failed quality check.",
                immediate_action=f"Quarantine affected part {qr.part.ERP_id} pending investigation.",
                part=qr.part,
                step=qr.step,
                work_order=qr.part.work_order,
                initiated_by=self.get_weighted_qa_staff(users),
                initiated_date=timezone.now().date(),
                assigned_to=random.choice(users['managers']) if users.get('managers') else self.get_weighted_employee(users),
                due_date=timezone.now().date() + timedelta(days=random.randint(14, 60)),
            )
            capa.quality_reports.add(qr)

            # Create CAPA tasks
            self.create_capa_tasks(capa, users, status)

            # Create RCA for in-progress or closed CAPAs
            if status in ['IN_PROGRESS', 'PENDING_VERIFICATION', 'CLOSED']:
                self.create_rca_for_capa(capa, users)

            # Create verification for closed CAPAs
            if status == 'CLOSED':
                self.create_capa_verification(capa, users)

            capa_count += 1

        self.stdout.write(f"Created {capa_count} CAPAs with tasks and RCA")

    def create_capa_tasks(self, capa, users, capa_status):
        """Create realistic CAPA tasks"""
        task_templates = [
            ('CONTAINMENT', 'Containment Action', 'Isolate affected parts and prevent further impact'),
            ('CORRECTIVE', 'Corrective Action', 'Implement fix to address root cause'),
            ('PREVENTIVE', 'Preventive Action', 'Implement controls to prevent recurrence'),
        ]

        for task_type, title, description in task_templates:
            # Task status based on CAPA status
            if capa_status == 'OPEN':
                task_status = 'NOT_STARTED'
            elif capa_status == 'IN_PROGRESS':
                task_status = random.choice(['NOT_STARTED', 'IN_PROGRESS'])
            elif capa_status == 'PENDING_VERIFICATION':
                task_status = random.choice(['IN_PROGRESS', 'COMPLETED'])
            else:  # CLOSED
                task_status = 'COMPLETED'

            assignee = self.get_weighted_employee(users)

            CapaTasks.objects.create(
                tenant=self.tenant,
                capa=capa,
                task_type=task_type,
                description=f"{title} - {description} for {capa.capa_number}",
                assigned_to=assignee,
                status=task_status,
                due_date=capa.due_date - timedelta(days=random.randint(1, 7)) if capa.due_date else None,
                completed_date=timezone.now().date() if task_status == 'COMPLETED' else None,
                completed_by=assignee if task_status == 'COMPLETED' else None,
            )

    def create_rca_for_capa(self, capa, users):
        """Create Root Cause Analysis record with 5-Whys or Fishbone"""
        qa_user = self.get_weighted_qa_staff(users)
        is_verified = capa.status in ['PENDING_VERIFICATION', 'CLOSED']

        # Create RCA record
        rca = RcaRecord.objects.create(
            tenant=self.tenant,
            capa=capa,
            rca_method=random.choice(['FIVE_WHYS', 'FISHBONE']),
            problem_description=f"Quality failure investigation for {capa.capa_number}",
            conducted_by=qa_user,
            conducted_date=timezone.now().date(),
            root_cause_summary=f"Root cause identified for {capa.capa_number}",
            root_cause_verification_status='VERIFIED' if is_verified else 'UNVERIFIED',
            root_cause_verified_at=timezone.now() if is_verified else None,
            root_cause_verified_by=qa_user if is_verified else None,
        )
        rca.quality_reports.set(capa.quality_reports.all())

        # Add 5-Whys analysis
        if rca.rca_method == 'FIVE_WHYS':
            FiveWhys.objects.create(
                tenant=self.tenant,
                rca_record=rca,
                why_1_question="Why did the part fail inspection?",
                why_1_answer="Measurement exceeded tolerance limits",
                why_2_question="Why did the measurement exceed limits?",
                why_2_answer="Equipment calibration had drifted",
                why_3_question="Why had calibration drifted?",
                why_3_answer="Preventive maintenance was overdue",
                why_4_question="Why was maintenance overdue?",
                why_4_answer="Maintenance schedule not followed",
                why_5_question="Why wasn't the schedule followed?",
                why_5_answer="No automated reminder system in place",
                identified_root_cause="Lack of automated calibration tracking and reminders",
            )

        # Add Fishbone analysis
        elif rca.rca_method == 'FISHBONE':
            Fishbone.objects.create(
                tenant=self.tenant,
                rca_record=rca,
                problem_statement=f"Quality failure on {capa.capa_number}",
                man_causes=["Operator training gap", "Fatigue during shift"],
                machine_causes=["Calibration drift", "Worn tooling"],
                material_causes=["Incoming material variance", "Supplier batch issue"],
                method_causes=["Outdated work instruction", "Process parameter drift"],
                measurement_causes=["Gauge repeatability", "Environmental factors"],
                environment_causes=["Temperature fluctuation", "Humidity out of spec"],
                identified_root_cause="Multiple contributing factors identified - see 6M analysis",
            )

    def create_capa_verification(self, capa, users):
        """Create CAPA verification record"""
        qa_user = self.get_weighted_qa_staff(users)

        CapaVerification.objects.create(
            tenant=self.tenant,
            capa=capa,
            verification_method="Review of production data and quality reports post-implementation",
            verification_criteria="Zero recurrence of defect type for 30 days and 200+ parts",
            verified_by=qa_user,
            verification_date=timezone.now().date(),
            effectiveness_result='CONFIRMED',
            effectiveness_decided_at=timezone.now(),
            verification_notes="Verified corrective actions effective. No recurrence observed after implementation.",
        )

    def create_company_documents(self, companies, users):
        """Create company-level documents (SOPs, policies, etc.) with revision history."""
        # Get AMBAC (internal company)
        ambac = companies[0]

        doc_configs = [
            ('SOP', 'SOP-001 Quality Manual', ClassificationLevel.INTERNAL, True),  # Has revisions
            ('SOP', 'SOP-002 Receiving Inspection', ClassificationLevel.INTERNAL, True),
            ('WI', 'WI-001 Injector Disassembly', ClassificationLevel.PUBLIC, True),
            ('WI', 'WI-002 Flow Testing Procedure', ClassificationLevel.PUBLIC, False),
            ('POL', 'POL-001 Quality Policy', ClassificationLevel.PUBLIC, True),
            ('FRM', 'FRM-001 Inspection Checklist', ClassificationLevel.INTERNAL, False),
            ('SPEC', 'SPEC-001 Injector Specifications', ClassificationLevel.CONFIDENTIAL, True),
        ]

        doc_count = 0
        revision_count = 0

        for doc_type_code, doc_name, classification, has_revisions in doc_configs:
            try:
                doc_type = DocumentType.objects.get(code=doc_type_code)
            except DocumentType.DoesNotExist:
                continue

            file_name = f"{doc_name.lower().replace(' ', '_')}.pdf"
            uploader = self.get_weighted_employee(users)
            approver = self.get_weighted_qa_staff(users)

            # Base timestamp for document creation (spread over past 6 months)
            base_date = timezone.now() - timedelta(days=random.randint(30, 180))

            if has_revisions:
                # Create revision history: v1 (OBSOLETE) → v2 (OBSOLETE) → v3 (RELEASED)
                num_versions = random.randint(2, 3)
                previous_doc = None

                for version_num in range(1, num_versions + 1):
                    is_current = (version_num == num_versions)
                    version_date = base_date + timedelta(days=(version_num - 1) * random.randint(14, 45))

                    if version_num < num_versions:
                        status = 'OBSOLETE'
                    else:
                        status = 'RELEASED'

                    version_file_name = f"{doc_name.lower().replace(' ', '_')}_v{version_num}.pdf"

                    doc = Documents.objects.create(
                        tenant=self.tenant,
                        document_type=doc_type,
                        classification=classification,
                        is_image=False,
                        file_name=version_file_name,
                        file=ContentFile(f"Content of {doc_name} - Version {version_num}".encode(), name=version_file_name),
                        uploaded_by=uploader,
                        content_type=ContentType.objects.get_for_model(Companies),
                        object_id=ambac.id,
                        status=status,
                        version=version_num,
                        previous_version=previous_doc,
                        is_current_version=is_current,
                        approved_by=approver if status == 'RELEASED' else None,
                        approved_at=version_date + timedelta(days=random.randint(1, 7)) if status == 'RELEASED' else None,
                    )

                    # Backdate the document
                    Documents.objects.filter(pk=doc.pk).update(
                        created_at=version_date,
                        updated_at=version_date + timedelta(days=random.randint(1, 14))
                    )

                    previous_doc = doc
                    doc_count += 1
                    if version_num < num_versions:
                        revision_count += 1
            else:
                # Single version document
                doc = Documents.objects.create(
                    tenant=self.tenant,
                    document_type=doc_type,
                    classification=classification,
                    is_image=False,
                    file_name=file_name,
                    file=ContentFile(f"Content of {doc_name}".encode(), name=file_name),
                    uploaded_by=uploader,
                    content_type=ContentType.objects.get_for_model(Companies),
                    object_id=ambac.id,
                    status='RELEASED',
                    approved_by=approver,
                    approved_at=base_date + timedelta(days=random.randint(1, 7)),
                )

                # Backdate the document
                Documents.objects.filter(pk=doc.pk).update(
                    created_at=base_date,
                    updated_at=base_date + timedelta(days=random.randint(1, 7))
                )
                doc_count += 1

        self.stdout.write(f"Created {doc_count} company-level documents ({revision_count} historical revisions)")

    def create_approval_workflow_demo(self, users):
        """Create approval workflow demo data for documents requiring approval"""
        # Get documents that should have approval workflows
        # SOPs and controlled documents typically require approval
        documents_needing_approval = Documents.objects.filter(
            document_type__requires_approval=True,
            status='RELEASED'
        )[:15]  # Limit to avoid too many

        if not documents_needing_approval.exists():
            self.stdout.write("  No documents requiring approval found")
            return

        # Get approval template for documents
        try:
            doc_template = ApprovalTemplate.objects.get(approval_type='DOCUMENT_RELEASE')
        except ApprovalTemplate.DoesNotExist:
            self.stdout.write("  No DOCUMENT_RELEASE approval template found")
            return

        qa_managers = [u for u in users.get('qa_staff', []) if u.groups.filter(name='QA_Manager').exists()]
        if not qa_managers:
            qa_managers = users.get('managers', users['employees'][:2])

        approval_count = 0
        response_count = 0

        # Status distribution for demo
        status_weights = [
            (Approval_Status_Type.APPROVED, 0.4),
            (Approval_Status_Type.PENDING, 0.35),
            (Approval_Status_Type.REJECTED, 0.15),
            (Approval_Status_Type.CANCELLED, 0.1),
        ]

        for doc in documents_needing_approval:
            status = self.weighted_choice(status_weights)
            requester = doc.uploaded_by or random.choice(users['employees'])

            # Create ApprovalRequest
            approval_request = ApprovalRequest.objects.create(
                tenant=self.tenant,
                approval_number=ApprovalRequest.generate_approval_number(tenant=self.tenant),
                content_type=ContentType.objects.get_for_model(Documents),
                object_id=doc.id,
                approval_type=Approval_Type.DOCUMENT_RELEASE,
                status=status,
                requested_by=requester,
                flow_type=doc_template.approval_flow_type,
                due_date=timezone.now() + timedelta(days=doc_template.default_due_days),
                reason=f"Release approval for {doc.file_name}",
            )

            # Add approvers from QA group (TenantGroup)
            qa_group = TenantGroup.objects.filter(name='QA_Manager', tenant=self.tenant).first()
            if qa_group:
                approval_request.approver_groups.add(qa_group)
            for approver in qa_managers[:2]:
                approval_request.required_approvers.add(approver)

            approval_count += 1

            # Create responses for non-pending approvals
            if status != Approval_Status_Type.PENDING:
                for approver in qa_managers[:2]:
                    if status == Approval_Status_Type.APPROVED:
                        decision = ApprovalDecision.APPROVED
                        comments = "Document reviewed and approved. Content meets quality standards."
                    elif status == Approval_Status_Type.REJECTED:
                        decision = ApprovalDecision.REJECTED
                        comments = "Revisions needed. Please address formatting and technical accuracy."
                    else:  # CANCELLED
                        decision = ApprovalDecision.APPROVED  # Was approved before cancellation
                        comments = "Approved but request was later cancelled."

                    ApprovalResponse.objects.create(
                        tenant=self.tenant,
                        approval_request=approval_request,
                        approver=approver,
                        decision=decision,
                        comments=comments,
                    )
                    response_count += 1

                # Set completed_at for approved/rejected
                if status in [Approval_Status_Type.APPROVED, Approval_Status_Type.REJECTED]:
                    approval_request.completed_at = timezone.now()
                    approval_request.save()

        self.stdout.write(f"Created {approval_count} approval requests with {response_count} responses")

    def create_3d_models_and_annotations(self, part_types, employees):
        """Create 3D benchy models and realistic annotations for each part type."""
        import os
        import shutil
        from django.conf import settings

        self.stdout.write("Creating 3D models and annotations...")

        # Source benchy file from seed_assets (baked into Docker image for airgap deployments)
        source_benchy = os.path.join(settings.BASE_DIR, 'seed_assets', 'models', '3DBenchy.glb')

        # Fallback to media if seed_assets doesn't exist (for backwards compatibility)
        if not os.path.exists(source_benchy):
            source_benchy = os.path.join(settings.MEDIA_ROOT, 'models', '3DBenchyStepFile_dPId9CK.glb')

        # Realistic annotation coordinates on a benchy model (from real data)
        # These are positions in scaled space (model scaled to ~3 units)
        BENCHY_ANNOTATIONS = [
            # Hull area - coating defects
            {'x': 0.4710, 'y': -0.3082, 'z': 0.5955, 'defect_type': 'Coating defects present', 'severity': 'low'},
            {'x': 0.2821, 'y': -0.3059, 'z': 0.5298, 'defect_type': 'Coating defects present', 'severity': 'medium'},
            {'x': 0.2999, 'y': -0.1841, 'z': 0.6156, 'defect_type': 'Coating defects present', 'severity': 'low'},
            {'x': 0.4050, 'y': -0.0024, 'z': -0.1466, 'defect_type': 'Coating defects present', 'severity': 'low'},
            {'x': 0.5941, 'y': -0.2539, 'z': 0.5218, 'defect_type': 'Coating defects present', 'severity': 'low'},
            {'x': 0.3851, 'y': 0.0180, 'z': -0.0699, 'defect_type': 'Coating defects present', 'severity': 'high'},
            {'x': -0.0131, 'y': -0.1376, 'z': 0.5827, 'defect_type': 'Coating defects present', 'severity': 'medium'},
            # Cabin/deck area - layer separation
            {'x': 0.6779, 'y': 0.5497, 'z': -0.6679, 'defect_type': 'Layer separation', 'severity': 'low'},
            {'x': 0.6787, 'y': 0.5377, 'z': -0.6980, 'defect_type': 'Layer separation', 'severity': 'low'},
            {'x': 1.2149, 'y': 0.1190, 'z': -0.6669, 'defect_type': 'Layer separation', 'severity': 'medium'},
            {'x': 0.9073, 'y': 0.5218, 'z': -0.3667, 'defect_type': 'Layer separation', 'severity': 'high'},
            {'x': -0.6264, 'y': 0.5147, 'z': -0.9464, 'defect_type': 'Layer separation', 'severity': 'medium'},
            # Chimney area - dimensional issues
            {'x': -0.2860, 'y': -0.1342, 'z': 1.0418, 'defect_type': 'Dimensional out of tolerance', 'severity': 'high'},
            {'x': -0.1081, 'y': 0.0956, 'z': 1.0661, 'defect_type': 'Dimensional out of tolerance', 'severity': 'medium'},
            {'x': -0.2720, 'y': 0.1473, 'z': 1.1223, 'defect_type': 'Dimensional out of tolerance', 'severity': 'low'},
        ]

        models_created = 0
        annotations_created = 0

        for part_type in part_types:
            # Check if model already exists for this part type
            existing_model = ThreeDModel.objects.filter(part_type=part_type, is_current_version=True).first()
            if existing_model:
                self.stdout.write(f"  Model already exists for {part_type.name}, skipping...")
                continue

            # Create a unique filename for this part type
            safe_name = part_type.name.replace(' ', '_').replace('/', '_')
            dest_filename = f"3DBenchy_{safe_name}.glb"
            dest_path = os.path.join(settings.MEDIA_ROOT, 'models', dest_filename)

            # Ensure models directory exists
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)

            # Copy benchy file if source exists
            if os.path.exists(source_benchy):
                shutil.copy2(source_benchy, dest_path)
            else:
                self.stdout.write(self.style.WARNING(
                    f"  Benchy source file not found. Ensure seed_assets/models/3DBenchy.glb exists."
                ))
                continue

            # Create the ThreeDModel record
            if os.path.exists(dest_path):
                three_d_model = ThreeDModel.objects.create(
                    tenant=self.tenant,
                    name=f"3D Benchy - {part_type.name}",
                    file=f"models/{dest_filename}",
                    part_type=part_type,
                    file_type="glb",
                    is_current_version=True,
                    version=1,
                )
                models_created += 1
                self.stdout.write(f"  Created 3D model for {part_type.name}")

                # Get parts of this type to link annotations to
                parts_of_type = list(Parts.objects.filter(part_type=part_type)[:10])
                if not parts_of_type:
                    self.stdout.write(self.style.WARNING(f"  No parts found for {part_type.name}, skipping annotations"))
                    continue

                # Create annotations for this model
                # Select a random subset (3-6) of annotations for variety
                num_annotations = random.randint(3, 6)
                selected_annotations = random.sample(BENCHY_ANNOTATIONS, min(num_annotations, len(BENCHY_ANNOTATIONS)))

                operator = random.choice(employees)

                for ann_data in selected_annotations:
                    # Pick a random part of this type
                    part = random.choice(parts_of_type)

                    annotation = HeatMapAnnotations.objects.create(
                        tenant=self.tenant,
                        model=three_d_model,
                        part=part,
                        position_x=ann_data['x'],
                        position_y=ann_data['y'],
                        position_z=ann_data['z'],
                        defect_type=ann_data['defect_type'],
                        severity=ann_data['severity'],
                        notes=f"Demo annotation - {ann_data['defect_type']} detected during inspection",
                        created_by=operator,
                    )
                    annotations_created += 1

                    # Link to any quality reports for this part
                    quality_reports = QualityReports.objects.filter(part=part)[:2]
                    if quality_reports.exists():
                        annotation.quality_reports.set(quality_reports)
            else:
                self.stdout.write(self.style.WARNING(f"  Could not find benchy source file for {part_type.name}"))

        self.stdout.write(self.style.SUCCESS(f"Created {models_created} 3D models and {annotations_created} annotations"))

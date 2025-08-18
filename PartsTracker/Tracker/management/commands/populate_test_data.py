import random
from datetime import timedelta, datetime

from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker

from Tracker.models import (Companies, User, PartTypes, Processes, Steps, Orders, Parts, Documents, Equipments,
                            EquipmentType, QualityErrorsList, QualityReports, WorkOrder, SamplingRuleSet, SamplingRule,
                            MeasurementDefinition, MeasurementResult, PartsStatus, OrdersStatus, SamplingTriggerState,
                            SamplingAuditLog, SamplingAnalytics, MeasurementDisposition, ExternalAPIOrderIdentifier,
                            WorkOrderStatus, ClassificationLevel)


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

        # Create realistic user groups
        self.create_realistic_groups()

        # Create realistic companies
        companies = self.create_realistic_companies()

        # Create users with proper roles
        users = self.create_realistic_users(companies, config)

        # Create manufacturing equipment
        equipment = self.create_manufacturing_equipment()

        # Create realistic part types and processes
        part_types = self.create_injector_part_types_and_processes(users['employees'])

        # Create realistic orders with proper timing
        orders = self.create_realistic_orders(companies, users['customers'], config)

        # Create parts with realistic workflows
        self.create_parts_with_workflows(orders, part_types, users, equipment, config)

        # Create external API identifiers
        self.create_external_api_identifiers(orders)

        # Create admin if needed
        self.create_admin_user(companies[0])  # Pass AMBAC company

        self.stdout.write(self.style.SUCCESS(f"Generated realistic {self.scale} scale production data!"))
        self.show_data_summary()

    def clear_data(self):
        """Clear existing data in dependency order"""
        self.stdout.write("Skipping data clearing - no delete operations performed")
        self.stdout.write("Note: You may want to manually clear data if needed")

    def create_realistic_groups(self):
        """Create realistic user groups for manufacturing environment"""
        groups_data = [('Customer', 'External customers who place orders'),
            ('Operator', 'Production floor workers and technicians'), ('Manager', 'Production and operations managers'),
            ('Admin', 'System administrators'), ]

        self.groups = {}
        for name, description in groups_data:
            group, created = Group.objects.get_or_create(name=name)
            self.groups[name.lower()] = group
            if created:
                self.stdout.write(f"  Created group: {name}")

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
            company = Companies.objects.create(name=name, description=f"{desc} - {company_type}",
                hubspot_api_id=f"HS_{company_type}_{len(companies):03d}")
            companies.append(company)

        self.stdout.write(f"Created {len(companies)} realistic companies (including AMBAC)")
        return companies

    def create_realistic_users(self, companies, config):
        """Create realistic users with proper roles and company associations"""
        users = {'customers': [], 'employees': [], 'managers': []}

        # Get AMBAC company (always first in list)
        ambac_company = companies[0]  # AMBAC Manufacturing

        # Create customers from external companies
        for i in range(config['customers']):
            company = random.choice(companies[1:])  # Skip AMBAC (internal company)
            first_name = self.fake.first_name()
            last_name = self.fake.last_name()

            # Create realistic email based on company
            company_domain = company.name.lower().replace(' ', '').replace('.', '').replace(',', '')[:15] + '.com'

            user = User.objects.create_user(first_name=first_name, last_name=last_name,
                username=f"{first_name.lower()}.{last_name.lower()}@{company_domain}", password="password123",
                email=f"{first_name.lower()}.{last_name.lower()}@{company_domain}", parent_company=company,
                is_active=True)
            user.groups.add(self.groups['customer'])
            users['customers'].append(user)

        # Managers (about 15% of employees) - all work for AMBAC
        manager_count = max(2, config['employees'] // 7)
        for i in range(manager_count):
            first_name = self.fake.first_name()
            last_name = self.fake.last_name()

            user = User.objects.create_user(first_name=first_name, last_name=last_name,
                username=f"{first_name.lower()}.{last_name.lower()}", password="password123",
                email=f"{first_name.lower()}.{last_name.lower()}@ambacmanufacturing.com", parent_company=ambac_company,
                is_staff=True, is_active=True)
            user.groups.add(self.groups['manager'])
            users['managers'].append(user)

        # Operators (remaining employees) - all work for AMBAC
        operator_count = config['employees'] - manager_count
        for i in range(operator_count):
            first_name = self.fake.first_name()
            last_name = self.fake.last_name()

            user = User.objects.create_user(first_name=first_name, last_name=last_name,
                username=f"{first_name.lower()}.{last_name.lower()}", password="password123",
                email=f"{first_name.lower()}.{last_name.lower()}@ambacmanufacturing.com", parent_company=ambac_company,
                is_active=True)
            user.groups.add(self.groups['operator'])
            users['employees'].append(user)

        # Include managers in employees list
        users['employees'].extend(users['managers'])

        self.stdout.write(f"Created {len(users['customers'])} customers and {len(users['employees'])} employees")
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
            eq_type, _ = EquipmentType.objects.get_or_create(name=eq_type_name)

            for eq_name in equipment_names:
                eq = Equipments.objects.create(name=eq_name, equipment_type=eq_type)
                equipment.append(eq)

        self.stdout.write(f"Created {len(equipment)} pieces of manufacturing equipment")
        return equipment

    def create_injector_part_types_and_processes(self, employees):
        """Create realistic diesel injector part types with manufacturing processes"""
        part_type_data = [{'name': 'Common Rail Injector', 'prefix': 'CRI', 'processes': [
            {'name': 'Remanufacturing Process', 'is_reman': True,
                'steps': ['Initial Inspection', 'Disassembly', 'Parts Cleaning', 'Component Testing', 'Wear Assessment',
                    'Parts Replacement', 'Assembly', 'Calibration', 'Flow Testing', 'Final QC']},
            {'name': 'New Manufacturing Process', 'is_reman': False,
                'steps': ['Material Receiving', 'Component Fabrication', 'Precision Machining', 'Assembly',
                    'Initial Testing', 'Calibration', 'Flow Testing', 'Final QC']}]},
            {'name': 'Unit Injector', 'prefix': 'UI', 'processes': [
                {'name': 'Remanufacturing Process', 'is_reman': True,
                    'steps': ['Intake Inspection', 'Disassembly', 'Ultrasonic Cleaning', 'Pressure Testing',
                        'Nozzle Replacement', 'Reassembly', 'Electronic Testing', 'Final Validation']},
                {'name': 'New Manufacturing Process', 'is_reman': False,
                    'steps': ['Raw Material Prep', 'Component Manufacturing', 'Quality Inspection', 'Assembly',
                        'Electronic Testing', 'Performance Testing', 'Final QC']}]},
            {'name': 'HEUI Injector', 'prefix': 'HEUI', 'processes': [
                {'name': 'Remanufacturing Process', 'is_reman': True,
                    'steps': ['Visual Inspection', 'Teardown', 'Component Cleaning', 'Hydraulic Testing',
                        'Electrical Testing', 'Rebuild', 'Performance Testing', 'Quality Verification']},
                {'name': 'New Manufacturing Process', 'is_reman': False,
                    'steps': ['Material Sourcing', 'Component Fabrication', 'Hydraulic Assembly', 'Electrical Assembly',
                        'System Testing', 'Final QC']}]}]

        part_types = []
        for pt_data in part_type_data:
            part_type = PartTypes.objects.create(name=pt_data['name'], ID_prefix=pt_data['prefix'])
            part_types.append(part_type)

            for proc_data in pt_data['processes']:
                is_remanufactured = proc_data['is_reman']

                # Remanufacturing typically uses individual part tracking for traceability
                # New manufacturing may use more batch processing
                if is_remanufactured:
                    is_batch = random.random() < 0.2  # 20% chance of batch for reman
                else:
                    is_batch = random.random() < 0.4  # 40% chance of batch for new manufacturing

                process = Processes.objects.create(name=proc_data['name'], is_remanufactured=is_remanufactured,
                    part_type=part_type, num_steps=len(proc_data['steps']), is_batch_process=is_batch)

                # Create steps with realistic measurement definitions
                for order, step_name in enumerate(proc_data['steps'], 1):
                    step = Steps.objects.create(name=step_name, process=process, order=order, part_type=part_type,
                        description=f"{step_name} for {part_type.name}")

                    # Add measurement definitions for ALL steps
                    self.create_measurement_definitions_for_step(step)

        self.stdout.write(f"Created {len(part_types)} part types with realistic processes")
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
            # Default measurements for any other step type
            measurements.extend([
                ('Process Complete', 'PASS_FAIL', '', None, None, None),
                ('Quality Check', 'PASS_FAIL', '', None, None, None),
            ])

        # Create measurement definitions
        for label, type_val, unit, nominal, upper_tol, lower_tol in measurements:
            MeasurementDefinition.objects.create(
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

            order = Orders.objects.create(name=order_number, customer=customer, company=customer.parent_company,
                order_status=status, estimated_completion=estimated_completion,
                created_at=timezone.make_aware(datetime.combine(order_date, datetime.min.time())),
                customer_note=f"Diesel injector remanufacturing order for {customer.parent_company.name}")
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

            order_steps = list(order_process.steps.order_by('order'))
            if not order_steps:
                continue

            # Create sampling rulesets for this order's part type and process
            self.ensure_sampling_rulesets_exist(order_part_type, order_process, order_steps, users['employees'])

            # Determine target step progression for this order (all work orders will be close to this)
            base_target_step_index = self.get_target_step_index(order_steps, order.order_status)

            for wo_index in range(num_work_orders):
                steps = order_steps

                # Determine work order details based on order
                work_order_details = self.determine_work_order_details(order, order_part_type, order_process, wo_index,
                                                                       config)

                # Create work order using proper status
                work_order = WorkOrder.objects.create(ERP_id=work_order_details['erp_id'], related_order=order,
                    expected_completion=work_order_details['expected_completion'],
                    quantity=work_order_details['quantity'], workorder_status=work_order_details['status'])
                total_work_orders += 1

                # Use WorkOrder's create_parts_batch method to generate parts properly
                initial_step = steps[0]
                parts = work_order.create_parts_batch(order_part_type, initial_step, work_order_details['quantity'])

                # Set order reference for parts to match work order's related order
                Parts.objects.filter(id__in=[p.id for p in parts]).update(order=work_order.related_order)

                # Use real batch advancement with variation around base target for similar progression
                # Work orders within same order should be close in step progression
                variation = random.randint(-1, 1)  # Allow ±1 step variation within same order
                target_step_index = max(0, min(len(steps) - 1, base_target_step_index + variation))
                self.advance_work_order_batch(work_order, target_step_index)
                
                # CRITICAL: ALWAYS ensure sampling is properly evaluated after work order creation
                # This makes it impossible for work orders to have zero sampling parts
                work_order._bulk_evaluate_sampling(work_order.parts.all())

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
        processes = list(part_type.processes.all())
        if not processes:
            return None

        # Simply choose randomly from available processes for this part type
        # The remanufactured vs new nature is determined by the process definition itself
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
        """Advance work order batch using real increment_step method"""
        if target_step_index <= 0:
            return  # Already at first step

        # Get any part from the batch to drive advancement
        first_part = work_order.parts.first()
        if not first_part:
            return

        # Use real increment_step method to advance the batch
        for _ in range(target_step_index):
            # Set all parts to ready status
            work_order.parts.filter(step=first_part.step).update(part_status=PartsStatus.READY_FOR_NEXT_STEP)

            # Let increment_step do the real batch advancement
            result = first_part.increment_step()

            if result == "completed_workorder":
                break
            elif result == "marked_ready":
                break  # Can't advance further

            # Refresh the part to get updated step
            first_part.refresh_from_db()

    def ensure_sampling_rulesets_exist(self, part_type, process, steps, employees):
        """Create sampling rulesets for ALL steps"""
        for step in steps:
            ruleset, created = SamplingRuleSet.objects.get_or_create(part_type=part_type, process=process, step=step,
                is_fallback=False,
                defaults={"name": f"QC Rules - {part_type.name} - {step.name}", "origin": "production", "active": True,
                    "created_by": random.choice(employees), "modified_by": random.choice(employees), })

            if created:
                # Create realistic sampling rules based on step type
                rule_configs = self.get_realistic_sampling_rules_for_step(step)
                for rule_config in rule_configs:
                    SamplingRule.objects.create(ruleset=ruleset, rule_type=rule_config['rule_type'],
                        value=rule_config['value'], order=rule_config.get('order', 0),
                        created_by=random.choice(employees), modified_by=random.choice(employees))

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

    def create_quality_report_for_part(self, part, step, users, equipment):
        """Create quality report for a sampled part"""
        # 85% pass rate for realistic data
        status = "PASS" if random.random() < 0.85 else "FAIL"

        qr = QualityReports.objects.create(part=part, machine=random.choice(equipment) if equipment else None,
            step=step,
            description=f"{step.name} results for {part.ERP_id} - {'measurements completed successfully' if status == 'PASS' else 'issues found during testing'}",
            sampling_method="statistical" if random.random() > 0.3 else "manual", status=status)
        qr.operator.add(random.choice(users['employees']))

        # Create quality error lists and dispositions
        self.create_quality_error_lists_and_dispositions(qr, part.part_type, users)

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

                MeasurementResult.objects.create(report=qr, definition=measurement_def, value_numeric=round(value, 4),
                    is_within_spec=is_within_spec, created_by=random.choice(users['employees']))

    def create_admin_user(self, ambac_company):
        """Create admin user if needed"""
        if not User.objects.filter(username="admin").exists():
            admin_user = User.objects.create_superuser(username="admin", email="admin@email.com", password="Annoy1ng",
                first_name="Admin", last_name="User", parent_company=ambac_company)
            # Add to admin group
            admin_user.groups.add(self.groups['admin'])
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
        self.stdout.write(f"Documents: {Documents.objects.count()}")
        self.stdout.write(f"Sampling Analytics: {SamplingAnalytics.objects.count()}")
        self.stdout.write(f"Measurement Dispositions: {MeasurementDisposition.objects.count()}")
        self.stdout.write(f"External API Identifiers: {ExternalAPIOrderIdentifier.objects.count()}")
        self.stdout.write("\nOrder Status Distribution:")
        for status in OrdersStatus.choices:
            count = Orders.objects.filter(order_status=status[0]).count()
            if count > 0:
                self.stdout.write(f"  {status[1]}: {count}")
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
                SamplingAuditLog.objects.create(part=part, rule=first_rule, sampling_decision=part.requires_sampling,
                    ruleset_type='PRIMARY')

        # Create sampling trigger state for work orders
        if part.work_order and part.sampling_ruleset:
            trigger_state, created = SamplingTriggerState.objects.get_or_create(ruleset=part.sampling_ruleset,
                work_order=part.work_order, step=part.step,
                defaults={'active': part.part_status in [PartsStatus.IN_PROGRESS, PartsStatus.AWAITING_QA],
                    'success_count': random.randint(0, 5) if part.part_status == PartsStatus.COMPLETED else 0,
                    'fail_count': random.randint(0, 2), })

            # Add this part to the inspected parts
            trigger_state.parts_inspected.add(part)

        # Create sampling analytics for completed work orders
        if (
                part.work_order and part.sampling_ruleset and part.work_order.workorder_status == WorkOrderStatus.COMPLETED):
            analytics, created = SamplingAnalytics.objects.get_or_create(ruleset=part.sampling_ruleset,
                work_order=part.work_order, defaults={'parts_sampled': random.randint(1, part.work_order.quantity),
                    'parts_total': part.work_order.quantity, 'defects_found': random.randint(0, 2),
                    'actual_sampling_rate': random.uniform(0.1, 0.3), 'target_sampling_rate': 0.2,
                    'variance': random.uniform(-0.05, 0.05)})

    def create_comprehensive_documents(self, part, users):
        """Create various types of documents"""
        doc_types = [('Quality Report', ClassificationLevel.INTERNAL, True),
            ('Process Instructions', ClassificationLevel.PUBLIC, False),
            ('Inspection Photo', ClassificationLevel.INTERNAL, True),
            ('Test Results', ClassificationLevel.CONFIDENTIAL, False), ]

        # Create 1-3 documents per part randomly
        num_docs = random.randint(1, 3)
        doc_type_sample = random.sample(doc_types, min(num_docs, len(doc_types)))

        for doc_name, classification, is_image in doc_type_sample:
            Documents.objects.create(classification=classification, is_image=is_image,
                file_name=f"{doc_name.lower().replace(' ', '_')}_{part.ERP_id}.{'jpg' if is_image else 'pdf'}",
                file=ContentFile(b"Sample document content for " + doc_name.encode(),
                    name=f"{doc_name.lower().replace(' ', '_')}_{part.ERP_id}.{'jpg' if is_image else 'pdf'}"),
                uploaded_by=random.choice(users['employees']), content_type=ContentType.objects.get_for_model(Parts),
                object_id=part.id)

    def create_quality_error_lists_and_dispositions(self, quality_report, part_type, users):
        """Create quality error lists and handle failed measurements"""
        # Create quality error list for this part type if needed
        error_types = ["Surface scratches detected", "Dimensional out of tolerance", "Contamination found",
            "Wear patterns excessive", "Coating defects present"]

        errors = []
        if quality_report.status == "FAIL":
            # Create 1-2 error types for failed reports
            for _ in range(random.randint(1, 2)):
                error_name = random.choice(error_types)
                error, created = QualityErrorsList.objects.get_or_create(error_name=error_name, part_type=part_type,
                    defaults={'error_example': f"Example: {error_name} in {part_type.name}"})
                errors.append(error)

        quality_report.errors.set(errors)

        # Create measurement dispositions for failed measurements
        failed_measurements = quality_report.measurements.filter(is_within_spec=False)
        for measurement in failed_measurements:
            disposition_types = ["QUARANTINE", "REMEASURE", "OVERRIDDEN", "ESCALATED"]
            MeasurementDisposition.objects.create(measurement=measurement,
                disposition_type=random.choice(disposition_types), resolved_by=random.choice(users['employees']),
                notes=f"Disposition for {measurement.definition.label} measurement failure")

    def create_external_api_identifiers(self, orders):
        """Create external API identifiers for orders"""
        # Create some HubSpot stage mappings
        hubspot_stages = ["Initial Contact", "Quote Sent", "Negotiation", "Production", "Quality Check", "Shipped",
            "Completed"]

        for stage in hubspot_stages:
            ExternalAPIOrderIdentifier.objects.get_or_create(stage_name=stage,
                defaults={'API_id': f'HS_STAGE_{stage.upper().replace(" ", "_")}'})

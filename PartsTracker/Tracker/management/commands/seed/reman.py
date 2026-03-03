"""
Remanufacturing seed data: Cores, HarvestedComponents, DisassemblyBOMs.

Creates the core→component→part pipeline fundamental to remanufacturing operations.
"""

import random
import uuid
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone

from Tracker.models import (
    Core, HarvestedComponent, DisassemblyBOMLine,
    PartTypes, Parts, PartsStatus, WorkOrder, WorkOrderStatus, ProcessStep, ProcessStatus,
)
from .base import BaseSeeder


class RemanSeeder(BaseSeeder):
    """
    Seeds remanufacturing-specific data: Cores, HarvestedComponents, DisassemblyBOMs.

    Creates:
    - DisassemblyBOMLines (define expected yields from core types)
    - Cores (incoming used units with realistic distribution)
    - HarvestedComponents (components extracted during disassembly)
    - Parts from usable components (via accept_to_inventory)
    - Auto-entry of usable components into production workflow
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manufacturing_seeder = None  # Set by orchestrator

        # Scale configurations for reman
        self.reman_scale_config = {
            'small': {'cores': 10},
            'medium': {'cores': 30},
            'large': {'cores': 100},
        }

        # Component definitions for Common Rail Injector disassembly
        self.component_definitions = [
            # (component_name, ID_prefix, expected_qty, fallout_rate)
            ('Injector Body', 'BODY', 1, Decimal('0.05')),     # 5% fallout
            ('Plunger Assembly', 'PLGR', 1, Decimal('0.10')),  # 10% fallout
            ('Nozzle', 'NOZL', 1, Decimal('0.15')),            # 15% fallout
            ('Spring Set', 'SPRG', 1, Decimal('0.03')),        # 3% fallout
            ('Solenoid Valve', 'SOLV', 1, Decimal('0.08')),    # 8% fallout
            ('Control Valve', 'CTLV', 1, Decimal('0.12')),     # 12% fallout
        ]

    @property
    def reman_config(self):
        return self.reman_scale_config[self.scale]

    def seed(self, companies, users, part_types):
        """Run the full reman seeding process."""
        # Get or create component part types
        component_types = self._ensure_component_part_types(part_types)

        # Create DisassemblyBOMLines
        bom_lines = self._create_disassembly_bom_lines(part_types, component_types)

        # Create Cores with realistic distribution
        cores = self._create_cores(companies, users, part_types)

        # Create HarvestedComponents from disassembled cores
        harvested = self._create_harvested_components(cores, users, component_types)

        # Accept usable components to inventory and enter production
        parts_created = self._accept_components_to_inventory(harvested, users)

        return {
            'cores': cores,
            'harvested_components': harvested,
            'component_types': component_types,
            'parts_from_reman': parts_created,
        }

    # =========================================================================
    # Component Part Types
    # =========================================================================

    def _ensure_component_part_types(self, existing_part_types):
        """Ensure component part types exist for harvesting."""
        component_types = {}

        for comp_name, prefix, _, _ in self.component_definitions:
            # Check if already exists
            existing = PartTypes.objects.filter(
                tenant=self.tenant,
                name=comp_name
            ).first()

            if existing:
                component_types[comp_name] = existing
            else:
                pt = PartTypes.objects.create(
                    tenant=self.tenant,
                    name=comp_name,
                    ID_prefix=prefix
                )
                component_types[comp_name] = pt

        self.log(f"Ensured {len(component_types)} component part types exist")
        return component_types

    # =========================================================================
    # Disassembly BOM Lines
    # =========================================================================

    def _create_disassembly_bom_lines(self, part_types, component_types):
        """Create DisassemblyBOMLines defining expected yields."""
        bom_lines = []

        # Find the Common Rail Injector part type (core type)
        cri_type = None
        for pt in part_types:
            if 'Common Rail' in pt.name:
                cri_type = pt
                break

        if not cri_type:
            self.log("  Warning: Common Rail Injector part type not found, skipping BOM lines", warning=True)
            return bom_lines

        created_count = 0
        for line_num, (comp_name, prefix, expected_qty, fallout_rate) in enumerate(self.component_definitions, 1):
            comp_type = component_types.get(comp_name)
            if not comp_type:
                continue

            bom_line, created = DisassemblyBOMLine.objects.get_or_create(
                tenant=self.tenant,
                core_type=cri_type,
                component_type=comp_type,
                defaults={
                    'expected_qty': expected_qty,
                    'expected_fallout_rate': fallout_rate,
                    'line_number': line_num,
                    'notes': f"Standard {comp_name} harvest from CRI core"
                }
            )
            bom_lines.append(bom_line)
            if created:
                created_count += 1

        if created_count > 0:
            self.log(f"Created {created_count} DisassemblyBOMLines for CRI core type")
        else:
            self.log(f"DisassemblyBOMLines already exist ({len(bom_lines)} total)")

        return bom_lines

    # =========================================================================
    # Cores
    # =========================================================================

    def _create_cores(self, companies, users, part_types):
        """Create cores with realistic distribution."""
        cores = []
        num_cores = self.reman_config['cores']

        # Find core type (Common Rail Injector)
        core_type = None
        for pt in part_types:
            if 'Common Rail' in pt.name:
                core_type = pt
                break

        if not core_type:
            self.log("  Warning: No core type found, skipping core creation", warning=True)
            return cores

        # Status distribution: 20% received, 30% in_disassembly, 40% disassembled, 10% scrapped
        status_weights = [
            ('received', 0.20),
            ('in_disassembly', 0.30),
            ('disassembled', 0.40),
            ('scrapped', 0.10),
        ]

        # Condition grade distribution: 15% A, 45% B, 30% C, 10% SCRAP
        grade_weights = [
            ('A', 0.15),
            ('B', 0.45),
            ('C', 0.30),
            ('SCRAP', 0.10),
        ]

        # Source distribution: 60% customer_return, 25% purchased, 10% warranty, 5% trade_in
        source_weights = [
            ('customer_return', 0.60),
            ('purchased', 0.25),
            ('warranty', 0.10),
            ('trade_in', 0.05),
        ]

        # Get customers (companies that could return cores)
        customers = [c for c in companies if c.name != 'AMBAC Manufacturing']
        if not customers:
            customers = companies

        employees = users.get('employees', [])
        if not employees:
            self.log("  Warning: No employees available for core creation", warning=True)
            return cores

        created_count = 0
        for i in range(num_cores):
            # Generate backdated received date (past 60 days)
            days_ago = random.randint(1, 60)
            received_date = (timezone.now() - timedelta(days=days_ago)).date()

            # Determine status and grade
            status = self.weighted_choice(status_weights)
            condition_grade = self.weighted_choice(grade_weights)

            # Scrapped cores always have SCRAP grade
            if status == 'scrapped':
                condition_grade = 'SCRAP'
            # SCRAP grade cores should be scrapped
            if condition_grade == 'SCRAP' and status != 'scrapped':
                status = 'scrapped'

            source_type = self.weighted_choice(source_weights)
            customer = random.choice(customers) if customers else None

            # Generate core number
            core_number = f"CORE-{received_date.strftime('%y%m%d')}-{i+1:04d}"

            # Check if already exists
            existing = Core.objects.filter(
                tenant=self.tenant,
                core_number=core_number
            ).first()

            if existing:
                cores.append(existing)
                continue

            # Generate source reference based on type
            if source_type == 'customer_return':
                source_ref = f"RMA-{random.randint(10000, 99999)}"
            elif source_type == 'purchased':
                source_ref = f"PO-{random.randint(10000, 99999)}"
            elif source_type == 'warranty':
                source_ref = f"WTY-{random.randint(10000, 99999)}"
            else:
                source_ref = f"TI-{random.randint(10000, 99999)}"

            # Generate credit value based on grade
            credit_values = {'A': (150, 200), 'B': (100, 150), 'C': (50, 100), 'SCRAP': (0, 0)}
            credit_range = credit_values.get(condition_grade, (50, 100))
            credit_value = Decimal(random.randint(*credit_range)) if credit_range[1] > 0 else None

            received_by = random.choice(employees)

            core = Core.objects.create(
                tenant=self.tenant,
                core_number=core_number,
                serial_number=f"SN-{uuid.uuid4().hex[:8].upper()}",
                core_type=core_type,
                received_date=received_date,
                received_by=received_by,
                customer=customer,
                source_type=source_type,
                source_reference=source_ref,
                condition_grade=condition_grade,
                condition_notes=self._generate_condition_notes(condition_grade),
                status='received',  # Start as received, will update below
                core_credit_value=credit_value,
            )

            # Backdate the created_at
            received_datetime = timezone.make_aware(
                timezone.datetime.combine(received_date, timezone.datetime.min.time())
            ) + timedelta(hours=random.randint(8, 16))
            Core.objects.filter(pk=core.pk).update(created_at=received_datetime)

            # Progress status with timestamps
            if status in ['in_disassembly', 'disassembled', 'scrapped']:
                disassembly_start = received_datetime + timedelta(hours=random.randint(2, 48))
                Core.objects.filter(pk=core.pk).update(
                    status='in_disassembly' if status != 'scrapped' else 'scrapped',
                    disassembly_started_at=disassembly_start
                )

            if status == 'disassembled':
                disassembly_complete = received_datetime + timedelta(hours=random.randint(4, 72))
                Core.objects.filter(pk=core.pk).update(
                    status='disassembled',
                    disassembly_completed_at=disassembly_complete,
                    disassembled_by=random.choice(employees)
                )

            if status == 'scrapped':
                Core.objects.filter(pk=core.pk).update(status='scrapped')

            core.refresh_from_db()
            cores.append(core)
            created_count += 1

        self.log(f"Created {created_count} cores with realistic status distribution")

        # Log distribution
        status_counts = {}
        for core in cores:
            status_counts[core.status] = status_counts.get(core.status, 0) + 1
        self.log(f"  Core status distribution: {status_counts}")

        return cores

    def _generate_condition_notes(self, grade):
        """Generate realistic condition notes based on grade."""
        notes_by_grade = {
            'A': [
                "Excellent condition. Minor cosmetic wear only.",
                "Very clean. No visible damage or corrosion.",
                "Minimal wear. All components present.",
            ],
            'B': [
                "Good condition with normal wear patterns.",
                "Light corrosion on external surfaces. Internals good.",
                "Some carbon buildup. Standard cleaning required.",
            ],
            'C': [
                "Fair condition. Heavy wear on nozzle tip.",
                "Significant corrosion. May have high fallout.",
                "Carbon deposits present. Requires aggressive cleaning.",
            ],
            'SCRAP': [
                "Severe damage. Cracked body - not salvageable.",
                "Heavy corrosion damage throughout. Scrap only.",
                "Missing components. Cannot be disassembled.",
            ],
        }
        return random.choice(notes_by_grade.get(grade, ["Standard condition."]))

    # =========================================================================
    # Harvested Components
    # =========================================================================

    def _create_harvested_components(self, cores, users, component_types):
        """Create harvested components from disassembled cores."""
        harvested = []
        employees = users.get('employees', [])
        if not employees:
            return harvested

        # Only create components from cores that are in_disassembly or disassembled
        processable_cores = [c for c in cores if c.status in ['in_disassembly', 'disassembled']]

        # Grade distribution: 20% A, 50% B, 25% C, 5% SCRAP
        grade_weights = [
            ('A', 0.20),
            ('B', 0.50),
            ('C', 0.25),
            ('SCRAP', 0.05),
        ]

        created_count = 0
        for core in processable_cores:
            # Get BOM lines for this core type
            bom_lines = DisassemblyBOMLine.objects.filter(
                tenant=self.tenant,
                core_type=core.core_type
            )

            # If no BOM lines, create 4-6 random components
            if not bom_lines.exists():
                num_components = random.randint(4, 6)
                available_types = list(component_types.values())
                for i in range(min(num_components, len(available_types))):
                    comp_type = available_types[i]
                    harvested.extend(
                        self._create_component_for_core(
                            core, comp_type, employees, grade_weights, i
                        )
                    )
                    created_count += 1
            else:
                # Use BOM lines to create expected components
                for bom_line in bom_lines:
                    # Apply fallout rate to determine if component is scrapped
                    is_fallout = random.random() < float(bom_line.expected_fallout_rate)

                    for qty in range(bom_line.expected_qty):
                        # Check if already exists
                        existing = HarvestedComponent.objects.filter(
                            tenant=self.tenant,
                            core=core,
                            component_type=bom_line.component_type,
                            position=f"Pos-{qty+1}" if bom_line.expected_qty > 1 else ""
                        ).first()

                        if existing:
                            harvested.append(existing)
                            continue

                        if is_fallout:
                            grade = 'SCRAP'
                        else:
                            grade = self.weighted_choice(grade_weights)

                        hc = HarvestedComponent.objects.create(
                            tenant=self.tenant,
                            core=core,
                            component_type=bom_line.component_type,
                            disassembled_by=random.choice(employees),
                            condition_grade=grade,
                            condition_notes=self._generate_component_condition_notes(grade),
                            is_scrapped=(grade == 'SCRAP'),
                            scrap_reason="Fallout - exceeded wear limits" if grade == 'SCRAP' else "",
                            position=f"Pos-{qty+1}" if bom_line.expected_qty > 1 else "",
                        )

                        # Backdate to match core disassembly
                        if core.disassembly_started_at:
                            hc_time = core.disassembly_started_at + timedelta(minutes=random.randint(10, 120))
                            HarvestedComponent.objects.filter(pk=hc.pk).update(
                                disassembled_at=hc_time,
                                created_at=hc_time
                            )

                        if grade == 'SCRAP':
                            HarvestedComponent.objects.filter(pk=hc.pk).update(
                                scrapped_at=hc_time if core.disassembly_started_at else timezone.now(),
                                scrapped_by=random.choice(employees)
                            )

                        hc.refresh_from_db()
                        harvested.append(hc)
                        created_count += 1

        self.log(f"Created {created_count} harvested components")

        # Log grade distribution
        grade_counts = {}
        for hc in harvested:
            grade_counts[hc.condition_grade] = grade_counts.get(hc.condition_grade, 0) + 1
        self.log(f"  Component grade distribution: {grade_counts}")

        return harvested

    def _create_component_for_core(self, core, comp_type, employees, grade_weights, position):
        """Create a single component for a core (fallback when no BOM)."""
        grade = self.weighted_choice(grade_weights)

        hc = HarvestedComponent.objects.create(
            tenant=self.tenant,
            core=core,
            component_type=comp_type,
            disassembled_by=random.choice(employees),
            condition_grade=grade,
            condition_notes=self._generate_component_condition_notes(grade),
            is_scrapped=(grade == 'SCRAP'),
            scrap_reason="Condition assessment - not usable" if grade == 'SCRAP' else "",
            position=f"Position {position + 1}",
        )

        return [hc]

    def _generate_component_condition_notes(self, grade):
        """Generate realistic component condition notes."""
        notes_by_grade = {
            'A': [
                "Excellent. Ready for reuse without rework.",
                "Pristine condition. Passes all dimensional checks.",
                "Minimal wear. Within all tolerances.",
            ],
            'B': [
                "Good condition. Minor surface wear acceptable.",
                "Standard wear patterns. Suitable for rework.",
                "Light carbon deposits. Cleaning required.",
            ],
            'C': [
                "Fair condition. Near tolerance limits.",
                "Significant wear. Requires reconditioning.",
                "Heavy deposits. Aggressive cleaning needed.",
            ],
            'SCRAP': [
                "Cracked - cannot be repaired.",
                "Exceeded maximum wear limits.",
                "Corrosion damage too severe.",
            ],
        }
        return random.choice(notes_by_grade.get(grade, ["Standard condition."]))

    # =========================================================================
    # Accept to Inventory and Enter Production
    # =========================================================================

    def _accept_components_to_inventory(self, harvested_components, users):
        """Accept usable components to inventory and enter production."""
        parts_created = []
        employees = users.get('employees', [])
        if not employees:
            return parts_created

        # Only process non-scrapped components that don't already have a part
        usable = [hc for hc in harvested_components
                  if not hc.is_scrapped and not hc.component_part]

        for hc in usable:
            try:
                # Generate ERP ID: HC-{core_number}-{component_prefix}{seq}
                short_id = str(hc.pk).replace('-', '')[:8].upper()
                erp_id = f"HC-{hc.core.core_number}-{hc.component_type.ID_prefix or 'P'}{short_id}"

                part = hc.accept_to_inventory(
                    user=random.choice(employees),
                    erp_id=erp_id,
                    transfer_life=True
                )

                parts_created.append(part)

            except ValueError as e:
                # Component already accepted or scrapped
                continue

        # Auto-enter into production workflow
        parts_entered = self._enter_parts_into_production(parts_created, users)

        self.log(f"Accepted {len(parts_created)} components to inventory")
        self.log(f"  Entered {parts_entered} parts into production workflow")

        return parts_created

    def _enter_parts_into_production(self, parts, users):
        """
        Assign parts to work orders and progress through remanufacturing workflow.

        Creates realistic workflow progression with:
        - StepExecution records
        - QualityReports at decision points
        - Rework loops for some parts
        """
        if not parts:
            return 0

        employees = users.get('employees', [])
        entered_count = 0
        progressed_count = 0

        # Find available work orders with IN_PROGRESS status
        available_work_orders = list(WorkOrder.objects.filter(
            tenant=self.tenant,
            workorder_status=WorkOrderStatus.IN_PROGRESS
        ).select_related('process'))

        if not available_work_orders:
            return 0

        from Tracker.models import StepExecution

        for part in parts:
            # Randomly decide if this part enters production immediately (70% chance)
            if random.random() > 0.70:
                continue

            # Find a work order with a reman process
            matching_wo = None
            for wo in available_work_orders:
                if wo.process and wo.process.is_remanufactured:
                    matching_wo = wo
                    break

            if not matching_wo and available_work_orders:
                matching_wo = random.choice(available_work_orders)

            if not matching_wo:
                continue

            # Get process steps
            process_steps = ProcessStep.objects.filter(
                process=matching_wo.process
            ).select_related('step').order_by('order')

            if not process_steps.exists():
                continue

            steps = [ps.step for ps in process_steps]
            first_step = steps[0]

            # Assign part to work order
            part.work_order = matching_wo
            part.order = matching_wo.related_order
            part.step = first_step
            part.part_status = PartsStatus.PENDING
            part.save()
            entered_count += 1

            # Progress part through workflow (30-80% through process)
            target_progress = random.uniform(0.3, 0.8)
            target_idx = int(len(steps) * target_progress)
            target_idx = max(1, min(len(steps) - 2, target_idx))  # Not first or last

            # Get base timestamp from harvested component
            harvested_from = getattr(part, 'harvested_from', None)
            if harvested_from and hasattr(harvested_from, 'disassembled_at'):
                base_timestamp = harvested_from.disassembled_at + timedelta(hours=random.randint(2, 24))
            else:
                base_timestamp = timezone.now() - timedelta(days=random.randint(1, 30))

            # Progress through steps with StepExecution records
            self._progress_reman_part(part, steps, target_idx, base_timestamp, employees)
            progressed_count += 1

        self.log(f"  Progressed {progressed_count} reman parts through workflow")
        return entered_count

    def _progress_reman_part(self, part, steps, target_idx, base_timestamp, employees):
        """
        Progress a reman part through workflow using increment_step().

        Uses the workflow engine for ALL advancement to ensure:
        - Proper StepExecution records
        - QualityReports at decision points
        - Correct routing based on PASS/FAIL
        - Rework loop handling
        """
        from Tracker.models import StepExecution, QualityReports, PartsStatus

        current_time = base_timestamp
        advancement_count = 0
        max_advancements = target_idx + 10  # Allow extra for rework loops
        visits_at_step = {}

        while advancement_count < max_advancements:
            part.refresh_from_db()
            current_step = part.step

            if not current_step:
                break

            if part.part_status in [PartsStatus.COMPLETED, PartsStatus.SCRAPPED, PartsStatus.CANCELLED]:
                break

            step_id = current_step.id
            visits_at_step[step_id] = visits_at_step.get(step_id, 0) + 1

            # Calculate timestamps for this step
            step_duration = timedelta(hours=random.uniform(0.5, 4))
            entry_time = current_time
            started_at = entry_time + timedelta(minutes=random.randint(1, 15))
            operator = random.choice(employees) if employees else None

            # Create StepExecution for this visit
            execution = StepExecution.objects.create(
                tenant=part.tenant,
                part=part,
                step=current_step,
                visit_number=visits_at_step[step_id],
                entered_at=entry_time,
                exited_at=None,  # Will be set when we advance
                started_at=started_at,
                assigned_to=operator,
                status='in_progress',
            )

            # Handle decision points - ALWAYS create QualityReport
            decision_result = None
            if current_step.is_decision_point:
                # Calculate pass rate with rework penalty
                base_fail_rate = 0.15
                rework_penalty = 0.08 * (visits_at_step[step_id] - 1)
                fail_rate = min(0.50, base_fail_rate + rework_penalty)
                passed = random.random() > fail_rate
                decision_result = 'PASS' if passed else 'FAIL'

                QualityReports.objects.create(
                    tenant=self.tenant,
                    part=part,
                    step=current_step,
                    status=decision_result,
                    description=f"Reman QA at {current_step.name} - Visit #{visits_at_step[step_id]}",
                    sampling_method='statistical',
                    detected_by=operator,
                )

            # Set part status based on decision outcome
            if decision_result == 'FAIL':
                part.part_status = PartsStatus.REWORK_NEEDED
            else:
                part.part_status = PartsStatus.READY_FOR_NEXT_STEP
            part.save(update_fields=['part_status'])

            # Use workflow engine to advance
            try:
                increment_result = part.increment_step(decision_result=decision_result)
            except ValueError:
                try:
                    increment_result = part.increment_step(decision_result='default')
                except ValueError:
                    break  # Can't advance

            # Close the execution record
            exit_time = current_time + step_duration
            StepExecution.objects.filter(pk=execution.pk).update(
                exited_at=exit_time,
                completed_by=operator,
                status='completed'
            )

            advancement_count += 1
            current_time = exit_time + timedelta(minutes=random.randint(10, 60))

            if increment_result == "completed":
                break
            elif increment_result == "marked_ready":
                break

            # Check if we've reached target depth (but continue through rework)
            part.refresh_from_db()
            if part.step:
                current_idx = next((i for i, s in enumerate(steps) if s.id == part.step.id), -1)
                if current_idx >= target_idx and part.step.step_type != 'rework':
                    break

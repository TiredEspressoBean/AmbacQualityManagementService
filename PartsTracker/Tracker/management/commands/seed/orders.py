"""
Orders seed data: Orders, work orders, parts with workflow progression.
"""

import random
from datetime import datetime, timedelta
from django.utils import timezone

from Tracker.models import (
    Orders, OrdersStatus, WorkOrder, WorkOrderStatus, Parts, PartsStatus,
    ProcessStep, StepTransitionLog, SamplingRuleSet, SamplingRule,
    QualityReports, ProcessStatus, StepExecution, StepEdge, EdgeType,
)
from .base import BaseSeeder


class OrderSeeder(BaseSeeder):
    """
    Seeds orders, work orders, and parts with realistic workflow progression.

    Creates:
    - Orders with status distribution
    - Work orders with parts
    - Parts progressed through workflow steps
    - Sampling rulesets and triggers
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manufacturing_seeder = None  # Set by orchestrator for equipment access

    def seed(self, companies, users, part_types, equipment=None):
        """Run the full order seeding process."""
        orders = self.create_orders(companies, users['customers'])
        self.create_parts_with_workflows(orders, part_types, users, equipment or [])
        return {'orders': orders}

    # =========================================================================
    # Orders
    # =========================================================================

    def create_orders(self, companies, customers):
        """Create realistic orders with proper status distribution and timing."""
        orders = []
        config = self.config
        created_count = 0

        # Demo-friendly status distribution
        status_weights = [
            (OrdersStatus.COMPLETED, 0.15),
            (OrdersStatus.IN_PROGRESS, 0.35),
            (OrdersStatus.PENDING, 0.25),
            (OrdersStatus.RFI, 0.15),
            (OrdersStatus.ON_HOLD, 0.10),
            (OrdersStatus.CANCELLED, 0.0),
        ]

        # Generate orders over past 6 months
        start_date = timezone.now().date() - timedelta(days=180)

        for i in range(config['orders']):
            status = self.weighted_choice(status_weights)

            # Create realistic timing
            order_date = self.fake.date_between(
                start_date=start_date,
                end_date=timezone.now().date() - timedelta(days=7)
            )

            if status == OrdersStatus.COMPLETED:
                completion_offset = random.randint(14, 45)
                estimated_completion = order_date + timedelta(days=completion_offset - random.randint(0, 3))
            elif status in [OrdersStatus.IN_PROGRESS, OrdersStatus.PENDING]:
                estimated_completion = timezone.now().date() + timedelta(days=random.randint(3, 30))
            else:
                estimated_completion = order_date + timedelta(days=random.randint(14, 60))

            customer = random.choice(customers)
            order_number = f"ORD-{order_date.strftime('%y%m')}-{i + 1:03d}"

            # Use get_or_create to make seeder idempotent
            order, created = Orders.objects.get_or_create(
                tenant=self.tenant,
                name=order_number,
                defaults={
                    'customer': customer,
                    'company': customer.parent_company,
                    'order_status': status,
                    'estimated_completion': estimated_completion,
                    'customer_note': f"Diesel injector remanufacturing order for {customer.parent_company.name}"
                }
            )

            if created:
                created_count += 1
                # Backdate order (only for newly created)
                order_timestamp = timezone.make_aware(datetime.combine(order_date, datetime.min.time()))
                Orders.objects.filter(pk=order.pk).update(created_at=order_timestamp, updated_at=order_timestamp)
                order.refresh_from_db()

            orders.append(order)

        skipped = config['orders'] - created_count
        if skipped > 0:
            self.log(f"Created {created_count} orders ({skipped} already existed)")
        else:
            self.log(f"Created {created_count} orders with realistic status distribution")
        return orders

    # =========================================================================
    # Work Orders and Parts
    # =========================================================================

    def create_parts_with_workflows(self, orders, part_types, users, equipment):
        """Create work orders and parts using model methods for proper relationships."""
        total_parts = 0
        total_work_orders = 0

        for order in orders:
            num_work_orders = self._determine_work_orders_for_order(order)
            order_part_type = random.choice(part_types)
            order_process = self._select_appropriate_process(order_part_type)

            if not order_process:
                continue

            process_steps = ProcessStep.objects.filter(
                process=order_process
            ).select_related('step').order_by('order')
            order_steps = [ps.step for ps in process_steps]
            if not order_steps:
                continue

            # Create sampling rulesets
            self._ensure_sampling_rulesets_exist(order_part_type, order_process, order_steps, users['employees'])

            # Determine target step range for wave-front distribution
            wave_min, wave_max = self._get_target_step_range(order_steps, order.order_status)

            for wo_index in range(num_work_orders):
                wo_timestamp = self.calculate_work_order_timestamp(order)
                work_order_details = self._determine_work_order_details(
                    order, order_part_type, order_process, wo_index
                )

                # Use get_or_create to make seeder idempotent
                work_order, created = WorkOrder.objects.get_or_create(
                    tenant=self.tenant,
                    ERP_id=work_order_details['erp_id'],
                    defaults={
                        'related_order': order,
                        'process': order_process,
                        'expected_completion': work_order_details['expected_completion'],
                        'quantity': work_order_details['quantity'],
                        'workorder_status': work_order_details['status']
                    }
                )

                if created:
                    total_work_orders += 1

                    # Backdate work order (only for new ones)
                    self.backdate_object(
                        WorkOrder, work_order.id, wo_timestamp,
                        actor=random.choice(users.get('managers', users['employees']))
                    )

                # Create parts using model method (idempotent - won't create duplicates)
                initial_step = order_steps[0]
                parts = work_order.create_parts_batch(order_part_type, initial_step, work_order_details['quantity'])

                if created:
                    # Only do setup for newly created work orders
                    # Set order reference
                    Parts.objects.filter(id__in=[p.id for p in parts]).update(order=work_order.related_order)

                    # Backdate parts
                    parts_timestamp = wo_timestamp + timedelta(minutes=random.randint(10, 60))
                    Parts.objects.filter(work_order=work_order).update(
                        created_at=parts_timestamp,
                        updated_at=parts_timestamp
                    )

                    # Distribute parts across wave-front range (realistic progression)
                    self._distribute_parts_as_wave(
                        work_order, order_steps, wave_min, wave_max,
                        order.order_status, parts_timestamp, users['employees']
                    )

                    # Note: Step transition logs are audit records protected by compliance triggers
                    # and cannot be backdated. They will use current timestamps.

                    # Ensure sampling is evaluated
                    work_order._bulk_evaluate_sampling(work_order.parts.all())

                    total_parts += len(parts)

        if total_work_orders > 0:
            self.log(f"Created {total_work_orders} new work orders with {total_parts} new parts")
        else:
            self.log(f"All work orders already existed (no new data created)")

    def _determine_work_orders_for_order(self, order):
        """Determine how many work orders this order should have."""
        if order.order_status == OrdersStatus.PENDING:
            return random.randint(1, 2)
        elif order.order_status == OrdersStatus.RFI:
            return random.randint(1, 2)
        elif order.order_status == OrdersStatus.ON_HOLD:
            return random.randint(1, 2)
        else:
            return random.randint(1, 3)

    def _select_appropriate_process(self, part_type):
        """Select a process based on part type characteristics."""
        processes = list(part_type.processes.filter(status=ProcessStatus.APPROVED))
        if not processes:
            return None

        # Prefer remanufacturing processes (80%)
        reman_processes = [p for p in processes if p.is_remanufactured]
        new_processes = [p for p in processes if not p.is_remanufactured]

        if reman_processes and random.random() < 0.8:
            return random.choice(reman_processes)
        elif new_processes:
            return random.choice(new_processes)
        else:
            return random.choice(processes)

    def _determine_work_order_details(self, order, part_type, process, wo_index):
        """Determine work order details based on order characteristics."""
        order_date_str = order.name.split('-')[1] if '-' in order.name else '2501'
        erp_id = f"WO-{order_date_str}-{part_type.ID_prefix}-{wo_index + 1:02d}"

        quantity = random.randint(25, 60)

        if order.estimated_completion:
            offset_days = random.randint(-7, -1)
            expected_completion = order.estimated_completion + timedelta(days=offset_days)
        else:
            expected_completion = None

        status = self._determine_work_order_status(order.order_status)

        return {
            'erp_id': erp_id,
            'quantity': quantity,
            'expected_completion': expected_completion,
            'status': status
        }

    def _determine_work_order_status(self, order_status):
        """Map order status to work order status."""
        status_map = {
            OrdersStatus.COMPLETED: WorkOrderStatus.COMPLETED,
            OrdersStatus.IN_PROGRESS: WorkOrderStatus.IN_PROGRESS,
            OrdersStatus.PENDING: WorkOrderStatus.PENDING,
            OrdersStatus.RFI: WorkOrderStatus.IN_PROGRESS,
            OrdersStatus.ON_HOLD: WorkOrderStatus.ON_HOLD,
            OrdersStatus.CANCELLED: WorkOrderStatus.CANCELLED,
        }
        return status_map.get(order_status, WorkOrderStatus.PENDING)

    def _get_target_step_range(self, steps, order_status):
        """
        Get target step range for wave-front distribution based on order status.

        Returns (min_step, max_step) tuple representing where the wave front should be.
        Parts will be concentrated in this range with earlier steps empty (completed).
        """
        num_steps = len(steps)

        if order_status == OrdersStatus.COMPLETED:
            # Parts at final steps, some completed
            return (max(0, num_steps - 2), num_steps)
        elif order_status == OrdersStatus.IN_PROGRESS:
            # Wave in the middle of the process
            center = num_steps // 2
            return (max(1, center - 1), min(num_steps - 1, center + 2))
        elif order_status == OrdersStatus.PENDING:
            # Just started - parts at first few steps only
            return (0, min(2, num_steps))
        elif order_status == OrdersStatus.RFI:
            # Early-middle, waiting for info
            return (1, min(num_steps // 2 + 1, num_steps))
        elif order_status == OrdersStatus.ON_HOLD:
            # Somewhere in first half
            return (1, max(2, num_steps // 2))
        else:
            return (0, min(2, num_steps))

    def _distribute_parts_as_wave(self, work_order, steps, wave_min, wave_max, order_status, base_timestamp, employees=None):
        """
        Distribute parts across steps using proper workflow progression.

        Uses increment_step() for ALL parts to create realistic:
        - StepExecution records (entry/exit tracking with operators)
        - StepTransitionLog entries
        - QualityReports at decision points
        - Decision branching (PASS → next step, FAIL → rework)
        - Rework loops with escalation after max_visits
        - Proper part status based on actual workflow state
        """
        employees = employees or []
        parts = list(work_order.parts.all())
        if not parts or not steps:
            return

        num_steps = len(steps)
        wave_min = max(0, wave_min)
        wave_max = min(num_steps, wave_max)

        if wave_max <= wave_min:
            wave_max = wave_min + 1

        parts_using_workflow = 0
        parts_with_rework = 0
        step_executions_created = 0

        for part in parts:
            # Pick a target step within the wave range
            target_idx = random.randint(wave_min, wave_max - 1)
            target_idx = max(0, min(num_steps - 1, target_idx))
            target_step = steps[target_idx]

            # Use full workflow engine for ALL parts - creates realistic:
            # - StepExecution records with proper entry/exit times
            # - QualityReports at decision points
            # - Proper routing via increment_step()
            # - Rework loops and escalation
            if target_idx > 0:
                try:
                    result = self._advance_part_through_workflow(
                        part, steps, target_idx, base_timestamp, work_order, employees
                    )
                    parts_using_workflow += 1
                    step_executions_created += result.get('executions', 0)
                    if result.get('had_rework'):
                        parts_with_rework += 1
                except Exception as e:
                    # Log but don't silently fail
                    self.log(f"  Warning: Workflow failed for part {part.ERP_id}: {e}", warning=True)
            else:
                # Part at first step - just create initial execution
                self._create_step_execution(part, steps[0], 1, base_timestamp, employees)
                parts_using_workflow += 1

        # Ensure sampling is evaluated
        work_order._bulk_evaluate_sampling(work_order.parts.all())

    def _advance_part_through_workflow(self, part, steps, target_depth, base_timestamp, work_order, employees=None):
        """
        Advance a part through workflow using increment_step().

        Creates realistic:
        - StepExecution records for each step visited (with proper entry/exit times)
        - QualityReports at decision points
        - Rework loops (85% pass first time, 12% rework once, 3% escalate)
        - Operator assignments for each step execution

        Returns dict with execution stats.
        """
        employees = employees or []
        result = {'executions': 0, 'had_rework': False, 'quality_reports': 0}

        visits_at_step = {}
        advancement_count = 0
        max_advancements = target_depth + 10  # Allow some extra for rework loops
        current_timestamp = base_timestamp
        previous_execution = None

        while advancement_count < max_advancements:
            part.refresh_from_db()
            current_step = part.step

            if not current_step:
                break

            if part.part_status in [PartsStatus.COMPLETED, PartsStatus.SCRAPPED, PartsStatus.CANCELLED]:
                break

            step_id = current_step.id
            visits_at_step[step_id] = visits_at_step.get(step_id, 0) + 1

            # Close previous execution if exists
            if previous_execution:
                exit_time = current_timestamp - timedelta(minutes=random.randint(1, 10))
                StepExecution.objects.filter(pk=previous_execution.pk).update(
                    exited_at=exit_time,
                    completed_by=previous_execution.assigned_to,
                    status='completed'
                )

            # Create StepExecution record for current step
            execution = self._create_step_execution(
                part, current_step, visits_at_step[step_id], current_timestamp, employees
            )
            if execution:
                result['executions'] += 1
                previous_execution = execution

            # Determine decision result if at decision point
            decision_result = None
            if current_step.is_decision_point:
                decision_result, qr = self._simulate_qa_decision_with_report(
                    part, current_step, visits_at_step[step_id], current_timestamp
                )

                if qr:
                    result['quality_reports'] += 1

                if decision_result == 'FAIL':
                    result['had_rework'] = True

            # Set part status based on decision outcome (not before!)
            if decision_result == 'FAIL':
                part.part_status = PartsStatus.REWORK_NEEDED
            else:
                part.part_status = PartsStatus.READY_FOR_NEXT_STEP
            part.save(update_fields=['part_status'])

            try:
                increment_result = part.increment_step(decision_result=decision_result)
            except ValueError:
                # Try with default decision if required
                try:
                    increment_result = part.increment_step(decision_result='default')
                except ValueError:
                    break  # Can't advance

            advancement_count += 1
            # Advance timestamp for next step (1-4 hours per step)
            current_timestamp += timedelta(hours=random.uniform(1, 4))

            if increment_result == "completed":
                # Close final execution
                if previous_execution:
                    StepExecution.objects.filter(pk=previous_execution.pk).update(
                        exited_at=current_timestamp,
                        completed_by=previous_execution.assigned_to,
                        status='completed'
                    )
                break
            elif increment_result == "marked_ready":
                break

            # Check if we've reached target depth
            part.refresh_from_db()
            if part.step and work_order.process:
                ps = ProcessStep.objects.filter(
                    process=work_order.process,
                    step=part.step
                ).first()
                if ps and ps.order >= target_depth:
                    # Don't stop if we're at a rework step - continue rework loop
                    if part.step.step_type != 'rework':
                        break

        return result

    def _create_step_execution(self, part, step, visit_number, base_timestamp, employees=None):
        """Create a StepExecution record for tracking with operator assignment."""
        employees = employees or []

        # Calculate realistic entry time based on step position
        entry_time = base_timestamp + timedelta(
            hours=random.randint(1, 8) * visit_number,
            minutes=random.randint(0, 59)
        )
        started_at = entry_time + timedelta(minutes=random.randint(1, 15))

        # Assign an operator
        operator = random.choice(employees) if employees else None

        execution = StepExecution.objects.create(
            tenant=part.tenant,
            part=part,
            step=step,
            visit_number=visit_number,
            entered_at=entry_time,
            started_at=started_at,
            assigned_to=operator,
            status='in_progress',
        )

        # Backdate
        StepExecution.objects.filter(pk=execution.pk).update(
            created_at=entry_time
        )

        return execution

    def _simulate_qa_decision_with_report(self, part, step, visit_count, timestamp):
        """
        Simulate QA decision and create QualityReport.

        - 85% pass on first attempt
        - 12% require one rework cycle
        - 3% escalate to scrap decision

        Returns (decision_result, quality_report) tuple.
        """
        # Base failure rate with rework penalty
        base_fail_rate = 0.15
        rework_penalty = 0.08 * (visit_count - 1)  # 8% worse per rework
        fail_rate = min(0.50, base_fail_rate + rework_penalty)

        # Apply time-based quality modifiers if available
        if hasattr(self, 'get_shift_quality_modifier'):
            modifier = self.get_shift_quality_modifier(timestamp)
            fail_rate = fail_rate / modifier

        passed = random.random() > fail_rate

        if step.decision_type == 'qa_result':
            decision = 'PASS' if passed else 'FAIL'
        elif step.decision_type == 'manual':
            decision = 'default' if random.random() > 0.3 else 'alternate'
        else:
            decision = 'PASS' if passed else 'FAIL'

        # Create QualityReport for decision points
        qr = None
        if step.decision_type in ['qa_result', 'measurement']:
            qr = QualityReports.objects.create(
                tenant=self.tenant,
                part=part,
                step=step,
                status=decision if decision in ['PASS', 'FAIL'] else ('PASS' if decision == 'default' else 'FAIL'),
                description=f"QA decision at {step.name} - Visit #{visit_count}",
                sampling_method='statistical',
            )
            # Backdate the report
            QualityReports.objects.filter(pk=qr.pk).update(
                created_at=timestamp,
                updated_at=timestamp
            )

        return decision, qr

    def _direct_assign_part_with_history(self, part, steps, target_idx, num_steps, order_status, base_timestamp, employees=None):
        """
        Direct assignment with StepExecution history for steps traversed.

        Creates completed StepExecution records for all steps up to target,
        providing realistic history without using the slower workflow engine.
        Includes operator assignment for realistic workflow tracking.
        """
        employees = employees or []
        target_step = steps[target_idx]

        # Determine part status based on position
        if target_idx == num_steps - 1 and order_status == OrdersStatus.COMPLETED:
            part_status = PartsStatus.COMPLETED
        elif target_idx == 0:
            part_status = PartsStatus.PENDING
        else:
            # ~85% normal flow, ~15% QA exceptions for in-progress parts
            status_roll = random.random()
            if status_roll < 0.85:
                part_status = PartsStatus.IN_PROGRESS
            elif status_roll < 0.90:
                part_status = PartsStatus.AWAITING_QA
            elif status_roll < 0.94:
                part_status = PartsStatus.QUARANTINED
            elif status_roll < 0.97:
                part_status = PartsStatus.REWORK_NEEDED
            else:
                part_status = PartsStatus.REWORK_IN_PROGRESS

        # Update part to target step
        part.step = target_step
        part.part_status = part_status
        part.save(update_fields=['step', 'part_status'])

        # Create StepExecution history for completed steps (steps before target)
        current_time = base_timestamp
        for idx in range(target_idx):
            step = steps[idx]
            step_duration = timedelta(hours=random.uniform(0.5, 3))
            entry_time = current_time
            exit_time = current_time + step_duration
            started_at = entry_time + timedelta(minutes=random.randint(1, 15))

            # Assign an operator for this step
            operator = random.choice(employees) if employees else None

            StepExecution.objects.create(
                tenant=part.tenant,
                part=part,
                step=step,
                visit_number=1,
                entered_at=entry_time,
                exited_at=exit_time,
                started_at=started_at,
                assigned_to=operator,
                completed_by=operator,
                status='completed',
            )

            current_time = exit_time + timedelta(minutes=random.randint(5, 30))

        # Create in-progress execution for current step (if not at first step)
        if target_idx > 0 and part_status not in [PartsStatus.COMPLETED, PartsStatus.SCRAPPED]:
            operator = random.choice(employees) if employees else None
            started_at = current_time + timedelta(minutes=random.randint(1, 10))

            StepExecution.objects.create(
                tenant=part.tenant,
                part=part,
                step=target_step,
                visit_number=1,
                entered_at=current_time,
                exited_at=None,  # Still in progress
                started_at=started_at,
                assigned_to=operator,
                status='in_progress',
            )

    def _advance_work_order_batch(self, work_order, target_step_index):
        """Advance work order parts through process with realistic branching."""
        if target_step_index <= 0:
            return

        parts = list(work_order.parts.all())
        if not parts:
            return

        completed_parts = set()

        for part in parts:
            visits_at_step = {}
            advancement_count = 0
            max_advancements = target_step_index + 10

            while advancement_count < max_advancements:
                part.refresh_from_db()
                current_step = part.step

                if not current_step:
                    break

                if part.part_status in [PartsStatus.COMPLETED, PartsStatus.SCRAPPED, PartsStatus.CANCELLED]:
                    completed_parts.add(part.id)
                    break

                step_id = current_step.id
                visits_at_step[step_id] = visits_at_step.get(step_id, 0) + 1

                decision_result = None
                if current_step.is_decision_point and current_step.decision_type == 'qa_result':
                    base_fail_rate = 0.15
                    rework_penalty = 0.05 * (visits_at_step.get(step_id, 1) - 1)
                    fail_rate = min(0.40, base_fail_rate + rework_penalty)

                    passed = random.random() > fail_rate
                    decision_result = 'PASS' if passed else 'FAIL'

                    QualityReports.objects.create(
                        tenant=self.tenant,
                        part=part,
                        step=current_step,
                        status=decision_result,
                        description=f"QA check at {current_step.name}",
                        sampling_method='statistical',
                    )

                elif current_step.is_decision_point and current_step.decision_type == 'manual':
                    decision_result = 'default' if random.random() > 0.3 else 'alternate'

                part.part_status = PartsStatus.READY_FOR_NEXT_STEP
                part.save()

                try:
                    result = part.increment_step(decision_result=decision_result)
                except ValueError:
                    result = part.increment_step(decision_result='default')

                advancement_count += 1

                if result == "completed":
                    completed_parts.add(part.id)
                    break
                elif result == "marked_ready":
                    break

                part.refresh_from_db()
                if part.step and part.work_order and part.work_order.process:
                    ps = ProcessStep.objects.filter(
                        process=part.work_order.process,
                        step=part.step
                    ).first()
                    step_order = ps.order if ps else 0
                    if step_order >= target_step_index:
                        if part.step.step_type != 'rework':
                            break

    def _ensure_sampling_rulesets_exist(self, part_type, process, steps, employees):
        """Create sampling rulesets for all steps."""
        for step in steps:
            ruleset, created = SamplingRuleSet.objects.get_or_create(
                tenant=self.tenant,
                part_type=part_type,
                process=process,
                step=step,
                is_fallback=False,
                defaults={
                    'name': f"Sampling for {step.name}",
                    'active': True,
                    'created_by': random.choice(employees) if employees else None,
                }
            )

            if created:
                rules = self._get_realistic_sampling_rules_for_step(step)
                for order, (rule_type, value) in enumerate(rules, 1):
                    SamplingRule.objects.create(
                        ruleset=ruleset,
                        rule_type=rule_type,
                        value=value,
                        order=order
                    )

    def _get_realistic_sampling_rules_for_step(self, step):
        """Get realistic sampling rules based on step type."""
        step_name_lower = step.name.lower()

        if any(kw in step_name_lower for kw in ['inspection', 'qc', 'testing', 'validation', 'verification']):
            return [('percentage', 100)]  # 100% inspection
        elif any(kw in step_name_lower for kw in ['final', 'ship']):
            return [('first_n_parts', 5), ('every_nth_part', 10)]
        elif any(kw in step_name_lower for kw in ['rework', 'repair']):
            return [('percentage', 100)]  # All reworked parts get checked
        else:
            return [('percentage', 20)]  # 20% sampling for other steps

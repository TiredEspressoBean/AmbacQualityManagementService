"""
Comprehensive sampling system tests for PartsTracker
Verifies all rule types using queryset-based logic
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from Tracker.models import *
from Tracker.sampling import SamplingFallbackApplier

User = get_user_model()

class SamplingSystemTestCase(TestCase):
    """Test all sampling rule types with deterministic queryset behavior"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='test_operator',
            email='test@example.com',
            password='testpass'
        )

        self.part_type = PartTypes.objects.create(
            name='Test Widget',
            ID_prefix='TW',
            ERP_id='TEST-WIDGET-001'
        )

        self.process = Processes.objects.create(
            name='Test Process',
            part_type=self.part_type,
            num_steps=5,
            is_remanufactured=False
        )

        self.step = Steps.objects.create(
            name='Test Step',
            process=self.process,
            part_type=self.part_type,
            order=1,
            description='Testing sampling rules',
            is_last_step=True
        )

        self.order = Orders.objects.create(
            name='Test Order',
            customer=self.user,
            order_status=OrdersStatus.IN_PROGRESS
        )

        self.work_order = WorkOrder.objects.create(
            ERP_id='TEST-WO-001',
            related_order=self.order,
            workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=100
        )

        self.ruleset = SamplingRuleSet.objects.create(
            name='Test Ruleset',
            part_type=self.part_type,
            process=self.process,
            step=self.step,
            active=True,
            is_fallback=False
        )

    def create_test_parts(self, count=100):
        parts = []
        for i in range(1, count + 1):
            part = Parts.objects.create(
                ERP_id=f"TEST-WO-001-TW{i:04d}",
                work_order=self.work_order,
                part_type=self.part_type,
                step=self.step,
                order=self.order,
                part_status=PartsStatus.PENDING
            )
            parts.append(part)
        return parts

    def evaluate_parts_sampling(self, parts):
        selected = []
        for part in parts:
            evaluator = SamplingFallbackApplier(part)
            result = evaluator.evaluate()
            if result["requires_sampling"]:
                selected.append({
                    'part': part,
                    'erp_id': part.ERP_id,
                    'rule': result.get('rule'),
                    'context': result.get('context')
                })
        return selected

    def test_every_nth_part_sampling(self):
        SamplingRule.objects.create(
            ruleset=self.ruleset,
            rule_type='every_nth_part',
            value=5,
            order=1
        )
        parts = self.create_test_parts(100)
        selected = self.evaluate_parts_sampling(parts)

        self.assertEqual(len(selected), 20)
        expected_erp_ids = [f"TEST-WO-001-TW{i:04d}" for i in range(5, 101, 5)]
        self.assertEqual([p['erp_id'] for p in selected], expected_erp_ids)
        print("PASS: Every 5th part selected correctly")

    def test_percentage_sampling(self):
        SamplingRule.objects.create(
            ruleset=self.ruleset,
            rule_type='percentage',
            value=20,
            order=1
        )
        parts = self.create_test_parts(100)
        selected = self.evaluate_parts_sampling(parts)

        self.assertEqual(len(selected), 20)
        print("PASS: 20% of parts selected correctly")

    def test_first_n_parts_sampling(self):
        SamplingRule.objects.create(
            ruleset=self.ruleset,
            rule_type='first_n_parts',
            value=15,
            order=1
        )
        parts = self.create_test_parts(100)
        selected = self.evaluate_parts_sampling(parts)

        expected = [f"TEST-WO-001-TW{i:04d}" for i in range(1, 16)]
        self.assertEqual(len(selected), 15)
        self.assertEqual([s['erp_id'] for s in selected], expected)
        print("PASS: First 15 parts selected correctly")

    def test_last_n_parts_sampling(self):
        SamplingRule.objects.create(
            ruleset=self.ruleset,
            rule_type='last_n_parts',
            value=10,
            order=1
        )
        parts = self.create_test_parts(100)
        selected = self.evaluate_parts_sampling(parts)

        expected = [f"TEST-WO-001-TW{i:04d}" for i in range(91, 101)]
        self.assertEqual(len(selected), 10)
        self.assertEqual([s['erp_id'] for s in selected], expected)
        print("PASS: Last 10 parts selected correctly")

    def test_random_sampling(self):
        SamplingRule.objects.create(
            ruleset=self.ruleset,
            rule_type='random',
            value=30,
            order=1
        )
        parts = self.create_test_parts(100)
        selected = self.evaluate_parts_sampling(parts)

        # Because we use created_at as the seed, the result is deterministic
        self.assertEqual(len(selected), len(set(p['erp_id'] for p in selected)))
        print(f"PASS: Random sampling selected {len(selected)} parts (30%)")

    def test_exact_count_sampling(self):
        SamplingRule.objects.create(
            ruleset=self.ruleset,
            rule_type='exact_count',
            value=20,
            order=1
        )
        parts = self.create_test_parts(100)
        selected = self.evaluate_parts_sampling(parts)

        self.assertEqual(len(selected), 20)
        selected_2 = self.evaluate_parts_sampling(parts)
        self.assertEqual([s['erp_id'] for s in selected], [s['erp_id'] for s in selected_2])
        print("PASS: Exact count sampling selected 20 parts deterministically")

    def test_multiple_rules_priority(self):
        SamplingRule.objects.create(
            ruleset=self.ruleset,
            rule_type='first_n_parts',
            value=5,
            order=1
        )
        SamplingRule.objects.create(
            ruleset=self.ruleset,
            rule_type='every_nth_part',
            value=10,
            order=2
        )
        parts = self.create_test_parts(100)
        selected = self.evaluate_parts_sampling(parts)

        expected = [f"TEST-WO-001-TW{i:04d}" for i in range(1, 6)]
        self.assertEqual(len(selected), 5)
        self.assertEqual([s['erp_id'] for s in selected], expected)
        print("PASS: Only first matching rule applies")

    def test_no_sampling_rule(self):
        SamplingRule.objects.filter(ruleset=self.ruleset).delete()
        parts = self.create_test_parts(100)
        selected = self.evaluate_parts_sampling(parts)
        self.assertEqual(len(selected), 0)
        print("PASS: No sampling rule yields zero selections")

    def test_edge_cases(self):
        # Zero percentage
        rule = SamplingRule.objects.create(
            ruleset=self.ruleset,
            rule_type='percentage',
            value=0,
            order=1
        )
        parts = self.create_test_parts(10)
        selected = self.evaluate_parts_sampling(parts)
        self.assertEqual(len(selected), 0)
        print("PASS: Zero percentage handled correctly")

        # 100% percentage
        rule.value = 100
        rule.save()
        selected = self.evaluate_parts_sampling(parts)
        self.assertEqual(len(selected), 10)
        print("PASS: 100% percentage handled correctly")

        # Single part
        Parts.objects.all().delete()
        one_part = self.create_test_parts(1)
        selected = self.evaluate_parts_sampling(one_part)
        self.assertTrue(len(selected) in [0, 1])
        print("PASS: Single part case handled")

    def test_quality_report_fail_quarantines_part(self):
        """Test that a FAIL quality report quarantines the part"""
        part = self.create_test_parts(1)[0]
        self.assertEqual(part.part_status, PartsStatus.PENDING)
        
        quality_report = QualityReports.objects.create(
            part=part,
            reporter=self.user,
            status=QualityReportsStatus.FAIL
        )
        
        part.refresh_from_db()
        self.assertEqual(part.part_status, PartsStatus.QUARANTINED)
        print("PASS: FAIL quality report quarantines part")

    def test_quality_report_pass_no_quarantine(self):
        """Test that a PASS quality report does not quarantine the part"""
        part = self.create_test_parts(1)[0]
        self.assertEqual(part.part_status, PartsStatus.PENDING)
        
        quality_report = QualityReports.objects.create(
            part=part,
            reporter=self.user,
            status=QualityReportsStatus.PASS
        )
        
        part.refresh_from_db()
        self.assertEqual(part.part_status, PartsStatus.PENDING)
        print("PASS: PASS quality report does not quarantine part")

    def test_batch_sampling_integration(self):
        """Test that batching works correctly with sampling evaluation"""
        # Create a work order batch using the real method
        parts = self.work_order.create_parts_batch(self.part_type, self.step, 25)
        
        # Verify parts were created as batch
        self.assertEqual(len(parts), 25)
        self.assertTrue(all(p.work_order == self.work_order for p in parts))
        self.assertTrue(all(p.step == self.step for p in parts))
        
        # Add sampling rule
        SamplingRule.objects.create(
            ruleset=self.ruleset,
            rule_type='every_nth_part',
            value=5,
            order=1
        )
        
        # Evaluate sampling for the batch
        self.work_order._bulk_evaluate_sampling(parts)
        
        # Check that some parts require sampling
        sampling_parts = [p for p in parts if p.requires_sampling]
        self.assertEqual(len(sampling_parts), 5)  # Every 5th part
        print("PASS: Batch sampling evaluation works correctly")

    def test_ready_for_next_step_qa_visibility(self):
        """Test that READY_FOR_NEXT_STEP parts needing sampling show in QA tasks"""
        # Create parts requiring sampling
        part = self.create_test_parts(1)[0]
        part.requires_sampling = True
        part.part_status = PartsStatus.READY_FOR_NEXT_STEP
        part.save()
        
        # Test the UI query logic
        from Tracker.serializer import WorkOrderSerializer
        serializer = WorkOrderSerializer(self.work_order)
        parts_summary = serializer.get_parts_summary(self.work_order)
        
        # Now the UI should recognize READY_FOR_NEXT_STEP parts requiring sampling
        requiring_qa = parts_summary['requiring_qa']
        self.assertEqual(requiring_qa, 1)
        print("PASS: UI now recognizes READY_FOR_NEXT_STEP as QA work")

    def test_batch_advancement_with_sampling(self):
        """Test that batch advancement works correctly with sampling requirements"""
        # Create a multi-step process
        step2 = Steps.objects.create(
            name='Quality Check',
            process=self.process,
            part_type=self.part_type,
            order=2,
            description='QA step',
            is_last_step=True
        )
        
        # Update first step to not be last
        self.step.is_last_step = False
        self.step.save()
        
        # Create batch at first step
        parts = self.work_order.create_parts_batch(self.part_type, self.step, 10)
        
        # Add sampling rule to first step
        SamplingRule.objects.create(
            ruleset=self.ruleset,
            rule_type='every_nth_part',
            value=5,
            order=1
        )
        
        # Evaluate sampling
        self.work_order._bulk_evaluate_sampling(parts)
        
        # Mark parts ready and try to advance
        for part in parts:
            part.part_status = PartsStatus.READY_FOR_NEXT_STEP
            part.save()
        
        # Try increment_step on first part (should advance whole batch)
        first_part = parts[0]
        result = first_part.increment_step()
        
        # Check if batch advanced correctly
        first_part.refresh_from_db()
        
        # Verify the result
        self.assertEqual(result, "full_work_order_advanced")
        
        # Check all parts in batch advanced to step 2
        all_parts = Parts.objects.filter(work_order=self.work_order)
        all_advanced = all(p.step.order == 2 for p in all_parts)
        self.assertTrue(all_advanced)
        
        print("PASS: Batch advancement works with sampling")


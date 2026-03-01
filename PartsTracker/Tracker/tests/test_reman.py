"""
Tests for the Remanufacturing module.

Tests Core, HarvestedComponent, DisassemblyBOMLine models
and the complete reman workflow including life tracking transfer.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from Tracker.models import (
    Tenant,
    User,
    Companies,
    PartTypes,
    Processes,
    Parts,
    PartsStatus,
    Core,
    HarvestedComponent,
    DisassemblyBOMLine,
    LifeLimitDefinition,
    PartTypeLifeLimit,
    LifeTracking,
)


class RemanBaseTestCase(TestCase):
    """Base test case with common reman setup."""

    @classmethod
    def setUpTestData(cls):
        # Create tenant
        cls.tenant = Tenant.objects.create(name="Reman Shop", slug="reman-shop")

        # Create users
        cls.receiving_clerk = User.objects.create_user(
            username="receiver",
            email="receiver@test.com",
            password="testpass",
            tenant=cls.tenant
        )
        cls.disassembly_tech = User.objects.create_user(
            username="tech",
            email="tech@test.com",
            password="testpass",
            tenant=cls.tenant
        )
        cls.qa_inspector = User.objects.create_user(
            username="qa",
            email="qa@test.com",
            password="testpass",
            tenant=cls.tenant
        )

        # Create customer
        cls.customer = Companies.objects.create(
            name="Return Customer",
            tenant=cls.tenant
        )

        # Create part types (core type and component types)
        cls.injector_core_type = PartTypes.objects.create(
            name="Fuel Injector Core",
            ID_prefix="INJ",
            tenant=cls.tenant
        )
        cls.nozzle_type = PartTypes.objects.create(
            name="Nozzle Assembly",
            ID_prefix="NOZ",
            tenant=cls.tenant
        )
        cls.solenoid_type = PartTypes.objects.create(
            name="Solenoid Valve",
            ID_prefix="SOL",
            tenant=cls.tenant
        )
        cls.body_type = PartTypes.objects.create(
            name="Injector Body",
            ID_prefix="BOD",
            tenant=cls.tenant
        )


class CoreModelTests(RemanBaseTestCase):
    """Tests for Core model."""

    def test_create_core(self):
        """Test basic core creation."""
        core = Core.objects.create(
            tenant=self.tenant,
            core_number="CORE-001",
            serial_number="SN123456",
            core_type=self.injector_core_type,
            received_date=date.today(),
            received_by=self.receiving_clerk,
            customer=self.customer,
            source_type='customer_return',
            source_reference="RMA-001",
            condition_grade='B',
            condition_notes="Minor wear on housing"
        )

        self.assertEqual(core.status, 'received')
        self.assertEqual(core.core_number, "CORE-001")
        self.assertFalse(core.core_credit_issued)
        self.assertEqual(str(core), "Core CORE-001 (Fuel Injector Core)")

    def test_core_unique_per_tenant(self):
        """Test core_number is unique per tenant."""
        Core.objects.create(
            tenant=self.tenant,
            core_number="CORE-DUP",
            core_type=self.injector_core_type,
            received_date=date.today(),
            received_by=self.receiving_clerk,
            condition_grade='A'
        )

        with self.assertRaises(Exception):  # IntegrityError
            Core.objects.create(
                tenant=self.tenant,
                core_number="CORE-DUP",  # Duplicate
                core_type=self.injector_core_type,
                received_date=date.today(),
                received_by=self.receiving_clerk,
                condition_grade='A'
            )

    def test_start_disassembly(self):
        """Test starting disassembly workflow."""
        core = Core.objects.create(
            tenant=self.tenant,
            core_number="CORE-002",
            core_type=self.injector_core_type,
            received_date=date.today(),
            received_by=self.receiving_clerk,
            condition_grade='A'
        )

        core.start_disassembly(user=self.disassembly_tech)

        self.assertEqual(core.status, 'in_disassembly')
        self.assertIsNotNone(core.disassembly_started_at)

    def test_cannot_start_disassembly_twice(self):
        """Test that disassembly cannot be started on non-received core."""
        core = Core.objects.create(
            tenant=self.tenant,
            core_number="CORE-003",
            core_type=self.injector_core_type,
            received_date=date.today(),
            received_by=self.receiving_clerk,
            condition_grade='A'
        )
        core.start_disassembly(user=self.disassembly_tech)

        with self.assertRaises(ValueError) as ctx:
            core.start_disassembly(user=self.disassembly_tech)
        self.assertIn("in_disassembly", str(ctx.exception))

    def test_complete_disassembly(self):
        """Test completing disassembly workflow."""
        core = Core.objects.create(
            tenant=self.tenant,
            core_number="CORE-004",
            core_type=self.injector_core_type,
            received_date=date.today(),
            received_by=self.receiving_clerk,
            condition_grade='A'
        )
        core.start_disassembly(user=self.disassembly_tech)
        core.complete_disassembly(user=self.disassembly_tech)

        self.assertEqual(core.status, 'disassembled')
        self.assertIsNotNone(core.disassembly_completed_at)
        self.assertEqual(core.disassembled_by, self.disassembly_tech)

    def test_scrap_core(self):
        """Test scrapping a core."""
        core = Core.objects.create(
            tenant=self.tenant,
            core_number="CORE-005",
            core_type=self.injector_core_type,
            received_date=date.today(),
            received_by=self.receiving_clerk,
            condition_grade='C'
        )

        core.scrap(reason="Cracked housing, not salvageable")

        self.assertEqual(core.status, 'scrapped')
        self.assertEqual(core.condition_grade, 'SCRAP')
        self.assertIn("Cracked housing", core.condition_notes)

    def test_issue_credit(self):
        """Test issuing core credit."""
        core = Core.objects.create(
            tenant=self.tenant,
            core_number="CORE-006",
            core_type=self.injector_core_type,
            received_date=date.today(),
            received_by=self.receiving_clerk,
            condition_grade='A',
            core_credit_value=Decimal('150.00')
        )

        core.issue_credit()

        self.assertTrue(core.core_credit_issued)
        self.assertIsNotNone(core.core_credit_issued_at)

    def test_cannot_issue_credit_without_value(self):
        """Test that credit cannot be issued without value set."""
        core = Core.objects.create(
            tenant=self.tenant,
            core_number="CORE-007",
            core_type=self.injector_core_type,
            received_date=date.today(),
            received_by=self.receiving_clerk,
            condition_grade='A'
            # No core_credit_value set
        )

        with self.assertRaises(ValueError) as ctx:
            core.issue_credit()
        self.assertIn("No credit value", str(ctx.exception))


class HarvestedComponentTests(RemanBaseTestCase):
    """Tests for HarvestedComponent model."""

    def setUp(self):
        """Create a core for harvesting."""
        self.core = Core.objects.create(
            tenant=self.tenant,
            core_number="CORE-HC-001",
            core_type=self.injector_core_type,
            received_date=date.today(),
            received_by=self.receiving_clerk,
            condition_grade='A'
        )
        self.core.start_disassembly(user=self.disassembly_tech)

    def test_harvest_component(self):
        """Test creating a harvested component."""
        component = HarvestedComponent.objects.create(
            tenant=self.tenant,
            core=self.core,
            component_type=self.nozzle_type,
            disassembled_by=self.disassembly_tech,
            condition_grade='A',
            condition_notes="Clean, no wear",
            position="Tip"
        )

        self.assertFalse(component.is_scrapped)
        self.assertIsNone(component.component_part)
        self.assertEqual(str(component), "Nozzle Assembly from Core CORE-HC-001")

    def test_scrap_component(self):
        """Test scrapping a harvested component."""
        component = HarvestedComponent.objects.create(
            tenant=self.tenant,
            core=self.core,
            component_type=self.solenoid_type,
            disassembled_by=self.disassembly_tech,
            condition_grade='C'
        )

        component.scrap(user=self.qa_inspector, reason="Coil resistance out of spec")

        self.assertTrue(component.is_scrapped)
        self.assertEqual(component.condition_grade, 'SCRAP')
        self.assertEqual(component.scrap_reason, "Coil resistance out of spec")
        self.assertEqual(component.scrapped_by, self.qa_inspector)
        self.assertIn("(scrapped)", str(component))

    def test_accept_to_inventory(self):
        """Test accepting a component to inventory."""
        component = HarvestedComponent.objects.create(
            tenant=self.tenant,
            core=self.core,
            component_type=self.nozzle_type,
            disassembled_by=self.disassembly_tech,
            condition_grade='A'
        )

        part = component.accept_to_inventory(user=self.qa_inspector)

        self.assertIsNotNone(component.component_part)
        self.assertEqual(component.component_part, part)
        self.assertEqual(part.part_type, self.nozzle_type)
        self.assertEqual(part.part_status, PartsStatus.PENDING)
        self.assertIn("HC-CORE-HC-001", part.ERP_id)

    def test_accept_to_inventory_custom_erp_id(self):
        """Test accepting with custom ERP ID."""
        component = HarvestedComponent.objects.create(
            tenant=self.tenant,
            core=self.core,
            component_type=self.body_type,
            disassembled_by=self.disassembly_tech,
            condition_grade='B'
        )

        part = component.accept_to_inventory(user=self.qa_inspector, erp_id="CUSTOM-001")

        self.assertEqual(part.ERP_id, "CUSTOM-001")

    def test_cannot_accept_scrapped_component(self):
        """Test that scrapped components cannot be accepted."""
        component = HarvestedComponent.objects.create(
            tenant=self.tenant,
            core=self.core,
            component_type=self.solenoid_type,
            disassembled_by=self.disassembly_tech,
            condition_grade='C'
        )
        component.scrap(user=self.qa_inspector, reason="Damaged")

        with self.assertRaises(ValueError) as ctx:
            component.accept_to_inventory(user=self.qa_inspector)
        self.assertIn("scrapped", str(ctx.exception))

    def test_cannot_accept_twice(self):
        """Test that components cannot be accepted twice."""
        component = HarvestedComponent.objects.create(
            tenant=self.tenant,
            core=self.core,
            component_type=self.nozzle_type,
            disassembled_by=self.disassembly_tech,
            condition_grade='A'
        )
        component.accept_to_inventory(user=self.qa_inspector)

        with self.assertRaises(ValueError) as ctx:
            component.accept_to_inventory(user=self.qa_inspector)
        self.assertIn("already accepted", str(ctx.exception))

    def test_core_component_counts(self):
        """Test core's component count properties."""
        # Create some components
        HarvestedComponent.objects.create(
            tenant=self.tenant,
            core=self.core,
            component_type=self.nozzle_type,
            disassembled_by=self.disassembly_tech,
            condition_grade='A'
        )
        HarvestedComponent.objects.create(
            tenant=self.tenant,
            core=self.core,
            component_type=self.solenoid_type,
            disassembled_by=self.disassembly_tech,
            condition_grade='B'
        )
        scrapped = HarvestedComponent.objects.create(
            tenant=self.tenant,
            core=self.core,
            component_type=self.body_type,
            disassembled_by=self.disassembly_tech,
            condition_grade='C'
        )
        scrapped.scrap(user=self.qa_inspector, reason="Damaged")

        self.assertEqual(self.core.harvested_component_count, 3)
        self.assertEqual(self.core.usable_component_count, 2)


class DisassemblyBOMLineTests(RemanBaseTestCase):
    """Tests for DisassemblyBOMLine model."""

    def test_create_bom_line(self):
        """Test creating a disassembly BOM line."""
        bom_line = DisassemblyBOMLine.objects.create(
            tenant=self.tenant,
            core_type=self.injector_core_type,
            component_type=self.nozzle_type,
            expected_qty=1,
            expected_fallout_rate=Decimal('0.05'),  # 5% fallout
            notes="Handle with care"
        )

        self.assertEqual(bom_line.expected_qty, 1)
        self.assertEqual(bom_line.expected_usable_qty, 0.95)
        self.assertEqual(
            str(bom_line),
            "Fuel Injector Core yields 1x Nozzle Assembly"
        )

    def test_expected_usable_qty_calculation(self):
        """Test expected usable quantity calculation."""
        bom_line = DisassemblyBOMLine.objects.create(
            tenant=self.tenant,
            core_type=self.injector_core_type,
            component_type=self.solenoid_type,
            expected_qty=4,
            expected_fallout_rate=Decimal('0.10')  # 10% fallout
        )

        # 4 * (1 - 0.10) = 3.6
        self.assertAlmostEqual(bom_line.expected_usable_qty, 3.6)


class LifeTrackingTests(RemanBaseTestCase):
    """Tests for life tracking integration with reman."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Create life limit definitions
        cls.cycles_def = LifeLimitDefinition.objects.create(
            tenant=cls.tenant,
            name="Injection Cycles",
            unit="cycles",
            unit_label="Cycles",
            is_calendar_based=False,
            soft_limit=Decimal('800000'),
            hard_limit=Decimal('1000000')
        )
        cls.hours_def = LifeLimitDefinition.objects.create(
            tenant=cls.tenant,
            name="Operating Hours",
            unit="hours",
            unit_label="Hours",
            is_calendar_based=False,
            hard_limit=Decimal('50000')
        )
        cls.shelf_life_def = LifeLimitDefinition.objects.create(
            tenant=cls.tenant,
            name="Shelf Life",
            unit="days",
            unit_label="Days",
            is_calendar_based=True,
            hard_limit=Decimal('365')
        )

        # Link cycles to nozzle type (applicable for transfer)
        PartTypeLifeLimit.objects.create(
            tenant=cls.tenant,
            part_type=cls.nozzle_type,
            definition=cls.cycles_def,
            is_required=True
        )

    def test_create_life_tracking_for_core(self):
        """Test creating life tracking for a core."""
        core = Core.objects.create(
            tenant=self.tenant,
            core_number="CORE-LT-001",
            core_type=self.injector_core_type,
            received_date=date.today(),
            received_by=self.receiving_clerk,
            condition_grade='A'
        )

        tracking, created = LifeTracking.for_object(
            core,
            self.cycles_def,
            accumulated=Decimal('500000'),
            source=LifeTracking.Source.CUSTOMER
        )

        self.assertTrue(created)
        self.assertEqual(tracking.accumulated, Decimal('500000'))
        self.assertEqual(tracking.status, 'ok')
        self.assertEqual(tracking.percent_used, 50.0)

    def test_life_tracking_status_warning(self):
        """Test life tracking warning status."""
        core = Core.objects.create(
            tenant=self.tenant,
            core_number="CORE-LT-002",
            core_type=self.injector_core_type,
            received_date=date.today(),
            received_by=self.receiving_clerk,
            condition_grade='B'
        )

        tracking, _ = LifeTracking.for_object(
            core,
            self.cycles_def,
            accumulated=Decimal('850000')  # Above soft limit
        )

        self.assertEqual(tracking.status, 'warning')
        self.assertEqual(tracking.cached_status, 'warning')

    def test_life_tracking_status_expired(self):
        """Test life tracking expired status."""
        core = Core.objects.create(
            tenant=self.tenant,
            core_number="CORE-LT-003",
            core_type=self.injector_core_type,
            received_date=date.today(),
            received_by=self.receiving_clerk,
            condition_grade='C'
        )

        tracking, _ = LifeTracking.for_object(
            core,
            self.cycles_def,
            accumulated=Decimal('1000001')  # Above hard limit
        )

        self.assertEqual(tracking.status, 'expired')
        self.assertTrue(tracking.is_blocked)

    def test_life_tracking_increment(self):
        """Test incrementing life tracking."""
        core = Core.objects.create(
            tenant=self.tenant,
            core_number="CORE-LT-004",
            core_type=self.injector_core_type,
            received_date=date.today(),
            received_by=self.receiving_clerk,
            condition_grade='A'
        )

        tracking, _ = LifeTracking.for_object(
            core,
            self.cycles_def,
            accumulated=Decimal('100000')
        )

        tracking.increment(50000)

        self.assertEqual(tracking.accumulated, Decimal('150000'))

    def test_life_tracking_reset(self):
        """Test resetting life tracking after overhaul."""
        core = Core.objects.create(
            tenant=self.tenant,
            core_number="CORE-LT-005",
            core_type=self.injector_core_type,
            received_date=date.today(),
            received_by=self.receiving_clerk,
            condition_grade='A'
        )

        tracking, _ = LifeTracking.for_object(
            core,
            self.cycles_def,
            accumulated=Decimal('500000')
        )

        tracking.reset(user=self.qa_inspector, reason="Complete rebuild")

        self.assertEqual(tracking.accumulated, Decimal('0'))
        self.assertEqual(tracking.source, LifeTracking.Source.RESET)
        self.assertEqual(len(tracking.reset_history), 1)
        self.assertEqual(tracking.reset_history[0]['from_value'], 500000)
        self.assertEqual(tracking.reset_history[0]['reason'], "Complete rebuild")

    def test_life_tracking_override(self):
        """Test per-instance limit override."""
        core = Core.objects.create(
            tenant=self.tenant,
            core_number="CORE-LT-006",
            core_type=self.injector_core_type,
            received_date=date.today(),
            received_by=self.receiving_clerk,
            condition_grade='A'
        )

        tracking, _ = LifeTracking.for_object(
            core,
            self.cycles_def,
            accumulated=Decimal('950000')  # Would be warning normally
        )

        # Apply override to extend limits
        tracking.apply_override(
            hard_limit=Decimal('1200000'),
            soft_limit=Decimal('1000000'),
            reason="Engineering approved extended service",
            approved_by=self.qa_inspector
        )

        self.assertEqual(tracking.effective_hard_limit, Decimal('1200000'))
        self.assertEqual(tracking.effective_soft_limit, Decimal('1000000'))
        self.assertEqual(tracking.status, 'ok')  # No longer warning

    def test_calendar_based_life_tracking(self):
        """Test calendar-based life tracking."""
        core = Core.objects.create(
            tenant=self.tenant,
            core_number="CORE-LT-007",
            core_type=self.injector_core_type,
            received_date=date.today(),
            received_by=self.receiving_clerk,
            condition_grade='A'
        )

        # Reference date 200 days ago
        ref_date = date.today() - timedelta(days=200)

        tracking, _ = LifeTracking.for_object(
            core,
            self.shelf_life_def,
            reference_date=ref_date
        )

        # Current value should be ~200 days
        self.assertAlmostEqual(float(tracking.current_value), 200, delta=1)
        self.assertEqual(tracking.status, 'ok')  # Still within 365 day limit

    def test_life_transfer_on_accept_to_inventory(self):
        """Test life tracking transfer when accepting component to inventory."""
        # Create core with life tracking
        core = Core.objects.create(
            tenant=self.tenant,
            core_number="CORE-LT-008",
            core_type=self.injector_core_type,
            received_date=date.today(),
            received_by=self.receiving_clerk,
            condition_grade='A'
        )
        core.start_disassembly(user=self.disassembly_tech)

        # Add life tracking to core
        core_tracking, _ = LifeTracking.for_object(
            core,
            self.cycles_def,
            accumulated=Decimal('300000'),
            source=LifeTracking.Source.CUSTOMER
        )

        # Harvest a nozzle (which has cycles_def linked via PartTypeLifeLimit)
        component = HarvestedComponent.objects.create(
            tenant=self.tenant,
            core=core,
            component_type=self.nozzle_type,  # Has cycles linked
            disassembled_by=self.disassembly_tech,
            condition_grade='A'
        )

        # Accept to inventory - should transfer life tracking
        part = component.accept_to_inventory(user=self.qa_inspector)

        # Check that life tracking was transferred to the part
        part_tracking = LifeTracking.objects.filter(
            content_type=ContentType.objects.get_for_model(part),
            object_id=part.id
        ).first()

        self.assertIsNotNone(part_tracking)
        self.assertEqual(part_tracking.accumulated, Decimal('300000'))
        self.assertEqual(part_tracking.source, LifeTracking.Source.TRANSFERRED)
        self.assertEqual(part_tracking.definition, self.cycles_def)

    def test_life_not_transferred_for_non_applicable_type(self):
        """Test that life tracking is NOT transferred for non-applicable part types."""
        # Create core with life tracking
        core = Core.objects.create(
            tenant=self.tenant,
            core_number="CORE-LT-009",
            core_type=self.injector_core_type,
            received_date=date.today(),
            received_by=self.receiving_clerk,
            condition_grade='A'
        )
        core.start_disassembly(user=self.disassembly_tech)

        # Add life tracking to core
        LifeTracking.for_object(
            core,
            self.cycles_def,
            accumulated=Decimal('300000')
        )

        # Harvest a solenoid (which does NOT have cycles_def linked)
        component = HarvestedComponent.objects.create(
            tenant=self.tenant,
            core=core,
            component_type=self.solenoid_type,  # No life limits linked
            disassembled_by=self.disassembly_tech,
            condition_grade='A'
        )

        # Accept to inventory
        part = component.accept_to_inventory(user=self.qa_inspector)

        # Check that NO life tracking was transferred
        part_tracking = LifeTracking.objects.filter(
            content_type=ContentType.objects.get_for_model(part),
            object_id=part.id
        ).first()

        self.assertIsNone(part_tracking)


class RemanWorkflowIntegrationTests(RemanBaseTestCase):
    """Integration tests for complete reman workflow."""

    def test_full_reman_workflow(self):
        """Test complete workflow: receive -> disassemble -> harvest -> accept/scrap."""
        # 1. Receive core
        core = Core.objects.create(
            tenant=self.tenant,
            core_number="CORE-FULL-001",
            core_type=self.injector_core_type,
            received_date=date.today(),
            received_by=self.receiving_clerk,
            customer=self.customer,
            source_type='customer_return',
            source_reference="RMA-100",
            condition_grade='B',
            core_credit_value=Decimal('200.00')
        )
        self.assertEqual(core.status, 'received')

        # 2. Start disassembly
        core.start_disassembly(user=self.disassembly_tech)
        self.assertEqual(core.status, 'in_disassembly')

        # 3. Harvest components
        nozzle = HarvestedComponent.objects.create(
            tenant=self.tenant,
            core=core,
            component_type=self.nozzle_type,
            disassembled_by=self.disassembly_tech,
            condition_grade='A',
            position="Tip"
        )
        solenoid = HarvestedComponent.objects.create(
            tenant=self.tenant,
            core=core,
            component_type=self.solenoid_type,
            disassembled_by=self.disassembly_tech,
            condition_grade='B',
            position="Top"
        )
        body = HarvestedComponent.objects.create(
            tenant=self.tenant,
            core=core,
            component_type=self.body_type,
            disassembled_by=self.disassembly_tech,
            condition_grade='C',  # Poor condition
            position="Main"
        )

        self.assertEqual(core.harvested_component_count, 3)

        # 4. Complete disassembly
        core.complete_disassembly(user=self.disassembly_tech)
        self.assertEqual(core.status, 'disassembled')

        # 5. Disposition components
        # Accept good ones
        nozzle_part = nozzle.accept_to_inventory(user=self.qa_inspector)
        solenoid_part = solenoid.accept_to_inventory(user=self.qa_inspector)

        # Scrap damaged one
        body.scrap(user=self.qa_inspector, reason="Housing cracked")

        # Verify
        self.assertIsNotNone(nozzle.component_part)
        self.assertIsNotNone(solenoid.component_part)
        self.assertTrue(body.is_scrapped)
        self.assertEqual(core.usable_component_count, 2)

        # 6. Issue core credit
        core.issue_credit()
        self.assertTrue(core.core_credit_issued)

        # 7. Verify parts are in inventory
        self.assertEqual(nozzle_part.part_status, PartsStatus.PENDING)
        self.assertEqual(solenoid_part.part_status, PartsStatus.PENDING)

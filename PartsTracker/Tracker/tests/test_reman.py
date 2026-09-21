"""
Tests for the Remanufacturing module.

Tests Core, HarvestedComponent, DisassemblyBOMLine models
and the complete reman workflow including life tracking transfer.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.core.exceptions import ValidationError as DjangoValidationError
from django.test import SimpleTestCase, TestCase
from Tracker.tests.base import TenantTestCase
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from Tracker.models import (
    Tenant,
    User,
    Companies,
    PartTypes,
    Processes,
    ProcessStep,
    Steps,
    Parts,
    PartsStatus,
    Orders,
    WorkOrder,
    WorkOrderStatus,
    Core,
    HarvestedComponent,
    DisassemblyBOMLine,
    LifeLimitDefinition,
    PartTypeLifeLimit,
    LifeTracking,
    QualityReports,
    MeasurementDefinition,
    MeasurementResult,
)
from Tracker.utils.tenant_context import (
    set_current_tenant_id,
    reset_current_tenant,
)


class RemanBaseTestCase(TestCase):
    """Base test case with common reman setup.

    Sets the tenant ContextVar for the duration of setUpTestData (so
    class-level fixtures created via `Model.objects.create(tenant=...)`
    don't trip SecureManager's tenant-required guard) and re-asserts it
    per-test via setUp/tearDown so test-body queries auto-scope correctly.
    """

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name="Reman Shop", slug="reman-shop")
        cls._class_cv_token = set_current_tenant_id(cls.tenant.id)

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

    @classmethod
    def tearDownClass(cls):
        token = getattr(cls, '_class_cv_token', None)
        if token is not None:
            reset_current_tenant(token)
            cls._class_cv_token = None
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        # Re-assert ContextVar for this test's lifetime (a prior test's
        # tearDown may have reset it).
        self._test_cv_token = set_current_tenant_id(self.tenant.id)

    def tearDown(self):
        token = getattr(self, '_test_cv_token', None)
        if token is not None:
            reset_current_tenant(token)
            self._test_cv_token = None
        super().tearDown()


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
            source_type='CUSTOMER_RETURN',
            source_reference="RMA-001",
            condition_grade='B',
            condition_notes="Minor wear on housing"
        )

        self.assertEqual(core.status, 'RECEIVED')
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

        self.assertEqual(core.status, 'IN_DISASSEMBLY')
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
        self.assertIn("IN_DISASSEMBLY", str(ctx.exception))

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

        self.assertEqual(core.status, 'DISASSEMBLED')
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

        self.assertEqual(core.status, 'SCRAPPED')
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
        self.assertEqual(tracking.status, 'OK')
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

        self.assertEqual(tracking.status, 'WARNING')
        self.assertEqual(tracking.cached_status, 'WARNING')

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

        self.assertEqual(tracking.status, 'EXPIRED')
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
        self.assertEqual(tracking.status, 'OK')  # No longer warning

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
        self.assertEqual(tracking.status, 'OK')  # Still within 365 day limit

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
            source_type='CUSTOMER_RETURN',
            source_reference="RMA-100",
            condition_grade='B',
            core_credit_value=Decimal('200.00')
        )
        self.assertEqual(core.status, 'RECEIVED')

        # 2. Start disassembly
        core.start_disassembly(user=self.disassembly_tech)
        self.assertEqual(core.status, 'IN_DISASSEMBLY')

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
        self.assertEqual(core.status, 'DISASSEMBLED')

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


class RemanWorkOrderIntegrationTests(RemanBaseTestCase):
    """Tests for reman integration with WorkOrder model."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Create a process for the nozzle type (so parts can enter workflow)
        cls.nozzle_process = Processes.objects.create(
            name="Nozzle Rebuild Process",
            part_type=cls.nozzle_type,
            tenant=cls.tenant
        )

    def test_core_linked_to_work_order(self):
        """Test that a core can be linked to a work order for tracking."""
        # Create an order for the disassembly work
        order = Orders.objects.create(
            tenant=self.tenant,
            company=self.customer,  # company FK is Companies
            name="Disassembly Order"
        )

        # Create work order for disassembly
        work_order = WorkOrder.objects.create(
            tenant=self.tenant,
            related_order=order,
            process=self.nozzle_process,
            ERP_id="WO-DISASM-001",
            workorder_status=WorkOrderStatus.IN_PROGRESS
        )

        # Create core linked to work order
        core = Core.objects.create(
            tenant=self.tenant,
            core_number="CORE-WO-001",
            core_type=self.injector_core_type,
            received_date=date.today(),
            received_by=self.receiving_clerk,
            condition_grade='A',
            work_order=work_order  # Link to WO
        )

        self.assertEqual(core.work_order, work_order)
        self.assertIn(core, work_order.cores.all())

    def test_reman_part_enters_production_workflow(self):
        """Test that a part from reman can enter and progress through workflow."""
        # Setup: Create steps for nozzle process
        step1 = Steps.objects.create(
            tenant=self.tenant,
            name="Clean",
            part_type=self.nozzle_type
        )
        step2 = Steps.objects.create(
            tenant=self.tenant,
            name="Inspect",
            part_type=self.nozzle_type
        )
        step3 = Steps.objects.create(
            tenant=self.tenant,
            name="Test",
            part_type=self.nozzle_type,
            is_terminal=True
        )

        # Link steps to process
        ProcessStep.objects.create(process=self.nozzle_process, step=step1, order=1, is_entry_point=True)
        ProcessStep.objects.create(process=self.nozzle_process, step=step2, order=2)
        ProcessStep.objects.create(process=self.nozzle_process, step=step3, order=3)

        # Create core and harvest component
        core = Core.objects.create(
            tenant=self.tenant,
            core_number="CORE-PROD-001",
            core_type=self.injector_core_type,
            received_date=date.today(),
            received_by=self.receiving_clerk,
            condition_grade='A'
        )
        core.start_disassembly(user=self.disassembly_tech)

        component = HarvestedComponent.objects.create(
            tenant=self.tenant,
            core=core,
            component_type=self.nozzle_type,
            disassembled_by=self.disassembly_tech,
            condition_grade='A'
        )

        # Accept to inventory
        part = component.accept_to_inventory(user=self.qa_inspector)
        self.assertEqual(part.part_status, PartsStatus.PENDING)

        # Create production order and work order
        prod_order = Orders.objects.create(
            tenant=self.tenant,
            company=self.customer,  # company FK is Companies
            name="Production Order"
        )

        prod_wo = WorkOrder.objects.create(
            tenant=self.tenant,
            related_order=prod_order,
            process=self.nozzle_process,
            ERP_id="WO-PROD-001",
            workorder_status=WorkOrderStatus.IN_PROGRESS
        )

        # Assign part to work order
        part.work_order = prod_wo
        part.step = step1
        part.part_status = PartsStatus.IN_PROGRESS
        part.save()

        # Verify part is in workflow
        self.assertEqual(part.work_order, prod_wo)
        self.assertEqual(part.step, step1)
        self.assertEqual(part.part_status, PartsStatus.IN_PROGRESS)

        # Part can progress through steps
        part.step = step2
        part.save()
        self.assertEqual(part.step.name, "Inspect")

        # Verify traceability back to core
        self.assertEqual(part.harvested_from.core, core)
        self.assertEqual(part.harvested_from.core.core_number, "CORE-PROD-001")


class RemanQualityIntegrationTests(RemanBaseTestCase):
    """Tests for reman integration with Quality models."""

    def test_component_quality_report(self):
        """Test that harvested components can have quality reports."""
        # Create core and harvest component
        core = Core.objects.create(
            tenant=self.tenant,
            core_number="CORE-QA-001",
            core_type=self.injector_core_type,
            received_date=date.today(),
            received_by=self.receiving_clerk,
            condition_grade='B'
        )
        core.start_disassembly(user=self.disassembly_tech)

        component = HarvestedComponent.objects.create(
            tenant=self.tenant,
            core=core,
            component_type=self.nozzle_type,
            disassembled_by=self.disassembly_tech,
            condition_grade='B',
            condition_notes="Needs inspection"
        )

        # Accept to inventory first (QR typically on Parts)
        part = component.accept_to_inventory(user=self.qa_inspector)

        # Create quality report for the part
        qr = QualityReports.objects.create(
            tenant=self.tenant,
            part=part,
            status='PASS',
            detected_by=self.qa_inspector
        )

        self.assertEqual(qr.part, part)
        self.assertEqual(qr.status, 'PASS')

        # Can trace QR back to harvested component and core
        self.assertEqual(qr.part.harvested_from.core.core_number, "CORE-QA-001")

    def test_part_with_measurements_from_reman(self):
        """Test measurements on parts sourced from reman."""
        # Create step with measurement requirement
        inspect_step = Steps.objects.create(
            tenant=self.tenant,
            name="Dimensional Check",
            part_type=self.nozzle_type
        )

        measurement_def = MeasurementDefinition.objects.create(
            tenant=self.tenant,
            step=inspect_step,
            label="Nozzle Tip Diameter",
            type="NUMERIC",
            unit="mm",
            nominal=Decimal('2.500'),
            upper_tol=Decimal('0.010'),
            lower_tol=Decimal('0.010')  # Lower tol is positive magnitude
        )

        # Create core and harvest
        core = Core.objects.create(
            tenant=self.tenant,
            core_number="CORE-MEAS-001",
            core_type=self.injector_core_type,
            received_date=date.today(),
            received_by=self.receiving_clerk,
            condition_grade='A'
        )
        core.start_disassembly(user=self.disassembly_tech)

        component = HarvestedComponent.objects.create(
            tenant=self.tenant,
            core=core,
            component_type=self.nozzle_type,
            disassembled_by=self.disassembly_tech,
            condition_grade='A'
        )

        part = component.accept_to_inventory(user=self.qa_inspector)

        # Create quality report first (measurements are linked to reports)
        qr = QualityReports.objects.create(
            tenant=self.tenant,
            part=part,
            step=inspect_step,
            status='PASS',
            detected_by=self.qa_inspector
        )

        # Record measurement on the quality report
        measurement = MeasurementResult.objects.create(
            tenant=self.tenant,
            report=qr,
            definition=measurement_def,
            value_numeric=2.503,  # Within tolerance
            is_within_spec=True,
            created_by=self.qa_inspector
        )

        self.assertEqual(measurement.report.part, part)
        self.assertEqual(measurement.value_numeric, 2.503)

        # Check if within tolerance (already verified by is_within_spec)
        self.assertTrue(measurement.is_within_spec)


class RemanMultiCoreIntegrationTests(RemanBaseTestCase):
    """Tests for scenarios involving multiple cores."""

    def test_batch_core_receiving(self):
        """Test receiving multiple cores from same source."""
        cores = []
        for i in range(5):
            core = Core.objects.create(
                tenant=self.tenant,
                core_number=f"BATCH-{i+1:03d}",
                core_type=self.injector_core_type,
                received_date=date.today(),
                received_by=self.receiving_clerk,
                customer=self.customer,
                source_type='CUSTOMER_RETURN',
                source_reference="RMA-BATCH-001",
                condition_grade='B'
            )
            cores.append(core)

        # Query cores by source reference
        batch_cores = Core.objects.filter(source_reference="RMA-BATCH-001")
        self.assertEqual(batch_cores.count(), 5)

        # All from same customer
        self.assertTrue(all(c.customer == self.customer for c in batch_cores))

    def test_component_inventory_aggregation(self):
        """Test aggregating components across multiple cores."""
        # Create and disassemble multiple cores
        for i in range(3):
            core = Core.objects.create(
                tenant=self.tenant,
                core_number=f"AGG-{i+1:03d}",
                core_type=self.injector_core_type,
                received_date=date.today(),
                received_by=self.receiving_clerk,
                condition_grade='A'
            )
            core.start_disassembly(user=self.disassembly_tech)

            # Each core yields 2 nozzles
            for j in range(2):
                component = HarvestedComponent.objects.create(
                    tenant=self.tenant,
                    core=core,
                    component_type=self.nozzle_type,
                    disassembled_by=self.disassembly_tech,
                    condition_grade='A',
                    position=f"Position {j+1}"
                )
                component.accept_to_inventory(user=self.qa_inspector)

            core.complete_disassembly(user=self.disassembly_tech)

        # Query all nozzle parts from harvested components
        harvested_nozzles = Parts.objects.filter(
            harvested_from__isnull=False,
            part_type=self.nozzle_type
        )

        self.assertEqual(harvested_nozzles.count(), 6)  # 3 cores x 2 nozzles

    def test_yield_tracking_against_bom(self):
        """Test tracking actual yield against DisassemblyBOM expectations."""
        # Create BOM expectations
        nozzle_bom = DisassemblyBOMLine.objects.create(
            tenant=self.tenant,
            core_type=self.injector_core_type,
            component_type=self.nozzle_type,
            expected_qty=1,
            expected_fallout_rate=Decimal('0.10')  # 10% expected fallout
        )
        solenoid_bom = DisassemblyBOMLine.objects.create(
            tenant=self.tenant,
            core_type=self.injector_core_type,
            component_type=self.solenoid_type,
            expected_qty=1,
            expected_fallout_rate=Decimal('0.05')
        )

        # Disassemble 10 cores
        actual_nozzles_good = 0
        actual_nozzles_scrapped = 0
        actual_solenoids_good = 0
        actual_solenoids_scrapped = 0

        for i in range(10):
            core = Core.objects.create(
                tenant=self.tenant,
                core_number=f"YIELD-{i+1:03d}",
                core_type=self.injector_core_type,
                received_date=date.today(),
                received_by=self.receiving_clerk,
                condition_grade='B'
            )
            core.start_disassembly(user=self.disassembly_tech)

            # Harvest nozzle - simulate 20% actual fallout (2 of 10 scrapped)
            nozzle = HarvestedComponent.objects.create(
                tenant=self.tenant,
                core=core,
                component_type=self.nozzle_type,
                disassembled_by=self.disassembly_tech,
                condition_grade='B' if i < 8 else 'SCRAP'
            )
            if i < 8:
                nozzle.accept_to_inventory(user=self.qa_inspector)
                actual_nozzles_good += 1
            else:
                nozzle.scrap(user=self.qa_inspector, reason="Damaged")
                actual_nozzles_scrapped += 1

            # Harvest solenoid - simulate 10% actual fallout (1 of 10 scrapped)
            solenoid = HarvestedComponent.objects.create(
                tenant=self.tenant,
                core=core,
                component_type=self.solenoid_type,
                disassembled_by=self.disassembly_tech,
                condition_grade='A' if i < 9 else 'SCRAP'
            )
            if i < 9:
                solenoid.accept_to_inventory(user=self.qa_inspector)
                actual_solenoids_good += 1
            else:
                solenoid.scrap(user=self.qa_inspector, reason="Coil failure")
                actual_solenoids_scrapped += 1

            core.complete_disassembly(user=self.disassembly_tech)

        # Calculate actual vs expected
        total_cores = 10

        # Nozzles: expected 90% yield, actual 80%
        expected_nozzle_yield = total_cores * nozzle_bom.expected_usable_qty  # 9
        actual_nozzle_yield = actual_nozzles_good  # 8
        self.assertEqual(actual_nozzle_yield, 8)
        self.assertLess(actual_nozzle_yield, expected_nozzle_yield)  # Worse than expected

        # Solenoids: expected 95% yield, actual 90%
        expected_solenoid_yield = total_cores * solenoid_bom.expected_usable_qty  # 9.5
        actual_solenoid_yield = actual_solenoids_good  # 9
        self.assertEqual(actual_solenoid_yield, 9)

        # Query for analytics
        total_harvested = HarvestedComponent.objects.filter(
            core__core_number__startswith="YIELD-"
        ).count()
        total_scrapped = HarvestedComponent.objects.filter(
            core__core_number__startswith="YIELD-",
            is_scrapped=True
        ).count()

        self.assertEqual(total_harvested, 20)  # 10 cores x 2 components
        self.assertEqual(total_scrapped, 3)  # 2 nozzles + 1 solenoid


class ComponentDispositionPermissionTests(TenantTestCase):
    """Accepting a used part into inventory is a held authority, not a side effect of
    being able to record a teardown.

    `grade_component`, `accept_component` and `reject_component` shipped declared on the
    model and enforced nowhere, so the CRUD default decided all three: anyone who could
    add a harvested component could also put one into the pool of parts that go into
    customer product. These pin the gates now that they exist, and the distribution
    decision behind them.
    """

    def setUp(self):
        super().setUp()
        from Tracker.models import Core, HarvestedComponent, PartTypes

        self.core_type = PartTypes.objects.create(tenant=self.tenant_a, name='Injector')
        self.comp_type = PartTypes.objects.create(tenant=self.tenant_a, name='Nozzle')
        self.core = Core.objects.create(
            tenant=self.tenant_a, core_number='CORE-PERM-1', core_type=self.core_type,
            received_date=date.today(), received_by=self.user_a, status='IN_DISASSEMBLY')
        self.component = HarvestedComponent.objects.create(
            tenant=self.tenant_a, core=self.core, component_type=self.comp_type,
            condition_grade='B', disassembled_by=self.user_a)

    def _as(self, *perms):
        self.grant_tenant_permissions(
            self.user_a, self.tenant_a,
            ['view_harvestedcomponent', 'full_tenant_access', *perms])
        self.authenticate_as(self.user_a)

    def test_accept_is_refused_without_the_disposition_permission(self):
        self._as('add_harvestedcomponent', 'change_harvestedcomponent')
        resp = self.client.post(
            f'/api/HarvestedComponents/{self.component.id}/accept_to_inventory/', {})
        self.assertEqual(resp.status_code, 403)

    def test_accept_is_allowed_with_it(self):
        """And the CRUD perm is NOT additionally required — accepting creates a Parts
        record, it does not add a harvested component, so demanding `add_` would
        misdescribe the act."""
        self._as('accept_component')
        resp = self.client.post(
            f'/api/HarvestedComponents/{self.component.id}/accept_to_inventory/', {})
        self.assertNotEqual(resp.status_code, 403)

    def test_scrap_is_refused_without_the_reject_permission(self):
        self._as('add_harvestedcomponent', 'change_harvestedcomponent')
        resp = self.client.post(
            f'/api/HarvestedComponents/{self.component.id}/scrap/', {'reason': 'worn'})
        self.assertEqual(resp.status_code, 403)

    def test_recording_a_component_is_refused_without_grade_component(self):
        """Creating a harvested component carries its condition grade, so creating one
        IS grading it. The permission ships with the general operational grant, so this
        changes who can grade for nobody — it makes the lever exist."""
        self._as('add_harvestedcomponent')
        resp = self.client.post('/api/HarvestedComponents/', {
            'core': str(self.core.id), 'component_type': str(self.comp_type.id),
            'condition_grade': 'B'})
        self.assertEqual(resp.status_code, 403)

    def test_recording_a_component_is_allowed_with_it(self):
        self._as('add_harvestedcomponent', 'grade_component')
        resp = self.client.post('/api/HarvestedComponents/', {
            'core': str(self.core.id), 'component_type': str(self.comp_type.id),
            'condition_grade': 'B'})
        self.assertNotEqual(resp.status_code, 403)


class ComponentDispositionPresetTests(SimpleTestCase):
    """The distribution decision, pinned. Same tier as FPI sign-off and decision
    resolution: the line Operator records what teardown found, the QA / lead / manager
    tier decides what becomes of it."""

    def test_the_operator_records_but_does_not_disposition(self):
        from Tracker.presets import GROUP_PRESETS
        perms = set(GROUP_PRESETS['operator']['permissions'])
        self.assertIn('grade_component', perms)
        self.assertNotIn('accept_component', perms)
        self.assertNotIn('reject_component', perms)

    def test_the_qa_and_supervisor_tier_holds_disposition(self):
        from Tracker.presets import GROUP_PRESETS
        for role in ('qa_inspector', 'qa_manager', 'production_manager',
                     'shift_lead', 'tenant_admin'):
            perms = set(GROUP_PRESETS[role]['permissions'])
            self.assertIn('accept_component', perms, role)
            self.assertIn('reject_component', perms, role)


class CoreFulfilmentModeTests(TenantTestCase):
    """How a core is fulfilled decides three separate things.

    `source_type` records where a core came FROM; nothing recorded where it was GOING.
    A customer return is either their own unit to repair and send back, or a core
    surrendered against an exchange — and the two differ on unit identity, on whether a
    wider scope needs the customer's authorisation, and on whether components harvested
    from other cores may be built in.
    """

    def setUp(self):
        super().setUp()
        from Tracker.models import Core, PartTypes

        self.core_type = PartTypes.objects.create(tenant=self.tenant_a, name='Injector')
        self.core = Core.objects.create(
            tenant=self.tenant_a, core_number='CORE-FM-1', core_type=self.core_type,
            received_date=date.today(), received_by=self.user_a)

    def test_exchange_is_the_default(self):
        """The mode with no extra obligations. A shop that never configures this should
        not silently acquire a customer-authorisation requirement it does not have."""
        self.assertEqual(self.core.fulfilment_mode, 'EXCHANGE')
        self.assertFalse(self.core.returns_to_customer)

    def test_an_exchange_rebuild_may_use_the_harvest_pool(self):
        """The customer gets *a* unit, so harvested stock is stock like any other."""
        self.assertTrue(self.core.allows_pooled_harvest)

    def test_a_returned_unit_keeps_its_own_parts(self):
        self.core.fulfilment_mode = 'REPAIR_RETURN'
        self.core.save(update_fields=['fulfilment_mode'])

        self.assertTrue(self.core.returns_to_customer)
        self.assertFalse(self.core.allows_pooled_harvest)

    def test_only_a_returned_unit_needs_scope_authorised(self):
        """On an exchange the shop owns the unit and the cost, so scope is an internal
        decision. On repair-and-return a wider scope is a bigger bill for someone who
        has not agreed to it — the over-and-above process."""
        self.assertFalse(self.core.scope_needs_customer_approval)

        self.core.fulfilment_mode = 'REPAIR_RETURN'
        self.core.save(update_fields=['fulfilment_mode'])
        self.assertTrue(self.core.scope_needs_customer_approval)

    def test_the_mode_is_independent_of_where_the_core_came_from(self):
        """The distinction the field exists to draw: a CUSTOMER_RETURN can be either."""
        self.core.source_type = 'CUSTOMER_RETURN'
        for mode, expected in (('EXCHANGE', False), ('REPAIR_RETURN', True)):
            self.core.fulfilment_mode = mode
            self.core.save(update_fields=['source_type', 'fulfilment_mode'])
            self.assertEqual(self.core.returns_to_customer, expected, mode)


class FulfilmentModeInheritanceTests(TenantTestCase):
    """A core inherits its customer's standing arrangement.

    An exchange programme is a contract with a customer, not a decision about one unit,
    so a receiving clerk should be confirming rather than guessing — the cost of
    guessing wrong is asymmetric, and only in one direction is it recoverable.
    """

    def setUp(self):
        super().setUp()
        from Tracker.models import Companies
        self.acme = Companies.objects.create(
            tenant=self.tenant_a, name='Acme', description='',
            default_core_fulfilment_mode='REPAIR_RETURN')
        self.nobody = Companies.objects.create(
            tenant=self.tenant_a, name='Unarranged', description='')

    def test_the_customers_arrangement_is_inherited(self):
        from Tracker.services.reman.core import resolve_fulfilment_mode
        self.assertEqual(resolve_fulfilment_mode(self.acme),
                         ('REPAIR_RETURN', 'customer'))

    def test_an_explicit_choice_overrides_the_arrangement(self):
        """Someone deliberately overriding a contract default must win — that is the
        exception the arrangement cannot know about."""
        from Tracker.services.reman.core import resolve_fulfilment_mode
        self.assertEqual(resolve_fulfilment_mode(self.acme, 'EXCHANGE'),
                         ('EXCHANGE', 'requested'))

    def test_no_arrangement_falls_back_and_says_so(self):
        """`default` provenance is the point: it lets the screen admit this is a
        fallback rather than presenting it as the customer's known arrangement."""
        from Tracker.services.reman.core import resolve_fulfilment_mode
        self.assertEqual(resolve_fulfilment_mode(self.nobody),
                         ('EXCHANGE', 'default'))
        self.assertEqual(resolve_fulfilment_mode(None), ('EXCHANGE', 'default'))

    def test_blank_is_distinct_from_exchange_on_the_company(self):
        """Nullable on purpose: 'nobody has recorded an arrangement' must not collapse
        into 'they are on exchange', or the screen cannot prompt for what is missing."""
        self.assertIsNone(self.nobody.default_core_fulfilment_mode)
        self.assertEqual(self.acme.default_core_fulfilment_mode, 'REPAIR_RETURN')

    def test_recording_an_arrangement_does_not_fork_a_company_version(self):
        """It is a commercial term that changes when a contract is renegotiated, not a
        controlled fact. Versioning the company each time would bury real supplier
        qualification history under sales terms."""
        from Tracker.serializers.core import CompanySerializer
        before = self.acme.version
        ser = CompanySerializer(self.acme,
                                data={'default_core_fulfilment_mode': 'EXCHANGE'},
                                partial=True)
        ser.is_valid(raise_exception=True)
        saved = ser.save()
        self.assertEqual(saved.version, before)
        self.assertEqual(saved.default_core_fulfilment_mode, 'EXCHANGE')


class HarvestReservationTests(TenantTestCase):
    """A repair-and-return core's components are the customer's property.

    Accepting a harvested component into inventory turns it into an ordinary Parts
    row. Without a marker it is indistinguishable from stock, and the first thing
    that ever consumes it takes a part the customer is owed — a loss that cannot be
    undone once the unit is reassembled without it.
    """

    def setUp(self):
        super().setUp()
        from Tracker.models import Core, HarvestedComponent, PartTypes

        self.core_type = PartTypes.objects.create(tenant=self.tenant_a, name='Injector')
        self.component_type = PartTypes.objects.create(
            tenant=self.tenant_a, name='Nozzle', ID_prefix='NZ')

        def _core(number, mode):
            return Core.objects.create(
                tenant=self.tenant_a, core_number=number, core_type=self.core_type,
                fulfilment_mode=mode, received_date=date.today(),
                received_by=self.user_a)

        self.theirs = _core('CORE-RSV-1', 'REPAIR_RETURN')
        self.ours = _core('CORE-RSV-2', 'EXCHANGE')

        def _component(core):
            return HarvestedComponent.objects.create(
                tenant=self.tenant_a, core=core, component_type=self.component_type,
                condition_grade='A', disassembled_by=self.user_a)

        self.their_component = _component(self.theirs)
        self.our_component = _component(self.ours)

    def _accept(self, component):
        from Tracker.services.reman.harvested_component import accept_component_to_inventory
        return accept_component_to_inventory(component, self.user_a, transfer_life=False)

    def test_a_repair_and_return_cores_parts_are_reserved_to_it(self):
        part = self._accept(self.their_component)
        self.assertEqual(part.reserved_for_core_id, self.theirs.id)

    def test_an_exchange_cores_parts_go_to_stock_unreserved(self):
        """The shop owns the unit, so the harvest is stock like any other. Reserving
        it would strand usable inventory for no reason."""
        part = self._accept(self.our_component)
        self.assertIsNone(part.reserved_for_core_id)

    def test_the_reservation_is_set_as_the_part_is_created(self):
        """Not in a follow-up write: between the two there would be a window in which
        the customer's part sits in stock looking free, which is the one transition
        the reservation exists to cover."""
        from Tracker.models import Parts
        part = self._accept(self.their_component)
        # Re-read rather than trusting the in-memory object.
        self.assertEqual(
            Parts.objects.get(pk=part.pk).reserved_for_core_id, self.theirs.id)

    def test_a_reserved_part_is_refused_by_another_jobs_work_order(self):
        from django.core.exceptions import ValidationError
        from Tracker.models import WorkOrder
        from Tracker.services.reman.reservation import assert_work_order_allowed

        part = self._accept(self.their_component)
        other = WorkOrder.objects.create(tenant=self.tenant_a, ERP_id='WO-OTHER', quantity=1)
        with self.assertRaises(ValidationError) as ctx:
            assert_work_order_allowed(part, other)
        # The message has to name the core, or nobody can act on the refusal.
        self.assertIn('CORE-RSV-1', str(ctx.exception))

    def test_a_reserved_part_may_join_its_own_cores_work(self):
        from Tracker.models import WorkOrder
        from Tracker.services.reman.reservation import assert_work_order_allowed

        part = self._accept(self.their_component)
        wo = WorkOrder.objects.create(tenant=self.tenant_a, ERP_id='WO-OWN', quantity=1)
        self.theirs.work_order = wo
        self.theirs.save(update_fields=['work_order'])
        part.refresh_from_db()
        assert_work_order_allowed(part, wo)  # must not raise

    def test_detaching_a_reserved_part_is_always_allowed(self):
        """Putting a part back on the shelf takes nothing from anyone, and refusing it
        would strand a part that was attached by mistake."""
        from Tracker.services.reman.reservation import assert_work_order_allowed
        part = self._accept(self.their_component)
        assert_work_order_allowed(part, None)  # must not raise

    def test_an_unreserved_part_goes_anywhere(self):
        from Tracker.models import WorkOrder
        from Tracker.services.reman.reservation import assert_work_order_allowed
        part = self._accept(self.our_component)
        wo = WorkOrder.objects.create(tenant=self.tenant_a, ERP_id='WO-FREE', quantity=1)
        assert_work_order_allowed(part, wo)  # must not raise

    def test_the_api_refuses_to_attach_a_reserved_part(self):
        """The serializer is the boundary that matters: parts are otherwise created
        fresh per work order, so this is the only path by which a harvested part can
        reach somebody else's job."""
        from rest_framework.exceptions import ValidationError as DRFValidationError
        from Tracker.models import WorkOrder
        from Tracker.serializers.mes_lite import PartsSerializer

        part = self._accept(self.their_component)
        other = WorkOrder.objects.create(tenant=self.tenant_a, ERP_id='WO-API', quantity=1)
        ser = PartsSerializer(part, data={'work_order': str(other.pk)}, partial=True)
        with self.assertRaises((DRFValidationError, DjangoValidationError)):
            ser.is_valid(raise_exception=True)

    def test_releasing_puts_it_back_in_stock(self):
        """The escape hatch for an arrangement that changed after receipt — a customer
        scrapping their unit and taking an exchange instead."""
        from Tracker.models import WorkOrder
        from Tracker.services.reman.reservation import (
            assert_work_order_allowed, release_reservation)

        part = self._accept(self.their_component)
        release_reservation(part)
        part.refresh_from_db()
        self.assertIsNone(part.reserved_for_core_id)
        wo = WorkOrder.objects.create(tenant=self.tenant_a, ERP_id='WO-REL', quantity=1)
        assert_work_order_allowed(part, wo)  # must not raise

    def test_voiding_a_core_does_not_release_its_parts(self):
        """The realistic path: cores are soft-deleted, so `delete()` archives the row
        and the reservation must survive it. A voided core whose parts quietly became
        stock would lose the customer's property to a bookkeeping action."""
        part = self._accept(self.their_component)
        self.theirs.delete()  # soft delete — archives, does not remove
        part.refresh_from_db()
        self.assertEqual(part.reserved_for_core_id, self.theirs.id)


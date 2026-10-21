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
from Tracker.services.reman.core_part import create_core, move_core


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
        core = create_core(
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
        create_core(
            tenant=self.tenant,
            core_number="CORE-DUP",
            core_type=self.injector_core_type,
            received_date=date.today(),
            received_by=self.receiving_clerk,
            condition_grade='A'
        )

        with self.assertRaises(Exception):  # IntegrityError
            create_core(
                tenant=self.tenant,
                core_number="CORE-DUP",  # Duplicate
                core_type=self.injector_core_type,
                received_date=date.today(),
                received_by=self.receiving_clerk,
                condition_grade='A'
            )

    def test_start_disassembly(self):
        """Test starting disassembly workflow."""
        core = create_core(
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
        core = create_core(
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
        core = create_core(
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
        core = create_core(
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
        core = create_core(
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
        core = create_core(
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
        self.core = create_core(
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
        # IN_STOCK, not PENDING: accepting a component is what makes it available,
        # and `_available_supply` counts only IN_STOCK — left PENDING it was
        # invisible as supply. PENDING means "created, not yet started", which
        # describes a unit to be built, not a part on a shelf.
        self.assertEqual(part.part_status, PartsStatus.IN_STOCK)
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
        core = create_core(
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
        core = create_core(
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
        core = create_core(
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
        core = create_core(
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
        core = create_core(
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
        core = create_core(
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
        core = create_core(
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
        core = create_core(
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
        core = create_core(
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
        core = create_core(
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
        # IN_STOCK, not PENDING: accepting a component is what makes it available,
        # and `_available_supply` counts only IN_STOCK — left PENDING it was
        # invisible as supply. PENDING means "created, not yet started", which
        # describes a unit to be built, not a part on a shelf.
        self.assertEqual(nozzle_part.part_status, PartsStatus.IN_STOCK)
        self.assertEqual(solenoid_part.part_status, PartsStatus.IN_STOCK)


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
        core = create_core(
            tenant=self.tenant,
            core_number="CORE-WO-001",
            core_type=self.injector_core_type,
            received_date=date.today(),
            received_by=self.receiving_clerk,
            condition_grade='A',
            work_order=work_order  # Link to WO
        )

        self.assertEqual(core.part.work_order, work_order)
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
        core = create_core(
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
        # IN_STOCK, not PENDING: accepting a component is what makes it available,
        # and `_available_supply` counts only IN_STOCK — left PENDING it was
        # invisible as supply. PENDING means "created, not yet started", which
        # describes a unit to be built, not a part on a shelf.
        self.assertEqual(part.part_status, PartsStatus.IN_STOCK)

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
        core = create_core(
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
        core = create_core(
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
            core = create_core(
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
            core = create_core(
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
            core = create_core(
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
        self.core = create_core(
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
        self.core = create_core(
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
            return create_core(
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
        move_core(self.theirs, work_order=wo)
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



class RebuildScopeResolutionTests(TenantTestCase):
    """Scope is derived FROM the resolved slots, not beside them — and since 2026-10-12
    it PLANS the rebuild rather than routing it: the codes a unit's findings raise, and
    the Repair nodes in its process those codes send it to (services/reman/scope)."""

    def setUp(self):
        super().setUp()
        from Tracker.models import (
            HarvestedComponent, PartTypes, Processes, ProcessStep, RebuildScopePreset,
            RepairCode, StepEdge, Steps, WorkOrder, WorkOrderStatus,
        )
        from Tracker.models.mes_lite import EdgeType

        self.core_type = PartTypes.objects.create(tenant=self.tenant_a, name='Injector')
        self.nozzle = PartTypes.objects.create(tenant=self.tenant_a, name='Nozzle')
        process = Processes.objects.create(
            tenant=self.tenant_a, name='Reman', part_type=self.core_type, status='APPROVED')

        def _step(name, order, **kw):
            st = Steps.objects.create(tenant=self.tenant_a, part_type=self.core_type,
                                      name=name, **kw)
            ProcessStep.objects.create(process=process, step=st, order=order)
            return st

        self.base = RepairCode.objects.create(
            tenant=self.tenant_a, code='BASE', name='Base rebuild', trigger='ALWAYS')
        self.recon = RepairCode.objects.create(
            tenant=self.tenant_a, code='NZL-RECON', name='Recondition nozzle',
            component_type=self.nozzle, trigger='RECONDITION')
        self.premium = RepairCode.objects.create(
            tenant=self.tenant_a, code='FLOW', name='Flow test', trigger='PRESET')

        self.check = _step('Nozzle Check', 1)
        self.hone = _step('Hone Nozzle', 2, step_type='REPAIR', repair_code=self.recon)
        self.assemble = _step('Assembly', 3)
        self.edge = StepEdge.objects.create(process=process, from_step=self.check,
                                            to_step=self.hone, edge_type=EdgeType.ALTERNATE,
                                            pre_approved=True)
        StepEdge.objects.create(process=process, from_step=self.check, to_step=self.assemble,
                                edge_type=EdgeType.DEFAULT)

        wo = WorkOrder.objects.create(tenant=self.tenant_a, ERP_id='WO-SCOPE-R', quantity=1,
                                      workorder_status=WorkOrderStatus.IN_PROGRESS,
                                      process=process)
        self.core = create_core(
            tenant=self.tenant_a, core_number='CORE-SCOPE-1', core_type=self.core_type,
            status='DISASSEMBLED', received_date=date.today(), received_by=self.user_a,
            work_order=wo, step=self.check)
        self._HarvestedComponent = HarvestedComponent
        self._RebuildScopePreset = RebuildScopePreset

    def _harvest(self, grade):
        return self._HarvestedComponent.objects.create(
            tenant=self.tenant_a, core=self.core, component_type=self.nozzle,
            condition_grade=grade, disassembled_by=self.user_a)

    def _slots(self):
        """Slots as the rebuild resolver would produce them, without a BOM fixture."""
        from Tracker.services.reman.rebuild import RECONDITION, REUSE, Slot
        hc = self.core.harvested_components.filter(is_scrapped=False).first()
        grade = hc.condition_grade if hc else None
        resolution = REUSE if grade in ('A', 'B') else RECONDITION
        return [Slot(
            position='', component_type_id=str(self.nozzle.id),
            component_type_name='Nozzle', bom_line_id=None,
            finding=f"Grade {grade}, from this unit", resolution=resolution,
            reason='', candidates=[],
        )]

    def test_always_codes_are_raised_whatever_the_finding(self):
        from Tracker.services.reman.scope import resolve_scope
        self._harvest('A')
        self.assertIn('BASE', resolve_scope(self.core, self._slots()).raised_codes)

    def test_a_finding_raises_its_repair_and_says_why(self):
        """The `because` is the point: a repair nobody can trace back to a finding is one
        nobody can challenge, and the over-and-above quote has to show it."""
        from Tracker.services.reman.scope import resolve_scope
        self._harvest('C')
        scope = resolve_scope(self.core, self._slots())
        hone = next(o for o in scope.expected_repairs if o.step_name == 'Hone Nozzle')
        self.assertEqual((hone.code, hone.check_name), ('NZL-RECON', 'Nozzle Check'))
        self.assertTrue(any('Grade C' in b for b in hone.because))
        self.assertFalse(hone.needs_approval)   # pre-approved at the check

    def test_a_repair_not_pre_approved_is_flagged_early(self):
        """Seen on the plan before the unit reaches the check, so the answer can be
        sought ahead of time rather than discovered as a hold."""
        from Tracker.services.reman.scope import resolve_scope
        self.edge.pre_approved = False
        self.edge.save(update_fields=['pre_approved'])
        self._harvest('C')
        hone = next(o for o in resolve_scope(self.core, self._slots()).expected_repairs)
        self.assertTrue(hone.needs_approval)

    def test_a_serviceable_component_raises_no_repair(self):
        from Tracker.services.reman.scope import resolve_scope
        self._harvest('B')
        self.assertEqual(resolve_scope(self.core, self._slots()).expected_repairs, [])

    def test_a_preset_only_code_needs_the_preset(self):
        """PRESET is what distinguishes one sold rebuild level from another: no finding
        raises it, so without the level it is simply not raised."""
        from Tracker.services.reman.scope import resolve_scope
        self._harvest('A')
        self.assertNotIn('FLOW', resolve_scope(self.core, self._slots()).raised_codes)
        preset = self._RebuildScopePreset.objects.create(
            tenant=self.tenant_a, core_type=self.core_type, name='Full overhaul', is_default=True)
        preset.codes.set([self.premium])
        scope = resolve_scope(self.core, self._slots())
        self.assertIn('FLOW', scope.raised_codes)
        self.assertEqual(scope.entry_scope, 'Full overhaul')

    def test_no_configuration_degrades_to_a_warning_not_an_error(self):
        """A shop that has authored nothing gets an honest empty answer and a warning."""
        from Tracker.services.reman.scope import resolve_scope
        from Tracker.models import RepairCode
        RepairCode.objects.all().delete()
        self._harvest('A')
        scope = resolve_scope(self.core, self._slots())
        self.assertEqual(scope.expected_repairs, [])
        self.assertTrue(scope.warnings)

class CoreReleaseTests(TenantTestCase):
    """Teardown ends in one of two places, and which one is not a free choice.

    A unit that goes back to its customer must be rebuilt; anything else is a source
    of parts. The services refuse the wrong one rather than trusting the caller, so a
    mis-click on the work-order surface cannot pool a customer's own components.
    """

    def setUp(self):
        super().setUp()
        from Tracker.models import Core, HarvestedComponent, PartTypes

        self.core_type = PartTypes.objects.create(tenant=self.tenant_a, name='Injector')
        self.component_type = PartTypes.objects.create(
            tenant=self.tenant_a, name='Nozzle', ID_prefix='NZ')

        def _core(number, mode):
            return create_core(
                tenant=self.tenant_a, core_number=number, core_type=self.core_type,
                fulfilment_mode=mode, status='DISASSEMBLED',
                received_date=date.today(), received_by=self.user_a)

        self.theirs = _core('CORE-REL-1', 'REPAIR_RETURN')
        self.ours = _core('CORE-REL-2', 'EXCHANGE')
        for core in (self.theirs, self.ours):
            HarvestedComponent.objects.create(
                tenant=self.tenant_a, core=core, component_type=self.component_type,
                condition_grade='A', disassembled_by=self.user_a)

    def test_an_exchange_core_releases_its_components_to_stock(self):
        from Tracker.models import PartsStatus
        from Tracker.services.reman.release import release_core_to_inventory

        core, accepted = release_core_to_inventory(self.ours, self.user_a)
        self.assertEqual(core.status, 'HARVESTED')
        self.assertEqual(len(accepted), 1)
        # Stock, not PENDING — otherwise nothing counts it as supply and the exchange
        # premise connects at neither end.
        self.assertEqual(accepted[0].part_status, PartsStatus.IN_STOCK)

    def test_a_customers_unit_cannot_be_released_to_stock(self):
        """The expensive direction: pooling a repair-and-return core's components means
        the customer's own unit can never be reassembled."""
        from django.core.exceptions import ValidationError
        from Tracker.services.reman.release import release_core_to_inventory

        with self.assertRaises(ValidationError) as ctx:
            release_core_to_inventory(self.theirs, self.user_a)
        self.assertIn('back to its customer', str(ctx.exception))

    def test_an_exchange_core_may_be_released_into_rebuild(self):
        """Exchange cores are normally rebuilt — to stock (decided 2026-09-24; it used
        to be refused, which left planning's exchange rebuilds unreachable). This one
        has no route to continue on, so it is refused for THAT reason, not its mode."""
        from django.core.exceptions import ValidationError
        from Tracker.services.reman.release import release_core_to_rebuild

        with self.assertRaises(ValidationError) as ctx:
            release_core_to_rebuild(self.ours, self.user_a)
        self.assertNotIn('exchange unit', str(ctx.exception))
        self.assertIn('no next step on its route', str(ctx.exception))

    def test_releasing_into_rebuild_needs_a_route_to_continue_on(self):
        """Releasing with nowhere to go would put a unit on a work order with nothing
        to do, which reads as 'rebuilt' having done none of the work."""
        from django.core.exceptions import ValidationError
        from Tracker.services.reman.release import release_core_to_rebuild

        with self.assertRaises(ValidationError) as ctx:
            release_core_to_rebuild(self.theirs, self.user_a)
        self.assertIn('no next step on its route', str(ctx.exception))

    def test_only_a_disassembled_core_can_be_released(self):
        from django.core.exceptions import ValidationError
        from Tracker.services.reman.release import release_core_to_inventory

        self.ours.status = 'IN_DISASSEMBLY'
        self.ours.save(update_fields=['status'])
        with self.assertRaises(ValidationError):
            release_core_to_inventory(self.ours, self.user_a)

    def test_releasing_to_inventory_twice_finishes_cleanly(self):
        """A partial release must be resumable — components already accepted are
        skipped rather than raising, so a second run completes the job."""
        from Tracker.services.reman.release import release_core_to_inventory

        release_core_to_inventory(self.ours, self.user_a)
        self.ours.status = 'DISASSEMBLED'          # simulate a resumed release
        self.ours.save(update_fields=['status'])
        core, accepted = release_core_to_inventory(self.ours, self.user_a)
        self.assertEqual(core.status, 'HARVESTED')
        self.assertEqual(accepted, [])


class RecoverabilityResolutionTests(TenantTestCase):
    """Recoverability is a property of the ITEM, not of a BOM line's use of it.

    A seal kit is expendable in every BOM for everyone; asking per line is how the same
    part ends up flagged reusable in one place and not another. The chain mirrors the
    outside-process turnaround and the fulfilment mode: per-use override → item master
    → no.
    """

    def setUp(self):
        super().setUp()
        from Tracker.models import BOM, BOMLine, Material, PartTypes

        self.parent = PartTypes.objects.create(tenant=self.tenant_a, name='Injector')
        self.rotable = PartTypes.objects.create(
            tenant=self.tenant_a, name='Nozzle Assembly', can_recover=True)
        self.expendable = PartTypes.objects.create(
            tenant=self.tenant_a, name='Seal Kit', can_recover=False)
        self.material = Material.objects.create(tenant=self.tenant_a, name='Sealant')

        self.bom = BOM.objects.create(
            tenant=self.tenant_a, part_type=self.parent, revision='A',
            bom_type='ASSEMBLY', status='RELEASED')
        self._BOMLine = BOMLine

    def _line(self, **kw):
        return self._BOMLine.objects.create(tenant=self.tenant_a, bom=self.bom, quantity=1, **kw)

    def test_a_rotable_component_is_recoverable_by_default(self):
        from Tracker.services.mes.bom import line_allows_recovery
        self.assertTrue(line_allows_recovery(self._line(component_type=self.rotable)))

    def test_an_expendable_component_is_not(self):
        from Tracker.services.mes.bom import line_allows_recovery
        self.assertFalse(line_allows_recovery(self._line(component_type=self.expendable)))

    def test_raw_material_is_never_recoverable_whatever_the_override(self):
        """The bug this replaces: `allow_harvested` defaulted True on EVERY line
        including material ones, and `consume_for_step` skips harvest-eligible lines on
        a reman WO — so a reman job silently never issued its springs or seals."""
        from Tracker.services.mes.bom import line_allows_recovery
        line = self._line(material=self.material, allow_harvested=True)
        self.assertFalse(line_allows_recovery(line))

    def test_an_override_beats_the_item_master_in_both_directions(self):
        """The exception the override exists for: a safety-critical position or a
        customer contract that forbids reuse even of a normally recoverable item."""
        from Tracker.services.mes.bom import line_allows_recovery
        self.assertFalse(
            line_allows_recovery(self._line(component_type=self.rotable, allow_harvested=False)))
        self.assertTrue(
            line_allows_recovery(self._line(component_type=self.expendable, allow_harvested=True)))

    def test_the_values_row_variant_agrees_with_the_orm_one(self):
        """The scheduling gate reads `.values()` rows in bulk. Two readings of one rule
        is how they drift, so they are tested against each other."""
        from Tracker.services.mes.bom import line_allows_recovery, values_row_allows_recovery
        for line in (self._line(component_type=self.rotable),
                     self._line(component_type=self.expendable),
                     self._line(material=self.material)):
            row = {
                'component_type_id': line.component_type_id,
                'allow_harvested': line.allow_harvested,
                'component_type__can_recover': (
                    line.component_type.can_recover if line.component_type_id else None),
            }
            self.assertEqual(
                values_row_allows_recovery(row), line_allows_recovery(line),
                f"disagreement on {line}")


class RebuildLifecycleTests(TenantTestCase):
    """The repair-and-return path end to end: rebuild, authorise, return.

    Each transition refuses the states it does not belong to, because a lifecycle that
    only works when called in the right order is one that will be called in the wrong
    order.
    """

    def setUp(self):
        super().setUp()
        from Tracker.models import Core, HarvestedComponent, PartTypes

        self.core_type = PartTypes.objects.create(tenant=self.tenant_a, name='Injector')
        self.component_type = PartTypes.objects.create(
            tenant=self.tenant_a, name='Nozzle', can_recover=True)
        from Tracker.models import Companies
        self.customer = Companies.objects.create(tenant=self.tenant_a, name='Fleet Co')
        self.core = create_core(
            tenant=self.tenant_a, core_number='CORE-LIFE-1', core_type=self.core_type,
            fulfilment_mode='REPAIR_RETURN', status='IN_REBUILD', customer=self.customer,
            received_date=date.today(), received_by=self.user_a)
        self.hc = HarvestedComponent.objects.create(
            tenant=self.tenant_a, core=self.core, component_type=self.component_type,
            condition_grade='B', disassembled_by=self.user_a)

    def test_installing_the_units_own_component_is_recorded_as_built(self):
        from Tracker.services.reman.rebuild_execution import install_component
        usage = install_component(self.core, harvested=self.hc, user=self.user_a)
        # The unit being rebuilt is the core's part (a core is a part).
        self.assertEqual(usage.assembly_id, self.core.part_id)
        self.assertEqual(usage.component_harvested_id, self.hc.id)
        # The child is the unit's own harvested component, never a stock part — it is
        # the customer's, and never became stock.
        self.assertIsNone(usage.component_id)

    def test_another_cores_component_is_refused(self):
        """Reinstalling one unit's part into another is what `reserved_for_core` exists
        to prevent — a repair-and-return customer's components are their property."""
        from django.core.exceptions import ValidationError
        from Tracker.models import Core, HarvestedComponent
        other = create_core(
            tenant=self.tenant_a, core_number='CORE-LIFE-2', core_type=self.core_type,
            fulfilment_mode='REPAIR_RETURN', status='IN_REBUILD',
            received_date=date.today(), received_by=self.user_a)
        theirs = HarvestedComponent.objects.create(
            tenant=self.tenant_a, core=other, component_type=self.component_type,
            condition_grade='A', disassembled_by=self.user_a)
        from Tracker.services.reman.rebuild_execution import install_component
        with self.assertRaises(ValidationError):
            install_component(self.core, harvested=theirs, user=self.user_a)

    def test_a_scrapped_component_cannot_go_back_in(self):
        from django.core.exceptions import ValidationError
        from Tracker.services.reman.harvested_component import scrap_component
        from Tracker.services.reman.rebuild_execution import install_component
        scrap_component(self.hc, self.user_a, reason='cracked')
        with self.assertRaises(ValidationError):
            install_component(self.core, harvested=self.hc, user=self.user_a)

    def test_completing_a_rebuild_does_not_demand_every_slot_filled(self):
        """The as-built record is what WENT IN. Asserting completeness against the
        proposal would make the proposal authoritative over what the bench did."""
        from Tracker.services.reman.rebuild_execution import complete_rebuild
        core = complete_rebuild(self.core, self.user_a)
        self.assertEqual(core.status, 'REBUILT')

    def test_a_rebuilt_unit_returns_to_its_customer(self):
        from Tracker.services.reman.rebuild_execution import complete_rebuild
        from Tracker.services.reman.release import return_core_to_customer
        complete_rebuild(self.core, self.user_a)
        core = return_core_to_customer(self.core, self.user_a, reference='CN-99',
                                       carrier='UPS', tracking_number='1Z9')
        self.assertEqual(core.status, 'RETURNED')
        self.assertIsNotNone(core.returned_at)
        # It left on a shipment of its own, so its packing list and CoC print.
        shipment = core.part.customer_shipment
        self.assertIsNotNone(shipment)
        self.assertEqual(shipment.customer_id, self.customer.id)
        self.assertEqual((shipment.reference, shipment.carrier, shipment.tracking_number),
                         ('CN-99', 'UPS', '1Z9'))
        self.assertEqual(core.return_reference, shipment.shipment_number)
        self.assertEqual(core.part.part_status, 'SHIPPED')

    def test_a_unit_with_no_customer_recorded_cannot_be_returned(self):
        from django.core.exceptions import ValidationError
        from Tracker.services.reman.rebuild_execution import complete_rebuild
        from Tracker.services.reman.release import return_core_to_customer
        complete_rebuild(self.core, self.user_a)
        self.core.customer = None
        self.core.save(update_fields=['customer'])
        with self.assertRaises(ValidationError):
            return_core_to_customer(self.core, self.user_a)

    def test_an_exchange_unit_has_no_owner_to_return_to(self):
        from django.core.exceptions import ValidationError
        from Tracker.services.reman.release import return_core_to_customer
        self.core.fulfilment_mode = 'EXCHANGE'
        self.core.status = 'REBUILT'
        self.core.save(update_fields=['fulfilment_mode', 'status'])
        with self.assertRaises(ValidationError):
            return_core_to_customer(self.core, self.user_a)

    def test_authorisation_is_only_asked_for_work_beyond_what_was_sold(self):
        """The entry scope was already bought. A job whose findings raised nothing new
        needs no gate, and being sent to one would stall it for nothing."""
        from django.core.exceptions import ValidationError
        from Tracker.services.reman.release import request_authorisation
        with self.assertRaises(ValidationError) as ctx:
            request_authorisation(self.core, self.user_a)
        self.assertIn('nothing to authorise', str(ctx.exception))

    def test_a_declined_scope_still_has_to_go_back(self):
        """Declined is not the end: the unit is still the customer's and still in the
        building. It leaves by the same dispatch a rebuilt one does."""
        from Tracker.services.reman.release import record_authorisation, return_core_to_customer
        self.core.status = 'AWAITING_AUTHORISATION'
        self.core.save(update_fields=['status'])
        core = record_authorisation(self.core, approved=False, user=self.user_a,
                                    note='Customer declined the nozzle work')
        self.assertEqual(core.status, 'DECLINED')
        core = return_core_to_customer(core, self.user_a, reference='CN-100')
        self.assertEqual(core.status, 'RETURNED_UNREPAIRED')
        self.assertIsNotNone(core.part.customer_shipment)

    def test_approval_resumes_the_rebuild(self):
        from Tracker.services.reman.release import record_authorisation
        self.core.status = 'AWAITING_AUTHORISATION'
        self.core.save(update_fields=['status'])
        core = record_authorisation(self.core, approved=True, user=self.user_a)
        self.assertEqual(core.status, 'IN_REBUILD')


class RecoverableSupplyTests(TenantTestCase):
    """What the core bank could yield — reported, never netted.

    Recoverable supply is a FORECAST: teardown has not happened. On-hand is a fact.
    Folding one into the other would let a planner skip an order on stock that does
    not exist yet, and the error is asymmetric — over-counting future supply stops a
    line, under-counting only buys a part you could have harvested.
    """

    def setUp(self):
        super().setUp()
        from Tracker.models import Core, DisassemblyBOMLine, PartTypes

        self.core_type = PartTypes.objects.create(tenant=self.tenant_a, name='Injector')
        self.rotable = PartTypes.objects.create(
            tenant=self.tenant_a, name='Nozzle', can_recover=True)
        self.expendable = PartTypes.objects.create(
            tenant=self.tenant_a, name='Seal Kit', can_recover=False)

        for ct in (self.rotable, self.expendable):
            DisassemblyBOMLine.objects.create(
                tenant=self.tenant_a, core_type=self.core_type, component_type=ct,
                expected_qty=2, expected_fallout_rate=Decimal('0.50'))

        self._Core = Core

    def _core(self, number, status, mode='EXCHANGE'):
        return create_core(
            tenant=self.tenant_a, core_number=number, core_type=self.core_type,
            fulfilment_mode=mode, status=status,
            received_date=date.today(), received_by=self.user_a)

    def test_the_bank_yields_expected_usable_quantity(self):
        from Tracker.services.reman.recovery import recoverable_supply
        self._core('BANK-1', 'RECEIVED')
        self._core('BANK-2', 'IN_DISASSEMBLY')
        # 2 cores x (2 expected - 50% fallout) = 2
        self.assertEqual(recoverable_supply(self.rotable).quantity, Decimal('2.0'))

    def test_an_expendable_yields_nothing_whatever_the_bank_holds(self):
        from Tracker.services.reman.recovery import recoverable_supply
        self._core('BANK-3', 'RECEIVED')
        self.assertEqual(recoverable_supply(self.expendable).quantity, Decimal('0'))

    def test_a_customers_own_unit_is_not_available_supply(self):
        """A repair-and-return core is committed to its owner. You cannot tear down
        someone's unit for another job."""
        from Tracker.services.reman.recovery import recoverable_supply
        self._core('BANK-4', 'RECEIVED', mode='REPAIR_RETURN')
        self.assertEqual(recoverable_supply(self.rotable).quantity, Decimal('0'))

    def test_an_already_torn_down_core_is_not_counted_twice(self):
        """A DISASSEMBLED core has given its components up — they are harvested rows by
        then, and counting the core as well would double them."""
        from Tracker.services.reman.recovery import recoverable_supply
        self._core('BANK-5', 'DISASSEMBLED')
        self._core('BANK-6', 'HARVESTED')
        self._core('BANK-7', 'SCRAPPED')
        self.assertEqual(recoverable_supply(self.rotable).quantity, Decimal('0'))

    def test_it_names_where_the_number_came_from(self):
        """A planner who cannot see which cores a forecast came from cannot judge
        whether to trust it."""
        from Tracker.services.reman.recovery import recoverable_supply
        self._core('BANK-8', 'RECEIVED')
        rs = recoverable_supply(self.rotable)
        self.assertEqual(rs.core_count, 1)
        self.assertEqual(rs.sources[0]['core_type'], 'Injector')
        self.assertEqual(rs.sources[0]['cores'], 1)


class RepairRoutingTests(TenantTestCase):
    """Repairs are branches off checks (2026-10-12, services/reman/repair_routing).

    Every op on the main line runs — nothing is skipped. A check sends a unit down a
    Repair node when its code is raised; a repair the check pre-approves goes ahead on
    the finding, anything else holds the unit there until a person decides.

    Route: Grade (last teardown step) → Clean → Check → Assemble → Test, with Hone
    (NZL-RECON, pre-approved) and Replace (NZL-REPLACE) off Check, both back to Assemble.
    """

    def setUp(self):
        super().setUp()
        from Tracker.models import (
            HarvestedComponent, PartTypes, Processes, ProcessStep, RepairCode, StepEdge,
            Steps, WorkOrder, WorkOrderStatus,
        )
        from Tracker.models.mes_lite import EdgeType

        self.core_type = PartTypes.objects.create(tenant=self.tenant_a, name='Injector')
        self.nozzle = PartTypes.objects.create(
            tenant=self.tenant_a, name='Nozzle', can_recover=True)
        self.process = Processes.objects.create(
            tenant=self.tenant_a, name='Reman', part_type=self.core_type, status='APPROVED')
        self.recon = RepairCode.objects.create(
            tenant=self.tenant_a, code='NZL-RECON', name='Recondition nozzle',
            component_type=self.nozzle, trigger='RECONDITION')
        self.replace = RepairCode.objects.create(
            tenant=self.tenant_a, code='NZL-REPLACE', name='Replace nozzle',
            component_type=self.nozzle, trigger='REPLACE_BUY')

        self.steps = {}
        for i, (n, kw) in enumerate([
                ('Grade', {}), ('Clean', {}), ('Check', {}), ('Assemble', {}), ('Test', {}),
                ('Hone', {'step_type': 'REPAIR', 'repair_code': self.recon}),
                ('Replace', {'step_type': 'REPAIR', 'repair_code': self.replace}),
                ('Rework', {'step_type': 'REWORK'})], start=1):
            st = Steps.objects.create(tenant=self.tenant_a, part_type=self.core_type, name=n, **kw)
            ProcessStep.objects.create(process=self.process, step=st, order=i)
            self.steps[n] = st

        def edge(a, b, t=EdgeType.DEFAULT, pre=False):
            return StepEdge.objects.create(process=self.process, from_step=self.steps[a],
                                           to_step=self.steps[b], edge_type=t, pre_approved=pre)
        for a, b in [('Grade', 'Clean'), ('Clean', 'Check'), ('Check', 'Assemble'),
                     ('Assemble', 'Test'), ('Hone', 'Assemble'), ('Replace', 'Assemble'),
                     ('Rework', 'Check')]:
            edge(a, b)
        self.hone_edge = edge('Check', 'Hone', EdgeType.ALTERNATE, pre=True)
        edge('Check', 'Replace', EdgeType.ALTERNATE, pre=False)
        edge('Check', 'Rework', EdgeType.ALTERNATE)

        self.wo = WorkOrder.objects.create(
            tenant=self.tenant_a, ERP_id='WO-REPAIR', quantity=1,
            workorder_status=WorkOrderStatus.IN_PROGRESS, process=self.process)
        # Findings raise codes through the rebuild plan, which is laid out against the
        # core type's released assembly BOM — no BOM, no slots, no codes.
        from decimal import Decimal
        from Tracker.models import BOM, BOMLine
        bom = BOM.objects.create(tenant=self.tenant_a, part_type=self.core_type, revision='A',
                                 bom_type='ASSEMBLY', status='RELEASED', is_current_version=True)
        BOMLine.objects.create(tenant=self.tenant_a, bom=bom, component_type=self.nozzle,
                               quantity=Decimal(1), source='BUY', line_number=1)
        self.core = self._core('CORE-RR-1', 'REPAIR_RETURN', step='Clean')
        self.hc = HarvestedComponent.objects.create(
            tenant=self.tenant_a, core=self.core, component_type=self.nozzle,
            condition_grade='A', disassembled_by=self.user_a)

    def _core(self, number, mode, *, step, status='IN_REBUILD'):
        return create_core(
            tenant=self.tenant_a, core_number=number, core_type=self.core_type,
            fulfilment_mode=mode, status=status, work_order=self.wo,
            step=self.steps[step], received_date=date.today(), received_by=self.user_a)

    def _grade(self, grade):
        self.hc.condition_grade = grade
        self.hc.save(update_fields=['condition_grade'])

    def _advance(self, core=None):
        from Tracker.services.mes.parts import advance_part_step
        core = core or self.core
        core.refresh_from_db()
        result = advance_part_step(core.part, operator=self.user_a)
        core.refresh_from_db()
        core.part.refresh_from_db()
        return result

    def test_nothing_on_the_main_line_is_skipped(self):
        """A serviceable unit walks every op. There is no SKIPPED any more: a repair not
        needed is a branch not taken."""
        from Tracker.models import StepExecution
        for expected in ('Check', 'Assemble', 'Test'):
            self._advance()
            self.assertEqual(self.core.part.step.name, expected)
        self.assertFalse(StepExecution.objects.filter(part=self.core.part, status='SKIPPED').exists())

    def test_a_raised_pre_approved_repair_is_taken_and_rejoins(self):
        self._grade('C')                       # reconditionable → NZL-RECON
        self._advance()                        # Clean → Check
        self._advance()                        # Check → Hone (pre-approved)
        self.assertEqual(self.core.part.step.name, 'Hone')
        self._advance()                        # Hone → Assemble
        self.assertEqual(self.core.part.step.name, 'Assemble')

    def test_a_repair_not_pre_approved_holds_a_customers_unit_for_their_answer(self):
        from Tracker.services.reman.release import record_authorisation, request_authorisation
        self.hone_edge.pre_approved = False
        self.hone_edge.save(update_fields=['pre_approved'])
        self._grade('C')
        self._advance()                        # → Check
        with self.assertRaisesMessage(ValueError, "the customer's answer"):
            self._advance()
        self.assertEqual(self.core.part.step.name, 'Check')   # held, not passed

        core, asked = request_authorisation(self.core, self.user_a)
        self.assertEqual(asked, ['NZL-RECON'])
        core = record_authorisation(core, approved=True, user=self.user_a,
                                    contact='J. Fleet', method='phone', reference='PO-77')
        self.assertIn('NZL-RECON', core.approved_repair_codes)
        self.assertIn('answered by J. Fleet', core.condition_notes)
        self._advance()
        self.assertEqual(self.core.part.step.name, 'Hone')

    def test_on_an_exchange_unit_a_lead_approves_and_no_customer_is_asked(self):
        from django.core.exceptions import ValidationError
        from Tracker.services.reman.release import request_authorisation
        from Tracker.services.reman.repair_routing import approve_repair
        self.hone_edge.pre_approved = False
        self.hone_edge.save(update_fields=['pre_approved'])
        self.core.fulfilment_mode = 'EXCHANGE'
        self.core.save(update_fields=['fulfilment_mode'])
        self._grade('C')
        self._advance()
        with self.assertRaisesMessage(ValueError, "a lead's approval"):
            self._advance()
        with self.assertRaises(ValidationError):
            request_authorisation(self.core, self.user_a)   # no customer to ask
        approve_repair(self.core, 'NZL-RECON', user=self.user_a)
        self._advance()
        self.assertEqual(self.core.part.step.name, 'Hone')

    def test_a_lead_cannot_approve_on_a_customers_behalf(self):
        from django.core.exceptions import ValidationError
        from Tracker.services.reman.repair_routing import approve_repair
        self.hone_edge.pre_approved = False
        self.hone_edge.save(update_fields=['pre_approved'])
        self._grade('C')
        with self.assertRaises(ValidationError):
            approve_repair(self.core, 'NZL-RECON', user=self.user_a)

    def test_a_repair_sold_with_the_rebuild_level_needs_no_approval(self):
        from Tracker.models import RebuildScopePreset
        self.hone_edge.pre_approved = False
        self.hone_edge.save(update_fields=['pre_approved'])
        preset = RebuildScopePreset.objects.create(
            tenant=self.tenant_a, core_type=self.core_type, name='Standard', is_default=True)
        preset.codes.set([self.recon])
        self._grade('C')
        self._advance()
        self._advance()
        self.assertEqual(self.core.part.step.name, 'Hone')

    def test_a_pending_finding_holds_the_unit_at_a_check_only(self):
        """Passing an unreviewed finding down the main line is the silent release this
        replaces; a step with no repairs isn't where it's decided, so it doesn't hold."""
        from Tracker.services.reman.findings import record_finding
        record_finding(self.hc, grade='C', finding='Pitting on the seat', user=self.user_a)
        self._advance()                        # Clean has no repairs → moves on
        self.assertEqual(self.core.part.step.name, 'Check')
        with self.assertRaisesMessage(ValueError, "waiting on a lead"):
            self._advance()

    def test_a_finding_with_no_repair_at_this_check_says_raise_an_ncr(self):
        from Tracker.models import HarvestedComponent, PartTypes
        from Tracker.services.reman.findings import record_finding
        body_type = PartTypes.objects.create(tenant=self.tenant_a, name='Body', can_recover=True)
        body = HarvestedComponent.objects.create(
            tenant=self.tenant_a, core=self.core, component_type=body_type,
            condition_grade='A', disassembled_by=self.user_a)
        self._advance()
        record_finding(body, grade='C', finding='Thread galled', user=self.user_a)
        with self.assertRaisesMessage(ValueError, 'no planned repair'):
            self._advance()

    def test_a_serviceable_finding_waits_on_a_lead_not_an_ncr(self):
        from Tracker.services.reman.findings import record_finding
        self._advance()
        record_finding(self.hc, grade='B', finding='Seat a shade dull', user=self.user_a)
        with self.assertRaisesMessage(ValueError, "waiting on a lead"):
            self._advance()

    def test_a_scrap_finding_waits_on_a_lead_without_promising_a_branch(self):
        """Whether scrap ends in a replace branch depends on stock the plan finds, so
        the hold names the sign-off, not a repair."""
        from Tracker.services.reman.findings import record_finding
        self._advance()
        record_finding(self.hc, grade='SCRAP', finding='Cracked', user=self.user_a)
        with self.assertRaisesMessage(ValueError, 'proposed for scrap'):
            self._advance()

    def test_a_finding_captured_at_a_check_applies_itself_when_pre_approved(self):
        from Tracker.models import StepExecution
        from Tracker.services.reman.findings import record_findings_from_capture
        self._advance()                        # → Check
        se = StepExecution.objects.filter(part=self.core.part, step=self.steps['Check']).first() \
            or StepExecution.objects.create(part=self.core.part, step=self.steps['Check'],
                                            status='IN_PROGRESS', visit_number=1)
        out = record_findings_from_capture(se, [{'harvested_id': str(self.hc.id), 'grade': 'C',
                                                 'finding': 'Seat pitted'}], self.user_a)
        self.hc.refresh_from_db()
        self.assertEqual(out['applied_component_ids'], [str(self.hc.id)])
        self.assertEqual((self.hc.condition_grade, self.hc.proposed_grade), ('C', ''))
        self.assertIn('Applied automatically', self.hc.condition_notes)

    def test_scrap_is_never_applied_without_a_lead(self):
        from Tracker.models import StepExecution
        from Tracker.services.reman.findings import record_findings_from_capture
        self._advance()
        se = StepExecution.objects.create(part=self.core.part, step=self.steps['Check'],
                                          status='IN_PROGRESS', visit_number=9)
        out = record_findings_from_capture(se, [{'harvested_id': str(self.hc.id),
                                                 'grade': 'SCRAP', 'finding': 'Cracked'}],
                                           self.user_a)
        self.hc.refresh_from_db()
        self.assertEqual(out['applied_component_ids'], [])
        self.assertEqual(self.hc.proposed_grade, 'SCRAP')

    def test_a_failed_inspection_goes_to_rework_not_down_a_repair(self):
        """With repair branches and a rework branch both on the check, the ordinary
        pass/fail lookup must not pick a Repair node."""
        from Tracker.models.mes_lite import EdgeType
        self.core.part.step = self.steps['Check']
        self.assertEqual(self.core.part._get_edge(self.steps['Check'], EdgeType.ALTERNATE),
                         self.steps['Rework'])

    def test_a_teardown_core_is_not_routed_to_repairs(self):
        self._grade('C')
        unit = self._core('CORE-TD-1', 'EXCHANGE', step='Check', status='IN_DISASSEMBLY')
        self._advance(unit)
        self.assertEqual(unit.part.step.name, 'Assemble')

    def test_a_repair_already_done_is_not_taken_again(self):
        """A route that sends the unit back through the check after its repair must not
        loop it down the same repair."""
        from Tracker.models import StepExecution
        self._grade('C')
        StepExecution.objects.create(part=self.core.part, step=self.steps['Hone'],
                                     status='COMPLETED', visit_number=1)
        self._advance()
        self._advance()
        self.assertEqual(self.core.part.step.name, 'Assemble')

    # ----- the REPAIR ("Needs repair") inspection result (2026-10-21) -----

    def _at_check(self):
        """Advance to Check and return the visit there."""
        from Tracker.models import StepExecution
        self._advance()                        # Clean → Check
        return (StepExecution.get_current_execution(self.core.part)
                or StepExecution.objects.create(part=self.core.part, step=self.steps['Check'],
                                                status='IN_PROGRESS', visit_number=1))

    def _repair_result(self, se):
        from Tracker.models import QualityReports
        return QualityReports.objects.create(
            tenant=self.tenant_a, part=self.core.part, step=se.step, step_execution=se,
            status='REPAIR', detected_by=self.user_a)

    def test_needs_repair_is_refused_off_a_repair_check(self):
        from django.core.exceptions import ValidationError
        from Tracker.models import QualityReports
        from Tracker.services.dwi.operator_capture import _apply_status
        from Tracker.services.reman.repair_routing import repair_result_offered
        self.assertFalse(repair_result_offered(self.core.part, self.steps['Clean']))
        self.assertTrue(repair_result_offered(self.core.part, self.steps['Check']))
        qr = QualityReports.objects.create(tenant=self.tenant_a, part=self.core.part,
                                           step=self.steps['Clean'], status='PENDING',
                                           detected_by=self.user_a)
        with self.assertRaisesMessage(ValidationError, 'Record Pass or Fail'):
            _apply_status(qr, {'status': 'REPAIR'})
        qr.refresh_from_db()
        self.assertEqual(qr.status, 'PENDING')

    def test_needs_repair_with_no_finding_holds_and_never_goes_to_rework(self):
        se = self._at_check()
        self._repair_result(se)
        with self.assertRaisesMessage(ValueError, 'no repair was raised'):
            self._advance()
        self.assertEqual(self.core.part.step.name, 'Check')

    def test_needs_repair_with_a_pre_approved_finding_takes_the_branch_and_opens_nothing(self):
        from Tracker.models import QuarantineDisposition
        from Tracker.services.reman.findings import record_findings_from_capture
        se = self._at_check()
        record_findings_from_capture(se, [{'harvested_id': str(self.hc.id), 'grade': 'C',
                                           'finding': 'Light pitting on the seat face'}], self.user_a)
        self._repair_result(se)
        self._advance()
        self.assertEqual(self.core.part.step.name, 'Hone')
        self.assertFalse(QuarantineDisposition.objects.filter(part=self.core.part).exists())
        self.assertNotEqual(self.core.part.part_status, 'QUARANTINED')

    def test_needs_repair_with_a_finding_not_pre_approved_holds_for_a_decision(self):
        from Tracker.services.reman.findings import record_findings_from_capture
        self.hone_edge.pre_approved = False
        self.hone_edge.save(update_fields=['pre_approved'])
        se = self._at_check()
        record_findings_from_capture(se, [{'harvested_id': str(self.hc.id), 'grade': 'C',
                                           'finding': 'Seat pitted'}], self.user_a)
        self._repair_result(se)
        with self.assertRaisesMessage(ValueError, 'waiting on a lead'):
            self._advance()
        self.assertEqual(self.core.part.step.name, 'Check')

    def test_a_needs_repair_visit_is_not_an_attempt_toward_the_visit_cap(self):
        from Tracker.models import StepExecution
        se = self._at_check()
        self.assertEqual(StepExecution.get_attempt_count(self.core.part, self.steps['Check']), 1)
        self._repair_result(se)
        self.assertEqual(StepExecution.get_attempt_count(self.core.part, self.steps['Check']), 0)

    def test_first_pass_yield_leaves_out_planned_repairs_and_reports_them_apart(self):
        from Tracker.models import QualityReports
        self.grant_tenant_permissions(self.user_a, self.tenant_a, ['full_tenant_access',
                                                                   'view_qualityreports'])
        self.authenticate_as(self.user_a, self.tenant_a)
        for status in ('PASS', 'FAIL', 'REPAIR'):
            QualityReports.objects.create(tenant=self.tenant_a, part=self.core.part,
                                          step=self.steps['Check'], status=status,
                                          detected_by=self.user_a)
        r = self.client.get('/api/dashboard/kpis/')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual((r.json()['current_fpy'], r.json()['needed_repair_rate']), (50.0, 33.3))

    def test_a_finding_waiting_on_a_lead_is_in_needs_attention(self):
        from Tracker.services.reman.findings import record_finding
        record_finding(self.hc, grade='SCRAP', finding='Cracked tip', user=self.user_a)
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            'accept_component', 'full_tenant_access', 'view_harvestedcomponent'])
        self.authenticate_as(self.user_a, self.tenant_a)
        r = self.client.get('/api/dashboard/needs-attention/')
        self.assertEqual(r.status_code, 200, r.content)
        row, = [d for d in r.json()['data'] if d['type'] == 'rebuild_finding']
        self.assertEqual(row['link'], f"/reman/cores/{self.core.id}/rebuild")
        self.assertIn(self.core.core_number, row['message'])
        self.assertEqual(self.core.pending_finding_count, 1)

    def test_what_an_authorisation_request_would_ask_is_shown_before_sending(self):
        from Tracker.services.reman.release import pending_authorisation_scope
        self.hone_edge.pre_approved = False
        self.hone_edge.save(update_fields=['pre_approved'])
        self._grade('C')
        self.core.refresh_from_db()
        asking = pending_authorisation_scope(self.core, asking=True)
        self.assertEqual([a['code'] for a in asking], ['NZL-RECON'])
        self.assertEqual(pending_authorisation_scope(self.core), [])   # not yet awaiting

    def test_release_picks_up_after_the_last_teardown_step(self):
        from Tracker.services.reman.release import release_core_to_rebuild
        # The fixture's released BOM is what release plans against.
        unit = self._core('CORE-REL-AT', 'REPAIR_RETURN', step='Grade', status='DISASSEMBLED')
        core, _ = release_core_to_rebuild(unit, self.user_a)
        core.part.refresh_from_db()
        self.assertEqual((core.status, core.part.step.name), ('IN_REBUILD', 'Clean'))

    def _released(self, number, mode):
        from decimal import Decimal
        from Tracker.models import BOM, BOMLine
        from Tracker.services.reman.release import release_core_to_rebuild
        if not BOM.objects.filter(part_type=self.core_type).exists():
            bom = BOM.objects.create(
                tenant=self.tenant_a, part_type=self.core_type, revision='A',
                bom_type='ASSEMBLY', status='RELEASED', is_current_version=True)
            BOMLine.objects.create(tenant=self.tenant_a, bom=bom, component_type=self.nozzle,
                                   quantity=Decimal(1), source='BUY', line_number=1)
        unit = self._core(number, mode, step='Grade', status='DISASSEMBLED')
        core, _ = release_core_to_rebuild(unit, self.user_a)
        return core

    def test_an_exchange_unit_is_rebuilt_to_stock_keeping_its_identity(self):
        from Tracker.models import PartsStatus
        from Tracker.services.reman.rebuild_execution import complete_rebuild
        core = complete_rebuild(self._released('CORE-EX-STOCK', 'EXCHANGE'), self.user_a)
        core.part.refresh_from_db()
        self.assertEqual(core.status, 'REBUILT_TO_STOCK')
        self.assertEqual(core.part.part_status, PartsStatus.IN_STOCK)
        # Same unit: the core number is still its part's identity.
        self.assertEqual(core.part.ERP_id, 'CORE-EX-STOCK')

    def test_a_repair_and_return_unit_is_rebuilt_to_go_back(self):
        from Tracker.models import PartsStatus
        from Tracker.services.reman.rebuild_execution import complete_rebuild
        core = complete_rebuild(self._released('CORE-RR-BACK', 'REPAIR_RETURN'), self.user_a)
        core.part.refresh_from_db()
        self.assertEqual(core.status, 'REBUILT')
        self.assertEqual(core.part.part_status, PartsStatus.COMPLETED)

    def test_a_rebuilt_exchange_unit_is_not_component_stock(self):
        """Reman finished goods on the shelf are not new stock of their part type — a
        build consuming that type must not draw one as if it were new."""
        from Tracker.services.mes.bom import usable_stock_parts
        from Tracker.services.reman.rebuild_execution import complete_rebuild
        complete_rebuild(self._released('CORE-EX-SHELF', 'EXCHANGE'), self.user_a)
        for for_reman in (False, True):
            self.assertFalse(list(usable_stock_parts(
                self.core_type.id, tenant=self.tenant_a, for_reman=for_reman)))

class RemanStagingTests(TenantTestCase):
    """A rebuild's kit list.

    Staging used to skip core-subject tasks outright — "cores aren't staged" — so a
    bench rebuilding a customer's unit got no kit list at all, for the one job where
    getting the kit wrong is least recoverable.
    """

    def setUp(self):
        super().setUp()
        from Tracker.models import (
            BOM, BOMLine, Core, Material, PartTypes, Steps, WorkCenter,
        )

        self.core_type = PartTypes.objects.create(tenant=self.tenant_a, name='Injector')
        self.rotable = PartTypes.objects.create(
            tenant=self.tenant_a, name='Nozzle', can_recover=True, can_buy=True)
        self.consumable = Material.objects.create(tenant=self.tenant_a, name='Seal')

        self.wc = WorkCenter.objects.create(tenant=self.tenant_a, name='Bench')
        self.step = Steps.objects.create(
            tenant=self.tenant_a, part_type=self.core_type, name='Assemble',
            work_center=self.wc)

        bom = BOM.objects.create(
            tenant=self.tenant_a, part_type=self.core_type, revision='A',
            bom_type='ASSEMBLY', status='RELEASED')
        BOMLine.objects.create(
            tenant=self.tenant_a, bom=bom, component_type=self.rotable, quantity=1,
            source='BUY', consumed_at_step=self.step)
        BOMLine.objects.create(
            tenant=self.tenant_a, bom=bom, material=self.consumable, quantity=1,
            source='BUY', consumed_at_step=self.step)

        self.core = create_core(
            tenant=self.tenant_a, core_number='CORE-STAGE-1', core_type=self.core_type,
            fulfilment_mode='REPAIR_RETURN', status='IN_REBUILD',
            received_date=date.today(), received_by=self.user_a)

    def _rows(self, is_reman):
        from Tracker.services.mes.staging import _materials_for
        return _materials_for(
            self.core_type.id, self.step.id, units=1, onhand={},
            bom_cache={}, tenant=self.tenant_a, is_reman=is_reman)

    def test_a_recoverable_component_is_not_picked_on_a_reman_job(self):
        """`consume_for_step` skips recoverable lines on a reman WO. Listing them as
        picks would have the picker pulling a part that is then never issued — the pick
        list and the issue disagreeing about the same line."""
        rows = {r['material']: r for r in self._rows(is_reman=True)}
        self.assertTrue(rows['Nozzle']['from_teardown'])
        self.assertEqual(rows['Nozzle']['short'], 0.0)
        self.assertEqual(rows['Nozzle']['lots'], [])

    def test_consumables_are_still_picked_on_a_reman_job(self):
        """You cannot harvest a seal. The recoverability classification lives on the
        item master, and Material has none."""
        rows = {r['material']: r for r in self._rows(is_reman=True)}
        self.assertFalse(rows['Seal']['from_teardown'])
        self.assertGreater(rows['Seal']['short'], 0.0)

    def test_an_ordinary_job_picks_everything(self):
        rows = {r['material']: r for r in self._rows(is_reman=False)}
        self.assertFalse(rows['Nozzle']['from_teardown'])
        self.assertGreater(rows['Nozzle']['short'], 0.0)


class RecoveredStockVisibilityTests(TenantTestCase):
    """Recovered components are `Parts`, not `MaterialLot`s.

    Acceptance from teardown mints a Parts row, and staging built on-hand from lots
    alone — so a shelf full of recovered nozzles read as zero and the pick list called
    the line short while the part sat in the rack.
    """

    def setUp(self):
        super().setUp()
        from Tracker.models import (
            BOM, BOMLine, Core, HarvestedComponent, PartTypes, Steps, WorkCenter,
        )

        self.core_type = PartTypes.objects.create(tenant=self.tenant_a, name='Injector')
        self.rotable = PartTypes.objects.create(
            tenant=self.tenant_a, name='Nozzle', can_recover=True, can_buy=True,
            ID_prefix='NZ')
        self.wc = WorkCenter.objects.create(tenant=self.tenant_a, name='Bench')
        self.step = Steps.objects.create(
            tenant=self.tenant_a, part_type=self.core_type, name='Assemble',
            work_center=self.wc)
        bom = BOM.objects.create(
            tenant=self.tenant_a, part_type=self.core_type, revision='A',
            bom_type='ASSEMBLY', status='RELEASED')
        BOMLine.objects.create(
            tenant=self.tenant_a, bom=bom, component_type=self.rotable, quantity=1,
            source='BUY', consumed_at_step=self.step)

        # A donor core, harvested and accepted — the normal way recovered stock appears.
        donor = create_core(
            tenant=self.tenant_a, core_number='CORE-DONOR', core_type=self.core_type,
            fulfilment_mode='EXCHANGE', status='DISASSEMBLED',
            received_date=date.today(), received_by=self.user_a)
        hc = HarvestedComponent.objects.create(
            tenant=self.tenant_a, core=donor, component_type=self.rotable,
            condition_grade='A', disassembled_by=self.user_a)
        from Tracker.services.reman.harvested_component import accept_component_to_inventory
        self.recovered_part = accept_component_to_inventory(hc, self.user_a,
                                                            transfer_life=False)

    def _row(self, *, is_reman, lots=0, recovered=1, units=1):
        from Tracker.services.mes.staging import _materials_for
        key = ('PART_TYPE', self.rotable.id)
        return _materials_for(
            self.core_type.id, self.step.id, units=units,
            onhand={key: lots}, bom_cache={}, tenant=self.tenant_a,
            is_reman=is_reman, recovered={key: recovered})[0]

    def test_a_reman_job_sees_the_recovered_pool(self):
        """The only rows recovered stock may supply: a reman job, on a line that
        allows recovery. The pool is the fallback when the unit's own part comes out
        scrapped."""
        row = self._row(is_reman=True)
        self.assertTrue(row['from_teardown'])
        self.assertEqual(row['recovered_on_hand'], 1.0)

    def test_a_new_build_never_counts_recovered_stock(self):
        """Recovered stock does not go into new builds (decided 2026-09-24). Counted
        here, the sheet would say "not short" for a part that may not be issued —
        and consumption has no path to issue a Parts row into a new build anyway."""
        row = self._row(is_reman=False, lots=0, recovered=1)
        self.assertEqual(row['on_hand'], 0.0)
        self.assertEqual(row['short'], 1.0)
        self.assertEqual(row['recovered_on_hand'], 0.0)

    def test_a_reman_line_forbidding_harvested_parts_gets_none(self):
        """A line override can forbid harvested parts — a customer contract, say.
        That line is not supplied from teardown, and the pool must not be offered as
        cover for it either: that would send a picker for a part the unit may not
        take."""
        from Tracker.models import BOMLine
        BOMLine.objects.filter(component_type=self.rotable).update(allow_harvested=False)
        row = self._row(is_reman=True, lots=0, recovered=1)
        self.assertFalse(row['from_teardown'])
        self.assertEqual(row['recovered_on_hand'], 0.0)
        self.assertEqual(row['short'], 1.0)

    def test_the_accepted_component_is_what_makes_the_stock(self):
        """Guards the join the counting depends on: recovered stock is a Parts row
        with `harvested_from` set, which is how it is told apart from purchased."""
        from Tracker.models import PartsStatus
        self.assertEqual(self.recovered_part.part_status, PartsStatus.IN_STOCK)
        self.assertEqual(self.recovered_part.harvested_from.core.core_number,
                         'CORE-DONOR')

    def test_purchased_stock_on_a_new_build_is_lots_only(self):
        """Purchased and recovered are kept apart: a new build's on-hand is its lots,
        with the pool reported nowhere on its row."""
        row = self._row(is_reman=False, lots=3, recovered=1, units=3)
        self.assertEqual(row['on_hand'], 3.0)
        self.assertEqual(row['short'], 0.0)
        self.assertEqual(row['recovered_on_hand'], 0.0)

    def test_a_part_reserved_to_a_core_is_not_free_stock(self):
        """`reserved_for_core` means it belongs to a customer's unit. It is on the
        shelf and it is not available."""
        from Tracker.models import Core, Parts, PartsStatus
        owner = create_core(
            tenant=self.tenant_a, core_number='CORE-OWNER', core_type=self.core_type,
            fulfilment_mode='REPAIR_RETURN', status='DISASSEMBLED',
            received_date=date.today(), received_by=self.user_a)
        # Calls the function the pick sheet actually uses. An earlier version of this
        # test re-implemented the filter inline, so it would have passed even if the
        # sheet's own query had dropped the reserved exclusion.
        from Tracker.services.mes.bom import recovered_stock_by_type
        self.assertEqual(recovered_stock_by_type(self.tenant_a).get(self.rotable.id), 1)
        Parts.objects.filter(pk=self.recovered_part.pk).update(reserved_for_core=owner)
        self.assertIsNone(recovered_stock_by_type(self.tenant_a).get(self.rotable.id))


class PendingAcceptanceFilterTests(TenantTestCase):
    """The reman dashboard's "Pending Inventory Acceptance" link filters on
    `component_part__isnull=true`. The filter was not declared, so django-filter
    dropped it silently and the queue listed accepted components too — the same list
    as "Usable"."""

    def setUp(self):
        super().setUp()
        from Tracker.models import HarvestedComponent, PartTypes

        core_type = PartTypes.objects.create(tenant=self.tenant_a, name='Injector')
        comp_type = PartTypes.objects.create(tenant=self.tenant_a, name='Nozzle')
        core = create_core(
            tenant=self.tenant_a, core_number='CORE-PEND-1', core_type=core_type,
            received_date=date.today(), received_by=self.user_a, status='IN_DISASSEMBLY')
        self.pending = HarvestedComponent.objects.create(
            tenant=self.tenant_a, core=core, component_type=comp_type,
            condition_grade='B', disassembled_by=self.user_a)
        self.accepted = HarvestedComponent.objects.create(
            tenant=self.tenant_a, core=core, component_type=comp_type,
            condition_grade='A', disassembled_by=self.user_a)
        self.accepted.accept_to_inventory(user=self.user_a)
        self.grant_tenant_permissions(
            self.user_a, self.tenant_a, ['view_harvestedcomponent', 'full_tenant_access'])
        self.authenticate_as(self.user_a)

    def _ids(self, query):
        resp = self.client.get(f'/api/HarvestedComponents/?{query}')
        self.assertEqual(resp.status_code, 200, resp.content)
        return {row['id'] for row in resp.json()['results']}

    def test_pending_leaves_out_an_accepted_component(self):
        self.assertEqual(self._ids('component_part__isnull=true&is_scrapped=false'),
                         {str(self.pending.id)})

    def test_the_inverse_is_the_accepted_ones(self):
        self.assertEqual(self._ids('component_part__isnull=false'), {str(self.accepted.id)})

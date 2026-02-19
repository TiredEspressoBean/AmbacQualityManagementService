"""
Tests for the Training module.

Tests TrainingType, TrainingRecord, TrainingRequirement models
and the training authorization service.
"""

from datetime import date, timedelta
from django.test import TestCase
from django.utils import timezone

from Tracker.models import (
    Tenant,
    User,
    PartTypes,
    Processes,
    Steps,
    EquipmentType,
    TrainingType,
    TrainingRecord,
    TrainingRequirement,
)
from Tracker.services.training import (
    check_training_authorization,
    get_required_training,
    get_qualified_users_for_step,
)


class TrainingModuleTestCase(TestCase):
    """Base test case with common setup."""

    @classmethod
    def setUpTestData(cls):
        # Create tenant
        cls.tenant = Tenant.objects.create(name="Test Tenant", slug="test-tenant")

        # Create users
        cls.operator = User.objects.create_user(
            username="operator",
            email="operator@test.com",
            password="testpass",
            tenant=cls.tenant
        )
        cls.untrained_user = User.objects.create_user(
            username="untrained",
            email="untrained@test.com",
            password="testpass",
            tenant=cls.tenant
        )

        # Create training types
        cls.cmm_training = TrainingType.objects.create(
            name="CMM Operation",
            description="Coordinate Measuring Machine operation",
            validity_period_days=365,
            tenant=cls.tenant
        )
        cls.safety_training = TrainingType.objects.create(
            name="Safety Training",
            description="General safety training",
            validity_period_days=None,  # Never expires
            tenant=cls.tenant
        )
        cls.soldering_training = TrainingType.objects.create(
            name="IPC-A-610",
            description="Soldering certification",
            validity_period_days=730,
            tenant=cls.tenant
        )

        # Create part type, process, step
        cls.part_type = PartTypes.objects.create(
            name="Test Part",
            tenant=cls.tenant
        )
        cls.process = Processes.objects.create(
            name="Test Process",
            part_type=cls.part_type,
            tenant=cls.tenant
        )
        cls.inspection_step = Steps.objects.create(
            name="Dimensional Inspection",
            part_type=cls.part_type,
            tenant=cls.tenant
        )
        cls.soldering_step = Steps.objects.create(
            name="Soldering",
            part_type=cls.part_type,
            tenant=cls.tenant
        )

        # Create equipment type
        cls.cmm_type = EquipmentType.objects.create(
            name="CMM",
            tenant=cls.tenant
        )


class TrainingRequirementModelTests(TrainingModuleTestCase):
    """Tests for TrainingRequirement model."""

    def test_create_step_requirement(self):
        """Can create a training requirement for a step."""
        req = TrainingRequirement.objects.create(
            training_type=self.cmm_training,
            step=self.inspection_step,
            notes="Per QP-401",
            tenant=self.tenant
        )
        self.assertEqual(req.scope, 'step')
        self.assertEqual(req.target, self.inspection_step)

    def test_create_process_requirement(self):
        """Can create a training requirement for a process."""
        req = TrainingRequirement.objects.create(
            training_type=self.safety_training,
            process=self.process,
            notes="ITAR requirement",
            tenant=self.tenant
        )
        self.assertEqual(req.scope, 'process')
        self.assertEqual(req.target, self.process)

    def test_create_equipment_type_requirement(self):
        """Can create a training requirement for an equipment type."""
        req = TrainingRequirement.objects.create(
            training_type=self.cmm_training,
            equipment_type=self.cmm_type,
            tenant=self.tenant
        )
        self.assertEqual(req.scope, 'equipment_type')
        self.assertEqual(req.target, self.cmm_type)

    def test_must_set_exactly_one_target(self):
        """Validation fails if zero or multiple targets set."""
        from django.core.exceptions import ValidationError

        # Zero targets
        with self.assertRaises(ValidationError):
            TrainingRequirement.objects.create(
                training_type=self.cmm_training,
                tenant=self.tenant
            )

        # Multiple targets
        with self.assertRaises(ValidationError):
            TrainingRequirement.objects.create(
                training_type=self.cmm_training,
                step=self.inspection_step,
                process=self.process,
                tenant=self.tenant
            )

    def test_unique_constraint_prevents_duplicates(self):
        """Cannot create duplicate requirement for same training+target."""
        from django.core.exceptions import ValidationError

        TrainingRequirement.objects.create(
            training_type=self.cmm_training,
            step=self.inspection_step,
            tenant=self.tenant
        )

        with self.assertRaises(ValidationError):
            TrainingRequirement.objects.create(
                training_type=self.cmm_training,
                step=self.inspection_step,
                tenant=self.tenant
            )


class TrainingAuthorizationTests(TrainingModuleTestCase):
    """Tests for training authorization service."""

    def test_no_requirements_means_authorized(self):
        """User is authorized if no training requirements are defined."""
        result = check_training_authorization(
            user=self.untrained_user,
            step=self.inspection_step
        )
        self.assertTrue(result.authorized)
        self.assertEqual(result.missing, [])

    def test_user_with_valid_training_is_authorized(self):
        """User with all required training is authorized."""
        # Create requirement
        TrainingRequirement.objects.create(
            training_type=self.cmm_training,
            step=self.inspection_step,
            tenant=self.tenant
        )

        # Give operator the training
        TrainingRecord.objects.create(
            user=self.operator,
            training_type=self.cmm_training,
            completed_date=date.today(),
            tenant=self.tenant
        )

        result = check_training_authorization(
            user=self.operator,
            step=self.inspection_step
        )
        self.assertTrue(result.authorized)
        self.assertEqual(len(result.verified), 1)
        self.assertEqual(result.verified[0][0], "CMM Operation")

    def test_user_without_training_is_not_authorized(self):
        """User without required training is not authorized."""
        # Create requirement
        TrainingRequirement.objects.create(
            training_type=self.cmm_training,
            step=self.inspection_step,
            tenant=self.tenant
        )

        result = check_training_authorization(
            user=self.untrained_user,
            step=self.inspection_step
        )
        self.assertFalse(result.authorized)
        self.assertEqual(len(result.missing), 1)
        self.assertEqual(result.missing[0][0], "CMM Operation")
        self.assertEqual(result.missing[0][1], "Not completed")

    def test_expired_training_not_authorized(self):
        """User with expired training is not authorized."""
        # Create requirement
        TrainingRequirement.objects.create(
            training_type=self.cmm_training,
            step=self.inspection_step,
            tenant=self.tenant
        )

        # Give operator expired training
        TrainingRecord.objects.create(
            user=self.operator,
            training_type=self.cmm_training,
            completed_date=date.today() - timedelta(days=400),
            expires_date=date.today() - timedelta(days=35),
            tenant=self.tenant
        )

        result = check_training_authorization(
            user=self.operator,
            step=self.inspection_step
        )
        self.assertFalse(result.authorized)
        self.assertIn("Expired", result.missing[0][1])

    def test_aggregates_step_process_equipment_requirements(self):
        """Authorization check aggregates requirements from all levels."""
        # Step-level requirement
        TrainingRequirement.objects.create(
            training_type=self.cmm_training,
            step=self.inspection_step,
            tenant=self.tenant
        )

        # Process-level requirement
        TrainingRequirement.objects.create(
            training_type=self.safety_training,
            process=self.process,
            tenant=self.tenant
        )

        # Equipment-level requirement
        TrainingRequirement.objects.create(
            training_type=self.soldering_training,
            equipment_type=self.cmm_type,
            tenant=self.tenant
        )

        # User has only safety training
        TrainingRecord.objects.create(
            user=self.operator,
            training_type=self.safety_training,
            completed_date=date.today(),
            tenant=self.tenant
        )

        result = check_training_authorization(
            user=self.operator,
            step=self.inspection_step,
            process=self.process,
            equipment_type=self.cmm_type
        )

        self.assertFalse(result.authorized)
        self.assertEqual(len(result.verified), 1)  # Safety training
        self.assertEqual(len(result.missing), 2)  # CMM and soldering


class GetQualifiedUsersTests(TrainingModuleTestCase):
    """Tests for get_qualified_users_for_step."""

    def test_no_requirements_returns_all_users(self):
        """When no requirements, all users are qualified."""
        qualified = get_qualified_users_for_step(
            step=self.inspection_step,
            tenant=self.tenant
        )
        self.assertIn(self.operator, qualified)
        self.assertIn(self.untrained_user, qualified)

    def test_returns_only_qualified_users(self):
        """Only users with required training are returned."""
        # Create requirement
        TrainingRequirement.objects.create(
            training_type=self.cmm_training,
            step=self.inspection_step,
            tenant=self.tenant
        )

        # Give operator the training
        TrainingRecord.objects.create(
            user=self.operator,
            training_type=self.cmm_training,
            completed_date=date.today(),
            tenant=self.tenant
        )

        qualified = get_qualified_users_for_step(
            step=self.inspection_step,
            tenant=self.tenant
        )

        self.assertIn(self.operator, qualified)
        self.assertNotIn(self.untrained_user, qualified)


class TrainingRecordTests(TrainingModuleTestCase):
    """Tests for TrainingRecord model."""

    def test_auto_calculates_expiration(self):
        """Expiration date is auto-calculated from training type validity period."""
        record = TrainingRecord.objects.create(
            user=self.operator,
            training_type=self.cmm_training,  # 365 days validity
            completed_date=date.today(),
            tenant=self.tenant
        )
        expected_expiration = date.today() + timedelta(days=365)
        self.assertEqual(record.expires_date, expected_expiration)

    def test_no_expiration_for_perpetual_training(self):
        """Training with no validity period has no expiration."""
        record = TrainingRecord.objects.create(
            user=self.operator,
            training_type=self.safety_training,  # No validity period
            completed_date=date.today(),
            tenant=self.tenant
        )
        self.assertIsNone(record.expires_date)

    def test_is_current_property(self):
        """is_current returns True for valid training, False for expired."""
        # Current training
        current_record = TrainingRecord.objects.create(
            user=self.operator,
            training_type=self.cmm_training,
            completed_date=date.today(),
            tenant=self.tenant
        )
        self.assertTrue(current_record.is_current)

        # Expired training
        expired_record = TrainingRecord.objects.create(
            user=self.untrained_user,
            training_type=self.cmm_training,
            completed_date=date.today() - timedelta(days=400),
            expires_date=date.today() - timedelta(days=35),
            tenant=self.tenant
        )
        self.assertFalse(expired_record.is_current)

    def test_status_property(self):
        """status returns 'current', 'expiring_soon', or 'expired'."""
        # Current (expires in 6 months)
        current = TrainingRecord.objects.create(
            user=self.operator,
            training_type=self.soldering_training,
            completed_date=date.today(),
            expires_date=date.today() + timedelta(days=180),
            tenant=self.tenant
        )
        self.assertEqual(current.status, 'current')

        # Expiring soon (expires in 15 days)
        expiring = TrainingRecord(
            user=self.operator,
            training_type=self.cmm_training,
            completed_date=date.today() - timedelta(days=350),
            expires_date=date.today() + timedelta(days=15),
            tenant=self.tenant
        )
        self.assertEqual(expiring.status, 'expiring_soon')

        # Expired
        expired = TrainingRecord(
            user=self.operator,
            training_type=self.cmm_training,
            completed_date=date.today() - timedelta(days=400),
            expires_date=date.today() - timedelta(days=35),
            tenant=self.tenant
        )
        self.assertEqual(expired.status, 'expired')

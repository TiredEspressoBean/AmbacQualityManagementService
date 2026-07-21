"""
Tests for the Training module.

Tests TrainingType, TrainingRecord, TrainingRequirement models
and the training authorization service.
"""

from datetime import date, timedelta
from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone

from Tracker.models import (
    Tenant,
    User,
    PartTypes,
    Processes,
    Steps,
    EquipmentType,
    CompetencyLevel,
    JobRole,
    TrainingType,
    TrainingRecord,
    TrainingRequirement,
)
from Tracker.services.training import (
    check_training_authorization,
    get_required_training,
    get_qualified_users_for_step,
    build_training_matrix,
    get_role_requirements,
    notify_expiring_training,
)
from Tracker.tests.base import TenantContextMixin


class TrainingModuleTestCase(TenantContextMixin, TestCase):
    """Base test case with common setup."""

    @classmethod
    def setUpTestData(cls):
        # Create tenant
        cls.tenant = Tenant.objects.create(name="Test Tenant", slug="test-tenant")
        cls.set_tenant_context_class(cls.tenant)

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
        self.assertIn("Not completed", result.missing[0][1])

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

    def test_below_required_level_not_authorized(self):
        """Holding the training but below the required level is not authorized."""
        TrainingRequirement.objects.create(
            training_type=self.cmm_training,
            step=self.inspection_step,
            min_level=CompetencyLevel.EXPERT,
            tenant=self.tenant,
        )
        TrainingRecord.objects.create(
            user=self.operator,
            training_type=self.cmm_training,
            completed_date=date.today(),
            level=CompetencyLevel.QUALIFIED,
            tenant=self.tenant,
        )
        result = check_training_authorization(user=self.operator, step=self.inspection_step)
        self.assertFalse(result.authorized)
        self.assertEqual(len(result.missing), 1)
        self.assertIn("needs Level 4", result.missing[0][1])

    def test_meets_required_level_authorized(self):
        """A higher held level than required satisfies the requirement."""
        TrainingRequirement.objects.create(
            training_type=self.cmm_training,
            step=self.inspection_step,
            min_level=CompetencyLevel.ASSISTED,
            tenant=self.tenant,
        )
        TrainingRecord.objects.create(
            user=self.operator,
            training_type=self.cmm_training,
            completed_date=date.today(),
            level=CompetencyLevel.QUALIFIED,
            tenant=self.tenant,
        )
        result = check_training_authorization(user=self.operator, step=self.inspection_step)
        self.assertTrue(result.authorized)

    def test_max_level_across_multiple_records(self):
        """Current competency = max level among a user's in-date records for a type."""
        TrainingRequirement.objects.create(
            training_type=self.cmm_training,
            step=self.inspection_step,
            min_level=CompetencyLevel.QUALIFIED,
            tenant=self.tenant,
        )
        TrainingRecord.objects.create(
            user=self.operator, training_type=self.cmm_training,
            completed_date=date.today() - timedelta(days=100),
            level=CompetencyLevel.TRAINEE, tenant=self.tenant,
        )
        TrainingRecord.objects.create(
            user=self.operator, training_type=self.cmm_training,
            completed_date=date.today(),
            level=CompetencyLevel.QUALIFIED, tenant=self.tenant,
        )
        result = check_training_authorization(user=self.operator, step=self.inspection_step)
        self.assertTrue(result.authorized)

    def test_strictest_min_level_wins_across_sources(self):
        """When a type is required by two sources, the highest min_level applies."""
        TrainingRequirement.objects.create(
            training_type=self.cmm_training, step=self.inspection_step,
            min_level=CompetencyLevel.ASSISTED, tenant=self.tenant,
        )
        TrainingRequirement.objects.create(
            training_type=self.cmm_training, equipment_type=self.cmm_type,
            min_level=CompetencyLevel.EXPERT, tenant=self.tenant,
        )
        TrainingRecord.objects.create(
            user=self.operator, training_type=self.cmm_training,
            completed_date=date.today(), level=CompetencyLevel.QUALIFIED, tenant=self.tenant,
        )
        result = check_training_authorization(
            user=self.operator, step=self.inspection_step, equipment_type=self.cmm_type,
        )
        self.assertFalse(result.authorized)
        self.assertEqual(len(result.missing), 1)
        self.assertIn("needs Level 4", result.missing[0][1])

    def test_default_level_preserves_legacy_authorization(self):
        """A record/requirement with default levels (Qualified) stays authorized —
        the backfill guarantee for pre-level data."""
        TrainingRequirement.objects.create(
            training_type=self.cmm_training, step=self.inspection_step, tenant=self.tenant,
        )
        TrainingRecord.objects.create(
            user=self.operator, training_type=self.cmm_training,
            completed_date=date.today(), tenant=self.tenant,
        )
        result = check_training_authorization(user=self.operator, step=self.inspection_step)
        self.assertTrue(result.authorized)

    def test_get_required_training_returns_min_levels(self):
        """get_required_training returns {training_type: min_level}."""
        TrainingRequirement.objects.create(
            training_type=self.cmm_training, step=self.inspection_step,
            min_level=CompetencyLevel.EXPERT, tenant=self.tenant,
        )
        required = get_required_training(self.inspection_step)
        self.assertEqual(required, {self.cmm_training: CompetencyLevel.EXPERT})


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

    def test_qualified_respects_min_level(self):
        """Only users at/above the requirement's min_level are returned."""
        TrainingRequirement.objects.create(
            training_type=self.cmm_training,
            step=self.inspection_step,
            min_level=CompetencyLevel.EXPERT,
            tenant=self.tenant,
        )
        # operator holds it but only at Qualified (below Expert)
        TrainingRecord.objects.create(
            user=self.operator, training_type=self.cmm_training,
            completed_date=date.today(), level=CompetencyLevel.QUALIFIED, tenant=self.tenant,
        )
        # untrained_user holds it at Expert
        TrainingRecord.objects.create(
            user=self.untrained_user, training_type=self.cmm_training,
            completed_date=date.today(), level=CompetencyLevel.EXPERT, tenant=self.tenant,
        )
        qualified = get_qualified_users_for_step(step=self.inspection_step, tenant=self.tenant)
        self.assertIn(self.untrained_user, qualified)
        self.assertNotIn(self.operator, qualified)


class TrainingMatrixServiceTests(TrainingModuleTestCase):
    """Tests for build_training_matrix (the CompetenceMatrix aggregate)."""

    def test_matrix_cells_and_coverage(self):
        TrainingRecord.objects.create(
            user=self.operator, training_type=self.cmm_training,
            completed_date=date.today(), level=CompetencyLevel.QUALIFIED, tenant=self.tenant,
        )
        TrainingRecord.objects.create(
            user=self.operator, training_type=self.soldering_training,
            completed_date=date.today(), level=CompetencyLevel.TRAINEE, tenant=self.tenant,
        )
        matrix = build_training_matrix(tenant=self.tenant)

        # Columns include the training types
        names = {c['name'] for c in matrix['training_types']}
        self.assertIn("CMM Operation", names)
        self.assertIn("IPC-A-610", names)

        # Operator row carries the right cell levels
        op = next(o for o in matrix['operators'] if o['id'] == self.operator.id)
        levels = {c['training_type']: c['level'] for c in op['cells']}
        self.assertEqual(levels[str(self.cmm_training.id)], CompetencyLevel.QUALIFIED)
        self.assertEqual(levels[str(self.soldering_training.id)], CompetencyLevel.TRAINEE)

        # Coverage: CMM has one qualified (L3), soldering has none (only L1)
        cov = {c['training_type']: c for c in matrix['coverage']}
        self.assertEqual(cov[str(self.cmm_training.id)]['qualified_count'], 1)
        self.assertEqual(cov[str(self.soldering_training.id)]['qualified_count'], 0)

    def test_expired_record_shows_zero_level_cell(self):
        TrainingRecord.objects.create(
            user=self.operator, training_type=self.cmm_training,
            completed_date=date.today() - timedelta(days=400),
            expires_date=date.today() - timedelta(days=35),
            level=CompetencyLevel.EXPERT, tenant=self.tenant,
        )
        matrix = build_training_matrix(tenant=self.tenant)
        op = next(o for o in matrix['operators'] if o['id'] == self.operator.id)
        cell = next(c for c in op['cells'] if c['training_type'] == str(self.cmm_training.id))
        self.assertEqual(cell['level'], 0)
        self.assertEqual(cell['status'], 'EXPIRED')

    def test_matrix_is_tenant_scoped(self):
        """Users from another tenant must never appear — explicitly or via the
        ContextVar-derived (no-arg) path the endpoint uses."""
        from Tracker.models import Tenant, User
        from Tracker.utils.tenant_context import tenant_context

        other = Tenant.objects.create(name="Other Tenant", slug="other-tenant")
        ghost = User.objects.create_user(
            username="ghost", email="ghost@other.com", password="x", tenant=other,
        )

        # Explicit tenant arg
        ids = {o['id'] for o in build_training_matrix(tenant=self.tenant)['operators']}
        self.assertIn(self.operator.id, ids)
        self.assertNotIn(ghost.id, ids)

        # No-arg path (endpoint) — must self-scope from the request ContextVar
        with tenant_context(str(self.tenant.id)):
            ids2 = {o['id'] for o in build_training_matrix()['operators']}
        self.assertIn(self.operator.id, ids2)
        self.assertNotIn(ghost.id, ids2)


class RoleRequirementTests(TrainingModuleTestCase):
    """Tests for JobRole-scoped requirements + role gaps in the matrix."""

    def test_job_role_requirement_target(self):
        role = JobRole.objects.create(name="CMM Inspector", tenant=self.tenant)
        req = TrainingRequirement.objects.create(
            training_type=self.cmm_training, job_role=role,
            min_level=CompetencyLevel.EXPERT, tenant=self.tenant,
        )
        self.assertEqual(req.scope, 'job_role')
        self.assertEqual(req.target, role)

    def test_get_role_requirements(self):
        role = JobRole.objects.create(name="Machinist", tenant=self.tenant)
        TrainingRequirement.objects.create(
            training_type=self.cmm_training, job_role=role,
            min_level=CompetencyLevel.QUALIFIED, tenant=self.tenant,
        )
        self.assertEqual(get_role_requirements(role), {self.cmm_training: CompetencyLevel.QUALIFIED})

    def test_matrix_role_gaps(self):
        from Tracker.models import User
        role = JobRole.objects.create(name="CMM Inspector", tenant=self.tenant)
        TrainingRequirement.objects.create(
            training_type=self.cmm_training, job_role=role,
            min_level=CompetencyLevel.EXPERT, tenant=self.tenant,
        )
        TrainingRequirement.objects.create(
            training_type=self.soldering_training, job_role=role,
            min_level=CompetencyLevel.QUALIFIED, tenant=self.tenant,
        )
        # Assign the role without mutating the shared class-level instance.
        op_user = User.objects.get(pk=self.operator.pk)
        op_user.job_role = role
        op_user.save(update_fields=['job_role'])
        # Holds CMM at L3 (below required L4); nothing on soldering (missing).
        TrainingRecord.objects.create(
            user=op_user, training_type=self.cmm_training,
            completed_date=date.today(), level=CompetencyLevel.QUALIFIED, tenant=self.tenant,
        )

        matrix = build_training_matrix(tenant=self.tenant)
        op = next(o for o in matrix['operators'] if o['id'] == op_user.id)
        self.assertEqual(op['job_role_name'], "CMM Inspector")
        self.assertEqual(op['required_count'], 2)
        self.assertEqual(op['gap_count'], 2)

        cells = {c['training_type']: c for c in op['cells']}
        cmm_cell = cells[str(self.cmm_training.id)]
        self.assertEqual(cmm_cell['required_level'], CompetencyLevel.EXPERT)
        self.assertTrue(cmm_cell['gap'])
        # A required-but-untrained type still surfaces as a level-0 gap cell.
        sol_cell = cells[str(self.soldering_training.id)]
        self.assertEqual(sol_cell['level'], 0)
        self.assertTrue(sol_cell['gap'])

        self.assertIn("CMM Inspector", {r['name'] for r in matrix['job_roles']})


class TrainingExpiryNotificationTests(TrainingModuleTestCase):
    """notify_expiring_training decision logic (emit helpers patched out)."""

    def _record(self, days_from_today, training_type=None):
        return TrainingRecord.objects.create(
            user=self.operator,
            training_type=training_type or self.cmm_training,
            completed_date=date.today() - timedelta(days=400),
            expires_date=date.today() + timedelta(days=days_from_today),
            level=CompetencyLevel.QUALIFIED,
            tenant=self.tenant,
        )

    def test_within_30_day_window_emits_expiring_soon(self):
        rec = self._record(20)
        with patch('Tracker.services.training._emit_training_expiring_soon') as soon, \
             patch('Tracker.services.training._emit_training_expired') as expd:
            self.assertTrue(notify_expiring_training(rec))
            soon.assert_called_once()
            self.assertEqual(soon.call_args.kwargs['window'], 30)
            expd.assert_not_called()

    def test_within_60_day_window_emits_window_60(self):
        rec = self._record(50)
        with patch('Tracker.services.training._emit_training_expiring_soon') as soon:
            self.assertTrue(notify_expiring_training(rec))
            self.assertEqual(soon.call_args.kwargs['window'], 60)

    def test_outside_window_no_emit(self):
        rec = self._record(90)
        with patch('Tracker.services.training._emit_training_expiring_soon') as soon:
            self.assertFalse(notify_expiring_training(rec))
            soon.assert_not_called()

    def test_no_expiry_no_emit(self):
        # safety_training has no validity period → record never expires
        rec = TrainingRecord.objects.create(
            user=self.operator, training_type=self.safety_training,
            completed_date=date.today(), tenant=self.tenant,
        )
        with patch('Tracker.services.training._emit_training_expiring_soon') as soon:
            self.assertFalse(notify_expiring_training(rec))
            soon.assert_not_called()

    def test_expired_emits_expired(self):
        rec = self._record(-3)
        with patch('Tracker.services.training._emit_training_expired') as expd:
            self.assertTrue(notify_expiring_training(rec))
            expd.assert_called_once()

    def test_superseded_by_renewal_no_emit(self):
        old = self._record(20)     # expiring soon
        self._record(400)          # renewal with a later expiry supersedes it
        with patch('Tracker.services.training._emit_training_expiring_soon') as soon:
            self.assertFalse(notify_expiring_training(old))
            soon.assert_not_called()


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
        """status returns 'CURRENT', 'EXPIRING_SOON', or 'EXPIRED'."""
        # Current (expires in 6 months)
        current = TrainingRecord.objects.create(
            user=self.operator,
            training_type=self.soldering_training,
            completed_date=date.today(),
            expires_date=date.today() + timedelta(days=180),
            tenant=self.tenant
        )
        self.assertEqual(current.status, 'CURRENT')

        # Expiring soon (expires in 15 days)
        expiring = TrainingRecord(
            user=self.operator,
            training_type=self.cmm_training,
            completed_date=date.today() - timedelta(days=350),
            expires_date=date.today() + timedelta(days=15),
            tenant=self.tenant
        )
        self.assertEqual(expiring.status, 'EXPIRING_SOON')

        # Expired
        expired = TrainingRecord(
            user=self.operator,
            training_type=self.cmm_training,
            completed_date=date.today() - timedelta(days=400),
            expires_date=date.today() - timedelta(days=35),
            tenant=self.tenant
        )
        self.assertEqual(expired.status, 'EXPIRED')

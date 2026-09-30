"""Follow-up fixes (2026-09-29, batch b).

1. Tenant/customer notification rule + schedule viewsets are gated by model perms
   (was: any tenant member could create, edit or delete tenant-wide notification
   config). Personal rules/schedules and the feed stay self-service.
2. TrainingRequirement validation and the TrainingRecord expiry default moved out of
   the models' save() into `services.training`, which every write path calls.
3. `get_or_create_shelf_life_definition` revives an archived Shelf Life definition
   instead of handing back a deleted one.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase

from Tracker.tests.base import TenantContextMixin, TenantTestCase


# =============================================================================
# 1. Notification rule / schedule permissions
# =============================================================================

GATED_VIEWSETS = ('TenantRuleViewSet', 'CustomerRuleViewSet',
                  'TenantScheduleViewSet', 'CustomerScheduleViewSet')
SELF_SERVICE_VIEWSETS = ('PersonalRuleViewSet', 'PersonalScheduleViewSet',
                         'NotificationFeedViewSet')
MANAGE_PERMS = ['add_notificationrule', 'change_notificationrule', 'delete_notificationrule',
                'add_notificationschedule', 'change_notificationschedule',
                'delete_notificationschedule']


class NotificationConfigPresetTests(SimpleTestCase):
    def test_admin_scope_viewsets_apply_model_permissions(self):
        from Tracker.permissions import TenantModelPermissions
        from Tracker.viewsets import notifications
        for name in GATED_VIEWSETS:
            self.assertIn(TenantModelPermissions,
                          getattr(notifications, name).permission_classes, name)

    def test_self_service_viewsets_stay_ungated(self):
        """A user manages their own personal rules/schedules and reads their own
        feed without holding the tenant-config perms."""
        from Tracker.permissions import TenantModelPermissions
        from Tracker.viewsets import notifications
        for name in SELF_SERVICE_VIEWSETS:
            self.assertNotIn(TenantModelPermissions,
                             getattr(notifications, name).permission_classes, name)

    def test_notification_managers_hold_every_manage_perm(self):
        from Tracker.presets import GROUP_PRESETS
        for role in ('tenant_admin', 'qa_manager', 'production_manager'):
            perms = set(GROUP_PRESETS[role]['permissions'])
            for p in MANAGE_PERMS:
                self.assertIn(p, perms, f"{role} must hold {p}")

    def test_line_roles_can_view_but_not_manage(self):
        from Tracker.presets import GROUP_PRESETS
        for role in ('operator', 'qa_inspector'):
            perms = set(GROUP_PRESETS[role]['permissions'])
            self.assertIn('view_notificationrule', perms, role)
            self.assertIn('view_notificationschedule', perms, role)
            for p in MANAGE_PERMS:
                self.assertNotIn(p, perms, f"{role} must not hold {p}")


class TenantRuleApiPermissionTests(TenantTestCase):
    URL = '/api/notifications/rules/tenant/'

    def _post(self):
        return self.client.post(self.URL, {
            'name': 'CAPA assigned', 'event_code': 'capa.assigned',
            'channels': ['in_app'], 'recipient_strategy': 'static',
        }, format='json')

    def _grant_preset(self, role):
        from Tracker.presets import GROUP_PRESETS
        self.grant_tenant_permissions(self.user_a, self.tenant_a,
                                      list(GROUP_PRESETS[role]['permissions']))
        self.authenticate_as(self.user_a, self.tenant_a)

    def test_a_line_role_cannot_create_a_tenant_rule(self):
        from Tracker.models import NotificationRule
        self._grant_preset('operator')
        r = self._post()
        self.assertEqual(r.status_code, 403, r.content[:500])
        self.assertFalse(NotificationRule.objects.filter(name='CAPA assigned').exists())

    def test_a_line_role_can_still_list_tenant_rules(self):
        self._grant_preset('operator')
        r = self.client.get(self.URL)
        self.assertEqual(r.status_code, 200, r.content[:500])

    def test_a_notification_manager_can_create_a_tenant_rule(self):
        from Tracker.models import NotificationRule
        self._grant_preset('production_manager')
        r = self._post()
        self.assertEqual(r.status_code, 201, r.content[:500])
        self.assertTrue(NotificationRule.objects.filter(
            name='CAPA assigned', scope_kind='tenant').exists())


# =============================================================================
# 2. Training writes go through services.training
# =============================================================================

class _TrainingFixture(TenantContextMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        from Tracker.models import PartTypes, Processes, Steps, Tenant, TrainingType
        cls.tenant = Tenant.objects.create(name="Train B", slug="train-0929b")
        cls.set_tenant_context_class(cls.tenant)
        cls.user = get_user_model().objects.create_user(
            username="trainee-0929b", email="t@0929b.test", password="x", tenant=cls.tenant)
        cls.cmm = TrainingType.objects.create(
            tenant=cls.tenant, name="CMM 0929b", validity_period_days=365)
        cls.safety = TrainingType.objects.create(
            tenant=cls.tenant, name="Safety 0929b", validity_period_days=None)
        cls.pt = PartTypes.objects.create(tenant=cls.tenant, name="PT 0929b")
        cls.process = Processes.objects.create(tenant=cls.tenant, name="P 0929b", part_type=cls.pt)
        cls.step = Steps.objects.create(tenant=cls.tenant, part_type=cls.pt,
                                        name="Inspect 0929b", step_type="TASK")

    def setUp(self):
        super().setUp()
        self.set_tenant_context(self.tenant)


class TrainingRequirementServiceTests(_TrainingFixture):
    def test_model_save_no_longer_validates(self):
        """The rule moved: save() only saves. (A zero-target row saves at the ORM
        level; every write path calls the service, which refuses it.)"""
        from Tracker.models import TrainingRequirement
        req = TrainingRequirement(tenant=self.tenant, training_type=self.cmm)
        req.save()
        self.assertIsNotNone(req.pk)

    def test_service_refuses_zero_targets(self):
        from Tracker.services.training import create_training_requirement
        with self.assertRaises(ValidationError) as cm:
            create_training_requirement(tenant=self.tenant, training_type=self.cmm)
        self.assertIn("Exactly one of step", str(cm.exception))

    def test_service_refuses_two_targets(self):
        from Tracker.services.training import create_training_requirement
        with self.assertRaises(ValidationError):
            create_training_requirement(tenant=self.tenant, training_type=self.cmm,
                                        step=self.step, process=self.process)

    def test_service_refuses_a_duplicate(self):
        from Tracker.services.training import create_training_requirement
        create_training_requirement(tenant=self.tenant, training_type=self.cmm, step=self.step)
        with self.assertRaises(ValidationError):
            create_training_requirement(tenant=self.tenant, training_type=self.cmm,
                                        step=self.step)

    def test_update_validates(self):
        from Tracker.services.training import (
            create_training_requirement, update_training_requirement,
        )
        req = create_training_requirement(tenant=self.tenant, training_type=self.cmm,
                                          step=self.step)
        with self.assertRaises(ValidationError):
            update_training_requirement(req, process=self.process)

    def test_upsert_creates_then_updates(self):
        from Tracker.services.training import upsert_training_requirement
        req, created = upsert_training_requirement(
            tenant=self.tenant, training_type=self.cmm, step=self.step,
            defaults={'min_level': 1})
        self.assertTrue(created)
        again, created = upsert_training_requirement(
            tenant=self.tenant, training_type=self.cmm, step=self.step,
            defaults={'min_level': 2})
        self.assertFalse(created)
        self.assertEqual(again.pk, req.pk)
        self.assertEqual(again.min_level, 2)

    def test_step_versioning_copies_min_level(self):
        """The copy used to drop min_level, so a Trainee-level requirement came back
        on the new step version at the model default (Qualified)."""
        from Tracker.models import TrainingRequirement
        from Tracker.services.mes.steps import create_new_step_version
        from Tracker.services.training import create_training_requirement
        create_training_requirement(tenant=self.tenant, training_type=self.cmm,
                                    step=self.step, min_level=1, notes='WI-1')
        v2 = create_new_step_version(self.step, user=self.user, change_description='Rev')
        copied = TrainingRequirement.objects.get(step=v2, archived=False)
        self.assertEqual(copied.min_level, 1)
        self.assertEqual(copied.notes, 'WI-1')


class TrainingRecordServiceTests(_TrainingFixture):
    def test_model_save_no_longer_derives_expiry(self):
        from Tracker.models import TrainingRecord
        rec = TrainingRecord.objects.create(tenant=self.tenant, user=self.user,
                                            training_type=self.cmm, completed_date=date.today())
        self.assertIsNone(rec.expires_date)

    def test_service_defaults_expiry_from_the_training_type(self):
        from Tracker.services.training import create_training_record
        done = date.today() - timedelta(days=10)
        rec = create_training_record(tenant=self.tenant, user=self.user,
                                     training_type=self.cmm, completed_date=done)
        self.assertEqual(rec.expires_date, done + timedelta(days=365))

    def test_service_keeps_an_explicit_expiry(self):
        from Tracker.services.training import create_training_record
        explicit = date.today() + timedelta(days=5)
        rec = create_training_record(tenant=self.tenant, user=self.user,
                                     training_type=self.cmm, completed_date=date.today(),
                                     expires_date=explicit)
        self.assertEqual(rec.expires_date, explicit)

    def test_service_leaves_a_perpetual_type_unexpiring(self):
        from Tracker.services.training import create_training_record
        rec = create_training_record(tenant=self.tenant, user=self.user,
                                     training_type=self.safety, completed_date=date.today())
        self.assertIsNone(rec.expires_date)

    def test_update_refills_a_cleared_expiry(self):
        """Same as the old save(): any write with no expiry gets the default."""
        from Tracker.services.training import create_training_record, update_training_record
        rec = create_training_record(tenant=self.tenant, user=self.user,
                                     training_type=self.cmm, completed_date=date.today())
        rec = update_training_record(rec, expires_date=None)
        self.assertEqual(rec.expires_date, date.today() + timedelta(days=365))


class TrainingApiWritePathTests(TenantTestCase):
    """The serializers route writes through the service."""

    def setUp(self):
        super().setUp()
        from Tracker.models import PartTypes, Steps, TrainingType
        self.cmm = TrainingType.objects.create(tenant=self.tenant_a, name="CMM api",
                                               validity_period_days=365)
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="PT api")
        self.step = Steps.objects.create(tenant=self.tenant_a, part_type=pt,
                                         name="Op api", step_type="TASK")
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            'view_trainingrecord', 'add_trainingrecord', 'change_trainingrecord',
            'view_trainingrequirement', 'add_trainingrequirement',
            'change_trainingrequirement', 'view_trainingtype', 'view_steps',
            'view_user',
        ])
        self.authenticate_as(self.user_a, self.tenant_a)

    def test_record_created_via_api_gets_the_default_expiry(self):
        from Tracker.models import TrainingRecord
        r = self.client.post('/api/TrainingRecords/', {
            'user': self.user_a.pk, 'training_type': str(self.cmm.pk),
            'completed_date': date.today().isoformat(),
        }, format='json')
        self.assertEqual(r.status_code, 201, r.content[:500])
        rec = TrainingRecord.objects.get(pk=r.data['id'])
        self.assertEqual(rec.expires_date, date.today() + timedelta(days=365))

    def test_requirement_with_no_target_is_a_400(self):
        from Tracker.models import TrainingRequirement
        r = self.client.post('/api/TrainingRequirements/', {
            'training_type': str(self.cmm.pk),
        }, format='json')
        self.assertEqual(r.status_code, 400, r.content[:500])
        self.assertFalse(TrainingRequirement.objects.filter(training_type=self.cmm).exists())

    def test_duplicate_requirement_is_a_400(self):
        body = {'training_type': str(self.cmm.pk), 'step': str(self.step.pk)}
        first = self.client.post('/api/TrainingRequirements/', body, format='json')
        self.assertEqual(first.status_code, 201, first.content[:500])
        again = self.client.post('/api/TrainingRequirements/', body, format='json')
        self.assertEqual(again.status_code, 400, again.content[:500])


# =============================================================================
# 3. Shelf Life definition revival
# =============================================================================

class ShelfLifeDefinitionReviveTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        from Tracker.models import Tenant
        self.tenant = Tenant.objects.create(name="Shelf B", slug="shelf-0929b", tier="PRO")
        self.set_tenant_context(self.tenant)

    def test_creates_on_first_use(self):
        from Tracker.services.life_tracking.shelf_life import get_or_create_shelf_life_definition
        d = get_or_create_shelf_life_definition(self.tenant)
        self.assertFalse(d.archived)
        self.assertEqual(d.hard_limit, Decimal("365"))

    def test_returns_the_live_definition(self):
        from Tracker.services.life_tracking.shelf_life import get_or_create_shelf_life_definition
        first = get_or_create_shelf_life_definition(self.tenant)
        self.assertEqual(get_or_create_shelf_life_definition(self.tenant).pk, first.pk)

    def test_revives_an_archived_definition(self):
        """A deleted Shelf Life definition was handed back still archived, so the
        lot was tracked against a deleted definition. Now it is un-archived in place
        (same row: the name is unique among current versions, so a new one can't be
        created alongside it)."""
        from Tracker.models.life_tracking import LifeLimitDefinition
        from Tracker.services.life_tracking.shelf_life import get_or_create_shelf_life_definition
        original = get_or_create_shelf_life_definition(self.tenant)
        original.delete()  # soft delete
        original.refresh_from_db()
        self.assertTrue(original.archived)

        again = get_or_create_shelf_life_definition(self.tenant)
        self.assertEqual(again.pk, original.pk)
        again.refresh_from_db()
        self.assertFalse(again.archived)
        self.assertIsNone(again.deleted_at)
        self.assertEqual(
            LifeLimitDefinition.objects.filter(name="Shelf Life", is_current_version=True).count(),
            1)

"""The permission sync at migrate keeps admins' additions (user ruling 2026-11-17):
a preset group gains its preset's missing permissions and loses only what its preset
granted once and no longer does (presets.RETIRED_PRESET_PERMISSIONS)."""
from unittest import mock

from django.contrib.auth.models import Permission

from Tracker.groups import GroupSeeder
from Tracker.models import TenantGroup
from Tracker.presets import GROUP_PRESETS
from Tracker.tests.base import TenantTestCase

OPERATOR = next(p for p in GROUP_PRESETS.values() if p['name'] == 'Operator')


class PermissionSyncTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.group, _ = TenantGroup.objects.get_or_create(
            tenant=self.tenant_a, name='Operator', defaults={'is_custom': False})
        GroupSeeder.sync_permissions()

    def _has(self, codename):
        return self.group.permissions.filter(codename=codename).exists()

    def test_an_admins_addition_survives(self):
        self.assertNotIn('release_workorder', OPERATOR['permissions'])
        self.group.permissions.add(Permission.objects.get(codename='release_workorder'))
        GroupSeeder.sync_permissions()
        self.assertTrue(self._has('release_workorder'))

    def test_a_missing_preset_permission_is_added(self):
        codename = next(c for c in OPERATOR['permissions'] if Permission.objects.filter(
            codename=c).exists())
        self.group.permissions.remove(*Permission.objects.filter(codename=codename))
        GroupSeeder.sync_permissions()
        self.assertTrue(self._has(codename))

    def test_a_permission_retired_from_the_preset_is_revoked(self):
        self.group.permissions.add(Permission.objects.get(codename='release_workorder'))
        with mock.patch.dict('Tracker.presets.RETIRED_PRESET_PERMISSIONS',
                             {'Operator': ['release_workorder']}):
            result = GroupSeeder.sync_permissions()
        self.assertFalse(self._has('release_workorder'))
        self.assertGreaterEqual(result['permissions_removed'], 1)

    def test_a_retired_permission_the_preset_grants_again_stays(self):
        codename = next(c for c in OPERATOR['permissions'] if Permission.objects.filter(
            codename=c).exists())
        with mock.patch.dict('Tracker.presets.RETIRED_PRESET_PERMISSIONS',
                             {'Operator': [codename]}):
            GroupSeeder.sync_permissions()
        self.assertTrue(self._has(codename))

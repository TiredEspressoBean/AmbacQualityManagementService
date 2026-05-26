"""Resolver tests — 4-layer channel precedence for a user × event.

Layers (most specific first):
    1. UserNotificationPreference
    2. TenantNotificationDefault role-scoped (multi-role union)
    3. TenantNotificationDefault tenant-wide
    4. EVENT_REGISTRY default_channels
"""
from __future__ import annotations

from django.core.cache import cache
from django.test import TestCase

from Tracker.models import Tenant
from Tracker.services.core.notifications.resolver import resolve_default_channels
from Tracker.tests.base import TenantContextMixin
from Tracker.tests.notifications.factories import (
    make_tenant_group,
    make_user_in_groups,
    set_tenant_default,
    set_user_preference,
)


class ResolverPrecedenceTests(TenantContextMixin, TestCase):
    """Pin the 4-layer precedence for `ncr.opened` (registry: in_app+email, default_on=True)."""

    def setUp(self):
        super().setUp()
        cache.clear()
        self.tenant = Tenant.objects.create(name='Resolver Tenant', slug='resolver-tenant')
        self.set_tenant_context(self.tenant)
        self.qa_group = make_tenant_group(self.tenant, 'QA Inspector')
        self.user = make_user_in_groups(self.tenant, self.qa_group)

    def test_layer4_registry_default_when_no_db_rows(self):
        """No prefs, no defaults → registry's default_channels rules."""
        resolved = resolve_default_channels(self.user, 'ncr.opened')

        # ncr.opened registers default_channels=['in_app', 'email'].
        self.assertTrue(resolved['in_app'])
        self.assertTrue(resolved['email'])

    def test_layer3_tenant_wide_overrides_registry(self):
        """Tenant-wide row (role=None) wins over registry."""
        set_tenant_default(self.tenant, 'ncr.opened', 'email', enabled=False)

        resolved = resolve_default_channels(self.user, 'ncr.opened')
        self.assertFalse(resolved['email'])
        # in_app untouched — still falls through to registry default.
        self.assertTrue(resolved['in_app'])

    def test_layer2_role_scoped_overrides_tenant_wide(self):
        """Role-scoped row for a group the user belongs to wins over tenant-wide."""
        set_tenant_default(self.tenant, 'ncr.opened', 'email', enabled=False)
        set_tenant_default(self.tenant, 'ncr.opened', 'email', enabled=True, role=self.qa_group)

        resolved = resolve_default_channels(self.user, 'ncr.opened')
        self.assertTrue(resolved['email'])

    def test_layer2_role_scoped_ignored_when_user_not_in_role(self):
        """Role-scoped row for a group the user doesn't belong to is ignored."""
        other_group = make_tenant_group(self.tenant, 'QA Manager')
        set_tenant_default(self.tenant, 'ncr.opened', 'email', enabled=False)
        set_tenant_default(self.tenant, 'ncr.opened', 'email', enabled=True, role=other_group)

        resolved = resolve_default_channels(self.user, 'ncr.opened')
        # User isn't in QA Manager → falls through to tenant-wide row.
        self.assertFalse(resolved['email'])

    def test_layer2_multi_role_union_any_enabled_wins(self):
        """User in two roles → if either role's row is enabled, channel is on."""
        group_b = make_tenant_group(self.tenant, 'Engineer')
        user = make_user_in_groups(self.tenant, self.qa_group, group_b)

        set_tenant_default(self.tenant, 'ncr.opened', 'email', enabled=False, role=self.qa_group)
        set_tenant_default(self.tenant, 'ncr.opened', 'email', enabled=True, role=group_b)

        resolved = resolve_default_channels(user, 'ncr.opened')
        self.assertTrue(resolved['email'], "multi-role union: any-enabled should win")

    def test_layer1_user_preference_overrides_all_lower_layers(self):
        """Explicit user preference wins over role-scoped, tenant-wide, and registry."""
        set_tenant_default(self.tenant, 'ncr.opened', 'email', enabled=True)
        set_tenant_default(self.tenant, 'ncr.opened', 'email', enabled=True, role=self.qa_group)
        set_user_preference(self.user, 'ncr.opened', 'email', enabled=False)

        resolved = resolve_default_channels(self.user, 'ncr.opened')
        self.assertFalse(resolved['email'])

    def test_layer1_user_preference_can_enable_when_lower_disabled(self):
        """Always-write: user can opt INTO a channel even if all defaults are off."""
        set_tenant_default(self.tenant, 'ncr.opened', 'email', enabled=False)
        set_tenant_default(self.tenant, 'ncr.opened', 'email', enabled=False, role=self.qa_group)
        set_user_preference(self.user, 'ncr.opened', 'email', enabled=True)

        resolved = resolve_default_channels(self.user, 'ncr.opened')
        self.assertTrue(resolved['email'])

    def test_cache_returns_same_dict_on_repeat_calls(self):
        """Second call hits cache — mutating DB between calls is invisible until invalidation/TTL."""
        first = resolve_default_channels(self.user, 'ncr.opened')
        # Mutate underlying state — cache should mask it.
        set_tenant_default(self.tenant, 'ncr.opened', 'email', enabled=False)
        second = resolve_default_channels(self.user, 'ncr.opened')

        self.assertEqual(first, second)

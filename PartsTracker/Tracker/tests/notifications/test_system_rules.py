"""System starter-rule seeder tests.

Covers `seed_system_rules_for_tenant`: idempotency of explicit STARTER_RULES
entries, and pass-2 synthesis from `EventType.default_recipient_groups` for
events not covered by an explicit entry.
"""
from __future__ import annotations

from django.test import TestCase

from Tracker.models import NotificationRule, Tenant, TenantGroup
from Tracker.services.core.notifications.registry import EVENT_REGISTRY
from Tracker.services.core.notifications.system_rules import (
    STARTER_RULES,
    seed_system_rules_for_tenant,
)
from Tracker.tests.base import TenantContextMixin, VectorTestCase


class SystemRulesSeederTests(TenantContextMixin, VectorTestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name='Rule Tenant', slug='rule-tenant')
        self.set_tenant_context(self.tenant)
        # Tenant post_save already seeded starter rules; clear so we can
        # observe the seeder from a known-empty baseline.
        NotificationRule.objects.filter(tenant=self.tenant).delete()

    def _ensure_groups_for_events(self, events):
        """Create the TenantGroups each event's default_recipient_groups needs."""
        names = {n for e in events for n in e.default_recipient_groups}
        for name in names:
            TenantGroup.objects.get_or_create(tenant=self.tenant, name=name)

    def test_fallback_synthesizes_rule_for_uncovered_event(self):
        """Events with default_recipient_groups but no STARTER_RULES entry get a synthesized rule."""
        explicit_codes = {spec['event_code'] for spec in STARTER_RULES}
        candidates = [
            e for e in EVENT_REGISTRY.values()
            if e.code not in explicit_codes and e.default_recipient_groups
        ]
        self.assertTrue(candidates, "expected at least one uncovered event with defaults")
        self._ensure_groups_for_events(candidates)

        seed_system_rules_for_tenant(self.tenant)

        for event in candidates:
            rule = NotificationRule.objects.filter(
                tenant=self.tenant, event_code=event.code,
            ).first()
            self.assertIsNotNone(rule, f'no synthesized rule for {event.code}')
            self.assertEqual(rule.recipient_strategy, 'static')
            self.assertEqual(
                set(rule.recipient_groups.values_list('name', flat=True)),
                set(event.default_recipient_groups),
            )
            self.assertEqual(list(rule.channels), list(event.default_channels))

    def test_explicit_starter_rule_wins_over_fallback(self):
        """Events with a STARTER_RULES entry get only the explicit rule — no synthesized dup."""
        self._ensure_groups_for_events(EVENT_REGISTRY.values())
        seed_system_rules_for_tenant(self.tenant)

        for spec in STARTER_RULES:
            rules = NotificationRule.objects.filter(
                tenant=self.tenant, event_code=spec['event_code'],
            )
            # Only the explicit rule; no auto-synthesized "- default recipients" sibling.
            names = set(rules.values_list('name', flat=True))
            self.assertIn(spec['name'], names)
            for name in names:
                self.assertFalse(
                    name.endswith('- default recipients'),
                    f'unexpected fallback rule {name!r} alongside explicit STARTER_RULES entry',
                )

    def test_seeder_is_idempotent_across_both_passes(self):
        """Re-running the seeder creates zero new rules."""
        self._ensure_groups_for_events(EVENT_REGISTRY.values())
        seed_system_rules_for_tenant(self.tenant)
        before = NotificationRule.objects.filter(tenant=self.tenant).count()

        counts = seed_system_rules_for_tenant(self.tenant)
        after = NotificationRule.objects.filter(tenant=self.tenant).count()

        self.assertEqual(before, after)
        self.assertEqual(counts['created'], 0)

    def test_event_with_no_default_recipients_produces_no_fallback(self):
        """Events with empty default_recipient_groups don't get a synthesized rule."""
        explicit_codes = {spec['event_code'] for spec in STARTER_RULES}
        empty_events = [
            e for e in EVENT_REGISTRY.values()
            if e.code not in explicit_codes and not e.default_recipient_groups
        ]
        self._ensure_groups_for_events(EVENT_REGISTRY.values())
        seed_system_rules_for_tenant(self.tenant)

        for event in empty_events:
            self.assertFalse(
                NotificationRule.objects.filter(
                    tenant=self.tenant, event_code=event.code,
                ).exists(),
                f'unexpected rule for {event.code!r} which has no default recipients',
            )

"""
Security-audit regression for the integration framework hardening.

These guard the *template* invariants every future adapter inherits:
- Webhook verification fails CLOSED (BaseAdapter.verify_webhook default-denies;
  any adapter that handles webhooks must implement verification).
- Sync runs inside the integration's tenant_context (framework-owned scoping).
- Cross-tenant contact linking (a feature) can never escalate beyond an
  order-scoped portal role.
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from Tracker.tests.base import TenantTestCase
from integrations.adapters.base import BaseAdapter


class WebhookFailClosedTests(TestCase):
    def test_base_adapter_denies_by_default(self):
        self.assertFalse(BaseAdapter().verify_webhook(MagicMock(), MagicMock()))

    def test_webhook_adapters_must_implement_verification(self):
        """Any registered adapter that handles webhooks must also override
        verify_webhook — otherwise the framework's default-deny would silently
        reject all of its webhooks (and, pre-fix, the old code would have
        accepted them unverified)."""
        from integrations.services.registry import get_all_adapters

        for adapter in get_all_adapters():
            cls = type(adapter)
            handles = cls.handle_webhook is not BaseAdapter.handle_webhook
            verifies = cls.verify_webhook is not BaseAdapter.verify_webhook
            if handles:
                self.assertTrue(
                    verifies,
                    f"{cls.__name__} handles webhooks but does not override "
                    f"verify_webhook (framework would fail closed).",
                )


class SyncTenantContextTests(TenantTestCase):
    def test_sync_task_establishes_tenant_context(self):
        """The framework wraps the sync in tenant_context(integration.tenant_id)
        so adapters get correct `.objects` scoping for free."""
        from integrations.models.config import IntegrationConfig
        from integrations.tasks import sync_hubspot_deals_task
        from Tracker.utils.tenant_context import current_tenant_var

        config = IntegrationConfig.objects.create(
            tenant=self.tenant_b, provider='hubspot', is_enabled=True, api_key='x',
        )

        captured = {}

        def fake_sync(integration):
            captured['tenant'] = current_tenant_var.get()
            return {'status': 'success'}

        with patch('integrations.adapters.hubspot.sync.sync_all_deals', side_effect=fake_sync):
            sync_hubspot_deals_task.apply(kwargs={'integration_id': str(config.id)}).get()

        self.assertEqual(str(captured.get('tenant')), str(self.tenant_b.id))


class ResolveContactEscalationGuardTests(TenantTestCase):
    def _contact(self, email):
        return {'email': email, 'first_name': 'X', 'last_name': 'Y', 'associated_company_id': None}

    def test_role_refused_when_group_has_full_tenant_access(self):
        from django.contrib.auth.models import Permission
        from Tracker.models import TenantGroup, UserRole
        from Tracker.utils.tenant_context import tenant_context
        from integrations.adapters.hubspot.serializers import resolve_contact

        # The Customer group is auto-seeded per tenant; fetch it (unscoped, since
        # the ambient ContextVar is tenant_a) and mis-configure it with
        # full_tenant_access to simulate the escalation case.
        grp, _ = TenantGroup.objects.get_or_create(
            tenant=self.tenant_b, name='Customer', defaults={'is_custom': False},
        )
        grp.permissions.add(Permission.objects.get(codename='full_tenant_access'))

        integration = MagicMock()
        integration.tenant = self.tenant_b
        # Mirror production: resolve_contact runs inside the integration's tenant
        # context (the framework establishes this in the sync task).
        with tenant_context(self.tenant_b.id):
            user = resolve_contact(self._contact('esc@example.com'), {}, integration, self.tenant_b)

        self.assertIsNotNone(user)  # user still resolved
        self.assertFalse(
            UserRole.objects.filter(user=user, group=grp).exists(),
            "must NOT grant a portal role that confers full_tenant_access",
        )

    def test_role_granted_for_scoped_customer_group(self):
        from Tracker.models import UserRole
        from Tracker.utils.tenant_context import tenant_context
        from integrations.adapters.hubspot.serializers import resolve_contact

        integration = MagicMock()
        integration.tenant = self.tenant_a
        with tenant_context(self.tenant_a.id):
            user = resolve_contact(self._contact('ok@example.com'), {}, integration, self.tenant_a)

        self.assertTrue(
            UserRole.objects.filter(
                user=user, group__name='Customer', group__tenant=self.tenant_a,
            ).exists()
        )

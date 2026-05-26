"""CustomerActiveOrdersProvider tests — R2 coverage.

Covers:
  - Provider is registered and `get_provider('customer_active_orders')` returns it
  - Param validation rejects an unknown customer
  - build_content returns None when the customer has no active orders
  - build_content returns RenderedContent with non-empty html/text/subject
    when the customer has at least one qualifying order
  - Greeting personalizes from a User's first_name and from an
    ExternalContact's name field

The provider re-renders Django templates that already exist
(`templates/emails/weekly_customer_update.{html,txt,_subject.txt}`); we
assert structural properties (subject non-empty, html contains order name)
rather than exact template output.
"""
from __future__ import annotations

from django.test import TestCase

from Tracker.models import (
    Companies,
    ExternalContact,
    Orders,
    OrdersStatus,
    Tenant,
)
from Tracker.services.core.notifications.scheduled_content import (
    UnknownProviderError,
    get_all_providers,
    get_provider,
)
from Tracker.services.core.notifications.scheduled_content.customer_active_orders import (
    CustomerActiveOrdersProvider,
)
from Tracker.tests.base import TenantContextMixin
from Tracker.tests.notifications.factories import make_user_in_groups, make_tenant_group


class ProviderRegistryTests(TestCase):
    """The provider is wired into the registry."""

    def test_get_provider_returns_customer_active_orders(self):
        provider = get_provider("customer_active_orders")
        self.assertIsInstance(provider, CustomerActiveOrdersProvider)

    def test_get_provider_unknown_raises(self):
        with self.assertRaises(UnknownProviderError):
            get_provider("no_such_provider")

    def test_get_all_providers_includes_customer_active_orders(self):
        all_providers = get_all_providers()
        self.assertIn("customer_active_orders", all_providers)


class CustomerActiveOrdersProviderTests(TenantContextMixin, TestCase):
    """End-to-end rendering for a tenant with real Orders rows."""

    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name='Prov Tenant', slug='prov-tenant')
        self.set_tenant_context(self.tenant)
        self.customer = Companies.objects.create(name='Acme Aero', description='')
        self.provider = CustomerActiveOrdersProvider()

    def _user_recipient(self):
        return make_user_in_groups(
            self.tenant, make_tenant_group(self.tenant, 'Buyer'),
            first_name='Jane', last_name='Procurement',
        )

    def _external_recipient(self):
        return ExternalContact.objects.create(
            tenant=self.tenant, customer=self.customer,
            name='Jordan Buyer', email='jordan@acme.example',
        )

    def test_validate_params_rejects_unknown_customer(self):
        from rest_framework.exceptions import ValidationError as DRFValidationError
        with self.assertRaises(DRFValidationError):
            self.provider.validate_params(
                {"customer_id": "00000000-0000-0000-0000-000000000000"},
                tenant=self.tenant,
            )

    def test_validate_params_accepts_known_customer(self):
        validated = self.provider.validate_params(
            {"customer_id": str(self.customer.id)},
            tenant=self.tenant,
        )
        self.assertEqual(str(validated["customer_id"]), str(self.customer.id))

    def test_no_active_orders_returns_none(self):
        result = self.provider.build_content(
            validated_params={"customer_id": self.customer.id},
            tenant=self.tenant,
            recipient=self._user_recipient(),
        )
        self.assertIsNone(result)

    def test_active_orders_renders_content(self):
        """Renders subject + html + text when the legacy helper returns rows.

        We patch `_prepare_order_data` rather than build the full Orders +
        Parts + Steps + ProcessSteps graph the helper requires for an order
        to survive its progress filter — that's the helper's contract, not
        this provider's. The provider's contract is "if the helper returned
        rows, render the templates with them."
        """
        Orders.objects.create(
            tenant=self.tenant,
            name='ACM-001',
            company=self.customer,
            order_status=OrdersStatus.PENDING,
        )

        canned_rows = [{
            'name': 'ACM-001',
            'status': 'Pending',
            'progress': 25,
            'current_stage': 'Heat Treat',
            'completion_date': None,
            'original_completion': None,
            'total_parts': 8,
            'completed_parts': 2,
            'gate_info': None,
        }]

        from unittest.mock import patch
        with patch(
            'Tracker.tasks._prepare_order_data',
            return_value=canned_rows,
        ):
            result = self.provider.build_content(
                validated_params={"customer_id": self.customer.id},
                tenant=self.tenant,
                recipient=self._user_recipient(),
            )

        self.assertIsNotNone(result)
        self.assertTrue(result.subject.strip())
        # Both templates render the order's name; html should contain it.
        self.assertIn('ACM-001', result.html)
        self.assertIn('ACM-001', result.text)

    def test_missing_customer_returns_none(self):
        """A scope_customer that was deleted between schedule save and fire."""
        Companies.objects.filter(id=self.customer.id).delete()
        result = self.provider.build_content(
            validated_params={"customer_id": self.customer.id},
            tenant=self.tenant,
            recipient=self._user_recipient(),
        )
        self.assertIsNone(result)


class GreetingPersonalizationTests(TenantContextMixin, TestCase):
    """The greeting namespace adapts to recipient kind."""

    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name='Greet Tenant', slug='greet-tenant')
        self.set_tenant_context(self.tenant)

    def test_user_first_name_used(self):
        from Tracker.services.core.notifications.scheduled_content.customer_active_orders import (
            _greeting_namespace,
        )
        user = make_user_in_groups(
            self.tenant, make_tenant_group(self.tenant, 'Buyer'),
            first_name='Jane', last_name='X',
        )
        ns = _greeting_namespace(user)
        self.assertEqual(ns.first_name, 'Jane')

    def test_external_contact_uses_first_token_of_name(self):
        from Tracker.services.core.notifications.scheduled_content.customer_active_orders import (
            _greeting_namespace,
        )
        customer = Companies.objects.create(name='Foo', description='')
        contact = ExternalContact.objects.create(
            tenant=self.tenant, customer=customer,
            name='Jordan Buyer', email='jordan@example.com',
        )
        ns = _greeting_namespace(contact)
        self.assertEqual(ns.first_name, 'Jordan')

    def test_empty_recipient_yields_empty_string(self):
        from Tracker.services.core.notifications.scheduled_content.customer_active_orders import (
            _greeting_namespace,
        )

        class _Anon:
            pass
        ns = _greeting_namespace(_Anon())
        # Template's default filter handles the empty case; we just confirm
        # the helper doesn't blow up.
        self.assertEqual(ns.first_name, '')

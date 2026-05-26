"""
CustomerActiveOrdersProvider — snapshot of one customer organization's
currently-active orders.

Replaces the legacy weekly customer order update flow
(`Tracker.tasks.send_weekly_order_update_task`). Renders the same HTML and
text templates the legacy path uses (`templates/emails/weekly_customer_update.{html,txt}`)
so customers see no behavioral change after migration.

One semantic improvement over the legacy path: the query is org-scoped
(`Orders.company=scope_customer`) instead of user-scoped (`Orders.customer=user`).
The legacy mechanism subscribed individual customer Users; the new system
subscribes Companies. The schedule's recipient_users / recipient_external
M2Ms decide who gets the rendered email; the content is identical for
every recipient on a given schedule fire.
"""
from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any

from django.template.loader import render_to_string
from django.utils import timezone
from rest_framework import serializers

from .base import RenderedContent, ScheduledContentProvider

logger = logging.getLogger(__name__)


class _CustomerActiveOrdersParams(serializers.Serializer):
    """Param shape. `customer_id` is auto-merged from `scope_customer.id`
    by the fire dispatcher for customer-scoped schedules; admins only need
    to set it explicitly on tenant-scoped schedules (rare — pick a target
    company by hand)."""

    customer_id = serializers.UUIDField()

    def validate_customer_id(self, value):
        """Belt-and-suspenders: confirm the Companies row exists in this tenant."""
        tenant = self.context.get("tenant")
        if tenant is None:
            return value
        from Tracker.models import Companies
        exists = Companies.unscoped.filter(id=value, tenant=tenant).exists()
        if not exists:
            raise serializers.ValidationError(
                "Customer does not exist in this tenant."
            )
        return value


def _greeting_namespace(recipient) -> SimpleNamespace:
    """Build a `customer`-shaped namespace the templates can render against.

    Templates use `{{ customer.first_name|default:"there" }}`. Recipients are
    either Users (have `.first_name`) or ExternalContacts (have `.name` like
    'Jane Procurement'). We split the contact's name on whitespace to give
    the template something to render that won't read awkwardly.
    """
    first_name = getattr(recipient, "first_name", None)
    if first_name:
        return SimpleNamespace(first_name=first_name)
    raw_name = getattr(recipient, "name", None) or getattr(recipient, "username", "")
    first_token = raw_name.split()[0] if raw_name else ""
    return SimpleNamespace(first_name=first_token)


class CustomerActiveOrdersProvider(ScheduledContentProvider):
    name = "customer_active_orders"
    title = "Customer active orders"
    description = (
        "Snapshot of one customer organization's currently-active orders "
        "(RFI / PENDING / IN_PROGRESS / ON_HOLD). Equivalent to the legacy "
        "weekly order update email."
    )
    param_serializer_class = _CustomerActiveOrdersParams

    def build_content(
        self,
        *,
        validated_params: dict,
        tenant,
        recipient,
    ) -> RenderedContent | None:
        """Render the digest for one recipient. Returns None when the
        customer has zero qualifying orders — the fire dispatcher then
        skips writing an outbox row for that recipient.

        We deliberately re-run the order query per recipient. Order count
        is small (single-digit to low hundreds per customer), the queryset
        is identical across recipients on the same schedule fire, and the
        cached-once pattern would require either a class-level cache (state
        bug surface) or a sibling helper the dispatcher pre-computes. Keep
        the contract simple; optimize if a perf trace shows it matters.
        """
        from Tracker.models import Companies, Orders, OrdersStatus

        customer_id = validated_params["customer_id"]
        try:
            customer = Companies.objects.get(id=customer_id, tenant=tenant)
        except Companies.DoesNotExist:
            logger.warning(
                "CustomerActiveOrdersProvider: customer %s not found in tenant %s",
                customer_id, tenant.id,
            )
            return None

        active_statuses = [
            OrdersStatus.RFI,
            OrdersStatus.PENDING,
            OrdersStatus.IN_PROGRESS,
            OrdersStatus.ON_HOLD,
        ]
        orders_qs = (
            Orders.objects
            .filter(company=customer, archived=False, order_status__in=active_statuses)
            .select_related("company")
            .prefetch_related("parts__step")
        )

        # Reuse the legacy helper — same field shape the templates expect.
        # Import locally to avoid a model-import-time dependency on tasks.py.
        from Tracker.tasks import _prepare_order_data
        order_summaries = _prepare_order_data(orders_qs)

        if not order_summaries:
            # Nothing to send. Mirrors the legacy `if not active_orders: continue`
            # behavior in send_weekly_emails.py.
            return None

        context: dict[str, Any] = {
            "customer": _greeting_namespace(recipient),
            "orders": order_summaries,
            "week_ending": timezone.now().date(),
            "total_orders": len(order_summaries),
        }

        subject = render_to_string(
            "emails/weekly_customer_update_subject.txt", context,
        ).strip()
        html = render_to_string("emails/weekly_customer_update.html", context)
        text = render_to_string("emails/weekly_customer_update.txt", context)

        return RenderedContent(subject=subject, html=html, text=text)

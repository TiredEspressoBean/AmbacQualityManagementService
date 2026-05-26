"""MES notification event registrations.

Imported by TrackerConfig.ready() so registration runs at startup.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from Tracker.services.core.notifications import EventType, register_event


# =============================================================================
# workorder.held — fired from scan_work_order_holds_and_overdue beat task
# =============================================================================

@dataclass(frozen=True)
class WorkOrderHeldPayload:
    """Payload for `workorder.held`. Replaces the legacy WORK_ORDER_HELD_TOO_LONG
    event_type. Tenant rules can route on work_order_id / reason via CEL."""

    id: str                          # WorkOrder id; correlation id source
    tenant_id: str
    work_order_id: str
    work_order_number: str
    hold_id: str
    reason: str
    placed_at: datetime | None
    hours_open: float | None

    @classmethod
    def sample(cls) -> 'WorkOrderHeldPayload':
        return cls(
            id='00000000-0000-0000-0000-000000000007',
            tenant_id='00000000-0000-0000-0000-000000000000',
            work_order_id='00000000-0000-0000-0000-000000000007',
            work_order_number='WO-2026-0007',
            hold_id='00000000-0000-0000-0000-000000000077',
            reason='Awaiting material',
            placed_at=datetime(2026, 5, 1, 8, 0),
            hours_open=72.5,
        )


register_event(EventType(
    code='workorder.held',
    label='Work Order Held Too Long',
    domain='Orders',
    payload_schema=WorkOrderHeldPayload,
    default_channels=['in_app', 'email'],
    default_recipient_groups=['Production Manager'],
    default_on=False,
    transactional=False,
    description='A work order has been on hold past the configured threshold.',
    external_routable=False,
))


# =============================================================================
# workorder.overdue — fired from scan_work_order_holds_and_overdue beat task
# =============================================================================

@dataclass(frozen=True)
class WorkOrderOverduePayload:
    """Payload for `workorder.overdue`. Replaces the legacy WORK_ORDER_OVERDUE
    event_type."""

    id: str                          # WorkOrder id; correlation id source
    tenant_id: str
    work_order_id: str
    work_order_number: str
    expected_completion: str | None  # ISO date string

    @classmethod
    def sample(cls) -> 'WorkOrderOverduePayload':
        return cls(
            id='00000000-0000-0000-0000-000000000007',
            tenant_id='00000000-0000-0000-0000-000000000000',
            work_order_id='00000000-0000-0000-0000-000000000007',
            work_order_number='WO-2026-0007',
            expected_completion='2026-05-10',
        )


register_event(EventType(
    code='workorder.overdue',
    label='Work Order Overdue',
    domain='Orders',
    payload_schema=WorkOrderOverduePayload,
    default_channels=['in_app', 'email'],
    default_recipient_groups=['Production Manager'],
    default_on=True,
    transactional=False,
    description='A work order is past its expected completion date.',
    external_routable=False,
))


# =============================================================================
# order.shipped — outbound ASN-style notification to customer contacts
# =============================================================================

@dataclass(frozen=True)
class OrderShippedPayload:
    """Payload for `order.shipped`. `customer_id` enables customer-scope
    rule matching for outbound ASN notifications."""

    id: str                          # Order id; correlation id source
    tenant_id: str
    order_number: str
    customer_id: str | None          # nullable — internal orders may not have a customer
    customer_name: str
    shipped_at: datetime
    carrier: str
    tracking_number: str
    expected_delivery: str | None    # ISO date string

    @classmethod
    def sample(cls) -> 'OrderShippedPayload':
        return cls(
            id='00000000-0000-0000-0000-000000000009',
            tenant_id='00000000-0000-0000-0000-000000000000',
            order_number='ORD-2026-0009',
            customer_id='00000000-0000-0000-0000-000000000abc',
            customer_name='Acme Aero',
            shipped_at=datetime(2026, 5, 12, 14, 30),
            carrier='UPS',
            tracking_number='1Z999AA10123456784',
            expected_delivery='2026-05-15',
        )


register_event(EventType(
    code='order.shipped',
    label='Order Shipped',
    domain='Orders',
    payload_schema=OrderShippedPayload,
    default_channels=['email'],
    default_recipient_groups=[],
    default_on=False,
    transactional=True,
    description='Shipment dispatched. Customer-scoped rules can route to ExternalContacts.',
    external_routable=True,
))

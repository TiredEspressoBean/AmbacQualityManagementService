"""The plant's clock: what "today" and "now" mean for a tenant.

A shop works on the clock on its wall. `Tenant.default_timezone` (organization
settings) is that clock. `timezone.now().date()` is the UTC day and `date.today()` is
the server's, and both disagree with the plant's every evening in a zone behind UTC —
so a lot received at 8 pm in a UTC-5 plant was dated tomorrow, a certificate expiring
"today" read as expired a few hours early, and a CAPA due today went overdue at 7 pm.

Use these instead, for any date a person reads or a rule compares:

    from Tracker.services.core.clock import tenant_today, tenant_now
    received_date = tenant_today(lot.tenant)
    if cert.expiry_date < tenant_today(cert.tenant): ...

`tenant` may be a Tenant, a tenant id, or None (the current request / task tenant from
the tenant ContextVar). With no tenant at all it falls back to the server's current
timezone — the old behaviour — rather than raising.

Timestamps (`created_at`, `approved_at`, …) stay aware datetimes in UTC; only the DAY a
person means is resolved on the plant's clock.
"""
from __future__ import annotations

from datetime import date, datetime

from django.utils import timezone


def plant_tz(tenant=None):
    """The tenant's timezone (`Tenant.default_timezone`), or the server's if none."""
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    tenant = _resolve(tenant)
    name = getattr(tenant, 'default_timezone', None)
    if not name:
        return timezone.get_current_timezone()
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return timezone.get_current_timezone()


def tenant_now(tenant=None) -> datetime:
    """Now, as an aware datetime on the plant's clock."""
    return timezone.now().astimezone(plant_tz(tenant))


def tenant_today(tenant=None) -> date:
    """Today, on the plant's clock."""
    return tenant_now(tenant).date()


def _resolve(tenant):
    """A Tenant from a Tenant, an id, or the current tenant ContextVar."""
    if tenant is not None and hasattr(tenant, 'default_timezone'):
        return tenant
    tenant_id = tenant
    if tenant_id is None:
        from Tracker.utils.tenant_context import get_current_tenant_id
        tenant_id = get_current_tenant_id()
    if tenant_id is None:
        return None
    from Tracker.models import Tenant
    return Tenant.objects.filter(pk=tenant_id).only('id', 'default_timezone').first()

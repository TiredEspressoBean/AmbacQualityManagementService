"""Test helpers for the notification system.

Small surface — tests reach for the real registry / outbox / channel
modules. These factories shave off boilerplate for common patterns.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from typing import Any, Iterator
from unittest.mock import patch

from django.contrib.auth import get_user_model

from Tracker.services.core.notifications.registry import get_event


User = get_user_model()


def make_event_payload(event_code: str, **overrides: Any):
    """Build a payload instance for `event_code` from its `sample()` plus overrides.

    Usage:
        payload = make_event_payload('ncr.opened', severity='critical', part_number='P-9')
    """
    event = get_event(event_code)
    sample = event.payload_schema.sample()
    if overrides:
        return replace(sample, **overrides)
    return sample


@contextmanager
def capture_channel_sends() -> Iterator[list]:
    """Patch every registered channel's `send` so tests can assert what fired.

    Yields a list that fills with `(channel_code, outbox_row)` tuples in order.
    """
    from Tracker.services.core.notifications.channels.base import CHANNEL_REGISTRY

    captured: list = []
    patchers = []
    try:
        for code, channel in CHANNEL_REGISTRY._channels.items():
            p = patch.object(
                channel,
                'send',
                side_effect=lambda row, _code=code: captured.append((_code, row)),
            )
            p.start()
            patchers.append(p)
        yield captured
    finally:
        for p in patchers:
            p.stop()


def make_tenant_group(tenant, name: str, *, is_custom: bool = False):
    """Get-or-create a TenantGroup under the given tenant.

    Tenant post_save signals may pre-seed common groups (QA Manager, etc.),
    so tests that name those groups must not error on duplicate creation.
    """
    from Tracker.models import TenantGroup
    group, _ = TenantGroup.objects.get_or_create(
        tenant=tenant, name=name, defaults={'is_custom': is_custom},
    )
    return group


def make_user_in_groups(tenant, *groups, email: str | None = None, **extra):
    """Create a user assigned to one or more TenantGroups via UserRole rows.

    Usage:
        operator = make_user_in_groups(tenant, operator_group)
        manager_and_inspector = make_user_in_groups(tenant, mgr_group, qa_group)
    """
    from Tracker.models import UserRole
    import uuid

    if email is None:
        email = f'user-{uuid.uuid4().hex[:8]}@test.local'
    user = User.objects.create_user(
        email=email,
        username=email,
        tenant=tenant,
        **extra,
    )
    for group in groups:
        UserRole.objects.create(user=user, group=group)
    return user


def set_user_preference(user, event_code: str, channel: str, enabled: bool) -> None:
    """Upsert a single (event, channel) override on UserNotificationPreference."""
    from Tracker.models import UserNotificationPreference
    pref, _ = UserNotificationPreference.objects.get_or_create(
        user=user,
        defaults={'tenant': user.tenant, 'preferences': {}},
    )
    prefs = dict(pref.preferences or {})
    event_prefs = dict(prefs.get(event_code) or {})
    event_prefs[channel] = enabled
    prefs[event_code] = event_prefs
    pref.preferences = prefs
    pref.save(update_fields=['preferences', 'updated_at'])


def set_tenant_default(tenant, event_code: str, channel: str, enabled: bool, *, role=None) -> None:
    """Upsert a TenantNotificationDefault row. role=None → tenant-wide; role=<TenantGroup> → role-scoped."""
    from Tracker.models import TenantNotificationDefault
    TenantNotificationDefault.objects.update_or_create(
        tenant=tenant,
        event_code=event_code,
        channel=channel,
        role=role,
        defaults={'enabled': enabled},
    )


def make_tenant_rule(tenant, event_code, *, channels=None, conditions='', name=None,
                     recipient_users=(), recipient_groups=(), min_gap_seconds=0,
                     recipient_strategy='static'):
    """Create a tenant-scoped NotificationRule for tests."""
    from Tracker.models import NotificationRule
    rule = NotificationRule.objects.create(
        tenant=tenant,
        name=name or f'tenant rule for {event_code}',
        event_code=event_code,
        scope_kind='tenant',
        conditions_source=conditions,
        channels=channels or ['in_app'],
        min_gap_seconds=min_gap_seconds,
        recipient_strategy=recipient_strategy,
    )
    if recipient_users:
        rule.recipient_users.add(*recipient_users)
    if recipient_groups:
        rule.recipient_groups.add(*recipient_groups)
    return rule


def make_personal_rule(tenant, owner_user, event_code, *, channels=None, conditions='',
                      name=None, min_gap_seconds=0, recipient_strategy='static'):
    """Create a personal-scope NotificationRule for tests."""
    from Tracker.models import NotificationRule
    return NotificationRule.objects.create(
        tenant=tenant,
        owner_user=owner_user,
        name=name or f'personal rule for {event_code}',
        event_code=event_code,
        scope_kind='personal',
        conditions_source=conditions,
        channels=channels or ['in_app'],
        min_gap_seconds=min_gap_seconds,
        recipient_strategy=recipient_strategy,
    )


def make_customer_rule(tenant, customer, event_code, *, channels=None, conditions='',
                       name=None, recipient_users=(), recipient_groups=(),
                       recipient_external=(), min_gap_seconds=0,
                       recipient_strategy='static'):
    """Create a customer-scoped NotificationRule for tests."""
    from Tracker.models import NotificationRule
    rule = NotificationRule.objects.create(
        tenant=tenant,
        scope_customer=customer,
        name=name or f'customer rule for {event_code}',
        event_code=event_code,
        scope_kind='customer',
        conditions_source=conditions,
        channels=channels or ['email'],
        min_gap_seconds=min_gap_seconds,
        recipient_strategy=recipient_strategy,
    )
    if recipient_users:
        rule.recipient_users.add(*recipient_users)
    if recipient_groups:
        rule.recipient_groups.add(*recipient_groups)
    if recipient_external:
        rule.recipient_external.add(*recipient_external)
    return rule


def make_tenant_schedule(tenant, *, name=None, provider_kind='customer_active_orders',
                         provider_params=None, cadence='weekly', day_of_week=4,
                         day_of_month=None, time_of_day=None, channels=None,
                         recipient_users=(), recipient_groups=()):
    """Create a tenant-scoped NotificationSchedule for tests."""
    from datetime import time as dtime
    from Tracker.models import NotificationSchedule
    sched = NotificationSchedule.objects.create(
        tenant=tenant,
        name=name or f'tenant schedule {provider_kind}',
        scope_kind='tenant',
        provider_kind=provider_kind,
        provider_params=provider_params or {},
        cadence=cadence,
        day_of_week=day_of_week if cadence == 'weekly' else None,
        day_of_month=day_of_month if cadence == 'monthly' else None,
        time_of_day=time_of_day or dtime(8, 0),
        channels=channels or ['email'],
    )
    if recipient_users:
        sched.recipient_users.add(*recipient_users)
    if recipient_groups:
        sched.recipient_groups.add(*recipient_groups)
    return sched


def make_customer_schedule(tenant, customer, *, name=None,
                           provider_kind='customer_active_orders',
                           provider_params=None, cadence='weekly', day_of_week=4,
                           day_of_month=None, time_of_day=None, channels=None,
                           recipient_users=(), recipient_groups=(), recipient_external=()):
    """Create a customer-scoped NotificationSchedule for tests."""
    from datetime import time as dtime
    from Tracker.models import NotificationSchedule
    sched = NotificationSchedule.objects.create(
        tenant=tenant,
        scope_customer=customer,
        name=name or f'customer schedule {provider_kind}',
        scope_kind='customer',
        provider_kind=provider_kind,
        provider_params=provider_params or {},
        cadence=cadence,
        day_of_week=day_of_week if cadence == 'weekly' else None,
        day_of_month=day_of_month if cadence == 'monthly' else None,
        time_of_day=time_of_day or dtime(8, 0),
        channels=channels or ['email'],
    )
    if recipient_users:
        sched.recipient_users.add(*recipient_users)
    if recipient_groups:
        sched.recipient_groups.add(*recipient_groups)
    if recipient_external:
        sched.recipient_external.add(*recipient_external)
    return sched


def make_personal_schedule(tenant, owner_user, *, name=None,
                           provider_kind='customer_active_orders',
                           provider_params=None, cadence='weekly', day_of_week=4,
                           day_of_month=None, time_of_day=None, channels=None):
    """Create a personal NotificationSchedule for tests. Owner is the implicit
    recipient — no recipient_* M2Ms are populated."""
    from datetime import time as dtime
    from Tracker.models import NotificationSchedule
    sched = NotificationSchedule.objects.create(
        tenant=tenant,
        owner_user=owner_user,
        name=name or f'personal schedule {provider_kind}',
        scope_kind='personal',
        provider_kind=provider_kind,
        provider_params=provider_params or {},
        cadence=cadence,
        day_of_week=day_of_week if cadence == 'weekly' else None,
        day_of_month=day_of_month if cadence == 'monthly' else None,
        time_of_day=time_of_day or dtime(8, 0),
        channels=channels or ['email'],
    )
    return sched

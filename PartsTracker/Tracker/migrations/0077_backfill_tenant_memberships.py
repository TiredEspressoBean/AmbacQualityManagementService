"""Backfill TenantMembership rows from the legacy access derivation.

Behavior-preserving: every (user, tenant) pair that previously granted access
(home `User.tenant`, or any `UserRole` in the tenant) gets an ACTIVE membership.
Idempotent via get_or_create; reverse is a no-op (the table drop in 0076's
reverse handles teardown).
"""
from django.db import migrations


def backfill(apps, schema_editor):
    User = apps.get_model('Tracker', 'User')
    UserRole = apps.get_model('Tracker', 'UserRole')
    TenantMembership = apps.get_model('Tracker', 'TenantMembership')

    # Home memberships — one per user with a home tenant.
    for user_id, tenant_id in (
        User.objects.exclude(tenant__isnull=True).values_list('id', 'tenant_id')
    ):
        TenantMembership.objects.get_or_create(
            user_id=user_id, tenant_id=tenant_id,
            defaults={'status': 'ACTIVE', 'is_home': True},
        )

    # Role-derived memberships — consultants / cross-tenant members.
    for user_id, tenant_id in (
        UserRole.objects.values_list('user_id', 'group__tenant_id').distinct()
    ):
        if tenant_id is None:
            continue
        TenantMembership.objects.get_or_create(
            user_id=user_id, tenant_id=tenant_id,
            defaults={'status': 'ACTIVE'},
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('Tracker', '0076_tenantmembership'),
    ]

    operations = [
        migrations.RunPython(backfill, noop_reverse),
    ]

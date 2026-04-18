"""
Tenant-aware serializer fields.

TenantScopedPrimaryKeyRelatedField closes the cross-tenant FK poisoning
hole that opens when a SecureModel's `objects` manager is used with
auto-scoping: module-level queryset declarations on `PrimaryKeyRelatedField`
evaluate at import time (before any tenant context exists), so they must
use `Model.unscoped.all()` — but that queryset sees every tenant's rows
at validation time too, letting a request body reference a foreign-tenant
PK and pass validation.

This subclass re-scopes the lookup queryset at validation time using the
Python ContextVar set by TenantMiddleware / tenant_context(). A foreign-
tenant PK fails the lookup and DRF raises "object does not exist."

Usage:
    from Tracker.serializers.fields import TenantScopedPrimaryKeyRelatedField

    class OrderSerializer(serializers.ModelSerializer):
        company = TenantScopedPrimaryKeyRelatedField(
            queryset=Companies.unscoped.all(),
            allow_null=True, required=False,
        )
"""
from rest_framework import serializers

from Tracker.utils.tenant_context import current_tenant_var


class TenantScopedPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    """PrimaryKeyRelatedField that scopes its lookup to the current tenant.

    Behavior:
    - The `queryset=` argument is evaluated at class definition (import
      time, no tenant context), so callers must pass `Model.unscoped.all()`
      or similar — a plain-manager queryset that won't raise.
    - `get_queryset()` is called per-request at validation time. We read
      the ContextVar and filter the base queryset by tenant_id when:
        - the ContextVar is set, AND
        - the target model has a `tenant` FK.
    - If the ContextVar is unset (exempt paths, shell, etc.) or the
      target model is not tenant-scoped, the queryset is returned
      unfiltered — consistent with the rest of the Secure* pattern.

    For tenant-scoped target models, a request body referencing a
    foreign-tenant PK fails to resolve and DRF raises its standard
    "object does not exist" validation error.
    """

    def get_queryset(self):
        qs = super().get_queryset()
        if qs is None:
            return qs

        tenant_id = current_tenant_var.get()
        if tenant_id is None:
            return qs

        # Only tenant-scoped models have a `tenant` field. Defensively
        # introspect rather than import SecureModel here to avoid a
        # circular import at module load time.
        model = qs.model
        if not any(f.name == 'tenant' for f in model._meta.get_fields()):
            return qs

        return qs.filter(tenant_id=tenant_id)

# viewsets/base.py - Base classes and mixins for tenant-scoped viewsets
"""
Multi-tenancy support for DRF ViewSets.

This module provides mixins and base classes that ensure all API queries
are properly scoped to the current tenant and users have appropriate permissions.

Permission Enforcement:
    TenantScopedMixin automatically applies TenantModelPermissions which:
    - Maps HTTP methods to permission codenames (GET->view, POST->add, etc.)
    - Checks permissions via User.has_tenant_perm() (tenant-scoped)
    - Superusers bypass permission checks

CSV Import/Export:
    All TenantScopedModelViewSet classes automatically include CSV import/export
    capabilities via CSVImportMixin and DataExportMixin. These provide:
    - GET /import-template/ - Download import template (CSV or Excel)
    - POST /import/ - Import data from CSV/Excel file
    - GET /export/ - Export filtered data to CSV/Excel

    Configuration is automatic via model introspection, but can be customized
    by setting class attributes (export_fields, csv_field_mapping, etc.)

Usage:
    # For most ViewSets, use the mixin:
    class MyViewSet(TenantScopedMixin, viewsets.ModelViewSet):
        queryset = MyModel.objects.all()
        serializer_class = MySerializer

    # For ViewSets that need tenant but shouldn't filter (e.g., superuser views):
    class AdminViewSet(TenantAwareMixin, viewsets.ModelViewSet):
        ...
"""

import logging
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from Tracker.permissions import TenantModelPermissions
from Tracker.viewsets.mixins import CSVImportMixin, DataExportMixin

logger = logging.getLogger(__name__)


class TenantAwareMixin:
    """
    Base mixin that provides tenant context to ViewSets.

    This mixin:
    - Exposes self.tenant (current tenant from request)
    - Provides auto-assignment of tenant on create
    - Does NOT filter querysets (use TenantScopedMixin for that)

    Use this when you need tenant awareness but want to handle
    filtering yourself (e.g., admin views that can see all tenants).
    """

    @property
    def tenant(self):
        """Get the current tenant from the request."""
        return getattr(self.request, 'tenant', None)

    def qs_for_user(self, model, include_archived=False):
        """
        Get a tenant-filtered queryset for any model.

        Use this in custom actions that query models other than the viewset's main model.
        Leverages the model's for_user() method if available (from SecureManager),
        otherwise falls back to basic tenant filtering.

        Args:
            model: The model class to query
            include_archived: Whether to include soft-deleted records (default: False)

        Returns:
            A tenant-filtered queryset

        Usage in custom actions:
            capas = self.qs_for_user(CAPA).filter(status='OPEN')
            reports = self.qs_for_user(QualityReports).filter(status='FAIL')
        """
        qs = model.objects.all()
        if hasattr(qs, 'for_user'):
            return qs.for_user(self.request.user, include_archived=include_archived)
        # Fallback for models without for_user (e.g., Django built-ins)
        if hasattr(model, 'tenant') and self.tenant:
            return qs.filter(tenant=self.tenant)
        return qs

    def perform_create(self, serializer):
        """Auto-assign tenant when creating new objects."""
        # Only set tenant if the model has a tenant field
        model = serializer.Meta.model
        if hasattr(model, 'tenant'):
            tenant = self.tenant
            if tenant:
                serializer.save(tenant=tenant)
                return
            elif not self.request.user.is_superuser:
                # Non-superusers must have a tenant
                raise PermissionDenied("No tenant context available")

        # Fall back to default behavior
        super().perform_create(serializer)

    def perform_update(self, serializer):
        """Prevent changing tenant on update."""
        instance = serializer.instance
        if hasattr(instance, 'tenant') and instance.tenant:
            # Ensure tenant isn't changed
            if 'tenant' in serializer.validated_data:
                if serializer.validated_data['tenant'] != instance.tenant:
                    raise PermissionDenied("Cannot change tenant of existing object")

        super().perform_update(serializer)


class TenantScopedMixin(TenantAwareMixin):
    """
    Mixin that filters all querysets to the current tenant and applies user permissions.

    This is the primary mixin for most ViewSets. It:
    - Enforces tenant-scoped permissions (TenantModelPermissions)
    - Filters queryset to current tenant
    - Applies for_user() filtering (permission-based data scoping)
    - Auto-assigns tenant on create
    - Prevents cross-tenant access

    Permission Enforcement:
    - GET/HEAD/OPTIONS -> view_{model} permission
    - POST -> add_{model} permission
    - PUT/PATCH -> change_{model} permission
    - DELETE -> delete_{model} permission

    Superusers bypass both permission checks and tenant filtering.

    Query parameters:
    - include_archived=true: Include soft-deleted records (default: false)
    - tenant=<uuid>: (superuser only) Filter to specific tenant

    Usage:
        class OrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
            queryset = Order.objects.all()
            serializer_class = OrderSerializer
    """

    # Permission classes - require authentication and tenant-scoped model permissions
    permission_classes = [IsAuthenticated, TenantModelPermissions]

    # Set to True to require tenant (return empty queryset if no tenant)
    tenant_required = True

    # Set to True to allow superusers to see all tenants
    allow_superuser_bypass = True

    def get_queryset(self):
        """Filter queryset to current tenant and apply user permissions."""
        queryset = super().get_queryset()

        # Check if model has tenant field
        model = queryset.model
        if not hasattr(model, 'tenant'):
            # Non-tenant model - apply for_user if available, otherwise return as-is
            if hasattr(queryset, 'for_user'):
                return queryset.for_user(self.request.user, include_archived=self._include_archived())
            return queryset

        # Superuser bypass (if enabled)
        if self.allow_superuser_bypass and self.request.user.is_superuser:
            # Superusers can optionally filter by tenant via query param
            tenant_filter = self.request.query_params.get('tenant')
            if tenant_filter:
                queryset = queryset.filter(tenant_id=tenant_filter)

            # Still apply for_user for export control, but superusers see all
            if hasattr(queryset, 'for_user'):
                return queryset.for_user(self.request.user, include_archived=self._include_archived())
            return queryset

        # Get tenant from request
        tenant = self.tenant

        if tenant:
            queryset = queryset.filter(tenant=tenant)
        elif self.tenant_required:
            # No tenant and tenant is required - return empty queryset
            logger.warning(
                f"No tenant context for {self.__class__.__name__}, "
                f"user={self.request.user}, path={self.request.path}"
            )
            return queryset.none()

        # Apply user-based filtering (security, archived, customer scoping)
        if hasattr(queryset, 'for_user'):
            queryset = queryset.for_user(self.request.user, include_archived=self._include_archived())

        return queryset

    def _include_archived(self):
        """Check if client requested to include archived records."""
        param = self.request.query_params.get('include_archived', '').lower()
        return param in ('true', '1', 'yes')


class TenantScopedModelViewSet(TenantScopedMixin, CSVImportMixin, DataExportMixin, viewsets.ModelViewSet):
    """
    Convenience base class for tenant-scoped ModelViewSets with CSV import/export.

    Includes:
    - Tenant scoping and permission enforcement
    - CSV/Excel import (POST /import/)
    - CSV/Excel export (GET /export/)
    - Import template download (GET /import-template/)

    All import/export configuration is automatic via model introspection.
    Override class attributes for customization:
    - export_fields: List of fields to export
    - export_filename: Base filename for exports
    - csv_import_serializer: Custom import serializer class
    - csv_field_mapping: Dict mapping CSV columns to model fields

    Usage:
        class OrderViewSet(TenantScopedModelViewSet):
            queryset = Order.objects.all()
            serializer_class = OrderSerializer
            # Optional: customize export
            export_fields = ['id', 'name', 'status', 'company__name']
    """
    pass


class TenantScopedReadOnlyModelViewSet(TenantScopedMixin, DataExportMixin, viewsets.ReadOnlyModelViewSet):
    """
    Convenience base class for tenant-scoped read-only ViewSets with CSV export.

    Includes:
    - Tenant scoping and permission enforcement
    - CSV/Excel export (GET /export/)

    Note: Import is not included since this is read-only.

    Usage:
        class ReportViewSet(TenantScopedReadOnlyModelViewSet):
            queryset = Report.objects.all()
            serializer_class = ReportSerializer
    """
    pass


# ===== Non-tenant models =====

class NonTenantModelViewSet(viewsets.ModelViewSet):
    """
    Base class for ViewSets of models that are NOT tenant-scoped.

    Examples: Django's Group, Permission, ContentType, LogEntry

    These are global resources shared across all tenants.
    Requires authentication but not tenant-scoped permissions.
    """
    permission_classes = [IsAuthenticated]


# ===== Nested resource helpers =====

class TenantScopedNestedMixin(TenantScopedMixin):
    """
    Mixin for nested resources that should inherit tenant from parent.

    For URLs like /orders/{order_id}/parts/, this ensures parts
    are filtered to both the tenant AND the parent order.

    Usage:
        class OrderPartsViewSet(TenantScopedNestedMixin, viewsets.ModelViewSet):
            queryset = Part.objects.all()
            parent_lookup_field = 'order_id'
            parent_model = Order

            def get_queryset(self):
                qs = super().get_queryset()
                order_id = self.kwargs.get('order_id')
                if order_id:
                    qs = qs.filter(order_id=order_id)
                return qs
    """
    parent_lookup_field = None
    parent_model = None

    def get_parent_object(self):
        """Get the parent object, ensuring tenant access."""
        if not self.parent_model or not self.parent_lookup_field:
            return None

        parent_id = self.kwargs.get(self.parent_lookup_field)
        if not parent_id:
            return None

        # Query parent with tenant scoping
        tenant = self.tenant
        qs = self.parent_model.objects.all()

        if tenant and hasattr(self.parent_model, 'tenant'):
            qs = qs.filter(tenant=tenant)

        return qs.filter(pk=parent_id).first()

    def perform_create(self, serializer):
        """Auto-assign both tenant and parent on create."""
        parent = self.get_parent_object()
        if parent:
            # Use parent's tenant if model is tenant-scoped
            tenant = getattr(parent, 'tenant', None) or self.tenant
            kwargs = {}

            if hasattr(serializer.Meta.model, 'tenant') and tenant:
                kwargs['tenant'] = tenant

            # Set parent FK if the serializer expects it
            parent_field = self.parent_lookup_field.replace('_id', '')
            if hasattr(serializer.Meta.model, parent_field):
                kwargs[parent_field] = parent

            if kwargs:
                serializer.save(**kwargs)
                return

        # Fall back to default behavior
        super().perform_create(serializer)

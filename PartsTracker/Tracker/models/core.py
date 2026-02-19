"""
Base models and infrastructure for the Tracker app.

Contains:
- SecureQuerySet: QuerySet with soft delete, versioning, and audit logging
- SecureManager: Manager with filtering, security, and permissions
- SecureModel: Abstract base model with soft delete, timestamps, versioning
- User: Extended user model with company association
- Companies: Company/customer entity model
- Documents: Universal document storage with classification and version control
- ArchiveReason: Archive tracking for auditing
- UserInvitation: User invitation and onboarding model
- NotificationTask: Unified notification scheduling system
- ApprovalRequest/Response/Template: Approval workflow infrastructure
- Utility functions and enums (ClassificationLevel, part_doc_upload_path)
"""

import json
import os
from datetime import date

from auditlog.models import LogEntry
from django.contrib.auth.models import AbstractUser, Group
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from uuid_utils.compat import uuid7


# =============================================================================
# TENANT MODEL - Must be defined before SecureModel
# =============================================================================

class Tenant(models.Model):
    """
    Represents a SaaS customer organization.

    Tenant is the top-level isolation boundary. All business data is scoped to a tenant.
    Note: Tenant ≠ Companies. Companies are the tenant's customers.
    """

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    name = models.CharField(max_length=100, help_text="Display name of the organization")
    slug = models.SlugField(unique=True, help_text="URL-safe identifier, immutable after creation")

    class Tier(models.TextChoices):
        STARTER = 'starter', 'Starter'
        PRO = 'pro', 'Pro'
        ENTERPRISE = 'enterprise', 'Enterprise'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        TRIAL = 'trial', 'Trial'
        SUSPENDED = 'suspended', 'Suspended'
        PENDING_DELETION = 'pending_deletion', 'Pending Deletion'

    tier = models.CharField(max_length=20, choices=Tier.choices, default=Tier.STARTER)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    is_active = models.BooleanField(default=True)  # Kept for backward compatibility
    is_demo = models.BooleanField(default=False, help_text="Demo tenant with reset capability")

    # Organization details
    logo = models.ImageField(
        upload_to='tenant_logos/',
        null=True,
        blank=True,
        help_text="Organization logo (recommended: 200x200 PNG)"
    )
    contact_email = models.EmailField(
        blank=True,
        help_text="Primary contact email for the organization"
    )
    contact_phone = models.CharField(
        max_length=30,
        blank=True,
        help_text="Primary contact phone number"
    )
    website = models.URLField(
        blank=True,
        help_text="Organization website URL"
    )
    address = models.TextField(
        blank=True,
        help_text="Organization mailing address"
    )
    default_timezone = models.CharField(
        max_length=50,
        default='UTC',
        help_text="Default timezone for the organization (IANA format, e.g., 'America/New_York')"
    )

    # Status tracking
    status_changed_at = models.DateTimeField(null=True, blank=True)
    trial_ends_at = models.DateTimeField(null=True, blank=True, help_text="Trial expiration date")

    # SSO / Identity configuration
    allowed_domains = models.JSONField(
        default=list,
        blank=True,
        help_text="Email domains for automatic SSO tenant matching, e.g. ['acme.com', 'acme.co.uk']"
    )

    # Timestamps - stored as UTC
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    settings = models.JSONField(default=dict, blank=True, help_text="Tenant-specific configuration")

    class Meta:
        ordering = ['name']
        verbose_name = 'Tenant'
        verbose_name_plural = 'Tenants'
        permissions = [
            ("full_tenant_access", "Has full visibility to all tenant data (without this, users only see data related to their orders)"),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Enforce immutable slug after creation
        if self.pk:
            old = Tenant.objects.filter(pk=self.pk).values_list('slug', flat=True).first()
            if old and old != self.slug:
                raise ValueError("Tenant slug cannot be changed after creation")
        super().save(*args, **kwargs)


# =============================================================================
# FACILITY MODEL - Multi-site support within a tenant
# =============================================================================

class Facility(models.Model):
    """
    Physical facility/plant within a tenant.

    Enables multi-facility deployments where:
    - Data can be scoped to specific facilities
    - Users can have different roles at different facilities
    - Reports can be filtered by facility

    For single-facility tenants, this model is optional (UserRole.facility can be null).
    """

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    tenant = models.ForeignKey(
        'Tenant',
        on_delete=models.CASCADE,
        related_name='facilities'
    )

    name = models.CharField(max_length=100, help_text="Display name (e.g., 'Plant A')")
    code = models.CharField(max_length=20, help_text="Short code (e.g., 'PLANT-A', 'MFG-01')")

    address = models.TextField(blank=True)
    tz = models.CharField(max_length=50, default='UTC', help_text="IANA timezone (e.g., 'America/New_York')")

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tracker_facility'
        unique_together = [('tenant', 'code')]
        ordering = ['name']
        verbose_name = 'Facility'
        verbose_name_plural = 'Facilities'

    def __str__(self):
        return f"{self.name} ({self.code})"


# =============================================================================
# TENANT GROUP MODEL - Tenant-scoped groups with customizable permissions
# =============================================================================

class TenantGroup(models.Model):
    """
    Tenant-scoped groups for organizing users with customizable permissions.

    Permissions control BOTH actions AND data visibility:
    - Action permissions: add_orders, change_parts, delete_qualityreports, etc.
    - Data-scoping permissions: view_orders (all) vs view_own_orders (relationship-filtered)

    A user can have different groups in different tenants:
    - QA Manager in Tenant A (full data access)
    - Customer in Tenant B (sees only their orders)

    Groups can be preset (seeded from presets.py) or custom (created by tenant admin).
    """

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    tenant = models.ForeignKey(
        'Tenant',
        on_delete=models.CASCADE,
        related_name='custom_groups'
    )

    name = models.CharField(max_length=100, help_text="Display name")
    description = models.TextField(blank=True)

    # Granular permissions - determines action permissions (what they can do)
    permissions = models.ManyToManyField(
        'auth.Permission',
        blank=True,
        related_name='tenant_groups',
        help_text="Specific permissions for this group (customizable per tenant)"
    )

    # Track preset vs custom groups
    is_custom = models.BooleanField(
        default=False,
        help_text="True if created by tenant admin, False if seeded from presets"
    )

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tracker_tenant_group'
        unique_together = [('tenant', 'name')]
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.tenant.slug})"

    def has_all_permissions(self):
        """Check if this group has all permissions (admin-level)."""
        from django.contrib.auth.models import Permission
        total_perms = Permission.objects.count()
        return self.permissions.count() >= total_perms


# =============================================================================
# USER ROLE MODEL - User's role assignment with facility/company scoping
# =============================================================================

class UserRole(models.Model):
    """
    User's role assignment within a tenant, with optional facility and company scoping.

    This is the core permission assignment model. A user can have multiple roles:
    - Different roles in different tenants (consultant working for multiple orgs)
    - Different roles in different facilities (operator at Plant A, manager at Plant B)
    - Customer role scoped to specific company (Boeing rep sees only Boeing orders)

    Replaces TenantGroupMembership with more flexible scoping.
    """

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    # Who
    user = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='user_roles'
    )

    # What group/role
    group = models.ForeignKey(
        'TenantGroup',
        on_delete=models.CASCADE,
        related_name='role_assignments'
    )

    # Scoping (all optional - None means "all")
    facility = models.ForeignKey(
        'Facility',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='role_assignments',
        help_text="Null = access to all facilities in tenant"
    )

    company = models.ForeignKey(
        'Companies',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='customer_roles',
        help_text="For customer/external roles: which company they represent"
    )

    # Audit
    granted_at = models.DateTimeField(default=timezone.now, editable=False)
    granted_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='roles_granted'
    )

    class Meta:
        db_table = 'tracker_user_role'
        unique_together = [('user', 'group', 'facility', 'company')]
        verbose_name = 'User Role'
        verbose_name_plural = 'User Roles'
        indexes = [
            models.Index(fields=['user', 'group']),
            models.Index(fields=['group', 'facility']),
        ]

    @property
    def tenant(self):
        """Tenant is derived from the group."""
        return self.group.tenant

    def __str__(self):
        parts = [f"{self.user.username} is {self.group.name}"]
        if self.facility:
            parts.append(f"@ {self.facility.name}")
        if self.company:
            parts.append(f"for {self.company.name}")
        return " ".join(parts)


class SecureQuerySet(models.QuerySet):
    """QuerySet with soft delete, versioning, audit logging, and export control filtering.

    Export control methods (chainable):
        .for_export_control(user)  - Filter by ITAR/EAR restrictions
        .for_classification(user)  - Filter by classification level
        .for_secure_access(user)   - Apply all security filters
    """

    # =========================================================================
    # Export Control Filtering (ITAR/EAR/Classification)
    # =========================================================================

    def for_export_control(self, user):
        """
        Filter queryset to only include items the user can access
        based on export control regulations (ITAR/EAR).

        - Excludes ITAR-controlled items if user is not a US Person
        - Excludes EAR-controlled items based on citizenship/authorization
        - Logs all access denials for compliance auditing
        """
        from Tracker.services.export_control import ExportControlService, ExportControlDenialReason

        model = self.model
        model_name = model._meta.model_name

        has_itar = hasattr(model, 'itar_controlled')
        has_eccn = hasattr(model, 'eccn')

        if not has_itar and not has_eccn:
            return self

        queryset = self

        # ITAR filtering
        if has_itar:
            can_access_itar, denial_reason = ExportControlService.can_access_itar_data(user)
            if not can_access_itar:
                ExportControlService.log_access_denial(
                    user=user,
                    resource_type=model_name,
                    resource_id='<queryset_filter>',
                    reason=denial_reason,
                    additional_context={'filter_type': 'ITAR_BULK_EXCLUSION'}
                )
                queryset = queryset.exclude(itar_controlled=True)

        # EAR filtering
        if has_eccn:
            citizenship = getattr(user, 'citizenship', '')
            if citizenship in ExportControlService.EAR_DENIED_COUNTRIES:
                ExportControlService.log_access_denial(
                    user=user,
                    resource_type=model_name,
                    resource_id='<queryset_filter>',
                    reason=ExportControlDenialReason.EAR_DENIED_COUNTRY,
                    additional_context={'filter_type': 'EAR_COUNTRY_EXCLUSION', 'citizenship': citizenship}
                )
                queryset = queryset.exclude(
                    ~models.Q(eccn='') & ~models.Q(eccn__iexact='EAR99')
                )

        return queryset

    def for_classification(self, user):
        """
        Filter queryset to only include items at classification levels
        the user is authorized to access (PUBLIC, INTERNAL, CONFIDENTIAL, etc.).
        """
        from Tracker.services.export_control import ExportControlService

        model = self.model
        if not hasattr(model, 'classification'):
            return self

        accessible_levels = ExportControlService.get_accessible_classification_levels(user)
        return self.filter(classification__in=accessible_levels)

    def for_secure_access(self, user):
        """
        Apply all security filters: export control + classification.

        Usage:
            Documents.objects.for_tenant(tenant).for_secure_access(user)
        """
        return self.for_export_control(user).for_classification(user)

    def for_user(self, user, include_archived=False):
        """
        Apply user-based filtering for data scoping.

        Data scoping logic:
        - Superuser: all data (optionally filtered by _current_tenant)
        - has view_{model} + full_tenant_access: all records of that type in tenant
        - has view_{model} only: filter by Order relationships (customer/viewers)
        - no view_{model} permission: no access

        The `full_tenant_access` permission grants visibility to all tenant data.
        Without it, users only see data related to their orders (via Order.customer
        and Order.viewers). This allows the same user to have different visibility
        in different tenants based on their group membership.

        Args:
            user: The user to filter for
            include_archived: If True, include soft-deleted records
        """
        model_name = self.model._meta.model_name

        # Start with archived filtering
        if include_archived:
            queryset = self
        else:
            queryset = self.active()

        # Superuser bypasses all checks (but still apply security filters)
        if user.is_superuser:
            tenant = getattr(user, '_current_tenant', None)
            if tenant:
                queryset = queryset.filter(tenant=tenant)
            return self._apply_security_filters(queryset, user, model_name)

        # Check for view permission on this model
        # Django permissions are named view_{model_name} without trailing 's'
        view_perm = f'view_{model_name}'
        if not user.has_tenant_perm(view_perm):
            # No permission to view this model at all
            return queryset.none()

        # User can view this model - check if they have full tenant access
        if user.has_tenant_perm('full_tenant_access'):
            return self._apply_security_filters(queryset, user, model_name)

        # Has view permission but not full access - filter by Order relationships
        return self._filter_by_relationship(queryset, user, model_name)

    def _apply_security_filters(self, queryset, user, model_name):
        """Apply export control and classification filters."""
        queryset = queryset.for_export_control(user)
        if model_name in ['documents', 'docchunk']:
            queryset = queryset.for_classification(user)
        return queryset

    def _filter_by_relationship(self, queryset, user, model_name):
        """
        Filter queryset to records related to user's orders.

        Used for users without broad view permissions. Access is derived from
        Order.customer and Order.viewers - the source of truth for object-level
        access. Child models derive access via FK joins to Order.
        """
        from django.db.models import Q
        from django.contrib.contenttypes.models import ContentType

        # Models that support relationship-based filtering
        relationship_models = {'orders', 'parts', 'workorder', 'qualityreports',
                               'documents', 'docchunk', 'user', 'companies'}

        if model_name not in relationship_models:
            return queryset.none()

        def get_accessible_order_ids():
            from Tracker.models import Orders
            return Orders.objects.filter(
                Q(customer=user) | Q(viewers=user)
            ).values_list('id', flat=True)

        if model_name == 'orders':
            return queryset.filter(Q(customer=user) | Q(viewers=user)).distinct()

        elif model_name == 'parts':
            return queryset.filter(
                Q(order__customer=user) | Q(order__viewers=user)
            ).distinct()

        elif model_name == 'workorder':
            return queryset.filter(
                Q(related_order__customer=user) | Q(related_order__viewers=user)
            ).distinct()

        elif model_name == 'qualityreports':
            return queryset.filter(
                Q(part__order__customer=user) | Q(part__order__viewers=user)
            ).distinct()

        elif model_name == 'documents':
            from Tracker.models import Orders, WorkOrder, Parts, PartTypes

            accessible_order_ids = get_accessible_order_ids()

            order_ct = ContentType.objects.get_for_model(Orders)
            workorder_ct = ContentType.objects.get_for_model(WorkOrder)
            part_ct = ContentType.objects.get_for_model(Parts)
            parttype_ct = ContentType.objects.get_for_model(PartTypes)

            accessible_workorder_ids = WorkOrder.objects.filter(
                related_order_id__in=accessible_order_ids
            ).values_list('id', flat=True)

            accessible_part_ids = Parts.objects.filter(
                order_id__in=accessible_order_ids
            ).values_list('id', flat=True)

            accessible_parttype_ids = PartTypes.objects.filter(
                parts__order_id__in=accessible_order_ids
            ).values_list('id', flat=True)

            return queryset.filter(
                classification='public'
            ).filter(
                Q(content_type=order_ct, object_id__in=[str(id) for id in accessible_order_ids]) |
                Q(content_type=workorder_ct, object_id__in=[str(id) for id in accessible_workorder_ids]) |
                Q(content_type=part_ct, object_id__in=[str(id) for id in accessible_part_ids]) |
                Q(content_type=parttype_ct, object_id__in=[str(id) for id in accessible_parttype_ids])
            ).distinct()

        elif model_name == 'docchunk':
            from Tracker.models import Documents
            accessible_doc_ids = Documents.objects.for_user(user).values_list('id', flat=True)
            return queryset.filter(doc_id__in=accessible_doc_ids)

        elif model_name == 'user':
            return queryset.filter(id=user.id)

        elif model_name == 'companies':
            if hasattr(user, 'parent_company') and user.parent_company:
                return queryset.filter(id=user.parent_company.id)
            return queryset.none()

        return queryset.none()

    def delete(self):
        """Soft delete all objects in queryset"""
        deleted_count = 0
        for obj in self:
            if not obj.archived:
                obj.delete()  # Calls model's delete() method
                deleted_count += 1
        return deleted_count, {}

    def bulk_soft_delete(self, actor=None, reason="bulk_operation"):
        """Fast bulk soft delete WITH audit logging"""
        objects_to_delete = list(self.filter(archived=False).values('id', 'pk'))
        if not objects_to_delete:
            return 0

        updated_count = self.filter(archived=False).update(deleted_at=timezone.now(), archived=True)

        if updated_count > 0:
            self._create_bulk_audit_logs(objects_to_delete, 'soft_delete_bulk', actor, reason)

        return updated_count

    def bulk_restore(self, actor=None, reason="bulk_restore"):
        """Bulk restore WITH audit logging"""
        objects_to_restore = list(self.filter(archived=True).values('id', 'pk'))
        if not objects_to_restore:
            return 0

        updated_count = self.filter(archived=True).update(deleted_at=None, archived=False)

        if updated_count > 0:
            self._create_bulk_audit_logs(objects_to_restore, 'restore_bulk', actor, reason)

        return updated_count

    def _create_bulk_audit_logs(self, object_list, action, actor=None, reason=""):
        """Create audit log entries for bulk operations"""
        if not object_list:
            return

        content_type = ContentType.objects.get_for_model(self.model)
        log_entries = []

        for obj_data in object_list:
            log_entries.append(
                LogEntry(content_type=content_type, object_pk=str(obj_data['pk']), object_id=obj_data['id'],
                         object_repr=f"{self.model.__name__} (id={obj_data['id']})", action=LogEntry.Action.UPDATE,
                         changes=json.dumps({'archived': [False, True] if 'delete' in action else [True, False],
                                             'bulk_operation': action, 'reason': reason}), actor=actor,
                         timestamp=timezone.now()))

        LogEntry.objects.bulk_create(log_entries)

    def hard_delete(self):
        """
        Hard delete is disabled until retention policy system with
        legal hold support is implemented.
        """
        raise NotImplementedError(
            "Hard delete disabled. Use soft delete (archive). "
            "Permanent deletion requires retention policy system with legal hold support."
        )

    # Basic filters
    def active(self):
        """Get non-archived objects"""
        # Some models (like DocChunk) don't have archived field
        model_fields = [f.name for f in self.model._meta.get_fields()]
        if 'archived' in model_fields:
            return self.filter(archived=False)
        return self

    def deleted(self):
        """Get archived objects"""
        return self.filter(archived=True)

    # Versioning filters
    def current_versions(self):
        """Get only current versions"""
        return self.filter(is_current_version=True)

    def all_versions(self):
        """Get all versions (current and old)"""
        return self

    # Combined filters
    def active_current(self):
        """Get active objects that are current versions"""
        return self.active().current_versions()


class SecureManager(models.Manager):
    """Unified manager with filtering, soft delete, versioning, and security"""

    # Define which models support customer filtering (Upgrade #4: Model Registration)
    RELATIONSHIP_FILTERABLE_MODELS = {
        'orders', 'parts', 'workorder', 'qualityreports',
        'documents', 'docchunk', 'user', 'companies'
    }

    def get_queryset(self):
        return SecureQuerySet(self.model, using=self._db)

    # User-based filtering
    def for_user(self, user, include_archived=False):
        """
        Apply user-based filtering for data scoping.

        Data scoping logic:
        - Superuser: all data (optionally filtered by _current_tenant)
        - has view_{model} + full_tenant_access: all records of that type in tenant
        - has view_{model} only: filter by Order relationships (customer/viewers)
        - no view_{model} permission: no access

        The `full_tenant_access` permission grants visibility to all tenant data.
        Without it, users only see data related to their orders (via Order.customer
        and Order.viewers). This allows the same user to have different visibility
        in different tenants based on their group membership.

        Args:
            user: The user to filter for
            include_archived: If True, include soft-deleted records
        """
        # Start with archived filtering
        if include_archived:
            queryset = self.get_queryset()
        else:
            queryset = self.active()

        model_name = self.model._meta.model_name

        # Superuser bypasses all checks (but still apply security filters)
        if user.is_superuser:
            tenant = getattr(user, '_current_tenant', None)
            if tenant:
                queryset = queryset.filter(tenant=tenant)
            return self._apply_security_filters(queryset, user, model_name)

        # Check for view permission on this model
        # Django permissions are named view_{model_name} without trailing 's'
        view_perm = f'view_{model_name}'
        if not user.has_tenant_perm(view_perm):
            # No permission to view this model at all
            return queryset.none()

        # User can view this model - check if they have full tenant access
        if user.has_tenant_perm('full_tenant_access'):
            return self._apply_security_filters(queryset, user, model_name)

        # Has view permission but not full access - filter by Order relationships
        return self._filter_by_relationship(queryset, user, model_name)

    def _apply_security_filters(self, queryset, user, model_name):
        """Apply export control and classification filters."""
        queryset = queryset.for_export_control(user)
        if model_name in ['documents', 'docchunk']:
            queryset = queryset.for_classification(user)
        return queryset

    def _filter_by_relationship(self, queryset, user, model_name):
        """
        Filter queryset to records related to user's orders.

        Used for users without broad view permissions. Access is derived from
        Order.customer and Order.viewers - the source of truth for object-level
        access. Child models derive access via FK joins to Order.
        """
        from django.db.models import Q
        from django.contrib.contenttypes.models import ContentType

        # Models that support relationship-based filtering
        if model_name not in self.RELATIONSHIP_FILTERABLE_MODELS:
            return queryset.none()

        # Get customer's accessible order IDs (used by multiple filters)
        def get_accessible_order_ids():
            from Tracker.models import Orders
            return Orders.objects.filter(
                Q(customer=user) | Q(viewers=user)
            ).values_list('id', flat=True)

        if model_name == 'orders':
            return queryset.filter(Q(customer=user) | Q(viewers=user)).distinct()

        elif model_name == 'parts':
            return queryset.filter(
                Q(order__customer=user) | Q(order__viewers=user)
            ).select_related('order').distinct()

        elif model_name == 'workorder':
            return queryset.filter(
                Q(related_order__customer=user) | Q(related_order__viewers=user)
            ).select_related('related_order').distinct()

        elif model_name == 'qualityreports':
            return queryset.filter(
                Q(part__order__customer=user) | Q(part__order__viewers=user)
            ).select_related('part__order').distinct()

        elif model_name == 'documents':
            # Customer sees PUBLIC docs attached to objects they can access
            from Tracker.models import Orders, WorkOrder, Parts, PartTypes

            accessible_order_ids = get_accessible_order_ids()

            # Get content types for linkable objects
            order_ct = ContentType.objects.get_for_model(Orders)
            workorder_ct = ContentType.objects.get_for_model(WorkOrder)
            part_ct = ContentType.objects.get_for_model(Parts)
            parttype_ct = ContentType.objects.get_for_model(PartTypes)

            # Get IDs of accessible related objects
            accessible_workorder_ids = WorkOrder.objects.filter(
                related_order_id__in=accessible_order_ids
            ).values_list('id', flat=True)

            accessible_part_ids = Parts.objects.filter(
                order_id__in=accessible_order_ids
            ).values_list('id', flat=True)

            # Part types from their orders
            accessible_parttype_ids = PartTypes.objects.filter(
                parts__order_id__in=accessible_order_ids
            ).values_list('id', flat=True)

            # Filter: PUBLIC classification AND attached to accessible object
            return queryset.filter(
                classification='public'
            ).filter(
                Q(content_type=order_ct, object_id__in=[str(id) for id in accessible_order_ids]) |
                Q(content_type=workorder_ct, object_id__in=[str(id) for id in accessible_workorder_ids]) |
                Q(content_type=part_ct, object_id__in=[str(id) for id in accessible_part_ids]) |
                Q(content_type=parttype_ct, object_id__in=[str(id) for id in accessible_parttype_ids])
            ).distinct()

        elif model_name == 'docchunk':
            # DocChunks follow the same logic via their parent document
            from Tracker.models import Documents
            accessible_doc_ids = Documents.objects.for_user(user).values_list('id', flat=True)
            return queryset.filter(doc_id__in=accessible_doc_ids).select_related('doc')

        elif model_name == 'user':
            return queryset.filter(id=user.id)

        elif model_name == 'companies':
            if hasattr(user, 'parent_company') and user.parent_company:
                return queryset.filter(id=user.parent_company.id)
            return queryset.none()

        return queryset.none()


    # Convenience methods that delegate to queryset
    def active(self):
        """Get active (non-archived) objects"""
        return self.get_queryset().active()

    def deleted(self):
        """Get archived objects"""
        return self.get_queryset().deleted()

    def current_versions(self):
        """Get only current versions"""
        return self.get_queryset().current_versions()

    def active_current(self):
        """Get active objects that are current versions"""
        return self.get_queryset().active_current()

    def for_user_current(self, user):
        """Get current versions filtered for user"""
        return self.for_user(user).current_versions()

    # Bulk operations
    def bulk_soft_delete(self, actor=None, reason="bulk_operation"):
        """Manager-level bulk soft delete"""
        return self.get_queryset().bulk_soft_delete(actor=actor, reason=reason)

    def bulk_restore(self, actor=None, reason="bulk_restore"):
        """Manager-level bulk restore"""
        return self.get_queryset().bulk_restore(actor=actor, reason=reason)

    # Versioning helpers
    def get_version_chain(self, root_id):
        """Get all versions of a particular object"""
        try:
            root = self.get(id=root_id)
            while root.previous_version:
                root = root.previous_version
            return root.get_version_history()
        except self.model.DoesNotExist:
            return []



class SecureModel(models.Model):
    """
    Base model with soft delete, timestamps, versioning, tenant scoping, and audit logging.

    Timezone Convention:
        All DateTimeFields store UTC timestamps. Frontend is responsible for
        converting to user's local timezone for display. This ensures:
        - Consistent storage regardless of server location
        - Correct ordering across timezones
        - No ambiguity during DST transitions

    Timestamp Fields:
        - created_at: Set to UTC now on creation. Can be overridden for data imports.
        - updated_at: Automatically updated to UTC now on every save.
        - deleted_at: Set to UTC now on soft delete.
    """

    # Primary key - UUIDv7 for time-ordered, globally unique IDs
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    # Tenant scoping - nullable for migration, all new records should have tenant
    tenant = models.ForeignKey(
        'Tenant',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_index=True,
        help_text="Tenant this record belongs to"
    )

    # External integration ID - for idempotent upserts from ERP, webhooks, etc.
    external_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text="External system identifier for integration sync"
    )

    # Soft delete fields
    archived = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    # Timestamp fields - all stored as UTC
    # Using default=timezone.now allows override for data imports/tests
    # editable=False prevents accidental modification in forms/admin
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    # Versioning fields
    version = models.PositiveIntegerField(default=1)
    previous_version = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name='next_versions')
    is_current_version = models.BooleanField(default=True)

    # Single manager that does everything
    objects = SecureManager()

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['tenant', 'created_at']),
        ]

    def delete(self, using=None, keep_parents=False):
        """Soft delete - django-auditlog will automatically log this"""
        if self.archived:
            return

        self.archived = True
        self.deleted_at = timezone.now()
        self.save(using=using)

    def archive(self, reason="user_request", user=None, notes=""):
        """
        Archives the object with a specific reason for audit trail.

        Args:
            reason (str): Archive reason code
            user (User): The user responsible for the archive action
            notes (str): Additional notes explaining the archive
        """
        if self.archived:
            return

        # Perform the soft delete
        self.delete()

        # Create archive reason record for audit trail
        try:
            # ArchiveReason is defined later in this same file, so we need to handle circular reference
            # Get it from the current module after it's defined
            ArchiveReason = globals().get('ArchiveReason')
            if ArchiveReason:
                content_type = ContentType.objects.get_for_model(self.__class__)
                ArchiveReason.objects.update_or_create(content_type=content_type, object_id=self.pk,
                                                       defaults={"reason": reason, "notes": notes, "user": user})
        except Exception:
            # If ArchiveReason model doesn't exist or other issues,
            # still complete the archive operation
            pass

    def restore(self):
        """Restore soft-deleted object"""
        if not self.archived:
            return

        self.archived = False
        self.deleted_at = None
        self.save()

    def hard_delete(self, using=None, keep_parents=False):
        """
        Hard delete is disabled until retention policy system with
        legal hold support is implemented.

        For gov contractor compliance, permanent deletion cannot occur
        without legal hold checks in place.
        """
        raise NotImplementedError(
            "Hard delete disabled. Use soft delete (archive). "
            "Permanent deletion requires retention policy system with legal hold support."
        )

    def create_new_version(self, **field_updates):
        """Create a new version of this object"""
        if not self.is_current_version:
            raise ValueError("Can only create new versions from current version")

        # Mark current version as not current
        self.is_current_version = False
        self.save()

        # Create new version
        new_data = {}
        for field in self._meta.fields:
            if field.name not in ['id', 'created_at', 'version', 'previous_version', 'is_current_version']:
                new_data[field.name] = getattr(self, field.name)

        # Apply updates
        new_data.update(field_updates)
        new_data.update({'version': self.version + 1, 'previous_version': self, 'is_current_version': True, })

        new_version = self.__class__.objects.create(**new_data)
        return new_version

    def get_version_history(self):
        """Get all versions in chronological order"""
        # Find the root version
        root = self
        while root.previous_version:
            root = root.previous_version

        # Build version chain
        versions = [root]
        current = root
        while True:
            next_version = self.__class__.objects.filter(previous_version=current).first()
            if not next_version:
                break
            versions.append(next_version)
            current = next_version

        return versions

    def get_version(self, version_number):
        """Get a specific version number"""
        versions = self.get_version_history()
        for v in versions:
            if v.version == version_number:
                return v
        return None

    def get_current_version(self):
        """Get the current (latest) version"""
        versions = self.get_version_history()
        return versions[-1] if versions else None

    def __str__(self):
        base_str = super().__str__() if hasattr(super(), '__str__') else str(self.pk)
        return f"{base_str} (v{self.version})"


# Utility functions and enums

def part_doc_upload_path(self, filename):
    """
    Constructs a secure, tenant-isolated file upload path.

    The final path structure is:
        parts_docs/{tenant_slug}/{YYYY-MM-DD}/{uuid}/{file_name}.{ext}

    - tenant_slug: isolates files per tenant (uses 'default' if tenant not set)
    - date: enables time-based organization and backups
    - uuid: prevents path enumeration and filename collisions
    - original filename preserved for user clarity

    Args:
        filename (str): The original name of the uploaded file.

    Returns:
        str: A structured path to store the uploaded file.
    """
    import uuid

    tenant_slug = self.tenant.slug if self.tenant else 'default'
    today = date.today().isoformat()
    unique_id = uuid.uuid4().hex[:12]
    ext = filename.split('.')[-1]

    # Check if file_name already has an extension to avoid double extensions
    file_name = self.file_name
    if file_name.endswith(f'.{ext}'):
        new_filename = file_name
    else:
        new_filename = f"{file_name}.{ext}"

    return os.path.join("parts_docs", tenant_slug, today, unique_id, new_filename)


class ClassificationLevel(models.TextChoices):
    PUBLIC = "public", "Public"
    INTERNAL = "internal", "Internal Use"
    CONFIDENTIAL = "confidential", "Confidential"
    RESTRICTED = "restricted", "Restricted"  # serious impact
    SECRET = "secret", "Secret"  # critical impact


class Companies(SecureModel):
    """
    Represents a company or customer entity associated with deals, parts, and HubSpot CRM integration.

    Stores identifying information and external CRM reference data.
    """

    documents = GenericRelation('Tracker.Documents')
    """Documents attached to this company (agreements, NDAs, certifications, approved vendor docs, etc.)"""

    name = models.CharField(max_length=50)
    """The display name of the company or customer."""

    description = models.TextField()
    """A longer text description providing context or background on the company."""

    hubspot_api_id = models.CharField(max_length=50, null=True, blank=True)
    """The unique identifier for this company in the HubSpot API (used for CRM integration)."""

    class Meta:
        verbose_name_plural = 'Companies'
        verbose_name = 'Company'

    def __str__(self):
        """Returns the company name for display in admin and string contexts."""
        return self.name


class ExternalAPIOrderIdentifier(SecureModel):
    """
    Maps external API pipeline stage IDs to human-readable names.

    Originally designed for HubSpot but kept generic for future integrations.
    When HubSpot API returns cryptic stage IDs (e.g., '123456789'),
    this model provides the human-readable name (e.g., 'Qualification').
    Supports tracking which pipeline each stage belongs to and stage ordering.

    Note: While named generically, this is currently HubSpot-specific.
    For other integrations, consider creating SalesforceStage, NetSuiteStage, etc.
    """

    stage_name = models.CharField(max_length=100)
    """Human-readable stage name (e.g., 'Qualification', 'Closed Won')."""

    API_id = models.CharField(max_length=50)
    """The external system's identifier for the stage (e.g., from HubSpot API)."""

    pipeline_id = models.CharField(max_length=50, null=True, blank=True)
    """Pipeline ID this stage belongs to (e.g., HubSpot pipeline ID)."""

    display_order = models.IntegerField(default=0)
    """Order in which this stage appears in the pipeline (for progress tracking)."""

    last_synced_at = models.DateTimeField(null=True, blank=True)
    """When this stage was last synced from the external system."""

    include_in_progress = models.BooleanField(default=False)
    """Whether to include this gate in customer progress tracking. Set to True for active pipeline gates."""

    class Meta:
        verbose_name = "External API Order Identifier"
        verbose_name_plural = "External API Order Identifiers"
        ordering = ['pipeline_id', 'display_order']
        indexes = [
            models.Index(fields=['pipeline_id', 'display_order']),
            models.Index(fields=['API_id']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'stage_name'], name='externalapiorderid_tenant_stage_uniq'),
        ]

    def __str__(self):
        """Returns a string that clearly represents the stage."""
        return self.stage_name

    def get_customer_display_name(self):
        """
        Get customer-facing display name by removing 'Gate [Number]' prefix.

        Examples:
            'Gate One Quotation' -> 'Quotation'
            'Gate Two Design Review' -> 'Design Review'
            'Gate Five' -> 'Gate Five'
            'Closed Won' -> 'Closed Won'
        """
        import re
        # Remove "Gate [Word] " prefix if present
        cleaned = re.sub(r'^Gate\s+\w+\s+', '', self.stage_name)
        # If nothing was removed or result is empty, return original
        return cleaned if cleaned and cleaned != self.stage_name else self.stage_name


class ArchiveReason(SecureModel):
    """
    Represents the reason and metadata for archiving a model instance.

    This model supports generic relationships to any other model in the system
    and is used to log why and by whom an object was archived. Useful for auditing,
    compliance, and traceability in regulated environments.
    """

    REASON_CHOICES = [("completed", "Completed"), ("user_error", "Archived due to User Error"),
                      ("obsolete", "Obsolete"), ]
    """Standardized choices explaining why the object was archived."""

    reason = models.CharField(max_length=50, choices=REASON_CHOICES)
    """The reason for archiving the object (e.g., completed, error, obsolete)."""

    notes = models.TextField(blank=True)
    """Optional free-text notes describing the archive context."""

    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT)
    """The content type of the related object (generic foreign key base)."""

    object_id = models.CharField(max_length=36)
    """The ID of the related object being archived (CharField for UUID compatibility)."""

    content_object = GenericForeignKey("content_type", "object_id")
    """The actual model instance being archived (resolved via generic relation)."""

    archived_at = models.DateTimeField(auto_now_add=True)
    """Timestamp when the object was archived."""

    user = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True)
    """Optional user responsible for the archive action."""

    class Meta:
        verbose_name = 'Archive Reason'
        verbose_name_plural = 'Archive Reasons'
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'content_type', 'object_id'],
                condition=models.Q(deleted_at__isnull=True),
                name='archivereason_tenant_content_object_unique'
            ),
        ]

    def __str__(self):
        """
        Returns a human-readable string summarizing the archive entry.
        """
        return f"{self.content_object} → {self.reason}"


class User(AbstractUser):
    """
    Extends Django's built-in AbstractUser to associate users with a tenant and company.

    User does NOT inherit SecureModel, so tenant FK is added directly here.
    Includes a timestamp for user registration and optional organizational linkage for access scoping.
    """

    # Tenant scoping - User belongs to a tenant (SaaS customer)
    tenant = models.ForeignKey(
        'Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='users',
        help_text="Tenant this user belongs to"
    )

    class UserType(models.TextChoices):
        INTERNAL = 'internal', 'Internal'  # Staff user of the tenant
        PORTAL = 'portal', 'Portal'  # External customer portal user

    user_type = models.CharField(
        max_length=20,
        choices=UserType.choices,
        default=UserType.INTERNAL,
        help_text="Type of user account"
    )

    first_name = models.CharField(max_length=150, blank=True, null=True)
    """User's first name - nullable to support HubSpot contacts without complete information."""

    last_name = models.CharField(max_length=150, blank=True, null=True)
    """User's last name - nullable to support HubSpot contacts without complete information."""

    date_joined = models.DateTimeField(default=timezone.now)
    """Timestamp for when the user account was created."""

    parent_company = models.ForeignKey(Companies, on_delete=models.SET_NULL, null=True, blank=True, default=None,
                                       related_name='users')
    """
    Optional reference to the company this user belongs to.

    For internal users: their employer (the tenant's company record).
    For portal users: the customer company they represent.
    Must belong to the same tenant as the user.
    """

    # =========================================================================
    # ITAR / Export Control Fields
    # =========================================================================
    citizenship = models.CharField(
        max_length=3,
        blank=True,
        help_text="ISO 3166-1 alpha-3 country code (e.g., USA, GBR, DEU)"
    )
    """User's country of citizenship for export control determination."""

    # Per-regime authorization flags (auditable booleans for compliance queries)
    us_person = models.BooleanField(
        default=False,
        help_text="ITAR 'US Person': US citizen, permanent resident, or protected individual (22 CFR 120.62)"
    )
    """Authorized to access ITAR-controlled technical data and EAR-controlled items."""

    eu_authorized = models.BooleanField(
        default=False,
        help_text="EU Person: Authorized under EU Dual-Use Regulation (EC 428/2009)"
    )
    """Authorized to access EU dual-use controlled items."""

    uk_authorized = models.BooleanField(
        default=False,
        help_text="UK Person: Authorized under UK Export Control Act 2002 / ECJU"
    )
    """Authorized to access UK export-controlled items."""

    export_control_verified = models.BooleanField(
        default=False,
        help_text="Whether export control status has been verified by authorized personnel"
    )
    """Indicates HR/security has verified the user's export control eligibility."""

    export_control_verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When export control status was last verified"
    )
    """Timestamp of last export control verification."""

    export_control_verified_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='export_verifications_performed',
        help_text="User who verified export control status"
    )
    """The authorized user who performed export control verification."""

    export_control_notes = models.TextField(
        blank=True,
        help_text="Notes on special authorizations (TAAs, specific licenses, Canadian exemption, etc.)"
    )
    """For documenting TAAs, license exceptions, AUKUS/Canada exemptions, etc."""

    class Meta:
        verbose_name_plural = 'Users'
        verbose_name = 'User'

    def save(self, *args, **kwargs):
        # Validate parent_company belongs to same tenant
        if self.parent_company_id and self.tenant_id:
            # Avoid circular import by checking via FK
            if hasattr(self.parent_company, 'tenant_id') and self.parent_company.tenant_id != self.tenant_id:
                raise ValueError("User's parent_company must belong to the same tenant")
        super().save(*args, **kwargs)

    def deactivate(self, reason=""):
        """Deactivate user account"""
        self.is_active = False
        self.save()

    def reactivate(self):
        """Reactivate user account"""
        self.is_active = True
        self.save()

    # =========================================================================
    # Tenant-Scoped Group Methods
    # =========================================================================

    def get_tenant_groups(self, tenant=None):
        """
        Get all groups the user belongs to in the specified tenant.

        Args:
            tenant: Tenant instance. Defaults to self.tenant if not specified.

        Returns:
            QuerySet of Group objects
        """
        tenant = tenant or self.tenant
        if not tenant:
            return Group.objects.none()
        return Group.objects.filter(
            tenant_memberships__user=self,
            tenant_memberships__tenant=tenant
        )

    def get_tenant_group_names(self, tenant=None):
        """
        Get set of group names for the user in the specified tenant.

        Useful for caching and permission checks.

        Args:
            tenant: Tenant instance. Defaults to self.tenant if not specified.

        Returns:
            Set of group name strings
        """
        from Tracker.models import UserRole  # Late import to avoid circular reference
        tenant = self._resolve_tenant(tenant)
        if not tenant:
            return set()
        return set(
            UserRole.objects.filter(
                user=self,
                group__tenant=tenant
            ).values_list('group__name', flat=True)
        )

    def has_tenant_group(self, group_name, tenant=None):
        """
        Check if user has a specific group membership in the tenant.

        Args:
            group_name: Name of the group to check
            tenant: Tenant instance. Defaults to self.tenant if not specified.

        Returns:
            Boolean indicating membership
        """
        from Tracker.models import UserRole  # Late import to avoid circular reference
        tenant = self._resolve_tenant(tenant)
        if not tenant:
            return False
        return UserRole.objects.filter(
            user=self,
            group__name=group_name,
            group__tenant=tenant
        ).exists()

    def add_to_tenant_group(self, group_or_name, tenant=None, granted_by=None):
        """
        Add user to a TenantGroup within the specified tenant.

        Args:
            group_or_name: TenantGroup instance or group name string
            tenant: Tenant instance. Defaults to user's resolved tenant if not specified.
            granted_by: User who granted the membership (for audit trail)

        Returns:
            UserRole instance (created or existing)

        Raises:
            ValueError: If tenant cannot be resolved
            TenantGroup.DoesNotExist: If group_name doesn't exist in tenant
        """
        from Tracker.models import TenantGroup, UserRole  # Late import to avoid circular reference
        tenant = self._resolve_tenant(tenant)
        if not tenant:
            raise ValueError("Tenant must be specified for group membership")

        if isinstance(group_or_name, str):
            group = TenantGroup.objects.get(name=group_or_name, tenant=tenant)
        else:
            group = group_or_name

        role, _ = UserRole.objects.get_or_create(
            user=self,
            group=group,
            defaults={'granted_by': granted_by}
        )
        # Clear cached group names if present
        if hasattr(self, '_cached_tenant_group_names'):
            delattr(self, '_cached_tenant_group_names')
        self.clear_permission_cache(tenant)
        return role

    def remove_from_tenant_group(self, group_or_name, tenant=None):
        """
        Remove user from a TenantGroup within the specified tenant.

        Args:
            group_or_name: TenantGroup instance or group name string
            tenant: Tenant instance. Defaults to user's resolved tenant if not specified.

        Returns:
            Number of role assignments deleted (0 or 1)
        """
        from Tracker.models import UserRole  # Late import to avoid circular reference
        tenant = self._resolve_tenant(tenant)
        if not tenant:
            return 0

        if isinstance(group_or_name, str):
            filter_kwargs = {'user': self, 'group__name': group_or_name, 'group__tenant': tenant}
        else:
            filter_kwargs = {'user': self, 'group': group_or_name}

        deleted_count, _ = UserRole.objects.filter(**filter_kwargs).delete()
        # Clear cached group names if present
        if hasattr(self, '_cached_tenant_group_names'):
            delattr(self, '_cached_tenant_group_names')
        self.clear_permission_cache(tenant)
        return deleted_count

    # =========================================================================
    # Convenience Methods (using Groups constants)
    # =========================================================================

    def grant_group(self, group_name, tenant=None, granted_by=None):
        """
        Add user to a TenantGroup, creating the group if it doesn't exist.

        This is the preferred method - uses group name constants and auto-creates groups.

        Args:
            group_name: Group name string (use Groups.PRODUCTION_OPERATOR, etc.)
            tenant: Tenant instance. Defaults to user's resolved tenant if not specified.
            granted_by: User who granted the membership (for audit trail)

        Returns:
            Tuple of (UserRole, created_boolean)

        Example:
            from Tracker.groups import Groups
            user.grant_group(Groups.PRODUCTION_OPERATOR, tenant)
        """
        from Tracker.models import TenantGroup, UserRole

        tenant = self._resolve_tenant(tenant)
        if not tenant:
            raise ValueError("Tenant must be specified for group membership")

        group, _ = TenantGroup.objects.get_or_create(
            name=group_name,
            tenant=tenant,
            defaults={'description': f'Auto-created group: {group_name}', 'is_custom': True}
        )

        role, created = UserRole.objects.get_or_create(
            user=self,
            group=group,
            defaults={'granted_by': granted_by}
        )

        # Clear cached group names if present
        if hasattr(self, '_cached_tenant_group_names'):
            delattr(self, '_cached_tenant_group_names')
        self.clear_permission_cache(tenant)

        return role, created

    def revoke_group(self, group_name, tenant=None):
        """
        Remove user from a group in a tenant.

        Alias for remove_from_tenant_group() with consistent naming.

        Args:
            group_name: Group name string
            tenant: Tenant instance. Defaults to self.tenant if not specified.

        Returns:
            Number of memberships deleted (0 or 1)
        """
        return self.remove_from_tenant_group(group_name, tenant)

    def has_group(self, group_names, tenant=None):
        """
        Check if user has any of the specified TenantGroups in a tenant.

        Supports checking a single group or multiple groups at once.

        Args:
            group_names: Single group name string, or set/list of group names
            tenant: Tenant instance. Defaults to user's resolved tenant if not specified.

        Returns:
            Boolean indicating membership in any of the specified groups

        Example:
            from Tracker.groups import Groups

            # Single group
            user.has_group(Groups.PRODUCTION_OPERATOR)

            # Multiple groups (returns True if user has ANY of them)
            user.has_group(Groups.INTERNAL_STAFF)  # INTERNAL_STAFF is a set
        """
        from Tracker.models import UserRole

        tenant = self._resolve_tenant(tenant)
        if not tenant:
            return False

        # Normalize to set
        if isinstance(group_names, str):
            group_names = {group_names}
        elif not isinstance(group_names, set):
            group_names = set(group_names)

        return UserRole.objects.filter(
            user=self,
            group__tenant=tenant,
            group__name__in=group_names
        ).exists()

    def is_internal_staff(self, tenant=None):
        """
        Check if user has any internal staff group in the tenant.

        Internal staff groups: Admin, QA_Manager, QA_Inspector,
        Production_Manager, Production_Operator, Document_Controller

        Args:
            tenant: Tenant instance. Defaults to self.tenant if not specified.

        Returns:
            Boolean
        """
        from Tracker.groups import Groups
        return self.has_group(Groups.INTERNAL_STAFF, tenant)

    def is_customer(self, tenant=None):
        """
        Check if user is a customer (external) in the tenant.

        Args:
            tenant: Tenant instance. Defaults to self.tenant if not specified.

        Returns:
            Boolean
        """
        from Tracker.groups import Groups
        return self.has_group(Groups.CUSTOMER, tenant)

    # =========================================================================
    # SIMPLE ROLE-BASED ACCESS
    # =========================================================================

    def get_user_roles(self, tenant=None):
        """Get all UserRole assignments for this user in a tenant."""
        tenant = tenant or self.tenant
        if not tenant:
            return UserRole.objects.none()

        return UserRole.objects.filter(
            user=self,
            group__tenant=tenant
        ).select_related('group', 'facility', 'company')

    def has_any_role(self, tenant=None):
        """Check if user has any role in a tenant."""
        tenant = tenant or self.tenant
        if not tenant:
            return False
        return self.get_user_roles(tenant).exists()


    # -------------------------------------------------------------------------
    # Permission checking methods (action permissions via TenantGroup.permissions)
    # -------------------------------------------------------------------------

    def get_tenant_permissions(self, tenant=None):
        """
        Get all permission codenames for user in tenant (cached).

        Returns a set of permission codenames like {'add_orders', 'view_parts', ...}
        """
        from django.core.cache import cache
        from django.contrib.auth.models import Permission

        tenant = self._resolve_tenant(tenant)
        if not tenant:
            return set()

        cache_key = f'user_{self.id}_tenant_{tenant.id}_perms'
        perms = cache.get(cache_key)

        if perms is None:
            if self.is_superuser:
                # Superuser has all permissions
                perms = set(Permission.objects.values_list('codename', flat=True))
            else:
                # Get permissions from all groups user belongs to in this tenant
                perms = set(Permission.objects.filter(
                    tenant_groups__role_assignments__user=self,
                    tenant_groups__tenant=tenant
                ).values_list('codename', flat=True))

            cache.set(cache_key, perms, timeout=300)  # 5 min cache

        return perms

    def _resolve_tenant(self, tenant=None):
        """
        Resolve which tenant to use for permission checks.

        Resolution order:
        1. Explicit tenant parameter (for programmatic checks)
        2. _current_tenant (set by TenantMiddleware for current request)
        3. self.tenant (user's home tenant)

        This enables both:
        - Dedicated mode: middleware sets default tenant on every request
        - SaaS mode: middleware resolves tenant from header/subdomain
        """
        if tenant:
            return tenant
        if hasattr(self, '_current_tenant') and self._current_tenant:
            return self._current_tenant
        return self.tenant

    def has_tenant_perm(self, perm, tenant=None):
        """
        Check if user has specific permission in tenant.

        Args:
            perm: Permission codename (e.g., 'add_orders', 'approve_capa')
            tenant: Tenant to check. Auto-resolves if not provided:
                    1. Current request's tenant (from middleware)
                    2. User's home tenant

        Returns:
            bool: True if user has the permission
        """
        if self.is_superuser:
            return True

        tenant = self._resolve_tenant(tenant)
        if not tenant:
            return False

        return perm in self.get_tenant_permissions(tenant)

    def has_tenant_perms(self, perms, tenant=None):
        """
        Check if user has all specified permissions.

        Args:
            perms: Iterable of permission codenames
            tenant: Tenant to check. Auto-resolves if not provided.

        Returns:
            bool: True if user has ALL the permissions
        """
        if self.is_superuser:
            return True

        tenant = self._resolve_tenant(tenant)
        if not tenant:
            return False

        user_perms = self.get_tenant_permissions(tenant)
        return all(perm in user_perms for perm in perms)

    def clear_permission_cache(self, tenant=None):
        """
        Clear cached permissions for this user.

        Call this when user's roles or group permissions change.
        """
        from django.core.cache import cache

        tenant = tenant or self.tenant
        if tenant:
            cache.delete(f'user_{self.id}_tenant_{tenant.id}_perms')

    @classmethod
    def create_tenant_user(cls, username, tenant, group=None, email=None, password=None, **kwargs):
        """
        Create a user with tenant and optional group in one call.

        Convenience factory method for tests and user provisioning.

        Args:
            username: Username for the new user
            tenant: Tenant instance to assign
            group: Optional group name to add user to (e.g., Groups.PRODUCTION_OPERATOR)
            email: Optional email (defaults to username@example.com)
            password: Optional password (defaults to 'testpass')
            **kwargs: Additional fields (us_person, first_name, etc.)

        Returns:
            User instance

        Example:
            from Tracker.groups import Groups

            user = User.create_tenant_user(
                'operator1',
                tenant=acme,
                group=Groups.PRODUCTION_OPERATOR,
                us_person=True
            )
        """
        email = email or f"{username}@example.com"
        password = password or 'testpass'

        user = cls.objects.create_user(
            username=username,
            email=email,
            password=password,
            tenant=tenant,
            **kwargs
        )

        if group:
            user.grant_group(group, tenant)

        return user

    def __str__(self):
        """Returns a readable representation of the user with username and full name."""
        return f"{self.username}: {self.first_name} {self.last_name}"


class UserInvitation(models.Model):
    """
    Tracks invitation tokens for user account activation.

    Allows staff to invite customers to create accounts with secure, time-limited tokens.
    Maintains history of invitations sent, accepted, and expired.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='invitations')
    """The user being invited."""

    token = models.CharField(max_length=64, unique=True, db_index=True)
    """Secure random token for invitation link."""

    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='invitations_sent')
    """Staff member who sent the invitation."""

    sent_at = models.DateTimeField(auto_now_add=True)
    """Timestamp when invitation was sent."""

    expires_at = models.DateTimeField()
    """Expiration timestamp for the invitation token."""

    accepted_at = models.DateTimeField(null=True, blank=True)
    """Timestamp when user accepted invitation and completed signup."""

    accepted_ip_address = models.GenericIPAddressField(null=True, blank=True)
    """IP address from which the invitation was accepted."""

    accepted_user_agent = models.TextField(null=True, blank=True)
    """User agent string from the browser used to accept invitation."""

    class Meta:
        verbose_name = 'User Invitation'
        verbose_name_plural = 'User Invitations'
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user', '-sent_at']),
        ]

    def __str__(self):
        status = "accepted" if self.accepted_at else ("expired" if self.is_expired() else "pending")
        return f"Invitation for {self.user.email} ({status})"

    def is_expired(self):
        """Check if invitation has expired."""
        return timezone.now() > self.expires_at and not self.accepted_at

    def is_valid(self):
        """Check if invitation is still valid (not expired and not yet accepted)."""
        return not self.accepted_at and not self.is_expired()

    @classmethod
    def generate_token(cls):
        """Generate a secure random token."""
        import secrets
        return secrets.token_urlsafe(48)


class TenantGroupMembership(models.Model):
    """
    Tenant-scoped group membership for users.

    This model enables users to have different group memberships in different tenants,
    while keeping Django's auth.Group table unchanged. A user can be:
    - Admin in Tenant A
    - Operator in Tenant B
    - Manager AND Operator in Tenant C (multiple groups per tenant supported)

    The TenantPermissionBackend uses this table to resolve permissions based on the
    current tenant context.
    """

    tenant = models.ForeignKey(
        'Tenant',
        on_delete=models.CASCADE,
        related_name='group_memberships'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tenant_group_memberships'
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='tenant_memberships'
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    granted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='group_grants_made'
    )

    class Meta:
        unique_together = [('tenant', 'user', 'group')]
        verbose_name = 'Tenant Group Membership'
        verbose_name_plural = 'Tenant Group Memberships'
        indexes = [
            models.Index(fields=['tenant', 'user']),
            models.Index(fields=['user', 'group']),
        ]

    def __str__(self):
        return f"{self.user.username} -> {self.group.name} @ {self.tenant.slug}"

    @classmethod
    def get_user_groups(cls, user, tenant):
        """Get all groups a user belongs to in a specific tenant."""
        return Group.objects.filter(
            tenant_memberships__user=user,
            tenant_memberships__tenant=tenant
        )

    @classmethod
    def user_has_group(cls, user, group_name, tenant):
        """Check if user has a specific group membership in tenant."""
        return cls.objects.filter(
            user=user,
            group__name=group_name,
            tenant=tenant
        ).exists()


class NotificationTask(models.Model):
    """
    Unified notification task supporting both recurring (fixed interval)
    and escalating (deadline-based) notifications.

    Supports multiple channels (email, in-app, SMS, etc.) via simple channel_type field.

    Examples:
    - Weekly order reports: interval_type='fixed', day_of_week=4, time='15:00', interval_weeks=1
    - CAPA reminders: interval_type='deadline_based', deadline=due_date, escalation_tiers=[...]
    """

    # Notification types (hardcoded for now, can move to separate table later if needed)
    NOTIFICATION_TYPES = [
        ('WEEKLY_REPORT', 'Weekly Order Report'),
        ('CAPA_REMINDER', 'CAPA Reminder'),
        ('APPROVAL_REQUEST', 'Approval Request'),
        ('APPROVAL_DECISION', 'Approval Decision'),
        ('APPROVAL_ESCALATION', 'Approval Escalation'),
    ]

    # Interval types
    INTERVAL_TYPES = [
        ('fixed', 'Fixed Interval'),
        ('deadline_based', 'Deadline Based'),
    ]

    # Notification status
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    # Channel types (email only for now, but structured for extension)
    CHANNEL_TYPES = [
        ('email', 'Email'),
        ('in_app', 'In-App Notification'),
        ('sms', 'SMS'),
    ]

    # Core fields
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notification_tasks')
    channel_type = models.CharField(max_length=20, choices=CHANNEL_TYPES, default='email')
    interval_type = models.CharField(max_length=20, choices=INTERVAL_TYPES)

    # Fixed interval fields (for recurring notifications)
    day_of_week = models.IntegerField(null=True, blank=True, help_text="0=Monday, 6=Sunday")
    time = models.TimeField(null=True, blank=True, help_text="Time in UTC")
    interval_weeks = models.IntegerField(null=True, blank=True, help_text="Number of weeks between sends")

    # Deadline-based fields (for escalating notifications)
    deadline = models.DateTimeField(null=True, blank=True, help_text="Deadline for escalation calculation")
    escalation_tiers = models.JSONField(
        null=True,
        blank=True,
        help_text="List of [threshold_days, interval_days] tuples. Example: [[28, 28], [14, 7], [0, 3.5], [-999, 1]]"
    )

    # State tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    attempt_count = models.IntegerField(default=0)
    last_sent_at = models.DateTimeField(null=True, blank=True)
    next_send_at = models.DateTimeField(db_index=True, help_text="When this notification should be sent (UTC)")
    max_attempts = models.IntegerField(null=True, blank=True, help_text="Max sends before stopping. Null = infinite")

    # Related object (optional, for context)
    related_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    related_object_id = models.CharField(max_length=36, null=True, blank=True)
    related_object = GenericForeignKey('related_content_type', 'related_object_id')

    # Timestamps - stored as UTC
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Notification Task'
        verbose_name_plural = 'Notification Tasks'
        indexes = [
            models.Index(fields=['recipient', 'notification_type', 'channel_type']),
            models.Index(fields=['status', 'next_send_at']),
            models.Index(fields=['related_content_type', 'related_object_id']),
        ]
        ordering = ['next_send_at']

    def __str__(self):
        return f"{self.get_notification_type_display()} to {self.recipient.email} via {self.channel_type}"

    def calculate_next_send(self):
        """
        Calculate when this notification should be sent next.
        Returns a datetime object.
        """
        from datetime import timedelta

        base_time = self.last_sent_at or self.created_at

        if self.interval_type == 'fixed':
            # Fixed interval with specific day/time
            if self.last_sent_at:
                # Add interval_weeks to last send
                next_date = self.last_sent_at.date() + timedelta(weeks=self.interval_weeks)
            else:
                # First occurrence - find next target day
                now = timezone.now()
                days_ahead = (self.day_of_week - now.weekday()) % 7
                if days_ahead == 0 and now.time() > self.time:
                    days_ahead = 7
                next_date = (now + timedelta(days=days_ahead)).date()

            # Combine date with time
            from datetime import datetime
            import pytz
            next_dt = datetime.combine(next_date, self.time)
            # Make timezone aware in UTC
            return timezone.make_aware(next_dt, pytz.UTC)

        elif self.interval_type == 'deadline_based':
            # Deadline-based: use escalation tiers
            interval_days = self._get_current_interval()
            return base_time + timedelta(days=interval_days)

        else:
            raise ValueError(f"Unknown interval_type: {self.interval_type}")

    def _get_current_interval(self):
        """Get the interval (in days) until next send based on escalation tier."""
        if self.interval_type == 'fixed':
            return self.interval_weeks * 7

        elif self.interval_type == 'deadline_based':
            tier = self._find_matching_tier()
            return tier[1] if tier else 1  # Default to 1 day if no tier found

        else:
            raise ValueError(f"Unknown interval_type: {self.interval_type}")

    def _find_matching_tier(self):
        """Find the matching escalation tier based on days until deadline."""
        if self.interval_type != 'deadline_based' or not self.escalation_tiers or not self.deadline:
            return None

        base_time = self.last_sent_at or self.created_at
        days_until = (self.deadline - base_time).days

        # Find first matching tier
        for tier in self.escalation_tiers:
            if days_until > tier[0]:
                return tier

        # Fallback to last tier
        return self.escalation_tiers[-1] if self.escalation_tiers else None

    def should_send(self):
        """Check if this notification should be sent now."""
        if self.status != 'pending':
            return False

        if timezone.now() < self.next_send_at:
            return False

        return True

    def mark_sent(self, success=True, sent_at=None):
        """Update state after send attempt."""
        self.attempt_count += 1
        self.last_sent_at = sent_at or self.next_send_at

        if success:
            self.status = 'sent'

            # Check if we should continue sending
            if self.max_attempts is None or self.attempt_count < self.max_attempts:
                self.status = 'pending'
                self.next_send_at = self.calculate_next_send()
        else:
            self.status = 'failed'

        self.save()


class Approval_Type(models.TextChoices):
    DOCUMENT_RELEASE = 'DOCUMENT_RELEASE', 'Document Release'
    CAPA_CRITICAL = 'CAPA_CRITICAL', 'CAPA Critical'
    CAPA_MAJOR = 'CAPA_MAJOR', 'CAPA Major'
    ECO = 'ECO', 'Engineering Change Order'
    TRAINING_CERT = 'TRAINING_CERT', 'Training Certification'
    PROCESS_APPROVAL = 'PROCESS_APPROVAL', 'Process Approval'

class Approval_Status_Type(models.TextChoices):
    NOT_REQUIRED = 'NOT_REQUIRED', 'Not Required'
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    CANCELLED = 'CANCELLED', 'Cancelled'

class ApprovalFlows(models.TextChoices):
    ALL_REQUIRED = 'ALL_REQUIRED', 'All Required'
    THRESHOLD = 'THRESHOLD', 'Threshold'
    ANY = 'ANY', 'Any'

class SequenceTypes(models.TextChoices):
    PARALLEL = 'PARALLEL', 'Parallel'
    SEQUENTIAL = 'SEQUENTIAL', 'Sequential'

class ApprovalDelegation(models.TextChoices):
    OPTIONAL = 'OPTIONAL', 'Optional'
    DISABLED = 'DISABLED', 'Disabled'


class ApproverAssignmentSource(models.TextChoices):
    """How an approver was assigned to an approval request"""
    TEMPLATE_DEFAULT = 'TEMPLATE_DEFAULT', 'Template Default'
    TEMPLATE_GROUP = 'TEMPLATE_GROUP', 'Template Group Auto-Assign'
    MANUAL = 'MANUAL', 'Manual Assignment'
    DELEGATION = 'DELEGATION', 'Delegated'
    ESCALATION = 'ESCALATION', 'Escalation'


class ApproverAssignment(models.Model):
    """
    Through model for ApprovalRequest approvers.

    Tracks metadata about how/when each approver was assigned, enabling:
    - Audit trail for approver assignments
    - Sequential approval ordering
    - Tracking auto-assigned vs manual assignments
    - Reminders and escalation targeting
    """
    approval_request = models.ForeignKey(
        'ApprovalRequest',
        on_delete=models.CASCADE,
        related_name='approver_assignments'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='approval_assignments'
    )

    # Assignment metadata
    is_required = models.BooleanField(
        default=True,
        help_text="True for required approvers, False for optional/FYI"
    )
    sequence_order = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Order in sequential approval flow (null for parallel)"
    )
    assignment_source = models.CharField(
        max_length=20,
        choices=ApproverAssignmentSource.choices,
        default=ApproverAssignmentSource.MANUAL
    )

    # Audit fields
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approver_assignments_made',
        help_text="User who made this assignment (null for auto-assignments)"
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    # For delegations
    delegated_from = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='delegations',
        help_text="Original assignment if this was delegated"
    )

    # Notification tracking
    notified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When approver was notified of this assignment"
    )
    reminder_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of reminder notifications sent"
    )
    last_reminder_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'tracker_approver_assignment'
        ordering = ['sequence_order', 'assigned_at']
        constraints = [
            models.UniqueConstraint(
                fields=['approval_request', 'user'],
                name='approverassignment_request_user_uniq'
            ),
        ]
        indexes = [
            models.Index(fields=['approval_request', 'is_required']),
            models.Index(fields=['user', 'assigned_at']),
        ]

    def __str__(self):
        req_str = "Required" if self.is_required else "Optional"
        return f"{self.user.get_full_name()} ({req_str}) - {self.approval_request.approval_number}"


class GroupApproverAssignment(models.Model):
    """
    Through model for ApprovalRequest group assignments.

    When a group is assigned, any member can respond. Tracks assignment metadata.
    """
    approval_request = models.ForeignKey(
        'ApprovalRequest',
        on_delete=models.CASCADE,
        related_name='group_assignments'
    )
    group = models.ForeignKey(
        'TenantGroup',
        on_delete=models.CASCADE,
        related_name='approval_assignments'
    )

    # Assignment metadata
    sequence_order = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Order in sequential approval flow (null for parallel)"
    )
    assignment_source = models.CharField(
        max_length=20,
        choices=ApproverAssignmentSource.choices,
        default=ApproverAssignmentSource.TEMPLATE_GROUP
    )

    # Audit fields
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='group_assignments_made'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tracker_group_approver_assignment'
        ordering = ['sequence_order', 'assigned_at']
        constraints = [
            models.UniqueConstraint(
                fields=['approval_request', 'group'],
                name='groupapproverassignment_request_group_uniq'
            ),
        ]

    def __str__(self):
        return f"{self.group.name} - {self.approval_request.approval_number}"


class ApprovalRequest(SecureModel):
    """
    Represents a request for approval on a document, CAPA, or other entity.

    Supports various approval flows including ALL_REQUIRED, THRESHOLD, and ANY.
    Tracks approvers, responses, escalation, and completion status.
    """

    documents = GenericRelation('Tracker.Documents')
    """Supporting documentation submitted with approval requests, sign-off evidence, etc."""

    approval_number = models.CharField(max_length=20)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.CharField(max_length=36, null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    approval_type = models.CharField(max_length=50, choices=Approval_Type.choices)
    status = models.CharField(max_length=20, choices=Approval_Status_Type.choices, default=Approval_Status_Type.PENDING)

    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='approval_requests_made')
    requested_at = models.DateTimeField(auto_now_add=True)

    # Approvers with through model for audit trail and sequencing
    approvers = models.ManyToManyField(
        User,
        through='ApproverAssignment',
        through_fields=('approval_request', 'user'),
        related_name='approval_requests_assigned',
        blank=True
    )
    approver_groups = models.ManyToManyField(
        'TenantGroup',
        through='GroupApproverAssignment',
        related_name='approval_requests_group_assigned',
        blank=True
    )

    flow_type = models.CharField(max_length=20, choices=ApprovalFlows.choices, default=ApprovalFlows.ALL_REQUIRED)
    sequence_type = models.CharField(max_length=20, choices=SequenceTypes.choices, default=SequenceTypes.PARALLEL)
    threshold = models.IntegerField(null=True, blank=True)
    delegation_policy = models.CharField(max_length=20, choices=ApprovalDelegation.choices, default=ApprovalDelegation.DISABLED)
    escalation_day = models.DateField(null=True, blank=True, help_text="Specific date when escalation should trigger")
    escalate_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='escalated_approvals')

    due_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    reason = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-requested_at']
        verbose_name = 'Approval Request'
        verbose_name_plural = 'Approval Requests'
        permissions = [
            ("respond_to_approval", "Can respond to approval requests"),
        ]
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'approval_number'], name='approvalrequest_tenant_number_uniq'),
        ]
        indexes = [
            models.Index(fields=['status', 'due_date'], name='approvalrequest_status_due_idx'),
        ]

    def __str__(self):
        return f"{self.approval_number} - {self.get_approval_type_display()}"

    # =========================================================================
    # BACKWARD-COMPATIBLE APPROVER ACCESSORS
    # =========================================================================
    # These properties provide the same interface as the old ManyToMany fields
    # while using the new through model for proper audit trail.

    @property
    def required_approvers(self):
        """
        Backward-compatible accessor for required approvers.
        Returns a queryset of Users who are required approvers.
        """
        return User.objects.filter(
            approval_assignments__approval_request=self,
            approval_assignments__is_required=True
        )

    @property
    def optional_approvers(self):
        """
        Backward-compatible accessor for optional approvers.
        Returns a queryset of Users who are optional approvers.
        """
        return User.objects.filter(
            approval_assignments__approval_request=self,
            approval_assignments__is_required=False
        )

    def add_approver(self, user, is_required=True, sequence_order=None,
                     assignment_source=None, assigned_by=None):
        """
        Add an approver with full audit trail.

        Args:
            user: User to add as approver
            is_required: True for required, False for optional
            sequence_order: Order for sequential approvals (None for parallel)
            assignment_source: How user was assigned (defaults based on context)
            assigned_by: User who made this assignment (None for auto-assignments)
        """
        if assignment_source is None:
            assignment_source = ApproverAssignmentSource.MANUAL

        return ApproverAssignment.objects.get_or_create(
            approval_request=self,
            user=user,
            defaults={
                'is_required': is_required,
                'sequence_order': sequence_order,
                'assignment_source': assignment_source,
                'assigned_by': assigned_by,
            }
        )

    def remove_approver(self, user):
        """Remove an approver from this request."""
        return ApproverAssignment.objects.filter(
            approval_request=self,
            user=user
        ).delete()

    def set_approvers(self, users, is_required=True, assignment_source=None, assigned_by=None):
        """
        Replace all approvers of a given type with new list.

        Args:
            users: Iterable of Users
            is_required: True for required approvers, False for optional
            assignment_source: How users were assigned
            assigned_by: User who made this assignment
        """
        if assignment_source is None:
            assignment_source = ApproverAssignmentSource.MANUAL

        # Remove existing approvers of this type
        ApproverAssignment.objects.filter(
            approval_request=self,
            is_required=is_required
        ).delete()

        # Add new approvers
        for i, user in enumerate(users):
            ApproverAssignment.objects.create(
                approval_request=self,
                user=user,
                is_required=is_required,
                sequence_order=i if self.sequence_type == SequenceTypes.SEQUENTIAL else None,
                assignment_source=assignment_source,
                assigned_by=assigned_by,
            )

    @classmethod
    def generate_approval_number(cls, tenant=None):
        """Auto-generate approval number: APR-YYYY-####

        Uses SELECT FOR UPDATE to prevent race conditions under concurrent load.
        """
        from datetime import datetime
        from Tracker.utils.sequences import generate_next_sequence

        year = datetime.now().year
        prefix = f"APR-{year}-"

        return generate_next_sequence(
            queryset=cls.objects,
            number_field='approval_number',
            prefix=prefix,
            padding=4,
            tenant=tenant
        )

    @classmethod
    def create_from_template(cls, content_object, template, requested_by, reason=None):
        """Create approval request from template with auto-assignment"""
        from datetime import timedelta
        from django.utils import timezone

        # Get tenant from content_object or requested_by
        tenant = getattr(content_object, 'tenant', None) or getattr(requested_by, 'tenant', None)

        approval = cls.objects.create(
            approval_number=cls.generate_approval_number(tenant),
            tenant=tenant,
            content_object=content_object,
            approval_type=template.approval_type,
            requested_by=requested_by,
            reason=reason,
            flow_type=template.approval_flow_type,
            sequence_type=template.approval_sequence,
            threshold=template.default_threshold if template.approval_flow_type == ApprovalFlows.THRESHOLD else None,
            delegation_policy=template.delegation_policy,
            escalation_day=timezone.now().date() + timedelta(days=template.escalation_days) if template.escalation_days else None,
            escalate_to=template.escalate_to,
            due_date=timezone.now() + timedelta(days=template.default_due_days)
        )

        # Assign approvers from template with audit trail
        approval.set_approvers(
            template.default_approvers.all(),
            is_required=True,
            assignment_source=ApproverAssignmentSource.TEMPLATE_DEFAULT
        )

        # Assign groups from template
        for group in template.default_groups.all():
            GroupApproverAssignment.objects.create(
                approval_request=approval,
                group=group,
                assignment_source=ApproverAssignmentSource.TEMPLATE_GROUP
            )

        # Auto-assign by role (via TenantGroup/UserRole)
        if template.auto_assign_by_role:
            role_users = User.objects.filter(
                user_roles__group__name=template.auto_assign_by_role,
                user_roles__group__tenant=tenant
            )
            for user in role_users:
                approval.add_approver(
                    user,
                    is_required=True,
                    assignment_source=ApproverAssignmentSource.TEMPLATE_GROUP
                )

        # Notify approvers now that approval is fully configured
        # Note: We do this manually here rather than via signal because signals fire
        # before M2M relationships are established, causing approvers to be empty
        approval.notify_approvers()

        return approval

    def check_approval_status(self):
        """Determine if approval is complete

        Returns: (status: str, pending_approvers: list[User])
        """
        responses = self.responses.all()

        # Any rejection kills the request
        if responses.filter(decision=ApprovalDecision.REJECTED).exists():
            return (Approval_Status_Type.REJECTED, [])

        approvals = responses.filter(decision=ApprovalDecision.APPROVED)

        # SEQUENTIAL: Approvers must approve in order
        if self.sequence_type == SequenceTypes.SEQUENTIAL:
            return self._check_sequential_status(approvals)

        # ANY: one approval is enough
        if self.flow_type == ApprovalFlows.ANY:
            if approvals.exists():
                return (Approval_Status_Type.APPROVED, [])
            return (Approval_Status_Type.PENDING, list(self.get_pending_approvers()))

        # THRESHOLD: N approvals required
        if self.flow_type == ApprovalFlows.THRESHOLD:
            threshold = self.threshold or 0
            if threshold > 0 and approvals.count() >= threshold:
                return (Approval_Status_Type.APPROVED, [])
            return (Approval_Status_Type.PENDING, list(self.get_pending_approvers()))

        # Default: ALL_REQUIRED (parallel)
        approved_by = set(approvals.values_list('approver_id', flat=True))
        required = set(self.required_approvers.values_list('id', flat=True))
        pending_ids = required - approved_by

        if not pending_ids:
            return (Approval_Status_Type.APPROVED, [])

        pending = User.objects.filter(id__in=pending_ids)
        return (Approval_Status_Type.PENDING, list(pending))

    def _check_sequential_status(self, approvals):
        """Check status for sequential approval flow.

        In sequential mode, approvers must approve in order (by sequence_order).
        Only the next pending approver can submit a response.
        """
        # Get ordered list of required approver assignments
        assignments = self.approver_assignments.filter(
            is_required=True
        ).order_by('sequence_order', 'assigned_at')

        approved_by = set(approvals.values_list('approver_id', flat=True))

        # Find first approver who hasn't approved
        for assignment in assignments:
            if assignment.user_id not in approved_by:
                # This is the next pending approver
                return (Approval_Status_Type.PENDING, [assignment.user])

        # All approved
        return (Approval_Status_Type.APPROVED, [])

    def update_status(self):
        """Update approval status and cascade to content object"""
        from django.utils import timezone

        new_status, pending = self.check_approval_status()

        if new_status != self.status:
            self.status = new_status

            if new_status in [Approval_Status_Type.APPROVED, Approval_Status_Type.REJECTED]:
                self.completed_at = timezone.now()

            self.save()

            # Cascade to content object
            self.trigger_content_object_update(new_status)

    def trigger_content_object_update(self, status):
        """Update the object being approved based on approval outcome"""
        from django.utils import timezone
        obj = self.content_object

        if not obj:
            return

        # Document approval
        if hasattr(obj, 'status') and hasattr(obj, 'approved_by'):
            if status == Approval_Status_Type.APPROVED:
                obj.status = 'APPROVED'
                obj.approved_by = self.get_primary_approver()
                obj.approved_at = timezone.now()
                obj.save()

    def get_primary_approver(self):
        """Get first approver who approved"""
        response = self.responses.filter(decision=ApprovalDecision.APPROVED).first()
        return response.approver if response else None

    def get_pending_approvers(self):
        """Get list of users who haven't responded yet.

        For SEQUENTIAL approval, returns only the next approver in sequence.
        For PARALLEL approval, returns all pending approvers.
        """
        responded = set(self.responses.values_list('approver_id', flat=True))

        # Get required approver assignments ordered by sequence
        assignments = self.approver_assignments.filter(
            is_required=True
        ).exclude(
            user_id__in=responded
        ).select_related('user').order_by('sequence_order', 'assigned_at')

        if self.sequence_type == SequenceTypes.SEQUENTIAL:
            # Return only the first (next) pending approver
            first_assignment = assignments.first()
            return [first_assignment.user] if first_assignment else []

        return [a.user for a in assignments]

    def is_overdue(self):
        """Check if approval is past due date"""
        from django.utils import timezone
        if self.status in [Approval_Status_Type.APPROVED, Approval_Status_Type.REJECTED, Approval_Status_Type.CANCELLED]:
            return False
        return self.due_date and timezone.now() > self.due_date

    def can_approve(self, user):
        """Check if user is authorized to approve"""
        # Check if user is assigned as approver (required or optional)
        if self.approver_assignments.filter(user=user).exists():
            return True

        # Check if user is in any assigned approver group (tenant-scoped)
        user_groups = user.get_tenant_groups() if hasattr(user, 'get_tenant_groups') else []
        if self.group_assignments.filter(group_id__in=[g.id for g in user_groups]).exists():
            return True

        return False

    def get_template(self):
        """Get the approval template used for this request"""
        try:
            return ApprovalTemplate.objects.get(
                approval_type=self.approval_type,
                tenant=self.tenant
            )
        except ApprovalTemplate.DoesNotExist:
            return None

    def save(self, *args, **kwargs):
        """Track status changes for signal detection."""
        if self.pk:
            try:
                old = ApprovalRequest.objects.get(pk=self.pk)
                self._old_status = old.status
            except ApprovalRequest.DoesNotExist:
                pass
        super().save(*args, **kwargs)

    def notify_approvers(self):
        """Send notifications to all pending approvers"""
        from django.contrib.contenttypes.models import ContentType
        from django.utils import timezone

        for approver in self.get_pending_approvers():
            NotificationTask.objects.create(
                notification_type='APPROVAL_REQUEST',
                recipient=approver,
                channel_type='email',
                interval_type='fixed',
                related_content_type=ContentType.objects.get_for_model(self),
                related_object_id=self.id,
                next_send_at=timezone.now()
            )

    def notify_status_change(self, new_status):
        """Notify requester of approval decision"""
        from django.contrib.contenttypes.models import ContentType
        from django.utils import timezone

        NotificationTask.objects.create(
            notification_type='APPROVAL_DECISION',
            recipient=self.requested_by,
            channel_type='email',
            interval_type='fixed',
            related_content_type=ContentType.objects.get_for_model(self),
            related_object_id=self.id,
            next_send_at=timezone.now()
        )

    def escalate(self):
        """Escalate overdue approval using snapshot configuration.

        Called by scheduled task for overdue approvals.
        Creates escalation notification for escalate_to user.
        """
        from django.contrib.contenttypes.models import ContentType
        from django.utils import timezone

        if self.escalate_to:
            NotificationTask.objects.create(
                notification_type='APPROVAL_ESCALATION',
                recipient=self.escalate_to,
                channel_type='email',
                interval_type='fixed',
                related_content_type=ContentType.objects.get_for_model(self),
                related_object_id=self.id,
                next_send_at=timezone.now()
            )


class ApprovalDecision(models.TextChoices):
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    DELEGATED = 'DELEGATED', 'Delegated'


class VerificationMethod(models.TextChoices):
    PASSWORD = 'PASSWORD', 'Password'
    SSO = 'SSO', 'SSO'
    NONE = 'NONE', 'None'


class ApprovalResponse(SecureModel):

    approval_request = models.ForeignKey(ApprovalRequest, on_delete=models.CASCADE, related_name='responses')
    approver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='approval_responses')

    decision = models.CharField(max_length=20, choices=ApprovalDecision.choices)
    decision_date = models.DateTimeField(auto_now_add=True)
    comments = models.TextField(null=True, blank=True)

    # Delegation
    delegated_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='delegated_approvals')

    # Signature capture
    signature_data = models.TextField(null=True, blank=True, help_text="Base64 encoded signature image (PNG)")
    signature_meaning = models.CharField(max_length=200, null=True, blank=True, help_text="e.g., 'I approve as QA Manager'")
    verified_at = models.DateTimeField(null=True, blank=True, help_text="When identity verification succeeded")
    verification_method = models.CharField(max_length=20, choices=VerificationMethod.choices, default=VerificationMethod.NONE)

    # Audit trail
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    self_approved = models.BooleanField(default=False, help_text="True if requester approved their own request")

    class Meta:
        ordering = ['-decision_date']
        verbose_name = 'Approval Response'
        verbose_name_plural = 'Approval Responses'
        unique_together = [['approval_request', 'approver']]

    def __str__(self):
        return f"{self.approver.get_full_name()} - {self.get_decision_display()} - {self.approval_request.approval_number}"

    @classmethod
    def submit_response(cls, approval_request, approver, decision, comments=None, signature_data=None, signature_meaning=None, password=None, ip_address=None):
        """Record approval decision with signature capture and identity verification"""
        from django.core.exceptions import PermissionDenied, ValidationError
        from django.utils import timezone

        # Validate authorization
        if not approval_request.can_approve(approver):
            raise PermissionDenied("You are not authorized to approve this request")

        # Check for duplicate response
        if cls.objects.filter(approval_request=approval_request, approver=approver).exists():
            raise ValidationError("You have already responded to this approval")

        # Self-approval check
        is_self_approval = (approval_request.requested_by == approver)
        if is_self_approval:
            template = approval_request.get_template()
            if not template or not template.allow_self_approval:
                raise ValidationError("Self-approval is not permitted for this approval type")
            if not comments or len(comments.strip()) < 10:
                raise ValidationError("Justification required for self-approval (minimum 10 characters)")

        # Identity verification: Re-authenticate password
        verification_method = VerificationMethod.NONE
        verified_at = None
        if password:
            if not approver.check_password(password):
                raise ValidationError("Password incorrect. Identity verification failed.")
            verification_method = VerificationMethod.PASSWORD
            verified_at = timezone.now()

        # Record response
        response = cls.objects.create(
            approval_request=approval_request,
            approver=approver,
            decision=decision,
            comments=comments,
            signature_data=signature_data,
            signature_meaning=signature_meaning,
            verified_at=verified_at,
            verification_method=verification_method,
            ip_address=ip_address,
            self_approved=is_self_approval
        )

        # Update parent status
        approval_request.update_status()

        return response

    def delegate_to(self, delegatee, reason):
        """Delegate approval to another user with full audit trail"""
        from django.core.exceptions import ValidationError

        if self.approval_request.delegation_policy == ApprovalDelegation.DISABLED:
            raise ValidationError("Delegation not allowed for this approval type")

        self.decision = ApprovalDecision.DELEGATED
        self.delegated_to = delegatee
        self.comments = reason
        self.save()

        # Update approval request assignments with audit trail
        request = self.approval_request

        # Find original assignment
        try:
            original_assignment = ApproverAssignment.objects.get(
                approval_request=request,
                user=self.approver
            )

            # Create new assignment for delegatee, linking to original
            ApproverAssignment.objects.create(
                approval_request=request,
                user=delegatee,
                is_required=original_assignment.is_required,
                sequence_order=original_assignment.sequence_order,
                assignment_source=ApproverAssignmentSource.DELEGATION,
                assigned_by=self.approver,
                delegated_from=original_assignment
            )

            # Mark original as no longer active by removing (keeps history via delegated_from)
            original_assignment.delete()

        except ApproverAssignment.DoesNotExist:
            # Fallback: create assignment without linking
            request.add_approver(
                delegatee,
                is_required=True,
                assignment_source=ApproverAssignmentSource.DELEGATION,
                assigned_by=self.approver
            )


class ApprovalTemplate(SecureModel):

    template_name = models.CharField(max_length=100)
    approval_type = models.CharField(max_length=50, choices=Approval_Type.choices)

    # Default approvers
    default_approvers = models.ManyToManyField(User, related_name='default_approval_templates', blank=True)
    default_groups = models.ManyToManyField('TenantGroup', related_name='default_approval_templates', blank=True)
    default_threshold = models.IntegerField(null=True, blank=True)
    auto_assign_by_role = models.CharField(max_length=50, null=True, blank=True, help_text="Group name to auto-assign (e.g., 'QA_Manager')")

    # Rules
    approval_flow_type = models.CharField(max_length=20, choices=ApprovalFlows.choices, default=ApprovalFlows.ALL_REQUIRED)
    delegation_policy = models.CharField(max_length=20, choices=ApprovalDelegation.choices, default=ApprovalDelegation.DISABLED)
    approval_sequence = models.CharField(max_length=20, choices=SequenceTypes.choices, default=SequenceTypes.PARALLEL)
    allow_self_approval = models.BooleanField(default=False, help_text="Allow requesters to approve their own requests (requires justification)")

    # SLA
    default_due_days = models.IntegerField(default=5, help_text="Days until due date")
    escalation_days = models.IntegerField(null=True, blank=True, help_text="Days before escalation triggers")
    escalate_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='template_escalations')

    deactivated_at = models.DateTimeField(null=True, blank=True, help_text="Null = currently active")

    class Meta:
        ordering = ['template_name']
        verbose_name = 'Approval Template'
        verbose_name_plural = 'Approval Templates'
        permissions = [
            ("create_approval_template", "Can create approval templates"),
            ("manage_approval_workflow", "Can manage approval workflows"),
        ]
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'template_name'], name='approvaltemplate_tenant_name_uniq'),
            models.UniqueConstraint(fields=['tenant', 'approval_type'], name='approvaltemplate_tenant_type_uniq'),
        ]

    def __str__(self):
        return f"{self.template_name} ({self.get_approval_type_display()})"

# ===== DOCUMENT MANAGEMENT =====

class DocumentType(SecureModel):
    """
    Configurable document types for categorization.

    Examples: SOP, Work Instruction, Drawing, Specification, Form, Policy, etc.

    DMS Compliance Features:
    - requires_approval: Whether documents must go through approval workflow
    - approval_template: Links to specific ApprovalTemplate for this document type
    - default_review_period_days: How often documents of this type should be reviewed
    - default_retention_days: How long documents must be retained (compliance)
    """
    name = models.CharField(max_length=100, help_text="Display name (e.g., 'Standard Operating Procedure')")
    code = models.CharField(max_length=20, help_text="Short code for ID prefix (e.g., 'SOP', 'WI', 'DWG')")
    description = models.TextField(blank=True, help_text="Description of this document type")
    requires_approval = models.BooleanField(
        default=True,
        help_text="Whether documents of this type require approval before release"
    )

    # Link to approval workflow template (optional - defaults to DOCUMENT_RELEASE)
    approval_template = models.ForeignKey(
        'ApprovalTemplate',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='document_types',
        help_text="Approval template to use for this document type (defaults to DOCUMENT_RELEASE if not set)"
    )

    # DMS Compliance: Review and retention policies
    default_review_period_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Default number of days between reviews for documents of this type (e.g., 365 for annual review)"
    )
    default_retention_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Default retention period in days for documents of this type (e.g., 2555 for 7 years)"
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Document Type'
        verbose_name_plural = 'Document Types'
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'name'], name='documenttype_tenant_name_uniq'),
            models.UniqueConstraint(fields=['tenant', 'code'], name='documenttype_tenant_code_uniq'),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"


class Documents(SecureModel):
    """
    Represents a file uploaded and optionally associated with any entity.

    This model supports version tracking and stores metadata about uploaded files such as
    whether the file is an image, who uploaded it, and when. File storage is dynamically
    structured for traceability and organization.

    This is core infrastructure used across all modules (MES, QMS, etc.) to attach
    controlled documents to any entity via GenericForeignKey.

    Fields:
        is_image (bool): Whether the uploaded file is an image.
        file_name (str): Logical filename (not necessarily the original) used to rename uploaded content.
        file (FileField): The actual file stored, path determined by `part_doc_upload_path`.
        upload_date (date): Date the file was uploaded.
        uploaded_by (ForeignKey): Reference to the User who uploaded the file.
        related_object (GenericForeignKey): Optional reference to the Object associated with this file.
        version (int): Simple version number to track document revisions.
        classification (str): Security classification level (PUBLIC, INTERNAL, CONFIDENTIAL, etc.)
        ai_readable (bool): Whether this document should be processed by AI/LLM features

    Storage:
        Files are stored under a directory tree like:
        parts_docs/part_<part_id>/<YYYY-MM-DD>/<file_name>.<ext>
    """

    classification = models.CharField(max_length=20, choices=ClassificationLevel.choices,
                                      default=ClassificationLevel.INTERNAL,
                                      help_text="Security classification level for document access control", null=True,
                                      blank=False)

    # =========================================================================
    # ITAR / Export Control Fields
    # =========================================================================
    itar_controlled = models.BooleanField(
        default=False,
        help_text="Document contains ITAR-controlled technical data (22 CFR 120-130)"
    )
    """Indicates document is subject to ITAR export restrictions."""

    eccn = models.CharField(
        max_length=20,
        blank=True,
        help_text="Export Control Classification Number (e.g., EAR99, 3A001, 9A004.a)"
    )
    """
    ECCN from the Commerce Control List (CCL) for EAR-controlled items.
    Common values:
    - EAR99: No license required for most destinations
    - 3A001: Electronics
    - 9A004: Gas turbine engines
    - Empty: Not yet classified or not subject to EAR
    """

    export_control_reason = models.CharField(
        max_length=100,
        blank=True,
        help_text="Reason for export control classification (e.g., 'Contains defense article specs')"
    )
    """Brief explanation of why this document is export controlled."""

    ai_readable = models.BooleanField(default=False)

    is_image = models.BooleanField(default=False)

    file_name = models.CharField(max_length=50)

    file = models.FileField(upload_to=part_doc_upload_path)

    upload_date = models.DateField(auto_now_add=True)

    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, auto_created=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True,
                                     help_text="Model of the object this document relates to")

    object_id = models.CharField(max_length=36, null=True, blank=True,
                                 help_text="ID of the object this document relates to (CharField for UUID compatibility)")

    content_object = GenericForeignKey('content_type', 'object_id')

    # Approval workflow fields
    status = models.CharField(
        max_length=20,
        choices=[
            ('DRAFT', 'Draft'),
            ('UNDER_REVIEW', 'Under Review'),
            ('APPROVED', 'Approved'),
            ('RELEASED', 'Released'),
            ('OBSOLETE', 'Obsolete'),
        ],
        default='DRAFT',
        help_text="Document workflow status"
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents_approved'
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    # Document type (optional - for categorization)
    document_type = models.ForeignKey(
        DocumentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents',
        help_text="Type/category of document (e.g., SOP, Work Instruction)"
    )

    # Revision tracking
    change_justification = models.TextField(
        blank=True,
        help_text="Reason for this revision (required when creating new versions)"
    )

    # =========================================================================
    # DMS COMPLIANCE FIELDS
    # =========================================================================
    effective_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when this document version becomes effective (typically set on release)"
    )
    review_date = models.DateField(
        null=True,
        blank=True,
        help_text="Next scheduled review date (auto-calculated from document_type.default_review_period_days)"
    )
    obsolete_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when document was marked obsolete (set automatically on status change)"
    )
    retention_until = models.DateField(
        null=True,
        blank=True,
        help_text="Date until which this document must be retained (calculated from effective_date + retention_days)"
    )

    class Meta:
        verbose_name_plural = 'Documents'
        verbose_name = 'Document'
        permissions = [
            ("view_confidential_documents", "Can view confidential classification documents"),
            ("view_restricted_documents", "Can view restricted classification documents"),
            ("view_secret_documents", "Can view secret classification documents"),
            ("classify_documents", "Can change document classification level"),
        ]
        indexes = [
            models.Index(fields=['content_type', 'object_id'], name='documents_content_object_idx'),
            models.Index(fields=['status', 'created_at'], name='documents_status_created_idx'),
            models.Index(fields=['review_date'], name='documents_review_date_idx'),
            models.Index(fields=['retention_until'], name='documents_retention_idx'),
        ]

    def __str__(self):
        return self.file_name

    def user_can_access(self, user):
        if user.is_superuser:
            return True
        # Use tenant-scoped group membership
        if user.has_tenant_group("Customer") if hasattr(user, 'has_tenant_group') else False:
            return self.classification == ClassificationLevel.PUBLIC
        elif user.has_tenant_group("Employee") if hasattr(user, 'has_tenant_group') else False:
            return self.classification in [ClassificationLevel.PUBLIC, ClassificationLevel.INTERNAL]
        elif user.has_tenant_group("Manager") if hasattr(user, 'has_tenant_group') else False:
            return self.classification in [ClassificationLevel.PUBLIC, ClassificationLevel.INTERNAL,
                                           ClassificationLevel.CONFIDENTIAL]
        return False

    def get_access_level_for_user(self, user):
        if user.is_superuser:
            return "full_access"
        # Use tenant-scoped group membership
        user_groups = user.get_tenant_group_names() if hasattr(user, 'get_tenant_group_names') else set()
        if "Customer" in user_groups:
            return "public_only" if self.classification == ClassificationLevel.PUBLIC else "no_access"
        elif "Employee" in user_groups:
            if self.classification in [ClassificationLevel.PUBLIC, ClassificationLevel.INTERNAL]:
                return "read_only"
            return "no_access"
        elif "Manager" in user_groups:
            if self.classification in [ClassificationLevel.PUBLIC, ClassificationLevel.INTERNAL,
                                       ClassificationLevel.CONFIDENTIAL]:
                return "read_write"
            return "no_access"
        return "no_access"

    def auto_detect_properties(self, file=None):
        from mimetypes import guess_type
        file = file or self.file
        if not file:
            return {}
        properties = {}
        mime_type, _ = guess_type(file.name)
        properties['is_image'] = mime_type and mime_type.startswith("image/")
        if not self.file_name:
            properties['file_name'] = file.name
        return properties

    def embed_async(self):
        from Tracker.tasks import embed_document_async
        return embed_document_async.delay(self.id)

    def embed_inline(self) -> bool:
        """
        Minimal, synchronous embedding for small text files and PDFs.
        Returns True if chunks were embedded, False if skipped.

        Note: Consider using embed_async() instead to avoid blocking requests.
        """
        import os
        from django.conf import settings
        from django.db import transaction
        from Tracker.ai_embed import embed_texts, chunk_text
        from Tracker.models.dms import DocChunk

        if not settings.AI_EMBED_ENABLED:
            return False

        if not self.file or not os.path.exists(self.file.path):
            return False
        if os.path.getsize(self.file.path) > settings.AI_EMBED_MAX_FILE_BYTES:
            return False

        # Extract text based on file type
        text = self._extract_text_from_file()
        if not text or not text.strip():
            return False

        chunks = chunk_text(text, max_chars=settings.AI_EMBED_CHUNK_CHARS, max_chunks=settings.AI_EMBED_MAX_CHUNKS)
        if not chunks:
            return False

        vecs = embed_texts(chunks)
        # (optional) sanity check on dimensions:
        assert len(vecs[0]) == settings.AI_EMBED_DIM

        rows = [DocChunk(doc=self, preview_text=t[:300], full_text=t, span_meta={"i": i}, embedding=v) for i, (t, v) in
                enumerate(zip(chunks, vecs))]
        with transaction.atomic():
            DocChunk.objects.filter(doc=self).delete()
            DocChunk.objects.bulk_create(rows, batch_size=50)
            self.ai_readable = True
            self.save(update_fields=["ai_readable"])
        return True

    def _extract_text_from_file(self) -> str:
        """
        Extract text from various file formats (PDF, text files, etc.)
        Returns empty string if extraction fails
        """
        import os

        file_path = self.file.path
        file_ext = os.path.splitext(file_path)[1].lower()

        try:
            if file_ext == '.pdf':
                return self._extract_pdf_text(file_path)
            else:
                # Handle as text file
                return self._extract_text_file(file_path)
        except Exception:
            return ""

    def _extract_pdf_text(self, file_path: str) -> str:
        """Extract text from PDF file using PyPDF2"""
        try:
            import PyPDF2
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"

            # Remove null bytes that cause PostgreSQL issues
            text = text.replace('\x00', '')
            return text.strip()
        except ImportError:
            # PyPDF2 not available, return empty
            return ""
        except Exception:
            # PDF extraction failed
            return ""

    def _extract_text_file(self, file_path: str) -> str:
        """Extract text from regular text files"""
        try:
            from django.conf import settings
            with open(file_path, "rb") as f:
                data = f.read(settings.AI_EMBED_MAX_FILE_BYTES + 1)

            text = data.decode("utf-8", errors="ignore")
            # Remove null bytes that cause PostgreSQL issues
            text = text.replace('\x00', '')
            return text.strip()
        except Exception:
            return ""

    def log_access(self, user, request=None, action_type='view'):
        """
        Log document access for compliance auditing.

        Args:
            user: The user accessing the document
            request: Optional HTTP request for IP extraction
            action_type: 'view' (metadata) or 'download' (file retrieval)

        Logs to both django-auditlog (for UI) and compliance logger (for SIEM).
        """
        from auditlog.models import LogEntry
        from django.contrib.contenttypes.models import ContentType
        from django.utils import timezone
        import json
        import logging

        compliance_logger = logging.getLogger('compliance.access_control')

        # Extract remote address
        remote_addr = None
        if request:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                remote_addr = x_forwarded_for.split(',')[0].strip()
            else:
                remote_addr = request.META.get('REMOTE_ADDR')

        # Build access record with export control context
        access_data = {
            'action_type': f'document_{action_type}',
            'file_name': self.file_name,
            'classification': self.classification,
            'itar_controlled': getattr(self, 'itar_controlled', False),
            'eccn': getattr(self, 'eccn', ''),
            'is_image': self.is_image,
        }

        # Create auditlog entry
        LogEntry.objects.create(
            content_type=ContentType.objects.get_for_model(self),
            object_pk=str(self.pk),
            object_id=self.id,
            object_repr=str(self),
            action=LogEntry.Action.ACCESS,
            changes=json.dumps(access_data),
            actor=user,
            timestamp=timezone.now(),
            remote_addr=remote_addr
        )

        # Log to compliance logger for SIEM integration
        compliance_logger.info({
            'event_type': 'ACCESS_GRANTED',
            'timestamp': timezone.now().isoformat(),
            'action': action_type,
            'user_id': str(user.id),
            'user_email': user.email,
            'user_us_person': getattr(user, 'us_person', False),
            'user_citizenship': getattr(user, 'citizenship', 'UNKNOWN'),
            'document_id': str(self.id),
            'document_name': self.file_name,
            'classification': self.classification,
            'itar_controlled': getattr(self, 'itar_controlled', False),
            'eccn': getattr(self, 'eccn', ''),
            'remote_addr': remote_addr,
        })

    # =========================================================================
    # DMS COMPLIANCE PROPERTIES
    # =========================================================================

    @property
    def is_due_for_review(self):
        """Check if document is due for periodic review"""
        from datetime import date
        if not self.review_date:
            return False
        return date.today() >= self.review_date

    @property
    def is_past_retention(self):
        """Check if document is past its retention period (can be archived/deleted)"""
        from datetime import date
        if not self.retention_until:
            return False
        return date.today() > self.retention_until

    @property
    def days_until_review(self):
        """Days until next review (negative if overdue)"""
        from datetime import date
        if not self.review_date:
            return None
        return (self.review_date - date.today()).days

    def calculate_compliance_dates(self, effective_date=None):
        """
        Calculate review_date and retention_until based on document_type settings.
        Called automatically when document is released.

        Args:
            effective_date: Override effective date (defaults to today)
        """
        from datetime import date, timedelta

        if not effective_date:
            effective_date = date.today()

        self.effective_date = effective_date

        if self.document_type:
            # Calculate review date
            if self.document_type.default_review_period_days:
                self.review_date = effective_date + timedelta(days=self.document_type.default_review_period_days)

            # Calculate retention date
            if self.document_type.default_retention_days:
                self.retention_until = effective_date + timedelta(days=self.document_type.default_retention_days)

    def release(self, user, effective_date=None):
        """
        Release an approved document, setting it to RELEASED status and calculating compliance dates.

        Args:
            user: User performing the release
            effective_date: When the document becomes effective (defaults to today)

        Raises:
            ValueError: If document is not in APPROVED status
        """
        if self.status != 'APPROVED':
            raise ValueError(f"Cannot release document with status {self.status}. Must be APPROVED.")

        self.status = 'RELEASED'
        self.calculate_compliance_dates(effective_date)
        self.save()

    def mark_obsolete(self, user):
        """
        Mark document as obsolete.

        Args:
            user: User marking the document obsolete
        """
        from datetime import date

        if self.status not in ('APPROVED', 'RELEASED'):
            raise ValueError(f"Cannot obsolete document with status {self.status}.")

        self.status = 'OBSOLETE'
        self.obsolete_date = date.today()
        self.save()

    def submit_for_approval(self, user):
        """
        Submit document for approval workflow.

        Uses the document_type's approval_template if configured, otherwise
        falls back to the default DOCUMENT_RELEASE template.

        Args:
            user: The user submitting the document for approval

        Returns:
            ApprovalRequest: The created approval request

        Raises:
            ValueError: If document is not in DRAFT status, approval not required,
                        or template not found
        """
        if self.status != 'DRAFT':
            raise ValueError(f"Cannot submit document with status {self.status}. Must be DRAFT.")

        # Check if this document type requires approval
        if self.document_type and not self.document_type.requires_approval:
            raise ValueError(
                f"Document type '{self.document_type.name}' does not require approval. "
                "Use release() directly or update the document type settings."
            )

        # Get approval template: prefer document_type's template, fallback to DOCUMENT_RELEASE
        template = None
        if self.document_type and self.document_type.approval_template:
            template = self.document_type.approval_template
        else:
            try:
                # Filter by tenant to avoid MultipleObjectsReturned
                template = ApprovalTemplate.objects.get(
                    approval_type='DOCUMENT_RELEASE',
                    tenant=self.tenant
                )
            except ApprovalTemplate.DoesNotExist:
                raise ValueError("DOCUMENT_RELEASE approval template not found. Please configure approval templates.")

        # Create approval request from template
        approval_request = ApprovalRequest.create_from_template(
            content_object=self,
            template=template,
            requested_by=user,
            reason=f"Document Release: {self.file_name}"
        )

        # Update document status
        self.status = 'UNDER_REVIEW'
        self.save(update_fields=['status'])

        return approval_request

    @staticmethod
    def extract_text_from_file(file_path: str) -> str:
        try:
            from django.conf import settings
            with open(file_path, "rb") as f:
                data = f.read(settings.AI_EMBED_MAX_FILE_BYTES + 1)
            text = data.decode("utf-8", errors="ignore")
            text = text.replace('', '')
            return text.strip()
        except Exception:
            return ""


# =============================================================================
# PERMISSION AUDIT TRAIL
# =============================================================================

class PermissionChangeLog(models.Model):
    """
    Audit trail for permission changes - important for QMS compliance.

    Tracks when permissions are added/removed from groups, who made the change,
    and why. Essential for answering "who had access to what, when?"
    """

    ACTION_CHOICES = [
        ('added', 'Permission Added'),
        ('removed', 'Permission Removed'),
        ('group_created', 'Group Created'),
        ('group_deleted', 'Group Deleted'),
    ]

    SOURCE_CHOICES = [
        ('migration', 'Database Migration'),
        ('post_migrate', 'Post-Migrate Signal'),
        ('management_cmd', 'Management Command'),
        ('admin_ui', 'Admin Interface'),
        ('api', 'API Call'),
    ]

    tenant = models.ForeignKey(
        'Tenant',
        on_delete=models.CASCADE,
        null=True,  # Null for system-wide changes (e.g., migrations)
        blank=True,
        related_name='permission_change_logs',
        help_text="Tenant scope for this change (null for system-wide operations)"
    )
    timestamp = models.DateTimeField(default=timezone.now, editable=False, db_index=True)
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='permission_changes_made',
        help_text="User who made the change (null for system operations)"
    )

    group_name = models.CharField(max_length=150, db_index=True)
    permission_codename = models.CharField(
        max_length=255,
        blank=True,
        help_text="Permission codename (empty for group create/delete)"
    )

    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default='management_cmd'
    )

    reason = models.TextField(
        blank=True,
        help_text="Why this change was made"
    )

    # Metadata
    permissions_before = models.IntegerField(
        default=0,
        help_text="Number of permissions in group before change"
    )
    permissions_after = models.IntegerField(
        default=0,
        help_text="Number of permissions in group after change"
    )

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Permission Change Log'
        verbose_name_plural = 'Permission Change Logs'
        indexes = [
            models.Index(fields=['group_name', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['tenant', '-timestamp'], name='permlog_tenant_time_idx'),
        ]

    def __str__(self):
        if self.permission_codename:
            return f"{self.get_action_display()}: {self.permission_codename} -> {self.group_name}"
        return f"{self.get_action_display()}: {self.group_name}"

    @classmethod
    def log_permission_added(cls, group_name: str, permission: str, source: str = 'management_cmd',
                              user=None, tenant=None, reason: str = '', before: int = 0, after: int = 0):
        """Log a permission being added to a group."""
        # Auto-derive tenant from user if not provided
        if tenant is None and user is not None:
            tenant = getattr(user, 'tenant', None)
        return cls.objects.create(
            tenant=tenant,
            group_name=group_name,
            permission_codename=permission,
            action='added',
            source=source,
            changed_by=user,
            reason=reason,
            permissions_before=before,
            permissions_after=after,
        )

    @classmethod
    def log_permission_removed(cls, group_name: str, permission: str, source: str = 'management_cmd',
                                user=None, tenant=None, reason: str = '', before: int = 0, after: int = 0):
        """Log a permission being removed from a group."""
        if tenant is None and user is not None:
            tenant = getattr(user, 'tenant', None)
        return cls.objects.create(
            tenant=tenant,
            group_name=group_name,
            permission_codename=permission,
            action='removed',
            source=source,
            changed_by=user,
            reason=reason,
            permissions_before=before,
            permissions_after=after,
        )

    @classmethod
    def log_group_created(cls, group_name: str, source: str = 'management_cmd',
                          user=None, tenant=None, reason: str = ''):
        """Log a group being created."""
        if tenant is None and user is not None:
            tenant = getattr(user, 'tenant', None)
        return cls.objects.create(
            tenant=tenant,
            group_name=group_name,
            permission_codename='',
            action='group_created',
            source=source,
            changed_by=user,
            reason=reason,
        )

    @classmethod
    def log_group_deleted(cls, group_name: str, source: str = 'management_cmd',
                          user=None, tenant=None, reason: str = ''):
        """Log a group being deleted."""
        if tenant is None and user is not None:
            tenant = getattr(user, 'tenant', None)
        return cls.objects.create(
            tenant=tenant,
            group_name=group_name,
            permission_codename='',
            action='group_deleted',
            source=source,
            changed_by=user,
            reason=reason,
        )

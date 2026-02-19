# viewsets/core.py - Core infrastructure (Users, Companies, Auth, Approvals, Documents, Mixins)
import os
import pandas as pd
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.http import HttpResponse, FileResponse, Http404
from django.views.decorators.clickjacking import xframe_options_exempt
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema_view, extend_schema, inline_serializer, OpenApiResponse, OpenApiParameter
from rest_framework import viewsets, status, filters, serializers, parsers, permissions
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet
from auditlog.models import LogEntry
from dj_rest_auth.views import UserDetailsView as BaseUserDetailsView

from Tracker.filters import UserFilter
from Tracker.models.core import User, Companies, UserInvitation, ApprovalTemplate, ApprovalRequest, ApprovalResponse, Documents, DocumentType
from Tracker.serializers.core import (
    UserSerializer, UserSelectSerializer, UserDetailSerializer,
    CompanySerializer, GroupSerializer, UserInvitationSerializer,
    ContentTypeSerializer, AuditLogSerializer,
    ApprovalTemplateSerializer, ApprovalRequestSerializer, ApprovalResponseSerializer
)
from Tracker.serializers.dms import DocumentsSerializer, DocumentTypeSerializer
from .base import TenantScopedMixin, NonTenantModelViewSet


# ===== BASE MIXINS =====

class ListMetadataMixin:
    """
    Mixin to expose search, filter, and ordering fields to the frontend.

    Adds a /metadata/ action that returns what fields are searchable,
    filterable, and sortable. This helps the frontend build dynamic
    search UIs with placeholder text like "Search by Work Order ID, Order Name..."

    Usage:
        class MyViewSet(ListMetadataMixin, viewsets.ModelViewSet):
            search_fields = ['name', 'description']
            ordering_fields = ['created_at', 'name']
            filterset_fields = ['status', 'category']

        GET /api/my-model/metadata/
        Returns:
        {
            "search_fields": ["name", "description"],
            "ordering_fields": ["created_at", "name"],
            "filterset_fields": ["status", "category"],
            "search_fields_display": ["Name", "Description"]
        }
    """

    @extend_schema(
        responses=inline_serializer(
            name='ListMetadataResponse',
            fields={
                'search_fields': serializers.ListField(child=serializers.CharField()),
                'search_fields_display': serializers.ListField(child=serializers.CharField()),
                'ordering_fields': serializers.ListField(child=serializers.CharField()),
                'ordering_fields_display': serializers.ListField(child=serializers.CharField()),
                'filterset_fields': serializers.ListField(child=serializers.CharField()),
                'filters': serializers.DictField(),
            }
        )
    )
    @action(detail=False, methods=['get'])
    def metadata(self, request):
        """Return searchable/filterable/orderable field information with filter options."""
        search_fields = getattr(self, 'search_fields', [])
        ordering_fields = getattr(self, 'ordering_fields', [])
        filterset_fields = getattr(self, 'filterset_fields', [])
        filterset_class = getattr(self, 'filterset_class', None)

        # Convert field names to human-readable display names
        def field_to_display(field: str) -> str:
            # Remove prefixes like ^ (startswith) or @ (search) or = (exact)
            clean = field.lstrip('^@=')
            # Handle related fields like 'related_order__name' -> 'Order Name'
            parts = clean.split('__')
            # Title case each part and join with space
            return ' '.join(part.replace('_', ' ').title() for part in parts)

        # Build filter metadata with choices/options
        filters = {}
        model = getattr(self, 'queryset', None)
        if model is not None:
            model = model.model
        elif hasattr(self, 'get_queryset'):
            try:
                qs = self.get_queryset()
                model = qs.model if qs is not None else None
            except Exception:
                model = None

        # Get filter fields from filterset_class if available
        filter_field_names = []
        if filterset_class:
            filter_field_names = list(filterset_class.base_filters.keys())
        elif isinstance(filterset_fields, list):
            filter_field_names = filterset_fields
        elif isinstance(filterset_fields, dict):
            filter_field_names = list(filterset_fields.keys())

        for field_name in filter_field_names:
            # Skip complex filters (date ranges, etc.)
            if '__' in field_name and field_name.split('__')[1] in ('gte', 'lte', 'gt', 'lt', 'in'):
                continue

            filter_info = {
                'name': field_name,
                'display': field_to_display(field_name),
                'type': 'text',  # default
                'choices': None,
            }

            # Try to get field info from model
            if model:
                try:
                    # Handle the base field name (strip lookup suffixes)
                    base_field_name = field_name.split('__')[0] if '__' in field_name else field_name
                    model_field = model._meta.get_field(base_field_name)

                    # Check for choices
                    if hasattr(model_field, 'choices') and model_field.choices:
                        filter_info['type'] = 'choice'
                        filter_info['choices'] = [
                            {'value': choice[0], 'label': choice[1]}
                            for choice in model_field.choices
                        ]
                    # Check for boolean
                    elif model_field.get_internal_type() == 'BooleanField':
                        filter_info['type'] = 'boolean'
                        filter_info['choices'] = [
                            {'value': 'true', 'label': 'Yes'},
                            {'value': 'false', 'label': 'No'},
                        ]
                    # Check for FK - provide endpoint hint
                    elif model_field.get_internal_type() == 'ForeignKey':
                        filter_info['type'] = 'foreignkey'
                        related_model = model_field.related_model
                        filter_info['related_model'] = related_model._meta.model_name
                except Exception:
                    pass

            # Also check filterset_class for additional info
            if filterset_class and field_name in filterset_class.base_filters:
                filter_obj = filterset_class.base_filters[field_name]
                # BooleanFilter
                if filter_obj.__class__.__name__ == 'BooleanFilter':
                    filter_info['type'] = 'boolean'
                    filter_info['choices'] = [
                        {'value': 'true', 'label': 'Yes'},
                        {'value': 'false', 'label': 'No'},
                    ]

            filters[field_name] = filter_info

        return Response({
            'search_fields': search_fields,
            'search_fields_display': [field_to_display(f) for f in search_fields],
            'ordering_fields': ordering_fields,
            'ordering_fields_display': [field_to_display(f) for f in ordering_fields],
            'filterset_fields': filter_field_names,
            'filters': filters,
        })


class ExcelExportMixin:
    """
    Mixin to add Excel export functionality to ViewSets.

    Current features:
    - Exports all non-relation fields by default
    - Respects filtering, search, and ordering from list view
    - Supports query param ?fields=id,name,status to select specific fields
    - Supports query param ?filename=custom.xlsx for custom filename

    Future enhancements (TODO):
    - Add ExportConfiguration model for user-saved preferences
    - Add available_fields() action to return list of exportable fields
    - Add save_export_config() action to save user preferences
    - Frontend: React modal with field checkboxes and "Save as Default" button

    Usage:
        class MyViewSet(ExcelExportMixin, viewsets.ModelViewSet):
            excel_fields = ['id', 'name', 'status']  # Optional: override default fields
            excel_filename = 'my_export.xlsx'  # Optional: override default filename

        GET /api/my-model/export_excel/
        GET /api/my-model/export_excel/?fields=id,name
        GET /api/my-model/export_excel/?filename=custom_export.xlsx
    """

    excel_fields = None  # Override in viewset to specify default fields
    excel_filename = 'export.xlsx'  # Override in viewset for default filename

    def get_excel_fields(self):
        """
        Get the list of fields to export.

        Priority:
        1. Query param ?fields=id,name,status (user override)
        2. self.excel_fields (class attribute)
        3. All non-relation model fields (auto-detect)

        Future TODO: Add DB lookup for user-saved preferences between steps 1 and 2
        """
        # 1. Check query params first (highest priority)
        fields_param = self.request.query_params.get('fields')
        if fields_param:
            return [f.strip() for f in fields_param.split(',')]

        # TODO: Add DB lookup here for user-saved ExportConfiguration
        # try:
        #     config = ExportConfiguration.objects.get(
        #         user=self.request.user,
        #         model_name=self.queryset.model.__name__,
        #         is_default=True
        #     )
        #     return config.fields
        # except ExportConfiguration.DoesNotExist:
        #     pass

        # 2. Use class attribute if specified
        if self.excel_fields:
            return self.excel_fields

        # 3. Default: export all non-relation fields
        return [f.name for f in self.queryset.model._meta.fields if not f.is_relation]

    def get_excel_filename(self):
        """
        Get the filename for the export.

        Priority:
        1. Query param ?filename=custom.xlsx
        2. self.excel_filename (class attribute)

        Future TODO: Could pull from DB config as well
        """
        filename_param = self.request.query_params.get('filename')
        if filename_param:
            # Ensure .xlsx extension
            if not filename_param.endswith('.xlsx'):
                filename_param += '.xlsx'
            return filename_param

        return self.excel_filename

    @extend_schema(parameters=[OpenApiParameter(name='fields',
                                                description='Comma-separated list of field names to export (e.g., id,name,status)',
                                                required=False, type=str), OpenApiParameter(name='filename',
                                                                                            description='Custom filename for the download (e.g., my_export.xlsx)',
                                                                                            required=False,
                                                                                            type=str), ],
                   responses={200: {'type': 'string', 'format': 'binary', 'description': 'Excel file download'}},
                   description='Export the current queryset to Excel format. Respects all filters, search, and ordering applied to the list view.')
    @action(detail=False, methods=['get'], url_path='export-excel')
    def export_excel(self, request):
        """
        Export the current queryset to Excel format.

        Respects all filters, search, and ordering applied to the list view.

        Query params:
        - fields: Comma-separated list of field names to export (e.g., ?fields=id,name,status)
        - filename: Custom filename for the download (e.g., ?filename=my_export.xlsx)

        Returns:
        - Excel file download
        """
        # Get the filtered/searched/ordered queryset (same as list view)
        queryset = self.filter_queryset(self.get_queryset())

        # Get fields to export
        fields = self.get_excel_fields()

        # Convert queryset to DataFrame using only requested fields
        df = pd.DataFrame(queryset.values(*fields))

        # Create HTTP response with Excel content type
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{self.get_excel_filename()}"'

        # Write DataFrame to Excel
        df.to_excel(response, index=False, engine='openpyxl')

        return response


def with_int_pk_schema(cls):
    """Decorator to add integer PK parameter to OpenAPI schema for detail endpoints"""
    return extend_schema_view(
        retrieve=extend_schema(parameters=[OpenApiParameter(name='id', type=int, location=OpenApiParameter.PATH)]),
        update=extend_schema(parameters=[OpenApiParameter(name='id', type=int, location=OpenApiParameter.PATH)]),
        partial_update=extend_schema(
            parameters=[OpenApiParameter(name='id', type=int, location=OpenApiParameter.PATH)]),
        destroy=extend_schema(parameters=[OpenApiParameter(name='id', type=int, location=OpenApiParameter.PATH)]), )(
        cls)


# ===== USER & COMPANY VIEWSETS =====

class EmployeeSelectViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    """Select list for employees (staff users)."""
    queryset = User.objects.all()
    serializer_class = UserSelectSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return User.objects.none()

        # Apply tenant scoping, then filter to staff
        return super().get_queryset().filter(is_staff=True)


class CustomerViewSet(TenantScopedMixin, ListMetadataMixin, ExcelExportMixin, viewsets.ModelViewSet):
    """Customer (non-staff user) management."""
    queryset = User.objects.all()
    serializer_class = UserDetailSerializer
    pagination_class = None

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return User.objects.none()

        # Apply tenant scoping, then filter to non-staff
        return super().get_queryset().filter(is_staff=False)


@with_int_pk_schema
class UserViewSet(TenantScopedMixin, ListMetadataMixin, ExcelExportMixin, viewsets.ModelViewSet):
    """Enhanced User ViewSet with comprehensive filtering, ordering, and search"""
    serializer_class = UserSerializer
    pagination_class = LimitOffsetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = UserFilter
    ordering_fields = ['username', 'first_name', 'last_name', 'email', 'date_joined', 'is_active', 'is_staff']
    ordering = ['-date_joined']
    search_fields = ['username', 'first_name', 'last_name', 'email', 'parent_company__name']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return User.objects.none()

        # User model doesn't inherit from SecureModel, so filter by company manually
        user = self.request.user
        if user.is_staff:
            # Superusers always see all users
            if user.is_superuser:
                return User.objects.all().select_related('parent_company')

            # Check if user has any groups that are NOT 'Customers' (tenant-scoped)
            user_group_names = user.get_tenant_group_names() if hasattr(user, 'get_tenant_group_names') else set()
            non_customer_groups = bool(user_group_names - {'Customer', 'Customers'})
            if non_customer_groups:
                # Staff with non-customer groups (Employees, QA, Admin, Manager, Operator, etc.) see all users
                return User.objects.all().select_related('parent_company')

            # Staff with no company see all users (system-level staff)
            if not user.parent_company:
                return User.objects.all().select_related('parent_company')

            # Other staff (or staff only in Customers group) see their company's users
            return User.objects.filter(parent_company=user.parent_company).select_related('parent_company')
        else:
            # Non-staff users can only see themselves
            return User.objects.filter(id=user.id).select_related('parent_company')

    @extend_schema(request=inline_serializer(name="BulkUserActivationInput", fields={
        "user_ids": serializers.ListField(child=serializers.IntegerField()), "is_active": serializers.BooleanField()}),
                   responses={
                       200: OpenApiResponse(response=dict, description="Bulk activation response")})
    @action(detail=False, methods=['post'], url_path='bulk-activate')
    def bulk_activate(self, request):
        """Bulk activate/deactivate users"""
        user_ids = request.data.get('user_ids', [])
        is_active = request.data.get('is_active', True)

        if not user_ids:
            return Response({"detail": "No user IDs provided"}, status=status.HTTP_400_BAD_REQUEST)

        # Filter to only users accessible by the requesting user
        queryset = self.get_queryset().filter(id__in=user_ids)
        updated_count = queryset.update(is_active=is_active)

        return Response(
            {"detail": f"Updated {updated_count} users", "updated_count": updated_count, "is_active": is_active})

    @extend_schema(request=inline_serializer(name="BulkCompanyAssignmentInput", fields={
        "user_ids": serializers.ListField(child=serializers.IntegerField()),
        "company_id": serializers.UUIDField(allow_null=True)}), responses={
        200: OpenApiResponse(response=dict, description="Bulk company assignment response")})
    @action(detail=False, methods=['post'], url_path='bulk-assign-company')
    def bulk_assign_company(self, request):
        """Bulk assign users to a company"""
        user_ids = request.data.get('user_ids', [])
        company_id = request.data.get('company_id')

        if not user_ids:
            return Response({"detail": "No user IDs provided"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate company exists if provided
        company = None
        if company_id:
            try:
                company = Companies.objects.for_user(self.request.user).get(id=company_id)
            except Companies.DoesNotExist:
                return Response({"detail": "Company not found"}, status=status.HTTP_404_NOT_FOUND)

        # Filter to only users accessible by the requesting user
        queryset = self.get_queryset().filter(id__in=user_ids)
        updated_count = queryset.update(parent_company=company)

        return Response({"detail": f"Assigned {updated_count} users to {'company' if company else 'no company'}",
                         "updated_count": updated_count, "company_name": company.name if company else None})

    @extend_schema(
        request=inline_serializer(name="SendInvitationInput", fields={"user_id": serializers.IntegerField()}),
        responses={201: OpenApiResponse(response=dict, description="Invitation sent successfully")})
    @action(detail=False, methods=['post'], url_path='send-invitation')
    def send_invitation(self, request):
        """Send invitation email to a user"""
        from datetime import timedelta
        from Tracker.models import UserInvitation

        user_id = request.data.get('user_id')

        if not user_id:
            return Response({"detail": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_to_invite = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        # Check if user already has a pending invitation
        existing_invitation = UserInvitation.objects.filter(user=user_to_invite, accepted_at__isnull=True,
                                                            expires_at__gt=timezone.now()).first()

        if existing_invitation:
            return Response(
                {"detail": "User already has a pending invitation", "invitation_id": existing_invitation.id},
                status=status.HTTP_400_BAD_REQUEST)

        # Create invitation
        invitation = UserInvitation.objects.create(user=user_to_invite, invited_by=request.user,
                                                   token=UserInvitation.generate_token(),
                                                   expires_at=timezone.now() + timedelta(days=7)  # 7 day expiration
                                                   )

        # Send invitation email via Celery
        from Tracker.email_notifications import send_invitation_email
        send_invitation_email(invitation.id, immediate=True)

        return Response({"detail": "Invitation sent successfully", "invitation_id": invitation.id,
                         "user_email": user_to_invite.email, "expires_at": invitation.expires_at},
                        status=status.HTTP_201_CREATED)


class GroupViewSet(viewsets.ModelViewSet):
    """ViewSet for Django Groups with user and permission management"""
    serializer_class = GroupSerializer
    pagination_class = LimitOffsetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name']
    ordering = ['name']
    http_method_names = ['get', 'post', 'patch', 'delete']  # No PUT

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Group.objects.none()

        # Only staff users can see groups
        if self.request.user and self.request.user.is_staff:
            # prefetch_related prevents N+1 queries for M2M traversal in serializer
            return Group.objects.all().prefetch_related('user_set', 'permissions')
        return Group.objects.none()

    def get_permissions(self):
        """Only admins can modify groups"""
        admin_actions = [
            'create', 'update', 'partial_update', 'destroy',
            'add_users', 'remove_users',
            'add_permissions', 'remove_permissions', 'set_permissions'
        ]
        if self.action in admin_actions:
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]

    @extend_schema(
        request=inline_serializer(
            name='GroupAddUsersInput',
            fields={'user_ids': serializers.ListField(child=serializers.IntegerField())}
        ),
        responses={200: inline_serializer(
            name='GroupAddUsersResponse',
            fields={
                'detail': serializers.CharField(),
                'group': GroupSerializer()
            }
        )}
    )
    @action(detail=True, methods=['post'], url_path='add-users')
    def add_users(self, request, pk=None):
        """Add users to this group"""
        group = self.get_object()
        user_ids = request.data.get('user_ids', [])

        if not user_ids:
            return Response(
                {"detail": "user_ids is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        users = User.objects.filter(id__in=user_ids)
        added_count = 0
        tenant = request.user.tenant  # Use requesting user's tenant for group membership
        for user in users:
            if tenant and not user.has_tenant_group(group.name, tenant):
                user.add_to_tenant_group(group, tenant=tenant, granted_by=request.user)
                added_count += 1

        return Response({
            "detail": f"Added {added_count} users to group {group.name}",
            "group": GroupSerializer(group).data
        })

    @extend_schema(
        request=inline_serializer(
            name='GroupRemoveUsersInput',
            fields={'user_ids': serializers.ListField(child=serializers.IntegerField())}
        ),
        responses={200: inline_serializer(
            name='GroupRemoveUsersResponse',
            fields={
                'detail': serializers.CharField(),
                'group': GroupSerializer()
            }
        )}
    )
    @action(detail=True, methods=['post'], url_path='remove-users')
    def remove_users(self, request, pk=None):
        """Remove users from this group"""
        group = self.get_object()
        user_ids = request.data.get('user_ids', [])

        if not user_ids:
            return Response(
                {"detail": "user_ids is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        users = User.objects.filter(id__in=user_ids)
        removed_count = 0
        tenant = request.user.tenant  # Use requesting user's tenant for group membership
        for user in users:
            if tenant and user.has_tenant_group(group.name, tenant):
                user.remove_from_tenant_group(group, tenant=tenant)
                removed_count += 1

        return Response({
            "detail": f"Removed {removed_count} users from group {group.name}",
            "group": GroupSerializer(group).data
        })

    @extend_schema(
        responses={200: inline_serializer(
            name='AvailableUserResponse',
            fields={
                'id': serializers.IntegerField(),
                'email': serializers.EmailField(),
                'first_name': serializers.CharField(),
                'last_name': serializers.CharField(),
                'groups': serializers.ListField(child=serializers.CharField())
            },
            many=True
        )}
    )
    @action(detail=False, methods=['get'], url_path='available-users')
    def available_users(self, request):
        """Get all users available to add to groups"""
        users = User.objects.filter(is_active=True).order_by('email')
        tenant = request.user.tenant
        return Response([
            {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'groups': [g.name for g in user.get_tenant_groups(tenant)] if tenant else [],
            }
            for user in users
        ])

    @extend_schema(
        responses={200: inline_serializer(
            name='AvailablePermissionResponse',
            fields={
                'id': serializers.IntegerField(),
                'codename': serializers.CharField(),
                'name': serializers.CharField(),
                'content_type': serializers.CharField(),
            },
            many=True
        )}
    )
    @action(detail=False, methods=['get'], url_path='available-permissions', pagination_class=None)
    def available_permissions(self, request):
        """Get all available permissions that can be assigned to groups"""
        # Filter to only Tracker app permissions (not django admin stuff)
        permissions = Permission.objects.filter(
            content_type__app_label='Tracker'
        ).select_related('content_type').order_by('content_type__model', 'codename')

        return Response([
            {
                'id': perm.id,
                'codename': perm.codename,
                'name': perm.name,
                'content_type': perm.content_type.model,
            }
            for perm in permissions
        ])

    @extend_schema(
        request=inline_serializer(
            name='GroupAddPermissionsInput',
            fields={'permission_ids': serializers.ListField(child=serializers.IntegerField())}
        ),
        responses={200: inline_serializer(
            name='GroupAddPermissionsResponse',
            fields={
                'detail': serializers.CharField(),
                'added_count': serializers.IntegerField(),
                'group': GroupSerializer()
            }
        )}
    )
    @action(detail=True, methods=['post'], url_path='add-permissions')
    def add_permissions(self, request, pk=None):
        """Add permissions to this group"""
        group = self.get_object()
        permission_ids = request.data.get('permission_ids', [])

        if not permission_ids:
            return Response(
                {"detail": "permission_ids is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        permissions = Permission.objects.filter(id__in=permission_ids)
        added_count = 0
        for perm in permissions:
            if not group.permissions.filter(id=perm.id).exists():
                group.permissions.add(perm)
                added_count += 1

        return Response({
            "detail": f"Added {added_count} permissions to group {group.name}",
            "added_count": added_count,
            "group": GroupSerializer(group).data
        })

    @extend_schema(
        request=inline_serializer(
            name='GroupRemovePermissionsInput',
            fields={'permission_ids': serializers.ListField(child=serializers.IntegerField())}
        ),
        responses={200: inline_serializer(
            name='GroupRemovePermissionsResponse',
            fields={
                'detail': serializers.CharField(),
                'removed_count': serializers.IntegerField(),
                'group': GroupSerializer()
            }
        )}
    )
    @action(detail=True, methods=['post'], url_path='remove-permissions')
    def remove_permissions(self, request, pk=None):
        """Remove permissions from this group"""
        group = self.get_object()
        permission_ids = request.data.get('permission_ids', [])

        if not permission_ids:
            return Response(
                {"detail": "permission_ids is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        permissions = Permission.objects.filter(id__in=permission_ids)
        removed_count = 0
        for perm in permissions:
            if group.permissions.filter(id=perm.id).exists():
                group.permissions.remove(perm)
                removed_count += 1

        return Response({
            "detail": f"Removed {removed_count} permissions from group {group.name}",
            "removed_count": removed_count,
            "group": GroupSerializer(group).data
        })

    @extend_schema(
        request=inline_serializer(
            name='GroupSetPermissionsInput',
            fields={'permission_ids': serializers.ListField(child=serializers.IntegerField())}
        ),
        responses={200: inline_serializer(
            name='GroupSetPermissionsResponse',
            fields={
                'detail': serializers.CharField(),
                'group': GroupSerializer()
            }
        )}
    )
    @action(detail=True, methods=['post'], url_path='set-permissions')
    def set_permissions(self, request, pk=None):
        """Replace all permissions on this group with the provided list"""
        group = self.get_object()
        permission_ids = request.data.get('permission_ids', [])

        # Can set to empty list to clear all permissions
        permissions = Permission.objects.filter(id__in=permission_ids)
        group.permissions.set(permissions)

        return Response({
            "detail": f"Set {len(permission_ids)} permissions on group {group.name}",
            "group": GroupSerializer(group).data
        })


class CompanyViewSet(TenantScopedMixin, ListMetadataMixin, ExcelExportMixin, viewsets.ModelViewSet):
    """Company management - scoped to tenant and user permissions."""
    queryset = Companies.objects.all()
    serializer_class = CompanySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["name"]
    search_fields = ["name"]
    ordering_fields = ["created_at", "updated_at", "name"]
    ordering = ["-created_at"]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Companies.objects.none()

        # Apply tenant scoping first, then user-level filtering
        qs = super().get_queryset()
        # Companies.objects.for_user filters based on user permissions
        return qs


class UserDetailsView(BaseUserDetailsView):
    """Enhanced user details view with staff and group info"""
    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        response.data['is_staff'] = request.user.is_staff
        response.data['is_superuser'] = request.user.is_superuser
        response.data['is_active'] = request.user.is_active
        # Add user groups to the response (tenant-scoped)
        tenant_groups = request.user.get_tenant_groups() if hasattr(request.user, 'get_tenant_groups') else []
        response.data['groups'] = [{'id': group.id, 'name': group.name} for group in tenant_groups]
        return response


class UserInvitationViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing user invitations.

    Provides endpoints for:
    - Listing invitations (staff only)
    - Validating invitation tokens (public)
    - Accepting invitations (public)
    - Resending invitations (staff only)
    """
    queryset = UserInvitation.objects.all()
    serializer_class = UserInvitationSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['user', 'invited_by', 'accepted_at']
    ordering_fields = ['sent_at', 'expires_at', 'accepted_at']
    ordering = ['-sent_at']
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        """Staff can see all invitations within tenant, others can't list"""
        if getattr(self, 'swagger_fake_view', False):
            return UserInvitation.objects.none()

        # Apply tenant scoping first
        qs = super().get_queryset().select_related('user', 'invited_by')

        if self.request.user and self.request.user.is_staff:
            return qs
        return qs.none()

    def get_permissions(self):
        """Allow unauthenticated access to validate and accept actions"""
        from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser

        if self.action in ['validate_token', 'accept_invitation']:
            return [AllowAny()]
        elif self.action in ['resend']:
            return [IsAdminUser()]
        return [IsAuthenticated()]

    @extend_schema(request=inline_serializer(name="ValidateTokenInput", fields={"token": serializers.CharField()}),
                   responses={200: inline_serializer(name="ValidateTokenResponse",
                                                     fields={"valid": serializers.BooleanField(),
                                                             "user_email": serializers.EmailField(),
                                                             "expires_at": serializers.DateTimeField(),
                                                             "expired": serializers.BooleanField()})})
    @action(detail=False, methods=['post'], url_path='validate-token')
    def validate_token(self, request):
        """Validate an invitation token (public endpoint)"""
        token = request.data.get('token')

        if not token:
            return Response({"detail": "Token is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            invitation = UserInvitation.objects.select_related('user').get(token=token)

            return Response({"valid": invitation.is_valid(), "user_email": invitation.user.email,
                             "user_first_name": invitation.user.first_name, "user_last_name": invitation.user.last_name,
                             "expires_at": invitation.expires_at, "expired": invitation.is_expired(),
                             "already_accepted": invitation.accepted_at is not None})
        except UserInvitation.DoesNotExist:
            return Response({"valid": False, "detail": "Invalid invitation token"}, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(request=inline_serializer(name="AcceptInvitationInput", fields={"token": serializers.CharField(),
                                                                                   "password": serializers.CharField(
                                                                                       write_only=True),
                                                                                   "opt_in_notifications": serializers.BooleanField(
                                                                                       default=False)}), responses={
        200: inline_serializer(name="AcceptInvitationResponse",
                               fields={"detail": serializers.CharField(), "user_id": serializers.IntegerField()})})
    @action(detail=False, methods=['post'], url_path='accept')
    def accept_invitation(self, request):
        """Accept an invitation and set up user account (public endpoint)"""
        from datetime import timedelta

        token = request.data.get('token')
        password = request.data.get('password')
        opt_in_notifications = request.data.get('opt_in_notifications', False)

        if not token or not password:
            return Response({"detail": "Token and password are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            invitation = UserInvitation.objects.select_related('user').get(token=token)
        except UserInvitation.DoesNotExist:
            return Response({"detail": "Invalid invitation token"}, status=status.HTTP_404_NOT_FOUND)

        # Check if valid
        if not invitation.is_valid():
            if invitation.accepted_at:
                return Response({"detail": "This invitation has already been accepted"},
                                status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"detail": "This invitation has expired"}, status=status.HTTP_400_BAD_REQUEST)

        # Set password and activate user
        user = invitation.user
        user.set_password(password)
        user.is_active = True
        user.save()

        # Mark invitation as accepted with metadata
        invitation.accepted_at = timezone.now()
        invitation.accepted_ip_address = self.get_client_ip(request)
        invitation.accepted_user_agent = request.META.get('HTTP_USER_AGENT', '')
        invitation.save()

        # Create notification preference if opted in
        if opt_in_notifications:
            from Tracker.models import NotificationTask
            NotificationTask.objects.create(recipient=user, notification_type='WEEKLY_REPORT', channel_type='email',
                                            interval_type='fixed', day_of_week=4,  # Friday
                                            time=timezone.now().time().replace(hour=15, minute=0),  # 3 PM
                                            interval_weeks=1, next_send_at=timezone.now() + timedelta(days=7))

        return Response({"detail": "Account activated successfully", "user_id": user.id, "email": user.email},
                        status=status.HTTP_200_OK)

    @extend_schema(
        request=inline_serializer(name="ResendInvitationInput", fields={"invitation_id": serializers.IntegerField()}),
        responses={200: OpenApiResponse(response=dict, description="Invitation resent successfully")})
    @action(detail=False, methods=['post'], url_path='resend')
    def resend(self, request):
        """Resend an invitation (staff only)"""
        from datetime import timedelta

        invitation_id = request.data.get('invitation_id')

        if not invitation_id:
            return Response({"detail": "invitation_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            invitation = UserInvitation.objects.select_related('user').get(id=invitation_id)
        except UserInvitation.DoesNotExist:
            return Response({"detail": "Invitation not found"}, status=status.HTTP_404_NOT_FOUND)

        # Can't resend accepted invitations
        if invitation.accepted_at:
            return Response({"detail": "Cannot resend an accepted invitation"}, status=status.HTTP_400_BAD_REQUEST)

        # Create new invitation (invalidates old token)
        new_invitation = UserInvitation.objects.create(user=invitation.user, invited_by=request.user,
                                                       token=UserInvitation.generate_token(),
                                                       expires_at=timezone.now() + timedelta(days=7))

        # Send invitation email via Celery
        from Tracker.email_notifications import send_invitation_email
        send_invitation_email(new_invitation.id, immediate=False)

        return Response({"detail": "Invitation resent successfully", "invitation_id": new_invitation.id,
                         "user_email": new_invitation.user.email, "expires_at": new_invitation.expires_at},
                        status=status.HTTP_200_OK)

    def get_client_ip(self, request):
        """Extract client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# ===== DOCUMENT VIEWSETS =====

@extend_schema_view(
    create=extend_schema(request={'multipart/form-data': DocumentsSerializer}),
    update=extend_schema(request={'multipart/form-data': DocumentsSerializer}),
    partial_update=extend_schema(request={'multipart/form-data': DocumentsSerializer})
)
class DocumentViewSet(TenantScopedMixin, ListMetadataMixin, ExcelExportMixin, viewsets.ModelViewSet):
    """ViewSet for managing document attachments (universal infrastructure)"""
    queryset = Documents.objects.all()
    serializer_class = DocumentsSerializer
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["content_type", "object_id", "is_image", "status"]
    search_fields = ["file_name", "uploaded_by__email"]
    ordering_fields = ["upload_date", "version", "file_name"]
    ordering = ["-upload_date"]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Documents.objects.none()

        # Layered security filtering:
        # 1. Tenant scoping (from TenantScopedMixin via super())
        # 2. User filtering (export control + classification + ownership)
        queryset = (
            super().get_queryset()
            .select_related("uploaded_by", "content_type")
        )

        # Handle needs_my_approval filter
        needs_my_approval = self.request.query_params.get('needs_my_approval', '').lower() == 'true'
        if needs_my_approval:
            user = self.request.user
            doc_ct = ContentType.objects.get_for_model(Documents)
            user_groups = user.get_tenant_groups() if hasattr(user, 'get_tenant_groups') else []
            user_group_ids = [g.id for g in user_groups]
            needs_my_approval_ids = ApprovalRequest.objects.filter(
                content_type=doc_ct,
                status='PENDING'
            ).filter(
                models.Q(approver_assignments__user=user) |
                models.Q(group_assignments__group_id__in=user_group_ids)
            ).exclude(
                responses__approver=user
            ).values_list('object_id', flat=True).distinct()
            # Convert string object_ids to UUIDs for proper comparison
            from uuid import UUID
            uuid_ids = [UUID(oid) for oid in needs_my_approval_ids if oid]
            queryset = queryset.filter(id__in=uuid_ids)

        return queryset

    def perform_create(self, serializer):
        doc = serializer.save(
            uploaded_by=self.request.user
        )  # Note: Embedding is automatically triggered by the post_save signal in signals.py

    def perform_update(self, serializer):
        instance = self.get_object()
        old_file = instance.file
        old_ai_readable = instance.ai_readable
        old_status = instance.status
        new_status = serializer.validated_data.get('status', old_status)

        # Block file changes on approved/released documents
        if instance.status in ('APPROVED', 'RELEASED'):
            if 'file' in serializer.validated_data:
                raise serializers.ValidationError({
                    "file": "Cannot change file on approved/released documents. Create a new revision instead."
                })

        # Enforce approval requirement when transitioning to RELEASED
        if new_status == 'RELEASED' and old_status != 'RELEASED':
            if instance.document_type and instance.document_type.requires_approval:
                # Check if document has an approved ApprovalRequest
                from django.contrib.contenttypes.models import ContentType
                from Tracker.models import ApprovalRequest, Approval_Status_Type
                content_type = ContentType.objects.get_for_model(instance)
                has_approval = ApprovalRequest.objects.filter(
                    content_type=content_type,
                    object_id=str(instance.id),
                    status=Approval_Status_Type.APPROVED
                ).exists()

                if not has_approval:
                    raise serializers.ValidationError({
                        "status": f"Cannot release document of type '{instance.document_type.name}' without approval. "
                                  "Submit for approval first using the submit-for-approval endpoint."
                    })

        doc = serializer.save()

        # Handle AI readability changes
        if doc.archived:
            # Archived documents should not be AI readable
            if doc.ai_readable:
                doc.ai_readable = False
                doc.save(update_fields=["ai_readable"])
                # Clean up existing chunks
                doc.chunks.all().delete()
        elif doc.ai_readable and not old_ai_readable:
            # User wants to make it AI readable
            # Note: Embedding is automatically triggered by the post_save signal in signals.py
            pass
        elif not doc.ai_readable and old_ai_readable:
            # User wants to make it NOT AI readable - clean up chunks
            doc.chunks.all().delete()
        elif doc.ai_readable and 'file' in serializer.validated_data and old_file != doc.file:
            # File changed and user wants it to remain AI readable - re-embed
            doc.chunks.all().delete()  # Clean up old chunks
            # Note: Re-embedding is automatically triggered by the post_save signal in signals.py

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        # Use model method for access logging
        instance.log_access(request.user, request)

        return Response(self.get_serializer(instance).data)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download the actual file"""
        document = self.get_object()

        # Log access as download (not just view)
        document.log_access(request.user, request, action_type='download')

        if not document.file:
            return Response({"detail": "No file attached"}, status=status.HTTP_404_NOT_FOUND)

        try:
            response = FileResponse(
                document.file.open('rb'),
                as_attachment=True,
                filename=document.file_name or os.path.basename(document.file.name)
            )
            return response
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error serving file: {e}")
            return Response(
                {"detail": "Error serving file"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='submit-for-approval')
    def submit_for_approval(self, request, pk=None):
        """Submit document for approval workflow"""
        document = self.get_object()

        try:
            approval_request = document.submit_for_approval(request.user)
            from Tracker.serializers.core import ApprovalRequestSerializer
            return Response(
                ApprovalRequestSerializer(approval_request, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to submit for approval: {e}")
            return Response(
                {"error": "Failed to submit for approval"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def revise(self, request, pk=None):
        """Create a new revision of this document.

        Requires:
        - file: The new file for the revision (optional - can keep same file)
        - change_justification: Reason for the revision (required)

        The new version will:
        - Increment the version number
        - Link to the previous version
        - Reset status to DRAFT
        - Preserve document_type, classification, and linked object
        """
        document = self.get_object()

        # Validate change justification is provided
        change_justification = request.data.get('change_justification', '').strip()
        if not change_justification:
            return Response(
                {"error": "change_justification is required when creating a revision"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check document is current version
        if not document.is_current_version:
            return Response(
                {"error": "Can only create revisions from the current version"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Build field updates for new version
            field_updates = {
                'change_justification': change_justification,
                'status': 'DRAFT',
                'approved_by': None,
                'approved_at': None,
                'uploaded_by': request.user,
            }

            # Handle new file if provided
            new_file = request.FILES.get('file')
            if new_file:
                field_updates['file'] = new_file
                field_updates['file_name'] = request.data.get('file_name', new_file.name)
                # Auto-detect if image
                field_updates['is_image'] = new_file.content_type.startswith('image/')

            # Create new version using model method
            new_version = document.create_new_version(**field_updates)

            serializer = self.get_serializer(new_version, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to create revision: {e}")
            return Response(
                {"error": "Failed to create revision"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'], url_path='version-history')
    def version_history(self, request, pk=None):
        """Get the full version history for this document"""
        document = self.get_object()
        versions = document.get_version_history()
        serializer = self.get_serializer(versions, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def release(self, request, pk=None):
        """
        Release an approved document.

        Sets status to RELEASED and calculates compliance dates (effective_date,
        review_date, retention_until) based on document_type settings.

        Optional body:
        - effective_date: Override the effective date (ISO format, defaults to today)
        """
        document = self.get_object()

        effective_date = None
        if 'effective_date' in request.data:
            from datetime import datetime
            try:
                effective_date = datetime.strptime(request.data['effective_date'], '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {"error": "effective_date must be in YYYY-MM-DD format"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        try:
            document.release(request.user, effective_date)
            return Response(
                self.get_serializer(document, context={'request': request}).data,
                status=status.HTTP_200_OK
            )
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], url_path='mark-obsolete')
    def mark_obsolete(self, request, pk=None):
        """
        Mark a released/approved document as obsolete.

        Sets status to OBSOLETE and records the obsolete_date.
        """
        document = self.get_object()

        try:
            document.mark_obsolete(request.user)
            return Response(
                self.get_serializer(document, context={'request': request}).data,
                status=status.HTTP_200_OK
            )
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'], url_path='due-for-review')
    def due_for_review(self, request):
        """
        Get documents that are due for periodic review.

        Returns documents where review_date <= today.
        """
        from datetime import date
        queryset = self.get_queryset().filter(
            review_date__lte=date.today(),
            status='RELEASED'
        ).order_by('review_date')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get document statistics for dashboard"""
        user = request.user
        queryset = self.get_queryset()

        # Get pending approval count for documents
        from django.contrib.contenttypes.models import ContentType
        doc_ct = ContentType.objects.get_for_model(Documents)
        pending_approval_ids = ApprovalRequest.objects.filter(
            content_type=doc_ct,
            status='PENDING'
        ).values_list('object_id', flat=True)

        # Get documents needing user's approval (tenant-scoped groups)
        user_groups = user.get_tenant_groups() if hasattr(user, 'get_tenant_groups') else []
        user_group_ids = [g.id for g in user_groups]
        needs_my_approval_ids = ApprovalRequest.objects.filter(
            content_type=doc_ct,
            status='PENDING'
        ).filter(
            models.Q(approver_assignments__user=user) |
            models.Q(group_assignments__group_id__in=user_group_ids)
        ).exclude(
            responses__approver=user
        ).values_list('object_id', flat=True).distinct()

        # Convert string object_ids to UUIDs for proper comparison
        from uuid import UUID
        pending_uuid_ids = [UUID(oid) for oid in pending_approval_ids if oid]
        needs_my_uuid_ids = [UUID(oid) for oid in needs_my_approval_ids if oid]

        # DMS Compliance: Count documents due for review
        from datetime import date
        today = date.today()
        due_for_review_count = queryset.filter(
            review_date__lte=today,
            status='RELEASED'
        ).count()

        stats = {
            'total': queryset.count(),
            'pending_approval': queryset.filter(id__in=pending_uuid_ids).count(),
            'needs_my_approval': queryset.filter(id__in=needs_my_uuid_ids).count(),
            'my_uploads': queryset.filter(uploaded_by=user).count(),
            'by_classification': {},
            'by_status': {},
            'recent_count': queryset.filter(
                upload_date__gte=timezone.now() - timezone.timedelta(days=30)
            ).count(),
            # DMS Compliance stats
            'due_for_review': due_for_review_count,
            'released': queryset.filter(status='RELEASED').count(),
            'obsolete': queryset.filter(status='OBSOLETE').count(),
        }

        # Count by classification
        for doc in queryset.values('classification').annotate(count=models.Count('id')):
            if doc['classification']:
                stats['by_classification'][doc['classification'].lower()] = doc['count']

        # Count by status
        for doc in queryset.values('status').annotate(count=models.Count('id')):
            if doc['status']:
                stats['by_status'][doc['status'].lower()] = doc['count']

        return Response(stats)

    @action(detail=False, methods=['get'], url_path='my-uploads')
    def my_uploads(self, request):
        """Get documents uploaded by the current user"""
        queryset = self.get_queryset().filter(uploaded_by=request.user)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='recent')
    def recent(self, request):
        """Get recently updated documents"""
        queryset = self.get_queryset().order_by('-updated_at')[:10]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


# ===== DOCUMENT TYPE VIEWSET =====

class DocumentTypeViewSet(TenantScopedMixin, ListMetadataMixin, ExcelExportMixin, viewsets.ModelViewSet):
    """ViewSet for managing document types"""
    queryset = DocumentType.objects.all()
    serializer_class = DocumentTypeSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['requires_approval']
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['name', 'code', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return DocumentType.objects.none()
        return super().get_queryset().filter(archived=False)


# ===== CONTENT TYPE & AUDIT LOG VIEWSETS =====

class ContentTypeViewSet(ReadOnlyModelViewSet):
    queryset = ContentType.objects.all()
    serializer_class = ContentTypeSerializer
    pagination_class = None  # Content types are a small fixed set, no need to paginate

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return ContentType.objects.none()

        return ContentType.objects.all()


class LogEntryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LogEntry.objects.all()
    serializer_class = AuditLogSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["actor", "content_type", "object_pk", "action"]
    search_fields = ["object_repr", "changes"]
    ordering_fields = ["timestamp"]
    ordering = ["-timestamp"]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return LogEntry.objects.none()

        # LogEntry doesn't have SecureManager, so use the base queryset
        return self.queryset


# ===== APPROVAL WORKFLOW VIEWSETS =====

@extend_schema_view(
    list=extend_schema(
        description="List approval templates with filtering and search",
        parameters=[
            OpenApiParameter(name='approval_type', description='Filter by approval type', required=False, type=str),
            OpenApiParameter(name='active', description='Filter by active status', required=False, type=bool),
        ]
    ),
    create=extend_schema(description="Create a new approval template"),
    retrieve=extend_schema(description="Retrieve a specific approval template"),
    update=extend_schema(description="Update an approval template"),
    partial_update=extend_schema(description="Partially update an approval template"),
    destroy=extend_schema(description="Soft delete an approval template")
)
class ApprovalTemplateViewSet(TenantScopedMixin, ListMetadataMixin, ExcelExportMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing approval templates.

    Approval templates define the rules and default settings for approval workflows,
    including approver assignments, sequence types, delegation policies, and SLA settings.
    """
    queryset = ApprovalTemplate.objects.all()
    serializer_class = ApprovalTemplateSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['approval_type', 'approval_flow_type', 'delegation_policy', 'approval_sequence']
    search_fields = ['template_name', 'approval_type']
    ordering_fields = ['template_name', 'created_at', 'updated_at']
    ordering = ['template_name']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return ApprovalTemplate.objects.none()

        # Apply tenant scoping first, then user-level filtering
        queryset = super().get_queryset()

        # Filter for active templates (deactivated_at is null)
        active_only = self.request.query_params.get('active', 'true').lower() == 'true'
        if active_only:
            queryset = queryset.filter(deactivated_at__isnull=True)

        return queryset.select_related().prefetch_related('default_approvers', 'default_groups')

    @action(detail=True, methods=['post'], url_path='deactivate')
    def deactivate(self, request, pk=None):
        """Deactivate an approval template"""
        # Check permission
        if not request.user.has_tenant_perm('manage_approval_workflow'):
            return Response(
                {'error': 'You do not have permission to manage approval templates'},
                status=status.HTTP_403_FORBIDDEN
            )

        template = self.get_object()
        template.deactivated_at = timezone.now()
        template.save(update_fields=['deactivated_at'])
        return Response({'status': 'Template deactivated'})

    @action(detail=True, methods=['post'], url_path='activate')
    def activate(self, request, pk=None):
        """Reactivate an approval template"""
        # Check permission
        if not request.user.has_tenant_perm('manage_approval_workflow'):
            return Response(
                {'error': 'You do not have permission to manage approval templates'},
                status=status.HTTP_403_FORBIDDEN
            )

        template = self.get_object()
        template.deactivated_at = None
        template.save(update_fields=['deactivated_at'])
        return Response({'status': 'Template activated'})


@extend_schema_view(
    list=extend_schema(
        description="List approval requests with filtering and search",
        parameters=[
            OpenApiParameter(name='status', description='Filter by status (PENDING, APPROVED, REJECTED, CANCELLED)',
                             required=False, type=str),
            OpenApiParameter(name='approval_type', description='Filter by approval type', required=False, type=str),
            OpenApiParameter(name='requested_by', description='Filter by requester user ID', required=False, type=int),
            OpenApiParameter(name='overdue', description='Show only overdue approvals', required=False, type=bool),
        ]
    ),
    create=extend_schema(description="Create a new approval request"),
    retrieve=extend_schema(description="Retrieve a specific approval request"),
    update=extend_schema(description="Update an approval request"),
    partial_update=extend_schema(description="Partially update an approval request"),
    destroy=extend_schema(description="Cancel an approval request")
)
class ApprovalRequestViewSet(TenantScopedMixin, ListMetadataMixin, ExcelExportMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing approval requests.

    Approval requests track the approval workflow for specific content objects,
    managing approver assignments, responses, status tracking, and escalations.
    """
    queryset = ApprovalRequest.objects.all()
    serializer_class = ApprovalRequestSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'approval_type', 'requested_by', 'content_type', 'object_id']
    search_fields = ['approval_number', 'reason', 'notes']
    ordering_fields = ['requested_at', 'completed_at', 'due_date', 'approval_number']
    ordering = ['-requested_at']
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return ApprovalRequest.objects.none()

        # Apply tenant scoping first, then user-level filtering
        queryset = super().get_queryset()
        queryset = queryset.select_related(
            'requested_by', 'content_type'
        ).prefetch_related(
            'responses', 'responses__approver',
            'approver_assignments', 'approver_assignments__user', 'approver_assignments__assigned_by',
            'group_assignments', 'group_assignments__group'
        )

        # Filter for overdue approvals if requested
        overdue = self.request.query_params.get('overdue', '').lower() == 'true'
        if overdue:
            queryset = [req for req in queryset if req.is_overdue()]
            # Convert back to queryset
            ids = [req.id for req in queryset]
            queryset = ApprovalRequest.objects.filter(id__in=ids)

        return queryset

    def perform_create(self, serializer):
        """Auto-generate approval number and set requested_by"""
        tenant = self.tenant
        serializer.save(
            tenant=tenant,
            requested_by=self.request.user,
            approval_number=ApprovalRequest.generate_approval_number(tenant=tenant)
        )

    def perform_destroy(self, instance):
        """Cancel the approval instead of hard deleting"""
        instance.status = 'CANCELLED'
        instance.save(update_fields=['status'])

    @action(detail=True, methods=['get'], url_path='pending-approvers')
    def pending_approvers(self, request, pk=None):
        """Get list of pending approvers for this request"""
        approval = self.get_object()
        pending = approval.get_pending_approvers()
        from Tracker.serializers import UserSelectSerializer
        return Response(UserSelectSerializer(pending, many=True).data)

    @action(detail=True, methods=['post'], url_path='submit-response')
    def submit_response(self, request, pk=None):
        """Submit an approval response (approve/reject/delegate)"""
        approval = self.get_object()

        # Check permission
        if not request.user.has_tenant_perm('respond_to_approval'):
            return Response(
                {'error': 'You do not have permission to respond to approval requests'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if user is an assigned approver
        if not approval.can_approve(request.user):
            return Response(
                {'error': 'You are not assigned as an approver for this request'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Validate required fields
        decision = request.data.get('decision')
        if not decision:
            return Response(
                {'error': 'Decision is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Use the model's submit_response method
            response = ApprovalResponse.submit_response(
                approval_request=approval,
                approver=request.user,
                decision=decision,
                comments=request.data.get('comments'),
                signature_data=request.data.get('signature_data'),
                signature_meaning=request.data.get('signature_meaning'),
                password=request.data.get('password'),
                ip_address=request.META.get('REMOTE_ADDR')
            )

            return Response(ApprovalResponseSerializer(response).data)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @extend_schema(
        description="Get all approval requests pending for current user",
        responses={200: ApprovalRequestSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='my-pending')
    def my_pending(self, request):
        """Get all approval requests pending for current user"""
        user = request.user

        # Find approvals where user is assigned and hasn't responded (tenant-scoped groups)
        user_groups = user.get_tenant_groups() if hasattr(user, 'get_tenant_groups') else []
        user_group_ids = [g.id for g in user_groups]
        pending_approvals = ApprovalRequest.objects.filter(
            status='PENDING'
        ).filter(
            models.Q(approver_assignments__user=user) |
            models.Q(group_assignments__group_id__in=user_group_ids)
        ).exclude(
            responses__approver=user
        ).distinct()

        page = self.paginate_queryset(pending_approvals)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(pending_approvals, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        description="List approval responses with filtering",
        parameters=[
            OpenApiParameter(name='approval_request', description='Filter by approval request ID',
                             required=False, type=int),
            OpenApiParameter(name='approver', description='Filter by approver user ID', required=False, type=int),
            OpenApiParameter(name='decision', description='Filter by decision (APPROVED, REJECTED, DELEGATED)',
                             required=False, type=str),
        ]
    ),
    create=extend_schema(description="Create a new approval response"),
    retrieve=extend_schema(description="Retrieve a specific approval response"),
    update=extend_schema(description="Update an approval response"),
    partial_update=extend_schema(description="Partially update an approval response"),
)
class ApprovalResponseViewSet(TenantScopedMixin, ListMetadataMixin, ExcelExportMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing approval responses.

    Approval responses record individual approver decisions with signature capture,
    identity verification, and delegation support.
    """
    queryset = ApprovalResponse.objects.all()
    serializer_class = ApprovalResponseSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['approval_request', 'approver', 'decision', 'verification_method']
    ordering_fields = ['decision_date', 'responded_at']
    ordering = ['-decision_date']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return ApprovalResponse.objects.none()

        # Apply tenant scoping first, then user-level filtering
        queryset = super().get_queryset()
        return queryset.select_related(
            'approval_request', 'approver', 'delegated_to'
        )

    @action(detail=True, methods=['post'], url_path='delegate')
    def delegate(self, request, pk=None):
        """Delegate this approval to another user"""
        response = self.get_object()

        # Check permission - user must have respond_to_approval permission
        if not request.user.has_tenant_perm('respond_to_approval'):
            return Response(
                {'error': 'You do not have permission to delegate approval requests'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if user is the approver for this response
        if response.approver != request.user:
            return Response(
                {'error': 'You can only delegate your own approval responses'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Validate required fields
        delegatee_id = request.data.get('delegatee_id')
        reason = request.data.get('reason')

        if not delegatee_id or not reason:
            return Response(
                {'error': 'delegatee_id and reason are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            delegatee = User.objects.get(id=delegatee_id)
            response.delegate_to(delegatee, reason)
            return Response(ApprovalResponseSerializer(response).data)

        except User.DoesNotExist:
            return Response(
                {'error': 'Delegatee user not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


# ===== SCOPE VIEW =====

class ScopeView(viewsets.ViewSet):
    """
    Generic scope endpoint for querying related objects across the model graph.

    Solves the N+1 endpoint problem by allowing clients to compose queries
    for related data without creating custom endpoints for each use case.

    Usage:
        GET /api/scope/?root=orders:123&include=documents
        GET /api/scope/?root=orders:123&include=documents,annotations,stats
        GET /api/scope/?root=parttypes:45&include=documents&classification=public
    """
    permission_classes = [IsAuthenticated]

    # Registry of includable types with their model, serializer, and filters
    INCLUDABLES = {
        'documents': {
            'model': Documents,
            'serializer': DocumentsSerializer,
            'filters': ['classification'],
            'select_related': ['uploaded_by', 'approved_by', 'content_type'],
        },
    }

    # Models to exclude from traversal by default (audit/log tables that slow queries)
    # These are typically not needed for document/annotation lookups
    DEFAULT_EXCLUDE_MODELS = [
        'samplingauditlog',
        'steptransitionlog',
        'samplingtriggerstate',
        'equipmentusage',
    ]

    def _get_exclude_types(self):
        """Get model classes to exclude from traversal for performance."""
        from django.apps import apps
        exclude_types = []
        for model_name in self.DEFAULT_EXCLUDE_MODELS:
            try:
                model_class = apps.get_model('Tracker', model_name)
                exclude_types.append(model_class)
            except LookupError:
                pass  # Model doesn't exist, skip
        return exclude_types

    def _parse_root(self, root_param):
        """Parse root parameter like 'orders:123' into (model_class, object_id)."""
        from django.apps import apps

        if not root_param or ':' not in root_param:
            raise ValueError("root must be in format 'model:id' (e.g., 'orders:123')")

        model_name, obj_id = root_param.split(':', 1)

        try:
            obj_id = int(obj_id)
        except ValueError:
            raise ValueError(f"Invalid object ID: {obj_id}")

        try:
            model_class = apps.get_model('Tracker', model_name)
        except LookupError:
            raise ValueError(f"Unknown model: {model_name}")

        return model_class, obj_id

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='root',
                description="Root object in format 'model:id' (e.g., 'orders:123')",
                required=True,
                type=str,
            ),
            OpenApiParameter(
                name='include',
                description="Comma-separated types: documents, stats",
                required=True,
                type=str,
            ),
            OpenApiParameter(
                name='direction',
                description="Traversal direction: 'down' (default) or 'up'",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name='classification',
                description="Filter documents by classification",
                required=False,
                type=str,
            ),
        ],
        responses={200: OpenApiResponse(description="Scoped query results")}
    )
    def list(self, request):
        """Query related objects across the model graph from a root object."""
        from Tracker.scope import related_to, count_descendants

        # Parse root
        root_param = request.query_params.get('root')
        if not root_param:
            return Response(
                {'error': "root parameter required (e.g., 'orders:123')"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            model_class, obj_id = self._parse_root(root_param)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Get root object with permission check
        try:
            if hasattr(model_class.objects, 'for_user'):
                root_obj = model_class.objects.for_user(request.user).get(pk=obj_id)
            else:
                root_obj = model_class.objects.get(pk=obj_id)
        except model_class.DoesNotExist:
            return Response(
                {'error': f'{model_class.__name__} {obj_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Parse include
        include_param = request.query_params.get('include')
        if not include_param:
            return Response(
                {'error': "include parameter required (e.g., 'documents')"},
                status=status.HTTP_400_BAD_REQUEST
            )

        include_types = [t.strip().lower() for t in include_param.split(',')]

        # Validate
        valid_types = list(self.INCLUDABLES.keys()) + ['stats']
        invalid = [t for t in include_types if t not in valid_types]
        if invalid:
            return Response(
                {'error': f"Unknown types: {invalid}. Valid: {valid_types}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Direction
        direction = request.query_params.get('direction', 'down')
        if direction not in ('down', 'up'):
            return Response(
                {'error': "direction must be 'down' or 'up'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Build response
        result = {}

        # Get exclude types for performance (skip audit/log tables)
        exclude_types = self._get_exclude_types()

        for include_type in include_types:
            if include_type == 'stats':
                result['stats'] = count_descendants(
                    root_obj, user=request.user, exclude_types=exclude_types
                )
                continue

            config = self.INCLUDABLES[include_type]
            model = config['model']
            serializer_class = config['serializer']

            # Get related objects (with exclusions for performance)
            queryset = related_to(
                model, root_obj,
                user=request.user,
                direction=direction,
                exclude_types=exclude_types
            )

            # Apply filters
            for filter_name in config.get('filters', []):
                filter_value = request.query_params.get(filter_name)
                if filter_value:
                    queryset = queryset.filter(**{filter_name: filter_value})

            # Optimize queries with select_related for FK fields
            select_related_fields = config.get('select_related', [])
            if select_related_fields:
                queryset = queryset.select_related(*select_related_fields)

            serializer = serializer_class(queryset, many=True, context={'request': request})
            result[include_type] = serializer.data

        return Response(result)


# ===== MEDIA SERVING FUNCTION =====

@xframe_options_exempt
def serve_media_iframe_safe(request, path):
    """
    Serve media files (PDFs, images, 3D models, etc.) with iframe-safe headers.

    This function allows media files to be embedded in iframes from localhost:5173
    (the frontend development server). It sets appropriate CSP and CORS headers.
    """
    import mimetypes

    full_path = os.path.join(settings.MEDIA_ROOT, path)
    if not os.path.exists(full_path):
        raise Http404()

    # Detect content type based on file extension
    content_type, _ = mimetypes.guess_type(full_path)

    # Handle special cases for 3D model files
    ext = os.path.splitext(full_path)[1].lower()
    if ext == '.glb':
        content_type = 'model/gltf-binary'
    elif ext == '.gltf':
        content_type = 'model/gltf+json'
    elif content_type is None:
        content_type = 'application/octet-stream'

    response = FileResponse(open(full_path, 'rb'), content_type=content_type)
    response["Content-Disposition"] = f'inline; filename="{os.path.basename(full_path)}"'
    response["Content-Security-Policy"] = "frame-ancestors http://localhost:5173"
    # CORS headers for frontend dev server
    response["Access-Control-Allow-Origin"] = "http://localhost:5173"
    response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response["Access-Control-Allow-Headers"] = "Content-Type"
    return response

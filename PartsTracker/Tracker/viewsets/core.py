# viewsets/core.py - Core infrastructure (Users, Companies, Auth, Approvals, Documents, Mixins)
import logging
import os
from typing import Any, Dict, List, Optional
import pandas as pd
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
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

from Tracker.filters import UserFilter, DocumentFilter
from Tracker.permissions import TenantAccessPermission
from Tracker.models.core import User, Companies, UserInvitation, ApprovalTemplate, ApprovalRequest, ApprovalResponse, Documents, DocumentType
from Tracker.serializers.core import (
    UserSerializer, UserSelectSerializer, UserDetailSerializer,
    TenantAwareUserDetailsSerializer,
    CompanySerializer, UserInvitationSerializer,
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
    """Select list for employees (the tenant's internal workforce)."""
    queryset = User.objects.all()
    serializer_class = UserSelectSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return User.objects.none()

        # Apply tenant scoping, then filter to the tenant's internal employees.
        # NOT is_staff — in this system is_staff marks platform/UQMES staff (only
        # a handful per tenant), so it wrongly collapsed the picker to one name.
        # The workforce is user_type='INTERNAL' (PORTAL = external customers).
        return super().get_queryset().filter(user_type='INTERNAL', is_active=True)


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
    queryset = User.objects.all()  # Base queryset - filtered in get_queryset()
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

        # Start with the base queryset from parent (applies standard mixin processing)
        qs = super().get_queryset().select_related('parent_company', 'tenant')

        user = self.request.user
        request_tenant = self.tenant  # From middleware

        # Platform staff (UQMES) see all users, optionally filtered by request tenant
        if user.is_staff or user.is_superuser:
            if request_tenant:
                return qs.filter(tenant=request_tenant)
            return qs

        # Check tenant group membership for the request tenant context
        tenant_for_groups = request_tenant or user.tenant
        user_group_names = set()
        if tenant_for_groups and hasattr(user, 'get_tenant_group_names'):
            user_group_names = user.get_tenant_group_names(tenant_for_groups)

        is_customer_only = user_group_names and user_group_names <= {'Customer', 'Customers'}

        # Internal tenant users see all MEMBERS of the request tenant context.
        # Membership-based (not the home-tenant FK) so cross-tenant members
        # (e.g. consultants homed elsewhere) are visible and manageable here,
        # matching the access check. Suspended members are included so an admin
        # can still see and reactivate them.
        from Tracker.services.core.tenant_membership import member_user_ids
        if request_tenant and not is_customer_only:
            return qs.filter(id__in=member_user_ids(request_tenant))

        # Fallback: use user's own tenant if no request tenant context
        if user.tenant and not is_customer_only:
            return qs.filter(id__in=member_user_ids(user.tenant))

        # Portal/Customer users see only users from their company
        if user.parent_company:
            return qs.filter(parent_company=user.parent_company)

        # No tenant and no company - can only see themselves
        return qs.filter(id=user.id)

    @extend_schema(
        responses={200: OpenApiResponse(response=dict, description="Debug info about current user's filtering context")}
    )
    @action(detail=False, methods=['get'], url_path='debug-filter')
    def debug_filter(self, request):
        """Debug endpoint to show what filtering is applied to the current user"""
        user = request.user
        request_tenant = self.tenant  # From middleware (header/subdomain)
        tenant_for_groups = request_tenant or user.tenant

        user_group_names = set()
        if tenant_for_groups and hasattr(user, 'get_tenant_group_names'):
            user_group_names = user.get_tenant_group_names(tenant_for_groups)

        is_customer_only = bool(user_group_names and user_group_names <= {'Customer', 'Customers'})

        # Determine which branch of filtering will be applied (matches get_queryset logic)
        if user.is_staff or user.is_superuser:
            if request_tenant:
                filter_mode = "staff_tenant_filtered"
                queryset_count = User.objects.filter(tenant=request_tenant).count()
            else:
                filter_mode = "staff_all_users"
                queryset_count = User.objects.count()
        elif request_tenant and not is_customer_only:
            filter_mode = "request_tenant_users"
            queryset_count = User.objects.filter(tenant=request_tenant).count()
        elif user.tenant and not is_customer_only:
            filter_mode = "user_tenant_users"
            queryset_count = User.objects.filter(tenant=user.tenant).count()
        elif user.parent_company:
            filter_mode = "company_users"
            queryset_count = User.objects.filter(parent_company=user.parent_company).count()
        else:
            filter_mode = "self_only"
            queryset_count = 1

        return Response({
            "user_id": user.id,
            "email": user.email,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
            # Request tenant (from middleware)
            "request_tenant_id": str(request_tenant.id) if request_tenant else None,
            "request_tenant_name": request_tenant.name if request_tenant else None,
            "request_tenant_source": getattr(request, 'tenant_source', None),
            # User's own tenant
            "user_tenant_id": str(user.tenant_id) if user.tenant_id else None,
            "user_tenant_name": user.tenant.name if user.tenant else None,
            # Company
            "parent_company_id": str(user.parent_company_id) if user.parent_company_id else None,
            "parent_company_name": user.parent_company.name if user.parent_company else None,
            # Groups (evaluated in tenant context)
            "tenant_group_names": list(user_group_names),
            "is_customer_only": is_customer_only,
            "filter_mode": filter_mode,
            "queryset_count": queryset_count,
        })

    @extend_schema(request=inline_serializer(name="BulkUserActivationInput", fields={
        "user_ids": serializers.ListField(child=serializers.IntegerField()), "is_active": serializers.BooleanField()}),
                   responses={
                       200: OpenApiResponse(response=dict, description="Bulk activation response")})
    @action(detail=False, methods=['post'], url_path='bulk-activate')
    def bulk_activate(self, request):
        """Bulk activate/deactivate users **within the current tenant**.

        Tenant-scoped: suspends/reactivates the user's TenantMembership in the
        request tenant rather than flipping the GLOBAL `User.is_active` (which
        is reserved for platform admins). A user suspended here loses access to
        this tenant only; their account and any other tenant memberships are
        untouched. Request/response shape is unchanged.
        """
        from Tracker.services.core.tenant_membership import (
            suspend_membership, reactivate_membership,
        )

        user_ids = request.data.get('user_ids', [])
        is_active = request.data.get('is_active', True)

        if not user_ids:
            return Response({"detail": "No user IDs provided"}, status=status.HTTP_400_BAD_REQUEST)

        tenant = self.tenant  # request tenant (middleware)
        if tenant is None:
            return Response(
                {"detail": "No tenant context for membership change"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Filter to only users accessible by the requesting user (membership-scoped).
        targets = self.get_queryset().filter(id__in=user_ids)
        updated_count = 0
        for user in targets:
            if user.id == request.user.id:
                continue  # never let an admin suspend their own access
            if is_active:
                reactivate_membership(user, tenant)
            else:
                suspend_membership(user, tenant, by=request.user)
            updated_count += 1

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
        responses={201: inline_serializer(name="SendInvitationResponse", fields={
            "detail": serializers.CharField(),
            "invitation_id": serializers.IntegerField(),
            "user_email": serializers.EmailField(),
            "expires_at": serializers.DateTimeField(),
            "invitation_url": serializers.CharField(),
            "email_sent": serializers.BooleanField(),
        })})
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
            # Return the live link so an admin can copy it instead of hitting a
            # dead end — onboarding must work even when email delivery is off.
            return Response(
                {"detail": "User already has a pending invitation",
                 "invitation_id": existing_invitation.id,
                 "expires_at": existing_invitation.expires_at,
                 "invitation_url": f"{settings.FRONTEND_URL}/signup?token={existing_invitation.token}"},
                status=status.HTTP_400_BAD_REQUEST)

        # Create invitation
        invitation = UserInvitation.objects.create(user=user_to_invite, invited_by=request.user,
                                                   token=UserInvitation.generate_token(),
                                                   expires_at=timezone.now() + timedelta(days=7)  # 7 day expiration
                                                   )

        # Send invitation email — best-effort. The invitation row + copyable
        # link below are the source of truth; onboarding must not depend on a
        # working mail path (a misconfigured/disabled backend must not 500).
        email_sent = True
        try:
            from Tracker.email_notifications import send_invitation_email
            send_invitation_email(invitation.id, immediate=True)
        except Exception:  # noqa: BLE001 - surface link regardless of mail health
            email_sent = False
            logging.getLogger(__name__).warning(
                "Invitation email dispatch failed for invitation %s; returning link only",
                invitation.id, exc_info=True,
            )

        detail = ("Invitation sent successfully" if email_sent
                  else "Invitation created — email could not be sent, share the link directly")
        return Response({"detail": detail, "invitation_id": invitation.id,
                         "user_email": user_to_invite.email, "expires_at": invitation.expires_at,
                         "invitation_url": f"{settings.FRONTEND_URL}/signup?token={invitation.token}",
                         "email_sent": email_sent},
                        status=status.HTTP_201_CREATED)

    @extend_schema(
        request=inline_serializer(
            name="BulkReconcileUsersRequest",
            fields={
                "rows": serializers.ListField(
                    child=serializers.DictField(),
                    help_text=(
                        "List of row dicts: "
                        "{email, first_name, last_name, group, status, message}. "
                        "Either `rows` (this field) or a `file` upload must be provided."
                    ),
                    required=False,
                ),
            },
        ),
        responses={
            207: inline_serializer(
                name="BulkReconcileUsersResponse",
                fields={
                    "summary": inline_serializer(
                        name="BulkReconcileSummary",
                        fields={
                            "total": serializers.IntegerField(),
                            "created": serializers.IntegerField(),
                            "updated": serializers.IntegerField(),
                            "unchanged": serializers.IntegerField(),
                            "errors": serializers.IntegerField(),
                        },
                    ),
                    "results": serializers.ListField(child=serializers.DictField()),
                },
            ),
            400: {"description": "Bad request (no rows, bad file)"},
        },
        description=(
            "Reconcile the tenant's user roster to match a list of row "
            "descriptors. State-based: each row describes a desired user; "
            "missing emails are created + invited, existing emails are "
            "updated to match. Accepts either inline `rows` in JSON, or "
            "a CSV/Excel file upload via multipart form-data."
        ),
        tags=["Users"],
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="bulk-reconcile",
        parser_classes=[parsers.MultiPartParser, parsers.JSONParser],
    )
    def bulk_reconcile(self, request):
        """Bulk-reconcile tenant users from either inline rows or a workbook.

        See `Tracker.services.core.user_reconcile.reconcile_user_row` for
        per-row semantics. Sync if < 25 rows, otherwise the response
        includes a Celery task id to poll via `bulk-reconcile-status`.
        """
        from Tracker.services.core.user_reconcile import reconcile_user_row
        from Tracker.services.csv_utils import parse_file

        # Resolve tenant scope. Bulk-roster operations are admin-shaped;
        # the request must be tied to a specific tenant context.
        tenant = self.tenant or getattr(request.user, "tenant", None)
        if tenant is None:
            return Response(
                {"detail": "No tenant context. Cannot reconcile."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Collect rows from either a file upload or inline JSON.
        rows: Optional[List[Dict[str, Any]]] = None
        uploaded = request.FILES.get("file")
        if uploaded is not None:
            try:
                rows, _headers = parse_file(uploaded, uploaded.name)
            except ValueError as e:
                return Response(
                    {"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST,
                )
            except Exception as e:  # noqa: BLE001
                return Response(
                    {"detail": f"Error reading file: {e}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            inline = request.data.get("rows")
            if isinstance(inline, list):
                rows = inline

        if not rows:
            return Response(
                {"detail": "Provide a 'file' upload or non-empty 'rows' list."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Threshold: synchronous below 25, async above. Matches the
        # existing CSVImportMixin pattern so behavior is consistent.
        SYNC_LIMIT = 25
        if len(rows) >= SYNC_LIMIT:
            from uuid import uuid4
            from Tracker.tasks import bulk_reconcile_users_task
            task_id = str(uuid4())
            transaction.on_commit(lambda: bulk_reconcile_users_task.apply_async(
                kwargs={
                    "rows": rows,
                    "tenant_id": str(tenant.id),
                    "acting_user_id": request.user.id,
                },
                task_id=task_id,
            ))
            return Response(
                {
                    "task_id": task_id,
                    "status": "queued",
                    "total_rows": len(rows),
                    "message": (
                        f"Reconcile queued. Poll "
                        f"/api/User/bulk-reconcile-status/{task_id}/ for progress."
                    ),
                },
                status=status.HTTP_202_ACCEPTED,
            )

        # Synchronous path
        results: List[Dict[str, Any]] = []
        for i, row in enumerate(rows, start=1):
            res = reconcile_user_row(
                row=row, tenant=tenant, acting_user=request.user,
            )
            res["row"] = i
            results.append(res)

        summary = {
            "total": len(results),
            "created": sum(1 for r in results if r.get("outcome") == "created"),
            "updated": sum(1 for r in results if r.get("outcome") == "updated"),
            "unchanged": sum(1 for r in results if r.get("outcome") == "unchanged"),
            "errors": sum(1 for r in results if r.get("outcome") == "error"),
        }
        return Response(
            {"summary": summary, "results": results},
            status=status.HTTP_207_MULTI_STATUS,
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="task_id",
                location=OpenApiParameter.PATH,
                type=str,
                description="Celery task ID from a queued bulk-reconcile",
                required=True,
            ),
        ],
        responses={200: OpenApiResponse(response=dict, description="Task status + result if done")},
        tags=["Users"],
    )
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="populate",
                location=OpenApiParameter.QUERY,
                type=bool,
                required=False,
                description=(
                    "If true, pre-fill the Data sheet with the tenant's "
                    "current users (snapshot-and-edit workflow). Default "
                    "false returns an empty template (add-new-users workflow)."
                ),
            ),
        ],
        responses={200: {"type": "string", "format": "binary", "description": "XLSX workbook"}},
        description=(
            "Download a multi-sheet Excel template for bulk-reconcile. "
            "Sheets: Data (editable rows — parsed on import), Instructions, "
            "Groups (tenant-scoped names — drives Group dropdown), Statuses "
            "(Active/Inactive — drives Status dropdown). Pass populate=true "
            "to pre-fill the Data sheet with current users."
        ),
        tags=["Users"],
    )
    @action(detail=False, methods=["get"], url_path="bulk-reconcile-template")
    def bulk_reconcile_template(self, request):
        """Return the Excel workbook template populated with this tenant's groups,
        optionally pre-filled with the current user roster."""
        from Tracker.services.core.user_reconcile import build_user_reconcile_template

        tenant = self.tenant or getattr(request.user, "tenant", None)
        if tenant is None:
            return Response(
                {"detail": "No tenant context."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # `?populate=true` produces the snapshot-and-edit workbook. Anything
        # else (including absent / "false" / "0") returns the empty template.
        populate_raw = str(request.query_params.get("populate", "")).strip().lower()
        populate = populate_raw in ("1", "true", "yes", "y")

        content = build_user_reconcile_template(tenant, populate=populate)
        response = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        filename = (
            "bulk_user_reconcile_current.xlsx" if populate
            else "bulk_user_reconcile_template.xlsx"
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="task_id",
                location=OpenApiParameter.PATH,
                type=str,
                description="Celery task ID from a queued bulk-reconcile",
                required=True,
            ),
        ],
        responses={200: OpenApiResponse(response=dict, description="Task status + result if done")},
        tags=["Users"],
    )
    @action(
        detail=False,
        methods=["get"],
        url_path=r"bulk-reconcile-status/(?P<task_id>[^/.]+)",
    )
    def bulk_reconcile_status(self, request, task_id=None):
        """Poll a queued bulk reconcile job. Mirrors the CSV-import status pattern."""
        from celery.result import AsyncResult

        result = AsyncResult(task_id)
        payload: Dict[str, Any] = {"task_id": task_id, "status": result.status}
        if result.status == "PROGRESS":
            payload["progress"] = result.info or {}
        elif result.status == "SUCCESS":
            payload["result"] = result.result
        elif result.status == "FAILURE":
            payload["error"] = str(result.result) if result.result else "Unknown error"
        elif result.status == "PENDING":
            payload["progress"] = {"current": 0, "total": 0, "percent": 0}
        return Response(payload)


class CompanyViewSet(TenantScopedMixin, ListMetadataMixin, ExcelExportMixin, viewsets.ModelViewSet):
    """Company management - scoped to tenant and user permissions."""
    queryset = Companies.unscoped.all()
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
    """User details with staff flags + tenant-scoped groups.

    Fields are declared on the serializer (not injected post-hoc into
    `response.data`) so drf-spectacular emits them and the generated
    frontend client's response validation lets them through.
    """
    serializer_class = TenantAwareUserDetailsSerializer


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
        """Internal tenant users can see invitations within their tenant"""
        if getattr(self, 'swagger_fake_view', False):
            return UserInvitation.objects.none()

        user = self.request.user
        if not user:
            return UserInvitation.objects.none()

        # Apply tenant scoping first (uses self.tenant from middleware)
        qs = super().get_queryset().select_related('user', 'invited_by')

        # Platform staff see all (already tenant-filtered by super() if request tenant set)
        if user.is_staff or user.is_superuser:
            return qs

        # Check if internal tenant user (using request tenant context)
        request_tenant = self.tenant
        tenant_for_groups = request_tenant or user.tenant

        user_group_names = set()
        if tenant_for_groups and hasattr(user, 'get_tenant_group_names'):
            user_group_names = user.get_tenant_group_names(tenant_for_groups)

        is_customer_only = user_group_names and user_group_names <= {'Customer', 'Customers'}

        # Tenant users who aren't Customer-only can see invitations
        if (request_tenant or user.tenant) and not is_customer_only:
            return qs
        return qs.none()

    def get_permissions(self):
        """Allow unauthenticated access to validate and accept actions"""
        from rest_framework.permissions import AllowAny, IsAuthenticated

        if self.action in ['validate_token', 'accept_invitation']:
            return [AllowAny()]
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

        # If the invitee checked the "weekly order updates" opt-in box on
        # the activation form, create a personal NotificationSchedule for
        # them. This is an explicit user choice, not a silent default —
        # `opt_in_notifications=False` (unchecked) creates nothing, and the
        # user can always set up / change cadence from /profile.
        if opt_in_notifications and user.tenant_id:
            from datetime import time
            from Tracker.models import NotificationSchedule
            from Tracker.utils.tenant_context import tenant_context
            with tenant_context(user.tenant_id):
                NotificationSchedule.objects.create(
                    tenant=user.tenant,
                    owner_user=user,
                    scope_kind='personal',
                    name='Weekly orders summary',
                    description=(
                        'Opted in during account activation. Edit cadence or '
                        'turn off any time at /profile/notifications.'
                    ),
                    enabled=True,
                    provider_kind='customer_active_orders',
                    provider_params={},
                    cadence='weekly',
                    day_of_week=4,           # Friday — matches the legacy default
                    time_of_day=time(15, 0),  # 3pm UTC — matches the legacy default
                    timezone='UTC',
                    channels=['email'],
                )

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
        """Trusted client IP (edge-set header, not spoofable X-Forwarded-For).
        Delegates to the shared resolver — see Tracker/throttling.py."""
        from Tracker.throttling import get_client_ip as _trusted_client_ip
        return _trusted_client_ip(request)


# ===== DOCUMENT VIEWSETS =====

@extend_schema_view(
    create=extend_schema(request={'multipart/form-data': DocumentsSerializer}),
    update=extend_schema(request={'multipart/form-data': DocumentsSerializer}),
    partial_update=extend_schema(request={'multipart/form-data': DocumentsSerializer})
)
class DocumentViewSet(TenantScopedMixin, ListMetadataMixin, ExcelExportMixin, viewsets.ModelViewSet):
    """ViewSet for managing document attachments (universal infrastructure)"""
    queryset = Documents.unscoped.all()
    serializer_class = DocumentsSerializer
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    # Link-aware: filtering by content_type+object_id returns docs attached via
    # the primary GFK OR a secondary DocumentLink. See DocumentFilter.
    filterset_class = DocumentFilter
    search_fields = ["file_name", "uploaded_by__email"]
    ordering_fields = ["upload_date", "version", "file_name"]
    ordering = ["-upload_date"]

    # attach/detach manage DocumentLink rows, not the Document itself, so they
    # gate on the DocumentLink CRUD perms rather than the POST→add_documents
    # default. crud_exempt skips that default so the action perm is the sole gate.
    action_permissions = {
        'attach': ['add_documentlink'],
        'detach': ['delete_documentlink'],
    }
    crud_exempt_actions = {'attach', 'detach'}

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
            # tenant-safe: viewset runs inside tenant-scoped request context with RLS enforced
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
                from Tracker.models import ApprovalRequest, Approval_Status_Type
                content_type = ContentType.objects.get_for_model(instance)
                # tenant-safe: instance is tenant-scoped (from get_object); RLS enforced on viewset
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
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to submit for approval: {e}")
            return Response(
                {"detail": "Failed to submit for approval"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _resolve_link_target(self, request):
        """Resolve (content_type, object_id) from the request body to a live,
        tenant-scoped target instance. Returns (target, error_response)."""
        content_type_id = request.data.get('content_type')
        object_id = request.data.get('object_id')
        if not content_type_id or not object_id:
            return None, Response(
                {"detail": "Both 'content_type' (id) and 'object_id' are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            ct = ContentType.objects.get_for_id(content_type_id)
        except ContentType.DoesNotExist:
            return None, Response(
                {"detail": "Unknown content_type."}, status=status.HTTP_400_BAD_REQUEST,
            )
        model = ct.model_class()
        if model is None:
            return None, Response(
                {"detail": "content_type resolves to no model."}, status=status.HTTP_400_BAD_REQUEST,
            )
        # tenant-safe: `.objects` auto-scopes — a target in another tenant
        # (or non-existent) is rejected, so attach can't cross tenants.
        target = model.objects.filter(pk=object_id).first()
        if target is None:
            return None, Response(
                {"detail": "Target object was not found in your tenant."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return target, None

    @action(detail=True, methods=['post'])
    def attach(self, request, pk=None):
        """Attach this document to an additional target (secondary association).

        Body: {content_type: <id>, object_id: <pk>}. Idempotent; revives a
        previously detached link. Never affects the primary GFK owner.
        Returns the refreshed document (with `links`).
        """
        document = self.get_object()
        target, error = self._resolve_link_target(request)
        if error is not None:
            return error
        from Tracker.services.core.documents import attach_document_to
        attach_document_to(document, target)
        return Response(self.get_serializer(document).data)

    @action(detail=True, methods=['post'])
    def detach(self, request, pk=None):
        """Remove a secondary association from this document.

        Body: {content_type: <id>, object_id: <pk>}. Soft-deletes the link;
        no-op if none exists. Never affects the primary GFK owner.
        Returns the refreshed document (with `links`).
        """
        document = self.get_object()
        target, error = self._resolve_link_target(request)
        if error is not None:
            return error
        from Tracker.services.core.documents import detach_document_from
        detach_document_from(document, target)
        return Response(self.get_serializer(document).data)

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
                {"detail": "change_justification is required when creating a revision"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check document is current version
        if not document.is_current_version:
            return Response(
                {"detail": "Can only create revisions from the current version"},
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
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to create revision: {e}")
            return Response(
                {"detail": "Failed to create revision"},
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
                    {"detail": "effective_date must be in YYYY-MM-DD format"},
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
                {"detail": str(e)},
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
                {"detail": str(e)},
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

    @extend_schema(
        responses=inline_serializer(
            name="DocumentStatsResponse",
            fields={
                "total": serializers.IntegerField(),
                "pending_approval": serializers.IntegerField(),
                "needs_my_approval": serializers.IntegerField(),
                "my_uploads": serializers.IntegerField(),
                "recent_count": serializers.IntegerField(),
                "due_for_review": serializers.IntegerField(),
                "released": serializers.IntegerField(),
                "obsolete": serializers.IntegerField(),
                "by_classification": serializers.DictField(child=serializers.IntegerField()),
                "by_status": serializers.DictField(child=serializers.IntegerField()),
            },
        ),
    )
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get document statistics for dashboard"""
        user = request.user
        queryset = self.get_queryset()

        # Get pending approval count for documents
        doc_ct = ContentType.objects.get_for_model(Documents)
        # tenant-safe: viewset runs inside tenant-scoped request context with RLS enforced
        pending_approval_ids = ApprovalRequest.objects.filter(
            content_type=doc_ct,
            status='PENDING'
        ).values_list('object_id', flat=True)

        # Get documents needing user's approval (tenant-scoped groups)
        user_groups = user.get_tenant_groups() if hasattr(user, 'get_tenant_groups') else []
        user_group_ids = [g.id for g in user_groups]
        # tenant-safe: viewset runs inside tenant-scoped request context with RLS enforced
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

    @action(detail=False, methods=['get'], url_path='my-uploads', permission_classes=[IsAuthenticated, TenantAccessPermission])
    def my_uploads(self, request):
        """Get documents uploaded by the current user"""
        queryset = self.get_queryset().filter(uploaded_by=request.user)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(responses=DocumentsSerializer(many=True))
    @action(detail=False, methods=['get'], url_path='recent')
    def recent(self, request):
        """Get recently updated documents (paginated; defaults to 10 per page)."""
        queryset = self.get_queryset().order_by('-updated_at')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


# ===== DOCUMENT TYPE VIEWSET =====

class DocumentTypeViewSet(TenantScopedMixin, ListMetadataMixin, ExcelExportMixin, viewsets.ModelViewSet):
    """ViewSet for managing document types"""
    queryset = DocumentType.unscoped.all()
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

    # Content types are framework metadata (model name → numeric id),
    # not tenant data — the ids already appear in every GFK field of
    # every API response. The default permission stack's
    # TenantModelPermissions would demand `view_contenttype`, which
    # only admin groups carry; that silently broke the frontend's
    # content-type mapping (and with it the approval signature panels)
    # for every non-admin user. Authenticated + tenant access is the
    # right gate.
    permission_classes = [IsAuthenticated, TenantAccessPermission]

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

        # LogEntry has no tenant column (and no SecureManager), so scope by
        # the acting user's tenant. Conservative by design: entries with no
        # actor (system/service writes) are visible to superusers only —
        # they can't be attributed to a tenant without joining every audited
        # table, and showing them would leak other tenants' changes.
        if self.request.user.is_superuser:
            return self.queryset

        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return LogEntry.objects.none()

        return self.queryset.filter(actor__tenant=tenant)


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
    queryset = ApprovalTemplate.unscoped.all()
    serializer_class = ApprovalTemplateSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['approval_type', 'approval_flow_type', 'delegation_policy', 'approval_sequence']
    search_fields = ['template_name', 'approval_type']
    ordering_fields = ['template_name', 'created_at', 'updated_at']
    ordering = ['template_name']
    action_permissions = {
        'activate': ['manage_approval_workflow'],
        'deactivate': ['manage_approval_workflow'],
    }

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
        # `manage_approval_workflow` enforced declaratively via action_permissions.
        template = self.get_object()
        template.deactivated_at = timezone.now()
        template.save(update_fields=['deactivated_at'])
        return Response({'status': 'Template deactivated'})

    @action(detail=True, methods=['post'], url_path='activate')
    def activate(self, request, pk=None):
        """Reactivate an approval template"""
        # `manage_approval_workflow` enforced declaratively via action_permissions.
        template = self.get_object()
        template.deactivated_at = None
        template.save(update_fields=['deactivated_at'])
        return Response({'status': 'Template activated'})

    @extend_schema(
        description=(
            "Create a new revision of an ApprovalTemplate. "
            "Returns the new version with incremented version number. "
            "M2M default_approvers and default_groups are copied to the new version."
        ),
        request={
            "application/json": {
                "type": "object",
                "required": ["change_description"],
                "properties": {
                    "change_description": {
                        "type": "string",
                        "description": "Human narrative of what changed and why (ISO 9001 4.4)."
                    },
                },
            }
        },
        responses={201: ApprovalTemplateSerializer},
    )
    @action(detail=True, methods=['post'], url_path='revisions')
    def create_revision(self, request, pk=None):
        """Create a new version of this approval template.

        PATCH routes content edits through create_new_version via the
        serializer's update() method. This endpoint is the explicit
        "create a new revision" path when callers want full control.
        Returns 201 with the new version.
        """
        from Tracker.services.core.approval_template import (
            create_new_approval_template_version,
        )

        template = self.get_object()
        change_description = request.data.get('change_description', '')

        try:
            new_version = create_new_approval_template_version(
                template,
                user=request.user,
                change_description=change_description,
            )
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            ApprovalTemplateSerializer(new_version, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


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
    queryset = ApprovalRequest.unscoped.all()
    serializer_class = ApprovalRequestSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'approval_type', 'requested_by', 'content_type', 'object_id']
    search_fields = ['approval_number', 'reason', 'notes']
    ordering_fields = ['requested_at', 'completed_at', 'due_date', 'approval_number']
    ordering = ['-requested_at']
    pagination_class = LimitOffsetPagination
    action_permissions = {
        'submit_response': ['respond_to_approval'],
    }
    # Responding to an approval is not creating an ApprovalRequest, so
    # the POST→add_approvalrequest CRUD gate must not apply here — an
    # eligible approver legitimately lacks `add_approvalrequest`.
    # `respond_to_approval` (above) + the per-instance `can_approve`
    # check inside the action are the real gates.
    crud_exempt_actions = {'submit_response'}

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

    @extend_schema(
        description="Submit an approval response (approve/reject/delegate) with optional signature + password identity verification.",
        request=inline_serializer(
            name='ApprovalResponseSubmitRequest',
            fields={
                'decision': serializers.ChoiceField(choices=['APPROVED', 'REJECTED', 'DELEGATED']),
                'comments': serializers.CharField(required=False, allow_blank=True),
                'signature_data': serializers.CharField(
                    required=False, allow_blank=True,
                    help_text='Base64 PNG of the drawn signature.',
                ),
                'signature_meaning': serializers.CharField(required=False, allow_blank=True),
                'password': serializers.CharField(
                    required=False, allow_blank=True,
                    help_text='Re-entered account password for identity verification.',
                ),
                'delegate_to': serializers.IntegerField(required=False, allow_null=True),
            },
        ),
        responses={200: ApprovalResponseSerializer},
    )
    @action(detail=True, methods=['post'], url_path='submit-response')
    def submit_response(self, request, pk=None):
        """Submit an approval response (approve/reject/delegate).

        The explicit `@extend_schema(request=...)` matters: without it,
        spectacular defaults the request body to the viewset's
        ApprovalRequestRequest serializer, whose required fields the
        real payload doesn't carry — the generated frontend client then
        rejects every legitimate submit with a request-validation error
        before it leaves the browser.
        """
        # `respond_to_approval` enforced declaratively via action_permissions.
        # Per-instance assignment check (can_approve) remains inline — it's
        # template-binding logic that depends on the specific approval row.
        approval = self.get_object()

        # Check if user is an assigned approver
        if not approval.can_approve(request.user):
            return Response(
                {'detail': 'You are not assigned as an approver for this request'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Validate required fields
        decision = request.data.get('decision')
        if not decision:
            return Response(
                {'detail': 'Decision is required'},
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
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @extend_schema(
        description="Get all approval requests pending for current user",
        responses={200: ApprovalRequestSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='my-pending', permission_classes=[IsAuthenticated, TenantAccessPermission])
    def my_pending(self, request):
        """Get all approval requests pending for current user"""
        user = request.user

        # Find approvals where user is assigned and hasn't responded (tenant-scoped groups)
        # Use get_queryset() to ensure tenant filtering is applied
        user_groups = user.get_tenant_groups() if hasattr(user, 'get_tenant_groups') else []
        user_group_ids = [g.id for g in user_groups]
        pending_approvals = self.get_queryset().filter(
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
    queryset = ApprovalResponse.unscoped.all()
    serializer_class = ApprovalResponseSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['approval_request', 'approver', 'decision', 'verification_method']
    ordering_fields = ['decision_date', 'responded_at']
    ordering = ['-decision_date']
    action_permissions = {
        'delegate': ['respond_to_approval'],
    }
    # Delegating is a respond-type action by an approver, not creation
    # of an ApprovalResponse row in the CRUD sense — gate on
    # `respond_to_approval` alone, not POST→add_approvalresponse.
    crud_exempt_actions = {'delegate'}

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
        # `respond_to_approval` enforced declaratively via action_permissions.
        # Per-instance ownership check (response.approver == user) remains
        # inline — it depends on the specific response row.
        response = self.get_object()

        # Check if user is the approver for this response
        if response.approver != request.user:
            return Response(
                {'detail': 'You can only delegate your own approval responses'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Validate required fields
        delegatee_id = request.data.get('delegatee_id')
        reason = request.data.get('reason')

        if not delegatee_id or not reason:
            return Response(
                {'detail': 'delegatee_id and reason are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            delegatee = User.objects.get(id=delegatee_id)
            response.delegate_to(delegatee, reason)
            return Response(ApprovalResponseSerializer(response).data)

        except User.DoesNotExist:
            return Response(
                {'detail': 'Delegatee user not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'detail': str(e)},
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
                {'detail': "root parameter required (e.g., 'orders:123')"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            model_class, obj_id = self._parse_root(root_param)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Get root object with permission check
        try:
            if hasattr(model_class.objects, 'for_user'):
                root_obj = model_class.objects.for_user(request.user).get(pk=obj_id)
            else:
                root_obj = model_class.objects.get(pk=obj_id)
        except model_class.DoesNotExist:
            return Response(
                {'detail': f'{model_class.__name__} {obj_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Parse include
        include_param = request.query_params.get('include')
        if not include_param:
            return Response(
                {'detail': "include parameter required (e.g., 'documents')"},
                status=status.HTTP_400_BAD_REQUEST
            )

        include_types = [t.strip().lower() for t in include_param.split(',')]

        # Validate
        valid_types = list(self.INCLUDABLES.keys()) + ['stats']
        invalid = [t for t in include_types if t not in valid_types]
        if invalid:
            return Response(
                {'detail': f"Unknown types: {invalid}. Valid: {valid_types}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Direction
        direction = request.query_params.get('direction', 'down')
        if direction not in ('down', 'up'):
            return Response(
                {'detail': "direction must be 'down' or 'up'"},
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

# Media path prefixes that are intentionally public — tenant branding shown
# pre-login (CurrentTenantView already exposes logo_url to anonymous callers).
# Everything else requires an authenticated, authorized request.
_PUBLIC_MEDIA_PREFIXES = ('tenant_logos/',)


def _authorize_media_path(request, rel_path):
    """Authorize a `/media/<rel_path>` read.

    The media endpoint serves raw bytes outside the ORM/permission layer, so
    we re-impose access control here by resolving the file back to its owning
    record and checking the requester against it:

    - Public branding prefixes (`tenant_logos/`) are open.
    - Superusers / SaaS-vendor staff may read any tenant's files (support),
      consistent with the rest of the system's staff bypass.
    - Documents (incl. generated reports stored as Documents) go through the
      full `for_user` gate (tenant + classification + export-control).
    - 3D models and material-lot certificates require tenant membership.
    - Any path not owned by a known record fails closed.
    """
    norm = rel_path.replace('\\', '/')
    if any(norm.startswith(p) for p in _PUBLIC_MEDIA_PREFIXES):
        return True

    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True

    from Tracker.models import Documents, ThreeDModel, MaterialLot, UserRole
    from Tracker.utils.tenant_context import tenant_context

    def can_reach(tenant):
        if tenant is None:
            return False
        if getattr(user, 'tenant_id', None) == tenant.id:
            return True
        return UserRole.objects.filter(user=user, group__tenant=tenant).exists()

    # Documents: full access gate (tenant + classification + export-control).
    # tenant-safe: cross-tenant lookup to resolve the file's owning record;
    # access is enforced immediately below via can_reach + Documents.for_user.
    doc = Documents.all_tenants.filter(file=norm).first()
    if doc is not None:
        if not can_reach(doc.tenant):
            return False
        # for_user resolves perms against _current_tenant; set it to the doc's
        # tenant so classification/relationship checks evaluate in the right
        # tenant rather than the user's home tenant.
        user._current_tenant = doc.tenant
        with tenant_context(doc.tenant_id):
            return Documents.objects.for_user(user).filter(pk=doc.pk).exists()

    # 3D models — tenant membership is the bar.
    # tenant-safe: cross-tenant lookup to resolve the file's owner; access is
    # enforced immediately below via can_reach(tenant).
    tm = ThreeDModel.all_tenants.filter(file=norm).first()
    if tm is not None:
        return can_reach(tm.tenant)

    # Material-lot certificates of conformance.
    # tenant-safe: cross-tenant lookup to resolve the file's owner; access is
    # enforced immediately below via can_reach(tenant).
    lot = MaterialLot.all_tenants.filter(certificate_of_conformance=norm).first()
    if lot is not None:
        return can_reach(lot.tenant)

    # Unowned / unknown path — fail closed.
    return False


@xframe_options_exempt
def serve_media_iframe_safe(request, path):
    """
    Serve media files (PDFs, images, 3D models, etc.) with iframe-safe headers.

    This function allows media files to be embedded in iframes from the frontend.
    It sets appropriate CSP and CORS headers based on FRONTEND_URL setting.

    Access control: this endpoint serves bytes outside the ORM/permission
    layer, so every request is authorized via `_authorize_media_path` (tenant +
    classification + export-control). `/media/` is tenant-exempt in middleware,
    but `request.user` is still set from the session by AuthenticationMiddleware,
    so cookie-authenticated iframe/img loads authorize correctly.
    """
    import mimetypes

    full_path = os.path.join(settings.MEDIA_ROOT, path)

    # Security: Prevent path traversal attacks
    # Resolve to absolute path and verify it's within MEDIA_ROOT
    real_path = os.path.realpath(full_path)
    media_root = os.path.realpath(settings.MEDIA_ROOT)
    if not real_path.startswith(media_root + os.sep) and real_path != media_root:
        raise Http404()

    # Authorize before disclosing existence — unauthorized reads 404.
    if not _authorize_media_path(request, path):
        raise Http404()

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

    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')

    response = FileResponse(open(full_path, 'rb'), content_type=content_type)
    response["Content-Disposition"] = f'inline; filename="{os.path.basename(full_path)}"'
    response["Content-Security-Policy"] = f"frame-ancestors {frontend_url}"
    response["Access-Control-Allow-Origin"] = frontend_url
    response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response["Access-Control-Allow-Headers"] = "Content-Type"
    return response

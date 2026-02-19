# serializers/core.py - Core infrastructure (Users, Companies, Auth, Approvals, Audit Logs, Shared Mixins)
from auditlog.models import LogEntry
from dj_rest_auth.forms import AllAuthPasswordResetForm
from dj_rest_auth.serializers import PasswordResetSerializer as BasePasswordResetSerializer
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.shortcuts import get_current_site
from django.conf import settings
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from Tracker.models.core import (
    User, Companies, UserInvitation, TenantGroup,
    # Approval workflow models
    ApprovalRequest, ApprovalResponse, ApprovalTemplate,
    Approval_Type, Approval_Status_Type, SequenceTypes
)

if 'allauth' in settings.INSTALLED_APPS:
    from allauth.account import app_settings as allauth_account_settings
    from allauth.account.adapter import get_adapter
    from allauth.account.forms import default_token_generator
    from allauth.account.utils import (filter_users_by_email, user_pk_to_url_str, user_username, )


# ===== BASE MIXINS =====

class SecureModelMixin:
    """Mixin for serializers that work with SecureModel instances"""

    def get_user_filtered_queryset(self, model_class):
        """Get queryset filtered for the requesting user"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            return model_class.objects.for_user(request.user)
        return model_class.objects.active()


class BulkOperationsMixin:
    """Mixin providing bulk operation methods"""

    def bulk_soft_delete(self, queryset, reason="serializer_bulk_delete"):
        """Perform bulk soft delete with audit logging"""
        request = self.context.get('request')
        actor = request.user if request else None
        return queryset.bulk_soft_delete(actor=actor, reason=reason)

    def bulk_restore(self, queryset, reason="serializer_bulk_restore"):
        """Perform bulk restore with audit logging"""
        request = self.context.get('request')
        actor = request.user if request else None
        return queryset.bulk_restore(actor=actor, reason=reason)


class DynamicFieldsMixin:
    """
    Mixin that allows field selection via ?fields=id,name,status query param.
    Reduces response payload size by only returning requested fields.

    Usage:
        1. Add mixin to your serializer (BEFORE ModelSerializer):
           class PartsSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
               ...

        2. Override get_serializer_context in your ViewSet:
           def get_serializer_context(self):
               context = super().get_serializer_context()
               context['fields'] = self.request.query_params.get('fields')
               return context

        3. Call API with ?fields param:
           GET /api/parts/?fields=id,ERP_id,part_status
           GET /api/dispositions/?fields=id,current_state

    Note:
        - Field names must match serializer fields exactly
        - Invalid field names are silently ignored
        - If no fields param provided, all fields are returned (normal behavior)
        - Works with nested serializers - only top-level fields are filtered
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Get fields param from context (set by ViewSet)
        fields_param = self.context.get('fields') if self.context else None

        if fields_param:
            # Parse comma-separated field names
            requested_fields = set(f.strip() for f in fields_param.split(',') if f.strip())

            if requested_fields:
                # Get existing field names
                existing_fields = set(self.fields.keys())

                # Remove fields not in the requested set
                for field_name in existing_fields - requested_fields:
                    self.fields.pop(field_name)


# ===== USER & COMPANY SERIALIZERS =====

class UserSelectSerializer(serializers.ModelSerializer):
    """Simplified user serializer for dropdowns and selections"""
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'email', 'full_name', 'is_active')
        read_only_fields = ('username', 'is_active')

    @extend_schema_field(serializers.CharField())
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username


class EmployeeSelectSerializer(serializers.ModelSerializer):
    """Employee selection serializer"""

    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'email')


class CompanySerializer(serializers.ModelSerializer, SecureModelMixin):
    """Company serializer with secure filtering"""
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = Companies
        fields = ('id', 'name', 'description', 'hubspot_api_id', 'user_count', 'created_at', 'updated_at', 'archived')
        read_only_fields = ('created_at', 'updated_at')

    @extend_schema_field(serializers.IntegerField())
    def get_user_count(self, obj):
        return obj.users.filter(is_active=True).count()


class CustomerSerializer(serializers.ModelSerializer):
    """Customer serializer with company info"""
    parent_company = CompanySerializer(read_only=True, allow_null=True)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_staff', 'parent_company', 'id']


class UserDetailSerializer(serializers.ModelSerializer):
    """Detailed user serializer with company info"""
    parent_company = CompanySerializer(read_only=True, allow_null=True)
    parent_company_id = serializers.PrimaryKeyRelatedField(queryset=Companies.objects.all(), source='parent_company',
                                                           write_only=True, required=False)

    class Meta:
        model = User
        fields = (
        'id', 'username', 'first_name', 'last_name', 'email', 'is_staff', 'is_active', 'date_joined', 'parent_company',
        'parent_company_id')
        read_only_fields = ('date_joined',)


class UserSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Enhanced user serializer with company and permission info"""
    full_name = serializers.SerializerMethodField()
    parent_company = CompanySerializer(read_only=True, allow_null=True)
    parent_company_id = serializers.PrimaryKeyRelatedField(queryset=Companies.objects.all(), source='parent_company',
                                                           write_only=True, required=False, allow_null=True)
    groups = serializers.SerializerMethodField()
    group_ids = serializers.PrimaryKeyRelatedField(many=True, queryset=Group.objects.all(), source='groups',
                                                   write_only=True, required=False)

    class Meta:
        model = User
        fields = (
            'id', 'username', 'first_name', 'last_name', 'email', 'full_name', 'is_staff', 'is_active', 'date_joined',
            'parent_company', 'parent_company_id', 'groups', 'group_ids')
        read_only_fields = ('date_joined', 'full_name')
        extra_kwargs = {'password': {'write_only': True}}

    @extend_schema_field(serializers.CharField())
    def get_full_name(self, obj):
        """Get formatted full name or fallback to username"""
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_groups(self, obj):
        """Get user groups (tenant-scoped)"""
        # Get tenant from request context if available, otherwise use obj's tenant
        request = self.context.get('request')
        tenant = getattr(request.user, 'tenant', None) if request else getattr(obj, 'tenant', None)
        if hasattr(obj, 'get_tenant_groups') and tenant:
            return GroupSerializer(obj.get_tenant_groups(tenant), many=True).data
        return []


class UserInvitationSerializer(serializers.ModelSerializer):
    """Serializer for user invitations"""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    invited_by_name = serializers.SerializerMethodField()
    is_expired = serializers.BooleanField(read_only=True)
    is_valid = serializers.BooleanField(read_only=True)
    invitation_url = serializers.SerializerMethodField()

    class Meta:
        model = UserInvitation
        fields = (
            'id', 'user', 'user_email', 'user_name', 'invited_by', 'invited_by_name',
            'sent_at', 'expires_at', 'accepted_at', 'is_expired', 'is_valid',
            'accepted_ip_address', 'accepted_user_agent', 'invitation_url'
        )
        read_only_fields = (
            'sent_at', 'accepted_at', 'is_expired', 'is_valid',
            'accepted_ip_address', 'accepted_user_agent', 'token'
        )

    @extend_schema_field(serializers.CharField())
    def get_user_name(self, obj):
        """Get formatted user name"""
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email
        return None

    @extend_schema_field(serializers.CharField())
    def get_invited_by_name(self, obj):
        """Get formatted invited_by name"""
        if obj.invited_by:
            return f"{obj.invited_by.first_name} {obj.invited_by.last_name}".strip() or obj.invited_by.email
        return None

    @extend_schema_field(serializers.CharField())
    def get_invitation_url(self, obj):
        """Generate invitation signup URL"""
        request = self.context.get('request')
        if request:
            # Get frontend URL from settings
            if settings.DEBUG:
                frontend_url = "http://localhost:5173"
            else:
                frontend_url = getattr(settings, 'FRONTEND_URL', 'https://yourdomain.com')

            return f"{frontend_url}/signup?token={obj.token}"
        return None


# ===== AUTHENTICATION & PASSWORD RESET SERIALIZERS =====

class CustomAllAuthPasswordResetForm(AllAuthPasswordResetForm):
    def clean_email(self):
        """
        Invalid email should not raise error, as this would leak users
        for unit test: test_password_reset_with_invalid_email
        """
        email = self.cleaned_data["email"]
        email = get_adapter().clean_email(email)
        self.users = filter_users_by_email(email, is_active=True)
        return self.cleaned_data["email"]

    def save(self, request, **kwargs):
        current_site = get_current_site(request)
        email = self.cleaned_data['email']
        token_generator = kwargs.get('token_generator', default_token_generator)

        from django.template.loader import select_template
        try:
            template_names = ['account/email/password_reset_key_message.html',
                              'account/email/password_reset_key_message.txt', ]
            template = select_template(template_names)
            print(f" Allauth will use template: {template.origin.name}")
        except Exception as e:
            print(f" Template selection error: {e}")

        # Get frontend URL from settings
        if settings.DEBUG:
            frontend_url = "http://localhost:5173"
        else:
            frontend_url = getattr(settings, 'FRONTEND_URL', 'https://yourdomain.com')

        for user in self.users:
            temp_key = token_generator.make_token(user)
            uid = user_pk_to_url_str(user)

            # Custom URL pointing to your frontend
            custom_url = f"{frontend_url}/reset-password/{uid}/{temp_key}/"

            context = {'current_site': current_site, 'user': user, 'site_name': "AMBAC",
                       'password_reset_url': custom_url,
                       'request': request, 'token': temp_key, 'uid': uid, }
            if (allauth_account_settings.AUTHENTICATION_METHOD != allauth_account_settings.AuthenticationMethod.EMAIL):
                context['username'] = user_username(user)

            get_adapter(request).send_mail('account/email/password_reset_key', email, context)

        return self.cleaned_data['email']


class PasswordResetSerializer(BasePasswordResetSerializer):
    @property
    def password_reset_form_class(self):
        """Force use of our custom form instead of the default AllAuth form"""
        return CustomAllAuthPasswordResetForm


class GroupSerializer(serializers.ModelSerializer):
    """Serializer for Django Groups with user and permission details"""
    user_count = serializers.SerializerMethodField()
    users = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ('id', 'name', 'description', 'user_count', 'users', 'permissions')

    @extend_schema_field({"type": "integer"})
    def get_user_count(self, obj):
        return obj.user_set.count()

    @extend_schema_field({"type": "array", "items": {"type": "object"}})
    def get_users(self, obj):
        """Return list of users in this group"""
        return [
            {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_active': user.is_active,
            }
            for user in obj.user_set.all().order_by('email')
        ]

    @extend_schema_field({"type": "array", "items": {"type": "object"}})
    def get_permissions(self, obj):
        """Return list of permissions for this group"""
        return [
            {
                'id': perm.id,
                'codename': perm.codename,
                'name': perm.name,
                'content_type': perm.content_type.model if perm.content_type else None,
            }
            for perm in obj.permissions.all().select_related('content_type').order_by('codename')
        ]

    @extend_schema_field({"type": "string", "nullable": True})
    def get_description(self, obj):
        """Get description from GROUP_DEFINITIONS"""
        from Tracker.permissions import GROUP_DEFINITIONS
        group_def = GROUP_DEFINITIONS.get(obj.name, {})
        return group_def.get('description', None)


class TenantGroupSerializer(serializers.ModelSerializer):
    """Serializer for TenantGroup - used in approval workflows"""
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = TenantGroup
        fields = ('id', 'name', 'description', 'user_count')

    @extend_schema_field({"type": "integer"})
    def get_user_count(self, obj):
        """Return count of users in this group via UserRole"""
        return obj.user_roles.count()


# ===== AUDIT LOG SERIALIZERS =====

class AuditLogSerializer(serializers.ModelSerializer):
    """Enhanced audit log serializer"""
    content_type_name = serializers.CharField(source='content_type.model', read_only=True)
    actor_info = serializers.SerializerMethodField()

    class Meta:
        model = LogEntry
        fields = (
            'id', 'object_pk', 'object_repr', 'content_type', 'content_type_name', 'actor', 'actor_info', 'remote_addr',
            'timestamp', 'action', 'changes')
        read_only_fields = ('id', 'timestamp', 'content_type_name', 'actor_info')

    @extend_schema_field({"type": "object", "nullable": True})
    def get_actor_info(self, obj):
        if obj.actor:
            return UserSelectSerializer(obj.actor).data
        return None


class LogEntrySerializer(serializers.ModelSerializer):
    """Legacy log entry serializer"""
    content_type_name = serializers.CharField(source="content_type.model", read_only=True)

    class Meta:
        model = LogEntry
        fields = ["id", "object_pk", "object_repr", "content_type_name", "actor", "remote_addr", "timestamp", "action",
                  "changes"]


# ===== CONTENT TYPE SERIALIZERS =====

class ContentTypeSerializer(serializers.ModelSerializer):
    """Content type serializer"""

    class Meta:
        model = ContentType
        fields = ['id', 'app_label', 'model']


# ===== BULK OPERATION SERIALIZERS =====

class BulkSoftDeleteSerializer(serializers.Serializer, BulkOperationsMixin):
    """Serializer for bulk soft delete operations"""
    ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
    reason = serializers.CharField(max_length=200, default="bulk_admin_delete")

    def perform_bulk_delete(self, model_class):
        """Perform bulk soft delete using SecureManager"""
        ids = self.validated_data['ids']
        reason = self.validated_data['reason']

        queryset = model_class.objects.filter(id__in=ids)
        return self.bulk_soft_delete(queryset, reason)


class BulkRestoreSerializer(serializers.Serializer, BulkOperationsMixin):
    """Serializer for bulk restore operations"""
    ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
    reason = serializers.CharField(max_length=200, default="bulk_admin_restore")

    def perform_bulk_restore(self, model_class):
        """Perform bulk restore using SecureManager"""
        ids = self.validated_data['ids']
        reason = self.validated_data['reason']

        queryset = model_class.all_objects.filter(id__in=ids, archived=True)
        return self.bulk_restore(queryset, reason)


# ===== APPROVAL WORKFLOW SERIALIZERS =====

class ApprovalTemplateSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Approval template serializer"""
    approval_type_display = serializers.CharField(source='get_approval_type_display', read_only=True)
    approval_flow_type_display = serializers.CharField(source='get_approval_flow_type_display', read_only=True)
    approval_sequence_display = serializers.CharField(source='get_approval_sequence_display', read_only=True)
    delegation_policy_display = serializers.CharField(source='get_delegation_policy_display', read_only=True)
    default_groups_info = serializers.SerializerMethodField()
    default_approvers_info = serializers.SerializerMethodField()
    escalate_to_info = serializers.SerializerMethodField()

    class Meta:
        model = ApprovalTemplate
        fields = (
            'id', 'template_name', 'approval_type', 'approval_type_display',
            'default_groups', 'default_groups_info',
            'default_approvers', 'default_approvers_info',
            'default_threshold', 'auto_assign_by_role',
            'approval_flow_type', 'approval_flow_type_display',
            'delegation_policy', 'delegation_policy_display',
            'approval_sequence', 'approval_sequence_display',
            'allow_self_approval',
            'default_due_days', 'escalation_days', 'escalate_to', 'escalate_to_info',
            'deactivated_at',
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = ('created_at', 'updated_at')

    @extend_schema_field(serializers.ListField())
    def get_default_groups_info(self, obj):
        return TenantGroupSerializer(obj.default_groups.all(), many=True).data

    @extend_schema_field(serializers.ListField())
    def get_default_approvers_info(self, obj):
        return UserSelectSerializer(obj.default_approvers.all(), many=True).data

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_escalate_to_info(self, obj):
        if obj.escalate_to:
            return UserSelectSerializer(obj.escalate_to).data
        return None


class ApprovalResponseSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Approval response serializer"""
    approver_info = serializers.SerializerMethodField()
    delegated_to_info = serializers.SerializerMethodField()
    decision_display = serializers.CharField(source='get_decision_display', read_only=True)
    verification_method_display = serializers.CharField(source='get_verification_method_display', read_only=True)

    class Meta:
        model = ApprovalResponse
        fields = (
            'id', 'approval_request', 'approver', 'approver_info',
            'decision', 'decision_display', 'decision_date', 'comments',
            'signature_data', 'signature_meaning', 'verified_at',
            'verification_method', 'verification_method_display',
            'delegated_to', 'delegated_to_info',
            'ip_address', 'self_approved',
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = ('decision_date', 'verified_at', 'ip_address', 'created_at', 'updated_at', 'self_approved')

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_approver_info(self, obj):
        if obj.approver:
            return UserSelectSerializer(obj.approver).data
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_delegated_to_info(self, obj):
        if obj.delegated_to:
            return UserSelectSerializer(obj.delegated_to).data
        return None


class ApproverAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for approver assignments with full audit metadata"""
    user_info = serializers.SerializerMethodField()
    assigned_by_info = serializers.SerializerMethodField()
    assignment_source_display = serializers.CharField(source='get_assignment_source_display', read_only=True)

    class Meta:
        from Tracker.models import ApproverAssignment
        model = ApproverAssignment
        fields = (
            'id', 'user', 'user_info', 'is_required', 'sequence_order',
            'assignment_source', 'assignment_source_display',
            'assigned_by', 'assigned_by_info', 'assigned_at',
            'notified_at', 'reminder_count', 'last_reminder_at'
        )
        read_only_fields = fields

    @extend_schema_field(serializers.DictField())
    def get_user_info(self, obj):
        return UserSelectSerializer(obj.user).data

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_assigned_by_info(self, obj):
        if obj.assigned_by:
            return UserSelectSerializer(obj.assigned_by).data
        return None


class ApprovalRequestSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Approval request serializer"""
    approval_number = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    approval_type_display = serializers.CharField(source='get_approval_type_display', read_only=True)
    flow_type_display = serializers.CharField(source='get_flow_type_display', read_only=True)
    requested_by_info = serializers.SerializerMethodField()
    # Full assignment info with audit metadata
    approver_assignments_info = serializers.SerializerMethodField()
    # Backward-compatible simple lists
    required_approvers_info = serializers.SerializerMethodField()
    optional_approvers_info = serializers.SerializerMethodField()
    approver_groups_info = serializers.SerializerMethodField()
    responses = ApprovalResponseSerializer(many=True, read_only=True)
    pending_approvers = serializers.SerializerMethodField()
    content_object_info = serializers.SerializerMethodField()

    class Meta:
        model = ApprovalRequest
        fields = (
            'id', 'approval_number', 'content_type', 'object_id',
            'content_object_info', 'requested_by', 'requested_by_info',
            'reason', 'notes', 'status', 'status_display',
            'approval_type', 'approval_type_display',
            'flow_type', 'flow_type_display', 'sequence_type', 'threshold',
            'delegation_policy', 'escalation_day', 'escalate_to', 'due_date',
            # New: full assignment info with audit trail
            'approver_assignments_info',
            # Backward-compatible: simple user lists
            'required_approvers_info', 'optional_approvers_info',
            'approver_groups', 'approver_groups_info',
            'responses', 'pending_approvers',
            'requested_at', 'completed_at', 'created_at', 'updated_at', 'archived'
        )
        read_only_fields = (
            'approval_number', 'requested_at', 'completed_at',
            'created_at', 'updated_at', 'archived'
        )

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_requested_by_info(self, obj):
        if obj.requested_by:
            return UserSelectSerializer(obj.requested_by).data
        return None

    @extend_schema_field(serializers.ListField())
    def get_approver_assignments_info(self, obj):
        """Get full assignment info with audit metadata"""
        assignments = obj.approver_assignments.select_related('user', 'assigned_by').order_by('sequence_order', 'assigned_at')
        return ApproverAssignmentSerializer(assignments, many=True).data

    @extend_schema_field(serializers.ListField())
    def get_required_approvers_info(self, obj):
        """Get info for required approvers (backward-compatible)"""
        return UserSelectSerializer(obj.required_approvers, many=True).data

    @extend_schema_field(serializers.ListField())
    def get_optional_approvers_info(self, obj):
        """Get info for optional approvers (backward-compatible)"""
        return UserSelectSerializer(obj.optional_approvers, many=True).data

    @extend_schema_field(serializers.ListField())
    def get_approver_groups_info(self, obj):
        """Get info for approver groups (TenantGroup)"""
        groups = obj.approver_groups.all()
        return TenantGroupSerializer(groups, many=True).data

    @extend_schema_field(serializers.ListField())
    def get_pending_approvers(self, obj):
        """Get list of users who still need to approve"""
        pending = obj.get_pending_approvers()
        return UserSelectSerializer(pending, many=True).data

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_content_object_info(self, obj):
        """Get basic info about the linked content object"""
        if obj.content_object:
            # Return basic info - type and ID
            return {
                'type': obj.content_type.model,
                'id': obj.object_id,
                'str': str(obj.content_object)
            }
        return None

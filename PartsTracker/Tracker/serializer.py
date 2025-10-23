# serializers.py - Complete merged version with SecureModel integration
from dj_rest_auth.forms import AllAuthPasswordResetForm
from dj_rest_auth.serializers import PasswordResetSerializer as BasePasswordResetSerializer
from django.contrib.auth.models import Group
from django.contrib.sites.shortcuts import get_current_site
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import *

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
        read_only_fields = ('created_at', 'updated_at', 'archived')

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


# ===== STAGE AND PROCESS SERIALIZERS =====

class StageSerializer(serializers.Serializer):
    """Serializer for process stages"""
    name = serializers.CharField()
    timestamp = serializers.DateTimeField(allow_null=True)
    is_completed = serializers.BooleanField()
    is_current = serializers.BooleanField()


# ===== CORE BUSINESS SERIALIZERS =====

class OrdersSerializer(serializers.ModelSerializer, SecureModelMixin, BulkOperationsMixin):
    """Enhanced orders serializer with user filtering and features"""
    order_status = serializers.ChoiceField(choices=OrdersStatus.choices)

    # Display fields
    customer_info = serializers.SerializerMethodField()
    company_info = serializers.SerializerMethodField()
    parts_summary = serializers.SerializerMethodField()
    process_stages = serializers.SerializerMethodField()
    gate_info = serializers.SerializerMethodField()

    # Legacy fields for compatibility - using SerializerMethodField to handle null relations safely
    customer_first_name = serializers.SerializerMethodField(required=False, allow_null=True)
    customer_last_name = serializers.SerializerMethodField(required=False, allow_null=True)
    company_name = serializers.SerializerMethodField(required=False, allow_null=True)

    # Write fields
    customer = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), allow_null=True, required=False)
    company = serializers.PrimaryKeyRelatedField(queryset=Companies.objects.all(), allow_null=True, required=False)
    current_hubspot_gate = serializers.PrimaryKeyRelatedField(queryset=ExternalAPIOrderIdentifier.objects.all(),
                                                              allow_null=True, required=False)

    class Meta:
        model = Orders
        fields = (
        'id', 'name', 'customer_note', 'customer', 'customer_info', 'company', 'company_info', 'estimated_completion',
        'order_status', 'current_hubspot_gate', 'parts_summary', 'process_stages', 'gate_info', 'customer_first_name',
        'customer_last_name', 'company_name', 'created_at', 'updated_at', 'archived', 'archived')
        read_only_fields = (
            'created_at', 'updated_at', 'archived', 'parts_summary', 'process_stages', 'gate_info', 'customer_info', 'company_info',
            'customer_first_name', 'customer_last_name', 'company_name')

    @extend_schema_field(UserSelectSerializer(allow_null=True))
    def get_customer_info(self, obj):
        if obj.customer:
            return UserSelectSerializer(obj.customer).data
        return None

    @extend_schema_field(CompanySerializer(allow_null=True))
    def get_company_info(self, obj):
        if obj.company:
            return CompanySerializer(obj.company, context=self.context).data
        return None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_customer_first_name(self, obj):
        """Safe access to customer first name"""
        return obj.customer.first_name if obj.customer else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_customer_last_name(self, obj):
        """Safe access to customer last name"""
        return obj.customer.last_name if obj.customer else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_company_name(self, obj):
        """Safe access to company name"""
        return obj.company.name if obj.company else None

    @extend_schema_field(serializers.DictField())
    def get_parts_summary(self, obj):
        """Use model method for parts distribution"""
        return {'total_parts': obj.parts.count(), 'step_distribution': obj.get_step_distribution(),
                'completed_parts': obj.parts.filter(part_status=PartsStatus.COMPLETED).count()}

    @extend_schema_field(serializers.ListField())
    def get_process_stages(self, obj):
        """Use enhanced model method for detailed stage info"""
        return obj.get_detailed_stage_info()

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_gate_info(self, obj):
        """Get HubSpot gate progress information"""
        return obj.get_gate_info()


class TrackerPageOrderSerializer(serializers.ModelSerializer):
    """Legacy tracker page order serializer"""
    order_status = serializers.ChoiceField(choices=OrdersStatus.choices)
    stages = serializers.SerializerMethodField()
    customer = CustomerSerializer(read_only=True)
    company = CompanySerializer(read_only=True, allow_null=True)

    class Meta:
        model = Orders
        exclude = ['hubspot_deal_id', 'last_synced_hubspot_stage', 'current_hubspot_gate']

    @extend_schema_field(StageSerializer(many=True))
    def get_stages(self, order):
        """Use the model method for process stages"""
        return order.get_process_stages()


class PartsSerializer(serializers.ModelSerializer, SecureModelMixin, BulkOperationsMixin):
    """Enhanced parts serializer using model methods"""

    # Display fields using model methods
    sampling_info = serializers.SerializerMethodField()
    quality_info = serializers.SerializerMethodField()
    work_order_info = serializers.SerializerMethodField()
    sampling_history = serializers.SerializerMethodField()

    # Related object info
    order_info = serializers.SerializerMethodField()
    part_type_info = serializers.SerializerMethodField()
    step_info = serializers.SerializerMethodField()

    # Legacy compatibility fields
    has_error = serializers.SerializerMethodField(read_only=True)
    part_type_name = serializers.SerializerMethodField(read_only=True)
    process = serializers.SerializerMethodField(read_only=True)
    process_name = serializers.SerializerMethodField(read_only=True)
    order_name = serializers.SerializerMethodField(read_only=True, allow_null=True)
    step_description = serializers.SerializerMethodField(read_only=True)
    work_order_erp_id = serializers.SerializerMethodField(read_only=True, allow_null=True)
    quality_status = serializers.SerializerMethodField(read_only=True)

    # Batch process info
    is_from_batch_process = serializers.SerializerMethodField(read_only=True)

    # Write fields
    step = serializers.PrimaryKeyRelatedField(queryset=Steps.objects.all())
    part_type = serializers.PrimaryKeyRelatedField(queryset=PartTypes.objects.all())
    order = serializers.PrimaryKeyRelatedField(queryset=Orders.objects.all(), required=False)
    work_order = serializers.PrimaryKeyRelatedField(queryset=WorkOrder.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Parts
        fields = ('id', 'ERP_id', 'part_status', 'archived', 'requires_sampling', 'order', 'order_info', 'part_type',
                  'part_type_info', 'step', 'step_info', 'work_order', 'work_order_info', 'sampling_info',
                  'quality_info', 'sampling_history', 'created_at', 'updated_at', 'archived', 'has_error',
                  'part_type_name', 'process_name', 'order_name', 'step_description', 'work_order_erp_id',
                  'quality_status', 'is_from_batch_process', 'sampling_rule', 'sampling_ruleset', 'sampling_context',
                  'process', 'total_rework_count')
        read_only_fields = (
            'created_at', 'updated_at', 'archived', 'requires_sampling', 'sampling_info', 'quality_info',
            'work_order_info', 'sampling_history', 'order_info', 'part_type_info', 'step_info', 'has_error',
            'part_type_name', 'process_name', 'order_name', 'step_description', 'work_order_erp_id', 'quality_status',
            'is_from_batch_process', 'process', 'total_rework_count')

    @extend_schema_field(serializers.DictField())
    def get_sampling_info(self, obj):
        """Use model method for sampling display info"""
        return obj.get_sampling_display_info()

    @extend_schema_field(serializers.DictField())
    def get_quality_info(self, obj):
        """Use model methods for quality status"""
        return {'has_errors': obj.has_quality_errors(), 'latest_status': obj.get_latest_quality_status(),
                'error_count': obj.error_reports.count()}

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_work_order_info(self, obj):
        """Use model method for work order info"""
        return obj.get_work_order_display_info()

    @extend_schema_field(serializers.DictField())
    def get_sampling_history(self, obj):
        """Use model method for complete sampling history"""
        return obj.get_sampling_history()

    @extend_schema_field(serializers.DictField())
    def get_order_info(self, obj):
        if obj.order:
            return {'id': obj.order.id, 'name': obj.order.name, 'status': obj.order.order_status,
                    'customer': obj.order.customer.username if obj.order.customer else None}
        return None

    @extend_schema_field(serializers.DictField())
    def get_part_type_info(self, obj):
        if obj.part_type:
            return {'id': obj.part_type.id, 'name': obj.part_type.name, 'version': obj.part_type.version,
                    'ID_prefix': obj.part_type.ID_prefix}
        return None

    @extend_schema_field(serializers.IntegerField())
    def get_process(self, obj):
        if obj.step and obj.step.process:
            return obj.step.process.id
        else:
            return None

    @extend_schema_field(serializers.DictField())
    def get_step_info(self, obj):
        if obj.step:
            return {'id': obj.step.id, 'name': obj.step.name, 'order': obj.step.order,
                    'description': obj.step.description, 'is_last_step': obj.step.is_last_step,
                    'process_name': obj.step.process.name if obj.step.process else None}
        return None

    # Legacy compatibility methods
    @extend_schema_field(serializers.BooleanField())
    def get_has_error(self, obj):
        """Use model method"""
        return obj.has_quality_errors()

    @extend_schema_field(serializers.CharField())
    def get_work_order_erp_id(self, obj):
        return obj.work_order.ERP_id if obj.work_order and obj.work_order.ERP_id else None

    @extend_schema_field(serializers.CharField())
    def get_part_type_name(self, obj):
        return obj.part_type.name if obj.part_type else None

    @extend_schema_field(serializers.CharField())
    def get_order_name(self, obj):
        return obj.order.name if obj.order else None

    @extend_schema_field(serializers.CharField())
    def get_step_description(self, obj):
        return obj.step.description if obj.step else None

    @extend_schema_field(serializers.CharField())
    def get_process_name(self, obj):
        return obj.step.process.name if obj.step else None

    @extend_schema_field(serializers.DictField())
    def get_quality_status(self, obj):
        """Use model method for quality status"""
        return {'has_errors': obj.has_quality_errors(), 'latest_status': obj.get_latest_quality_status()}

    @extend_schema_field(serializers.BooleanField())
    def get_is_from_batch_process(self, obj):
        """Check if this part comes from a batch process"""
        if obj.part_type and obj.part_type.processes.exists():
            return obj.part_type.processes.filter(is_batch_process=True).exists()
        return False


class CustomerPartsSerializer(serializers.ModelSerializer):
    """Customer parts serializer with order info"""
    Orders = TrackerPageOrderSerializer

    class Meta:
        model = Parts
        exclude = ['ERP_id', 'work_order']
        depth = 2


class WorkOrderSerializer(serializers.ModelSerializer, SecureModelMixin, BulkOperationsMixin):
    """Enhanced work order serializer"""
    related_order_info = serializers.SerializerMethodField()
    parts_summary = serializers.SerializerMethodField()
    related_order_detail = serializers.SerializerMethodField()
    is_batch_work_order = serializers.SerializerMethodField()

    related_order = serializers.PrimaryKeyRelatedField(queryset=Orders.objects.all(), required=False, allow_null=True)

    class Meta:
        model = WorkOrder
        fields = (
        'id', 'ERP_id', 'workorder_status', 'quantity', 'related_order', 'related_order_info', 'related_order_detail',
        'expected_completion', 'expected_duration', 'true_completion', 'true_duration', 'notes', 'parts_summary',
        'is_batch_work_order', 'created_at', 'updated_at', 'archived')
        read_only_fields = (
            'created_at', 'updated_at', 'archived', 'related_order_info', 'parts_summary', 'related_order_detail',
            'is_batch_work_order')

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_related_order_info(self, obj):
        if obj.related_order:
            return {'id': obj.related_order.id, 'name': obj.related_order.name,
                    'status': obj.related_order.order_status,
                    'customer': obj.related_order.customer.username if obj.related_order.customer else None}
        return None

    @extend_schema_field(OrdersSerializer(allow_null=True))
    def get_related_order_detail(self, obj):
        if obj.related_order:
            return OrdersSerializer(obj.related_order, context=self.context).data
        return None

    @extend_schema_field(serializers.DictField())
    def get_parts_summary(self, obj):
        parts = obj.parts.all()
        has_batch_parts = parts.filter(part_type__processes__is_batch_process=True).exists()

        return {'total': parts.count(), 'requiring_qa': parts.filter(requires_sampling=True,
                                                                     part_status__in=['PENDING', 'IN_PROGRESS',
                                                                                      'AWAITING_QA',
                                                                                      'READY FOR NEXT STEP']).count(),
                'completed': parts.filter(part_status=PartsStatus.COMPLETED).count(),
                'in_progress': parts.filter(part_status=PartsStatus.IN_PROGRESS).count(),
                'pending': parts.filter(part_status=PartsStatus.PENDING).count(), 'has_batch_parts': has_batch_parts}

    @extend_schema_field(serializers.BooleanField())
    def get_is_batch_work_order(self, obj):
        """Check if any parts in this work order come from batch processes"""
        return obj.parts.filter(part_type__processes__is_batch_process=True).exists()


class DocumentsSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Enhanced documents serializer using model methods"""
    file_url = serializers.SerializerMethodField()
    uploaded_by_info = serializers.SerializerMethodField()
    content_type_info = serializers.SerializerMethodField()
    access_info = serializers.SerializerMethodField()
    auto_properties = serializers.SerializerMethodField()

    class Meta:
        model = Documents
        fields = ('id', 'classification', 'ai_readable', 'is_image', 'file_name', 'file', 'file_url', 'upload_date',
                  'uploaded_by', 'uploaded_by_info', 'content_type', 'object_id', 'content_type_info', 'version',
                  'access_info', 'auto_properties', 'created_at', 'updated_at', 'archived')
        read_only_fields = (
            'upload_date', 'created_at', 'updated_at', 'archived', 'file_url', 'uploaded_by_info', 'content_type_info',
            'access_info', 'auto_properties')

    @extend_schema_field(serializers.CharField())
    def get_file_url(self, obj):
        try:
            return obj.file.url if obj.file else None
        except ValueError:
            return None

    @extend_schema_field(serializers.DictField())
    def get_uploaded_by_info(self, obj):
        if obj.uploaded_by:
            return UserSelectSerializer(obj.uploaded_by).data
        return None

    @extend_schema_field(serializers.DictField())
    def get_content_type_info(self, obj):
        if obj.content_type:
            return {'app_label': obj.content_type.app_label, 'model': obj.content_type.model,
                    'name': str(obj.content_type)}
        return None

    @extend_schema_field(serializers.DictField())
    def get_access_info(self, obj):
        """Use model methods for access control"""
        request = self.context.get('request')
        if request and request.user:
            return {'can_access': obj.user_can_access(request.user),
                    'access_level': obj.get_access_level_for_user(request.user)}
        return {'can_access': False, 'access_level': 'no_access'}

    @extend_schema_field(serializers.DictField())
    def get_auto_properties(self, obj):
        """Use model method for auto-detected properties"""
        return obj.auto_detect_properties()

    def create(self, validated_data):
        """Enhanced create using model methods"""
        request = self.context.get('request')

        # Auto-assign uploader
        if request and request.user.is_authenticated:
            validated_data['uploaded_by'] = request.user

        # Use model method for auto-detection
        document = Documents(**validated_data)
        auto_properties = document.auto_detect_properties(validated_data.get('file'))

        # Apply auto-detected properties that weren't explicitly set
        for key, value in auto_properties.items():
            if key not in validated_data or not validated_data[key]:
                validated_data[key] = value

        return super().create(validated_data)


class DocumentSerializer(serializers.ModelSerializer):
    """Alternative document serializer for compatibility"""
    file_url = serializers.SerializerMethodField()
    uploaded_by_name = serializers.SerializerMethodField()
    content_type_model = serializers.SerializerMethodField()
    access_level = serializers.SerializerMethodField()

    class Meta:
        model = Documents
        fields = ["id", "is_image", "file_name", "file", "file_url", "upload_date", "uploaded_by", "uploaded_by_name",
                  "content_type", "content_type_model", "object_id", "version", "classification", "access_level",
                  "ai_readable"]
        read_only_fields = ["upload_date", "uploaded_by_name", "file_url", "content_type_model", "access_level"]

    def get_file_url(self, obj) -> str | None:
        try:
            return obj.file.url if obj.file else None
        except ValueError:
            return None

    def get_uploaded_by_name(self, obj) -> str:
        if obj.uploaded_by:
            first = obj.uploaded_by.first_name or ""
            last = obj.uploaded_by.last_name or ""
            return f"{first} {last}".strip() or obj.uploaded_by.username
        return "Unknown"

    def get_content_type_model(self, obj) -> str | None:
        return obj.content_type.model if obj.content_type else None

    def get_access_level(self, obj) -> str:
        """Use model method for access level"""
        request = self.context.get('request')
        if request and request.user:
            return obj.get_access_level_for_user(request.user)
        return "no_access"

    def validate_file(self, file):
        if not file.name.lower().endswith((".pdf", ".png", ".jpg", ".jpeg", ".docx")):
            raise serializers.ValidationError("Unsupported file type.")
        return file

    def create(self, validated_data):
        request = self.context.get("request")
        file = validated_data.get("file")

        # Use model method for auto-detection
        document = Documents(**validated_data)
        auto_properties = document.auto_detect_properties(file)

        # Apply auto-detected properties
        for key, value in auto_properties.items():
            if key not in validated_data:
                validated_data[key] = value

        # Auto-assign uploader
        if request and request.user.is_authenticated:
            validated_data["uploaded_by"] = request.user

        return super().create(validated_data)


# ===== STEP AND PROCESS SERIALIZERS =====

class StepsSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Enhanced steps serializer with resolved sampling rules"""
    process_info = serializers.SerializerMethodField()
    part_type_info = serializers.SerializerMethodField()
    resolved_sampling_rules = serializers.SerializerMethodField()
    sampling_coverage = serializers.SerializerMethodField()

    # Legacy compatibility fields
    process_name = serializers.CharField(source="process.name", read_only=True)
    part_type_name = serializers.CharField(source="process.part_type.name", read_only=True)

    class Meta:
        model = Steps
        fields = ('id', 'name', 'order', 'expected_duration', 'description', 'is_last_step', 'block_on_quarantine',
                  'requires_qa_signoff', 'sampling_required', 'min_sampling_rate', 'pass_threshold', 'process',
                  'part_type', 'process_info', 'part_type_info', 'resolved_sampling_rules', 'sampling_coverage',
                  'process_name', 'part_type_name', 'created_at', 'updated_at', 'archived')
        read_only_fields = (
            'created_at', 'updated_at', 'archived', 'process_info', 'part_type_info', 'resolved_sampling_rules',
            'sampling_coverage', 'process_name', 'part_type_name')

    @extend_schema_field(serializers.DictField())
    def get_process_info(self, obj):
        if obj.process:
            return {'id': obj.process.id, 'name': obj.process.name, 'is_remanufactured': obj.process.is_remanufactured,
                    'version': obj.process.version}
        return None

    @extend_schema_field(serializers.DictField())
    def get_part_type_info(self, obj):
        if obj.part_type:
            return {'id': obj.part_type.id, 'name': obj.part_type.name, 'version': obj.part_type.version,
                    'ID_prefix': obj.part_type.ID_prefix}
        return None

    @extend_schema_field(serializers.JSONField())
    def get_resolved_sampling_rules(self, obj):
        """Use model method for resolved sampling rules"""
        resolved_rules = obj.get_resolved_sampling_rules()  # Get the raw resolved sampling rules

        # Ensure that resolved_rules is either a list of SamplingRule objects or data that can be serialized
        if resolved_rules:
            # If resolved_rules is a list or queryset of SamplingRule objects, serialize them
            if hasattr(resolved_rules, 'all'):  # This checks if resolved_rules is a queryset
                return SamplingRuleSerializer(resolved_rules, many=True).data
            # Otherwise, if it's a dictionary, return it directly
            return resolved_rules

        return {}  # Return an empty dictionary if no resolved rules are found

    @extend_schema_field(serializers.DictField())
    def get_sampling_coverage(self, obj):
        """Use model method for sampling coverage report"""
        request = self.context.get('request')
        work_order_id = request.GET.get('work_order_id') if request else None

        if work_order_id:
            try:
                work_order = WorkOrder.objects.get(id=work_order_id)
                coverage_report = obj.get_sampling_coverage_report(work_order)

                # Since get_sampling_coverage_report already returns a dictionary, return it directly
                return coverage_report
            except WorkOrder.DoesNotExist:
                pass

        return {}


class StepSerializer(serializers.ModelSerializer):
    """Legacy step serializer for compatibility"""
    process_name = serializers.CharField(source="process.name", read_only=True)
    part_type_name = serializers.CharField(source="process.part_type.name", read_only=True)

    class Meta:
        model = Steps
        fields = ["name", "id", "order", "description", "is_last_step", "process", "part_type", "process_name",
                  "part_type_name", "sampling_required", "min_sampling_rate"]


class PartTypesSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Part types serializer"""

    class Meta:
        model = PartTypes
        fields = "__all__"


class PartTypeSerializer(serializers.ModelSerializer):
    """Legacy part type serializer"""

    class Meta:
        model = PartTypes
        fields = "__all__"


class ProcessesSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Processes serializer"""
    part_type_name = serializers.CharField(source="part_type.name", read_only=True)
    steps = StepSerializer(many=True, read_only=True)

    class Meta:
        model = Processes
        fields = "__all__"


class ProcessWithStepsSerializer(serializers.ModelSerializer):
    """Process with steps serializer for creation/updates"""
    steps = StepSerializer(many=True)

    class Meta:
        model = Processes
        fields = ["id", "name", "is_remanufactured", "part_type", "steps", "num_steps", "is_batch_process"]

    def create(self, validated_data):
        steps_data = validated_data.pop("steps", [])
        process = Processes.objects.create(**validated_data)

        for step_index, step_data in enumerate(steps_data):
            step = Steps.objects.create(process=process, part_type=process.part_type, order=step_index + 1, **step_data)

        return process

    def update(self, instance, validated_data):
        steps_data = validated_data.pop("steps", [])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Replace all steps and related rulesets
        instance.steps.all().delete()  # Use soft delete from SecureManager

        for step_index, step_data in enumerate(steps_data):
            step = Steps.objects.create(process=instance, part_type=instance.part_type, order=step_index + 1,
                                        **step_data)

        return instance


# ===== EQUIPMENT SERIALIZERS =====

class EquipmentTypeSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Equipment type serializer"""

    class Meta:
        model = EquipmentType
        fields = "__all__"


class EquipmentsSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Equipment serializer"""
    equipment_type_name = serializers.CharField(source="equipment_type.name", read_only=True)

    class Meta:
        model = Equipments
        fields = ["id", "name", "equipment_type", "equipment_type_name"]


class EquipmentSerializer(serializers.ModelSerializer):
    """Legacy equipment serializer"""
    equipment_type_name = serializers.CharField(source="equipment_type.name", read_only=True)

    class Meta:
        model = Equipments
        fields = ["id", "name", "equipment_type", "equipment_type_name"]


class EquipmentSelectSerializer(serializers.ModelSerializer):
    """Equipment select serializer"""
    equipment_type = EquipmentTypeSerializer(read_only=True)

    class Meta:
        model = Equipments
        fields = "__all__"


# ===== EXTERNAL API SERIALIZERS =====

class ExternalAPIOrderIdentifierSerializer(serializers.ModelSerializer, SecureModelMixin):
    """External API order identifier serializer"""

    class Meta:
        model = ExternalAPIOrderIdentifier
        fields = "__all__"


# ===== QUALITY AND ERROR SERIALIZERS =====

class QualityErrorsListSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Quality errors list serializer"""
    part_type_name = serializers.CharField(source="part_type.name", read_only=True)

    class Meta:
        model = QualityErrorsList
        fields = ["id", "error_name", "error_example", "part_type", "part_type_name"]


class ErrorTypeSerializer(serializers.ModelSerializer):
    """Legacy error type serializer"""
    part_type_name = serializers.CharField(source="part_type.name", read_only=True)

    class Meta:
        model = QualityErrorsList
        fields = ["id", "error_name", "error_example", "part_type", "part_type_name"]


class MeasurementDefinitionSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Measurement definition serializer"""
    step_name = serializers.SerializerMethodField()

    class Meta:
        model = MeasurementDefinition
        fields = ["id", "label", "step_name", "unit", "nominal", "upper_tol", "lower_tol", "required", "type", "step"]
        read_only_fields = ["id", "step"]

    @extend_schema_field(serializers.CharField())
    def get_step_name(self, obj) -> str | None:
        return obj.step.name if obj.step else None


class MeasurementResultSerializer(serializers.ModelSerializer, SecureModelMixin):
    report = serializers.CharField(read_only=True)
    is_within_spec = serializers.BooleanField(read_only=True)
    created_by = serializers.IntegerField(read_only=True)

    class Meta:
        model = MeasurementResult
        fields = ["report", "definition", "value_numeric", "value_pass_fail", "is_within_spec", "created_by"]


class QualityReportsSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Quality reports serializer"""
    measurements = MeasurementResultSerializer(many=True, write_only=True)

    class Meta:
        model = QualityReports
        fields = ["id", "step", "part", "machine", "operator", "sampling_rule", "sampling_method", "status",
                  "description", "file", "created_at", "errors", "measurements", "sampling_audit_log"]

    def create(self, validated_data):
        measurements_data = validated_data.pop("measurements", [])
        report = super().create(validated_data)

        for m in measurements_data:
            # Create measurement result - is_within_spec is automatically calculated by save() method
            MeasurementResult.objects.create(report=report, definition_id=m['definition'].id,
                                             value_numeric=m.get('value_numeric'),
                                             value_pass_fail=m.get('value_pass_fail'),
                                             created_by=self.context["request"].user)

        return report


# ===== SAMPLING SERIALIZERS =====

class SamplingRuleSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Enhanced sampling rule serializer"""
    rule_type_display = serializers.CharField(source='get_rule_type_display', read_only=True)
    ruleset_info = serializers.SerializerMethodField()

    # Legacy compatibility fields
    ruletype_name = serializers.SerializerMethodField()
    ruleset_name = serializers.CharField(source="ruleset.name", read_only=True)

    class Meta:
        model = SamplingRule
        fields = (
        'id', 'rule_type', 'rule_type_display', 'value', 'order', 'algorithm_description', 'last_validated', 'ruleset',
        'ruleset_info', 'created_by', 'created_at', 'modified_by', 'updated_at', 'archived', 'ruletype_name',
        'ruleset_name')
        read_only_fields = ('created_at', 'updated_at', 'archived', 'ruleset_info', 'ruletype_name', 'ruleset_name')

    @extend_schema_field(serializers.DictField())
    def get_ruleset_info(self, obj):
        if obj.ruleset:
            return {'id': obj.ruleset.id, 'name': obj.ruleset.name, 'version': obj.ruleset.version}
        return None

    @extend_schema_field(serializers.CharField())
    def get_ruletype_name(self, obj) -> str:
        return obj.get_rule_type_display()


class SamplingRuleSetSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Enhanced sampling ruleset serializer"""
    rules = serializers.SerializerMethodField()
    part_type_info = serializers.SerializerMethodField()
    process_info = serializers.SerializerMethodField()
    step_info = serializers.SerializerMethodField()

    # Legacy compatibility fields
    part_type_name = serializers.CharField(source="part_type.name", read_only=True)
    process_name = serializers.CharField(source="process.name", read_only=True)

    class Meta:
        model = SamplingRuleSet
        fields = ('id', 'name', 'origin', 'active', 'version', 'is_fallback', 'fallback_threshold', 'fallback_duration',
                  'archived', 'part_type', 'part_type_info', 'process', 'process_info', 'step', 'step_info', 'rules',
                  'created_by', 'created_at', 'modified_by', 'updated_at', 'archived', 'part_type_name', 'process_name')
        read_only_fields = (
            'created_at', 'updated_at', 'archived', 'rules', 'part_type_info', 'process_info', 'step_info',
            'part_type_name', 'process_name')

    @extend_schema_field(serializers.ListField())
    def get_rules(self, obj):
        # Use model method to avoid circular import
        return obj.get_rules_summary() if hasattr(obj, 'get_rules_summary') else list(
            obj.rules.all().values('id', 'rule_type', 'value', 'order', 'algorithm_description', 'last_validated'))

    @extend_schema_field(serializers.DictField())
    def get_part_type_info(self, obj):
        if obj.part_type:
            return {'id': obj.part_type.id, 'name': obj.part_type.name}
        return None

    @extend_schema_field(serializers.DictField())
    def get_process_info(self, obj):
        if obj.process:
            return {'id': obj.process.id, 'name': obj.process.name}
        return None

    @extend_schema_field(serializers.DictField())
    def get_step_info(self, obj):
        if obj.step:
            return {'id': obj.step.id, 'name': obj.step.name, 'order': obj.step.order}
        return None


class ResolvedSamplingRuleSetSerializer(serializers.ModelSerializer):
    """Resolved sampling ruleset serializer"""
    rules = SamplingRuleSerializer(many=True, read_only=True)

    class Meta:
        model = SamplingRuleSet
        fields = ["id", "name", "rules", "fallback_threshold", "fallback_duration"]


class StepWithResolvedRulesSerializer(serializers.ModelSerializer):
    """Step with resolved sampling rules"""
    active_ruleset = serializers.SerializerMethodField()
    fallback_ruleset = serializers.SerializerMethodField()
    process_name = serializers.CharField(source="process.name", read_only=True)
    part_type_name = serializers.CharField(source="part_type.name", read_only=True)
    sampling_coverage = serializers.SerializerMethodField()

    class Meta:
        model = Steps
        fields = ["id", "name", "description", "expected_duration", "order", "part_type", "part_type_name", "process",
                  "process_name", "active_ruleset", "fallback_ruleset", "sampling_required", "min_sampling_rate",
                  "sampling_coverage"]

    @extend_schema_field(ResolvedSamplingRuleSetSerializer)
    def get_active_ruleset(self, step):
        """Use model method for resolved sampling rules"""
        resolved = step.get_resolved_sampling_rules()
        return resolved.get('active_ruleset')

    @extend_schema_field(ResolvedSamplingRuleSetSerializer)
    def get_fallback_ruleset(self, step):
        """Use model method for resolved sampling rules"""
        resolved = step.get_resolved_sampling_rules()
        return resolved.get('fallback_ruleset')

    @extend_schema_field(serializers.DictField())
    def get_sampling_coverage(self, step):
        """Get sampling coverage for work orders at this step"""
        request = self.context.get('request')
        work_order_id = request.GET.get('work_order_id') if request else None

        if work_order_id:
            try:
                work_order = WorkOrder.objects.get(id=work_order_id)
                return step.get_sampling_coverage_report(work_order)
            except WorkOrder.DoesNotExist:
                pass

        return None


# ===== BULK OPERATION SERIALIZERS =====

class BulkSoftDeleteSerializer(serializers.Serializer, BulkOperationsMixin):
    """Serializer for bulk soft delete operations"""
    ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
    reason = serializers.CharField(max_length=200, default="bulk_admin_delete")

    def perform_bulk_delete(self, model_class):
        """Perform bulk soft delete using SecureManager"""
        ids = self.validated_data['ids']
        reason = self.validated_data['reason']

        queryset = model_class.objects.filter(id__in=ids)
        return self.bulk_soft_delete(queryset, reason)


class BulkRestoreSerializer(serializers.Serializer, BulkOperationsMixin):
    """Serializer for bulk restore operations"""
    ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
    reason = serializers.CharField(max_length=200, default="bulk_admin_restore")

    def perform_bulk_restore(self, model_class):
        """Perform bulk restore using SecureManager"""
        ids = self.validated_data['ids']
        reason = self.validated_data['reason']

        queryset = model_class.all_objects.filter(id__in=ids, archived=True)
        return self.bulk_restore(queryset, reason)


class BulkAddPartsSerializer(serializers.Serializer):
    """Legacy bulk add parts serializer"""
    part_type = serializers.PrimaryKeyRelatedField(queryset=PartTypes.objects.all(), source="part_type_id")
    step = serializers.PrimaryKeyRelatedField(queryset=Steps.objects.all(), source="step_id")
    quantity = serializers.IntegerField(min_value=1)
    part_status = serializers.ChoiceField(choices=PartsStatus.choices)
    process_id = serializers.IntegerField()
    ERP_id = serializers.CharField()


class BulkRemovePartsSerializer(serializers.Serializer):
    """Legacy bulk remove parts serializer"""
    ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)


# ===== STEP ADVANCEMENT SERIALIZERS =====

class StepAdvancementSerializer(serializers.ModelSerializer):
    """Serializer for part step advancement"""

    class Meta:
        model = Parts
        fields = ['id', 'part_status', 'step']
        read_only_fields = ['id', 'part_status', 'step']

    def update(self, instance, validated_data):
        """Use model method for step advancement"""
        result = instance.increment_step()
        return instance


class IncrementStepSerializer(serializers.ModelSerializer):
    """Legacy increment step serializer"""

    class Meta:
        model = Parts
        fields = []  # no input fields required

    def update(self, instance, validated_data):
        result = instance.increment_step()
        return instance


class BulkStepAdvancementSerializer(serializers.Serializer):
    """Serializer for bulk step advancement"""
    step_id = serializers.IntegerField()

    def advance_parts_at_step(self, order):
        """Use model method for bulk step advancement"""
        step_id = self.validated_data['step_id']
        return order.bulk_increment_parts_at_step(step_id)


# ===== SAMPLING RULES UPDATE SERIALIZERS =====

class SamplingRuleUpdateSerializer(serializers.Serializer):
    """Serializer for updating sampling rules on steps"""
    rule_type = serializers.ChoiceField(choices=SamplingRule.RuleType.choices)
    value = serializers.IntegerField(allow_null=True, required=False)
    order = serializers.IntegerField()


class SamplingRuleWriteSerializer(serializers.Serializer):
    """Write serializer for sampling rules"""
    rule_type = serializers.ChoiceField(choices=SamplingRule.RuleType.choices)
    value = serializers.IntegerField(allow_null=True, required=False)
    order = serializers.IntegerField()
    is_fallback = serializers.BooleanField(required=False)


class StepSamplingRulesUpdateSerializer(serializers.Serializer):
    """Serializer for updating step sampling rules"""
    rules = SamplingRuleUpdateSerializer(many=True)
    fallback_rules = SamplingRuleUpdateSerializer(many=True, required=False)
    fallback_threshold = serializers.IntegerField(required=False)
    fallback_duration = serializers.IntegerField(required=False)

    def update_step_rules(self, step):
        """Use model method for applying sampling rules"""
        user = self.context.get('request', {}).user

        return step.apply_sampling_rules_update(rules_data=self.validated_data['rules'],
                                                fallback_rules_data=self.validated_data.get('fallback_rules', []),
                                                fallback_threshold=self.validated_data.get('fallback_threshold'),
                                                fallback_duration=self.validated_data.get('fallback_duration'),
                                                user=user)


class StepSamplingRulesWriteSerializer(serializers.Serializer):
    """Write serializer for step sampling rules"""
    rules = SamplingRuleWriteSerializer(many=True)
    fallback_rules = SamplingRuleWriteSerializer(many=True, required=False)
    fallback_threshold = serializers.IntegerField(required=False)
    fallback_duration = serializers.IntegerField(required=False)

    def save(self, step: Steps):
        """Use the model method for applying sampling rules"""
        user = self.context["request"].user

        rules = self.validated_data["rules"]
        fallback_data = self.validated_data.get("fallback_rules", [])
        threshold = self.validated_data.get("fallback_threshold")
        duration = self.validated_data.get("fallback_duration")

        return step.apply_sampling_rules_update(rules_data=rules, fallback_rules_data=fallback_data,
                                                fallback_threshold=threshold, fallback_duration=duration, user=user)


class StepSamplingRulesResponseSerializer(serializers.Serializer):
    """Response serializer for sampling rules updates"""
    detail = serializers.CharField()
    ruleset_id = serializers.IntegerField()
    step_id = serializers.IntegerField()


# ===== CSV UPLOAD SERIALIZERS =====

class WorkOrderCSVUploadSerializer(serializers.Serializer):
    """Serializer for CSV work order uploads using model methods"""
    ERP_id = serializers.CharField()
    workorder_status = serializers.ChoiceField(choices=WorkOrderStatus.choices, required=False)
    related_order_erp_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    quantity = serializers.IntegerField()
    expected_completion = serializers.CharField(required=False, allow_blank=True)
    expected_duration = serializers.DurationField(required=False)
    true_duration = serializers.DurationField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate_expected_completion(self, value):
        """Use model method for date processing"""
        if not value:
            return None
        try:
            return WorkOrder.process_csv_date(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))

    def create_work_order(self):
        """Use model method for CSV creation"""
        user = self.context.get('request', {}).user
        work_order, created, warnings = WorkOrder.create_from_csv_row(self.validated_data, user=user)
        return work_order, created, warnings


class WorkOrderUploadSerializer(serializers.Serializer):
    """Alternative work order upload serializer"""
    ERP_id = serializers.CharField()
    workorder_status = serializers.ChoiceField(choices=WorkOrderStatus.choices, required=False)
    related_order_erp_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    quantity = serializers.IntegerField()
    expected_completion = serializers.CharField(required=False, allow_blank=True)
    expected_duration = serializers.DurationField(required=False)
    true_duration = serializers.DurationField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    part_type_erp_id = serializers.CharField(required=False)

    def validate_expected_completion(self, value):
        """Use model method for date processing"""
        if not value:
            return None
        try:
            return WorkOrder.process_csv_date(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))

    def validate_related_order_erp_id(self, value):
        if not value:
            return None
        try:
            return Orders.objects.get(ERP_id=value)
        except Orders.DoesNotExist:
            return None

    def create_or_update(self, validated_data):
        """Use model method for CSV creation"""
        try:
            work_order, created, warnings = WorkOrder.create_from_csv_row(validated_data,
                                                                          user=self.context.get('request', {}).get(
                                                                              'user'))
            return work_order
        except ValueError as e:
            raise serializers.ValidationError(str(e))


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


# ===== ANALYTICS SERIALIZERS =====

class SamplingAnalyticsSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Enhanced sampling analytics serializer using model properties"""
    ruleset_info = serializers.SerializerMethodField()
    work_order_info = serializers.SerializerMethodField()
    effectiveness = serializers.FloatField(source='sampling_effectiveness', read_only=True)
    is_compliant = serializers.BooleanField(read_only=True)

    # Legacy compatibility fields
    ruleset_name = serializers.CharField(source="ruleset.name", read_only=True)
    work_order_erp = serializers.CharField(source="work_order.ERP_id", read_only=True)
    sampling_effectiveness = serializers.FloatField(read_only=True)

    class Meta:
        model = SamplingAnalytics
        fields = ('id', 'parts_sampled', 'parts_total', 'defects_found', 'actual_sampling_rate', 'target_sampling_rate',
                  'variance', 'effectiveness', 'is_compliant', 'ruleset', 'ruleset_info', 'work_order',
                  'work_order_info', 'created_at', 'archived', 'ruleset_name', 'work_order_erp',
                  'sampling_effectiveness')
        read_only_fields = (
            'created_at', 'archived', 'effectiveness', 'is_compliant', 'ruleset_info', 'work_order_info',
            'ruleset_name', 'work_order_erp', 'sampling_effectiveness')

    @extend_schema_field(serializers.DictField())
    def get_ruleset_info(self, obj):
        if obj.ruleset:
            return {'id': obj.ruleset.id, 'name': obj.ruleset.name, 'version': obj.ruleset.version}
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_work_order_info(self, obj):
        if obj.work_order:
            return {'id': obj.work_order.id, 'ERP_id': obj.work_order.ERP_id, 'status': obj.work_order.workorder_status}
        return {}


class SamplingAuditLogSerializer(serializers.ModelSerializer):
    """Sampling audit log serializer"""
    part_erp_id = serializers.CharField(source="part.ERP_id", read_only=True)
    rule_type = serializers.CharField(source="rule.rule_type", read_only=True)
    work_order_erp = serializers.CharField(source="part.work_order.ERP_id", read_only=True)

    class Meta:
        model = SamplingAuditLog
        fields = ["id", "part", "part_erp_id", "rule", "rule_type", "hash_input", "hash_output", "sampling_decision",
                  "timestamp", "ruleset_type", "work_order_erp"]
        read_only_fields = ["id", "timestamp"]


class SamplingTriggerStateSerializer(serializers.ModelSerializer):
    """Sampling trigger state serializer"""
    ruleset_name = serializers.CharField(source="ruleset.name", read_only=True)
    work_order_erp = serializers.CharField(source="work_order.ERP_id", read_only=True)
    step_name = serializers.CharField(source="step.name", read_only=True)
    triggered_by_status = serializers.CharField(source="triggered_by.status", read_only=True)

    class Meta:
        model = SamplingTriggerState
        fields = ["id", "ruleset", "ruleset_name", "work_order", "work_order_erp", "step", "step_name", "active",
                  "triggered_by", "triggered_by_status", "triggered_at", "success_count", "fail_count",
                  "parts_inspected"]
        read_only_fields = ["id", "triggered_at"]


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

            # 🔥 Custom URL pointing to your frontend
            custom_url = f"{frontend_url}/reset-password/{uid}/{temp_key}/"

            context = {'current_site': current_site, 'user': user, 'site_name': "AMBAC",
                       'password_reset_url': custom_url,  # This is the key!
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
    """Serializer for Django Groups"""

    class Meta:
        model = Group
        fields = ('id', 'name')


class UserSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Enhanced user serializer with company and permission info"""
    full_name = serializers.SerializerMethodField()
    parent_company = CompanySerializer(read_only=True, allow_null=True)
    parent_company_id = serializers.PrimaryKeyRelatedField(queryset=Companies.objects.all(), source='parent_company',
                                                           write_only=True, required=False, allow_null=True)
    groups = GroupSerializer(many=True, read_only=True)
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


class QuarantineDispositionSerializer(serializers.ModelSerializer, SecureModelMixin):
    disposition_number = serializers.CharField(read_only=True)
    assignee_name = serializers.SerializerMethodField()
    choices_data = serializers.SerializerMethodField()
    resolution_completed_by_name = serializers.SerializerMethodField()
    step_info = serializers.SerializerMethodField()
    rework_limit_exceeded = serializers.SerializerMethodField()

    class Meta:
        model = QuarantineDisposition
        fields = ('id', 'disposition_number', 'current_state', 'disposition_type', 'assigned_to', 'description',
                  'resolution_notes', 'resolution_completed', 'resolution_completed_by', 'resolution_completed_by_name',
                  'resolution_completed_at', 'part', 'step', 'step_info', 'rework_attempt_at_step',
                  'rework_limit_exceeded', 'quality_reports', 'assignee_name', 'choices_data')

        read_only_fields = ('disposition_number', 'assignee_name', 'choices_data', 'step_info', 'rework_limit_exceeded')

    @extend_schema_field(serializers.CharField())
    def get_assignee_name(self, obj):
        """Get formatted full name or fallback to username"""
        if obj.assigned_to:
            return f"{obj.assigned_to.first_name} {obj.assigned_to.last_name}".strip() or obj.username
        else:
            return ""

    @extend_schema_field(serializers.CharField())
    def get_resolution_completed_by_name(self, obj):
        if obj.resolution_completed_by:
            return f"{obj.resolution_completed_by.first_name} {obj.resolution_completed_by.last_name}".strip() or obj.username
        else:
            return ""

    @extend_schema_field(serializers.DictField())
    def get_choices_data(self, obj):
        return {'state_choices': QuarantineDisposition.STATE_CHOICES,
            'disposition_type_choices': QuarantineDisposition.DISPOSITION_TYPES}

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_step_info(self, obj):
        if obj.step:
            return {'id': obj.step.id, 'name': obj.step.name, 'order': obj.step.order,
                'description': obj.step.description}
        return None

    @extend_schema_field(serializers.BooleanField())
    def get_rework_limit_exceeded(self, obj):
        """Check if rework limit is exceeded for this step"""
        return obj.check_rework_limit_exceeded()


class ThreeDModelSerializer(SecureModelMixin, serializers.ModelSerializer):
    """Serializer for 3D model files"""
    part_type_display = serializers.CharField(source='part_type.__str__', read_only=True)
    step_display = serializers.CharField(source='step.__str__', read_only=True)
    annotation_count = serializers.SerializerMethodField()

    class Meta:
        model = ThreeDModel
        fields = [
            'id', 'name', 'file', 'part_type', 'part_type_display', 'step', 'step_display',
            'uploaded_at', 'file_type', 'annotation_count', 'created_at', 'updated_at',
            'archived', 'deleted_at'
        ]
        read_only_fields = ['uploaded_at', 'file_type', 'created_at', 'updated_at', 'archived', 'deleted_at']

    @extend_schema_field(serializers.IntegerField())
    def get_annotation_count(self, obj):
        """Get count of annotations on this model"""
        return obj.annotations.filter(archived=False).count()


class HeatMapAnnotationsSerializer(SecureModelMixin, serializers.ModelSerializer):
    """Serializer for heatmap annotations"""
    model_display = serializers.CharField(source='model.__str__', read_only=True)
    part_display = serializers.CharField(source='part.__str__', read_only=True)
    created_by_display = serializers.SerializerMethodField()

    class Meta:
        model = HeatMapAnnotations
        fields = [
            'id', 'model', 'model_display', 'part', 'part_display',
            'position_x', 'position_y', 'position_z',
            'measurement_value', 'defect_type', 'severity',
            'notes', 'created_by', 'created_by_display', 'created_at', 'updated_at',
            'archived', 'deleted_at'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'archived', 'deleted_at']

    @extend_schema_field(serializers.CharField())
    def get_created_by_display(self, obj):
        """Get full name of creator"""
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip() or obj.created_by.email
        return None

    def create(self, validated_data):
        """Set created_by to current user"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['created_by'] = request.user
        return super().create(validated_data)


# ===== NOTIFICATION SERIALIZERS =====

class NotificationScheduleSerializer(serializers.Serializer):
    """
    Nested serializer for notification schedule configuration.
    Handles both fixed and deadline-based interval types.
    """
    interval_type = serializers.ChoiceField(choices=['fixed', 'deadline_based'])

    # Fixed interval fields (for recurring notifications)
    day_of_week = serializers.IntegerField(min_value=0, max_value=6, required=False, allow_null=True,
                                          help_text="0=Monday, 6=Sunday")
    time = serializers.TimeField(required=False, allow_null=True, help_text="Time in user's local timezone")
    interval_weeks = serializers.IntegerField(min_value=1, required=False, allow_null=True,
                                             help_text="Number of weeks between sends")

    # Deadline-based fields (for escalating notifications)
    escalation_tiers = serializers.ListField(
        child=serializers.ListField(child=serializers.FloatField(), min_length=2, max_length=2),
        required=False,
        allow_null=True,
        help_text="List of [threshold_days, interval_days] tuples"
    )

    def validate(self, attrs):
        """Validate that correct fields are present for each interval_type."""
        interval_type = attrs.get('interval_type')

        if interval_type == 'fixed':
            # Fixed interval requires day_of_week, time, interval_weeks
            required_fields = ['day_of_week', 'time', 'interval_weeks']
            missing = [f for f in required_fields if not attrs.get(f)]
            if missing:
                raise serializers.ValidationError(
                    f"Fixed interval requires: {', '.join(missing)}"
                )

        elif interval_type == 'deadline_based':
            # Deadline-based requires escalation_tiers
            if not attrs.get('escalation_tiers'):
                raise serializers.ValidationError(
                    "Deadline-based interval requires escalation_tiers"
                )

        return attrs


class NotificationPreferenceSerializer(serializers.ModelSerializer, SecureModelMixin):
    """
    Serializer for user notification preferences.

    Handles timezone conversion:
    - INPUT: User sends time in their local timezone
    - STORED: Time converted to UTC in database
    - OUTPUT: Time converted back to user's local timezone
    """
    schedule = NotificationScheduleSerializer(required=False)
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    channel_type_display = serializers.CharField(source='get_channel_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    # Read-only fields
    next_send_at_display = serializers.SerializerMethodField()
    last_sent_at_display = serializers.SerializerMethodField()

    class Meta:
        model = NotificationTask
        fields = (
            'id', 'notification_type', 'notification_type_display', 'channel_type', 'channel_type_display',
            'status', 'status_display', 'schedule', 'next_send_at', 'next_send_at_display',
            'last_sent_at', 'last_sent_at_display', 'attempt_count', 'max_attempts',
            'created_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'notification_type_display', 'channel_type_display', 'status', 'status_display',
            'next_send_at', 'next_send_at_display', 'last_sent_at', 'last_sent_at_display',
            'attempt_count', 'created_at', 'updated_at'
        )

    @extend_schema_field(serializers.DateTimeField(allow_null=True))
    def get_next_send_at_display(self, obj):
        """Convert next_send_at from UTC to user's timezone."""
        if not obj.next_send_at:
            return None

        request = self.context.get('request')
        if request and hasattr(request, 'user') and hasattr(request.user, 'timezone'):
            import pytz
            user_tz = pytz.timezone(request.user.timezone) if request.user.timezone else pytz.UTC
            return obj.next_send_at.astimezone(user_tz).isoformat()

        return obj.next_send_at.isoformat()

    @extend_schema_field(serializers.DateTimeField(allow_null=True))
    def get_last_sent_at_display(self, obj):
        """Convert last_sent_at from UTC to user's timezone."""
        if not obj.last_sent_at:
            return None

        request = self.context.get('request')
        if request and hasattr(request, 'user') and hasattr(request.user, 'timezone'):
            import pytz
            user_tz = pytz.timezone(request.user.timezone) if request.user.timezone else pytz.UTC
            return obj.last_sent_at.astimezone(user_tz).isoformat()

        return obj.last_sent_at.isoformat()

    def to_representation(self, instance):
        """Convert schedule fields to nested format for output."""
        data = super().to_representation(instance)

        # Build schedule object from model fields
        schedule = {
            'interval_type': instance.interval_type,
        }

        if instance.interval_type == 'fixed':
            schedule['day_of_week'] = instance.day_of_week
            schedule['interval_weeks'] = instance.interval_weeks

            # Convert time from UTC to user's timezone
            if instance.time:
                request = self.context.get('request')
                if request and hasattr(request, 'user') and hasattr(request.user, 'timezone'):
                    import pytz
                    from datetime import datetime
                    user_tz = pytz.timezone(request.user.timezone) if request.user.timezone else pytz.UTC
                    # Combine with arbitrary date to convert timezone
                    dt = datetime.combine(datetime.now().date(), instance.time)
                    dt_utc = pytz.UTC.localize(dt)
                    dt_local = dt_utc.astimezone(user_tz)
                    schedule['time'] = dt_local.time().isoformat()
                else:
                    schedule['time'] = instance.time.isoformat()

        elif instance.interval_type == 'deadline_based':
            schedule['escalation_tiers'] = instance.escalation_tiers

        data['schedule'] = schedule
        return data

    def create(self, validated_data):
        """Create notification preference with timezone conversion."""
        schedule_data = validated_data.pop('schedule', {})
        request = self.context.get('request')

        # Set recipient to current user
        validated_data['recipient'] = request.user

        # Extract schedule fields
        validated_data['interval_type'] = schedule_data.get('interval_type')

        if validated_data['interval_type'] == 'fixed':
            validated_data['day_of_week'] = schedule_data.get('day_of_week')
            validated_data['interval_weeks'] = schedule_data.get('interval_weeks')

            # Convert time from user's timezone to UTC
            time_local = schedule_data.get('time')
            if time_local and hasattr(request.user, 'timezone'):
                import pytz
                from datetime import datetime
                user_tz = pytz.timezone(request.user.timezone) if request.user.timezone else pytz.UTC
                # Combine with arbitrary date to convert timezone
                dt_local = user_tz.localize(datetime.combine(datetime.now().date(), time_local))
                dt_utc = dt_local.astimezone(pytz.UTC)
                validated_data['time'] = dt_utc.time()
            else:
                validated_data['time'] = time_local

        elif validated_data['interval_type'] == 'deadline_based':
            validated_data['escalation_tiers'] = schedule_data.get('escalation_tiers')
            # deadline and related_object will be set by signals or business logic

        # Create the notification task
        notification = NotificationTask(**validated_data)
        notification.next_send_at = notification.calculate_next_send()
        notification.save()

        return notification

    def update(self, instance, validated_data):
        """Update notification preference with timezone conversion."""
        schedule_data = validated_data.pop('schedule', {})
        request = self.context.get('request')

        # Update basic fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Update schedule fields
        if schedule_data:
            instance.interval_type = schedule_data.get('interval_type', instance.interval_type)

            if instance.interval_type == 'fixed':
                instance.day_of_week = schedule_data.get('day_of_week', instance.day_of_week)
                instance.interval_weeks = schedule_data.get('interval_weeks', instance.interval_weeks)

                # Convert time from user's timezone to UTC
                time_local = schedule_data.get('time')
                if time_local and hasattr(request.user, 'timezone'):
                    import pytz
                    from datetime import datetime
                    user_tz = pytz.timezone(request.user.timezone) if request.user.timezone else pytz.UTC
                    dt_local = user_tz.localize(datetime.combine(datetime.now().date(), time_local))
                    dt_utc = dt_local.astimezone(pytz.UTC)
                    instance.time = dt_utc.time()
                elif time_local:
                    instance.time = time_local

            elif instance.interval_type == 'deadline_based':
                instance.escalation_tiers = schedule_data.get('escalation_tiers', instance.escalation_tiers)

            # Recalculate next send time
            instance.next_send_at = instance.calculate_next_send()

        instance.save()
        return instance

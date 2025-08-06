# serializers.py - Complete merged version with SecureModel integration
from allauth import app_settings
from allauth.account.adapter import get_adapter
from allauth.account.forms import default_token_generator
from allauth.account.utils import user_username, filter_users_by_email, user_pk_to_url_str
from allauth.utils import build_absolute_uri
from auditlog.models import LogEntry
from dj_rest_auth.forms import AllAuthPasswordResetForm
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.shortcuts import get_current_site
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from dj_rest_auth.serializers import PasswordResetSerializer as BasePasswordResetSerializer, PasswordResetSerializer

from .models import *

if 'allauth' in settings.INSTALLED_APPS:
    from allauth.account import app_settings as allauth_account_settings
    from allauth.account.adapter import get_adapter
    from allauth.account.forms import ResetPasswordForm as DefaultPasswordResetForm
    from allauth.account.forms import default_token_generator
    from allauth.account.utils import (
        filter_users_by_email,
        user_pk_to_url_str,
        user_username,
    )
    from allauth.utils import build_absolute_uri


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
    parent_company_id = serializers.PrimaryKeyRelatedField(
        queryset=Companies.objects.all(),
        source='parent_company',
        write_only=True,
        required=False
    )

    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'email', 'is_staff', 'is_active', 'date_joined',
                  'parent_company', 'parent_company_id')
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

    # Legacy fields for compatibility
    customer_first_name = serializers.CharField(source="customer.first_name", read_only=True)
    customer_last_name = serializers.CharField(source="customer.last_name", read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)

    # Write fields
    customer = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    company = serializers.PrimaryKeyRelatedField(queryset=Companies.objects.all())
    current_hubspot_gate = serializers.PrimaryKeyRelatedField(
        queryset=ExternalAPIOrderIdentifier.objects.all(),
        allow_null=True,
        required=False
    )

    class Meta:
        model = Orders
        fields = ('id', 'name', 'customer_note', 'customer', 'customer_info', 'company', 'company_info',
                  'estimated_completion', 'order_status', 'current_hubspot_gate', 'parts_summary', 'process_stages',
                  'customer_first_name', 'customer_last_name', 'company_name', 'created_at', 'updated_at',
                  'archived', 'archived')
        read_only_fields = ('created_at', 'updated_at', 'archived', 'parts_summary', 'process_stages',
                            'customer_info', 'company_info', 'customer_first_name', 'customer_last_name',
                            'company_name')

    @extend_schema_field(UserSelectSerializer())
    def get_customer_info(self, obj):
        if obj.customer:
            return UserSelectSerializer(obj.customer).data
        return None

    @extend_schema_field(CompanySerializer())
    def get_company_info(self, obj):
        if obj.company:
            return CompanySerializer(obj.company, context=self.context).data
        return None

    @extend_schema_field(serializers.DictField())
    def get_parts_summary(self, obj):
        """Use model method for parts distribution"""
        return {
            'total_parts': obj.parts.count(),
            'step_distribution': obj.get_step_distribution(),
            'completed_parts': obj.parts.filter(part_status=PartsStatus.COMPLETED).count()
        }

    @extend_schema_field(serializers.ListField())
    def get_process_stages(self, obj):
        """Use enhanced model method for detailed stage info"""
        return obj.get_detailed_stage_info()


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
    process_name = serializers.SerializerMethodField(read_only=True)
    order_name = serializers.SerializerMethodField(read_only=True, allow_null=True)
    step_description = serializers.SerializerMethodField(read_only=True)
    work_order_erp_id = serializers.SerializerMethodField(read_only=True, allow_null=True)
    quality_status = serializers.SerializerMethodField(read_only=True)

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
                  'quality_status', 'sampling_rule', 'sampling_ruleset', 'sampling_context')
        read_only_fields = ('created_at', 'updated_at', 'archived', 'requires_sampling', 'sampling_info',
                            'quality_info', 'work_order_info', 'sampling_history', 'order_info', 'part_type_info',
                            'step_info', 'has_error', 'part_type_name', 'process_name', 'order_name',
                            'step_description', 'work_order_erp_id', 'quality_status')

    @extend_schema_field(serializers.DictField())
    def get_sampling_info(self, obj):
        """Use model method for sampling display info"""
        return obj.get_sampling_display_info()

    @extend_schema_field(serializers.DictField())
    def get_quality_info(self, obj):
        """Use model methods for quality status"""
        return {
            'has_errors': obj.has_quality_errors(),
            'latest_status': obj.get_latest_quality_status(),
            'error_count': obj.error_reports.count()
        }

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
            return {
                'id': obj.order.id,
                'name': obj.order.name,
                'status': obj.order.order_status,
                'customer': obj.order.customer.username if obj.order.customer else None
            }
        return None

    @extend_schema_field(serializers.DictField())
    def get_part_type_info(self, obj):
        if obj.part_type:
            return {
                'id': obj.part_type.id,
                'name': obj.part_type.name,
                'version': obj.part_type.version,
                'ID_prefix': obj.part_type.ID_prefix
            }
        return None

    @extend_schema_field(serializers.DictField())
    def get_step_info(self, obj):
        if obj.step:
            return {
                'id': obj.step.id,
                'name': obj.step.name,
                'order': obj.step.order,
                'description': obj.step.description,
                'is_last_step': obj.step.is_last_step,
                'process_name': obj.step.process.name if obj.step.process else None
            }
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
        return {
            'has_errors': obj.has_quality_errors(),
            'latest_status': obj.get_latest_quality_status()
        }


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

    related_order = serializers.PrimaryKeyRelatedField(queryset=Orders.objects.all(), required=False, allow_null=True)

    class Meta:
        model = WorkOrder
        fields = ('id', 'ERP_id', 'workorder_status', 'quantity', 'related_order', 'related_order_info',
                  'related_order_detail', 'expected_completion', 'expected_duration', 'true_completion',
                  'true_duration', 'notes', 'parts_summary', 'created_at', 'updated_at', 'archived')
        read_only_fields = ('created_at', 'updated_at', 'archived', 'related_order_info', 'parts_summary',
                            'related_order_detail')

    @extend_schema_field(serializers.DictField())
    def get_related_order_info(self, obj):
        if obj.related_order:
            return {
                'id': obj.related_order.id,
                'name': obj.related_order.name,
                'status': obj.related_order.order_status,
                'customer': obj.related_order.customer.username if obj.related_order.customer else None
            }
        return None

    @extend_schema_field(OrdersSerializer())
    def get_related_order_detail(self, obj):
        if obj.related_order:
            return OrdersSerializer(obj.related_order, context=self.context).data
        return None

    @extend_schema_field(serializers.DictField())
    def get_parts_summary(self, obj):
        parts = obj.parts.all()
        return {
            'total_parts': parts.count(),
            'completed_parts': parts.filter(part_status=PartsStatus.COMPLETED).count(),
            'in_progress_parts': parts.filter(part_status=PartsStatus.IN_PROGRESS).count(),
            'pending_parts': parts.filter(part_status=PartsStatus.PENDING).count()
        }


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
        read_only_fields = ('upload_date', 'created_at', 'updated_at', 'archived', 'file_url', 'uploaded_by_info',
                            'content_type_info', 'access_info', 'auto_properties')

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
            return {
                'app_label': obj.content_type.app_label,
                'model': obj.content_type.model,
                'name': str(obj.content_type)
            }
        return None

    @extend_schema_field(serializers.DictField())
    def get_access_info(self, obj):
        """Use model methods for access control"""
        request = self.context.get('request')
        if request and request.user:
            return {
                'can_access': obj.user_can_access(request.user),
                'access_level': obj.get_access_level_for_user(request.user)
            }
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
        read_only_fields = ('created_at', 'updated_at', 'archived', 'process_info', 'part_type_info',
                            'resolved_sampling_rules', 'sampling_coverage', 'process_name', 'part_type_name')

    @extend_schema_field(serializers.DictField())
    def get_process_info(self, obj):
        if obj.process:
            return {
                'id': obj.process.id,
                'name': obj.process.name,
                'is_remanufactured': obj.process.is_remanufactured,
                'version': obj.process.version
            }
        return None

    @extend_schema_field(serializers.DictField())
    def get_part_type_info(self, obj):
        if obj.part_type:
            return {
                'id': obj.part_type.id,
                'name': obj.part_type.name,
                'version': obj.part_type.version,
                'ID_prefix': obj.part_type.ID_prefix
            }
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
        fields = ["id", "name", "is_remanufactured", "part_type", "steps", "num_steps"]

    def create(self, validated_data):
        steps_data = validated_data.pop("steps", [])
        process = Processes.objects.create(**validated_data)

        for step_index, step_data in enumerate(steps_data):
            step = Steps.objects.create(
                process=process,
                part_type=process.part_type,
                order=step_index + 1,
                **step_data
            )

        return process

    def update(self, instance, validated_data):
        steps_data = validated_data.pop("steps", [])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Replace all steps and related rulesets
        instance.steps.all().delete()  # Use soft delete from SecureManager

        for step_index, step_data in enumerate(steps_data):
            step = Steps.objects.create(
                process=instance,
                part_type=instance.part_type,
                order=step_index + 1,
                **step_data
            )

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
        fields = ["id", "label", "step_name", "allow_override", "allow_remeasure", "allow_quarantine", "unit",
                  "require_qa_review", "nominal", "upper_tol", "lower_tol", "required", "type", "step"]
        read_only_fields = ["id", "step"]

    @extend_schema_field(serializers.CharField())
    def get_step_name(self, obj) -> str | None:
        return obj.step.name if obj.step else None


class QualityReportsSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Quality reports serializer"""
    measurements = MeasurementDefinitionSerializer(many=True, write_only=True)

    class Meta:
        model = QualityReports
        fields = ["id", "step", "part", "machine", "operator", "sampling_rule", "sampling_method", "status",
                  "description", "file", "created_at", "errors", "measurements", "sampling_audit_log"]

    def create(self, validated_data):
        measurements_data = validated_data.pop("measurements", [])
        report = super().create(validated_data)

        for m in measurements_data:
            MeasurementResult.objects.create(
                report=report,
                step=report.step,
                operator=self.context["request"].user,
                **m
            )

        return report


class QualityReportFormSerializer(serializers.ModelSerializer):
    """Legacy quality report form serializer"""
    measurements = MeasurementDefinitionSerializer(many=True, write_only=True)

    class Meta:
        model = QualityReports
        fields = ["id", "step", "part", "machine", "operator", "sampling_rule", "sampling_method", "status",
                  "description", "file", "created_at", "errors", "measurements", "sampling_audit_log"]

    def create(self, validated_data):
        measurements_data = validated_data.pop("measurements", [])
        report = super().create(validated_data)

        for m in measurements_data:
            MeasurementResult.objects.create(
                report=report,
                step=report.step,
                operator=self.context["request"].user,
                **m
            )

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
        fields = ('id', 'rule_type', 'rule_type_display', 'value', 'order', 'algorithm_description', 'last_validated',
                  'ruleset', 'ruleset_info', 'created_by', 'created_at', 'modified_by', 'updated_at', 'archived',
                  'ruletype_name', 'ruleset_name')
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
                  'created_by', 'created_at', 'modified_by', 'updated_at', 'archived', 'part_type_name',
                  'process_name')
        read_only_fields = ('created_at', 'updated_at', 'archived', 'rules', 'part_type_info', 'process_info',
                            'step_info', 'part_type_name', 'process_name')

    @extend_schema_field(serializers.ListField())
    def get_rules(self, obj):
        # Use model method to avoid circular import
        return obj.get_rules_summary() if hasattr(obj, 'get_rules_summary') else list(
            obj.rules.all().values('id', 'rule_type', 'value', 'order', 'algorithm_description', 'last_validated')
        )

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

        return step.apply_sampling_rules_update(
            rules_data=self.validated_data['rules'],
            fallback_rules_data=self.validated_data.get('fallback_rules', []),
            fallback_threshold=self.validated_data.get('fallback_threshold'),
            fallback_duration=self.validated_data.get('fallback_duration'),
            user=user
        )


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

        return step.apply_sampling_rules_update(
            rules_data=rules,
            fallback_rules_data=fallback_data,
            fallback_threshold=threshold,
            fallback_duration=duration,
            user=user
        )


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
        work_order, created, warnings = WorkOrder.create_from_csv_row(
            self.validated_data,
            user=user
        )
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
            work_order, created, warnings = WorkOrder.create_from_csv_row(
                validated_data,
                user=self.context.get('request', {}).get('user')
            )
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
        fields = ('id', 'object_pk', 'object_repr', 'content_type', 'content_type_name', 'actor', 'actor_info',
                  'remote_addr', 'timestamp', 'action', 'changes')
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
        read_only_fields = ('created_at', 'archived', 'effectiveness', 'is_compliant', 'ruleset_info',
                            'work_order_info', 'ruleset_name', 'work_order_erp', 'sampling_effectiveness')

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
        fields = ["id", "part", "part_erp_id", "rule", "rule_type", "hash_input", "hash_output",
                  "sampling_decision", "timestamp", "ruleset_type", "work_order_erp"]
        read_only_fields = ["id", "timestamp"]


class SamplingTriggerStateSerializer(serializers.ModelSerializer):
    """Sampling trigger state serializer"""
    ruleset_name = serializers.CharField(source="ruleset.name", read_only=True)
    work_order_erp = serializers.CharField(source="work_order.ERP_id", read_only=True)
    step_name = serializers.CharField(source="step.name", read_only=True)
    triggered_by_status = serializers.CharField(source="triggered_by.status", read_only=True)

    class Meta:
        model = SamplingTriggerState
        fields = ["id", "ruleset", "ruleset_name", "work_order", "work_order_erp", "step", "step_name",
                  "active", "triggered_by", "triggered_by_status", "triggered_at", "success_count",
                  "fail_count", "parts_inspected"]
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
            template_names = [
                'account/email/password_reset_key_message.html',
                'account/email/password_reset_key_message.txt',
            ]
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

            context = {
                'current_site': current_site,
                'user': user,
                'site_name': "AMBAC",
                'password_reset_url': custom_url,  # This is the key!
                'request': request,
                'token': temp_key,
                'uid': uid,
            }
            if (
                    allauth_account_settings.AUTHENTICATION_METHOD != allauth_account_settings.AuthenticationMethod.EMAIL
            ):
                context['username'] = user_username(user)

            get_adapter(request).send_mail(
                'account/email/password_reset_key', email, context
            )

        return self.cleaned_data['email']


class PasswordResetSerializer(BasePasswordResetSerializer):
    @property
    def password_reset_form_class(self):
        """Force use of our custom form instead of the default AllAuth form"""
        return CustomAllAuthPasswordResetForm

class UserSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Enhanced user serializer with company and permission info"""
    full_name = serializers.SerializerMethodField()
    parent_company = CompanySerializer(read_only=True, allow_null=True)
    parent_company_id = serializers.PrimaryKeyRelatedField(
        queryset=Companies.objects.all(),
        source='parent_company',
        write_only=True,
        required=False,
        allow_null=True
    )
    
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'email', 'full_name', 'is_staff', 'is_active', 
                  'date_joined', 'parent_company', 'parent_company_id')
        read_only_fields = ('date_joined', 'full_name')
        extra_kwargs = {
            'password': {'write_only': True}
        }

    @extend_schema_field(serializers.CharField())
    def get_full_name(self, obj):
        """Get formatted full name or fallback to username"""
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username

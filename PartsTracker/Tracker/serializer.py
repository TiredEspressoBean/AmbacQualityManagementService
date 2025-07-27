from datetime import datetime
from mimetypes import guess_type

from auditlog.models import LogEntry
from django.db import transaction
from django.db.models import Max
from django.utils.dateparse import parse_date
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import *


class EmployeeSelectSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'email')


class StageSerializer(serializers.Serializer):
    name = serializers.CharField()
    timestamp = serializers.DateTimeField(allow_null=True)
    is_completed = serializers.BooleanField()
    is_current = serializers.BooleanField()


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Companies
        fields = '__all__'


class CustomerSerializer(serializers.ModelSerializer):
    parent_company = CompanySerializer()

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_staff', 'parent_company', 'id']


class TrackerPageOrderSerializer(serializers.ModelSerializer):
    order_status = serializers.ChoiceField(choices=OrdersStatus.choices)
    stages = serializers.SerializerMethodField()
    customer = CustomerSerializer()
    company = CompanySerializer()

    class Meta:
        model = Orders
        exclude = ['hubspot_deal_id', 'last_synced_hubspot_stage', 'current_hubspot_gate']

    @extend_schema_field(StageSerializer(many=True))
    def get_stages(self, order):
        # If there are no parts, return an empty stage list
        if not order.parts.exists():
            return []

        # Assuming all parts in the order have the same PartType → Process
        first_part = Parts.objects.filter(order_id=order.id).first()
        process = first_part.step.process

        # If no process defined, return empty
        if not process:
            return []

        # Now serialize steps
        process_steps = Steps.objects.filter(process=process)  # or whatever field orders the steps

        # Optional: you can cross-reference with part state to fill in timestamp/completion
        return [{"name": step.name, "timestamp": None,  # Or computed if you have tracking data
                 "is_completed": True if step.order <= first_part.step.order else False,
                 # Could be dynamically calculated
                 "is_current": True if first_part.order == step else False  # Logic to determine current step
                 } for step in process_steps]


class CustomerPartsSerializer(serializers.ModelSerializer):
    Orders = TrackerPageOrderSerializer

    class Meta:
        model = Parts
        exclude = ['ERP_id', 'work_order']
        depth = 2


class StepSerializer(serializers.ModelSerializer):
    process_name = serializers.CharField(source="process.name", read_only=True)
    part_type_name = serializers.CharField(source="process.part_type.name", read_only=True)

    class Meta:
        model = Steps
        fields = ["name", "id", "order", "description", "is_last_step", "process", "part_type", "process_name",
                  "part_type_name", ]


class PartTypeSerializer(serializers.ModelSerializer):
    previous_version = serializers.PrimaryKeyRelatedField(read_only=True, allow_null=True)
    previous_version_name = serializers.SerializerMethodField(allow_null=True)

    class Meta:
        model = PartTypes
        fields = "__all__"

    @extend_schema_field(serializers.CharField())
    def get_previous_version_name(self, obj):
        return obj.previous_version.name if obj.previous_version else None


class PartsSerializer(serializers.ModelSerializer):
    step = serializers.PrimaryKeyRelatedField(queryset=Steps.objects.all())
    part_type = serializers.PrimaryKeyRelatedField(queryset=PartTypes.objects.all())
    has_error = serializers.SerializerMethodField(read_only=True)
    part_type_name = serializers.SerializerMethodField(read_only=True)
    order_name = serializers.SerializerMethodField(read_only=True, allow_null=True)
    step_description = serializers.SerializerMethodField(read_only=True)
    work_order = serializers.PrimaryKeyRelatedField(queryset=WorkOrder.objects.all(), required=False, allow_null=True)
    requires_sampling = serializers.BooleanField(read_only=True)
    work_order_erp_id = serializers.SerializerMethodField(read_only=True, allow_null=True)

    class Meta:
        model = Parts
        fields = ["id", "part_status", "order", "part_type", 'created_at', 'order_name', "part_type_name", "step",
                  "step_description", "requires_sampling", "ERP_id", "archived", "has_error", "work_order",
                  "sampling_rule", "sampling_ruleset", "work_order_erp_id"]

    @extend_schema_field(serializers.BooleanField())
    def get_has_error(self, obj):
        return QualityReports.objects.filter(part=obj, errors=True).exists()

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


class ExternalAPIOrderIdentifierSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalAPIOrderIdentifier
        fields = "__all__"


class OrdersSerializer(serializers.ModelSerializer):
    order_status = serializers.ChoiceField(choices=OrdersStatus.choices)
    customer = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    company = serializers.PrimaryKeyRelatedField(queryset=Companies.objects.all())
    current_hubspot_gate = serializers.PrimaryKeyRelatedField(queryset=ExternalAPIOrderIdentifier.objects.all(),
                                                              allow_null=True, required=False)

    customer_first_name = serializers.CharField(source="customer.first_name", read_only=True)
    customer_last_name = serializers.CharField(source="customer.last_name", read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = Orders
        exclude = ['hubspot_deal_id', 'created_at', 'updated_at']


class IncrementStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parts
        fields = []  # no input fields required

    def update(self, instance, validated_data):
        result = instance.increment_step()
        return instance


class EquipmentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipmentType
        fields = "__all__"


class EquipmentSelectSerializer(serializers.ModelSerializer):
    equipment_type = EquipmentTypeSerializer()

    class Meta:
        model = Equipments
        fields = "__all__"


class WorkOrderSerializer(serializers.ModelSerializer):
    related_order = serializers.PrimaryKeyRelatedField(queryset=Orders.objects.all(), allow_null=True, required=False)
    related_order_detail = OrdersSerializer(source="related_order", read_only=True, required=False, allow_null=True)

    class Meta:
        model = WorkOrder
        fields = "__all__"


class BulkAddPartsSerializer(serializers.Serializer):
    part_type = serializers.PrimaryKeyRelatedField(queryset=PartTypes.objects.all(), source="part_type_id")
    step = serializers.PrimaryKeyRelatedField(queryset=Steps.objects.all(), source="step_id")
    # work_order = serializers.PrimaryKeyRelatedField(queryset=WorkOrder.objects.all(), required=False, allow_null=True,
    #                                                 source="work_order_id")
    quantity = serializers.IntegerField(min_value=1)
    part_status = serializers.ChoiceField(choices=PartsStatus.choices)
    process_id = serializers.IntegerField()
    ERP_id = serializers.CharField()


class BulkRemovePartsSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)


class ProcessesSerializer(serializers.ModelSerializer):
    part_type_name = serializers.CharField(source="part_type.name", read_only=True)
    steps = StepSerializer(many=True)

    class Meta:
        model = Processes
        fields = "__all__"


class EquipmentSerializer(serializers.ModelSerializer):
    equipment_type_name = serializers.CharField(source="equipment_type.name", read_only=True)

    class Meta:
        model = Equipments
        fields = ["id", "name", "equipment_type", "equipment_type_name"]


class ErrorTypeSerializer(serializers.ModelSerializer):
    part_type_name = serializers.CharField(source="part_type.name", read_only=True)

    class Meta:
        model = QualityErrorsList
        fields = ["id", "error_name", "error_example", "part_type", "part_type_name"]


class DocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    uploaded_by_name = serializers.SerializerMethodField()
    content_type_model = serializers.SerializerMethodField()

    class Meta:
        model = Documents
        fields = ["id", "is_image", "file_name", "file", "file_url", "upload_date", "uploaded_by", "uploaded_by_name",
            "content_type", "content_type_model", "object_id", "version", "classification"]
        read_only_fields = ["upload_date", "uploaded_by_name", "file_url", "content_type_model", ]

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

    def validate_file(self, file):
        if not file.name.lower().endswith((".pdf", ".png", ".jpg", ".jpeg", ".docx")):
            raise serializers.ValidationError("Unsupported file type.")
        return file

    def create(self, validated_data):
        request = self.context.get("request")
        file = validated_data.get("file")

        # Auto-fill file_name from the uploaded file if not explicitly provided
        if "file_name" not in validated_data and file:
            validated_data["file_name"] = file.name

        # Auto-assign uploader
        if request and request.user.is_authenticated:
            validated_data["uploaded_by"] = request.user

        # Auto-set is_image if not provided
        if "is_image" not in validated_data and file:
            mime_type, _ = guess_type(file.name)
            validated_data["is_image"] = mime_type and mime_type.startswith("image/")

        # Auto-increment version if not specified
        ct = validated_data.get("content_type")
        obj_id = validated_data.get("object_id")
        if ct and obj_id and "version" not in validated_data:
            existing = Documents.objects.filter(content_type=ct, object_id=obj_id)
            max_version = existing.aggregate(Max("version"))["version__max"] or 0
            validated_data["version"] = max_version + 1

        return super().create(validated_data)


class SamplingRuleSerializer(serializers.ModelSerializer):
    ruletype_name = serializers.SerializerMethodField()
    ruleset_name = serializers.CharField(source="ruleset.name", read_only=True)

    @extend_schema_field(serializers.CharField())
    def get_ruletype_name(self, obj) -> str:
        return obj.get_rule_type_display()

    class Meta:
        model = SamplingRule
        fields = ["id", "ruleset", "rule_type", "value", "order", "created_by", "created_at", "modified_by",
                  "modified_at", "ruletype_name", "ruleset_name"]


class SamplingRuleSetSerializer(serializers.ModelSerializer):
    rules = SamplingRuleSerializer(many=True, read_only=True)

    # Add related object names
    part_type_name = serializers.CharField(source="part_type.name", read_only=True)
    process_name = serializers.CharField(source="process.name", read_only=True)

    class Meta:
        model = SamplingRuleSet
        fields = "__all__"  # or explicitly list all + these two fields
        read_only_fields = ("part_type_name", "process_name")


class ProcessWithStepsSerializer(serializers.ModelSerializer):
    steps = StepSerializer(many=True)

    class Meta:
        model = Processes
        fields = ["id", "name", "is_remanufactured", "part_type", "steps", "num_steps"]

    def create(self, validated_data):
        steps_data = validated_data.pop("steps", [])
        process = Processes.objects.create(**validated_data)

        for step_index, step_data in enumerate(steps_data):
            step = Steps.objects.create(process=process, part_type=process.part_type, order=step_index + 1,
                                        **step_data, )

        return process

    def update(self, instance, validated_data):
        steps_data = validated_data.pop("steps", [])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Replace all steps and related rulesets
        instance.steps.all().delete()

        for step_index, step_data in enumerate(steps_data):
            step = Steps.objects.create(process=instance, part_type=instance.part_type, order=step_index + 1,
                                        **step_data, )

        return instance


class MeasurementDefinitionSerializer(serializers.ModelSerializer):
    step_name = serializers.SerializerMethodField()

    class Meta:
        model = MeasurementDefinition
        fields = ["id", "label", "step_name", "allow_override", "allow_remeasure", "allow_quarantine", "unit",
                  "require_qa_review", "nominal", "upper_tol", "lower_tol", "required", "type", "step"]
        read_only_fields = ["id", "step"]

    @extend_schema_field(serializers.CharField())
    def get_step_name(self, obj) -> str | None:
        return obj.step.name if obj.step else None


class QualityReportFormSerializer(serializers.ModelSerializer):
    measurements = MeasurementDefinitionSerializer(many=True, write_only=True)

    class Meta:
        model = QualityReports
        fields = ["id", "step", "part", "machine", "operator", "sampling_rule", "sampling_method", "status",
                  "description", "file", "created_at", "errors", "measurements"]

    def create(self, validated_data):
        measurements_data = validated_data.pop("measurements", [])
        report = super().create(validated_data)

        for m in measurements_data:
            MeasurementResult.objects.create(report=report, step=report.step, operator=self.context["request"].user,
                                             **m)
        return report


class ContentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentType
        fields = ['id', 'app_label', 'model']


class ResolvedSamplingRuleSetSerializer(serializers.ModelSerializer):
    rules = SamplingRuleSerializer(many=True, read_only=True)

    class Meta:
        model = SamplingRuleSet
        fields = ["id", "name", "rules", "fallback_threshold", "fallback_duration"]


class StepWithResolvedRulesSerializer(serializers.ModelSerializer):
    active_ruleset = serializers.SerializerMethodField()
    fallback_ruleset = serializers.SerializerMethodField()
    process_name = serializers.CharField(source="process.name", read_only=True)
    part_type_name = serializers.CharField(source="part_type.name", read_only=True)

    class Meta:
        model = Steps
        fields = ["id", "name", "description", "expected_duration", "order", "part_type", "part_type_name", "process",
                  "process_name", "active_ruleset", "fallback_ruleset", ]

    @extend_schema_field(ResolvedSamplingRuleSetSerializer)
    def get_active_ruleset(self, step):
        # Get the highest-versioned non-fallback ruleset
        ruleset = step.sampling_ruleset.filter(is_fallback=False).order_by("-version").first()
        if ruleset:
            return ResolvedSamplingRuleSetSerializer(ruleset).data
        return None

    @extend_schema_field(ResolvedSamplingRuleSetSerializer)
    def get_fallback_ruleset(self, step):
        # Get the fallback_ruleset from the highest-versioned main ruleset
        main_ruleset = step.sampling_ruleset.filter(is_fallback=False).order_by("-version").first()
        if main_ruleset and main_ruleset.fallback_ruleset:
            return ResolvedSamplingRuleSetSerializer(main_ruleset.fallback_ruleset).data
        return None


class SamplingRuleWriteSerializer(serializers.Serializer):
    rule_type = serializers.ChoiceField(choices=SamplingRule.RuleType.choices)
    value = serializers.IntegerField(allow_null=True, required=False)
    order = serializers.IntegerField()
    is_fallback = serializers.BooleanField(required=False)


class StepSamplingRulesWriteSerializer(serializers.Serializer):
    rules = SamplingRuleWriteSerializer(many=True)
    fallback_rules = SamplingRuleWriteSerializer(many=True, required=False)
    fallback_threshold = serializers.IntegerField(required=False)
    fallback_duration = serializers.IntegerField(required=False)  # matches model field type

    def save(self, step: Steps):
        return self._apply_to_step(step)

    def _apply_to_step(self, step: Steps):
        user = self.context["request"].user

        rules = self.validated_data["rules"]
        fallback_data = self.validated_data.get("fallback_rules", [])
        threshold = self.validated_data.get("fallback_threshold")
        duration = self.validated_data.get("fallback_duration")

        # Atomically compute versions and create rule sets
        with transaction.atomic():
            # Archive existing rulesets (both main and fallback)
            step.sampling_ruleset.filter(active=True).update(active=False, archived=True)

            # Compute next version numbers
            main_version = (SamplingRuleSet.objects.filter(part_type=step.part_type, process=step.process, step=step,
                                                           is_fallback=False, ).aggregate(models.Max("version"))[
                                "version__max"] or 0) + 1

            fallback_version = (SamplingRuleSet.objects.filter(part_type=step.part_type, process=step.process,
                                                               step=step, is_fallback=True, ).aggregate(
                models.Max("version"))["version__max"] or 0) + 1

            # Create fallback first (so we can pass reference to main)
            fallback_ruleset = None
            if fallback_data:
                fallback_ruleset = SamplingRuleSet.create_with_rules(part_type=step.part_type, process=step.process,
                                                                     step=step,
                                                                     name=f"Fallback for Step {step.id} v{fallback_version}",
                                                                     version=fallback_version, rules=fallback_data,
                                                                     fallback_ruleset=None, fallback_threshold=None,
                                                                     fallback_duration=None, created_by=user,
                                                                     origin="auto-fallback", active=True,
                                                                     is_fallback=True, )

            # Create main ruleset
            new_ruleset = SamplingRuleSet.create_with_rules(part_type=step.part_type, process=step.process, step=step,
                                                            name=f"Rules for Step {step.id} v{main_version}",
                                                            version=main_version, rules=rules,
                                                            fallback_ruleset=fallback_ruleset,
                                                            fallback_threshold=threshold, fallback_duration=duration,
                                                            created_by=user, origin="manual-update", active=True,
                                                            is_fallback=False, supersedes=None, )

        return new_ruleset


class StepSamplingRulesResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    ruleset_id = serializers.IntegerField()
    step_id = serializers.IntegerField()


DATE_FORMATS = ["%b %d", "%B %d", "%Y-%m-%d"]

from datetime import datetime
from django.utils.dateparse import parse_date
from rest_framework import serializers
from .models import WorkOrder, Orders, Parts, PartTypes, WorkOrderStatus, PartsStatus

DATE_FORMATS = ["%b %d", "%B %d", "%Y-%m-%d"]  # e.g., "Jan 25", "January 25", "2024-01-25"

class WorkOrderUploadSerializer(serializers.Serializer):
    ERP_id = serializers.CharField()
    workorder_status = serializers.ChoiceField(choices=WorkOrderStatus.choices, required=False)
    related_order_erp_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    quantity = serializers.IntegerField()
    expected_completion = serializers.CharField(required=False, allow_blank=True)
    expected_duration = serializers.DurationField(required=False)
    true_duration = serializers.DurationField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    # Optional: allow passing `part_type_erp_id` through unvalidated if needed for lookup
    part_type_erp_id = serializers.CharField(required=False)

    def _parse_date_with_fallback(self, value):
        parsed = parse_date(value)
        if parsed:
            return parsed

        for fmt in DATE_FORMATS:
            try:
                dt = datetime.strptime(value.strip(), fmt)
                today = datetime.today()
                year = today.year
                if dt.month < today.month or (dt.month == today.month and dt.day < today.day):
                    year += 1
                return dt.replace(year=year).date()
            except Exception:
                continue

        raise serializers.ValidationError(f"Invalid date format: {value}")

    def validate_expected_completion(self, value):
        if not value:
            return None
        return self._parse_date_with_fallback(value)

    def validate_related_order_erp_id(self, value):
        if not value:
            return None
        try:
            return Orders.objects.get(ERP_id=value)
        except Orders.DoesNotExist:
            return None

    def create_or_update(self, validated_data):
        erp_id = validated_data.get("ERP_id")
        quantity = validated_data.pop("quantity", 0)
        related_order = validated_data.pop("related_order_erp_id", None)

        part_type_erp_id = validated_data.pop("part_type_erp_id", None) or validated_data.pop("PartType", None)
        part_type = None
        if part_type_erp_id:
            try:
                part_type = PartTypes.objects.get(ERP_id=part_type_erp_id)
            except PartTypes.DoesNotExist:
                pass

        existing_wo = WorkOrder.objects.filter(ERP_id=erp_id).first()

        if "workorder_status" not in validated_data or not validated_data["workorder_status"]:
            validated_data["workorder_status"] = (
                existing_wo.workorder_status if existing_wo else WorkOrderStatus.PENDING
            )

        # Explicitly drop unsupported fields like true_completion
        validated_data.pop("true_completion", None)

        wo, created = WorkOrder.objects.update_or_create(
            ERP_id=erp_id,
            defaults={**validated_data, "related_order": related_order}
        )

        return wo


class LogEntrySerializer(serializers.ModelSerializer):
    content_type_name = serializers.CharField(source="content_type.model", read_only=True)

    class Meta:
        model = LogEntry
        fields = ["id", "object_pk", "object_repr", "content_type_name", "actor", "remote_addr", "timestamp", "action",
            "changes", ]

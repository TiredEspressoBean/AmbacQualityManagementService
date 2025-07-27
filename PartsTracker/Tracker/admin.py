from django.contrib import admin

from .models import Companies, User, Documents, PartTypes, Processes, MeasurementDefinition, Steps, Orders, WorkOrder, SamplingRuleSet, SamplingRule, Parts, EquipmentType, Equipments, QualityErrorsList, QualityReports, MeasurementResult, EquipmentUsage, ExternalAPIOrderIdentifier, ArchiveReason, StepTransitionLog, SamplingTriggerState, QaApproval, MeasurementDisposition


@admin.register(Companies)
class CompaniesAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description', 'hubspot_api_id')
    search_fields = ('name',)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'password',
        'last_login',
        'is_superuser',
        'username',
        'first_name',
        'last_name',
        'email',
        'is_staff',
        'is_active',
        'date_joined',
        'parent_company',
    )
    list_filter = (
        'last_login',
        'is_superuser',
        'is_staff',
        'is_active',
        'date_joined',
        'parent_company',
    )
    raw_id_fields = ('groups', 'user_permissions')


@admin.register(Documents)
class DocumentsAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'uploaded_by',
        'classification',
        'AI_readable',
        'is_image',
        'file_name',
        'file',
        'upload_date',
        'content_type',
        'object_id',
        'version',
    )
    list_filter = (
        'uploaded_by',
        'AI_readable',
        'is_image',
        'upload_date',
        'content_type',
    )


@admin.register(PartTypes)
class PartTypesAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'created_at',
        'updated_at',
        'name',
        'ID_prefix',
        'version',
        'previous_version',
    )
    list_filter = ('created_at', 'updated_at', 'previous_version')
    search_fields = ('name',)
    date_hierarchy = 'created_at'


@admin.register(Processes)
class ProcessesAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'created_at',
        'updated_at',
        'name',
        'is_remanufactured',
        'num_steps',
        'part_type',
        'version',
        'previous_version',
    )
    list_filter = (
        'created_at',
        'updated_at',
        'is_remanufactured',
        'part_type',
        'previous_version',
    )
    search_fields = ('name',)
    date_hierarchy = 'created_at'


@admin.register(MeasurementDefinition)
class MeasurementDefinitionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'step',
        'label',
        'type',
        'allow_quarantine',
        'allow_remeasure',
        'allow_override',
        'require_qa_review',
        'unit',
        'nominal',
        'upper_tol',
        'lower_tol',
        'required',
    )
    list_filter = (
        'step',
        'allow_quarantine',
        'allow_remeasure',
        'allow_override',
        'require_qa_review',
        'required',
    )


@admin.register(Steps)
class StepsAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'pass_threshold',
        'order',
        'expected_duration',
        'process',
        'description',
        'part_type',
        'is_last_step',
        'block_on_quarantine',
        'requires_qa_signoff',
    )
    list_filter = (
        'is_last_step',
        'block_on_quarantine',
        'requires_qa_signoff',
    )
    raw_id_fields = ('required_measurements',)
    search_fields = ('name',)


@admin.register(Orders)
class OrdersAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'created_at',
        'updated_at',
        'name',
        'customer_note',
        'customer',
        'company',
        'estimated_completion',
        'original_completion_date',
        'order_status',
        'current_hubspot_gate',
        'archived',
        'hubspot_deal_id',
        'last_synced_hubspot_stage',
    )
    list_filter = (
        'created_at',
        'updated_at',
        'customer',
        'company',
        'estimated_completion',
        'original_completion_date',
        'current_hubspot_gate',
        'archived',
    )
    search_fields = ('name',)
    date_hierarchy = 'created_at'


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'workorder_status',
        'quantity',
        'ERP_id',
        'created_at',
        'updated_at',
        'related_order',
        'expected_completion',
        'expected_duration',
        'true_completion',
        'true_duration',
        'notes',
    )
    list_filter = (
        'created_at',
        'updated_at',
        'related_order',
        'expected_completion',
        'true_completion',
    )
    date_hierarchy = 'created_at'


@admin.register(SamplingRuleSet)
class SamplingRuleSetAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'part_type',
        'process',
        'step',
        'name',
        'origin',
        'active',
        'version',
        'supersedes',
        'fallback_ruleset',
        'fallback_threshold',
        'fallback_duration',
        'created_by',
        'created_at',
        'modified_by',
        'modified_at',
    )
    list_filter = (
        'part_type',
        'process',
        'step',
        'active',
        'supersedes',
        'fallback_ruleset',
        'created_by',
        'created_at',
        'modified_by',
        'modified_at',
    )
    search_fields = ('name',)
    date_hierarchy = 'created_at'


@admin.register(SamplingRule)
class SamplingRuleAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'ruleset',
        'rule_type',
        'value',
        'order',
        'created_by',
        'created_at',
        'modified_by',
        'modified_at',
    )
    list_filter = ('created_at', 'modified_at')
    date_hierarchy = 'created_at'


@admin.register(Parts)
class PartsAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'created_at',
        'updated_at',
        'ERP_id',
        'part_type',
        'step',
        'order',
        'part_status',
        'archived',
        'work_order',
        'requires_sampling',
        'sampling_rule',
        'sampling_ruleset',
    )
    list_filter = (
        'created_at',
        'updated_at',
        'part_type',
        'step',
        'order',
        'archived',
        'work_order',
        'requires_sampling',
        'sampling_rule',
        'sampling_ruleset',
    )
    date_hierarchy = 'created_at'


@admin.register(EquipmentType)
class EquipmentTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(Equipments)
class EquipmentsAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'equipment_type')
    list_filter = ('equipment_type',)
    search_fields = ('name',)


@admin.register(QualityErrorsList)
class QualityErrorsListAdmin(admin.ModelAdmin):
    list_display = ('id', 'error_name', 'error_example', 'part_type')
    list_filter = ('part_type',)


@admin.register(QualityReports)
class QualityReportsAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'step',
        'part',
        'machine',
        'sampling_rule',
        'sampling_method',
        'status',
        'description',
        'file',
        'created_at',
    )
    list_filter = (
        'step',
        'part',
        'machine',
        'sampling_rule',
        'file',
        'created_at',
    )
    raw_id_fields = ('operator', 'errors')
    date_hierarchy = 'created_at'


@admin.register(MeasurementResult)
class MeasurementResultAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'report',
        'definition',
        'value_numeric',
        'value_pass_fail',
        'is_within_spec',
        'created_by',
        'created_at',
    )
    list_filter = (
        'report',
        'definition',
        'is_within_spec',
        'created_by',
        'created_at',
    )
    date_hierarchy = 'created_at'


@admin.register(EquipmentUsage)
class EquipmentUsageAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'equipment',
        'step',
        'part',
        'error_report',
        'used_at',
        'operator',
        'notes',
    )
    list_filter = (
        'equipment',
        'step',
        'part',
        'error_report',
        'used_at',
        'operator',
    )


@admin.register(ExternalAPIOrderIdentifier)
class ExternalAPIOrderIdentifierAdmin(admin.ModelAdmin):
    list_display = ('id', 'stage_name', 'API_id')


@admin.register(ArchiveReason)
class ArchiveReasonAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'reason',
        'notes',
        'content_type',
        'object_id',
        'archived_at',
        'user',
    )
    list_filter = ('content_type', 'archived_at', 'user')


@admin.register(StepTransitionLog)
class StepTransitionLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'step', 'part', 'operator', 'timestamp')
    list_filter = ('timestamp',)


@admin.register(SamplingTriggerState)
class SamplingTriggerStateAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'ruleset',
        'work_order',
        'step',
        'active',
        'triggered_by',
        'triggered_at',
        'success_count',
        'fail_count',
    )
    list_filter = (
        'ruleset',
        'work_order',
        'step',
        'active',
        'triggered_by',
        'triggered_at',
    )
    raw_id_fields = ('parts_inspected',)


@admin.register(QaApproval)
class QaApprovalAdmin(admin.ModelAdmin):
    list_display = ('id', 'step', 'work_order', 'qa_staff')
    list_filter = ('step', 'work_order', 'qa_staff')


@admin.register(MeasurementDisposition)
class MeasurementDispositionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'measurement',
        'disposition_type',
        'resolved_by',
        'notes',
        'resolved_at',
    )
    list_filter = ('measurement', 'resolved_by', 'resolved_at')
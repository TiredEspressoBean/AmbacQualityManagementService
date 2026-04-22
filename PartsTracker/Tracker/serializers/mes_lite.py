# serializers/mes_lite.py - Manufacturing, Orders, Parts & Processes
from django.db import models
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from Tracker.serializers.fields import TenantScopedPrimaryKeyRelatedField

from Tracker.models import (
    # MES Lite models
    Orders, OrdersStatus, Parts, PartsStatus, WorkOrder, WorkOrderStatus,
    Steps, PartTypes, Processes, StepExecution, ProcessStep, StepEdge, EdgeType,
    # MES Standard models
    EquipmentType, Equipments, TimeEntry, MaterialUsage,
    # QMS models
    QualityReports, MeasurementResult, QuarantineDisposition, EquipmentUsage,
    # Core models
    ExternalAPIOrderIdentifier, User, Companies, Documents,
    # Milestone models
    Milestone, MilestoneTemplate,
)

from .core import SecureModelMixin, BulkOperationsMixin, UserSelectSerializer, CompanySerializer


# ===== STAGE SERIALIZERS =====

class StageSerializer(serializers.Serializer):
    """Serializer for process stages"""
    name = serializers.CharField()
    timestamp = serializers.DateTimeField(allow_null=True)
    is_completed = serializers.BooleanField()
    is_current = serializers.BooleanField()


# ===== ORDERS SERIALIZERS =====

class OrdersSerializer(serializers.ModelSerializer, SecureModelMixin, BulkOperationsMixin):
    """Enhanced orders serializer with user filtering and features"""
    order_status = serializers.ChoiceField(choices=OrdersStatus.choices)

    # Display fields
    customer_info = serializers.SerializerMethodField()
    company_info = serializers.SerializerMethodField()
    parts_summary = serializers.SerializerMethodField()
    process_stages = serializers.SerializerMethodField()
    gate_info = serializers.SerializerMethodField()
    latest_note = serializers.SerializerMethodField()
    notes_timeline = serializers.SerializerMethodField()

    # Legacy fields for compatibility - using SerializerMethodField to handle null relations safely
    customer_first_name = serializers.SerializerMethodField()
    customer_last_name = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()

    # Write fields
    customer = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), allow_null=True, required=False)
    company = TenantScopedPrimaryKeyRelatedField(queryset=Companies.unscoped.all(), allow_null=True, required=False)
    # TODO: Remove current_hubspot_gate after Phase 5 cleanup (replaced by current_milestone)
    current_hubspot_gate = TenantScopedPrimaryKeyRelatedField(queryset=ExternalAPIOrderIdentifier.unscoped.all(),
                                                              allow_null=True, required=False)
    current_milestone = TenantScopedPrimaryKeyRelatedField(
        queryset=Milestone.unscoped.all(), allow_null=True, required=False
    )

    class Meta:
        model = Orders
        fields = (
        'id', 'order_number', 'name', 'customer_note', 'latest_note', 'notes_timeline', 'customer', 'customer_info', 'company', 'company_info',
        'estimated_completion', 'original_completion_date', 'order_status',
        'current_hubspot_gate',  # TODO: Remove after Phase 5 cleanup
        'current_milestone', 'parts_summary',
        'process_stages', 'gate_info', 'customer_first_name', 'customer_last_name', 'company_name', 'created_at', 'updated_at', 'archived')
        read_only_fields = (
            'order_number', 'created_at', 'updated_at', 'parts_summary', 'process_stages', 'gate_info', 'customer_info', 'company_info',
            'customer_first_name', 'customer_last_name', 'company_name', 'original_completion_date', 'latest_note', 'notes_timeline')

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_customer_info(self, obj):
        if obj.customer:
            return UserSelectSerializer(obj.customer).data
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
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

    @extend_schema_field(serializers.DictField(allow_null=True))
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
        """Get milestone/gate progress information. Reads from current_milestone, falls back to legacy HubSpot."""
        return obj.get_gate_info()

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_latest_note(self, obj):
        """Get the most recent note"""
        return obj.get_latest_note()

    @extend_schema_field(serializers.ListField())
    def get_notes_timeline(self, obj):
        """Get all notes (staff sees all, including internal)"""
        return obj.get_notes(customer_view=False)


class TrackerPageOrderSerializer(serializers.ModelSerializer):
    """Legacy tracker page order serializer"""
    order_status = serializers.ChoiceField(choices=OrdersStatus.choices)
    stages = serializers.SerializerMethodField()
    customer = serializers.SerializerMethodField()
    company = CompanySerializer(read_only=True, allow_null=True)

    class Meta:
        model = Orders
        # TODO: Remove hubspot fields from exclude after Phase 5 cleanup (fields will be dropped from model)
        exclude = ['hubspot_deal_id', 'last_synced_hubspot_stage', 'current_hubspot_gate']

    @extend_schema_field(serializers.ListField())
    def get_stages(self, order):
        """Use the model method for process stages"""
        return order.get_process_stages()

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_customer(self, obj):
        """Get customer info"""
        if obj.customer:
            return UserSelectSerializer(obj.customer).data
        return None


class CustomerOrderSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for customer-facing order tracking.

    Exposes only what customers need to see:
    - Order identification and status
    - Delivery dates (original and estimated)
    - Progress tracking (stages, gates)
    - Customer notes

    Excludes internal fields like FK IDs, HubSpot internals, archived status.
    """
    order_status = serializers.CharField(source='get_order_status_display', read_only=True)
    order_status_code = serializers.CharField(source='order_status', read_only=True)

    # Progress info
    process_stages = serializers.SerializerMethodField()
    gate_info = serializers.SerializerMethodField()
    parts_summary = serializers.SerializerMethodField()

    # Notes (filtered to visible only)
    latest_note = serializers.SerializerMethodField()
    notes_timeline = serializers.SerializerMethodField()

    # Company display name (not the FK)
    company_name = serializers.SerializerMethodField()

    # Customer name fields
    customer_first_name = serializers.CharField(source='customer.first_name', read_only=True, allow_null=True)
    customer_last_name = serializers.CharField(source='customer.last_name', read_only=True, allow_null=True)

    class Meta:
        model = Orders
        fields = (
            'id',
            'order_number',
            'name',
            'latest_note',
            'notes_timeline',
            'order_status',
            'order_status_code',
            'estimated_completion',
            'original_completion_date',
            'process_stages',
            'gate_info',
            'parts_summary',
            'company_name',
            'customer_first_name',
            'customer_last_name',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields  # All fields are read-only

    @extend_schema_field(serializers.ListField())
    def get_process_stages(self, obj):
        """Get detailed stage info for progress tracking"""
        return obj.get_detailed_stage_info()

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_gate_info(self, obj):
        """Get milestone/gate progress information. Reads from current_milestone, falls back to legacy HubSpot."""
        return obj.get_gate_info()

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_parts_summary(self, obj):
        """Summary of parts progress using weighted position through workflow."""
        from Tracker.models import ProcessStep

        total = obj.parts.count()
        completed = obj.parts.filter(part_status=PartsStatus.COMPLETED).count()

        if total == 0:
            return {
                'total_parts': 0,
                'completed_parts': 0,
                'progress_percent': 0.0
            }

        # Get the process from work order
        wo = obj.related_orders.filter(process__isnull=False).first()
        if not wo or not wo.process:
            # Fall back to simple completed count
            return {
                'total_parts': total,
                'completed_parts': completed,
                'progress_percent': round((completed / total * 100), 1)
            }

        # Build step order map
        process_steps = ProcessStep.objects.filter(process=wo.process).order_by('order')
        step_order_map = {ps.step_id: ps.order for ps in process_steps}
        total_steps = process_steps.count()

        if total_steps == 0:
            return {
                'total_parts': total,
                'completed_parts': completed,
                'progress_percent': 0.0
            }

        # Calculate weighted progress based on part positions
        # Step order is 1-based, so step_order / total_steps gives progress
        total_progress = 0.0
        for part in obj.parts.select_related('step').all():
            if part.part_status == PartsStatus.COMPLETED:
                # Completed parts count as 100%
                total_progress += 1.0
            elif part.step_id and part.step_id in step_order_map:
                # Progress = step_order / total_steps (1-based order)
                # Step 1 of 11 = 9%, Step 4 of 11 = 36%, Step 11 of 11 = 100%
                step_order = step_order_map[part.step_id]
                total_progress += step_order / total_steps
            # Parts with no step or not in process count as 0%

        progress_percent = round((total_progress / total) * 100, 1)

        return {
            'total_parts': total,
            'completed_parts': completed,
            'progress_percent': progress_percent
        }

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_company_name(self, obj):
        """Safe access to company name"""
        return obj.company.name if obj.company else None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_latest_note(self, obj):
        """Get the most recent visible note"""
        return obj.get_latest_note(customer_view=True)

    @extend_schema_field(serializers.ListField())
    def get_notes_timeline(self, obj):
        """Get all visible notes (internal notes filtered out)"""
        return obj.get_notes(customer_view=True)


# ===== PARTS SERIALIZERS =====

class PartsSerializer(serializers.ModelSerializer, SecureModelMixin, BulkOperationsMixin):
    """Enhanced parts serializer using model methods"""

    # QA status from model properties (single source of truth)
    needs_qa = serializers.BooleanField(read_only=True)
    qa_completed = serializers.BooleanField(read_only=True)

    # Display fields using model methods
    quality_info = serializers.SerializerMethodField()

    # Related object info
    part_type_info = serializers.SerializerMethodField()
    step_info = serializers.SerializerMethodField()

    # Legacy compatibility fields
    has_error = serializers.SerializerMethodField(read_only=True)
    part_type_name = serializers.SerializerMethodField(read_only=True)
    process = serializers.SerializerMethodField(read_only=True)
    process_name = serializers.SerializerMethodField(read_only=True)
    order_name = serializers.SerializerMethodField()
    step_description = serializers.SerializerMethodField(read_only=True)
    work_order_erp_id = serializers.SerializerMethodField()

    # Batch process info
    is_from_batch_process = serializers.SerializerMethodField(read_only=True)

    # Write fields
    step = TenantScopedPrimaryKeyRelatedField(queryset=Steps.unscoped.all())
    part_type = TenantScopedPrimaryKeyRelatedField(queryset=PartTypes.unscoped.all())
    order = TenantScopedPrimaryKeyRelatedField(queryset=Orders.unscoped.all(), required=False, allow_null=True)
    work_order = TenantScopedPrimaryKeyRelatedField(queryset=WorkOrder.unscoped.all(), required=False, allow_null=True)

    class Meta:
        model = Parts
        fields = ('id', 'ERP_id', 'part_status', 'requires_sampling', 'needs_qa', 'qa_completed',
                  'order', 'part_type', 'part_type_info', 'step', 'step_info', 'work_order', 'quality_info',
                  'created_at', 'updated_at', 'has_error', 'part_type_name', 'process_name', 'order_name',
                  'step_description', 'work_order_erp_id', 'is_from_batch_process', 'sampling_rule',
                  'sampling_ruleset', 'sampling_context', 'process', 'total_rework_count', 'archived')
        read_only_fields = (
            'created_at', 'updated_at', 'requires_sampling', 'needs_qa', 'qa_completed', 'quality_info',
            'part_type_info', 'step_info', 'has_error', 'part_type_name', 'process_name', 'order_name',
            'step_description', 'work_order_erp_id', 'is_from_batch_process', 'process', 'total_rework_count',
            'step')  # Step changes must go through increment action for validation

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_quality_info(self, obj):
        """Use model methods for quality status"""
        return {'has_errors': obj.has_quality_errors(), 'latest_status': obj.get_latest_quality_status(),
                'error_count': obj.error_reports.count()}

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_part_type_info(self, obj):
        if obj.part_type:
            return {'id': obj.part_type.id, 'name': obj.part_type.name, 'version': obj.part_type.version,
                    'ID_prefix': obj.part_type.ID_prefix}
        return None

    @extend_schema_field(serializers.UUIDField(allow_null=True))
    def get_process(self, obj):
        # Prefer work_order's locked process
        if obj.work_order and obj.work_order.process:
            return obj.work_order.process.id
        # Fallback: find approved process for part_type
        if obj.part_type:
            process = obj.part_type.processes.filter(status__in=['APPROVED', 'DEPRECATED']).first()
            if process:
                return process.id
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_step_info(self, obj):
        if obj.step:
            # Get process from work_order for process-specific fields
            process = obj.work_order.process if obj.work_order else None
            process_name = process.name if process else None

            # Get step order from ProcessStep if we have a process context
            step_order = None
            is_last_step = False
            if process:
                from Tracker.models import ProcessStep
                ps = ProcessStep.objects.filter(process=process, step=obj.step).first()
                if ps:
                    step_order = ps.order
                    # Check if this is the last step by comparing with max order
                    max_order = process.process_steps.aggregate(m=models.Max('order'))['m']
                    is_last_step = ps.order == max_order

            return {
                'id': obj.step.id,
                'name': obj.step.name,
                'order': step_order,
                'description': obj.step.description,
                'is_last_step': is_last_step,
                'process_name': process_name
            }
        return None

    # Legacy compatibility methods
    @extend_schema_field(serializers.BooleanField())
    def get_has_error(self, obj):
        """Use model method"""
        return obj.has_quality_errors()

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_work_order_erp_id(self, obj):
        return obj.work_order.ERP_id if obj.work_order and obj.work_order.ERP_id else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_part_type_name(self, obj):
        return obj.part_type.name if obj.part_type else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_order_name(self, obj):
        return obj.order.name if obj.order else None

    @extend_schema_field(serializers.CharField())
    def get_step_description(self, obj):
        return obj.step.description if obj.step else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_process_name(self, obj):
        # Prefer work_order's locked process
        if obj.work_order and obj.work_order.process:
            return obj.work_order.process.name
        # Fallback: find approved process for part_type
        if obj.part_type:
            process = obj.part_type.processes.filter(status__in=['APPROVED', 'DEPRECATED']).first()
            if process:
                return process.name
        return None

    @extend_schema_field(serializers.BooleanField())
    def get_is_from_batch_process(self, obj):
        """Check if this part comes from a batch process"""
        if obj.part_type and obj.part_type.processes.exists():
            return obj.part_type.processes.filter(is_batch_process=True).exists()
        return False


class PartSelectSerializer(serializers.ModelSerializer):
    """Lightweight part serializer for dropdown/combobox selections"""
    part_type_name = serializers.CharField(source='part_type.name', read_only=True, allow_null=True)

    class Meta:
        model = Parts
        fields = ('id', 'ERP_id', 'part_type', 'part_type_name', 'part_status')


class CustomerPartsSerializer(serializers.ModelSerializer):
    """Customer parts serializer with order info"""
    orders = serializers.SerializerMethodField()

    class Meta:
        model = Parts
        exclude = ['ERP_id', 'work_order']
        depth = 2

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_orders(self, obj):
        """Get order info"""
        if obj.order:
            return {'id': obj.order.id, 'name': obj.order.name, 'status': obj.order.order_status}
        return None


# ===== WORK ORDER SERIALIZERS =====

def _serialize_current_hold(wo):
    """Return {reason, placed_at, placed_by_name, notes, hours_open} or None."""
    holds = getattr(wo, '_open_holds_cache', None)
    if holds is None:
        from Tracker.models import WorkOrderHold
        holds = list(WorkOrderHold.objects.filter(
            work_order=wo, cleared_at__isnull=True, is_voided=False,
        ).select_related('placed_by')[:1])
    if not holds:
        return None
    h = holds[0]
    from django.utils import timezone
    hours_open = (timezone.now() - h.placed_at).total_seconds() / 3600.0 if h.placed_at else None
    placed_by_name = None
    if h.placed_by:
        placed_by_name = (f"{h.placed_by.first_name} {h.placed_by.last_name}".strip()
                          or h.placed_by.username)
    return {
        'id': str(h.id),
        'reason': h.reason,
        'placed_at': h.placed_at,
        'placed_by_name': placed_by_name,
        'notes': h.notes,
        'expected_clear_at': h.expected_clear_at,
        'hours_open': round(hours_open, 2) if hours_open is not None else None,
    }


class WorkOrderListSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Lightweight serializer for work order list views - avoids N+1 queries."""
    related_order_info = serializers.SerializerMethodField()
    parts_count = serializers.SerializerMethodField()
    qa_progress = serializers.SerializerMethodField()
    process_info = serializers.SerializerMethodField()
    completed_parts_count = serializers.SerializerMethodField()
    is_batch_work_order = serializers.SerializerMethodField()
    current_hold = serializers.SerializerMethodField()
    parent_workorder_id = serializers.UUIDField(read_only=True, allow_null=True)
    child_count = serializers.SerializerMethodField()

    class Meta:
        model = WorkOrder
        fields = (
            'id', 'ERP_id', 'workorder_status', 'priority', 'quantity', 'related_order', 'related_order_info',
            'process', 'process_info', 'expected_completion', 'true_completion',
            'expected_duration', 'true_duration', 'notes', 'parts_count', 'qa_progress',
            'completed_parts_count', 'is_batch_work_order', 'current_hold',
            'parent_workorder_id', 'split_reason', 'split_at', 'child_count',
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = (
            'created_at', 'updated_at', 'related_order_info', 'parts_count', 'qa_progress', 'process_info',
            'completed_parts_count', 'is_batch_work_order', 'current_hold',
            'parent_workorder_id', 'split_reason', 'split_at', 'child_count',
        )

    @extend_schema_field(serializers.IntegerField())
    def get_child_count(self, obj):
        if hasattr(obj, '_child_count'):
            return obj._child_count
        return obj.child_workorders.count()

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_current_hold(self, obj):
        return _serialize_current_hold(obj)

    @extend_schema_field(serializers.IntegerField())
    def get_completed_parts_count(self, obj):
        if hasattr(obj, '_completed_parts_count'):
            return obj._completed_parts_count
        return obj.parts.filter(part_status__in=(
            PartsStatus.COMPLETED, PartsStatus.SHIPPED, PartsStatus.IN_STOCK,
            PartsStatus.AWAITING_PICKUP, PartsStatus.CORE_BANKED, PartsStatus.RMA_CLOSED,
        )).count()

    @extend_schema_field(serializers.BooleanField())
    def get_is_batch_work_order(self, obj):
        if hasattr(obj, '_is_batch_work_order'):
            return obj._is_batch_work_order
        return obj.parts.filter(part_type__processes__is_batch_process=True).exists()

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_process_info(self, obj):
        if obj.process:
            return {'id': obj.process.id, 'name': obj.process.name, 'version': obj.process.version}
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_related_order_info(self, obj):
        if obj.related_order:
            order = obj.related_order
            return {
                'id': order.id,
                'name': order.name,
                'status': order.order_status,
                'customer': {
                    'id': order.customer.id,
                    'username': order.customer.username,
                    'first_name': order.customer.first_name,
                    'last_name': order.customer.last_name,
                    'email': order.customer.email,
                } if order.customer else None,
                'company': {
                    'id': order.company.id,
                    'name': order.company.name,
                } if order.company else None,
            }
        return None

    @extend_schema_field(serializers.IntegerField())
    def get_parts_count(self, obj):
        # Use prefetched count if available, otherwise query
        if hasattr(obj, '_parts_count'):
            return obj._parts_count
        return obj.parts.count()

    @extend_schema_field(serializers.DictField())
    def get_qa_progress(self, obj):
        """Return QA progress as completed/required counts."""
        # Use annotated values if available from optimized queryset
        if hasattr(obj, '_qa_required') and hasattr(obj, '_qa_completed'):
            return {
                'required': obj._qa_required,
                'completed': obj._qa_completed,
            }

        # Fallback to queries - only count active parts (exclude SCRAPPED/CANCELLED)
        # This matches the QA detail page filter for consistency
        from Tracker.models import PartsStatus
        active_statuses = [
            PartsStatus.PENDING, PartsStatus.IN_PROGRESS,
            PartsStatus.AWAITING_QA,  # Parts waiting for QA inspection
            PartsStatus.REWORK_NEEDED, PartsStatus.REWORK_IN_PROGRESS,
            PartsStatus.READY_FOR_NEXT_STEP, PartsStatus.COMPLETED
        ]
        parts = obj.parts.filter(part_status__in=active_statuses)
        required = parts.filter(requires_sampling=True).count()
        # Completed = has at least one error_report (QualityReport) with PASS status
        completed = parts.filter(
            requires_sampling=True,
            error_reports__status='PASS'
        ).distinct().count()

        return {
            'required': required,
            'completed': completed,
        }


class WorkOrderSerializer(serializers.ModelSerializer, SecureModelMixin, BulkOperationsMixin):
    """Full work order serializer for detail views"""
    related_order_info = serializers.SerializerMethodField()
    parts_summary = serializers.SerializerMethodField()
    related_order_detail = serializers.SerializerMethodField()
    is_batch_work_order = serializers.SerializerMethodField()
    process_info = serializers.SerializerMethodField()
    current_hold = serializers.SerializerMethodField()
    parent_workorder_id = serializers.UUIDField(read_only=True, allow_null=True)
    child_count = serializers.SerializerMethodField()

    related_order = TenantScopedPrimaryKeyRelatedField(queryset=Orders.unscoped.all(), required=False, allow_null=True)

    class Meta:
        model = WorkOrder
        fields = (
        'id', 'ERP_id', 'workorder_status', 'priority', 'quantity', 'related_order', 'related_order_info', 'related_order_detail',
        'process', 'process_info', 'expected_completion', 'expected_duration', 'true_completion', 'true_duration',
        'notes', 'parts_summary', 'is_batch_work_order', 'current_hold',
        'parent_workorder_id', 'split_reason', 'split_at', 'child_count',
        'created_at', 'updated_at', 'archived')
        read_only_fields = (
            'created_at', 'updated_at', 'related_order_info', 'parts_summary', 'related_order_detail',
            'is_batch_work_order', 'process_info', 'current_hold',
            'parent_workorder_id', 'split_reason', 'split_at', 'child_count')

    @extend_schema_field(serializers.IntegerField())
    def get_child_count(self, obj):
        if hasattr(obj, '_child_count'):
            return obj._child_count
        return obj.child_workorders.count()

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_current_hold(self, obj):
        return _serialize_current_hold(obj)

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_process_info(self, obj):
        if obj.process:
            return {'id': obj.process.id, 'name': obj.process.name, 'version': obj.process.version}
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_related_order_info(self, obj):
        if obj.related_order:
            return {'id': obj.related_order.id, 'name': obj.related_order.name,
                    'status': obj.related_order.order_status,
                    'customer': obj.related_order.customer.username if obj.related_order.customer else None}
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_related_order_detail(self, obj):
        if obj.related_order:
            return OrdersSerializer(obj.related_order, context=self.context).data
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_parts_summary(self, obj):
        parts = obj.parts.all()
        has_batch_parts = parts.filter(part_type__processes__is_batch_process=True).exists()

        # Parts needing QA = requires_sampling but no PASS report yet (mirrors Parts.needs_qa property)
        needs_qa_parts = parts.filter(
            requires_sampling=True,
            part_status__in=['PENDING', 'IN_PROGRESS', 'AWAITING_QA', 'READY_FOR_NEXT_STEP',
                            'REWORK_NEEDED', 'REWORK_IN_PROGRESS']
        ).exclude(error_reports__status='PASS')
        return {'total': parts.count(), 'requiring_qa': needs_qa_parts.count(),
                'completed': parts.filter(part_status=PartsStatus.COMPLETED).count(),
                'in_progress': parts.filter(part_status=PartsStatus.IN_PROGRESS).count(),
                'pending': parts.filter(part_status=PartsStatus.PENDING).count(), 'has_batch_parts': has_batch_parts}

    @extend_schema_field(serializers.BooleanField())
    def get_is_batch_work_order(self, obj):
        """Check if any parts in this work order come from batch processes"""
        return obj.parts.filter(part_type__processes__is_batch_process=True).exists()


# ===== DIGITAL TRAVELER SERIALIZERS =====

# --- Work Order Step Summary (lightweight) ---

class StepSummarySerializer(serializers.Serializer):
    """Lightweight step summary for work order overview"""
    step_id = serializers.UUIDField()
    step_name = serializers.CharField()
    step_order = serializers.IntegerField()
    status = serializers.ChoiceField(choices=['COMPLETED', 'IN_PROGRESS', 'PENDING', 'SKIPPED'])
    started_at = serializers.DateTimeField(allow_null=True)
    completed_at = serializers.DateTimeField(allow_null=True)
    duration_seconds = serializers.IntegerField(allow_null=True)
    operator_name = serializers.CharField(allow_null=True)
    quality_status = serializers.ChoiceField(choices=['PASS', 'FAIL', 'CONDITIONAL'], allow_null=True)
    parts_at_step = serializers.IntegerField()
    parts_completed = serializers.IntegerField()
    measurement_count = serializers.IntegerField()
    defect_count = serializers.IntegerField()
    attachment_count = serializers.IntegerField()


class WorkOrderStepHistoryResponseSerializer(serializers.Serializer):
    """Response for GET /api/WorkOrders/{id}/step_history/"""
    work_order_id = serializers.UUIDField()
    process_name = serializers.CharField(allow_null=True)
    total_parts = serializers.IntegerField()
    step_history = StepSummarySerializer(many=True)


# --- Part Traveler (detailed) ---

class TravelerOperatorSerializer(serializers.Serializer):
    """Operator info for part traveler"""
    id = serializers.IntegerField()
    name = serializers.CharField()
    employee_id = serializers.CharField(allow_null=True)


class TravelerApprovalSerializer(serializers.Serializer):
    """Approval info for part traveler"""
    id = serializers.IntegerField()
    name = serializers.CharField()
    approved_at = serializers.DateTimeField()


class TravelerEquipmentSerializer(serializers.Serializer):
    """Equipment used at a step"""
    id = serializers.UUIDField()
    name = serializers.CharField()
    calibration_due = serializers.DateField(allow_null=True)


class TravelerMeasurementSerializer(serializers.Serializer):
    """Measurement result for part traveler"""
    definition_id = serializers.UUIDField()
    label = serializers.CharField()
    nominal = serializers.FloatField(allow_null=True)
    upper_tol = serializers.FloatField(allow_null=True)
    lower_tol = serializers.FloatField(allow_null=True)
    actual_value = serializers.FloatField(allow_null=True)
    unit = serializers.CharField(allow_null=True)
    passed = serializers.BooleanField()
    recorded_at = serializers.DateTimeField()
    recorded_by = serializers.CharField(allow_null=True)


class TravelerDefectSerializer(serializers.Serializer):
    """Defect found at a step"""
    error_type_id = serializers.UUIDField(allow_null=True)
    error_name = serializers.CharField()
    severity = serializers.CharField(allow_null=True)
    disposition = serializers.CharField(allow_null=True)


class TravelerMaterialSerializer(serializers.Serializer):
    """Material used at a step"""
    material_name = serializers.CharField()
    lot_number = serializers.CharField(allow_null=True)
    quantity = serializers.FloatField()


class TravelerAttachmentSerializer(serializers.Serializer):
    """Attachment for part traveler"""
    id = serializers.UUIDField()
    file_name = serializers.CharField()
    file_url = serializers.CharField()
    uploaded_at = serializers.DateTimeField()
    classification = serializers.CharField(allow_null=True)


class TravelerStepEntrySerializer(serializers.Serializer):
    """Full step entry in the part traveler history"""
    step_id = serializers.UUIDField()
    step_name = serializers.CharField()
    step_order = serializers.IntegerField()
    visit_number = serializers.IntegerField(default=1)
    status = serializers.ChoiceField(choices=['COMPLETED', 'IN_PROGRESS', 'PENDING', 'SKIPPED'])

    started_at = serializers.DateTimeField(allow_null=True)
    completed_at = serializers.DateTimeField(allow_null=True)
    duration_seconds = serializers.IntegerField(allow_null=True)

    operator = TravelerOperatorSerializer(allow_null=True)
    approved_by = TravelerApprovalSerializer(allow_null=True)

    equipment_used = TravelerEquipmentSerializer(many=True)
    measurements = TravelerMeasurementSerializer(many=True)
    quality_status = serializers.ChoiceField(choices=['PASS', 'FAIL', 'CONDITIONAL'], allow_null=True)
    defects_found = TravelerDefectSerializer(many=True)
    materials_used = TravelerMaterialSerializer(many=True)
    attachments = TravelerAttachmentSerializer(many=True)


class PartTravelerResponseSerializer(serializers.Serializer):
    """Response for GET /api/Parts/{id}/traveler/"""
    part_id = serializers.UUIDField()
    part_erp_id = serializers.CharField()
    work_order_id = serializers.UUIDField(allow_null=True)
    process_name = serializers.CharField(allow_null=True)
    current_step_id = serializers.UUIDField(allow_null=True)
    current_step_name = serializers.CharField(allow_null=True)
    part_status = serializers.CharField()
    traveler = TravelerStepEntrySerializer(many=True)


# ===== STEP AND PROCESS SERIALIZERS =====

class StepsSerializer(serializers.ModelSerializer, SecureModelMixin):
    """
    Steps serializer - represents step node properties.

    Steps are now independent entities that can be shared across process versions.
    Ordering and routing are defined in ProcessStep and StepEdge tables.

    Versioning (leaf-style): Steps have no DRAFT/APPROVED status lifecycle, so
    content edits are routed through `create_new_version` automatically. Only
    `archived` bypasses versioning (archive-in-place).
    """
    part_type_info = serializers.SerializerMethodField()
    part_type_name = serializers.CharField(source="part_type.name", read_only=True, allow_null=True)

    # Fields whose edits are metadata-only and should NOT trigger a new version.
    _NON_VERSIONING_FIELDS = frozenset({'archived'})

    class Meta:
        model = Steps
        fields = (
            'id', 'name', 'expected_duration', 'description', 'block_on_quarantine',
            'requires_qa_signoff', 'sampling_required', 'min_sampling_rate', 'pass_threshold',
            # First Piece Inspection
            'requires_first_piece_inspection',
            'part_type', 'part_type_info', 'part_type_name',
            # Workflow engine - step type
            'step_type',
            # Workflow engine - branching type (edges defined separately in StepEdge)
            'is_decision_point', 'decision_type',
            # Workflow engine - terminal
            'is_terminal', 'terminal_status',
            # Workflow engine - cycle control
            'max_visits', 'revisit_assignment', 'revisit_role',
            # Timestamps
            'created_at', 'updated_at', 'archived',
            # Versioning
            'version',
        )
        read_only_fields = (
            'created_at', 'updated_at', 'part_type_info', 'part_type_name', 'version'
        )

    def update(self, instance, validated_data):
        """Route content edits through `create_new_version`; let archive
        toggles through as a plain save."""
        from Tracker.services.core.versioning import apply_versioned_update
        return apply_versioned_update(
            instance, validated_data,
            non_versioning_fields=self._NON_VERSIONING_FIELDS,
            default_update=super().update,
        )

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_part_type_info(self, obj):
        if obj.part_type:
            return {'id': obj.part_type.id, 'name': obj.part_type.name, 'version': obj.part_type.version,
                    'ID_prefix': obj.part_type.ID_prefix}
        return None


# ===== STEP EXECUTION SERIALIZERS =====

class StepExecutionSerializer(serializers.ModelSerializer, SecureModelMixin):
    """
    Serializer for step execution tracking (workflow engine).

    Provides WIP tracking, visit history, and operator assignment info.
    """
    # Related info
    part_info = serializers.SerializerMethodField()
    step_info = serializers.SerializerMethodField()
    assigned_to_info = serializers.SerializerMethodField()
    completed_by_info = serializers.SerializerMethodField()

    # Computed fields
    duration_seconds = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = StepExecution
        fields = (
            'id', 'part', 'step', 'visit_number',
            'part_info', 'step_info',
            'entered_at', 'exited_at', 'duration_seconds',
            'assigned_to', 'assigned_to_info',
            'completed_by', 'completed_by_info',
            'next_step', 'decision_result', 'status', 'is_active',
            'created_at', 'updated_at', 'archived'
        )
        read_only_fields = (
            'created_at', 'updated_at', 'part_info', 'step_info',
            'assigned_to_info', 'completed_by_info', 'duration_seconds', 'is_active'
        )

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_part_info(self, obj):
        if obj.part:
            return {
                'id': obj.part.id,
                'ERP_id': obj.part.ERP_id,
                'status': obj.part.part_status,
                'part_type_name': obj.part.part_type.name if obj.part.part_type else None,
            }
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_step_info(self, obj):
        if obj.step:
            # Get step order from ProcessStep using the part's work_order process context
            step_order = None
            if obj.part and obj.part.work_order and obj.part.work_order.process:
                ps = ProcessStep.objects.filter(
                    process=obj.part.work_order.process,
                    step=obj.step
                ).first()
                if ps:
                    step_order = ps.order

            return {
                'id': obj.step.id,
                'name': obj.step.name,
                'order': step_order,
                'is_decision_point': obj.step.is_decision_point,
                'decision_type': obj.step.decision_type,
                'max_visits': obj.step.max_visits,
            }
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_assigned_to_info(self, obj):
        if obj.assigned_to:
            return {
                'id': obj.assigned_to.id,
                'username': obj.assigned_to.username,
                'full_name': f"{obj.assigned_to.first_name} {obj.assigned_to.last_name}".strip(),
            }
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_completed_by_info(self, obj):
        if obj.completed_by:
            return {
                'id': obj.completed_by.id,
                'username': obj.completed_by.username,
                'full_name': f"{obj.completed_by.first_name} {obj.completed_by.last_name}".strip(),
            }
        return None

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_duration_seconds(self, obj):
        """Return duration in seconds for easier JS handling."""
        duration = obj.duration
        if duration:
            return duration.total_seconds()
        return None

    @extend_schema_field(serializers.BooleanField())
    def get_is_active(self, obj):
        """Whether this execution is still active (not exited)."""
        return obj.exited_at is None


class StepExecutionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views - avoids N+1 with select_related."""
    part_erp_id = serializers.CharField(source='part.ERP_id', read_only=True)
    part_status = serializers.CharField(source='part.part_status', read_only=True)
    step_name = serializers.CharField(source='step.name', read_only=True)
    step_order = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = StepExecution
        fields = (
            'id', 'part', 'part_erp_id', 'part_status',
            'step', 'step_name', 'step_order', 'visit_number',
            'entered_at', 'exited_at', 'status',
            'assigned_to', 'assigned_to_name', 'decision_result'
        )

    @extend_schema_field(serializers.IntegerField(allow_null=True))
    def get_step_order(self, obj):
        """Get step order from ProcessStep using part's work_order process context."""
        if obj.step and obj.part and obj.part.work_order and obj.part.work_order.process:
            ps = ProcessStep.objects.filter(
                process=obj.part.work_order.process,
                step=obj.step
            ).first()
            if ps:
                return ps.order
        return None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_assigned_to_name(self, obj):
        if obj.assigned_to:
            return f"{obj.assigned_to.first_name} {obj.assigned_to.last_name}".strip()
        return None


class WIPSummarySerializer(serializers.Serializer):
    """Serializer for WIP summary by step."""
    step_id = serializers.UUIDField()
    step_name = serializers.CharField()
    step_order = serializers.IntegerField()
    is_decision_point = serializers.BooleanField()
    pending_count = serializers.IntegerField()
    in_progress_count = serializers.IntegerField()
    total_active = serializers.IntegerField()


class StepSerializer(serializers.ModelSerializer):
    """Step serializer - just the node properties (no process/order/branching)"""
    part_type_name = serializers.CharField(source="part_type.name", read_only=True)

    class Meta:
        model = Steps
        fields = [
            "id", "name", "description", "part_type", "part_type_name", "expected_duration",
            # QA settings
            "requires_qa_signoff", "sampling_required", "min_sampling_rate",
            "block_on_quarantine", "pass_threshold",
            # Workflow engine - step type & behavior
            "step_type", "is_decision_point", "decision_type",
            # Workflow engine - terminal
            "is_terminal", "terminal_status",
            # Workflow engine - cycle control
            "max_visits", "revisit_assignment",
        ]


class ProcessStepSerializer(serializers.ModelSerializer):
    """ProcessStep junction serializer - links step to process with order"""
    step = StepSerializer(read_only=True)
    step_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = ProcessStep
        fields = ["id", "step", "step_id", "order", "is_entry_point"]


class StepEdgeSerializer(serializers.ModelSerializer):
    """StepEdge serializer - DAG edges between steps"""
    from_step_name = serializers.CharField(source="from_step.name", read_only=True)
    to_step_name = serializers.CharField(source="to_step.name", read_only=True)

    class Meta:
        model = StepEdge
        fields = [
            "id", "from_step", "to_step", "edge_type",
            "from_step_name", "to_step_name",
            "condition_measurement", "condition_operator", "condition_value",
        ]


class PartTypesSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Part types serializer with versioning support.

    Content edits (name, ID_prefix, ERP_id, ITAR fields) create a new
    version via `create_new_version`.  Archive-only updates go through a
    plain save.
    """

    # Fields whose edits are soft-delete / metadata only and should NOT
    # trigger a new version.
    _NON_VERSIONING_FIELDS = frozenset({'archived'})

    class Meta:
        model = PartTypes
        fields = [
            'id', 'tenant', 'external_id', 'created_at', 'updated_at', 'archived',
            'name', 'ID_prefix', 'ERP_id',
            'itar_controlled', 'eccn', 'usml_category',
            'version', 'is_current_version', 'previous_version',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'version',
                            'is_current_version', 'previous_version']

    def update(self, instance, validated_data):
        """Route content edits through `create_new_version`; let
        archive toggles through as a plain save."""
        from Tracker.services.core.versioning import apply_versioned_update
        return apply_versioned_update(
            instance, validated_data,
            non_versioning_fields=self._NON_VERSIONING_FIELDS,
            default_update=super().update,
        )


class PartTypeSerializer(serializers.ModelSerializer):
    """Legacy part type serializer"""

    class Meta:
        model = PartTypes
        fields = [
            'id', 'tenant', 'external_id', 'created_at', 'updated_at',
            'name', 'ID_prefix', 'ERP_id',
            'itar_controlled', 'eccn', 'usml_category',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PartTypeSelectSerializer(serializers.ModelSerializer):
    """Lightweight part type serializer for dropdown/combobox selections"""

    class Meta:
        model = PartTypes
        fields = ('id', 'name', 'ID_prefix')


class ProcessesSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Processes serializer with graph structure"""
    part_type_name = serializers.CharField(source="part_type.name", read_only=True)
    process_steps = ProcessStepSerializer(many=True, read_only=True)
    step_edges = StepEdgeSerializer(many=True, read_only=True)
    num_steps = serializers.SerializerMethodField()

    class Meta:
        model = Processes
        fields = [
            'id', 'tenant', 'external_id', 'created_at', 'updated_at',
            'name', 'is_remanufactured', 'part_type', 'is_batch_process',
            'status', 'category', 'change_description', 'approved_at', 'approved_by',
            # Serializer-specific fields
            'part_type_name', 'process_steps', 'step_edges', 'num_steps',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'approved_at', 'approved_by']

    @extend_schema_field(serializers.IntegerField())
    def get_num_steps(self, obj):
        """Return the number of steps in this process."""
        return obj.process_steps.count()


class ProcessWithStepsSerializer(serializers.ModelSerializer):
    """
    Process with steps serializer for creation/updates.

    Uses graph structure:
    - `nodes`: Step definitions (id, name, step_type, etc.)
    - `edges`: Connections between steps (from_step, to_step, edge_type)

    Frontend sends:
    {
        "name": "My Process",
        "part_type": 1,
        "nodes": [
            {"id": 1, "name": "Step 1", "order": 1, ...},  # existing step
            {"id": -1, "name": "New Step", "order": 2, ...},  # new step (negative ID)
        ],
        "edges": [
            {"from_step": 1, "to_step": -1, "edge_type": "default"},  # can reference temp IDs
        ]
    }
    """
    # Read: return nested structure
    process_steps = ProcessStepSerializer(many=True, read_only=True)
    step_edges = StepEdgeSerializer(many=True, read_only=True)

    # Write: accept nodes and edges
    nodes = serializers.ListField(child=serializers.DictField(), write_only=True, required=False)
    edges = serializers.ListField(child=serializers.DictField(), write_only=True, required=False)

    class Meta:
        model = Processes
        fields = [
            "id", "name", "is_remanufactured", "part_type", "is_batch_process",
            # Graph structure (read)
            "process_steps", "step_edges",
            # Graph structure (write)
            "nodes", "edges",
            # Approval workflow fields
            "status", "change_description", "approved_at", "approved_by",
            # Versioning
            "version", "previous_version", "is_current_version",
        ]
        read_only_fields = ["approved_at", "approved_by", "version", "previous_version", "is_current_version"]

    def create(self, validated_data):
        from Tracker.services.mes.processes import create_process_with_steps
        return create_process_with_steps(validated_data)

    def update(self, instance, validated_data):
        """
        Update process with graph structure.

        - Nodes with positive ID: UPDATE existing step
        - Nodes with negative ID: CREATE new step
        - Nodes in DB but not in payload: REMOVE from process (step may be shared)
        - Edges: Replace all (delete and recreate)
        """
        from Tracker.services.mes.processes import update_process_with_steps
        user = self.context['request'].user if 'request' in self.context else None
        try:
            return update_process_with_steps(instance, validated_data, user=user)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc


# ===== EQUIPMENT SERIALIZERS =====

class EquipmentTypeSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Equipment type serializer.

    EquipmentType is a versioned configuration record. Content edits
    (name, description, calibration settings, portability flags) route
    through `create_new_version`. Archiving goes through a plain save.
    """

    class Meta:
        model = EquipmentType
        fields = [
            'id', 'tenant', 'external_id', 'created_at', 'updated_at',
            'name', 'description', 'requires_calibration',
            'default_calibration_interval_days', 'is_portable', 'track_downtime',
            'archived', 'version',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'version']

    _NON_VERSIONING_FIELDS = frozenset({'archived'})

    def update(self, instance, validated_data):
        """Route content edits through `create_new_version`; let
        archive toggles through as a plain save."""
        from Tracker.services.core.versioning import apply_versioned_update
        return apply_versioned_update(
            instance, validated_data,
            non_versioning_fields=self._NON_VERSIONING_FIELDS,
            default_update=super().update,
        )


class EquipmentsSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Equipment serializer.

    Equipments is a versioned asset record. Content edits (name, type,
    serial number, calibration settings, identity fields) route through
    `create_new_version`. Archiving and operational status changes go
    through a plain save.
    """
    equipment_type_name = serializers.CharField(source="equipment_type.name", read_only=True)

    class Meta:
        model = Equipments
        fields = [
            "id", "name", "equipment_type", "equipment_type_name",
            "serial_number", "manufacturer", "model_number", "location", "status", "notes",
            "created_at", "updated_at", "archived", "version",
        ]
        read_only_fields = ("created_at", "updated_at", "version")

    # status is an operational state changed by calibration/maintenance workflows,
    # not a configuration content change.
    _NON_VERSIONING_FIELDS = frozenset({'archived', 'status'})

    def update(self, instance, validated_data):
        """Route content edits through `create_new_version`; let
        archive and status changes through as a plain save."""
        from Tracker.services.core.versioning import apply_versioned_update
        return apply_versioned_update(
            instance, validated_data,
            non_versioning_fields=self._NON_VERSIONING_FIELDS,
            default_update=super().update,
        )


class EquipmentSerializer(serializers.ModelSerializer):
    """Legacy equipment serializer"""
    equipment_type_name = serializers.CharField(source="equipment_type.name", read_only=True)

    class Meta:
        model = Equipments
        fields = [
            "id", "name", "equipment_type", "equipment_type_name",
            "serial_number", "manufacturer", "model_number", "location", "status", "notes",
            "created_at", "updated_at", "archived"
        ]
        read_only_fields = ("created_at", "updated_at")


class EquipmentSelectSerializer(serializers.ModelSerializer):
    """Equipment select serializer"""
    equipment_type = EquipmentTypeSerializer(read_only=True)

    class Meta:
        model = Equipments
        fields = [
            'id', 'name', 'serial_number', 'equipment_type',
            'status', 'location', 'manufacturer', 'model_number',
        ]


# Note: ExternalAPIOrderIdentifier serializer moved to integrations/hubspot_serializers.py


# ===== MILESTONE SERIALIZERS =====

class MilestoneSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Single milestone within a template."""
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = Milestone
        fields = [
            'id', 'template', 'name', 'customer_display_name', 'display_name',
            'display_order', 'description', 'is_active',
        ]
        read_only_fields = ['id', 'display_name']

    @extend_schema_field(serializers.CharField())
    def get_display_name(self, obj):
        return obj.get_display_name()


class MilestoneTemplateSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Milestone template with nested milestones."""
    milestones = MilestoneSerializer(many=True, read_only=True)

    class Meta:
        model = MilestoneTemplate
        fields = [
            'id', 'name', 'description', 'is_default', 'milestones',
            'created_at', 'updated_at', 'archived', 'version',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'version']

    # Fields whose edits are metadata/soft-delete only and should NOT
    # trigger a new version.
    _NON_VERSIONING_FIELDS = frozenset({'archived'})

    def update(self, instance, validated_data):
        """Route content edits through `create_new_version`; let
        archive toggles through as a plain save."""
        from Tracker.services.core.versioning import apply_versioned_update
        return apply_versioned_update(
            instance, validated_data,
            non_versioning_fields=self._NON_VERSIONING_FIELDS,
            default_update=super().update,
        )


class MilestoneTemplateListSerializer(serializers.ModelSerializer, SecureModelMixin):
    """Lightweight template serializer for list views (no nested milestones)."""
    milestone_count = serializers.SerializerMethodField()

    class Meta:
        model = MilestoneTemplate
        fields = ['id', 'name', 'description', 'is_default', 'milestone_count']

    @extend_schema_field(serializers.IntegerField())
    def get_milestone_count(self, obj):
        return obj.milestones.count()


# ===== BULK OPERATION SERIALIZERS =====

class BulkAddPartsSerializer(serializers.Serializer):
    """Legacy bulk add parts serializer"""
    part_type = TenantScopedPrimaryKeyRelatedField(queryset=PartTypes.unscoped.all(), source="part_type_id")
    step = TenantScopedPrimaryKeyRelatedField(queryset=Steps.unscoped.all(), source="step_id")
    quantity = serializers.IntegerField(min_value=1)
    part_status = serializers.ChoiceField(choices=PartsStatus.choices)
    process_id = serializers.UUIDField()
    ERP_id = serializers.CharField()


class BulkRemovePartsSerializer(serializers.Serializer):
    """Legacy bulk remove parts serializer"""
    ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)


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
        fields = []

    def update(self, instance, validated_data):
        result = instance.increment_step()
        return instance


class BulkStepAdvancementSerializer(serializers.Serializer):
    """Serializer for bulk step advancement"""
    step_id = serializers.UUIDField()

    def advance_parts_at_step(self, order):
        """Use model method for bulk step advancement"""
        step_id = self.validated_data['step_id']
        return order.bulk_increment_parts_at_step(step_id)


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
        user = self.context['request'].user
        try:
            return Orders.objects.for_user(user).get(ERP_id=value)
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

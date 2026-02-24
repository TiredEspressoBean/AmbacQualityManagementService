# viewsets/mes_lite.py - MES Lite ViewSets (Manufacturing, Orders, Parts, Processes, Equipment)
from collections import Counter

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema_view, extend_schema, inline_serializer, OpenApiParameter, OpenApiTypes
from rest_framework import viewsets, status, filters, serializers
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.generics import ListAPIView
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from Tracker.filters import PartFilter, OrderFilter
from Tracker.models import (
    # MES Lite models
    Orders, Parts, PartsStatus, WorkOrder, Steps, PartTypes, Processes,
    StepExecution, ProcessStatus,
    # MES Standard models
    Equipments, EquipmentType,
    # Core models
    Documents,
)
from Tracker.serializers.mes_lite import (
    OrdersSerializer, CustomerOrderSerializer, PartsSerializer, PartSelectSerializer, CustomerPartsSerializer,
    WorkOrderSerializer, WorkOrderListSerializer,
    StepsSerializer, StepSerializer, PartTypesSerializer, PartTypeSelectSerializer, ProcessesSerializer,
    ProcessWithStepsSerializer, EquipmentsSerializer, EquipmentTypeSerializer,
    BulkAddPartsSerializer, BulkRemovePartsSerializer,
    StepAdvancementSerializer, BulkStepAdvancementSerializer,
    StepExecutionSerializer, StepExecutionListSerializer, WIPSummarySerializer,
    # Digital Traveler serializers
    WorkOrderStepHistoryResponseSerializer, PartTravelerResponseSerializer,
)
from Tracker.serializers.qms import StepSamplingRulesUpdateSerializer
from Tracker.serializers.dms import DocumentsSerializer
from .core import ExcelExportMixin, ListMetadataMixin, with_int_pk_schema
from .base import TenantScopedMixin
from .mixins import CSVImportMixin, DataExportMixin

# Note: Most viewsets can now use CSVImportMixin and DataExportMixin for automatic
# CSV import/export based on model introspection. Just add the mixins to get:
#   - GET /import-template/ - Download import template
#   - POST /import/ - Import data from CSV/Excel
#   - GET /export/ - Export filtered data to CSV/Excel


# ===== ORDERS VIEWSETS =====

class TrackerOrderViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    """
    Customer-facing read-only order tracking endpoint.

    Security:
    - Read-only: customers cannot create, update, or delete orders
    - Filtered by SecureManager.for_user(): customers only see their own orders
    - Limited fields via CustomerOrderSerializer: no internal data exposed

    Use /api/Orders/ for full CRUD operations (staff only).
    """
    queryset = Orders.objects.all()
    serializer_class = CustomerOrderSerializer
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Orders.objects.none()

        # Apply tenant scoping first, then user filtering
        qs = super().get_queryset()
        return qs

    @extend_schema(
        request=inline_serializer(
            name="InviteViewerInput",
            fields={"email": serializers.EmailField()}
        ),
        responses={
            201: inline_serializer(
                name="InviteViewerResponse",
                fields={
                    "status": serializers.CharField(),
                    "email": serializers.EmailField(),
                    "invitation_id": serializers.IntegerField(allow_null=True),
                    "user_created": serializers.BooleanField(),
                }
            ),
            400: inline_serializer(name="InviteError", fields={"detail": serializers.CharField()}),
        }
    )
    @action(detail=True, methods=['post'], url_path='invite')
    def invite_viewer(self, request, pk=None):
        """
        Invite someone to view this order.

        Works for both staff and customers who have access to the order.
        Creates user if doesn't exist, sends invitation email via Celery.
        """
        from datetime import timedelta
        from django.utils import timezone
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Group
        from Tracker.models.core import UserInvitation
        from Tracker.email_notifications import send_invitation_email
        import secrets

        User = get_user_model()
        order = self.get_object()  # Already filtered by for_user()

        email = request.data.get('email', '').strip().lower()
        if not email:
            return Response({"detail": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Rate limit: max 10 viewers per order
        if order.viewers.count() >= 10:
            return Response(
                {"detail": "Maximum viewers (10) reached for this order"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user already has access
        existing_user = User.objects.filter(email=email).first()
        if existing_user:
            if order.customer == existing_user or order.viewers.filter(id=existing_user.id).exists():
                return Response(
                    {"detail": "This user already has access to this order"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Get or create user
        user_created = False
        if existing_user:
            user = existing_user
        else:
            user = User.objects.create(
                username=email,
                email=email,
                is_active=False,
                is_staff=False,
                tenant=request.user.tenant,  # Assign to requesting user's tenant
            )
            # Add to Customer group within tenant
            customer_group, _ = Group.objects.get_or_create(name='Customer')
            if request.user.tenant:
                user.add_to_tenant_group(customer_group, tenant=request.user.tenant, granted_by=request.user)
            user_created = True

        # Add as viewer
        order.viewers.add(user)

        # Create and send invitation if user needs to activate
        invitation_id = None
        if not user.is_active:
            pending = UserInvitation.objects.filter(
                user=user,
                accepted_at__isnull=True,
                expires_at__gt=timezone.now()
            ).first()

            if pending:
                invitation_id = pending.id
            else:
                invitation = UserInvitation.objects.create(
                    user=user,
                    token=secrets.token_urlsafe(32),
                    invited_by=request.user,
                    expires_at=timezone.now() + timedelta(days=7),
                )
                invitation_id = invitation.id
                send_invitation_email(invitation.id, immediate=False)

        return Response({
            "status": "invited",
            "email": email,
            "invitation_id": invitation_id,
            "user_created": user_created,
        }, status=status.HTTP_201_CREATED)


@extend_schema(
    parameters=[
        OpenApiParameter(
            name='order_id',
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.PATH,
            description='UUID of the order to get parts for'
        ),
    ]
)
class PartsByOrderView(ListAPIView):
    serializer_class = PartsSerializer
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Parts.objects.none()

        order_id = self.kwargs["order_id"]
        # Use SecureManager for user filtering
        return Parts.objects.for_user(self.request.user).filter(order__id=order_id)


@extend_schema_view(list=extend_schema(parameters=[
    OpenApiParameter(name='ordering', description='Which field to order by, prepend "-" for descending.',
                     required=False, type=str), ]))
@extend_schema(parameters=[
    OpenApiParameter(name='status__in', description='Filter by multiple status values.', required=False,
                     type={'type': 'array', 'items': {'type': 'string'}},
                     style='form', explode=True, )])
class PartsViewSet(TenantScopedMixin, ListMetadataMixin, CSVImportMixin, DataExportMixin, viewsets.ModelViewSet):
    """
    Parts CRUD with CSV import/export support.

    Import/Export endpoints (auto-configured from model):
    - GET /import-template/ - Download import template (CSV or Excel)
    - POST /import/ - Import data from CSV/Excel file
    - GET /export/ - Export filtered data to CSV/Excel
    """
    queryset = Parts.objects.all()
    serializer_class = PartsSerializer
    pagination_class = LimitOffsetPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter, filters.SearchFilter]
    filterset_class = PartFilter
    ordering_fields = ['created_at', 'ERP_id', 'part_status']
    ordering = ['-created_at']
    search_fields = ["ERP_id", "order__name", "work_order__ERP_id", "step__name", "part_type__name", "part_status", ]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Parts.objects.none()

        # Apply tenant scoping first, then user filtering
        qs = super().get_queryset()
        return qs.select_related(
            'order', 'order__customer',
            'part_type',
            'step', 'step__part_type',
            'work_order', 'work_order__process'
        )

    @extend_schema(
        request=inline_serializer(
            name="PartIncrementInput",
            fields={
                "decision": serializers.CharField(
                    required=False,
                    help_text="Decision result for branching steps: 'pass', 'fail', 'default', 'alternate', or measurement value"
                )
            }
        ),
        responses={200: dict}
    )
    @action(detail=True, methods=["post"])
    def increment(self, request, pk=None):
        """
        Advance part to next step.

        For decision point steps, provide the decision parameter:
        - qa_result decisions: 'pass' or 'fail'
        - manual decisions: 'default' or 'alternate'
        - measurement decisions: the measurement value (will be compared to threshold)

        If no decision is provided for qa_result decisions, the latest QualityReport status is used.
        """
        part = self.get_object()
        decision_result = request.data.get('decision')

        try:
            result = part.increment_step(
                operator=request.user,
                decision_result=decision_result
            )
            return Response({
                "detail": f"Step {result}.",
                "result": result,
                "new_step_id": part.step.id if part.step else None,
                "new_step_name": part.step.name if part.step else None,
                "part_status": part.part_status,
            })
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        description="Check if part can be rolled back to previous step",
        responses={200: dict}
    )
    @action(detail=True, methods=["get"], url_path="can-rollback")
    def can_rollback(self, request, pk=None):
        """
        Check if this part can be rolled back to its previous step.

        Returns whether rollback is allowed, any blocking reason,
        and whether supervisor approval is required.
        """
        part = self.get_object()
        can_rollback, message, requires_approval = part.can_rollback_step(request.user)

        return Response({
            "can_rollback": can_rollback,
            "message": message,
            "requires_approval": requires_approval,
            "current_step": part.step.name if part.step else None,
            "undo_window_minutes": getattr(part.step, 'undo_window_minutes', 15) if part.step else None,
        })

    @extend_schema(
        description="Roll back part to previous step (configurable per step)",
        request={"application/json": {"type": "object", "properties": {
            "reason": {"type": "string", "description": "Justification for rollback (required if approval needed)"},
            "override_id": {"type": "string", "format": "uuid", "description": "Pre-approved override ID"}
        }}},
        responses={200: dict}
    )
    @action(detail=True, methods=["post"])
    def rollback(self, request, pk=None):
        """
        Roll back part to previous step.

        Respects per-step configuration:
        - undo_window_minutes: Time window during which rollback is allowed
        - rollback_requires_approval: Whether supervisor approval is required

        If approval is required and no override_id is provided, a rollback request
        is created and must be approved before the actual rollback can occur.
        """
        part = self.get_object()
        reason = request.data.get('reason', '')
        override_id = request.data.get('override_id')

        try:
            result = part.rollback_step(
                operator=request.user,
                reason=reason,
                override_id=override_id
            )

            if result['success']:
                return Response({
                    "detail": result['message'],
                    "success": True,
                    "new_step_id": result['previous_step'].id if result.get('previous_step') else None,
                    "new_step_name": result['previous_step'].name if result.get('previous_step') else None,
                    "part_status": part.part_status,
                })
            else:
                # Rollback request submitted, awaiting approval
                return Response({
                    "detail": result['message'],
                    "success": False,
                    "requires_approval": True,
                    "previous_step_name": result['previous_step'].name if result.get('previous_step') else None,
                }, status=status.HTTP_202_ACCEPTED)

        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        description="Lightweight endpoint for dropdown/combobox selections",
        responses={200: PartSelectSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def select(self, request):
        """Return lightweight part data for dropdown selections."""
        queryset = self.filter_queryset(self.get_queryset()).select_related('part_type')
        serializer = PartSelectSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        responses={200: PartTravelerResponseSerializer},
        description="Get full traveler history for a part showing what happened at each step"
    )
    @action(detail=True, methods=['get'])
    def traveler(self, request, pk=None):
        """
        GET /api/Parts/{id}/traveler/

        Returns full step-by-step history for the part, including:
        - Timing (started/completed/duration)
        - Operator and approver info
        - Equipment used
        - Measurements taken
        - Defects found and dispositions
        - Materials consumed
        - Attachments
        """
        from Tracker.models import (
            ProcessStep, QualityReports, MeasurementResult, QuarantineDisposition,
            EquipmentUsage, MaterialUsage, Documents, StepExecution, TimeEntry
        )
        from django.contrib.contenttypes.models import ContentType

        part = self.get_object()
        work_order = part.work_order
        process = work_order.process if work_order else None

        # Get ordered steps for this process
        ordered_steps = []
        if process:
            process_steps = ProcessStep.objects.filter(
                process=process
            ).select_related('step').order_by('order')
            ordered_steps = [(ps.step, ps.order) for ps in process_steps]

        # Get step executions for this part
        executions = StepExecution.objects.filter(
            part=part
        ).select_related('step', 'assigned_to', 'completed_by').order_by('entered_at')
        execution_map = {}  # step_id -> list of executions
        for ex in executions:
            if ex.step_id not in execution_map:
                execution_map[ex.step_id] = []
            execution_map[ex.step_id].append(ex)

        # Get time entries for this part
        time_entries = TimeEntry.objects.filter(
            part=part
        ).select_related('user', 'approved_by').order_by('start_time')
        time_entry_map = {}  # step_id -> list of time entries
        for te in time_entries:
            if te.step_id:
                if te.step_id not in time_entry_map:
                    time_entry_map[te.step_id] = []
                time_entry_map[te.step_id].append(te)

        # Get quality reports for this part
        quality_reports = QualityReports.objects.filter(
            part=part
        ).select_related('step', 'detected_by', 'verified_by').prefetch_related(
            'measurements__definition', 'errors', 'equipment_usages__equipment'
        )
        qr_map = {}  # step_id -> list of quality reports
        for qr in quality_reports:
            if qr.step_id:
                if qr.step_id not in qr_map:
                    qr_map[qr.step_id] = []
                qr_map[qr.step_id].append(qr)

        # Get dispositions for this part
        dispositions = QuarantineDisposition.objects.filter(
            part=part
        ).select_related('step')
        disposition_map = {}  # step_id -> list of dispositions
        for disp in dispositions:
            if disp.step_id:
                if disp.step_id not in disposition_map:
                    disposition_map[disp.step_id] = []
                disposition_map[disp.step_id].append(disp)

        # Get equipment usage for this part
        equipment_usages = EquipmentUsage.objects.filter(
            part=part
        ).select_related('equipment', 'step')
        equipment_map = {}  # step_id -> list of equipment
        for eu in equipment_usages:
            if eu.step_id:
                if eu.step_id not in equipment_map:
                    equipment_map[eu.step_id] = []
                equipment_map[eu.step_id].append(eu)

        # Get material usage for this part
        material_usages = MaterialUsage.objects.filter(
            part=part
        ).select_related('lot', 'step')
        material_map = {}  # step_id -> list of materials
        for mu in material_usages:
            if mu.step_id:
                if mu.step_id not in material_map:
                    material_map[mu.step_id] = []
                material_map[mu.step_id].append(mu)

        # Get attachments for this part and its steps
        part_ct = ContentType.objects.get_for_model(Parts)
        step_ct = ContentType.objects.get_for_model(Steps)
        qr_ct = ContentType.objects.get_for_model(QualityReports)

        # Part-level documents
        part_docs = Documents.objects.filter(
            content_type=part_ct,
            object_id=str(part.id)
        )

        # Step-level documents
        step_ids = [str(step.id) for step, _ in ordered_steps]
        step_docs = Documents.objects.filter(
            content_type=step_ct,
            object_id__in=step_ids
        )

        # QR-level documents
        qr_ids = [str(qr.id) for qrs in qr_map.values() for qr in qrs]
        qr_docs = Documents.objects.filter(
            content_type=qr_ct,
            object_id__in=qr_ids
        ) if qr_ids else Documents.objects.none()

        # Build attachment map by step
        attachment_map = {}  # step_id -> list of docs
        for doc in step_docs:
            step_id_str = doc.object_id
            try:
                from uuid import UUID
                step_uuid = UUID(step_id_str)
                if step_uuid not in attachment_map:
                    attachment_map[step_uuid] = []
                attachment_map[step_uuid].append(doc)
            except ValueError:
                pass

        # Determine max step order reached
        current_step_order = -1
        if part.step:
            for step, order in ordered_steps:
                if step.id == part.step_id:
                    current_step_order = order
                    break

        # Build traveler entries
        traveler = []
        for step, order in ordered_steps:
            step_id = step.id
            step_execs = execution_map.get(step_id, [])
            step_time_entries = time_entry_map.get(step_id, [])
            step_qrs = qr_map.get(step_id, [])
            step_dispositions = disposition_map.get(step_id, [])
            step_equipment = equipment_map.get(step_id, [])
            step_materials = material_map.get(step_id, [])
            step_attachments = attachment_map.get(step_id, [])

            # Handle multiple visits (rework cycles)
            visit_count = len(step_execs) if step_execs else (1 if order <= current_step_order else 0)
            visit_number = visit_count if visit_count > 0 else 1

            # Determine status
            if part.step_id == step_id:
                step_status = 'IN_PROGRESS'
            elif step_execs and any(ex.status == 'completed' for ex in step_execs):
                step_status = 'COMPLETED'
            elif order < current_step_order:
                step_status = 'COMPLETED'
            elif step_execs and any(ex.status == 'skipped' for ex in step_execs):
                step_status = 'SKIPPED'
            else:
                step_status = 'PENDING'

            # Get timing from executions or time entries
            started_at = None
            completed_at = None
            if step_execs:
                started_at = min((ex.entered_at for ex in step_execs if ex.entered_at), default=None)
                completed_at = max((ex.exited_at for ex in step_execs if ex.exited_at), default=None)
            elif step_time_entries:
                started_at = min((te.start_time for te in step_time_entries if te.start_time), default=None)
                completed_at = max((te.end_time for te in step_time_entries if te.end_time), default=None)

            duration_seconds = None
            if started_at and completed_at:
                duration_seconds = int((completed_at - started_at).total_seconds())

            # Get operator info
            operator = None
            if step_execs and step_execs[0].assigned_to:
                user = step_execs[0].assigned_to
                operator = {
                    'id': user.id,
                    'name': user.get_full_name() or user.username,
                    'employee_id': getattr(user, 'employee_id', None)
                }
            elif step_time_entries and step_time_entries[0].user:
                user = step_time_entries[0].user
                operator = {
                    'id': user.id,
                    'name': user.get_full_name() or user.username,
                    'employee_id': getattr(user, 'employee_id', None)
                }

            # Get approval info
            approved_by = None
            for te in step_time_entries:
                if te.approved and te.approved_by:
                    approved_by = {
                        'id': te.approved_by.id,
                        'name': te.approved_by.get_full_name() or te.approved_by.username,
                        'approved_at': te.approved_at
                    }
                    break

            # Build equipment list
            equipment_used = []
            seen_equipment = set()
            for eu in step_equipment:
                if eu.equipment and eu.equipment.id not in seen_equipment:
                    seen_equipment.add(eu.equipment.id)
                    equipment_used.append({
                        'id': eu.equipment.id,
                        'name': eu.equipment.name,
                        'calibration_due': eu.equipment.calibration_due if hasattr(eu.equipment, 'calibration_due') else None
                    })

            # Build measurements list
            measurements = []
            for qr in step_qrs:
                for mr in qr.measurements.all():
                    measurements.append({
                        'definition_id': mr.definition.id if mr.definition else None,
                        'label': mr.definition.label if mr.definition else 'Unknown',
                        'nominal': mr.definition.nominal if mr.definition else None,
                        'upper_tol': mr.definition.upper_tol if mr.definition else None,
                        'lower_tol': mr.definition.lower_tol if mr.definition else None,
                        'actual_value': mr.value_numeric,
                        'unit': mr.definition.unit if mr.definition else '',
                        'passed': mr.is_within_spec,
                        'recorded_at': mr.created_at,
                        'recorded_by': mr.created_by.get_full_name() if mr.created_by else None
                    })

            # Determine quality status
            quality_status = None
            for qr in step_qrs:
                if qr.status == 'FAIL':
                    quality_status = 'FAIL'
                    break
                elif qr.status == 'PASS' and quality_status != 'FAIL':
                    quality_status = 'PASS'

            # Build defects list
            defects_found = []
            for qr in step_qrs:
                if qr.status == 'FAIL':
                    for error in qr.errors.all():
                        # Find disposition for this defect
                        disp_type = None
                        for disp in step_dispositions:
                            if qr in disp.quality_reports.all():
                                disp_type = disp.disposition_type
                                break
                        defects_found.append({
                            'error_type_id': error.id if hasattr(error, 'id') else None,
                            'error_name': error.error_name if hasattr(error, 'error_name') else str(error),
                            'severity': getattr(error, 'severity', None),
                            'disposition': disp_type
                        })

            # Build materials list
            materials_used = []
            for mu in step_materials:
                material_name = mu.lot.material_type if mu.lot and hasattr(mu.lot, 'material_type') else 'Unknown'
                lot_number = mu.lot.lot_number if mu.lot else None
                materials_used.append({
                    'material_name': material_name,
                    'lot_number': lot_number,
                    'quantity': mu.qty_consumed
                })

            # Build attachments list
            attachments = []
            for doc in step_attachments:
                attachments.append({
                    'id': doc.id,
                    'file_name': doc.file_name,
                    'file_url': doc.file.url if doc.file else '',
                    'uploaded_at': doc.upload_date,
                    'classification': doc.classification
                })

            traveler.append({
                'step_id': step_id,
                'step_name': step.name,
                'step_order': order,
                'visit_number': visit_number,
                'status': step_status,
                'started_at': started_at,
                'completed_at': completed_at,
                'duration_seconds': duration_seconds,
                'operator': operator,
                'approved_by': approved_by,
                'equipment_used': equipment_used,
                'measurements': measurements,
                'quality_status': quality_status,
                'defects_found': defects_found,
                'materials_used': materials_used,
                'attachments': attachments,
            })

        return Response({
            'part_id': part.id,
            'part_erp_id': part.ERP_id,
            'work_order_id': work_order.id if work_order else None,
            'process_name': process.name if process else None,
            'current_step_id': part.step_id,
            'current_step_name': part.step.name if part.step else None,
            'part_status': part.part_status,
            'traveler': traveler
        })


class OrdersViewSet(TenantScopedMixin, ListMetadataMixin, CSVImportMixin, DataExportMixin, viewsets.ModelViewSet):
    """
    Orders CRUD with CSV import/export support.

    Import/Export endpoints (auto-configured from model):
    - GET /import-template/ - Download import template (CSV or Excel)
    - POST /import/ - Import data from CSV/Excel file
    - GET /export/ - Export filtered data to CSV/Excel
    """
    queryset = Orders.objects.all()
    serializer_class = OrdersSerializer
    pagination_class = LimitOffsetPagination

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = OrderFilter
    ordering_fields = ["created_at", "order_status", "name", "estimated_completion"]
    ordering = ["-created_at"]
    search_fields = ["name", "company__name", "customer__first_name", "customer__last_name"]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Orders.objects.none()

        # TenantScopedMixin.get_queryset() handles tenant scoping and for_user() filtering
        # (including archived filtering based on ?include_archived param)
        qs = super().get_queryset()
        return qs.select_related('customer', 'company')

    def get_filter_backends(self):
        # disable filters for specific actions
        if self.action == "step_distribution":
            return []
        return super().get_filter_backends()

    @extend_schema(parameters=[
        OpenApiParameter(name='archived', location=OpenApiParameter.QUERY, exclude=True),
        OpenApiParameter(name='company', location=OpenApiParameter.QUERY, exclude=True),
        OpenApiParameter(name='created_at__gte', location=OpenApiParameter.QUERY, exclude=True),
        OpenApiParameter(name='created_at__lte', location=OpenApiParameter.QUERY, exclude=True),
        OpenApiParameter(name='customer', location=OpenApiParameter.QUERY, exclude=True),
        OpenApiParameter(name='estimated_completion__gte', location=OpenApiParameter.QUERY, exclude=True),
        OpenApiParameter(name='estimated_completion__lte', location=OpenApiParameter.QUERY, exclude=True),
        OpenApiParameter(name='ordering', location=OpenApiParameter.QUERY, exclude=True),
        OpenApiParameter(name='status', location=OpenApiParameter.QUERY, exclude=True),
        OpenApiParameter(name='limit', location=OpenApiParameter.QUERY, required=False, type=int),
        OpenApiParameter(name='offset', location=OpenApiParameter.QUERY, required=False, type=int), ],
        responses=inline_serializer(name="StepDistributionResponse",
                                    fields={"id": serializers.UUIDField(), "count": serializers.IntegerField(),
                                            "name": serializers.CharField(), }, many=True))
    @action(detail=True, methods=['get'], url_path='step-distribution')
    def step_distribution(self, request, pk=None):
        order = self.get_object()
        # Use model method instead of manual logic
        result = order.get_step_distribution()
        paginated = self.paginate_queryset(result)
        return self.get_paginated_response(paginated)

    @extend_schema(request=inline_serializer(name="StepIncrementInput", fields={"step_id": serializers.UUIDField()}),
                   responses=inline_serializer(name="StepIncrementResponse",
                                               fields={"advanced": serializers.IntegerField(),
                                                       "total": serializers.IntegerField()}))
    @action(detail=True, methods=['post'], url_path='increment-step')
    def increment_parts_step(self, request, pk=None):
        step_id = request.data.get("step_id")

        if not step_id:
            return Response({"detail": "Missing step_id"}, status=status.HTTP_400_BAD_REQUEST)

        order = self.get_object()

        # Use model method for bulk step advancement
        serializer = BulkStepAdvancementSerializer(data={"step_id": step_id})
        serializer.is_valid(raise_exception=True)

        try:
            result = order.bulk_increment_parts_at_step(step_id)
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(request=inline_serializer(name="BulkRemovePartsInput", fields={"ids": serializers.ListField(child=serializers.UUIDField())}),
                   responses={200: dict})
    @action(detail=True, methods=['post'], url_path='parts/bulk-remove')
    def bulk_remove_parts(self, request, pk=None):
        from Tracker.serializers import BulkSoftDeleteSerializer
        serializer = BulkSoftDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order = self.get_object()
        # Use model method for bulk removal
        result = order.bulk_remove_parts(serializer.validated_data['ids'])
        return Response(result, status=status.HTTP_200_OK)

    @extend_schema(request=inline_serializer(name="BulkAddPartsInput", fields={
        "part_type": serializers.PrimaryKeyRelatedField(queryset=PartTypes.objects.all()),
        "step": serializers.PrimaryKeyRelatedField(queryset=Steps.objects.all()),
        "quantity": serializers.IntegerField(),
        "part_status": serializers.ChoiceField(choices=PartsStatus.choices, default=PartsStatus.PENDING),
        "work_order": serializers.PrimaryKeyRelatedField(queryset=WorkOrder.objects.all(), required=False),
        "erp_id_start": serializers.IntegerField(default=1)}), responses={201: dict})
    @action(detail=True, methods=["post"], url_path="parts/bulk-add")
    def bulk_add_parts(self, request, pk=None):
        order = self.get_object()

        # Validate input data
        part_type_id = request.data.get('part_type')
        step_id = request.data.get('step')
        quantity = request.data.get('quantity')
        part_status = request.data.get('part_status', PartsStatus.PENDING)
        work_order_id = request.data.get('work_order')
        erp_id_start = request.data.get('erp_id_start', 1)

        if not all([part_type_id, step_id, quantity]):
            return Response({"detail": "Missing required fields: part_type, step, quantity"},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            part_type = PartTypes.objects.get(id=part_type_id)
            step = Steps.objects.get(id=step_id)
            work_order = WorkOrder.objects.get(id=work_order_id) if work_order_id else None

            # Use model method for bulk creation
            result = order.bulk_add_parts(part_type=part_type, step=step, quantity=int(quantity),
                                          part_status=part_status, work_order=work_order,
                                          erp_id_start=int(erp_id_start))
            return Response(result, status=status.HTTP_201_CREATED)

        except (PartTypes.DoesNotExist, Steps.DoesNotExist, WorkOrder.DoesNotExist) as e:
            return Response({"detail": f"Invalid reference: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        request=inline_serializer(
            name="AddNoteInput",
            fields={
                "message": serializers.CharField(),
                "visibility": serializers.ChoiceField(choices=['visible', 'internal'], default='visible')
            }
        ),
        responses={200: OrdersSerializer}
    )
    @action(detail=True, methods=['post'], url_path='add-note')
    def add_note(self, request, pk=None):
        """Add a note to the order timeline."""
        order = self.get_object()

        message = request.data.get('message')
        visibility = request.data.get('visibility', 'visible')

        if not message:
            return Response({"detail": "Message is required"}, status=status.HTTP_400_BAD_REQUEST)

        if visibility not in ('visible', 'internal'):
            return Response({"detail": "Visibility must be 'visible' or 'internal'"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order.add_note(request.user, message, visibility)
            order.save()
            return Response(OrdersSerializer(order, context={'request': request}).data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ===== WORK ORDER VIEWSETS =====

class WorkOrderViewSet(TenantScopedMixin, ListMetadataMixin, CSVImportMixin, DataExportMixin, viewsets.ModelViewSet):
    """
    Work Orders CRUD with CSV import/export support.

    Import/Export endpoints (auto-configured from model):
    - GET /import-template/ - Download import template (CSV or Excel)
    - POST /import/ - Import data from CSV/Excel file (small files immediate, large files queued)
    - GET /import-status/{task_id}/ - Check status of background import
    - GET /export/ - Export filtered data to CSV/Excel
    """
    queryset = WorkOrder.objects.all()
    serializer_class = WorkOrderSerializer
    pagination_class = LimitOffsetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ["related_order", "workorder_status", "priority", "process"]
    ordering_fields = ["created_at", "expected_completion", "ERP_id", "workorder_status", "priority"]
    ordering = ["ERP_id"]
    search_fields = ["ERP_id", "related_order__name", "notes"]

    # Custom field mapping for legacy Excel headers
    csv_field_mapping = {
        "item": "part_type_erp_id",
        "wo_number": "ERP_id",
        "wo number": "ERP_id",
    }

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return WorkOrder.objects.none()

        # Apply tenant scoping first, then user filtering
        qs = super().get_queryset()

        # Optimize for list view - select related order, customer, company to avoid N+1
        if self.action == 'list':
            qs = qs.select_related(
                'related_order',
                'related_order__customer',
                'related_order__company'
            )

        return qs

    def get_serializer_class(self):
        """Use lightweight serializer for list, full serializer for detail/create/update."""
        if self.action == 'list':
            return WorkOrderListSerializer
        return WorkOrderSerializer

    @action(detail=True, methods=['get'])
    def qa_summary(self, request, pk=None):
        """Get QA summary for work order including batch status"""
        work_order = self.get_object()

        parts = work_order.parts.all()
        parts_needing_qa = parts.filter(requires_sampling=True,
                                        part_status__in=['PENDING', 'IN_PROGRESS', 'AWAITING_QA'])

        return Response({'work_order': self.get_serializer(work_order).data,
                         'is_batch_work_order': work_order.parts.filter(
                             part_type__processes__is_batch_process=True).exists(),
                         'parts_summary': {'total': parts.count(), 'needing_qa': parts_needing_qa.count(),
                                           'completed': parts.filter(part_status='COMPLETED').count(),
                                           'quarantined': parts.filter(part_status='QUARANTINED').count(),
                                           'in_progress': parts.filter(part_status='IN_PROGRESS').count()},
                         'parts_needing_qa': PartsSerializer(parts_needing_qa, many=True,
                                                             context={'request': request}).data})

    @extend_schema(
        responses={
            200: inline_serializer(
                name='QADocumentsResponse',
                fields={
                    'work_order_documents': serializers.ListSerializer(child=serializers.DictField()),
                    'current_step_documents': serializers.ListSerializer(child=serializers.DictField()),
                    'part_type_documents': serializers.ListSerializer(child=serializers.DictField()),
                    'current_step_id': serializers.UUIDField(allow_null=True),
                    'parts_in_qa': serializers.IntegerField(),
                }
            )
        }
    )
    @action(detail=True, methods=['get'])
    def qa_documents(self, request, pk=None):
        """Get documents relevant to QA for this work order"""
        work_order = self.get_object()

        # Get parts needing QA to determine current steps
        parts_needing_qa = work_order.parts.filter(requires_sampling=True,
                                                   part_status__in=['PENDING', 'IN_PROGRESS', 'AWAITING_QA',
                                                                    'REWORK_NEEDED',
                                                                    'REWORK_IN_PROGRESS']).select_related('step',
                                                                                                          'part_type')

        if not parts_needing_qa.exists():
            return Response({'work_order_documents': [], 'current_step_documents': [], 'part_type_documents': [],
                             'current_step_id': None})

        # Determine the most common step (current step)
        step_counts = Counter(part.step.id for part in parts_needing_qa if part.step)
        current_step_id = step_counts.most_common(1)[0][0] if step_counts else None
        current_step = None
        if current_step_id:
            current_step = parts_needing_qa.filter(step_id=current_step_id).first().step

        # Get part type (should be same for all parts in work order)
        part_type = parts_needing_qa.first().part_type if parts_needing_qa.exists() else None

        # Get content types
        work_order_ct = ContentType.objects.get_for_model(WorkOrder)
        step_ct = ContentType.objects.get_for_model(Steps) if current_step else None
        part_type_ct = ContentType.objects.get_for_model(PartTypes) if part_type else None

        # Get documents (filtered by user permissions)
        work_order_docs = Documents.objects.for_user(request.user).filter(
            content_type=work_order_ct,
            object_id=str(work_order.id)
        )

        current_step_docs = Documents.objects.none()
        if step_ct and current_step:
            current_step_docs = Documents.objects.for_user(request.user).filter(
                content_type=step_ct,
                object_id=str(current_step.id)
            )

        part_type_docs = Documents.objects.none()
        if part_type_ct and part_type:
            part_type_docs = Documents.objects.for_user(request.user).filter(
                content_type=part_type_ct,
                object_id=str(part_type.id)
            )

        # Serialize documents
        document_serializer = DocumentsSerializer

        return Response(
            {'work_order_documents': document_serializer(work_order_docs, many=True, context={'request': request}).data,
             'current_step_documents': document_serializer(current_step_docs, many=True,
                                                           context={'request': request}).data,
             'part_type_documents': document_serializer(part_type_docs, many=True, context={'request': request}).data,
             'current_step_id': current_step_id, 'parts_in_qa': parts_needing_qa.count()})

    @extend_schema(
        responses={200: WorkOrderStepHistoryResponseSerializer},
        description="Get step history summary for digital traveler display"
    )
    @action(detail=True, methods=['get'])
    def step_history(self, request, pk=None):
        """
        GET /api/WorkOrders/{id}/step_history/

        Returns lightweight step-level aggregates for the work order's process.
        Use /api/Parts/{id}/traveler/ for detailed part-level history.
        """
        from Tracker.models import (
            ProcessStep, QualityReports, MeasurementResult,
            EquipmentUsage, MaterialUsage, Documents, StepExecution, TimeEntry
        )
        from django.contrib.contenttypes.models import ContentType
        from django.db.models import Count, Min, Max, Q

        work_order = self.get_object()

        # Get process and ordered steps
        process = work_order.process
        if not process:
            return Response({
                'work_order_id': work_order.id,
                'process_name': None,
                'total_parts': work_order.parts.count(),
                'step_history': []
            })

        # Get ordered steps for this process
        process_steps = ProcessStep.objects.filter(
            process=process
        ).select_related('step').order_by('order')

        # Build step order map
        ordered_steps = [(ps.step, ps.order) for ps in process_steps]

        # Get all parts for this work order
        parts = work_order.parts.all()
        total_parts = parts.count()

        # Get step IDs
        step_ids = [step.id for step, _ in ordered_steps]

        # Aggregate parts at each step
        parts_by_step = {}
        completed_by_step = {}
        for part in parts:
            if part.step_id:
                parts_by_step[part.step_id] = parts_by_step.get(part.step_id, 0) + 1
            if part.part_status == 'COMPLETED':
                # Completed parts count toward all steps they passed
                completed_by_step['__completed__'] = completed_by_step.get('__completed__', 0) + 1

        # Get step executions for timing data
        executions = StepExecution.objects.filter(
            part__work_order=work_order,
            step_id__in=step_ids
        ).values('step_id').annotate(
            first_entered=Min('entered_at'),
            last_exited=Max('exited_at'),
        )
        execution_map = {e['step_id']: e for e in executions}

        # Get time entries for operator info
        time_entries = TimeEntry.objects.filter(
            work_order=work_order,
            step_id__in=step_ids
        ).select_related('user').order_by('start_time')
        operator_by_step = {}
        for te in time_entries:
            if te.step_id and te.step_id not in operator_by_step and te.user:
                operator_by_step[te.step_id] = te.user.get_full_name() or te.user.username

        # Get quality reports aggregated by step
        qr_stats = QualityReports.objects.filter(
            part__work_order=work_order,
            step_id__in=step_ids
        ).values('step_id').annotate(
            total=Count('id'),
            passed=Count('id', filter=Q(status='PASS')),
            failed=Count('id', filter=Q(status='FAIL')),
        )
        qr_map = {q['step_id']: q for q in qr_stats}

        # Get measurement counts by step
        measurement_counts = MeasurementResult.objects.filter(
            report__part__work_order=work_order,
            report__step_id__in=step_ids
        ).values('report__step_id').annotate(count=Count('id'))
        measurement_map = {m['report__step_id']: m['count'] for m in measurement_counts}

        # Get defect counts (from quality reports with FAIL status)
        defect_counts = QualityReports.objects.filter(
            part__work_order=work_order,
            step_id__in=step_ids,
            status='FAIL'
        ).values('step_id').annotate(count=Count('errors'))
        defect_map = {d['step_id']: d['count'] for d in defect_counts}

        # Get attachment counts
        step_ct = ContentType.objects.get_for_model(Steps)
        attachment_counts = Documents.objects.filter(
            content_type=step_ct,
            object_id__in=[str(s) for s in step_ids]
        ).values('object_id').annotate(count=Count('id'))
        attachment_map = {a['object_id']: a['count'] for a in attachment_counts}

        # Determine max step order reached by any part
        max_order_reached = -1
        for part in parts:
            if part.part_status == 'COMPLETED':
                max_order_reached = max(max_order_reached, len(ordered_steps))
            elif part.step_id:
                for step, order in ordered_steps:
                    if step.id == part.step_id:
                        max_order_reached = max(max_order_reached, order)
                        break

        # Build step history
        step_history = []
        for step, order in ordered_steps:
            step_id = step.id
            parts_at = parts_by_step.get(step_id, 0)
            exec_data = execution_map.get(step_id, {})
            qr_data = qr_map.get(step_id, {})

            # Determine status
            if parts_at > 0:
                step_status = 'IN_PROGRESS'
            elif order < max_order_reached:
                step_status = 'COMPLETED'
            else:
                step_status = 'PENDING'

            # Determine quality status
            quality_status = None
            if qr_data:
                if qr_data.get('failed', 0) > 0:
                    quality_status = 'FAIL'
                elif qr_data.get('passed', 0) > 0:
                    quality_status = 'PASS'

            # Calculate duration
            started_at = exec_data.get('first_entered')
            completed_at = exec_data.get('last_exited')
            duration_seconds = None
            if started_at and completed_at:
                duration_seconds = int((completed_at - started_at).total_seconds())

            step_history.append({
                'step_id': step_id,
                'step_name': step.name,
                'step_order': order,
                'status': step_status,
                'started_at': started_at,
                'completed_at': completed_at,
                'duration_seconds': duration_seconds,
                'operator_name': operator_by_step.get(step_id),
                'quality_status': quality_status,
                'parts_at_step': parts_at,
                'parts_completed': completed_by_step.get('__completed__', 0) if step_status == 'COMPLETED' else 0,
                'measurement_count': measurement_map.get(step_id, 0),
                'defect_count': defect_map.get(step_id, 0),
                'attachment_count': attachment_map.get(str(step_id), 0),
            })

        return Response({
            'work_order_id': work_order.id,
            'process_name': process.name if process else None,
            'total_parts': total_parts,
            'step_history': step_history
        })


# ===== STEPS & PROCESS VIEWSETS =====

@extend_schema(parameters=[
    OpenApiParameter(name="process", type=str, location=OpenApiParameter.QUERY, required=False,
                     description="Filter steps by process UUID (via ProcessStep)"),
    OpenApiParameter(name="part_type", type=str, location=OpenApiParameter.QUERY, required=False,
                     description="Filter steps by process's part type UUID"), ])
class StepsViewSet(TenantScopedMixin, ListMetadataMixin, ExcelExportMixin, viewsets.ModelViewSet):
    queryset = Steps.objects.all()
    serializer_class = StepsSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    # Steps are now linked to processes via ProcessStep junction table
    filterset_fields = {
        "process_memberships__process": ["exact"],
        "process_memberships__process__part_type": ["exact"],
        "part_type": ["exact"],
    }
    search_fields = ["part_type__name", "name"]
    ordering_fields = ["part_type__name", "name"]
    ordering = ["name"]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Steps.objects.none()

        # Apply tenant scoping first, then user filtering
        qs = super().get_queryset()
        return qs.select_related(
            'part_type'
        ).prefetch_related('process_memberships__process')

    @extend_schema(request=StepSamplingRulesUpdateSerializer, responses={
        200: StepsSerializer},
                   methods=["POST"], description="Update or create a sampling rule set for this step")
    @action(detail=True, methods=["post"])
    def update_sampling_rules(self, request, pk=None):
        """
        POST /steps/:id/update_sampling_rules/
        Body:
        {
            "rules": [...],
            "fallback_rules": [...],
            "fallback_threshold": 2,
            "fallback_duration": 5
        }
        """
        step = self.get_object()
        serializer = StepSamplingRulesUpdateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        # Use serializer method that calls model method
        serializer.update_step_rules(step)

        # Refresh and return the updated step
        step.refresh_from_db()
        return Response(StepsSerializer(step, context={"request": request}).data)

    @action(detail=True, methods=["get"])
    def resolved_rules(self, request, pk=None):
        """
        GET /steps/:id/resolved_rules/
        Returns the active + fallback rulesets for a given step
        """
        step = self.get_object()
        # Use StepWithResolvedRulesSerializer which returns active_ruleset and fallback_ruleset at top level
        from ..serializers.qms import StepWithResolvedRulesSerializer
        serializer = StepWithResolvedRulesSerializer(step, context={'request': request})
        return Response(serializer.data)


# ===== STEP EXECUTION VIEWSET =====

class StepExecutionViewSet(TenantScopedMixin, ListMetadataMixin, viewsets.ModelViewSet):
    """
    ViewSet for step execution tracking (workflow engine).

    Provides:
    - CRUD for step executions
    - WIP queries (work in progress)
    - Operator workload tracking
    - Step history for parts

    Used by the workflow engine for tracking part progression through steps.
    """
    queryset = StepExecution.objects.all()
    serializer_class = StepExecutionSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'part': ['exact'],
        'step': ['exact'],
        'step__process_memberships__process': ['exact'],  # Steps are now linked via ProcessStep
        'status': ['exact', 'in'],
        'assigned_to': ['exact', 'isnull'],
        'visit_number': ['exact', 'gte', 'lte'],
    }
    search_fields = ['part__ERP_id', 'step__name']
    ordering_fields = ['entered_at', 'exited_at', 'visit_number', 'status']
    ordering = ['-entered_at']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return StepExecution.objects.none()

        # Apply tenant scoping first, then user filtering
        qs = super().get_queryset()
        return qs.select_related(
            'part', 'part__part_type', 'step', 'step__part_type',
            'assigned_to', 'completed_by', 'next_step'
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return StepExecutionListSerializer
        return StepExecutionSerializer

    @extend_schema(
        responses={200: WIPSummarySerializer(many=True)},
        description="Get WIP summary grouped by step for a process"
    )
    @action(detail=False, methods=['get'])
    def wip_summary(self, request):
        """
        GET /step-executions/wip_summary/?process=1

        Returns WIP counts grouped by step for monitoring dashboards.
        Shows how many parts are pending vs in-progress at each step.
        """
        from django.db.models import Count, Q

        process_id = request.query_params.get('process')
        if not process_id:
            return Response(
                {"detail": "process query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get steps via ProcessStep junction table with execution counts
        process_steps = ProcessStep.objects.filter(
            process_id=process_id
        ).select_related('step').annotate(
            pending_count=Count(
                'step__executions',
                filter=Q(step__executions__status='pending', step__executions__exited_at__isnull=True)
            ),
            in_progress_count=Count(
                'step__executions',
                filter=Q(step__executions__status='in_progress', step__executions__exited_at__isnull=True)
            ),
        ).order_by('order')

        result = []
        for ps in process_steps:
            result.append({
                'step_id': ps.step.id,
                'step_name': ps.step.name,
                'step_order': ps.order,
                'is_decision_point': ps.step.is_decision_point,
                'pending_count': ps.pending_count,
                'in_progress_count': ps.in_progress_count,
                'total_active': ps.pending_count + ps.in_progress_count,
            })

        serializer = WIPSummarySerializer(result, many=True)
        return Response(serializer.data)

    @extend_schema(
        responses={200: StepExecutionListSerializer(many=True)},
        description="Get all active WIP at a specific step"
    )
    @action(detail=False, methods=['get'])
    def wip_at_step(self, request):
        """
        GET /step-executions/wip_at_step/?step=1

        Returns all parts currently at a specific step.
        Useful for step-level work queues.
        """
        step_id = request.query_params.get('step')
        if not step_id:
            return Response(
                {"detail": "step query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        queryset = self.get_queryset().filter(
            step_id=step_id,
            exited_at__isnull=True,
            status__in=['pending', 'in_progress']
        )

        serializer = StepExecutionListSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        responses={200: StepExecutionListSerializer(many=True)},
        description="Get current operator's assigned work"
    )
    @action(detail=False, methods=['get'])
    def my_workload(self, request):
        """
        GET /step-executions/my_workload/

        Returns all active step executions assigned to the current user.
        Used for operator work queue / inbox.
        """
        queryset = self.get_queryset().filter(
            assigned_to=request.user,
            exited_at__isnull=True,
            status__in=['pending', 'in_progress']
        ).order_by('entered_at')

        serializer = StepExecutionListSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        responses={200: StepExecutionSerializer(many=True)},
        description="Get visit history for a part at a specific step"
    )
    @action(detail=False, methods=['get'])
    def part_step_history(self, request):
        """
        GET /step-executions/part_step_history/?part=1&step=2

        Returns all visits for a part at a specific step.
        Useful for tracking rework cycles.
        """
        part_id = request.query_params.get('part')
        step_id = request.query_params.get('step')

        if not part_id:
            return Response(
                {"detail": "part query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        queryset = self.get_queryset().filter(part_id=part_id)
        if step_id:
            queryset = queryset.filter(step_id=step_id)

        queryset = queryset.order_by('entered_at')
        serializer = StepExecutionSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        request=inline_serializer(
            name="ClaimStepInput",
            fields={}
        ),
        responses={200: StepExecutionSerializer}
    )
    @action(detail=True, methods=['post'])
    def claim(self, request, pk=None):
        """
        POST /step-executions/{id}/claim/

        Operator claims a pending step execution.
        Sets assigned_to to current user and status to in_progress.
        """
        execution = self.get_object()

        if execution.status == 'completed':
            return Response(
                {"detail": "Cannot claim a completed execution"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if execution.assigned_to and execution.assigned_to != request.user:
            return Response(
                {"detail": "Already assigned to another operator"},
                status=status.HTTP_400_BAD_REQUEST
            )

        execution.assigned_to = request.user
        execution.status = 'in_progress'
        execution.save()

        serializer = StepExecutionSerializer(execution)
        return Response(serializer.data)

    @extend_schema(
        responses={200: inline_serializer(
            name="StepDurationStats",
            fields={
                'step_id': serializers.UUIDField(),
                'step_name': serializers.CharField(),
                'avg_duration_seconds': serializers.FloatField(),
                'min_duration_seconds': serializers.FloatField(),
                'max_duration_seconds': serializers.FloatField(),
                'completed_count': serializers.IntegerField(),
            }
        )},
        description="Get duration statistics for steps in a process"
    )
    @action(detail=False, methods=['get'])
    def duration_stats(self, request):
        """
        GET /step-executions/duration_stats/?process=1

        Returns duration statistics for completed step executions.
        Useful for process optimization and capacity planning.
        """
        from django.db.models import Avg, Min, Max, Count, F, ExpressionWrapper, DurationField

        process_id = request.query_params.get('process')
        if not process_id:
            return Response(
                {"detail": "process query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        stats = StepExecution.objects.filter(
            step__process_memberships__process_id=process_id,
            status='completed',
            exited_at__isnull=False
        ).values(
            'step__id', 'step__name'
        ).annotate(
            duration=ExpressionWrapper(
                F('exited_at') - F('entered_at'),
                output_field=DurationField()
            )
        ).values(
            'step__id', 'step__name'
        ).annotate(
            avg_duration=Avg(F('exited_at') - F('entered_at')),
            min_duration=Min(F('exited_at') - F('entered_at')),
            max_duration=Max(F('exited_at') - F('entered_at')),
            completed_count=Count('id'),
        ).order_by('step__id')

        result = []
        for s in stats:
            result.append({
                'step_id': s['step__id'],
                'step_name': s['step__name'],
                'avg_duration_seconds': s['avg_duration'].total_seconds() if s['avg_duration'] else None,
                'min_duration_seconds': s['min_duration'].total_seconds() if s['min_duration'] else None,
                'max_duration_seconds': s['max_duration'].total_seconds() if s['max_duration'] else None,
                'completed_count': s['completed_count'],
            })

        return Response(result)


class ProcessViewSet(TenantScopedMixin, ListMetadataMixin, ExcelExportMixin, viewsets.ModelViewSet):
    queryset = Processes.objects.all()
    serializer_class = ProcessesSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["part_type", "status"]
    search_fields = ["name", "part_type__name"]
    ordering_fields = ["created_at", "updated_at", "name", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Processes.objects.none()

        # Apply tenant scoping first, then user filtering
        qs = super().get_queryset()
        return qs.select_related("part_type").prefetch_related("process_steps__step")


@extend_schema(parameters=[
    OpenApiParameter(name="part_type", type=str, location=OpenApiParameter.QUERY, required=False,
                     description="Filter processes by associated part type UUID"), ])
class PartTypeViewSet(TenantScopedMixin, ListMetadataMixin, CSVImportMixin, DataExportMixin, viewsets.ModelViewSet):
    """
    Part Types CRUD with CSV import/export support.

    Import/Export endpoints (auto-configured from model):
    - GET /import-template/ - Download import template (CSV or Excel)
    - POST /import/ - Import data from CSV/Excel file
    - GET /export/ - Export filtered data to CSV/Excel
    """
    queryset = PartTypes.objects.all()
    serializer_class = PartTypesSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, OrderingFilter]
    ordering_fields = ['created_at', 'name', 'updated_at', 'ID_prefix']
    ordering = ['-created_at']
    search_fields = ["name", "ID_prefix"]
    filterset_fields = ['name']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return PartTypes.objects.none()

        # Apply tenant scoping first, then user filtering
        qs = super().get_queryset()
        return qs

    @extend_schema(
        description="Lightweight endpoint for dropdown/combobox selections",
        responses={200: PartTypeSelectSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def select(self, request):
        """Return lightweight part type data for dropdown selections."""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = PartTypeSelectSerializer(queryset, many=True)
        return Response(serializer.data)


class ProcessWithStepsViewSet(TenantScopedMixin, ExcelExportMixin, viewsets.ModelViewSet):
    queryset = Processes.objects.all()
    serializer_class = ProcessWithStepsSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["part_type", "status"]
    search_fields = ["name"]
    ordering_fields = ["created_at", "name", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Processes.objects.none()

        # Apply tenant scoping first, then user filtering
        qs = super().get_queryset()
        return qs.prefetch_related("process_steps__step__sampling_ruleset__rules")

    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            return super().update(request, *args, **kwargs)

    # ===== APPROVAL & DUPLICATION ACTIONS =====

    @extend_schema(
        description="List all approved processes available for work orders",
        parameters=[
            OpenApiParameter(name='part_type', type=OpenApiTypes.INT, description='Filter by part type ID')
        ],
        responses={200: ProcessWithStepsSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def available(self, request):
        """Get all approved processes available for new work orders."""
        queryset = self.get_queryset().filter(status=ProcessStatus.APPROVED)

        # Optional filter by part_type
        part_type_id = request.query_params.get('part_type')
        if part_type_id:
            queryset = queryset.filter(part_type_id=part_type_id)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        description="Submit a draft process for formal approval workflow. Creates an ApprovalRequest that must be approved before the process can be used.",
        request=inline_serializer(
            name='SubmitProcessForApprovalRequest',
            fields={'reason': serializers.CharField(required=False, help_text='Optional reason for approval request')}
        ),
        responses={200: inline_serializer(
            name='SubmitProcessForApprovalResponse',
            fields={
                'process': ProcessWithStepsSerializer(),
                'approval_request_id': serializers.UUIDField(),
                'approval_number': serializers.CharField(),
            }
        )}
    )
    @action(detail=True, methods=['post'])
    def submit_for_approval(self, request, pk=None):
        """Submit a draft process for formal approval workflow."""
        process = self.get_object()

        try:
            approval_request = process.submit_for_approval(user=request.user)
            serializer = self.get_serializer(process)
            return Response({
                'process': serializer.data,
                'approval_request_id': approval_request.id,
                'approval_number': approval_request.approval_number,
            })
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        description="Directly approve a draft process for production use (bypasses formal approval workflow). Once approved, the process cannot be modified.",
        request=None,
        responses={200: ProcessWithStepsSerializer}
    )
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Directly approve a draft process, making it available for work orders (bypasses approval workflow)."""
        process = self.get_object()

        try:
            process.approve(user=request.user)
            serializer = self.get_serializer(process)
            return Response(serializer.data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        description="Mark an approved process as deprecated. It can still be used by existing work orders but won't appear for new ones.",
        request=None,
        responses={200: ProcessWithStepsSerializer}
    )
    @action(detail=True, methods=['post'])
    def deprecate(self, request, pk=None):
        """Deprecate a process."""
        process = self.get_object()

        try:
            process.deprecate()
            serializer = self.get_serializer(process)
            return Response(serializer.data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        description="Create a copy of this process for customization. The copy starts as DRAFT.",
        request=inline_serializer(
            name='DuplicateProcessRequest',
            fields={'name_suffix': serializers.CharField(default=' (Copy)', required=False)}
        ),
        responses={201: ProcessWithStepsSerializer}
    )
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Create a copy of this process for customization."""
        process = self.get_object()
        name_suffix = request.data.get('name_suffix', ' (Copy)')

        try:
            new_process = process.duplicate(user=request.user, name_suffix=name_suffix)
            serializer = self.get_serializer(new_process)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ===== EQUIPMENT VIEWSETS =====

class EquipmentSelectViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Equipments.objects.all()
    serializer_class = EquipmentsSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Equipments.objects.none()

        # Apply tenant scoping first, then user filtering
        qs = super().get_queryset()
        return qs


class EquipmentViewSet(TenantScopedMixin, ListMetadataMixin, ExcelExportMixin, viewsets.ModelViewSet):
    queryset = Equipments.objects.all()
    serializer_class = EquipmentsSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ["equipment_type", "status", "location"]
    ordering_fields = ["name", "equipment_type__name", "serial_number", "status", "location", "updated_at", "created_at"]
    ordering = ["name"]  # Alphabetical by default
    search_fields = ["name", "serial_number", "location"]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Equipments.objects.none()

        # Apply tenant scoping first, then user filtering
        qs = super().get_queryset()
        return qs.select_related('equipment_type')


class EquipmentTypeViewSet(TenantScopedMixin, ListMetadataMixin, ExcelExportMixin, viewsets.ModelViewSet):
    queryset = EquipmentType.objects.all()
    serializer_class = EquipmentTypeSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ["name"]
    ordering_fields = ["id", "name"]
    ordering = ["name"]
    search_fields = ["name"]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return EquipmentType.objects.none()

        # Apply tenant scoping first, then user filtering
        qs = super().get_queryset()
        return qs

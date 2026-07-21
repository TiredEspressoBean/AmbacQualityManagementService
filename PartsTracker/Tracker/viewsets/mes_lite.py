# viewsets/mes_lite.py - MES Lite ViewSets (Manufacturing, Orders, Parts, Processes, Equipment)
from collections import Counter

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
import django_filters
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema_view, extend_schema, inline_serializer, OpenApiParameter, OpenApiTypes
from rest_framework import viewsets, status, filters, serializers
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.generics import ListAPIView
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from Tracker.serializers.fields import TenantScopedPrimaryKeyRelatedField

from Tracker.filters import PartFilter, OrderFilter
from Tracker.models import (
    # MES Lite models
    Orders, Parts, PartsStatus, WorkOrder, WorkOrderStatus, Steps, PartTypes, Processes,
    StepExecution, ProcessStatus, OutsideProcessShipment,
    # MES Standard models
    Equipments, EquipmentType,
    # Core models
    Documents,
    # Milestone models
    MilestoneTemplate, Milestone,
)
from Tracker.serializers.mes_lite import (
    OrdersSerializer, CustomerOrderSerializer, PartsSerializer, PartSelectSerializer, CustomerPartsSerializer,
    WorkOrderSerializer, WorkOrderListSerializer,
    StepsSerializer, StepSerializer, PartTypesSerializer, PartTypeSelectSerializer, ProcessesSerializer,
    ProcessWithStepsSerializer, EquipmentsSerializer, EquipmentTypeSerializer,
    BulkAddPartsSerializer, BulkRemovePartsSerializer,
    StepAdvancementSerializer, BulkStepAdvancementSerializer,
    StepExecutionSerializer, StepExecutionListSerializer, WIPSummarySerializer,
    OutsideProcessShipmentSerializer, ReadyToShipGroupSerializer,
    # Digital Traveler serializers
    WorkOrderStepHistoryResponseSerializer, PartTravelerResponseSerializer,
)
from Tracker.serializers.qms import (
    StepSamplingRulesUpdateSerializer, StepWithResolvedRulesSerializer,
    QualityReportsSerializer, SamplePlanResponseSerializer,
)
from Tracker.services.mes import outside_process
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
    queryset = Orders.unscoped.all()
    serializer_class = CustomerOrderSerializer
    pagination_class = LimitOffsetPagination

    # Inviting a viewer is not order creation: without the exemption,
    # POST /invite/ would demand add_orders (POST → add_{model}), which
    # customers rightly lack. Gate on add_orderviewer instead — row scoping
    # is already enforced by get_object() over the for_user()-filtered
    # queryset, so customers can only invite to orders they can reach.
    crud_exempt_actions = {'invite_viewer'}
    action_permissions = {
        'invite_viewer': ['add_orderviewer'],
    }

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Orders.objects.none()

        # Apply tenant scoping first, then user filtering
        qs = super().get_queryset()
        return qs.select_related('current_milestone__template')

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
        from Tracker.models.core import UserInvitation
        from Tracker.services.core.user import add_user_to_tenant_group
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
            # Grant Customer role within tenant
            if request.user.tenant:
                add_user_to_tenant_group(
                    user, 'Customer', tenant=request.user.tenant, granted_by=request.user
                )
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
    # Class-level queryset for drf-spectacular introspection; real
    # filtering in get_queryset.
    queryset = Parts.all_tenants.none()
    serializer_class = PartsSerializer
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Parts.all_tenants.none()

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
    queryset = Parts.unscoped.all()
    serializer_class = PartsSerializer
    pagination_class = LimitOffsetPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter, filters.SearchFilter]
    filterset_class = PartFilter
    ordering_fields = ['created_at', 'ERP_id', 'part_status']
    ordering = ['-created_at']
    search_fields = ["ERP_id", "order__name", "work_order__ERP_id", "step__name", "part_type__name", "part_status", ]

    # 4a — resolving a MANUAL decision-point branch is manager/lead-gated, and
    # isn't "creating a part" (so it's CRUD-exempt; the action perm is the gate).
    crud_exempt_actions = {'resolve_decision'}
    action_permissions = {
        'resolve_decision': ['resolve_step_decision'],
    }

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
        responses={200: inline_serializer(
            name="DecisionOptionsResponse",
            fields={
                "is_decision_point": serializers.BooleanField(),
                "decision_type": serializers.CharField(required=False, allow_blank=True),
                "default_branch": serializers.DictField(required=False, allow_null=True),
                "alternate_branch": serializers.DictField(required=False, allow_null=True),
                "qa_suggested": serializers.CharField(required=False, allow_null=True),
            },
        )},
    )
    @action(detail=True, methods=["get"], url_path="decision_options")
    def decision_options(self, request, pk=None):
        """4a — decision-point metadata for the operator runtime resolver.

        Tells the runtime whether this part's current step is a decision
        point, its `decision_type`, and the resolved DEFAULT/ALTERNATE branch
        targets so it can label 'pass → X' / 'fail/rework → Y'. For QA_RESULT
        it also returns the QualityReport-suggested branch (those route
        automatically; no manual pick)."""
        from Tracker.models.mes_lite import EdgeType

        part = self.get_object()
        step = part.step
        if step is None or not step.is_decision_point:
            return Response({"is_decision_point": False})

        def branch(edge_type):
            to_step = part._get_edge(step, edge_type)
            return {"step_id": str(to_step.id), "step_name": to_step.name} if to_step else None

        qa_suggested = None
        if step.decision_type == 'QA_RESULT':
            from Tracker.models.qms import QualityReports
            qr = (
                QualityReports.objects.filter(part=part, step=step)
                .order_by('-created_at').first()
            )
            qa_suggested = qr.status if qr else None

        return Response({
            "is_decision_point": True,
            "decision_type": step.decision_type,
            "default_branch": branch(EdgeType.DEFAULT),
            "alternate_branch": branch(EdgeType.ALTERNATE),
            "qa_suggested": qa_suggested,
        })

    @extend_schema(
        responses={200: inline_serializer(
            name="ReworkStatusResponse",
            fields={
                "total_rework_count": serializers.IntegerField(),
                "current_step_name": serializers.CharField(allow_null=True),
                "max_visits": serializers.IntegerField(allow_null=True),
                "current_visits": serializers.IntegerField(),
                "remaining": serializers.IntegerField(allow_null=True),
                "at_limit": serializers.BooleanField(),
                "escalation_step_name": serializers.CharField(allow_null=True),
            },
        )},
    )
    @action(detail=True, methods=["get"], url_path="rework_status")
    def rework_status(self, request, pk=None):
        """4b — rework-cycle visibility.

        Reports the part's cumulative rework count and, when its current step
        carries a visit cap (`max_visits`), how many visits it's used, how many
        remain, and the ESCALATION target it routes to once the cap is exceeded
        (engine-driven — `_check_cycle_limit`)."""
        from Tracker.models import StepExecution
        from Tracker.models.mes_lite import EdgeType, StepEdge

        part = self.get_object()
        step = part.step
        max_visits = getattr(step, 'max_visits', None) if step else None
        current_visits = StepExecution.get_visit_count(part, step) if step else 0

        escalation_step_name = None
        if step and max_visits is not None:
            process = part.work_order.process if part.work_order else None
            if process:
                esc = StepEdge.objects.filter(
                    process=process, from_step=step, edge_type=EdgeType.ESCALATION,
                ).first()
                escalation_step_name = esc.to_step.name if esc and esc.to_step else None

        remaining = max(0, max_visits - current_visits) if max_visits is not None else None
        return Response({
            "total_rework_count": part.total_rework_count or 0,
            "current_step_name": step.name if step else None,
            "max_visits": max_visits,
            "current_visits": current_visits,
            "remaining": remaining,
            "at_limit": max_visits is not None and current_visits >= max_visits,
            "escalation_step_name": escalation_step_name,
        })

    @extend_schema(
        request=inline_serializer(
            name="ResolveDecisionInput",
            fields={"decision": serializers.CharField(
                help_text="Branch to route along: 'DEFAULT'/'PASS' or 'ALTERNATE'/'FAIL'."
            )},
        ),
        responses={200: dict},
    )
    @action(detail=True, methods=["post"], url_path="resolve_decision")
    def resolve_decision(self, request, pk=None):
        """4a — manager/lead resolves a MANUAL decision-point step by choosing
        the routing branch. Gated by `resolve_step_decision`. QA_RESULT points
        route automatically from the QualityReport and don't use this."""
        from django.core.exceptions import ValidationError as DjangoValidationError
        from Tracker.services.mes.parts import advance_part_step

        part = self.get_object()
        step = part.step
        if step is None or not step.is_decision_point:
            return Response(
                {"detail": "This step is not a decision point."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if step.decision_type != 'MANUAL':
            return Response(
                {"detail": "Only MANUAL decision points are resolved here; "
                           "QA_RESULT routes from the inspection result."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        decision = (request.data.get("decision") or "").upper()
        if decision not in ("DEFAULT", "ALTERNATE", "PASS", "FAIL"):
            return Response(
                {"detail": "decision must be 'DEFAULT'/'PASS' or 'ALTERNATE'/'FAIL'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            # The manual decision is authoritative — a manager/lead has explicitly
            # chosen the branch, so bypass the per-part advancement gate. Otherwise
            # the gate's pass-oriented checks (QA signoff, FPI) would paradoxically
            # block routing a FAILED part to its rework branch. The
            # `resolve_step_decision` permission is the control here.
            #
            # In a transaction so the visit-number lock advance_part_step takes
            # (get_visit_count_for_update) is held through the StepExecution insert.
            with transaction.atomic():
                result = advance_part_step(
                    part, operator=request.user, decision_result=decision, skip_gate_check=True,
                )
        except (ValueError, DjangoValidationError) as e:
            msg = "; ".join(e.messages) if isinstance(e, DjangoValidationError) else str(e)
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            "result": result,
            "new_step_id": str(part.step.id) if part.step else None,
            "new_step_name": part.step.name if part.step else None,
            "part_status": part.part_status,
        })

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
        request=inline_serializer(
            name="PartsBulkIncrementInput",
            fields={"ids": serializers.ListField(child=serializers.UUIDField())},
        ),
        responses={200: inline_serializer(
            name="BulkResultResponse",
            fields={"results": serializers.ListField(child=serializers.DictField())},
        )},
        description="Advance each listed part one step. Per-id errors captured.",
    )
    @action(detail=False, methods=["post"], url_path="bulk_increment")
    def bulk_increment(self, request):
        from Tracker.services.mes.parts import bulk_increment as svc
        ids = request.data.get("ids") or []
        if not isinstance(ids, list):
            return Response({"detail": "ids must be a list"}, status=status.HTTP_400_BAD_REQUEST)
        results = svc(tenant_id=self.tenant.id if self.tenant else None,
                      part_ids=ids, operator=request.user)
        return Response({"results": [r.to_dict() for r in results]})

    @extend_schema(
        request=inline_serializer(
            name="AdvanceLotInput",
            fields={
                "work_order_id": serializers.UUIDField(),
                "step_id": serializers.UUIDField(),
            },
        ),
        responses={200: inline_serializer(
            name="AdvanceLotResponse",
            fields={
                "status": serializers.CharField(),
                "reason": serializers.CharField(required=False, allow_blank=True),
                "parts_advanced": serializers.ListField(child=serializers.CharField()),
                "blockers_by_part": serializers.DictField(),
                "split_parts_advanced": serializers.ListField(child=serializers.CharField()),
                "split_parts_blocked": serializers.DictField(),
            },
        )},
    )
    @action(detail=False, methods=["post"], url_path="advance_lot")
    def advance_lot(self, request):
        """
        POST /api/Parts/advance_lot/

        Lot-cohesion advancement: evaluate every non-split part at
        (work_order_id, step_id) and advance them as a cohort when the
        gate clears for all of them. Split parts at the same (WO, Step)
        each advance independently when their own gate clears.

        Body: { "work_order_id": "<uuid>", "step_id": "<uuid>" }
        """
        from Tracker.services.mes.advancement import try_advance_lot
        wo_id = request.data.get("work_order_id")
        step_id = request.data.get("step_id")
        if not wo_id or not step_id:
            return Response(
                {"detail": "work_order_id and step_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        result = try_advance_lot(
            work_order_id=wo_id,
            step_id=step_id,
            tenant_id=self.tenant.id if self.tenant else None,
            operator=request.user,
        )
        return Response({
            "status": result.status,
            "reason": result.reason,
            "parts_advanced": result.parts_advanced,
            "blockers_by_part": result.blockers_by_part,
            "split_parts_advanced": result.split_parts_advanced,
            "split_parts_blocked": result.split_parts_blocked,
        })

    @extend_schema(
        request=None,
        responses={200: inline_serializer(
            name="CompleteStepResponse",
            fields={
                "status": serializers.CharField(),
                "reason": serializers.CharField(required=False, allow_blank=True),
                "parts_advanced": serializers.ListField(child=serializers.CharField()),
                "blockers_by_part": serializers.DictField(),
                "split_parts_advanced": serializers.ListField(child=serializers.CharField()),
                "split_parts_blocked": serializers.DictField(),
            },
        )},
    )
    @action(detail=True, methods=["post"], url_path="complete_step")
    def complete_step(self, request, pk=None):
        """
        POST /api/Parts/{id}/complete_step/

        Operator "I'm done with this step for this part" — THE canonical
        advancement trigger. Synchronously runs the gate via
        `try_advance_lot` for this part's (work_order, step) and returns
        the result inline.

        If this part's gate clears AND it's the last cohort sibling to
        clear, the whole cohort advances. If this part is split, it
        advances solo. Bounded synchronous cascade through pass-through
        steps walks forward in the same request.

        Response shape matches the advance_lot action — the operator
        sees parts_advanced / blockers_by_part / etc. in the same
        request that triggered the gate.
        """
        from Tracker.services.mes.advancement import try_advance_lot

        part = self.get_object()
        if not part.work_order_id or not part.step_id:
            return Response(
                {"detail": "Part has no work_order or step; can't advance."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = try_advance_lot(
            work_order_id=str(part.work_order_id),
            step_id=str(part.step_id),
            tenant_id=str(part.tenant_id),
            operator=request.user,
        )
        return Response({
            "status": result.status,
            "reason": result.reason,
            "parts_advanced": result.parts_advanced,
            "blockers_by_part": result.blockers_by_part,
            "split_parts_advanced": result.split_parts_advanced,
            "split_parts_blocked": result.split_parts_blocked,
        })

    @extend_schema(
        request=inline_serializer(
            name="PartsBulkRollbackInput",
            fields={
                "ids": serializers.ListField(child=serializers.UUIDField()),
                "reason": serializers.CharField(required=False, allow_blank=True),
                "override_id": serializers.UUIDField(required=False, allow_null=True),
            },
        ),
        responses={200: inline_serializer(
            name="BulkRollbackResponse",
            fields={"results": serializers.ListField(child=serializers.DictField())},
        )},
    )
    @action(detail=False, methods=["post"], url_path="bulk_rollback")
    def bulk_rollback(self, request):
        from Tracker.services.mes.parts import bulk_rollback as svc
        ids = request.data.get("ids") or []
        if not isinstance(ids, list):
            return Response({"detail": "ids must be a list"}, status=status.HTTP_400_BAD_REQUEST)
        # Elevated users may reverse parts out of a terminal status (e.g. un-scrap).
        # Placeholder gate; precise elevated-role policy (admins, QA/prod managers)
        # is deferred — see remediation plan 0d.
        allow_terminal_exit = bool(
            getattr(request.user, "is_superuser", False) or getattr(request.user, "is_staff", False)
        )
        results = svc(
            tenant_id=self.tenant.id if self.tenant else None,
            part_ids=ids,
            operator=request.user,
            reason=request.data.get("reason", "") or "",
            override_id=request.data.get("override_id"),
            allow_terminal_exit=allow_terminal_exit,
        )
        return Response({"results": [r.to_dict() for r in results]})

    @extend_schema(
        request=inline_serializer(
            name="PartsBulkSetStatusInput",
            fields={
                "ids": serializers.ListField(child=serializers.UUIDField()),
                "status": serializers.ChoiceField(choices=PartsStatus.choices),
                "reason": serializers.CharField(required=False, allow_blank=True),
            },
        ),
        responses={200: inline_serializer(
            name="BulkSetStatusResponse",
            fields={"results": serializers.ListField(child=serializers.DictField())},
        )},
    )
    @action(detail=True, methods=["post"], url_path="split_from_lot")
    def split_from_lot(self, request, pk=None):
        """
        POST /api/Parts/{id}/split_from_lot/

        Pull this part off its WorkOrder cohort so it advances solo.
        Quarantine, rework, expedite, customer-pull, and scrap all flow
        through this endpoint. Body:
            { "reason": "rework", "rework_target_step_id": "<uuid?>",
              "notes": "<optional>" }
        """
        from Tracker.services.mes.splits import split_part_from_lot
        from Tracker.models import Steps

        part = self.get_object()
        reason = request.data.get("reason")
        if not reason:
            return Response({"detail": "reason is required"},
                            status=status.HTTP_400_BAD_REQUEST)

        target_step = None
        target_id = request.data.get("rework_target_step_id")
        if target_id:
            target_step = Steps.objects.filter(id=target_id).first()
            if target_step is None:
                return Response({"detail": "rework_target_step_id not found"},
                                status=status.HTTP_400_BAD_REQUEST)

        try:
            result = split_part_from_lot(
                part=part,
                reason=reason,
                user=request.user,
                rework_target_step=target_step,
                notes=request.data.get("notes") or "",
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "part_id": result.part_id,
            "reason": result.reason,
            "moved_to_step_id": result.moved_to_step_id,
            "already_split": result.already_split,
        })

    @action(detail=False, methods=["post"], url_path="bulk_set_status")
    def bulk_set_status(self, request):
        from Tracker.services.mes.parts import bulk_set_status as svc
        ids = request.data.get("ids") or []
        new_status = request.data.get("status")
        if not isinstance(ids, list) or not new_status:
            return Response({"detail": "ids (list) and status are required"},
                            status=status.HTTP_400_BAD_REQUEST)
        # Elevated users may move a part out of a terminal status (e.g. un-scrap).
        # Placeholder gate; precise elevated-role policy is deferred — see plan 0d.
        allow_terminal_exit = bool(
            getattr(request.user, "is_superuser", False) or getattr(request.user, "is_staff", False)
        )
        try:
            results = svc(
                tenant_id=self.tenant.id if self.tenant else None,
                part_ids=ids,
                new_status=new_status,
                operator=request.user,
                reason=request.data.get("reason"),
                allow_terminal_exit=allow_terminal_exit,
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"results": [r.to_dict() for r in results]})

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
            EquipmentUsage, MaterialUsage, Documents, StepExecution, TimeEntry,
            BatchExecution,
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

        # Get batch cycles this part rode in, grouped by step. A batch cycle's
        # readings and verdict belong to the whole load — surfaced here so the
        # traveler shows "this came from the cycle you shared with N parts"
        # without attributing a shared value to this one part.
        batches = BatchExecution.objects.filter(parts=part).prefetch_related(
            'measurements__measurement_definition', 'quality_reports', 'parts',
        )
        batch_map = {}  # step_id -> list of BatchExecution
        for b in batches:
            batch_map.setdefault(b.step_id, []).append(b)

        # Get attachments for this part and its steps
        part_ct = ContentType.objects.get_for_model(Parts)
        step_ct = ContentType.objects.get_for_model(Steps)
        qr_ct = ContentType.objects.get_for_model(QualityReports)

        # Part-level documents
        # tenant-safe: part/step/qr ids sourced from tenant-scoped objects; RLS enforced
        part_docs = Documents.objects.filter(
            content_type=part_ct,
            object_id=str(part.id)
        )

        # Step-level documents
        step_ids = [str(step.id) for step, _ in ordered_steps]
        # tenant-safe: step_ids sourced from tenant-scoped ordered_steps
        step_docs = Documents.objects.filter(
            content_type=step_ct,
            object_id__in=step_ids
        )

        # QR-level documents
        qr_ids = [str(qr.id) for qrs in qr_map.values() for qr in qrs]
        # tenant-safe: qr_ids sourced from tenant-scoped qr_map
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
            elif step_execs and any(ex.status == 'COMPLETED' for ex in step_execs):
                step_status = 'COMPLETED'
            elif order < current_step_order:
                step_status = 'COMPLETED'
            elif step_execs and any(ex.status == 'SKIPPED' for ex in step_execs):
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

            # Build batch-cycle list — cycles this part shared at this step.
            batch_cycles = []
            for b in batch_map.get(step_id, []):
                b_measurements = []
                for m in b.measurements.all():
                    d = m.measurement_definition
                    b_measurements.append({
                        'label': d.label if d else 'Unknown',
                        'nominal': d.nominal if d else None,
                        'upper_tol': d.upper_tol if d else None,
                        'lower_tol': d.lower_tol if d else None,
                        'unit': d.unit if d else '',
                        'actual_value': float(m.value) if m.value is not None else None,
                        'passed': m.is_within_spec,
                        'recorded_at': m.recorded_at,
                    })
                # Verdict from any batch inspection report on the cycle.
                b_status = None
                for qr in b.quality_reports.all():
                    if qr.status == 'FAIL':
                        b_status = 'FAIL'
                        break
                    elif qr.status == 'PASS' and b_status != 'FAIL':
                        b_status = 'PASS'
                batch_cycles.append({
                    'batch_id': b.id,
                    'started_at': b.started_at,
                    'sealed_at': b.sealed_at,
                    'completed_at': b.completed_at,
                    'part_count': len(b.parts.all()),
                    'quality_status': b_status,
                    'measurements': b_measurements,
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
                'batch_cycles': batch_cycles,
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
    queryset = Orders.unscoped.all()
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
        return qs.select_related('customer', 'company', 'current_milestone__template')

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
        "part_type": TenantScopedPrimaryKeyRelatedField(queryset=PartTypes.unscoped.all()),
        "step": TenantScopedPrimaryKeyRelatedField(queryset=Steps.unscoped.all()),
        "quantity": serializers.IntegerField(),
        "part_status": serializers.ChoiceField(choices=PartsStatus.choices, default=PartsStatus.PENDING),
        "work_order": TenantScopedPrimaryKeyRelatedField(queryset=WorkOrder.unscoped.all(), required=False),
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
                "visibility": serializers.ChoiceField(choices=['VISIBLE', 'INTERNAL'], default='VISIBLE')
            }
        ),
        responses={200: OrdersSerializer}
    )
    @action(detail=True, methods=['post'], url_path='add-note')
    def add_note(self, request, pk=None):
        """Add a note to the order timeline."""
        order = self.get_object()

        message = request.data.get('message')
        visibility = request.data.get('visibility', 'VISIBLE')

        if not message:
            return Response({"detail": "Message is required"}, status=status.HTTP_400_BAD_REQUEST)

        if visibility not in ('VISIBLE', 'INTERNAL'):
            return Response({"detail": "Visibility must be 'VISIBLE' or 'INTERNAL'"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order.add_note(request.user, message, visibility)
            order.save()
            return Response(OrdersSerializer(order, context={'request': request}).data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        request=inline_serializer(
            name="SetMilestoneInput",
            fields={"milestone_id": serializers.UUIDField(allow_null=True)}
        ),
        responses={200: OrdersSerializer}
    )
    @action(detail=True, methods=['patch'], url_path='set-milestone')
    def set_milestone(self, request, pk=None):
        """
        Set the current business milestone for an order.

        Accepts {"milestone_id": "<uuid>"} or {"milestone_id": null} to clear.
        If the order has a HubSpot link with a mapped stage, this also triggers
        a push to HubSpot.
        """
        from Tracker.models import Milestone

        order = self.get_object()
        milestone_id = request.data.get('milestone_id')

        if milestone_id is None:
            order.current_milestone = None
            order.save(update_fields=['current_milestone'])
            return Response(OrdersSerializer(order, context={'request': request}).data)

        try:
            milestone = Milestone.objects.get(
                id=milestone_id,
                tenant=request.user.tenant,
            )
        except Milestone.DoesNotExist:
            return Response(
                {"detail": "Milestone not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        order.current_milestone = milestone
        order.save(update_fields=['current_milestone'])

        # If this order has a HubSpot link, update the link's stage
        # to the mapped stage (reverse direction) and trigger push
        hubspot_link = getattr(order, 'hubspot_link', None)
        if hubspot_link:
            from integrations.models.links.hubspot import HubSpotPipelineStage
            mapped_stage = HubSpotPipelineStage.objects.filter(
                integration=hubspot_link.integration,
                mapped_milestone=milestone,
            ).first()
            if mapped_stage:
                hubspot_link.current_stage = mapped_stage
                hubspot_link.save()  # triggers signal -> push to HubSpot

        return Response(OrdersSerializer(order, context={'request': request}).data)


# ===== MILESTONE VIEWSETS =====

class MilestoneTemplateViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD for milestone templates. Admin-only."""
    from Tracker.serializers.mes_lite import MilestoneTemplateSerializer, MilestoneTemplateListSerializer

    queryset = MilestoneTemplate.unscoped.all()
    serializer_class = MilestoneTemplateSerializer
    pagination_class = None

    def get_serializer_class(self):
        from Tracker.serializers.mes_lite import MilestoneTemplateSerializer
        # Always use full serializer (with nested milestones) since pagination is off
        # and the milestones editor needs the full data
        return MilestoneTemplateSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return MilestoneTemplate.objects.none()
        qs = super().get_queryset()
        return qs.prefetch_related('milestones')

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)

    @extend_schema(
        description=(
            "Create a new revision of a MilestoneTemplate. "
            "Returns the new version with incremented version number. "
            "Milestone children are copied to the new version."
        ),
        request=inline_serializer(
            name="CreateMilestoneTemplateRevisionInput",
            fields={'change_description': serializers.CharField()},
        ),
        responses={201: None},
    )
    @action(detail=True, methods=['post'], url_path='revisions')
    def create_revision(self, request, pk=None):
        """Create a new version of this milestone template.

        PATCH routes content edits through create_new_version via the
        serializer's update() method. This endpoint is the explicit
        "create a new revision" path when callers want full control.
        Returns 201 with the new version.
        """
        from Tracker.services.mes.milestone_template import (
            create_new_milestone_template_version,
        )
        from Tracker.serializers.mes_lite import MilestoneTemplateSerializer

        template = self.get_object()
        change_description = request.data.get('change_description', '')

        try:
            new_version = create_new_milestone_template_version(
                template,
                user=request.user,
                change_description=change_description,
            )
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            MilestoneTemplateSerializer(new_version, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class MilestoneViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD for milestones within templates. Admin-only."""
    from Tracker.serializers.mes_lite import MilestoneSerializer

    queryset = Milestone.unscoped.all()
    serializer_class = MilestoneSerializer
    pagination_class = None

    def get_serializer_class(self):
        from Tracker.serializers.mes_lite import MilestoneSerializer
        return MilestoneSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Milestone.objects.none()
        qs = super().get_queryset()
        # Optionally filter by template
        template_id = self.request.query_params.get('template')
        if template_id:
            qs = qs.filter(template_id=template_id)
        return qs.select_related('template')

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)


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
    queryset = WorkOrder.unscoped.all()
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
            from django.db.models import Count, Q, Prefetch
            from Tracker.models import WorkOrderHold
            completed_statuses = (
                PartsStatus.COMPLETED, PartsStatus.SHIPPED, PartsStatus.IN_STOCK,
                PartsStatus.AWAITING_PICKUP, PartsStatus.CORE_BANKED, PartsStatus.RMA_CLOSED,
            )
            # tenant-safe: used as a Prefetch on a tenant-scoped parent (WorkOrder)
            open_holds = WorkOrderHold.objects.filter(
                cleared_at__isnull=True, is_voided=False,
            ).select_related('placed_by')
            qs = qs.select_related(
                'related_order',
                'related_order__customer',
                'related_order__company',
            ).prefetch_related(
                Prefetch('holds', queryset=open_holds, to_attr='_open_holds_cache'),
            ).annotate(
                _completed_parts_count=Count(
                    'parts',
                    filter=Q(parts__part_status__in=completed_statuses),
                    distinct=True,
                ),
                _child_count=Count('child_workorders', distinct=True),
            )

        return qs

    def get_serializer_class(self):
        """Use lightweight serializer for list, full serializer for detail/create/update."""
        if self.action == 'list':
            return WorkOrderListSerializer
        return WorkOrderSerializer

    @action(detail=True, methods=['get'])
    def qa_summary(self, request, pk=None):
        """Get QA summary for work order."""
        work_order = self.get_object()

        parts = work_order.parts.all()
        # Parts needing QA = requires_sampling but no PASS report yet (mirrors Parts.needs_qa property)
        parts_needing_qa = parts.filter(
            requires_sampling=True,
            part_status__in=['PENDING', 'IN_PROGRESS', 'AWAITING_QA', 'REWORK_NEEDED', 'REWORK_IN_PROGRESS']
        ).exclude(error_reports__status='PASS')

        return Response({'work_order': self.get_serializer(work_order).data,
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
                    'work_order_documents': DocumentsSerializer(many=True),
                    'current_step_documents': DocumentsSerializer(many=True),
                    'part_type_documents': DocumentsSerializer(many=True),
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
        # Mirrors Parts.needs_qa property: requires_sampling but no PASS report yet
        parts_needing_qa = work_order.parts.filter(
            requires_sampling=True,
            part_status__in=['PENDING', 'IN_PROGRESS', 'AWAITING_QA', 'REWORK_NEEDED', 'REWORK_IN_PROGRESS']
        ).exclude(error_reports__status='PASS').select_related('step', 'part_type')

        if not parts_needing_qa.exists():
            return Response({'work_order_documents': [], 'current_step_documents': [], 'part_type_documents': [],
                             'current_step_id': None, 'parts_in_qa': 0})

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

        # Get documents (filtered by user permissions). Link-aware: include
        # docs attached via a secondary DocumentLink, not just the primary GFK,
        # while preserving the for_user access scoping.
        from django.db.models import Q
        from Tracker.services.core.documents import linked_document_ids

        work_order_docs = Documents.objects.for_user(request.user).filter(
            Q(content_type=work_order_ct, object_id=str(work_order.id))
            | Q(id__in=linked_document_ids(work_order_ct, work_order.id))
        )

        current_step_docs = Documents.objects.none()
        if step_ct and current_step:
            current_step_docs = Documents.objects.for_user(request.user).filter(
                Q(content_type=step_ct, object_id=str(current_step.id))
                | Q(id__in=linked_document_ids(step_ct, current_step.id))
            )

        part_type_docs = Documents.objects.none()
        if part_type_ct and part_type:
            part_type_docs = Documents.objects.for_user(request.user).filter(
                Q(content_type=part_type_ct, object_id=str(part_type.id))
                | Q(id__in=linked_document_ids(part_type_ct, part_type.id))
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
        # tenant-safe: step_ids sourced from tenant-scoped work_order
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

    @extend_schema(
        request=inline_serializer(
            name="WorkOrderSplitInput",
            fields={
                "reason": serializers.CharField(),
                "new_erp_id": serializers.CharField(),
                "part_ids": serializers.ListField(child=serializers.UUIDField(), required=False),
                "quantity": serializers.IntegerField(required=False),
                "target_process_id": serializers.UUIDField(required=False, allow_null=True),
                "notes": serializers.CharField(required=False, allow_blank=True),
            },
        ),
        responses={200: inline_serializer(
            name="WorkOrderSplitResponse",
            fields={
                "child_work_order_id": serializers.UUIDField(),
                "child_erp_id": serializers.CharField(),
            },
        )},
    )
    @action(detail=True, methods=["post"], url_path="split")
    def split(self, request, pk=None):
        from Tracker.services.mes.work_order import split_work_order as svc
        parent = self.get_object()
        try:
            child = svc(
                parent_wo=parent,
                reason=request.data.get("reason"),
                actor=request.user,
                new_erp_id=request.data.get("new_erp_id"),
                part_ids=request.data.get("part_ids"),
                quantity=request.data.get("quantity"),
                target_process_id=request.data.get("target_process_id"),
                notes=request.data.get("notes", "") or "",
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            "child_work_order_id": str(child.id),
            "child_erp_id": child.ERP_id,
        })

    @extend_schema(request=None, responses={200: dict})
    @action(detail=True, methods=["post"], url_path="undo_split")
    def undo_split(self, request, pk=None):
        from Tracker.services.mes.work_order import undo_split as svc
        child = self.get_object()
        try:
            parent = svc(child, actor=request.user)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            "parent_work_order_id": str(parent.id),
            "parent_erp_id": parent.ERP_id,
        })

    @extend_schema(
        request=inline_serializer(
            name="WorkOrderPlaceOnHoldInput",
            fields={
                "reason": serializers.CharField(),
                "notes": serializers.CharField(required=False, allow_blank=True),
                "expected_clear_at": serializers.DateTimeField(required=False, allow_null=True),
            },
        ),
        responses={200: dict},
    )
    @action(detail=True, methods=["post"], url_path="place_on_hold")
    def place_on_hold(self, request, pk=None):
        from Tracker.services.mes.work_order import place_on_hold as svc
        wo = self.get_object()
        try:
            hold = svc(
                wo,
                reason=request.data.get("reason"),
                placed_by=request.user,
                notes=request.data.get("notes", "") or "",
                expected_clear_at=request.data.get("expected_clear_at"),
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"id": str(hold.id), "placed_at": hold.placed_at, "reason": hold.reason})

    @extend_schema(request=None, responses={200: dict})
    @action(detail=True, methods=["post"], url_path="clear_hold")
    def clear_hold(self, request, pk=None):
        from Tracker.services.mes.work_order import clear_hold as svc
        wo = self.get_object()
        hold = svc(wo, cleared_by=request.user)
        if hold is None:
            return Response({"detail": "No open hold"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"id": str(hold.id), "cleared_at": hold.cleared_at})

    @extend_schema(
        request=inline_serializer(
            name="WorkOrderBulkPlaceOnHoldInput",
            fields={
                "ids": serializers.ListField(child=serializers.UUIDField()),
                "reason": serializers.CharField(),
                "notes": serializers.CharField(required=False, allow_blank=True),
                "expected_clear_at": serializers.DateTimeField(required=False, allow_null=True),
            },
        ),
        responses={200: inline_serializer(
            name="WorkOrderBulkPlaceOnHoldResponse",
            fields={"results": serializers.ListField(child=serializers.DictField())},
        )},
    )
    @action(detail=False, methods=["post"], url_path="bulk_place_on_hold")
    def bulk_place_on_hold(self, request):
        from Tracker.services.mes.work_order import bulk_place_on_hold as svc
        ids = request.data.get("ids") or []
        reason = request.data.get("reason")
        if not isinstance(ids, list) or not reason:
            return Response({"detail": "ids (list) and reason are required"},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            results = svc(
                tenant_id=self.tenant.id if self.tenant else None,
                work_order_ids=ids,
                reason=reason,
                placed_by=request.user,
                notes=request.data.get("notes", "") or "",
                expected_clear_at=request.data.get("expected_clear_at"),
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"results": [r.to_dict() for r in results]})

    @extend_schema(
        responses={200: inline_serializer(
            name="WorkOrderStepMetricsResponse",
            fields={
                "steps": serializers.ListField(child=serializers.DictField()),
            },
        )},
    )
    @action(detail=True, methods=["get"], url_path="step_metrics")
    def step_metrics(self, request, pk=None):
        """4c — live part distribution per step for the flow-map overlay.

        Returns, for each step that currently holds live (non-terminal) parts on
        this work order, the total count plus an attention breakdown
        (in-rework / quarantined / awaiting-QA / on-hold). A single grouped
        query — accurate regardless of list pagination, unlike counting a capped
        client-side page."""
        from django.db.models import Count
        from Tracker.models import Parts

        wo = self.get_object()
        from Tracker.services.mes.parts import TERMINAL_PART_STATUSES

        # for_user (not raw .objects): the overlay must count only parts this
        # user can see — same row-level scoping (relationship / classification /
        # export-control) as the parts list — so the map can't leak counts of
        # restricted parts. `Parts` is unused now; qs_for_user supplies the base.
        rows = (
            self.qs_for_user(Parts)
            .filter(work_order=wo)
            .exclude(part_status__in=TERMINAL_PART_STATUSES)
            .exclude(step__isnull=True)
            .values("step_id", "part_status")
            .annotate(n=Count("id"))
        )

        # Roll up per step.
        by_step: dict[str, dict] = {}
        for r in rows:
            sid = str(r["step_id"])
            entry = by_step.setdefault(sid, {
                "step_id": sid, "total": 0,
                "in_rework": 0, "quarantined": 0, "awaiting_qa": 0,
            })
            n = r["n"]
            status_val = r["part_status"]
            entry["total"] += n
            if status_val in ("REWORK_NEEDED", "REWORK_IN_PROGRESS"):
                entry["in_rework"] += n
            elif status_val == "QUARANTINED":
                entry["quarantined"] += n
            elif status_val == "AWAITING_QA":
                entry["awaiting_qa"] += n

        return Response({"steps": list(by_step.values())})

    @extend_schema(
        request=inline_serializer(
            name="WorkOrderBulkClearHoldInput",
            fields={"ids": serializers.ListField(child=serializers.UUIDField())},
        ),
        responses={200: inline_serializer(
            name="WorkOrderBulkClearHoldResponse",
            fields={"results": serializers.ListField(child=serializers.DictField())},
        )},
    )
    @action(detail=False, methods=["post"], url_path="bulk_clear_hold")
    def bulk_clear_hold(self, request):
        from Tracker.services.mes.work_order import bulk_clear_hold as svc
        ids = request.data.get("ids") or []
        if not isinstance(ids, list):
            return Response({"detail": "ids must be a list"}, status=status.HTTP_400_BAD_REQUEST)
        results = svc(
            tenant_id=self.tenant.id if self.tenant else None,
            work_order_ids=ids,
            cleared_by=request.user,
        )
        return Response({"results": [r.to_dict() for r in results]})

    @extend_schema(
        request=inline_serializer(name="WorkOrderBulkAddPartsInput", fields={
            "part_type": TenantScopedPrimaryKeyRelatedField(queryset=PartTypes.unscoped.all()),
            "step": TenantScopedPrimaryKeyRelatedField(queryset=Steps.unscoped.all()),
            "quantity": serializers.IntegerField(min_value=1),
            "part_status": serializers.ChoiceField(choices=PartsStatus.choices, default=PartsStatus.PENDING, required=False),
            "erp_id_start": serializers.IntegerField(default=1, required=False, min_value=1),
        }),
        responses={201: inline_serializer(name="WorkOrderBulkAddPartsResponse", fields={
            "count": serializers.IntegerField(),
            "created_part_ids": serializers.ListField(child=serializers.UUIDField()),
        })},
        description="Create N Parts attached to this WO via services.mes.work_order.bulk_add_parts_to_workorder.",
    )
    @action(detail=True, methods=["post"], url_path="bulk_add_parts")
    def bulk_add_parts(self, request, pk=None):
        """Create N Parts on this WO. Atomic.

        Body: { part_type, step, quantity, part_status?, erp_id_start? }
        Returns: { count, created_part_ids }
        """
        from Tracker.services.mes.work_order import bulk_add_parts_to_workorder

        wo = self.get_object()

        part_type_id = request.data.get('part_type')
        step_id = request.data.get('step')
        quantity = request.data.get('quantity')
        part_status_val = request.data.get('part_status', PartsStatus.PENDING)
        erp_id_start = request.data.get('erp_id_start', 1)

        if not all([part_type_id, step_id, quantity]):
            return Response(
                {"detail": "Missing required fields: part_type, step, quantity"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            quantity_int = int(quantity)
            erp_id_start_int = int(erp_id_start)
        except (TypeError, ValueError):
            return Response({"detail": "quantity and erp_id_start must be integers"},
                            status=status.HTTP_400_BAD_REQUEST)
        if part_status_val not in PartsStatus.values:
            return Response({"detail": f"Invalid part_status: {part_status_val}"},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            part_type = PartTypes.objects.get(id=part_type_id)
            step = Steps.objects.get(id=step_id)
        except (PartTypes.DoesNotExist, Steps.DoesNotExist) as e:
            return Response({"detail": f"Invalid reference: {e}"},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            new_parts = bulk_add_parts_to_workorder(
                wo,
                part_type=part_type,
                step=step,
                quantity=quantity_int,
                erp_id_start=erp_id_start_int,
                part_status=part_status_val,
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "count": len(new_parts),
                "created_part_ids": [str(p.id) for p in new_parts],
            },
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        request=inline_serializer(
            name="WorkOrderBulkTransitionInput",
            fields={
                "ids": serializers.ListField(child=serializers.UUIDField()),
                "status": serializers.ChoiceField(choices=WorkOrderStatus.choices),
                "notes": serializers.CharField(required=False, allow_blank=True),
            },
        ),
        responses={200: inline_serializer(
            name="WorkOrderBulkTransitionResponse",
            fields={"results": serializers.ListField(child=serializers.DictField())},
        )},
        description="Transition multiple work orders. Per-id errors captured.",
    )
    @action(detail=False, methods=["post"], url_path="bulk_transition")
    def bulk_transition(self, request):
        from Tracker.services.mes.work_order import bulk_transition as svc
        ids = request.data.get("ids") or []
        new_status = request.data.get("status")
        if not isinstance(ids, list) or not new_status:
            return Response({"detail": "ids (list) and status are required"},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            results = svc(
                tenant_id=self.tenant.id if self.tenant else None,
                work_order_ids=ids,
                new_status=new_status,
                actor=request.user,
                notes=request.data.get("notes"),
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"results": [r.to_dict() for r in results]})


# ===== STEPS & PROCESS VIEWSETS =====

class StepFilterSet(django_filters.FilterSet):
    """Steps list filters. `standalone` (no process membership) + `step_type` let the
    standard list endpoint serve Receiving Inspection Plans — standalone RECEIVING
    steps — with DRF's built-in pagination, no custom action needed."""
    standalone = django_filters.BooleanFilter(
        field_name="process_memberships", lookup_expr="isnull",
        help_text="True = steps not attached to any process (e.g. purchased-material RIPs).")

    class Meta:
        model = Steps
        # Steps link to processes via the ProcessStep junction table.
        fields = {
            "process_memberships__process": ["exact"],
            "process_memberships__process__part_type": ["exact"],
            "part_type": ["exact"],
            "step_type": ["exact"],
        }


@extend_schema(parameters=[
    OpenApiParameter(name="process", type=str, location=OpenApiParameter.QUERY, required=False,
                     description="Filter steps by process UUID (via ProcessStep)"),
    OpenApiParameter(name="part_type", type=str, location=OpenApiParameter.QUERY, required=False,
                     description="Filter steps by process's part type UUID"), ])
@extend_schema_view(
    partial_update=extend_schema(
        parameters=[
            OpenApiParameter(
                name='process',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Process version the edit is scoped to. When supplied, "
                    "the resulting new Step version is junctioned into "
                    "that process's ProcessStep row only — the original "
                    "Step row stays attached to every other process "
                    "version that references it. Used by the PCR-DRAFT "
                    "editing flow to keep concurrent PCRs isolated."
                ),
            ),
        ],
    ),
    update=extend_schema(
        parameters=[
            OpenApiParameter(
                name='process',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                required=False,
                description="See partial_update.",
            ),
        ],
    ),
)
class StepsViewSet(TenantScopedMixin, ListMetadataMixin, ExcelExportMixin, viewsets.ModelViewSet):
    queryset = Steps.unscoped.all()
    serializer_class = StepsSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = StepFilterSet
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

    @extend_schema(
        request=inline_serializer(
            name="CreateReceivingPlanInput",
            fields={"part_type": serializers.UUIDField(),
                    "name": serializers.CharField(required=False, allow_blank=True)}),
        responses={201: StepsSerializer},
        description="Create a process-free RECEIVING step (a purchased-material Receiving "
                    "Inspection Plan) for a part type. Never adopts an in-process RECEIVING step.")
    @action(detail=False, methods=["post"], url_path="create_receiving_plan")
    def create_receiving_plan(self, request):
        from Tracker.services.qms import receiving_inspection
        pt_id = request.data.get("part_type")
        if not pt_id:
            return Response({"detail": "part_type is required."}, status=status.HTTP_400_BAD_REQUEST)
        part_type = PartTypes.objects.filter(pk=pt_id).first()
        if part_type is None:
            return Response({"detail": "Part type not found."}, status=status.HTTP_404_NOT_FOUND)
        step = receiving_inspection.create_standalone_receiving_plan(
            part_type, name=request.data.get("name", ""), user=request.user)
        return Response(StepsSerializer(step, context={"request": request}).data,
                        status=status.HTTP_201_CREATED)

    @extend_schema(responses=StepWithResolvedRulesSerializer)
    @action(detail=True, methods=["get"])
    def resolved_rules(self, request, pk=None):
        """
        GET /steps/:id/resolved_rules/
        Returns the active + fallback rulesets for a given step
        """
        step = self.get_object()
        # Returns active_ruleset and fallback_ruleset at top level (no version field).
        serializer = StepWithResolvedRulesSerializer(step, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        request=inline_serializer(
            name='CreateStepRevisionInput',
            fields={'change_description': serializers.CharField()},
        ),
        responses={201: StepsSerializer},
        description=(
            "Create a new revision of a Step. "
            "All child rows (StepMeasurementRequirement, StepRequirement, and "
            "step-owned TrainingRequirement) are copied to the new version. "
            "Returns the new version with incremented version number."
        ),
    )
    @action(detail=True, methods=['post'], url_path='revisions')
    def create_revision(self, request, pk=None):
        """Create a new version of this step.

        PATCH routes content edits through create_new_version via the
        serializer's update() method. This endpoint is the explicit
        "create a new revision" path when callers want full control.
        Returns 201 with the new version.
        """
        from Tracker.services.mes.steps import create_new_step_version

        step = self.get_object()
        change_description = request.data.get('change_description', '')

        try:
            new_version = create_new_step_version(
                step,
                user=request.user,
                change_description=change_description,
            )
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            StepsSerializer(new_version, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


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
    queryset = StepExecution.unscoped.all()
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

    # ------------------------------------------------------------------
    # Training authorization gate (warn + supervisor override)
    # ------------------------------------------------------------------
    def _gate_process_for(self, data):
        """Best-effort Process context for the gate, from the part's work order.

        Step-level requirements are always enforced (we have the step);
        process-level ones need the WorkOrder's process. Returns None when it
        can't be resolved (e.g. a core teardown), leaving step-level intact.
        """
        part_id = data.get('part')
        if not part_id:
            return None
        part = Parts.objects.filter(pk=part_id).select_related('work_order__process').first()
        wo = getattr(part, 'work_order', None) if part else None
        return getattr(wo, 'process', None) if wo else None

    def _training_gate(self, request, step, process):
        """Warn + supervisor-override training gate for starting active work.

        Returns ``(error_response, snapshot)``:
          - ``error_response`` — a DRF ``Response`` to return immediately, or
            ``None`` when the work may proceed.
          - ``snapshot`` — the authorization dict to persist on
            ``execution.training_authorization`` (competence evidence at the
            point of work). Includes the ``override`` block when a supervisor
            pushed an unqualified operator through.
        """
        from Tracker.services.training import check_training_authorization

        auth = check_training_authorization(request.user, step, process=process)
        snapshot = auth.to_dict()
        if auth.authorized:
            return None, snapshot

        override_raw = request.data.get('override')
        override = override_raw is True or str(override_raw).strip().lower() == 'true'
        # Tenant-scoped perm check (the convention used by every viewset here),
        # not the backend has_perm — override authority is a per-tenant grant.
        can_override = request.user.has_tenant_perm('override_training_gate')
        reason = (request.data.get('override_reason') or '').strip()

        if not override:
            # Default: block, and tell the client whether an override is even
            # possible for THIS user (drives the FE's override affordance).
            return Response({
                'detail': 'You are not qualified for this step.',
                'code': 'training_not_authorized',
                'missing': snapshot['missing'],
                'can_override': can_override,
            }, status=status.HTTP_409_CONFLICT), snapshot

        if not can_override:
            return Response({
                'detail': 'A supervisor override is required to start this step.',
                'code': 'override_not_permitted',
                'missing': snapshot['missing'],
                'can_override': False,
            }, status=status.HTTP_403_FORBIDDEN), snapshot

        if not reason:
            return Response({
                'detail': 'An override reason is required.',
                'code': 'override_reason_required',
                'missing': snapshot['missing'],
                'can_override': True,
            }, status=status.HTTP_400_BAD_REQUEST), snapshot

        snapshot['override'] = {
            'by': request.user.id,
            'by_name': request.user.get_full_name() or request.user.get_username(),
            'reason': reason,
            'at': timezone.now().isoformat(),
        }
        return None, snapshot

    def create(self, request, *args, **kwargs):
        # Gate the transition INTO active work. `useEnsureStepExecution` (the
        # operator's Start-Work funnel) POSTs a row with status=IN_PROGRESS —
        # that's the real authorization point. A part merely arriving at a step
        # (PENDING) isn't gated; nobody is working it yet. The workflow engine
        # creates executions via the ORM, not this HTTP path, so it is untouched.
        self._pending_training_snapshot = None
        if str(request.data.get('status', '')).upper() == 'IN_PROGRESS':
            step = Steps.objects.filter(pk=request.data.get('step')).first()
            if step is not None:
                process = self._gate_process_for(request.data)
                error, snapshot = self._training_gate(request, step, process)
                if error is not None:
                    return error
                self._pending_training_snapshot = snapshot
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        # Let the tenant-aware base assign tenant + save first, then stamp the
        # authorization snapshot captured by create()'s gate.
        super().perform_create(serializer)
        snapshot = getattr(self, '_pending_training_snapshot', None)
        if snapshot is not None:
            execution = serializer.instance
            execution.training_authorization = snapshot
            execution.save(update_fields=['training_authorization'])

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
                filter=Q(step__executions__status='PENDING', step__executions__exited_at__isnull=True)
            ),
            in_progress_count=Count(
                'step__executions',
                filter=Q(step__executions__status='IN_PROGRESS', step__executions__exited_at__isnull=True)
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
            status__in=['PENDING', 'IN_PROGRESS']
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
        Used for operator work queue / inbox. Paginated to match the schema
        (spectacular paginates list actions on a paginated viewset) and the rest
        of the list endpoints — the FE client expects the {results: [...]} shape.
        """
        queryset = self.get_queryset().filter(
            assigned_to=request.user,
            exited_at__isnull=True,
            status__in=['PENDING', 'IN_PROGRESS']
        ).order_by('entered_at')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = StepExecutionListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

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
            fields={
                'override': serializers.BooleanField(
                    required=False,
                    help_text="Set true (with override_reason) to push past the training gate.",
                ),
                'override_reason': serializers.CharField(
                    required=False,
                    help_text="Required when override=true. Logged on the execution.",
                ),
            }
        ),
        responses={200: StepExecutionSerializer}
    )
    @action(detail=True, methods=['post'])
    def claim(self, request, pk=None):
        """
        POST /step-executions/{id}/claim/

        Operator claims a pending step execution.
        Sets assigned_to to current user and status to in_progress.

        Training gate (warn + supervisor override): the operator must be
        qualified for the step. An unqualified claim is blocked (409) unless a
        user with `override_training_gate` passes `override=true` and an
        `override_reason`, which is logged on the execution's
        `training_authorization` snapshot.
        """
        execution = self.get_object()

        if execution.status == 'COMPLETED':
            return Response(
                {"detail": "Cannot claim a completed execution"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if execution.assigned_to and execution.assigned_to != request.user:
            return Response(
                {"detail": "Already assigned to another operator"},
                status=status.HTTP_400_BAD_REQUEST
            )

        process = getattr(execution.subject_work_order, 'process', None)
        error, snapshot = self._training_gate(request, execution.step, process)
        if error is not None:
            return error

        execution.assigned_to = request.user
        execution.status = 'IN_PROGRESS'
        execution.training_authorization = snapshot
        execution.save()

        serializer = StepExecutionSerializer(execution)
        return Response(serializer.data)

    @extend_schema(
        parameters=[OpenApiParameter(
            'parts', OpenApiTypes.STR,
            description="Comma-separated part ids to check the current user against.",
        )],
        responses={200: inline_serializer(
            name="WorkAuthorization",
            fields={
                'can_override': serializers.BooleanField(),
                'results': serializers.ListField(child=inline_serializer(
                    name="WorkAuthorizationRow",
                    fields={
                        'part': serializers.UUIDField(),
                        'step': serializers.UUIDField(allow_null=True),
                        'authorized': serializers.BooleanField(),
                        'missing': serializers.ListField(child=serializers.DictField()),
                    },
                )),
            },
        )},
        description="Per-part training authorization for the current user — the "
                    "Start-Work pre-flight gate (so unqualified parts can be marked "
                    "before launch, not just blocked on click).",
    )
    @action(detail=False, methods=['get'])
    def work_authorization(self, request):
        """
        GET /step-executions/work_authorization/?parts=<id>,<id>

        For each part, resolve its current step (+ the WorkOrder's process) and
        run the training authorization check for the CURRENT user. Memoized per
        (step, process) so a tote of parts at one station is one check, not N.
        `can_override` is the user-level override grant (same for every row).
        """
        from Tracker.services.training import check_training_authorization

        ids = [p for p in (request.query_params.get('parts') or '').split(',') if p]
        parts = Parts.objects.filter(pk__in=ids).select_related('step', 'work_order__process')

        cache: dict = {}
        results = []
        for part in parts:
            step = part.step
            if step is None:
                results.append({'part': str(part.id), 'step': None, 'authorized': True, 'missing': []})
                continue
            process = getattr(getattr(part, 'work_order', None), 'process', None)
            key = (step.id, getattr(process, 'id', None))
            if key not in cache:
                cache[key] = check_training_authorization(request.user, step, process=process).to_dict()
            snap = cache[key]
            results.append({
                'part': str(part.id),
                'step': str(step.id),
                'authorized': snap['authorized'],
                'missing': snap['missing'],
            })

        return Response({
            'can_override': request.user.has_tenant_perm('override_training_gate'),
            'results': results,
        })

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
            status='COMPLETED',
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
    queryset = Processes.unscoped.all()
    serializer_class = ProcessesSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["part_type", "status", "is_disassembly", "is_remanufactured"]
    search_fields = ["name", "part_type__name"]
    ordering_fields = ["created_at", "updated_at", "name", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Processes.objects.none()

        # Apply tenant scoping first, then user filtering
        qs = super().get_queryset()
        return qs.select_related("part_type").prefetch_related("process_steps__step")

    def _include_archived(self):
        # See ProcessWithStepsViewSet._include_archived — a retrieve-by-pk
        # of a superseded (archived) process version must still resolve so
        # WorkOrders pinned to a historical version can load their spec.
        if self.action == 'retrieve':
            return True
        return super()._include_archived()

    @extend_schema(
        description=(
            "Create a new revision of an APPROVED or DEPRECATED process. "
            "Returns the new DRAFT with incremented version. Children "
            "(ProcessStep, StepEdge, current Documents) are copied."
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
        responses={201: ProcessesSerializer},
    )
    @action(detail=True, methods=['post'], url_path='revisions')
    def create_revision(self, request, pk=None):
        """Create a new version of this process.

        PATCH on an APPROVED process is blocked by the serializer's
        editability gate; this endpoint is the explicit "create a new
        revision" path. Returns 201 with the new DRAFT.
        """
        from Tracker.services.mes.processes import create_new_process_version

        process = self.get_object()
        change_description = request.data.get('change_description', '')

        try:
            new_version = create_new_process_version(
                process,
                user=request.user,
                change_description=change_description,
            )
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            ProcessesSerializer(new_version, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


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
    queryset = PartTypes.unscoped.all()
    serializer_class = PartTypesSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, OrderingFilter]
    ordering_fields = ['created_at', 'name', 'updated_at', 'ID_prefix']
    ordering = ['-created_at']
    search_fields = ["name", "ID_prefix"]
    filterset_fields = ['name', 'requires_supplier_qualification', 'requires_part_approval']

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

    @extend_schema(
        description="Aggregate quality rollup for a part type: inspection "
                    "pass/fail + FPY, open dispositions/CAPAs, defect Pareto, "
                    "recent failures, and a 30-day FPY trend.",
        responses={200: inline_serializer(
            name="PartTypeQualitySummary",
            fields={
                "parts_total": serializers.IntegerField(),
                "reports": serializers.DictField(),
                "open": serializers.DictField(),
                "defect_pareto": serializers.ListField(child=serializers.DictField()),
                "spc": serializers.ListField(child=serializers.DictField()),
                "recent_failures": serializers.ListField(child=serializers.DictField()),
                "fpy_trend": serializers.ListField(child=serializers.DictField()),
            },
        )},
    )
    @action(detail=True, methods=['get'], url_path='quality-summary')
    def quality_summary(self, request, pk=None):
        """Aggregate this part type's quality data across all its parts.

        Scoped via `QualityReports.part.part_type`. Honors per-user access via
        `qs_for_user` (export-control / classification / relationship filtering).
        """
        import math
        from datetime import timedelta
        from django.utils import timezone
        from django.db.models import Count, Q
        from django.db.models.functions import TruncDate
        from Tracker.models import (
            QualityReports, QualityErrorsList, Parts, QuarantineDisposition, CAPA,
            MeasurementDefinition, MeasurementResult,
        )

        part_type = self.get_object()

        reports = self.qs_for_user(QualityReports).filter(part__part_type=part_type)
        total = reports.count()
        passed = reports.filter(status='PASS').count()
        failed = reports.filter(status='FAIL').count()
        pending = reports.filter(status='PENDING').count()
        fpy = round(passed / total * 100, 1) if total else None

        parts_total = self.qs_for_user(Parts).filter(part_type=part_type).count()

        open_dispositions = self.qs_for_user(QuarantineDisposition).filter(
            part__part_type=part_type,
        ).exclude(current_state='CLOSED').count()

        open_capas = self.qs_for_user(CAPA).filter(
            part__part_type=part_type,
        ).exclude(status__in=['CLOSED', 'CANCELLED']).count()

        # Defect Pareto (top 8) — error types on FAIL reports for this part type.
        defect_counts = self.qs_for_user(QualityErrorsList).filter(
            report_instances__report__part__part_type=part_type,
            report_instances__report__status='FAIL',
        ).values('error_name').annotate(
            count=Count('report_instances'),
        ).order_by('-count')[:8]
        defect_pareto = [
            {'error_type': d['error_name'], 'count': d['count']} for d in defect_counts
        ]

        recent_failures = [
            {
                'id': str(r.id),
                'report_number': r.report_number,
                'created_at': r.created_at.isoformat(),
                'part': r.part.ERP_id if r.part else None,
                'step': r.step.name if r.step else None,
            }
            for r in reports.filter(status='FAIL').select_related('part', 'step').order_by('-created_at')[:5]
        ]

        # 30-day FPY trend (one point per day; null fpy on days with no data).
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=29)
        daily = reports.filter(
            created_at__date__gte=start_date, created_at__date__lte=end_date,
        ).annotate(date=TruncDate('created_at')).values('date').annotate(
            t=Count('id'), p=Count('id', filter=Q(status='PASS')),
        )
        by_date = {d['date']: d for d in daily}
        fpy_trend = []
        cur = start_date
        while cur <= end_date:
            s = by_date.get(cur)
            t = s['t'] if s else 0
            p = s['p'] if s else 0
            fpy_trend.append({
                'date': cur.isoformat(),
                'label': cur.strftime('%b %d'),
                'fpy': round(p / t * 100, 1) if t else None,
                'total': t,
            })
            cur += timedelta(days=1)

        # SPC: measurement capability for this part type's numeric measurements,
        # top 8 by reading count. in_spec_pct from the stored is_within_spec flag;
        # Ppk (overall) computed from value spread vs nominal ± tolerance.
        meas_results = self.qs_for_user(MeasurementResult).filter(
            report__part__part_type=part_type, value_numeric__isnull=False,
            definition__type='NUMERIC',
        )
        top_defs = meas_results.values('definition').annotate(
            n=Count('id'),
        ).order_by('-n')[:8]
        def_ids = [r['definition'] for r in top_defs]
        defs_by_id = {
            d.id: d for d in self.qs_for_user(MeasurementDefinition).filter(id__in=def_ids)
        }
        spc = []
        for row in top_defs:
            d = defs_by_id.get(row['definition'])
            if d is None:
                continue
            rows = list(meas_results.filter(definition=d).values_list('value_numeric', 'is_within_spec'))
            vals = [float(v) for v, _ in rows]
            n = len(vals)
            if not n:
                continue
            in_spec = sum(1 for _, s in rows if s)
            mean = sum(vals) / n
            ppk = None
            capable = None
            nominal = float(d.nominal) if d.nominal is not None else None
            upper_tol = float(d.upper_tol) if d.upper_tol is not None else None
            lower_tol = float(d.lower_tol) if d.lower_tol is not None else None
            if n >= 2 and None not in (nominal, upper_tol, lower_tol):
                variance = sum((v - mean) ** 2 for v in vals) / (n - 1)
                std = math.sqrt(variance)
                if std > 0:
                    usl = nominal + upper_tol
                    lsl = nominal - lower_tol
                    ppk = round(min((usl - mean) / (3 * std), (mean - lsl) / (3 * std)), 2)
                    capable = ppk >= 1.33
            spc.append({
                'measurement_id': str(d.id),
                'label': d.label,
                'unit': d.unit or '',
                'n': n,
                'in_spec_pct': round(in_spec / n * 100, 1),
                'mean': round(mean, 4),
                'ppk': ppk,
                'capable': capable,
            })

        return Response({
            'parts_total': parts_total,
            'reports': {
                'total': total, 'passed': passed, 'failed': failed,
                'pending': pending, 'fpy': fpy,
            },
            'open': {'dispositions': open_dispositions, 'capas': open_capas},
            'defect_pareto': defect_pareto,
            'spc': spc,
            'recent_failures': recent_failures,
            'fpy_trend': fpy_trend,
        })


class ProcessWithStepsViewSet(TenantScopedMixin, ExcelExportMixin, viewsets.ModelViewSet):
    queryset = Processes.unscoped.all()
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

    def _include_archived(self):
        # A retrieve-by-pk must return the exact row even when it's an
        # archived (superseded) version. WorkOrders and execution records
        # legitimately pin to a historical process version; approving a
        # successor archives the predecessor, but the original spec must
        # stay fetchable for the traveller/flow view of in-flight WOs.
        # List/picker endpoints keep the default archived-excluding behavior.
        if self.action == 'retrieve':
            return True
        return super()._include_archived()

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
        """Get all approved processes available for new work orders.

        Limited to the *current* APPROVED row per version chain.
        Predecessor versions stay in the database for audit (work
        orders that started against them still resolve), but they
        carry `archived=True` once a successor is approved and must
        not appear in the new-WO process picker — otherwise every
        process line shows N duplicate "Injector Reman" entries.
        """
        queryset = self.get_queryset().filter(
            status=ProcessStatus.APPROVED,
            is_current_version=True,
            archived=False,
        )

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
    queryset = Equipments.unscoped.all()
    serializer_class = EquipmentsSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Equipments.objects.none()

        # Apply tenant scoping first, then user filtering
        qs = super().get_queryset()
        return qs


class EquipmentViewSet(TenantScopedMixin, ListMetadataMixin, ExcelExportMixin, viewsets.ModelViewSet):
    queryset = Equipments.unscoped.all()
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
    queryset = EquipmentType.unscoped.all()
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


class OutsideProcessShipmentViewSet(TenantScopedMixin, ExcelExportMixin, viewsets.ModelViewSet):
    """Outside-processing (subcontract) shipments — Flow B.

    List/retrieve are plain CRUD; the lifecycle (send-out, receive-back, and the
    return-inspection accept/reject) runs through the actions below, which delegate
    to services.mes.outside_process. The return inspection is a QualityReports keyed
    to the shipment and runs the same DWI receiving runtime as incoming lots.
    """
    queryset = OutsideProcessShipment.unscoped.select_related('supplier', 'step', 'work_order')
    serializer_class = OutsideProcessShipmentSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter, filters.SearchFilter]
    search_fields = ['shipment_number', 'reference', 'supplier__name']
    filterset_fields = ['status', 'supplier', 'step', 'work_order']
    ordering_fields = ['shipped_at', 'returned_at', 'shipment_number']
    ordering = ['-shipped_at']

    action_permissions = {
        'send_out': ['add_outsideprocessshipment'],
        'receive_back': ['change_outsideprocessshipment'],
        'accept': ['change_outsideprocessshipment'],
        'reject': ['change_outsideprocessshipment'],
    }
    # receive_back/accept/reject mutate an existing shipment → gated solely by
    # change_ (above), not the POST→add CRUD default. send_out genuinely creates,
    # so it stays non-exempt (add_ is correct there).
    crud_exempt_actions = {'receive_back', 'accept', 'reject'}

    def _qr_response(self, report, status_code=status.HTTP_200_OK):
        return Response(QualityReportsSerializer(report, context={'request': self.request}).data,
                        status=status_code)

    def _return_report(self, shipment):
        return shipment.quality_reports.order_by('-created_at').first()

    @extend_schema(
        request=inline_serializer(name="SendPartsOutRequest", fields={
            "step": serializers.UUIDField(),
            "part_ids": serializers.ListField(child=serializers.UUIDField()),
            "supplier": serializers.UUIDField(required=False),
            "reference": serializers.CharField(required=False, allow_blank=True),
        }),
        responses={201: OutsideProcessShipmentSerializer},
        description="Send a batch of parts out to a subcontract vendor for an outside-process "
                    "step. Creates the shipment, links the parts, and moves them to AT_OUTSIDE_PROCESS.",
    )
    @action(detail=False, methods=['post'], url_path='send_out')
    def send_out(self, request):
        step_id = request.data.get('step')
        part_ids = request.data.get('part_ids') or []
        if not step_id or not part_ids:
            return Response({'detail': 'step and part_ids are required.'},
                            status=status.HTTP_400_BAD_REQUEST)
        step = Steps.objects.filter(pk=step_id).first()
        if step is None:
            return Response({'detail': 'Step not found.'}, status=status.HTTP_400_BAD_REQUEST)
        parts = list(Parts.objects.filter(pk__in=part_ids))
        supplier = None
        if request.data.get('supplier'):
            from Tracker.models import Companies
            supplier = Companies.objects.filter(pk=request.data['supplier']).first()
        try:
            shipment = outside_process.send_parts_out(
                step=step, parts=parts, supplier=supplier,
                reference=request.data.get('reference', ''), user=request.user)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OutsideProcessShipmentSerializer(shipment, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)

    @extend_schema(
        responses=ReadyToShipGroupSerializer(many=True),
        description="Shipper board: parts staged at outside-process steps (not yet sent), "
                    "grouped by step/vendor across work orders, ready to dispatch.",
    )
    @action(detail=False, methods=['get'], url_path='ready_to_ship')
    def ready_to_ship(self, request):
        data = ReadyToShipGroupSerializer(
            outside_process.build_ready_to_ship_groups(), many=True).data
        # This action rides a paginated ModelViewSet, so the generated client types
        # the response as a paginated envelope — match it (the list is small; the
        # page params are accepted but unused).
        return Response({"count": len(data), "next": None, "previous": None, "results": data})

    @extend_schema(request=None, responses={201: QualityReportsSerializer},
                   description="Receive the shipment back and open its return inspection.")
    @action(detail=True, methods=['post'], url_path='receive_back')
    def receive_back(self, request, pk=None):
        shipment = self.get_object()
        try:
            report = outside_process.receive_parts_back(shipment, request.user)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return self._qr_response(report, status.HTTP_201_CREATED)

    @extend_schema(responses={200: SamplePlanResponseSerializer},
                   description="Acceptance-sampling plan for the returned batch (lot size = returned count).")
    @action(detail=True, methods=['get'], url_path='sample_plan')
    def sample_plan(self, request, pk=None):
        shipment = self.get_object()
        try:
            sp = outside_process.sample_plan_for_shipment(shipment)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        step = shipment.step
        chars = [
            {'id': m.id, 'label': m.label, 'unit': m.unit or '', 'type': m.type,
             'nominal': float(m.nominal) if m.nominal is not None else None,
             'upper_tol': float(m.upper_tol) if m.upper_tol is not None else None,
             'lower_tol': float(m.lower_tol) if m.lower_tol is not None else None}
            for m in (step.required_measurements.all() if step else [])
        ]
        rs = outside_process.resolve_sampling_ruleset(step, shipment.supplier) if step else None
        ex = outside_process._return_execution(shipment)
        return Response(SamplePlanResponseSerializer({
            **sp.__dict__,
            'variables_characteristic_id': rs.variables_characteristic_id if rs else None,
            'characteristics': chars,
            'step_id': step.id if step else None,
            'has_substeps': bool(step and step.substeps.filter(archived=False).exists()),
            'step_execution_id': ex.id if ex else None,
        }).data)

    @extend_schema(request=None, responses={200: QualityReportsSerializer})
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        shipment = self.get_object()
        report = self._return_report(shipment)
        if report is None:
            return Response({'detail': 'No return inspection for this shipment.'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            report = outside_process.accept_return(report, request.user)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return self._qr_response(report)

    @extend_schema(request=None, responses={200: QualityReportsSerializer})
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        shipment = self.get_object()
        report = self._return_report(shipment)
        if report is None:
            return Response({'detail': 'No return inspection for this shipment.'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            report = outside_process.reject_return(report, request.user)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return self._qr_response(report)

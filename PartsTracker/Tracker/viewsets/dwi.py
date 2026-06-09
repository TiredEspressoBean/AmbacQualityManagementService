# viewsets/dwi.py - Digital Work Instructions ViewSets
"""
ViewSets for the DWI subsystem.

CRUD endpoints for the Phase 1-3 models. Operator-side capture actions
(complete_substep, record_gate_completion, etc.) live in
`services/mes/substeps.py` and are exposed via dedicated viewset actions
when Phase 4 frontend wires them.
"""
from django.db import transaction
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiParameter, OpenApiTypes
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from Tracker.models import (
    BatchExecution,
    Steps,
    Substep,
    SubstepCompletion,
    SubstepResource,
    SubstepTranslation,
    SubstepGateCompletion,
    SubstepResponse,
)
from Tracker.serializers.dwi import (
    SubstepSerializer,
    SubstepResourceSerializer,
    SubstepTranslationSerializer,
    SubstepCompletionSerializer,
    SubstepGateCompletionSerializer,
    SubstepResponseSerializer,
)
from Tracker.models import StepExecution
from Tracker.services.dwi.operator_capture import submit_substep
from .base import TenantScopedMixin


_substep_process_param = OpenApiParameter(
    name='process',
    type=OpenApiTypes.UUID,
    location=OpenApiParameter.QUERY,
    required=False,
    description=(
        "Process version this substep edit is scoped to. When supplied "
        "and the process is DRAFT, the parent Step is versioned, all "
        "substeps are copied to the new Step row (preserving each "
        "substep's identity_id), and the edit applies to the cloned "
        "substep on that new Step. Sibling PCR drafts referencing the "
        "old Step row are unaffected."
    ),
)


@extend_schema_view(
    partial_update=extend_schema(parameters=[_substep_process_param]),
    update=extend_schema(parameters=[_substep_process_param]),
)
class SubstepViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD for Substep rows.

    Filter by `?step=<step_id>` to fetch all substeps belonging to a Step
    (the typical substep-editor query). Default ordering matches the
    operator's working order within the parent Op.

    Multi-PCR isolation: pass `?process=<uuid>` when editing from a PCR
    DRAFT. The serializer detects the DRAFT context and routes through
    `create_new_step_version` so the substep edit is isolated to that
    process's version of the parent Step.
    """

    queryset = Substep.unscoped.select_related('step', 'sampling_rule')
    serializer_class = SubstepSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_fields = ['step', 'is_optional', 'requires_signature', 'is_inspection_point']
    search_fields = ['title']
    ordering_fields = ['order', 'created_at', 'updated_at']
    ordering = ['step', 'order']

    # ----- DRAFT-only authoring guard -----
    #
    # Substeps are part of a Process's authoring lineage. Once any consuming
    # Process leaves DRAFT, the structural shape (substeps + their content)
    # is frozen and further edits must go through the change-control flow
    # (PCR / PCO / PCN). Writes hit `_assert_step_editable` before reaching
    # the model. Reads stay unrestricted so APPROVED processes can still be
    # inspected from the authoring page in read-only mode.

    @staticmethod
    def _assert_step_editable(step):
        """Raise PermissionDenied if the parent Step is locked (any consuming
        Process is not DRAFT). Pulls the message all the way to the operator
        so the UI can show a sensible explanation rather than a generic 403.
        """
        if not step.is_editable:
            raise PermissionDenied(
                "Cannot modify substeps on a Step whose Process is not DRAFT. "
                "Submit a Process Change Request to edit approved instructions."
            )

    def perform_create(self, serializer):
        step = serializer.validated_data.get('step')
        if step is not None:
            self._assert_step_editable(step)
        serializer.save()

    def perform_update(self, serializer):
        self._assert_step_editable(serializer.instance.step)
        serializer.save()

    def perform_destroy(self, instance):
        self._assert_step_editable(instance.step)
        instance.delete()

    @action(detail=True, methods=['post'])
    def submit(self, request, *args, **kwargs):
        """Operator-runtime submit endpoint.

        Persists everything an operator captured on a single substep:
        per-node `SubstepResponse` rows, `MeasurementInput` captures via
        the existing two-tier service, structured-capture rows on
        `QualityReports` + through tables (when the substep is an
        inspection point), and a closing `SubstepCompletion`.

        Body shape: see `services/dwi/operator_capture.py` docstring.

        Returns:
            ``{ completion_id, response_count, quality_report_id,
                 measurement_count }``
        """
        substep = self.get_object()

        step_execution_id = request.data.get('step_execution')
        if not step_execution_id:
            return Response(
                {'detail': 'Body must include `step_execution` id.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        step_execution = get_object_or_404(StepExecution, pk=step_execution_id)
        captures = request.data.get('captures') or []
        if not isinstance(captures, list):
            return Response(
                {'detail': '`captures` must be a list of capture dicts.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ip_address = (
            request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR')
        )
        if ip_address and ',' in ip_address:
            # X-Forwarded-For can be a chain; take the first.
            ip_address = ip_address.split(',')[0].strip()

        from django.core.exceptions import ValidationError as DjangoValidationError
        try:
            result = submit_substep(
                substep=substep,
                step_execution=step_execution,
                user=request.user if request.user.is_authenticated else None,
                captures=captures,
                notes=request.data.get('notes', '') or '',
                signature_data=request.data.get('signature_data'),
                signature_meaning=request.data.get('signature_meaning'),
                verification_method=request.data.get('verification_method'),
                marked_not_applicable=bool(request.data.get('marked_not_applicable')),
                na_reason_code=request.data.get('na_reason_code', '') or '',
                ip_address=ip_address,
            )
        except DjangoValidationError as exc:
            return Response(
                {'detail': '; '.join(exc.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                'completion_id': result.completion_id,
                'response_count': result.response_count,
                'quality_report_id': result.quality_report_id,
                'measurement_count': result.measurement_count,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='ensure_inspection_qr')
    def ensure_inspection_qr(self, request, pk=None):
        """
        POST /api/Substeps/{id}/ensure_inspection_qr/

        Eagerly find-or-create the `QualityReports` row that this
        inspection-point substep would create on submit. Lets the
        operator runtime pre-bind a QR id into `PartContext` before the
        operator finishes the substep — required by capture nodes like
        `PartAnnotation` that need a known QR id to attach annotations
        to as the operator works.

        Idempotent: returns the existing QR id when the runtime calls
        it on subsequent opens of the same (step_execution, substep)
        pair.

        Body: { "step_execution": "<uuid>" }
        Returns: { "quality_report_id": "<uuid>", "created": <bool> }
        """
        substep = self.get_object()
        if not substep.is_inspection_point:
            return Response(
                {'detail': 'Substep is not an inspection point — no QR needed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        step_execution_id = request.data.get('step_execution')
        if not step_execution_id:
            return Response(
                {'detail': 'Body must include `step_execution` id.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        step_execution = get_object_or_404(StepExecution, pk=step_execution_id)

        from Tracker.services.dwi.operator_capture import ensure_quality_report
        existed_before = bool(
            step_execution.part_id
            and getattr(step_execution, 'part', None)
        )  # rough; the function returns the same row if present
        report = ensure_quality_report(
            substep, step_execution,
            request.user if request.user.is_authenticated else None,
        )
        if report is None:
            return Response(
                {'detail': 'Cannot create QR — step execution has no part (core?).'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({
            'quality_report_id': str(report.id),
            # `created` is best-effort; the service is idempotent and
            # doesn't surface a "was created vs found" boolean.
            # Callers can ignore this field if they don't care.
            'created': not existed_before,
        })

    @action(detail=False, methods=['post'])
    def reorder(self, request, *args, **kwargs):
        """Atomically reorder substeps within a step.

        Body shape: ``{"step": "<uuid>", "order": ["<substep_id>", ...]}``.

        Why a dedicated action: the ``(step, order)`` UniqueConstraint
        rejects naive per-row PATCHes from the client because intermediate
        states collide mid-swap. We do a two-phase update inside a single
        transaction — first shift all involved rows to a non-conflicting
        negative range, then assign the final positive values.
        """
        step_id = request.data.get('step')
        ordering = request.data.get('order') or []
        if not step_id or not isinstance(ordering, list) or not ordering:
            return Response(
                {'detail': 'Body must include `step` and a non-empty `order` list.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Same DRAFT-only guard as the row-level mutations.
        step = get_object_or_404(Steps.unscoped, pk=step_id)
        self._assert_step_editable(step)

        # Tenant scoping is enforced by the viewset's queryset.
        qs = self.get_queryset().filter(step_id=step_id, pk__in=ordering)
        found_ids = {str(s.pk) for s in qs}
        missing = [sid for sid in ordering if str(sid) not in found_ids]
        if missing:
            return Response(
                {'detail': f'Substeps not found for this step: {missing}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            # Phase 1: park all involved rows at negative offsets so the unique
            # constraint on (step, order) can't fire while we shuffle.
            for i, sid in enumerate(ordering):
                Substep.unscoped.filter(pk=sid).update(order=-(i + 1))
            # Phase 2: write the final positive ordinals.
            for i, sid in enumerate(ordering):
                Substep.unscoped.filter(pk=sid).update(order=i)

        return Response(status=status.HTTP_204_NO_CONTENT)


class SubstepResourceViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD for SubstepResource rows.

    Filter by `?substep=<substep_id>` to fetch the resource list for a
    substep (the typical authoring-popover query).
    """

    queryset = SubstepResource.unscoped.select_related('substep', 'equipment_type')
    serializer_class = SubstepResourceSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['substep', 'equipment_type', 'required']
    ordering_fields = ['created_at']
    ordering = ['substep', 'pk']


class SubstepTranslationViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD for SubstepTranslation rows."""

    queryset = SubstepTranslation.unscoped.select_related('substep')
    serializer_class = SubstepTranslationSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['substep', 'language']
    ordering_fields = ['created_at']
    ordering = ['substep', 'language']


class SubstepCompletionViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Per-execution substep completions.

    Filter by `?step_execution=<id>` or `?substep=<id>` to scope queries.
    """

    queryset = SubstepCompletion.unscoped.select_related(
        'step_execution', 'substep', 'completed_by',
    )
    serializer_class = SubstepCompletionSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['step_execution', 'substep', 'completed_by', 'marked_not_applicable']
    ordering_fields = ['completed_at']
    ordering = ['-completed_at']

    @action(detail=True, methods=['post'], url_path='void')
    def void(self, request, pk=None):
        """
        POST /api/SubstepCompletions/{id}/void/

        QA voids an erroneous completion (gauge out of cal, wrong test
        method, calculator error, etc.). The gate ignores voided rows,
        so the next advancement attempt for the affected part will
        block on the missing completion until a fresh one lands.

        For parts already past the step, the void is audit-only — the
        containment investigation happens through the existing
        QualityReports list + CAPA tooling (Flow #10).

        Body: { "reason": "<text>" } — required.
        """
        completion = self.get_object()
        reason = (request.data.get('reason') or '').strip()
        if not reason:
            return Response(
                {'detail': 'reason is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if completion.is_voided:
            return Response(
                {'detail': 'Completion is already voided.',
                 'voided_at': completion.voided_at,
                 'void_reason': completion.void_reason},
                status=status.HTTP_400_BAD_REQUEST,
            )
        completion.void(request.user, reason)
        return Response({
            'id': str(completion.id),
            'is_voided': completion.is_voided,
            'voided_at': completion.voided_at.isoformat() if completion.voided_at else None,
            'void_reason': completion.void_reason,
        })


class SubstepGateCompletionViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Per-node attestation / signature gate completions."""

    queryset = SubstepGateCompletion.unscoped.select_related(
        'step_execution', 'substep', 'completed_by',
    )
    serializer_class = SubstepGateCompletionSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['step_execution', 'substep', 'node_id', 'completed_by']
    ordering_fields = ['completed_at']
    ordering = ['-completed_at']


class SubstepResponseViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Per-node operator capture rows."""

    queryset = SubstepResponse.unscoped.select_related(
        'step_execution', 'substep', 'responded_by', 'value_document',
    )
    serializer_class = SubstepResponseSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['step_execution', 'substep', 'node_id', 'kind', 'responded_by']
    ordering_fields = ['responded_at']
    ordering = ['-responded_at']

class BatchExecutionViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """BatchExecution rows + seal lifecycle action.

    GET endpoints expose membership / status; the only state-changing
    action in this iteration is `POST {id}/seal/` which closes the batch
    for advancement.
    """

    queryset = BatchExecution.unscoped.select_related(
        'work_order', 'step', 'started_by',
    ).prefetch_related('parts')
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['work_order', 'step', 'sealed_at']
    ordering_fields = ['started_at', 'sealed_at']
    ordering = ['-started_at']

    serializer_class = None  # populated lazily to avoid circular import at module load

    def get_serializer_class(self):
        from Tracker.serializers.dwi import BatchExecutionSerializer
        return BatchExecutionSerializer

    @action(detail=True, methods=['post'], url_path='seal')
    def seal(self, request, pk=None):
        """POST /api/BatchExecutions/{id}/seal/

        Locks the batch (timestamps `sealed_at`) and fires the
        advancement retry. ValidationError if required cohort substeps
        aren't all completed, or if membership crosses WO boundaries.
        """
        from django.core.exceptions import ValidationError
        from Tracker.services.dwi.batch_lifecycle import seal_batch

        batch = self.get_object()
        try:
            result = seal_batch(batch=batch, user=request.user)
        except ValidationError as exc:
            return Response(
                {'detail': 'Cannot seal batch', 'problems': list(exc.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({
            'batch_id': result.batch_id,
            'sealed_at': result.sealed_at,
        })


class SamplingDecisionViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    """Read-only access to live SamplingDecision rows.

    Operator runtime queries `?step_execution=<id>` to discover which
    substeps are SELECTED / DESELECTED / PENDING for this part and skip
    sampled-out work. Decisions are written by the sampling subsystem
    on step entry (`Tracker.services.dwi.sampling_decisions`); they're
    not editable through the API.
    """

    from Tracker.models import SamplingDecision
    from Tracker.serializers.dwi import SamplingDecisionSerializer

    queryset = SamplingDecision.unscoped.select_related(
        'step_execution', 'substep',
    )
    serializer_class = SamplingDecisionSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['step_execution', 'substep', 'outcome']
    ordering_fields = ['decided_at']
    ordering = ['-decided_at']

    def get_queryset(self):
        # Default to live decisions only (hide superseded rows). Pass
        # `?include_superseded=1` to get the full audit trail.
        qs = super().get_queryset()
        if self.request.query_params.get('include_superseded') != '1':
            qs = qs.filter(superseded_by__isnull=True)
        return qs

    @action(detail=False, methods=['post'], url_path='reconcile')
    def reconcile(self, request):
        """
        POST /api/SamplingDecisions/reconcile/

        Supervisor-triggered reconciliation of PENDING decisions for a
        WorkOrder (optionally narrowed to a step). Resolves rules like
        LAST_N_PARTS / EXACT_COUNT now that the cohort is closed.

        Body: { "work_order_id": "<uuid>", "step_id"?: "<uuid>" }

        Returns a summary: { reconciled, now_selected, now_deselected,
        still_pending }. Supervisor UI uses this to surface what flipped.
        """
        from Tracker.models import Steps, WorkOrder
        from Tracker.services.dwi.sampling_decisions import (
            reconcile_pending_decisions,
        )

        wo_id = request.data.get('work_order_id')
        if not wo_id:
            return Response(
                {'detail': 'work_order_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            wo = WorkOrder.objects.get(id=wo_id)
        except WorkOrder.DoesNotExist:
            return Response(
                {'detail': 'work_order not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        step = None
        step_id = request.data.get('step_id')
        if step_id:
            try:
                step = Steps.objects.get(id=step_id)
            except Steps.DoesNotExist:
                return Response(
                    {'detail': 'step not found'},
                    status=status.HTTP_404_NOT_FOUND,
                )

        summary = reconcile_pending_decisions(wo, step=step)
        return Response(summary)

# viewsets/dwi.py - Digital Work Instructions ViewSets
"""
ViewSets for the DWI subsystem.

CRUD endpoints for the Phase 1-3 models. Operator-side capture actions
(complete_substep, record_gate_completion, etc.) live in
`services/mes/substeps.py` and are exposed via dedicated viewset actions
when Phase 4 frontend wires them.
"""
from django.db.models import Max
from django.db import transaction
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import (
    extend_schema_view, extend_schema, inline_serializer,
    OpenApiParameter, OpenApiTypes,
)
from rest_framework import serializers as drf_serializers
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

    # Operator-runtime actions are NOT authoring. `submit` and
    # `ensure_inspection_qr` are POSTs, so the default CRUD gate would demand
    # `add_substep` — an AUTHORING permission that floor roles (Operator, QA
    # Inspector, Shift Lead) don't have, which wrongly 403s them out of running
    # an inspection. Exempt these from the CRUD gate and require the
    # operator-capture perm instead, so any staff member who can complete a
    # substep can run an inspection (everyone with STAFF_OPERATIONAL_WRITE).
    crud_exempt_actions = {'submit', 'ensure_inspection_qr', 'sampling_rule'}
    action_permissions = {
        'submit': ['add_substepcompletion'],
        'ensure_inspection_qr': ['add_substepcompletion'],
        # Authoring a substep's sampling is a substep edit (B7, 2026-10-28).
        'sampling_rule': ['change_substep'],
    }

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
        from Tracker.services.dwi.substep_sampling import retire_if_unused
        self._assert_step_editable(serializer.instance.step)
        former_rule = serializer.instance.sampling_rule_id
        serializer.save()
        # A sampling choice changed or cleared: its old rule goes once nothing uses it.
        if 'sampling_rule' in serializer.validated_data:
            retire_if_unused(former_rule)

    def perform_destroy(self, instance):
        self._assert_step_editable(instance.step)
        instance.delete()

    @extend_schema(
        request=inline_serializer(name='SubstepSamplingRuleRequest', fields={
            'step': drf_serializers.UUIDField(),
            # PERCENTAGE, RANDOM, EVERY_NTH_PART or FIRST_N_PARTS — checked by the
            # service (a plain string: a choice set here collides with SamplingRule's enum).
            'rule_type': drf_serializers.CharField(),
            'value': drf_serializers.IntegerField(),
        }),
        responses={201: inline_serializer(name='SubstepSamplingRule', fields={
            'id': drf_serializers.UUIDField(),
            'rule_type': drf_serializers.CharField(),
            'value': drf_serializers.IntegerField(),
        })},
        description="Create a sampling rule for a substep of a DRAFT step. The editor then "
                    "saves it as the substep's `sampling_rule` with its other edits.",
    )
    @action(detail=False, methods=['post'], url_path='sampling-rule')
    def sampling_rule(self, request):
        from Tracker.models import Steps
        from Tracker.services.dwi.substep_sampling import create_substep_rule
        step = Steps.objects.filter(tenant=self.tenant, id=request.data.get('step')).first()
        if step is None:
            return Response({'detail': 'Step not found'}, status=status.HTTP_404_NOT_FOUND)
        self._assert_step_editable(step)
        try:
            rule = create_substep_rule(step, request.data.get('rule_type'),
                                       request.data.get('value'), user=request.user)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'id': str(rule.id), 'rule_type': rule.rule_type, 'value': rule.value},
                        status=status.HTTP_201_CREATED)

    @extend_schema(
        request=inline_serializer(
            name='SubstepSubmitRequest',
            fields={
                # Exactly one of step_execution / batch_execution.
                'step_execution': drf_serializers.UUIDField(required=False),
                'batch_execution': drf_serializers.UUIDField(required=False),
                'captures': drf_serializers.ListField(
                    child=drf_serializers.DictField(), required=False,
                ),
                'notes': drf_serializers.CharField(required=False, allow_blank=True),
                'signature_data': drf_serializers.CharField(required=False, allow_blank=True),
                'signature_meaning': drf_serializers.CharField(required=False, allow_blank=True),
                # No password here: a signature belongs to a block in the body and is
                # made before submitting (POST /api/SubstepGateCompletions/). Submitting
                # checks those blocks were signed.
                'marked_not_applicable': drf_serializers.BooleanField(required=False),
                'na_reason_code': drf_serializers.CharField(required=False, allow_blank=True),
            },
        ),
        responses=inline_serializer(
            name='SubstepSubmitResponse',
            fields={
                'completion_id': drf_serializers.CharField(),
                'response_count': drf_serializers.IntegerField(),
                'quality_report_id': drf_serializers.CharField(allow_null=True),
                'measurement_count': drf_serializers.IntegerField(),
                # Recorded, but the operator should know (e.g. an overdue gauge).
                'warnings': drf_serializers.ListField(child=drf_serializers.CharField()),
            },
        ),
    )
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

        # A submit targets either a per-part StepExecution (SAMPLED substeps) or a
        # per-batch BatchExecution (BATCH-scope substeps, 3a) — exactly one.
        step_execution_id = request.data.get('step_execution')
        batch_execution_id = request.data.get('batch_execution')
        if bool(step_execution_id) == bool(batch_execution_id):
            return Response(
                {'detail': 'Body must include exactly one of `step_execution` / `batch_execution` id.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        step_execution = (
            get_object_or_404(StepExecution, pk=step_execution_id) if step_execution_id else None
        )
        batch_execution = (
            get_object_or_404(BatchExecution, pk=batch_execution_id) if batch_execution_id else None
        )
        captures = request.data.get('captures') or []
        if not isinstance(captures, list):
            return Response(
                {'detail': '`captures` must be a list of capture dicts.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Optional sampled-unit index (1..n) — receiving unit-by-unit runtime
        # stamps it on this unit's measurements so lot-acceptance evaluators can
        # group by unit / gather the sample. None for per-part DWI.
        sample_number = request.data.get('sample_number')
        if sample_number is not None:
            try:
                sample_number = int(sample_number)
            except (TypeError, ValueError):
                return Response(
                    {'detail': '`sample_number` must be an integer.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Trusted client IP (edge-set header, not spoofable X-Forwarded-For).
        from Tracker.throttling import get_client_ip
        ip_address = get_client_ip(request)

        from django.core.exceptions import ValidationError as DjangoValidationError
        try:
            result = submit_substep(
                substep=substep,
                step_execution=step_execution,
                batch_execution=batch_execution,
                user=request.user if request.user.is_authenticated else None,
                captures=captures,
                notes=request.data.get('notes', '') or '',
                signature_data=request.data.get('signature_data'),
                signature_meaning=request.data.get('signature_meaning'),
                marked_not_applicable=bool(request.data.get('marked_not_applicable')),
                na_reason_code=request.data.get('na_reason_code', '') or '',
                ip_address=ip_address,
                sample_number=sample_number,
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
                'warnings': result.warnings,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        request=inline_serializer(
            name='EnsureInspectionQrRequest',
            fields={'step_execution': drf_serializers.UUIDField()},
        ),
        responses={200: inline_serializer(
            name='EnsureInspectionQrResponse',
            fields={
                'quality_report_id': drf_serializers.UUIDField(),
                'created': drf_serializers.BooleanField(),
            },
        )},
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
                {'detail': 'Substep is not an inspection point - no QR needed.'},
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
                {'detail': 'Cannot create QR - step execution has no part (core?).'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({
            'quality_report_id': str(report.id),
            # `created` is best-effort; the service is idempotent and
            # doesn't surface a "was created vs found" boolean.
            # Callers can ignore this field if they don't care.
            'created': not existed_before,
        })

    @extend_schema(
        # Without this the body falls back to SubstepRequest -- a whole
        # substep, where `order` is a single integer ordinal. The generated
        # client then rejects `{step, order: [...]}` before it ever reaches
        # the network, so drag-to-reorder failed client-side every time.
        request=inline_serializer(
            name='SubstepReorderRequest',
            fields={
                'step': drf_serializers.UUIDField(),
                'order': drf_serializers.ListField(
                    child=drf_serializers.UUIDField(),
                    help_text='Substep ids in their intended final order.',
                ),
            },
        ),
        responses={204: None, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    @action(detail=False, methods=['post'])
    def reorder(self, request, *args, **kwargs):
        """Atomically reorder substeps within a step.

        Body shape: ``{"step": "<uuid>", "order": ["<substep_id>", ...]}``.

        Why a dedicated action: the ``(step, order)`` UniqueConstraint
        rejects naive per-row PATCHes from the client because intermediate
        states collide mid-swap. We do a two-phase update inside a single
        transaction — first park every involved row in a scratch range above
        anything currently in the step, then assign the final ordinals.

        The scratch range has to be *above* the live values, not below:
        ``order`` is a PositiveIntegerField, so Postgres carries a
        ``CHECK (order >= 0)`` and parking at negative offsets aborted the
        transaction every time.
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

        # Every live substep in the step has to be accounted for. A partial
        # ordering would leave unlisted rows holding ordinals that phase 2
        # then tries to reuse, which surfaced as an opaque unique-violation
        # 500 rather than a usable error.
        live_ids = {
            str(pk) for pk in
            self.get_queryset().filter(step_id=step_id).values_list('pk', flat=True)
        }
        unlisted = live_ids - {str(sid) for sid in ordering}
        if unlisted:
            return Response(
                {'detail': f'`order` must list every substep in the step; '
                           f'missing: {sorted(unlisted)}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            # Phase 1: park every involved row in a scratch range above the
            # step's current high-water mark, so neither the unique constraint
            # on (step, order) nor the `order >= 0` check can fire mid-shuffle.
            current_max = self.get_queryset().filter(
                step_id=step_id,
            ).aggregate(m=Max('order'))['m'] or 0
            scratch = current_max + 1
            for i, sid in enumerate(ordering):
                Substep.unscoped.filter(pk=sid).update(order=scratch + i)
            # Phase 2: write the final ordinals.
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


class SubstepCompletionViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    """Per-execution substep completions — read, plus `void`.

    Filter by `?step_execution=<id>` or `?substep=<id>` to scope queries.

    Read-only on purpose. A completion is the record that a named person did a
    piece of work, and `submit_substep` is the only thing that writes one: it
    stamps the signer, the server's time, the verification method and the IP,
    and enforces the password when the substep requires a verified signature.
    As a full ModelViewSet this endpoint let anyone holding `change_substepcompletion`
    — every staff role — PATCH those same fields directly, naming someone else as
    signer with `verification_method='PASSWORD'` at a time of their choosing. Nothing
    in the app ever wrote a completion this way; only `void` mutates one.
    """

    # `void` retracts a record of work someone else signed, so it is gated on
    # its own marker perm (QA Inspector / QA Manager / Tenant Admin) rather
    # than the CRUD default. As a POST the default would be
    # `add_substepcompletion`, which every role holds — including the Operator
    # whose completion is being invalidated — and `change_` is no narrower.
    # Same independence argument as `sign_off_fpi`. crud_exempt_actions keeps
    # the add gate from also applying, which would silently re-widen it to
    # everyone.
    crud_exempt_actions = {'void'}
    action_permissions = {
        'void': ['void_substepcompletion'],
    }

    queryset = SubstepCompletion.unscoped.select_related(
        'step_execution', 'batch_execution', 'substep', 'completed_by', 'voided_by',
    )
    serializer_class = SubstepCompletionSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    # `step_execution` takes `in` as well as `exact` because a traveler row is
    # per-step: rework means several executions sit behind one row, and QA
    # reviews the completions across all of them together.
    #
    # `batch_execution` is filterable for the same reason it exists at all: a
    # BATCH-scope completion has no step_execution, so a caller filtering only
    # on step_execution sees none of the shared-cycle work and would conclude
    # nothing was recorded.
    filterset_fields = {
        'step_execution': ['exact', 'in'],
        'batch_execution': ['exact', 'in'],
        'substep': ['exact'],
        'completed_by': ['exact'],
        'marked_not_applicable': ['exact'],
    }
    ordering_fields = ['completed_at']
    ordering = ['-completed_at']

    @extend_schema(
        # Undeclared, the body fell back to SubstepCompletionRequest, which
        # requires substep / completed_by / the whole row. The generated
        # client rejected `{reason}` client-side, so QA could never void a
        # completion -- no request was even sent.
        request=inline_serializer(
            name='SubstepCompletionVoidRequest',
            fields={'reason': drf_serializers.CharField()},
        ),
        responses={
            200: inline_serializer(
                name='SubstepCompletionVoidResponse',
                fields={
                    'id': drf_serializers.CharField(),
                    'is_voided': drf_serializers.BooleanField(),
                    'voided_at': drf_serializers.CharField(allow_null=True),
                    'void_reason': drf_serializers.CharField(),
                },
            ),
            400: OpenApiTypes.OBJECT,
        },
    )
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
        # Voiding also supersedes the report the capture recorded: it stays as recorded,
        # and the re-capture writes a new one (services/qms/report_supersede.py).
        from Tracker.services.qms.report_supersede import void_completion
        void_completion(completion, request.user, reason)
        return Response({
            'id': str(completion.id),
            'is_voided': completion.is_voided,
            'voided_at': completion.voided_at.isoformat() if completion.voided_at else None,
            'void_reason': completion.void_reason,
        })


class SubstepGateCompletionViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Per-node attestation / signature gate completions.

    An attestation is signed by whoever is logged in, when they sign, from where
    they are — all set here, none taken from the request body. Once signed it
    can't be edited or deleted (no PUT/PATCH/DELETE). No identity re-verification
    happens on this endpoint, so verification_method stays NONE."""

    queryset = SubstepGateCompletion.unscoped.select_related(
        'step_execution', 'substep', 'completed_by',
    )
    serializer_class = SubstepGateCompletionSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['step_execution', 'substep', 'node_id', 'completed_by']
    ordering_fields = ['completed_at']
    ordering = ['-completed_at']
    http_method_names = ['get', 'post', 'delete', 'head', 'options']
    # Clearing is the service's call (own signature always; someone else's needs
    # `clear_gate_signature`), so the CRUD delete gate must not also apply — it
    # would be `delete_substepgatecompletion`, which nobody holds.
    crud_exempt_actions = {'destroy'}

    def perform_create(self, serializer):
        """Sign one block. A `confirm` block is a tick and records no password; a
        `signature` block draws and re-enters the signer's own password, enforced in
        `services.dwi.gate_signature.sign_gate`."""
        from django.core.exceptions import ValidationError as DjangoValidationError
        from rest_framework.exceptions import ValidationError as DRFValidationError
        from Tracker.services.dwi.gate_signature import sign_gate
        from Tracker.throttling import get_client_ip

        data = serializer.validated_data
        substep = data.get('substep')
        node_id = str(data.get('node_id') or '')
        # Exactly one of the two: a part's run or a batch's. Without either it hit the
        # exactly-one check constraint as a 500.
        if bool(data.get('step_execution')) == bool(data.get('batch_execution')):
            raise DRFValidationError(
                {'detail': "Sign against the part's run or the batch's — exactly one."})
        from Tracker.services.dwi.gate_signature import signature_node_ids
        if substep is not None and node_id in signature_node_ids(substep):
            try:
                gate = sign_gate(
                    substep=substep,
                    step_execution=data.get('step_execution'),
                    # A batch substep's signature belongs to the batch: dropping it left
                    # the row with no execution at all (500, "Could not sign").
                    batch_execution=data.get('batch_execution'),
                    node_id=node_id,
                    user=self.request.user,
                    signature_data=data.get('signature_data'),
                    password=self.request.data.get('password'),
                    ip_address=get_client_ip(self.request) or None,
                )
            except DjangoValidationError as exc:
                raise DRFValidationError({'detail': '; '.join(exc.messages)})
            serializer.instance = gate
            return
        # A check-off block: no password, so the service isn't involved. The signer,
        # the time and the method are still the server's — none is accepted from the
        # body (see the serializer's read_only_fields). The node must be a real
        # attestation block on this substep, so the endpoint can't be used to mint
        # gate records against ids that aren't in the instructions.
        from Tracker.services.dwi.gate_signature import attestation_nodes
        if substep is None or node_id not in attestation_nodes(substep):
            raise DRFValidationError(
                {'detail': "That block isn't an attestation on this substep."})
        serializer.save(completed_by=self.request.user, ip_address=get_client_ip(self.request) or None)

    @extend_schema(
        request=inline_serializer(
            name='ClearGateSignatureRequest',
            fields={
                # A supervisor clearing someone else's signature is a second person at
                # the operator's terminal, not the session user — one browser, one login.
                'email': drf_serializers.EmailField(required=False, allow_blank=True),
                'password': drf_serializers.CharField(required=False, allow_blank=True,
                                                      write_only=True),
            },
        ),
        responses={204: None, 400: OpenApiTypes.OBJECT},
        description="Undo a signature that hasn't been submitted yet. Your own needs "
                    "nothing. Someone else's needs a supervisor's own email and password, "
                    "checked against `clear_gate_signature` — the case where the signer "
                    "has gone off shift. Once the substep is submitted its signatures "
                    "stand; QA voids the completion instead.",
    )
    def destroy(self, request, *args, **kwargs):
        from django.core.exceptions import ValidationError as DjangoValidationError
        from Tracker.services.dwi.gate_signature import clear_gate_signature
        try:
            clear_gate_signature(
                self.get_object(), request.user,
                email=request.data.get('email', '') or '',
                password=request.data.get('password', '') or '',
            )
        except DjangoValidationError as exc:
            return Response({'detail': '; '.join(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


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

    def perform_create(self, serializer):
        """Stamp the operator and enforce the disjoint-membership invariant
        (3c): a part may be in at most one open batch per step. Multiple open
        batches per (WO, step) are allowed (furnace/wash loads) as long as
        their parts don't overlap."""
        from django.core.exceptions import ValidationError as DjangoValidationError
        from django.db import transaction
        from rest_framework.exceptions import ValidationError as DRFValidationError
        from Tracker.models import Parts
        from Tracker.services.dwi.batch_lifecycle import assert_no_open_batch_overlap

        step = serializer.validated_data.get('step')
        parts = serializer.validated_data.get('parts') or []
        part_ids = [getattr(p, 'id', p) for p in parts]
        try:
            # Lock the candidate part rows, then check overlap, then create —
            # all in one transaction. Two concurrent creates that share a part
            # serialize on its lock; the loser's overlap check then sees the
            # winner's committed open batch and is rejected. Without this the
            # disjoint-membership invariant is a check-then-act race (no DB
            # constraint backs it).
            with transaction.atomic():
                if part_ids:
                    # Materialize the locked rows (FOR UPDATE) before the check.
                    locked = list(Parts.objects.select_for_update().filter(id__in=part_ids))
                    # A held unit isn't loadable: sealing the load would carry it past
                    # its hold (a core awaiting the customer's answer, a quarantined
                    # part) — Operator walk 2026-10-21.
                    held = sorted(p.ERP_id for p in locked if p.part_status in ("QUARANTINED", "ON_HOLD"))
                    if held:
                        raise DjangoValidationError(
                            f"{', '.join(held)} {'is' if len(held) == 1 else 'are'} held "
                            "(quarantined or on hold) and can't go into a load.")
                assert_no_open_batch_overlap(step=step, parts=parts)
                serializer.save(started_by=self.request.user)
        except DjangoValidationError as exc:
            raise DRFValidationError({'detail': exc.messages})

    @extend_schema(
        request=None,
        responses=inline_serializer(
            name='BatchSealResponse',
            fields={
                'batch_id': drf_serializers.CharField(),
                'sealed_at': drf_serializers.CharField(),
            },
        ),
    )
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

    @extend_schema(
        request=inline_serializer(name='RemoveBatchPartRequest', fields={
            'part': drf_serializers.UUIDField(), 'reason': drf_serializers.CharField()}),
        responses={200: inline_serializer(name='RemoveBatchPartResponse', fields={
            'batch_id': drf_serializers.UUIDField(), 'part': drf_serializers.UUIDField(),
            'outcome': drf_serializers.ChoiceField(
                choices=['REMOVED', 'ROLLBACK_PENDING'],
                help_text="ROLLBACK_PENDING: the part had moved on, and stepping it back was "
                          "sent for approval — take it out again once that's done.")})},
        description="Take the wrong part out of a sealed batch, with a reason. It goes back "
                    "to the batch's step and its batch-done work no longer counts for it. "
                    "No unseal.",
    )
    @action(detail=True, methods=['post'], url_path='remove-part')
    def remove_part(self, request, pk=None):
        from django.core.exceptions import ValidationError
        from Tracker.models import Parts
        from Tracker.services.dwi.batch_lifecycle import remove_part_from_sealed_batch
        batch = self.get_object()
        part = Parts.objects.filter(pk=request.data.get('part')).first()  # tenant-safe: .objects auto-scopes
        if part is None:
            return Response({'detail': 'Part not found.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            outcome = remove_part_from_sealed_batch(batch=batch, part=part, user=request.user,
                                                    reason=request.data.get('reason', ''))
        except ValidationError as exc:
            return Response({'detail': '; '.join(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'batch_id': str(batch.id), 'part': str(part.id), 'outcome': outcome})


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
    # `step_execution__part__work_order` is what the supervisor's pending-
    # reconciliation panel filters on. django-filter drops any param not
    # named here, so without it that panel was silently listing every PENDING
    # decision in the tenant rather than the one work order's.
    filterset_fields = [
        'step_execution', 'substep', 'outcome',
        'step_execution__part__work_order',
    ]
    ordering_fields = ['decided_at']
    ordering = ['-decided_at']

    # `reconcile` is a POST, so the default CRUD gate would demand
    # `add_samplingdecision` — a system-written perm granted to NO role
    # (decisions are engine-authored), which 403'd reconciliation for
    # everyone. It's a supervisory runtime action, not decision authoring:
    # exempt it from the CRUD gate and require the floor-supervision perm
    # instead (same pattern as SubstepViewSet.submit).
    crud_exempt_actions = {'reconcile'}
    action_permissions = {'reconcile': ['change_stepexecution']}

    def get_queryset(self):
        # Default to live decisions only (hide superseded rows). Pass
        # `?include_superseded=1` to get the full audit trail.
        qs = super().get_queryset()
        if self.request.query_params.get('include_superseded') != '1':
            qs = qs.filter(superseded_by__isnull=True)
        return qs

    @extend_schema(
        request=inline_serializer(
            name='SamplingDecisionReconcileRequest',
            fields={
                'work_order_id': drf_serializers.UUIDField(),
                'step_id': drf_serializers.UUIDField(required=False),
            },
        ),
        # Undeclared, the response fell back to SamplingDecision -- a
        # decision row, not this summary -- so the client rejected every
        # successful reconcile after the server had already done the work.
        responses={
            200: inline_serializer(
                name='SamplingDecisionReconcileResponse',
                fields={
                    'reconciled': drf_serializers.IntegerField(),
                    'now_selected': drf_serializers.IntegerField(),
                    'now_deselected': drf_serializers.IntegerField(),
                    'still_pending': drf_serializers.IntegerField(),
                },
            ),
            400: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
    )
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

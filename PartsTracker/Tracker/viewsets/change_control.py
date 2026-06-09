"""
Viewsets for Change Control artifacts (PCR / PCO / PCN).

Lifecycle transitions are exposed as @action endpoints (POST). Direct
PUT/PATCH is limited to fields safe to edit while the artifact is in
its initial DRAFT state — state machine transitions go through the
service layer via the action endpoints.

Mode resolution:
- The tenant's `change_control_mode` setting determines whether we
  pass SIMPLIFIED or REGULATED to lifecycle services.
- Until the Tenant model gains the field (separate work item), we
  default to SIMPLIFIED. Override by setting `_change_control_mode`
  on the request via middleware or by including a `mode` query param
  for testing.
"""
from __future__ import annotations

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from Tracker.models import (
    ProcessChangeNotice,
    ProcessChangeOrder,
    ProcessChangeRequest,
)
from Tracker.serializers.change_control import (
    PcnClosePayloadSerializer,
    PcoAuthorPayloadSerializer,
    PcoCancelPayloadSerializer,
    PcoImplementPayloadSerializer,
    PcrCancelPayloadSerializer,
    PcrRejectPayloadSerializer,
    ProcessChangeNoticeSerializer,
    ProcessChangeOrderSerializer,
    ProcessChangeRequestSerializer,
)
from Tracker.services.change_control import (
    ChangeControlMode,
    approve_pcr,
    approve_pco,
    author_pco,
    cancel_pco,
    cancel_pcr,
    close_pcn,
    implement_pco,
    mark_pco_approved,
    next_artifact_number,
    reject_pcr,
    release_pcn,
    submit_pcr,
)
from Tracker.viewsets.base import TenantScopedMixin


def _resolve_mode(request) -> str:
    """Pick SIMPLIFIED vs REGULATED for lifecycle services.

    Reads the tenant's configured mode. Defaults to SIMPLIFIED until the
    `Tenant.change_control_mode` field lands — at which point this
    becomes `request.tenant.change_control_mode`.

    No query-param override: SIMPLIFIED auto-approves PCOs at PCR
    approval, so accepting a client-supplied mode flag would let any
    tenant user bypass the REGULATED signature workflow simply by
    appending `?mode=SIMPLIFIED` to a request.
    """
    # TODO: return request.tenant.change_control_mode once the field exists.
    return ChangeControlMode.SIMPLIFIED


def _bad_request(message: str) -> Response:
    return Response({'detail': str(message)}, status=status.HTTP_400_BAD_REQUEST)


def _latest_approval_request_for(content_object):
    """Return the most recent `ApprovalRequest` for a content object.

    Used by REGULATED-mode gates that need to confirm signatures are
    in before allowing the finalizer endpoint to flip artifact state.
    """
    from django.contrib.contenttypes.models import ContentType
    from Tracker.models import ApprovalRequest
    ct = ContentType.objects.get_for_model(type(content_object))
    # tenant-safe: SecureManager auto-scopes via TenantMiddleware.
    return (
        ApprovalRequest.objects.filter(content_type=ct, object_id=str(content_object.id))
        .order_by('-requested_at')
        .first()
    )


# ---------------------------------------------------------------------------
# ProcessChangeRequest viewset
# ---------------------------------------------------------------------------

class ProcessChangeRequestViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD + lifecycle actions for ProcessChangeRequest.

    Lifecycle endpoints:
        POST /api/process-change-requests/{id}/submit/
        POST /api/process-change-requests/{id}/approve/
        POST /api/process-change-requests/{id}/reject/   {reason}
        POST /api/process-change-requests/{id}/cancel/   {reason?}
    """

    queryset = ProcessChangeRequest.unscoped.all().select_related(
        'target_process', 'created_by', 'submitted_by',
    )
    serializer_class = ProcessChangeRequestSerializer
    filterset_fields = ['status', 'target_process', 'draft_process_version', 'priority']
    ordering_fields = ['created_at', 'updated_at', 'priority']
    ordering = ['-created_at']

    # Custom action perms — TenantModelPermissions only maps default CRUD
    # methods. `propose` forks a DRAFT Process AND creates a PCR row, so
    # require both perms.
    action_permissions = {
        'propose': ['add_processchangerequest', 'add_processes'],
        'submit': ['change_processchangerequest'],
        'approve': ['change_processchangerequest'],
        'reject': ['change_processchangerequest'],
        'cancel': ['change_processchangerequest'],
    }

    def perform_create(self, serializer):
        """Auto-generate artifact_number on create."""
        tenant = self.tenant
        artifact_number = next_artifact_number(
            tenant_id=tenant.id,
            artifact_type='PCR',
        )
        serializer.save(
            tenant=tenant,
            artifact_number=artifact_number,
            created_by=self.request.user,
        )

    @action(detail=True, methods=['post'], url_path='submit')
    def submit(self, request, pk=None):
        pcr = self.get_object()
        try:
            submit_pcr(pcr, user=request.user)
        except ValueError as exc:
            return _bad_request(exc)
        pcr.refresh_from_db()
        return Response(self.get_serializer(pcr).data)

    @extend_schema(
        request=inline_serializer(
            name="ProposeProcessChangeRequest",
            fields={
                "target_process_id": serializers.UUIDField(),
                "title": serializers.CharField(required=False, allow_blank=True),
                "proposed_change": serializers.CharField(required=False, allow_blank=True),
                "justification": serializers.CharField(required=False, allow_blank=True),
                "risk_analysis": serializers.CharField(required=False, allow_blank=True),
                "priority": serializers.CharField(required=False),
                "customer_notification_required": serializers.BooleanField(required=False),
            },
        ),
        responses={
            201: inline_serializer(
                name="ProposeProcessChangeResponse",
                fields={
                    "pcr_id": serializers.UUIDField(),
                    "draft_process_id": serializers.UUIDField(),
                    "artifact_number": serializers.CharField(),
                },
            ),
            400: {"description": "Target process is not in APPROVED status — only approved processes can be forked into a PCR draft."},
        },
        description=(
            "Start a PCR by forking a DRAFT process version up-front. "
            "The engineer is then redirected to the DRAFT's editor; they "
            "make node-level edits and submit the PCR with the diff "
            "attached. Replaces the legacy text-only PCR-first flow."
        ),
        tags=["Change Control"],
    )
    @action(detail=False, methods=["post"], url_path="propose")
    def propose(self, request):
        """Engineer entry point — fork a DRAFT and create a linked PCR row.

        Multiple open PCRs against the same target_process are allowed —
        conflicts between drafts are resolved at approval time by the
        rebase service (see `services/change_control/rebase.py`).
        """
        from Tracker.services.change_control.process_change import propose_process_change
        from Tracker.models import Processes

        target_id = request.data.get("target_process_id")
        if not target_id:
            return _bad_request(ValueError("target_process_id is required."))

        try:
            # tenant-safe: SecureManager auto-scopes via TenantMiddleware
            # ContextVar; explicit cross-tenant check follows below.
            target = Processes.objects.get(id=target_id)
        except Processes.DoesNotExist:
            return Response({"detail": "Target process not found."}, status=status.HTTP_404_NOT_FOUND)

        # Defense in depth: SecureManager already scopes by tenant, but
        # assert explicitly so an SecureManager fallback (e.g. superuser
        # bypass) can't end up forking a foreign tenant's process.
        if target.tenant_id != self.tenant.id:
            raise PermissionDenied("Target process belongs to a different tenant.")

        try:
            pcr, draft = propose_process_change(
                target,
                user=request.user,
                title=request.data.get("title") or "",
                proposed_change=request.data.get("proposed_change") or "",
                justification=request.data.get("justification") or "",
                risk_analysis=request.data.get("risk_analysis") or "",
                priority=request.data.get("priority") or "NORMAL",
                customer_notification_required=bool(
                    request.data.get("customer_notification_required", False)
                ),
            )
        except ValueError as exc:
            return _bad_request(exc)

        return Response(
            {
                "pcr_id": str(pcr.id),
                "draft_process_id": str(draft.id),
                "artifact_number": pcr.artifact_number,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        from Tracker.services.change_control.process_change import PcrRebaseConflict
        from Tracker.services.change_control.process_change import ChangeControlMode
        pcr = self.get_object()
        mode = _resolve_mode(request)

        # REGULATED mode: this endpoint is a finalizer, not an override.
        # The PCR's ApprovalRequest must already be APPROVED by collected
        # signatures. In practice the auto-cascade in
        # `apply_approval_decision_to_content_object` fires
        # `approve_pcr` as soon as the AR transitions to APPROVED, so by
        # the time clients call this they typically find PCR.status
        # already APPROVED. Treat that as idempotent confirm rather than
        # a hard 400 — return the existing PCO so the client can keep
        # one code path for "approve & fetch result" in both modes.
        if mode == ChangeControlMode.REGULATED:
            ar = _latest_approval_request_for(pcr)
            if ar is None:
                return Response(
                    {'detail': 'No approval request exists for this PCR. Submit it first.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if ar.status != 'APPROVED':
                return Response(
                    {
                        'detail': (
                            'Approval signatures are still pending. '
                            'Wait for all required approvers to respond.'
                        ),
                        'approval_request_id': str(ar.id),
                        'approval_request_status': ar.status,
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        if pcr.status == ProcessChangeRequest.Status.APPROVED:
            existing_pco = getattr(pcr, 'order', None)
            if existing_pco is not None:
                return Response({
                    'pcr': self.get_serializer(pcr).data,
                    'pco': ProcessChangeOrderSerializer(
                        existing_pco, context=self.get_serializer_context(),
                    ).data,
                    'rebase': {'rebased': False},
                    'idempotent': True,
                })

        try:
            pco = approve_pcr(pcr, user=request.user, mode=mode)
        except ValueError as exc:
            return _bad_request(exc)
        except PcrRebaseConflict as exc:
            return Response(
                {
                    'detail': (
                        'This PCR conflicts with changes that were approved '
                        'while it was open. Resolve the conflicting fields '
                        'and re-submit.'
                    ),
                    'baseline_version_id': exc.conflict.baseline_version_id,
                    'current_approved_id': exc.conflict.current_approved_id,
                    'conflicts': [
                        {
                            'step_identity_id': c.step_identity_id,
                            'step_name': c.step_name,
                            'field': c.field,
                            'intent_value': c.intent_value,
                            'approved_value': c.approved_value,
                        }
                        for c in exc.conflict.conflicts
                    ],
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response({
            'pcr': self.get_serializer(pcr).data,
            'pco': ProcessChangeOrderSerializer(pco, context=self.get_serializer_context()).data,
            # When the rebase actually moved the draft onto a newer
            # baseline (not a no-op), surface the metadata so the UI
            # can toast "your draft was re-anchored." `_rebase_metadata`
            # is attached by `approve_pcr` after rebase.
            'rebase': getattr(pco, '_rebase_metadata', {'rebased': False}),
        })

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        pcr = self.get_object()
        payload = PcrRejectPayloadSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            reject_pcr(pcr, user=request.user, reason=payload.validated_data['reason'])
        except ValueError as exc:
            return _bad_request(exc)
        pcr.refresh_from_db()
        return Response(self.get_serializer(pcr).data)

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        pcr = self.get_object()
        payload = PcrCancelPayloadSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            cancel_pcr(
                pcr,
                user=request.user,
                reason=payload.validated_data.get('reason', ''),
            )
        except ValueError as exc:
            return _bad_request(exc)
        pcr.refresh_from_db()
        return Response(self.get_serializer(pcr).data)


# ---------------------------------------------------------------------------
# ProcessChangeOrder viewset
# ---------------------------------------------------------------------------

class ProcessChangeOrderViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD + lifecycle actions for ProcessChangeOrder.

    POs are created indirectly via PCR approval — the POST endpoint
    is disallowed; PCO comes into existence as a side-effect of
    approving its parent PCR.

    Lifecycle endpoints:
        POST /api/process-change-orders/{id}/author/    {implementation_plan?, effective_date?}
        POST /api/process-change-orders/{id}/approve/   (REGULATED — creates ApprovalRequest)
        POST /api/process-change-orders/{id}/mark-approved/  (used post-signature collection)
        POST /api/process-change-orders/{id}/implement/ {migration_disposition, ...}
        POST /api/process-change-orders/{id}/cancel/    {reason?}
    """

    queryset = ProcessChangeOrder.unscoped.all().select_related(
        'request',
        'request__target_process',
        'draft_process_version',
        'approved_by',
        'implemented_by',
    )
    serializer_class = ProcessChangeOrderSerializer
    filterset_fields = ['status', 'request', 'migration_disposition']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    action_permissions = {
        'author': ['change_processchangeorder'],
        'approve': ['change_processchangeorder'],
        'mark_approved': ['change_processchangeorder'],
        'implement': ['change_processchangeorder'],
        'cancel': ['change_processchangeorder'],
        'affected_workorders': ['view_processchangeorder'],
    }

    # PCOs are created indirectly via PCR approval. POST/PUT/DELETE on
    # the collection or individual rows are blocked; only PATCH (limited
    # field set) and the @action lifecycle endpoints are allowed.
    def create(self, request, *args, **kwargs):
        return Response(
            {"detail": "PCOs are created by approving a PCR, not via direct POST."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def update(self, request, *args, **kwargs):
        return Response(
            {"detail": "Full replace via PUT is not allowed; use PATCH or @action lifecycle endpoints."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "PCOs cannot be deleted; cancel them via the cancel action instead."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=True, methods=['post'], url_path='author')
    def author(self, request, pk=None):
        pco = self.get_object()
        payload = PcoAuthorPayloadSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            author_pco(
                pco,
                user=request.user,
                implementation_plan=payload.validated_data.get('implementation_plan'),
                effective_date=payload.validated_data.get('effective_date'),
            )
        except ValueError as exc:
            return _bad_request(exc)
        pco.refresh_from_db()
        return Response(self.get_serializer(pco).data)

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        """Submit PCO for approval (REGULATED mode — creates an
        ApprovalRequest). Once signatures are collected, call
        `mark-approved` to flip the PCO state."""
        pco = self.get_object()
        try:
            approval_request = approve_pco(pco, user=request.user)
        except ValueError as exc:
            return _bad_request(exc)
        return Response({
            'pco': self.get_serializer(pco).data,
            'approval_request_id': str(approval_request.id),
        })

    @action(detail=True, methods=['post'], url_path='mark-approved')
    def mark_approved(self, request, pk=None):
        """Finalize PCO approval after signatures are collected.
        Enforces separation of duties (approver != PCO author)."""
        pco = self.get_object()
        try:
            mark_pco_approved(pco, user=request.user)
        except ValueError as exc:
            return _bad_request(exc)
        pco.refresh_from_db()
        return Response(self.get_serializer(pco).data)

    @action(detail=True, methods=['get'], url_path='affected-workorders')
    def affected_workorders(self, request, pk=None):
        """Per-WO impact summary for the PCO migration picker.

        Returns a list of in-flight WOs with metadata (status, priority,
        total in-flight parts, parts whose current step is touched by
        the PCR diff). Drives the `MIGRATE_SELECTED` picker.
        """
        from Tracker.services.change_control.impact_analysis import (
            affected_workorders_with_impact,
        )
        pco = self.get_object()
        diff = getattr(pco.request, 'proposed_change_diff', None) or {}
        rows = affected_workorders_with_impact(
            target_process=pco.request.target_process,
            proposed_change_diff=diff,
        )
        return Response({'results': rows})

    @action(detail=True, methods=['post'], url_path='implement')
    def implement(self, request, pk=None):
        pco = self.get_object()
        payload = PcoImplementPayloadSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        mode = _resolve_mode(request)
        try:
            pcn = implement_pco(
                pco,
                user=request.user,
                migration_disposition=payload.validated_data['migration_disposition'],
                migration_reason=payload.validated_data.get('migration_reason', ''),
                selected_workorder_ids=payload.validated_data.get('selected_workorder_ids') or None,
                mode=mode,
            )
        except ValueError as exc:
            return _bad_request(exc)
        pco.refresh_from_db()
        return Response({
            'pco': self.get_serializer(pco).data,
            'pcn': ProcessChangeNoticeSerializer(pcn, context=self.get_serializer_context()).data,
        })

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        pco = self.get_object()
        payload = PcoCancelPayloadSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            cancel_pco(
                pco,
                user=request.user,
                reason=payload.validated_data.get('reason', ''),
            )
        except ValueError as exc:
            return _bad_request(exc)
        pco.refresh_from_db()
        return Response(self.get_serializer(pco).data)


# ---------------------------------------------------------------------------
# ProcessChangeNotice viewset
# ---------------------------------------------------------------------------

class ProcessChangeNoticeViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """CRUD + lifecycle actions for ProcessChangeNotice.

    PCNs are created indirectly via PCO implementation — direct POST
    is disallowed. Lifecycle endpoints:

        POST /api/process-change-notices/{id}/release/  (REGULATED)
        POST /api/process-change-notices/{id}/close/    {closure_evidence}
    """

    queryset = ProcessChangeNotice.unscoped.all().select_related(
        'order',
        'order__request',
        'order__request__target_process',
        'released_by',
        'closed_by',
    )
    serializer_class = ProcessChangeNoticeSerializer
    filterset_fields = ['status', 'order']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    action_permissions = {
        'release': ['change_processchangenotice'],
        'close': ['change_processchangenotice'],
    }

    def create(self, request, *args, **kwargs):
        return Response(
            {"detail": "PCNs are created by implementing a PCO, not via direct POST."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def update(self, request, *args, **kwargs):
        return Response(
            {"detail": "Full replace via PUT is not allowed; use PATCH or @action lifecycle endpoints."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "PCNs cannot be deleted; the artifact is part of the change-control audit trail."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=True, methods=['post'], url_path='release')
    def release(self, request, pk=None):
        pcn = self.get_object()
        try:
            release_pcn(pcn, user=request.user)
        except ValueError as exc:
            return _bad_request(exc)
        pcn.refresh_from_db()
        return Response(self.get_serializer(pcn).data)

    @action(detail=True, methods=['post'], url_path='close')
    def close(self, request, pk=None):
        pcn = self.get_object()
        payload = PcnClosePayloadSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            close_pcn(
                pcn,
                user=request.user,
                closure_evidence=payload.validated_data['closure_evidence'],
            )
        except ValueError as exc:
            return _bad_request(exc)
        pcn.refresh_from_db()
        return Response(self.get_serializer(pcn).data)

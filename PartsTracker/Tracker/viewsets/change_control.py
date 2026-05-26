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

from rest_framework import status, viewsets
from rest_framework.decorators import action
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

    Order of precedence:
    1. ?mode=REGULATED query param (testing override)
    2. tenant.change_control_mode (when Tenant gains the field)
    3. Default to SIMPLIFIED

    TODO: replace step 2 once `Tenant.change_control_mode` field lands.
    """
    override = request.query_params.get('mode', '').upper()
    if override in (ChangeControlMode.SIMPLIFIED, ChangeControlMode.REGULATED):
        return override
    return ChangeControlMode.SIMPLIFIED


def _bad_request(message: str) -> Response:
    return Response({'detail': str(message)}, status=status.HTTP_400_BAD_REQUEST)


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
    filterset_fields = ['status', 'target_process', 'priority']
    ordering_fields = ['created_at', 'updated_at', 'priority']
    ordering = ['-created_at']

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

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        pcr = self.get_object()
        mode = _resolve_mode(request)
        try:
            pco = approve_pcr(pcr, user=request.user, mode=mode)
        except ValueError as exc:
            return _bad_request(exc)
        return Response({
            'pcr': self.get_serializer(pcr).data,
            'pco': ProcessChangeOrderSerializer(pco, context=self.get_serializer_context()).data,
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
    http_method_names = ['get', 'patch', 'head', 'options']
    # No POST — PCOs are created by approving a PCR, not via direct API.

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
    http_method_names = ['get', 'patch', 'head', 'options']

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

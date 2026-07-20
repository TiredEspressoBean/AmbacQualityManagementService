"""Shift-note API — CRUD + acknowledge + the operator's active feed.

Delegates writes to services/mes/shift_notes. CRUD perms gate authoring
(add/change/delete_shiftnote → leads); reading (view_shiftnote) is broad so the
floor can see notes. `acknowledge` is CRUD-exempt: an operator acking a note is
not authoring one, so it must not demand add_shiftnote.
"""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from Tracker.models import ShiftNote
from Tracker.serializers.shift_notes import ShiftNoteSerializer
from Tracker.services.mes.shift_notes import (
    acknowledge_shift_note,
    active_shift_notes_for_user,
    retract_shift_note,
)
from Tracker.viewsets.base import TenantScopedMixin


class ShiftNoteViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """Human-authored floor handoff notes. Retract = DELETE (soft void)."""

    queryset = ShiftNote.unscoped.all().select_related("author", "work_order")
    serializer_class = ShiftNoteSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["priority", "work_order", "is_voided", "author"]
    ordering_fields = ["created_at", "updated_at", "priority"]
    ordering = ["-created_at"]

    # These custom actions skip the CRUD gate (POST → add_shiftnote): acking
    # and reading one's own feed are not authoring, and retract is a change
    # (gated below), not a create. `active` is a /me-style feed — any
    # authenticated user; `retract` requires change_shiftnote (the author tier).
    crud_exempt_actions = {"acknowledge", "active", "retract"}
    action_permissions = {"retract": ["change_shiftnote"]}

    def perform_create(self, serializer):
        serializer.save(tenant=self.tenant, author=self.request.user)

    def perform_destroy(self, instance):
        # Defensive: if DELETE were ever reachable, soft-void rather than
        # hard-delete. The real retract path is the `retract` action below.
        retract_shift_note(instance, user=self.request.user)

    @action(detail=False, methods=["get"], url_path="active")
    def active(self, request):
        """The notes this operator should see now (audience ∩ effective ∩
        un-acked). Paginated to match the list contract."""
        notes = active_shift_notes_for_user(request.user, tenant=self.tenant)
        page = self.paginate_queryset(notes)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        return Response(self.get_serializer(notes, many=True).data)

    @action(detail=True, methods=["post"], url_path="acknowledge")
    def acknowledge(self, request, pk=None):
        """Record that this user saw the note (idempotent)."""
        note = self.get_object()
        acknowledge_shift_note(note, user=request.user)
        return Response(self.get_serializer(note).data)

    @action(detail=True, methods=["post"], url_path="retract")
    def retract(self, request, pk=None):
        """Retract (void) a note. Author-tier (change_shiftnote)."""
        note = self.get_object()
        retract_shift_note(note, user=request.user, reason=request.data.get("reason", ""))
        return Response(self.get_serializer(note).data)

# viewsets/dms.py - DMS ViewSets (Optional AI/LLM Module)
"""
This file contains AI/LLM-specific viewsets for the DMS module.

ViewSets:
- ChatSessionViewSet: Manages AI chat sessions for users
- Future: DocChunkViewSet, SemanticSearchViewSet, EmbeddingManagementViewSet
"""

from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from Tracker.models.dms import ChatSession
from Tracker.serializers.dms import ChatSessionSerializer
from .base import TenantScopedMixin


class ChatSessionViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing AI chat sessions.

    Users can only see and manage their own chat sessions.
    Provides list, create, retrieve, update, and delete operations.
    """
    queryset = ChatSession.objects.all()
    serializer_class = ChatSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return only the current user's chat sessions, ordered by most recent."""
        if getattr(self, 'swagger_fake_view', False):
            return ChatSession.objects.none()
        # Apply tenant scoping first, then filter to user's sessions
        qs = super().get_queryset()
        return qs.filter(user=self.request.user).order_by('-updated_at')

    def perform_create(self, serializer):
        """Set user to current user when creating a session."""
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        """Update the updated_at timestamp when session is modified."""
        serializer.save(updated_at=timezone.now())

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive a chat session."""
        session = self.get_object()
        session.is_archived = True
        session.save()
        return Response(ChatSessionSerializer(session).data)

    @action(detail=True, methods=['post'])
    def unarchive(self, request, pk=None):
        """Unarchive a chat session."""
        session = self.get_object()
        session.is_archived = False
        session.save()
        return Response(ChatSessionSerializer(session).data)

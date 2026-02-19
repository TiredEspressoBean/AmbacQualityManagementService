"""
Document Management System (DMS) - AI/LLM Module

This optional module provides AI-powered document intelligence features including:
- Vector embeddings for semantic search
- Document chunking for LLM context windows
- Retrieval-Augmented Generation (RAG) support
- Chat session history for AI conversations

This module can be disabled/not installed for systems that don't need AI features.
The core Documents model is in core.py and is always available.

Models:
    - DocChunk: Text chunks extracted from documents with AI embeddings
    - ChatSession: User chat session history for AI conversations

Dependencies:
    - Requires pgvector extension in PostgreSQL
    - Requires AI_EMBED_DIM setting in Django settings
    - Requires Celery for async embedding tasks

Note: SecureManager and Documents are in core.py
"""

from django.conf import settings
from django.db import models
from django.utils import timezone
from pgvector.django import VectorField

from .core import SecureManager


class DocChunk(models.Model):
    """
    Represents a text chunk extracted from a Document with AI embedding.

    This model stores portions of document text along with their vector embeddings
    for semantic search and retrieval. Chunks are created from documents to enable
    efficient AI-powered document analysis and searching.

    This is part of the optional DMS (AI) module and can be disabled if AI features
    are not needed.

    Fields:
        doc (ForeignKey): Reference to the parent Document (in core.py)
        embedding (VectorField): Vector embedding of the chunk text
        preview_text (str): First 300 chars of the chunk for display
        full_text (str): Complete text of the chunk
        span_meta (JSONField): Metadata about the chunk's position/span
    """
    doc = models.ForeignKey('Tracker.Documents', on_delete=models.CASCADE, related_name='chunks')
    embedding = VectorField(dimensions=settings.AI_EMBED_DIM)  # uses settings
    preview_text = models.TextField(blank=True)
    full_text = models.TextField(blank=True)
    span_meta = models.JSONField(default=dict, blank=True)

    objects = SecureManager()

    class Meta:
        db_table = 'doc_chunks'
        indexes = [models.Index(fields=['doc'])]


class ChatSession(models.Model):
    """
    Represents an AI chat session for a user.

    Stores the reference to LangGraph thread_id to enable persistent
    chat history across browser sessions. Users can have multiple chat
    sessions and switch between them.

    Fields:
        tenant (ForeignKey): Tenant for data isolation (derived from user on creation)
        user (ForeignKey): The user who owns this chat session
        langgraph_thread_id (str): The LangGraph thread ID for this session
        title (str): Display title for the session (auto-generated or user-provided)
        created_at (datetime): When the session was created
        updated_at (datetime): When the session was last used/modified
    """
    tenant = models.ForeignKey(
        'Tracker.Tenant',
        on_delete=models.CASCADE,
        null=True,  # Nullable for migration, backfill from user.tenant
        blank=True,
        related_name='chat_sessions',
        help_text="Tenant for data isolation (auto-set from user on creation)"
    )
    user = models.ForeignKey(
        'Tracker.User',
        on_delete=models.CASCADE,
        related_name='chat_sessions'
    )
    langgraph_thread_id = models.CharField(max_length=255)  # Tenant-scoped uniqueness via constraint
    title = models.CharField(max_length=255, default="New Chat")
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chat_sessions'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', '-updated_at']),
            models.Index(fields=['langgraph_thread_id']),
            models.Index(fields=['tenant', '-updated_at'], name='chat_tenant_updated_idx'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'langgraph_thread_id'],
                name='chatsession_tenant_thread_uniq'
            ),
        ]

    def save(self, *args, **kwargs):
        # Auto-populate tenant from user if not set
        if not self.tenant_id and self.user_id:
            self.tenant_id = self.user.tenant_id
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.user.username})"

"""
Documents aggregate services.

Documents is a VERSIONED model — any future content-changing service here
must route through `document.create_new_version(**updates)`, not raw `.save()`.
State-transition-only changes (status field flips on an existing version) may
use `.save()` directly.

Plain functions; no service class.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import date

from django.utils import timezone


# =========================================================================
# Release / lifecycle transitions
# =========================================================================

def release_document(document, user, effective_date=None):
    """Flip an approved document to RELEASED and calculate compliance dates.

    Pure status transition on the existing version — no content fields change,
    so `.save()` is correct here (no `create_new_version` needed).

    Raises:
        ValueError: document is not in APPROVED status.
    """
    if document.status != 'APPROVED':
        raise ValueError(
            f"Cannot release document with status {document.status}. Must be approved."
        )

    document.status = 'RELEASED'
    document.calculate_compliance_dates(effective_date)
    document.save()


def mark_document_obsolete(document, user):
    """Mark a released or approved document as obsolete.

    Pure status transition — sets status and obsolete_date on the existing
    version. No content fields change, so `.save()` is correct.

    Raises:
        ValueError: document is not in APPROVED or RELEASED status.
    """
    if document.status not in ('APPROVED', 'RELEASED'):
        raise ValueError(
            f"Cannot obsolete document with status {document.status}."
        )

    document.status = 'OBSOLETE'
    document.obsolete_date = date.today()
    document.save()


def submit_document_for_approval(document, user):
    """Submit a draft document into the approval workflow.

    Looks up the appropriate ApprovalTemplate (from document_type or the
    tenant-default DOCUMENT_RELEASE template), creates an ApprovalRequest via
    `ApprovalRequest.create_from_template`, then flips the document status to
    UNDER_REVIEW.

    Status flip only — no content fields change — so `.save()` is correct.

    Raises:
        ValueError: document not in DRAFT, type does not require approval,
                    or no template found.

    Returns:
        ApprovalRequest
    """
    from Tracker.models.core import ApprovalRequest, ApprovalTemplate

    if document.status != 'DRAFT':
        raise ValueError(
            f"Cannot submit document with status {document.status}. Must be draft."
        )

    if document.document_type and not document.document_type.requires_approval:
        raise ValueError(
            f"Document type '{document.document_type.name}' does not require approval. "
            "Use release_document() directly or update the document type settings."
        )

    template = None
    if document.document_type and document.document_type.approval_template:
        template = document.document_type.approval_template
    else:
        try:
            template = ApprovalTemplate.objects.get(
                approval_type='DOCUMENT_RELEASE',
                tenant=document.tenant,
            )
        except ApprovalTemplate.DoesNotExist:
            raise ValueError(
                "DOCUMENT_RELEASE approval template not found. "
                "Please configure approval templates."
            )

    approval_request = ApprovalRequest.create_from_template(
        content_object=document,
        template=template,
        requested_by=user,
        reason=f"Document Release: {document.file_name}",
    )

    document.status = 'UNDER_REVIEW'
    document.save(update_fields=['status'])

    return approval_request


# =========================================================================
# Embedding
# =========================================================================

def embed_document_async(document):
    """Dispatch the Celery embedding task and return the AsyncResult.

    Callers inside a transaction must wrap with `transaction.on_commit` to
    avoid orphan tasks on rollback.
    """
    from Tracker.tasks import embed_document_async as _task
    return _task.delay(document.id)


def embed_document_inline(document) -> bool:
    """Synchronously embed a document's text content.

    Returns True if chunks were embedded, False if skipped.
    Prefer `embed_document_async` to avoid blocking requests.
    """
    from django.conf import settings
    from django.db import transaction
    from Tracker.ai_embed import embed_texts, chunk_text
    from Tracker.models.dms import DocChunk

    if not settings.AI_EMBED_ENABLED:
        return False

    if not document.file or not os.path.exists(document.file.path):
        return False
    if os.path.getsize(document.file.path) > settings.AI_EMBED_MAX_FILE_BYTES:
        return False

    text = document._extract_text_from_file()
    if not text or not text.strip():
        return False

    chunks = chunk_text(
        text,
        max_chars=settings.AI_EMBED_CHUNK_CHARS,
        max_chunks=settings.AI_EMBED_MAX_CHUNKS,
    )
    if not chunks:
        return False

    vecs = embed_texts(chunks)
    assert len(vecs[0]) == settings.AI_EMBED_DIM

    rows = [
        DocChunk(
            doc=document,
            preview_text=t[:300],
            full_text=t,
            span_meta={"i": i},
            embedding=v,
        )
        for i, (t, v) in enumerate(zip(chunks, vecs))
    ]
    with transaction.atomic():
        DocChunk.objects.filter(doc=document).delete()
        DocChunk.objects.bulk_create(rows, batch_size=50)
        document.ai_readable = True
        document.save(update_fields=["ai_readable"])

    return True


# =========================================================================
# Access logging
# =========================================================================

def log_document_access(document, user, request=None, action_type='view'):
    """Log document access for compliance auditing.

    Writes to both django-auditlog (for UI) and the compliance logger (for SIEM).

    Args:
        document: Documents instance being accessed.
        user: User performing the access.
        request: Optional HTTP request for IP extraction.
        action_type: 'view' (metadata) or 'download' (file retrieval).
    """
    from auditlog.models import LogEntry
    from django.contrib.contenttypes.models import ContentType

    compliance_logger = logging.getLogger('compliance.access_control')

    remote_addr = None
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            remote_addr = x_forwarded_for.split(',')[0].strip()
        else:
            remote_addr = request.META.get('REMOTE_ADDR')

    access_data = {
        'action_type': f'document_{action_type}',
        'file_name': document.file_name,
        'classification': document.classification,
        'itar_controlled': getattr(document, 'itar_controlled', False),
        'eccn': getattr(document, 'eccn', ''),
        'is_image': document.is_image,
    }

    LogEntry.objects.create(
        content_type=ContentType.objects.get_for_model(document),
        object_pk=str(document.pk),
        object_repr=str(document),
        action=LogEntry.Action.ACCESS,
        changes=access_data,
        actor=user,
        timestamp=timezone.now(),
        remote_addr=remote_addr,
    )

    compliance_logger.info({
        'event_type': 'ACCESS_GRANTED',
        'timestamp': timezone.now().isoformat(),
        'action': action_type,
        'user_id': str(user.id),
        'user_email': user.email,
        'user_us_person': getattr(user, 'us_person', False),
        'user_citizenship': getattr(user, 'citizenship', 'UNKNOWN'),
        'document_id': str(document.id),
        'document_name': document.file_name,
        'classification': document.classification,
        'itar_controlled': getattr(document, 'itar_controlled', False),
        'eccn': getattr(document, 'eccn', ''),
        'remote_addr': remote_addr,
    })


# =========================================================================
# Property auto-detection
# =========================================================================

def auto_detect_document_properties(document, file=None):
    """Inspect a file and return a dict of inferred field values.

    Does not mutate the document; callers apply the returned dict.
    Called during document creation to fill `is_image`, `file_name`, etc.

    Returns:
        dict of field-name → value.
    """
    from mimetypes import guess_type

    file = file or document.file
    if not file:
        return {}

    properties = {}
    mime_type, _ = guess_type(file.name)
    properties['is_image'] = mime_type and mime_type.startswith("image/")
    if not document.file_name:
        properties['file_name'] = file.name
    return properties

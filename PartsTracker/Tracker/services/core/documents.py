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
        # `is_current_version=True` is load-bearing — ApprovalTemplate
        # is versioned, so editing the template creates a new row with
        # the same `approval_type`. Without this filter the lookup
        # raises `MultipleObjectsReturned` the moment any admin edits
        # the template.
        try:
            # tenant-safe: SecureManager .objects auto-scopes to the request tenant
            template = ApprovalTemplate.objects.get(
                approval_type='DOCUMENT_RELEASE',
                is_current_version=True,
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
# Parent-version cloning
# =========================================================================

# Fields rewritten (not carried) when a Document is cloned onto a new
# parent version. Identity, GFK target, and soft-delete state always reset
# — the clone is a fresh row in its own version chain attached to the new
# parent. The document's own revision narrative (`change_justification`)
# does NOT carry: this is a re-attachment, not a content revision.
#
# Everything NOT listed here carries forward — crucially the approval
# lifecycle (`status`, `approved_by`, `approved_at`) and the
# approval-linked compliance dates (`effective_date`, `review_date`,
# `obsolete_date`, `retention_until`). An unchanged document stays
# APPROVED with its approver and dates intact, so revving the parent
# spec does not force re-signing identical attachments. The `file` field
# is also carried — it holds the storage path string, so the clone shares
# the same stored blob (no re-upload); a genuine file replacement later
# writes a fresh key via `upload_to`.
_DOCUMENT_VERSION_RESET_FIELDS = frozenset({
    'id', 'created_at', 'updated_at',
    'archived', 'deleted_at',
    'version', 'previous_version', 'is_current_version',
    'object_id',
    'change_justification',
})


def clone_current_documents(*, source, target):
    """Clone every current Document attached to `source` onto `target`.

    Used when a versioned composite parent (Process, Step, …) creates a
    new version: the new parent row gets its own Document rows so each
    historical version keeps a complete attachment set. Each clone:

    - **shares the source's stored file** — the `file` FieldFile carries
      its storage-path string forward, so both rows point at the same
      blob. No bytes are re-read or re-uploaded. When the new version's
      file is genuinely replaced later, the upload path writes a fresh
      key and the versions diverge naturally.
    - is a **fresh Document row in its own version chain** (new id, version
      reset, `previous_version` cleared) attached to `target` via GFK.
    - **carries the approval lifecycle forward unchanged** — an unchanged
      document stays in its current status (e.g. APPROVED) with approver
      and compliance dates intact. Revving the parent does not reset
      identical attachments to DRAFT or demand re-approval.

    `source` and `target` must be instances of the same model; the GFK
    content type is derived from `source`.

    Returns the list of created Document clones (may be empty).
    """
    from django.contrib.contenttypes.models import ContentType

    from Tracker.models import Documents

    ct = ContentType.objects.get_for_model(type(source))
    # tenant-safe: scoped via the source content_type/object_id GFK
    source_docs = Documents.objects.filter(
        content_type=ct,
        object_id=source.pk,
        is_current_version=True,
    )

    cloned = []
    for doc in source_docs:
        clone_data = {
            f.name: getattr(doc, f.name)
            for f in Documents._meta.fields
            if f.name not in _DOCUMENT_VERSION_RESET_FIELDS and not f.auto_created
        }
        clone_data['object_id'] = target.pk
        # tenant-safe: clone_data carries the tenant FK from the source doc.
        clone = Documents.objects.create(**clone_data)
        # Carry the source doc's secondary links onto the clone so the new
        # parent version starts with the same association set as the primary
        # GFK already does.
        clone_document_links(source_document=doc, target_document=clone)
        cloned.append(clone)
    return cloned


# =========================================================================
# Multi-target association (DocumentLink)
# =========================================================================
#
# A Document's *primary* owner is its own `content_type`/`object_id` GFK.
# These helpers manage *additional* associations via `DocumentLink` and never
# touch the primary GFK. Soft-delete (`archived`) is the system convention, so
# detach archives the link and attach revives an archived one rather than
# colliding with the partial unique constraint.

def attach_document_to(document, target):
    """Associate `document` with an additional `target` entity.

    Idempotent and revive-aware:
    - a live link to `target` already exists → returns it unchanged;
    - a soft-deleted link exists → restores and returns it;
    - otherwise creates a new link.

    The document's primary GFK (`content_object`) is never modified.

    Returns the DocumentLink.
    """
    from django.contrib.contenttypes.models import ContentType

    from Tracker.models import DocumentLink

    ct = ContentType.objects.get_for_model(type(target))
    # tenant-safe: `.objects` auto-scopes to the current tenant, so we never
    # match or revive a link belonging to another tenant.
    existing = DocumentLink.objects.filter(
        document=document, content_type=ct, object_id=str(target.pk),
    ).first()
    if existing is not None:
        if existing.archived:
            existing.restore()
        return existing
    return DocumentLink.objects.create(
        document=document, content_type=ct, object_id=str(target.pk),
    )


def detach_document_from(document, target):
    """Remove the secondary link from `document` to `target`.

    Soft-deletes (archives) the link to preserve the audit trail — consistent
    with the rest of the system. No-op if no live link exists. Never affects
    the primary GFK. Returns the number of links archived.
    """
    from django.contrib.contenttypes.models import ContentType

    from Tracker.models import DocumentLink

    ct = ContentType.objects.get_for_model(type(target))
    count = 0
    # tenant-safe: `.objects` auto-scopes to the current tenant.
    for link in DocumentLink.objects.filter(
        document=document, content_type=ct, object_id=str(target.pk), archived=False,
    ):
        link.delete()  # SecureModel.delete() is a soft delete
        count += 1
    return count


def linked_document_ids(content_type, object_id):
    """Ids of documents *linked* (secondary) to a single (content_type, object_id) target.

    The shared primitive behind the link-aware reads: the customer access
    filter, `documents_attached_to`, and the documents list FilterSet all need
    "which documents point here via a live DocumentLink". Returns a list (the
    querysets that consume it `__in` against it, and evaluating once avoids a
    correlated subquery). tenant-safe: `.objects` auto-scopes.
    """
    from Tracker.models import DocumentLink

    return list(
        DocumentLink.objects.filter(  # tenant-safe: .objects auto-scopes
            content_type=content_type, object_id=str(object_id), archived=False,
        ).values_list('document_id', flat=True)
    )


def documents_attached_to(target):
    """Return all Documents attached to `target` — primary GFK *or* link.

    Deduplicated. Tenant-scoped via `.objects`. Does not filter by archived
    document state or version; callers chain `.active()` / `.for_user()` /
    `.current_versions()` as needed (same contract as a plain GFK query).
    """
    from django.contrib.contenttypes.models import ContentType
    from django.db.models import Q

    from Tracker.models import Documents

    ct = ContentType.objects.get_for_model(type(target))
    return Documents.objects.filter(  # tenant-safe: .objects auto-scopes
        Q(content_type=ct, object_id=str(target.pk))
        | Q(id__in=linked_document_ids(ct, target.pk))
    ).distinct()


def forward_target_links(*, old_target, new_target):
    """Carry inbound DocumentLinks from a superseded target onto its new version.

    When a versioned entity (PartType, Process, Step, …) is re-versioned, the
    primary-GFK documents attached to it are cloned onto the new version
    (`clone_current_documents`). This does the same for *secondary* links: every
    live DocumentLink pointing at `old_target` is copied to point at
    `new_target`, so a document linked to "this part type" stays associated as
    the part type revs. The old version keeps its links for history (copy, not
    move) — mirroring the primary-GFK clone semantics exactly.

    Idempotent per (document, new_target). Returns the links created on the new
    target. No-op when nothing points at `old_target`.
    """
    from django.contrib.contenttypes.models import ContentType

    from Tracker.models import DocumentLink

    ct = ContentType.objects.get_for_model(type(old_target))
    created = []
    # tenant-safe: `.objects` auto-scopes to the current tenant.
    for link in DocumentLink.objects.filter(
        content_type=ct, object_id=str(old_target.pk), archived=False,
    ):
        created.append(
            DocumentLink.objects.get_or_create(
                document=link.document, content_type=ct, object_id=str(new_target.pk),
            )[0]
        )
    return created


def clone_document_links(*, source_document, target_document):
    """Copy every live link from `source_document` onto `target_document`.

    Used when a document is carried forward to a new version (either its own
    re-version or a parent-version clone) so the new row starts with the same
    secondary associations as the primary GFK already does. Idempotent per
    target via `attach_document_to`. Returns the list of links on the target.
    """
    from Tracker.models import DocumentLink

    created = []
    # tenant-safe: `.objects` auto-scopes; clones stay within the tenant.
    for link in DocumentLink.objects.filter(document=source_document, archived=False):
        created.append(
            DocumentLink.objects.get_or_create(
                document=target_document,
                content_type=link.content_type,
                object_id=link.object_id,
            )[0]
        )
    return created


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
        # Trusted client IP (edge-set header, not spoofable X-Forwarded-For).
        from Tracker.throttling import get_client_ip
        remote_addr = get_client_ip(request)

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

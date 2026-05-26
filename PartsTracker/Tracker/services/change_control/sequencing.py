"""
artifact_number sequencing for change-control artifacts.

Per-tenant, per-artifact-type, per-year sequence with annual reset.
Format: `{TYPE}-{YEAR}-{SEQ:04d}` (e.g. PCR-2026-0001).

Concurrent insert safety: SELECT FOR UPDATE inside an atomic transaction
on the ArtifactSequence row, so two simultaneous calls for the same
(tenant, type, year) serialize on the row lock.

Per-tenant scope means cross-tenant numbering collisions are correct,
not bugs — Tenant A and Tenant B can each have PCR-2026-0001 referring
to different changes.
"""
from __future__ import annotations

from uuid import UUID

from django.db import transaction
from django.utils import timezone

from Tracker.models import ArtifactSequence


def next_artifact_number(
    *,
    tenant_id: UUID,
    artifact_type: str,
    year: int | None = None,
) -> str:
    """Generate the next artifact number for a tenant + type + year.

    Args:
        tenant_id: Tenant UUID. Required — sequences are tenant-scoped.
        artifact_type: Prefix string (e.g. 'PCR', 'PCO', 'PCN', 'DCR').
        year: 4-digit year. Defaults to current UTC year.

    Returns:
        Formatted artifact number string, e.g. 'PCR-2026-0001'.

    Concurrency: SELECT FOR UPDATE on the ArtifactSequence row inside
    transaction.atomic() — two concurrent calls for the same triple
    will serialize on the row lock, so each gets a distinct number.
    """
    if not artifact_type:
        raise ValueError('artifact_type is required')

    year = year or timezone.now().year

    with transaction.atomic():
        # tenant-safe: cross-tenant access is intentional — sequencing
        # operates on the ArtifactSequence rows directly. The row's
        # tenant FK still constrains the result to the requested tenant.
        seq, _created = ArtifactSequence.all_tenants.select_for_update().get_or_create(
            tenant_id=tenant_id,
            artifact_type=artifact_type,
            year=year,
            defaults={'next_value': 1},
        )
        current = seq.next_value
        seq.next_value = current + 1
        seq.save(update_fields=['next_value', 'updated_at'])

    return f'{artifact_type}-{year}-{current:04d}'

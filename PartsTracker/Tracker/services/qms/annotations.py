"""3D defect annotations — when one stops being a draft.

An annotation placed during an inspection is saved at once, linked to that
inspection's still-PENDING quality report, so the inspector can remove a mis-placed
marker while working. Once a linked report is finished (PASS / FAIL) the annotation
is evidence: the "Requires 3D Annotation" disposition gate reads it
(`QuarantineDisposition.has_pending_annotations`). From then on deleting it is a
quality-record judgement, held by `delete_submitted_heatmapannotations`.
"""
from __future__ import annotations

SUBMITTED_DELETE_PERM = 'delete_submitted_heatmapannotations'


def is_submitted(annotation) -> bool:
    """True once any quality report the annotation is linked to has been finished."""
    return annotation.quality_reports.exclude(status='PENDING').exists()


def can_delete(annotation, user) -> bool:
    """A draft annotation goes with the ordinary delete permission; a submitted one
    also needs the quality team's."""
    return not is_submitted(annotation) or user.has_tenant_perm(SUBMITTED_DELETE_PERM)

"""
AssemblyUsage aggregate services.

Tiny for now — one mutator. Expand here if the removal flow grows
side effects (inventory returns, audit logs, etc.).
"""
from __future__ import annotations

from django.utils import timezone

from Tracker.models import AssemblyUsage


def remove_assembly_usage(
    usage: AssemblyUsage,
    user,
    reason: str = '',
) -> AssemblyUsage:
    """Mark a component as removed from the assembly."""
    usage.removed_at = timezone.now()
    usage.removed_by = user
    usage.removal_reason = reason
    usage.save()
    return usage

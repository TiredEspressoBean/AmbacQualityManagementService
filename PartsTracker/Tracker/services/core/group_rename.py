"""Renaming a tenant group, and what names it.

An approval template auto-assigns a group by NAME (`ApprovalTemplate.auto_assign_by_role`),
so renaming the group silently left its templates assigning nobody (doc audit,
2026-11-17). The rename and the templates move together, in one transaction.

Everything else that refers to a group holds its id (notification rules'
recipient_groups, approval stages, a step's revisit role), so it follows on its own.
`PermissionChangeLog.group_name` is history — what the group was called when it
changed — and is left as it was.
"""
from __future__ import annotations

from django.db import transaction


def rename_group(group, new_name: str) -> int:
    """Rename `group` to `new_name`; its tenant's approval templates that auto-assign
    the old name follow it. Returns how many templates were repointed."""
    from Tracker.models import ApprovalTemplate
    old_name = group.name
    if not new_name or new_name == old_name:
        return 0
    with transaction.atomic():
        group.name = new_name
        group.save(update_fields=['name', 'updated_at'])
        # The current version only, in place: the template still means the same group
        # (as an FK would follow), so this isn't a new version of it. Older versions
        # are history and keep the name they were written with.
        return (ApprovalTemplate.unscoped  # tenant-safe: explicit tenant filter
                .filter(tenant_id=group.tenant_id, auto_assign_by_role=old_name,
                        is_current_version=True)
                .update(auto_assign_by_role=new_name))

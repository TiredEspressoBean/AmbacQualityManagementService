"""
Permission Service for managing group permissions.

This service applies permissions from the declarative structure in permissions.py
to the database, with audit logging and diff capabilities.
"""

import fnmatch
import logging
from typing import Optional

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from Tracker.permissions import GROUPS, get_group_names, get_all_app_labels

logger = logging.getLogger(__name__)


class PermissionService:
    """
    Service for managing group permissions based on declarative config.

    Features:
    - Idempotent permission application
    - Dry-run mode for previewing changes
    - Diff detection between declared and actual permissions
    - Audit logging via PermissionChangeLog
    """

    def __init__(self, user=None, source: str = 'manual'):
        """
        Initialize the permission service.

        Args:
            user: User performing the operation (for audit logging)
            source: Source of the change ('manual', 'post_migrate', 'migration')
        """
        self.user = user
        self.source = source
        self._all_tracker_permissions = None

    # =========================================================================
    # PUBLIC METHODS
    # =========================================================================

    def apply_permissions(self, dry_run: bool = False) -> dict:
        """
        Apply all permissions from the declarative structure.

        All changes are applied atomically - if any group fails, all changes
        are rolled back to prevent inconsistent permission states.

        Args:
            dry_run: If True, only calculate changes without applying

        Returns:
            Dict with results: {
                'groups_processed': int,
                'permissions_added': int,
                'permissions_removed': int,
                'errors': list,
                'changes': list of change dicts
            }
        """
        results = {
            'groups_processed': 0,
            'permissions_added': 0,
            'permissions_removed': 0,
            'errors': [],
            'changes': [],
        }

        try:
            with transaction.atomic():
                for group_name in get_group_names():
                    group_result = self._apply_group_permissions(group_name, dry_run)
                    results['groups_processed'] += 1
                    results['permissions_added'] += group_result['added']
                    results['permissions_removed'] += group_result['removed']
                    results['changes'].extend(group_result['changes'])
        except Exception as e:
            error_msg = f"Permission sync failed, all changes rolled back: {e}"
            logger.error(error_msg, exc_info=True)
            results['errors'].append(error_msg)
            # Reset counts since everything was rolled back
            results['groups_processed'] = 0
            results['permissions_added'] = 0
            results['permissions_removed'] = 0
            results['changes'] = []

        if not dry_run and results['changes']:
            logger.info(
                f"Permission sync complete: {results['permissions_added']} added, "
                f"{results['permissions_removed']} removed across "
                f"{results['groups_processed']} groups"
            )

        return results

    def diff(self, group_name: Optional[str] = None) -> dict:
        """
        Calculate diff between declared and actual permissions.

        Args:
            group_name: Specific group to diff, or None for all groups

        Returns:
            Dict with diffs per group
        """
        diffs = {}
        groups_to_check = [group_name] if group_name else get_group_names()

        for name in groups_to_check:
            if name not in GROUPS:
                continue

            declared = self._get_declared_permissions(name)
            actual = self._get_actual_permissions(name)

            to_add = declared - actual
            to_remove = actual - declared

            if to_add or to_remove:
                diffs[name] = {
                    'to_add': sorted(to_add),
                    'to_remove': sorted(to_remove),
                    'declared_count': len(declared),
                    'actual_count': len(actual),
                }

        return diffs

    def get_group_status(self, group_name: str) -> dict:
        """
        Get detailed status for a specific group.

        Args:
            group_name: Name of the group

        Returns:
            Dict with group permission status
        """
        if group_name not in GROUPS:
            return {'error': f"Group '{group_name}' not defined"}

        declared = self._get_declared_permissions(group_name)
        actual = self._get_actual_permissions(group_name)

        return {
            'group_name': group_name,
            'description': GROUPS[group_name].get('description', ''),
            'declared_permissions': sorted(declared),
            'actual_permissions': sorted(actual),
            'missing': sorted(declared - actual),
            'extra': sorted(actual - declared),
            'in_sync': declared == actual,
        }

    def ensure_groups_exist(self) -> list[str]:
        """
        Ensure all declared groups exist in the database.

        Returns:
            List of created group names
        """
        created = []
        for group_name in get_group_names():
            group, was_created = Group.objects.get_or_create(name=group_name)
            if was_created:
                created.append(group_name)
                logger.info(f"Created group: {group_name}")

        return created

    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================

    def _apply_group_permissions(self, group_name: str, dry_run: bool) -> dict:
        """Apply permissions for a single group."""
        result = {'added': 0, 'removed': 0, 'changes': []}

        # Ensure group exists
        group, _ = Group.objects.get_or_create(name=group_name)

        declared = self._get_declared_permissions(group_name)
        actual = self._get_actual_permissions(group_name)

        to_add = declared - actual
        to_remove = actual - declared

        if not to_add and not to_remove:
            return result

        # Get current counts for logging
        count_before = len(actual)

        if not dry_run:
            # Add missing permissions
            for codename in to_add:
                perm = self._get_permission_by_codename(codename)
                if perm:
                    group.permissions.add(perm)
                    result['added'] += 1
                    result['changes'].append({
                        'group': group_name,
                        'permission': codename,
                        'action': 'added',
                    })
                    self._log_change(group_name, codename, 'added', count_before, count_before + 1)

            # Remove extra permissions
            for codename in to_remove:
                perm = self._get_permission_by_codename(codename)
                if perm:
                    group.permissions.remove(perm)
                    result['removed'] += 1
                    result['changes'].append({
                        'group': group_name,
                        'permission': codename,
                        'action': 'removed',
                    })
                    self._log_change(group_name, codename, 'removed', count_before, count_before - 1)
        else:
            # Dry run - just record what would happen
            for codename in to_add:
                result['added'] += 1
                result['changes'].append({
                    'group': group_name,
                    'permission': codename,
                    'action': 'would_add',
                })

            for codename in to_remove:
                result['removed'] += 1
                result['changes'].append({
                    'group': group_name,
                    'permission': codename,
                    'action': 'would_remove',
                })

        return result

    def _get_declared_permissions(self, group_name: str) -> set[str]:
        """Get the set of permission codenames declared for a group."""
        config = GROUPS.get(group_name, {})
        perms_config = config.get('permissions', [])

        # Handle __all__ for admin
        if perms_config == '__all__':
            return self._get_all_tracker_permissions()

        # Expand wildcards and build permission set
        result = set()
        all_perms = self._get_all_tracker_permissions()

        for perm_pattern in perms_config:
            if '*' in perm_pattern:
                # Wildcard pattern - match against all permissions
                for perm in all_perms:
                    if fnmatch.fnmatch(perm, perm_pattern):
                        result.add(perm)
            else:
                # Exact permission - add if it exists
                if perm_pattern in all_perms:
                    result.add(perm_pattern)
                else:
                    # Permission doesn't exist yet - this is normal during initial setup
                    logger.debug(f"Permission '{perm_pattern}' not found in database")

        return result

    def _get_actual_permissions(self, group_name: str) -> set[str]:
        """Get the set of permission codenames currently assigned to a group."""
        try:
            group = Group.objects.get(name=group_name)
            return set(
                f"{p.content_type.app_label}.{p.codename}"
                for p in group.permissions.all()
            )
        except Group.DoesNotExist:
            return set()

    def _get_all_tracker_permissions(self) -> set[str]:
        """Get all permissions from configured app labels."""
        if self._all_tracker_permissions is None:
            try:
                # Query all app labels defined in MODULE_APPS
                app_labels = get_all_app_labels()
                content_types = ContentType.objects.filter(app_label__in=app_labels)
                perms = Permission.objects.filter(content_type__in=content_types)
                self._all_tracker_permissions = set(
                    f"{p.content_type.app_label}.{p.codename}" for p in perms
                )
            except Exception:
                # Database might not be ready yet
                self._all_tracker_permissions = set()

        return self._all_tracker_permissions

    def _get_permission_by_codename(self, full_codename: str) -> Optional[Permission]:
        """Get a Permission object by its full codename (app_label.codename)."""
        try:
            app_label, codename = full_codename.split('.', 1)
            return Permission.objects.get(
                content_type__app_label=app_label,
                codename=codename
            )
        except (ValueError, Permission.DoesNotExist):
            logger.warning(f"Permission not found: {full_codename}")
            return None

    def _log_change(
        self,
        group_name: str,
        permission_codename: str,
        action: str,
        count_before: int,
        count_after: int,
    ):
        """Log a permission change to the audit log."""
        # Import here to avoid circular imports
        from Tracker.models import PermissionChangeLog

        try:
            PermissionChangeLog.objects.create(
                changed_by=self.user,
                group_name=group_name,
                permission_codename=permission_codename,
                action=action,
                source=self.source,
                reason=f"Applied from permissions.py via {self.source}",
                permissions_before=count_before,
                permissions_after=count_after,
            )
        except Exception as e:
            # Don't fail the whole operation if logging fails
            logger.error(f"Failed to log permission change: {e}")


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def apply_permissions(user=None, source: str = 'manual', dry_run: bool = False) -> dict:
    """
    Convenience function to apply all permissions.

    Args:
        user: User performing the operation
        source: Source of the change
        dry_run: If True, only calculate changes

    Returns:
        Results dict
    """
    service = PermissionService(user=user, source=source)
    service.ensure_groups_exist()
    return service.apply_permissions(dry_run=dry_run)


def get_permission_diff() -> dict:
    """
    Convenience function to get permission diff.

    Returns:
        Dict with diffs per group
    """
    service = PermissionService()
    return service.diff()

# models.py - Simple Secure Base Model and Manager (using django-auditlog)

from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

from django.contrib.contenttypes.models import ContentType
from auditlog.models import LogEntry
import json


class SecureQuerySet(models.QuerySet):
    """QuerySet with soft delete functionality"""

    def delete(self):
        """Soft delete all objects in queryset with full logging"""
        # For bulk operations, we need to call individual delete() methods
        # to ensure proper logging with django-auditlog
        deleted_count = 0
        for obj in self:
            if not obj.archived:
                obj.delete()  # This calls the model's delete() method
                deleted_count += 1
        return deleted_count, {}

    def bulk_soft_delete(self, actor=None, reason="bulk_operation"):
        """Fast bulk soft delete WITH audit logging"""
        # Get objects that will be affected
        objects_to_delete = list(self.filter(archived=False).values('id', 'pk'))

        if not objects_to_delete:
            return 0

        # Perform the bulk update
        updated_count = self.filter(archived=False).update(
            deleted_at=timezone.now(),
            archived=True
        )

        # Create bulk audit log entries
        if updated_count > 0:
            self._create_bulk_audit_logs(
                objects_to_delete,
                action='soft_delete_bulk',
                actor=actor,
                reason=reason
            )

        return updated_count

    def bulk_restore(self, actor=None, reason="bulk_restore"):
        """Bulk restore WITH audit logging"""
        # Get objects that will be affected
        objects_to_restore = list(self.filter(archived=True).values('id', 'pk'))

        if not objects_to_restore:
            return 0

        # Perform the bulk update
        updated_count = self.filter(archived=True).update(
            deleted_at=None,
            archived=False
        )

        # Create bulk audit log entries
        if updated_count > 0:
            self._create_bulk_audit_logs(
                objects_to_restore,
                action='restore_bulk',
                actor=actor,
                reason=reason
            )

        return updated_count

    def _create_bulk_audit_logs(self, object_list, action, actor=None, reason=""):
        """Create audit log entries for bulk operations"""
        if not object_list:
            return

        content_type = ContentType.objects.get_for_model(self.model)

        # Create individual log entries for each affected object
        log_entries = []
        for obj_data in object_list:
            log_entries.append(LogEntry(
                content_type=content_type,
                object_pk=str(obj_data['pk']),
                object_id=obj_data['id'],
                object_repr=f"{self.model.__name__} (id={obj_data['id']})",
                action=LogEntry.Action.UPDATE,
                changes=json.dumps({
                    'archived': [False, True] if 'delete' in action else [True, False],
                    'bulk_operation': action,
                    'reason': reason
                }),
                actor=actor,
                timestamp=timezone.now()
            ))

        # Bulk create the log entries
        LogEntry.objects.bulk_create(log_entries)

        # Also create a summary log entry
        LogEntry.objects.create(
            content_type=content_type,
            object_pk='bulk_operation',
            object_id=None,
            object_repr=f"Bulk {action} - {len(object_list)} {self.model.__name__} objects",
            action=LogEntry.Action.UPDATE,
            changes=json.dumps({
                'operation': action,
                'affected_count': len(object_list),
                'affected_ids': [obj['id'] for obj in object_list],
                'reason': reason
            }),
            actor=actor,
            timestamp=timezone.now()
        )

    def hard_delete(self):
        """Actually delete from database"""
        return super().delete()

    def active(self):
        """Get non-deleted objects"""
        return self.filter(archived=False)

    def deleted(self):
        """Get soft-deleted objects"""
        return self.filter(archived=True)


class SecureManager(models.Manager):
    """Manager with customer filtering and soft delete"""

    def get_queryset(self):
        return SecureQuerySet(self.model, using=self._db)

    def for_user(self, user):
        """Filter data based on user permissions"""
        queryset = self.active()  # Start with non-deleted objects

        # Superusers see everything
        if user.is_superuser:
            return queryset

        # Staff see all active objects
        if user.is_staff:
            return queryset

        # Customer filtering - only see their own data
        model_name = self.model._meta.model_name

        if model_name == 'order':
            return queryset.filter(customer=user)
        elif model_name == 'part':
            return queryset.filter(order__customer=user)
        elif model_name == 'document':
            return queryset.filter(
                models.Q(customer=user) |  # Their documents
                models.Q(classification='public')  # Public documents
            )
        elif model_name == 'user':
            # Customers only see themselves
            return queryset.filter(id=user.id)

        # Default: no access
        return queryset.none()

    def active(self):
        """Get active (non-deleted) objects"""
        return self.get_queryset().active()

    def deleted(self):
        """Get soft-deleted objects"""
        return self.get_queryset().deleted()

# Retention Policy System Design

> **STATUS: DRAFT - Not Yet Implemented**
> This is a design document for a future feature. The retention policy system has not been built yet.

## Overview

Multi-tenant retention policy system for QMS/MES compliance. Supports varying regulatory requirements (commercial vs government contractors) with tenant-configurable policies and legal hold capability.

## Requirements

- **Tenant-configurable**: Different customers have different retention requirements
- **System defaults**: Sensible defaults that tenants can override
- **Legal hold**: Pause retention for litigation/audits (critical for gov contractors)
- **Audit trail**: Log all retention actions for compliance
- **Multiple dispositions**: Delete, review, or archive to cold storage

## Data Model

### RetentionPolicy

Defines retention rules per model, with tenant overrides.

```python
class RetentionCategory(models.TextChoices):
    PERMANENT = 'PERMANENT', 'Permanent (never auto-delete)'
    REGULATORY = 'REGULATORY', 'Regulatory (per compliance requirements)'
    BUSINESS = 'BUSINESS', 'Business (per internal policy)'
    OPERATIONAL = 'OPERATIONAL', 'Operational (short-term)'
    TRANSIENT = 'TRANSIENT', 'Transient (delete when done)'


class RetentionDisposition(models.TextChoices):
    DELETE = 'DELETE', 'Permanently delete'
    REVIEW = 'REVIEW', 'Flag for manual review'
    ARCHIVE = 'ARCHIVE', 'Move to cold storage'


class RetentionPolicy(SecureModel):
    """
    Tenant-configurable retention rules with system defaults.

    Lookup order:
    1. Tenant-specific policy for model
    2. System default (tenant=null) for model
    3. Hardcoded fallback (PERMANENT - never delete)
    """

    tenant = models.ForeignKey(
        'Tenant',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="Null = system-wide default"
    )

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        help_text="The model this policy applies to"
    )

    category = models.CharField(
        max_length=20,
        choices=RetentionCategory.choices,
        default=RetentionCategory.REGULATORY
    )

    retention_days = models.IntegerField(
        help_text="Days to retain after trigger event. 0 = permanent."
    )

    trigger_field = models.CharField(
        max_length=50,
        default='deleted_at',
        help_text="Field that starts retention clock: created_at, deleted_at, completed_at, etc."
    )

    disposition = models.CharField(
        max_length=20,
        choices=RetentionDisposition.choices,
        default=RetentionDisposition.DELETE
    )

    requires_approval = models.BooleanField(
        default=False,
        help_text="Require approval before disposition (for sensitive records)"
    )

    notify_before_days = models.IntegerField(
        default=0,
        help_text="Days before disposition to notify admins. 0 = no notification."
    )

    class Meta:
        unique_together = ['tenant', 'content_type']
        verbose_name = 'Retention Policy'
        verbose_name_plural = 'Retention Policies'

    @classmethod
    def get_policy(cls, model_class, tenant=None):
        """Get applicable policy for a model, with fallback chain."""
        content_type = ContentType.objects.get_for_model(model_class)

        # Try tenant-specific first
        if tenant:
            policy = cls.objects.filter(
                tenant=tenant,
                content_type=content_type
            ).first()
            if policy:
                return policy

        # Fall back to system default
        return cls.objects.filter(
            tenant__isnull=True,
            content_type=content_type
        ).first()
```

### LegalHold

Pauses retention for specific records during litigation/audits.

```python
class LegalHold(SecureModel):
    """
    Pause retention on specific records for litigation/audit.

    Records with active legal holds are NEVER auto-deleted,
    regardless of retention policy.
    """

    tenant = models.ForeignKey('Tenant', on_delete=models.CASCADE)

    # Can hold a specific record or all records of a type
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(
        max_length=36,
        null=True,
        blank=True,
        help_text="Specific record ID, or null for all records of this type"
    )

    hold_name = models.CharField(
        max_length=200,
        help_text="e.g., 'DOJ Audit 2026', 'Contract Dispute ABC-123'"
    )

    reason = models.TextField(
        help_text="Legal justification for the hold"
    )

    held_by = models.ForeignKey(
        'User',
        on_delete=models.PROTECT,
        related_name='legal_holds_created'
    )

    held_at = models.DateTimeField(default=timezone.now)

    released_by = models.ForeignKey(
        'User',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='legal_holds_released'
    )

    released_at = models.DateTimeField(null=True, blank=True)
    release_reason = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['tenant', 'released_at']),
        ]

    @property
    def is_active(self):
        return self.released_at is None

    @classmethod
    def is_held(cls, obj):
        """Check if a specific object is under legal hold."""
        content_type = ContentType.objects.get_for_model(obj)
        return cls.objects.filter(
            content_type=content_type,
            released_at__isnull=True
        ).filter(
            models.Q(object_id=str(obj.pk)) | models.Q(object_id__isnull=True)
        ).exists()
```

### RetentionLog

Audit trail for all retention actions.

```python
class RetentionLog(models.Model):
    """Audit log for retention actions - never delete these."""

    tenant = models.ForeignKey('Tenant', null=True, on_delete=models.SET_NULL)

    action = models.CharField(
        max_length=20,
        choices=[
            ('DELETED', 'Record deleted'),
            ('ARCHIVED', 'Record archived to cold storage'),
            ('REVIEWED', 'Record flagged for review'),
            ('HELD', 'Legal hold applied'),
            ('RELEASED', 'Legal hold released'),
            ('SKIPPED', 'Skipped due to legal hold'),
        ]
    )

    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True)
    object_id = models.CharField(max_length=36)
    object_repr = models.CharField(max_length=200)  # String representation at time of action

    policy = models.ForeignKey(RetentionPolicy, null=True, on_delete=models.SET_NULL)
    legal_hold = models.ForeignKey(LegalHold, null=True, blank=True, on_delete=models.SET_NULL)

    performed_by = models.ForeignKey('User', null=True, on_delete=models.SET_NULL)
    performed_at = models.DateTimeField(default=timezone.now)

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-performed_at']
        indexes = [
            models.Index(fields=['tenant', '-performed_at']),
            models.Index(fields=['content_type', 'object_id']),
        ]
```

## Cleanup Task

Single Celery Beat task that runs daily.

```python
from celery import shared_task
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from datetime import timedelta

@shared_task
def retention_cleanup():
    """
    Daily task to process retention policies.

    For each model with a retention policy:
    1. Find archived records past retention period
    2. Skip records under legal hold
    3. Apply disposition (delete, review, or archive)
    4. Log all actions
    """
    from Tracker.models import RetentionPolicy, LegalHold, RetentionLog, Tenant

    processed = {'deleted': 0, 'reviewed': 0, 'archived': 0, 'held': 0}

    # Get all models with retention policies
    policies = RetentionPolicy.objects.filter(
        retention_days__gt=0  # Skip permanent retention
    ).select_related('content_type', 'tenant')

    for policy in policies:
        model_class = policy.content_type.model_class()
        if not model_class:
            continue

        # Calculate cutoff date
        cutoff = timezone.now() - timedelta(days=policy.retention_days)

        # Build query for expired records
        trigger_filter = {f'{policy.trigger_field}__lt': cutoff}

        # Only process archived records (soft-deleted)
        if hasattr(model_class, 'archived'):
            trigger_filter['archived'] = True

        # Tenant filter
        if policy.tenant:
            trigger_filter['tenant'] = policy.tenant

        expired_records = model_class.objects.filter(**trigger_filter)

        for record in expired_records.iterator():
            # Check legal hold
            if LegalHold.is_held(record):
                RetentionLog.objects.create(
                    tenant=policy.tenant,
                    action='SKIPPED',
                    content_type=policy.content_type,
                    object_id=str(record.pk),
                    object_repr=str(record)[:200],
                    policy=policy,
                    notes='Skipped due to active legal hold'
                )
                processed['held'] += 1
                continue

            # Apply disposition
            if policy.disposition == 'DELETE':
                RetentionLog.objects.create(
                    tenant=policy.tenant,
                    action='DELETED',
                    content_type=policy.content_type,
                    object_id=str(record.pk),
                    object_repr=str(record)[:200],
                    policy=policy
                )
                record.hard_delete()
                processed['deleted'] += 1

            elif policy.disposition == 'REVIEW':
                # Flag for review (implementation depends on your review workflow)
                RetentionLog.objects.create(
                    tenant=policy.tenant,
                    action='REVIEWED',
                    content_type=policy.content_type,
                    object_id=str(record.pk),
                    object_repr=str(record)[:200],
                    policy=policy
                )
                processed['reviewed'] += 1

            elif policy.disposition == 'ARCHIVE':
                # Move to cold storage (implementation depends on your archive strategy)
                RetentionLog.objects.create(
                    tenant=policy.tenant,
                    action='ARCHIVED',
                    content_type=policy.content_type,
                    object_id=str(record.pk),
                    object_repr=str(record)[:200],
                    policy=policy
                )
                processed['archived'] += 1

    return processed
```

## System Defaults

Seed these via migration or management command:

| Model | Category | Retention | Trigger | Disposition |
|-------|----------|-----------|---------|-------------|
| QualityReports | REGULATORY | 2555 days (7 years) | deleted_at | DELETE |
| CAPA | REGULATORY | 2555 days | deleted_at | DELETE |
| QuarantineDisposition | REGULATORY | 2555 days | deleted_at | DELETE |
| Orders | BUSINESS | 1825 days (5 years) | deleted_at | DELETE |
| WorkOrder | BUSINESS | 1825 days | deleted_at | DELETE |
| Parts | BUSINESS | 1825 days | deleted_at | DELETE |
| Documents | REGULATORY | 2555 days | deleted_at | REVIEW |
| ChatSession | OPERATIONAL | 90 days | updated_at | DELETE |
| NotificationTask | OPERATIONAL | 30 days | created_at | DELETE |
| PermissionChangeLog | PERMANENT | 0 | - | - |
| RetentionLog | PERMANENT | 0 | - | - |

## Regulatory References

Common retention requirements by industry:

- **FDA 21 CFR Part 820** (Medical Devices): Quality records for design/production must be retained for the life of the device + 2 years
- **ISO 13485**: Quality records retained per documented procedures (typically 5-10 years)
- **AS9100** (Aerospace): Records retained per customer/regulatory requirements (often 10+ years)
- **ITAR** (Defense): Records retained for 5 years from export/transfer
- **FAR 4.703** (Federal Contracts): 3 years after final payment
- **DFARS** (DoD Contracts): 6 years for most records, longer for specific categories

## Implementation Phases

### Phase 1: Foundation
- [ ] Add RetentionPolicy model
- [ ] Add LegalHold model
- [ ] Add RetentionLog model
- [ ] Management command to seed defaults
- [ ] Admin UI for viewing/editing policies

### Phase 2: Enforcement
- [ ] Celery task for daily cleanup
- [ ] Legal hold check in hard_delete()
- [ ] Notification before disposition (optional)

### Phase 3: Advanced
- [ ] Cold storage archive integration
- [ ] Review workflow for REVIEW disposition
- [ ] Bulk legal hold management
- [ ] Retention policy reports/dashboard
- [ ] Export retention logs for auditors

## API Endpoints (Future)

```
GET    /api/retention-policies/                 # List policies (admin)
POST   /api/retention-policies/                 # Create tenant override
GET    /api/retention-policies/{model}/         # Get effective policy for model
PUT    /api/retention-policies/{id}/            # Update policy

GET    /api/legal-holds/                        # List active holds
POST   /api/legal-holds/                        # Create hold
POST   /api/legal-holds/{id}/release/           # Release hold

GET    /api/retention-logs/                     # Audit log (admin/auditor)
```

## Notes

- RetentionLog records should NEVER be auto-deleted (auditor requirement)
- Legal holds take absolute precedence over retention policies
- Consider adding `retention_override` field to individual records for exceptions
- Cold storage archive could be S3 Glacier, Azure Archive, or separate DB

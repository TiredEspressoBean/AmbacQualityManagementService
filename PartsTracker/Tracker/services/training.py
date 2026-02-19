"""
Training Authorization Service

Provides work authorization checks based on training requirements.
Aggregates requirements from Step, Process, and EquipmentType levels.

Usage:
    from Tracker.services.training import check_training_authorization

    # Check if user can perform a step
    result = check_training_authorization(
        user=operator,
        step=inspection_step,
        process=fuel_injector_process,
        equipment_type=cmm_type  # optional
    )

    if result.authorized:
        # Proceed with work
    else:
        # Block or warn based on result.missing
"""

from dataclasses import dataclass, field
from typing import Optional
from django.db import models
from django.utils import timezone


@dataclass
class TrainingAuthorizationResult:
    """Result of a training authorization check."""

    authorized: bool
    """True if user has all required training."""

    missing: list = field(default_factory=list)
    """List of (training_type_name, reason) tuples for missing/expired training."""

    verified: list = field(default_factory=list)
    """List of (training_type_name, expires_date) tuples for verified training."""

    def to_dict(self):
        """Convert to JSON-serializable dict for API responses."""
        return {
            'authorized': self.authorized,
            'missing': [
                {'training': name, 'reason': reason}
                for name, reason in self.missing
            ],
            'verified': [
                {'training': name, 'expires': expires.isoformat() if expires else None}
                for name, expires in self.verified
            ],
        }


def get_required_training(step, process=None, equipment_type=None):
    """
    Get all TrainingTypes required for work.

    Aggregates requirements from:
    - Step-level requirements
    - Process-level requirements (if process provided)
    - EquipmentType-level requirements (if equipment_type provided)

    Args:
        step: The Step being performed
        process: The Process context (optional)
        equipment_type: The EquipmentType being used (optional)

    Returns:
        Set of TrainingType instances
    """
    required = set()

    # Step-level
    for req in step.training_requirements.select_related('training_type').all():
        required.add(req.training_type)

    # Process-level
    if process:
        for req in process.training_requirements.select_related('training_type').all():
            required.add(req.training_type)

    # EquipmentType-level
    if equipment_type:
        for req in equipment_type.training_requirements.select_related('training_type').all():
            required.add(req.training_type)

    return required


def get_user_current_training(user):
    """
    Get all TrainingTypes the user currently holds (not expired).

    Returns:
        Dict mapping training_type_id to expires_date (or None if no expiration)
    """
    from Tracker.models import TrainingRecord

    today = timezone.now().date()

    # Get all training records that are current
    current_records = TrainingRecord.objects.filter(
        user=user
    ).filter(
        models.Q(expires_date__isnull=True) | models.Q(expires_date__gte=today)
    ).select_related('training_type')

    # Return dict of training_type_id -> expires_date
    return {
        record.training_type_id: record.expires_date
        for record in current_records
    }


def check_training_authorization(
    user,
    step,
    process=None,
    equipment_type=None
) -> TrainingAuthorizationResult:
    """
    Check if a user is authorized to perform work based on training requirements.

    Args:
        user: The operator/user
        step: The Step being performed
        process: The Process context (optional, for process-level requirements)
        equipment_type: The EquipmentType being used (optional)

    Returns:
        TrainingAuthorizationResult with authorization status and details
    """
    # Get all required training
    required = get_required_training(step, process, equipment_type)

    # No requirements = authorized
    if not required:
        return TrainingAuthorizationResult(authorized=True)

    # Get user's current training
    user_training = get_user_current_training(user)

    missing = []
    verified = []

    for training_type in required:
        if training_type.id in user_training:
            expires = user_training[training_type.id]
            verified.append((training_type.name, expires))
        else:
            # Check if they have an expired record
            from Tracker.models import TrainingRecord
            expired_record = TrainingRecord.objects.filter(
                user=user,
                training_type=training_type,
                expires_date__lt=timezone.now().date()
            ).order_by('-expires_date').first()

            if expired_record:
                reason = f"Expired {expired_record.expires_date}"
            else:
                reason = "Not completed"

            missing.append((training_type.name, reason))

    return TrainingAuthorizationResult(
        authorized=len(missing) == 0,
        missing=missing,
        verified=verified
    )


def get_training_snapshot(user, step, process=None, equipment_type=None) -> dict:
    """
    Create a snapshot of training status for audit trail.

    Use this when recording work completion to preserve the training
    state at the time of execution.

    Returns:
        Dict suitable for storing in JSONField
    """
    result = check_training_authorization(user, step, process, equipment_type)
    return result.to_dict()


def get_qualified_users_for_step(step, process=None, equipment_type=None, tenant=None):
    """
    Get all users who are qualified to perform a step.

    Args:
        step: The Step
        process: Optional Process context
        equipment_type: Optional EquipmentType
        tenant: Optional Tenant to filter users

    Returns:
        QuerySet of User objects who have all required training
    """
    from Tracker.models import User, TrainingRecord

    required = get_required_training(step, process, equipment_type)

    if not required:
        # No requirements = all users qualified
        qs = User.objects.all()
        if tenant:
            qs = qs.filter(tenant=tenant)
        return qs

    today = timezone.now().date()
    required_ids = [t.id for t in required]

    # Get users who have current training for ALL required types
    # This uses a subquery approach
    qualified_user_ids = (
        TrainingRecord.objects.filter(
            training_type_id__in=required_ids
        ).filter(
            models.Q(expires_date__isnull=True) | models.Q(expires_date__gte=today)
        ).values('user_id')
        .annotate(training_count=models.Count('training_type_id', distinct=True))
        .filter(training_count=len(required_ids))
        .values_list('user_id', flat=True)
    )

    qs = User.objects.filter(id__in=qualified_user_ids)
    if tenant:
        qs = qs.filter(tenant=tenant)

    return qs

"""
Training Authorization Service

Provides work authorization checks based on training requirements.
Aggregates requirements from Step, Process, and EquipmentType levels.

Authorization is competency-LEVEL aware: each requirement carries a
`min_level` (1-4, see `CompetencyLevel`), and a user is authorized for a
training type when the max level among their in-date records for that type
is >= the strictest required min_level.

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
from django.db import models
from django.utils import timezone


@dataclass
class TrainingAuthorizationResult:
    """Result of a training authorization check."""

    authorized: bool
    """True if user meets every required training at the required level."""

    missing: list = field(default_factory=list)
    """List of (training_type_name, reason) tuples for missing/expired/under-level training."""

    verified: list = field(default_factory=list)
    """List of (training_type_name, expires_date) tuples for satisfied training."""

    def to_dict(self):
        """Convert to JSON-serializable dict for API responses / audit snapshots."""
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
    Get the training required for work, with the minimum level for each.

    Aggregates requirements from:
    - Step-level requirements
    - Process-level requirements (if process provided)
    - EquipmentType-level requirements (if equipment_type provided)

    When the same TrainingType is required by more than one source, the
    STRICTEST (highest) min_level wins.

    Returns:
        Dict mapping TrainingType instance -> required min_level (int)
    """
    required: dict = {}

    def _absorb(requirements):
        for req in requirements:
            tt = req.training_type
            if req.min_level > required.get(tt, 0):
                required[tt] = req.min_level

    _absorb(step.training_requirements.select_related('training_type').all())
    if process:
        _absorb(process.training_requirements.select_related('training_type').all())
    if equipment_type:
        _absorb(equipment_type.training_requirements.select_related('training_type').all())

    return required


def get_user_current_levels(user):
    """
    Get the user's current (in-date) competency level for each training type.

    A user may hold several records for one training type over time
    (renewals / progression); the current competency is the MAX level among
    their in-date records.

    Returns:
        Dict mapping training_type_id -> (level, expires_date)
    """
    from Tracker.models import TrainingRecord

    today = timezone.now().date()

    # tenant-safe: scoped to a specific user; users belong to one tenant
    current_records = TrainingRecord.objects.filter(
        user=user
    ).filter(
        models.Q(expires_date__isnull=True) | models.Q(expires_date__gte=today)
    ).select_related('training_type')

    levels: dict = {}
    for record in current_records:
        existing = levels.get(record.training_type_id)
        if existing is None or record.level > existing[0]:
            levels[record.training_type_id] = (record.level, record.expires_date)

    return levels


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
    required = get_required_training(step, process, equipment_type)

    # No requirements = authorized
    if not required:
        return TrainingAuthorizationResult(authorized=True)

    user_levels = get_user_current_levels(user)

    missing = []
    verified = []

    for training_type, min_level in required.items():
        held = user_levels.get(training_type.id)

        if held is not None and held[0] >= min_level:
            verified.append((training_type.name, held[1]))
        elif held is not None:
            # Holds a current record but below the required level.
            missing.append((
                training_type.name,
                f"Level {held[0]}, needs Level {min_level}",
            ))
        else:
            # No current record — expired or never completed.
            from Tracker.models import TrainingRecord
            expired_record = TrainingRecord.objects.filter(
                user=user,
                training_type=training_type,
                expires_date__lt=timezone.now().date()
            ).order_by('-expires_date').first()

            if expired_record:
                reason = f"Expired {expired_record.expires_date}"
            else:
                reason = f"Not completed (needs Level {min_level})"

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

    A user is qualified only if, for EVERY required training type, they hold a
    current (in-date) record at or above that requirement's min_level.

    Args:
        step: The Step
        process: Optional Process context
        equipment_type: Optional EquipmentType
        tenant: Optional Tenant to filter users

    Returns:
        QuerySet of User objects who meet every requirement at the required level
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

    # Each requirement has its own level threshold, so we can't use a single
    # distinct-count; intersect the qualifying user sets per (type, min_level).
    # tenant-safe: training types are already tenant-scoped upstream; RLS applies
    qualified_user_ids = None
    for training_type, min_level in required.items():
        ids = set(
            TrainingRecord.objects.filter(
                training_type=training_type,
                level__gte=min_level,
            ).filter(
                models.Q(expires_date__isnull=True) | models.Q(expires_date__gte=today)
            ).values_list('user_id', flat=True)
        )
        qualified_user_ids = ids if qualified_user_ids is None else (qualified_user_ids & ids)
        if not qualified_user_ids:
            break

    qs = User.objects.filter(id__in=(qualified_user_ids or set()))
    if tenant:
        qs = qs.filter(tenant=tenant)

    return qs


# Coverage bar: an operator counts as "qualified" on a training type at this level+.
QUALIFIED_AT = 3  # CompetencyLevel.QUALIFIED


def get_role_requirements(job_role):
    """
    Get the competence a job role requires, with the minimum level for each.

    Returns:
        Dict mapping TrainingType instance -> required min_level (int).
        Empty dict if job_role is None or has no requirements.
    """
    if job_role is None:
        return {}
    required: dict = {}
    for req in job_role.training_requirements.select_related('training_type').all():
        tt = req.training_type
        if req.min_level > required.get(tt, 0):
            required[tt] = req.min_level
    return required


def build_training_matrix(tenant=None):
    """
    Build the operators x training-types competency matrix.

    Returns a JSON-serializable dict:
        {
          "qualified_at": int,
          "training_types": [{"id", "name"}],
          "operators": [{"id", "name",
                         "cells": [{"training_type", "level", "level_display",
                                    "status", "expires_date"}]}],
          "coverage": [{"training_type", "qualified_count", "expiring_count"}],
        }

    A cell is emitted only when the operator has some standing on that type
    (a current level, or an expired record worth flagging); absent cells mean
    "no training". The current level for a (user, type) is the MAX level among
    the user's in-date records; if none are in-date but an expired record
    exists, the cell shows level 0 with status EXPIRED.
    """
    from Tracker.models import User, TrainingType, TrainingRecord

    types = list(TrainingType.objects.all().order_by('name'))

    users_qs = User.objects.filter(user_type='INTERNAL')
    if tenant:
        users_qs = users_qs.filter(tenant=tenant)
    users = list(users_qs.order_by('first_name', 'last_name', 'username'))

    # One pass over the tenant's records. `.objects` is tenant-scoped in-request;
    # `tenant` narrows further when called outside a request context.
    rec_qs = TrainingRecord.objects.select_related('training_type')
    if tenant:
        rec_qs = rec_qs.filter(user__tenant=tenant)

    # (user_id, type_id) -> best in-date cell dict; plus a set of pairs with an expired record.
    best: dict = {}
    expired_pairs: set = set()
    for rec in rec_qs:
        key = (rec.user_id, rec.training_type_id)
        if rec.is_current:
            cur = best.get(key)
            if cur is None or rec.level > cur['level']:
                best[key] = {
                    'level': rec.level,
                    'expires_date': rec.expires_date,
                    'status': rec.status,
                }
        else:
            expired_pairs.add(key)

    def _display(level):
        from Tracker.models import CompetencyLevel
        return CompetencyLevel(level).label if level else 'None'

    # Role requirements: job_role_id -> {type_id: strictest min_level}
    from Tracker.models import JobRole, TrainingRequirement
    role_reqs: dict = {}
    rr_qs = TrainingRequirement.objects.filter(job_role__isnull=False).select_related('training_type')
    if tenant:
        rr_qs = rr_qs.filter(job_role__tenant=tenant)
    for req in rr_qs:
        d = role_reqs.setdefault(req.job_role_id, {})
        if req.min_level > d.get(req.training_type_id, 0):
            d[req.training_type_id] = req.min_level

    roles_qs = JobRole.objects.all()
    if tenant:
        roles_qs = roles_qs.filter(tenant=tenant)
    all_roles = {r.id: r for r in roles_qs}
    job_roles = [
        {'id': str(r.id), 'name': r.name}
        for r in sorted((r for r in all_roles.values() if r.active), key=lambda r: r.name)
    ]

    operators = []
    # coverage counters keyed by type_id
    qualified_count = {t.id: 0 for t in types}
    expiring_count = {t.id: 0 for t in types}

    for user in users:
        req = role_reqs.get(user.job_role_id, {})   # {type_id: min_level}
        role = all_roles.get(user.job_role_id)
        cells = []
        gap_count = 0

        for t in types:
            key = (user.id, t.id)
            standing = best.get(key)
            required_level = req.get(t.id, 0)

            if standing is not None:
                level = standing['level']
                status = standing['status']
                expires = standing['expires_date']
                if level >= QUALIFIED_AT:
                    qualified_count[t.id] += 1
                if status == 'EXPIRING_SOON':
                    expiring_count[t.id] += 1
            elif key in expired_pairs:
                level, status, expires = 0, 'EXPIRED', None
            else:
                level, status, expires = 0, 'NONE', None

            gap = required_level > 0 and level < required_level
            if gap:
                gap_count += 1

            # Emit a cell when the operator has standing OR the role requires it
            # (so an unmet requirement shows as a gap even with no training).
            if standing is not None or key in expired_pairs or required_level > 0:
                cells.append({
                    'training_type': str(t.id),
                    'level': level,
                    'level_display': _display(level),
                    'status': status,
                    'expires_date': expires,
                    'required_level': required_level,
                    'gap': gap,
                })

        operators.append({
            'id': user.id,
            'name': user.get_full_name() or user.username,
            'job_role': str(user.job_role_id) if user.job_role_id else None,
            'job_role_name': role.name if role else '',
            'required_count': len(req),
            'gap_count': gap_count,
            'cells': cells,
        })

    return {
        'qualified_at': QUALIFIED_AT,
        'job_roles': job_roles,
        'training_types': [{'id': str(t.id), 'name': t.name} for t in types],
        'operators': operators,
        'coverage': [
            {
                'training_type': str(t.id),
                'qualified_count': qualified_count[t.id],
                'expiring_count': expiring_count[t.id],
            }
            for t in types
        ],
    }

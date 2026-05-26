"""
Change Control models — PCR / PCO / PCN three-stage workflow.

See `Documents/CHANGE_CONTROL_PLAN.md` for the design rationale.

Phase 1 covers process-change artifacts only. Document-change artifacts
(DCR / DCO / DCN) reusing the same abstract bases come in Phase 2.

Out of scope (across all phases): FDA / medical device compliance.
Supported regulatory targets are ISO 9001 8.5.6 (SIMPLIFIED mode),
IATF 16949 8.5.6.1, and AS9100D 8.5.6 (REGULATED mode).
"""
from __future__ import annotations

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from .core import SecureModel
from .qms import VoidableModel


# ---------------------------------------------------------------------------
# Shared choices
# ---------------------------------------------------------------------------

class ChangeControlPriority(models.TextChoices):
    """Priority for any change-control artifact."""
    LOW = 'LOW', 'Low'
    NORMAL = 'NORMAL', 'Normal'
    HIGH = 'HIGH', 'High'
    CRITICAL = 'CRITICAL', 'Critical'


class ChangeControlDataOrigin(models.TextChoices):
    """Whether an artifact was created natively or backfilled from import.

    Imported records bypass the live workflow (no ApprovalRequest, no
    notifications, no version creation) and arrive in their final state
    with backdated timestamps. Used during onboarding data migration.
    """
    NATIVE = 'NATIVE', 'Native'
    IMPORTED = 'IMPORTED', 'Imported'


class ProcessChangeMigrationDisposition(models.TextChoices):
    """Disposition of in-flight WorkOrders when a PCO is implemented.

    PENDING is the default before the implementer makes a decision.
    """
    PENDING = 'PENDING', 'Pending'
    MIGRATE_ALL = 'MIGRATE_ALL', 'Migrate All'
    MIGRATE_SELECTED = 'MIGRATE_SELECTED', 'Migrate Selected'
    KEEP_ALL = 'KEEP_ALL', 'Keep All'


# ---------------------------------------------------------------------------
# Sequencing — per-tenant per-type per-year artifact_number generation
# ---------------------------------------------------------------------------

class ArtifactSequence(SecureModel):
    """Counter table for `artifact_number` generation.

    Per-tenant, per-artifact-type, per-year sequence. The next_value
    column is read-and-incremented under SELECT FOR UPDATE inside a
    transaction by the sequencing service.

    Format: `{ARTIFACT_TYPE}-{YEAR}-{SEQ:04d}` — e.g. `PCR-2026-0001`.

    artifact_type values match the prefix portion of the format string
    (PCR, PCO, PCN, DCR, DCO, DCN, ...).
    """

    artifact_type = models.CharField(max_length=8)
    year = models.PositiveIntegerField()
    next_value = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = 'Artifact Number Sequence'
        verbose_name_plural = 'Artifact Number Sequences'
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'artifact_type', 'year'],
                name='artifactsequence_one_per_tenant_type_year',
            ),
        ]
        indexes = [
            models.Index(fields=['tenant', 'artifact_type', 'year']),
        ]

    def __str__(self):
        return f"{self.artifact_type}-{self.year}: next={self.next_value}"


# ---------------------------------------------------------------------------
# Abstract base classes
# ---------------------------------------------------------------------------

class BaseChangeArtifact(SecureModel, VoidableModel):
    """Common scaffolding for any change-control artifact.

    SecureModel provides: id, tenant, created_at, updated_at, archived,
    deleted_at, version chain, plus tenant auto-scoping via ContextVar.

    VoidableModel provides: is_voided, voided_at, voided_by, void_reason.

    Subclasses add: status (with their own choices), plus type-specific
    fields. Concrete subclasses must define a `STATUS_CHOICES` class
    attribute and a `status` field referencing it (Django doesn't allow
    overriding choices on an inherited field cleanly, so each concrete
    model declares its own status field).
    """

    artifact_number = models.CharField(
        max_length=32,
        db_index=True,
        help_text='Per-tenant identifier, e.g. PCR-2026-0001. '
                  'Generated via ArtifactSequence.',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )
    data_origin = models.CharField(
        max_length=16,
        choices=ChangeControlDataOrigin.choices,
        default=ChangeControlDataOrigin.NATIVE,
    )

    class Meta:
        abstract = True
        # Inherit SecureModel.Meta's manager-name settings so Django
        # internals (DRF, drf-filter, schema generation) reach for
        # `unscoped` instead of `objects` when introspecting the model.
        # Without this, our intermediate abstract Meta would drop the
        # SecureModel.Meta values and `_default_manager` would resolve
        # to SecureManager (which raises without tenant context).
        base_manager_name = 'unscoped'
        default_manager_name = 'unscoped'


class BaseChangeRequest(BaseChangeArtifact):
    """Shared fields for any *Request artifact (PCR / DCR).

    The Request stage is the proposal / case file: what's being proposed,
    why, initial impact, risk. Approved Requests trigger creation of an
    Order; rejected Requests are terminal and retry creates a new Request
    that can optionally point back via `superseded_by_request_*`.
    """

    title = models.CharField(max_length=255)
    proposed_change = models.TextField(
        help_text='What is being proposed.',
    )
    justification = models.TextField(
        help_text='Why the change is needed.',
    )
    risk_analysis = models.TextField(
        help_text='What could go wrong, and what mitigations apply. '
                  'Free-text in Phase 1; structured S/P/D scoring is '
                  'Phase 5 territory.',
    )
    priority = models.CharField(
        max_length=16,
        choices=ChangeControlPriority.choices,
        default=ChangeControlPriority.NORMAL,
    )

    submitted_at = models.DateTimeField(null=True, blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )
    rejected_reason = models.TextField(blank=True, default='')

    customer_notification_required = models.BooleanField(
        default=False,
        help_text='Flag PPAP / customer-flow-down triggers. The actual '
                  'submission is handled outside this system.',
    )

    # Optional forward link from a rejected Request to the new attempt.
    # GFK so a PCR can be superseded by a different change_type's
    # Request if cross-type supersession ever becomes useful (currently
    # PCR → PCR is the only realistic path).
    superseded_by_request_ct = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )
    superseded_by_request_id = models.UUIDField(null=True, blank=True)
    superseded_by_request = GenericForeignKey(
        'superseded_by_request_ct',
        'superseded_by_request_id',
    )

    class Meta:
        abstract = True
        # Inherit SecureModel.Meta's manager-name settings so Django
        # internals (DRF, drf-filter, schema generation) reach for
        # `unscoped` instead of `objects` when introspecting the model.
        # Without this, our intermediate abstract Meta would drop the
        # SecureModel.Meta values and `_default_manager` would resolve
        # to SecureManager (which raises without tenant context).
        base_manager_name = 'unscoped'
        default_manager_name = 'unscoped'


class BaseChangeOrder(BaseChangeArtifact):
    """Shared fields for any *Order artifact (PCO / DCO).

    The Order stage is the authorization to implement an approved
    Request. Carries the implementation plan, effective date, and
    approval / implementation signatures. Implementing an Order
    triggers the actual change (process version flip, document
    version flip) and creates the corresponding Notice.
    """

    implementation_plan = models.TextField(
        help_text='How the change will be carried out, who is '
                  'responsible, what artifacts will be modified.',
    )
    effective_date = models.DateField(
        null=True,
        blank=True,
        help_text='Calendar date the change takes effect.',
    )

    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )
    implemented_at = models.DateTimeField(null=True, blank=True)
    implemented_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )

    class Meta:
        abstract = True
        # Inherit SecureModel.Meta's manager-name settings so Django
        # internals (DRF, drf-filter, schema generation) reach for
        # `unscoped` instead of `objects` when introspecting the model.
        # Without this, our intermediate abstract Meta would drop the
        # SecureModel.Meta values and `_default_manager` would resolve
        # to SecureManager (which raises without tenant context).
        base_manager_name = 'unscoped'
        default_manager_name = 'unscoped'


class BaseChangeNotice(BaseChangeArtifact):
    """Shared fields for any *Notice artifact (PCN / DCN).

    The Notice stage is the communication of a completed change to
    affected stakeholders. Distribution and audience routing are
    handled by the existing NotificationRule infrastructure on the
    artifact's release event — no per-Notice audience field in
    Phase 1. Closure captures effectiveness verification.
    """

    notice_content = models.TextField(
        help_text='Distributable description of what changed, when it '
                  'takes effect, and what affected parties need to do.',
    )

    released_at = models.DateTimeField(null=True, blank=True)
    released_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )

    closure_evidence = models.TextField(
        blank=True,
        default='',
        help_text='Effectiveness verification narrative recorded at '
                  'closure. Phase 5 will add structured metrics.',
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )

    class Meta:
        abstract = True
        # Inherit SecureModel.Meta's manager-name settings so Django
        # internals (DRF, drf-filter, schema generation) reach for
        # `unscoped` instead of `objects` when introspecting the model.
        # Without this, our intermediate abstract Meta would drop the
        # SecureModel.Meta values and `_default_manager` would resolve
        # to SecureManager (which raises without tenant context).
        base_manager_name = 'unscoped'
        default_manager_name = 'unscoped'


# ---------------------------------------------------------------------------
# Concrete models — Process Change (Phase 1)
# ---------------------------------------------------------------------------

class ProcessChangeRequest(BaseChangeRequest):
    """PCR — proposal to change a manufacturing process.

    Created against a specific approved Process. Submission snapshots
    affected in-flight WorkOrders and records the baseline version
    (future-proofing for Phase 5 parallel mode where rebasing requires
    the original baseline).

    Serial constraint: at most one open PCR (status DRAFT / SUBMITTED /
    UNDER_REVIEW / APPROVED, not voided) per target_process. Phase 5
    parallel-mode support drops this constraint without schema migration.
    """

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SUBMITTED = 'SUBMITTED', 'Submitted'
        UNDER_REVIEW = 'UNDER_REVIEW', 'Under Review'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        CANCELLED = 'CANCELLED', 'Cancelled'

    OPEN_STATUSES = (
        Status.DRAFT,
        Status.SUBMITTED,
        Status.UNDER_REVIEW,
        Status.APPROVED,
    )

    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )

    target_process = models.ForeignKey(
        'Tracker.Processes',
        on_delete=models.PROTECT,
        related_name='change_requests',
    )

    # Captured at submission. Records which Processes.id this PCR was
    # proposed against. Serial mode doesn't strictly need it (baseline
    # is always "current"); this is one of the four future-proofing
    # moves for Phase 5 parallel mode where rebasing requires the
    # original baseline.
    baseline_version_id = models.UUIDField(
        null=True,
        blank=True,
        help_text='The Tracker.Processes.id this PCR was proposed against. '
                  'Captured at submission.',
    )

    # Snapshot of {wo_id, erp_id, status, current_step_order, parts_count}
    # at submission time. Used by the PCO implementation panel to show
    # affected WorkOrders for migration disposition.
    affected_workorders_snapshot = models.JSONField(default=list, blank=True)

    class Meta:
        verbose_name = 'Process Change Request'
        verbose_name_plural = 'Process Change Requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status', 'created_at']),
            models.Index(fields=['target_process', 'status']),
        ]
        constraints = [
            # Serial: at most one open PCR per target_process.
            # Drop this constraint to enable Phase 5 parallel mode.
            models.UniqueConstraint(
                fields=['target_process'],
                condition=models.Q(
                    status__in=['DRAFT', 'SUBMITTED', 'UNDER_REVIEW', 'APPROVED'],
                    is_voided=False,
                ),
                name='processchangerequest_one_open_per_process',
            ),
        ]

    def __str__(self):
        return f"{self.artifact_number}: {self.title}"

    @property
    def is_open(self) -> bool:
        """True if the PCR is in any pre-terminal status and not voided."""
        return self.status in self.OPEN_STATUSES and not self.is_voided


class ProcessChangeOrder(BaseChangeOrder):
    """PCO — authorization to implement an approved PCR.

    Pattern C: PCO authoring creates a DRAFT process version copying
    current state, edited via the existing process editor, then flipped
    to APPROVED at PCO implementation via the existing approve_process
    service. The DRAFT is linked via `draft_process_version`.

    Implementation also captures the disposition of in-flight WorkOrders
    (migration_disposition + migration_reason + migrated_workorder_ids).
    Per-WO migration events are recorded in auditlog on the
    WorkOrder.process FK change — no separate per-WO ticket model.
    """

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        APPROVED = 'APPROVED', 'Approved'
        IN_IMPLEMENTATION = 'IN_IMPLEMENTATION', 'In Implementation'
        IMPLEMENTED = 'IMPLEMENTED', 'Implemented'
        CANCELLED = 'CANCELLED', 'Cancelled'

    OPEN_STATUSES = (
        Status.DRAFT,
        Status.APPROVED,
        Status.IN_IMPLEMENTATION,
    )

    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )

    request = models.OneToOneField(
        ProcessChangeRequest,
        on_delete=models.PROTECT,
        related_name='order',
    )

    draft_process_version = models.ForeignKey(
        'Tracker.Processes',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='+',
        help_text='DRAFT process version created during PCO authoring '
                  '(Pattern C). Edited via the existing process editor, '
                  'flipped to APPROVED at PCO implementation.',
    )

    migration_disposition = models.CharField(
        max_length=24,
        choices=ProcessChangeMigrationDisposition.choices,
        default=ProcessChangeMigrationDisposition.PENDING,
    )
    migration_reason = models.TextField(blank=True, default='')
    migrated_workorder_ids = models.JSONField(default=list, blank=True)

    class Meta:
        verbose_name = 'Process Change Order'
        verbose_name_plural = 'Process Change Orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status', 'created_at']),
        ]

    def __str__(self):
        return f"{self.artifact_number} (← {self.request.artifact_number})"

    @property
    def is_open(self) -> bool:
        return self.status in self.OPEN_STATUSES and not self.is_voided


class ProcessChangeNotice(BaseChangeNotice):
    """PCN — distribution and effectiveness verification of an
    implemented PCO.

    Audience routing handled by existing NotificationRule on the
    PCN_RELEASED event. No per-Notice audience field in Phase 1.
    Acknowledgment tracking is Phase 5 territory.
    """

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        RELEASED = 'RELEASED', 'Released'
        CLOSED = 'CLOSED', 'Closed'

    OPEN_STATUSES = (
        Status.DRAFT,
        Status.RELEASED,
    )

    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )

    order = models.OneToOneField(
        ProcessChangeOrder,
        on_delete=models.PROTECT,
        related_name='notice',
    )

    class Meta:
        verbose_name = 'Process Change Notice'
        verbose_name_plural = 'Process Change Notices'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status', 'created_at']),
        ]

    def __str__(self):
        return f"{self.artifact_number} (← {self.order.artifact_number})"

    @property
    def is_open(self) -> bool:
        return self.status in self.OPEN_STATUSES and not self.is_voided

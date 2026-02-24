"""
QMS (Quality Management System) Models Module

This module contains all Quality Management System related models including:
- Quality reports and error tracking
- Measurement results
- Quarantine disposition workflows
- Equipment usage tracking
- Step transitions and QA approvals
- CAPA (Corrective and Preventive Actions)
- Root Cause Analysis (RCA)
- 3D Models and Heatmap Annotations for spatial quality inspection

Note: Sampling models (SamplingRuleSet, SamplingRule, etc.) are in mes_lite.py
      MeasurementDefinition is in mes_lite.py
      SecureModel, User, and Documents are in core.py
"""

from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.conf import settings

from .core import SecureModel, User


class QualityErrorsList(SecureModel):
    """
    Defines a type of known quality error that can be associated with a part inspection.

    This model serves as a reference catalog of defect types, optionally scoped to a specific part type.
    Each entry includes a name and a textual example to help inspectors identify and classify errors accurately.
    """

    documents = GenericRelation('Tracker.Documents')
    """Reference photos, acceptance criteria visuals, or documentation for this error type."""

    error_name = models.CharField(max_length=50)
    """Short descriptive name of the error (e.g., 'Crack', 'Surface Porosity')."""

    error_example = models.TextField()
    """Detailed example or explanation of what the error typically looks like."""

    part_type = models.ForeignKey("PartTypes", on_delete=models.SET_NULL, null=True, blank=True)
    """
    Optional link to a specific `PartType` this error is associated with.
    If unset, the error may be considered general-purpose or applicable across multiple part types.
    """

    requires_3d_annotation = models.BooleanField(default=False)
    """
    Indicates whether this error type requires 3D model annotation when reported.
    If True, inspectors must annotate the defect location on the 3D model when creating a quality report.
    Spatial defects (e.g., Crack, Porosity, Burn Mark) should set this to True.
    Process defects (e.g., Wrong Material, Late Delivery) can leave this False.
    """

    def __str__(self):
        """
        Returns a readable label showing the error name and associated part type.
        """
        return f"{self.error_name} ({self.part_type})" if self.part_type else self.error_name


class DefectSeverity(models.TextChoices):
    """Severity classification for individual defect instances."""
    MINOR = 'minor', 'Minor'
    MAJOR = 'major', 'Major'
    CRITICAL = 'critical', 'Critical'


class QualityReportDefect(models.Model):
    """
    Through model linking QualityReports to QualityErrorsList with per-defect metadata.

    Enables proper QMS tracking:
    - Defect counts for Pareto analysis
    - Location tracking for pattern detection
    - Per-instance severity classification
    """
    report = models.ForeignKey(
        'QualityReports',
        on_delete=models.CASCADE,
        related_name='defects'
    )
    error_type = models.ForeignKey(
        QualityErrorsList,
        on_delete=models.PROTECT,
        related_name='report_instances'
    )

    count = models.PositiveIntegerField(
        default=1,
        help_text="Number of this defect type found"
    )
    location = models.CharField(
        max_length=100,
        blank=True,
        help_text="Location on part (e.g., 'Near bore #3', 'Left edge')"
    )
    severity = models.CharField(
        max_length=20,
        choices=DefectSeverity.choices,
        default=DefectSeverity.MAJOR,
        help_text="Severity of this specific defect instance"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional details about this defect"
    )

    class Meta:
        ordering = ['-severity', 'error_type__error_name']

    def __str__(self):
        return f"{self.count}x {self.error_type.error_name} ({self.severity})"


class QualityReports(SecureModel):
    """
    Records an instance of a quality issue or operational anomaly identified during part production.

    This model captures contextual information such as the affected part, the machine in use,
    who detected/verified the defect, a textual description, and the defect types observed.

    Personnel tracking uses named roles for proper QMS compliance:
    - detected_by: Who found the defect (required)
    - operator: Who was running the process (optional, for root cause)
    - verified_by: Second signature for critical items (optional)

    Defect types are linked via QualityReportDefect through model, enabling:
    - Counts per defect type for Pareto analysis
    - Location tracking for pattern detection
    - Per-instance severity classification
    """

    STATUS_CHOICES = [("PASS", "Pass"), ("FAIL", "Fail"), ("PENDING", "Pending")]

    report_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="Auto-generated: QR-YYYY-######"
    )
    """Unique report number for audit reference, auto-generated on creation."""

    documents = GenericRelation('Tracker.Documents')
    """Documents attached to this quality report (inspection photos, test results, etc.)"""

    step = models.ForeignKey("Steps", on_delete=models.SET_NULL, null=True, blank=True)

    part = models.ForeignKey("Parts", on_delete=models.SET_NULL, null=True, blank=True, related_name="error_reports")
    """The specific part associated with this error report (if known)."""

    machine = models.ForeignKey("Equipments", on_delete=models.SET_NULL, null=True, blank=True)
    """The equipment or machine used when the error was encountered (if applicable)."""

    # Named operator/inspector roles (replaces M2M for proper QMS tracking)
    detected_by = models.ForeignKey(
        User, on_delete=models.PROTECT,
        null=True, blank=False,  # Nullable for migration, but required in forms
        related_name='defects_detected',
        help_text="Inspector/operator who detected the defect (required for new reports)"
    )
    """Who found and reported this defect. Required for new reports; null for legacy data."""

    operators = models.ManyToManyField(
        User,
        blank=True,
        related_name='defects_during_operation',
        help_text="Operators running the process when defect occurred (for root cause)"
    )
    """Optional: Who was operating when the defect occurred (may differ from detector)."""

    verified_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='defects_verified',
        help_text="Second signature for critical inspections (aerospace/medical)"
    )
    """Optional: Witness/verifier for critical quality checks."""

    sampling_method = models.CharField(max_length=50, default="manual")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)

    is_first_piece = models.BooleanField(
        default=False,
        help_text="If True, this inspection is a First Piece Inspection (FPI) for setup verification"
    )
    """
    First Piece Inspection flag - marks this inspection as an FPI.
    FPI inspections verify setup correctness before full production begins.
    A passing FPI unlocks production for subsequent parts at this step.
    """

    description = models.TextField(max_length=300, null=True, blank=True)
    """A detailed description of the issue or anomaly observed."""

    file = models.ForeignKey("Documents", null=True, blank=True, on_delete=models.SET_NULL)
    """Optional file attachment providing supporting evidence (e.g., photo, scan, or log)."""

    errors = models.ManyToManyField(
        QualityErrorsList,
        through='QualityReportDefect',
        blank=True,
        related_name='quality_reports'
    )
    """Defect types with counts, location, and severity via QualityReportDefect."""

    sampling_audit_log = models.ForeignKey('Tracker.SamplingAuditLog', null=True, blank=True, on_delete=models.SET_NULL,
                                           help_text="Links to the sampling decision that triggered this inspection")
    """Link to the sampling audit log that triggered this quality report."""

    class Meta:
        verbose_name_plural = 'Error Reports'
        verbose_name = 'Error Report'
        permissions = [
            ("approve_qualityreports", "Can approve quality reports"),
            ("approve_own_qualityreports", "Can approve own quality reports"),
        ]
        indexes = [
            models.Index(fields=['part', 'status'], name='qr_part_status_idx'),
            models.Index(fields=['step', 'created_at'], name='qr_step_created_idx'),
            models.Index(fields=['status', 'created_at'], name='qr_status_created_idx'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'report_number'],
                condition=models.Q(report_number__isnull=False) & ~models.Q(report_number=''),
                name='qualityreport_tenant_number_uniq'
            ),
        ]

    def __str__(self):
        """
        Returns a summary string indicating which part the report refers to and the date.
        """
        if self.report_number:
            return f"{self.report_number} - {self.part}"
        return f"Quality Report for {self.part} on {self.created_at.date()}"

    @classmethod
    def generate_report_number(cls, tenant=None):
        """Auto-generate report number: QR-YYYY-######

        Uses SELECT FOR UPDATE to prevent race conditions under concurrent load.
        """
        from Tracker.utils.sequences import generate_next_sequence

        year = timezone.now().year
        prefix = f"QR-{year}-"

        return generate_next_sequence(
            queryset=cls.objects,
            number_field='report_number',
            prefix=prefix,
            padding=6,
            tenant=tenant
        )

    def save(self, *args, **kwargs):
        """Enhanced save with report number generation and sampling integration"""
        from Tracker.models import PartsStatus, SamplingTriggerManager, SamplingAnalytics, SamplingAuditLog
        from Tracker.sampling import SamplingFallbackApplier

        is_new = self.pk is None

        # Auto-generate report number on creation
        if not self.report_number:
            self.report_number = self.generate_report_number(self.tenant)

        super().save(*args, **kwargs)

        if is_new:
            # Link to sampling audit log if this was a sampled part
            self._link_sampling_audit_log()

            # Update sampling trigger state
            if self.status in {"PASS", "FAIL"}:
                SamplingTriggerManager(self.part, self.status).update_state()

            # Trigger fallback if failure
            if self.status == "FAIL":
                self._trigger_sampling_fallback()

                # Auto-quarantine part on FAIL
                if self.part:
                    self.part.part_status = PartsStatus.QUARANTINED
                    self.part.save(update_fields=['part_status'])

            # Update sampling analytics
            self._update_sampling_analytics()

    def _link_sampling_audit_log(self):
        """Link quality report to the sampling decision that triggered it"""
        from Tracker.models import SamplingAuditLog

        if self.part and self.part.requires_sampling:
            # Find the most recent sampling audit log for this part
            audit_log = SamplingAuditLog.objects.filter(part=self.part, sampling_decision=True).order_by(
                '-timestamp').first()

            if audit_log:
                self.sampling_audit_log = audit_log
                self.save(update_fields=['sampling_audit_log'])

    def _trigger_sampling_fallback(self):
        """Trigger fallback sampling for remaining parts"""
        from Tracker.sampling import SamplingFallbackApplier

        if self.part and self.part.sampling_ruleset:
            # Use the new method instead
            trigger_state = self.part.sampling_ruleset.create_fallback_trigger(triggering_part=self.part,
                                                                               quality_report=self)
            return trigger_state

        # Fallback to original method
        fallback_applier = SamplingFallbackApplier(self.part)
        fallback_applier.apply()

    def _update_sampling_analytics(self):
        """Update sampling analytics based on quality report results"""
        from Tracker.models import SamplingAnalytics

        if not self.part or not self.part.sampling_ruleset:
            return

        analytics, created = SamplingAnalytics.objects.get_or_create(ruleset=self.part.sampling_ruleset,
                                                                     work_order=self.part.work_order,
                                                                     defaults={'parts_sampled': 0,
                                                                               'parts_total': self.part.work_order.quantity,
                                                                               'defects_found': 0,
                                                                               'actual_sampling_rate': 0.0,
                                                                               'target_sampling_rate': 0.0,
                                                                               'variance': 0.0})

        # Update counters
        analytics.parts_sampled += 1
        if self.status == "FAIL":
            analytics.defects_found += 1

        # Recalculate rates
        analytics.actual_sampling_rate = (analytics.parts_sampled / analytics.parts_total * 100)
        analytics.variance = abs(analytics.actual_sampling_rate - analytics.target_sampling_rate)

        analytics.save()

    def clean(self):
        """Validate that sampled parts have sampling requirements"""
        if self.part and not self.part.requires_sampling:
            from django.core.exceptions import ValidationError
            raise ValidationError("Cannot create quality report for non-sampled part")


class MeasurementResult(SecureModel):
    """
    Records the result of a single measurement taken during quality inspection.

    Automatically evaluates whether the measurement is within specification.
    """
    report = models.ForeignKey("QualityReports", on_delete=models.CASCADE, related_name="measurements")
    definition = models.ForeignKey("MeasurementDefinition", on_delete=models.CASCADE)
    value_numeric = models.FloatField(null=True, blank=True)
    value_pass_fail = models.CharField(max_length=4, choices=[("PASS", "Pass"), ("FAIL", "Fail")], null=True,
                                       blank=True)
    is_within_spec = models.BooleanField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    def save(self, *args, **kwargs):
        # Auto-calculate is_within_spec before saving
        self.is_within_spec = self.evaluate_spec()
        super().save(*args, **kwargs)

    def evaluate_spec(self):
        if self.definition.type == "NUMERIC":
            if self.value_numeric is None:
                return False
            return (
                    self.definition.nominal - self.definition.lower_tol <= self.value_numeric <= self.definition.nominal + self.definition.upper_tol)
        if self.definition.type == "PASS_FAIL":
            return self.value_pass_fail == "PASS"
        return False


class EquipmentUsage(SecureModel):
    """
    Tracks the usage of equipment on a specific part and step in the manufacturing process.

    Each record logs when a piece of equipment was used, by whom, and optionally links to an error report
    if an issue occurred during usage. This model supports traceability of machine activity and is useful
    for both auditing and performance analysis.
    """

    equipment = models.ForeignKey("Equipments", on_delete=models.SET_NULL, null=True, blank=True)
    """The equipment or machine that was used."""

    step = models.ForeignKey("Steps", on_delete=models.SET_NULL, null=True, blank=True)
    """The specific step in the manufacturing process during which the equipment was used."""

    part = models.ForeignKey("Parts", on_delete=models.SET_NULL, null=True, blank=True)
    """The part involved in the usage event."""

    error_report = models.ForeignKey(QualityReports, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name="equipment_usages")
    """Optional link to an error report generated during or after this usage event."""

    used_at = models.DateTimeField(auto_now_add=True)
    """Timestamp indicating when the equipment was used."""

    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    """The user or operator who performed the operation using the equipment."""

    notes = models.TextField(blank=True)
    """Optional notes capturing additional context or observations during usage."""

    class Meta:
        verbose_name_plural = 'Equipment Usage'
        verbose_name = 'Equipment Usage'

    def __str__(self):
        """
        Returns a human-readable summary combining equipment, part, and step information.
        """
        return f"{self.equipment} on {self.part} (step: {self.step})"


class StepTransitionLog(SecureModel):
    """
    Logs each transition of a part from one step to the next within a manufacturing process.

    This model enables historical tracking of part progression for auditing, traceability,
    and metrics collection. Each log entry captures the part, the step it moved to,
    the operator who performed the transition, and the timestamp of the event.
    """

    step = models.ForeignKey("Steps", on_delete=models.SET_NULL, null=True, blank=True,
                             help_text="The step the part transitioned to.")
    """ForeignKey to the `Steps` instance representing the current step reached."""

    part = models.ForeignKey("Parts", on_delete=models.SET_NULL, null=True, blank=True,
                             help_text="The part that transitioned to the step.")
    """ForeignKey to the `Parts` instance being tracked."""

    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                 help_text="The user (operator) who performed the step transition.")
    """ForeignKey to the `User` who executed the step transition."""

    timestamp = models.DateTimeField(auto_now_add=True,
                                     help_text="Timestamp automatically recorded at the time of transition.")
    """Datetime when the step transition occurred (auto-generated)."""

    class Meta:
        verbose_name_plural = 'Step Transition Log'
        verbose_name = 'Step Transition Log'

    def __str__(self):
        """
        Return a human-readable summary of the transition event.
        """
        return f"Step '{self.step.name}' for {self.part} completed at {self.timestamp}"


class QaApproval(SecureModel):
    """
    Records QA staff approval for a work order at a specific step.

    Ensures proper authorization and audit trail for quality signoff requirements.
    """
    step = models.ForeignKey("Steps", related_name='qa_approvals', on_delete=models.PROTECT)
    work_order = models.ForeignKey("WorkOrder", related_name='qa_approvals', on_delete=models.PROTECT)
    qa_staff = models.ForeignKey(User, related_name='qa_approvals', on_delete=models.PROTECT)


class QuarantineDisposition(SecureModel):
    """
    Disposition workflow for failed quality reports.

    Tracks the workflow for handling quarantined parts including rework, repair, scrap,
    use-as-is, and return-to-supplier decisions. Supports AS9100D and IATF 16949 requirements
    for automotive, aerospace, and remanufacturing industries.
    """

    STATE_CHOICES = [('OPEN', 'Open'), ('IN_PROGRESS', 'In Progress'), ('CLOSED', 'Closed'), ]

    DISPOSITION_TYPES = [
        ('REWORK', 'Rework'),           # Return to full conformance via process
        ('REPAIR', 'Repair'),           # AS9100: May deviate from spec, requires approval
        ('SCRAP', 'Scrap'),
        ('USE_AS_IS', 'Use As Is'),
        ('RETURN_TO_SUPPLIER', 'Return to Supplier'),
    ]

    SEVERITY_CHOICES = [
        ('CRITICAL', 'Critical'),   # Safety/regulatory, requires special handling
        ('MAJOR', 'Major'),         # Affects function, correctable
        ('MINOR', 'Minor'),         # Cosmetic, no function impact
    ]

    # Basic fields
    disposition_number = models.CharField(max_length=20, editable=False)
    current_state = models.CharField(max_length=15, choices=STATE_CHOICES, default='OPEN')
    disposition_type = models.CharField(max_length=20, choices=DISPOSITION_TYPES, blank=True)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='MAJOR')

    # QA workflow
    assigned_to = models.ForeignKey(User, on_delete=models.PROTECT, related_name='assigned_dispositions', null=True,
                                    blank=True)
    description = models.TextField(blank=True)
    resolution_notes = models.TextField(blank=True)

    # Containment tracking (immediate action taken to prevent escape)
    containment_action = models.TextField(blank=True, help_text="Immediate action taken to prevent escape")
    containment_completed_at = models.DateTimeField(null=True, blank=True)
    containment_completed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='containment_actions'
    )

    # Customer approval tracking (simple - airgapped LAN)
    requires_customer_approval = models.BooleanField(default=False)
    customer_approval_received = models.BooleanField(default=False)
    customer_approval_reference = models.CharField(
        max_length=100, blank=True,
        help_text="PO#, email reference, or approval document number"
    )
    customer_approval_date = models.DateField(null=True, blank=True)

    # Scrap verification (optional, not enforced as gate)
    scrap_verified = models.BooleanField(default=False)
    scrap_verification_method = models.CharField(
        max_length=100, blank=True,
        help_text="How product was rendered unusable: crushed, marked, etc."
    )
    scrap_verified_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='scrap_verifications'
    )
    scrap_verified_at = models.DateTimeField(null=True, blank=True)

    # Resolution tracking
    resolution_completed = models.BooleanField(default=False)
    resolution_completed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='completed_dispositions')
    resolution_completed_at = models.DateTimeField(null=True, blank=True)

    # Relationships
    part = models.ForeignKey('Parts', on_delete=models.PROTECT, null=True, blank=True)
    step = models.ForeignKey('Steps', on_delete=models.PROTECT, null=True, blank=True, related_name='dispositions')
    quality_reports = models.ManyToManyField('QualityReports', related_name='dispositions')
    documents = GenericRelation('Documents')

    # Rework tracking
    rework_attempt_at_step = models.IntegerField(default=1)
    """Which rework attempt this is at the specific step (1st, 2nd, 3rd, etc.)"""

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Disposition'
        verbose_name_plural = 'Dispositions'
        permissions = [
            ("approve_disposition", "Can approve disposition decisions"),
            ("close_disposition", "Can close dispositions"),
        ]
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'disposition_number'], name='disposition_tenant_number_uniq'),
        ]
        indexes = [
            models.Index(fields=['current_state', 'created_at'], name='disposition_state_created_idx'),
            models.Index(fields=['part', 'current_state'], name='disposition_part_state_idx'),
        ]

    def __str__(self):
        return f"{self.disposition_number} - {self.get_current_state_display()}"

    def save(self, *args, **kwargs):
        from Tracker.models import PartsStatus

        old_disposition_type = None
        old_state = None

        # Track changes for status updates
        if self.pk:
            try:
                old_instance = QuarantineDisposition.objects.get(pk=self.pk)
                old_disposition_type = old_instance.disposition_type
                old_state = old_instance.current_state
            except QuarantineDisposition.DoesNotExist:
                pass

        if not self.disposition_number:
            self.disposition_number = self._generate_disposition_number()

        # Auto-set requires_customer_approval for USE_AS_IS or REPAIR
        if self.disposition_type in ['USE_AS_IS', 'REPAIR']:
            self.requires_customer_approval = True

        # Auto-transition from OPEN to IN_PROGRESS when disposition type is set
        if self.disposition_type and self.current_state == 'OPEN':
            self.current_state = 'IN_PROGRESS'

        # Block transition to CLOSED if annotations are pending
        if self.current_state == 'CLOSED' and old_state != 'CLOSED':
            has_pending, pending_reports = self.has_pending_annotations()
            if has_pending:
                raise ValueError(
                    f"Cannot close disposition: 3D annotations required for {len(pending_reports)} quality report(s). "
                    "Complete annotations before closing."
                )

        super().save(*args, **kwargs)

        # Update part status when disposition type changes or state changes
        if (old_disposition_type != self.disposition_type or old_state != self.current_state) and self.part:
            self._update_part_status()

    def _generate_disposition_number(self):
        """Generate disposition number with race condition protection.

        Uses SELECT FOR UPDATE to prevent duplicates under concurrent load.
        """
        from Tracker.utils.sequences import generate_next_sequence

        year = timezone.now().year
        prefix = f'DISP-{year}-'

        return generate_next_sequence(
            queryset=QuarantineDisposition.objects,
            number_field='disposition_number',
            prefix=prefix,
            padding=6,
            tenant=self.tenant if self.tenant_id else None
        )

    def complete_resolution(self, completed_by_user):
        """Mark resolution as completed and close disposition if appropriate.

        Raises:
            ValueError: If disposition cannot be completed (missing annotations, etc.)
        """
        blockers = self.get_completion_blockers()
        if blockers:
            raise ValueError(f"Cannot complete disposition: {'; '.join(blockers)}")

        self.resolution_completed = True
        self.resolution_completed_by = completed_by_user
        self.resolution_completed_at = timezone.now()

        # Auto-close if currently in progress
        if self.current_state == 'IN_PROGRESS':
            self.current_state = 'CLOSED'

        self.save()
        return self

    def _update_part_status(self):
        """Update part status based on disposition type and state"""
        from Tracker.models import PartsStatus

        if not self.part or not self.disposition_type:
            return

        # Only update if disposition is being implemented/closed
        if self.current_state not in ['IN_PROGRESS', 'CLOSED']:
            return

        # Map disposition types to part statuses (QMS standard workflow)
        # REPAIR uses same status as REWORK per AS9100 - both need rework processing
        status_mapping = {
            'REWORK': PartsStatus.REWORK_NEEDED,
            'REPAIR': PartsStatus.REWORK_NEEDED,  # AS9100: May not fully conform, requires approval
            'SCRAP': PartsStatus.SCRAPPED,
            'USE_AS_IS': PartsStatus.READY_FOR_NEXT_STEP,  # QA approved, ready to advance
            'RETURN_TO_SUPPLIER': PartsStatus.CANCELLED,
        }

        new_status = status_mapping.get(self.disposition_type)

        if new_status and self.part.part_status != new_status:
            self.part.part_status = new_status

            # Increment rework counter if rework or repair disposition
            if self.disposition_type in ['REWORK', 'REPAIR']:
                self.part.total_rework_count += 1

            self.part.save(update_fields=['part_status', 'total_rework_count'])

    def has_pending_annotations(self):
        """
        Check if any linked quality reports require 3D annotations but don't have any.
        Returns tuple: (has_pending: bool, pending_reports: list of report IDs)
        """
        pending_reports = []

        for report in self.quality_reports.all():
            # Check if any error type on this report requires 3D annotation
            requires_annotation = report.errors.filter(requires_3d_annotation=True).exists()

            if requires_annotation:
                # Check if the report has any annotations
                has_annotations = report.annotations.exists()
                if not has_annotations:
                    pending_reports.append(report.id)

        return (len(pending_reports) > 0, pending_reports)

    def can_be_completed(self):
        """Check if disposition is ready to be marked as completed"""
        if not self.disposition_type:  # Must have a disposition decision
            return False
        if self.current_state not in ['OPEN', 'IN_PROGRESS']:  # Must be active
            return False
        if self.resolution_completed:  # Not already completed
            return False

        # Check for pending 3D annotations
        has_pending, _ = self.has_pending_annotations()
        if has_pending:
            return False

        return True

    def get_completion_blockers(self):
        """Get list of reasons why disposition cannot be completed"""
        blockers = []

        if not self.disposition_type:
            blockers.append("No disposition decision selected")
        if self.current_state not in ['OPEN', 'IN_PROGRESS']:
            blockers.append(f"Disposition is {self.get_current_state_display()}, not active")
        if self.resolution_completed:
            blockers.append("Resolution already completed")

        has_pending, pending_reports = self.has_pending_annotations()
        if has_pending:
            blockers.append(f"3D annotations required for {len(pending_reports)} quality report(s)")

        return blockers

    def get_step_rework_count(self):
        """Get number of rework attempts at this step for this part"""
        if not self.part or not self.step:
            return 0

        return QuarantineDisposition.objects.filter(part=self.part, step=self.step, disposition_type='REWORK',
            current_state='CLOSED').count()

    def check_rework_limit_exceeded(self, max_attempts=2):
        """Check if rework limit exceeded at this step (default 2 attempts)"""
        if not self.step or self.disposition_type != 'REWORK':
            return False

        current_count = self.get_step_rework_count()
        return current_count >= max_attempts

    def calculate_rework_attempt_number(self):
        """Calculate which rework attempt this is at the current step"""
        if not self.part or not self.step:
            return 1

        existing_rework_count = QuarantineDisposition.objects.filter(part=self.part, step=self.step,
            disposition_type='REWORK').count()

        return existing_rework_count + 1


# ============================================================================
# 3D MODELS AND HEATMAP ANNOTATIONS
# ============================================================================

class CapaType(models.TextChoices):
    CORRECTIVE = 'CORRECTIVE', 'Corrective Action'
    PREVENTIVE = 'PREVENTIVE', 'Preventive Action'
    CUSTOMER_COMPLAINT = 'CUSTOMER_COMPLAINT', 'Customer Complaint'
    INTERNAL_AUDIT = 'INTERNAL_AUDIT', 'Internal Audit'
    SUPPLIER = 'SUPPLIER', 'Supplier Issue'


class CapaSeverity(models.TextChoices):
    CRITICAL = 'CRITICAL', 'Critical'
    MAJOR = 'MAJOR', 'Major'
    MINOR = 'MINOR', 'Minor'


class CapaStatus(models.TextChoices):
    OPEN = 'OPEN', 'Open'
    IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
    PENDING_VERIFICATION = 'PENDING_VERIFICATION', 'Pending Verification'
    CLOSED = 'CLOSED', 'Closed'
    CANCELLED = 'CANCELLED', 'Cancelled'


class CAPA(SecureModel):
    """
    Corrective and Preventive Action tracking model.

    Manages the full CAPA lifecycle from problem identification through
    root cause analysis, corrective actions, verification, and closure.
    """

    capa_number = models.CharField(max_length=30, help_text="Auto-generated: CAPA-{type}-{year}-{seq}")
    capa_type = models.CharField(max_length=30, choices=CapaType.choices)
    severity = models.CharField(max_length=20, choices=CapaSeverity.choices)
    status = models.CharField(max_length=30, choices=CapaStatus.choices, default=CapaStatus.OPEN)

    # Problem description
    problem_statement = models.TextField(help_text="Clear description of the problem")
    immediate_action = models.TextField(null=True, blank=True, help_text="Containment action taken immediately")

    # Assignment and dates
    initiated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='capas_initiated')
    initiated_date = models.DateField(auto_now_add=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='capas_assigned')
    due_date = models.DateField(null=True, blank=True, help_text="User-set due date")
    completed_date = models.DateField(null=True, blank=True)

    # Verification
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='capas_verified')

    # Approval workflow fields (for Critical/Major CAPAs)
    approval_required = models.BooleanField(
        default=False,
        help_text="Whether this CAPA requires management approval (auto-set for Critical/Major)"
    )
    approval_status = models.CharField(
        max_length=20,
        choices=[
            ('NOT_REQUIRED', 'Not Required'),
            ('PENDING', 'Pending'),
            ('APPROVED', 'Approved'),
            ('REJECTED', 'Rejected'),
        ],
        default='NOT_REQUIRED',
        help_text="Approval workflow status"
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='capas_approved'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    allow_self_verification = models.BooleanField(default=False, help_text="Allow initiator/assignee to verify their own CAPA (requires justification)")

    # Context links
    part = models.ForeignKey('Parts', on_delete=models.SET_NULL, null=True, blank=True, help_text="Representative part if applicable")
    step = models.ForeignKey('Steps', on_delete=models.SET_NULL, null=True, blank=True, help_text="Process step where issue occurred")
    work_order = models.ForeignKey('WorkOrder', on_delete=models.SET_NULL, null=True, blank=True)

    # Links to triggering issues
    quality_reports = models.ManyToManyField('QualityReports', blank=True, related_name='capas')
    dispositions = models.ManyToManyField('QuarantineDisposition', blank=True, related_name='capas')

    # Documents
    documents = GenericRelation('Documents')

    class Meta:
        ordering = ['-initiated_date']
        verbose_name = 'CAPA'
        verbose_name_plural = 'CAPAs'
        indexes = [
            models.Index(fields=['capa_number']),
            models.Index(fields=['status', 'due_date']),
            models.Index(fields=['severity', 'status']),
        ]
        permissions = [
            ("initiate_capa", "Can initiate new CAPAs"),
            ("close_capa", "Can close CAPAs"),
            ("approve_capa", "Can approve CAPAs"),
            ("verify_capa", "Can verify CAPA effectiveness"),
        ]
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'capa_number'], name='capa_tenant_number_uniq'),
        ]

    def __str__(self):
        return f"{self.capa_number} - {self.get_severity_display()} - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        """Auto-generate CAPA number on creation"""
        if not self.capa_number:
            from django.utils import timezone
            # Use initiated_date if it exists, otherwise use today
            initiated_date = self.initiated_date if hasattr(self, 'initiated_date') and self.initiated_date else timezone.now().date()
            self.capa_number = self.generate_capa_number(self.capa_type, initiated_date, self.tenant)

        super().save(*args, **kwargs)

    @classmethod
    def generate_capa_number(cls, capa_type, initiated_date, tenant=None):
        """Auto-generate CAPA number: CAPA-{type_code}-{year}-{sequence}

        Uses SELECT FOR UPDATE to prevent race conditions under concurrent load.

        Examples:
        - CAPA-CA-2025-001 (Corrective Action)
        - CAPA-PA-2025-002 (Preventive Action)
        - CAPA-CC-2025-003 (Customer Complaint)
        """
        from Tracker.utils.sequences import generate_next_sequence

        type_codes = {
            'CORRECTIVE': 'CA',
            'PREVENTIVE': 'PA',
            'CUSTOMER_COMPLAINT': 'CC',
            'INTERNAL_AUDIT': 'IA',
            'SUPPLIER': 'SU'
        }
        year = initiated_date.year
        type_code = type_codes.get(capa_type, 'XX')
        prefix = f"CAPA-{type_code}-{year}-"

        return generate_next_sequence(
            queryset=cls.objects,
            number_field='capa_number',
            prefix=prefix,
            padding=3,
            tenant=tenant
        )

    @classmethod
    def suggest_due_date(cls, severity, initiated_date):
        """Suggest default due date based on severity

        - CRITICAL: 30 business days
        - MAJOR: 60 business days
        - MINOR: 90 business days
        """
        from datetime import timedelta
        days_map = {'CRITICAL': 30, 'MAJOR': 60, 'MINOR': 90}
        days = days_map.get(severity, 90)
        # Simple calendar days for now, could add business day calculation
        return initiated_date + timedelta(days=days)

    def rca_complete(self):
        """Check if RCA analysis is complete"""
        if not hasattr(self, 'rca_records') or not self.rca_records.exists():
            return False
        return self.rca_records.first().root_cause_summary is not None

    def all_tasks_completed(self):
        """Check if all tasks are completed"""
        if not hasattr(self, 'tasks'):
            return True
        return not self.tasks.exclude(status='COMPLETED').exists()

    def has_confirmed_verification(self):
        """Check if there's a verification with CONFIRMED effectiveness"""
        if not hasattr(self, 'verifications'):
            return False
        return self.verifications.filter(effectiveness_result='CONFIRMED').exists()

    @property
    def computed_status(self):
        """Derive CAPA status from task/RCA/verification state.

        Status logic:
        - CLOSED: Has verified effectiveness confirmed
        - PENDING_VERIFICATION: All tasks complete + RCA done, awaiting verification
        - IN_PROGRESS: At least one task exists or RCA started
        - OPEN: No work started yet
        """
        # Check for closure first
        if self.has_confirmed_verification():
            return CapaStatus.CLOSED

        # Check if ready for verification
        if self.all_tasks_completed() and self.rca_complete():
            # Has tasks and they're all done, plus RCA is complete
            if hasattr(self, 'tasks') and self.tasks.exists():
                return CapaStatus.PENDING_VERIFICATION

        # Check if work has started
        has_tasks = hasattr(self, 'tasks') and self.tasks.exists()
        has_rca = hasattr(self, 'rca_records') and self.rca_records.exists()
        if has_tasks or has_rca:
            return CapaStatus.IN_PROGRESS

        return CapaStatus.OPEN

    def calculate_completion_percentage(self):
        """Calculate overall CAPA completion progress

        Weighted by stage:
        - RCA completed: 25%
        - All tasks completed: 50%
        - Verification completed: 25%
        """
        progress = 0
        if self.rca_complete():
            progress += 25

        if hasattr(self, 'tasks') and self.tasks.exists():
            completed = self.tasks.filter(status='COMPLETED').count()
            total = self.tasks.count()
            progress += int((completed / total) * 50)

        if hasattr(self, 'verification') and self.verification:
            if self.verification.effectiveness_result == 'CONFIRMED':
                progress += 25

        return progress

    def get_blocking_items(self):
        """Identify what's preventing CAPA closure

        Returns: List of blocker strings
        """
        blockers = []

        if not self.rca_complete():
            blockers.append("RCA not completed")

        if hasattr(self, 'tasks'):
            incomplete_tasks = self.tasks.exclude(status='COMPLETED')
            if incomplete_tasks.exists():
                blockers.append(f"{incomplete_tasks.count()} task(s) still pending")

        if not hasattr(self, 'verifications') or not self.verifications.exists():
            blockers.append("Verification not performed")
        elif not self.verifications.filter(effectiveness_result='CONFIRMED').exists():
            blockers.append("Effectiveness not confirmed")

        return blockers

    def is_overdue(self):
        """Check if CAPA is overdue based on due_date

        Returns: bool - True if overdue, False otherwise
        """
        from django.utils import timezone

        # Closed CAPAs are never overdue
        if self.status == 'CLOSED':
            return False

        # No due date means not overdue
        if not self.due_date:
            return False

        # Check if due date has passed
        today = timezone.now().date()
        return today > self.due_date

    def request_approval(self, user):
        """
        Request management approval for CAPA (typically for Critical/Major severity).

        This method manually requests approval. For automatic approval triggering,
        see the post_save signal handler for CAPA in signals.py.

        Args:
            user: The user requesting approval

        Returns:
            ApprovalRequest: The created approval request

        Raises:
            ValueError: If approval already pending/approved or template not found
        """
        from .core import ApprovalRequest, ApprovalTemplate

        if self.approval_status == 'APPROVED':
            raise ValueError("CAPA is already approved")
        if self.approval_status == 'PENDING':
            raise ValueError("CAPA approval is already pending")

        # Get the CAPA_APPROVAL template (filtered by tenant)
        try:
            template = ApprovalTemplate.objects.get(
                approval_type='CAPA_APPROVAL',
                tenant=self.tenant
            )
        except ApprovalTemplate.DoesNotExist:
            raise ValueError("CAPA_APPROVAL template not found. Please configure approval templates.")

        # Create approval request from template
        approval_request = ApprovalRequest.create_from_template(
            content_object=self,
            template=template,
            requested_by=user,
            reason=f"CAPA Approval: {self.capa_number} - {self.get_severity_display()}"
        )

        # Update CAPA approval fields
        self.approval_required = True
        self.approval_status = 'PENDING'
        self.save(update_fields=['approval_required', 'approval_status'])

        return approval_request

    def transition_to(self, new_status, user, notes=None):
        """
        Transition CAPA to a new status with validation.

        Valid transitions:
        - OPEN -> IN_PROGRESS, CANCELLED
        - IN_PROGRESS -> PENDING_VERIFICATION, CANCELLED
        - PENDING_VERIFICATION -> CLOSED, IN_PROGRESS (reopen), CANCELLED
        - CLOSED -> (no transitions, terminal state)
        - CANCELLED -> (no transitions, terminal state)

        Args:
            new_status: Target status (CapaStatus value)
            user: User performing the transition
            notes: Optional notes/reason for the transition

        Raises:
            ValueError: If transition is not allowed or requirements not met
        """
        from django.utils import timezone

        # Define allowed transitions
        allowed_transitions = {
            'OPEN': ['IN_PROGRESS', 'CANCELLED'],
            'IN_PROGRESS': ['PENDING_VERIFICATION', 'CANCELLED'],
            'PENDING_VERIFICATION': ['CLOSED', 'IN_PROGRESS', 'CANCELLED'],
            'CLOSED': [],
            'CANCELLED': [],
        }

        current = self.status
        allowed = allowed_transitions.get(current, [])

        if new_status not in allowed:
            raise ValueError(
                f"Cannot transition from {current} to {new_status}. "
                f"Allowed transitions: {allowed}"
            )

        # Validate requirements for specific transitions
        if new_status == 'PENDING_VERIFICATION':
            if not self.rca_complete():
                raise ValueError("Cannot move to PENDING_VERIFICATION: RCA not completed")

        if new_status == 'CLOSED':
            blockers = self.get_blocking_items()
            if blockers:
                raise ValueError(
                    f"Cannot close CAPA: {', '.join(blockers)}"
                )

        # Perform the transition
        self.status = new_status

        # Set completed_date when closing
        if new_status == 'CLOSED':
            self.completed_date = timezone.now().date()

        self.save()

        # TODO: Could add audit log entry here with user and notes
        return self


class CapaTaskType(models.TextChoices):
    CONTAINMENT = 'CONTAINMENT', 'Containment'
    CORRECTIVE = 'CORRECTIVE', 'Corrective Action'
    PREVENTIVE = 'PREVENTIVE', 'Preventive Action'


class CapaTaskStatus(models.TextChoices):
    NOT_STARTED = 'NOT_STARTED', 'Not Started'
    IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
    COMPLETED = 'COMPLETED', 'Completed'
    CANCELLED = 'CANCELLED', 'Cancelled'


class CapaTaskCompletionMode(models.TextChoices):
    SINGLE_OWNER = 'SINGLE_OWNER', 'Single Owner'
    ANY_ASSIGNEE = 'ANY_ASSIGNEE', 'Any Assignee'
    ALL_ASSIGNEES = 'ALL_ASSIGNEES', 'All Assignees'


class CapaTasks(SecureModel):
    """Individual action items within a CAPA"""

    capa = models.ForeignKey(CAPA, on_delete=models.CASCADE, related_name='tasks')
    task_number = models.CharField(max_length=40, help_text="Auto-generated: {capa_number}-T{seq}")

    task_type = models.CharField(max_length=20, choices=CapaTaskType.choices)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=CapaTaskStatus.choices, default=CapaTaskStatus.NOT_STARTED)

    # Assignment
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='capa_tasks_assigned')
    completion_mode = models.CharField(max_length=20, choices=CapaTaskCompletionMode.choices, default=CapaTaskCompletionMode.SINGLE_OWNER)

    # Completion requirements
    due_date = models.DateField(null=True, blank=True)
    requires_signature = models.BooleanField(default=False, help_text="If true, task completion requires signature and password verification")

    # Completion tracking
    completed_date = models.DateField(null=True, blank=True)
    completed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='capa_tasks_completed')
    completion_notes = models.TextField(null=True, blank=True)
    completion_signature = models.TextField(null=True, blank=True, help_text="Base64-encoded signature image data")

    # Evidence/Documentation
    documents = GenericRelation('Tracker.Documents')
    """Supporting documents and completion evidence for this task (e.g., updated procedures, photos, test results)."""

    class Meta:
        ordering = ['capa', 'created_at']
        verbose_name = 'CAPA Task'
        verbose_name_plural = 'CAPA Tasks'
        indexes = [
            models.Index(fields=['capa', 'status']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'task_number'], name='capatask_tenant_number_uniq'),
        ]

    def __str__(self):
        return f"{self.task_number} - {self.description[:50]}"

    def save(self, *args, **kwargs):
        """Auto-generate task number if not set.

        Uses SELECT FOR UPDATE to prevent race conditions under concurrent load.
        """
        if not self.task_number:
            from Tracker.utils.sequences import generate_next_child_sequence

            # Generate task number: {capa_number}-T{seq}
            prefix = f"{self.capa.capa_number}-T"

            self.task_number = generate_next_child_sequence(
                queryset=CapaTasks.objects,
                number_field='task_number',
                prefix=prefix,
                separator='-T',
                padding=3,
                tenant=self.tenant if self.tenant_id else None
            )

        super().save(*args, **kwargs)

    def mark_completed(self, user, notes, signature_data=None, password=None):
        """Complete task with validation

        Behavior depends on completion_mode:
        - SINGLE_OWNER: Task completed directly
        - ANY_ASSIGNEE: Any one assignee can complete
        - ALL_ASSIGNEES: All assignees must complete

        If requires_signature is True, signature_data and password are required.
        """
        from django.utils import timezone

        # Validate signature requirement
        if self.requires_signature:
            if not signature_data:
                raise ValueError("Signature is required for this task")
            if not password:
                raise ValueError("Password is required for identity verification")
            # Verify password
            if not user.check_password(password):
                raise ValueError("Invalid password")

        if self.completion_mode == CapaTaskCompletionMode.SINGLE_OWNER:
            self.status = CapaTaskStatus.COMPLETED
            self.completed_date = timezone.now().date()
            self.completed_by = user
            self.completion_notes = notes
            if self.requires_signature:
                self.completion_signature = signature_data
            self.save()
        else:
            # Multi-assignee modes use CapaTaskAssignee rows
            assignee, _ = CapaTaskAssignee.objects.get_or_create(task=self, user=user)
            assignee.status = CapaTaskStatus.COMPLETED
            assignee.completed_at = timezone.now()
            assignee.completion_notes = notes
            assignee.save()

            # Re-evaluate task completion
            assignees = self.assignees.all()

            if self.completion_mode == CapaTaskCompletionMode.ANY_ASSIGNEE:
                if assignees.filter(status=CapaTaskStatus.COMPLETED).exists():
                    self.status = CapaTaskStatus.COMPLETED
                    self.completed_date = timezone.now().date()
                    self.completed_by = user
                    if self.requires_signature:
                        self.completion_signature = signature_data
            elif self.completion_mode == CapaTaskCompletionMode.ALL_ASSIGNEES:
                total = assignees.count()
                completed = assignees.filter(status=CapaTaskStatus.COMPLETED).count()
                if total > 0 and completed == total:
                    self.status = CapaTaskStatus.COMPLETED
                    self.completed_date = timezone.now().date()
                    self.completed_by = user
                    if self.requires_signature:
                        self.completion_signature = signature_data

            if self.status == CapaTaskStatus.COMPLETED:
                self.save()

        # Check if CAPA can move to next stage
        if self.capa.all_tasks_completed() and self.capa.rca_complete():
            # Trigger notification
            pass

    def check_overdue(self):
        """Determine if task is overdue

        Returns: (is_overdue: bool, days_overdue: int)
        """
        from django.utils import timezone

        if self.status == CapaTaskStatus.COMPLETED or self.due_date is None:
            return (False, 0)

        today = timezone.now().date()
        if today > self.due_date:
            return (True, (today - self.due_date).days)

        return (False, 0)


class CapaTaskAssignee(SecureModel):
    """Multi-person task assignment tracking"""

    task = models.ForeignKey(CapaTasks, on_delete=models.CASCADE, related_name='assignees')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='capa_task_assignments')

    status = models.CharField(max_length=20, choices=CapaTaskStatus.choices, default=CapaTaskStatus.NOT_STARTED)
    completed_at = models.DateTimeField(null=True, blank=True)
    completion_notes = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = [['task', 'user']]
        verbose_name = 'CAPA Task Assignee'
        verbose_name_plural = 'CAPA Task Assignees'

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.task.task_number}"


class RcaMethod(models.TextChoices):
    FIVE_WHYS = 'FIVE_WHYS', '5 Whys'
    FISHBONE = 'FISHBONE', 'Fishbone Diagram'
    FAULT_TREE = 'FAULT_TREE', 'Fault Tree'
    PARETO = 'PARETO', 'Pareto Analysis'


class RcaReviewStatus(models.TextChoices):
    NOT_REQUIRED = 'NOT_REQUIRED', 'Not Required'
    REQUIRED = 'REQUIRED', 'Required'
    COMPLETED = 'COMPLETED', 'Completed'


class RootCauseVerificationStatus(models.TextChoices):
    UNVERIFIED = 'UNVERIFIED', 'Unverified'
    VERIFIED = 'VERIFIED', 'Verified'
    DISPUTED = 'DISPUTED', 'Disputed'


class RcaRecord(SecureModel):
    """Root Cause Analysis record for CAPA"""

    capa = models.ForeignKey(CAPA, on_delete=models.CASCADE, related_name='rca_records')
    rca_method = models.CharField(max_length=20, choices=RcaMethod.choices)

    problem_description = models.TextField()
    root_cause_summary = models.TextField(null=True, blank=True)

    # Review and verification
    rca_review_status = models.CharField(max_length=20, choices=RcaReviewStatus.choices, default=RcaReviewStatus.NOT_REQUIRED)
    root_cause_verification_status = models.CharField(max_length=20, choices=RootCauseVerificationStatus.choices, default=RootCauseVerificationStatus.UNVERIFIED)
    root_cause_verified_at = models.DateTimeField(null=True, blank=True)
    root_cause_verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='rca_verifications')
    self_verified = models.BooleanField(default=False, help_text="True if conductor verified their own RCA")

    # Conductor
    conducted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='rca_conducted')
    conducted_date = models.DateField(null=True, blank=True)

    # Links to triggering issues
    quality_reports = models.ManyToManyField('QualityReports', blank=True, related_name='rca_records')
    dispositions = models.ManyToManyField('QuarantineDisposition', blank=True, related_name='rca_records')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'RCA Record'
        verbose_name_plural = 'RCA Records'
        permissions = [
            ("conduct_rca", "Can conduct root cause analysis"),
            ("review_rca", "Can review RCA findings"),
        ]

    def __str__(self):
        return f"RCA for {self.capa.capa_number} - {self.get_rca_method_display()}"

    def validate_completeness(self):
        """Check if RCA is complete enough to proceed

        Returns: (is_complete: bool, issues: list)
        """
        issues = []

        if not self.problem_description:
            issues.append("Problem description is required")

        if not self.root_cause_summary:
            issues.append("Root cause summary is required")

        if not self.conducted_by or not self.conducted_date:
            issues.append("Conductor and date are required")

        if self.rca_method == RcaMethod.FIVE_WHYS:
            if hasattr(self, 'five_whys'):
                whys_answered = sum([
                    bool(self.five_whys.why_1_answer),
                    bool(self.five_whys.why_2_answer),
                    bool(self.five_whys.why_3_answer),
                ])
                if whys_answered < 3:
                    issues.append("At least 3 'why' levels must be answered")

        if self.rca_method == RcaMethod.FISHBONE:
            if hasattr(self, 'fishbone'):
                categories_filled = sum([
                    bool(self.fishbone.man_causes),
                    bool(self.fishbone.machine_causes),
                    bool(self.fishbone.material_causes),
                    bool(self.fishbone.method_causes),
                    bool(self.fishbone.measurement_causes),
                    bool(self.fishbone.environment_causes),
                ])
                if categories_filled < 3:
                    issues.append("At least 3 fishbone categories must have causes")

        return (len(issues) == 0, issues)

    def verify_root_cause(self, user, verification_notes=None):
        """Verify the root cause analysis"""
        from django.utils import timezone
        from django.core.exceptions import ValidationError

        # Self-verification check
        is_self_verification = (user == self.conducted_by)
        if is_self_verification:
            if not self.capa.allow_self_verification:
                raise ValidationError("Self-verification of RCA is not permitted for this CAPA")
            if not verification_notes or len(verification_notes.strip()) < 10:
                raise ValidationError("Justification required for RCA self-verification (minimum 10 characters)")

        self.root_cause_verification_status = RootCauseVerificationStatus.VERIFIED
        self.root_cause_verified_by = user
        self.root_cause_verified_at = timezone.now()
        self.self_verified = is_self_verification
        self.save()


class FiveWhys(SecureModel):
    """5 Whys analysis structure"""

    rca_record = models.OneToOneField(RcaRecord, on_delete=models.CASCADE, related_name='five_whys')

    why_1_question = models.TextField(null=True, blank=True)
    why_1_answer = models.TextField(null=True, blank=True)
    why_2_question = models.TextField(null=True, blank=True)
    why_2_answer = models.TextField(null=True, blank=True)
    why_3_question = models.TextField(null=True, blank=True)
    why_3_answer = models.TextField(null=True, blank=True)
    why_4_question = models.TextField(null=True, blank=True)
    why_4_answer = models.TextField(null=True, blank=True)
    why_5_question = models.TextField(null=True, blank=True)
    why_5_answer = models.TextField(null=True, blank=True)

    identified_root_cause = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = '5 Whys Analysis'
        verbose_name_plural = '5 Whys Analyses'

    def __str__(self):
        return f"5 Whys for {self.rca_record.capa.capa_number}"


class Fishbone(SecureModel):
    """Fishbone (Ishikawa) diagram structure"""

    rca_record = models.OneToOneField(RcaRecord, on_delete=models.CASCADE, related_name='fishbone')

    problem_statement = models.TextField()

    # 6M categories (stored as JSON arrays)
    man_causes = models.JSONField(default=list, blank=True, help_text="Array of cause strings")
    machine_causes = models.JSONField(default=list, blank=True)
    material_causes = models.JSONField(default=list, blank=True)
    method_causes = models.JSONField(default=list, blank=True)
    measurement_causes = models.JSONField(default=list, blank=True)
    environment_causes = models.JSONField(default=list, blank=True)

    identified_root_cause = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = 'Fishbone Diagram'
        verbose_name_plural = 'Fishbone Diagrams'

    def __str__(self):
        return f"Fishbone for {self.rca_record.capa.capa_number}"


class RootCauseCategory(models.TextChoices):
    MAN = 'MAN', 'Man (People)'
    MACHINE = 'MACHINE', 'Machine (Equipment)'
    MATERIAL = 'MATERIAL', 'Material'
    METHOD = 'METHOD', 'Method (Process)'
    MEASUREMENT = 'MEASUREMENT', 'Measurement'
    ENVIRONMENT = 'ENVIRONMENT', 'Environment'
    OTHER = 'OTHER', 'Other'


class RootCauseRole(models.TextChoices):
    PRIMARY = 'PRIMARY', 'Primary'
    CONTRIBUTING = 'CONTRIBUTING', 'Contributing'


class RootCause(SecureModel):
    """Individual root cause identification"""

    rca_record = models.ForeignKey(RcaRecord, on_delete=models.CASCADE, related_name='root_causes')
    description = models.TextField()
    category = models.CharField(max_length=20, choices=RootCauseCategory.choices)
    role = models.CharField(max_length=20, choices=RootCauseRole.choices, default=RootCauseRole.PRIMARY)
    sequence = models.IntegerField(default=1, help_text="Order in causal chain")

    class Meta:
        ordering = ['rca_record', 'sequence']
        verbose_name = 'Root Cause'
        verbose_name_plural = 'Root Causes'

    def __str__(self):
        return f"{self.get_category_display()} - {self.description[:50]}"


class EffectivenessResult(models.TextChoices):
    CONFIRMED = 'CONFIRMED', 'Confirmed Effective'
    NOT_EFFECTIVE = 'NOT_EFFECTIVE', 'Not Effective'
    INCONCLUSIVE = 'INCONCLUSIVE', 'Inconclusive'


class CapaVerification(SecureModel):
    """Verification of CAPA effectiveness"""

    capa = models.ForeignKey(CAPA, on_delete=models.CASCADE, related_name='verifications')

    verification_method = models.TextField(help_text="How effectiveness was verified")
    verification_criteria = models.TextField(help_text="What defines success")
    verification_date = models.DateField(null=True, blank=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='capa_verifications_performed')

    effectiveness_result = models.CharField(max_length=20, choices=EffectivenessResult.choices, default=EffectivenessResult.INCONCLUSIVE)
    effectiveness_decided_at = models.DateTimeField(null=True, blank=True)
    verification_notes = models.TextField(null=True, blank=True)
    self_verified = models.BooleanField(default=False, help_text="True if initiator/assignee verified their own CAPA")

    class Meta:
        verbose_name = 'CAPA Verification'
        verbose_name_plural = 'CAPA Verifications'

    def __str__(self):
        return f"Verification for {self.capa.capa_number} - {self.get_effectiveness_result_display()}"

    def verify_effectiveness(self, user, confirmed, notes):
        """Complete verification process"""
        from django.utils import timezone
        from django.core.exceptions import ValidationError

        # Self-verification check
        is_self_verification = (user == self.capa.initiated_by or user == self.capa.assigned_to)
        if is_self_verification:
            if not self.capa.allow_self_verification:
                raise ValidationError("Self-verification is not permitted for this CAPA")
            if not notes or len(notes.strip()) < 10:
                raise ValidationError("Justification required for self-verification (minimum 10 characters)")

        self.verified_by = user
        self.verification_date = timezone.now().date()
        self.effectiveness_result = EffectivenessResult.CONFIRMED if confirmed else EffectivenessResult.NOT_EFFECTIVE
        self.effectiveness_decided_at = timezone.now()
        self.verification_notes = notes
        self.self_verified = is_self_verification
        self.save()

        if self.effectiveness_result == EffectivenessResult.CONFIRMED:
            # Close the CAPA when effectiveness is confirmed
            self.capa.status = CapaStatus.CLOSED
            self.capa.completed_date = timezone.now().date()
            self.capa.save(update_fields=['status', 'completed_date'])
        else:
            # Mark RCA for review and move CAPA back to IN_PROGRESS
            rca = self.capa.rca_records.first()
            if rca:
                rca.rca_review_status = RcaReviewStatus.REQUIRED
                rca.save()

            self.capa.status = CapaStatus.IN_PROGRESS
            self.capa.save()

            # Create follow-up task (task_number auto-generated by CapaTasks.save())
            CapaTasks.objects.create(
                capa=self.capa,
                tenant=self.capa.tenant,  # Ensure tenant is set for proper sequence generation
                task_type=CapaTaskType.CORRECTIVE,
                description=f"Review and update RCA due to failed verification: {notes}",
                assigned_to=self.capa.assigned_to,
                due_date=timezone.now().date() + timezone.timedelta(days=30)
            )



# ===== 3D MODEL AND VISUALIZATION =====


def threed_model_upload_path(self, filename):
    """
    Constructs a secure, tenant-isolated upload path for 3D model files.

    The final path structure is:
        models/{tenant_slug}/{YYYY-MM-DD}/{uuid}_{filename}

    - tenant_slug: isolates files per tenant (uses 'default' if tenant not set)
    - date: enables time-based organization and backups
    - uuid prefix: prevents path enumeration and filename collisions

    Args:
        filename (str): The original name of the uploaded file.

    Returns:
        str: A structured path to store the uploaded file.
    """
    import os
    import uuid
    from datetime import date

    tenant_slug = self.tenant.slug if self.tenant else 'default'
    today = date.today().isoformat()
    unique_id = uuid.uuid4().hex[:12]

    return os.path.join("models", tenant_slug, today, f"{unique_id}_{filename}")


class ModelProcessingStatus(models.TextChoices):
    """Processing status for 3D model conversion and optimization."""
    PENDING = 'pending', 'Pending'
    PROCESSING = 'processing', 'Processing'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'


class ThreeDModel(SecureModel):
    """
    3D model files for quality inspection and heatmap visualization.

    This model represents 3D model files (in formats like GLB, GLTF, OBJ) that are used
    for interactive visualization and annotation in quality inspection heatmap viewers.
    Each model can be linked to a specific part type and optionally to a process step.

    These models serve as reference geometry for quality inspectors to annotate defects
    and measurements spatially during inspection processes.

    Supported upload formats:
        - CAD: STEP (.step, .stp) - converted to GLB via cascadio
        - Mesh: STL, OBJ, PLY - optimized and converted to GLB
        - glTF: GLB, glTF - optimized if needed

    All uploads are processed asynchronously:
        1. File uploaded with processing_status='pending'
        2. Celery task converts/optimizes to GLB
        3. Status updated to 'completed' or 'failed'
    """

    documents = GenericRelation('Tracker.Documents')
    """Related documents (2D drawings, revision notes, source CAD files, etc.)"""

    name = models.CharField(max_length=255)
    file = models.FileField(upload_to=threed_model_upload_path)
    part_type = models.ForeignKey('Tracker.PartTypes', on_delete=models.CASCADE, related_name='three_d_models')
    step = models.ForeignKey('Tracker.Steps', on_delete=models.CASCADE, related_name='three_d_models', null=True, blank=True,
                             help_text="Optional: Link to specific step if this shows intermediate state")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_type = models.CharField(max_length=50, blank=True, help_text="Output format after processing (always 'glb')")

    # Processing status tracking
    processing_status = models.CharField(
        max_length=20,
        choices=ModelProcessingStatus.choices,
        default=ModelProcessingStatus.PENDING,
        help_text="Current processing state"
    )
    processing_error = models.TextField(
        blank=True,
        help_text="Error message if processing failed"
    )
    processed_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When processing completed"
    )

    # Original file info (before conversion)
    original_filename = models.CharField(
        max_length=255, blank=True,
        help_text="Original uploaded filename"
    )
    original_format = models.CharField(
        max_length=20, blank=True,
        help_text="Original file format (e.g., 'step', 'stl', 'obj')"
    )
    original_size_bytes = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Original file size in bytes"
    )

    # Processing metrics (after optimization)
    face_count = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Number of triangles in processed mesh"
    )
    vertex_count = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Number of vertices in processed mesh"
    )
    final_size_bytes = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Final GLB file size in bytes"
    )

    class Meta:
        verbose_name = '3D Model'
        verbose_name_plural = '3D Models'

    def __str__(self):
        return f"{self.name} ({self.file_type or self.original_format or 'unknown'})"

    @property
    def is_ready(self) -> bool:
        """True if model is processed and ready for viewing."""
        return self.processing_status == ModelProcessingStatus.COMPLETED

    @property
    def compression_ratio(self) -> float | None:
        """Calculate size reduction from original to final."""
        if self.original_size_bytes and self.final_size_bytes:
            return round(1 - (self.final_size_bytes / self.original_size_bytes), 3)
        return None


class HeatMapAnnotations(SecureModel):
    """
    User-placed annotations on 3D models for heatmap visualization during quality inspection.

    This model represents annotations that quality inspectors place on 3D models to mark defects,
    measurements, or areas of interest. Annotations can be linked to quality reports
    to provide visual evidence and context for quality findings.

    This is quality inspection data captured spatially on reference 3D models.

    Fields:
        model (ForeignKey): Reference to the ThreeDModel being annotated
        part (ForeignKey): Reference to the Part being inspected
        quality_reports (ManyToManyField): Links to QualityReports that reference this annotation
        position_x, position_y, position_z (float): 3D coordinates of the annotation
        measurement_value (float): Optional measured value at this location
        defect_type (str): Type/classification of defect (if applicable)
        severity (str): Severity level: 'low', 'medium', 'high', 'critical'
        notes (str): Additional notes about the annotation
        created_by (ForeignKey): User who created the annotation

    Inherited from SecureModel:
        created_at, updated_at, archived, deleted_at, tenant, version, etc.
    """
    model = models.ForeignKey(ThreeDModel, on_delete=models.CASCADE, related_name='annotations')
    part = models.ForeignKey('Tracker.Parts', on_delete=models.CASCADE, related_name='heatmap_annotations')

    quality_reports = models.ManyToManyField('Tracker.QualityReports', blank=True, related_name='annotations')

    position_x = models.FloatField()
    position_y = models.FloatField()
    position_z = models.FloatField()

    measurement_value = models.FloatField(null=True, blank=True)
    defect_type = models.CharField(max_length=255, null=True, blank=True)
    severity = models.CharField(
        max_length=50,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical')
        ],
        null=True,
        blank=True
    )

    notes = models.TextField(blank=True)
    created_by = models.ForeignKey('Tracker.User', on_delete=models.SET_NULL, null=True, related_name='heatmap_annotations')
    # Note: created_at and updated_at inherited from SecureModel

    class Meta:
        verbose_name = 'Heatmap Annotation'
        verbose_name_plural = 'Heatmap Annotations'
        indexes = [
            models.Index(fields=['model', 'part']),
            # created_at index inherited from SecureModel via ['tenant', 'created_at']
        ]

    def __str__(self):
        return f"Annotation on {self.model.name} for {self.part} at ({self.position_x}, {self.position_y}, {self.position_z})"


# ===== GENERATED REPORTS (PDF AUDIT TRAIL) =====

class GeneratedReport(SecureModel):
    """
    Audit trail for PDF reports generated by the system.

    Tracks all reports generated via the PDF generation service (Playwright),
    providing compliance traceability for who requested what report and when.
    This supports QMS audit requirements for document control.

    The actual PDF file is stored as a Document (part of DMS), referenced by
    the 'document' field. This ensures generated reports benefit from the
    document management system's versioning, access control, and audit features.

    Fields:
        report_type: Type of report (spc, capa, quality_report, etc.)
        generated_by: User who requested the report
        generated_at: When the report was generated
        parameters: JSON of parameters used to generate the report (for reproducibility)
        document: Reference to the Document containing the PDF file
        emailed_to: Email address the report was sent to
        status: Generation status (pending, completed, failed)
        error_message: Error details if generation failed
    """

    class ReportStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'

    report_type = models.CharField(
        max_length=50,
        help_text="Type of report: spc, capa, quality_report, etc."
    )
    generated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='generated_reports'
    )
    generated_at = models.DateTimeField(auto_now_add=True)
    parameters = models.JSONField(
        default=dict,
        help_text="Parameters used to generate the report (for reproducibility)"
    )

    # Document reference (PDF stored in DMS)
    document = models.ForeignKey(
        'Tracker.Documents',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_reports',
        help_text="The Document containing the generated PDF file"
    )

    # Delivery tracking
    emailed_to = models.EmailField(
        null=True,
        blank=True,
        help_text="Email address the report was sent to"
    )
    emailed_at = models.DateTimeField(null=True, blank=True)

    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=ReportStatus.choices,
        default=ReportStatus.PENDING
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text="Error details if generation failed"
    )

    class Meta:
        ordering = ['-generated_at']
        verbose_name = 'Generated Report'
        verbose_name_plural = 'Generated Reports'
        indexes = [
            models.Index(fields=['report_type', 'generated_at']),
            models.Index(fields=['generated_by', 'generated_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        user_name = self.generated_by.get_full_name() if self.generated_by else "Unknown"
        return f"{self.report_type} report by {user_name} at {self.generated_at}"

    def mark_completed(self, document):
        """Mark report as successfully generated with associated document"""
        self.document = document
        self.status = self.ReportStatus.COMPLETED
        self.save(update_fields=['document', 'status'])

    def mark_failed(self, error_message: str):
        """Mark report generation as failed"""
        self.status = self.ReportStatus.FAILED
        self.error_message = error_message
        self.save(update_fields=['status', 'error_message'])

    def mark_emailed(self, email_address: str):
        """Record that the report was emailed"""
        from django.utils import timezone
        self.emailed_to = email_address
        self.emailed_at = timezone.now()
        self.save(update_fields=['emailed_to', 'emailed_at'])


# ===== TRAINING & CALIBRATION =====

class TrainingType(SecureModel):
    """
    Defines a type of training or qualification that personnel can hold.

    Examples: 'Blueprint Reading', 'CMM Operation', 'Soldering IPC-A-610'
    """

    documents = GenericRelation('Tracker.Documents')
    """Linked training materials, SOPs, or work instructions."""

    name = models.CharField(max_length=100)
    """Name of the training/qualification."""

    description = models.TextField(blank=True)
    """Description of what this training covers."""

    validity_period_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Default number of days training is valid. Null = never expires."
    )

    class Meta:
        verbose_name = 'Training Type'
        verbose_name_plural = 'Training Types'
        ordering = ['name']

    def __str__(self):
        return self.name


class TrainingRecord(SecureModel):
    """
    Records that a user has completed a specific training.

    Tracks completion date, expiration, trainer, and evidence documentation.
    """

    documents = GenericRelation('Tracker.Documents')
    """Evidence documents - signed training records, certificates, etc."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='training_records'
    )
    """The person who received the training."""

    training_type = models.ForeignKey(
        TrainingType,
        on_delete=models.PROTECT,
        related_name='records'
    )
    """The type of training completed."""

    completed_date = models.DateField()
    """Date training was completed."""

    expires_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date training expires. Null = never expires."
    )
    """When this training expires. Calculated from TrainingType.validity_period_days if not set."""

    trainer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='trainings_given',
        help_text="Person who conducted the training"
    )

    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Training Record'
        verbose_name_plural = 'Training Records'
        ordering = ['-completed_date']

    def __str__(self):
        return f"{self.user} - {self.training_type} ({self.completed_date})"

    def save(self, *args, **kwargs):
        # Auto-calculate expiration if not set and training type has validity period
        if not self.expires_date and self.training_type.validity_period_days:
            from datetime import timedelta
            self.expires_date = self.completed_date + timedelta(days=self.training_type.validity_period_days)
        super().save(*args, **kwargs)

    @property
    def is_current(self):
        """Returns True if training has not expired."""
        if not self.expires_date:
            return True
        return self.expires_date >= timezone.now().date()

    @property
    def status(self):
        """Returns 'current', 'expiring_soon', or 'expired'."""
        if not self.expires_date:
            return 'current'
        today = timezone.now().date()
        if self.expires_date < today:
            return 'expired'
        from datetime import timedelta
        if self.expires_date <= today + timedelta(days=30):
            return 'expiring_soon'
        return 'current'


class TrainingRequirement(SecureModel):
    """
    Links a TrainingType to work activities (Step, Process, or EquipmentType).

    Exactly one of step/process/equipment_type must be set.
    If no requirements are defined for a Step/Process, no training checks apply.

    Usage:
        # Get all requirements for a step
        step.training_requirements.all()

        # Get all requirements across the system
        TrainingRequirement.objects.filter(tenant=tenant)

        # Check what training a user needs for a step
        required = set(r.training_type for r in step.training_requirements.all())
    """

    training_type = models.ForeignKey(
        TrainingType,
        on_delete=models.CASCADE,
        related_name='requirements'
    )

    # Target - exactly one should be set
    step = models.ForeignKey(
        'Tracker.Steps',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='training_requirements'
    )
    process = models.ForeignKey(
        'Tracker.Processes',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='training_requirements'
    )
    equipment_type = models.ForeignKey(
        'Tracker.EquipmentType',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='training_requirements'
    )

    notes = models.TextField(
        blank=True,
        help_text="Why is this required? e.g., 'Per WI-042' or 'Customer requirement'"
    )

    class Meta:
        verbose_name = 'Training Requirement'
        verbose_name_plural = 'Training Requirements'
        constraints = [
            # Prevent duplicate training requirements for same target
            models.UniqueConstraint(
                fields=['training_type', 'step'],
                condition=models.Q(step__isnull=False),
                name='unique_training_per_step'
            ),
            models.UniqueConstraint(
                fields=['training_type', 'process'],
                condition=models.Q(process__isnull=False),
                name='unique_training_per_process'
            ),
            models.UniqueConstraint(
                fields=['training_type', 'equipment_type'],
                condition=models.Q(equipment_type__isnull=False),
                name='unique_training_per_equipment_type'
            ),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        targets = [self.step, self.process, self.equipment_type]
        count = sum(1 for t in targets if t is not None)
        if count != 1:
            raise ValidationError(
                "Exactly one of step, process, or equipment_type must be set."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def target(self):
        """Returns the Step, Process, or EquipmentType this requirement applies to."""
        return self.step or self.process or self.equipment_type

    @property
    def scope(self):
        """Returns 'step', 'process', or 'equipment_type'."""
        if self.step:
            return 'step'
        if self.process:
            return 'process'
        return 'equipment_type'

    def __str__(self):
        return f"{self.training_type} → {self.target}"


class CalibrationRecordQuerySet(models.QuerySet):
    """Custom queryset for CalibrationRecord."""

    def due_soon(self, within_days=30):
        """Calibration records with due date within N days."""
        from datetime import timedelta
        cutoff = timezone.now().date() + timedelta(days=within_days)
        today = timezone.now().date()
        return self.filter(due_date__lte=cutoff, due_date__gte=today)

    def overdue(self):
        """Calibration records past due date."""
        return self.filter(due_date__lt=timezone.now().date())

    def current(self):
        """Calibration records that are current (not overdue, not failed)."""
        return self.filter(
            due_date__gte=timezone.now().date()
        ).exclude(result='fail')

    def for_equipment(self, equipment):
        """Calibration records for a specific piece of equipment."""
        return self.filter(equipment=equipment)

    def latest_per_equipment(self):
        """Return only the most recent calibration record per equipment."""
        from django.db.models import OuterRef, Subquery
        latest_ids = self.filter(
            equipment=OuterRef('equipment')
        ).order_by('-calibration_date').values('id')[:1]
        return self.filter(id__in=Subquery(latest_ids))


class CalibrationRecordManager(models.Manager):
    """Manager using CalibrationRecordQuerySet."""

    def get_queryset(self):
        return CalibrationRecordQuerySet(self.model, using=self._db)

    def due_soon(self, within_days=30):
        return self.get_queryset().due_soon(within_days)

    def overdue(self):
        return self.get_queryset().overdue()

    def current(self):
        return self.get_queryset().current()

    def for_equipment(self, equipment):
        return self.get_queryset().for_equipment(equipment)

    def latest_per_equipment(self):
        return self.get_queryset().latest_per_equipment()


class CalibrationRecord(SecureModel):
    """
    Records a calibration event for a piece of equipment.

    Tracks calibration date, result, next due date, certificate info, and traceability.
    Standards_used field captures traceability to national/international standards
    as required by ISO 9001.
    """

    class CalibrationResult(models.TextChoices):
        PASS = 'pass', 'Pass'
        FAIL = 'fail', 'Fail'
        LIMITED = 'limited', 'Limited/Restricted Use'

    class CalibrationType(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        INITIAL = 'initial', 'Initial'
        AFTER_REPAIR = 'after_repair', 'After Repair'
        AFTER_ADJUSTMENT = 'after_adjustment', 'After Adjustment'
        VERIFICATION = 'verification', 'Verification Check'

    documents = GenericRelation('Tracker.Documents')
    """Calibration certificate and related documentation."""

    equipment = models.ForeignKey(
        'Tracker.Equipments',
        on_delete=models.CASCADE,
        related_name='calibration_records'
    )
    """The equipment that was calibrated."""

    # === CORE CALIBRATION DATA ===

    calibration_date = models.DateField()
    """Date calibration was performed."""

    due_date = models.DateField()
    """Date next calibration is due."""

    result = models.CharField(
        max_length=10,
        choices=CalibrationResult.choices,
        default=CalibrationResult.PASS
    )
    """Result of the calibration."""

    calibration_type = models.CharField(
        max_length=20,
        choices=CalibrationType.choices,
        default=CalibrationType.SCHEDULED
    )
    """Type of calibration event."""

    # === WHO PERFORMED IT ===

    performed_by = models.CharField(
        max_length=200,
        blank=True,
        help_text="Person or lab that performed calibration"
    )
    """Who performed the calibration - could be internal user or external lab name."""

    external_lab = models.CharField(
        max_length=200,
        blank=True,
        help_text="External calibration lab name if sent out"
    )
    """Name of external lab if calibration was outsourced."""

    # === TRACEABILITY (ISO 9001 requirement) ===

    certificate_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Calibration certificate number for traceability"
    )

    standards_used = models.TextField(
        blank=True,
        help_text="Reference standards used with traceability info (e.g., 'NIST-traceable gauge blocks, cert #12345')"
    )
    """Standards used during calibration, with certificate/traceability information."""

    # === AS-FOUND / AS-LEFT ===

    as_found_in_tolerance = models.BooleanField(
        null=True,
        blank=True,
        help_text="Was equipment within tolerance when received for calibration?"
    )
    """Whether equipment was in tolerance before any adjustments. Null = not recorded."""

    adjustments_made = models.BooleanField(
        default=False,
        help_text="Were adjustments made during calibration?"
    )
    """Whether the equipment required adjustment during calibration."""

    notes = models.TextField(blank=True)

    objects = CalibrationRecordManager()

    class Meta:
        verbose_name = 'Calibration Record'
        verbose_name_plural = 'Calibration Records'
        ordering = ['-calibration_date']
        get_latest_by = 'calibration_date'

    def __str__(self):
        return f"{self.equipment} - {self.calibration_date} ({self.result})"

    # === STATUS PROPERTIES ===

    @property
    def is_current(self) -> bool:
        """Returns True if calibration has not expired and passed."""
        if self.result == self.CalibrationResult.FAIL:
            return False
        return self.due_date >= timezone.now().date()

    @property
    def status(self) -> str:
        """Returns 'current', 'due_soon', 'overdue', or 'failed'."""
        if self.result == self.CalibrationResult.FAIL:
            return 'failed'
        today = timezone.now().date()
        if self.due_date < today:
            return 'overdue'
        from datetime import timedelta
        if self.due_date <= today + timedelta(days=30):
            return 'due_soon'
        return 'current'

    @property
    def days_until_due(self) -> int:
        """Days until calibration due. Negative if overdue."""
        return (self.due_date - timezone.now().date()).days

    @property
    def days_overdue(self) -> int | None:
        """Days overdue, or None if not overdue."""
        days = self.days_until_due
        return abs(days) if days < 0 else None

    # === IMPACT ASSESSMENT ===

    def get_affected_parts(self):
        """Return parts inspected by this equipment during this calibration period.

        Date range: from this calibration_date to (next calibration date or due_date).
        Critical for impact assessment when calibration fails or equipment found out of tolerance.
        """
        from Tracker.models import Parts
        from Tracker.models.qms import EquipmentUsage

        # Find end date: next calibration record or this due_date
        next_cal = CalibrationRecord.objects.filter(
            equipment=self.equipment,
            calibration_date__gt=self.calibration_date
        ).order_by('calibration_date').first()

        end_date = next_cal.calibration_date if next_cal else self.due_date

        return Parts.objects.filter(
            id__in=EquipmentUsage.objects.filter(
                equipment=self.equipment,
                created_at__date__range=(self.calibration_date, end_date)
            ).values_list('part_id', flat=True)
        ).distinct()

    def get_previous_calibration(self):
        """Return the calibration record this one supersedes, or None."""
        return CalibrationRecord.objects.filter(
            equipment=self.equipment,
            calibration_date__lt=self.calibration_date
        ).order_by('-calibration_date').first()


# ===== STEP COMPLETION & WORKFLOW MODELS =====

class FPIStatus(models.TextChoices):
    """First Piece Inspection status choices."""
    NOT_REQUIRED = 'not_required', 'Not Required'
    PENDING = 'pending', 'Pending'
    PASSED = 'passed', 'Passed'
    FAILED = 'failed', 'Failed'
    WAIVED = 'waived', 'Waived'


class FPIResult(models.TextChoices):
    """FPI result choices."""
    PASS = 'pass', 'Pass'
    FAIL = 'fail', 'Fail'
    CONDITIONAL = 'conditional', 'Conditional Pass'


class FPIRecord(SecureModel):
    """
    First Piece Inspection (FPI) record.

    Tracks FPI requirements and results for a work order/step/equipment combination.
    FPI verifies setup correctness before full production begins.

    FPI scope options (defined on Step):
    - per_workorder: One FPI per work order at this step
    - per_shift: One FPI per shift per step
    - per_equipment: One FPI per equipment per step per work order
    - per_operator: One FPI per operator per step per work order
    """

    work_order = models.ForeignKey(
        'Tracker.WorkOrder',
        on_delete=models.CASCADE,
        related_name='fpi_records'
    )
    step = models.ForeignKey(
        'Tracker.Steps',
        on_delete=models.PROTECT,
        related_name='fpi_records'
    )
    part_type = models.ForeignKey(
        'Tracker.PartTypes',
        on_delete=models.PROTECT,
        related_name='fpi_records'
    )
    designated_part = models.ForeignKey(
        'Tracker.Parts',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='fpi_records',
        help_text='The part designated for FPI'
    )
    equipment = models.ForeignKey(
        'Tracker.Equipments',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='fpi_records',
        help_text='Equipment being used (for per-equipment FPI)'
    )
    shift_date = models.DateField(
        null=True,
        blank=True,
        help_text='Date of the shift for per-shift FPI'
    )

    status = models.CharField(
        max_length=20,
        choices=FPIStatus.choices,
        default=FPIStatus.PENDING,
        help_text='Current status of the FPI'
    )
    result = models.CharField(
        max_length=20,
        choices=FPIResult.choices,
        blank=True,
        help_text='Final result of the FPI'
    )

    inspected_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='fpi_inspections',
        help_text='User who performed the inspection'
    )
    inspected_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When inspection was completed'
    )

    waived = models.BooleanField(
        default=False,
        help_text='Whether FPI requirement was waived'
    )
    waived_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        help_text='User who waived the FPI'
    )
    waive_reason = models.TextField(
        blank=True,
        help_text='Reason for waiving FPI requirement'
    )

    class Meta:
        verbose_name = 'FPI Record'
        verbose_name_plural = 'FPI Records'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['work_order', 'step', 'status']),
            models.Index(fields=['equipment', 'shift_date']),
        ]

    def __str__(self):
        return f"FPI for WO-{self.work_order.ERP_id} @ {self.step.name}"

    def pass_inspection(self, user, notes=''):
        """Mark FPI as passed."""
        self.status = FPIStatus.PASSED
        self.result = FPIResult.PASS
        self.inspected_by = user
        self.inspected_at = timezone.now()
        self.save()

    def fail_inspection(self, user, notes=''):
        """Mark FPI as failed."""
        self.status = FPIStatus.FAILED
        self.result = FPIResult.FAIL
        self.inspected_by = user
        self.inspected_at = timezone.now()
        self.save()

    def waive(self, user, reason):
        """Waive the FPI requirement."""
        if not reason or len(reason.strip()) < 10:
            raise ValueError("Waive reason must be at least 10 characters")
        self.status = FPIStatus.WAIVED
        self.waived = True
        self.waived_by = user
        self.waive_reason = reason
        self.save()


class BlockType(models.TextChoices):
    """Types of blocks that can prevent step advancement."""
    QA_SIGNOFF = 'qa_signoff', 'QA Signoff Required'
    FPI_REQUIRED = 'fpi_required', 'FPI Required'
    MEASUREMENT_FAILED = 'measurement_failed', 'Measurement Failed'
    QUARANTINE = 'quarantine', 'Part Quarantined'
    SAMPLING_REQUIRED = 'sampling_required', 'Sampling Required'
    BATCH_INCOMPLETE = 'batch_incomplete', 'Batch Incomplete'
    TRAINING_EXPIRED = 'training_expired', 'Training Expired'
    CALIBRATION_EXPIRED = 'calibration_expired', 'Calibration Expired'
    REGULATORY_HOLD = 'regulatory_hold', 'Regulatory Hold'
    ROLLBACK = 'rollback', 'Step Rollback'
    OTHER = 'other', 'Other'


class OverrideStatus(models.TextChoices):
    """Status of an override request."""
    PENDING = 'pending', 'Pending'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'
    EXPIRED = 'expired', 'Expired'


class StepOverride(SecureModel):
    """
    Override record for bypassing step advancement blocks.

    Used when parts need to advance despite failing validation checks.
    Requires approval workflow and maintains audit trail.
    """

    step_execution = models.ForeignKey(
        'Tracker.StepExecution',
        on_delete=models.CASCADE,
        related_name='overrides'
    )
    block_type = models.CharField(
        max_length=30,
        choices=BlockType.choices,
        help_text='Type of block being overridden'
    )

    requested_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='override_requests'
    )
    requested_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When override was requested'
    )
    reason = models.TextField(
        help_text='Justification for the override'
    )

    approved_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='override_approvals',
        help_text='User who approved/rejected the override'
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When override was approved'
    )
    status = models.CharField(
        max_length=20,
        choices=OverrideStatus.choices,
        default=OverrideStatus.PENDING,
        help_text='Current status of the override request'
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When this override expires'
    )
    used = models.BooleanField(
        default=False,
        help_text='Whether this override has been used'
    )
    used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When this override was used'
    )

    class Meta:
        verbose_name = 'Step Override'
        verbose_name_plural = 'Step Overrides'
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['step_execution', 'status']),
            models.Index(fields=['status', 'expires_at']),
        ]

    def __str__(self):
        return f"Override for {self.step_execution}: {self.get_block_type_display()}"

    def approve(self, user, expiry_hours=None):
        """Approve the override request."""
        from datetime import timedelta

        self.approved_by = user
        self.approved_at = timezone.now()
        self.status = OverrideStatus.APPROVED

        # Set expiry based on step configuration or parameter
        if expiry_hours:
            self.expires_at = timezone.now() + timedelta(hours=expiry_hours)
        elif hasattr(self.step_execution.step, 'override_expiry_hours'):
            hours = self.step_execution.step.override_expiry_hours
            self.expires_at = timezone.now() + timedelta(hours=hours)

        self.save()

    def reject(self, user, reason=''):
        """Reject the override request."""
        self.approved_by = user
        self.approved_at = timezone.now()
        self.status = OverrideStatus.REJECTED
        if reason:
            self.reason = f"{self.reason}\n\n[REJECTED]: {reason}"
        self.save()

    def mark_used(self):
        """Mark the override as used."""
        if self.status != OverrideStatus.APPROVED:
            raise ValueError("Only approved overrides can be used")
        if self.expires_at and timezone.now() > self.expires_at:
            self.status = OverrideStatus.EXPIRED
            self.save()
            raise ValueError("Override has expired")

        self.used = True
        self.used_at = timezone.now()
        self.save()

    @property
    def is_valid(self):
        """Check if override is approved and not expired or used."""
        if self.status != OverrideStatus.APPROVED:
            return False
        if self.used:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True


class StepExecutionMeasurement(SecureModel):
    """
    Measurement recorded during step execution.

    Links measurements to specific step executions rather than quality reports,
    enabling real-time validation during production.
    """

    step_execution = models.ForeignKey(
        'Tracker.StepExecution',
        on_delete=models.CASCADE,
        related_name='measurements'
    )
    measurement_definition = models.ForeignKey(
        'Tracker.MeasurementDefinition',
        on_delete=models.PROTECT,
        related_name='execution_measurements'
    )

    value = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text='Numeric measurement value'
    )
    string_value = models.CharField(
        max_length=100,
        blank=True,
        help_text='String value for pass/fail or text measurements'
    )
    is_within_spec = models.BooleanField(
        null=True,
        help_text='Whether measurement is within specification (auto-calculated)'
    )

    recorded_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='recorded_measurements'
    )
    recorded_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When measurement was recorded'
    )
    equipment = models.ForeignKey(
        'Tracker.Equipments',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='step_measurements',
        help_text='Equipment used for measurement'
    )

    class Meta:
        verbose_name = 'Step Execution Measurement'
        verbose_name_plural = 'Step Execution Measurements'
        ordering = ['step_execution', 'recorded_at']
        indexes = [
            models.Index(fields=['step_execution', 'measurement_definition']),
        ]

    def __str__(self):
        return f"{self.measurement_definition.label}: {self.value or self.string_value}"

    def save(self, *args, **kwargs):
        # Auto-calculate is_within_spec
        self.is_within_spec = self.evaluate_spec()
        super().save(*args, **kwargs)

    def evaluate_spec(self):
        """Evaluate if measurement is within specification."""
        defn = self.measurement_definition
        if defn.type == "NUMERIC":
            if self.value is None:
                return None
            from decimal import Decimal
            if defn.nominal is None or defn.lower_tol is None or defn.upper_tol is None:
                return None
            lower = defn.nominal - defn.lower_tol
            upper = defn.nominal + defn.upper_tol
            return lower <= Decimal(str(self.value)) <= upper
        elif defn.type == "PASS_FAIL":
            return self.string_value.upper() == "PASS"
        return None


# =============================================================================
# VOIDABLE MODEL MIXIN
# =============================================================================

class VoidableModel(models.Model):
    """
    Abstract mixin for models that can be voided instead of deleted.

    Voiding preserves the record for audit trail while marking it as invalid.
    Voided records can optionally point to a replacement record.
    """
    is_voided = models.BooleanField(
        default=False,
        help_text='Whether this record has been voided'
    )
    voided_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When this record was voided'
    )
    voided_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        help_text='User who voided this record'
    )
    void_reason = models.TextField(
        blank=True,
        help_text='Reason for voiding this record'
    )

    class Meta:
        abstract = True

    def void(self, user, reason):
        """Void this record."""
        from django.utils import timezone
        self.is_voided = True
        self.voided_at = timezone.now()
        self.voided_by = user
        self.void_reason = reason
        self.save(update_fields=['is_voided', 'voided_at', 'voided_by', 'void_reason'])


# =============================================================================
# RECORD EDIT (AUDIT TRAIL)
# =============================================================================

class RecordEdit(SecureModel):
    """
    Tracks field-level edits to records for audit trail.

    Used when records are edited (not voided) to maintain history
    of what was changed, by whom, and why.
    """
    # What was edited (generic foreign key)
    content_type = models.ForeignKey(
        'contenttypes.ContentType',
        on_delete=models.CASCADE,
        help_text='Type of the edited record'
    )
    object_id = models.UUIDField(
        help_text='ID of the edited record'
    )

    # Field-level tracking
    field_name = models.CharField(
        max_length=100,
        help_text='Name of the field that was edited'
    )
    old_value = models.TextField(
        blank=True,
        help_text='Previous value (serialized)'
    )
    new_value = models.TextField(
        blank=True,
        help_text='New value (serialized)'
    )

    # Why
    reason = models.TextField(
        help_text='Reason for the edit'
    )

    # Who/when
    edited_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='record_edits',
        help_text='User who made the edit'
    )
    edited_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When the edit was made'
    )

    class Meta:
        ordering = ['-edited_at']
        verbose_name = 'Record Edit'
        verbose_name_plural = 'Record Edits'
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['edited_by', 'edited_at']),
        ]

    def __str__(self):
        return f"{self.content_type.model}.{self.field_name} edited by {self.edited_by}"


# =============================================================================
# STEP ROLLBACK
# =============================================================================

class RollbackReason(models.TextChoices):
    """Standard reasons for rolling back a step."""
    OPERATOR_ERROR = 'operator_error', 'Operator Error'
    DATA_ENTRY_ERROR = 'data_entry_error', 'Data Entry Error'
    WRONG_DECISION = 'wrong_decision', 'Wrong Decision Path'
    DEFECT_FOUND = 'defect_found', 'Defect Found Later'
    REWORK_REQUIRED = 'rework_required', 'Rework Required'
    EQUIPMENT_ISSUE = 'equipment_issue', 'Equipment Issue Discovered'
    PROCESS_DEVIATION = 'process_deviation', 'Process Deviation'
    ENGINEERING_REQUEST = 'engineering_request', 'Engineering Request'
    CUSTOMER_REJECTION = 'customer_rejection', 'Customer Rejection'
    OTHER = 'other', 'Other'


class RollbackStatus(models.TextChoices):
    """Status of a rollback request."""
    PENDING = 'pending', 'Pending Approval'
    APPROVED = 'approved', 'Approved'
    EXECUTED = 'executed', 'Executed'
    REJECTED = 'rejected', 'Rejected'


class StepRollback(SecureModel):
    """
    Records a rollback operation on a part.

    Tracks what was rolled back, why, and what happened to affected records.
    Supports both quick undo (same step) and full rollback (multiple steps back).
    """
    # What was rolled back
    part = models.ForeignKey(
        'Tracker.Parts',
        on_delete=models.CASCADE,
        related_name='rollbacks',
        help_text='Part that was rolled back'
    )
    from_step = models.ForeignKey(
        'Tracker.Steps',
        on_delete=models.PROTECT,
        related_name='rollbacks_from',
        help_text='Step the part was at before rollback'
    )
    to_step = models.ForeignKey(
        'Tracker.Steps',
        on_delete=models.PROTECT,
        related_name='rollbacks_to',
        help_text='Step the part was rolled back to'
    )

    # Why
    reason = models.CharField(
        max_length=30,
        choices=RollbackReason.choices,
        help_text='Reason category for the rollback'
    )
    reason_detail = models.TextField(
        help_text='Detailed explanation for the rollback'
    )

    # Related records
    ncr_reference = models.ForeignKey(
        'Tracker.CAPA',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='related_rollbacks',
        help_text='Related NCR/CAPA if applicable'
    )

    # What was voided (for traceability)
    voided_executions = models.JSONField(
        default=list,
        help_text='StepExecution IDs that were voided'
    )
    voided_quality_reports = models.JSONField(
        default=list,
        help_text='QualityReport IDs that were voided'
    )
    voided_measurements = models.JSONField(
        default=list,
        help_text='StepExecutionMeasurement IDs that were voided'
    )

    # Options
    preserve_measurements = models.BooleanField(
        default=False,
        help_text='If True, measurements at target step are preserved'
    )
    require_re_inspection = models.BooleanField(
        default=True,
        help_text='If True, part is re-flagged for sampling at target step'
    )
    require_re_fpi = models.BooleanField(
        default=False,
        help_text='If True, FPI must be redone'
    )

    # Request workflow
    requested_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='rollback_requests',
        help_text='User who requested the rollback'
    )
    requested_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When rollback was requested'
    )

    # Approval workflow
    approved_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='rollback_approvals',
        help_text='User who approved/rejected the rollback'
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When rollback was approved'
    )

    status = models.CharField(
        max_length=20,
        choices=RollbackStatus.choices,
        default=RollbackStatus.PENDING,
        help_text='Current status of the rollback'
    )

    # Execution tracking
    executed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When rollback was executed'
    )
    executed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='rollback_executions',
        help_text='User who executed the rollback'
    )

    class Meta:
        ordering = ['-requested_at']
        verbose_name = 'Step Rollback'
        verbose_name_plural = 'Step Rollbacks'
        indexes = [
            models.Index(fields=['part', 'status']),
            models.Index(fields=['status', 'requested_at']),
        ]

    def __str__(self):
        return f"Rollback {self.part} from {self.from_step} to {self.to_step}"

    def approve(self, user):
        """Approve this rollback request."""
        from django.utils import timezone
        self.status = RollbackStatus.APPROVED
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save(update_fields=['status', 'approved_by', 'approved_at'])

    def reject(self, user):
        """Reject this rollback request."""
        from django.utils import timezone
        self.status = RollbackStatus.REJECTED
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save(update_fields=['status', 'approved_by', 'approved_at'])


# =============================================================================
# BATCH ROLLBACK
# =============================================================================

class BatchRollback(SecureModel):
    """
    Rollback multiple parts at once.

    Used for systemic issues affecting many parts (e.g., equipment out of cal,
    bad material lot, process deviation affecting multiple units).
    """
    work_order = models.ForeignKey(
        'Tracker.WorkOrder',
        on_delete=models.CASCADE,
        related_name='batch_rollbacks',
        help_text='Work order containing affected parts'
    )
    to_step = models.ForeignKey(
        'Tracker.Steps',
        on_delete=models.PROTECT,
        related_name='batch_rollbacks_to',
        help_text='Target step for rollback'
    )

    # Which parts
    affected_parts = models.ManyToManyField(
        'Tracker.Parts',
        related_name='batch_rollbacks',
        help_text='Parts included in this batch rollback'
    )
    selection_criteria = models.JSONField(
        default=dict,
        help_text='How parts were selected (for audit)'
    )
    """
    Example selection_criteria:
    {
        "type": "equipment",
        "equipment_id": "uuid",
        "date_range": ["2024-01-15", "2024-01-16"],
        "steps": ["uuid1", "uuid2"]
    }
    """

    # Why
    reason = models.CharField(
        max_length=30,
        choices=RollbackReason.choices,
        help_text='Reason category for the rollback'
    )
    reason_detail = models.TextField(
        help_text='Detailed explanation for the rollback'
    )

    # Related records
    ncr_reference = models.ForeignKey(
        'Tracker.CAPA',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='related_batch_rollbacks',
        help_text='Related NCR/CAPA if applicable'
    )

    # Individual rollbacks created for each part
    individual_rollbacks = models.ManyToManyField(
        StepRollback,
        related_name='batch_rollback',
        blank=True,
        help_text='Individual StepRollback records created for each part'
    )

    # Request workflow
    requested_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='batch_rollback_requests',
        help_text='User who requested the batch rollback'
    )
    requested_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When batch rollback was requested'
    )

    # Approval workflow
    approved_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='batch_rollback_approvals',
        help_text='User who approved/rejected the batch rollback'
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When batch rollback was approved'
    )

    status = models.CharField(
        max_length=20,
        choices=RollbackStatus.choices,
        default=RollbackStatus.PENDING,
        help_text='Current status of the batch rollback'
    )

    # Execution tracking
    executed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When batch rollback was executed'
    )
    executed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='batch_rollback_executions',
        help_text='User who executed the batch rollback'
    )

    class Meta:
        ordering = ['-requested_at']
        verbose_name = 'Batch Rollback'
        verbose_name_plural = 'Batch Rollbacks'

    def __str__(self):
        return f"Batch rollback to {self.to_step} ({self.affected_parts.count()} parts)"

    @property
    def parts_count(self):
        """Number of parts affected by this batch rollback."""
        return self.affected_parts.count()

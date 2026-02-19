"""
SPC (Statistical Process Control) Models

Contains:
- SPCBaseline: Frozen control limits for a measurement definition
- ChartType: Enum for SPC chart types (X-bar R, X-bar S, I-MR)
- BaselineStatus: Enum for baseline status (Active, Superseded)
"""

from django.db import models
from django.conf import settings
from django.utils import timezone

from .core import SecureModel


class ChartType(models.TextChoices):
    """SPC chart types supported by the system."""
    XBAR_R = 'XBAR_R', 'X̄-R'
    XBAR_S = 'XBAR_S', 'X̄-S'
    I_MR = 'I_MR', 'I-MR'


class BaselineStatus(models.TextChoices):
    """Status of an SPC baseline."""
    ACTIVE = 'ACTIVE', 'Active'
    SUPERSEDED = 'SUPERSEDED', 'Superseded'


class SPCBaseline(SecureModel):
    """
    Stores frozen SPC control limits for a measurement definition.

    Represents a point-in-time snapshot of control limits that can be used
    for monitoring mode. Supports multiple baselines over time for audit trail.

    QMS Requirements:
    - Full audit trail via SecureModel (soft delete, versioning, audit logging)
    - Track who froze the limits and when
    - Support baseline history (active vs superseded)
    - Store all control limit values for different chart types
    """

    # === Core Relationship ===
    measurement_definition = models.ForeignKey(
        "MeasurementDefinition",
        on_delete=models.CASCADE,
        related_name='spc_baselines',
        help_text="The measurement definition this baseline applies to"
    )

    # === Chart Configuration ===
    chart_type = models.CharField(
        max_length=10,
        choices=ChartType.choices,
        help_text="Type of control chart (X-bar R, X-bar S, or I-MR)"
    )
    subgroup_size = models.PositiveIntegerField(
        default=5,
        help_text="Number of samples per subgroup (n=2 to 25 for X-bar charts, n=1 for I-MR)"
    )

    # === X-bar Chart Control Limits (for XBAR_R and XBAR_S) ===
    xbar_ucl = models.DecimalField(
        max_digits=16, decimal_places=6, null=True, blank=True,
        help_text="X-bar chart Upper Control Limit"
    )
    xbar_cl = models.DecimalField(
        max_digits=16, decimal_places=6, null=True, blank=True,
        help_text="X-bar chart Center Line (grand mean)"
    )
    xbar_lcl = models.DecimalField(
        max_digits=16, decimal_places=6, null=True, blank=True,
        help_text="X-bar chart Lower Control Limit"
    )

    # === Range/Sigma Chart Control Limits (for XBAR_R and XBAR_S) ===
    range_ucl = models.DecimalField(
        max_digits=16, decimal_places=6, null=True, blank=True,
        help_text="Range (or S) chart Upper Control Limit"
    )
    range_cl = models.DecimalField(
        max_digits=16, decimal_places=6, null=True, blank=True,
        help_text="Range (or S) chart Center Line"
    )
    range_lcl = models.DecimalField(
        max_digits=16, decimal_places=6, null=True, blank=True,
        help_text="Range (or S) chart Lower Control Limit"
    )

    # === I-MR Chart Control Limits (for I_MR) ===
    individual_ucl = models.DecimalField(
        max_digits=16, decimal_places=6, null=True, blank=True,
        help_text="Individual chart Upper Control Limit"
    )
    individual_cl = models.DecimalField(
        max_digits=16, decimal_places=6, null=True, blank=True,
        help_text="Individual chart Center Line"
    )
    individual_lcl = models.DecimalField(
        max_digits=16, decimal_places=6, null=True, blank=True,
        help_text="Individual chart Lower Control Limit"
    )
    mr_ucl = models.DecimalField(
        max_digits=16, decimal_places=6, null=True, blank=True,
        help_text="Moving Range chart Upper Control Limit"
    )
    mr_cl = models.DecimalField(
        max_digits=16, decimal_places=6, null=True, blank=True,
        help_text="Moving Range chart Center Line"
    )

    # === Baseline Status ===
    status = models.CharField(
        max_length=15,
        choices=BaselineStatus.choices,
        default=BaselineStatus.ACTIVE,
        help_text="Current status of this baseline"
    )

    # === Freeze/Activation Tracking ===
    frozen_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='frozen_spc_baselines',
        help_text="User who froze/created this baseline"
    )
    frozen_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when baseline was frozen"
    )

    # === Supersession Tracking ===
    superseded_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='supersedes',
        help_text="The baseline that replaced this one"
    )
    superseded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when this baseline was superseded"
    )
    superseded_reason = models.TextField(
        blank=True,
        help_text="Reason for superseding this baseline"
    )

    # === Metadata ===
    sample_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of data points used to calculate this baseline"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about this baseline"
    )

    class Meta:
        verbose_name = "SPC Baseline"
        verbose_name_plural = "SPC Baselines"
        ordering = ['-frozen_at']
        indexes = [
            models.Index(fields=['measurement_definition', 'status']),
            models.Index(fields=['measurement_definition', '-frozen_at']),
        ]

    def __str__(self):
        return f"{self.measurement_definition.label} - {self.get_chart_type_display()} ({self.frozen_at.strftime('%Y-%m-%d') if self.frozen_at else 'new'})"

    def save(self, *args, **kwargs):
        # If setting to ACTIVE, supersede any existing active baseline for same measurement
        if self.status == BaselineStatus.ACTIVE and not self.pk:
            SPCBaseline.objects.filter(
                measurement_definition=self.measurement_definition,
                status=BaselineStatus.ACTIVE
            ).update(
                status=BaselineStatus.SUPERSEDED,
                superseded_at=timezone.now()
            )
        super().save(*args, **kwargs)

    @classmethod
    def get_active(cls, measurement_definition_id):
        """Get the active baseline for a measurement definition."""
        return cls.objects.filter(
            measurement_definition_id=measurement_definition_id,
            status=BaselineStatus.ACTIVE,
            archived=False
        ).first()

    @property
    def control_limits(self):
        """Return control limits as a dictionary matching frontend types."""
        if self.chart_type == ChartType.I_MR:
            return {
                'individualUCL': float(self.individual_ucl) if self.individual_ucl else None,
                'individualLCL': float(self.individual_lcl) if self.individual_lcl else None,
                'individualCL': float(self.individual_cl) if self.individual_cl else None,
                'mrUCL': float(self.mr_ucl) if self.mr_ucl else None,
                'mrCL': float(self.mr_cl) if self.mr_cl else None,
            }
        else:
            return {
                'xBarUCL': float(self.xbar_ucl) if self.xbar_ucl else None,
                'xBarLCL': float(self.xbar_lcl) if self.xbar_lcl else None,
                'xBarCL': float(self.xbar_cl) if self.xbar_cl else None,
                'rangeUCL': float(self.range_ucl) if self.range_ucl else None,
                'rangeLCL': float(self.range_lcl) if self.range_lcl else None,
                'rangeCL': float(self.range_cl) if self.range_cl else None,
            }

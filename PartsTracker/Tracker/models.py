import os
import random
from datetime import date

from django.contrib.auth.models import AbstractUser
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone

from PartsTrackerApp import settings
from Tracker.hubspot.api import update_deal_stage
from Tracker.sampling import SamplingFallbackApplier


class Companies(models.Model):
    """
    Represents a company or customer entity associated with deals, parts, and HubSpot CRM integration.

    Stores identifying information and external CRM reference data.
    """

    name = models.CharField(max_length=50)
    """The display name of the company or customer."""

    description = models.TextField()
    """A longer text description providing context or background on the company."""

    hubspot_api_id = models.CharField(max_length=50)
    """The unique identifier for this company in the HubSpot API (used for CRM integration)."""

    class Meta:
        verbose_name_plural = 'Companies'
        verbose_name = 'Company'

    def __str__(self):
        """Returns the company name for display in admin and string contexts."""
        return self.name


class User(AbstractUser):
    """
    Extends Django's built-in AbstractUser to associate users with a parent company.

    Includes a timestamp for user registration and optional organizational linkage for access scoping.
    """

    date_joined = models.DateTimeField(default=timezone.now)
    """Timestamp for when the user account was created."""

    parent_company = models.ForeignKey(Companies, on_delete=models.SET_NULL, null=True, blank=True, default=None,
                                       related_name='users')
    """
    Optional reference to the company this user belongs to.

    Used for permission scoping, multi-tenancy logic, and filtering data access by organization.
    """

    class Meta:
        verbose_name_plural = 'Users'
        verbose_name = 'User'

    def __str__(self):
        """Returns a readable representation of the user with username and full name."""
        return f"{self.username}: {self.first_name} {self.last_name}"


def part_doc_upload_path(self, filename):
    """
    Constructs a dynamic file upload path based on part ID, upload date, and custom file name.

    The final path structure is:
        parts_docs/part_<part_id>/<YYYY-MM-DD>/<file_name>.<ext>

    If the part is not yet assigned, 'unassigned' is used in the path.

    Args:
        filename (str): The original name of the uploaded file.

    Returns:
        str: A structured path to store the uploaded file.
    """
    today = date.today().isoformat()
    ext = filename.split('.')[-1]
    new_filename = f"{self.file_name}.{ext}"
    return os.path.join("parts_docs", today, new_filename)


class ClassificationLevel(models.TextChoices):
    PUBLIC = "public", "Public"
    INTERNAL = "internal", "Internal Use"
    CONFIDENTIAL = "confidential", "Confidential"
    RESTRICTED = "restricted", "Restricted"  # serious impact
    SECRET = "secret", "Secret"  # critical impact


class Documents(models.Model):
    """
    Represents a file uploaded and optionally associated with a specific part.

    This model supports version tracking and stores metadata about uploaded files such as
    whether the file is an image, who uploaded it, and when. File storage is dynamically
    structured for traceability and organization.

    Fields:
        is_image (bool): Whether the uploaded file is an image.
        file_name (str): Logical filename (not necessarily the original) used to rename uploaded content.
        file (FileField): The actual file stored, path determined by `part_doc_upload_path`.
        upload_date (date): Date the file was uploaded.
        uploaded_by (ForeignKey): Reference to the User who uploaded the file.
        related_object (GenericForeignKey): Optional reference to the Object associated with this file.
        version (int): Simple version number to track document revisions.

    Storage:
        Files are stored under a directory tree like:
        parts_docs/part_<part_id>/<YYYY-MM-DD>/<file_name>.<ext>
    """

    classification = models.CharField(max_length=20, choices=ClassificationLevel.choices,
                                      default=ClassificationLevel.INTERNAL,
                                      help_text=(
                                          "Level of document classification:\n"
                                          '- "public": Public\n'
                                          '- "internal": Internal Use\n'
                                          '- "confidential": Confidential\n'
                                          '- "restricted": Restricted (serious impact)\n'
                                          '- "secret": Secret (critical impact)'
                                      ),
                                      null=True,
                                      blank=False)

    AI_readable = models.BooleanField(default=False)

    is_image = models.BooleanField()
    """Flag indicating whether the file is an image (for preview/display logic)."""

    file_name = models.CharField(max_length=50)
    """The user-defined logical name used in renaming the uploaded file."""

    file = models.FileField(upload_to=part_doc_upload_path)
    """File field storing the uploaded document in a structured directory path."""

    upload_date = models.DateField(auto_now_add=True)
    """Automatically captures the date the file was uploaded."""

    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, auto_created=True)
    """The user who uploaded the file. May be null if the user was deleted."""

    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True,
                                     help_text="Model of the object this document relates to")

    object_id = models.PositiveBigIntegerField(null=True, blank=True,
                                               help_text="ID of the object this document relates to")

    related_object = GenericForeignKey('content_type', 'object_id')
    """Optional reference to the Object this document relates to."""

    version = models.PositiveSmallIntegerField(default=1)
    """Version number of the document, useful for document change tracking."""

    class Meta:
        verbose_name_plural = 'Documents'
        verbose_name = 'Document'

    def __str__(self):
        """
        Returns a simple string representation of the document for display in admin.
        """
        return self.file_name


class PartTypes(models.Model):
    """
    Represents a type/category of part that can be associated with processes and orders.

    Each new change to a PartType results in version increment and a new database entry.
    Useful for maintaining a historical record of part definitions over time.
    """

    documents = GenericRelation(Documents)
    """Optional Document related to this type of part"""

    created_at = models.DateTimeField(auto_now_add=True)
    """Timestamp of when the part type was first created."""

    updated_at = models.DateTimeField(auto_now=True)
    """Timestamp of the last update to this part type."""

    name = models.CharField(max_length=50)
    """Name of the part type, e.g., 'Fuel Injector'."""

    ID_prefix = models.CharField(max_length=50, null=True, blank=True)
    """Optional prefix for autogenerated part IDs, e.g., 'FJ-'."""

    version = models.IntegerField(default=1)
    """Integer version number of this part type. Auto-incremented on updates."""

    previous_version = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name='next_versions')
    """
    Optional reference to the prior version of this part type.
    Enables version tracking through forward and backward relations.
    """

    ERP_id = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        verbose_name_plural = 'Part Types'
        verbose_name = 'Part Type'

    def save(self, *args, **kwargs):
        """
        Overrides the default save behavior to increment version and create a new DB row
        instead of updating an existing one. This ensures immutability for previous versions.
        """
        if self.pk:
            self.pk = None
            self.version += 1
        super().save(*args, **kwargs)

    def __str__(self):
        """
        Returns a human-readable representation of the part type.
        """
        return self.name


class Processes(models.Model):
    """
    Defines a manufacturing process applied to a given part type.

    Each process consists of multiple sequential steps and may have remanufacturing logic.
    The model is versioned to preserve historical configurations.
    """

    documents = GenericRelation(Documents)
    """Optional Document related to this type of process"""

    created_at = models.DateTimeField(auto_now_add=True)
    """Timestamp of when the process was created."""

    updated_at = models.DateTimeField(auto_now=True)
    """Timestamp of the most recent update to the process."""

    name = models.CharField(max_length=50)
    """Name of the process, e.g., 'Assembly Line A'."""

    is_remanufactured = models.BooleanField()
    """Indicates whether this process is for remanufacturing existing parts."""

    num_steps = models.IntegerField()
    """The total number of steps to generate for this process."""

    part_type = models.ForeignKey(PartTypes, on_delete=models.CASCADE, related_name='processes')
    """ForeignKey to the PartType this process is associated with."""

    version = models.IntegerField(default=1)
    """Version number for tracking process changes over time."""

    previous_version = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name='next_versions')
    """
    Link to the previous version of this process.
    Used for version tracking and historical auditing.
    """

    class Meta:
        verbose_name_plural = 'Processes'
        verbose_name = 'Process'

    def generate_steps(self):
        """
        Creates new `Steps` for this Process if any are missing.
        Can be safely called multiple times. Will not delete existing steps.
        """
        if not self.pk:
            raise ValueError("Process must be saved before generating steps.")

        existing_steps = self.steps.count()
        if self.num_steps <= existing_steps:
            return  # nothing to do

        STEP_NAMES = ["Receiving", "Disassembly", "Cleaning", "Inspection", "Measurement", "Assembly", "Testing",
                      "Calibration", "Packaging", "Shipping"]

        new_steps = [
            Steps(name=f"{self.part_type.name} step {i}" if not settings.DEBUG else random.choice(STEP_NAMES), step=i,
                  process=self, part_type=self.part_type, description=f"Step {i}", expected_duration=None,
                  is_last_step=(i == self.num_steps)) for i in range(existing_steps + 1, self.num_steps + 1)]

        # Reset `is_last_step` flag for all existing steps
        self.steps.update(is_last_step=False)

        # Mark only the new last step if any were added
        if new_steps:
            new_steps[-1].is_last_step = True

        Steps.objects.bulk_create(new_steps)

    def save(self, *args, **kwargs):
        """
        Overrides save to enforce versioning by creating a new DB entry on changes.
        Ensures immutability of past versions for compliance and traceability.
        """
        if self.pk:
            self.pk = None
            self.version += 1
        super().save(*args, **kwargs)

    def __str__(self):
        """
        Returns a readable string showing the name, part type, and remanufacture flag.
        """
        return f"{self.name} {self.part_type}{' Reman' if self.is_remanufactured else ''}"


class MeasurementDefinition(models.Model):
    step = models.ForeignKey("Steps", on_delete=models.CASCADE, related_name="measurement_definitions")
    label = models.CharField(max_length=100)           # e.g. "Outer Diameter"
    type = models.CharField(
        max_length=20,
        choices=[("NUMERIC", "Numeric"), ("PASS_FAIL", "Pass/Fail")],
    )
    allow_quarantine = models.BooleanField(default=True)
    allow_remeasure = models.BooleanField(default=False)
    allow_override = models.BooleanField(default=False)
    require_qa_review = models.BooleanField(default=True)
    unit = models.CharField(max_length=50, blank=True) # e.g. "mm", "psi"
    nominal = models.FloatField(null=True, blank=True)
    upper_tol = models.FloatField(null=True, blank=True)
    lower_tol = models.FloatField(null=True, blank=True)
    required = models.BooleanField(default=True)

    def evaluate_spec(self):
        if self.definition.type == "NUMERIC":
            return (
                    self.definition.nominal - self.definition.lower_tol
                    <= self.value_numeric
                    <= self.definition.nominal + self.definition.upper_tol
            )
        if self.definition.type == "PASS_FAIL":
            return self.value_pass_fail == "PASS"
        return False


class Steps(models.Model):
    """
    Represents a single step within a manufacturing process for a specific part type.

    Each step can have an expected duration, a description, and an associated file.
    Steps are ordered and unique within a process and can be marked as the final step.
    """

    name = models.CharField(max_length=50)

    pass_threshold = models.FloatField(default=1.0)

    documents = GenericRelation(Documents)
    """Optional Document related to this step."""

    order = models.IntegerField()
    """The sequential number of the step within the process."""

    expected_duration = models.DurationField(null=True, blank=True)
    """The estimated time this step is expected to take."""

    process = models.ForeignKey(Processes, related_name='steps', on_delete=models.PROTECT)
    """Reference to the parent `Processes` object. Cannot be deleted if steps exist."""

    description = models.TextField(null=True, blank=True)
    """Optional human-readable explanation of what this step entails."""

    part_type = models.ForeignKey(PartTypes, related_name='steps', on_delete=models.PROTECT)
    """Reference to the `PartTypes` this step belongs to. Used for filtering and validation."""

    is_last_step = models.BooleanField(default=False)
    """Indicates if this is the final step in the process."""

    block_on_quarantine = models.BooleanField(default=False)

    requires_qa_signoff = models.BooleanField(default=False)

    required_measurements = models.ManyToManyField(
        MeasurementDefinition,
        blank=True,
        related_name="required_on_steps",
        help_text="Measurements that must be collected during this step"
    )

    class Meta:
        ordering = ('part_type', 'order')
        unique_together = ('process', 'order')
        verbose_name_plural = 'Steps'
        verbose_name = 'Step'

    def __str__(self):
        """Human-readable representation showing the part type and step number."""
        return f"{self.part_type.name} Step {self.order}"

    def can_advance_step(self, work_order, step):
        parts = Parts.objects.filter(work_order=work_order, current_step=step)
        completed = parts.filter(status='COMPLETED').count()
        total = parts.count()

        if step.block_on_quarantine and parts.filter(status='QUARANTINED').exists():
            return False

        if completed / total < step.pass_threshold:
            return False

        if step.requires_qa_signoff and not QaApproval.objects.filter(step=step, work_order=work_order).exists():
            return False

        return True


class OrdersStatus(models.TextChoices):
    RFI = 'RFI', 'RFI'
    PENDING = 'PENDING', "Pending"
    IN_PROGRESS = 'IN_PROGRESS', "In progress"
    COMPLETED = 'COMPLETED', "Completed"
    ON_HOLD = 'ON_HOLD', "On hold"
    CANCELLED = 'CANCELLED', "Cancelled"


class Orders(models.Model):
    """
    Represents a production or delivery order submitted by a customer.

    Orders define the high-level context for a batch of parts tied to a customer and company.
    Supports lifecycle tracking via status, estimated deadlines, and soft-archiving for traceability.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    """Timestamp indicating when the order was first created."""

    updated_at = models.DateTimeField(auto_now=True)
    """Timestamp automatically updated when the order is modified."""

    name = models.CharField(max_length=50)
    """Internal or customer-facing name for the order."""

    customer_note = models.TextField(max_length=500, null=True, blank=True)
    """Optional note from the customer with extra details or special instructions."""

    documents = GenericRelation(Documents)
    """Optional documents associated with this order."""

    customer = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='customer_orders')
    """Optional link to the user who submitted or is responsible for the order."""

    company = models.ForeignKey('Companies', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    """Company the order is associated with (usually customer company)."""

    estimated_completion = models.DateField(null=True, blank=True)
    """Optional expected date of completion for this order."""

    original_completion_date = models.DateTimeField(null=True, blank=True)

    order_status = models.CharField(max_length=50, choices=OrdersStatus.choices, default=OrdersStatus.PENDING)
    """Current status of the order used to track its lifecycle."""

    class APQP(models.TextChoices):
        PLANNING = 'PLANNING', "Planning"
        PRODUCT_DESIGN_AND_DEVELOPMENT = 'PRODUCT DESIGN AND DEVELOPMENT', "Product design and development"
        PROCESS_DESIGN_AND_DEVELOPMENT = 'PROCESS DESIGN AND DEVELOPMENT', "Process and development"
        PRODUCT_AND_PROCESS_VALIDATION = 'PRODUCT AND PROCESS VALIDATION', "Product and process validation"
        PRODUCTION = 'PRODUCTION', "Production"

    current_hubspot_gate = models.ForeignKey("ExternalAPIOrderIdentifier", blank=True, null=True,
                                             on_delete=models.SET_NULL)

    """Optional field to track HubSpot pipeline status or stage."""

    archived = models.BooleanField(default=False)
    """Soft-deletion flag for keeping old data without fully deleting the record."""

    # --- HubSpot Integration Fields ---
    hubspot_deal_id = models.CharField(max_length=60, unique=True, null=True, blank=True)
    last_synced_hubspot_stage = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        verbose_name = 'Order'

    def delete(self, *args, **kwargs):
        """
        Overrides the default delete to perform a soft archive instead of true deletion.
        """
        self.archived = True
        self.save()

    def archive(self, reason="user_error", user=None, notes=""):
        """
        Archives the order and records the reason for traceability.

        Args:
            reason (str): Archive reason code (must match ArchiveReason.REASON_CHOICES).
            user (User): The user responsible for the action (optional).
            notes (str): Free-text notes elaborating on the archive reason.
        """
        if self.archived:
            return  # Prevent duplicate archiving

        self.archived = True
        self.save()

        ArchiveReason.objects.update_or_create(content_type=ContentType.objects.get_for_model(self), object_id=self.pk,
                                               defaults={"reason": reason, "notes": notes, "user": user, })

    def push_to_hubspot(self):
        if not self.hubspot_deal_id:
            return

        response = update_deal_stage(self.hubspot_deal_id, self.current_hubspot_gate, self)

    def save(self, *args, **kwargs):
        is_update = self.pk is not None
        old_stage = None

        if is_update:
            try:
                old_stage = Orders.objects.get(pk=self.pk).current_hubspot_gate
            except Orders.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        if is_update and self.current_hubspot_gate != old_stage:
            self.push_to_hubspot()


class WorkOrderStatus(models.TextChoices):
    PENDING = 'PENDING', "Pending"
    IN_PROGRESS = 'IN_PROGRESS', "In progress"
    COMPLETED = 'COMPLETED', "Completed"
    ON_HOLD = 'ON_HOLD', "On hold"
    CANCELLED = 'CANCELLED', "Cancelled"
    WAITING_FOR_OPERATOR = 'WAITING_FOR_OPERATOR', "Waiting for operator"

    def __str__(self):
        """Returns the order name for human-readable use in admin or logs."""
        return self.name


class WorkOrder(models.Model):
    """
    Represents a production Work Order derived from a customer Order.

    Work Orders are internal job assignments typically associated with a factory operator.
    Each is traceable to its parent `Orders` record and includes both estimated and actual
    timing data for operational tracking and audit.

    This model supports lifecycle management via statuses and soft notes fields.
    """

    workorder_status = models.CharField(max_length=50, choices=WorkOrderStatus.choices, default=WorkOrderStatus.PENDING)
    """Current status of the work order (e.g., in progress, completed)."""


    quantity = models.IntegerField(default=1)

    documents = GenericRelation(Documents)
    """Optional document relating to this Work Order"""

    ERP_id = models.CharField(max_length=50)
    """External ERP identifier used to sync or reference the work order."""

    created_at = models.DateTimeField(auto_now_add=True)
    """Timestamp when the work order was created."""

    updated_at = models.DateTimeField(auto_now=True)
    """Timestamp for the last modification to this work order."""

    related_order = models.ForeignKey('Orders', on_delete=models.PROTECT, related_name='related_orders', null=True,
                                      blank=True)
    """The customer-facing order this work order is derived from."""

    expected_completion = models.DateField(null=True, blank=True)
    """Projected calendar date by which the work order should be complete."""

    expected_duration = models.DurationField(null=True, blank=True)
    """Planned time span estimated for completing this work order."""

    true_completion = models.DateField(null=True, blank=True)
    """Actual calendar date when the work was completed."""

    true_duration = models.DurationField(null=True, blank=True)
    """Measured time taken to complete the work order."""

    notes = models.TextField(max_length=500, null=True, blank=True)
    """Optional notes or remarks logged during execution or review."""



    class Meta:
        verbose_name = "Work Order"
        verbose_name_plural = "Work Orders"
        ordering = ["-created_at"]

    def __str__(self):
        """Returns a string representation for admin and logs."""
        return f"WO-{self.ERP_id} ({self.workorder_status})"


class SamplingRuleSet(models.Model):
    part_type = models.ForeignKey(PartTypes, on_delete=models.CASCADE)
    process = models.ForeignKey(Processes, on_delete=models.CASCADE)
    step = models.ForeignKey(Steps, on_delete=models.CASCADE, related_name="sampling_ruleset")

    name = models.CharField(max_length=100)
    origin = models.CharField(max_length=100, blank=True)
    active = models.BooleanField(default=True)

    version = models.PositiveIntegerField(default=1)
    supersedes = models.OneToOneField("self", null=True, blank=True, on_delete=models.SET_NULL,
                                      related_name="superseded_by")

    # CSP fallback support
    fallback_ruleset = models.OneToOneField("self", null=True, blank=True, on_delete=models.SET_NULL,
                                            related_name="used_as_fallback_for")
    fallback_threshold = models.PositiveIntegerField(null=True, blank=True,
                                                     help_text="Number of consecutive failures before switching to fallback")
    fallback_duration = models.PositiveIntegerField(null=True, blank=True,
                                                    help_text="Number of good parts required before reverting to this ruleset")

    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    modified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    modified_at = models.DateTimeField(auto_now=True)

    is_fallback = models.BooleanField(default=False)

    archived = models.BooleanField(default=False)

    class Meta:
        unique_together = ("part_type", "process", "step", "version", "is_fallback")

    def __str__(self):
        return f"{self.name} (v{self.version})"

    def supersede_with(self, *, name, rules, created_by):
        new_version = self.version + 1
        return SamplingRuleSet.create_with_rules(
            part_type=self.part_type,
            process=self.process,
            step=self.step,
            name=name,
            version=new_version,
            rules=rules,
            supersedes=self,
            created_by=created_by,
        )

    @classmethod
    def create_with_rules(
            cls,
            *,
            part_type,
            process,
            step,
            name,
            version=1,
            rules=None,
            fallback_ruleset=None,
            fallback_threshold=None,
            fallback_duration=None,
            created_by=None,
            origin="",
            active=True,
            supersedes=None,
            is_fallback=False
    ):
        ruleset = cls.objects.create(
            part_type=part_type,
            process=process,
            step=step,
            name=name,
            version=version,
            fallback_ruleset=fallback_ruleset,
            fallback_threshold=fallback_threshold,
            fallback_duration=fallback_duration,
            created_by=created_by,
            origin=origin,
            active=active,
            supersedes=supersedes,
            is_fallback=is_fallback,
        )

        SamplingRule.bulk_create_for_ruleset(
            ruleset=ruleset,
            rules=rules or [],
            created_by=created_by,
        )

        return ruleset


class SamplingRule(models.Model):
    class RuleType(models.TextChoices):
        EVERY_NTH_PART = "every_nth_part", "Every Nth Part"
        PERCENTAGE = "percentage", "Percentage of Parts"
        RANDOM = "random", "Pure Random"
        FIRST_N_PARTS = "first_n_parts", "First N Parts"
        LAST_N_PARTS = "last_n_parts", "Last N Parts"

    ruleset = models.ForeignKey(SamplingRuleSet, on_delete=models.CASCADE, related_name="rules")
    rule_type = models.CharField(max_length=32, choices=RuleType.choices)
    value = models.PositiveIntegerField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    created_by = models.ForeignKey("User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    modified_by = models.ForeignKey("User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    modified_at = models.DateTimeField(auto_now=True)

    @classmethod
    def bulk_create_for_ruleset(cls, *, ruleset, rules, created_by=None):
        instances = [
            cls(
                ruleset=ruleset,
                rule_type=rule["rule_type"],
                value=rule.get("value"),
                order=rule.get("order", i),
                created_by=created_by,
            )
            for i, rule in enumerate(rules)
        ]
        cls.objects.bulk_create(instances)


class PartsStatus(models.TextChoices):
    # Before production starts
    PENDING = "PENDING", "Pending"  # Created, not yet started

    # Core flow
    IN_PROGRESS = "IN_PROGRESS", "In Progress"  # Actively being worked on
    AWAITING_QA = "AWAITING_QA", "Awaiting QA"  # Step done, waiting for inspection
    READY_FOR_NEXT_STEP = "READY FOR NEXT STEP", "Ready for next step"
    COMPLETED = "COMPLETED", "Completed"  # Fully passed all steps

    # Exceptions
    QUARANTINED = "QUARANTINED", "Quarantined"  # Temporarily flagged for QA review
    REWORK_NEEDED = "REWORK_NEEDED", "Rework Needed"  # Needs rework from QA or operator
    REWORK_IN_PROGRESS = "REWORK_IN_PROGRESS", "Rework In Progress"

    # Terminal failures
    SCRAPPED = "SCRAPPED", "Scrapped"  # Rejected permanently
    CANCELLED = "CANCELLED", "Cancelled"  # Removed before production finished


class Parts(models.Model):
    """
    Represents an individual part undergoing a manufacturing process.

    Parts are linked to Orders, Work Orders, and a specific PartType and Step.
    This model tracks a part’s lifecycle status, position in the process chain,
    and is capable of version-safe archiving and step progression.

    Lifecycle transitions and traceability are critical for quality control and compliance audits.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    """Timestamp when the part was created in the system."""

    updated_at = models.DateTimeField(auto_now=True)
    """Timestamp of the last update to the part's record."""

    class Meta:
        verbose_name_plural = 'Parts'
        verbose_name = 'Part'

    ERP_id = models.CharField(max_length=50)
    """External ERP identifier used to reference this part in outside systems."""

    documents = GenericRelation('Documents')

    part_type = models.ForeignKey(PartTypes, on_delete=models.SET_NULL, null=True, blank=True, related_name='parts')
    """The part type defining process steps and classification of this part."""

    step = models.ForeignKey(Steps, on_delete=models.SET_NULL, null=True, blank=True, related_name='active_parts')
    """The current step the part is undergoing in its manufacturing process."""

    order = models.ForeignKey(Orders, on_delete=models.CASCADE, related_name='parts', null=True, blank=True)
    """Reference to the customer Order that this part belongs to."""

    part_status = models.CharField(max_length=50, choices=PartsStatus.choices, default=PartsStatus.PENDING)
    """Lifecycle status indicating part progress through the workflow."""

    archived = models.BooleanField(default=False)
    """Soft-deletion flag to mark the part as archived without removing it."""

    work_order = models.ForeignKey(WorkOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name='parts')
    """Optional reference to the internal Work Order this part is attached to."""

    requires_sampling = models.BooleanField(default=False)
    """Whether this part requires quality inspection at its current step, determined by SamplingRule evaluation."""

    sampling_rule = models.ForeignKey(SamplingRule, null=True, blank=True, on_delete=models.SET_NULL,
                                      related_name="sampled_parts")
    """The specific sampling rule that triggered inspection for this part."""

    sampling_ruleset = models.ForeignKey(SamplingRuleSet, null=True, blank=True, on_delete=models.SET_NULL,
                                         related_name="sampled_parts")
    """The full sampling rule set used to evaluate this part for inspection."""

    def delete(self, *args, **kwargs):
        """
        Overrides default delete behavior to perform a soft archive instead.

        Automatically triggers archival logic with a default 'user_error' reason.
        A `user` keyword argument can be passed for tracking who initiated deletion.
        """
        self.archive(reason="user_error", user=kwargs.pop(User, None))

    def increment_step(self):
        """
        Marks this part as ready for the next step. If all other parts are ready AND
        the step's advancement conditions are met, bulk-advance them.

        Returns:
            str: "completed_workorder" if final step reached,
                 "marked_ready" if waiting for others,
                 "full_work_order_advanced" if step advanced.
        """
        if not self.step or not self.part_type:
            raise ValueError("Current step or part type is missing.")

        # Final step: mark this part completed
        if self.step.is_last_step:
            self.status = PartsStatus.COMPLETED
            self.save()
            return "completed_workorder"

        try:
            next_step = Steps.objects.get(
                part_type=self.part_type,
                process=self.step.process,
                order=self.step.order + 1
            )
        except Steps.DoesNotExist:
            raise ValueError("Next step not found for this part.")

        # Mark this part ready
        self.status = PartsStatus.READY_FOR_NEXT_STEP
        self.save()

        # Check if all parts at this step are ready
        other_parts_pending = Parts.objects.filter(
            work_order=self.work_order,
            part_type=self.part_type,
            step=self.step
        ).exclude(status=PartsStatus.READY_FOR_NEXT_STEP)

        if other_parts_pending.exists():
            return "marked_ready"

        # All parts are ready. Check if step allows advancement.
        if not self.step.can_advance_step(work_order=self.work_order, step=self.step):
            return "marked_ready"  # Step not ready due to QA/quarantine/pass rate

        # Bulk-advance all parts
        ready_parts = list(Parts.objects.filter(
            work_order=self.work_order,
            part_type=self.part_type,
            step=self.step,
            status=PartsStatus.READY_FOR_NEXT_STEP
        ))

        for part in ready_parts:
            part.step = next_step
            part.status = PartsStatus.IN_PROGRESS  # Or blank if you use "" for active
            evaluator = SamplingFallbackApplier(part=part)
            result = evaluator.evaluate()
            part.requires_sampling = result.get("requires_sampling", False)
            part.sampling_rule = result.get("rule")
            part.sampling_ruleset = result.get("ruleset")
            part.sampling_context = result.get("context")

        Parts.objects.bulk_update(
            ready_parts,
            ["step", "status", "requires_sampling", "sampling_rule", "sampling_ruleset", "sampling_context"]
        )

        return "full_work_order_advanced"

    def archive(self, reason="user_error", user=None, notes=""):
        """
        Archives the part entry without deletion and logs the reason.

        Args:
            reason (str): Code or label for why the part is archived.
            user (User): Optional user object for audit attribution.
            notes (str): Optional explanation or context.
        """
        if self.archived:
            return

        self.archived = True
        self.save()

        try:
            content_type = ContentType.objects.get_for_model(self)
            ArchiveReason.objects.update_or_create(content_type=content_type, object_id=self.pk,
                                                   defaults={"reason": reason, "notes": notes, "user": user, })
        except ContentType.DoesNotExist:
            pass  # Optional: add logging here

    def __str__(self):
        """
        Returns a human-readable identifier combining ERP ID, Order, and PartType.
        """
        deal_name = getattr(self.order, 'name', 'Unknown Deal') if self.order else 'Unknown Deal'
        part_type_name = getattr(self.part_type, 'name', 'Unknown Part Type') if self.part_type else 'Unknown Part Type'
        return f"{self.ERP_id} {deal_name} {part_type_name}"


class EquipmentType(models.Model):
    """
    Represents a category or classification of equipment used in the manufacturing process.

    Examples include 'Lathe', '3D Printer', or 'CMM Machine'.
    This model provides a way to group and differentiate equipment
    based on function or operational use cases.
    """

    name = models.CharField(max_length=50)
    """The unique name for this equipment type (e.g., 'Laser Welder')."""

    class Meta:
        verbose_name_plural = 'Equipment Types'
        verbose_name = 'Equipment Type'

    def __str__(self):
        """
        Returns the name of the equipment type for display purposes.
        """
        return self.name


class Equipments(models.Model):
    name = models.CharField(max_length=50)
    equipment_type = models.ForeignKey(EquipmentType, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name_plural = 'Equipments'
        verbose_name = 'Equipment'

    def __str__(self):
        return f"{self.name} ({self.equipment_type})" if self.equipment_type else self.name


class QualityErrorsList(models.Model):
    """
    Defines a type of known quality error that can be associated with a part inspection.

    This model serves as a reference catalog of defect types, optionally scoped to a specific part type.
    Each entry includes a name and a textual example to help inspectors identify and classify errors accurately.
    """

    error_name = models.CharField(max_length=50)
    """Short descriptive name of the error (e.g., 'Crack', 'Surface Porosity')."""

    error_example = models.TextField()
    """Detailed example or explanation of what the error typically looks like."""

    part_type = models.ForeignKey(PartTypes, on_delete=models.SET_NULL, null=True, blank=True)
    """
    Optional link to a specific `PartType` this error is associated with.
    If unset, the error may be considered general-purpose or applicable across multiple part types.
    """

    def __str__(self):
        """
        Returns a readable label showing the error name and associated part type.
        """
        return f"{self.error_name} ({self.part_type})" if self.part_type else self.error_name


class QualityReports(models.Model):
    """
    Records an instance of a quality issue or operational anomaly identified during part production.

    This model captures contextual information such as the affected part, the machine in use,
    the operator involved, a textual description of the issue, an optional file (e.g., image or PDF),
    and the types of known quality errors observed.

    Multiple quality error types can be associated with a single report via the `errors` ManyToMany field.
    """

    step = models.ForeignKey(Steps, on_delete=models.SET_NULL, null=True, blank=True)

    part = models.ForeignKey(Parts, on_delete=models.SET_NULL, null=True, blank=True, related_name="error_reports")
    """The specific part associated with this error report (if known)."""

    machine = models.ForeignKey(Equipments, on_delete=models.SET_NULL, null=True, blank=True)
    """The equipment or machine used when the error was encountered (if applicable)."""

    operator = models.ManyToManyField(User, blank=True)
    """The operator or inspector who logged the report (if known)."""

    sampling_rule = models.ForeignKey(SamplingRule, null=True, blank=True, on_delete=models.SET_NULL)
    sampling_method = models.CharField(max_length=50, default="manual")
    status = models.CharField(max_length=10, choices=[("PASS", "Pass"), ("FAIL", "Fail"), ("PENDING", "Pending")])

    description = models.TextField(max_length=300, null=True, blank=True)
    """A detailed description of the issue or anomaly observed."""

    file = models.ForeignKey(Documents, null=True, blank=True, on_delete=models.SET_NULL)
    """Optional file attachment providing supporting evidence (e.g., photo, scan, or log)."""

    created_at = models.DateTimeField(auto_now_add=True)
    """Timestamp of when the error report was created."""

    errors = models.ManyToManyField(QualityErrorsList, blank=True)
    """List of known quality errors that this report corresponds to."""

    class Meta:
        verbose_name_plural = 'Error Reports'
        verbose_name = 'Error Report'

    def __str__(self):
        """
        Returns a summary string indicating which part the report refers to and the date.
        """
        return f"Quality Report for {self.part} on {self.created_at.date()}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new and self.status in {"PASS", "FAIL"}:
            SamplingTriggerManager(self.part, self.status).update_state()

        # Trigger fallback if this is a new FAIL report
        if is_new and self.status == "FAIL":
            from Tracker.sampling import SamplingFallbackApplier
            SamplingFallbackApplier(self.part).apply()

class MeasurementResult(models.Model):
    report = models.ForeignKey("QualityReports", on_delete=models.CASCADE, related_name="measurements")
    definition = models.ForeignKey("MeasurementDefinition", on_delete=models.CASCADE)
    value_numeric = models.FloatField(null=True, blank=True)
    value_pass_fail = models.CharField(max_length=4, choices=[("PASS", "Pass"), ("FAIL", "Fail")], null=True, blank=True)
    is_within_spec = models.BooleanField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class EquipmentUsage(models.Model):
    """
    Tracks the usage of equipment on a specific part and step in the manufacturing process.

    Each record logs when a piece of equipment was used, by whom, and optionally links to an error report
    if an issue occurred during usage. This model supports traceability of machine activity and is useful
    for both auditing and performance analysis.
    """

    equipment = models.ForeignKey(Equipments, on_delete=models.SET_NULL, null=True, blank=True)
    """The equipment or machine that was used."""

    step = models.ForeignKey(Steps, on_delete=models.SET_NULL, null=True, blank=True)
    """The specific step in the manufacturing process during which the equipment was used."""

    part = models.ForeignKey(Parts, on_delete=models.SET_NULL, null=True, blank=True)
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


class ExternalAPIOrderIdentifier(models.Model):
    """
    Maps internal order objects to external API identifiers.

    This model is used to associate a local `Orders` instance with an identifier used by
    an external system (such as a customer ERP or third-party integration platform).
    It supports integrations that require reconciliation between internal and external IDs.
    """

    stage_name = models.CharField(max_length=100, unique=True)
    """The internal `Order` object this external identifier corresponds to."""

    API_id = models.CharField(max_length=50)
    """The external system’s identifier for the order (e.g., from HubSpot, ERP, etc.)."""

    class Meta:
        verbose_name = "External API Order Identifier"
        verbose_name_plural = "External API Order Identifiers"

    def __str__(self):
        """
        Returns a string that clearly represents the external mapping.
        """
        return f"Hubspot deal stage: {self.stage_name}, id: {self.API_id}"


class ArchiveReason(models.Model):
    """
    Represents the reason and metadata for archiving a model instance.

    This model supports generic relationships to any other model in the system
    and is used to log why and by whom an object was archived. Useful for auditing,
    compliance, and traceability in regulated environments.
    """

    REASON_CHOICES = [("completed", "Completed"), ("user_error", "Archived due to User Error"),
                      ("obsolete", "Obsolete"), ]
    """Standardized choices explaining why the object was archived."""

    reason = models.CharField(max_length=50, choices=REASON_CHOICES)
    """The reason for archiving the object (e.g., completed, error, obsolete)."""

    notes = models.TextField(blank=True)
    """Optional free-text notes describing the archive context."""

    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT)
    """The content type of the related object (generic foreign key base)."""

    object_id = models.PositiveIntegerField()
    """The ID of the related object being archived."""

    content_object = GenericForeignKey("content_type", "object_id")
    """The actual model instance being archived (resolved via generic relation)."""

    archived_at = models.DateTimeField(auto_now_add=True)
    """Timestamp when the object was archived."""

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    """Optional user responsible for the archive action."""

    class Meta:
        unique_together = ('content_type', 'object_id')
        verbose_name = 'Archive Reason'
        verbose_name_plural = 'Archive Reasons'

    def __str__(self):
        """
        Returns a human-readable string summarizing the archive entry.
        """
        return f"{self.content_object} → {self.reason}"


class StepTransitionLog(models.Model):
    """
    Logs each transition of a part from one step to the next within a manufacturing process.

    This model enables historical tracking of part progression for auditing, traceability,
    and metrics collection. Each log entry captures the part, the step it moved to,
    the operator who performed the transition, and the timestamp of the event.
    """

    step = models.ForeignKey(Steps, on_delete=models.SET_NULL, null=True, blank=True,
                             help_text="The step the part transitioned to.")
    """ForeignKey to the `Steps` instance representing the current step reached."""

    part = models.ForeignKey(Parts, on_delete=models.SET_NULL, null=True, blank=True,
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
        return f"Step {self.step.order} for {self.part} completed at {self.timestamp}"


class SamplingTriggerState(models.Model):
    ruleset = models.ForeignKey(SamplingRuleSet, on_delete=models.CASCADE)
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE)
    step = models.ForeignKey(Steps, on_delete=models.CASCADE)
    active = models.BooleanField(default=True)

    triggered_by = models.ForeignKey(QualityReports, null=True, blank=True, on_delete=models.SET_NULL)
    triggered_at = models.DateTimeField(auto_now_add=True)

    success_count = models.PositiveIntegerField(default=0)
    fail_count = models.PositiveIntegerField(default=0)

    parts_inspected = models.ManyToManyField("Parts", blank=True)

    class Meta:
        unique_together = ("ruleset", "work_order", "step")

    def __str__(self):
        return f"Fallback {self.ruleset} active on WO-{self.work_order.ERP_id} @ {self.step}"


class SamplingTriggerManager:
    def __init__(self, part: Parts, status: str):
        self.part = part
        self.status = status
        self.step = part.step
        self.work_order = part.work_order

    def update_state(self):
        active_state = SamplingTriggerState.objects.filter(step=self.step, work_order=self.work_order,
                                                           active=True).order_by("-triggered_at").first()

        if not active_state:
            return

        if self.status == "PASS":
            active_state.success_count += 1
        else:
            active_state.fail_count += 1

        active_state.parts_inspected.add(self.part)
        active_state.save()

        # Auto-deactivate?
        if active_state.ruleset.fallback_duration:
            if active_state.success_count >= active_state.ruleset.fallback_duration:
                active_state.active = False
                active_state.save()


class QaApproval(models.Model):
    step = models.ForeignKey(Steps, related_name='qa_approvals', on_delete=models.PROTECT)
    work_order = models.ForeignKey(WorkOrder, related_name='qa_approvals', on_delete=models.PROTECT)
    qa_staff = models.ForeignKey(User, related_name='qa_approvals', on_delete=models.PROTECT)


class MeasurementDisposition(models.Model):
    measurement = models.OneToOneField(MeasurementResult, on_delete=models.CASCADE, related_name="disposition")
    disposition_type = models.CharField(choices=[
        ("QUARANTINE", "Quarantined"),
        ("REMEASURE", "Re-measured"),
        ("OVERRIDDEN", "Overridden by QA"),
        ("ESCALATED", "Escalated for Review"),
    ])
    resolved_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    notes = models.TextField(blank=True)
    resolved_at = models.DateTimeField(auto_now_add=True)
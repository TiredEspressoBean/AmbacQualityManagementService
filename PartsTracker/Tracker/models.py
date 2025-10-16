import json
import os
import random
from datetime import date

from auditlog.models import LogEntry
from django.contrib.auth.models import AbstractUser
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from pgvector.django import VectorField

from PartsTrackerApp import settings
from Tracker.hubspot.api import update_deal_stage
from Tracker.sampling import SamplingFallbackApplier


class SecureQuerySet(models.QuerySet):
    """QuerySet with soft delete, versioning, and audit logging"""

    def delete(self):
        """Soft delete all objects in queryset"""
        deleted_count = 0
        for obj in self:
            if not obj.archived:
                obj.delete()  # Calls model's delete() method
                deleted_count += 1
        return deleted_count, {}

    def bulk_soft_delete(self, actor=None, reason="bulk_operation"):
        """Fast bulk soft delete WITH audit logging"""
        objects_to_delete = list(self.filter(archived=False).values('id', 'pk'))
        if not objects_to_delete:
            return 0

        updated_count = self.filter(archived=False).update(deleted_at=timezone.now(), archived=True)

        if updated_count > 0:
            self._create_bulk_audit_logs(objects_to_delete, 'soft_delete_bulk', actor, reason)

        return updated_count

    def bulk_restore(self, actor=None, reason="bulk_restore"):
        """Bulk restore WITH audit logging"""
        objects_to_restore = list(self.filter(archived=True).values('id', 'pk'))
        if not objects_to_restore:
            return 0

        updated_count = self.filter(archived=True).update(deleted_at=None, archived=False)

        if updated_count > 0:
            self._create_bulk_audit_logs(objects_to_restore, 'restore_bulk', actor, reason)

        return updated_count

    def _create_bulk_audit_logs(self, object_list, action, actor=None, reason=""):
        """Create audit log entries for bulk operations"""
        if not object_list:
            return

        content_type = ContentType.objects.get_for_model(self.model)
        log_entries = []

        for obj_data in object_list:
            log_entries.append(
                LogEntry(content_type=content_type, object_pk=str(obj_data['pk']), object_id=obj_data['id'],
                         object_repr=f"{self.model.__name__} (id={obj_data['id']})", action=LogEntry.Action.UPDATE,
                         changes=json.dumps({'archived': [False, True] if 'delete' in action else [True, False],
                                             'bulk_operation': action, 'reason': reason}), actor=actor,
                         timestamp=timezone.now()))

        LogEntry.objects.bulk_create(log_entries)

    def hard_delete(self):
        """Actually delete from database"""
        return super().delete()

    # Basic filters
    def active(self):
        """Get non-archived objects"""
        return self.filter(archived=False)

    def deleted(self):
        """Get archived objects"""
        return self.filter(archived=True)

    # Versioning filters
    def current_versions(self):
        """Get only current versions"""
        return self.filter(is_current_version=True)

    def all_versions(self):
        """Get all versions (current and old)"""
        return self

    # Combined filters
    def active_current(self):
        """Get active objects that are current versions"""
        return self.active().current_versions()


class SecureManager(models.Manager):
    """Unified manager with filtering, soft delete, versioning, and security"""

    def get_queryset(self):
        return SecureQuerySet(self.model, using=self._db)

    # User-based filtering
    def for_user(self, user):
        """Filter data based on user group permissions"""
        queryset = self.active()  # Start with non-archived objects

        # Superusers see everything
        if user.is_superuser:
            return queryset

        # Get user groups for efficiency
        user_groups = set(user.groups.values_list('name', flat=True))

        # Admin and Manager groups see everything
        if 'Admin' in user_groups or 'Manager' in user_groups:
            return queryset

        # Operator group sees all work data (no customer filtering)
        if 'Operator' in user_groups:
            return queryset

        # Customer group filtering - only see their own data
        if 'Customer' in user_groups:
            return self._filter_for_customer(queryset, user)

        # Default: no access for users without groups
        return queryset.none()

    def _filter_for_customer(self, queryset, user):
        """Filter data for customer users"""
        model_name = self.model._meta.model_name

        if model_name == 'orders':
            return queryset.filter(customer=user)
        elif model_name == 'parts':
            return queryset.filter(order__customer=user)
        elif model_name == 'workorder':
            return queryset.filter(related_order__customer=user)
        elif model_name == 'qualityreports':
            return queryset.filter(part__order__customer=user)
        elif model_name == 'documents':
            return queryset.filter(classification='public')
        elif model_name == 'user':
            return queryset.filter(id=user.id)
        elif model_name == 'companies':
            if user.parent_company:
                return queryset.filter(id=user.parent_company.id)
            return queryset.none()

        return queryset.none()

    # Convenience methods that delegate to queryset
    def active(self):
        """Get active (non-archived) objects"""
        return self.get_queryset().active()

    def deleted(self):
        """Get archived objects"""
        return self.get_queryset().deleted()

    def current_versions(self):
        """Get only current versions"""
        return self.get_queryset().current_versions()

    def active_current(self):
        """Get active objects that are current versions"""
        return self.get_queryset().active_current()

    def for_user_current(self, user):
        """Get current versions filtered for user"""
        return self.for_user(user).current_versions()

    # Bulk operations
    def bulk_soft_delete(self, actor=None, reason="bulk_operation"):
        """Manager-level bulk soft delete"""
        return self.get_queryset().bulk_soft_delete(actor=actor, reason=reason)

    def bulk_restore(self, actor=None, reason="bulk_restore"):
        """Manager-level bulk restore"""
        return self.get_queryset().bulk_restore(actor=actor, reason=reason)

    # Versioning helpers
    def get_version_chain(self, root_id):
        """Get all versions of a particular object"""
        try:
            root = self.get(id=root_id)
            while root.previous_version:
                root = root.previous_version
            return root.get_version_history()
        except self.model.DoesNotExist:
            return []


class SecureModel(models.Model):
    """Base model with soft delete, timestamps, versioning, and audit logging"""




    # Soft delete fields
    archived = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    # Auto timestamp fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Versioning fields
    version = models.PositiveIntegerField(default=1)
    previous_version = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name='next_versions')
    is_current_version = models.BooleanField(default=True)

    # Single manager that does everything
    objects = SecureManager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """Soft delete - django-auditlog will automatically log this"""
        if self.archived:
            return

        self.archived = True
        self.deleted_at = timezone.now()
        self.save(using=using)

    def archive(self, reason="user_request", user=None, notes=""):
        """
        Archives the object with a specific reason for audit trail.
        
        Args:
            reason (str): Archive reason code
            user (User): The user responsible for the archive action
            notes (str): Additional notes explaining the archive
        """
        if self.archived:
            return

        # Perform the soft delete
        self.delete()

        # Create archive reason record for audit trail
        try:
            from django.contrib.contenttypes.models import ContentType
            content_type = ContentType.objects.get_for_model(self.__class__)
            ArchiveReason.objects.update_or_create(content_type=content_type, object_id=self.pk,
                                                   defaults={"reason": reason, "notes": notes, "user": user})
        except Exception:
            # If ArchiveReason model doesn't exist or other issues, 
            # still complete the archive operation
            pass

    def restore(self):
        """Restore soft-deleted object"""
        if not self.archived:
            return

        self.archived = False
        self.deleted_at = None
        self.save()

    def hard_delete(self, using=None, keep_parents=False):
        """Actually delete from database"""
        super().delete(using=using, keep_parents=keep_parents)

    def create_new_version(self, **field_updates):
        """Create a new version of this object"""
        if not self.is_current_version:
            raise ValueError("Can only create new versions from current version")

        # Mark current version as not current
        self.is_current_version = False
        self.save()

        # Create new version
        new_data = {}
        for field in self._meta.fields:
            if field.name not in ['id', 'created_at', 'version', 'previous_version', 'is_current_version']:
                new_data[field.name] = getattr(self, field.name)

        # Apply updates
        new_data.update(field_updates)
        new_data.update({'version': self.version + 1, 'previous_version': self, 'is_current_version': True, })

        new_version = self.__class__.objects.create(**new_data)
        return new_version

    def get_version_history(self):
        """Get all versions in chronological order"""
        # Find the root version
        root = self
        while root.previous_version:
            root = root.previous_version

        # Build version chain
        versions = [root]
        current = root
        while True:
            next_version = self.__class__.objects.filter(previous_version=current).first()
            if not next_version:
                break
            versions.append(next_version)
            current = next_version

        return versions

    def get_version(self, version_number):
        """Get a specific version number"""
        versions = self.get_version_history()
        for v in versions:
            if v.version == version_number:
                return v
        return None

    def get_current_version(self):
        """Get the current (latest) version"""
        versions = self.get_version_history()
        return versions[-1] if versions else None

    def __str__(self):
        base_str = super().__str__() if hasattr(super(), '__str__') else str(self.pk)
        return f"{base_str} (v{self.version})"


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

    # Check if file_name already has an extension to avoid double extensions
    file_name = self.file_name
    if file_name.endswith(f'.{ext}'):
        new_filename = file_name
    else:
        new_filename = f"{file_name}.{ext}"

    return os.path.join("parts_docs", today, new_filename)


class ClassificationLevel(models.TextChoices):
    PUBLIC = "public", "Public"
    INTERNAL = "internal", "Internal Use"
    CONFIDENTIAL = "confidential", "Confidential"
    RESTRICTED = "restricted", "Restricted"  # serious impact
    SECRET = "secret", "Secret"  # critical impact


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


class Companies(SecureModel):
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

    def deactivate(self, reason=""):
        """Deactivate user account"""
        self.is_active = False
        self.save()

    def reactivate(self):
        """Reactivate user account"""
        self.is_active = True
        self.save()

    def __str__(self):
        """Returns a readable representation of the user with username and full name."""
        return f"{self.username}: {self.first_name} {self.last_name}"


class UserInvitation(models.Model):
    """
    Tracks invitation tokens for user account activation.

    Allows staff to invite customers to create accounts with secure, time-limited tokens.
    Maintains history of invitations sent, accepted, and expired.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='invitations')
    """The user being invited."""

    token = models.CharField(max_length=64, unique=True, db_index=True)
    """Secure random token for invitation link."""

    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='invitations_sent')
    """Staff member who sent the invitation."""

    sent_at = models.DateTimeField(auto_now_add=True)
    """Timestamp when invitation was sent."""

    expires_at = models.DateTimeField()
    """Expiration timestamp for the invitation token."""

    accepted_at = models.DateTimeField(null=True, blank=True)
    """Timestamp when user accepted invitation and completed signup."""

    accepted_ip_address = models.GenericIPAddressField(null=True, blank=True)
    """IP address from which the invitation was accepted."""

    accepted_user_agent = models.TextField(null=True, blank=True)
    """User agent string from the browser used to accept invitation."""

    class Meta:
        verbose_name = 'User Invitation'
        verbose_name_plural = 'User Invitations'
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user', '-sent_at']),
        ]

    def __str__(self):
        status = "accepted" if self.accepted_at else ("expired" if self.is_expired() else "pending")
        return f"Invitation for {self.user.email} ({status})"

    def is_expired(self):
        """Check if invitation has expired."""
        return timezone.now() > self.expires_at and not self.accepted_at

    def is_valid(self):
        """Check if invitation is still valid (not expired and not yet accepted)."""
        return not self.accepted_at and not self.is_expired()

    @classmethod
    def generate_token(cls):
        """Generate a secure random token."""
        import secrets
        return secrets.token_urlsafe(48)


class Documents(SecureModel):
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
                                      help_text="Security classification level for document access control", null=True,
                                      blank=False)

    ai_readable = models.BooleanField(default=False)

    is_image = models.BooleanField(default=False)
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

    content_object = GenericForeignKey('content_type', 'object_id')
    """Optional reference to the Object this document relates to."""

    class Meta:
        verbose_name_plural = 'Documents'
        verbose_name = 'Document'

    def __str__(self):
        """
        Returns a simple string representation of the document for display in admin.
        """
        return self.file_name

    def user_can_access(self, user):
        """Check if user has permission to access this document"""
        if user.is_superuser:
            return True

        if user.groups.filter(name="Customer").exists():
            return self.classification == ClassificationLevel.PUBLIC
        elif user.groups.filter(name="Employee").exists():
            return self.classification in [ClassificationLevel.PUBLIC, ClassificationLevel.INTERNAL]
        elif user.groups.filter(name="Manager").exists():
            return self.classification in [ClassificationLevel.PUBLIC, ClassificationLevel.INTERNAL,
                                           ClassificationLevel.CONFIDENTIAL]

        return False

    def get_access_level_for_user(self, user):
        """Get the access level this user has for this document"""
        if user.is_superuser:
            return "full_access"

        user_groups = user.groups.values_list('name', flat=True)

        if "Customer" in user_groups:
            return "public_only" if self.classification == ClassificationLevel.PUBLIC else "no_access"
        elif "Employee" in user_groups:
            if self.classification in [ClassificationLevel.PUBLIC, ClassificationLevel.INTERNAL]:
                return "read_only"
            return "no_access"
        elif "Manager" in user_groups:
            if self.classification in [ClassificationLevel.PUBLIC, ClassificationLevel.INTERNAL,
                                       ClassificationLevel.CONFIDENTIAL]:
                return "read_write"
            return "no_access"

        return "no_access"

    def log_access(self, user, request=None):
        """Log document access for audit trail"""
        from auditlog.models import LogEntry
        from django.contrib.contenttypes.models import ContentType
        from django.utils import timezone
        import json

        # Extract request metadata
        remote_addr = None
        if request:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                remote_addr = x_forwarded_for.split(',')[0].strip()
            else:
                remote_addr = request.META.get('REMOTE_ADDR')

        # Log document access
        LogEntry.objects.create(content_type=ContentType.objects.get_for_model(self), object_pk=str(self.pk),
                                object_id=self.id, object_repr=str(self), action=LogEntry.Action.ACCESS,
                                # Use proper Action enum
                                changes=json.dumps({'action_type': 'document_viewed', 'file_name': self.file_name,
                                                    'classification': self.classification, 'is_image': self.is_image}),
                                actor=user, remote_addr=remote_addr, timestamp=timezone.now(),
                                additional_data=json.dumps({'actor_email': user.email if user else None,
                                                            'user_agent': request.META.get(
                                                                'HTTP_USER_AGENT') if request else None,
                                                            'referer': request.META.get(
                                                                'HTTP_REFERER') if request else None}))

        # Log access to related object if it exists
        if self.content_object:
            LogEntry.objects.create(content_type=ContentType.objects.get_for_model(self.content_object),
                                    object_pk=str(self.content_object.pk), object_id=self.content_object.id,
                                    object_repr=str(self.content_object), action=LogEntry.Action.ACCESS,
                                    changes=json.dumps(
                                        {'action_type': 'related_object_accessed_via_document', 'document_id': self.id,
                                         'document_name': self.file_name}), actor=user, remote_addr=remote_addr,
                                    timestamp=timezone.now(), additional_data=json.dumps(
                    {'access_method': 'document_view', 'document_classification': self.classification}))

    def auto_detect_properties(self, file=None):
        """Auto-detect document properties from uploaded file"""
        from mimetypes import guess_type

        file = file or self.file
        if not file:
            return {}

        properties = {}

        # Auto-detect file type
        mime_type, _ = guess_type(file.name)
        properties['is_image'] = mime_type and mime_type.startswith("image/")

        # Auto-set file name if not provided
        if not self.file_name:
            properties['file_name'] = file.name

        return properties

    @classmethod
    def get_user_accessible_queryset(cls, user):
        """Get queryset filtered by user's access permissions"""
        qs = cls.objects.select_related("uploaded_by", "content_type")

        if user.is_superuser:
            return qs
        elif user.groups.filter(name="Customer").exists():
            return qs.filter(classification=ClassificationLevel.PUBLIC)
        elif user.groups.filter(name="Employee").exists():
            return qs.filter(classification__in=[ClassificationLevel.PUBLIC, ClassificationLevel.INTERNAL])
        elif user.groups.filter(name="Manager").exists():
            return qs.filter(classification__in=[ClassificationLevel.PUBLIC, ClassificationLevel.INTERNAL,
                                                 ClassificationLevel.CONFIDENTIAL])
        else:
            return qs.none()

    def embed_async(self):
        """
        Trigger asynchronous embedding of this document via Celery.
        Returns the Celery task result object.

        Use this method to queue embedding in the background without blocking.
        """
        from Tracker.tasks import embed_document_async
        return embed_document_async.delay(self.id)

    def embed_inline(self) -> bool:
        """
        Minimal, synchronous embedding for small text files and PDFs.
        Returns True if chunks were embedded, False if skipped.

        Note: Consider using embed_async() instead to avoid blocking requests.
        """
        import os
        from django.conf import settings
        from django.db import transaction
        from Tracker.ai_embed import embed_texts, chunk_text

        if not settings.AI_EMBED_ENABLED:
            return False

        if not self.file or not os.path.exists(self.file.path):
            return False
        if os.path.getsize(self.file.path) > settings.AI_EMBED_MAX_FILE_BYTES:
            return False

        # Extract text based on file type
        text = self._extract_text_from_file()
        if not text or not text.strip():
            return False

        chunks = chunk_text(text, max_chars=settings.AI_EMBED_CHUNK_CHARS, max_chunks=settings.AI_EMBED_MAX_CHUNKS)
        if not chunks:
            return False

        vecs = embed_texts(chunks)
        # (optional) sanity check on dimensions:
        assert len(vecs[0]) == settings.AI_EMBED_DIM

        rows = [DocChunk(doc=self, preview_text=t[:300], full_text=t, span_meta={"i": i}, embedding=v) for i, (t, v) in
                enumerate(zip(chunks, vecs))]
        with transaction.atomic():
            DocChunk.objects.filter(doc=self).delete()
            DocChunk.objects.bulk_create(rows, batch_size=50)
            self.ai_readable = True
            self.save(update_fields=["ai_readable"])
        return True

    def _extract_text_from_file(self) -> str:
        """
        Extract text from various file formats (PDF, text files, etc.)
        Returns empty string if extraction fails
        """
        import os

        file_path = self.file.path
        file_ext = os.path.splitext(file_path)[1].lower()

        try:
            if file_ext == '.pdf':
                return self._extract_pdf_text(file_path)
            else:
                # Handle as text file
                return self._extract_text_file(file_path)
        except Exception:
            return ""

    def _extract_pdf_text(self, file_path: str) -> str:
        """Extract text from PDF file using PyPDF2"""
        try:
            import PyPDF2
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"

            # Remove null bytes that cause PostgreSQL issues
            text = text.replace('\x00', '')
            return text.strip()
        except ImportError:
            # PyPDF2 not available, return empty
            return ""
        except Exception:
            # PDF extraction failed
            return ""

    def _extract_text_file(self, file_path: str) -> str:
        """Extract text from regular text files"""
        try:
            from django.conf import settings
            with open(file_path, "rb") as f:
                data = f.read(settings.AI_EMBED_MAX_FILE_BYTES + 1)

            text = data.decode("utf-8", errors="ignore")
            # Remove null bytes that cause PostgreSQL issues
            text = text.replace('\x00', '')
            return text.strip()
        except Exception:
            return ""


class PartTypes(SecureModel):
    """
    Represents a type/category of part that can be associated with processes and orders.

    Each new change to a PartType results in version increment and a new database entry.
    Useful for maintaining a historical record of part definitions over time.
    """

    documents = GenericRelation(Documents)
    """Optional Document related to this type of part"""

    name = models.CharField(max_length=50)
    """Name of the part type, e.g., 'Fuel Injector'."""

    ID_prefix = models.CharField(max_length=50, null=True, blank=True)
    """Optional prefix for autogenerated part IDs, e.g., 'FJ-'."""

    ERP_id = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        verbose_name_plural = 'Part Types'
        verbose_name = 'Part Type'

    def __str__(self):
        """
        Returns a human-readable representation of the part type.
        """
        return self.name


class Processes(SecureModel):
    """
    Defines a manufacturing process applied to a given part type.

    Each process consists of multiple sequential steps and may have remanufacturing logic.
    The model is versioned to preserve historical configurations.
    """

    documents = GenericRelation(Documents)
    """Optional Document related to this type of process"""

    name = models.CharField(max_length=50)
    """Name of the process, e.g., 'Assembly Line A'."""

    is_remanufactured = models.BooleanField(default=False)
    """Indicates whether this process is for remanufacturing existing parts."""

    num_steps = models.IntegerField()
    """The total number of steps to generate for this process."""

    part_type = models.ForeignKey(PartTypes, on_delete=models.CASCADE, related_name='processes')
    """ForeignKey to the PartType this process is associated with."""

    is_batch_process = models.BooleanField(default=False,
                                           help_text="If True, UI treats work order parts as a batch unit")
    """Indicates whether this process should be handled as batch-level tracking in the UI."""

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
            Steps(name=f"{self.part_type.name} step {i}" if not settings.DEBUG else random.choice(STEP_NAMES), order=i,
                  process=self, part_type=self.part_type, description=f"Step {i}", expected_duration=None,
                  is_last_step=(i == self.num_steps)) for i in range(existing_steps + 1, self.num_steps + 1)]

        # Reset `is_last_step` flag for all existing steps
        self.steps.update(is_last_step=False)

        # Mark only the new last step if any were added
        if new_steps:
            new_steps[-1].is_last_step = True

        Steps.objects.bulk_create(new_steps)

    def __str__(self):
        """
        Returns a readable string showing the name, part type, and remanufacture flag.
        """
        return f"{self.name} {self.part_type}{' Reman' if self.is_remanufactured else ''}"


class MeasurementDefinition(SecureModel):
    step = models.ForeignKey("Steps", on_delete=models.CASCADE, related_name="measurement_definitions")
    label = models.CharField(max_length=100)  # e.g. "Outer Diameter"
    type = models.CharField(max_length=20, choices=[("NUMERIC", "Numeric"), ("PASS_FAIL", "Pass/Fail")], )
    unit = models.CharField(max_length=50, blank=True)  # e.g. "mm", "psi"
    nominal = models.DecimalField(null=True, blank=True, decimal_places=6, max_digits=9)
    upper_tol = models.DecimalField(null=True, blank=True, decimal_places=6, max_digits=9)
    lower_tol = models.DecimalField(null=True, blank=True, decimal_places=6, max_digits=9)
    required = models.BooleanField(default=True)


class Steps(SecureModel):
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

    notification_users = models.ManyToManyField(User, related_name='notification_users', blank=True)

    required_measurements = models.ManyToManyField(MeasurementDefinition, blank=True, related_name="required_on_steps",
                                                   help_text="Measurements that must be collected during this step")

    sampling_required = models.BooleanField(default=False)
    """Whether this step requires sampling for quality control."""

    min_sampling_rate = models.FloatField(default=0.0, help_text="Minimum % of parts that must be sampled at this step")
    """Minimum sampling rate required for step advancement."""

    class Meta:
        ordering = ('part_type', 'order')
        unique_together = ('process', 'order')
        verbose_name_plural = 'Steps'
        verbose_name = 'Step'

    def __str__(self):
        """Human-readable representation showing the part type and step number."""
        return f"{self.part_type.name} Step {self.order}"

    def get_resolved_sampling_rules(self):
        """Get complete resolved sampling rules for this step"""
        # Get active primary ruleset
        primary_ruleset = self.sampling_ruleset.filter(is_fallback=False, active=True).order_by("-version").first()

        fallback_ruleset = None
        if primary_ruleset and primary_ruleset.fallback_ruleset:
            fallback_ruleset = primary_ruleset.fallback_ruleset

        return {'active_ruleset': {'id': primary_ruleset.id if primary_ruleset else None,
                                   'name': primary_ruleset.name if primary_ruleset else None, 'rules': list(
                primary_ruleset.rules.all().values('id', 'rule_type', 'value', 'order')) if primary_ruleset else [],
                                   'fallback_threshold': primary_ruleset.fallback_threshold if primary_ruleset else None,
                                   'fallback_duration': primary_ruleset.fallback_duration if primary_ruleset else None},
                'fallback_ruleset': {'id': fallback_ruleset.id if fallback_ruleset else None,
                                     'name': fallback_ruleset.name if fallback_ruleset else None, 'rules': list(
                        fallback_ruleset.rules.all().values('id', 'rule_type', 'value',
                                                            'order')) if fallback_ruleset else []} if fallback_ruleset else None}

    def apply_sampling_rules_update(self, rules_data, fallback_rules_data=None, fallback_threshold=None,
                                    fallback_duration=None, user=None):
        """Apply sampling rules update with proper versioning and activation"""
        from django.db import transaction

        with transaction.atomic():
            # Archive existing rulesets
            self.sampling_ruleset.filter(active=True).update(active=False, archived=True)

            # Create fallback ruleset first if provided
            fallback_ruleset = None
            if fallback_rules_data:
                fallback_ruleset = SamplingRuleSet.create_with_rules(part_type=self.part_type, process=self.process,
                                                                     step=self, name=f"Fallback for Step {self.id}",
                                                                     rules=fallback_rules_data, created_by=user,
                                                                     origin="serializer-update", active=True,
                                                                     is_fallback=True)

            # Create main ruleset
            main_ruleset = SamplingRuleSet.create_with_rules(part_type=self.part_type, process=self.process, step=self,
                                                             name=f"Rules for Step {self.id}", rules=rules_data,
                                                             fallback_ruleset=fallback_ruleset,
                                                             fallback_threshold=fallback_threshold,
                                                             fallback_duration=fallback_duration, created_by=user,
                                                             origin="serializer-update", active=True, is_fallback=False)

            # Re-evaluate sampling for any active parts at this step
            active_parts = Parts.objects.filter(step=self,
                                                part_status__in=[PartsStatus.PENDING, PartsStatus.IN_PROGRESS])

            if active_parts.exists():
                self._reevaluate_parts_sampling(list(active_parts))

            return main_ruleset

    def _reevaluate_parts_sampling(self, parts_list):
        """Re-evaluate sampling for list of parts after rule changes"""
        updates = []
        for part in parts_list:
            evaluator = SamplingFallbackApplier(part=part)
            result = evaluator.evaluate()

            part.requires_sampling = result.get("requires_sampling", False)
            part.sampling_rule = result.get("rule")
            part.sampling_ruleset = result.get("ruleset")
            part.sampling_context = result.get("context", {})
            updates.append(part)

        # Bulk update for efficiency
        Parts.objects.bulk_update(updates,
                                  ["requires_sampling", "sampling_rule", "sampling_ruleset", "sampling_context"])

    def update_sampling_rules(self, rules_data, fallback_rules_data=None, fallback_threshold=None,
                              fallback_duration=None, user=None):
        """Update sampling rules for this step"""
        from django.db import transaction

        with transaction.atomic():
            # Get or create primary ruleset
            primary_ruleset = SamplingRuleSet.objects.filter(step=self, part_type=self.part_type, active=True,
                                                             is_fallback=False).first()

            if primary_ruleset:
                # Supersede existing ruleset
                new_ruleset = primary_ruleset.supersede_with(name=f"{self.name} Rules v{primary_ruleset.version + 1}",
                                                             rules=rules_data, created_by=user)
            else:
                # Create new ruleset
                new_ruleset = SamplingRuleSet.create_with_rules(part_type=self.part_type, process=self.process,
                                                                step=self, name=f"{self.name} Rules v1",
                                                                rules=rules_data, created_by=user)

            # Handle fallback ruleset if provided
            if fallback_rules_data:
                fallback_ruleset = SamplingRuleSet.create_with_rules(part_type=self.part_type, process=self.process,
                                                                     step=self, name=f"{self.name} Fallback Rules v1",
                                                                     rules=fallback_rules_data, created_by=user,
                                                                     is_fallback=True)

                # Link fallback to primary
                new_ruleset.fallback_ruleset = fallback_ruleset
                new_ruleset.fallback_threshold = fallback_threshold
                new_ruleset.fallback_duration = fallback_duration
                new_ruleset.save()

            return new_ruleset

    def can_advance_step(self, work_order, step):
        """Fixed method with proper field references"""
        parts = Parts.objects.filter(work_order=work_order, step=step)
        ready_for_next = parts.filter(part_status=PartsStatus.READY_FOR_NEXT_STEP).count()
        total = parts.count()

        if step.block_on_quarantine and parts.filter(part_status='QUARANTINED').exists():
            return False

        # For batch processing, pass threshold should check parts ready to advance
        if ready_for_next / total < step.pass_threshold:
            return False

        if step.requires_qa_signoff and not QaApproval.objects.filter(step=step, work_order=work_order).exists():
            return False

        return True

    def get_active_sampling_ruleset(self, part_type):
        """Get the currently active ruleset for this step"""
        return SamplingRuleSet.objects.filter(step=self, part_type=part_type, active=True, is_fallback=False).order_by(
            "version").last()

    def validate_sampling_coverage(self, work_order):
        """Ensure minimum sampling rate is met"""
        total_parts = Parts.objects.filter(work_order=work_order, step=self).count()
        sampled_parts = Parts.objects.filter(work_order=work_order, step=self, requires_sampling=True).count()

        actual_rate = (sampled_parts / total_parts * 100) if total_parts > 0 else 0
        return actual_rate >= self.min_sampling_rate

    def get_sampling_coverage_report(self, work_order):
        """Generate sampling coverage report for this step"""
        total_parts = Parts.objects.filter(work_order=work_order, step=self).count()
        sampled_parts = Parts.objects.filter(work_order=work_order, step=self, requires_sampling=True).count()

        inspected_parts = QualityReports.objects.filter(part__work_order=work_order, step=self).count()

        return {'total_parts': total_parts, 'sampled_parts': sampled_parts, 'inspected_parts': inspected_parts,
                'sampling_rate': (sampled_parts / total_parts * 100) if total_parts > 0 else 0,
                'inspection_completion': (inspected_parts / sampled_parts * 100) if sampled_parts > 0 else 0,
                'meets_minimum': self.validate_sampling_coverage(work_order)}


class OrdersStatus(models.TextChoices):
    RFI = 'RFI', 'RFI'
    PENDING = 'PENDING', "Pending"
    IN_PROGRESS = 'IN_PROGRESS', "In progress"
    COMPLETED = 'COMPLETED', "Completed"
    ON_HOLD = 'ON_HOLD', "On hold"
    CANCELLED = 'CANCELLED', "Cancelled"


class Orders(SecureModel):
    """
    Represents a production or delivery order submitted by a customer.

    Orders define the high-level context for a batch of parts tied to a customer and company.
    Supports lifecycle tracking via status, estimated deadlines, and soft-archiving for traceability.
    """

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

    # --- HubSpot Integration Fields ---
    hubspot_deal_id = models.CharField(max_length=60, unique=True, null=True, blank=True)
    """HubSpot deal ID - NULL if order was created locally, not from HubSpot."""

    last_synced_hubspot_stage = models.CharField(max_length=100, null=True, blank=True)
    """Cached stage name from last sync."""

    hubspot_last_synced_at = models.DateTimeField(null=True, blank=True)
    """When this order was last synced from HubSpot - NULL if never synced or not a HubSpot order."""

    class Meta:
        verbose_name = 'Order'

    def push_to_hubspot(self):
        """Push order stage changes back to HubSpot."""
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

        # Only push to HubSpot if:
        # 1. This IS a HubSpot order (has hubspot_deal_id)
        # 2. Stage changed
        # 3. Not currently syncing FROM HubSpot (_skip_hubspot_push flag)
        if (is_update and
            self.hubspot_deal_id and
            self.current_hubspot_gate != old_stage and
            not getattr(self, '_skip_hubspot_push', False)):
            # Queue async task to push to HubSpot
            from Tracker.tasks import update_hubspot_deal_stage_task
            update_hubspot_deal_stage_task.delay(
                self.hubspot_deal_id,
                self.current_hubspot_gate.id,
                self.id
            )

    def get_step_distribution(self, exclude_completed=True):
        """Get distribution of parts across steps for this order"""
        from django.db.models import Count

        queryset = self.parts.all()
        if exclude_completed:
            queryset = queryset.exclude(part_status=PartsStatus.COMPLETED)

        step_counts = queryset.values("step_id").annotate(count=Count("id"))

        # Get step names efficiently
        step_id_to_name = {step.id: step.name for step in
                           Steps.objects.filter(id__in=[s["step_id"] for s in step_counts])}

        return [{"id": step["step_id"], "name": step_id_to_name.get(step["step_id"], f"Step {step['step_id']}"),
                 "count": step["count"]} for step in step_counts]

    def bulk_increment_parts_at_step(self, step_id):
        """Increment all parts at a specific step"""
        try:
            target_step = Steps.objects.get(id=step_id)
        except Steps.DoesNotExist:
            raise ValueError(f"Step with id {step_id} does not exist")

        parts_to_advance = self.parts.filter(step=target_step)
        advanced = 0

        for part in parts_to_advance:
            try:
                result = part.increment_step()
                if result in ["completed_workorder", "full_work_order_advanced"]:
                    advanced += 1
            except Exception:
                continue  # Skip failed parts, continue with others

        return {"advanced": advanced, "total": parts_to_advance.count()}

    def bulk_add_parts(self, part_type, step, quantity, part_status=PartsStatus.PENDING, work_order=None,
                       erp_id_start=1):
        """Add multiple parts to this order efficiently"""
        # Create parts without sampling evaluation
        parts = []
        for i in range(quantity):
            erp_id = f"{part_type.ID_prefix or 'P'}{erp_id_start + i:04d}"
            part = Parts(part_status=part_status, order=self, part_type=part_type, step=step, work_order=work_order,
                         archived=False, ERP_id=erp_id)
            parts.append(part)

        # Bulk create for efficiency
        created_parts = Parts.objects.bulk_create(parts)

        # Evaluate sampling for all new parts
        updates = []
        for part in created_parts:
            evaluator = SamplingFallbackApplier(part=part)
            result = evaluator.evaluate()

            part.requires_sampling = result.get("requires_sampling", False)
            part.sampling_rule = result.get("rule")
            part.sampling_ruleset = result.get("ruleset")
            part.sampling_context = result.get("context", {})
            updates.append(part)

        # Bulk update sampling fields
        Parts.objects.bulk_update(updates,
                                  ["requires_sampling", "sampling_rule", "sampling_ruleset", "sampling_context"])

        return {"created": len(created_parts), "parts": created_parts}

    def bulk_remove_parts(self, part_ids):
        """Remove parts from this order by setting order to None"""
        parts = Parts.objects.filter(id__in=part_ids, order=self)
        count = parts.update(order=None)
        return {"removed": count}

    def get_process_stages(self):
        """Get stage progression for order based on parts' current steps"""
        if not self.parts.exists():
            return []

        # Get the process from the first part (assuming all parts follow same process)
        first_part = self.parts.first()
        if not first_part or not first_part.step:
            return []

        process = first_part.step.process
        process_steps = process.steps.order_by('order')

        # Calculate current step based on part progression
        current_step_order = first_part.step.order

        stages = []
        for step in process_steps:
            stages.append({"name": step.name, "timestamp": None,  # Could be enhanced with StepTransitionLog data
                           "is_completed": step.order < current_step_order,
                           "is_current": step.order == current_step_order, "step_id": step.id, "order": step.order})

        return stages

    def get_detailed_stage_info(self):
        """Get detailed stage information with timing and sampling data"""

        stages = self.get_process_stages()
        # Enhance with actual transition data
        for stage in stages:
            step_id = stage['step_id']

            # Get transition timing from logs
            transition_log = StepTransitionLog.objects.filter(part__order=self, step_id=step_id).order_by(
                '-timestamp').first()

            if transition_log:
                stage['timestamp'] = transition_log.timestamp

            # Add sampling information
            parts_at_step = self.parts.filter(step_id=step_id)
            sampled_parts = parts_at_step.filter(requires_sampling=True)

            stage['sampling_info'] = {'total_parts': parts_at_step.count(), 'sampled_parts': sampled_parts.count(),
                                      'sampling_rate': (
                                              sampled_parts.count() / parts_at_step.count() * 100) if parts_at_step.count() > 0 else 0}

        return stages


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


class WorkOrder(SecureModel):
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

    def save(self, *args, **kwargs):
        """Enhanced save with sampling lifecycle management"""
        is_new = self.pk is None
        old_status = None

        if not is_new:
            try:
                old_instance = WorkOrder.objects.get(pk=self.pk)
                old_status = old_instance.workorder_status
            except WorkOrder.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        # Update related order's expected completion date
        if self.related_order and self.expected_completion:
            current_order_completion = self.related_order.estimated_completion

            # Set to the maximum of current order date and this work order's date
            if current_order_completion is None:
                new_completion = self.expected_completion
            else:
                new_completion = max(current_order_completion, self.expected_completion)

            # Only update if the date actually changed to avoid unnecessary saves
            if self.related_order.estimated_completion != new_completion:
                self.related_order.estimated_completion = new_completion
                self.related_order.save(update_fields=['estimated_completion'])

        # Handle status transitions
        if old_status != self.workorder_status:
            self._handle_status_change(old_status)

    def _handle_status_change(self, old_status):
        """Handle work order status changes affecting sampling"""
        if self.workorder_status == WorkOrderStatus.IN_PROGRESS and old_status == WorkOrderStatus.PENDING:
            # Initialize sampling for all parts when work order starts
            self._initialize_sampling()

        elif self.workorder_status == WorkOrderStatus.COMPLETED:
            # Generate final sampling analytics
            self._generate_final_sampling_report()

        elif self.workorder_status == WorkOrderStatus.ON_HOLD:
            # Pause any active fallback triggers
            self._pause_sampling_triggers()

    def _initialize_sampling(self):
        """Initialize sampling evaluation for all parts in work order"""
        parts_without_sampling = self.parts.filter(requires_sampling__isnull=True)

        if parts_without_sampling.exists():
            self._bulk_evaluate_sampling(list(parts_without_sampling))

    def _bulk_evaluate_sampling(self, parts_list):
        """Evaluate sampling for multiple parts efficiently"""
        updates = []
        for part in parts_list:
            evaluator = SamplingFallbackApplier(part=part)
            result = evaluator.evaluate()

            part.requires_sampling = result.get("requires_sampling", False)
            part.sampling_rule = result.get("rule")
            part.sampling_ruleset = result.get("ruleset")
            part.sampling_context = result.get("context", {})
            updates.append(part)

        # Bulk update sampling fields
        Parts.objects.bulk_update(updates,
                                  ["requires_sampling", "sampling_rule", "sampling_ruleset", "sampling_context"])

    def _generate_final_sampling_report(self):
        """Generate comprehensive sampling report for completed work order"""
        # This could create a summary document or trigger reporting
        pass

    def _pause_sampling_triggers(self):
        """Pause active sampling triggers when work order is on hold"""
        SamplingTriggerState.objects.filter(work_order=self, active=True).update(active=False)

    def create_parts_batch(self, part_type, step, quantity=None):
        """Create parts in batch with sampling evaluation"""
        quantity = quantity or self.quantity

        # Create parts without sampling evaluation first
        parts = []
        for i in range(quantity):
            part = Parts(work_order=self, part_type=part_type, step=step,
                         ERP_id=f"{self.ERP_id}-{part_type.ID_prefix or 'P'}{i + 1:04d}",
                         part_status=PartsStatus.PENDING)
            parts.append(part)

        # Bulk create for efficiency
        Parts.objects.bulk_create(parts)

        # CRITICAL FIX: Get fresh parts from DB with IDs for proper sampling evaluation
        # Only get the parts that were just created (latest by ID)
        fresh_parts = list(Parts.objects.filter(work_order=self, part_type=part_type, step=step).order_by('id'))

        # Now evaluate sampling for all parts using fresh objects with IDs
        self._bulk_evaluate_sampling(fresh_parts)

        return fresh_parts

    @classmethod
    def process_csv_date(cls, date_string):
        """Process various date formats from CSV uploads"""
        from datetime import datetime
        from django.utils.dateparse import parse_date

        if not date_string or str(date_string).strip() == '':
            return None

        # Try standard ISO format first
        parsed = parse_date(str(date_string).strip())
        if parsed:
            return parsed

        # Try various formats
        date_formats = ["%b %d", "%B %d", "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]

        for fmt in date_formats:
            try:
                dt = datetime.strptime(str(date_string).strip(), fmt)
                today = datetime.today()
                year = today.year

                # For formats without year, assume next year if date has passed
                if fmt in ["%b %d", "%B %d"]:
                    if dt.month < today.month or (dt.month == today.month and dt.day < today.day):
                        year += 1
                    return dt.replace(year=year).date()
                else:
                    return dt.date()
            except (ValueError, TypeError):
                continue

        raise ValueError(f"Invalid date format: {date_string}")

    @classmethod
    def create_from_csv_row(cls, row_data, user=None):
        """Create or update work order from CSV row data"""
        erp_id = row_data.get('ERP_id')
        if not erp_id:
            raise ValueError("ERP_id is required")

        # Process related order lookup
        related_order = None
        related_order_erp = row_data.get("related_order_erp_id")
        if related_order_erp:
            try:
                related_order = Orders.objects.get(ERP_id=related_order_erp)
            except Orders.DoesNotExist:
                pass  # Continue without related order

        # Process expected completion date
        expected_completion = None
        warnings = []
        if row_data.get("expected_completion"):
            try:
                expected_completion = cls.process_csv_date(row_data["expected_completion"])
            except ValueError as e:
                warnings.append(f"Invalid date format: {e}")

        # Create or update work order
        work_order, created = cls.objects.update_or_create(ERP_id=erp_id,
                                                           defaults={'quantity': row_data.get('quantity', 1),
                                                                     'expected_completion': expected_completion,
                                                                     'notes': row_data.get('notes', ''),
                                                                     'workorder_status': row_data.get(
                                                                         'workorder_status', WorkOrderStatus.PENDING),
                                                                     'related_order': related_order,
                                                                     'expected_duration': row_data.get(
                                                                         'expected_duration'),
                                                                     'true_duration': row_data.get('true_duration')})

        return work_order, created, warnings

    @classmethod
    def bulk_create_from_csv(cls, file_data, user=None):
        """Process CSV file and create multiple work orders"""
        results = []

        for i, row in enumerate(file_data, start=1):
            try:
                work_order, created, warnings = cls.create_from_csv_row(row, user)
                result = {"row": i, "status": "success" if created else "updated", "id": work_order.id}
                if warnings:
                    result["warnings"] = warnings
                results.append(result)

            except Exception as e:
                results.append({"row": i, "status": "error", "errors": str(e)})

        return results


class SamplingRuleSet(SecureModel):
    part_type = models.ForeignKey(PartTypes, on_delete=models.CASCADE)
    process = models.ForeignKey(Processes, on_delete=models.CASCADE)
    step = models.ForeignKey(Steps, on_delete=models.CASCADE, related_name="sampling_ruleset")

    name = models.CharField(max_length=100)
    origin = models.CharField(max_length=100, blank=True)
    active = models.BooleanField(default=True)

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
    modified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    is_fallback = models.BooleanField(default=False)

    class Meta:
        unique_together = ("part_type", "process", "step", "is_fallback")

    def __str__(self):
        return f"{self.name} (v{self.version})"

    def supersede_with(self, *, name, rules, created_by):
        return SamplingRuleSet.create_with_rules(part_type=self.part_type, process=self.process, step=self.step,
                                                 name=name, rules=rules, supersedes=self, created_by=created_by, )

    @classmethod
    def create_with_rules(cls, *, part_type, process, step, name, rules=None, fallback_ruleset=None,
                          fallback_threshold=None, fallback_duration=None, created_by=None, origin="", active=True,
                          supersedes=None, is_fallback=False):
        ruleset = cls.objects.create(part_type=part_type, process=process, step=step, name=name,
                                     fallback_ruleset=fallback_ruleset, fallback_threshold=fallback_threshold,
                                     fallback_duration=fallback_duration, created_by=created_by, origin=origin,
                                     active=active, supersedes=supersedes, is_fallback=is_fallback, )

        SamplingRule.bulk_create_for_ruleset(ruleset=ruleset, rules=rules or [], created_by=created_by, )

        return ruleset

    def activate(self, user=None):
        """Activate this ruleset and deactivate others"""
        # Deactivate other rulesets for same step/part_type
        SamplingRuleSet.objects.filter(step=self.step, part_type=self.part_type, active=True,
                                       is_fallback=self.is_fallback).exclude(pk=self.pk).update(active=False)

        # Activate this ruleset
        self.active = True
        self.modified_by = user
        self.save()

        # Re-evaluate sampling for affected active parts
        self._reevaluate_active_parts(user)

    def _reevaluate_active_parts(self, user=None):
        """Re-evaluate sampling for parts currently at this step"""
        active_parts = Parts.objects.filter(step=self.step, part_type=self.part_type,
                                            part_status__in=[PartsStatus.PENDING, PartsStatus.IN_PROGRESS])

        updates = []
        for part in active_parts:
            evaluator = SamplingFallbackApplier(part=part)
            result = evaluator.evaluate()

            part.requires_sampling = result.get("requires_sampling", False)
            part.sampling_rule = result.get("rule")
            part.sampling_ruleset = result.get("ruleset")
            part.sampling_context = result.get("context", {})
            updates.append(part)

        # Bulk update
        Parts.objects.bulk_update(updates,
                                  ["requires_sampling", "sampling_rule", "sampling_ruleset", "sampling_context"])

    def create_fallback_trigger(self, triggering_part, quality_report):
        """Create fallback trigger and re-evaluate remaining parts"""
        if not self.fallback_ruleset:
            return None

        trigger_state = SamplingTriggerState.objects.create(ruleset=self.fallback_ruleset,
                                                            work_order=triggering_part.work_order, step=self.step,
                                                            triggered_by=quality_report)

        # Re-evaluate remaining parts with fallback rules
        self._apply_fallback_to_remaining_parts(triggering_part)

        return trigger_state

    def _apply_fallback_to_remaining_parts(self, triggering_part):
        """Apply fallback sampling to remaining parts in work order"""
        remaining_parts = Parts.objects.filter(work_order=triggering_part.work_order, step=self.step,
                                               part_type=self.part_type,
                                               part_status__in=[PartsStatus.PENDING, PartsStatus.IN_PROGRESS],
                                               id__gt=triggering_part.id)

        updates = []
        for part in remaining_parts:
            evaluator = SamplingFallbackApplier(part=part)
            result = evaluator.evaluate()  # Will use fallback rules

            part.requires_sampling = result.get("requires_sampling", False)
            part.sampling_rule = result.get("rule")
            part.sampling_ruleset = result.get("ruleset")
            part.sampling_context = result.get("context", {})
            updates.append(part)

        Parts.objects.bulk_update(updates,
                                  ["requires_sampling", "sampling_rule", "sampling_ruleset", "sampling_context"])


class SamplingRule(SecureModel):
    class RuleType(models.TextChoices):
        EVERY_NTH_PART = "every_nth_part", "Every Nth Part"
        PERCENTAGE = "percentage", "Percentage of Parts"
        RANDOM = "random", "Pure Random"
        FIRST_N_PARTS = "first_n_parts", "First N Parts"
        LAST_N_PARTS = "last_n_parts", "Last N Parts"
        EXACT_COUNT = "exact_count", "Exact Count (No Variance)"

    ruleset = models.ForeignKey(SamplingRuleSet, on_delete=models.CASCADE, related_name="rules")
    rule_type = models.CharField(max_length=32, choices=RuleType.choices)
    value = models.PositiveIntegerField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    created_by = models.ForeignKey("User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    modified_by = models.ForeignKey("User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    # ADD THESE NEW FIELDS:
    algorithm_description = models.TextField(default="SHA-256 hash modulo arithmetic",
                                             help_text="Description of sampling algorithm for audit purposes")
    """Documentation of the sampling algorithm used for compliance."""

    last_validated = models.DateTimeField(null=True, blank=True)
    """Timestamp of last validation for regulatory compliance."""

    @classmethod
    def bulk_create_for_ruleset(cls, *, ruleset, rules, created_by=None):
        instances = [
            cls(ruleset=ruleset, rule_type=rule["rule_type"], value=rule.get("value"), order=rule.get("order", i),
                created_by=created_by, ) for i, rule in enumerate(rules)]
        cls.objects.bulk_create(instances)


class Parts(SecureModel):
    """
    Represents an individual part undergoing a manufacturing process.

    Parts are linked to Orders, Work Orders, and a specific PartType and Step.
    This model tracks a part’s lifecycle status, position in the process chain,
    and is capable of version-safe archiving and step progression.

    Lifecycle transitions and traceability are critical for quality control and compliance audits.
    """

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

    sampling_context = models.JSONField(default=dict, blank=True)
    """Context data for sampling decisions, used by SamplingFallbackApplier."""

    total_rework_count = models.IntegerField(default=0)
    """Total number of times this part has been reworked across all steps."""

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
            self.part_status = PartsStatus.COMPLETED
            self.save()
            return "completed_workorder"

        try:
            next_step = Steps.objects.get(part_type=self.part_type, process=self.step.process,
                                          order=self.step.order + 1)
        except Steps.DoesNotExist:
            raise ValueError("Next step not found for this part.")

        # Mark this part ready
        self.part_status = PartsStatus.READY_FOR_NEXT_STEP
        self.save()

        # Check if all parts at this step are ready
        other_parts_pending = Parts.objects.filter(work_order=self.work_order, part_type=self.part_type,
                                                   step=self.step).exclude(part_status=PartsStatus.READY_FOR_NEXT_STEP)

        if other_parts_pending.exists():
            return "marked_ready"

        # All parts are ready. Check if step allows advancement.
        if not self.step.can_advance_step(work_order=self.work_order, step=self.step):
            return "marked_ready"  # Step not ready due to QA/quarantine/pass rate

        # Bulk-advance all parts
        ready_parts = list(Parts.objects.filter(work_order=self.work_order, part_type=self.part_type, step=self.step,
                                                part_status=PartsStatus.READY_FOR_NEXT_STEP))

        for part in ready_parts:
            part.step = next_step
            part.part_status = PartsStatus.IN_PROGRESS  # Or blank if you use "" for active
            evaluator = SamplingFallbackApplier(part=part)
            result = evaluator.evaluate()
            part.requires_sampling = result.get("requires_sampling", False)
            part.sampling_rule = result.get("rule")
            part.sampling_ruleset = result.get("ruleset")
            part.sampling_context = result.get("context", {})

        Parts.objects.bulk_update(ready_parts,
                                  ["step", "part_status", "requires_sampling", "sampling_rule", "sampling_ruleset",
                                   "sampling_context"])

        return "full_work_order_advanced"

    def has_quality_errors(self):
        """Check if part has any quality errors"""
        return self.error_reports.filter(status='FAIL').exists()

    def get_latest_quality_status(self):
        """Get the most recent quality report status"""
        latest_report = self.error_reports.order_by('-created_at').first()
        return latest_report.status if latest_report else None

    def get_sampling_display_info(self):
        """Get sampling information for display purposes"""
        return {'requires_sampling': self.requires_sampling,
                'sampling_rule_type': self.sampling_rule.rule_type if self.sampling_rule else None,
                'sampling_rule_value': self.sampling_rule.value if self.sampling_rule else None,
                'ruleset_name': self.sampling_ruleset.name if self.sampling_ruleset else None,
                'is_fallback_active': bool(
                    SamplingTriggerState.objects.filter(work_order=self.work_order, step=self.step,
                                                        active=True).exists()) if self.work_order and self.step else False}

    def get_work_order_display_info(self):
        """Get work order information for display"""
        if not self.work_order:
            return None

        return {'erp_id': self.work_order.ERP_id, 'status': self.work_order.workorder_status,
                'quantity': self.work_order.quantity, 'expected_completion': self.work_order.expected_completion}

    def get_sampling_history(self):
        """Get complete sampling history for this part"""
        return {'current_sampling': {'requires_sampling': self.requires_sampling,
                                     'rule': {'id': self.sampling_rule.id, 'rule_type': self.sampling_rule.rule_type,
                                              'value': self.sampling_rule.value,
                                              'order': self.sampling_rule.order} if self.sampling_rule else None,
                                     # ✅ Convert to dict
                                     'ruleset': {'id': self.sampling_ruleset.id, 'name': self.sampling_ruleset.name,
                                                 'version': self.sampling_ruleset.version,
                                                 'active': self.sampling_ruleset.active} if self.sampling_ruleset else None,
                                     # ✅ Convert to dict
                                     'context': self.sampling_context}, 'quality_reports': list(
            self.error_reports.all().values('status', 'created_at', 'sampling_method', 'description')),
                'audit_logs': list(SamplingAuditLog.objects.filter(part=self).values('sampling_decision', 'timestamp',
                                                                                     'ruleset_type')) if 'SamplingAuditLog' in globals() else []}

    @classmethod
    def get_filtered_queryset(cls, user=None, filters=None):
        """Get optimized queryset with common select_related/prefetch_related"""
        qs = cls.objects.select_related('part_type', 'step', 'order', 'work_order', 'sampling_rule',
                                        'sampling_ruleset').prefetch_related('error_reports')

        # Filter to only show customer's orders if user is in 'customer' group
        if user and user.groups.filter(name='customer').exists():
            qs = qs.filter(order__customer=user)

        return qs

    def save(self, *args, **kwargs):
        """Enhanced save method with sampling evaluation"""
        is_new = self.pk is None
        super().save(*args, **kwargs)

        # Evaluate sampling requirements for new parts
        if is_new and self.step and self.part_type and self.work_order:
            self._evaluate_initial_sampling()

    def _evaluate_initial_sampling(self):
        """Evaluate sampling requirements when part is first created"""
        evaluator = SamplingFallbackApplier(part=self)
        result = evaluator.evaluate()

        # Update sampling fields
        self.requires_sampling = result.get("requires_sampling", False)
        self.sampling_rule = result.get("rule")
        self.sampling_ruleset = result.get("ruleset")
        self.sampling_context = result.get("context", {})

        # Save without triggering recursion
        Parts.objects.filter(pk=self.pk).update(requires_sampling=self.requires_sampling,
                                                sampling_rule=self.sampling_rule,
                                                sampling_ruleset=self.sampling_ruleset,
                                                sampling_context=self.sampling_context)

    def __str__(self):
        """
        Returns a human-readable identifier combining ERP ID, Order, and PartType.
        """
        deal_name = getattr(self.order, 'name', 'Unknown Deal') if self.order else 'Unknown Deal'
        part_type_name = getattr(self.part_type, 'name', 'Unknown Part Type') if self.part_type else 'Unknown Part Type'
        return f"{self.ERP_id} {deal_name} {part_type_name}"


class EquipmentType(SecureModel):
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


class Equipments(SecureModel):
    name = models.CharField(max_length=50)
    equipment_type = models.ForeignKey(EquipmentType, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name_plural = 'Equipments'
        verbose_name = 'Equipment'

    def __str__(self):
        return f"{self.name} ({self.equipment_type})" if self.equipment_type else self.name


class QualityErrorsList(SecureModel):
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


class QualityReports(SecureModel):
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

    errors = models.ManyToManyField(QualityErrorsList, blank=True)
    """List of known quality errors that this report corresponds to."""

    sampling_audit_log = models.ForeignKey('SamplingAuditLog', null=True, blank=True, on_delete=models.SET_NULL,
                                           help_text="Links to the sampling decision that triggered this inspection")
    """Link to the sampling audit log that triggered this quality report."""

    class Meta:
        verbose_name_plural = 'Error Reports'
        verbose_name = 'Error Report'

    def __str__(self):
        """
        Returns a summary string indicating which part the report refers to and the date.
        """
        return f"Quality Report for {self.part} on {self.created_at.date()}"

    def save(self, *args, **kwargs):
        """Enhanced save with sampling integration and audit trail"""
        is_new = self.pk is None
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
        if self.part and self.part.requires_sampling:
            # Find the most recent sampling audit log for this part
            audit_log = SamplingAuditLog.objects.filter(part=self.part, sampling_decision=True).order_by(
                '-timestamp').first()

            if audit_log:
                self.sampling_audit_log = audit_log
                self.save(update_fields=['sampling_audit_log'])

    def _trigger_sampling_fallback(self):
        """Trigger fallback sampling for remaining parts"""
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


class ExternalAPIOrderIdentifier(SecureModel):
    """
    Maps HubSpot pipeline stage IDs to human-readable names.

    When HubSpot API returns cryptic stage IDs (e.g., '123456789'),
    this model provides the human-readable name (e.g., 'Qualification').
    Supports tracking which pipeline each stage belongs to and stage ordering.
    """

    stage_name = models.CharField(max_length=100, unique=True)
    """Human-readable stage name (e.g., 'Qualification', 'Closed Won')."""

    API_id = models.CharField(max_length=50)
    """The external system's identifier for the stage (e.g., from HubSpot API)."""

    pipeline_id = models.CharField(max_length=50, null=True, blank=True)
    """HubSpot pipeline ID this stage belongs to."""

    display_order = models.IntegerField(default=0)
    """Order in which this stage appears in the pipeline (for progress tracking)."""

    last_synced_at = models.DateTimeField(null=True, blank=True)
    """When this stage was last synced from HubSpot."""

    class Meta:
        verbose_name = "External API Order Identifier"
        verbose_name_plural = "External API Order Identifiers"
        ordering = ['pipeline_id', 'display_order']
        indexes = [
            models.Index(fields=['pipeline_id', 'display_order']),
            models.Index(fields=['API_id']),
        ]

    def __str__(self):
        """
        Returns a string that clearly represents the stage.
        """
        return self.stage_name


class HubSpotSyncLog(models.Model):
    """
    Tracks HubSpot sync operations for debugging and monitoring.

    Records each sync attempt with timing, counts, and error details.
    Useful for audit trails and identifying sync issues.
    """

    SYNC_TYPE_CHOICES = [
        ('full', 'Full Sync'),
        ('incremental', 'Incremental Sync'),
        ('single', 'Single Deal Sync'),
    ]

    STATUS_CHOICES = [
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    sync_type = models.CharField(max_length=20, choices=SYNC_TYPE_CHOICES, default='full')
    """Type of sync operation performed."""

    started_at = models.DateTimeField(auto_now_add=True)
    """When the sync operation began."""

    completed_at = models.DateTimeField(null=True, blank=True)
    """When the sync operation finished (null if still running)."""

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running')
    """Current status of the sync operation."""

    deals_processed = models.IntegerField(default=0)
    """Total number of deals processed during this sync."""

    deals_created = models.IntegerField(default=0)
    """Number of new orders created from HubSpot deals."""

    deals_updated = models.IntegerField(default=0)
    """Number of existing orders updated from HubSpot deals."""

    error_message = models.TextField(null=True, blank=True)
    """Error details if the sync failed."""

    class Meta:
        verbose_name = "HubSpot Sync Log"
        verbose_name_plural = "HubSpot Sync Logs"
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['-started_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        duration = ""
        if self.completed_at:
            delta = self.completed_at - self.started_at
            duration = f" ({delta.total_seconds():.1f}s)"
        return f"{self.get_sync_type_display()} - {self.get_status_display()} at {self.started_at}{duration}"

    @property
    def duration(self):
        """Calculate sync duration in seconds."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class ArchiveReason(SecureModel):
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


class StepTransitionLog(SecureModel):
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


class SamplingTriggerState(SecureModel):
    ruleset = models.ForeignKey(SamplingRuleSet, on_delete=models.CASCADE)
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE)
    step = models.ForeignKey(Steps, on_delete=models.CASCADE)
    active = models.BooleanField(default=True)

    triggered_by = models.ForeignKey(QualityReports, null=True, blank=True, on_delete=models.SET_NULL)
    triggered_at = models.DateTimeField(auto_now_add=True)

    success_count = models.PositiveIntegerField(default=0)
    fail_count = models.PositiveIntegerField(default=0)

    parts_inspected = models.ManyToManyField("Parts", blank=True)

    # Email notification fields
    notification_sent = models.BooleanField(default=False)
    notification_sent_at = models.DateTimeField(null=True, blank=True)
    notified_users = models.ManyToManyField(User, blank=True, related_name='sampling_notifications')

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


class QaApproval(SecureModel):
    step = models.ForeignKey(Steps, related_name='qa_approvals', on_delete=models.PROTECT)
    work_order = models.ForeignKey(WorkOrder, related_name='qa_approvals', on_delete=models.PROTECT)
    qa_staff = models.ForeignKey(User, related_name='qa_approvals', on_delete=models.PROTECT)


class QuarantineDisposition(SecureModel):
    """Minimal disposition for failed quality reports"""

    STATE_CHOICES = [('OPEN', 'Open'), ('IN_PROGRESS', 'In Progress'), ('CLOSED', 'Closed'), ]

    DISPOSITION_TYPES = [('REWORK', 'Rework'), ('SCRAP', 'Scrap'), ('USE_AS_IS', 'Use As Is'),
        ('RETURN_TO_SUPPLIER', 'Return to Supplier'), ]

    # Basic fields
    disposition_number = models.CharField(max_length=20, unique=True, editable=False)
    current_state = models.CharField(max_length=15, choices=STATE_CHOICES, default='OPEN')
    disposition_type = models.CharField(max_length=20, choices=DISPOSITION_TYPES, blank=True)

    # QA workflow
    assigned_to = models.ForeignKey(User, on_delete=models.PROTECT, related_name='assigned_dispositions', null=True,
                                    blank=True)
    description = models.TextField(blank=True)
    resolution_notes = models.TextField(blank=True)

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

    def __str__(self):
        return f"{self.disposition_number} - {self.get_current_state_display()}"

    def save(self, *args, **kwargs):
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

        # Auto-transition from OPEN to IN_PROGRESS when disposition type is set
        if self.disposition_type and self.current_state == 'OPEN':
            self.current_state = 'IN_PROGRESS'

        super().save(*args, **kwargs)

        # Update part status when disposition type changes or state changes
        if (old_disposition_type != self.disposition_type or old_state != self.current_state) and self.part:
            self._update_part_status()

    def _generate_disposition_number(self):
        year = timezone.now().year
        latest = QuarantineDisposition.objects.filter(disposition_number__startswith=f'DISP-{year}-').order_by(
            'disposition_number').last()

        next_num = 1
        if latest:
            last_num = int(latest.disposition_number.split('-')[-1])
            next_num = last_num + 1

        return f'DISP-{year}-{next_num:06d}'

    def complete_resolution(self, completed_by_user):
        """Mark resolution as completed and close disposition if appropriate"""
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
        if not self.part or not self.disposition_type:
            return

        # Only update if disposition is being implemented/closed
        if self.current_state not in ['IN_PROGRESS', 'CLOSED']:
            return

        # Map disposition types to part statuses (QMS standard workflow)
        status_mapping = {'REWORK': PartsStatus.REWORK_NEEDED, 'SCRAP': PartsStatus.SCRAPPED,
            'USE_AS_IS': PartsStatus.READY_FOR_NEXT_STEP,  # QA approved, ready to advance
            'RETURN_TO_SUPPLIER': PartsStatus.CANCELLED, }

        new_status = status_mapping.get(self.disposition_type)

        if new_status and self.part.part_status != new_status:
            self.part.part_status = new_status

            # Increment rework counter if rework disposition
            if self.disposition_type == 'REWORK':
                self.part.total_rework_count += 1

            self.part.save(update_fields=['part_status', 'total_rework_count'])

    def can_be_completed(self):
        """Check if disposition is ready to be marked as completed"""
        return (self.disposition_type and  # Must have a disposition decision
                self.current_state in ['OPEN', 'IN_PROGRESS'] and  # Must be active
                not self.resolution_completed  # Not already completed
        )

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


class SamplingAuditLog(SecureModel):
    """
    Comprehensive audit trail for sampling decisions.
    Logs which rule was applied to which part and whether it triggered sampling.
    """
    part = models.ForeignKey(Parts, on_delete=models.CASCADE)
    rule = models.ForeignKey(SamplingRule, on_delete=models.CASCADE)
    sampling_decision = models.BooleanField()
    timestamp = models.DateTimeField(auto_now_add=True)
    ruleset_type = models.CharField(max_length=20,
                                    choices=[('PRIMARY', 'Primary Ruleset'), ('FALLBACK', 'Fallback Ruleset')])

    class Meta:
        indexes = [models.Index(fields=['part', 'timestamp']), models.Index(fields=['rule', 'sampling_decision']), ]
        verbose_name = 'Sampling Audit Log'
        verbose_name_plural = 'Sampling Audit Logs'

    def __str__(self):
        return f"Sampling decision for {self.part} at {self.timestamp}"


class SamplingAnalytics(SecureModel):
    """Track sampling effectiveness and compliance metrics"""
    ruleset = models.ForeignKey(SamplingRuleSet, on_delete=models.CASCADE)
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE)

    parts_sampled = models.PositiveIntegerField(default=0)
    parts_total = models.PositiveIntegerField(default=0)
    defects_found = models.PositiveIntegerField(default=0)

    actual_sampling_rate = models.FloatField()
    target_sampling_rate = models.FloatField()
    variance = models.FloatField()  # Difference between actual and target

    class Meta:
        unique_together = ('ruleset', 'work_order')
        verbose_name = 'Sampling Analytics'
        verbose_name_plural = 'Sampling Analytics'

    @property
    def sampling_effectiveness(self):
        """Defects found per 100 sampled parts"""
        return (self.defects_found / self.parts_sampled * 100) if self.parts_sampled > 0 else 0

    @property
    def is_compliant(self):
        """Whether sampling rate is within acceptable variance"""
        return abs(self.variance) < 0.5  # Within 0.5%

    def __str__(self):
        return f"Analytics for {self.ruleset} - WO {self.work_order.ERP_id}"


# TODO: See about how to get classifications to inherit the classification of the related document
class DocChunk(models.Model):
    doc = models.ForeignKey('Tracker.Documents', on_delete=models.CASCADE, related_name='chunks')
    embedding = VectorField(dimensions=settings.AI_EMBED_DIM)  # uses settings
    preview_text = models.TextField(blank=True)
    full_text = models.TextField(blank=True)
    span_meta = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'doc_chunks'
        indexes = [models.Index(fields=['doc'])]

class ThreeDModel(SecureModel):
    """3D model files for heatmap visualization"""
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to='models/')
    part_type = models.ForeignKey('PartTypes', on_delete=models.CASCADE, related_name='three_d_models', null=True, blank=True)
    step = models.ForeignKey('Steps', on_delete=models.CASCADE, related_name='three_d_models', null=True, blank=True,
                             help_text="Optional: Link to specific step if this shows intermediate state")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_type = models.CharField(max_length=50, help_text="e.g., glb, gltf, obj")

    class Meta:
        verbose_name = '3D Model'
        verbose_name_plural = '3D Models'
        unique_together = [['part_type', 'step']]  # One model per part_type+step combination

    def __str__(self):
        return f"{self.name} ({self.file_type})"


class HeatMapAnnotations(SecureModel):
    """User-placed annotations on 3D models for heatmap visualization"""
    model = models.ForeignKey(ThreeDModel, on_delete=models.CASCADE, related_name='annotations')
    part = models.ForeignKey('Parts', on_delete=models.CASCADE, related_name='heatmap_annotations')

    # 3D position data (x, y, z coordinates)
    position_x = models.FloatField()
    position_y = models.FloatField()
    position_z = models.FloatField()

    # Measurement/defect data
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

    # Metadata
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey('Tracker.User', on_delete=models.SET_NULL, null=True, related_name='heatmap_annotations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Heatmap Annotation'
        verbose_name_plural = 'Heatmap Annotations'
        indexes = [
            models.Index(fields=['model', 'part']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Annotation on {self.model.name} for {self.part} at ({self.position_x}, {self.position_y}, {self.position_z})"


class NotificationTask(models.Model):
    """
    Unified notification task supporting both recurring (fixed interval)
    and escalating (deadline-based) notifications.

    Supports multiple channels (email, in-app, SMS, etc.) via simple channel_type field.

    Examples:
    - Weekly order reports: interval_type='fixed', day_of_week=4, time='15:00', interval_weeks=1
    - CAPA reminders: interval_type='deadline_based', deadline=due_date, escalation_tiers=[...]
    """

    # Notification types (hardcoded for now, can move to separate table later if needed)
    NOTIFICATION_TYPES = [
        ('WEEKLY_REPORT', 'Weekly Order Report'),
        ('CAPA_REMINDER', 'CAPA Reminder'),
    ]

    # Interval types
    INTERVAL_TYPES = [
        ('fixed', 'Fixed Interval'),
        ('deadline_based', 'Deadline Based'),
    ]

    # Notification status
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    # Channel types (email only for now, but structured for extension)
    CHANNEL_TYPES = [
        ('email', 'Email'),
        ('in_app', 'In-App Notification'),
        ('sms', 'SMS'),
    ]

    # Core fields
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notification_tasks')
    channel_type = models.CharField(max_length=20, choices=CHANNEL_TYPES, default='email')
    interval_type = models.CharField(max_length=20, choices=INTERVAL_TYPES)

    # Fixed interval fields (for recurring notifications)
    day_of_week = models.IntegerField(null=True, blank=True, help_text="0=Monday, 6=Sunday")
    time = models.TimeField(null=True, blank=True, help_text="Time in UTC")
    interval_weeks = models.IntegerField(null=True, blank=True, help_text="Number of weeks between sends")

    # Deadline-based fields (for escalating notifications)
    deadline = models.DateTimeField(null=True, blank=True, help_text="Deadline for escalation calculation")
    escalation_tiers = models.JSONField(
        null=True,
        blank=True,
        help_text="List of [threshold_days, interval_days] tuples. Example: [[28, 28], [14, 7], [0, 3.5], [-999, 1]]"
    )

    # State tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    attempt_count = models.IntegerField(default=0)
    last_sent_at = models.DateTimeField(null=True, blank=True)
    next_send_at = models.DateTimeField(db_index=True, help_text="When this notification should be sent (UTC)")
    max_attempts = models.IntegerField(null=True, blank=True, help_text="Max sends before stopping. Null = infinite")

    # Related object (optional, for context)
    related_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    related_object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey('related_content_type', 'related_object_id')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Notification Task'
        verbose_name_plural = 'Notification Tasks'
        indexes = [
            models.Index(fields=['recipient', 'notification_type', 'channel_type']),
            models.Index(fields=['status', 'next_send_at']),
            models.Index(fields=['related_content_type', 'related_object_id']),
        ]
        ordering = ['next_send_at']

    def __str__(self):
        return f"{self.get_notification_type_display()} to {self.recipient.email} via {self.channel_type}"

    def calculate_next_send(self):
        """
        Calculate when this notification should be sent next.
        Returns a datetime object.
        """
        from datetime import timedelta

        base_time = self.last_sent_at or self.created_at

        if self.interval_type == 'fixed':
            # Fixed interval with specific day/time
            if self.last_sent_at:
                # Add interval_weeks to last send
                next_date = self.last_sent_at.date() + timedelta(weeks=self.interval_weeks)
            else:
                # First occurrence - find next target day
                now = timezone.now()
                days_ahead = (self.day_of_week - now.weekday()) % 7
                if days_ahead == 0 and now.time() > self.time:
                    days_ahead = 7
                next_date = (now + timedelta(days=days_ahead)).date()

            # Combine date with time
            from datetime import datetime
            import pytz
            next_dt = datetime.combine(next_date, self.time)
            # Make timezone aware in UTC
            return timezone.make_aware(next_dt, pytz.UTC)

        elif self.interval_type == 'deadline_based':
            # Deadline-based: use escalation tiers
            interval_days = self._get_current_interval()
            return base_time + timedelta(days=interval_days)

        else:
            raise ValueError(f"Unknown interval_type: {self.interval_type}")

    def _get_current_interval(self):
        """Get the interval (in days) until next send based on escalation tier."""
        if self.interval_type == 'fixed':
            return self.interval_weeks * 7

        elif self.interval_type == 'deadline_based':
            tier = self._find_matching_tier()
            return tier[1] if tier else 1  # Default to 1 day if no tier found

        else:
            raise ValueError(f"Unknown interval_type: {self.interval_type}")

    def _find_matching_tier(self):
        """Find the matching escalation tier based on days until deadline."""
        if self.interval_type != 'deadline_based' or not self.escalation_tiers or not self.deadline:
            return None

        base_time = self.last_sent_at or self.created_at
        days_until = (self.deadline - base_time).days

        # Find first matching tier
        for tier in self.escalation_tiers:
            if days_until > tier[0]:
                return tier

        # Fallback to last tier
        return self.escalation_tiers[-1] if self.escalation_tiers else None

    def should_send(self):
        """Check if this notification should be sent now."""
        if self.status != 'pending':
            return False

        if timezone.now() < self.next_send_at:
            return False

        return True

    def mark_sent(self, success=True, sent_at=None):
        """Update state after send attempt."""
        self.attempt_count += 1
        self.last_sent_at = sent_at or self.next_send_at

        if success:
            self.status = 'sent'

            # Check if we should continue sending
            if self.max_attempts is None or self.attempt_count < self.max_attempts:
                self.status = 'pending'
                self.next_send_at = self.calculate_next_send()
        else:
            self.status = 'failed'

        self.save()

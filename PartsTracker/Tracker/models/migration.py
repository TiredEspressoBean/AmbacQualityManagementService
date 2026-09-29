"""A load of history from another system at go-live (see services.core.migration_import).

History brought in at go-live wasn't captured here. A MigrationBatch is the controlled
record of one load — what, from which system, who loaded it, when, how many rows — and
of its ONE verification sign-off (ISO 9001 7.5 / AS9100: verify the migration, not each
row). Migrated rows point at their batch and carry a `source_reference` to their
original evidence.
"""
from django.conf import settings
from django.db import models

from .core import SecureModel


class MigrationBatchKind(models.TextChoices):
    TRAINING_RECORDS = 'TRAINING_RECORDS', 'Training records'
    MATERIAL_LOTS = 'MATERIAL_LOTS', 'Material lots'


class MigrationBatch(SecureModel):
    kind = models.CharField(max_length=20, choices=MigrationBatchKind.choices)
    source_system = models.CharField(
        max_length=200,
        help_text="The system this history came from (e.g. 'Legacy HR — Workday').")
    notes = models.TextField(blank=True)
    imported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='migration_batches')
    row_count = models.PositiveIntegerField(default=0)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT,
        related_name='verified_migration_batches',
        help_text="Who checked the load against the source (quantities against the go-live "
                  "count, a sample of records against the originals). Not the loader.")
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Migration batch'
        verbose_name_plural = 'Migration batches'

    def __str__(self):
        return f"{self.get_kind_display()} from {self.source_system} ({self.row_count})"

    @property
    def is_verified(self) -> bool:
        return self.verified_at is not None

"""Shift notes — human-authored shop-floor handoff messages.

Distinct from the notification system (machine-generated, immutable, engine-
written): a shift note is authored by a person, aimed at an audience (role +
optional work order), carries an effective window, and is acknowledged by its
readers. The notification engine only *alerts* that a note exists (the
`shift_note.published` event); the note itself lives here.

Edit model: a note is editable until the first acknowledgment, then locked
(`is_locked`) so "what the reader saw" stays honest. Retract via `void()`
(VoidableModel) remains available at any time.
"""
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models

from .core import SecureModel
from .qms import VoidableModel


class ShiftNotePriority(models.TextChoices):
    NORMAL = "NORMAL", "Normal"
    HIGH = "HIGH", "High"


class ShiftNote(SecureModel, VoidableModel):
    """A human-authored handoff note targeted at a floor audience."""

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="authored_shift_notes",
    )
    body = models.TextField()
    # Audience: tenant group names this note targets (empty = everyone on the
    # floor) plus an optional work-order scope. Station-level targeting waits
    # for work-centers to be mapped (design doc rung 3).
    audience_roles = ArrayField(
        models.CharField(max_length=100),
        default=list,
        blank=True,
        help_text="Tenant group names targeted; empty = all floor staff.",
    )
    work_order = models.ForeignKey(
        "Tracker.WorkOrder",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="shift_notes",
    )
    priority = models.CharField(
        max_length=10,
        choices=ShiftNotePriority.choices,
        default=ShiftNotePriority.NORMAL,
    )
    # Two kinds: informational (dismiss-on-ack) vs acknowledgment-required
    # (compulsory — the operator sees a prominent "must acknowledge" call, and
    # the author gets a who-saw-it roster for the audit trail).
    acknowledgment_required = models.BooleanField(default=False)
    # Validity window — a shift note goes stale ("before lunch"), unlike a
    # point-in-time notification. Null bound = open-ended.
    effective_from = models.DateTimeField(null=True, blank=True)
    effective_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "is_voided"]),
        ]

    def __str__(self):
        who = self.author.get_full_name() if self.author else "unknown"
        return f"Shift note by {who} ({self.created_at:%Y-%m-%d %H:%M})"

    @property
    def is_locked(self) -> bool:
        """Editing is locked once anyone has acknowledged the note (preserves
        'what the reader saw'). Retract via void() stays available."""
        return self.acknowledgments.exists()


class ShiftNoteAck(SecureModel):
    """One reader's acknowledgment of a shift note — the handoff receipt
    ("who saw it at shift change"), distinct from a notification's mark-read."""

    note = models.ForeignKey(
        ShiftNote,
        on_delete=models.CASCADE,
        related_name="acknowledgments",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="shift_note_acks",
    )
    acknowledged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["note", "user"], name="uniq_shiftnote_ack_per_user"
            ),
        ]

    def __str__(self):
        return f"Ack of {self.note_id} by {self.user_id}"

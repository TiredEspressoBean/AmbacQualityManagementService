"""
Training Record adapter.

A Training Record report is the per-employee training history document
required by ISO 9001 clause 7.2 (Competence). It demonstrates that
training was effective — evidence of competence, not merely attendance.

The PDF covers:
- Header: employee name, email/ID, report generation date
- Summary bar: total trainings, current, expired, no-expiry counts
- Training table: topic, completed date, expiry date, trainer, status badge
- Signature block: Employee (attendance), Trainer (delivery), Supervisor (competency)

Defense-in-depth: every ORM query in build_context() filters by
tenant explicitly, in addition to the param serializer's upstream
check.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel
from rest_framework import serializers

from Tracker.reports.adapters.base import ReportAdapter


# ---------------------------------------------------------------------------
# Pydantic context model
# ---------------------------------------------------------------------------


class TrainingRecordEntry(BaseModel):
    """One training record row in the table."""

    topic: str                        # TrainingType.name
    completed_date: date
    expires_date: Optional[date]      # None = never expires
    trainer: str                      # trainer full name / email, or empty string
    status: str                       # CURRENT / EXPIRED / EXPIRING_SOON
    notes: str


class TrainingRecordContext(BaseModel):
    """Top-level shape passed to the training_record.typ template."""

    # ---- Employee identity ----
    employee_name: str
    employee_email: str
    employee_id: str                  # UUID as string, used as document reference

    # ---- Training records ----
    records: list[TrainingRecordEntry]

    # ---- Summary counts ----
    total_count: int
    current_count: int
    expired_count: int
    no_expiry_count: int

    # ---- Document metadata ----
    tenant_name: str
    generated_date: str               # ISO date string, formatted in template


# ---------------------------------------------------------------------------
# DRF param serializer
# ---------------------------------------------------------------------------


class TrainingRecordParamsSerializer(serializers.Serializer):
    """
    Accepts {"user_id": <uuid>} and confirms the user exists in the
    requesting user's tenant.

    The user PKs are UUIDs (SecureModel default), so user_id is a
    UUIDField, not IntegerField.
    """

    user_id = serializers.UUIDField()

    def validate_user_id(self, value):
        from Tracker.models import User

        user = self.context.get("user") or (
            getattr(self.context.get("request"), "user", None)
        )
        if user is None:
            raise serializers.ValidationError("Authenticated user required.")

        tenant = getattr(user, "_current_tenant", None) or getattr(user, "tenant", None)
        if tenant is None:
            raise serializers.ValidationError("No tenant context on user.")

        # tenant-safe: explicit tenant filter
        exists = User.objects.filter(
            id=value, tenant=tenant
        ).exists()
        if not exists:
            raise serializers.ValidationError(
                f"User {value} not found in this tenant."
            )
        return value


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user_display(user) -> str:
    """Render a User FK as 'Full Name' or fallback to email/username."""
    if user is None:
        return ""
    full = user.get_full_name() if hasattr(user, "get_full_name") else ""
    return full.strip() or getattr(user, "email", None) or getattr(user, "username", "") or ""


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class TrainingRecordAdapter(ReportAdapter):
    """Renders a per-employee training history as a Training Record PDF."""

    name = "training_record"
    title = "Training Record"
    template_path = "training_record.typ"
    context_model_class = TrainingRecordContext
    param_serializer_class = TrainingRecordParamsSerializer

    def build_context(self, validated_params, user, tenant) -> TrainingRecordContext:
        from Tracker.models import User
        from Tracker.models.qms import TrainingRecord

        # tenant-safe: explicit tenant filter (defense-in-depth)
        employee = (
            User.objects
            .filter(id=validated_params["user_id"], tenant=tenant)
            .get()
        )

        records_qs = (
            TrainingRecord.objects
            .filter(tenant=tenant, user=employee)
            .select_related("training_type", "trainer")
            .order_by("-completed_date")
        )

        entries: list[TrainingRecordEntry] = []
        total_count = 0
        current_count = 0
        expired_count = 0
        no_expiry_count = 0

        for rec in records_qs:
            total_count += 1
            status = rec.status  # CURRENT / EXPIRED / EXPIRING_SOON (property)

            if rec.expires_date is None:
                no_expiry_count += 1
            elif status == "EXPIRED":
                expired_count += 1
            else:
                current_count += 1

            entries.append(TrainingRecordEntry(
                topic=rec.training_type.name,
                completed_date=rec.completed_date,
                expires_date=rec.expires_date,
                trainer=_user_display(rec.trainer),
                status=status,
                notes=rec.notes or "",
            ))

        return TrainingRecordContext(
            employee_name=_user_display(employee) or employee.email,
            employee_email=employee.email,
            employee_id=str(employee.id),
            records=entries,
            total_count=total_count,
            current_count=current_count,
            expired_count=expired_count,
            no_expiry_count=no_expiry_count,
            tenant_name=tenant.name,
            generated_date=date.today().isoformat(),
        )

    def get_filename(self, validated_params) -> str:
        return f"training_record_{validated_params.get('user_id', 'unknown')}.pdf"

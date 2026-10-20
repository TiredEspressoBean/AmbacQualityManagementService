"""
PDF Generator — adapter dispatch.

The entry point for all PDF generation. Dispatches a report_type +
params pair to the matching ReportAdapter, runs its param validation,
calls its build_context(), and passes the result to typst_generator.

HOW TO ADD A NEW REPORT TYPE
============================

1. Create a Pydantic context model (the shape the Typst template reads).
2. Create a DRF param serializer (validates incoming IDs are in tenant).
3. Create a `ReportAdapter` subclass in `Tracker/reports/adapters/`:
   - Set `name`, `title`, `template_path`, `context_model_class`,
     `param_serializer_class`
   - Implement `build_context()` — query the ORM, return a Pydantic
     instance of the context model
4. Add the dotted path to REPORT_ADAPTERS in
   `Tracker/reports/services/registry.py`
5. Write a test subclassing `ReportAdapterTestMixin`
   (see `Tracker/reports/tests/base.py`)
6. Create the Typst template at `templates/<name>.typ`

That's it. No changes to PdfGenerator, no changes to the viewset,
no changes to the Celery task.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from Tracker.reports.adapters.base import ReportAdapter
from Tracker.reports.services.registry import (
    UnknownReportError,
    get_adapter,
    get_all_adapters,
)
from Tracker.reports.services.typst_generator import generate_typst_pdf

logger = logging.getLogger(__name__)


# Formats Typst can place, and a cap so a stray full-resolution scan doesn't bloat
# every document's context (the logo travels as a JSON int array).
_LOGO_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".svg")
_LOGO_MAX_BYTES = 1_000_000


# An ISO datetime that carries its offset — what pydantic emits for an aware datetime.
# Naive datetimes and plain dates are left alone: there is no zone to convert from.
_AWARE_ISO = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})$")


def localize_timestamps(value, tenant):
    """Every aware ISO timestamp in a report context, moved onto the plant's clock."""
    from Tracker.services.core.clock import plant_tz

    if tenant is None:
        return value
    tz = plant_tz(tenant)

    def walk(v):
        if isinstance(v, dict):
            return {k: walk(x) for k, x in v.items()}
        if isinstance(v, list):
            return [walk(x) for x in v]
        if isinstance(v, str) and _AWARE_ISO.match(v):
            return datetime.fromisoformat(v.replace("Z", "+00:00")).astimezone(tz).isoformat()
        return v

    return walk(value)


def document_meta(tenant) -> dict:
    """What every document's frame prints: the organisation, its logo, and when the
    copy was printed (in plant time)."""
    from Tracker.services.core.clock import tenant_now

    if tenant is None:
        return {}
    return {
        "org_name": tenant.name,
        "logo": _logo_bytes(tenant),
        "printed_at": tenant_now(tenant).strftime("%Y-%m-%d %H:%M %Z").strip(),
    }


def _logo_bytes(tenant) -> list[int] | None:
    logo = getattr(tenant, "logo", None)
    if not logo or not logo.name.lower().endswith(_LOGO_EXTENSIONS):
        return None
    try:
        with logo.open("rb") as f:
            data = f.read(_LOGO_MAX_BYTES + 1)
    except (OSError, ValueError):
        # A missing file shouldn't stop a document printing; it prints unbranded.
        logger.warning("Tenant %s logo %r could not be read", tenant.pk, logo.name)
        return None
    if len(data) > _LOGO_MAX_BYTES:
        logger.warning("Tenant %s logo is over %d bytes; printing unbranded",
                       tenant.pk, _LOGO_MAX_BYTES)
        return None
    return list(data)


class ReportParamError(ValueError):
    """Raised when params fail the adapter's serializer validation."""

    def __init__(self, message: str, errors: Any = None):
        super().__init__(message)
        self.errors = errors


class PdfGenerator:
    """
    Dispatches PDF generation requests to the registered adapter.

    Instances are stateless — one PdfGenerator can handle many
    sequential requests without init cost. Callers may construct a
    new instance per request or share one; both are safe.
    """

    # ---- Public API -----------------------------------------------------

    def generate(
        self,
        report_type: str,
        params: dict,
        user=None,
        tenant=None,
    ) -> bytes:
        """
        Compile a PDF for the given report_type.

        Args:
            report_type: Registry key (e.g. "cert_of_conformance").
            params: Raw params from the client (URL or request body).
            user: Authenticated Django user. Required for adapters
                whose param serializer validates against user.tenant.
                May be None when called from management commands or
                tests that don't exercise tenant scoping.
            tenant: Explicit tenant override. If None, falls back to
                user.tenant.

        Returns:
            PDF bytes (starts with b"%PDF").

        Raises:
            UnknownReportError: report_type not in the registry.
            ReportParamError: params failed the adapter's serializer.
            RuntimeError: Typst compile failed (template bug, syntax
                error, missing field in context, etc.)
        """
        adapter = get_adapter(report_type)

        validated_params = self._validate_params(adapter, params, user)

        if tenant is None and user is not None:
            tenant = getattr(user, "tenant", None)

        context_model = adapter.build_context(validated_params, user, tenant)

        context_dict = context_model.model_dump(mode="json")
        # Aware datetimes serialise as UTC ISO strings; a document is read on the plant
        # floor, so they print in plant time — the same clock as the footer's stamp.
        context_dict = localize_timestamps(context_dict, tenant)
        # The document frame reads branding and the print stamp from here, so no
        # adapter has to carry them (templates/_common/frame.typ).
        context_dict["_meta"] = document_meta(tenant)

        return generate_typst_pdf(adapter.template_path, context_dict)

    def get_filename(self, report_type: str, params: dict) -> str:
        """
        Return the filename for the given report + params.

        Used by callers (email task, sync download) after generate()
        has succeeded. Filename is computed from params directly, so
        this call does not re-run ORM queries or template compilation.
        """
        adapter = get_adapter(report_type)
        return adapter.get_filename(params)

    def get_title(self, report_type: str) -> str:
        """Human-readable title for the report, used in email subjects."""
        return get_adapter(report_type).title

    # ---- Convenience --------------------------------------------------

    def list_available_types(self) -> list[dict]:
        """
        Return a serializable list of available reports, for the
        `/api/reports/types/` endpoint and debugging.
        """
        return [
            {
                "name": a.name,
                "title": a.title,
                "template": a.template_path,
            }
            for a in get_all_adapters()
        ]

    # ---- Internal -----------------------------------------------------

    def _validate_params(
        self,
        adapter: ReportAdapter,
        params: dict,
        user,
    ) -> dict:
        """
        Run the adapter's param serializer and return validated_data.

        Raises ReportParamError with structured errors on failure so
        the viewset layer can return a 400 with useful messages.
        """
        serializer = adapter.param_serializer_class(
            data=params or {},
            context={"user": user, "request": _FakeRequest(user)},
        )
        if not serializer.is_valid():
            raise ReportParamError(
                f"Invalid params for report_type={adapter.name!r}",
                errors=serializer.errors,
            )
        return dict(serializer.validated_data)


class _FakeRequest:
    """
    Minimal stand-in for a DRF Request, used when PdfGenerator is
    called outside a view context (Celery task, management command).
    DRF serializers commonly read `context['request'].user`, so we
    expose .user to satisfy them.
    """
    def __init__(self, user):
        self.user = user

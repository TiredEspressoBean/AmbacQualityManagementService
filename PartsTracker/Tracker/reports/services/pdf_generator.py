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
from typing import Any

from Tracker.reports.adapters.base import ReportAdapter
from Tracker.reports.services.registry import (
    UnknownReportError,
    get_adapter,
    get_all_adapters,
)
from Tracker.reports.services.typst_generator import generate_typst_pdf

logger = logging.getLogger(__name__)


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

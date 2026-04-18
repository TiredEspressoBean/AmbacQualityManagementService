"""
Report Generation ViewSets

API endpoints for generating and managing Typst-based PDF reports.

Endpoints:
    POST /api/reports/generate/   — queue async generation, email result
    POST /api/reports/download/   — generate synchronously, return PDF bytes
    GET  /api/reports/history/    — list the user's generated reports
    GET  /api/reports/types/      — list registered report types
"""
from __future__ import annotations

import concurrent.futures
import logging

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema, extend_schema_field, inline_serializer
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from Tracker.models import GeneratedReport
from Tracker.reports.services.pdf_generator import (
    PdfGenerator,
    ReportParamError,
)
from Tracker.reports.services.registry import (
    UnknownReportError,
    get_all_adapters,
)
from Tracker.reports.tasks import generate_and_email_report

logger = logging.getLogger(__name__)


# Timeout for synchronous /download/ compiles. Matches the soft
# time limit on RetryableTypstTask so both paths fail uniformly.
SYNC_COMPILE_TIMEOUT_SECONDS = 30


# ---------------------------------------------------------------------------
# Request/response serializers
# ---------------------------------------------------------------------------


class GenerateReportSerializer(serializers.Serializer):
    """
    Top-level shape: {report_type, params}.

    Per-adapter param validation happens inside PdfGenerator via the
    adapter's `param_serializer_class`. We do NOT repeat that here —
    this serializer just ensures the top-level envelope is well-formed.
    """

    report_type = serializers.CharField(
        help_text="Registry key of the report to generate (e.g. 'cert_of_conformance')."
    )
    params = serializers.DictField(
        required=False,
        default=dict,
        help_text="Parameters specific to the report_type. Validated by the adapter.",
    )


class GeneratedReportSerializer(serializers.ModelSerializer):
    """Serializer for GeneratedReport audit records."""

    generated_by_name = serializers.SerializerMethodField()
    document_url = serializers.SerializerMethodField()

    class Meta:
        model = GeneratedReport
        fields = [
            "id",
            "report_type",
            "generated_by",
            "generated_by_name",
            "generated_at",
            "parameters",
            "document",
            "document_url",
            "emailed_to",
            "emailed_at",
            "status",
            "error_message",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_generated_by_name(self, obj):
        if obj.generated_by:
            return obj.generated_by.get_full_name()
        return None

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_document_url(self, obj):
        if obj.document and obj.document.file:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.document.file.url)
            return obj.document.file.url
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _error_response(message: str, status_code: int, **extra) -> Response:
    """
    Return a JSON error response. Verbosity is gated on settings.DEBUG:
    in dev the full message is returned; in production the message is
    replaced with a generic string but the full details are logged.
    """
    if settings.DEBUG:
        payload = {"error": message, **extra}
    else:
        payload = {"error": "PDF generation failed. Check server logs for details."}
    return Response(payload, status=status_code)


# ---------------------------------------------------------------------------
# ViewSet
# ---------------------------------------------------------------------------


class ReportViewSet(viewsets.GenericViewSet):
    """
    API surface for Typst-based PDF reports.
    """

    permission_classes = [IsAuthenticated]
    queryset = GeneratedReport.objects.none()  # drf-spectacular schema

    # ---- Async path ------------------------------------------------------

    @extend_schema(
        request=GenerateReportSerializer,
        responses={202: inline_serializer(
            name="GenerateReportResponse",
            fields={
                "message": serializers.CharField(),
                "task_id": serializers.CharField(),
            },
        )},
    )
    @action(detail=False, methods=["post"], url_path="generate")
    def generate(self, request):
        """
        Queue a Celery task to generate the report and email it to the
        requesting user. Responds 202 immediately.
        """
        envelope = GenerateReportSerializer(data=request.data)
        envelope.is_valid(raise_exception=True)

        report_type = envelope.validated_data["report_type"]
        params = envelope.validated_data.get("params") or {}

        # Dispatch after commit so a rolled-back request doesn't leave an
        # orphan task. ATOMIC_REQUESTS wraps every request in a transaction.
        user_id = request.user.id
        user_email = request.user.email
        tenant_id = str(request.user.tenant_id) if request.user.tenant_id else None
        transaction.on_commit(lambda: generate_and_email_report.delay(
            user_id=user_id,
            user_email=user_email,
            report_type=report_type,
            params=params,
            tenant_id=tenant_id,
        ))

        return Response(
            {
                "message": "Report is being generated. You'll receive an email shortly.",
            },
            status=status.HTTP_202_ACCEPTED,
        )

    # ---- Sync path -------------------------------------------------------

    @extend_schema(request=GenerateReportSerializer, responses={200: bytes})
    @action(detail=False, methods=["post"], url_path="download")
    def download(self, request):
        """
        Compile synchronously and return PDF bytes as an attachment.

        A hard timeout is enforced via concurrent.futures. If the
        compile exceeds SYNC_COMPILE_TIMEOUT_SECONDS, the worker thread
        is abandoned (Python cannot kill threads forcibly) — the request
        returns 504 and memory is reclaimed on gunicorn worker rotation.
        """
        envelope = GenerateReportSerializer(data=request.data)
        envelope.is_valid(raise_exception=True)

        report_type = envelope.validated_data["report_type"]
        params = envelope.validated_data.get("params") or {}

        generator = PdfGenerator()

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(
                    generator.generate,
                    report_type, params, request.user,
                )
                pdf_bytes = future.result(timeout=SYNC_COMPILE_TIMEOUT_SECONDS)
        except UnknownReportError as exc:
            return _error_response(str(exc), status.HTTP_400_BAD_REQUEST)
        except ReportParamError as exc:
            logger.warning(
                "Param validation failed for %s: %s", report_type, exc.errors
            )
            return _error_response(
                str(exc), status.HTTP_400_BAD_REQUEST,
                params_errors=exc.errors,
            )
        except concurrent.futures.TimeoutError:
            logger.error(
                "Sync PDF compile timed out after %ds for %s",
                SYNC_COMPILE_TIMEOUT_SECONDS, report_type,
            )
            return _error_response(
                f"PDF generation exceeded the {SYNC_COMPILE_TIMEOUT_SECONDS}s "
                f"sync limit. Use /api/reports/generate/ for long reports.",
                status.HTTP_504_GATEWAY_TIMEOUT,
            )
        except Exception as exc:
            logger.exception(
                "Sync PDF compile failed for report_type=%s", report_type
            )
            return _error_response(
                f"Failed to generate PDF: {exc}",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        filename = generator.get_filename(report_type, params)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    # ---- Metadata --------------------------------------------------------

    @extend_schema(
        responses={200: inline_serializer(
            name="ReportTypesResponse",
            fields={
                "name": serializers.CharField(),
                "title": serializers.CharField(),
                "template": serializers.CharField(),
            },
        )},
    )
    @action(detail=False, methods=["get"], url_path="types")
    def types(self, request):
        """Return a list of registered report types."""
        return Response([
            {"name": a.name, "title": a.title, "template": a.template_path}
            for a in get_all_adapters()
        ])

    @extend_schema(responses={200: GeneratedReportSerializer(many=True)})
    @action(detail=False, methods=["get"], url_path="history")
    def history(self, request):
        """List the current user's generated reports."""
        # tenant-safe: scoped to request.user; users belong to one tenant
        queryset = GeneratedReport.objects.filter(
            generated_by=request.user
        ).select_related("document", "generated_by")

        report_type = request.query_params.get("report_type")
        if report_type:
            queryset = queryset.filter(report_type=report_type)

        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        limit = int(request.query_params.get("limit", 50))
        queryset = queryset[:limit]

        serializer = GeneratedReportSerializer(
            queryset, many=True, context={"request": request}
        )
        return Response(serializer.data)

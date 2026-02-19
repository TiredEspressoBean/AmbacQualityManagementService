"""
Report Generation ViewSets

This module provides API endpoints for generating and managing PDF reports.
Reports are generated server-side using Playwright and can be emailed to users.
"""
from drf_spectacular.utils import extend_schema, extend_schema_field, inline_serializer
from rest_framework import viewsets, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ..services.pdf_generator import PdfGenerator
from ..tasks import generate_and_email_report
from ..models import GeneratedReport


class GenerateReportSerializer(serializers.Serializer):
    """Serializer for report generation requests."""
    report_type = serializers.ChoiceField(
        choices=list(PdfGenerator.REPORT_CONFIG.keys()),
        help_text="Type of report to generate (spc, capa, quality_report, etc.)"
    )
    params = serializers.DictField(
        help_text="Parameters specific to the report type"
    )


class GeneratedReportSerializer(serializers.ModelSerializer):
    """Serializer for GeneratedReport model."""
    generated_by_name = serializers.SerializerMethodField()
    document_url = serializers.SerializerMethodField()

    class Meta:
        model = GeneratedReport
        fields = [
            'id',
            'report_type',
            'generated_by',
            'generated_by_name',
            'generated_at',
            'parameters',
            'document',
            'document_url',
            'emailed_to',
            'emailed_at',
            'status',
            'error_message',
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
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.document.file.url)
            return obj.document.file.url
        return None


class ReportViewSet(viewsets.GenericViewSet):
    """
    ViewSet for generating PDF reports.

    Provides a single endpoint to generate any supported report type.
    Reports are generated asynchronously via Celery and emailed to the user.

    Endpoints:
        POST /api/reports/generate/ - Generate and email a report
        GET /api/reports/history/ - List user's generated reports
        GET /api/reports/types/ - List available report types
    """
    permission_classes = [IsAuthenticated]
    queryset = GeneratedReport.objects.none()  # For drf-spectacular schema generation

    @extend_schema(
        request=GenerateReportSerializer,
        responses={202: inline_serializer(
            name='GenerateReportResponse',
            fields={
                'message': serializers.CharField(),
                'task_id': serializers.CharField(),
            }
        )}
    )
    @action(detail=False, methods=["post"], url_path="generate")
    def generate(self, request):
        """
        Generate and email a PDF report.

        Request body:
        {
            "report_type": "spc",
            "params": {
                "process_id": 1,
                "step_id": 101,
                "measurement_id": 1001,
                "mode": "xbar-r"
            }
        }

        Response:
        {
            "message": "Report is being generated. You'll receive an email shortly.",
            "report_id": 123
        }
        """
        serializer = GenerateReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        report_type = serializer.validated_data["report_type"]
        params = serializer.validated_data["params"]

        # Queue the report generation task
        result = generate_and_email_report.delay(
            user_id=request.user.id,
            user_email=request.user.email,
            report_type=report_type,
            params=params
        )

        return Response({
            "message": "Report is being generated. You'll receive an email shortly.",
            "task_id": result.id
        }, status=status.HTTP_202_ACCEPTED)

    @extend_schema(responses={200: GeneratedReportSerializer(many=True)})
    @action(detail=False, methods=["get"], url_path="history")
    def history(self, request):
        """
        List the current user's generated reports.

        Query params:
            report_type: Filter by report type (optional)
            status: Filter by status (optional)
            limit: Number of results (default 50)
        """
        queryset = GeneratedReport.objects.filter(
            generated_by=request.user
        ).select_related('document', 'generated_by')

        # Apply filters
        report_type = request.query_params.get('report_type')
        if report_type:
            queryset = queryset.filter(report_type=report_type)

        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Limit results
        limit = int(request.query_params.get('limit', 50))
        queryset = queryset[:limit]

        serializer = GeneratedReportSerializer(
            queryset,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)

    @extend_schema(
        responses={200: inline_serializer(
            name='ReportTypesResponse',
            fields={
                'spc': serializers.DictField(help_text="SPC report configuration"),
                'capa': serializers.DictField(help_text="CAPA report configuration"),
            }
        )}
    )
    @action(detail=False, methods=["get"], url_path="types")
    def types(self, request):
        """
        List available report types with their configurations.

        Response:
        {
            "spc": {"title": "SPC Report", "route": "/spc/print"},
            "capa": {"title": "CAPA Report", "route": "/quality/capas/{id}/print"},
            ...
        }
        """
        report_types = {}
        for name, config in PdfGenerator.REPORT_CONFIG.items():
            report_types[name] = {
                "title": config.get("title"),
                "route": config.get("route"),
            }
        return Response(report_types)

    @extend_schema(
        request=GenerateReportSerializer,
        responses={200: bytes}
    )
    @action(detail=False, methods=["post"], url_path="download")
    def download(self, request):
        """
        Generate and download a PDF report directly (synchronous).

        This endpoint generates the PDF and returns it immediately for download,
        rather than emailing it. Use for on-device saves.

        Request body:
        {
            "report_type": "spc",
            "params": {
                "processId": 1,
                "stepId": 101,
                "measurementId": 1001,
                "mode": "xbar-r"
            }
        }

        Returns: PDF file as binary response
        """
        from django.http import HttpResponse

        serializer = GenerateReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        report_type = serializer.validated_data["report_type"]
        params = serializer.validated_data["params"]

        try:
            generator = PdfGenerator()
            pdf_bytes = generator.generate(report_type, params)
            filename = generator.get_filename(report_type, params)

            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": f"Failed to generate PDF: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

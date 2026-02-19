"""
Dashboard ViewSet for Quality Analytics

Provides comprehensive API endpoints for the Analysis/Dashboard page:
- KPIs (CAPAs, NCRs, FPY)
- First Pass Yield trend over time
- Defect Pareto analysis
- In-process actions list
- Recent failed inspections
- Open dispositions
"""
from datetime import timedelta
from collections import defaultdict

from django.db.models import Count, Q, F
from django.db.models.functions import TruncDate
from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiParameter
from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from Tracker.models import (
    CAPA,
    QualityReports,
    QuarantineDisposition,
    Parts,
    QualityErrorsList,
    Steps,
    PartTypes,
)
from .base import TenantAwareMixin


class DashboardViewSet(TenantAwareMixin, viewsets.GenericViewSet):
    """
    ViewSet for Quality Dashboard / Analysis page.

    Endpoints:
        GET /api/dashboard/kpis/ - Key performance indicators
        GET /api/dashboard/fpy-trend/ - First pass yield over time
        GET /api/dashboard/defect-pareto/ - Defects by error type
        GET /api/dashboard/capa-status/ - CAPA status distribution
        GET /api/dashboard/in-process-actions/ - Active CAPAs list
        GET /api/dashboard/failed-inspections/ - Recent failed QA reports
        GET /api/dashboard/open-dispositions/ - Pending dispositions
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: inline_serializer(
            name='DashboardKPIsResponse',
            fields={
                'active_capas': serializers.IntegerField(),
                'open_ncrs': serializers.IntegerField(),
                'overdue_capas': serializers.IntegerField(),
                'parts_in_quarantine': serializers.IntegerField(),
                'current_fpy': serializers.FloatField(allow_null=True),
            }
        )}
    )
    @action(detail=False, methods=['get'], url_path='kpis')
    def kpis(self, request):
        """
        Get key performance indicators for dashboard cards.

        Response:
        {
            "active_capas": 8,
            "open_ncrs": 12,
            "overdue_capas": 2,
            "parts_in_quarantine": 5,
            "current_fpy": 93.5
        }
        """
        today = timezone.now().date()
        seven_days_ago = today - timedelta(days=7)

        # Active CAPAs (not closed)
        active_capas = self.qs_for_user(CAPA).filter(
            archived=False
        ).exclude(
            status='CLOSED'
        ).count()

        # Open NCRs (Quality Reports with FAIL status awaiting disposition)
        # An NCR is a failed inspection that needs disposition
        open_ncrs = self.qs_for_user(QualityReports).filter(
            status='FAIL',
            archived=False,
        ).exclude(
            dispositions__current_state='CLOSED'
        ).count()

        # Overdue CAPAs
        overdue_capas = self.qs_for_user(CAPA).filter(
            archived=False,
            due_date__lt=today,
        ).exclude(
            status='CLOSED'
        ).count()

        # Parts in quarantine (parts with open disposition)
        parts_in_quarantine = self.qs_for_user(QuarantineDisposition).filter(
            archived=False,
            part__isnull=False,
        ).exclude(
            current_state='CLOSED'
        ).values('part').distinct().count()

        # Current FPY (7-day average)
        recent_reports = self.qs_for_user(QualityReports).filter(
            created_at__date__gte=seven_days_ago,
            archived=False,
        )
        total_recent = recent_reports.count()
        passed_recent = recent_reports.filter(status='PASS').count()
        current_fpy = round((passed_recent / total_recent * 100), 1) if total_recent > 0 else 0

        return Response({
            'active_capas': active_capas,
            'open_ncrs': open_ncrs,
            'overdue_capas': overdue_capas,
            'parts_in_quarantine': parts_in_quarantine,
            'current_fpy': current_fpy,
        })

    @extend_schema(
        parameters=[
            OpenApiParameter(name='days', type=int, required=False, default=30, description='Number of days to include'),
        ],
        responses={200: inline_serializer(
            name='FPYTrendResponse',
            fields={
                'data': serializers.ListField(child=serializers.DictField()),
                'average': serializers.FloatField(),
                'total_inspections': serializers.IntegerField(),
                'total_passed': serializers.IntegerField(),
            }
        )}
    )
    @action(detail=False, methods=['get'], url_path='fpy-trend')
    def fpy_trend(self, request):
        """
        Get First Pass Yield trend over time.

        Query params:
            days (optional): Number of days to include (default: 30)

        Response:
        {
            "data": [
                {"date": "2025-01-01", "label": "Jan 1", "fpy": 94.5, "total": 50, "passed": 47},
                ...
            ],
            "average": 93.2
        }
        """
        days = int(request.query_params.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days - 1)

        # Get daily counts
        daily_stats = self.qs_for_user(QualityReports).filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            archived=False,
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            total=Count('id'),
            passed=Count('id', filter=Q(status='PASS'))
        ).order_by('date')

        # Convert to dict for easy lookup
        stats_by_date = {s['date']: s for s in daily_stats}

        # Build complete series (including days with no data)
        data = []
        total_passed = 0
        total_inspections = 0

        current_date = start_date
        while current_date <= end_date:
            stats = stats_by_date.get(current_date, {'total': 0, 'passed': 0})
            total = stats['total']
            passed = stats['passed']
            fpy = round((passed / total * 100), 1) if total > 0 else None

            total_passed += passed
            total_inspections += total

            data.append({
                'date': current_date.isoformat(),
                'label': current_date.strftime('%b %d'),
                'fpy': fpy,
                'total': total,
                'passed': passed,
                'ts': int(timezone.datetime.combine(current_date, timezone.datetime.min.time()).timestamp() * 1000),
            })
            current_date += timedelta(days=1)

        average_fpy = round((total_passed / total_inspections * 100), 1) if total_inspections > 0 else 0

        return Response({
            'data': data,
            'average': average_fpy,
            'total_inspections': total_inspections,
            'total_passed': total_passed,
        })

    @extend_schema(
        parameters=[
            OpenApiParameter(name='days', type=int, required=False, default=30, description='Number of days to include'),
            OpenApiParameter(name='limit', type=int, required=False, default=10, description='Max number of error types'),
        ],
        responses={200: inline_serializer(
            name='DefectParetoResponse',
            fields={
                'data': serializers.ListField(child=serializers.DictField()),
                'total': serializers.IntegerField(),
            }
        )}
    )
    @action(detail=False, methods=['get'], url_path='defect-pareto')
    def defect_pareto(self, request):
        """
        Get defect counts by error type for Pareto analysis.

        Query params:
            days (optional): Number of days to include (default: 30)
            limit (optional): Max number of error types (default: 10)

        Response:
        {
            "data": [
                {"error_type": "Dimensional", "count": 18, "cumulative": 33},
                {"error_type": "Scratch", "count": 14, "cumulative": 59},
                ...
            ],
            "total": 54
        }
        """
        days = int(request.query_params.get('days', 30))
        limit = int(request.query_params.get('limit', 10))
        start_date = timezone.now() - timedelta(days=days)

        # Get counts by error type through QualityReportDefect -> QualityReports
        # Path: QualityErrorsList -> report_instances (QualityReportDefect) -> report (QualityReports)
        error_counts = self.qs_for_user(QualityErrorsList).filter(
            report_instances__report__created_at__gte=start_date,
            report_instances__report__status='FAIL',
            archived=False,
        ).values(
            'error_name'
        ).annotate(
            count=Count('report_instances')
        ).order_by('-count')[:limit]

        # Calculate cumulative percentages
        data = list(error_counts)
        total = sum(d['count'] for d in data)

        cumulative = 0
        for d in data:
            cumulative += d['count']
            d['cumulative'] = round((cumulative / total * 100)) if total > 0 else 0
            # Rename for frontend consistency
            d['errorType'] = d.pop('error_name') or 'Unknown'

        return Response({
            'data': data,
            'total': total,
        })

    @extend_schema(
        responses={200: inline_serializer(
            name='CAPAStatusResponse',
            fields={
                'data': serializers.ListField(child=serializers.DictField()),
                'total': serializers.IntegerField(),
            }
        )}
    )
    @action(detail=False, methods=['get'], url_path='capa-status')
    def capa_status(self, request):
        """
        Get CAPA status distribution for pie chart.

        Response:
        {
            "data": [
                {"status": "Open", "value": 2},
                {"status": "In Progress", "value": 4},
                {"status": "Pending Verification", "value": 2}
            ],
            "total": 8
        }
        """
        status_counts = self.qs_for_user(CAPA).filter(
            archived=False
        ).exclude(
            status='CLOSED'
        ).values('status').annotate(
            value=Count('id')
        ).order_by('status')

        # Map status codes to display labels
        status_labels = {
            'OPEN': 'Open',
            'IN_PROGRESS': 'In Progress',
            'PENDING_VERIFICATION': 'Pending Verification',
            'CLOSED': 'Closed',
        }

        data = []
        for s in status_counts:
            data.append({
                'status': status_labels.get(s['status'], s['status']),
                'value': s['value'],
            })

        total = sum(d['value'] for d in data)

        return Response({
            'data': data,
            'total': total,
        })

    @extend_schema(
        parameters=[
            OpenApiParameter(name='limit', type=int, required=False, default=10, description='Max number of items'),
        ],
        responses={200: inline_serializer(
            name='InProcessActionsResponse',
            fields={
                'data': serializers.ListField(child=serializers.DictField()),
            }
        )}
    )
    @action(detail=False, methods=['get'], url_path='in-process-actions')
    def in_process_actions(self, request):
        """
        Get list of active CAPAs for the actions table.

        Query params:
            limit (optional): Max number of items (default: 10)

        Response:
        {
            "data": [
                {
                    "id": "CAPA-2025-008",
                    "type": "CAPA",
                    "title": "Seal leak failures",
                    "assignee": "J. Gomez",
                    "due": "2025-12-18",
                    "status": "IN_PROGRESS"
                },
                ...
            ]
        }
        """
        limit = int(request.query_params.get('limit', 10))

        capas = self.qs_for_user(CAPA).filter(
            archived=False
        ).exclude(
            status='CLOSED'
        ).select_related(
            'assigned_to'
        ).order_by('due_date', '-created_at')[:limit]

        data = []
        for capa in capas:
            # Truncate problem statement for title
            title = capa.problem_statement[:60] + '...' if len(capa.problem_statement) > 60 else capa.problem_statement

            data.append({
                'id': capa.capa_number,
                'db_id': capa.id,
                'type': 'CAPA',
                'title': title,
                'assignee': capa.assigned_to.get_full_name() if capa.assigned_to else 'Unassigned',
                'due': capa.due_date.isoformat() if capa.due_date else None,
                'status': capa.status,
            })

        return Response({'data': data})

    @extend_schema(
        parameters=[
            OpenApiParameter(name='limit', type=int, required=False, default=10, description='Max number of items'),
            OpenApiParameter(name='days', type=int, required=False, default=14, description='Number of days to look back'),
        ],
        responses={200: inline_serializer(
            name='FailedInspectionsResponse',
            fields={
                'data': serializers.ListField(child=serializers.DictField()),
            }
        )}
    )
    @action(detail=False, methods=['get'], url_path='failed-inspections')
    def failed_inspections(self, request):
        """
        Get recent failed quality inspections.

        Query params:
            limit (optional): Max number of items (default: 10)
            days (optional): Number of days to look back (default: 14)

        Response:
        {
            "data": [
                {
                    "id": 1,
                    "part": "PN-2025-1847-003",
                    "step": "Final Assembly",
                    "error_type": "Dimensional",
                    "inspector": "Chen",
                    "date": "Dec 14"
                },
                ...
            ]
        }
        """
        limit = int(request.query_params.get('limit', 10))
        days = int(request.query_params.get('days', 14))
        start_date = timezone.now() - timedelta(days=days)

        reports = self.qs_for_user(QualityReports).filter(
            status='FAIL',
            created_at__gte=start_date,
            archived=False,
        ).select_related(
            'part',
            'step',
        ).prefetch_related(
            'errors',
            'operators',
        ).order_by('-created_at')[:limit]

        data = []
        for report in reports:
            # Get first error type
            error_types = [err.error_name for err in report.errors.all()]
            error_type = error_types[0] if error_types else 'Unknown'

            # Get first operator (M2M field)
            first_operator = report.operators.first()

            data.append({
                'id': report.id,
                'part': report.part.ERP_id if report.part else 'N/A',
                'part_id': report.part.id if report.part else None,
                'step': report.step.name if report.step else 'N/A',
                'error_type': error_type,
                'inspector': first_operator.get_short_name() if first_operator else 'N/A',
                'date': report.created_at.strftime('%b %d'),
            })

        return Response({'data': data})

    @extend_schema(
        parameters=[
            OpenApiParameter(name='limit', type=int, required=False, default=10, description='Max number of items'),
        ],
        responses={200: inline_serializer(
            name='OpenDispositionsResponse',
            fields={
                'data': serializers.ListField(child=serializers.DictField()),
            }
        )}
    )
    @action(detail=False, methods=['get'], url_path='open-dispositions')
    def open_dispositions(self, request):
        """
        Get open/pending dispositions.

        Query params:
            limit (optional): Max number of items (default: 10)

        Response:
        {
            "data": [
                {
                    "id": 1,
                    "part": "PN-2025-1847-003",
                    "disposition": "REWORK",
                    "reason": "Dim out of spec",
                    "assignee": "Rivera",
                    "created": "Dec 14"
                },
                ...
            ]
        }
        """
        limit = int(request.query_params.get('limit', 10))

        dispositions = self.qs_for_user(QuarantineDisposition).filter(
            archived=False,
        ).exclude(
            current_state='CLOSED'
        ).select_related(
            'part',
            'assigned_to',
        ).order_by('-created_at')[:limit]

        data = []
        for disp in dispositions:
            data.append({
                'id': disp.id,
                'part': disp.part.ERP_id if disp.part else 'N/A',
                'part_id': disp.part.id if disp.part else None,
                'disposition': disp.disposition_type or 'PENDING',
                'reason': disp.description[:50] + '...' if disp.description and len(disp.description) > 50 else (disp.description or 'N/A'),
                'assignee': disp.assigned_to.get_short_name() if disp.assigned_to else 'Unassigned',
                'created': disp.created_at.strftime('%b %d'),
                'status': disp.current_state,
            })

        return Response({'data': data})

    @extend_schema(
        parameters=[
            OpenApiParameter(name='days', type=int, required=False, default=30, description='Number of days to include'),
        ],
        responses={200: inline_serializer(
            name='QualityRatesResponse',
            fields={
                'scrap_rate': serializers.FloatField(),
                'rework_rate': serializers.FloatField(),
                'use_as_is_rate': serializers.FloatField(),
                'total_inspected': serializers.IntegerField(),
                'total_failed': serializers.IntegerField(),
            }
        )}
    )
    @action(detail=False, methods=['get'], url_path='quality-rates')
    def quality_rates(self, request):
        """
        Get scrap and rework rates for the specified period.

        Query params:
            days (optional): Number of days to include (default: 30)

        Response:
        {
            "scrap_rate": 1.2,
            "rework_rate": 3.4,
            "use_as_is_rate": 0.8,
            "total_inspected": 500,
            "total_failed": 27
        }
        """
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)

        # Total inspections in period
        total_inspected = self.qs_for_user(QualityReports).filter(
            created_at__gte=start_date,
            archived=False,
        ).count()

        # Failed inspections that led to dispositions
        total_failed = self.qs_for_user(QualityReports).filter(
            created_at__gte=start_date,
            status='FAIL',
            archived=False,
        ).count()

        # Disposition counts by type
        disposition_counts = self.qs_for_user(QuarantineDisposition).filter(
            created_at__gte=start_date,
            archived=False,
        ).values('disposition_type').annotate(
            count=Count('id')
        )

        disp_by_type = {d['disposition_type']: d['count'] for d in disposition_counts}
        scrap_count = disp_by_type.get('SCRAP', 0)
        rework_count = disp_by_type.get('REWORK', 0)
        use_as_is_count = disp_by_type.get('USE_AS_IS', 0)

        # Calculate rates as percentage of total inspected
        scrap_rate = round((scrap_count / total_inspected * 100), 1) if total_inspected > 0 else 0
        rework_rate = round((rework_count / total_inspected * 100), 1) if total_inspected > 0 else 0
        use_as_is_rate = round((use_as_is_count / total_inspected * 100), 1) if total_inspected > 0 else 0

        return Response({
            'scrap_rate': scrap_rate,
            'rework_rate': rework_rate,
            'use_as_is_rate': use_as_is_rate,
            'total_inspected': total_inspected,
            'total_failed': total_failed,
        })

    @extend_schema(
        parameters=[
            OpenApiParameter(name='days', type=int, required=False, default=30, description='Number of days to include'),
        ],
        responses={200: inline_serializer(
            name='NcrTrendResponse',
            fields={
                'data': serializers.ListField(child=serializers.DictField()),
                'summary': serializers.DictField(),
            }
        )}
    )
    @action(detail=False, methods=['get'], url_path='ncr-trend')
    def ncr_trend(self, request):
        """
        Get NCR (failed inspections) created/closed trend over time.

        Query params:
            days (optional): Number of days to include (default: 30)

        Response:
        {
            "data": [
                {"date": "2025-01-01", "created": 3, "closed": 2, "net_open": 1},
                ...
            ],
            "summary": {
                "total_created": 45,
                "total_closed": 38,
                "net_change": 7
            }
        }
        """
        days = int(request.query_params.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days - 1)

        # NCRs created per day (failed quality reports)
        created_by_day = self.qs_for_user(QualityReports).filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            status='FAIL',
            archived=False,
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            count=Count('id')
        )
        created_dict = {c['date']: c['count'] for c in created_by_day}

        # NCRs closed per day (dispositions closed)
        closed_by_day = self.qs_for_user(QuarantineDisposition).filter(
            updated_at__date__gte=start_date,
            updated_at__date__lte=end_date,
            current_state='CLOSED',
            archived=False,
        ).annotate(
            date=TruncDate('updated_at')
        ).values('date').annotate(
            count=Count('id')
        )
        closed_dict = {c['date']: c['count'] for c in closed_by_day}

        # Build complete series
        data = []
        total_created = 0
        total_closed = 0
        current_date = start_date

        while current_date <= end_date:
            created = created_dict.get(current_date, 0)
            closed = closed_dict.get(current_date, 0)
            total_created += created
            total_closed += closed

            data.append({
                'date': current_date.isoformat(),
                'label': current_date.strftime('%b %d'),
                'created': created,
                'closed': closed,
                'net_open': created - closed,
            })
            current_date += timedelta(days=1)

        return Response({
            'data': data,
            'summary': {
                'total_created': total_created,
                'total_closed': total_closed,
                'net_change': total_created - total_closed,
            }
        })

    @extend_schema(
        parameters=[
            OpenApiParameter(name='days', type=int, required=False, default=30, description='Number of days to include'),
        ],
        responses={200: inline_serializer(
            name='DispositionBreakdownResponse',
            fields={
                'data': serializers.ListField(child=serializers.DictField()),
                'total': serializers.IntegerField(),
            }
        )}
    )
    @action(detail=False, methods=['get'], url_path='disposition-breakdown')
    def disposition_breakdown(self, request):
        """
        Get disposition counts by type for pie/donut chart.

        Query params:
            days (optional): Number of days to include (default: 30)

        Response:
        {
            "data": [
                {"type": "Rework", "count": 15, "percentage": 45},
                {"type": "Scrap", "count": 8, "percentage": 24},
                {"type": "Use As-Is", "count": 10, "percentage": 31}
            ],
            "total": 33
        }
        """
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)

        # Count by disposition type
        type_counts = self.qs_for_user(QuarantineDisposition).filter(
            created_at__gte=start_date,
            archived=False,
        ).values('disposition_type').annotate(
            count=Count('id')
        ).order_by('-count')

        type_labels = {
            'SCRAP': 'Scrap',
            'REWORK': 'Rework',
            'USE_AS_IS': 'Use As-Is',
            'RETURN_TO_VENDOR': 'Return to Vendor',
            None: 'Pending',
        }

        data = []
        total = 0
        for tc in type_counts:
            count = tc['count']
            total += count
            data.append({
                'type': type_labels.get(tc['disposition_type'], tc['disposition_type'] or 'Pending'),
                'count': count,
            })

        # Calculate percentages
        for d in data:
            d['percentage'] = round((d['count'] / total * 100)) if total > 0 else 0

        return Response({
            'data': data,
            'total': total,
        })

    @extend_schema(
        responses={200: inline_serializer(
            name='NcrAgingResponse',
            fields={
                'data': serializers.ListField(child=serializers.DictField()),
                'avg_age_days': serializers.FloatField(),
                'overdue_count': serializers.IntegerField(),
            }
        )}
    )
    @action(detail=False, methods=['get'], url_path='ncr-aging')
    def ncr_aging(self, request):
        """
        Get NCR aging buckets for currently open NCRs.

        Response:
        {
            "data": [
                {"bucket": "0-3 days", "count": 8},
                {"bucket": "4-7 days", "count": 5},
                {"bucket": "8-14 days", "count": 3},
                {"bucket": ">14 days", "count": 2}
            ],
            "avg_age_days": 5.2,
            "overdue_count": 2
        }
        """
        today = timezone.now().date()

        # Get open dispositions (NCRs not yet closed)
        open_dispositions = self.qs_for_user(QuarantineDisposition).filter(
            archived=False,
        ).exclude(
            current_state='CLOSED'
        ).values_list('created_at', flat=True)

        # Calculate ages and bucket them
        buckets = {
            '0-3 days': 0,
            '4-7 days': 0,
            '8-14 days': 0,
            '>14 days': 0,
        }

        total_age = 0
        overdue_count = 0

        for created_at in open_dispositions:
            age = (today - created_at.date()).days
            total_age += age

            if age > 14:
                buckets['>14 days'] += 1
            elif age > 7:
                buckets['8-14 days'] += 1
            elif age > 3:
                buckets['4-7 days'] += 1
            else:
                buckets['0-3 days'] += 1

            if age > 7:  # Consider >7 days as overdue
                overdue_count += 1

        count = len(open_dispositions)
        avg_age = round(total_age / count, 1) if count > 0 else 0

        data = [{'bucket': k, 'count': v} for k, v in buckets.items()]

        return Response({
            'data': data,
            'avg_age_days': avg_age,
            'overdue_count': overdue_count,
        })

    @extend_schema(
        responses={200: inline_serializer(
            name='NeedsAttentionResponse',
            fields={
                'data': serializers.ListField(child=serializers.DictField()),
            }
        )}
    )
    @action(detail=False, methods=['get'], url_path='needs-attention')
    def needs_attention(self, request):
        """
        Get priority items that need attention for the overview dashboard.

        Response:
        {
            "data": [
                {
                    "type": "ncr",
                    "message": "NCRs open > 7 days",
                    "count": 3,
                    "severity": "high",
                    "link": "/quality/ncrs",
                    "linkParams": {"aging": "overdue"}
                },
                ...
            ]
        }
        """
        today = timezone.now().date()
        data = []

        # 1. NCRs open > 7 days
        old_ncrs = self.qs_for_user(QuarantineDisposition).filter(
            archived=False,
            created_at__date__lt=(today - timedelta(days=7)),
        ).exclude(
            current_state='CLOSED'
        ).count()

        if old_ncrs > 0:
            data.append({
                'type': 'ncr',
                'message': 'NCRs open > 7 days',
                'count': old_ncrs,
                'severity': 'high' if old_ncrs > 5 else 'medium',
                'link': '/production/dispositions',
                'linkParams': {'status': 'overdue'},
            })

        # 2. Overdue CAPAs
        overdue_capas = self.qs_for_user(CAPA).filter(
            archived=False,
            due_date__lt=today,
        ).exclude(
            status='CLOSED'
        ).count()

        if overdue_capas > 0:
            data.append({
                'type': 'capa',
                'message': 'CAPAs past due date',
                'count': overdue_capas,
                'severity': 'critical' if overdue_capas > 3 else 'high',
                'link': '/quality/capas',
                'linkParams': {'status': 'overdue'},
            })

        # 3. Dispositions awaiting decision
        pending_dispositions = self.qs_for_user(QuarantineDisposition).filter(
            archived=False,
            disposition_type__isnull=True,
        ).exclude(
            current_state='CLOSED'
        ).count()

        if pending_dispositions > 0:
            data.append({
                'type': 'disposition',
                'message': 'Awaiting disposition decision',
                'count': pending_dispositions,
                'severity': 'medium',
                'link': '/production/dispositions',
                'linkParams': {'status': 'pending'},
            })

        # 4. Parts in quarantine
        quarantine_parts = self.qs_for_user(Parts).filter(
            archived=False,
            part_status='QUARANTINE',
        ).count()

        if quarantine_parts > 0:
            data.append({
                'type': 'quarantine',
                'message': 'Parts in quarantine',
                'count': quarantine_parts,
                'severity': 'low',
                'link': '/editor/parts',
                'linkParams': {'status': 'QUARANTINE'},
            })

        # 5. CAPAs pending verification
        pending_verification = self.qs_for_user(CAPA).filter(
            archived=False,
            status='PENDING_VERIFICATION',
        ).count()

        if pending_verification > 0:
            data.append({
                'type': 'verification',
                'message': 'CAPAs pending verification',
                'count': pending_verification,
                'severity': 'low',
                'link': '/quality/capas',
                'linkParams': {'status': 'PENDING_VERIFICATION'},
            })

        # Sort by severity
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        data.sort(key=lambda x: severity_order.get(x['severity'], 4))

        return Response({'data': data})

    @extend_schema(
        parameters=[
            OpenApiParameter(name='days', type=int, required=False, default=30, description='Number of days to include'),
            OpenApiParameter(name='limit', type=int, required=False, default=10, description='Max number of processes'),
        ],
        responses={200: inline_serializer(
            name='DefectsByProcessResponse',
            fields={
                'data': serializers.ListField(child=serializers.DictField()),
                'total': serializers.IntegerField(),
            }
        )}
    )
    @action(detail=False, methods=['get'], url_path='defects-by-process')
    def defects_by_process(self, request):
        """
        Get defect counts grouped by process step.

        Query params:
            days (optional): Number of days to include (default: 30)
            limit (optional): Max number of processes (default: 10)

        Response:
        {
            "data": [
                {"process_name": "Final Assembly", "count": 18},
                {"process_name": "Machining", "count": 12},
                ...
            ],
            "total": 54
        }
        """
        days = int(request.query_params.get('days', 30))
        limit = int(request.query_params.get('limit', 10))
        start_date = timezone.now() - timedelta(days=days)

        # Count failed reports by step
        step_counts = self.qs_for_user(QualityReports).filter(
            created_at__gte=start_date,
            status='FAIL',
            archived=False,
            step__isnull=False,
        ).values(
            'step__name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:limit]

        data = []
        total = 0
        for sc in step_counts:
            data.append({
                'process_name': sc['step__name'] or 'Unknown',
                'count': sc['count'],
            })
            total += sc['count']

        return Response({
            'data': data,
            'total': total,
        })

    @extend_schema(
        parameters=[
            OpenApiParameter(name='days', type=int, required=False, default=30, description='Number of days to include'),
            OpenApiParameter(name='min_occurrences', type=int, required=False, default=3, description='Min occurrences to be considered repeat'),
            OpenApiParameter(name='limit', type=int, required=False, default=10, description='Max number of items'),
        ],
        responses={200: inline_serializer(
            name='RepeatDefectsResponse',
            fields={
                'data': serializers.ListField(child=serializers.DictField()),
                'total_repeat_count': serializers.IntegerField(),
            }
        )}
    )
    @action(detail=False, methods=['get'], url_path='repeat-defects')
    def repeat_defects(self, request):
        """
        Get recurring defects (same error type appearing multiple times).

        Query params:
            days (optional): Number of days to include (default: 30)
            min_occurrences (optional): Min occurrences to be considered repeat (default: 3)
            limit (optional): Max number of items (default: 10)

        Response:
        {
            "data": [
                {
                    "error_type": "Dimensional",
                    "count": 12,
                    "part_types_affected": ["Bracket", "Housing"],
                    "processes_affected": ["Machining", "Assembly"]
                },
                ...
            ],
            "total_repeat_count": 28
        }
        """
        days = int(request.query_params.get('days', 30))
        min_occurrences = int(request.query_params.get('min_occurrences', 3))
        limit = int(request.query_params.get('limit', 10))
        start_date = timezone.now() - timedelta(days=days)

        # Get error types with counts >= min_occurrences
        # Path: QualityErrorsList -> report_instances (QualityReportDefect) -> report (QualityReports)
        repeat_errors = self.qs_for_user(QualityErrorsList).filter(
            report_instances__report__created_at__gte=start_date,
            report_instances__report__status='FAIL',
            archived=False,
        ).annotate(
            count=Count('report_instances')
        ).filter(
            count__gte=min_occurrences
        ).order_by('-count')[:limit]

        data = []
        total_repeat = 0

        for error in repeat_errors:
            # Get related part types and processes
            # Path: QualityReports -> defects (QualityReportDefect) -> error_type (QualityErrorsList)
            related_reports = self.qs_for_user(QualityReports).filter(
                defects__error_type=error,
                created_at__gte=start_date,
                status='FAIL',
            ).select_related('part__part_type', 'step')

            part_types = set()
            processes = set()
            for r in related_reports:
                if r.part and r.part.part_type:
                    part_types.add(r.part.part_type.name)
                if r.step:
                    processes.add(r.step.name)

            data.append({
                'error_type': error.error_name or 'Unknown',
                'count': error.count,
                'part_types_affected': list(part_types)[:5],
                'processes_affected': list(processes)[:5],
            })
            total_repeat += error.count

        return Response({
            'data': data,
            'total_repeat_count': total_repeat,
        })

    @extend_schema(
        parameters=[
            OpenApiParameter(name='days', type=int, required=False, default=30, description='Number of days to include'),
            OpenApiParameter(name='defect_type', type=str, required=False, description='Filter by error type name'),
            OpenApiParameter(name='process', type=str, required=False, description='Filter by step/process name'),
            OpenApiParameter(name='part_type', type=str, required=False, description='Filter by part type name'),
            OpenApiParameter(name='limit', type=int, required=False, default=50, description='Max number of records'),
            OpenApiParameter(name='offset', type=int, required=False, default=0, description='Pagination offset'),
        ],
        responses={200: inline_serializer(
            name='DefectRecordsResponse',
            fields={
                'data': serializers.ListField(child=serializers.DictField()),
                'total': serializers.IntegerField(),
                'filters_applied': serializers.DictField(),
            }
        )}
    )
    @action(detail=False, methods=['get'], url_path='defect-records')
    def defect_records(self, request):
        """
        Get filtered defect (failed quality report) records for drill-down table.

        Query params:
            days (optional): Number of days to include (default: 30)
            defect_type (optional): Filter by error type name
            process (optional): Filter by step/process name
            part_type (optional): Filter by part type name
            limit (optional): Max number of records (default: 50)
            offset (optional): Pagination offset (default: 0)

        Response:
        {
            "data": [
                {
                    "id": 123,
                    "part_erp_id": "CRI-0042",
                    "part_id": 456,
                    "part_type": "Common Rail Injector",
                    "part_type_id": 1,
                    "step": "Flow Testing",
                    "step_id": 5,
                    "error_types": ["Dimensional", "Surface"],
                    "inspector": "J. Smith",
                    "date": "2025-01-02",
                    "date_formatted": "Jan 02",
                    "order": "ORD-2501-003",
                    "order_id": 789,
                    "work_order": "WO-2501-CRI-01",
                    "work_order_id": 101,
                    "disposition_status": "OPEN",
                    "disposition_type": "REWORK",
                    "description": "Flow rate below specification..."
                },
                ...
            ],
            "total": 127,
            "filters_applied": {
                "defect_type": "Dimensional",
                "process": null,
                "part_type": null,
                "days": 30
            }
        }
        """
        days = int(request.query_params.get('days', 30))
        limit = int(request.query_params.get('limit', 50))
        offset = int(request.query_params.get('offset', 0))
        defect_type = request.query_params.get('defect_type')
        process = request.query_params.get('process')
        part_type = request.query_params.get('part_type')

        start_date = timezone.now() - timedelta(days=days)

        # Base query: failed quality reports
        queryset = self.qs_for_user(QualityReports).filter(
            created_at__gte=start_date,
            status='FAIL',
            archived=False,
        ).select_related(
            'part',
            'part__part_type',
            'part__order',
            'part__work_order',
            'step',
        ).prefetch_related(
            'errors',
            'operators',
            'dispositions',
        ).order_by('-created_at')

        # Apply filters
        if defect_type:
            queryset = queryset.filter(errors__error_name__icontains=defect_type)

        if process:
            queryset = queryset.filter(step__name__icontains=process)

        if part_type:
            queryset = queryset.filter(part__part_type__name__icontains=part_type)

        # Get total before pagination
        total = queryset.count()

        # Apply pagination
        queryset = queryset.distinct()[offset:offset + limit]

        # Build response data
        data = []
        for report in queryset:
            error_types = [err.error_name for err in report.errors.all() if err.error_name]
            first_operator = report.operators.first()

            # Get disposition info if exists
            disposition = report.dispositions.first()
            disposition_status = disposition.current_state if disposition else None
            disposition_type = disposition.disposition_type if disposition else None

            data.append({
                'id': report.id,
                'part_erp_id': report.part.ERP_id if report.part else 'N/A',
                'part_id': report.part.id if report.part else None,
                'part_type': report.part.part_type.name if report.part and report.part.part_type else 'N/A',
                'part_type_id': report.part.part_type.id if report.part and report.part.part_type else None,
                'step': report.step.name if report.step else 'N/A',
                'step_id': report.step.id if report.step else None,
                'error_types': error_types,
                'inspector': first_operator.get_full_name() if first_operator else 'N/A',
                'date': report.created_at.date().isoformat(),
                'date_formatted': report.created_at.strftime('%b %d'),
                'order': report.part.order.name if report.part and report.part.order else 'N/A',
                'order_id': report.part.order.id if report.part and report.part.order else None,
                'work_order': report.part.work_order.ERP_id if report.part and report.part.work_order else 'N/A',
                'work_order_id': report.part.work_order.id if report.part and report.part.work_order else None,
                'disposition_status': disposition_status,
                'disposition_type': disposition_type,
                'description': report.description[:100] + '...' if report.description and len(report.description) > 100 else (report.description or ''),
            })

        return Response({
            'data': data,
            'total': total,
            'filters_applied': {
                'defect_type': defect_type,
                'process': process,
                'part_type': part_type,
                'days': days,
            }
        })

    @extend_schema(
        parameters=[
            OpenApiParameter(name='days', type=int, required=False, default=30, description='Number of days to include'),
        ],
        responses={200: inline_serializer(
            name='FilterOptionsResponse',
            fields={
                'defect_types': serializers.ListField(child=serializers.DictField()),
                'processes': serializers.ListField(child=serializers.DictField()),
                'part_types': serializers.ListField(child=serializers.DictField()),
            }
        )}
    )
    @action(detail=False, methods=['get'], url_path='filter-options')
    def filter_options(self, request):
        """
        Get available filter options for defect analysis drill-down.
        Returns lists of defect types, processes, and part types that have defects.

        Query params:
            days (optional): Number of days to include (default: 30)

        Response:
        {
            "defect_types": [
                {"value": "Dimensional", "label": "Dimensional", "count": 45},
                ...
            ],
            "processes": [
                {"value": "Flow Testing", "label": "Flow Testing", "count": 32},
                ...
            ],
            "part_types": [
                {"value": "Common Rail Injector", "label": "Common Rail Injector", "count": 28},
                ...
            ]
        }
        """
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)

        # Base filter for failed reports in period
        # Path: QualityErrorsList -> report_instances (QualityReportDefect) -> report (QualityReports)
        base_filter = Q(
            report_instances__report__created_at__gte=start_date,
            report_instances__report__status='FAIL',
            report_instances__report__archived=False,
        )

        # Defect types with counts
        defect_types = self.qs_for_user(QualityErrorsList).filter(
            base_filter,
            archived=False,
        ).values('error_name').annotate(
            count=Count('report_instances')
        ).order_by('-count')

        defect_type_options = [
            {'value': d['error_name'], 'label': d['error_name'] or 'Unknown', 'count': d['count']}
            for d in defect_types if d['error_name']
        ]

        # Processes (steps) with defect counts
        process_counts = self.qs_for_user(QualityReports).filter(
            created_at__gte=start_date,
            status='FAIL',
            archived=False,
            step__isnull=False,
        ).values('step__name', 'step__id').annotate(
            count=Count('id')
        ).order_by('-count')

        process_options = [
            {'value': p['step__name'], 'label': p['step__name'], 'count': p['count']}
            for p in process_counts if p['step__name']
        ]

        # Part types with defect counts
        part_type_counts = self.qs_for_user(QualityReports).filter(
            created_at__gte=start_date,
            status='FAIL',
            archived=False,
            part__part_type__isnull=False,
        ).values('part__part_type__name', 'part__part_type__id').annotate(
            count=Count('id')
        ).order_by('-count')

        part_type_options = [
            {'value': pt['part__part_type__name'], 'label': pt['part__part_type__name'], 'count': pt['count']}
            for pt in part_type_counts if pt['part__part_type__name']
        ]

        return Response({
            'defect_types': defect_type_options,
            'processes': process_options,
            'part_types': part_type_options,
        })

    @extend_schema(
        parameters=[
            OpenApiParameter(name='days', type=int, required=False, default=30, description='Number of days to include'),
        ],
        responses={200: inline_serializer(
            name='DefectTrendResponse',
            fields={
                'data': serializers.ListField(child=serializers.DictField()),
                'summary': serializers.DictField(),
            }
        )}
    )
    @action(detail=False, methods=['get'], url_path='defect-trend')
    def defect_trend(self, request):
        """
        Get defect count trend over time.

        Query params:
            days (optional): Number of days to include (default: 30)

        Response:
        {
            "data": [
                {"date": "2025-01-01", "label": "Jan 1", "count": 5, "ts": 1704067200000},
                ...
            ],
            "summary": {
                "total": 127,
                "daily_avg": 4.2,
                "trend_direction": "down",
                "trend_change": -12.5
            }
        }
        """
        days = int(request.query_params.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days - 1)

        # Get daily defect counts
        daily_counts = self.qs_for_user(QualityReports).filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            status='FAIL',
            archived=False,
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')

        counts_by_date = {c['date']: c['count'] for c in daily_counts}

        # Build complete series
        data = []
        total = 0
        first_half_total = 0
        second_half_total = 0
        midpoint = days // 2
        current_date = start_date
        day_index = 0

        while current_date <= end_date:
            count = counts_by_date.get(current_date, 0)
            total += count

            if day_index < midpoint:
                first_half_total += count
            else:
                second_half_total += count

            data.append({
                'date': current_date.isoformat(),
                'label': current_date.strftime('%b %d'),
                'count': count,
                'ts': int(timezone.datetime.combine(current_date, timezone.datetime.min.time()).timestamp() * 1000),
            })
            current_date += timedelta(days=1)
            day_index += 1

        # Calculate trend
        daily_avg = round(total / days, 1) if days > 0 else 0

        # Compare first half to second half for trend
        if first_half_total > 0:
            trend_change = round(((second_half_total - first_half_total) / first_half_total) * 100, 1)
        else:
            trend_change = 0 if second_half_total == 0 else 100

        if trend_change > 5:
            trend_direction = 'up'
        elif trend_change < -5:
            trend_direction = 'down'
        else:
            trend_direction = 'flat'

        return Response({
            'data': data,
            'summary': {
                'total': total,
                'daily_avg': daily_avg,
                'trend_direction': trend_direction,
                'trend_change': trend_change,
            }
        })


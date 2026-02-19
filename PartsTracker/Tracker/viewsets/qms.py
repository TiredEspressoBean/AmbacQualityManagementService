# viewsets/qms.py - QMS ViewSets (Quality, Sampling, CAPA, 3D Models, Heatmap Annotations)
from django.db import models
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, inline_serializer, extend_schema_view, OpenApiParameter
from rest_framework import viewsets, status, filters, serializers
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework import parsers
from rest_framework.response import Response
from rest_framework.filters import OrderingFilter

from Tracker.models import (
    # QMS models
    QualityReports, QualityErrorsList, QuarantineDisposition,
    CAPA, CapaTasks, RcaRecord, CapaVerification,
    FiveWhys, Fishbone,
    ThreeDModel, HeatMapAnnotations,
    # MES models
    SamplingRuleSet, SamplingRule, MeasurementDefinition,
    # Core models
    NotificationTask,
)
from Tracker.serializers.qms import (
    QualityReportsSerializer, QualityErrorsListSerializer, QuarantineDispositionSerializer,
    SamplingRuleSetSerializer, SamplingRuleSerializer, MeasurementDefinitionSerializer,
    NotificationPreferenceSerializer,
    CAPASerializer, CapaTasksSerializer, RcaRecordSerializer, CapaVerificationSerializer,
    FiveWhysSerializer, FishboneSerializer
)
from Tracker.serializers.dms import ThreeDModelSerializer, HeatMapAnnotationsSerializer
from .core import ExcelExportMixin, ListMetadataMixin
from .base import TenantScopedMixin


# ===== QUALITY VIEWSETS =====

class QualityReportViewSet(TenantScopedMixin, ListMetadataMixin, ExcelExportMixin, viewsets.ModelViewSet):
    queryset = QualityReports.objects.all()
    serializer_class = QualityReportsSerializer
    pagination_class = LimitOffsetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['status', 'part', 'step', 'machine', 'part__work_order']
    ordering_fields = ['id', 'status', 'created_at']
    ordering = ['-created_at']
    search_fields = ['description', 'part__ERP_id']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return QualityReports.objects.none()

        # Apply tenant scoping first, then user filtering with optimized joins
        qs = super().get_queryset()
        return qs.select_related(
            'part', 'part__part_type', 'part__work_order', 'part__work_order__process',
            'step', 'step__part_type',
            'machine', 'machine__equipment_type',
            'file',
        ).prefetch_related('operators', 'errors')


class ErrorTypeViewSet(TenantScopedMixin, ListMetadataMixin, ExcelExportMixin, viewsets.ModelViewSet):
    queryset = QualityErrorsList.objects.all()
    serializer_class = QualityErrorsListSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ["error_name", "part_type"]
    ordering_fields = ["id", "error_name", "part_type__name"]
    ordering = ["error_name"]
    search_fields = ["error_name", "part_type__name"]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return QualityErrorsList.objects.none()

        # Apply tenant scoping first, then user filtering
        qs = super().get_queryset()
        return qs


class QuarantineDispositionViewSet(TenantScopedMixin, ListMetadataMixin, ExcelExportMixin, viewsets.ModelViewSet):
    queryset = QuarantineDisposition.objects.all()
    serializer_class = QuarantineDispositionSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]

    # Fixed filterset fields - these should be actual model fields, not SerializerMethodField names
    filterset_fields = ["disposition_number", "current_state", "disposition_type", "resolution_completed",
                        "assigned_to", "resolution_completed_by", "part", "part__ERP_id", "part__part_type__name"]

    # Search fields should be actual model fields that can be searched
    search_fields = ["disposition_number", "description", "resolution_notes", "assigned_to__first_name",
                     "assigned_to__last_name", "assigned_to__username", "resolution_completed_by__first_name",
                     "resolution_completed_by__last_name", "part__ERP_id", "part__part_type__name"]

    # Fixed duplicate disposition_number in ordering_fields
    ordering_fields = ["disposition_number", "current_state", "created_at", "updated_at", "resolution_completed_at"]
    ordering = ["-updated_at"]

    def get_queryset(self):
        """Apply tenant scoping first, then SecureModel filtering for user-specific access"""
        if getattr(self, 'swagger_fake_view', False):
            return QuarantineDisposition.objects.none()
        qs = super().get_queryset()
        return qs.select_related('assigned_to',
                                                             'resolution_completed_by',
                                                             'part__part_type').prefetch_related(
            'quality_reports', 'documents')


# ===== SAMPLING VIEWSETS =====

class SamplingRuleSetViewSet(TenantScopedMixin, ListMetadataMixin, ExcelExportMixin, viewsets.ModelViewSet):
    queryset = SamplingRuleSet.objects.all()
    serializer_class = SamplingRuleSetSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ["part_type", "process", "step", "active", "version"]
    ordering_fields = ["id", "name", "version", "created_at"]
    ordering = ["name"]
    search_fields = ["name", "origin"]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return SamplingRuleSet.objects.none()

        # Apply tenant scoping first, then user filtering
        qs = super().get_queryset()
        return qs


class SamplingRuleViewSet(TenantScopedMixin, ListMetadataMixin, ExcelExportMixin, viewsets.ModelViewSet):
    queryset = SamplingRule.objects.all()
    serializer_class = SamplingRuleSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ["ruleset", "rule_type"]
    ordering_fields = ["id", "order", "created_at"]
    ordering = ["order"]
    search_fields = ["rule_type", "ruleset__name"]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return SamplingRule.objects.none()

        # Apply tenant scoping first, then user filtering
        qs = super().get_queryset()
        return qs


class MeasurementsDefinitionViewSet(TenantScopedMixin, ListMetadataMixin, ExcelExportMixin, viewsets.ModelViewSet):
    queryset = MeasurementDefinition.objects.all()
    serializer_class = MeasurementDefinitionSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ["step__name", "label", "step"]
    ordering_fields = ["step__name", "label"]
    ordering = ["label"]
    search_fields = ["label", "step__name", "step"]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return MeasurementDefinition.objects.none()

        # Apply tenant scoping first, then user filtering
        qs = super().get_queryset()
        return qs


# ===== NOTIFICATION VIEWSETS =====

@extend_schema_view(list=extend_schema(description="List user's notification preferences", parameters=[
    OpenApiParameter(name='notification_type', description='Filter by notification type', required=False, type=str),
    OpenApiParameter(name='channel_type', description='Filter by channel type (email, in_app, sms)', required=False,
                     type=str),
    OpenApiParameter(name='status', description='Filter by status (pending, sent, failed, cancelled)', required=False,
                     type=str), ]),
                    create=extend_schema(description="Create a new notification preference for the current user",
                                         request=NotificationPreferenceSerializer,
                                         responses={201: NotificationPreferenceSerializer}),
                    retrieve=extend_schema(description="Retrieve a specific notification preference"),
                    update=extend_schema(description="Update a notification preference",
                                         request=NotificationPreferenceSerializer,
                                         responses={200: NotificationPreferenceSerializer}),
                    partial_update=extend_schema(description="Partially update a notification preference",
                                                 request=NotificationPreferenceSerializer,
                                                 responses={200: NotificationPreferenceSerializer}),
                    destroy=extend_schema(description="Delete a notification preference"))
class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user notification preferences.

    Provides CRUD operations for notification preferences including:
    - Weekly order reports (recurring, fixed schedule)
    - CAPA reminders (escalating, deadline-based)

    Automatically handles timezone conversion between user's local time and UTC.

    Permissions:
    - Users can only see and manage their own notification preferences
    - Only authenticated users can access this endpoint
    """
    serializer_class = NotificationPreferenceSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['notification_type', 'channel_type', 'status']
    ordering_fields = ['created_at', 'updated_at', 'next_send_at']
    ordering = ['-created_at']
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        """
        Filter notifications to only show current user's preferences.
        Excludes system-managed notifications (e.g., CAPA reminders created by signals).
        """
        if getattr(self, 'swagger_fake_view', False):
            return NotificationTask.objects.none()

        # Users can only see their own notification preferences
        return NotificationTask.objects.filter(recipient=self.request.user,
                                               # Optionally filter to only user-configurable types
                                               notification_type='WEEKLY_REPORT'
                                               # For now, only weekly reports are user-configurable
                                               ).select_related('recipient')

    def perform_create(self, serializer):
        """Create notification preference for current user."""
        serializer.save()

    def perform_destroy(self, instance):
        """
        Soft delete: Cancel the notification instead of hard deleting.
        This preserves history and allows for audit logging.
        """
        instance.status = 'cancelled'
        instance.save()

    @extend_schema(description="Get available notification types that users can configure", responses={
        200: inline_serializer(name='AvailableNotificationTypes',
                               fields={'notification_types': serializers.ListField(child=serializers.DictField())})})
    @action(detail=False, methods=['get'], url_path='available-types')
    def available_types(self, request):
        """
        Return list of notification types that users can configure.

        Returns:
            {
                "notification_types": [
                    {
                        "value": "WEEKLY_REPORT",
                        "label": "Weekly Order Report",
                        "description": "Receive weekly updates on your active orders",
                        "configurable": true,
                        "supported_channels": ["email", "in_app"]
                    }
                ]
            }
        """
        types = [{"value": "WEEKLY_REPORT", "label": "Weekly Order Report",
                  "description": "Receive weekly updates on your active orders", "configurable": True,
                  "supported_channels": ["email", "in_app"], "interval_type": "fixed"},
                 # CAPA reminders are system-managed, not user-configurable
                 {"value": "CAPA_REMINDER", "label": "CAPA Reminder",
                  "description": "Reminders for pending CAPA actions (system-managed)", "configurable": False,
                  "supported_channels": ["email", "in_app"], "interval_type": "deadline_based"}]

        return Response({"notification_types": types})

    @extend_schema(description="Test send a notification immediately (for testing purposes)", request=None, responses={
        200: inline_serializer(name='TestSendResponse',
                               fields={'status': serializers.CharField(), 'message': serializers.CharField()})})
    @action(detail=True, methods=['post'], url_path='test-send')
    def test_send(self, request, pk=None):
        """
        Send a test notification immediately (bypasses normal scheduling).

        Useful for testing notification templates and delivery.
        """
        notification = self.get_object()

        # Import here to avoid circular imports
        from Tracker.notifications import get_notification_handler

        try:
            # Get the handler
            handler = get_notification_handler(notification.notification_type)

            # Check if can send
            if not handler.should_send(notification):
                return Response({"status": "error", "message": "Notification validation failed"},
                                status=status.HTTP_400_BAD_REQUEST)

            # Send it
            success = handler.send(notification)

            if success:
                return Response(
                    {"status": "success", "message": f"Test notification sent to {notification.recipient.email}"})
            else:
                return Response({"status": "error", "message": "Failed to send notification"},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ===== CAPA VIEWSETS =====

@extend_schema_view(
    list=extend_schema(
        description="List CAPAs with filtering and search",
        parameters=[
            OpenApiParameter(name='status', description='Filter by status', required=False, type=str),
            OpenApiParameter(name='capa_type', description='Filter by CAPA type (CORRECTIVE, PREVENTIVE)', required=False,
                             type=str),
            OpenApiParameter(name='severity', description='Filter by severity (LOW, MEDIUM, HIGH, CRITICAL)',
                             required=False, type=str),
            OpenApiParameter(name='assigned_to', description='Filter by assigned user ID', required=False, type=int),
            OpenApiParameter(name='overdue', description='Show only overdue CAPAs', required=False, type=bool),
        ]
    ),
    create=extend_schema(description="Create a new CAPA"),
    retrieve=extend_schema(description="Retrieve a specific CAPA"),
    update=extend_schema(description="Update a CAPA"),
    partial_update=extend_schema(description="Partially update a CAPA"),
    destroy=extend_schema(description="Soft delete a CAPA")
)
class CAPAViewSet(TenantScopedMixin, ListMetadataMixin, ExcelExportMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing CAPAs (Corrective and Preventive Actions).

    CAPAs track the full lifecycle from problem identification through
    root cause analysis, corrective actions, verification, and closure.
    """
    queryset = CAPA.objects.all()
    serializer_class = CAPASerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'capa_type', 'severity', 'assigned_to', 'initiated_by']
    search_fields = ['capa_number', 'problem_statement', 'immediate_action']
    ordering_fields = ['initiated_date', 'due_date', 'completed_date', 'capa_number', 'severity']
    ordering = ['-initiated_date']
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return CAPA.objects.none()

        # Apply tenant scoping first, then user filtering
        queryset = super().get_queryset()
        queryset = queryset.select_related(
            'initiated_by', 'assigned_to', 'verified_by', 'approved_by'
        ).prefetch_related(
            'tasks', 'rca_records', 'verifications'
        )

        # Filter for overdue CAPAs if requested
        overdue = self.request.query_params.get('overdue', '').lower() == 'true'
        if overdue:
            queryset = [capa for capa in queryset if capa.is_overdue()]
            # Convert back to queryset
            ids = [capa.id for capa in queryset]
            queryset = self.qs_for_user(CAPA).filter(id__in=ids)

        # Filter for CAPAs needing current user's approval
        needs_my_approval = self.request.query_params.get('needs_my_approval', '').lower() == 'true'
        if needs_my_approval:
            from Tracker.models.core import ApprovalRequest
            from django.contrib.contenttypes.models import ContentType

            capa_ct = ContentType.objects.get_for_model(CAPA)
            user = self.request.user

            # Find pending approval requests for CAPAs where user is an approver (tenant-scoped groups)
            user_groups = user.get_tenant_groups() if hasattr(user, 'get_tenant_groups') else []
            user_group_ids = [g.id for g in user_groups]
            pending_approval_capa_ids = self.qs_for_user(ApprovalRequest).filter(
                content_type=capa_ct,
                status='PENDING'
            ).filter(
                models.Q(approver_assignments__user=user) |
                models.Q(group_assignments__group_id__in=user_group_ids)
            ).exclude(
                responses__approver=user  # Exclude if user already responded
            ).values_list('object_id', flat=True).distinct()

            # Convert string object_ids to UUIDs for proper comparison
            from uuid import UUID
            uuid_ids = [UUID(oid) for oid in pending_approval_capa_ids if oid]
            queryset = queryset.filter(id__in=uuid_ids)

        return queryset

    def perform_create(self, serializer):
        """Auto-generate CAPA number and set initiated_by"""
        from django.utils import timezone
        capa_type = serializer.validated_data.get('capa_type')
        initiated_date = timezone.now().date()
        serializer.save(
            initiated_by=self.request.user,
            capa_number=CAPA.generate_capa_number(capa_type, initiated_date)
        )

    @action(detail=True, methods=['get'], url_path='blocking-items')
    def blocking_items(self, request, pk=None):
        """Get list of blocking items preventing closure"""
        capa = self.get_object()
        blocking = capa.get_blocking_items()
        return Response({'blocking_items': blocking})

    @action(detail=True, methods=['get'], url_path='completion-percentage')
    def completion_percentage(self, request, pk=None):
        """Get completion percentage of CAPA tasks"""
        capa = self.get_object()
        percentage = capa.get_completion_percentage()
        return Response({'completion_percentage': percentage})

    @extend_schema(
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'total': {'type': 'integer'},
                    'by_status': {
                        'type': 'object',
                        'properties': {
                            'open': {'type': 'integer'},
                            'in_progress': {'type': 'integer'},
                            'pending_verification': {'type': 'integer'},
                            'closed': {'type': 'integer'},
                        }
                    },
                    'by_severity': {
                        'type': 'object',
                        'properties': {
                            'CRITICAL': {'type': 'integer'},
                            'MAJOR': {'type': 'integer'},
                            'MINOR': {'type': 'integer'},
                        }
                    },
                    'overdue': {'type': 'integer'},
                }
            }
        }
    )
    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """Get aggregated CAPA statistics for dashboard display"""
        from django.utils import timezone
        from Tracker.models.qms import CapaStatus, CapaSeverity

        # Use the viewset's get_queryset() for proper tenant filtering
        # (same filtering as the list endpoint)
        base_queryset = super().get_queryset().prefetch_related('tasks', 'rca_records', 'verifications')
        capas = list(base_queryset)
        today = timezone.now().date()

        # Count by computed status
        by_status = {
            'open': 0,
            'in_progress': 0,
            'pending_verification': 0,
            'closed': 0,
        }
        by_severity = {
            'CRITICAL': 0,
            'MAJOR': 0,
            'MINOR': 0,
        }
        overdue_count = 0

        for capa in capas:
            # Status counts
            computed_status = capa.computed_status
            if computed_status == CapaStatus.OPEN:
                by_status['open'] += 1
            elif computed_status == CapaStatus.IN_PROGRESS:
                by_status['in_progress'] += 1
            elif computed_status == CapaStatus.PENDING_VERIFICATION:
                by_status['pending_verification'] += 1
            elif computed_status == CapaStatus.CLOSED:
                by_status['closed'] += 1

            # Severity counts (ALL CAPAs, not just non-closed)
            severity = capa.severity
            if severity in by_severity:
                by_severity[severity] += 1

            # Overdue count (only for non-closed with due date)
            if computed_status != CapaStatus.CLOSED and capa.due_date and capa.due_date < today:
                overdue_count += 1

        return Response({
            'total': len(capas),
            'by_status': by_status,
            'by_severity': by_severity,
            'overdue': overdue_count,
        })

    @action(detail=False, methods=['get'], url_path='my-assigned')
    def my_assigned(self, request):
        """Get all CAPAs assigned to current user"""
        user = request.user
        assigned_capas = self.qs_for_user(CAPA).filter(assigned_to=user).exclude(status='CLOSED')

        page = self.paginate_queryset(assigned_capas)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(assigned_capas, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='request-approval')
    def request_approval(self, request, pk=None):
        """Manually request approval for CAPA (typically for Critical/Major severity)"""
        capa = self.get_object()

        try:
            approval_request = capa.request_approval(request.user)
            from Tracker.serializers.core import ApprovalRequestSerializer
            return Response(
                ApprovalRequestSerializer(approval_request, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to request approval: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema_view(
    list=extend_schema(
        description="List CAPA tasks with filtering",
        parameters=[
            OpenApiParameter(name='capa', description='Filter by CAPA UUID', required=False, type=str),
            OpenApiParameter(name='status', description='Filter by status', required=False, type=str),
            OpenApiParameter(name='task_type', description='Filter by task type', required=False, type=str),
            OpenApiParameter(name='assigned_to', description='Filter by assigned user ID', required=False, type=int),
            OpenApiParameter(name='overdue', description='Show only overdue tasks', required=False, type=bool),
        ]
    ),
    create=extend_schema(description="Create a new CAPA task"),
    retrieve=extend_schema(description="Retrieve a specific CAPA task"),
    update=extend_schema(description="Update a CAPA task"),
    partial_update=extend_schema(description="Partially update a CAPA task"),
    destroy=extend_schema(description="Soft delete a CAPA task")
)
class CapaTasksViewSet(TenantScopedMixin, ListMetadataMixin, ExcelExportMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing CAPA tasks.

    Individual action items within a CAPA workflow, with assignment tracking,
    due dates, and completion verification.
    """
    queryset = CapaTasks.objects.all()
    serializer_class = CapaTasksSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['capa', 'status', 'task_type', 'assigned_to', 'completion_mode']
    search_fields = ['task_number', 'description', 'completion_notes']
    ordering_fields = ['due_date', 'completed_at', 'task_number']
    ordering = ['due_date']
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return CapaTasks.objects.none()

        # Apply tenant scoping first, then user filtering
        queryset = super().get_queryset()
        queryset = queryset.select_related(
            'capa', 'assigned_to', 'completed_by'
        ).prefetch_related('assignees')

        # Filter for overdue tasks if requested
        overdue = self.request.query_params.get('overdue', '').lower() == 'true'
        if overdue:
            queryset = [task for task in queryset if task.is_overdue()]
            # Convert back to queryset
            ids = [task.id for task in queryset]
            queryset = self.qs_for_user(CapaTasks).filter(id__in=ids)

        return queryset

    def perform_create(self, serializer):
        """Create task - task_number auto-generated by CapaTasks.save()"""
        capa = serializer.validated_data.get('capa')
        # Ensure tenant is set for proper sequence generation
        serializer.save(tenant=capa.tenant if capa else None)

    @action(detail=True, methods=['post'], url_path='complete')
    def complete_task(self, request, pk=None):
        """Mark task as complete

        If task.requires_signature is True, signature_data and password are required.
        """
        task = self.get_object()

        completion_notes = request.data.get('completion_notes')
        signature_data = request.data.get('signature_data')
        password = request.data.get('password')

        try:
            task.mark_completed(
                user=request.user,
                notes=completion_notes,
                signature_data=signature_data,
                password=password
            )
            return Response(CapaTasksSerializer(task).data)

        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @extend_schema(
        description="Get all tasks assigned to current user",
        responses={200: CapaTasksSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='my-tasks')
    def my_tasks(self, request):
        """Get all tasks assigned to current user"""
        user = request.user
        my_tasks = self.qs_for_user(CapaTasks).filter(assigned_to=user).exclude(status='COMPLETED')

        page = self.paginate_queryset(my_tasks)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(my_tasks, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        description="List RCA records with filtering",
        parameters=[
            OpenApiParameter(name='capa', description='Filter by CAPA UUID', required=False, type=str),
            OpenApiParameter(name='rca_method', description='Filter by RCA method (FIVE_WHYS, FISHBONE, etc.)',
                             required=False, type=str),
            OpenApiParameter(name='rca_review_status', description='Filter by RCA review status', required=False, type=str),
        ]
    ),
    create=extend_schema(description="Create a new RCA record"),
    retrieve=extend_schema(description="Retrieve a specific RCA record"),
    update=extend_schema(description="Update an RCA record"),
    partial_update=extend_schema(description="Partially update an RCA record"),
    destroy=extend_schema(description="Soft delete an RCA record")
)
class RcaRecordViewSet(TenantScopedMixin, ListMetadataMixin, ExcelExportMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing Root Cause Analysis records.

    Tracks RCA methodology (5 Whys, Fishbone, etc.) and findings for CAPAs.
    """
    queryset = RcaRecord.objects.all()
    serializer_class = RcaRecordSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['capa', 'rca_method', 'rca_review_status', 'conducted_by', 'root_cause_verified_by']
    ordering_fields = ['conducted_date', 'root_cause_verified_at']
    ordering = ['-conducted_date']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return RcaRecord.objects.none()

        # Apply tenant scoping first, then user filtering
        qs = super().get_queryset()
        return qs.select_related(
            'capa', 'conducted_by', 'root_cause_verified_by'
        ).prefetch_related('root_causes', 'five_whys', 'fishbone')

    @action(detail=True, methods=['post'], url_path='submit-for-review')
    def submit_for_review(self, request, pk=None):
        """Submit RCA for review"""
        rca = self.get_object()

        try:
            rca.rca_review_status = 'PENDING'
            rca.save(update_fields=['rca_review_status'])
            return Response(RcaRecordSerializer(rca).data)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], url_path='approve')
    def approve_rca(self, request, pk=None):
        """Approve RCA record"""
        # Check permission
        if not request.user.has_tenant_perm('review_rca'):
            return Response(
                {'error': 'You do not have permission to review RCA records'},
                status=status.HTTP_403_FORBIDDEN
            )

        rca = self.get_object()

        try:
            rca.root_cause_verification_status = 'VERIFIED'
            rca.root_cause_verified_by = request.user
            rca.root_cause_verified_at = timezone.now()
            rca.save(update_fields=['root_cause_verification_status', 'root_cause_verified_by', 'root_cause_verified_at'])
            return Response(RcaRecordSerializer(rca).data)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


@extend_schema_view(
    list=extend_schema(
        description="List CAPA verifications with filtering",
        parameters=[
            OpenApiParameter(name='capa', description='Filter by CAPA UUID', required=False, type=str),
            OpenApiParameter(name='effectiveness_result', description='Filter by effectiveness result', required=False,
                             type=str),
        ]
    ),
    create=extend_schema(description="Create a new CAPA verification"),
    retrieve=extend_schema(description="Retrieve a specific CAPA verification"),
    update=extend_schema(description="Update a CAPA verification"),
    partial_update=extend_schema(description="Partially update a CAPA verification"),
    destroy=extend_schema(description="Soft delete a CAPA verification")
)
class CapaVerificationViewSet(TenantScopedMixin, ListMetadataMixin, ExcelExportMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing CAPA verifications.

    Tracks verification of CAPA effectiveness with findings and evidence.
    """
    queryset = CapaVerification.objects.all()
    serializer_class = CapaVerificationSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['capa', 'effectiveness_result', 'verified_by']
    ordering_fields = ['verification_date']
    ordering = ['-verification_date']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return CapaVerification.objects.none()

        # Apply tenant scoping first, then user filtering
        qs = super().get_queryset()
        return qs.select_related(
            'capa', 'verified_by'
        )


# ===== RCA DETAIL VIEWSETS (FiveWhys & Fishbone) =====

@extend_schema_view(
    list=extend_schema(
        description="List 5 Whys analyses with filtering",
        parameters=[
            OpenApiParameter(name='rca_record', description='Filter by RCA record UUID', required=False, type=str),
        ]
    ),
    create=extend_schema(description="Create a new 5 Whys analysis"),
    retrieve=extend_schema(description="Retrieve a specific 5 Whys analysis"),
    update=extend_schema(description="Update a 5 Whys analysis"),
    partial_update=extend_schema(description="Partially update a 5 Whys analysis"),
    destroy=extend_schema(description="Delete a 5 Whys analysis")
)
class FiveWhysViewSet(TenantScopedMixin, ListMetadataMixin, ExcelExportMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing 5 Whys root cause analyses.

    The 5 Whys is an iterative interrogative technique used to explore
    the cause-and-effect relationships underlying a particular problem.
    """
    queryset = FiveWhys.objects.all()
    serializer_class = FiveWhysSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['rca_record']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return FiveWhys.objects.none()

        # Apply tenant scoping first, then user filtering
        qs = super().get_queryset()
        return qs.select_related(
            'rca_record', 'rca_record__capa'
        )


@extend_schema_view(
    list=extend_schema(
        description="List Fishbone diagrams with filtering",
        parameters=[
            OpenApiParameter(name='rca_record', description='Filter by RCA record UUID', required=False, type=str),
        ]
    ),
    create=extend_schema(description="Create a new Fishbone diagram"),
    retrieve=extend_schema(description="Retrieve a specific Fishbone diagram"),
    update=extend_schema(description="Update a Fishbone diagram"),
    partial_update=extend_schema(description="Partially update a Fishbone diagram"),
    destroy=extend_schema(description="Delete a Fishbone diagram")
)
class FishboneViewSet(TenantScopedMixin, ListMetadataMixin, ExcelExportMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing Fishbone (Ishikawa) diagrams.

    The Fishbone diagram organizes potential causes into 6M categories:
    Man, Machine, Material, Method, Measurement, and Environment.
    """
    queryset = Fishbone.objects.all()
    serializer_class = FishboneSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['rca_record']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Fishbone.objects.none()

        # Apply tenant scoping first, then user filtering
        qs = super().get_queryset()
        return qs.select_related(
            'rca_record', 'rca_record__capa'
        )


# ===== 3D MODEL VIEWSETS =====

@extend_schema_view(
    create=extend_schema(request={'multipart/form-data': ThreeDModelSerializer}),
    update=extend_schema(request={'multipart/form-data': ThreeDModelSerializer}),
    partial_update=extend_schema(request={'multipart/form-data': ThreeDModelSerializer}),
    list=extend_schema(
        description="List 3D models with filtering and search capabilities",
        parameters=[
            OpenApiParameter(name='part', description='Filter by part UUID', required=False, type=str),
            OpenApiParameter(name='process', description='Filter by process UUID', required=False, type=str),
            OpenApiParameter(name='file_type', description='Filter by file type (e.g., glb, gltf)', required=False,
                             type=str),
            OpenApiParameter(name='ordering', description='Order by field (prepend "-" for descending)', required=False,
                             type=str),
        ]
    )
)
class ThreeDModelViewSet(TenantScopedMixin, ListMetadataMixin, ExcelExportMixin, viewsets.ModelViewSet):
    """ViewSet for managing 3D model files for quality visualization"""
    queryset = ThreeDModel.objects.all()
    serializer_class = ThreeDModelSerializer
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, OrderingFilter]
    filterset_fields = {
        'part_type': ['exact'],
        'step': ['exact'],
        'file_type': ['exact', 'icontains'],
        'uploaded_at': ['gte', 'lte', 'exact'],
    }
    search_fields = ['name', 'file_type', 'part_type__name', 'step__step_name']
    ordering_fields = ['uploaded_at', 'name', 'file_type']
    ordering = ['name']

    def get_queryset(self):
        """Apply tenant scoping first, then SecureModel filtering for user-specific access"""
        if getattr(self, 'swagger_fake_view', False):
            return ThreeDModel.objects.none()
        qs = super().get_queryset()
        return qs.select_related('part_type', 'step')



# ===== HEATMAP ANNOTATION VIEWSETS =====

@extend_schema_view(
    list=extend_schema(
        description="List heatmap annotations with filtering and search capabilities",
        parameters=[
            OpenApiParameter(name='model', description='Filter by 3D model UUID', required=False, type=str),
            OpenApiParameter(name='part', description='Filter by part UUID', required=False, type=str),
            OpenApiParameter(name='severity', description='Filter by severity (low, medium, high, critical)',
                             required=False, type=str),
            OpenApiParameter(name='defect_type', description='Filter by defect type', required=False, type=str),
            OpenApiParameter(name='ordering', description='Order by field (prepend "-" for descending)', required=False,
                             type=str),
        ]
    ),
    create=extend_schema(description="Create a new heatmap annotation on a 3D model"),
    retrieve=extend_schema(description="Retrieve a specific heatmap annotation"),
    update=extend_schema(description="Update a heatmap annotation"),
    partial_update=extend_schema(description="Partially update a heatmap annotation"),
    destroy=extend_schema(description="Soft delete a heatmap annotation")
)
class HeatMapAnnotationsViewSet(TenantScopedMixin, ListMetadataMixin, ExcelExportMixin, viewsets.ModelViewSet):
    """ViewSet for managing heatmap annotations on 3D models for quality inspection"""
    queryset = HeatMapAnnotations.objects.all()
    serializer_class = HeatMapAnnotationsSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, OrderingFilter]
    filterset_fields = {
        'model': ['exact'],
        'part': ['exact'],
        'defect_type': ['exact', 'icontains'],
        'severity': ['exact'],
        'created_by': ['exact'],
        'created_at': ['gte', 'lte', 'exact'],
        'updated_at': ['gte', 'lte'],
        'measurement_value': ['gte', 'lte', 'exact'],
        'part__work_order': ['exact'],
        'model__file_type': ['exact'],
    }
    search_fields = ['notes', 'defect_type', 'part__ERP_id', 'model__name']
    ordering_fields = ['created_at', 'updated_at', 'severity', 'measurement_value']
    ordering = ['-created_at']

    def get_queryset(self):
        """Apply tenant scoping first, then SecureModel filtering for user-specific access"""
        if getattr(self, 'swagger_fake_view', False):
            return HeatMapAnnotations.objects.none()
        qs = super().get_queryset()
        return qs.select_related('model', 'part', 'created_by')

    @extend_schema(
        parameters=[
            OpenApiParameter(name='model', type=str, description='Filter by 3D model UUID'),
            OpenApiParameter(name='part', type=str, description='Filter by part UUID'),
            OpenApiParameter(name='part__work_order', type=str, description='Filter by work order UUID'),
            OpenApiParameter(name='created_at__gte', type=str, description='Filter by created date (start)'),
            OpenApiParameter(name='created_at__lte', type=str, description='Filter by created date (end)'),
        ],
        responses={
            200: inline_serializer(
                name='HeatMapFacetsResponse',
                fields={
                    'defect_types': serializers.ListSerializer(child=inline_serializer(
                        name='DefectTypeFacet',
                        fields={
                            'value': serializers.CharField(),
                            'count': serializers.IntegerField(),
                        }
                    )),
                    'severities': serializers.ListSerializer(child=inline_serializer(
                        name='SeverityFacet',
                        fields={
                            'value': serializers.CharField(),
                            'count': serializers.IntegerField(),
                        }
                    )),
                    'total_count': serializers.IntegerField(),
                }
            )
        }
    )
    @action(detail=False, methods=['get'])
    def facets(self, request):
        """
        Returns aggregated facet counts for defect_type and severity.
        Accepts the same filter parameters as the list endpoint for efficient filtering.
        """
        queryset = self.get_queryset()

        # Apply filters manually (same as filterset_fields)
        model_id = request.query_params.get('model')
        part_id = request.query_params.get('part')
        work_order_id = request.query_params.get('part__work_order')
        created_gte = request.query_params.get('created_at__gte')
        created_lte = request.query_params.get('created_at__lte')

        if model_id:
            queryset = queryset.filter(model_id=model_id)
        if part_id:
            queryset = queryset.filter(part_id=part_id)
        if work_order_id:
            queryset = queryset.filter(part__work_order_id=work_order_id)
        if created_gte:
            queryset = queryset.filter(created_at__gte=created_gte)
        if created_lte:
            queryset = queryset.filter(created_at__lte=created_lte)

        # Aggregate defect types
        defect_types = list(
            queryset.exclude(defect_type__isnull=True)
            .exclude(defect_type='')
            .values('defect_type')
            .annotate(count=models.Count('id'))
            .order_by('-count')
        )

        # Aggregate severities
        severities = list(
            queryset.exclude(severity__isnull=True)
            .exclude(severity='')
            .values('severity')
            .annotate(count=models.Count('id'))
            .order_by('-count')
        )

        return Response({
            'defect_types': [{'value': d['defect_type'], 'count': d['count']} for d in defect_types],
            'severities': [{'value': s['severity'], 'count': s['count']} for s in severities],
            'total_count': queryset.count(),
        })

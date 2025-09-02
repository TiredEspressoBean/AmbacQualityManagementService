import csv
import io
import os
from collections import Counter

import pandas as pd
from auditlog.models import LogEntry
from dj_rest_auth.views import UserDetailsView
from django.db.models import Count
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Group
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema_view, inline_serializer, OpenApiResponse, OpenApiRequest, \
    OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import viewsets, status, filters, serializers, parsers
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.generics import ListAPIView
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.views import APIView
from django.http import FileResponse, Http404
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_exempt
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

from Tracker.filters import *
from Tracker.serializer import *
from Tracker.models import *


def with_int_pk_schema(cls):
    return extend_schema_view(
        retrieve=extend_schema(parameters=[OpenApiParameter(name='id', type=int, location=OpenApiParameter.PATH)]),
        update=extend_schema(parameters=[OpenApiParameter(name='id', type=int, location=OpenApiParameter.PATH)]),
        partial_update=extend_schema(
            parameters=[OpenApiParameter(name='id', type=int, location=OpenApiParameter.PATH)]),
        destroy=extend_schema(parameters=[OpenApiParameter(name='id', type=int, location=OpenApiParameter.PATH)]), )(
        cls)


@with_int_pk_schema
class TrackerOrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrdersSerializer  # Updated to match serializers.py
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Orders.objects.none()

        # Use SecureManager for user filtering
        return Orders.objects.for_user(self.request.user)

    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


class PartsByOrderView(ListAPIView):
    serializer_class = PartsSerializer
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Parts.objects.none()

        order_id = self.kwargs["order_id"]
        # Use SecureManager for user filtering
        return Parts.objects.for_user(self.request.user).filter(order__id=order_id)


@extend_schema_view(list=extend_schema(parameters=[
    OpenApiParameter(name='ordering', description='Which field to order by, prepend "-" for descending.',
                     required=False, type=str), ]))
@extend_schema(parameters=[
    OpenApiParameter(name='status__in', description='Filter by multiple status values.', required=False,
                     type={'type': 'array', 'items': {'type': 'string'}},  # manual override
                     style='form', explode=True, )])

class PartsViewSet(viewsets.ModelViewSet):
    serializer_class = PartsSerializer
    pagination_class = LimitOffsetPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter, filters.SearchFilter]
    filterset_class = PartFilter
    ordering_fields = ['created_at', 'ERP_id', 'part_status']  # Updated field name
    ordering = ['-created_at']
    search_fields = ["ERP_id", "order__name", "work_order__ERP_id", "step__name", "part_type__name", "part_status", ]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Parts.objects.none()

        # Use SecureManager for user filtering
        return Parts.objects.for_user(self.request.user)

    @extend_schema(request=None, responses={
        200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="Step increment response")})
    @action(detail=True, methods=["post"])
    def increment(self, request, pk=None):
        part = self.get_object()
        serializer = StepAdvancementSerializer(part, data=request.data)  # Updated serializer name
        serializer.is_valid(raise_exception=True)
        try:
            result = part.increment_step()
            return Response({"detail": f"Step {result}."})
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class OrdersViewSet(viewsets.ModelViewSet):
    serializer_class = OrdersSerializer
    pagination_class = LimitOffsetPagination

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = OrderFilter
    ordering_fields = ["created_at", "order_status", "name", "estimated_completion"]  # Updated field name
    ordering = ["-created_at"]
    search_fields = ["name", "company__name", "customer__first_name", "customer__last_name"]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Orders.objects.none()

        # Use SecureManager for user filtering
        return Orders.objects.for_user(self.request.user)

    def get_filter_backends(self):
        # disable filters for specific actions
        if self.action == "step_distribution":
            return []
        return super().get_filter_backends()

    @extend_schema(parameters=[  # Exclude unrelated filters
        OpenApiParameter(name='archived', location=OpenApiParameter.QUERY, exclude=True),
        OpenApiParameter(name='company', location=OpenApiParameter.QUERY, exclude=True),
        OpenApiParameter(name='created_at__gte', location=OpenApiParameter.QUERY, exclude=True),
        OpenApiParameter(name='created_at__lte', location=OpenApiParameter.QUERY, exclude=True),
        OpenApiParameter(name='customer', location=OpenApiParameter.QUERY, exclude=True),
        OpenApiParameter(name='estimated_completion__gte', location=OpenApiParameter.QUERY, exclude=True),
        OpenApiParameter(name='estimated_completion__lte', location=OpenApiParameter.QUERY, exclude=True),
        OpenApiParameter(name='ordering', location=OpenApiParameter.QUERY, exclude=True),
        OpenApiParameter(name='status', location=OpenApiParameter.QUERY, exclude=True),
        # Keep these two for pagination
        OpenApiParameter(name='limit', location=OpenApiParameter.QUERY, required=False, type=int),
        OpenApiParameter(name='offset', location=OpenApiParameter.QUERY, required=False, type=int), ],
        responses=inline_serializer(name="StepDistributionResponse",
                                    fields={"id": serializers.IntegerField(), "count": serializers.IntegerField(),
                                            "name": serializers.CharField(), }, many=True))
    @action(detail=True, methods=['get'], url_path='step-distribution')
    def step_distribution(self, request, pk=None):
        order = self.get_object()
        # Use model method instead of manual logic
        result = order.get_step_distribution()
        paginated = self.paginate_queryset(result)
        return self.get_paginated_response(paginated)

    @extend_schema(request=inline_serializer(name="StepIncrementInput", fields={"step_id": serializers.IntegerField()}),
                   responses=inline_serializer(name="StepIncrementResponse",
                                               fields={"advanced": serializers.IntegerField(),
                                                       "total": serializers.IntegerField()}))
    @action(detail=True, methods=['post'], url_path='increment-step')
    def increment_parts_step(self, request, pk=None):
        step_id = request.data.get("step_id")

        if not step_id:
            return Response({"detail": "Missing step_id"}, status=status.HTTP_400_BAD_REQUEST)

        order = self.get_object()

        # Use model method for bulk step advancement
        serializer = BulkStepAdvancementSerializer(data={"step_id": step_id})
        serializer.is_valid(raise_exception=True)

        try:
            result = order.bulk_increment_parts_at_step(step_id)
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(request=BulkSoftDeleteSerializer, responses={200: OpenApiTypes.OBJECT})
    @action(detail=True, methods=['post'], url_path='parts/bulk-remove')
    def bulk_remove_parts(self, request, pk=None):
        serializer = BulkSoftDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order = self.get_object()
        # Use model method for bulk removal
        result = order.bulk_remove_parts(serializer.validated_data['ids'])
        return Response(result, status=status.HTTP_200_OK)

    @extend_schema(request=inline_serializer(name="BulkAddPartsInput", fields={
        "part_type": serializers.PrimaryKeyRelatedField(queryset=PartTypes.objects.all()),
        "step": serializers.PrimaryKeyRelatedField(queryset=Steps.objects.all()),
        "quantity": serializers.IntegerField(),
        "part_status": serializers.ChoiceField(choices=PartsStatus.choices, default=PartsStatus.PENDING),
        "work_order": serializers.PrimaryKeyRelatedField(queryset=WorkOrder.objects.all(), required=False),
        "erp_id_start": serializers.IntegerField(default=1)
    }), responses={201: OpenApiTypes.OBJECT})
    @action(detail=True, methods=["post"], url_path="parts/bulk-add")
    def bulk_add_parts(self, request, pk=None):
        order = self.get_object()

        # Validate input data
        part_type_id = request.data.get('part_type')
        step_id = request.data.get('step')
        quantity = request.data.get('quantity')
        part_status = request.data.get('part_status', PartsStatus.PENDING)
        work_order_id = request.data.get('work_order')
        erp_id_start = request.data.get('erp_id_start', 1)

        if not all([part_type_id, step_id, quantity]):
            return Response({"detail": "Missing required fields: part_type, step, quantity"},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            part_type = PartTypes.objects.get(id=part_type_id)
            step = Steps.objects.get(id=step_id)
            work_order = WorkOrder.objects.get(id=work_order_id) if work_order_id else None

            # Use model method for bulk creation
            result = order.bulk_add_parts(
                part_type=part_type,
                step=step,
                quantity=int(quantity),
                part_status=part_status,
                work_order=work_order,
                erp_id_start=int(erp_id_start)
            )
            return Response(result, status=status.HTTP_201_CREATED)

        except (PartTypes.DoesNotExist, Steps.DoesNotExist, WorkOrder.DoesNotExist) as e:
            return Response({"detail": f"Invalid reference: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class QualityReportViewSet(viewsets.ModelViewSet):
    serializer_class = QualityReportsSerializer  # Updated to match model name pattern
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return QualityReports.objects.none()

        # Use SecureManager for user filtering
        return QualityReports.objects.for_user(self.request.user)


class EmployeeSelectViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserSelectSerializer  # Updated to match existing serializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return User.objects.none()

        return User.objects.filter(is_staff=True)


class EquipmentSelectViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EquipmentsSerializer  # Will need to create this

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Equipments.objects.none()

        return Equipments.objects.for_user(self.request.user)


class HubspotGatesViewSet(viewsets.ModelViewSet):
    serializer_class = ExternalAPIOrderIdentifierSerializer  # Will need to create this
    pagination_class = None

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return ExternalAPIOrderIdentifier.objects.none()

        return ExternalAPIOrderIdentifier.objects.for_user(self.request.user)


class CustomerViewSet(viewsets.ModelViewSet):
    serializer_class = UserDetailSerializer  # Updated to use existing detailed serializer
    pagination_class = None

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return User.objects.none()

        return User.objects.filter(is_staff=False)


@with_int_pk_schema
class UserViewSet(viewsets.ModelViewSet):
    """Enhanced User ViewSet with comprehensive filtering, ordering, and search"""
    serializer_class = UserSerializer
    pagination_class = LimitOffsetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = UserFilter
    ordering_fields = ['username', 'first_name', 'last_name', 'email', 'date_joined', 'is_active', 'is_staff']
    ordering = ['-date_joined']
    search_fields = ['username', 'first_name', 'last_name', 'email', 'parent_company__name']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return User.objects.none()

        # User model doesn't inherit from SecureModel, so filter by company manually
        user = self.request.user
        if user.is_staff:
            # Staff users can see all users in their company or all users if no company
            if user.parent_company:
                return User.objects.filter(parent_company=user.parent_company).select_related('parent_company')
            else:
                return User.objects.all().select_related('parent_company')
        else:
            # Non-staff users can only see themselves
            return User.objects.filter(id=user.id).select_related('parent_company')

    @extend_schema(
        request=inline_serializer(name="BulkUserActivationInput", fields={
            "user_ids": serializers.ListField(child=serializers.IntegerField()),
            "is_active": serializers.BooleanField()
        }),
        responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="Bulk activation response")}
    )
    @action(detail=False, methods=['post'], url_path='bulk-activate')
    def bulk_activate(self, request):
        """Bulk activate/deactivate users"""
        user_ids = request.data.get('user_ids', [])
        is_active = request.data.get('is_active', True)
        
        if not user_ids:
            return Response({"detail": "No user IDs provided"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Filter to only users accessible by the requesting user
        queryset = self.get_queryset().filter(id__in=user_ids)
        updated_count = queryset.update(is_active=is_active)
        
        return Response({
            "detail": f"Updated {updated_count} users",
            "updated_count": updated_count,
            "is_active": is_active
        })

    @extend_schema(
        request=inline_serializer(name="BulkCompanyAssignmentInput", fields={
            "user_ids": serializers.ListField(child=serializers.IntegerField()),
            "company_id": serializers.IntegerField(allow_null=True)
        }),
        responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="Bulk company assignment response")}
    )
    @action(detail=False, methods=['post'], url_path='bulk-assign-company')
    def bulk_assign_company(self, request):
        """Bulk assign users to a company"""
        user_ids = request.data.get('user_ids', [])
        company_id = request.data.get('company_id')
        
        if not user_ids:
            return Response({"detail": "No user IDs provided"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate company exists if provided
        company = None
        if company_id:
            try:
                company = Companies.objects.for_user(self.request.user).get(id=company_id)
            except Companies.DoesNotExist:
                return Response({"detail": "Company not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Filter to only users accessible by the requesting user
        queryset = self.get_queryset().filter(id__in=user_ids)
        updated_count = queryset.update(parent_company=company)
        
        return Response({
            "detail": f"Assigned {updated_count} users to {'company' if company else 'no company'}",
            "updated_count": updated_count,
            "company_name": company.name if company else None
        })


class GroupViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Django Groups - read only for selection purposes"""
    serializer_class = GroupSerializer
    pagination_class = LimitOffsetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name']
    ordering = ['name']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Group.objects.none()
        
        # Only staff users can see groups
        if self.request.user and self.request.user.is_staff:
            return Group.objects.all()
        return Group.objects.none()


class CompanyViewSet(viewsets.ModelViewSet):
    serializer_class = CompanySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["name"]
    search_fields = ["name"]
    ordering_fields = ["created_at", "updated_at", "name"]
    ordering = ["-created_at"]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Companies.objects.none()

        return Companies.objects.for_user(self.request.user)


@extend_schema(parameters=[
    OpenApiParameter(name="process", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False,
                     description="Filter steps by process ID"),
    OpenApiParameter(name="part_type", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False,
                     description="Filter steps by process's part type ID"), ])
class StepsViewSet(viewsets.ModelViewSet):
    serializer_class = StepsSerializer  # Updated to match serializers.py
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {"process": ["exact"], "process__part_type": ["exact"]}
    search_fields = ["part_type__name", "process__name"]
    ordering_fields = ["part_type__name", "process__name"]
    ordering = ["process__name"]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Steps.objects.none()

        return Steps.objects.for_user(self.request.user)

    @extend_schema(request=StepSamplingRulesUpdateSerializer, responses={
        200: OpenApiResponse(response=StepsSerializer,
                             description="Sampling rules updated successfully.")}, methods=["POST"],
                   description="Update or create a sampling rule set for this step")
    @action(detail=True, methods=["post"])
    def update_sampling_rules(self, request, pk=None):
        """
        POST /steps/:id/update_sampling_rules/
        Body:
        {
            "rules": [...],
            "fallback_rules": [...],
            "fallback_threshold": 2,
            "fallback_duration": 5
        }
        """
        step = self.get_object()
        serializer = StepSamplingRulesUpdateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        # Use serializer method that calls model method
        ruleset = serializer.update_step_rules(step)

        return Response(
            {"detail": "Sampling rules updated successfully.", "ruleset_id": ruleset.id, "step_id": step.id},
            status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def resolved_rules(self, request, pk=None):
        """
        GET /steps/:id/resolved_rules/
        Returns the active + fallback rulesets for a given step
        """
        step = self.get_object()
        # Use model method directly
        resolved_rules = step.get_resolved_sampling_rules()

        # Return step data with resolved rules
        step_data = StepsSerializer(step, context={'request': request}).data
        step_data['resolved_sampling_rules'] = resolved_rules

        return Response(step_data)


class ProcessViewSet(viewsets.ModelViewSet):
    serializer_class = ProcessesSerializer  # Will need to create this
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["part_type"]
    search_fields = ["name", "part_type__name"]
    ordering_fields = ["created_at", "updated_at", "name"]
    ordering = ["-created_at"]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Processes.objects.none()

        return Processes.objects.for_user(self.request.user).select_related("part_type").prefetch_related("steps")


@extend_schema(parameters=[
    OpenApiParameter(name="part_type", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False,
                     description="Filter processes by associated part type ID"), ])
class PartTypeViewSet(viewsets.ModelViewSet):
    serializer_class = PartTypesSerializer  # Will need to create this (note: plural to match model)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, OrderingFilter]
    ordering_fields = ['created_at', 'name', 'updated_at', 'ID_prefix']
    ordering = ['-created_at']
    search_fields = ["name", "ID_prefix"]
    filterset_fields = ['name']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return PartTypes.objects.none()

        return PartTypes.objects.for_user(self.request.user)


class WorkOrderViewSet(viewsets.ModelViewSet):
    serializer_class = WorkOrderSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ["related_order"]
    ordering_fields = ["created_at", "expected_completion", "ERP_id"]
    search_fields = ["ERP_id", "related_order__name", "notes"]  # Updated field reference

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return WorkOrder.objects.none()

        return WorkOrder.objects.for_user(self.request.user)

    @extend_schema(
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "file": {
                        "type": "string",
                        "format": "binary",
                        "description": "CSV or XLSX file containing work order rows"
                    }
                },
                "required": ["file"]
            }
        },
        responses={
            207: OpenApiResponse(
                description="Multi-status response with per-row success/failure",
                response=OpenApiTypes.OBJECT
            )
        },
        operation_id="api_WorkOrders_upload_csv_create",
        tags=["WorkOrders"]
    )
    @action(detail=False, methods=["post"], parser_classes=[MultiPartParser])
    def upload_csv(self, request):
        import chardet

        file = request.FILES.get("file")
        if not file:
            return Response({"detail": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)

        filename = file.name.lower()
        results = []

        # Mapping from messy Excel headers to expected model fields
        FIELD_MAPPING = {
            "item": "part_type_erp_id",
            "wo number": "ERP_id",
            "quantity": "quantity",
            "due date": "expected_completion",
            "notes": "notes",
        }

        def normalize_header(header: str) -> str:
            return header.strip().lower().replace("'", "'").replace("'", "'")

        def remap_fields(row):
            return {
                FIELD_MAPPING.get(k.strip().lower(), k.strip()): v.strip() if isinstance(v, str) else v
                for k, v in row.items()
            }

        try:
            if filename.endswith(".csv"):
                raw = file.read()
                encoding = chardet.detect(raw)["encoding"] or "utf-8"
                try:
                    decoded = raw.decode(encoding)
                except UnicodeDecodeError:
                    decoded = raw.decode("windows-1252")

                reader = csv.DictReader(io.StringIO(decoded))
                rows = [remap_fields(row) for row in reader]

            elif filename.endswith((".xlsx", ".xls")):
                df = pd.read_excel(file)
                rows = [remap_fields(row) for _, row in df.iterrows()]

            else:
                return Response({"detail": "Unsupported file type."}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"detail": f"Error reading file: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        for i, row in enumerate(rows, start=1):
            serializer = WorkOrderCSVUploadSerializer(data=row, context={'request': request})
            if serializer.is_valid():
                try:
                    # Use serializer method that calls model method
                    work_order, created, warnings = serializer.create_work_order()

                    result = {
                        "row": i,
                        "status": "created" if created else "updated",
                        "id": work_order.id,
                    }
                    if warnings:
                        result["warnings"] = warnings

                    results.append(result)

                except Exception as e:
                    results.append({"row": i, "status": "error", "errors": str(e)})
            else:
                results.append({"row": i, "status": "error", "errors": serializer.errors})

        return Response(results, status=status.HTTP_207_MULTI_STATUS)

    @action(detail=True, methods=['get'])
    def qa_summary(self, request, pk=None):
        """Get QA summary for work order including batch status"""
        work_order = self.get_object()
        
        parts = work_order.parts.all()
        parts_needing_qa = parts.filter(
            requires_sampling=True,
            part_status__in=['PENDING', 'IN_PROGRESS', 'AWAITING_QA']
        )
        
        return Response({
            'work_order': self.get_serializer(work_order).data,
            'is_batch_work_order': work_order.parts.filter(
                part_type__processes__is_batch_process=True
            ).exists(),
            'parts_summary': {
                'total': parts.count(),
                'needing_qa': parts_needing_qa.count(),
                'completed': parts.filter(part_status='COMPLETED').count(),
                'quarantined': parts.filter(part_status='QUARANTINED').count(),
                'in_progress': parts.filter(part_status='IN_PROGRESS').count()
            },
            'parts_needing_qa': PartsSerializer(
                parts_needing_qa, 
                many=True, 
                context={'request': request}
            ).data
        })

    @action(detail=True, methods=['get'])
    def qa_documents(self, request, pk=None):
        """Get documents relevant to QA for this work order"""
        work_order = self.get_object()
        
        # Get parts needing QA to determine current steps
        parts_needing_qa = work_order.parts.filter(
            requires_sampling=True,
            part_status__in=['PENDING', 'IN_PROGRESS', 'AWAITING_QA', 'REWORK_NEEDED', 'REWORK_IN_PROGRESS']
        ).select_related('step', 'part_type')
        
        if not parts_needing_qa.exists():
            return Response({
                'work_order_documents': [],
                'current_step_documents': [],
                'part_type_documents': [],
                'current_step_id': None
            })
        
        # Determine the most common step (current step)
        step_counts = Counter(part.step.id for part in parts_needing_qa if part.step)
        current_step_id = step_counts.most_common(1)[0][0] if step_counts else None
        current_step = None
        if current_step_id:
            current_step = parts_needing_qa.filter(step_id=current_step_id).first().step
        
        # Get part type (should be same for all parts in work order)
        part_type = parts_needing_qa.first().part_type if parts_needing_qa.exists() else None
        
        # Get content types
        work_order_ct = ContentType.objects.get_for_model(WorkOrder)
        step_ct = ContentType.objects.get_for_model(Steps) if current_step else None
        part_type_ct = ContentType.objects.get_for_model(PartTypes) if part_type else None
        
        # Get documents
        work_order_docs = Documents.get_user_accessible_queryset(request.user).filter(
            content_type=work_order_ct,
            object_id=work_order.id
        )
        
        current_step_docs = Documents.objects.none()
        if step_ct and current_step:
            current_step_docs = Documents.get_user_accessible_queryset(request.user).filter(
                content_type=step_ct,
                object_id=current_step.id
            )
        
        part_type_docs = Documents.objects.none()
        if part_type_ct and part_type:
            part_type_docs = Documents.get_user_accessible_queryset(request.user).filter(
                content_type=part_type_ct,
                object_id=part_type.id
            )
        
        # Serialize documents
        document_serializer = DocumentsSerializer
        
        return Response({
            'work_order_documents': document_serializer(work_order_docs, many=True, context={'request': request}).data,
            'current_step_documents': document_serializer(current_step_docs, many=True, context={'request': request}).data,
            'part_type_documents': document_serializer(part_type_docs, many=True, context={'request': request}).data,
            'current_step_id': current_step_id,
            'parts_in_qa': parts_needing_qa.count()
        })


class EquipmentViewSet(viewsets.ModelViewSet):
    serializer_class = EquipmentsSerializer  # Will need to create this
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ["equipment_type"]
    ordering_fields = ["name", "equipment_type__name"]
    search_fields = ["name"]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Equipments.objects.none()

        return Equipments.objects.for_user(self.request.user)


class EquipmentTypeViewSet(viewsets.ModelViewSet):
    serializer_class = EquipmentTypeSerializer  # Will need to create this
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ["name"]
    ordering_fields = ["id", "name"]
    search_fields = ["name"]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return EquipmentType.objects.none()

        return EquipmentType.objects.for_user(self.request.user)


class ErrorTypeViewSet(viewsets.ModelViewSet):
    serializer_class = QualityErrorsListSerializer  # Will need to create this
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ["error_name"]
    ordering_fields = ["id", "error_name", "part_type__name"]
    search_fields = ["error_name", "part_type__name"]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return QualityErrorsList.objects.none()

        return QualityErrorsList.objects.for_user(self.request.user)


@extend_schema_view(
    create=extend_schema(
        request={
            'multipart/form-data': DocumentsSerializer
        }
    ),
    update=extend_schema(
        request={
            'multipart/form-data': DocumentsSerializer
        }
    ),
    partial_update=extend_schema(
        request={
            'multipart/form-data': DocumentsSerializer
        }
    )
)
class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentsSerializer  # Updated to match existing serializer
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["content_type", "object_id", "is_image"]
    search_fields = ["file_name", "uploaded_by__username"]
    ordering_fields = ["upload_date", "version", "file_name"]
    ordering = ["-upload_date"]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Documents.objects.none()
        return Documents.get_user_accessible_queryset(self.request.user).select_related("uploaded_by", "content_type")

    def perform_create(self, serializer):
        doc = serializer.save(uploaded_by=self.request.user)
        
        # Only try to embed if user wants it to be AI readable and it's not archived
        if doc.ai_readable and not doc.archived:
            try:
                success = doc.embed_inline()
                if not success:
                    # Embedding failed, set ai_readable to False
                    doc.ai_readable = False
                    doc.save(update_fields=['ai_readable'])
            except Exception as e:
                # Log the error and set ai_readable to False
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to embed document {doc.id}: {e}")
                doc.ai_readable = False
                doc.save(update_fields=['ai_readable'])

    def perform_update(self, serializer):
        instance = self.get_object()
        old_file = instance.file
        old_ai_readable = instance.ai_readable
        doc = serializer.save()
        
        # Handle AI readability changes
        if doc.archived:
            # Archived documents should not be AI readable
            if doc.ai_readable:
                doc.ai_readable = False
                doc.save(update_fields=["ai_readable"])
                # Clean up existing chunks
                doc.chunks.all().delete()
        elif doc.ai_readable and not old_ai_readable:
            # User wants to make it AI readable
            try:
                success = doc.embed_inline()
                if not success:
                    doc.ai_readable = False
                    doc.save(update_fields=["ai_readable"])
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to embed document {doc.id}: {e}")
                doc.ai_readable = False
                doc.save(update_fields=["ai_readable"])
        elif not doc.ai_readable and old_ai_readable:
            # User wants to make it NOT AI readable - clean up chunks
            doc.chunks.all().delete()
        elif doc.ai_readable and 'file' in serializer.validated_data and old_file != doc.file:
            # File changed and user wants it to remain AI readable - re-embed
            try:
                doc.chunks.all().delete()  # Clean up old chunks
                success = doc.embed_inline()
                if not success:
                    doc.ai_readable = False
                    doc.save(update_fields=["ai_readable"])
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to re-embed document {doc.id}: {e}")
                doc.ai_readable = False
                doc.save(update_fields=["ai_readable"])

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        # Use model method for access logging
        instance.log_access(request.user, request)

        return Response(self.get_serializer(instance).data)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download the actual file"""
        document = self.get_object()
        
        # Log access
        document.log_access(request.user, request)
        
        if not document.file:
            return Response({"detail": "No file attached"}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            response = FileResponse(
                document.file.open('rb'),
                as_attachment=True,
                filename=document.file_name or os.path.basename(document.file.name)
            )
            return response
        except Exception as e:
            return Response({"detail": f"Error serving file: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProcessWithStepsViewSet(viewsets.ModelViewSet):
    queryset = Processes.objects.all().prefetch_related("steps__sampling_ruleset__rules")
    serializer_class = ProcessWithStepsSerializer  # Use the correct serializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Processes.objects.none()

        # Apply filtering first, then optimize
        base_queryset = Processes.objects.all()  # AllowAny permission, so no user filtering
        return base_queryset.prefetch_related("steps__sampling_ruleset__rules")

    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            return super().update(request, *args, **kwargs)


class SamplingRuleSetViewSet(viewsets.ModelViewSet):
    queryset = SamplingRuleSet.objects.all()
    serializer_class = SamplingRuleSetSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ["part_type", "process", "step", "active", "version"]
    ordering_fields = ["id", "name", "version", "created_at"]
    search_fields = ["name", "origin"]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return SamplingRuleSet.objects.none()

        return SamplingRuleSet.objects.for_user(self.request.user)


class SamplingRuleViewSet(viewsets.ModelViewSet):
    queryset = SamplingRule.objects.all()
    serializer_class = SamplingRuleSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ["ruleset", "rule_type"]
    ordering_fields = ["id", "order", "created_at"]
    search_fields = ["rule_type", "ruleset__name"]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return SamplingRule.objects.none()

        return SamplingRule.objects.for_user(self.request.user)


class MeasurementsDefinitionViewSet(viewsets.ModelViewSet):
    queryset = MeasurementDefinition.objects.all()
    serializer_class = MeasurementDefinitionSerializer  # Will need to create this
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ["step__name", "label", "step"]
    ordering_fields = ["step__name", "label"]
    search_fields = ["label", "step__name", "step"]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return MeasurementDefinition.objects.none()

        return MeasurementDefinition.objects.for_user(self.request.user)


class ContentTypeViewSet(ReadOnlyModelViewSet):
    queryset = ContentType.objects.all()
    serializer_class = ContentTypeSerializer  # Will need to create this

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return ContentType.objects.none()

        return ContentType.objects.all()


class LogEntryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LogEntry.objects.all()  # ✅ This is the fix
    serializer_class = AuditLogSerializer  # Updated to match existing serializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["actor", "content_type", "object_pk", "action"]
    search_fields = ["object_repr", "changes"]
    ordering_fields = ["timestamp"]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return LogEntry.objects.none()

        # LogEntry doesn't have SecureManager, so use the base queryset
        return self.queryset


@xframe_options_exempt
def serve_media_iframe_safe(request, path):
    full_path = os.path.join(settings.MEDIA_ROOT, path)
    if not os.path.exists(full_path):
        raise Http404()

    response = FileResponse(open(full_path, 'rb'), content_type="application/pdf")  # or detect dynamically
    response["Content-Disposition"] = f'inline; filename="{os.path.basename(full_path)}"'
    response["Content-Security-Policy"] = "frame-ancestors http://localhost:5173"
    return response


class UserDetailsView(UserDetailsView):
    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        response.data['is_staff'] = request.user.is_staff
        # Add user groups to the response
        response.data['groups'] = [{'id': group.id, 'name': group.name} for group in request.user.groups.all()]
        return response
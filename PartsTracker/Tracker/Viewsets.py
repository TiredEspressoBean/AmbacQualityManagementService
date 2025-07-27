import csv
import io
from collections import Counter

import pandas as pd
from auditlog.models import LogEntry
from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema_view, inline_serializer, OpenApiResponse, OpenApiRequest
from requests.compat import chardet
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.generics import ListAPIView
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from Tracker.filters import *
from Tracker.serializer import *


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
    serializer_class = TrackerPageOrderSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Orders.objects.none()

        user = self.request.user
        if user.is_staff:
            return Orders.objects.all()
        else:
            return Orders.objects.filter(customer=user)

    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


class PartsByOrderView(ListAPIView):
    serializer_class = PartsSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Parts.objects.none()

        order_id = self.kwargs["order_id"]
        return Parts.objects.filter(order__id=order_id)


@extend_schema_view(list=extend_schema(parameters=[
    OpenApiParameter(name='ordering', description='Which field to order by, prepend "-" for descending.',
                     required=False, type=str), ]))
@extend_schema(parameters=[
    OpenApiParameter(name='status__in', description='Filter by multiple status values.', required=False,
                     type={'type': 'array', 'items': {'type': 'string'}},  # manual override
                     style='form', explode=True, )])
class PartsViewSet(viewsets.ModelViewSet):
    queryset = Parts.objects.all()
    serializer_class = PartsSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = LimitOffsetPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter, filters.SearchFilter]
    filterset_class = PartFilter
    ordering_fields = ['created_at', 'ERP_id', 'status']  # fields allowed to sort by
    ordering = ['-created_at']
    search_fields = ["ERP_id", "order__name", "work_order__ERP_id", "step__name", "part_type__name", "part_status", ]


    @extend_schema(request=None, responses={
        200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="Step increment response")})
    @action(detail=True, methods=["post"])
    def increment(self, request, pk=None):
        part = self.get_object()
        serializer = IncrementStepSerializer(part, data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = part.increment_step()
            return Response({"detail": f"Step {result}."})
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class OrdersViewSet(viewsets.ModelViewSet):
    queryset = Orders.objects.all()
    serializer_class = OrdersSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = LimitOffsetPagination

    # add SearchFilter here
    filter_backends = [DjangoFilterBackend,  # exact filters (status, customer, company…)
                       filters.SearchFilter,  # our global “search=…” box
                       filters.OrderingFilter,  # ordering via ?ordering=
                       ]

    # for exact-match filters (still works alongside search)
    filterset_class = OrderFilter

    # what fields can you sort by
    ordering_fields = ["created_at", "status", "name", "estimated_completion", ]
    ordering = ["-created_at"]

    # the magic: ?search=foo will OR across all these
    search_fields = ["name", "company__name", "customer__first_name", "customer__last_name", ]

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
        step_counts = Counter()

        for part in order.parts.all():
            step_id = part.step.id if part.step else 'Unassigned'
            step_counts[step_id] += 1

        # Optionally expand to include step names
        step_counts = (
        Parts.objects.filter(order_id=order).exclude(status='COMPLETED').values("step_id").annotate(count=Count("id")))

        # Create a map of step_id to name in one query
        step_id_to_name = {step.id: step.name for step in
                           Steps.objects.filter(id__in=[s["step_id"] for s in step_counts])}

        # Compose final output
        result = [{"id": step["step_id"], "name": step_id_to_name.get(step["step_id"], f"Step {step['step_id']}"),
                   "count": step["count"], } for step in step_counts]

        paginated = self.paginate_queryset(result)
        return self.get_paginated_response(paginated)

    @extend_schema(request=inline_serializer(name="StepIncrementInput", fields={"step_id": serializers.IntegerField(),
                                                                                "order_id": serializers.IntegerField(), }),
                   responses=inline_serializer(name="StepIncrementResponse",
                                               fields={"advanced": serializers.IntegerField(),
                                                       "total": serializers.IntegerField()}))
    @action(detail=True, methods=['post'], url_path='increment-step')
    def increment_parts_step(self, request, pk=None):
        order_id = request.data.get("order_id")
        step_id = request.data.get("step_id")

        if not step_id:
            return Response({"detail": "Missing step_id"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_step = Steps.objects.get(id=step_id)
        except Steps.DoesNotExist:
            return Response({"detail": "Invalid step_id"}, status=status.HTTP_404_NOT_FOUND)

        parts_to_advance = Parts.objects.filter(order__id=order_id, step=target_step)
        advanced = 0

        for part in parts_to_advance:
            if part.increment_step():  # You define this on the Part model
                advanced += 1

        return Response({"advanced": advanced, "total": parts_to_advance.count()}, status=status.HTTP_200_OK)

    @extend_schema(request=BulkRemovePartsSerializer, responses={200: OpenApiTypes.OBJECT})
    @action(detail=True, methods=['post'], url_path='parts/bulk-remove')
    def bulk_remove_parts(self, request, pk=None):
        serializer = BulkRemovePartsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order = self.get_object()
        parts = Parts.objects.filter(id__in=serializer.validated_data['ids'], order=order)

        count = parts.update(order=None)
        return Response({"removed": count}, status=status.HTTP_200_OK)

    @extend_schema(request=BulkAddPartsSerializer, responses={201: OpenApiTypes.OBJECT})
    @action(detail=True, methods=["post"], url_path="parts/bulk-add")
    def bulk_add_parts(self, request, pk=None):
        serializer = BulkAddPartsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order = self.get_object()
        part_type = serializer.validated_data['part_type_id']
        step = serializer.validated_data['step_id']
        part_status = serializer.validated_data['status']
        work_order = None
        if 'work_order_id' in serializer.validated_data:
            work_order = WorkOrder.objects.get(id=serializer.validated_data['work_order_id'])

        ERP_Id_start = int(serializer.validated_data["ERP_id"])

        parts = [Parts(status=part_status, order=order, part_type=part_type, step=step, work_order=work_order,
                       archived=False, ERP_id=part_type.ID_prefix + str(ERP_Id_start + i), ) for i in
                 range(serializer.validated_data["quantity"])]
        Parts.objects.bulk_create(parts)

        return Response({"created": len(parts)}, status=status.HTTP_201_CREATED)


class QualityReportViewSet(viewsets.ModelViewSet):
    queryset = QualityReports.objects.all()
    serializer_class = QualityReportFormSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = LimitOffsetPagination


class EmployeeSelectViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.filter(is_staff=True)
    serializer_class = EmployeeSelectSerializer
    permission_classes = [IsAuthenticated]


class EquipmentSelectViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Equipments.objects.all()
    serializer_class = EquipmentSelectSerializer
    permission_classes = [IsAuthenticated]


class HubspotGatesViewSet(viewsets.ModelViewSet):
    queryset = ExternalAPIOrderIdentifier.objects.all()
    serializer_class = ExternalAPIOrderIdentifierSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = User.objects.filter(is_staff=False)
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Companies.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None


@extend_schema(parameters=[
    OpenApiParameter(name="process", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False,
                     description="Filter steps by process ID"),
    OpenApiParameter(name="part_type", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False,
                     description="Filter steps by process's part type ID"), ])
class StepsViewSet(viewsets.ModelViewSet):
    queryset = Steps.objects.all()
    serializer_class = StepSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter, ]
    filterset_fields = {"process": ["exact"], "process__part_type": ["exact"],  # enables ?part_type= as a query param
                        }
    search_fields = ["part_type__name", "process__name"]
    ordering_fields = ["part_type__name", "process__name"]
    ordering = ["process__name"]

    @extend_schema(request=StepSamplingRulesWriteSerializer, responses={
        200: OpenApiResponse(response=StepSamplingRulesResponseSerializer,
                             description="Sampling rules updated successfully.")}, methods=["POST"],
                   description="Update or create a sampling rule set for this step"

                   )
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
        serializer = StepSamplingRulesWriteSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        ruleset = serializer.save(step=step)

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
        serializer = StepWithResolvedRulesSerializer(step)
        return Response(serializer.data)


class ProcessViewSet(viewsets.ModelViewSet):
    queryset = Processes.objects.select_related("part_type").prefetch_related("steps").all()
    serializer_class = ProcessesSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter, ]
    filterset_fields = ["part_type"]
    search_fields = ["name", "part_type__name"]
    ordering_fields = ["created_at", "updated_at", "name"]
    ordering = ["-created_at"]


@extend_schema(parameters=[
    OpenApiParameter(name="part_type", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False,
                     description="Filter processes by associated part type ID"), ])
class PartTypeViewSet(viewsets.ModelViewSet):
    queryset = PartTypes.objects.all()
    serializer_class = PartTypeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend,  # exact filters (status, customer, company…)
                       filters.SearchFilter,  # our global “search=…” box
                       OrderingFilter]
    ordering_fields = ['created_at', 'name', 'updated_at', 'ID_prefix']  # fields allowed to sort by
    ordering = ['-created_at']
    search_fields = ["name", "ID_prefix"]
    filterset_fields = ['name']


class WorkOrderViewSet(viewsets.ModelViewSet):
    queryset = WorkOrder.objects.all()
    serializer_class = WorkOrderSerializer  # Default serializer for listing/detail
    permission_classes = [IsAuthenticated]  # Set your real permissions here
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ["related_order"]
    ordering_fields = ["created_at", "expected_completion", "ERP_id"]
    search_fields = ["ERP_id", "related_order__ERP_id", "notes"]

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
        import chardet, csv, io
        import pandas as pd

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
            # optionally map any others you want to use
        }

        def normalize_header(header: str) -> str:
            return header.strip().lower().replace("’", "'").replace("‘", "'")

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
            serializer = WorkOrderUploadSerializer(data=row)
            if serializer.is_valid():
                try:
                    work_order = serializer.create_or_update(serializer.validated_data)
                    warnings = []

                    part_type_erp_id = row.get("part_type_erp_id") or row.get("item")
                    if part_type_erp_id and not PartTypes.objects.filter(ERP_id=part_type_erp_id).exists():
                        warnings.append(
                            f"PartType with ERP_id '{part_type_erp_id}' not found — parts created with null part_type"
                        )

                    results.append({
                        "row": i,
                        "status": "success",
                        "id": work_order.id,
                        **({"warnings": warnings} if warnings else {})
                    })

                except Exception as e:
                    results.append({"row": i, "status": "error", "errors": str(e)})
            else:
                results.append({"row": i, "status": "error", "errors": serializer.errors})

        return Response(results, status=status.HTTP_207_MULTI_STATUS)


class EquipmentViewSet(viewsets.ModelViewSet):
    queryset = Equipments.objects.all()
    serializer_class = EquipmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ["equipment_type"]
    ordering_fields = ["name", "equipment_type__name"]
    search_fields = ["name"]


class EquipmentTypeViewSet(viewsets.ModelViewSet):
    queryset = EquipmentType.objects.all()
    serializer_class = EquipmentTypeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ["name"]
    ordering_fields = ["id", "name"]
    search_fields = ["name"]


class ErrorTypeViewSet(viewsets.ModelViewSet):
    queryset = QualityErrorsList.objects.all()
    serializer_class = ErrorTypeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ["error_name"]
    ordering_fields = ["id", "error_name", "part_type__name"]
    search_fields = ["error_name", "part_type__name"]


class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter, ]
    filterset_fields = ["content_type", "object_id", "is_image"]
    search_fields = ["file_name", "uploaded_by__username"]
    ordering_fields = ["upload_date", "version", "file_name"]
    ordering = ["-upload_date"]

    def get_queryset(self):
        user = self.request.user
        qs = Documents.objects.select_related("uploaded_by", "content_type")

        if user.groups.filter(name="Customer").exists():
            return qs.filter(classification="PUBLIC")
        elif user.groups.filter(name="Employee").exists():
            return qs.filter(classification__in=["PUBLIC", "INTERNAL"])
        elif user.groups.filter(name="Manager").exists():
            return qs.filter(classification__in=["PUBLIC", "INTERNAL", "CONFIDENTIAL"])
        elif user.is_superuser:
            return qs
        else:
            return qs.none()

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)

    def log_view(self, instance, actor, remote_addr, remote_port, actor_email):
        """
        Helper function to log a 'view' action.
        This function handles logging both the document and its content_object if present.
        """
        # Log the document view
        serialized_data = DocumentSerializer(instance).data
        LogEntry.objects.create(action='viewed', object_id=instance.id, object_repr=str(instance),
                                action_object=instance, user=actor, timestamp=timezone.now(),
                                extra_data={'remote_addr': remote_addr, 'remote_port': remote_port,
                                            'actor_email': actor_email, 'serialized_data': serialized_data})

        # Log the associated Generic Foreign Key objects (if any)
        content_object = instance.content_object
        if content_object:
            serialized_content_data = DocumentSerializer(content_object).data
            LogEntry.objects.create(action='viewed', object_id=content_object.id, object_repr=str(content_object),
                                    action_object=content_object, user=actor, timestamp=timezone.now(),
                                    extra_data={'remote_addr': remote_addr, 'remote_port': remote_port,
                                                'actor_email': actor_email, 'serialized_data': serialized_content_data})

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        # Extract metadata
        ip_address = request.META.get('REMOTE_ADDR')
        real_ip = request.META.get('HTTP_X_FORWARDED_FOR', ip_address).split(',')[0]
        remote_port = request.META.get('REMOTE_PORT')
        actor = request.user  # The user performing the action
        actor_email = request.user.email  # The email of the actor

        # Log the view (read) action for the Document and associated GFK
        self.log_view(instance, actor, real_ip, remote_port, actor_email)

        return Response(self.get_serializer(instance).data)


class ProcessWithStepsViewSet(viewsets.ModelViewSet):
    queryset = Processes.objects.all().prefetch_related("steps__sampling_ruleset__rules")
    serializer_class = ProcessWithStepsSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            return super().update(request, *args, **kwargs)


class SamplingRuleSetViewSet(viewsets.ModelViewSet):
    queryset = SamplingRuleSet.objects.all()
    serializer_class = SamplingRuleSetSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ["part_type", "process", "step", "active", "version"]
    ordering_fields = ["id", "name", "version", "created_at"]
    search_fields = ["name", "origin"]


class SamplingRuleViewSet(viewsets.ModelViewSet):
    queryset = SamplingRule.objects.all()
    serializer_class = SamplingRuleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ["ruleset", "rule_type"]
    ordering_fields = ["id", "order", "created_at"]
    search_fields = ["rule_type__name", "ruleset__name"]


class MeasurementsDefinitionViewSet(viewsets.ModelViewSet):
    queryset = MeasurementDefinition.objects.all()
    serializer_class = MeasurementDefinitionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ["step__name", "label", "step"]
    ordering_fields = ["step__name", "label"]
    search_fields = ["label", "step__name", "step"]


class ContentTypeViewSet(ReadOnlyModelViewSet):
    queryset = ContentType.objects.all()
    serializer_class = ContentTypeSerializer

class LogEntryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LogEntry.objects.select_related("actor", "content_type").order_by("-timestamp")
    serializer_class = LogEntrySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["actor", "content_type", "object_pk", "action"]
    search_fields = ["object_repr", "changes"]
    ordering_fields = ["timestamp"]


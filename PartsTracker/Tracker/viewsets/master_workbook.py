"""The master migration workbook — download it, upload it (dry run, then load).

See `Tracker.services.core.master_workbook`. Each sheet checks its own table's add and
change permissions as it loads, so this endpoint asks only for tenant membership; the
sheet list says up front which sheets this user may load.
"""
from django.core.cache import cache
from django.db import transaction
from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import parsers, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from Tracker.permissions import TenantAccessPermission
from Tracker.serializers.master_workbook import (
    MasterWorkbookQueuedSerializer,
    MasterWorkbookResultSerializer,
    MasterWorkbookSheetInfoSerializer,
    MasterWorkbookStatusSerializer,
)

# Up to this many rows a workbook runs in the request; more goes to a worker, which
# a migration-sized workbook (thousands of parts) needs to stay inside an HTTP timeout.
INLINE_ROWS = 500

XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


def _owner_key(task_id):
    return f"master-workbook-owner:{task_id}"


class MasterWorkbookViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, TenantAccessPermission]

    @extend_schema(responses={200: MasterWorkbookSheetInfoSerializer(many=True)},
                   description="The workbook's sheets in load order, and whether you may load each.")
    @action(detail=False, methods=['get'], url_path='sheets')
    def sheets(self, request):
        from Tracker.services.core.master_workbook import SHEETS, _missing_perms
        data = [{'title': s.title, 'about': s.about, 'allowed': not _missing_perms(s, request)}
                for s in SHEETS]
        return Response(MasterWorkbookSheetInfoSerializer(data, many=True).data)

    @extend_schema(
        parameters=[OpenApiParameter('filled', OpenApiTypes.BOOL, required=False, description=(
            "True: each sheet holds what's in UQMES now (the sheets you may see), to edit "
            "and upload back."))],
        responses={(200, XLSX): OpenApiTypes.BINARY},
        description="The master workbook: a Read me sheet, then one sheet per table — blank, or filled in.")
    @action(detail=False, methods=['get'], url_path='template')
    def template(self, request):
        from Tracker.services.core.master_workbook import build_template
        filled = str(request.query_params.get('filled', '')).lower() in ('1', 'true', 'yes')
        resp = HttpResponse(build_template(request, filled=filled), content_type=XLSX)
        name = 'master_workbook_filled.xlsx' if filled else 'master_workbook.xlsx'
        resp['Content-Disposition'] = f'attachment; filename="{name}"'
        if filled:
            # Bulk egress of the whole plant: recorded as the per-table exports are.
            from Tracker.services.core.access_log import record_access
            from Tracker.throttling import get_client_ip
            record_access(obj=request.tenant, user=request.user, action_type='bulk_export',
                          object_repr='Export: master workbook (filled)',
                          remote_addr=get_client_ip(request),
                          payload={'export': 'master_workbook', 'filled': True})
        return resp

    @extend_schema(
        request={'multipart/form-data': inline_serializer(
            name='MasterWorkbookUploadRequest', fields={
                'file': serializers.FileField(),
                'dry_run': serializers.BooleanField(
                    required=False, default=True,
                    help_text="True (the default) reports what loading would do and keeps "
                              "nothing. False loads it — only if every row loads."),
            })},
        responses={200: MasterWorkbookResultSerializer, 202: MasterWorkbookQueuedSerializer},
        description=("Run a master workbook: 200 with the result for a small one, 202 with a "
                     "task id to poll on `status/{task_id}` for a large one."),
    )
    @action(detail=False, methods=['post'], url_path='run', parser_classes=[parsers.MultiPartParser])
    def run(self, request):
        from Tracker.services.core.master_workbook import read_workbook, run_workbook
        upload = request.FILES.get('file')
        if upload is None:
            return Response({'detail': 'Attach the workbook as "file".'},
                            status=status.HTTP_400_BAD_REQUEST)
        dry_run = str(request.data.get('dry_run', 'true')).lower() not in ('false', '0', 'no')
        try:
            rows_by_sheet, ignored = read_workbook(upload, request)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        if not rows_by_sheet:
            return Response({'detail': "None of the workbook's sheets have any rows."},
                            status=status.HTTP_400_BAD_REQUEST)

        total = sum(len(r) for r in rows_by_sheet.values())
        if total <= INLINE_ROWS:
            result = run_workbook(rows_by_sheet, request, dry_run=dry_run)
            result['ignored_sheets'] = ignored
            return Response(MasterWorkbookResultSerializer(result).data)

        from uuid import uuid4
        from Tracker.tasks import run_master_workbook_task
        task_id = str(uuid4())
        tenant_id, user_id = str(request.tenant.id), request.user.id
        cache.set(_owner_key(task_id), f"{tenant_id}:{user_id}", 60 * 60 * 24)
        transaction.on_commit(lambda: run_master_workbook_task.apply_async(
            kwargs={'rows_by_sheet': rows_by_sheet, 'ignored': ignored, 'tenant_id': tenant_id,
                    'user_id': user_id, 'dry_run': dry_run},
            task_id=task_id))
        return Response(MasterWorkbookQueuedSerializer({'task_id': task_id, 'total_rows': total}).data,
                        status=status.HTTP_202_ACCEPTED)

    @extend_schema(responses={200: MasterWorkbookStatusSerializer},
                   parameters=[OpenApiParameter('task_id', OpenApiTypes.STR, OpenApiParameter.PATH)],
                   description="How a queued workbook run is going, and its result when done.")
    @action(detail=False, methods=['get'], url_path=r'status/(?P<task_id>[^/.]+)')
    def run_status(self, request, task_id=None):
        from celery.result import AsyncResult
        # Only the run's own starter may read it (as the per-table import status).
        if cache.get(_owner_key(task_id)) != f"{request.tenant.id}:{request.user.id}":
            return Response({'detail': 'Run not found.'}, status=status.HTTP_404_NOT_FOUND)
        res = AsyncResult(task_id)
        body = {'task_id': task_id, 'status': res.status, 'progress': None, 'result': None,
                'error': ''}
        if res.status == 'PROGRESS':
            body['progress'] = res.info or None
        elif res.status == 'SUCCESS':
            body['result'] = res.result
        elif res.status == 'FAILURE':
            body['error'] = str(res.result) if res.result else 'The run failed.'
        elif res.status not in ('PENDING',):
            body['status'] = 'PENDING'  # STARTED / RETRY read as still waiting
        return Response(MasterWorkbookStatusSerializer(body).data)

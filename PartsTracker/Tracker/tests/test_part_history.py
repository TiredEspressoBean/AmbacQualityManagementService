"""A serial's history (2026-10-07): the audit log of the part and of every record about it,
as one timeline, derived on read — with foreign keys named, not shown as ids."""
from django.contrib.auth.models import Permission
from rest_framework.test import APIClient

from Tracker.models import (
    Parts, PartTypes, Processes, QualityReports, Steps, WorkOrder, WorkOrderStatus,
)
from Tracker.services.mes.part_history import part_history
from Tracker.tests.base import TenantTestCase


class PartHistoryTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Nozzle")
        process = Processes.objects.create(tenant=self.tenant_a, name="Rebuild", part_type=pt)
        self.assembly = Steps.objects.create(tenant=self.tenant_a, part_type=pt, name="Assembly")
        self.coating = Steps.objects.create(tenant=self.tenant_a, part_type=pt, name="Nitride Coating")
        wo = WorkOrder.objects.create(tenant=self.tenant_a, ERP_id="WO-H", quantity=2, process=process,
                                      workorder_status=WorkOrderStatus.IN_PROGRESS)
        self.part = Parts.objects.create(tenant=self.tenant_a, ERP_id="INJ-H-1", part_type=pt,
                                         work_order=wo, step=self.assembly)
        self.other = Parts.objects.create(tenant=self.tenant_a, ERP_id="INJ-H-2", part_type=pt,
                                          work_order=wo, step=self.assembly)

    def test_the_part_and_records_about_it_in_one_timeline_with_names(self):
        self.part.step = self.coating
        self.part.save()
        QualityReports.objects.create(tenant=self.tenant_a, part=self.part, status="PASS",
                                      report_number="QR-MINE")
        QualityReports.objects.create(tenant=self.tenant_a, part=self.other, status="FAIL",
                                      report_number="QR-OTHER")

        total, rows = part_history(self.part)
        records = {r.record_type.lower() for r in rows}
        self.assertIn("part", records)
        self.assertIn("quality report", records)  # not the model's legacy "error report"
        self.assertFalse(any("QR-OTHER" in r.record for r in rows))  # another serial's report
        self.assertEqual(total, len(rows))

        step_moves = [c for r in rows for c in r.changes if c.field == "step" and c.old]
        self.assertEqual((step_moves[0].old, step_moves[0].new),
                         (str(self.assembly), str(self.coating)))  # names, not ids

    def test_endpoint_needs_audit_log_access(self):
        group = self.grant_tenant_permissions(self.user_a, self.tenant_a,
                                              ['view_parts', 'full_tenant_access'])
        client = APIClient()
        client.force_authenticate(user=self.user_a)
        client.credentials(HTTP_X_TENANT_ID=str(self.tenant_a.id))
        url = f'/api/Parts/{self.part.id}/history/'
        self.assertEqual(client.get(url).status_code, 403)

        # admin and auditlog both register a LogEntry, so the codename alone is ambiguous.
        group.permissions.add(Permission.objects.get(codename='view_logentry',
                                                     content_type__app_label='auditlog'))
        self.user_a.clear_permission_cache(self.tenant_a)
        resp = client.get(url, {'limit': 5})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertIn('results', resp.json())
        self.assertLessEqual(len(resp.json()['results']), 5)

    def test_many_to_many_and_empty_values_read_as_words(self):
        from types import SimpleNamespace as NS
        from unittest import mock
        from Tracker.services.mes import part_history as ph
        entry = NS(pk=1, timestamp=None, action=1, actor_id=None, actor=None, object_pk=str(self.part.pk),
                   object_repr="INJ-H-1", content_type=NS(model_class=lambda: Parts, model="parts"),
                   changes_dict={
                       "quality_reports": {"type": "m2m", "operation": "add", "objects": ["QR-1", "QR-2"]},
                       "sampling_context": ["{}", "{}"],
                       "order": ["None", "Tracker.Orders.None"],
                   })
        qs = mock.MagicMock()
        qs.count.return_value = 1
        qs.__getitem__.return_value = [entry]
        with mock.patch.object(ph, "_entries_queryset", return_value=qs):
            _, rows = ph.part_history(self.part)
        self.assertEqual([(c.field, c.old, c.new) for c in rows[0].changes],
                         [("quality reports", None, "added QR-1, QR-2")])

    def test_audit_log_api_names_a_user_foreign_key(self):
        from auditlog.models import LogEntry
        from Tracker.serializers.core import AuditLogSerializer
        self.user_a.first_name, self.user_a.last_name = "Jennifer", "Walsh"
        self.user_a.save(update_fields=["first_name", "last_name"])
        qr = QualityReports.objects.create(tenant=self.tenant_a, part=self.part, status="PASS",
                                           report_number="QR-WHO", detected_by=self.user_a)
        entries = LogEntry.objects.filter(object_pk=str(qr.pk)).select_related("content_type", "actor")
        changes = AuditLogSerializer(entries, many=True).data[0]["changes_display"]
        detected = [c for c in changes if c["field"] == "detected by"]
        self.assertEqual(detected[0]["new"], "Jennifer Walsh")  # the person, not their id

    def test_a_time_reads_on_the_plant_clock_and_a_capture_draft_is_not_listed(self):
        from types import SimpleNamespace as NS
        from Tracker.models import StepExecution
        from Tracker.services.core.audit_display import display_changes
        from Tracker.utils.tenant_context import tenant_context
        self.tenant_a.default_timezone = "America/Chicago"
        self.tenant_a.save(update_fields=["default_timezone"])
        entry = NS(content_type=NS(model_class=lambda: StepExecution), changes_dict={
            "capture_draft": ["{}", '{"bore": "4.01"}'],
            "exited_at": ["None", "2026-10-27 14:03:00.123456+00:00"],
            "started_at": ["None", "2026-10-27 13:00:00.5"],  # auditlog's naive UTC
        })
        with tenant_context(self.tenant_a):
            changes = display_changes(entry, {})
        self.assertEqual([(c.field, c.old, c.new) for c in changes],
                         [("exited at", None, "Oct 27, 2026 09:03"),  # CDT, not raw UTC
                          ("started at", None, "Oct 27, 2026 08:00")])

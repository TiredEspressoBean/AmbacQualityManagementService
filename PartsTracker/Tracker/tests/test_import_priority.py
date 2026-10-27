"""A priority changed by import is recorded with its reason, as on the screen (Shift Lead
C1): the CSV import and the master workbook's Work Orders sheet both use this importer."""
from Tracker.models import WorkOrder, WorkOrderStatus
from Tracker.services.mes.work_order import priority_changes
from Tracker.tests.io_base import ImportExportTestCase


class WorkOrderPriorityImportTests(ImportExportTestCase):
    endpoint = "WorkOrders"
    tenant_slug = "wo-priority-import"

    @classmethod
    def build_fixtures(cls):
        cls.wo = WorkOrder.objects.create(
            tenant=cls.tenant, ERP_id="WO-PRI-1", quantity=1, priority=3,
            workorder_status=WorkOrderStatus.PENDING)

    def test_a_priority_change_carries_the_rows_reason(self):
        body = self.import_csv("ERP_id,priority,priority_reason\n"
                               "WO-PRI-1,1,Customer line down\n")
        self.assertEqual(body["summary"]["updated"], 1, body)
        self.wo.refresh_from_db()
        self.assertEqual(self.wo.priority, 1)
        changes = priority_changes(self.wo)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["reason"], "Customer line down")
        self.assertNotIn("priority_reason", str(body["results"][0].get("warnings")))

    def test_a_priority_change_without_a_reason_is_refused(self):
        body = self.import_csv("ERP_id,priority\nWO-PRI-1,1\n")
        self.assertEqual(body["summary"]["errors"], 1, body)
        self.wo.refresh_from_db()
        self.assertEqual(self.wo.priority, 3)

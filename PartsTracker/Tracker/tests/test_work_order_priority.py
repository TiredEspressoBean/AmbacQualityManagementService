"""A priority change takes a reason.

Expediting a job is setting its priority to Urgent, and that is often a call someone is
asked to justify later. Like hold, scrap and reject, the change now has to say why; the
reason is recorded (RecordEdit) and shown with the work order's priority history.
"""
from Tracker.models import PartTypes, Processes, RecordEdit, WorkOrder, WorkOrderStatus
from Tracker.tests.base import TenantTestCase


class WorkOrderPriorityTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        t = self.tenant_a
        pt = PartTypes.objects.create(tenant=t, name="Injector")
        process = Processes.objects.create(tenant=t, name="P", part_type=pt)
        self.wo = WorkOrder.objects.create(
            tenant=t, ERP_id="WO-PRI", workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=1, process=process, priority=3)
        self.url = f"/api/WorkOrders/{self.wo.id}/"
        self.authenticate_superuser(self.tenant_a)

    def test_a_priority_change_without_a_reason_is_refused(self):
        r = self.client.patch(self.url, {"priority": 1}, format="json")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("priority_reason", r.data)
        self.wo.refresh_from_db()
        self.assertEqual(self.wo.priority, 3)
        self.assertFalse(RecordEdit.objects.filter(object_id=self.wo.id).exists())

    def test_a_blank_reason_counts_as_none(self):
        r = self.client.patch(self.url, {"priority": 1, "priority_reason": "   "}, format="json")
        self.assertEqual(r.status_code, 400, r.content)

    def test_expediting_with_a_reason_records_it_and_shows_it(self):
        r = self.client.patch(self.url, {"priority": 1, "priority_reason": "Line-down at Midwest Fleet"},
                              format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.wo.refresh_from_db()
        self.assertEqual(self.wo.priority, 1)
        edit = RecordEdit.objects.get(object_id=self.wo.id, field_name="priority")
        self.assertEqual((edit.old_value, edit.new_value, edit.reason),
                         ("3", "1", "Line-down at Midwest Fleet"))
        change = r.data["priority_changes"][0]
        self.assertEqual((change["from_priority"], change["to_priority"], change["reason"]),
                         ("Normal", "Urgent", "Line-down at Midwest Fleet"))
        self.assertNotIn("priority_reason", r.data)  # write-only

    def test_an_edit_that_leaves_priority_alone_needs_no_reason(self):
        r = self.client.patch(self.url, {"priority": 3, "notes": "Customer called"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        r = self.client.patch(self.url, {"notes": "Again"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertFalse(RecordEdit.objects.filter(object_id=self.wo.id).exists())

    def test_a_new_work_order_sets_its_first_priority_without_a_reason(self):
        r = self.client.post("/api/WorkOrders/", {
            "ERP_id": "WO-NEW", "workorder_status": "PENDING", "quantity": 1,
            "process": str(self.wo.process_id), "priority": 1,
        }, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.data["priority_changes"], [])

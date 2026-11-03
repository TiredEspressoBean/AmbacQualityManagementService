"""Order lines import wherever orders import (2026-11-03): the per-table import (Data
Management) and the master workbook's Order Lines sheet, both through
OrderLineCSVImportSerializer. Matched on order + line number; a line left off is not
cancelled; bad rows are listed and the rest load. A work-order row can name its line.
"""
import io

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from Tracker.models import OrderLine, Orders, PartTypes, Processes, Tenant, WorkOrder


class OrderLineImportTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        from Tracker.utils.tenant_context import reset_current_tenant, set_current_tenant_id
        cls.tenant = Tenant.objects.create(name="Lines", slug="line-import")
        token = set_current_tenant_id(cls.tenant.id)
        try:
            cls.user = get_user_model().objects.create_user(
                username="lineadmin", email="lines@c.test", password="x",
                tenant=cls.tenant, is_staff=True)
            cls.user.is_superuser = True
            cls.user.save(update_fields=["is_superuser"])
            cls.pt = PartTypes.objects.create(tenant=cls.tenant, name="Injector", ERP_id="INJ-1")
            cls.order = Orders.objects.create(tenant=cls.tenant, name="Fleet", order_number="ORD-9")
            cls.rfi = Orders.objects.create(tenant=cls.tenant, name="Deal", order_number="ORD-RFI",
                                            order_status="RFI")
            cls.process = Processes.objects.create(tenant=cls.tenant, name="Build", part_type=cls.pt,
                                                   status="APPROVED")
        finally:
            reset_current_tenant(token)

    def setUp(self):
        from Tracker.utils.tenant_context import set_current_tenant_id
        self.client.force_authenticate(user=self.user)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        self._token = set_current_tenant_id(self.tenant.id)

    def tearDown(self):
        from Tracker.utils.tenant_context import reset_current_tenant
        reset_current_tenant(self._token)

    def _upload(self, url, content, mode="upsert"):
        f = io.BytesIO(content.encode("utf-8"))
        f.name = "import.csv"
        return self.client.post(url, {"file": f, "mode": mode}, format="multipart")

    def _lines(self, header, *rows):
        return self._upload("/api/OrderLines/import/", "\n".join([header, *rows]) + "\n")

    HEADER = "order,line_number,part_type,quantity,due_date,fulfilment"

    def test_lines_import_and_a_re_import_updates_on_order_and_line_number(self):
        r = self._lines(self.HEADER, "ORD-9,1,INJ-1,10,2027-03-01,", "ORD-9,2,Injector,4,2027-04-01,Repair & return")
        self.assertIn(r.status_code, (200, 207), r.content)
        lines = {l.line_number: l for l in OrderLine.objects.filter(order=self.order)}
        self.assertEqual((lines[1].quantity, lines[1].fulfilment), (10, "NEW_BUILD"))
        self.assertEqual((lines[2].part_type_id, lines[2].fulfilment), (self.pt.id, "REPAIR_RETURN"))
        r = self._lines(self.HEADER, "ORD-9,1,INJ-1,12,2027-03-01,Exchange")
        self.assertEqual(OrderLine.objects.filter(order=self.order).count(), 2,
                         "matched on order + line number; line 2, left off, is not cancelled")
        line1 = OrderLine.objects.get(order=self.order, line_number=1)
        self.assertEqual((line1.quantity, line1.fulfilment), (12, "EXCHANGE"))
        self.assertEqual(OrderLine.objects.get(order=self.order, line_number=2).status, "OPEN")

    def test_a_bad_row_is_listed_and_the_rest_load(self):
        r = self._lines(self.HEADER, "ORD-9,1,INJ-1,10,,", "ORD-9,2,NOPE,4,,", "ORD-9,3,INJ-1,4,,Lease")
        body = r.json()
        self.assertEqual(body["summary"]["created"], 1, body)
        self.assertEqual(body["summary"]["errors"], 2, body)
        self.assertEqual(list(OrderLine.objects.filter(order=self.order).values_list("line_number", flat=True)), [1])

    def test_an_rfi_orders_lines_import_and_stay_tentative(self):
        self._lines(self.HEADER, "ORD-RFI,1,INJ-1,60,2027-05-20,")
        line = OrderLine.objects.get(order=self.rfi)
        self.assertEqual((line.quantity, line.order.order_status), (60, "RFI"))

    def test_a_work_order_row_pegs_to_its_line(self):
        self._lines(self.HEADER, "ORD-9,1,INJ-1,10,2027-03-01,")
        r = self._upload("/api/WorkOrders/import/",
                         "ERP_id,related_order,order_line_number,process,quantity\n"
                         "WO-IMP-1,ORD-9,1,Build,6\n")
        self.assertEqual(r.json()["summary"]["created"], 1, r.content)
        wo = WorkOrder.objects.get(ERP_id="WO-IMP-1")
        line = OrderLine.objects.get(order=self.order, line_number=1)
        self.assertEqual(wo.order_line_id, line.id)
        self.assertEqual((line.planned_quantity, line.remaining_quantity), (6, 4))

    def test_a_work_order_naming_a_line_its_order_lacks_is_refused(self):
        r = self._upload("/api/WorkOrders/import/",
                         "ERP_id,related_order,order_line_number,process,quantity\n"
                         "WO-IMP-2,ORD-9,7,Build,6\n")
        self.assertEqual(r.json()["summary"]["errors"], 1, r.content)
        self.assertFalse(WorkOrder.objects.filter(ERP_id="WO-IMP-2").exists())

    def test_the_template_has_the_line_columns(self):
        r = self.client.get("/api/OrderLines/import-template/csv/")
        self.assertEqual(r.status_code, 200)
        head = r.content.decode("utf-8-sig").splitlines()[0].lower()
        for col in ("order", "line_number", "part_type", "quantity", "due_date", "fulfilment"):
            self.assertIn(col, head)

    def test_the_master_workbook_loads_order_lines_between_orders_and_work_orders(self):
        from Tracker.services.core.master_workbook import SHEETS
        titles = [s.title for s in SHEETS]
        self.assertLess(titles.index("Orders"), titles.index("Order Lines"))
        self.assertLess(titles.index("Order Lines"), titles.index("Work Orders"))

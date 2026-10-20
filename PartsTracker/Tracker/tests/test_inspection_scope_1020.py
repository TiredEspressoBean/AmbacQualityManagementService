"""Batch 2 of the seed-arc findings (2026-10-20).

- The inspection queue and the inspector inbox are aggregations, and they listed every
  row in the tenant whatever the reader could open. Rows now follow the reader's own
  row visibility (SecureManager.for_user), like every model endpoint.
- Make-up read a Pending work order with no parts yet as short by its whole quantity.
"""
import datetime
from decimal import Decimal

from Tracker.models import MaterialLot, Parts, PartTypes, WorkOrder
from Tracker.services.mes.makeup import work_order_shortfall
from Tracker.tests.base import TenantTestCase

PERMS = ['view_materiallot', 'view_outsideprocessshipment', 'view_fpirecord', 'view_stepexecution']


class InspectionRowsFollowVisibilityTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Nozzle")
        self.lot = MaterialLot.objects.create(
            tenant=self.tenant_a, lot_number="SCOPE-1", received_date=datetime.date.today(),
            received_by=self.user_a, quantity=Decimal("10"), quantity_remaining=Decimal("10"),
            unit_of_measure="EA", status="AWAITING_INSPECTION", material_type=pt)

    def _ids(self, url, perms):
        self.grant_tenant_permissions(self.user_a, self.tenant_a, perms)
        self.authenticate_as(self.user_a, self.tenant_a)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200, resp.content)
        return [r["id"] for r in resp.json()]

    def test_a_reader_with_tenant_wide_access_sees_the_lot(self):
        self.assertIn(str(self.lot.id), self._ids("/api/IncomingInspection/", PERMS + ['full_tenant_access']))

    def test_the_queue_hides_a_lot_the_reader_cannot_open(self):
        self.assertNotIn(str(self.lot.id), self._ids("/api/IncomingInspection/", PERMS))

    def test_the_inbox_hides_a_lot_the_reader_cannot_open(self):
        self.assertNotIn(str(self.lot.id), self._ids("/api/InspectionInbox/", PERMS))

    def test_the_inbox_shows_it_to_a_tenant_wide_reader(self):
        self.assertIn(str(self.lot.id), self._ids("/api/InspectionInbox/", PERMS + ['full_tenant_access']))


class MakeupShortfallTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        self.pt = PartTypes.objects.create(tenant=self.tenant_a, name="Injector")
        self.wo = WorkOrder.objects.create(tenant=self.tenant_a, ERP_id="WO-MU-1", quantity=3)

    def test_a_work_order_with_no_parts_yet_is_not_short(self):
        self.assertEqual(work_order_shortfall(self.wo)["shortfall"], 0)

    def test_scrap_makes_a_shortfall(self):
        for i, st in enumerate(["IN_PROGRESS", "IN_PROGRESS", "SCRAPPED"]):
            Parts.objects.create(tenant=self.tenant_a, ERP_id=f"MU-{i}", part_type=self.pt,
                                 work_order=self.wo, part_status=st)
        self.assertEqual(work_order_shortfall(self.wo)["shortfall"], 1)

    def test_an_ended_work_order_takes_no_make_up(self):
        Parts.objects.create(tenant=self.tenant_a, ERP_id="MU-X", part_type=self.pt,
                             work_order=self.wo, part_status="SCRAPPED")
        WorkOrder.objects.filter(pk=self.wo.pk).update(workorder_status="COMPLETED")
        self.wo.refresh_from_db()
        self.assertEqual(work_order_shortfall(self.wo)["shortfall"], 0)

"""A person can hold a suspect lot by hand (user decision 2026-10-28, B12). Holds
came only from system triggers, so stock already accepted or in use couldn't be held."""
import uuid
from datetime import date
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType

from Tracker.models import Material, MaterialLot, RecordEdit
from Tracker.services.mes.consumption import _usable_lots
from Tracker.services.qms import receiving_inspection
from Tracker.tests.base import TenantTestCase


class ManualLotHoldTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        self.seal = Material.objects.create(tenant=self.tenant_a, name="Seal", unit_of_measure="EA")
        self.lot = MaterialLot.objects.create(
            tenant=self.tenant_a, lot_number="SEAL-1", material=self.seal, quantity=Decimal(10),
            quantity_remaining=Decimal(10), unit_of_measure="EA", status="ACCEPTED",
            received_date=date(2026, 10, 1))

    def _post(self, perms, lot_id, action, body):
        self.grant_tenant_permissions(self.user_a, self.tenant_a, perms + ['full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        return self.client.post(f"/api/MaterialLots/{lot_id}/{action}/", body, format="json")

    def test_an_operator_is_refused(self):
        r = self._post(['view_materiallot', 'change_materiallot', 'add_materiallot'],
                       uuid.uuid4(), 'place-hold', {"reason": "suspect"})
        self.assertEqual(r.status_code, 403, r.content)

    def test_qa_holds_it_and_no_draw_takes_from_it(self):
        r = self._post(['view_materiallot', 'hold_materiallot'], self.lot.id, 'place-hold',
                       {"reason": "Supplier recalled this batch"})
        self.assertEqual(r.status_code, 200, r.content)
        self.lot.refresh_from_db()
        self.assertEqual((self.lot.status, self.lot.hold_reason), ("QUARANTINE", "MANUAL"))
        edit = RecordEdit.objects.get(content_type=ContentType.objects.get_for_model(MaterialLot),
                                      object_id=self.lot.id, field_name="hold_reason")
        self.assertEqual((edit.new_value, edit.reason, edit.edited_by_id),
                         ("MANUAL", "Supplier recalled this batch", self.user_a.id))
        self.assertNotIn(self.lot, _usable_lots(('MATERIAL', self.seal.id), self.tenant_a))

    def test_a_reason_is_required(self):
        r = self._post(['view_materiallot', 'hold_materiallot'], self.lot.id, 'place-hold', {"reason": " "})
        self.assertEqual(r.status_code, 400, r.content)

    def test_release_puts_stock_back_as_it_was(self):
        receiving_inspection.place_manual_hold(self.lot, self.user_a, "Supplier recalled this batch")
        with self.assertRaisesMessage(ValueError, "Say why"):
            receiving_inspection.release_hold(self.lot, self.user_a, "")
        receiving_inspection.release_hold(self.lot, self.user_a, "Recall cleared for our batch")
        self.lot.refresh_from_db()
        self.assertEqual((self.lot.status, self.lot.hold_reason), ("ACCEPTED", ""))
        self.assertIn(self.lot, _usable_lots(('MATERIAL', self.seal.id), self.tenant_a))

    def test_release_needs_approve_disposition(self):
        r = self._post(['view_materiallot', 'hold_materiallot', 'change_materiallot'],
                       uuid.uuid4(), 'release-hold', {"reason": "x"})
        self.assertEqual(r.status_code, 403, r.content)

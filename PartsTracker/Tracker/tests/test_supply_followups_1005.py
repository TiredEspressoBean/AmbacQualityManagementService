"""Supply follow-ups (2026-10-05): RMA + replacement on a return, material lots on
shipments, more than one hold at a time, and cycle counting."""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from Tracker.utils.tenant_context import reset_current_tenant, set_current_tenant_id

User = get_user_model()


class _Fixture(APITestCase):
    @classmethod
    def setUpTestData(cls):
        from Tracker.models import Companies, Material, Tenant
        cls.tenant = Tenant.objects.create(name="Follow", slug="supply-followups-1005")
        token = set_current_tenant_id(cls.tenant.id)
        try:
            cls.user = User.objects.create_user(username="fu", email="fu@x.test", password="x",
                                                tenant=cls.tenant, is_staff=True)
            cls.user.is_superuser = True
            cls.user.save(update_fields=["is_superuser"])
            cls.acme = Companies.objects.create(tenant=cls.tenant, name="Acme Seals", is_customer=False)
            cls.fleet = Companies.objects.create(tenant=cls.tenant, name="Fleet Co", is_supplier=False)
            cls.other = Companies.objects.create(tenant=cls.tenant, name="Other Co", is_supplier=False)
            cls.bar = Material.objects.create(tenant=cls.tenant, name="Bar stock 4140", unit_of_measure="ft")
        finally:
            reset_current_tenant(token)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        self._token = set_current_tenant_id(self.tenant.id)

    def tearDown(self):
        reset_current_tenant(self._token)

    def _lot(self, number, qty="100", status="ACCEPTED", owner=None, where="Rack 1", **kw):
        from Tracker.models import MaterialLot
        from Tracker.services.mes.locations import seed_location
        return MaterialLot.objects.create(
            tenant=self.tenant, lot_number=number, material=self.bar, quantity=Decimal(qty),
            quantity_remaining=Decimal(qty), unit_of_measure="ft", status=status, supplier=self.acme,
            owner=owner, location=seed_location(self.tenant, where) if where else None,
            received_date=date.today(), **kw)


class RmaTests(_Fixture):
    def test_ship_back_keeps_the_rma_and_expects_the_replacement(self):
        from Tracker.models import MaterialLot, QuarantineDisposition
        bad = self._lot("RTV-1", qty="40", status="REJECTED", erp_po_number="4500", erp_po_line="3")
        QuarantineDisposition.objects.create(tenant=self.tenant, material_lot=bad,
                                             disposition_type="RETURN_TO_SUPPLIER", quantity=Decimal(40))
        due = date.today() + timedelta(days=10)
        resp = self.client.post(f"/api/MaterialLots/{bad.id}/ship-back/",
                                {"rma_number": "RMA-77", "replacement_promised_date": str(due)}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual((resp.json()["status"], resp.json()["rma_number"]), ("RETURNED", "RMA-77"))
        rep = MaterialLot.objects.get(replaces=bad)
        self.assertEqual((rep.status, rep.quantity, rep.promised_date, rep.erp_po_line), ("ON_ORDER", Decimal(40), due, "3"))
        self.assertEqual([r["lot_number"] for r in resp.json()["replacement_lots"]], [rep.lot_number])

    def test_rtv_sheet_prints_the_rma(self):
        from Tracker.reports.adapters.rtv_sheet import build_rtv_sheet_context
        bad = self._lot("RTV-2", status="REJECTED")
        self.assertEqual(build_rtv_sheet_context(bad, self.tenant, self.user, "RMA-9").rma_number, "RMA-9")


class LotShippingTests(_Fixture):
    def _ship(self, lots, **body):
        return self.client.post("/api/CustomerShipments/ship/", {"lots": lots, **body}, format="json")

    def test_a_customers_lot_goes_back_to_them_whole(self):
        theirs = self._lot("THEIRS", owner=self.fleet)
        ready = self.client.get("/api/CustomerShipments/ready/").json()
        self.assertIn(str(theirs.id), [l["id"] for g in ready for l in g["lots"]])
        resp = self._ship([{"lot_id": str(theirs.id)}])
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["customer_name"], "Fleet Co")
        theirs.refresh_from_db()
        self.assertEqual((theirs.status, theirs.quantity_remaining), ("SHIPPED", Decimal(0)))

    def test_part_of_our_own_lot_ships_split_and_void_puts_it_back(self):
        ours = self._lot("OURS", qty="100")
        resp = self._ship([{"lot_id": str(ours.id), "quantity": "36"}], customer=str(self.fleet.id))
        self.assertEqual(resp.status_code, 201, resp.content)
        shipped = resp.json()["lots"][0]
        self.assertEqual(shipped["quantity"], 36.0)
        ours.refresh_from_db()
        self.assertEqual((ours.status, ours.quantity_remaining), ("ACCEPTED", Decimal(64)))
        void = self.client.post(f"/api/CustomerShipments/{resp.json()['id']}/void/", {"reason": "wrong truck"},
                                format="json")
        self.assertEqual(void.status_code, 200, void.content)
        from Tracker.models import MaterialLot
        # The split-off piece rejoins its lot: one lot again (user decision 2026-10-26).
        child = MaterialLot.objects.get(pk=shipped["id"])
        self.assertEqual((child.status, child.quantity_remaining), ("CONSUMED", Decimal(0)))
        ours.refresh_from_db()
        self.assertEqual((ours.status, ours.quantity_remaining), ("ACCEPTED", Decimal(100)))

    def test_a_customers_lot_cant_go_to_someone_else_and_shipped_stock_is_not_supply(self):
        theirs = self._lot("THEIRS-2", owner=self.fleet)
        bad = self._ship([{"lot_id": str(theirs.id)}], customer=str(self.other.id))
        self.assertEqual(bad.status_code, 400)
        from Tracker.services.mes.requirements import _TERMINAL_LOT_STATUSES
        self.assertIn("SHIPPED", _TERMINAL_LOT_STATUSES)


class HoldTests(_Fixture):
    def _received(self, **item_flags):
        from Tracker.services.qms.receiving_inspection import route_received_lot
        for k, v in item_flags.items():
            setattr(self.bar, k, v)
        self.bar.save()
        lot = self._lot("H-1", status="RECEIVED")
        route_received_lot(lot, self.user)
        lot.refresh_from_db()
        return lot

    def test_every_failing_gate_holds_and_each_clears_on_its_own(self):
        from Tracker.services.qms.receiving_inspection import reevaluate_hold
        lot = self._received(requires_coc=True, requires_heat_number=True)
        self.assertEqual((lot.status, lot.hold_reasons), ("QUARANTINE", ["AWAITING_COC", "AWAITING_HEAT_NUMBER"]))
        self.assertEqual(lot.hold_reason, "AWAITING_COC")
        lot.heat_number = "H9"
        lot.save(update_fields=["heat_number"])
        reevaluate_hold(lot, self.user)
        lot.refresh_from_db()
        self.assertEqual((lot.status, lot.hold_reasons, lot.hold_reason), ("QUARANTINE", ["AWAITING_COC"], "AWAITING_COC"))

    def test_releasing_one_of_several_needs_its_code_and_leaves_the_rest(self):
        lot = self._received(requires_coc=True, requires_heat_number=True)
        vague = self.client.post(f"/api/MaterialLots/{lot.id}/release-hold/", {"reason": "ok"}, format="json")
        self.assertEqual(vague.status_code, 400)
        resp = self.client.post(f"/api/MaterialLots/{lot.id}/release-hold/",
                                {"reason": "Cert waived for this lot", "code": "AWAITING_COC"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual((resp.json()["status"], resp.json()["hold_reasons"]), ("QUARANTINE", ["AWAITING_HEAT_NUMBER"]))
        m = self.client.get("/api/MaterialLots/dock-metrics/").json()
        self.assertEqual(m["held_now"], [{"reason": "AWAITING_HEAT_NUMBER", "lots": 1}])

    def test_a_split_carries_every_hold(self):
        from Tracker.services.mes.material_lot import split_material_lot
        lot = self._received(requires_coc=True, requires_heat_number=True)
        child = split_material_lot(lot, Decimal(10))
        self.assertEqual(child.hold_reasons, ["AWAITING_COC", "AWAITING_HEAT_NUMBER"])


class CycleCountTests(_Fixture):
    def test_count_submit_apply(self):
        from Tracker.models import MaterialLot, RecordEdit
        short = self._lot("CC-A", qty="100", where="Rack 3")
        exact = self._lot("CC-B", qty="50", where="Rack 3")
        stray = self._lot("CC-C", qty="20", where="Rack 7")
        start = self.client.post("/api/CycleCounts/", {"location": "Rack 3", "blind": True}, format="json")
        self.assertEqual(start.status_code, 201, start.content)
        c = start.json()
        self.assertTrue(all(l["expected"] is None for l in c["lines"]))  # blind while counting
        rec = self.client.post(f"/api/CycleCounts/{c['id']}/record/", {"entries": [
            {"kind": "LOT", "id": str(short.id), "counted": "94"},
            {"kind": "LOT", "id": str(exact.id), "counted": "50"},
            {"kind": "LOT", "id": str(stray.id), "counted": "20"},
        ]}, format="json")
        self.assertEqual(rec.status_code, 200, rec.content)
        sub = self.client.post(f"/api/CycleCounts/{c['id']}/submit/", format="json").json()
        found = {v["label"]: v["variance"] for v in sub["variances"]}
        self.assertEqual(found, {"CC-A": "SHORT", "CC-C": "FOUND_HERE"})
        # A draw while the count waited isn't undone: the difference is applied to what's left now.
        short.quantity_remaining = Decimal(90)
        short.save(update_fields=["quantity_remaining"])
        # Both differences are outside class C's ±5 % (and a lot found here always is): a
        # lead applying them says why (ABC cadence, 2026-11-04).
        bare = self.client.post(f"/api/CycleCounts/{c['id']}/apply/", format="json")
        self.assertEqual(bare.status_code, 400, bare.content)
        done = self.client.post(f"/api/CycleCounts/{c['id']}/apply/",
                                {"note": "Checked the rack: 6 drawn unbooked; CC-C moved here",
                                 "reasons": {f"LOT:{short.id}": "NOT_BOOKED", f"LOT:{stray.id}": "MISPLACED"}},
                                format="json")
        self.assertEqual((done.status_code, done.json()["status"]), (200, "APPLIED"))
        self.assertEqual(done.json()["apply_note"], "Checked the rack: 6 drawn unbooked; CC-C moved here")
        short.refresh_from_db()
        stray.refresh_from_db()
        self.assertEqual(short.quantity_remaining, Decimal(84))
        self.assertEqual(stray.storage_location, "Rack 3")
        self.assertTrue(RecordEdit.objects.filter(object_id=short.id, reason__startswith="Cycle count").exists())
        xlsx = self.client.get(f"/api/CycleCounts/{c['id']}/differences-xlsx/")
        self.assertEqual(xlsx.status_code, 200)

    def test_one_open_count_per_location_and_apply_needs_the_permission(self):
        self._lot("CC-D", where="Rack 4")
        first = self.client.post("/api/CycleCounts/", {"location": "Rack 4"}, format="json").json()
        self.assertEqual(self.client.post("/api/CycleCounts/", {"location": "Rack 4"}, format="json").status_code, 400)
        self.client.post(f"/api/CycleCounts/{first['id']}/submit/", format="json")
        clerk = User.objects.create_user(username="clerk", email="clerk@x.test", password="x", tenant=self.tenant)
        from Tracker.models import Tenant  # noqa: F401  (tenant membership comes with tenant=)
        self.client.force_authenticate(user=clerk)
        self.assertEqual(self.client.post(f"/api/CycleCounts/{first['id']}/apply/", format="json").status_code, 403)

    def test_an_uncounted_line_is_not_written_off(self):
        """Corrections #29: a blank line used to be submitted as 0 — "Not found" — and
        applying wrote the stock off. Blank stays blank; an empty spot is entered as 0."""
        skipped = self._lot("CC-E", qty="40", where="Rack 5")
        empty = self._lot("CC-F", qty="10", where="Rack 5")
        c = self.client.post("/api/CycleCounts/", {"location": "Rack 5"}, format="json").json()
        self.client.post(f"/api/CycleCounts/{c['id']}/record/", {"entries": [
            {"kind": "LOT", "id": str(empty.id), "counted": "0"}]}, format="json")
        sub = self.client.post(f"/api/CycleCounts/{c['id']}/submit/", format="json").json()
        self.assertEqual({v["label"]: v["variance"] for v in sub["variances"]}, {"CC-F": "MISSING"})
        self.assertEqual(sub["not_counted"], 1)
        self.client.post(f"/api/CycleCounts/{c['id']}/apply/",
                         {"note": "Spot is empty", "reasons": {f"LOT:{empty.id}": "NOT_BOOKED"}}, format="json")
        skipped.refresh_from_db()
        empty.refresh_from_db()
        self.assertEqual((skipped.quantity_remaining, empty.quantity_remaining), (Decimal(40), Decimal(0)))

    def test_a_lead_sends_a_submitted_count_back_for_recount(self):
        """Corrections #29 (user decision 2026-10-26): before applying, with a reason; the
        entries are kept; an applied count is final."""
        from Tracker.models import RecordEdit
        lot = self._lot("CC-G", qty="30", where="Rack 6")
        c = self.client.post("/api/CycleCounts/", {"location": "Rack 6"}, format="json").json()
        self.client.post(f"/api/CycleCounts/{c['id']}/record/", {"entries": [
            {"kind": "LOT", "id": str(lot.id), "counted": "3"}]}, format="json")
        self.client.post(f"/api/CycleCounts/{c['id']}/submit/", format="json")
        url = f"/api/CycleCounts/{c['id']}/send-back/"
        self.assertEqual(self.client.post(url, {"reason": ""}, format="json").status_code, 400)
        back = self.client.post(url, {"reason": "30 keyed as 3"}, format="json")
        self.assertEqual((back.status_code, back.json()["status"]), (200, "OPEN"))
        self.assertEqual(back.json()["lines"][0]["counted"], 3)
        self.assertTrue(RecordEdit.objects.filter(object_id=c["id"], reason="30 keyed as 3").exists())
        self.client.post(f"/api/CycleCounts/{c['id']}/submit/", format="json")
        self.client.post(f"/api/CycleCounts/{c['id']}/apply/",
                         {"note": "Recounted: 3 it is", "reasons": {f"LOT:{lot.id}": "SCRAPPED"}}, format="json")
        self.assertEqual(self.client.post(url, {"reason": "again"}, format="json").status_code, 400)


class CountCadenceTests(_Fixture):
    """ABC cycle-count cadence (user decision 2026-11-04): schedule by item, walk by
    location; tolerance per class, warned with a note; accuracy per class."""

    def _counted(self, where, entries):
        c = self.client.post("/api/CycleCounts/", {"location": where}, format="json").json()
        self.client.post(f"/api/CycleCounts/{c['id']}/record/", {"entries": entries}, format="json")
        return self.client.post(f"/api/CycleCounts/{c['id']}/submit/", format="json").json()

    def test_tolerance_follows_the_items_class(self):
        lot = self._lot("CT-A", qty="100", where="Rack 8")
        sub = self._counted("Rack 8", [{"kind": "LOT", "id": str(lot.id), "counted": "97"}])
        [v] = sub["variances"]
        self.assertEqual((v["abc_class"], v["within_tolerance"]), ("C", True), "3 of 100 is inside C's 5 %")
        url = f"/api/CycleCounts/{sub['id']}/apply/"
        self.assertEqual(self.client.post(url, format="json").status_code, 400, "every difference needs a reason")
        self.assertEqual(self.client.post(url, {"reasons": {f"LOT:{lot.id}": "NOT_BOOKED"}},
                                          format="json").status_code, 200)

        self.bar.abc_class = "A"
        self.bar.save(update_fields=["abc_class"])
        lot2 = self._lot("CT-B", qty="100", where="Rack 9")
        sub = self._counted("Rack 9", [{"kind": "LOT", "id": str(lot2.id), "counted": "97"}])
        self.assertFalse(sub["variances"][0]["within_tolerance"], "outside A's 1 %")
        refused = self.client.post(f"/api/CycleCounts/{sub['id']}/apply/",
                                   {"reasons": {f"LOT:{lot2.id}": "NOT_BOOKED"}}, format="json")
        self.assertEqual(refused.status_code, 400)
        self.assertIn("outside tolerance", refused.json()["detail"])

        # A minimum in units widens it: three off is now within.
        self.tenant.settings = {"cycle_count": {"tolerance_units": 5}}
        self.tenant.save(update_fields=["settings"])
        sub = self.client.get(f"/api/CycleCounts/{sub['id']}/").json()
        self.assertTrue(sub["variances"][0]["within_tolerance"])

    def test_due_follows_the_class_interval_and_the_last_applied_count(self):
        from datetime import timedelta
        from django.utils import timezone
        from Tracker.models import CycleCount
        self._lot("CT-C", qty="10", where="Rack 10")
        due = self.client.get("/api/CycleCounts/due/").json()
        [row] = [r for r in due if r["name"] == "Bar stock 4140"]
        self.assertTrue(row["never_counted"])
        self.assertEqual([l["location"] for l in row["locations"]], ["Rack 10"])

        sub = self._counted("Rack 10", [])
        self.client.post(f"/api/CycleCounts/{sub['id']}/apply/", format="json")
        self.assertFalse([r for r in self.client.get("/api/CycleCounts/due/").json()
                          if r["name"] == "Bar stock 4140"], "just counted")

        CycleCount.objects.filter(pk=sub["id"]).update(applied_at=timezone.now() - timedelta(days=40))
        self.assertFalse([r for r in self.client.get("/api/CycleCounts/due/").json()
                          if r["name"] == "Bar stock 4140"], "C: counted yearly")
        self.bar.abc_class = "A"
        self.bar.save(update_fields=["abc_class"])
        [row] = [r for r in self.client.get("/api/CycleCounts/due/").json() if r["name"] == "Bar stock 4140"]
        self.assertEqual((row["abc_class"], row["days_overdue"]), ("A", 10))

    def test_the_items_form_reads_last_counted_and_next_due_on_the_same_terms(self):
        from datetime import date, timedelta
        from django.utils import timezone
        from Tracker.models import CycleCount
        from Tracker.services.core.clock import tenant_today
        url = f"/api/CycleCounts/item-status/?material={self.bar.id}"
        st = self.client.get(url).json()
        self.assertEqual((st["on_hand"], st["next_due"], st["abc_class"]), (False, None, "C"),
                         "no stock in a location: nothing due")

        self._lot("CT-F", qty="10", where="Rack 12")
        st = self.client.get(url).json()
        self.assertTrue(st["on_hand"] and st["never_counted"])
        self.assertIsNone(st["last_counted"])
        today = tenant_today(self.tenant)
        self.assertEqual(st["next_due"], today.isoformat(), "never counted: due now")

        sub = self._counted("Rack 12", [])
        self.client.post(f"/api/CycleCounts/{sub['id']}/apply/", format="json")
        CycleCount.objects.filter(pk=sub["id"]).update(applied_at=timezone.now() - timedelta(days=40))
        st = self.client.get(url).json()
        self.assertFalse(st["never_counted"])
        self.assertIsNotNone(st["last_counted"])
        self.assertGreater(date.fromisoformat(st["next_due"]), today, "C: a year from the count")
        self.assertEqual(st["interval_days"], 365)

        self.assertEqual(self.client.get("/api/CycleCounts/item-status/").status_code, 400)

    def test_accuracy_counts_hits_per_class(self):
        a = self._lot("CT-D", qty="100", where="Rack 11")
        b = self._lot("CT-E", qty="100", where="Rack 11")
        sub = self._counted("Rack 11", [{"kind": "LOT", "id": str(a.id), "counted": "100"},
                                        {"kind": "LOT", "id": str(b.id), "counted": "50"}])
        self.client.post(f"/api/CycleCounts/{sub['id']}/apply/",
                         {"note": "Half went to scrap", "reasons": {f"LOT:{b.id}": "SCRAPPED"}}, format="json")
        acc = self.client.get("/api/CycleCounts/accuracy/").json()
        self.assertEqual((acc["C"]["counted"], acc["C"]["hits"], acc["C"]["pct"]), (2, 1, 50.0))
        self.assertEqual(acc["by_reason"], {"SCRAPPED": 1})
        self.assertIsNone(acc["A"]["pct"])


class CountScopeAndFollowUpTests(_Fixture):
    """Counting by item, and what follows a count (user decision 2026-11-04): units not
    found are chased until resolved; differences wait to be keyed into the ERP."""

    def test_an_item_count_spans_its_locations_and_moves_what_it_finds(self):
        from Tracker.models import MaterialLot
        a = self._lot("IT-A", qty="10", where="Rack 20")
        b = self._lot("IT-B", qty="10", where="Rack 21")
        loose = self._lot("IT-C", qty="5", where=None)  # nowhere on record: found on Rack 22
        from Tracker.services.mes.locations import seed_location
        seed_location(self.tenant, "Rack 22")
        start = self.client.post("/api/CycleCounts/", {"material": str(self.bar.id)}, format="json")
        self.assertEqual(start.status_code, 201, start.content)
        c = start.json()
        self.assertEqual((c["scope"], c["scope_name"]), ("MATERIAL", "Bar stock 4140"))
        self.assertEqual({l["label"]: l["system_location"] for l in c["lines"]},
                         {"IT-A": "Rack 20", "IT-B": "Rack 21"})
        url = f"/api/CycleCounts/{c['id']}/record/"
        bad = self.client.post(url, {"entries": [{"kind": "LOT", "id": str(loose.id), "counted": "5"}]},
                               format="json")
        self.assertEqual(bad.status_code, 400, "an item count needs to know where it was found")
        self.client.post(url, {"entries": [
            {"kind": "LOT", "id": str(a.id), "counted": "10"},
            {"kind": "LOT", "id": str(b.id), "counted": "10"},
            {"kind": "LOT", "id": str(loose.id), "counted": "5", "found_at": "Rack 22"}]}, format="json")
        self.client.post(f"/api/CycleCounts/{c['id']}/submit/", format="json")
        done = self.client.post(f"/api/CycleCounts/{c['id']}/apply/",
                                {"note": "Loose lot on Rack 22", "reasons": {f"LOT:{loose.id}": "MISPLACED"}},
                                format="json")
        self.assertEqual(done.status_code, 200, done.content)
        loose.refresh_from_db()
        self.assertEqual(loose.storage_location, "Rack 22")
        # It credits the item at the places it counted.
        self.assertFalse([r for r in self.client.get("/api/CycleCounts/due/").json()
                          if r["name"] == "Bar stock 4140"])
        self.assertEqual(MaterialLot.objects.get(pk=a.pk).quantity_remaining, 10)

    def test_a_unit_not_found_is_chased_until_resolved(self):
        from Tracker.models import Parts, PartTypes
        pt = PartTypes.objects.create(tenant=self.tenant, name="Nozzle")
        from Tracker.services.mes.locations import seed_location
        unit = Parts.objects.create(tenant=self.tenant, ERP_id="NZ-1", part_type=pt,
                                    location=seed_location(self.tenant, "Rack 30"), part_status="IN_STOCK")
        c = self.client.post("/api/CycleCounts/", {"location": "Rack 30"}, format="json").json()
        self.client.post(f"/api/CycleCounts/{c['id']}/record/",
                         {"entries": [{"kind": "PART", "id": str(unit.id), "counted": "0"}]}, format="json")
        self.client.post(f"/api/CycleCounts/{c['id']}/submit/", format="json")
        self.client.post(f"/api/CycleCounts/{c['id']}/apply/",
                         {"note": "Not on the rack", "reasons": {f"PART:{unit.id}": "UNKNOWN"}}, format="json")
        missing = self.client.get("/api/CycleCounts/missing/").json()
        self.assertEqual([m["serial"] for m in missing], ["NZ-1"])
        self.assertEqual(self.client.post(f"/api/CycleCounts/{c['id']}/resolve-missing/",
                                          {"part": str(unit.id), "note": ""}, format="json").status_code, 400)
        self.client.post(f"/api/CycleCounts/{c['id']}/resolve-missing/",
                         {"part": str(unit.id), "note": "Shipped on a rush order, not booked"}, format="json")
        self.assertEqual(self.client.get("/api/CycleCounts/missing/").json(), [])

    def test_differences_wait_to_be_keyed_into_the_erp(self):
        lot = self._lot("KY-A", qty="20", where="Rack 40")
        c = self.client.post("/api/CycleCounts/", {"location": "Rack 40"}, format="json").json()
        self.client.post(f"/api/CycleCounts/{c['id']}/record/",
                         {"entries": [{"kind": "LOT", "id": str(lot.id), "counted": "19"}]}, format="json")
        self.client.post(f"/api/CycleCounts/{c['id']}/submit/", format="json")
        self.client.post(f"/api/CycleCounts/{c['id']}/apply/",
                         {"note": "x", "reasons": {f"LOT:{lot.id}": "NOT_BOOKED"}}, format="json")
        self.assertEqual([k["id"] for k in self.client.get("/api/CycleCounts/to-key/").json()], [c["id"]])
        xlsx = self.client.get("/api/CycleCounts/to-key-xlsx/")
        self.assertEqual(xlsx.status_code, 200)
        r = self.client.post("/api/CycleCounts/mark-keyed/", {"counts": [c["id"]]}, format="json")
        self.assertEqual(r.json(), {"marked": 1})
        self.assertEqual(self.client.get("/api/CycleCounts/to-key/").json(), [])

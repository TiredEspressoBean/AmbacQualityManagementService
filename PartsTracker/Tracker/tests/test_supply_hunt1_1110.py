"""Supply hunt round 1 (2026-11-10): regression tests for the S-numbered fixes.

One class per finding; each docstring names it. Not covered here: S5's staging-list
half (`staging_list` needs a scheduled window to produce a job — the reservation half is
pinned through `reserved_by_lot` / `plan_draw`), and S8's `order_shipping` half (same
date rule as `delivery_performance`, which is pinned).
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from Tracker.tests.base import TenantContextMixin, TenantTestCase
from Tracker.tests.test_outside_process import _OSPFixtureMixin
from Tracker.utils.tenant_context import reset_current_tenant, set_current_tenant_id

User = get_user_model()


# --------------------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------------------

class _SupplyFixture(APITestCase):
    """A tenant, a superuser on it, a customer and a bar-stock material — as
    test_supply_followups_1005's fixture."""

    @classmethod
    def setUpTestData(cls):
        from Tracker.models import Companies, Material, Tenant
        cls.tenant = Tenant.objects.create(name="Hunt1", slug="supply-hunt1-1110")
        token = set_current_tenant_id(cls.tenant.id)
        try:
            cls.user = User.objects.create_user(username="sh1", email="sh1@x.test", password="x",
                                                tenant=cls.tenant, is_staff=True)
            cls.user.is_superuser = True
            cls.user.save(update_fields=["is_superuser"])
            cls.acme = Companies.objects.create(tenant=cls.tenant, name="Acme Seals", is_customer=False)
            cls.fleet = Companies.objects.create(tenant=cls.tenant, name="Fleet Co", is_supplier=False)
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
        kw.setdefault("received_date", date.today())
        return MaterialLot.objects.create(
            tenant=self.tenant, lot_number=number, material=self.bar, quantity=Decimal(qty),
            quantity_remaining=Decimal(qty), unit_of_measure="ft", status=status, supplier=self.acme,
            owner=owner, location=seed_location(self.tenant, where) if where else None, **kw)


class _ConsumptionFixture(TenantContextMixin, TestCase):
    """One step consuming 2 of a seal kit per unit — as test_material_consumption."""

    slug = "supply-hunt1-consume"

    def setUp(self):
        super().setUp()
        from Tracker.models import (
            BOM, BOMLine, Material, Parts, PartTypes, Processes, ProcessStep, Steps, Tenant,
            WorkOrder, WorkOrderStatus,
        )
        self.tenant = Tenant.objects.create(name="H1C", slug=self.slug, tier="PRO")
        self.set_tenant_context(self.tenant)
        self.operator = User.objects.create_user(
            username=f"{self.slug}-op", email=f"{self.slug}@c.test", password="x", tenant=self.tenant)
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Injector")
        self.process = Processes.objects.create(tenant=self.tenant, name="P", part_type=self.pt)
        self.step = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Assemble", step_type="TASK")
        ProcessStep.objects.create(process=self.process, step=self.step, order=1)
        self.seal = Material.objects.create(tenant=self.tenant, name="Seal Kit")
        self.key = ('MATERIAL', self.seal.id)
        bom = BOM.objects.create(tenant=self.tenant, part_type=self.pt, bom_type='ASSEMBLY',
                                 status='RELEASED', version=1)
        BOMLine.objects.create(tenant=self.tenant, bom=bom, material=self.seal, quantity=2,
                               source='BUY', consumed_at_step=self.step)
        self.wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-H1", quantity=2, process=self.process,
            workorder_status=WorkOrderStatus.IN_PROGRESS)
        self.parts = [Parts.objects.create(tenant=self.tenant, ERP_id=f"WO-H1-P{i}", part_type=self.pt,
                                           work_order=self.wo, step=self.step) for i in range(2)]

    def _lot(self, number, qty=10, status='ACCEPTED'):
        from Tracker.models import MaterialLot
        return MaterialLot.objects.create(
            tenant=self.tenant, material=self.seal, lot_number=number,
            quantity=Decimal(str(qty)), quantity_remaining=Decimal(str(qty)),
            unit_of_measure="EA", received_date=timezone.localdate(),
            received_by=self.operator, status=status)

    def _pick(self, lot, qty, wo=None):
        from Tracker.services.mes.staging import record_pick
        wo = wo or self.wo
        return record_pick(self.tenant, wo.id, self.step.id, self.seal.id, qty,
                           [{'lot_id': str(lot.id), 'lot_number': lot.lot_number, 'qty': qty}],
                           self.operator, qty_required=qty)

    def _set_status(self, lot, status):
        from Tracker.models import MaterialLot
        MaterialLot.objects.filter(pk=lot.pk).update(status=status)
        lot.refresh_from_db()


# --------------------------------------------------------------------------------------
# Cycle count
# --------------------------------------------------------------------------------------

class S3CountSnapshotsOnlyUsableLotsTests(_SupplyFixture):
    """S3: a location count snapshots only ACCEPTED / IN_USE lots. A rejected or held lot
    at the location can't be adjusted, and one such line failed the whole apply."""

    def test_held_and_rejected_lots_are_not_lines_and_the_count_applies(self):
        good = self._lot("S3-A", qty="100", where="Rack S3")
        drawn = self._lot("S3-B", qty="50", status="IN_USE", where="Rack S3")
        from Tracker.models import MaterialLot
        MaterialLot.objects.filter(pk=drawn.pk).update(quantity_remaining=Decimal(30))
        self._lot("S3-Q", qty="20", status="QUARANTINE", where="Rack S3")
        self._lot("S3-R", qty="20", status="REJECTED", where="Rack S3")

        start = self.client.post("/api/CycleCounts/", {"location": "Rack S3"}, format="json")
        self.assertEqual(start.status_code, 201, start.content)
        c = start.json()
        self.assertEqual({l["label"] for l in c["lines"]}, {"S3-A", "S3-B"})

        self.client.post(f"/api/CycleCounts/{c['id']}/record/", {"entries": [
            {"kind": "LOT", "id": str(good.id), "counted": "98"},
            {"kind": "LOT", "id": str(drawn.id), "counted": "30"},
        ]}, format="json")
        self.client.post(f"/api/CycleCounts/{c['id']}/submit/", format="json")
        done = self.client.post(f"/api/CycleCounts/{c['id']}/apply/",
                                {"note": "Two short", "reasons": {f"LOT:{good.id}": "NOT_BOOKED"}},
                                format="json")
        self.assertEqual(done.status_code, 200, done.content)
        self.assertEqual(done.json()["status"], "APPLIED")
        good.refresh_from_db()
        self.assertEqual(good.quantity_remaining, Decimal(98))


# --------------------------------------------------------------------------------------
# Consumption
# --------------------------------------------------------------------------------------

class S1WrongLotReturnKeepsHoldTests(_ConsumptionFixture):
    """S1: "Wrong lot?" — returning the quantity to an old lot that has since been held
    or rejected leaves that status alone (it used to lift the hold)."""

    slug = "supply-hunt1-s1"

    def _corrected(self, held_status):
        from Tracker.models import MaterialUsage
        from Tracker.services.mes.consumption import correct_usage_lot
        wrong = self._lot("WRONG")
        right = self._lot("RIGHT")
        usage = MaterialUsage.objects.create(
            tenant=self.tenant, lot=wrong, part=self.parts[0], work_order=self.wo,
            step=self.step, qty_consumed=Decimal('2'), consumed_by=self.operator)
        self._set_status(wrong, held_status)
        correct_usage_lot(usage, right, user=self.operator, reason="Picked from the next bin")
        wrong.refresh_from_db()
        return wrong

    def test_a_quarantined_old_lot_stays_quarantined(self):
        wrong = self._corrected('QUARANTINE')
        self.assertEqual((wrong.quantity_remaining, wrong.status), (Decimal('10'), 'QUARANTINE'))

    def test_a_rejected_old_lot_stays_rejected(self):
        wrong = self._corrected('REJECTED')
        self.assertEqual((wrong.quantity_remaining, wrong.status), (Decimal('10'), 'REJECTED'))


class S2HeldPickedLotNotDrawnTests(_ConsumptionFixture):
    """S2: a lot in the tote that was quarantined after the pick is not drawn by
    consume_for_step ("No draw can take from it")."""

    slug = "supply-hunt1-s2"

    def test_a_picked_lot_held_since_is_not_drawn(self):
        from Tracker.models import MaterialUsage
        from Tracker.services.mes.consumption import consume_for_step
        picked = self._lot("PICKED")
        other = self._lot("OTHER")
        self._pick(picked, 4)
        self._set_status(picked, 'QUARANTINE')

        consume_for_step(self.parts[0], self.step, self.operator)

        self.assertEqual(
            list(MaterialUsage.objects.filter(part=self.parts[0]).values_list('lot_id', flat=True)),
            [other.id])
        picked.refresh_from_db()
        self.assertEqual((picked.quantity_remaining, picked.status), (Decimal('10'), 'QUARANTINE'))


class S5OwnPickNotReservedAgainstItselfTests(_ConsumptionFixture):
    """S5: a job's own pick isn't held against it — `reserved_by_lot(exclude_job=…)`
    omits that job's line, so `plan_draw` offers its own tote; another job's pick still
    counts. (The staging-list half is not covered here.)"""

    slug = "supply-hunt1-s5"

    def test_the_jobs_own_line_is_excluded_and_others_are_not(self):
        from Tracker.models import WorkOrder, WorkOrderStatus
        from Tracker.services.mes.consumption import plan_draw, reserved_by_lot
        lot = self._lot("TOTE", qty=10)
        self._pick(lot, 7)
        own = (self.wo.id, self.step.id)

        self.assertEqual(reserved_by_lot(self.key, self.tenant), {str(lot.id): Decimal('7')})
        self.assertEqual(reserved_by_lot(self.key, self.tenant, exclude_job=own), {})
        # Without the exclusion only 3 are free; with it the job's own 7 are its own.
        self.assertEqual(sum(p['take'] for p in plan_draw(self.key, self.tenant, Decimal('7'))), 3.0)
        plan = plan_draw(self.key, self.tenant, Decimal('7'), exclude_job=own)
        self.assertEqual([(p['lot_number'], p['take']) for p in plan], [("TOTE", 7.0)])

        other_wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-H1-B", quantity=1, process=self.process,
            workorder_status=WorkOrderStatus.IN_PROGRESS)
        self._pick(lot, 2, wo=other_wo)
        self.assertEqual(reserved_by_lot(self.key, self.tenant, exclude_job=own),
                         {str(lot.id): Decimal('2')}, "another job's pick is still held")


class S17LineIssuedOnlyWhenFullyDrawnTests(_ConsumptionFixture):
    """S17: a job's staging line covers every unit and consumption runs per unit. After
    one unit's draw the rest stays reserved; the line is issued once all of it is drawn
    (the whole reservation used to be released after the first unit)."""

    slug = "supply-hunt1-s17"

    def test_the_line_stays_reserved_until_every_unit_has_drawn(self):
        from Tracker.services.mes.consumption import (
            consume_for_step, reserved_by_lot, reserved_quantity,
        )
        lot = self._lot("TOTE", qty=10)
        line = self._pick(lot, 4)   # 2 units x 2 each

        consume_for_step(self.parts[0], self.step, self.operator)
        line.refresh_from_db()
        self.assertIsNone(line.issued_at)
        self.assertEqual(line.qty_issued, Decimal('2'))
        self.assertEqual(Decimal(str(line.picked_lots[0]['issued'])), Decimal('2'))
        self.assertEqual(reserved_by_lot(self.key, self.tenant), {str(lot.id): Decimal('2')})
        self.assertEqual(reserved_quantity(self.seal.id, self.tenant), Decimal('2'))

        consume_for_step(self.parts[1], self.step, self.operator)
        line.refresh_from_db()
        self.assertIsNotNone(line.issued_at)
        self.assertEqual(line.qty_issued, Decimal('4'))
        self.assertEqual(reserved_by_lot(self.key, self.tenant), {})
        self.assertEqual(reserved_quantity(self.seal.id, self.tenant), Decimal('0'))
        lot.refresh_from_db()
        self.assertEqual(lot.quantity_remaining, Decimal('6'))


# --------------------------------------------------------------------------------------
# Shipping
# --------------------------------------------------------------------------------------

class S4ShippedQuantityIsWhatWentTests(_SupplyFixture):
    """S4: a partly drawn lot shipped whole ships what's left — the shipment, its lot
    rows and its paperwork say 60, not the 100 received."""

    def test_a_whole_remaining_lot_ships_its_remainder(self):
        from Tracker.models import CustomerShipment, MaterialLot
        from Tracker.reports.adapters.shipment_documents import build_shipment_document_context
        from Tracker.services.mes.shipping import shipped_quantity
        lot = self._lot("S4", qty="100", status="IN_USE")
        MaterialLot.objects.filter(pk=lot.pk).update(quantity_remaining=Decimal(60))

        resp = self.client.post("/api/CustomerShipments/ship/",
                                {"lots": [{"lot_id": str(lot.id)}], "customer": str(self.fleet.id)},
                                format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        [row] = resp.json()["lots"]
        self.assertEqual((row["id"], row["quantity"]), (str(lot.id), 60.0))

        shipment = CustomerShipment.objects.get(pk=resp.json()["id"])
        lot.refresh_from_db()
        self.assertEqual(shipped_quantity(lot, shipment), Decimal(60))
        ctx = build_shipment_document_context(shipment, self.tenant, self.user)
        [item] = [i for i in ctx.items if i.serials == ["Lot S4"]]
        self.assertEqual(item.quantity, "60 ft")


class _PlantClockMixin:
    """A plant in New York: 23:30 there is 04:30 (EST) or 03:30 (EDT) the next UTC day."""

    def _plant_in_new_york(self):
        self.tenant.default_timezone = "America/New_York"
        self.tenant.save(update_fields=["default_timezone"])

    @staticmethod
    def _plant_time(day, hour, minute):
        return datetime(day.year, day.month, day.day, hour, minute, tzinfo=ZoneInfo("America/New_York"))

    def _shipment(self, at):
        from Tracker.models import CustomerShipment
        return CustomerShipment.objects.create(tenant=self.tenant, customer=self.fleet, shipped_at=at)


class S8OnTimeUsesThePlantsDateTests(_PlantClockMixin, _SupplyFixture):
    """S8: delivery performance judges on-time on the plant's date. A shipment at 23:30
    plant time on the due date is the next day in UTC, and is still on time."""

    def test_late_evening_on_the_due_date_is_on_time_and_after_midnight_is_late(self):
        from Tracker.models import Parts, PartTypes, Processes, WorkOrder, WorkOrderStatus
        from Tracker.services.mes.shipping import delivery_performance
        self._plant_in_new_york()
        due = timezone.now().date() - timedelta(days=10)
        pt = PartTypes.objects.create(tenant=self.tenant, name="Nozzle")
        proc = Processes.objects.create(tenant=self.tenant, name="Build", part_type=pt)

        def deliver(erp, at):
            wo = WorkOrder.objects.create(
                tenant=self.tenant, ERP_id=erp, quantity=1, process=proc, expected_completion=due,
                workorder_status=WorkOrderStatus.IN_PROGRESS)
            Parts.objects.create(tenant=self.tenant, ERP_id=f"{erp}-1", part_type=pt, work_order=wo,
                                 part_status="SHIPPED", customer_shipment=self._shipment(at))

        evening = self._plant_time(due, 23, 30)
        self.assertEqual(evening.astimezone(ZoneInfo("UTC")).date(), due + timedelta(days=1))
        deliver("WO-S8-A", evening)
        perf = delivery_performance(self.tenant)
        self.assertEqual((perf["deliveries"], perf["on_time"]), (1, 1))

        deliver("WO-S8-B", self._plant_time(due + timedelta(days=1), 0, 30))
        perf = delivery_performance(self.tenant)
        self.assertEqual((perf["deliveries"], perf["on_time"]), (2, 1))


class S9ShippedDateIsThePlantsDateTests(_PlantClockMixin, _SupplyFixture):
    """S9: `shipped_date(shipment)` — what the paperwork prints — is the plant's day."""

    def test_late_evening_ships_on_the_plants_day(self):
        from Tracker.services.mes.shipping import shipped_date
        self._plant_in_new_york()
        day = date(2026, 3, 2)
        shipment = self._shipment(self._plant_time(day, 23, 30))
        self.assertEqual(shipped_date(shipment), day)


# --------------------------------------------------------------------------------------
# Outside processing
# --------------------------------------------------------------------------------------

class S18BeenOutAndBackNotReadyToShipTests(_OSPFixtureMixin, TenantTestCase):
    """S18: a part IN_PROGRESS at the OSP step whose open visit already went out on a
    shipment is not offered to ship again, and send_parts_out refuses it (reusing the
    visit moved it off the closed shipment)."""

    def setUp(self):
        super().setUp()
        self._build_fixtures(n_parts=1)

    def test_a_part_back_from_the_vendor_is_not_sent_out_again(self):
        from Tracker.models import OutsideProcessShipment, Parts, PartsStatus
        from Tracker.services.mes import outside_process as osp
        part = self.parts[0]
        first = osp.send_parts_out(step=self.osp_step, parts=[part], user=self.user_a)
        # Back from the vendor and IN_PROGRESS again on the same open visit.
        Parts.objects.filter(pk=part.pk).update(part_status=PartsStatus.IN_PROGRESS)
        part.refresh_from_db()

        self.assertEqual(osp.build_ready_to_ship_groups(), [])
        with self.assertRaisesMessage(ValueError, "already been out and back"):
            osp.send_parts_out(step=self.osp_step, parts=[part], user=self.user_a)
        self.assertEqual(list(OutsideProcessShipment.objects.values_list("id", flat=True)), [first.id])

        # A part that hasn't been out is still offered.
        Parts.objects.create(tenant=self.tenant_a, ERP_id="P-OSP-NEW", part_type=self.part_type,
                             work_order=self.wo, step=self.osp_step, part_status=PartsStatus.IN_PROGRESS)
        [group] = osp.build_ready_to_ship_groups()
        self.assertEqual(group["ready_count"], 1)


# --------------------------------------------------------------------------------------
# Lots: receipt corrections, dock metrics, stock import, list filter
# --------------------------------------------------------------------------------------

class S20BlankPoRemainderNotRewrittenTests(_SupplyFixture):
    """S20: correcting a BACKORDERED lot with a blank PO must not rewrite an unrelated
    ON_ORDER lot that merely shares its item, supplier and (blank) PO."""

    def test_an_unrelated_expected_lot_is_left_alone(self):
        from Tracker.services.mes.material_lot import correct_lot_source
        lot = self._lot("S20-A", qty="12", short_receipt="BACKORDERED")
        unrelated = self._lot("S20-OO", qty="30", status="ON_ORDER", where=None, received_date=None)
        self.assertEqual((lot.erp_po_number, unrelated.erp_po_number), ("", ""))

        correct_lot_source(lot, user=self.user, reason="Slip says line 2", changes={"erp_po_line": "2"})

        lot.refresh_from_db()
        unrelated.refresh_from_db()
        self.assertEqual(lot.erp_po_line, "2")
        self.assertEqual(unrelated.erp_po_line, "")


class S13ManualHoldIsNotARelease(_SupplyFixture):
    """S13: a hold being placed (hold_reason edit with old_value "") is not counted in
    dock metrics' holds released."""

    def test_only_edits_away_from_a_reason_count(self):
        from django.contrib.contenttypes.models import ContentType
        from Tracker.models import MaterialLot, RecordEdit
        from Tracker.services.mes.dock_metrics import dock_metrics
        lot = self._lot("S13")
        ct = ContentType.objects.get_for_model(MaterialLot)
        for old, new in (("", "MANUAL_HOLD"), ("AWAITING_COC", "")):
            RecordEdit.objects.create(tenant=self.tenant, content_type=ct, object_id=lot.id,
                                      field_name="hold_reason", old_value=old, new_value=new,
                                      reason="x", edited_by=self.user)
        m = dock_metrics(self.tenant, today=timezone.now().date())
        self.assertEqual(m["holds_released"], [{"reason": "AWAITING_COC", "lots": 1}])


class S16ReimportKeepsReceivedDateTests(_SupplyFixture):
    """S16: re-importing an identical opening-stock row with a blank received date
    leaves the existing lot UNCHANGED — it used to re-date it to today."""

    def test_a_blank_received_date_does_not_move_an_existing_lot(self):
        from Tracker.models import MaterialLot
        from Tracker.services.core.clock import tenant_today
        from Tracker.services.mes.stock_import import import_stock_rows
        row = {"lot_number": "OB-S16", "item": "Bar stock 4140", "quantity": "25", "unit": "ft"}
        first = import_stock_rows(tenant=self.tenant, rows=[dict(row)])
        self.assertEqual(first["created"], 1, first)
        lot = MaterialLot.objects.get(lot_number="OB-S16")
        self.assertEqual(lot.received_date, tenant_today(self.tenant), "blank is today for a new lot")

        MaterialLot.objects.filter(pk=lot.pk).update(received_date=date(2025, 1, 15))
        again = import_stock_rows(tenant=self.tenant, rows=[dict(row)])
        self.assertEqual((again["unchanged"], again["updated"]), (1, 0), again)
        lot.refresh_from_db()
        self.assertEqual(lot.received_date, date(2025, 1, 15))


class S12OnHandFilterTests(_SupplyFixture):
    """S12: the MaterialLots list `?on_hand=true` is ACCEPTED and IN_USE — partly drawn
    lots were hidden from the Materials tab."""

    def test_on_hand_is_accepted_and_in_use(self):
        for status in ("ACCEPTED", "IN_USE", "QUARANTINE", "REJECTED", "CONSUMED", "RECEIVED"):
            self._lot(f"S12-{status}", status=status)
        self._lot("S12-ON_ORDER", status="ON_ORDER", where=None, received_date=None)
        resp = self.client.get("/api/MaterialLots/?on_hand=true")
        self.assertEqual(resp.status_code, 200, resp.content)
        numbers = {r["lot_number"] for r in resp.json()["results"]}
        self.assertEqual({n for n in numbers if n.startswith("S12-")}, {"S12-ACCEPTED", "S12-IN_USE"})


class S14CorrectSourceClearsSupplierTests(_SupplyFixture):
    """S14: correct-source is JSON-only, so a cleared supplier arrives as null (as
    multipart the client sent the text "null", refused as not a UUID)."""

    def test_json_null_clears_the_supplier(self):
        lot = self._lot("S14")
        url = f"/api/MaterialLots/{lot.id}/correct-source/"
        resp = self.client.post(url, {"supplier": None, "reason": "No supplier on the slip"},
                                format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        lot.refresh_from_db()
        self.assertIsNone(lot.supplier_id)

    def test_multipart_is_refused(self):
        lot = self._lot("S14-M")
        resp = self.client.post(f"/api/MaterialLots/{lot.id}/correct-source/",
                                {"erp_po_line": "2", "reason": "x"}, format="multipart")
        self.assertEqual(resp.status_code, 415, resp.content)


# --------------------------------------------------------------------------------------
# Material Requisition
# --------------------------------------------------------------------------------------

class S15RequisitionPicksLatestReleasedAssemblyBomTests(TenantContextMixin, TestCase):
    """S15: the Material Requisition reads the released ASSEMBLY BOM with the highest
    version — not the highest revision text, not an archived BOM, not a disassembly BOM —
    and skips archived lines."""

    def setUp(self):
        super().setUp()
        from Tracker.models import (
            BOM, BOMLine, Material, PartTypes, Processes, ProcessStep, Steps, Tenant,
            WorkOrder, WorkOrderStatus,
        )
        self.tenant = Tenant.objects.create(name="H1P", slug="supply-hunt1-s15", tier="PRO")
        self.set_tenant_context(self.tenant)
        pt = PartTypes.objects.create(tenant=self.tenant, name="Injector")
        process = Processes.objects.create(tenant=self.tenant, name="Build", part_type=pt)
        step = Steps.objects.create(tenant=self.tenant, part_type=pt, name="Assemble", step_type="TASK")
        ProcessStep.objects.create(process=process, step=step, order=1)

        def bom(revision, version, name, **kw):
            b = BOM.objects.create(tenant=self.tenant, part_type=pt, revision=revision,
                                   version=version, status="RELEASED", **kw)
            BOMLine.objects.create(tenant=self.tenant, bom=b, quantity=1, source='BUY',
                                   material=Material.objects.create(tenant=self.tenant, name=name))
            return b

        bom("Z", 1, "Superseded seal", is_current_version=False)   # highest revision text
        current = bom("A", 2, "Current seal")
        bom("C", 3, "Archived BOM seal", archived=True)
        bom("D", 4, "Teardown kit", bom_type="DISASSEMBLY")
        BOMLine.objects.create(tenant=self.tenant, bom=current, quantity=1, source='BUY', archived=True,
                               material=Material.objects.create(tenant=self.tenant, name="Removed shim"))
        self.wo = WorkOrder.objects.create(tenant=self.tenant, ERP_id="WO-S15", quantity=1, process=process,
                                           workorder_status=WorkOrderStatus.IN_PROGRESS)

    def test_only_the_latest_released_assembly_boms_live_lines(self):
        from Tracker.reports.adapters.pick_list import PickListAdapter
        ctx = PickListAdapter().build_context({"id": self.wo.id}, user=None, tenant=self.tenant)
        self.assertEqual([i.component_name for i in ctx.items], ["Current seal"])

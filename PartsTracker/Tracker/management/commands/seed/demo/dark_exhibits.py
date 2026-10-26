"""Light the exhibits the demo builds but never populates.

Every block here exists because a workflow row in `Documents/ROLE_WORKFLOW_AUDIT.md`
was verified as working in code and then found dark in the browser — the surface was
right, the demo just had nothing to put on it. Each method names the row it unblocks.

Deliberately a separate module, run as its own late phase: everything here depends on
orders, work orders, parts, lots and BOMs already existing, and keeping it out of
`orders.py` / `receiving.py` leaves those owned by the flows that build them.

Where a service exists, it is used rather than writing rows directly. That is the
lesson the audit kept re-learning: a seed that stages outcomes by setting fields
produces states the application itself can never reach, and the dead ends only show up
later as "the code is broken" when it is the data that is impossible.
"""
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from ..base import BaseSeeder


class DemoDarkExhibitSeeder(BaseSeeder):
    """Populate the surfaces the audit found built-but-empty."""

    def __init__(self, stdout, style, tenant, scale='small'):
        super().__init__(stdout, style, scale=scale)
        self.tenant = tenant
        self.today = timezone.now()

    def seed(self, users):
        out = {}
        out['order_lines'] = self.seed_order_lines()
        out['coc_customer'] = self.seed_coc_customer()
        out['customer_property'] = self.seed_customer_property()
        out['consumption'] = self.seed_material_usage(users)
        out['cycle_count'] = self.seed_cycle_count(users)
        out['doc_control'] = self.seed_document_control(users)
        out['export_control'] = self.seed_export_control()
        return out

    # ------------------------------------------------------------------ #
    # Shipping row C1 — export-control screening
    # ------------------------------------------------------------------ #
    def seed_export_control(self):
        """Mark one part type and one document as export-controlled.

        `for_export_control` excludes `itar_controlled=True` rows for a non-US person
        and logs each denial to a separate compliance channel citing 22 CFR 120.62.
        The gate was verified working in isolation but **nothing carried the flag** —
        0 of 153 parts, 0 documents — so neither side could fire.

        This lights the data side only. **Seeing the filter actually deny** needs a
        non-US-person user, and no demo user is one. Flipping an existing demo
        account's `us_person` would silently change what that persona can see
        everywhere else, which is a worse trade for a demo than leaving the denial
        path to a facility's own test account.
        """
        from django.db.models import Count
        from Tracker.models import PartTypes, Documents

        touched = []
        # Deliberately the LEAST-used part type, not the first alphabetically. The
        # hero type carries 152 of 153 parts; flagging it would make the entire demo
        # export-controlled and, the moment a facility adds a non-US user, empty.
        # A peripheral component is both realistic and contained.
        pt = (PartTypes.objects.filter(itar_controlled=False)
              .annotate(n=Count('parts')).order_by('n', 'name').first())
        if pt is not None:
            pt.itar_controlled = True
            if hasattr(pt, 'eccn') and not pt.eccn:
                pt.eccn = '9A610'
            pt.save(update_fields=[f for f in ('itar_controlled', 'eccn')
                                   if hasattr(pt, f)])
            touched.append(f"part type {pt.name} -> ITAR ({getattr(pt, 'eccn', '')})")

        doc = Documents.objects.filter(itar_controlled=False).order_by('file_name').first()
        if doc is not None:
            doc.itar_controlled = True
            doc.eccn = doc.eccn or '9E610'
            doc.export_control_reason = (doc.export_control_reason
                                         or 'Technical data for a controlled article.')
            doc.save(update_fields=['itar_controlled', 'eccn', 'export_control_reason'])
            touched.append(f"document {doc.file_name} -> ITAR")

        for x in touched:
            self.log(f"  Export control: {x}")
        return touched

    # ------------------------------------------------------------------ #
    # Shipping row 9 — "Know whether we are on time"
    # ------------------------------------------------------------------ #
    def seed_order_lines(self):
        """Give each customer order the demand line it always implied.

        `delivery_performance` keys on `work_order__order_line__due_date`, so with no
        lines there is nothing to attribute a shipment to: the board reads
        *"On time, last 90 days: —"* beside 24 shipped units, and the *Line · due*
        column is empty for the same reason.

        Migration 0178 backfilled lines onto orders that existed when `OrderLine` was
        introduced, but it is one-shot history repair and `seed_demo` creates its
        orders afterwards — so a fresh seed has produced line-less orders ever since.
        One line per (order, part type), quantity summed from its non-cancelled work
        orders, which is the same derivation the migration used.
        """
        from Tracker.models import Orders, WorkOrder, OrderLine, OrderLineStatus

        created = 0
        for order in Orders.objects.filter(company__isnull=False):
            wos = list(WorkOrder.objects.filter(related_order=order)
                       .exclude(workorder_status='CANCELLED'))
            if not wos:
                continue

            by_type = {}
            for wo in wos:
                pt = self._work_order_part_type(wo)
                if pt is None:
                    continue
                by_type.setdefault(pt, []).append(wo)

            for n, (part_type, type_wos) in enumerate(by_type.items(), start=1):
                qty = sum(int(w.quantity or 0) for w in type_wos) or len(type_wos)
                # The due date is the whole point — without it the line exists but
                # still cannot be measured against.
                due = order.estimated_completion or (self.today + timedelta(days=7)).date()

                line, made = OrderLine.objects.update_or_create(
                    tenant=self.tenant, order=order, line_number=n,
                    defaults={
                        'part_type': part_type,
                        'quantity': qty,
                        'due_date': due,
                        'status': OrderLineStatus.OPEN,
                        'notes': 'Seeded demand line (demo).',
                    },
                )
                created += 1 if made else 0
                # Peg the jobs to it. `related_order` already pointed at the order;
                # this is what lets a shipment be attributed to a dated line.
                for wo in type_wos:
                    if wo.order_line_id != line.id:
                        wo.order_line = line
                        wo.save(update_fields=['order_line'])

        self.log(f"  Order lines: {OrderLine.objects.count()} total ({created} new)")
        return created

    def _work_order_part_type(self, wo):
        first = wo.parts.first() if hasattr(wo, 'parts') else None
        return getattr(first, 'part_type', None)

    # ------------------------------------------------------------------ #
    # Shipping rows 3-4 — the CoC badge on the shipping board
    # ------------------------------------------------------------------ #
    def seed_coc_customer(self):
        """Flag one customer as requiring a CoC with every shipment.

        `requires_coc_on_shipment` drives the badge the shipping clerk reads *before*
        packing. With nobody flagged, the badge never renders and the clerk has no way
        to learn it exists.
        """
        from Tracker.models import Companies

        c = Companies.objects.filter(is_customer=True, name='Great Lakes Diesel').first()
        if c is None:
            c = Companies.objects.filter(is_customer=True).first()
        if c is None:
            return None
        if not c.requires_coc_on_shipment:
            c.requires_coc_on_shipment = True
            c.save(update_fields=['requires_coc_on_shipment'])
        self.log(f"  CoC-on-every-shipment: {c.name}")
        return c.name

    # ------------------------------------------------------------------ #
    # Shipping row 8 — "Return customer property" (ISO 9001 §8.5.3)
    # ------------------------------------------------------------------ #
    def seed_customer_property(self):
        """Give one lot a customer owner.

        The shipping board's second half filters on `owner__isnull=False`. The audit
        proved the surface works by setting an owner by hand and reverting; this makes
        it permanent so the *Customer property* group is there on a fresh seed.
        """
        from Tracker.models import MaterialLot, Companies

        if MaterialLot.objects.filter(owner__isnull=False).exists():
            return None
        owner = Companies.objects.filter(is_customer=True, name='Midwest Fleet Services').first()
        template = (MaterialLot.objects.filter(status='ACCEPTED', owner__isnull=True)
                    .order_by('lot_number').first())
        if owner is None or template is None:
            return None
        # Its own lot, supplied by the customer. Giving an owner to a lot bought from a
        # supplier took that purchase out of the supplier's scorecard (customer property
        # says nothing about a supplier), so Great Lakes read 0 lots accepted.
        lot, _ = MaterialLot.objects.update_or_create(
            tenant=self.tenant, lot_number='RCV-CUST-0001',
            defaults={
                'material_type': template.material_type, 'material': template.material,
                'supplier': owner, 'owner': owner,
                'supplier_lot_number': 'MWF-CONSIGN-01',
                'received_date': template.received_date, 'received_by': template.received_by,
                'quantity': template.quantity, 'quantity_remaining': template.quantity,
                'unit_of_measure': template.unit_of_measure, 'status': 'ACCEPTED',
                'heat_number': template.heat_number, 'location': template.location,
            },
        )
        self.log(f"  Customer property: {lot.lot_number}, supplied by {owner.name}")
        return lot.lot_number

    # ------------------------------------------------------------------ #
    # Operator row 5 — "Record which material lot was actually taken"
    # ------------------------------------------------------------------ #
    def seed_material_usage(self, users):
        """Draw the BOM's material for parts that have already passed a consuming step.

        `MaterialUsage` was **0 rows tenant-wide**, which left three traveller sections
        dead for every serial — lots drawn, recorded values and overrides — plus the
        whole backward trace from a part to the lots that went into it.

        Goes through `consume_for_step`, which resolves released BOM lines, honours
        shelf life, and refuses another customer's property. Writing rows directly
        would produce usages that reconcile against no stock.
        """
        from Tracker.models import MaterialUsage, Parts, Steps
        from Tracker.services.mes.consumption import consume_for_step

        operator = self._pick_user(users, 'mike.ops@demo.ambac.com')
        if operator is None:
            return 0

        # Steps that a released BOM actually consumes at — ask the BOM, don't guess.
        consuming = set(self._consuming_step_ids())
        if not consuming:
            self.log("  Material usage: no released BOM lines consume at any step — skipped")
            return 0

        drawn = 0
        cache = {}
        # Parts that reached a consuming step, in a stable order. An unordered `[:40]`
        # took whatever rows Postgres returned first, and only a quarter of those had
        # reached Assembly — so the exhibit came and went as other seeding updated rows.
        reached = (Parts.objects
                   .filter(part_type__isnull=False, step_executions__step_id__in=consuming)
                   .distinct().order_by('id'))
        for part in reached[:40]:
            for step in Steps.objects.filter(id__in=consuming):
                # Only for work the part has actually reached or passed.
                if not part.step_executions.filter(step=step).exists():
                    continue
                # Advancing a part past the step draws its material already (the seed
                # walks advance through the real service), so only backfill what was
                # never drawn. Drawing again booked every assembled unit's lots twice.
                if MaterialUsage.objects.filter(part=part, step=step).exists():
                    continue
                res = consume_for_step(part, step, operator, bom_cache=cache)
                drawn += len(getattr(res, 'usages', []) or [])

        self.log(f"  Material usage: {MaterialUsage.objects.count()} rows ({drawn} drawn now)")
        return drawn

    def _consuming_step_ids(self):
        from Tracker.models import BOMLine
        try:
            return list(BOMLine.objects.filter(consumed_at_step__isnull=False)
                        .values_list('consumed_at_step_id', flat=True).distinct())
        except Exception:
            return []

    # ------------------------------------------------------------------ #
    # Receiving row 8 — "Count stock"
    # ------------------------------------------------------------------ #
    def seed_cycle_count(self, users):
        """Leave one blind count submitted but NOT applied.

        Applying needs `apply_cyclecount` — a lead. Leaving it submitted is what makes
        the exercise real: the trainee counts and submits, and someone else applies.
        A pre-applied count would teach neither half.
        """
        from Tracker.models import CycleCount, StorageLocation
        from Tracker.services.mes import cycle_count as cc

        if CycleCount.objects.exists():
            return None
        loc = (StorageLocation.objects.filter(name__icontains='Main Stores').first()
               or StorageLocation.objects.first())
        counter = self._pick_user(users, 'mike.ops@demo.ambac.com')
        if loc is None or counter is None:
            return None

        count = cc.start_count(self.tenant, loc.name, counter, blind=True)
        entries = self._count_entries(count)
        if entries:
            cc.record_count(count, entries)
        cc.submit_count(count, counter)
        self.log(f"  Cycle count: {count.count_number} submitted at {loc.name} (awaiting apply)")
        return count.count_number

    def _count_entries(self, count):
        """Count every line on the sheet, the first lot deliberately short — a variance
        to work. A line left blank isn't a count; leaving three of five blank made them
        read as missing stock.

        Entry shape is the service's own: ``{kind, id, counted, note}``.
        """
        entries = []
        lines = sorted(count.lines, key=lambda l: l.get('label') or '')
        for i, line in enumerate(lines):
            on_hand = Decimal(str(line.get('expected') or 0))
            short = i == 0 and line.get('kind') == 'LOT' and on_hand > 1
            entries.append({
                'kind': line.get('kind'),
                'id': line.get('id'),
                'counted': on_hand - 1 if short else on_hand,
                'note': 'One short on the shelf.' if short else '',
            })
        return entries

    def _pick_user(self, users, email):
        """Demo users come back as lists plus a `by_email` map, not role keys."""
        by_email = users.get('by_email') or {}
        if email in by_email:
            return by_email[email]
        for key in ('employees', 'managers', 'qa_staff'):
            seq = users.get(key) or []
            if seq:
                return seq[0]
        return users.get('admin')

    # ------------------------------------------------------------------ #
    # Document Controller rows 6 and 7 — review loop, classification tiers
    # ------------------------------------------------------------------ #
    def seed_document_control(self, users):
        """Put one document past its review date and one above Internal.

        Both are what the role is most distinctively *for*, and both were dark: the
        *Due for review* tile read 0 because no document had a review date, and every
        document was `Internal` so the classification filter could never be seen
        hiding anything.
        """
        from Tracker.models import ClassificationLevel, Documents

        touched = []
        docs = list(Documents.objects.order_by('file_name'))
        if not docs:
            return touched

        # A released drawing whose review date has passed, named rather than "the
        # first document": a new document sorting ahead of it once took the exhibit.
        overdue = next((d for d in docs if d.file_name == 'DWG-CRI-8800'), docs[0])
        overdue.review_date = (self.today - timedelta(days=14)).date()
        overdue.save(update_fields=['review_date'])
        touched.append(f"{overdue.file_name} due for review")

        if len(docs) > 1:
            classified = next((d for d in docs if d.file_name == 'DWG-CRI-8800'), docs[1])
            if (classified.classification or '').lower() in ('', 'internal', 'public'):
                classified.classification = ClassificationLevel.CONFIDENTIAL
                classified.save(update_fields=['classification'])
                touched.append(f"{classified.file_name} -> Confidential")

        for t in touched:
            self.log(f"  Document control: {t}")
        return touched

"""
Demo seeder for Receiving Inspection (purchased material, Flow A).

Receiving inspection is modeled as a RECEIVING Step node in the part type's process
(not a standalone plan). This seeder:
  - adds a RECEIVING step to the primary part type, wired into its process, with a
    couple of required_measurements (the characteristics);
  - creates a default (all-suppliers) C=0 sampling ruleset + one tightened
    supplier-specific ruleset on that step;
  - receives a spread of MaterialLots and drives them through the real receiving
    services so every screen has data (RECEIVED / AWAITING_INSPECTION / ACCEPTED / REJECTED).
"""
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from Tracker.services.mes.locations import seed_location
from Tracker.models import (
    MaterialLot, Steps, StepMeasurementRequirement, MeasurementDefinition,
    SamplingRuleSet, SamplingRule, ProcessStep,
)
from Tracker.services.qms import receiving_inspection

from ..base import BaseSeeder


class DemoReceivingSeeder(BaseSeeder):
    """Seeds a RECEIVING step + supplier sampling rulesets + MaterialLots."""

    def seed(self, companies, users, manufacturing):
        self.log("Creating demo receiving inspection data...")
        result = {'step': None, 'rulesets': [], 'lots': []}

        part_types = manufacturing.get('part_types', []) if isinstance(manufacturing, dict) else []
        processes = manufacturing.get('processes', []) if isinstance(manufacturing, dict) else []
        if not part_types:
            self.log("  Warning: no part types available, skipping receiving seed", warning=True)
            return result
        part_type = part_types[0]
        process = processes[0] if processes else None

        company_map = companies.get('by_name', {}) if isinstance(companies, dict) else {}
        # Incoming material comes from a material SUPPLIER — not AMBAC (the internal
        # org) and not a customer. Great Lakes Diesel is the demo's parts supplier.
        supplier = company_map.get('Great Lakes Diesel') or next(
            (c for c in company_map.values() if 'AMBAC' not in (c.name or '')), None)

        employees = users.get('employees', []) if isinstance(users, dict) else []
        received_by = employees[0] if employees else None
        if received_by is None:
            self.log("  Warning: no employees available, skipping receiving seed", warning=True)
            return result

        # --- RECEIVING step node ---
        recv_step, _ = Steps.objects.update_or_create(
            tenant=self.tenant, part_type=part_type, step_type='RECEIVING',
            name='Receiving Inspection',
            defaults={'description': 'Incoming inspection of purchased material.'},
        )
        result['step'] = recv_step

        # Characteristics on the step (reuse the measurement-requirement machinery)
        visual, _ = MeasurementDefinition.objects.update_or_create(
            tenant=self.tenant, step=recv_step, label='Visual Inspection',
            defaults={'type': 'PASS_FAIL'},
        )
        diameter, _ = MeasurementDefinition.objects.update_or_create(
            tenant=self.tenant, step=recv_step, label='Outer Diameter',
            defaults={'type': 'NUMERIC', 'unit': 'mm',
                      'nominal': Decimal('25.000000'),
                      'upper_tol': Decimal('0.050000'), 'lower_tol': Decimal('0.050000')},
        )
        for m in (visual, diameter):
            StepMeasurementRequirement.objects.get_or_create(step=recv_step, measurement=m)
        # NB: receiving capture defaults to the per-unit AQL sample grid. To run
        # the inspection as DWI instead, author substeps on this RECEIVING step
        # via the substep editor (the operator runtime + ReceivingNode support it).

        # Purchased-material receiving is a STANDALONE plan (RIP): the receiving
        # flow resolves it by (part_type, step_type=RECEIVING) — process membership
        # is irrelevant, and attaching it to the chain just renders an unreachable
        # dangling node in the flow editor. Detach any previously-seeded wiring.
        if process is not None:
            ProcessStep.objects.filter(process=process, step=recv_step).delete()

        # --- Sampling rulesets on the step (default + supplier-specific) ---
        default_rs, _ = SamplingRuleSet.objects.update_or_create(
            tenant=self.tenant, step=recv_step, supplier=None, name='Receiving C=0 (all suppliers)',
            defaults={'part_type': part_type, 'process': process, 'active': True,
                      'aql': Decimal('1.0'), 'inspection_level': 'II', 'severity': 'NORMAL', 'strategy': 'C0'},
        )
        SamplingRule.objects.get_or_create(
            tenant=self.tenant, ruleset=default_rs, rule_type='C_ZERO', defaults={'order': 1})
        result['rulesets'].append(default_rs)

        if supplier is not None:
            tightened_rs, _ = SamplingRuleSet.objects.update_or_create(
                tenant=self.tenant, step=recv_step, supplier=supplier,
                name=f'Receiving C=0 ({supplier.name}, tightened)',
                defaults={'part_type': part_type, 'process': process, 'active': True,
                          'aql': Decimal('0.65'), 'inspection_level': 'III', 'severity': 'TIGHTENED', 'strategy': 'C0'},
            )
            SamplingRule.objects.get_or_create(
                tenant=self.tenant, ruleset=tightened_rs, rule_type='C_ZERO', defaults={'order': 1})
            result['rulesets'].append(tightened_rs)

        # --- MaterialLots across the lifecycle ---
        today = timezone.now().date()

        # This part type is dual-sourced: normally made in-house, but also bought
        # from a supplier — so received lots run receiving inspection against the
        # RECEIVING step above (which is keyed to this part type). Flipping can_buy
        # also demonstrates the make/buy sourcing attribute.
        if not part_type.can_buy:
            part_type.can_buy = True
            part_type.purchase_lead_time_days = part_type.purchase_lead_time_days or 14
            part_type.save(update_fields=['can_buy', 'purchase_lead_time_days'])


        def make_lot(suffix, qty, days_ago, late=False):
            received = today - timedelta(days=days_ago)
            # On-time: promised on/after receipt. Late: promised before receipt.
            promised = received - timedelta(days=2) if late else received + timedelta(days=1)
            lot, _ = MaterialLot.objects.update_or_create(
                tenant=self.tenant, lot_number=f"RCV-MAT-{suffix}",
                defaults={
                    'material_type': part_type, 'supplier': supplier,
                    'supplier_lot_number': f"SUP-{suffix}",
                    'erp_po_number': f"PO-2026-{suffix}",
                    'promised_date': promised,
                    'received_date': received,
                    'received_by': received_by,
                    'quantity': Decimal(qty), 'quantity_remaining': Decimal(qty),
                    'unit_of_measure': 'EA', 'status': 'RECEIVED',
                    # The part type requires one (armed above). These lots carry it
                    # so they pass the gate; RCV-MAT-HOLD deliberately does not.
                    'heat_number': f"HT-2026-{suffix}",
                    'location': seed_location(self.tenant, 'Receiving Dock', kind='DOCK', receiving_dock=True),
                },
            )
            return lot

        # Four lots that auto-routed into the inspection queue on receipt
        # (0002 arrived late for an OTD ding). route_received_lot mirrors the
        # standards-compliant auto-on-receipt behavior the API applies.
        for suffix, qty, days, late in (('0001', '250', 2, False), ('0002', '60', 1, True),
                                        ('0003', '500', 3, False), ('0004', '40', 1, False)):
            lot = make_lot(suffix, qty, days, late=late)
            receiving_inspection.route_received_lot(lot, received_by)
            result['lots'].append(lot)

        # One ACCEPTED, one REJECTED
        accepted = make_lot('0005', '120', 5)
        try:
            report = receiving_inspection.open_inspection(accepted, received_by)
            receiving_inspection.record_inspection(
                report, [{'definition': str(visual.id), 'value_pass_fail': 'PASS'}], received_by)
            receiving_inspection.accept(report, received_by)
            result['lots'].append(accepted)
        except ValueError as e:
            self.log(f"  Skipped accept flow: {e}", warning=True)

        rejected = make_lot('0006', '80', 6)
        try:
            report = receiving_inspection.open_inspection(rejected, received_by)
            # Reject through `reject_lot`, NOT `receiving_inspection.reject`. The latter
            # is the primitive: it moves the lot to REJECTED and nothing else. The
            # disposition that says what physically HAPPENS to the goods is opened by
            # the caller, and `Ship back` is gated on an open RETURN_TO_SUPPLIER one —
            # so a lot seeded the primitive way is a dead end the dock can never return,
            # which is a state no user of the product can actually reach.
            # A whole-lot reject takes `reject_whole_lot`; for anyone without it this
            # correctly becomes a *request* that holds the lot, so run it as QA.
            from Tracker.services.qms.lot_reject import reject_lot
            reject_lot(
                report, (users.get('qa_manager') if isinstance(users, dict) else None) or received_by,
                disposition_type='RETURN_TO_SUPPLIER', whole_lot=True,
                description='Plating blistered on the thread relief across the lot.')
            rejected.refresh_from_db()
            result['lots'].append(rejected)
            # Raise a SCAR against the supplier for the rejected lot (SQM).
            from Tracker.services.qms.scar import open_scar_for_lot
            scar = open_scar_for_lot(rejected, user=received_by)
            self.log(f"  Raised SCAR {scar.capa_number} for {supplier.name if supplier else 'supplier'}")
        except ValueError as e:
            self.log(f"  Skipped reject/SCAR flow: {e}", warning=True)

        # --- Expected receipts: the half of the lifecycle that happens BEFORE the dock ---
        # Every lot above has already arrived, so nothing exercised `ON_ORDER` — "ordered
        # but not yet delivered, an expected receipt, not physical stock". Without one,
        # three receiving workflows have nothing to act on: knowing what is expected,
        # chasing a late delivery, and reconciling a short or over delivery.
        #
        # ON_ORDER is safe to seed: planning counts it as incoming supply, while
        # consumption and staging use an ACCEPTED/IN_USE allowlist, so it can never be
        # picked or issued.
        def make_expected(suffix, qty, due_in_days, *, ordered=None):
            """A lot on order. No received_date, no received_by — it isn't here yet."""
            lot, _ = MaterialLot.objects.update_or_create(
                tenant=self.tenant, lot_number=f"RCV-EXP-{suffix}",
                defaults={
                    'material_type': part_type, 'supplier': supplier,
                    'supplier_lot_number': f"SUP-EXP-{suffix}",
                    'erp_po_number': f"PO-2026-EXP{suffix}", 'erp_po_line': '1',
                    'promised_date': today + timedelta(days=due_in_days),
                    'received_date': None, 'received_by': None,
                    'quantity': Decimal(qty), 'quantity_remaining': Decimal(qty),
                    'ordered_quantity': Decimal(ordered or qty),
                    'unit_of_measure': 'EA', 'status': 'ON_ORDER',
                },
            )
            return lot

        expected_due = make_expected('0101', '200', 4)          # due later this week
        expected_late = make_expected('0102', '150', -3)        # promised 3 days ago, nothing said
        expected_chased = make_expected('0103', '300', -5)      # late, and the buyer rang them

        # Chase through the SERVICE, not by setting fields. It writes the RecordEdit
        # trail and — the point of the exhibit — preserves `original_promised_date`, so
        # the supplier's on-time record is still judged against the FIRST promise. A
        # supplier cannot improve their OTD by asking for a later date.
        try:
            from Tracker.services.mes.material_lot import chase_expected_receipt
            chase_expected_receipt(
                expected_chased, user=received_by,
                note="Spoke to their scheduler: held at the plating sub-tier, "
                     "re-promised for Friday.",
                promised_date=today + timedelta(days=2))
        except (ValueError, ImportError) as e:
            self.log(f"  Skipped chase exhibit: {e}", warning=True)

        result['lots'] += [expected_due, expected_late, expected_chased]

        # --- Short delivery: 60 ordered, 40 arrived, remainder still on order ---
        # `ordered_quantity` is what makes a receipt short; without it nothing can tell
        # a full delivery from a partial one. 0004 arrived at 40 above.
        short = next((l for l in result['lots'] if l.lot_number == 'RCV-MAT-0004'), None)
        if short is not None:
            short.ordered_quantity = Decimal('60')
            short.short_receipt = 'BACKORDERED'
            short.save(update_fields=['ordered_quantity', 'short_receipt', 'updated_at'])

        self.log(f"  Created RECEIVING step, {len(result['rulesets'])} sampling rulesets, "
                 f"{len(result['lots'])} material lots "
                 f"(3 on order, 1 chased, 1 short)")
        return result

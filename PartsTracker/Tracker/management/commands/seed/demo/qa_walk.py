"""
Demo seeder for the QA Inspector Onboarding Walkthrough (WO-QA-INSPECT-01).

Stands up a dedicated work order with parts pre-staged in the exact states
`Documents/UQMES_ONBOARDING_WALKTHROUGH.md` walks against, so every section
has a live exhibit without the walker having to drive earlier parts into
those states themselves.

Runs LATE in the phase order (after OSP + Quality + DWI) so it can:
  - use `outside_process.send_parts_out` / `receive_parts_back` to open a
    RETURNED shipment on part 005,
  - reference the seeded FPIRecord + QualityReports + Disposition models,
  - piggy-back on the DWI substep authoring so the FPI banner renders.

Parts on WO-QA-INSPECT-01 (all `INJ-QA-INSPECT-###`, Common Rail Injector,
Midwest Fleet Services customer):

  001 — Nozzle Inspection, IN_PROGRESS. First-piece complete, awaiting Sarah's
        buy-off. FPIRecord.status=PENDING, designated_part=001.
  002 — Nozzle Inspection, AWAITING_QA. Sampled with reason
        'Post-repair verification' (earlier rework history at Assembly).
  003 — Flow Testing, IN_PROGRESS. Fresh — ready for Sarah to fail live in
        Section 5 of the walk.
  004 — Flow Testing, AWAITING_QA, visit_number=2. Full trail: original FAIL
        QR at 98 mL/min + CLOSED REWORK disposition.
  005 — Nitride Coating, AT_OUTSIDE_PROCESS. On a RETURNED shipment from Apex
        Plating; return inspection awaiting Sarah.
  006 — Assembly, QUARANTINED. Bare OPEN disposition assigned to Sarah as
        background 'my dispositions: 1' noise.
  007 — Cleaning, IN_PROGRESS.  (filler)
  008 — Disassembly, IN_PROGRESS. (filler)
"""
from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from Tracker.models import (
    Companies, FPIRecord, FPIStatus, Orders, OrdersStatus, Parts, PartsStatus,
    QualityReports, QuarantineDisposition, Steps, WorkOrder,
    WorkOrderPriority, WorkOrderStatus,
)
from Tracker.services.mes import outside_process

from ..base import BaseSeeder


ORDER_NUMBER = 'ORD-2024-QA-INSPECT'
WO_ERP_ID = 'WO-QA-INSPECT-01'
CUSTOMER_NAME = 'Midwest Fleet Services'

PART_PLAN = [
    # (suffix, step_name, part_status, extra_kwargs)
    ('001', 'Nozzle Inspection', PartsStatus.IN_PROGRESS, {'is_fpi_candidate': True}),
    ('002', 'Nozzle Inspection', PartsStatus.AWAITING_QA, {
        'requires_sampling': True,
        'sampling_context': {'trigger_reason': 'POST_REPAIR_VERIFICATION',
                             'reason_label': 'Post-repair verification'},
        'total_rework_count': 1,
    }),
    ('003', 'Flow Testing', PartsStatus.IN_PROGRESS, {}),
    ('004', 'Flow Testing', PartsStatus.AWAITING_QA, {
        'total_rework_count': 1,
    }),
    ('005', 'Nitride Coating', PartsStatus.IN_PROGRESS, {}),  # flipped to AT_OSP by send_parts_out
    ('006', 'Assembly', PartsStatus.QUARANTINED, {}),
    ('007', 'Cleaning', PartsStatus.IN_PROGRESS, {}),
    ('008', 'Disassembly', PartsStatus.IN_PROGRESS, {}),
]


class DemoQaWalkSeeder(BaseSeeder):
    """Stands up WO-QA-INSPECT-01 for the QA onboarding walkthrough."""

    def __init__(self, stdout, style, tenant, scale='small'):
        super().__init__(stdout, style, scale=scale)
        self.tenant = tenant
        self.today = timezone.now()

    def seed(self, companies, users, manufacturing):
        """Create the WO, parts, and every exhibit the walkthrough references.

        Args:
            companies: list of Companies objects (from company seeder).
            users: dict with user lists (from user seeder).
            manufacturing: dict with part_types + processes (from mfg seeder).

        Returns:
            dict with created order, work_order, parts, and exhibit records.
        """
        self.log("Creating QA-inspector onboarding walkthrough data...")

        result = {'order': None, 'work_order': None, 'parts': [],
                  'fpi': None, 'fail_qr': None, 'rework_disposition': None,
                  'shipment': None, 'quarantine_disposition': None}

        part_types = manufacturing.get('part_types', []) if manufacturing else []
        processes = manufacturing.get('processes', []) if manufacturing else []
        if not part_types or not processes:
            self.log("  Warning: missing part types / process; skipping.", warning=True)
            return result
        part_type = part_types[0]
        process = processes[0]

        # Roles we need: Sarah (QA Inspector, assigned to dispositions & FPI ack),
        # Maria (QA Manager, alternate approver), Mike (Operator, step executor).
        qa_users = users.get('qa_staff', []) if users else []
        employees = users.get('employees', []) if users else []
        sarah = self._pick_user(qa_users, email_contains='sarah.qa')
        maria = self._pick_user(qa_users, email_contains='maria.qa')
        mike = self._pick_user(employees, email_contains='mike.ops')
        operator = mike or (employees[0] if employees else None)
        approver = sarah or maria or operator
        if approver is None:
            self.log("  Warning: no users available; skipping.", warning=True)
            return result

        # Customer for the demo WO — reuse Midwest Fleet.
        company_map = {c.name: c for c in (companies or [])}
        customer = company_map.get(CUSTOMER_NAME)
        if customer is None:
            self.log(f"  Warning: {CUSTOMER_NAME} not found; skipping.", warning=True)
            return result

        step_map = {s.name: s for s in Steps.objects.filter(tenant=self.tenant)}

        with transaction.atomic():
            order = self._create_order(customer)
            result['order'] = order

            work_order = self._create_work_order(order, process)
            result['work_order'] = work_order

            parts = self._create_parts(order, work_order, part_type, step_map)
            result['parts'] = parts
            part_by_suffix = {p.ERP_id.split('-')[-1]: p for p in parts}

            # 001 — PENDING FPI, first piece complete, awaiting buy-off.
            fpi = self._create_pending_fpi(work_order, part_by_suffix.get('001'),
                                           step_map.get('Nozzle Inspection'), part_type)
            result['fpi'] = fpi

            # 004 — original FAIL QR + CLOSED REWORK disposition.
            fail_qr = self._create_fail_qr(part_by_suffix.get('004'),
                                           step_map.get('Flow Testing'), approver)
            result['fail_qr'] = fail_qr
            if fail_qr is not None:
                rework_dispo = self._create_rework_disposition(
                    part_by_suffix.get('004'), fail_qr,
                    step_map.get('Flow Testing'), approver)
                result['rework_disposition'] = rework_dispo

            # 005 — send out to Apex Plating, then receive back → RETURNED shipment.
            shipment = self._stage_returned_shipment(
                part_by_suffix.get('005'), step_map.get('Nitride Coating'), operator)
            result['shipment'] = shipment

            # 006 — bare OPEN disposition assigned to Sarah, no linked QR.
            quarantine_dispo = self._create_open_disposition(
                part_by_suffix.get('006'), approver)
            result['quarantine_disposition'] = quarantine_dispo

        self.log(f"  Created {ORDER_NUMBER} / {WO_ERP_ID} with {len(parts)} parts")
        self.log(f"  Exhibits: FPI={'yes' if fpi else 'no'}, "
                 f"FAIL QR={'yes' if result['fail_qr'] else 'no'}, "
                 f"OSP shipment={'yes' if shipment else 'no'}, "
                 f"OPEN dispo={'yes' if quarantine_dispo else 'no'}")
        return result

    # ---- entity creation helpers ------------------------------------------

    def _pick_user(self, users, email_contains):
        for u in users or []:
            if email_contains in (getattr(u, 'email', '') or ''):
                return u
        return None

    def _create_order(self, customer):
        return Orders.objects.update_or_create(
            tenant=self.tenant, order_number=ORDER_NUMBER,
            defaults={
                'name': 'QA Inspector Onboarding Walkthrough',
                'company': customer,
                'order_status': OrdersStatus.IN_PROGRESS,
                'estimated_completion': self.today + timedelta(days=8),
            },
        )[0]

    def _create_work_order(self, order, process):
        wo, _ = WorkOrder.objects.update_or_create(
            tenant=self.tenant, ERP_id=WO_ERP_ID,
            defaults={
                'related_order': order,
                'process': process,
                'priority': WorkOrderPriority.NORMAL,
                'workorder_status': WorkOrderStatus.IN_PROGRESS,
                'expected_completion': self.today + timedelta(days=8),
                'quantity': 8,
                'notes': 'Onboarding walkthrough exhibit — pre-staged for QA training.',
            },
        )
        WorkOrder.objects.filter(pk=wo.pk).update(
            created_at=self.today - timedelta(days=2))
        return wo

    def _create_parts(self, order, work_order, part_type, step_map):
        """Create the 8 demo parts.

        `Parts.save()` runs `_evaluate_initial_sampling()` on new parts and
        overrides `requires_sampling` / `sampling_context` via a follow-up
        `.update()`. For seeded exhibits we then re-force our desired sampling
        values with another `.update()` — bypassing save() so the evaluator
        can't clobber them again. Same pattern the existing orders seeder uses
        to backfill REWORK_NEEDED status.
        """
        parts = []
        for suffix, step_name, part_status, extra in PART_PLAN:
            step = step_map.get(step_name)
            # Separate "post-save overrides" (fields the app resets in save())
            # from normal defaults.
            sampling_override = {}
            for k in ('requires_sampling', 'sampling_context', 'sampling_rule',
                      'sampling_ruleset'):
                if k in extra:
                    sampling_override[k] = extra.pop(k)

            defaults = {
                'part_type': part_type, 'order': order, 'work_order': work_order,
                'step': step, 'part_status': part_status,
                'requires_sampling': False, 'sampling_rule': None,
                'sampling_ruleset': None, 'sampling_context': {},
                'total_rework_count': 0,
                'itar_controlled': False, 'eccn': '',
                'export_license_required': False, 'country_of_origin': '',
                'is_fpi_candidate': False, 'fpi_override_reason': '',
            }
            defaults.update(extra)
            part, _ = Parts.objects.update_or_create(
                tenant=self.tenant, ERP_id=f'INJ-QA-INSPECT-{suffix}',
                defaults=defaults,
            )
            # Force our sampling values after save() ran its evaluator.
            if sampling_override:
                Parts.objects.filter(pk=part.pk).update(**sampling_override)
                part.refresh_from_db()
            parts.append(part)
        return parts

    def _create_pending_fpi(self, work_order, part, step, part_type):
        """PENDING FPI with designated_part set → check_status returns
        satisfied=False, has_pending=True, designated_part_id set. The
        FpiStatusBanner surfaces 'awaiting buy-off' when the operator's
        step-execution is complete; for the seed we just make the FPI
        pending with a designated part so Sarah sees a banner she can act on.
        """
        if not (work_order and part and step):
            return None
        fpi, _ = FPIRecord.objects.update_or_create(
            tenant=self.tenant, work_order=work_order, step=step,
            defaults={
                'part_type': part_type,
                'designated_part': part,
                'status': FPIStatus.PENDING,
                'shift_date': (self.today - timedelta(hours=4)).date(),
            },
        )
        FPIRecord.objects.filter(pk=fpi.pk).update(
            created_at=self.today - timedelta(hours=6))
        return fpi

    def _create_fail_qr(self, part, step, inspector):
        if not (part and step and inspector):
            return None
        qr, _ = QualityReports.objects.update_or_create(
            tenant=self.tenant, report_number='QR-QA-INSPECT-004-FT',
            defaults={
                'part': part, 'step': step, 'status': 'FAIL',
                'description': 'Flow rate 98 mL/min - below LSL of 100 mL/min. '
                               'Reworked and returned for re-inspection.',
                'detected_by': inspector, 'verified_by': None,
                'sampling_method': 'manual', 'is_first_piece': False,
                'file': None, 'sampling_audit_log': None,
            },
        )
        QualityReports.objects.filter(pk=qr.pk).update(
            created_at=self.today - timedelta(days=1, hours=8))
        return qr

    def _create_rework_disposition(self, part, quality_report, step, approver):
        if not (part and quality_report and step and approver):
            return None
        created_at = self.today - timedelta(days=1, hours=6)
        resolved_at = self.today - timedelta(hours=6)
        disp, _ = QuarantineDisposition.objects.update_or_create(
            tenant=self.tenant,
            disposition_number='DISP-QAI-004-REW',
            defaults={
                'part': part,
                'disposition_type': 'REWORK',
                'current_state': 'CLOSED',
                'severity': 'MAJOR',
                'description': quality_report.description,
                'resolution_notes': 'Flow-tested nozzle replaced; retested at bench. '
                                    'Returned to Flow Testing for re-inspection.',
                'assigned_to': approver,
                'step': step,
                'containment_action': 'Part quarantined pending rework decision.',
                'containment_completed_at': created_at + timedelta(hours=2),
                'containment_completed_by': approver,
                'requires_customer_approval': False,
                'customer_approval_received': False,
                'customer_approval_reference': '',
                'customer_approval_date': None,
                'scrap_verified': False,
                'scrap_verification_method': '',
                'scrap_verified_by': None,
                'scrap_verified_at': None,
                'resolution_completed': True,
                'resolution_completed_by': approver,
                'resolution_completed_at': resolved_at,
                'rework_attempt_at_step': 1,
            },
        )
        disp.quality_reports.add(quality_report)
        QuarantineDisposition.objects.filter(pk=disp.pk).update(created_at=created_at)
        # apply_disposition_to_part guards loop-back cascades to
        # QUARANTINED/PENDING parts, so this CLOSED REWORK dispo on an
        # AWAITING_QA part is treated as a paper record — part stays put.
        return disp

    def _stage_returned_shipment(self, part, osp_step, user):
        """Send part out and receive back → RETURNED shipment awaiting return
        inspection. Uses the outside_process service so the shipment lifecycle
        (SENT → RETURNED) and part_status transitions match production paths.
        """
        if not (part and osp_step and user):
            return None
        if not osp_step.is_outside_process or osp_step.outside_supplier_id is None:
            self.log("  Nitride Coating step is not flagged as OSP; skipping shipment.",
                     warning=True)
            return None
        try:
            shipped = outside_process.send_parts_out(
                step=osp_step, parts=[part],
                supplier=osp_step.outside_supplier,
                reference='OSP-QA-INSPECT-01', user=user)
            outside_process.receive_parts_back(shipped, user=user)
        except ValueError as e:
            self.log(f"  Skipped OSP send/receive: {e}", warning=True)
            return None
        return shipped

    def _create_open_disposition(self, part, assigned_user):
        """Bare OPEN disposition, no linked QR, assigned to Sarah. This is the
        background 'you already have work waiting' exhibit."""
        if not (part and assigned_user):
            return None
        created_at = self.today - timedelta(hours=10)
        disp, _ = QuarantineDisposition.objects.update_or_create(
            tenant=self.tenant,
            disposition_number='DISP-QAI-006-OPEN',
            defaults={
                'part': part,
                'disposition_type': '',  # untriaged
                'current_state': 'OPEN',
                'severity': 'MAJOR',
                'description': 'Torque check failed on assembly bolt at Assembly '
                               'station. Pending disposition.',
                'resolution_notes': '',
                'assigned_to': assigned_user,
                'step': None,
                'containment_action': '',
                'containment_completed_at': None,
                'containment_completed_by': None,
                'requires_customer_approval': False,
                'customer_approval_received': False,
                'customer_approval_reference': '',
                'customer_approval_date': None,
                'scrap_verified': False,
                'scrap_verification_method': '',
                'scrap_verified_by': None,
                'scrap_verified_at': None,
                'resolution_completed': False,
                'resolution_completed_by': None,
                'resolution_completed_at': None,
                'rework_attempt_at_step': 1,
            },
        )
        QuarantineDisposition.objects.filter(pk=disp.pk).update(created_at=created_at)
        return disp

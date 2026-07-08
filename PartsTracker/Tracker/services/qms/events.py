"""QMS notification event registrations.

Imported by TrackerConfig.ready() so registration runs at startup.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from Tracker.services.core.notifications import EventType, register_event


@dataclass(frozen=True)
class NCROpenedPayload:
    """Payload for `ncr.opened`. IDs are UUID strings (SecureModel PK convention)."""

    id: str                   # QualityReport id; satisfies correlation_id contract
    tenant_id: str
    part_id: str | None
    part_number: str
    work_order_id: str | None
    work_order_number: str
    step_id: str | None
    step_name: str
    severity: str
    description: str
    opened_by_id: int | None  # User PK is an int (AbstractUser default)
    opened_by_name: str
    opened_at: datetime

    @classmethod
    def sample(cls) -> 'NCROpenedPayload':
        return cls(
            id='00000000-0000-0000-0000-000000000001',
            tenant_id='00000000-0000-0000-0000-000000000000',
            part_id='00000000-0000-0000-0000-00000000002a',
            part_number='P-12345',
            work_order_id='00000000-0000-0000-0000-000000000007',
            work_order_number='WO-2026-0007',
            step_id='00000000-0000-0000-0000-000000000003',
            step_name='Final Inspection',
            severity='major',
            description='Dimensional out of tolerance on critical feature.',
            opened_by_id=1,
            opened_by_name='Jane Inspector',
            opened_at=datetime(2026, 5, 5, 14, 30),
        )


register_event(EventType(
    code='ncr.opened',
    label='Nonconformance Opened',
    domain='Quality',
    payload_schema=NCROpenedPayload,
    default_channels=['in_app', 'email'],
    default_recipient_groups=['QA Manager', 'QA Inspector'],
    default_on=True,
    transactional=False,
    description='A nonconformance report has been opened against a part or work order.',
    external_routable=False,
))


# =============================================================================
# quality.step_failure — fired from QualityReport status=FAIL
# =============================================================================

@dataclass(frozen=True)
class StepFailurePayload:
    """Payload for `quality.step_failure`. Replaces the legacy STEP_FAILURE
    event_type that used GFK scope. Tenant rules can route on part_id /
    step_id / work_order_id via CEL conditions."""

    id: str                              # QualityReport id; correlation id source
    tenant_id: str
    quality_report_id: str
    part_id: str
    part_number: str
    step_id: str | None
    step_name: str
    work_order_id: str | None
    work_order_number: str
    step_execution_id: str | None

    @classmethod
    def sample(cls) -> 'StepFailurePayload':
        return cls(
            id='00000000-0000-0000-0000-00000000001a',
            tenant_id='00000000-0000-0000-0000-000000000000',
            quality_report_id='00000000-0000-0000-0000-00000000001a',
            part_id='00000000-0000-0000-0000-00000000002a',
            part_number='P-12345',
            step_id='00000000-0000-0000-0000-000000000003',
            step_name='Final Inspection',
            work_order_id='00000000-0000-0000-0000-000000000007',
            work_order_number='WO-2026-0007',
            step_execution_id='00000000-0000-0000-0000-000000000005',
        )


register_event(EventType(
    code='quality.step_failure',
    label='Part Failed at Step',
    domain='Quality',
    payload_schema=StepFailurePayload,
    default_channels=['in_app', 'email'],
    default_recipient_groups=['QA Manager', 'QA Inspector'],
    default_on=True,
    transactional=False,
    description='A part has been failed at a step via QualityReport.',
    external_routable=False,
))


# =============================================================================
# capa.assigned — fired when a CAPA is created with an assignee OR reassigned
# to a new user. Recipient is the assignee (per-instance routing); rules use
# `recipient_strategy='from_payload'` to read `recipient_user_ids` from the
# payload at fire time.
# =============================================================================

from datetime import date


@dataclass(frozen=True)
class CapaAssignedPayload:
    """Payload for `capa.assigned`. `recipient_user_ids` carries the
    single-element list `[assigned_to.id]` for from_payload routing."""

    id: str                              # CAPA id (used for source GFK)
    tenant_id: str
    capa_id: str
    capa_number: str
    capa_type: str
    capa_type_display: str
    severity: str                        # 'CRITICAL' / 'MAJOR' / 'MINOR'
    severity_display: str
    status: str
    problem_statement: str
    assigned_to_id: int
    assigned_to_name: str
    assigned_to_email: str
    initiated_by_id: int | None
    initiated_by_name: str
    due_date: date | None
    is_reassignment: bool                # False on create, True on assigned_to change
    recipient_user_ids: list[int]        # [assigned_to_id] — for from_payload rules

    @classmethod
    def sample(cls) -> 'CapaAssignedPayload':
        return cls(
            id='00000000-0000-0000-0000-0000000000c1',
            tenant_id='00000000-0000-0000-0000-000000000000',
            capa_id='00000000-0000-0000-0000-0000000000c1',
            capa_number='CAPA-CORR-2026-0042',
            capa_type='CORRECTIVE',
            capa_type_display='Corrective',
            severity='MAJOR',
            severity_display='Major',
            status='OPEN',
            problem_statement='Recurring porosity at pressure-test step on PN-77.',
            assigned_to_id=42,
            assigned_to_name='Tina Engineer',
            assigned_to_email='tina@demo.ambac.com',
            initiated_by_id=1,
            initiated_by_name='Jane Inspector',
            due_date=date(2026, 6, 15),
            is_reassignment=False,
            recipient_user_ids=[42],
        )


register_event(EventType(
    code='capa.assigned',
    label='CAPA Assigned',
    domain='Quality',
    payload_schema=CapaAssignedPayload,
    default_channels=['in_app', 'email'],
    default_recipient_groups=[],          # routing is per-CAPA via payload.recipient_user_ids
    default_on=True,
    # `transactional` field is reserved for future use — the dispatcher does
    # not yet honor it. Cooldown is governed by `NotificationRule.min_gap_seconds`
    # alone; the starter rule for this event uses `min_gap_seconds=0` so
    # back-to-back reassignments still fire.
    transactional=True,
    description=(
        'A CAPA has been assigned to a specific user (on create or reassignment). '
        'Recipient is the assignee, routed via payload.recipient_user_ids.'
    ),
    external_routable=False,
))


# =============================================================================
# capa.ready_for_verification — fired when a CAPA's tasks + RCA are all
# complete and it can move to verification. Routed statically to the QA
# verifier group (the people who sign off effectiveness), not an individual.
# Replaces the legacy hardcoded-email task `send_capa_ready_for_verification_notification`.
# =============================================================================


@dataclass(frozen=True)
class CapaReadyForVerificationPayload:
    """Payload for `capa.ready_for_verification`. Recipients come from the
    NotificationRule (static QA group), so there is no per-user list here."""

    id: str                              # CAPA id (used for source GFK)
    tenant_id: str
    capa_id: str
    capa_number: str
    capa_type: str
    capa_type_display: str
    severity: str
    severity_display: str
    status: str
    problem_statement: str
    initiated_by_id: int | None
    initiated_by_name: str

    @classmethod
    def sample(cls) -> 'CapaReadyForVerificationPayload':
        return cls(
            id='00000000-0000-0000-0000-0000000000c1',
            tenant_id='00000000-0000-0000-0000-000000000000',
            capa_id='00000000-0000-0000-0000-0000000000c1',
            capa_number='CAPA-CORR-2026-0042',
            capa_type='CORRECTIVE',
            capa_type_display='Corrective',
            severity='MAJOR',
            severity_display='Major',
            status='PENDING_VERIFICATION',
            problem_statement='Recurring porosity at pressure-test step on PN-77.',
            initiated_by_id=1,
            initiated_by_name='Jane Inspector',
        )


register_event(EventType(
    code='capa.ready_for_verification',
    label='CAPA Ready for Verification',
    domain='Quality',
    payload_schema=CapaReadyForVerificationPayload,
    default_channels=['in_app', 'email'],
    default_recipient_groups=['QA Manager'],
    default_on=True,
    transactional=True,
    description=(
        'A CAPA has completed all tasks and RCA and is ready for effectiveness '
        'verification. Routed to the QA verifier group via the starter rule.'
    ),
    external_routable=False,
))


# =============================================================================
# supplier.unqualified — a lot was received from a supplier not qualified for it
# =============================================================================

@dataclass(frozen=True)
class SupplierUnqualifiedPayload:
    """Payload for `supplier.unqualified`. Fired when a received lot is soft-held
    because its supplier has no active qualification for the part type."""

    id: str                   # MaterialLot id; correlation id source
    tenant_id: str
    material_lot_id: str
    lot_number: str
    supplier_id: str | None
    supplier_name: str
    part_type_id: str | None
    part_type_name: str

    @classmethod
    def sample(cls) -> 'SupplierUnqualifiedPayload':
        return cls(
            id='00000000-0000-0000-0000-00000000010a',
            tenant_id='00000000-0000-0000-0000-000000000000',
            material_lot_id='00000000-0000-0000-0000-00000000010a',
            lot_number='LOT-2026-0007',
            supplier_id='00000000-0000-0000-0000-0000000000b1',
            supplier_name='Great Lakes Diesel',
            part_type_id='00000000-0000-0000-0000-00000000002a',
            part_type_name='Injector Body',
        )


register_event(EventType(
    code='supplier.unqualified',
    label='Unqualified Supplier Receipt',
    domain='Quality',
    payload_schema=SupplierUnqualifiedPayload,
    default_channels=['in_app', 'email'],
    default_recipient_groups=['QA Manager', 'Purchasing'],
    default_on=True,
    transactional=False,
    description='A received lot was held because its supplier is not qualified for the part type.',
    external_routable=False,
))


# =============================================================================
# part.unapproved — a lot was received for a (part type, supplier) with no
# active part approval (PPAP / FAI) covering it
# =============================================================================

@dataclass(frozen=True)
class PartUnapprovedPayload:
    """Payload for `part.unapproved`. Fired when a received lot is soft-held
    because its (part type, supplier) has no active part approval (PPAP/FAI)."""

    id: str                   # MaterialLot id; correlation id source
    tenant_id: str
    material_lot_id: str
    lot_number: str
    supplier_id: str | None
    supplier_name: str
    part_type_id: str | None
    part_type_name: str

    @classmethod
    def sample(cls) -> 'PartUnapprovedPayload':
        return cls(
            id='00000000-0000-0000-0000-00000000010b',
            tenant_id='00000000-0000-0000-0000-000000000000',
            material_lot_id='00000000-0000-0000-0000-00000000010b',
            lot_number='LOT-2026-0008',
            supplier_id='00000000-0000-0000-0000-0000000000b1',
            supplier_name='Great Lakes Diesel',
            part_type_id='00000000-0000-0000-0000-00000000002a',
            part_type_name='Injector Body',
        )


register_event(EventType(
    code='part.unapproved',
    label='Unapproved Part Receipt',
    domain='Quality',
    payload_schema=PartUnapprovedPayload,
    default_channels=['in_app', 'email'],
    default_recipient_groups=['QA Manager', 'Purchasing'],
    default_on=True,
    transactional=False,
    description='A received lot was held because its (part type, supplier) has no active part approval (PPAP/FAI).',
    external_routable=False,
))


# =============================================================================
# supplier.standing_review — a supplier's scorecard crossed a threshold; review
# its qualification standing (RECOMMEND-ONLY — no automatic status change)
# =============================================================================

@dataclass(frozen=True)
class SupplierStandingReviewPayload:
    """Payload for `supplier.standing_review`. Fired when a supplier's scorecard
    warrants reviewing its qualification standing. Recommend-only: the system does
    NOT transition the qualification — a human confirms via the SQ lifecycle."""

    id: str                     # supplier id; correlation source
    tenant_id: str
    supplier_id: str
    supplier_name: str
    rating: str                 # scorecard tier 'A' | 'B' | 'C'
    recommended_action: str     # 'REVIEW_CONDITIONAL' | 'REVIEW_SUSPEND' | 'REVIEW_RESTORE'
    reason: str

    @classmethod
    def sample(cls) -> 'SupplierStandingReviewPayload':
        return cls(
            id='00000000-0000-0000-0000-0000000000b1',
            tenant_id='00000000-0000-0000-0000-000000000000',
            supplier_id='00000000-0000-0000-0000-0000000000b1',
            supplier_name='Great Lakes Diesel',
            rating='C',
            recommended_action='REVIEW_SUSPEND',
            reason='Scorecard C — 1 open SCAR(s). Recommend suspension review.',
        )


register_event(EventType(
    code='supplier.standing_review',
    label='Supplier Standing Review',
    domain='Quality',
    payload_schema=SupplierStandingReviewPayload,
    default_channels=['in_app'],
    default_recipient_groups=['QA Manager'],
    default_on=True,
    transactional=False,
    description=('A supplier scorecard crossed a threshold; review its qualification '
                 'standing. Recommend-only — no automatic status change.'),
    external_routable=False,
))


# =============================================================================
# supplier.qualification_expired — a SupplierQualification passed its expiry_date
# and was flipped to EXPIRED by the daily beat task
# =============================================================================

@dataclass(frozen=True)
class SupplierQualificationExpiredPayload:
    """Payload for `supplier.qualification_expired`. Fired when the daily beat
    task expires a qualification past its expiry_date. The supplier is no longer
    on the ASL for this scope — a QA manager should re-qualify or reroute sourcing."""

    id: str                     # qualification id; correlation source
    tenant_id: str
    qualification_id: str
    qualification_number: str
    supplier_id: str
    supplier_name: str
    scope: str                  # scope_display (part type name / commodity / process)
    expiry_date: str            # ISO date

    @classmethod
    def sample(cls) -> 'SupplierQualificationExpiredPayload':
        return cls(
            id='00000000-0000-0000-0000-0000000000c1',
            tenant_id='00000000-0000-0000-0000-000000000000',
            qualification_id='00000000-0000-0000-0000-0000000000c1',
            qualification_number='SQ-000123',
            supplier_id='00000000-0000-0000-0000-0000000000b1',
            supplier_name='Great Lakes Diesel',
            scope='Injector Body',
            expiry_date='2026-06-30',
        )


register_event(EventType(
    code='supplier.qualification_expired',
    label='Supplier Qualification Expired',
    domain='Quality',
    payload_schema=SupplierQualificationExpiredPayload,
    default_channels=['in_app'],
    default_recipient_groups=['QA Manager'],
    default_on=True,
    transactional=False,
    description=('A supplier qualification passed its expiry date and was flipped to '
                 'EXPIRED. The supplier is off the ASL for this scope until re-qualified.'),
    external_routable=False,
))


# =============================================================================
# supplier.qualification_expiring_soon — a SupplierQualification is approaching
# its expiry_date (proactive re-qualification reminder, fired at 60- and 30-day
# marks by the daily beat task)
# =============================================================================

@dataclass(frozen=True)
class SupplierQualificationExpiringSoonPayload:
    """Payload for `supplier.qualification_expiring_soon`. Fired ahead of expiry
    so QA can re-qualify before the supplier drops off the ASL. Emitted once per
    reminder window (60, then 30 days out), not daily."""

    id: str                     # qualification id; correlation source
    tenant_id: str
    qualification_id: str
    qualification_number: str
    supplier_id: str
    supplier_name: str
    scope: str
    expiry_date: str            # ISO date
    days_to_expiry: int
    reminder_window: int        # 60 or 30 — which threshold this reminder is for

    @classmethod
    def sample(cls) -> 'SupplierQualificationExpiringSoonPayload':
        return cls(
            id='00000000-0000-0000-0000-0000000000c1',
            tenant_id='00000000-0000-0000-0000-000000000000',
            qualification_id='00000000-0000-0000-0000-0000000000c1',
            qualification_number='SQ-000123',
            supplier_id='00000000-0000-0000-0000-0000000000b1',
            supplier_name='Great Lakes Diesel',
            scope='Injector Body',
            expiry_date='2026-08-30',
            days_to_expiry=30,
            reminder_window=30,
        )


register_event(EventType(
    code='supplier.qualification_expiring_soon',
    label='Supplier Qualification Expiring Soon',
    domain='Quality',
    payload_schema=SupplierQualificationExpiringSoonPayload,
    default_channels=['in_app'],
    default_recipient_groups=['QA Manager'],
    default_on=True,
    transactional=False,
    description=('A supplier qualification is approaching its expiry date. Re-qualify '
                 'before it lapses. Fired at the 60- and 30-day marks.'),
    external_routable=False,
))


# =============================================================================
# supplier.inspection_discontinued — Z1.4 tightened inspection persisted 5
# consecutive lots without returning to normal; the standard says stop accepting
# the supplier's product for this step (surfaced as a recommendation, not an
# automatic ASL suspension)
# =============================================================================

@dataclass(frozen=True)
class InspectionDiscontinuedPayload:
    """Payload for `supplier.inspection_discontinued`. Fired when Z1.4 severity
    switching latches "discontinue" — QA should stop accepting this supplier's
    product for the step and drive corrective action before resuming."""

    id: str                     # severity-state id; correlation source
    tenant_id: str
    step_id: str
    step_name: str
    supplier_id: str
    supplier_name: str

    @classmethod
    def sample(cls) -> 'InspectionDiscontinuedPayload':
        return cls(
            id='00000000-0000-0000-0000-0000000000d1',
            tenant_id='00000000-0000-0000-0000-000000000000',
            step_id='00000000-0000-0000-0000-0000000000e1',
            step_name='Receiving Inspection',
            supplier_id='00000000-0000-0000-0000-0000000000b1',
            supplier_name='Great Lakes Diesel',
        )


register_event(EventType(
    code='supplier.inspection_discontinued',
    label='Inspection Discontinued (Z1.4)',
    domain='Quality',
    payload_schema=InspectionDiscontinuedPayload,
    default_channels=['in_app'],
    default_recipient_groups=['QA Manager'],
    default_on=True,
    transactional=False,
    description=('Z1.4 tightened inspection ran 5 consecutive lots without returning to '
                 'normal — stop accepting this supplier for the step and drive corrective '
                 'action. Recommendation, not an automatic suspension.'),
    external_routable=False,
))


# =============================================================================
# fpi.requested / fpi.decided — the first-piece andon loop. A pending FPI can
# idle a machine and an operator; the request is a queue-jumper to QA, the
# verdict routes back to the floor. The middle state ("seen by") lives on the
# record (acknowledged_by/at), read by the operator surface — not an event.
# =============================================================================

@dataclass(frozen=True)
class FpiRequestedPayload:
    """Payload for `fpi.requested`. Fired when a pending FPI record is created."""

    id: str                       # FPIRecord id; correlation id source
    tenant_id: str
    fpi_record_id: str
    work_order_id: str | None
    work_order_number: str
    step_id: str | None
    step_name: str
    equipment_name: str

    @classmethod
    def sample(cls) -> 'FpiRequestedPayload':
        return cls(
            id='00000000-0000-0000-0000-0000000000f1',
            tenant_id='00000000-0000-0000-0000-000000000000',
            fpi_record_id='00000000-0000-0000-0000-0000000000f1',
            work_order_id='00000000-0000-0000-0000-000000000007',
            work_order_number='WO-2026-0007',
            step_id='00000000-0000-0000-0000-000000000003',
            step_name='Final Test',
            equipment_name='Test Bench 2',
        )


register_event(EventType(
    code='fpi.requested',
    label='First Piece Waiting',
    domain='Quality',
    payload_schema=FpiRequestedPayload,
    default_channels=['in_app'],
    default_recipient_groups=['QA Inspector', 'QA Manager'],
    default_on=True,
    transactional=False,
    description='A first piece is waiting for inspection — a machine and operator may be idle behind it.',
    external_routable=False,
))


@dataclass(frozen=True)
class FpiDecidedPayload:
    """Payload for `fpi.decided`. Fired on pass / fail / waive."""

    id: str                       # FPIRecord id; correlation id source
    tenant_id: str
    fpi_record_id: str
    work_order_id: str | None
    work_order_number: str
    step_id: str | None
    step_name: str
    equipment_name: str
    status: str                   # PASSED | FAILED | WAIVED

    @classmethod
    def sample(cls) -> 'FpiDecidedPayload':
        return cls(
            id='00000000-0000-0000-0000-0000000000f1',
            tenant_id='00000000-0000-0000-0000-000000000000',
            fpi_record_id='00000000-0000-0000-0000-0000000000f1',
            work_order_id='00000000-0000-0000-0000-000000000007',
            work_order_number='WO-2026-0007',
            step_id='00000000-0000-0000-0000-000000000003',
            step_name='Final Test',
            equipment_name='Test Bench 2',
            status='PASSED',
        )


register_event(EventType(
    code='fpi.decided',
    label='First Piece Decided',
    domain='Quality',
    payload_schema=FpiDecidedPayload,
    default_channels=['in_app'],
    default_recipient_groups=['Production Manager'],
    default_on=True,
    transactional=False,
    description='A first-piece inspection was decided (passed / failed / waived) — the run can proceed or needs setup attention.',
    external_routable=False,
))

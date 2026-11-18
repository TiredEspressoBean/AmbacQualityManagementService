"""NCR aggregate services — the nonconformance, apart from what is decided about it.

An NCR records what is wrong: the description, where it was found, its severity, the
containment, and whether it needs a CAPA. Under it, each part it covers (or each rejected
quantity of a lot) has its own QuarantineDisposition — the decision — and each part keeps
its own failed inspection record, so holds, yield, SPC and history stay per part.

One rule (user ruling 2026-11-17):

- Every failed inspection record belongs to an NCR. `ncr_for_failed_report` is the one
  place that finds or raises it, from the report's FAIL save.
- A part that fails again while its NCR is open joins it (`open_ncr_for_part`).
- Parts are grouped only where the event is one: a failed batch load, a first-piece run
  with several bad pieces, or parts a person picks (`raise_ncr_for_parts`, `add_parts`).
  Nothing is grouped by guessing.
- An NCR is open while it has no decision yet or any decision under it is open, and
  closes when every one is closed (`sync_state`, run on every disposition save).
"""
from __future__ import annotations

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from Tracker.models import NCR, QualityReports, QuarantineDisposition


def raise_ncr(*, tenant, description: str = '', severity: str = 'MAJOR', step=None,
              work_order=None, batch_execution=None, raised_by=None, reports=()) -> NCR:
    """Open an NCR. `reports` are attached as its evidence (a report already on another
    NCR stays there: a record belongs to one)."""
    ncr = NCR.objects.create(
        tenant=tenant, description=description or '', severity=severity or 'MAJOR',
        step=step, work_order=work_order, batch_execution=batch_execution,
        raised_by=raised_by if getattr(raised_by, 'is_authenticated', False) else None)
    for report in reports:
        if report is not None and report.ncr_id is None:
            _attach(report, ncr)
    # Once it has its parts and findings: a load's members, the parts a person picked,
    # a capture's defects all land in the same transaction.
    ncr_id = ncr.pk
    transaction.on_commit(lambda: announce(ncr_id))
    return ncr


def announce(ncr_id) -> None:
    """Send `ncr.opened` for the NCR — once (its id is the idempotency key)."""
    from Tracker.services.core.notifications import emit
    from Tracker.services.qms.events import NCROpenedPayload

    ncr = (NCR.objects.select_related('step', 'work_order', 'raised_by')  # tenant-safe: by pk, in its tenant's commit
           .filter(pk=ncr_id).first())
    if ncr is None:
        return
    rows = members(ncr)
    parts = [m for m in rows if m['part_id'] and m['held']]
    if not parts:
        parts = [{'part_id': r.part_id, 'erp_id': r.part.ERP_id}
                 for r in ncr.reports.select_related('part').filter(part__isnull=False)]
    lots = [m['lot_number'] for m in rows if m['lot_number']]
    if len(parts) == 1:
        part_id, label = str(parts[0]['part_id']), parts[0]['erp_id']
    else:
        part_id = None
        label = (f"{len(parts)} parts" if parts else f"Lot {lots[0]}" if lots else "")
    work_order = ncr.work_order
    opener = ncr.raised_by or next((r.primary_detector for r in ncr.reports.all()
                                    if r.primary_detector), None)
    payload = NCROpenedPayload(
        id=str(ncr.pk), tenant_id=str(ncr.tenant_id) if ncr.tenant_id else '',
        part_id=part_id, part_number=label,
        work_order_id=str(work_order.pk) if work_order else None,
        work_order_number=work_order.ERP_id if work_order else '',
        step_id=str(ncr.step_id) if ncr.step_id else None,
        step_name=ncr.step.name if ncr.step_id else '',
        severity=ncr.severity, description=ncr.description or '',
        opened_by_id=opener.pk if opener else None,
        opened_by_name=(opener.get_full_name() or opener.username) if opener else '',
        opened_at=ncr.created_at, ncr_number=ncr.ncr_number, part_count=len(parts),
    )
    emit('ncr.opened', tenant=ncr.tenant, payload=payload,
         correlation_id=f"ncr:{ncr.pk}", idempotency_key=f"ncr.opened:ncr:{ncr.pk}")


def _attach(report, ncr) -> None:
    # A queryset write: the report's own save would run the FAIL signal again.
    QualityReports.objects.filter(pk=report.pk).update(ncr=ncr)  # tenant-safe: by a scoped report's pk
    report.ncr = ncr


def open_ncr_for_part(part):
    """The part's open NCR — the one a repeat failure joins — or None. The latest, when a
    person put the part on a second one."""
    return (NCR.objects  # tenant-safe: scoped by the part FK
            .filter(archived=False, state='OPEN')
            .filter(Q(dispositions__part=part, dispositions__archived=False) | Q(reports__part=part))
            .distinct().order_by('-created_at').first())


def ncr_for_failed_report(report):
    """The NCR a failed record belongs to: the one it is already on, the open one of its
    load or its part (a repeat failure joins), else a new one. Returns (ncr, raised)."""
    if report.ncr_id:
        return report.ncr, False
    ncr = None
    if report.batch_execution_id:
        ncr = (NCR.objects  # tenant-safe: scoped by the batch FK
               .filter(archived=False, state='OPEN', batch_execution_id=report.batch_execution_id)
               .order_by('created_at').first())
    elif report.part_id:
        ncr = open_ncr_for_part(report.part)
    if ncr is not None:
        _attach(report, ncr)
        refresh_description(ncr)
        return ncr, False
    batch = report.batch_execution
    part = report.part
    work_order = (batch.work_order if batch else
                  part.work_order if part is not None and part.work_order_id else None)
    from Tracker.services.qms.quality_report import report_severity
    ncr = raise_ncr(
        tenant=report.tenant, description=failure_description(report),
        severity=report_severity(report),
        step=report.step or (batch.step if batch else None), work_order=work_order,
        batch_execution=batch, raised_by=report.primary_detector, reports=[report])
    return ncr, True


_HEADER = ('description', 'severity', 'containment_action', 'containment_performed_by')


def ncr_for_new_disposition(*, part=None, reports=(), step=None, user=None, header=None) -> NCR:
    """The NCR a disposition opened by hand goes under: the open one its reports are on,
    else its part's open one, else a new one carrying `header` (description, severity,
    containment). An existing NCR keeps its header; a blank in it is filled."""
    header = {k: v for k, v in (header or {}).items() if k in _HEADER}
    ncr = next((r.ncr for r in reports if r.ncr_id and r.ncr.state == 'OPEN'), None)
    if ncr is None and part is not None:
        ncr = open_ncr_for_part(part)
    if ncr is None:
        tenant = part.tenant if part is not None else (reports[0].tenant if reports else None)
        ncr = raise_ncr(tenant=tenant, description=header.get('description', ''),
                        severity=header.get('severity') or 'MAJOR', step=step,
                        work_order=part.work_order if part is not None else None,
                        raised_by=user, reports=reports)
        rest = {k: v for k, v in header.items() if k in ('containment_action', 'containment_performed_by')}
    else:
        rest = {k: v for k, v in header.items() if v and not getattr(ncr, k)}
    if rest:
        for k, v in rest.items():
            setattr(ncr, k, v)
        ncr.save(update_fields=[*rest, 'updated_at'])
    return ncr


# --- the description -------------------------------------------------------------------

def failure_description(report) -> str:
    """What failed, in words. A report captured at a step usually has no description of
    its own, which left every auto-opened record reading "No description"."""
    if (report.description or "").strip():
        return f"Failed quality report: {report.description.strip()}"
    where = report.step.name if report.step_id else "inspection"
    findings = _findings(report) if report.pk else []
    return f"Failed {where}" + (f": {', '.join(findings)}" if findings else "")


def _findings(report) -> list[str]:
    """A failed report's findings in words: its own description, else its defects and
    out-of-spec readings — with their limits, so QA can decide without opening it."""
    if (report.description or "").strip():
        return [report.description.strip()]
    out = [d for d in report.defects.select_related("error_type")
           .values_list("error_type__error_name", flat=True)[:3] if d]
    out += [_reading_text(m) for m in
            report.measurements.select_related("definition").filter(is_within_spec=False)[:3]]
    return out


def _reading_text(m) -> str:
    """'Bore Diameter 4.007 mm (limits 3.995–4.005)' — or the pass/fail verdict."""
    d = m.definition
    if m.value_numeric is None:
        return f"{d.label} {m.value_pass_fail or 'FAIL'}"
    unit = f" {d.unit}" if d.unit else ""
    value = f"{m.value_numeric:g}"
    limits = ""
    if d.nominal is not None and (d.upper_tol is not None or d.lower_tol is not None):
        lo = f"{float(d.nominal - (d.lower_tol or 0)):g}"
        hi = f"{float(d.nominal + (d.upper_tol or 0)):g}"
        limits = f" (limits {lo}–{hi})"
    return f"{d.label} {value}{unit}{limits}"


def refresh_description(ncr) -> None:
    """Rewrite an auto-written description from every record the NCR now holds.

    A step's captures land after its report is first saved FAIL (defects, a second
    report joining), so the description written at that moment named only the step.
    Only an auto-written one ("Failed …") is rewritten — never what a person typed."""
    if not (ncr.description or "").startswith("Failed"):
        return
    findings = []
    for r in ncr.reports.order_by("created_at"):
        for f in _findings(r):
            if f not in findings:
                findings.append(f)
    where = ncr.step.name if ncr.step_id else "inspection"
    text = f"Failed {where}" + (f": {', '.join(findings)}" if findings else "")
    if text != ncr.description:
        ncr.description = text
        ncr.save(update_fields=["description", "updated_at"])


# --- state -----------------------------------------------------------------------------

def sync_state(ncr_id) -> None:
    """Open while it has no decision yet or any is open; closed, with when, once every
    disposition under it is closed. Reopening a disposition reopens it."""
    if not ncr_id:
        return
    # Unscoped: the id is the disposition's own FK, so it's that disposition's tenant —
    # and a save outside a request (a beat task, a fixture) has no tenant context.
    ncr = NCR.unscoped.filter(pk=ncr_id).first()  # tenant-safe: by the disposition's FK
    if ncr is None:
        return
    decisions = ncr.dispositions.filter(archived=False)
    closed = decisions.exists() and not decisions.exclude(current_state='CLOSED').exists()
    state = 'CLOSED' if closed else 'OPEN'
    if state == ncr.state:
        return
    ncr.state = state
    ncr.closed_at = timezone.now() if closed else None
    ncr.save(update_fields=['state', 'closed_at', 'updated_at'])


# --- members ---------------------------------------------------------------------------

def member_dispositions(ncr):
    """The decisions under the NCR, oldest first."""
    return (ncr.dispositions.filter(archived=False)
            .select_related('part', 'material_lot').order_by('created_at'))


def members(ncr) -> list[dict]:
    """What the NCR covers, one row per part (or lot): its latest decision, and whether
    that one still waits for a decision. A failed load's parts that had already moved
    past the step are listed too (held: False), so nothing in the load is hidden."""
    rows, seen = [], {}
    for d in member_dispositions(ncr):
        key = d.part_id or d.material_lot_id or d.pk
        row = {
            'part_id': d.part_id, 'erp_id': d.part.ERP_id if d.part_id else None,
            'part_status': d.part.part_status if d.part_id else None,
            'material_lot_id': d.material_lot_id,
            'lot_number': d.material_lot.lot_number if d.material_lot_id else None,
            'disposition_id': d.pk, 'disposition_number': d.disposition_number,
            'disposition_type': d.disposition_type or None, 'current_state': d.current_state,
            'awaiting_decision': not d.disposition_type and d.current_state != 'CLOSED',
            'held': True,
        }
        if key in seen:
            rows[seen[key]] = row  # the latest decision on it
        else:
            seen[key] = len(rows)
            rows.append(row)
    if ncr.batch_execution_id:
        for p in ncr.batch_execution.parts.order_by('ERP_id'):
            if p.pk not in seen:
                rows.append({'part_id': p.pk, 'erp_id': p.ERP_id, 'part_status': p.part_status,
                             'material_lot_id': None, 'lot_number': None,
                             'disposition_id': None, 'disposition_number': None,
                             'disposition_type': None, 'current_state': None,
                             'awaiting_decision': False, 'held': False})
    return rows


def member_part_ids(ncr) -> set:
    return set(ncr.dispositions.filter(archived=False, part__isnull=False)
               .values_list('part_id', flat=True))


# --- deciding --------------------------------------------------------------------------

def undecided(ncr):
    """The decisions under the NCR still waiting to be made."""
    return [d for d in member_dispositions(ncr)
            if not d.disposition_type and d.current_state != 'CLOSED']


@transaction.atomic
def decide_ncr(ncr, *, disposition_type: str, authorized_by, part_ids=None, notes: str = '',
               customer_approval: dict | None = None) -> list:
    """Decide the NCR for everything still waiting, or for the parts in `part_ids`.

    Each part's decision is its own disposition's, made through decide_disposition — the
    status mapping, the shipped and terminal guards, rework routing with its visit cap and
    MRB — exactly as a single part's (user decision 2026-11-05: the whole NCR or the parts
    QA picks). Returns the dispositions decided.

    Raises:
        ValueError: nothing left to decide; a part named that isn't waiting for a decision
            on this NCR; or any refusal decide_disposition makes.
    """
    from Tracker.services.qms.disposition import decide_disposition, route_after_decision

    if ncr.state == 'CLOSED':
        raise ValueError(f"{ncr.ncr_number} is closed; its decisions can no longer be changed.")
    waiting = [d for d in undecided(ncr) if d.part_id]
    if not waiting:
        raise ValueError(f"Everything on {ncr.ncr_number} already has a decision; change a "
                         "part's decision on its own disposition.")
    by_part = {str(d.part_id): d for d in waiting}
    if part_ids is None:
        chosen = waiting
    else:
        wanted = list(dict.fromkeys(str(i) for i in part_ids))
        if not wanted:
            raise ValueError("Choose at least one part, or decide them all.")
        if any(i not in by_part for i in wanted):
            raise ValueError(f"Only parts on {ncr.ncr_number} still waiting for a decision "
                             "can be chosen.")
        chosen = [by_part[i] for i in wanted]
    for d in chosen:
        decide_disposition(d, disposition_type=disposition_type, authorized_by=authorized_by,
                           notes=notes, customer_approval=customer_approval)
    for d in chosen:
        route_after_decision(d, authorized_by)
    return chosen


# --- raised by a person ----------------------------------------------------------------

def _common(values):
    found = {v for v in values}
    return found.pop() if len(found) == 1 else None


def _file_failure(ncr, part, user, description: str):
    """A failed record on `part`, on `ncr`, with the FAIL consequences any failure gets:
    the part held, its decision opened under the NCR (the report's save), sampling and
    the notices (record_quality_report_side_effects)."""
    from Tracker.services.qms.quality_report import record_quality_report_side_effects, sync_personnel
    report = QualityReports.objects.create(
        tenant=ncr.tenant, part=part, step=part.step, status="FAIL", ncr=ncr,
        description=description, detected_by=user if getattr(user, 'is_authenticated', False) else None)
    sync_personnel(report)
    record_quality_report_side_effects(report)
    return report


def _parts(parts):
    parts = list(dict.fromkeys(parts))
    if not parts:
        raise ValueError("Choose the parts the nonconformance covers.")
    return parts


@transaction.atomic
def raise_ncr_for_parts(parts, *, description: str, user, severity: str = 'MAJOR') -> NCR:
    """A person raises one NCR over parts they pick: one failed record and one decision
    per part, under the one NCR.

    Raises:
        ValueError: no parts, or no description of what is wrong.
    """
    parts = _parts(parts)
    description = (description or '').strip()
    if not description:
        raise ValueError("Say what is wrong — it's the NCR's description.")
    if severity not in dict(NCR.SEVERITY_CHOICES):
        raise ValueError("Severity is Critical, Major or Minor.")
    ncr = raise_ncr(
        tenant=parts[0].tenant, description=description, severity=severity,
        step=_common(p.step for p in parts), work_order=_common(p.work_order for p in parts),
        raised_by=user)
    for part in parts:
        _file_failure(ncr, part, user, description)
    return ncr


@transaction.atomic
def add_parts(ncr, parts, *, user, reason: str = '') -> list:
    """Put more parts on an open NCR: each gets its failed record and its decision under
    it, as the ones raised with it did. Returns the reports filed.

    Raises:
        ValueError: the NCR is closed, no parts, or a part already on it.
    """
    if ncr.state == 'CLOSED':
        raise ValueError(f"{ncr.ncr_number} is closed — raise a new NCR for these parts.")
    parts = _parts(parts)
    already = member_part_ids(ncr)
    on = [p.ERP_id for p in parts if p.pk in already]
    if on:
        raise ValueError(f"Already on {ncr.ncr_number}: {', '.join(on)}.")
    reason = (reason or '').strip()
    description = f"Added to {ncr.ncr_number}" + (f": {reason}" if reason else f": {ncr.description}")
    return [_file_failure(ncr, p, user, description) for p in parts]


# --- containment, CAPA -----------------------------------------------------------------

def record_containment_complete(ncr, user) -> None:
    """Containment is done: stamp who recorded it and when (the logged-in user, now).
    Who physically did it, if someone else, is `containment_performed_by` — the caller's
    to set. Idempotent: an already-recorded containment keeps its stamp."""
    if ncr.containment_completed_at:
        return
    if not (ncr.containment_action or "").strip():
        raise ValueError("Describe the containment action before marking it complete.")
    ncr.containment_completed_by = user if getattr(user, "is_authenticated", False) else None
    ncr.containment_completed_at = timezone.now()
    ncr.save(update_fields=["containment_completed_by", "containment_completed_at", "updated_at"])


def record_containment(ncr, *, action: str, user) -> None:
    """Write the containment action and record it done, as the form's save with
    "containment completed" ticked does."""
    ncr.containment_action = (action or '').strip()
    ncr.save(update_fields=["containment_action", "updated_at"])
    record_containment_complete(ncr, user)


def link_capa_ncrs(capa) -> None:
    """A CAPA linked to a report or a disposition acts on its NCR: link that too."""
    ids = set(capa.quality_reports.exclude(ncr__isnull=True).values_list('ncr_id', flat=True))
    ids |= set(capa.dispositions.exclude(ncr__isnull=True).values_list('ncr_id', flat=True))
    if ids:
        capa.ncrs.add(*ids)

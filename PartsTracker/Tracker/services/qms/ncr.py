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
              work_order=None, batch_execution=None, raised_by=None, reports=(),
              by_hand: bool = False) -> NCR:
    """Open an NCR. `reports` are attached as its evidence (a report already on another
    NCR stays there: a record belongs to one). `by_hand`: a person said what's wrong, so
    the description and severity are theirs, not the records' (header_by_hand)."""
    ncr = NCR.unscoped.create(  # tenant-safe: the tenant is given
        tenant=tenant, description=description or '', severity=severity or 'MAJOR',
        header_by_hand=by_hand and bool((description or '').strip()),
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

    # Unscoped by pk: on_commit can run after the caller's tenant context has exited.
    ncr = (NCR.unscoped.select_related('step', 'work_order', 'raised_by', 'tenant')  # tenant-safe: by the NCR's own pk
           .filter(pk=ncr_id).first())
    if ncr is None:
        return
    from Tracker.utils.tenant_context import tenant_context
    with tenant_context(ncr.tenant_id):
        _announce(ncr, emit, NCROpenedPayload)


def _announce(ncr, emit, NCROpenedPayload) -> None:
    rows = members(ncr)
    parts = ([m for m in rows if m['part_id'] and m['held']]
             or [m for m in rows if m['part_id']])
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
    QualityReports.unscoped.filter(pk=report.pk).update(ncr=ncr)  # tenant-safe: by the report's own pk
    report.ncr = ncr


def open_ncr_for_part(part):
    """The part's open NCR — the one a repeat failure joins — or None: an open NCR where
    the part's own decision is still open, or that holds its failed record with no
    decision on it yet. An NCR the part is done with (its decision closed, its load
    siblings still open) isn't its. The latest, when a person put it on a second one."""
    from django.db.models import Exists, OuterRef
    its = QuarantineDisposition.unscoped.filter(  # tenant-safe: correlated to a tenant-filtered NCR
        ncr=OuterRef('pk'), part=part, archived=False)
    open_decision = Exists(its.exclude(current_state='CLOSED'))
    record_only = (Exists(QualityReports.unscoped.filter(ncr=OuterRef('pk'), part=part))  # tenant-safe: correlated
                   & ~Exists(its))
    return (NCR.unscoped  # tenant-safe: the part's own tenant
            .filter(tenant_id=part.tenant_id, archived=False, state='OPEN')
            .filter(open_decision | record_only)
            .order_by('-created_at').first())


@transaction.atomic  # the lock below needs one; a save outside a request has none
def ncr_for_failed_report(report):
    """The NCR a failed record belongs to: the one it is already on, the open one of its
    load or its part (a repeat failure joins), else a new one. Returns (ncr, raised).

    A record already on an NCR stays there — even a closed one — unless it has just
    gone INTO fail (`report._entered_fail`, set by the save signal): a failure now on a
    record whose NCR closed (a declined whole-lot request) is a new nonconformance. A
    later save of a record that was already failed (a void, a re-save) changes nothing."""
    if report.ncr_id and (report.ncr.state == 'OPEN' or not getattr(report, '_entered_fail', False)):
        return report.ncr, False
    reclaim = bool(report.ncr_id)
    # Join-or-raise under a lock on what fails together — the part, or the load — so two
    # failures saved at once can't each raise an NCR.
    from Tracker.models import BatchExecution, Parts
    if report.batch_execution_id:
        BatchExecution.unscoped.select_for_update().filter(pk=report.batch_execution_id).first()  # tenant-safe: the report's own FK
    elif report.part_id:
        Parts.unscoped.select_for_update().filter(pk=report.part_id).first()  # tenant-safe: the report's own FK
    ncr = None
    if report.batch_execution_id:
        ncr = (NCR.unscoped  # tenant-safe: the report's own tenant
               .filter(tenant_id=report.tenant_id, archived=False, state='OPEN',
                       batch_execution_id=report.batch_execution_id)
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
    if reclaim:
        _attach(report, ncr)
    return ncr, True


_HEADER = ('description', 'severity', 'containment_action', 'containment_performed_by')


class HeaderRefused(PermissionError):
    """A header write the user may not make (change_ncr's) — the API answers 403."""


def _may_edit_header(user) -> bool:
    return bool(user and getattr(user, 'has_tenant_perm', None) and user.has_tenant_perm('change_ncr'))


def anything_decided(ncr) -> bool:
    """Something under the NCR has a decision. From then on its severity only rises
    (user ruling 2026-11-18): before it, the nonconformance is still being judged. The
    one test — the PATCH lock (approval_lock) asks it too."""
    return ncr.dispositions.filter(archived=False).exclude(disposition_type='').exists()


def _still_being_raised(ncr) -> bool:
    """An NCR the product raised from a failure, nothing decided and nobody having
    written its header: whoever raises the nonconformance (the reject, the first
    decision) still says what's wrong."""
    return not ncr.header_by_hand and not anything_decided(ncr)


def write_header(ncr, header, user) -> None:
    """The one rule for writing an NCR's header — description, severity, containment —
    from anywhere other than raising it (user ruling 2026-11-18):

    - an NCR still being raised (`_still_being_raised`) takes the raiser's description
      and severity;
    - otherwise the header is change_ncr's;
    - severity may be set either way until anything is decided, then only rises — the
      same rule, and words, as a PATCH (`anything_decided`);
    - containment is always change_ncr's;
    - a write without the permission is REFUSED (HeaderRefused), never silently dropped.
    Values equal to what's there aren't writes."""
    def current(k):
        return getattr(ncr, f'{k}_id' if k == 'containment_performed_by' else k)
    changes = {k: v for k, v in (header or {}).items()
               if k in _HEADER and v not in (None, '') and current(k) != getattr(v, 'pk', v)}
    if not changes:
        return
    raising = _still_being_raised(ncr)
    needs_perm = any(k.startswith('containment') for k in changes) or not raising
    if needs_perm and not _may_edit_header(user):
        raise HeaderRefused(f"What's wrong on {ncr.ncr_number} — its description, severity and "
                            "containment — is edited by a lead or QA.")
    if ('severity' in changes and anything_decided(ncr)
            and _RANK.get(changes['severity'], 0) < _RANK.get(ncr.severity, 0)):
        raise ValueError(f"{ncr.ncr_number} is {ncr.get_severity_display()}; its severity may only be raised.")
    for k, v in changes.items():
        setattr(ncr, k, v)
    ncr.header_by_hand = True
    ncr.save(update_fields=[*changes, 'header_by_hand', 'updated_at'])


def ncr_for_new_disposition(*, part=None, reports=(), step=None, user=None, header=None) -> NCR:
    """The NCR a disposition opened by hand goes under: the open one its reports are on,
    else its part's open one, else a new one. `header` (description, severity,
    containment) goes through write_header — the one rule — on whichever it is; a new
    one takes the description and severity as its raising."""
    header = {k: v for k, v in (header or {}).items() if k in _HEADER and v not in (None, '')}
    ncr = next((r.ncr for r in reports if r.ncr_id and r.ncr.state == 'OPEN'), None)
    if ncr is None and part is not None:
        ncr = open_ncr_for_part(part)
    if ncr is None:
        tenant = part.tenant if part is not None else (reports[0].tenant if reports else None)
        ncr = raise_ncr(tenant=tenant, description=header.pop('description', ''),
                        severity=header.pop('severity', None) or 'MAJOR', step=step,
                        work_order=part.work_order if part is not None else None,
                        raised_by=user, reports=reports, by_hand=True)
    write_header(ncr, header, user)
    return ncr


# --- the description -------------------------------------------------------------------

def failure_description(report) -> str:
    """What failed, in words. A report captured at a step usually has no description of
    its own, which left every auto-opened record reading "No description"."""
    if (report.description or "").strip():
        return f"Failed inspection: {report.description.strip()}"
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
    Never once a person has written the header (header_by_hand)."""
    if ncr.header_by_hand:
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
    follow_severity(ncr)


_RANK = {'MINOR': 1, 'MAJOR': 2, 'CRITICAL': 3}


def follow_severity(ncr) -> None:
    """Until something under it is decided, an NCR's severity IS the worst defect on its
    records as they land — up or down: a FAIL saved before its defects opens at the MAJOR
    default, and a MINOR-only finding then brings it down (user ruling 2026-11-17). Once
    decided, or once a person has set the header, it's theirs."""
    from Tracker.services.qms.quality_report import report_severity
    if ncr.header_by_hand or ncr.dispositions.filter(archived=False).exclude(disposition_type='').exists():
        return
    worst = max((report_severity(r) for r in ncr.reports.filter(superseded_at__isnull=True)),
                key=lambda s: _RANK.get(s, 0), default=ncr.severity)
    if worst != ncr.severity:
        ncr.severity = worst
        ncr.save(update_fields=["severity", "updated_at"])


# --- state -----------------------------------------------------------------------------

def sync_state(ncr_id) -> None:
    """Open while it has no decision yet or any is open; closed, with when, once every
    disposition under it is closed — or, with none, once none of its records still fails.
    Reopening a disposition reopens it."""
    if not ncr_id:
        return
    # Unscoped: the id is the disposition's own FK, so it's that disposition's tenant —
    # and a save outside a request (a beat task, a fixture) has no tenant context.
    ncr = NCR.unscoped.filter(pk=ncr_id).first()  # tenant-safe: by the disposition's FK
    if ncr is None:
        return
    decisions = ncr.dispositions.filter(archived=False)
    if decisions.exists():
        closed = not decisions.exclude(current_state='CLOSED').exists()
    elif ncr.dispositions.exists():
        # It had decisions and every one was removed: nothing is left to decide.
        closed = True
    else:
        # Nothing decided yet: open while any of its records still fails — a withdrawn
        # (superseded) one doesn't. A receiving sample re-recorded within its accept
        # number leaves nothing to decide.
        live = ncr.reports.filter(superseded_at__isnull=True)
        closed = ncr.reports.exists() and not live.filter(status='FAIL').exists()
    state = 'CLOSED' if closed else 'OPEN'
    if state == ncr.state:
        return
    ncr.state = state
    ncr.closed_at = timezone.now() if closed else None
    ncr.save(update_fields=['state', 'closed_at', 'updated_at'])


# --- members ---------------------------------------------------------------------------

def member_dispositions(ncr):
    """The decisions under the NCR, oldest first — from the prefetch when the caller made
    one (the NCR list and detail do), else one query."""
    if 'dispositions' in getattr(ncr, '_prefetched_objects_cache', {}):
        return sorted((d for d in ncr.dispositions.all() if not d.archived), key=lambda d: d.created_at)
    return list(ncr.dispositions.filter(archived=False)
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
            # Not held: a load's part already past the step, a part already shipped.
            'held': d.held,
            # An inspector's whole-lot reject request: the outcome asked for, nobody's
            # decision yet — confirmed or declined on the lot, not decided here.
            'requested': bool(d.disposition_type) and not is_decided(d),
        }
        if key in seen:
            rows[seen[key]] = row  # the latest decision on it
        else:
            seen[key] = len(rows)
            rows.append(row)
    if ncr.batch_execution_id:
        for p in sorted(ncr.batch_execution.parts.all(), key=lambda p: p.ERP_id):
            if p.pk not in seen:
                rows.append({'part_id': p.pk, 'erp_id': p.ERP_id, 'part_status': p.part_status,
                             'material_lot_id': None, 'lot_number': None,
                             'disposition_id': None, 'disposition_number': None,
                             'disposition_type': None, 'current_state': None,
                             'awaiting_decision': False, 'held': False, 'requested': False})
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
def decide_ncr(ncr, *, disposition_type: str, authorized_by, part_ids=None, disposition_ids=None,
               notes: str = '', customer_approval: dict | None = None) -> list:
    """Decide the NCR for everything still waiting — parts and rejected lot quantities —
    or for the parts in `part_ids` / the decisions in `disposition_ids` (a lot has no
    part, so it's chosen by its decision). A part with two decisions waiting (failed at
    two visits) has both decided.

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
    waiting = undecided(ncr)
    if not waiting:
        raise ValueError(f"Everything on {ncr.ncr_number} already has a decision; change a "
                         "part's decision on its own disposition.")
    if part_ids is None and disposition_ids is None:
        chosen = waiting
    else:
        by_part, by_id = {}, {str(d.pk): d for d in waiting}
        for d in waiting:
            if d.part_id:
                by_part.setdefault(str(d.part_id), []).append(d)
        wanted_parts = list(dict.fromkeys(str(i) for i in (part_ids or [])))
        wanted_ids = list(dict.fromkeys(str(i) for i in (disposition_ids or [])))
        if not wanted_parts and not wanted_ids:
            raise ValueError("Choose at least one part, or decide them all.")
        if any(i not in by_part for i in wanted_parts) or any(i not in by_id for i in wanted_ids):
            raise ValueError(f"Only parts on {ncr.ncr_number} still waiting for a decision "
                             "can be chosen.")
        chosen = list({d.pk: d for d in [*(d for i in wanted_parts for d in by_part[i]),
                                         *(by_id[i] for i in wanted_ids)]}.values())
    for d in chosen:
        try:
            decide_disposition(d, disposition_type=disposition_type, authorized_by=authorized_by,
                               notes=notes, customer_approval=customer_approval)
        except ValueError as e:
            if len(chosen) == 1:
                raise
            # Several decided at once: say which one refused (nothing is recorded).
            what = d.part.ERP_id if d.part_id else (
                f"lot {d.material_lot.lot_number}" if d.material_lot_id else d.disposition_number)
            raise ValueError(f"{what}: {e}") from e
    for d in chosen:
        route_after_decision(d, authorized_by)
    return chosen


# --- raised by a person ----------------------------------------------------------------

def _common(values):
    found = {v for v in values}
    return found.pop() if len(found) == 1 else None


def _file_failure(ncr, part, user, description: str):
    # A part no longer here (shipped, completed, scrapped) is an escape: recorded on the
    # NCR with a decision for the record, not held (ruling R6, 2026-11-18). The save
    # signal opens its decision; `held` comes from the part's status there.
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
        raised_by=user, by_hand=True)
    for part in parts:
        _file_failure(ncr, part, user, description)
    _owned_by_raiser(ncr, user)
    return ncr


def _owned_by_raiser(ncr, user) -> None:
    """QA and leads own what they raise or add parts to by hand, if nobody does; an
    operator's goes to the queue (user ruling 2026-11-18). "QA and leads" is change_ncr
    (NCR_HEADER_WRITE) — the take perm (change_quarantinedisposition) is operators' too.
    Not the automatic path: a failure's NCR waits to be taken."""
    ncr.refresh_from_db(fields=['assigned_to'])
    if (ncr.assigned_to_id is None and user is not None
            and getattr(user, 'has_tenant_perm', None) and user.has_tenant_perm('change_ncr')):
        assign_ncr(ncr, user)
        ncr.assigned_to = user


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
    # On another open NCR: one failure, one NCR — combine them instead of a second
    # failed record and decision for the same part.
    elsewhere = [(p, open_ncr_for_part(p)) for p in parts]
    elsewhere = [(p, n) for p, n in elsewhere if n is not None and n.pk != ncr.pk]
    if elsewhere:
        raise ValueError(" ".join(f"{p.ERP_id} is on {n.ncr_number}: combine instead." for p, n in elsewhere))
    reason = (reason or '').strip()
    description = f"Added to {ncr.ncr_number}" + (f": {reason}" if reason else f": {ncr.description}")
    filed = [_file_failure(ncr, p, user, description) for p in parts]
    _owned_by_raiser(ncr, user)
    return filed


# --- containment, CAPA -----------------------------------------------------------------

def record_containment_complete(ncr, user) -> None:
    """Containment is done: stamp who recorded it and when (the logged-in user, now).
    Who physically did it, if someone else, is `containment_performed_by` — the caller's
    to set. Idempotent: an already-recorded containment keeps its stamp."""
    if ncr.containment_completed_at:
        return
    if ncr.state == 'CLOSED':
        raise ValueError(f"{ncr.ncr_number} is closed, so it can't be edited.")
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


# --- combining -------------------------------------------------------------------------

@transaction.atomic
def combine_ncrs(target, others, *, user) -> NCR:
    """Combine NCRs into one (user go 2026-11-18): the others' decisions and inspection
    records move under `target`, and each emptied NCR closes as combined into it — kept,
    with the link both ways, never deleted.

    - The target keeps its header; its severity becomes the group's highest (never lower).
    - Containment: the target's stands; another's text is added to it, so nothing
      recorded is lost (the target takes it whole when it has none of its own).
    - CAPAs: the target is linked to every CAPA the others were; it says CAPA raised if
      any of them did, else it keeps its own call.

    Raises:
        ValueError: nothing to combine, the target among the others, or an NCR that
            isn't open.
    """
    from Tracker.models import CAPA  # noqa: F401 — the related manager below
    others = [o for o in others]
    if not others:
        raise ValueError("Choose the NCRs to combine into it.")
    if any(o.pk == target.pk for o in others):
        raise ValueError(f"{target.ncr_number} can't be combined into itself.")
    ids = sorted([target.pk, *(o.pk for o in others)], key=str)
    # Lock every NCR involved, in one order, so two combines can't cross.
    locked = {n.pk: n for n in NCR.objects.select_for_update().filter(pk__in=ids).order_by('pk')}  # tenant-safe: .objects auto-scopes
    if len(locked) != len(ids):
        raise ValueError("An NCR to combine was not found.")
    target = locked[target.pk]
    others = [locked[o.pk] for o in others]
    closed = [n.ncr_number for n in [target, *others] if n.state != 'OPEN']
    if closed:
        raise ValueError(f"Only open NCRs can be combined: {', '.join(closed)} is closed.")

    for other in others:
        QuarantineDisposition.objects.filter(ncr=other).update(ncr=target)  # tenant-safe: scoped by the NCR FK
        QualityReports.unscoped.filter(ncr=other).update(ncr=target)  # tenant-safe: scoped by the NCR FK
        if _RANK.get(other.severity, 0) > _RANK.get(target.severity, 0):
            target.severity = other.severity
        text = (other.containment_action or '').strip()
        if text:
            if not (target.containment_action or '').strip():
                target.containment_action = text
                target.containment_completed_at = other.containment_completed_at
                target.containment_completed_by = other.containment_completed_by
                target.containment_performed_by = other.containment_performed_by
            else:
                # The kept stamp is the first recorder's; each appended block says whose it was.
                who = []
                if other.containment_completed_by_id:
                    who.append(other.containment_completed_by.display_name)
                if other.containment_completed_at:
                    from Tracker.services.core.clock import plant_tz
                    who.append(other.containment_completed_at.astimezone(plant_tz(target.tenant))
                               .strftime('%m/%d %H:%M'))
                by = f" ({', '.join(who)})" if who else ""
                target.containment_action = f"{target.containment_action}\nFrom {other.ncr_number}{by}: {text}"
        capas = list(other.capas.all())
        if capas:
            target.capas.add(*capas)
        if other.capa_decision == 'PROMOTED' and target.capa_decision != 'PROMOTED':
            target.capa_decision = 'PROMOTED'
            target.capa_decision_note = other.capa_decision_note
            target.capa_decided_by = other.capa_decided_by
            target.capa_decided_at = other.capa_decided_at
        if target.assigned_to_id is None and other.assigned_to_id is not None:
            target.assigned_to_id = other.assigned_to_id
        other.state = 'CLOSED'
        other.closed_at = timezone.now()
        other.combined_into = target
        other.assigned_to = None
        other.save(update_fields=['state', 'closed_at', 'combined_into', 'assigned_to', 'updated_at'])
    target.save()
    # One owner: what moved in is the kept NCR's owner's now.
    if target.assigned_to_id is not None:
        _assign_open(target, target.assigned_to_id)
    sync_state(target.pk)
    target.refresh_from_db()
    return target


# --- owner -----------------------------------------------------------------------------

def todo(ncr) -> dict:
    """What an open NCR still needs: decisions to make, containment (Major/Critical —
    without it its decisions can't close), its CAPA call, decisions to close. Reads the
    prefetched dispositions."""
    open_ = ncr.state == 'OPEN'
    live = [d for d in ncr.dispositions.all() if not d.archived and d.current_state != 'CLOSED']
    return {
        'awaiting_decision': sum(1 for d in live if not d.disposition_type) if open_ else 0,
        'containment_needed': (open_ and ncr.severity in ('CRITICAL', 'MAJOR')
                               and not ncr.containment_completed_at and bool(live)),
        'capa_decision_needed': open_ and ncr.capa_decision is None and ncr.combined_into_id is None,
        'decided_to_close': sum(1 for d in live if is_decided(d)) if open_ else 0,
        # A part held at MRB (a visit cap or failed check sent it there).
        'at_mrb': any(d.escalated_from_step_id for d in live),
    }


@transaction.atomic
def close_decided(ncr, user) -> list:
    """Close every decision under the NCR that's decided and not yet closed, through the
    same completion check as closing one. All or nothing: if any can't close, none does,
    and the refusal names each one's blockers — the list of what's left to do, rather
    than an NCR half closed (user go 2026-11-18)."""
    from Tracker.services.qms.disposition import complete_disposition_resolution
    if ncr.state != 'OPEN':
        raise ValueError(f"{ncr.ncr_number} is closed.")
    ready = [d for d in (QuarantineDisposition.objects  # tenant-safe: scoped by the NCR FK
                         .filter(ncr=ncr, archived=False).exclude(current_state='CLOSED')
                         .select_related('part', 'material_lot').order_by('disposition_number'))
             if is_decided(d)]
    if not ready:
        raise ValueError(f"Nothing on {ncr.ncr_number} is decided and waiting to close.")
    blocked = []
    for d in ready:
        blockers = d.get_completion_blockers()
        if blockers:
            what = d.part.ERP_id if d.part_id else (
                f"lot {d.material_lot.lot_number}" if d.material_lot_id else d.disposition_number)
            blocked.append(f"{what}: {'; '.join(blockers)}")
    if blocked:
        raise ValueError("None closed — " + " | ".join(blocked))
    for d in ready:
        complete_disposition_resolution(d, user)
    return ready


def is_decided(d) -> bool:
    """Has a decision someone made — not a whole-lot reject request, which carries the
    outcome asked for and waits to be confirmed on the lot."""
    return bool(d.disposition_type) and not (d.material_lot_id and not d.decision_authorized_by_id)


def _assign_open(ncr, user_id) -> int:
    """Its decisions not yet closed go with the NCR."""
    return (QuarantineDisposition.objects  # tenant-safe: scoped by the NCR FK
            .filter(ncr=ncr, archived=False).exclude(current_state='CLOSED')
            .update(assigned_to_id=user_id))


@transaction.atomic
def assign_ncr(ncr, user) -> NCR:
    """Give the NCR to `user` (None: back to the queue): its containment, its CAPA call,
    and every decision under it not yet closed (user ruling 2026-11-18). Taking it from
    the queue is assigning it to yourself."""
    locked = NCR.objects.select_for_update().get(pk=ncr.pk)  # tenant-safe: .objects auto-scopes
    if locked.state != 'OPEN':
        raise ValueError(f"{locked.ncr_number} is closed; it has no owner to change.")
    locked.assigned_to = user
    locked.save(update_fields=['assigned_to', 'updated_at'])
    _assign_open(locked, user.pk if user is not None else None)
    return locked


def follow_owner(disposition) -> None:
    """A decision and its NCR have one owner: a new or unassigned decision under an
    owned NCR is the owner's; one taken on its own under an unowned NCR may make its
    taker the owner (adopt_owner)."""
    # Unscoped and fresh: a save outside a request has no tenant context, and the
    # disposition's cached NCR may predate its owner.
    ncr = NCR.unscoped.filter(pk=disposition.ncr_id).first() if disposition.ncr_id else None  # tenant-safe: own FK
    if ncr is None or disposition.current_state == 'CLOSED' or disposition.archived:
        return
    if ncr.assigned_to_id is not None and disposition.assigned_to_id is None:
        QuarantineDisposition.unscoped.filter(pk=disposition.pk).update(  # tenant-safe: own pk
            assigned_to_id=ncr.assigned_to_id)
        disposition.assigned_to_id = ncr.assigned_to_id
    elif ncr.assigned_to_id is None and disposition.assigned_to_id is not None:
        adopt_owner(ncr)


def adopt_owner(ncr) -> None:
    """An unowned NCR whose open decisions all have one assignee is theirs — a decision
    taken on its own (the disposition form) takes its NCR."""
    if ncr is None or ncr.assigned_to_id is not None or ncr.state != 'OPEN':
        return
    owners = set(QuarantineDisposition.unscoped  # tenant-safe: scoped by the NCR FK
                 .filter(ncr=ncr, archived=False, assigned_to__isnull=False)
                 .exclude(current_state='CLOSED').values_list('assigned_to_id', flat=True))
    if len(owners) == 1:
        NCR.unscoped.filter(pk=ncr.pk).update(assigned_to_id=owners.pop())  # tenant-safe: own pk

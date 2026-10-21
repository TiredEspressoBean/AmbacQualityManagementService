"""Has a sampled part passed its inspection *here*?

A part selected for sampling (`requires_sampling`, set when it arrives at a step) needs
QA until a PASS report is recorded for it at that step, during that visit. "Any PASS
report, ever" — what every reader used to check — counted a pass from an earlier step:
a part walked through the line with passes at Machining never showed as needing QA at
Nozzle Inspection, so the inspector's queue never listed it.

One rule, two shapes: `part_passed_qa_here` for one part, `with_qa_passed` to annotate a
Parts queryset (`_qa_passed`). `Parts.needs_qa` / `qa_completed`, the parts `needs_qa`
filter, the work order's QA progress and the inspector inbox all read it.
"""
from __future__ import annotations

import datetime

from django.db.models import Exists, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce

# A part with no open execution at its step (e.g. created at a step, not advanced into
# it) has no visit start: any PASS at the step counts.
_EPOCH = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)


def _visit_start(part):
    from Tracker.models import StepExecution
    ex = (StepExecution.unscoped  # tenant-safe: FK-correlated to a scoped part
          .filter(part=part, step_id=part.step_id, exited_at__isnull=True)
          .order_by('-visit_number').values_list('entered_at', flat=True).first())
    return ex or _EPOCH


# Results that complete a part's QA at a step: it was inspected and not failed. REPAIR
# ("Needs repair") is one — the unit was inspected, and routing takes it down a repair
# branch rather than holding it for an inspection it already had.
INSPECTED_OK = ('PASS', 'REPAIR')


def part_passed_qa_here(part) -> bool:
    """A PASS (or REPAIR) report for `part` at its current step, recorded during the
    current visit."""
    if part.step_id is None:
        return False
    return part.error_reports.filter(  # tenant-safe: reverse FK from a scoped part
        archived=False, status__in=INSPECTED_OK, step_id=part.step_id,
        created_at__gte=_visit_start(part),
    ).exists()


def with_qa_passed(qs):
    """`qs` (Parts) annotated with `_qa_passed`: the same rule as `part_passed_qa_here`."""
    from Tracker.models import QualityReports, StepExecution
    visit = (StepExecution.unscoped  # tenant-safe: correlated to the outer scoped part
             .filter(part=OuterRef('pk'), step=OuterRef('step'), exited_at__isnull=True)
             .order_by('-visit_number').values('entered_at')[:1])
    passed = QualityReports.unscoped.filter(  # tenant-safe: correlated to the outer scoped part
        part=OuterRef('pk'), step=OuterRef('step'), status__in=INSPECTED_OK, archived=False,
        created_at__gte=OuterRef('_qa_visit_start'))
    return (qs.annotate(_qa_visit_start=Coalesce(Subquery(visit), Value(_EPOCH)))
              .annotate(_qa_passed=Exists(passed)))


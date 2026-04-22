"""
Core aggregate services.

State-transition logic for the Core lifecycle: disassembly start/completion,
scrapping, and credit issuance.
"""
from __future__ import annotations

from django.utils import timezone

from Tracker.models import Core


def start_core_disassembly(core: Core, user) -> Core:
    """Transition a Core from RECEIVED to IN_DISASSEMBLY.

    Raises:
        ValueError: core is not in RECEIVED status.
    """
    if core.status != 'RECEIVED':
        raise ValueError(f"Cannot start disassembly - core is {core.status}")
    core.status = 'IN_DISASSEMBLY'
    core.disassembly_started_at = timezone.now()
    core.save()
    return core


def complete_core_disassembly(core: Core, user) -> Core:
    """Transition a Core from IN_DISASSEMBLY to DISASSEMBLED.

    Raises:
        ValueError: core is not in IN_DISASSEMBLY status.
    """
    if core.status != 'IN_DISASSEMBLY':
        raise ValueError(f"Cannot complete disassembly - core is {core.status}")
    core.status = 'DISASSEMBLED'
    core.disassembly_completed_at = timezone.now()
    core.disassembled_by = user
    core.save()
    return core


def scrap_core(core: Core, reason: str = '') -> Core:
    """Mark a Core as scrapped (not suitable for disassembly).

    Raises:
        ValueError: core is already scrapped.
    """
    if core.status == 'SCRAPPED':
        raise ValueError("Core is already scrapped")
    core.status = 'SCRAPPED'
    core.condition_grade = 'SCRAP'
    if reason:
        core.condition_notes = f"{core.condition_notes}\nScrapped: {reason}".strip()
    core.save()
    return core


def issue_core_credit(core: Core) -> Core:
    """Mark core credit as issued.

    Raises:
        ValueError: no credit value is set on the core.
    """
    if not core.core_credit_value:
        raise ValueError("No credit value set for this core")
    core.core_credit_issued = True
    core.core_credit_issued_at = timezone.now()
    core.save()
    return core

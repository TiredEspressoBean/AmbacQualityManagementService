"""Shared payload primitives."""
from __future__ import annotations

from typing import TypedDict


class AttachmentRef(TypedDict):
    """Payload-level reference to a stored artifact (e.g. GeneratedReport).

    The email channel adapter resolves the type+id pair to bytes at send time.
    """
    type: str   # 'generated_report' (v1); extend per shape (b) events as they ship
    id: int

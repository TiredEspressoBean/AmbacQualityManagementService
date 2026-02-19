"""
Integration module for external system synchronization.

ARCHITECTURE NOTE - Composition over Inheritance:
=================================================
Mixins have been deprecated in favor of composition (inline fields).
See hubspot.py for detailed notes and migration path.

This module now only exports concrete models:
- HubSpotSyncLog: Tracks sync operations for debugging

ExternalAPIOrderIdentifier moved to core.py to avoid circular imports.
"""

from .base import ExternalSyncMixin, ExternalPipelineMixin
from .hubspot import (
    HubSpotSyncLog,
    # Note: ExternalAPIOrderIdentifier moved to core.py
    # Note: Mixins deprecated - using composition instead
)

__all__ = [
    # Base mixins (kept for reference, but deprecated)
    'ExternalSyncMixin',
    'ExternalPipelineMixin',

    # HubSpot models
    'HubSpotSyncLog',
    # 'ExternalAPIOrderIdentifier' - moved to core.py
]

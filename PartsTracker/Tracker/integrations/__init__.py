"""
Integration services for external system synchronization.

This module provides a clean service-layer abstraction for integrations.
Each integration (HubSpot, ERP CSV, Salesforce, etc.) implements the
IntegrationService interface, allowing plug-and-play integration management.

Usage:
    from Tracker.integrations import registry

    # Get a specific integration
    hubspot = registry.get('hubspot')
    if hubspot and hubspot.is_enabled():
        hubspot.sync_orders()

    # Run sync across all enabled integrations
    for integration in registry.get_enabled():
        integration.sync_orders()

Architecture:
    - IntegrationService: Abstract base class defining the interface
    - IntegrationRegistry: Singleton registry for managing integrations
    - HubSpotService: HubSpot implementation
    - (Future) ERPCSVService: CSV-based ERP implementation
"""

from .base_service import IntegrationService, IntegrationConfig
from .registry import IntegrationRegistry, registry

__all__ = [
    'IntegrationService',
    'IntegrationConfig',
    'IntegrationRegistry',
    'registry',
]

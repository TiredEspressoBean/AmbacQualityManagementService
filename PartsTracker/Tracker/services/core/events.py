"""Core (cross-domain) notification event registrations.

Imported by TrackerConfig.ready() so registration runs at startup.
v1 has no core-domain events yet; module exists for future entries
(account.locked, role.privileged_changed, etc.).

Approval events will land here in Phase 6 alongside the per-instance
routing infrastructure they need (`recipient_strategy='from_payload'`).
"""

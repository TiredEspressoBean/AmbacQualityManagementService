"""
Registry for ScheduledContentProvider implementations.

Mirrors the lazy-import + lru_cache pattern from
`Tracker/reports/services/registry.py`. Adding a provider = appending one
dotted-path string to `SCHEDULED_CONTENT_PROVIDERS`. Imports happen on
first registry access; a buggy provider only breaks itself, not the app.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from importlib import import_module

from .base import ScheduledContentProvider

logger = logging.getLogger(__name__)


# Dotted paths to every ScheduledContentProvider subclass. Append entries
# at the end when adding a new provider; never reorder or remove without
# checking that no NotificationSchedule rows reference the removed name.
SCHEDULED_CONTENT_PROVIDERS: tuple[str, ...] = (
    "Tracker.services.core.notifications.scheduled_content.customer_active_orders.CustomerActiveOrdersProvider",
)


class UnknownProviderError(KeyError):
    """Raised by `get_provider` when a name is not in the registry."""


@lru_cache(maxsize=1)
def _build_registry() -> dict[str, ScheduledContentProvider]:
    registry: dict[str, ScheduledContentProvider] = {}
    for dotted_path in SCHEDULED_CONTENT_PROVIDERS:
        try:
            module_path, class_name = dotted_path.rsplit(".", 1)
            module = import_module(module_path)
            cls = getattr(module, class_name)
            instance = cls()
            registry[instance.name] = instance
        except Exception:
            logger.exception(
                "scheduled_content registry: failed to load %s; skipping",
                dotted_path,
            )
    return registry


def get_provider(name: str) -> ScheduledContentProvider:
    """Look up a provider by its registered `name`.

    Raises UnknownProviderError if not registered (or if the provider's
    module failed to import — check logs).
    """
    registry = _build_registry()
    if name not in registry:
        raise UnknownProviderError(name)
    return registry[name]


def get_all_providers() -> dict[str, ScheduledContentProvider]:
    """All loaded providers keyed by name. Cached per-process."""
    return dict(_build_registry())

"""
ScheduledContentProvider system — content renderers for NotificationSchedule.

Mirrors the lazy-import + lru_cache registry pattern from
`Tracker/reports/services/registry.py`. Providers register themselves by
adding a dotted path to `SCHEDULED_CONTENT_PROVIDERS`; concrete provider
classes are imported on first registry access and cached per-process.

Public API:
    get_provider(name)         → ScheduledContentProvider instance
    get_all_providers()        → dict[name, ScheduledContentProvider]
    UnknownProviderError       → raised by get_provider on miss
    ScheduledContentProvider   → abstract base for new providers
    RenderedContent            → frozen dataclass returned by build_content()
"""
from .base import RenderedContent, ScheduledContentProvider
from .registry import (
    UnknownProviderError,
    get_all_providers,
    get_provider,
)

__all__ = [
    "RenderedContent",
    "ScheduledContentProvider",
    "UnknownProviderError",
    "get_provider",
    "get_all_providers",
]

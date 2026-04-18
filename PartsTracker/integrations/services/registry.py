"""
Adapter registry.

Settings-based registration with import_string() — the standard Django pattern
(used by Django Storage, django-payments, Celery). Settings ARE the registry.
"""

from django.conf import settings
from django.utils.module_loading import import_string

from integrations.adapters.base import BaseAdapter

_adapter_cache = {}


def get_adapter(provider: str) -> BaseAdapter:
    """
    Get the adapter instance for a provider, considering deployment mode.
    Adapters are cached — same instance returned for multiple calls.
    """
    deployment_mode = getattr(settings, f'{provider.upper()}_MODE', 'cloud')
    cache_key = (provider, deployment_mode)

    if cache_key not in _adapter_cache:
        adapters_map = getattr(settings, 'INTEGRATION_ADAPTERS', {})
        adapter_path = adapters_map.get(cache_key)
        if not adapter_path:
            raise ValueError(f"No adapter registered for ({provider}, {deployment_mode})")
        adapter_class = import_string(adapter_path)
        _adapter_cache[cache_key] = adapter_class()

    return _adapter_cache[cache_key]


def get_all_adapters() -> list[BaseAdapter]:
    """Get all registered adapter instances. Useful for catalog/listing."""
    adapters_map = getattr(settings, 'INTEGRATION_ADAPTERS', {})
    seen = set()
    adapters = []
    for (provider, mode), path in adapters_map.items():
        if provider not in seen:
            adapters.append(get_adapter(provider))
            seen.add(provider)
    return adapters


# Map of capability names to the base class method/property they correspond to
CAPABILITY_METHOD_MAP = {
    'order_sync': 'sync_orders',
    'company_sync': 'sync_companies',
    'contact_sync': 'sync_contacts',
    'push_order_status': 'push_order_status',
    'webhooks': 'handle_webhook',
    'pipeline_stages': 'has_pipeline_stages',
}


def discover_capabilities(adapter: BaseAdapter) -> set[str]:
    """
    Discover which capabilities an adapter supports by checking
    which BaseAdapter methods it overrides.

    For regular methods: checks if the adapter's method is different from BaseAdapter's.
    For properties: checks if the value differs from the BaseAdapter default.
    """
    caps = set()
    for cap_name, method_name in CAPABILITY_METHOD_MAP.items():
        base_attr = getattr(BaseAdapter, method_name, None)
        adapter_attr = getattr(type(adapter), method_name, None)

        if adapter_attr is not None and adapter_attr is not base_attr:
            caps.add(cap_name)

    return caps


def clear_cache():
    """Clear cached adapter instances. Useful for testing."""
    _adapter_cache.clear()

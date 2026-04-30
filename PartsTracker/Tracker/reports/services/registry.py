"""
Adapter registry for report types.

Mirrors the pattern from `integrations/services/registry.py`:
- A flat list of dotted-path strings (REPORT_ADAPTERS)
- Lazy import + instantiate on first access
- Adapter instances are cached per-process

Adding a new report type = appending one line to REPORT_ADAPTERS.
Registry loading never fails — adapters import lazily so a buggy
adapter file only breaks that one report, not the whole application.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from importlib import import_module

from Tracker.reports.adapters.base import ReportAdapter

logger = logging.getLogger(__name__)


# Dotted paths to every ReportAdapter subclass. Append to the end when
# adding a new report type; never reorder or remove entries without
# removing the corresponding template + tests too.
REPORT_ADAPTERS: tuple[str, ...] = (
    "Tracker.reports.adapters.hello_world.HelloWorldAdapter",
    "Tracker.reports.adapters.ncr.NcrAdapter",
    "Tracker.reports.adapters.calibration_certificate.CalibrationCertificateAdapter",
    "Tracker.reports.adapters.calibration_due.CalibrationDueAdapter",
    "Tracker.reports.adapters.training_record.TrainingRecordAdapter",
    "Tracker.reports.adapters.capa_report.CapaReportAdapter",
    "Tracker.reports.adapters.bom_report.BOMReportAdapter",
    "Tracker.reports.adapters.deviation_request.DeviationRequestAdapter",
    "Tracker.reports.adapters.pick_list.PickListAdapter",
    "Tracker.reports.adapters.dispatch_list.DispatchListAdapter",
    "Tracker.reports.adapters.checking_aids.CheckingAidsAdapter",
    "Tracker.reports.adapters.part_id_label.PartIdLabelAdapter",
    "Tracker.reports.adapters.part_id_label_batch.PartIdLabelBatchAdapter",
    "Tracker.reports.adapters.spc.SpcAdapter",
)


class UnknownReportError(KeyError):
    """Raised when a report_type is not in the registry."""


@lru_cache(maxsize=1)
def _build_registry() -> dict[str, ReportAdapter]:
    """
    Import every adapter in REPORT_ADAPTERS and return a {name: instance} map.

    Cached — called once per process. If you add a new adapter at
    runtime (tests), call `_build_registry.cache_clear()` first.
    """
    registry: dict[str, ReportAdapter] = {}

    for dotted_path in REPORT_ADAPTERS:
        module_path, class_name = dotted_path.rsplit(".", 1)
        try:
            module = import_module(module_path)
            adapter_cls = getattr(module, class_name)
        except (ImportError, AttributeError) as exc:
            logger.error(
                "Failed to load report adapter %s: %s", dotted_path, exc
            )
            continue

        if not issubclass(adapter_cls, ReportAdapter):
            logger.error(
                "Report adapter %s is not a ReportAdapter subclass",
                dotted_path,
            )
            continue

        instance = adapter_cls()
        if instance.name in registry:
            logger.error(
                "Duplicate report adapter name %r (from %s); "
                "skipping second registration",
                instance.name, dotted_path,
            )
            continue

        registry[instance.name] = instance

    return registry


def get_adapter(name: str) -> ReportAdapter:
    """
    Return the adapter registered under `name`.
    Raises UnknownReportError if not found.
    """
    registry = _build_registry()
    try:
        return registry[name]
    except KeyError as exc:
        available = sorted(registry.keys())
        raise UnknownReportError(
            f"Unknown report type {name!r}. Available: {available}"
        ) from exc


def get_all_adapters() -> list[ReportAdapter]:
    """Return every registered adapter instance."""
    return list(_build_registry().values())


def reset_registry_cache() -> None:
    """
    Clear the internal registry cache. Used by tests that register
    adapters on the fly. Not needed in normal application code.
    """
    _build_registry.cache_clear()

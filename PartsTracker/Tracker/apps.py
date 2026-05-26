import logging

from django.apps import AppConfig
from django.db.backends.signals import connection_created
from django.db.models.signals import post_migrate

logger = logging.getLogger(__name__)


# Module-level flag so the DEBUG template auto-loader fires at most once per
# process. connection_created fires on every new connection (e.g., each
# Celery worker pre-fork), and we don't want to repeatedly upsert templates.
_DEBUG_TEMPLATES_LOADED = False


def _auto_load_templates_in_debug(sender, connection, **kwargs):
    """Idempotent template upsert wired to `connection_created`. DEBUG-only.

    Fires on the first real DB connection rather than at `apps.ready()` so
    we don't trip Django's "DB access during app init" warning. Process-level
    guard via `_DEBUG_TEMPLATES_LOADED` ensures we don't reseed on every
    subsequent connection.

    Wrapped in try/except — on a fresh clone where migrations haven't run,
    the NotificationTemplate table doesn't exist yet; we log and move on.
    """
    global _DEBUG_TEMPLATES_LOADED
    if _DEBUG_TEMPLATES_LOADED:
        return

    # Skip during management commands that don't need it (`migrate` already
    # triggers post_migrate; `test` uses its own setup; `makemigrations`
    # runs before any DB schema exists).
    import sys
    skip_subcommands = {
        'makemigrations', 'migrate', 'test', 'collectstatic',
        'showmigrations', 'sqlmigrate', 'check', 'shell',
    }
    if any(arg in skip_subcommands for arg in sys.argv):
        _DEBUG_TEMPLATES_LOADED = True   # don't keep retrying
        return

    try:
        from Tracker.services.core.notifications.system_templates import (
            setup_system_templates,
        )
        counts = setup_system_templates()
        if counts['created'] or counts['updated']:
            logger.info(
                "DEBUG notification template auto-load: "
                f"{counts['created']} created, {counts['updated']} updated"
            )
    except Exception as exc:  # pragma: no cover — boot-time defensive
        logger.debug(
            "DEBUG template auto-load skipped (likely DB not yet "
            f"migrated): {exc}"
        )
    finally:
        _DEBUG_TEMPLATES_LOADED = True


def setup_defaults(sender, **kwargs):
    """
    Post-migrate signal handler to set up all defaults.

    This runs after all migrations complete, ensuring:
    1. Groups and permissions are configured
    2. Document types are seeded
    3. Approval templates are seeded

    These can also be managed manually via:
    - python manage.py setup_permissions
    - python manage.py setup_document_types
    - python manage.py setup_approval_templates
    - python manage.py setup_defaults (runs all)
    """
    # Only run for Tracker app to avoid duplicate runs
    if sender.name != 'Tracker':
        return

    # 1. Set up permissions (groups + their permissions)
    try:
        from Tracker.services.permission_service import apply_permissions
        results = apply_permissions(user=None, source='post_migrate')

        if results['changes']:
            logger.info(
                f"Permission sync: {results['permissions_added']} added, "
                f"{results['permissions_removed']} removed"
            )
        if results['errors']:
            for error in results['errors']:
                logger.warning(f"Permission sync error: {error}")

    except Exception as e:
        logger.warning(f"Permission setup skipped: {e}")

    # 2. Load system notification templates (tenant=NULL rows). Idempotent.
    try:
        from Tracker.services.core.notifications.system_templates import (
            setup_system_templates,
        )
        counts = setup_system_templates()
        if counts['created'] or counts['updated']:
            logger.info(
                f"Notification templates: {counts['created']} created, "
                f"{counts['updated']} updated"
            )
    except Exception as e:
        logger.warning(f"Notification template setup skipped: {e}")

    # Note: Document types and approval templates are now tenant-specific only.
    # They are seeded via the Tenant post_save signal in signals.py


class TrackerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Tracker'
    verbose_name = 'Inventory Management'

    def ready(self):
        import Tracker.signals  # Import signals when app starts
        import Tracker.checks  # Register system checks

        # Notification event registry — importing populates EVENT_REGISTRY.
        import Tracker.services.core.events  # noqa: F401
        import Tracker.services.mes.events  # noqa: F401
        import Tracker.services.qms.events  # noqa: F401

        # Notification dispatcher receiver wires to the emit signal.
        import Tracker.services.core.notifications.dispatcher  # noqa: F401

        # Notification signal handlers — cache invalidation + tenant seeding.
        import Tracker.services.core.notifications.signals  # noqa: F401

        # Escalation ack predicates — each domain registers ack/cancel
        # predicates for events that support escalation chains. Imported
        # at startup so the registry is populated before any rule fires.
        import Tracker.services.qms.escalation_acks  # noqa: F401

        # Connect post_migrate signal for all default data setup
        post_migrate.connect(setup_defaults, sender=self)

        # In DEBUG mode, auto-seed notification templates after the first DB
        # connection is established. Triggered via `connection_created` rather
        # than directly in `ready()` so we avoid Django's "DB access during
        # app init" warning. The module-level flag ensures we run once per
        # process, not per connection.
        from django.conf import settings as _settings
        if getattr(_settings, 'DEBUG', False):
            connection_created.connect(_auto_load_templates_in_debug)

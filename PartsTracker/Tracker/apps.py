import logging

from django.apps import AppConfig
from django.db.models.signals import post_migrate

logger = logging.getLogger(__name__)


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

    # Note: Document types and approval templates are now tenant-specific only.
    # They are seeded via the Tenant post_save signal in signals.py


class TrackerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Tracker'
    verbose_name = 'Inventory Management'

    def ready(self):
        import Tracker.signals  # Import signals when app starts

        # Connect post_migrate signal for all default data setup
        post_migrate.connect(setup_defaults, sender=self)

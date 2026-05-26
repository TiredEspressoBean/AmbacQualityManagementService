"""Management command for loading system notification templates.

System templates (tenant=NULL rows in NotificationTemplate) are also
auto-loaded via post_migrate signal — this command provides explicit
control for development and CI.

Usage:
    python manage.py setup_notification_templates
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Load system notification templates (idempotent)."

    def handle(self, *args, **options):
        from Tracker.services.core.notifications.system_templates import (
            setup_system_templates,
        )
        counts = setup_system_templates()
        self.stdout.write(self.style.SUCCESS(
            f"System notification templates: "
            f"{counts['created']} created, {counts['updated']} updated."
        ))

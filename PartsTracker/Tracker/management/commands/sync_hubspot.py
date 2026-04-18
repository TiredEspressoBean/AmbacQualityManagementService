"""
Manually trigger a HubSpot sync for a tenant's enabled HubSpot integration.

Replaces the old broken command (pre-integrations-app refactor). Uses the
current integrations architecture:
  Tenant → IntegrationConfig (provider='hubspot') → sync_hubspot_deals_task

Usage:
    # Async (default) — enqueue a Celery task, return immediately
    python manage.py sync_hubspot --tenant ambac-international

    # Sync (blocking) — run the sync in-process, print results
    python manage.py sync_hubspot --tenant ambac-international --sync

    # Supply an explicit integration ID instead of resolving via tenant
    python manage.py sync_hubspot --integration-id <uuid>

Use cases:
  - Bootstrapping: first-time pull after configuring an integration
  - Backfill: re-sync after a schema change or data import
  - Debugging: check that a tenant's credentials + pipeline config work
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Trigger a HubSpot deals sync for a tenant."

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant",
            type=str,
            help="Tenant slug. Resolves the tenant's enabled HubSpot "
                 "IntegrationConfig. Mutually exclusive with --integration-id.",
        )
        parser.add_argument(
            "--integration-id",
            type=str,
            help="Explicit IntegrationConfig UUID. Bypasses tenant lookup.",
        )
        parser.add_argument(
            "--sync",
            action="store_true",
            help="Run synchronously (blocking) instead of enqueuing a task. "
                 "Useful for debugging — errors surface in the terminal.",
        )

    def handle(self, *args, **options):
        integration = self._resolve_integration(options)

        self.stdout.write(
            f"Tenant:      {integration.tenant.name} ({integration.tenant.slug})\n"
            f"Integration: {integration.id} ({integration.display_name or integration.provider})\n"
            f"Enabled:     {integration.is_enabled}\n"
            f"Status:      {integration.sync_status}\n"
        )

        if not integration.is_enabled:
            raise CommandError(
                f"Integration {integration.id} is disabled. "
                f"Enable it via /api/integrations/{integration.id}/ before syncing."
            )

        if options["sync"]:
            self._run_sync(integration)
        else:
            self._queue_async(integration)

    # ------------------------------------------------------------------

    def _resolve_integration(self, options):
        from Tracker.models import Tenant
        from integrations.models import IntegrationConfig

        integration_id = options.get("integration_id")
        tenant_slug = options.get("tenant")

        if bool(integration_id) == bool(tenant_slug):
            raise CommandError(
                "Specify exactly one of --tenant or --integration-id."
            )

        if integration_id:
            try:
                # tenant-safe: CLI admin context; explicit integration ID
                return IntegrationConfig.objects.select_related("tenant").get(
                    id=integration_id, provider="hubspot"
                )
            except IntegrationConfig.DoesNotExist:
                raise CommandError(
                    f"IntegrationConfig {integration_id} not found "
                    f"(or not a HubSpot integration)."
                )

        # Resolve via tenant
        try:
            # tenant-safe: CLI admin context
            tenant = Tenant.objects.get(slug=tenant_slug)
        except Tenant.DoesNotExist:
            raise CommandError(f"Tenant '{tenant_slug}' not found.")

        # tenant-safe: filter explicitly by the resolved tenant
        integration = IntegrationConfig.objects.filter(
            tenant=tenant, provider="hubspot"
        ).first()
        if integration is None:
            raise CommandError(
                f"No HubSpot IntegrationConfig for tenant "
                f"'{tenant.slug}'. Create one via /api/integrations/ first."
            )
        return integration

    def _queue_async(self, integration):
        from integrations.tasks import sync_hubspot_deals_task

        self.stdout.write("Enqueuing async sync task...")
        task = sync_hubspot_deals_task.delay(str(integration.id))
        self.stdout.write(self.style.SUCCESS(
            f"  Task ID: {task.id}\n"
            f"  Watch Celery logs or the integration's sync_logs endpoint "
            f"for progress."
        ))

    def _run_sync(self, integration):
        from integrations.adapters.hubspot.sync import sync_all_deals

        self.stdout.write("Running sync synchronously (blocking)...")
        try:
            result = sync_all_deals(integration)
        except Exception as exc:
            raise CommandError(f"Sync failed: {exc}") from exc

        status = result.get("status", "unknown")

        if status == "success":
            errors = result.get("errors") or []
            self.stdout.write(self.style.SUCCESS(
                f"Sync completed.\n"
                f"  Processed: {result.get('processed', 0)}\n"
                f"  Created:   {result.get('created', 0)}\n"
                f"  Updated:   {result.get('updated', 0)}\n"
                f"  Errors:    {len(errors)}"
            ))
            # Surface the first few errors so callers can see what broke
            for err in errors[:5]:
                self.stdout.write(self.style.WARNING(f"    • {err}"))
            if len(errors) > 5:
                self.stdout.write(f"    ... and {len(errors) - 5} more")

        elif status == "skipped":
            self.stdout.write(self.style.WARNING(
                f"Sync skipped: {result.get('reason', 'unknown reason')}"
            ))

        elif status == "error":
            self.stdout.write(self.style.ERROR(
                f"Sync failed: {result.get('message', 'unknown error')}"
            ))
            # Non-zero exit so CI / scripts catch it
            raise CommandError("Sync failed")

        else:
            self.stdout.write(self.style.WARNING(
                f"Unexpected status: {status}\n{result}"
            ))

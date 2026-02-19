"""
Management command to set up default approval templates.

Usage:
    python manage.py setup_approval_templates              # Create missing templates
    python manage.py setup_approval_templates --update     # Update existing templates
    python manage.py setup_approval_templates --dry-run    # Preview changes
    python manage.py setup_approval_templates --list       # List current templates

Note: Approval templates are also automatically seeded via post_migrate signal.
      This command provides explicit control and visibility.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from Tracker.models import ApprovalTemplate, TenantGroup, Tenant
from Tracker.services.defaults_service import APPROVAL_TEMPLATES


class Command(BaseCommand):
    help = "Set up default approval templates for QMS workflows"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without applying them",
        )
        parser.add_argument(
            "--update",
            action="store_true",
            help="Update existing templates with new values (by approval_type)",
        )
        parser.add_argument(
            "--list",
            action="store_true",
            help="List current approval templates in the database",
        )
        parser.add_argument(
            "--type",
            type=str,
            help="Only process a specific approval type (e.g., DOCUMENT_RELEASE)",
        )
        parser.add_argument(
            "--tenant",
            type=str,
            help="Tenant slug (required for creating templates with group assignments)",
        )

    def handle(self, *args, **options):
        if options["list"]:
            self._list_templates()
            return

        dry_run = options["dry_run"]
        update = options["update"]
        filter_type = options.get("type")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes will be applied\n"))

        templates_to_process = APPROVAL_TEMPLATES
        if filter_type:
            templates_to_process = [t for t in APPROVAL_TEMPLATES if t["approval_type"] == filter_type]
            if not templates_to_process:
                self.stdout.write(self.style.ERROR(f"Unknown approval type: {filter_type}"))
                self.stdout.write("Valid types: DOCUMENT_RELEASE, CAPA_CRITICAL, CAPA_MAJOR, ECO, TRAINING_CERT, PROCESS_APPROVAL")
                return

        created = 0
        updated = 0
        skipped = 0
        errors = []

        # Get tenant if specified
        tenant = None
        tenant_slug = options.get("tenant")
        if tenant_slug:
            try:
                tenant = Tenant.objects.get(slug=tenant_slug)
            except Tenant.DoesNotExist:
                raise CommandError(f"Tenant '{tenant_slug}' not found")

        with transaction.atomic():
            # Ensure required groups exist (TenantGroups if tenant specified)
            if tenant:
                existing_groups = {g.name: g for g in TenantGroup.objects.filter(tenant=tenant)}
            else:
                existing_groups = {}

            required_groups = set()
            for t in templates_to_process:
                required_groups.update(t.get("default_groups_names", []))

            missing_groups = required_groups - set(existing_groups.keys())
            if missing_groups and tenant:
                self.stdout.write(
                    self.style.WARNING(f"Note: TenantGroups not yet created: {', '.join(missing_groups)}")
                )
                self.stdout.write("  Run 'python manage.py setup_groups' first to create groups\n")
            elif missing_groups and not tenant:
                self.stdout.write(
                    self.style.WARNING(f"Note: Use --tenant to assign groups to templates")
                )

            for template_data in templates_to_process:
                try:
                    # Extract group names before processing
                    group_names = template_data.pop("default_groups_names", [])
                    description = template_data.pop("description", "")

                    existing = ApprovalTemplate.objects.filter(
                        approval_type=template_data["approval_type"]
                    ).first()

                    if existing:
                        if update:
                            if dry_run:
                                self.stdout.write(
                                    f"  Would update: {template_data['template_name']}"
                                )
                            else:
                                for key, value in template_data.items():
                                    setattr(existing, key, value)
                                existing.save()

                                # Update groups (TenantGroups if tenant specified)
                                if tenant and group_names:
                                    groups = TenantGroup.objects.filter(tenant=tenant, name__in=group_names)
                                    existing.default_groups.set(groups)

                                self.stdout.write(
                                    self.style.SUCCESS(f"  Updated: {template_data['template_name']}")
                                )
                            updated += 1
                        else:
                            self.stdout.write(f"  Skipped (exists): {template_data['template_name']}")
                            skipped += 1
                    else:
                        if dry_run:
                            self.stdout.write(f"  Would create: {template_data['template_name']}")
                        else:
                            # Add tenant to template if specified
                            if tenant:
                                template_data['tenant'] = tenant
                            template = ApprovalTemplate.objects.create(**template_data)

                            # Set groups (TenantGroups if tenant specified)
                            if tenant and group_names:
                                groups = TenantGroup.objects.filter(tenant=tenant, name__in=group_names)
                                template.default_groups.set(groups)

                            self.stdout.write(
                                self.style.SUCCESS(f"  Created: {template_data['template_name']}")
                            )
                        created += 1

                    # Restore for next iteration if needed
                    template_data["default_groups_names"] = group_names
                    template_data["description"] = description

                except Exception as e:
                    errors.append(f"{template_data.get('template_name', 'unknown')}: {str(e)}")
                    self.stdout.write(
                        self.style.ERROR(f"  Error: {template_data.get('template_name', 'unknown')} - {str(e)}")
                    )
                    # Restore popped values
                    template_data["default_groups_names"] = group_names
                    template_data["description"] = description

            if dry_run:
                transaction.set_rollback(True)

        # Summary
        self.stdout.write("")
        self.stdout.write("=" * 50)
        self.stdout.write(f"Created: {created}")
        self.stdout.write(f"Updated: {updated}")
        self.stdout.write(f"Skipped: {skipped}")
        if errors:
            self.stdout.write(self.style.ERROR(f"Errors: {len(errors)}"))

        if dry_run:
            self.stdout.write(self.style.WARNING("\nRun without --dry-run to apply changes"))
        else:
            self.stdout.write(self.style.SUCCESS("\nApproval templates setup complete"))

    def _list_templates(self):
        """List current approval templates in the database."""
        templates = ApprovalTemplate.objects.all().order_by("approval_type")

        if not templates.exists():
            self.stdout.write(self.style.WARNING("No approval templates found in database"))
            self.stdout.write("Run: python manage.py setup_approval_templates")
            return

        self.stdout.write(f"\nApproval Templates ({templates.count()}):\n")
        self.stdout.write(f"{'Type':<20} {'Name':<35} {'Flow':<15} {'Due Days':<10}")
        self.stdout.write("-" * 80)

        for t in templates:
            self.stdout.write(
                f"{t.approval_type:<20} {t.template_name:<35} {t.approval_flow_type:<15} {t.default_due_days:<10}"
            )

        self.stdout.write("")

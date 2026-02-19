"""
Management command to set up default document types.

Usage:
    python manage.py setup_document_types              # Create missing types
    python manage.py setup_document_types --update     # Update existing types
    python manage.py setup_document_types --dry-run    # Preview changes
    python manage.py setup_document_types --list       # List current types

Note: Document types are also automatically seeded via post_migrate signal.
      This command provides explicit control and visibility.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from Tracker.models import DocumentType
from Tracker.services.defaults_service import DOCUMENT_TYPES


class Command(BaseCommand):
    help = "Set up default document types for QMS"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without applying them",
        )
        parser.add_argument(
            "--update",
            action="store_true",
            help="Update existing document types with new values (by code)",
        )
        parser.add_argument(
            "--list",
            action="store_true",
            help="List current document types in the database",
        )
        parser.add_argument(
            "--code",
            type=str,
            help="Only process a specific document type code",
        )

    def handle(self, *args, **options):
        if options["list"]:
            self._list_types()
            return

        dry_run = options["dry_run"]
        update = options["update"]
        filter_code = options.get("code")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes will be applied\n"))

        types_to_process = DOCUMENT_TYPES
        if filter_code:
            types_to_process = [dt for dt in DOCUMENT_TYPES if dt["code"] == filter_code]
            if not types_to_process:
                self.stdout.write(self.style.ERROR(f"Unknown document type code: {filter_code}"))
                return

        created = 0
        updated = 0
        skipped = 0
        errors = []

        with transaction.atomic():
            for dt in types_to_process:
                try:
                    existing = DocumentType.objects.filter(code=dt["code"]).first()

                    if existing:
                        if update:
                            if dry_run:
                                self.stdout.write(f"  Would update: {dt['code']} - {dt['name']}")
                            else:
                                for key, value in dt.items():
                                    setattr(existing, key, value)
                                existing.save()
                                self.stdout.write(self.style.SUCCESS(f"  Updated: {dt['code']} - {dt['name']}"))
                            updated += 1
                        else:
                            self.stdout.write(f"  Skipped (exists): {dt['code']} - {dt['name']}")
                            skipped += 1
                    else:
                        if dry_run:
                            self.stdout.write(f"  Would create: {dt['code']} - {dt['name']}")
                        else:
                            DocumentType.objects.create(**dt)
                            self.stdout.write(self.style.SUCCESS(f"  Created: {dt['code']} - {dt['name']}"))
                        created += 1

                except Exception as e:
                    errors.append(f"{dt['code']}: {str(e)}")
                    self.stdout.write(self.style.ERROR(f"  Error: {dt['code']} - {str(e)}"))

            if dry_run:
                # Rollback in dry-run mode
                transaction.set_rollback(True)

        # Summary
        self.stdout.write("")
        self.stdout.write("=" * 50)
        action = "Would be" if dry_run else "Were"
        self.stdout.write(f"Created: {created}")
        self.stdout.write(f"Updated: {updated}")
        self.stdout.write(f"Skipped: {skipped}")
        if errors:
            self.stdout.write(self.style.ERROR(f"Errors: {len(errors)}"))

        if dry_run:
            self.stdout.write(self.style.WARNING("\nRun without --dry-run to apply changes"))
        else:
            self.stdout.write(self.style.SUCCESS("\nDocument types setup complete"))

    def _list_types(self):
        """List current document types in the database."""
        types = DocumentType.objects.all().order_by("code")

        if not types.exists():
            self.stdout.write(self.style.WARNING("No document types found in database"))
            self.stdout.write("Run: python manage.py setup_document_types")
            return

        self.stdout.write(f"\nDocument Types ({types.count()}):\n")
        self.stdout.write(f"{'Code':<8} {'Name':<35} {'Approval':<10}")
        self.stdout.write("-" * 55)

        for dt in types:
            approval = "Yes" if dt.requires_approval else "No"
            self.stdout.write(f"{dt.code:<8} {dt.name:<35} {approval:<10}")

        self.stdout.write("")

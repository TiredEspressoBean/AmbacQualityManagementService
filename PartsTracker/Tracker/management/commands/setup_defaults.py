"""
Master command to set up all default data for a new instance.

This orchestrates all individual setup commands with options to skip specific setups.

Usage:
    python manage.py setup_defaults                           # Run all setups
    python manage.py setup_defaults --dry-run                 # Preview all changes
    python manage.py setup_defaults --skip-permissions        # Skip permission setup
    python manage.py setup_defaults --skip-document-types     # Skip document types
    python manage.py setup_defaults --skip-approval-templates # Skip approval templates
    python manage.py setup_defaults --only=permissions        # Run only permissions
    python manage.py setup_defaults --list                    # List available setups
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand
from io import StringIO


# Available setup commands in execution order
SETUP_COMMANDS = [
    {
        "name": "permissions",
        "command": "setup_permissions",
        "description": "User groups and their permissions (Admin, Manager, Quality, Operator, Customer)",
        "skip_flag": "skip_permissions",
    },
    {
        "name": "document-types",
        "command": "setup_document_types",
        "description": "Document type classifications (SOP, WI, MTR, COC, etc.)",
        "skip_flag": "skip_document_types",
    },
    {
        "name": "approval-templates",
        "command": "setup_approval_templates",
        "description": "Approval workflow templates (Document Release, CAPA, ECO, etc.)",
        "skip_flag": "skip_approval_templates",
    },
]


class Command(BaseCommand):
    help = "Set up all default data for a new QMS instance"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without applying them",
        )
        parser.add_argument(
            "--update",
            action="store_true",
            help="Update existing records with new values",
        )
        parser.add_argument(
            "--list",
            action="store_true",
            help="List available setup commands",
        )
        parser.add_argument(
            "--only",
            type=str,
            help="Run only a specific setup (e.g., --only=permissions)",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed output from each command",
        )

        # Skip flags for each setup
        for setup in SETUP_COMMANDS:
            parser.add_argument(
                f"--{setup['skip_flag'].replace('_', '-')}",
                action="store_true",
                dest=setup["skip_flag"],
                help=f"Skip {setup['description']}",
            )

    def handle(self, *args, **options):
        if options["list"]:
            self._list_setups()
            return

        dry_run = options["dry_run"]
        update = options["update"]
        verbose = options["verbose"]
        only = options.get("only")

        if dry_run:
            self.stdout.write(self.style.WARNING("=" * 60))
            self.stdout.write(self.style.WARNING("DRY RUN - No changes will be applied"))
            self.stdout.write(self.style.WARNING("=" * 60))
            self.stdout.write("")

        self.stdout.write(self.style.HTTP_INFO("Setting up QMS defaults...\n"))

        results = {
            "success": [],
            "skipped": [],
            "failed": [],
        }

        for setup in SETUP_COMMANDS:
            # Check if we should skip this setup
            if only and setup["name"] != only:
                continue

            if options.get(setup["skip_flag"], False):
                self.stdout.write(f"  Skipping: {setup['description']}")
                results["skipped"].append(setup["name"])
                continue

            self.stdout.write(self.style.HTTP_INFO(f"\n{'=' * 60}"))
            self.stdout.write(self.style.HTTP_INFO(f"Running: {setup['command']}"))
            self.stdout.write(f"  {setup['description']}")
            self.stdout.write(self.style.HTTP_INFO("=" * 60))

            try:
                # Build command arguments
                cmd_args = []
                if dry_run:
                    cmd_args.append("--dry-run")
                if update:
                    cmd_args.append("--update")

                # Capture output
                if verbose:
                    call_command(setup["command"], *cmd_args, stdout=self.stdout, stderr=self.stderr)
                else:
                    output = StringIO()
                    call_command(setup["command"], *cmd_args, stdout=output, stderr=output)
                    # Show summary line only
                    output_text = output.getvalue()
                    if "complete" in output_text.lower() or "success" in output_text.lower():
                        self.stdout.write(self.style.SUCCESS(f"  Completed: {setup['name']}"))
                    else:
                        self.stdout.write(f"  Output:\n{output_text}")

                results["success"].append(setup["name"])

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  FAILED: {setup['name']} - {str(e)}"))
                results["failed"].append({"name": setup["name"], "error": str(e)})

        # Final summary
        self._print_summary(results, dry_run)

    def _list_setups(self):
        """List available setup commands."""
        self.stdout.write("\nAvailable Setup Commands:\n")
        self.stdout.write("-" * 70)

        for setup in SETUP_COMMANDS:
            self.stdout.write(f"\n  {self.style.HTTP_INFO(setup['name'])}")
            self.stdout.write(f"    Command: python manage.py {setup['command']}")
            self.stdout.write(f"    Skip: --{setup['skip_flag'].replace('_', '-')}")
            self.stdout.write(f"    {setup['description']}")

        self.stdout.write("\n" + "-" * 70)
        self.stdout.write("\nExamples:")
        self.stdout.write("  python manage.py setup_defaults                    # Run all")
        self.stdout.write("  python manage.py setup_defaults --dry-run          # Preview")
        self.stdout.write("  python manage.py setup_defaults --skip-permissions # Skip groups")
        self.stdout.write("  python manage.py setup_defaults --only=document-types")
        self.stdout.write("")

    def _print_summary(self, results, dry_run):
        """Print final summary."""
        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO("=" * 60))
        self.stdout.write(self.style.HTTP_INFO("SUMMARY"))
        self.stdout.write(self.style.HTTP_INFO("=" * 60))

        action_word = "would be" if dry_run else "were"

        if results["success"]:
            self.stdout.write(
                self.style.SUCCESS(f"\nSuccessful ({len(results['success'])}): {', '.join(results['success'])}")
            )

        if results["skipped"]:
            self.stdout.write(
                self.style.WARNING(f"\nSkipped ({len(results['skipped'])}): {', '.join(results['skipped'])}")
            )

        if results["failed"]:
            self.stdout.write(self.style.ERROR(f"\nFailed ({len(results['failed'])}):"))
            for failure in results["failed"]:
                self.stdout.write(self.style.ERROR(f"  - {failure['name']}: {failure['error']}"))

        self.stdout.write("")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN complete. Run without --dry-run to apply changes."))
        elif not results["failed"]:
            self.stdout.write(self.style.SUCCESS("All defaults setup complete!"))
        else:
            self.stdout.write(self.style.ERROR("Setup completed with errors. See above for details."))

"""
`python manage.py export_context <report_name>` — dump a report's
build_context() output as JSON for template development.

Used to build fixture files or to iterate on a Typst template with real
data via typst.app / Tinymist live preview.

Usage:
    # List available reports
    python manage.py export_context

    # Dump context for a report
    python manage.py export_context hello_world --params='{"name":"Dev","number":1}'
    python manage.py export_context hello_world > fixture.json
    python manage.py export_context cert_of_conformance --params='{"id":42}' --pretty
"""
from __future__ import annotations

import json
import sys

from django.core.management.base import BaseCommand, CommandError

from Tracker.reports.services.pdf_generator import (
    PdfGenerator,
    ReportParamError,
)
from Tracker.reports.services.registry import (
    UnknownReportError,
    get_adapter,
    get_all_adapters,
)


class Command(BaseCommand):
    help = "Dump a report adapter's build_context() output as JSON."

    def add_arguments(self, parser):
        parser.add_argument(
            "report_name",
            nargs="?",
            help="Registry key of the report (e.g. 'hello_world'). "
                 "Omit to list available reports.",
        )
        parser.add_argument(
            "--params",
            default="{}",
            help='JSON-encoded params dict (e.g. \'{"id":42}\'). '
                 "Defaults to an empty object.",
        )
        parser.add_argument(
            "--pretty",
            action="store_true",
            help="Pretty-print the JSON output (2-space indent).",
        )
        parser.add_argument(
            "--user-id",
            type=int,
            help="User ID for tenant scoping. Defaults to the first "
                 "superuser/staff user found.",
        )

    def handle(self, *args, **options):
        report_name = options.get("report_name")

        if not report_name:
            self._list_adapters()
            return

        try:
            adapter = get_adapter(report_name)
        except UnknownReportError as exc:
            raise CommandError(str(exc)) from exc

        try:
            params = json.loads(options["params"])
        except json.JSONDecodeError as exc:
            raise CommandError(f"--params must be valid JSON: {exc}") from exc

        if not isinstance(params, dict):
            raise CommandError(
                f"--params must be a JSON object, got {type(params).__name__}"
            )

        user = self._resolve_user(options.get("user_id"))
        tenant = getattr(user, "tenant", None) if user else None

        try:
            gen = PdfGenerator()
            validated = gen._validate_params(adapter, params, user)
            context = adapter.build_context(validated, user, tenant)
        except ReportParamError as exc:
            raise CommandError(f"Invalid params: {exc.errors}") from exc

        indent = 2 if options.get("pretty") else None
        json.dump(
            context.model_dump(mode="json"),
            sys.stdout,
            indent=indent,
            default=str,
        )
        sys.stdout.write("\n")

    def _list_adapters(self):
        self.stdout.write("Registered report adapters:\n")
        adapters = sorted(get_all_adapters(), key=lambda x: x.name)
        if not adapters:
            self.stdout.write("  (none)\n")
            return
        for a in adapters:
            self.stdout.write(f"  {a.name:32s} {a.title}\n")

    def _resolve_user(self, user_id):
        from Tracker.models import User
        if user_id:
            try:
                # tenant-safe: CLI use, admin context by design
                return User.objects.get(id=user_id)
            except User.DoesNotExist:
                raise CommandError(f"User {user_id} not found")
        # Default: first superuser or staff
        # tenant-safe: CLI use, admin context by design
        user = (
            User.objects.filter(is_superuser=True).first()
            or User.objects.filter(is_staff=True).first()
        )
        if user is None:
            self.stderr.write(
                "Warning: no superuser/staff user found. Running without "
                "user context; adapters that require request.user will fail.\n"
            )
        return user

"""
Management command to generate PDF reports for testing.

Usage:
    python manage.py generate_pdf spc                          # SPC with demo data
    python manage.py generate_pdf spc --process 1 --step 101   # Specific selection
    python manage.py generate_pdf --list                       # Show report types
    python manage.py generate_pdf --list-data                  # Show real DB data available
"""

import json
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from Tracker.services.pdf_generator import PdfGenerator

# Output directory for generated PDFs
REPORTS_DIR = Path(settings.BASE_DIR) / "generated_reports"

# Mock data options in SpcPrintPage (until wired to real API)
SPC_MOCK_DATA = {
    "processes": [
        {"id": 1, "name": "CNC Machining", "steps": [101, 102, 103, 104]},
        {"id": 2, "name": "Grinding", "steps": [201, 202, 203]},
        {"id": 3, "name": "Heat Treatment", "steps": [301, 302]},
        {"id": 4, "name": "Assembly", "steps": [401, 402, 403]},
        {"id": 5, "name": "Surface Treatment", "steps": [501, 502]},
    ],
    "steps": {
        101: {"name": "Rough Turning", "measurements": [1001, 1002, 1003]},
        102: {"name": "Finish Turning", "measurements": [1004, 1005, 1006]},
        103: {"name": "Boring", "measurements": [1007, 1008, 1009, 1010]},
        104: {"name": "Threading", "measurements": [1011, 1012, 1013]},
        201: {"name": "Centerless Grinding", "measurements": [2001, 2002, 2003]},
        202: {"name": "Surface Grinding", "measurements": [2004, 2005, 2006, 2007]},
        203: {"name": "Internal Grinding", "measurements": [2008, 2009, 2010]},
        301: {"name": "Hardening", "measurements": [3001, 3002, 3003]},
        302: {"name": "Tempering", "measurements": [3004, 3005]},
        401: {"name": "Press Fit", "measurements": [4001, 4002, 4003]},
        402: {"name": "Torque Assembly", "measurements": [4004, 4005, 4006]},
        403: {"name": "Final Inspection", "measurements": [4007, 4008, 4009]},
        501: {"name": "Anodizing", "measurements": [5001, 5002, 5003]},
        502: {"name": "Plating", "measurements": [5004, 5005, 5006]},
    },
}


class Command(BaseCommand):
    help = "Generate a PDF report for testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "report_type",
            nargs="?",
            type=str,
            help="Type of report to generate (spc, capa, quality_report)",
        )
        parser.add_argument(
            "--params",
            type=str,
            default="{}",
            help='JSON parameters for the report (e.g., \'{"processId": 1}\')',
        )
        parser.add_argument(
            "--output", "-o",
            type=str,
            help="Output filename (saved to generated_reports/ directory)",
        )
        parser.add_argument(
            "--list",
            action="store_true",
            help="List available report types",
        )
        parser.add_argument(
            "--list-data",
            action="store_true",
            help="List available data in the database for reports",
        )
        parser.add_argument(
            "--frontend-url",
            type=str,
            help="Override frontend URL (default: from settings or http://localhost:5173)",
        )
        # SPC-specific shortcuts
        parser.add_argument("--process", type=int, help="Process ID for SPC report")
        parser.add_argument("--step", type=int, help="Step ID for SPC report")
        parser.add_argument("--measurement", type=int, help="Measurement ID for SPC report")
        parser.add_argument("--mode", type=str, choices=["xbar-r", "i-mr"], default="xbar-r", help="Chart mode")
        parser.add_argument("--screenshot", action="store_true", help="Also save a screenshot for debugging")

    def handle(self, *args, **options):
        if options["list"]:
            self._list_report_types()
            return

        if options["list_data"]:
            self._list_available_data()
            return

        report_type = options["report_type"]
        if not report_type:
            self.stderr.write(self.style.ERROR("Report type required. Use --list to see available types."))
            return

        # Parse params - start with JSON params, then override with specific flags
        try:
            params = json.loads(options["params"])
        except json.JSONDecodeError as e:
            self.stderr.write(self.style.ERROR(f"Invalid JSON params: {e}"))
            return

        # Apply SPC-specific shortcuts
        if report_type == "spc":
            if options.get("process"):
                params["processId"] = options["process"]
            if options.get("step"):
                params["stepId"] = options["step"]
            if options.get("measurement"):
                params["measurementId"] = options["measurement"]
            if options.get("mode"):
                params["mode"] = options["mode"]

            # Default to first mock data option if no params specified
            if not params:
                params = {"processId": 1, "stepId": 101, "measurementId": 1001, "mode": "xbar-r"}
                self.stdout.write(self.style.WARNING(
                    "No params specified - using demo data defaults.\n"
                    "Run --list-data to see available mock options.\n"
                ))

        # Ensure output directory exists
        REPORTS_DIR.mkdir(exist_ok=True)

        # Output file with timestamp for uniqueness
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = options["output"] or f"{report_type}_{timestamp}.pdf"
        output_file = REPORTS_DIR / filename

        self.stdout.write(f"Generating {report_type} report...")
        self.stdout.write(f"  Params: {params}")
        self.stdout.write(f"  Output: {output_file}")

        try:
            generator = PdfGenerator(frontend_url=options.get("frontend_url"))

            # Check if report type is valid
            if report_type not in generator.REPORT_CONFIG:
                self.stderr.write(self.style.ERROR(
                    f"Unknown report type: {report_type}\n"
                    f"Valid types: {', '.join(generator.REPORT_CONFIG.keys())}"
                ))
                return

            self.stdout.write(f"  Fetching from: {generator.frontend_url}{generator.REPORT_CONFIG[report_type]['route']}")

            # Screenshot path for debugging
            screenshot_path = None
            if options.get("screenshot"):
                screenshot_path = str(REPORTS_DIR / f"{report_type}_{timestamp}.png")

            pdf_bytes = generator.generate(report_type, params, screenshot_path=screenshot_path)

            if screenshot_path:
                self.stdout.write(f"  Screenshot: {screenshot_path}")

            with open(output_file, "wb") as f:
                f.write(pdf_bytes)

            self.stdout.write(self.style.SUCCESS(
                f"\nPDF generated successfully!"
                f"\n  File: {output_file}"
                f"\n  Size: {len(pdf_bytes):,} bytes"
            ))

        except ImportError:
            self.stderr.write(self.style.ERROR(
                "Playwright is not installed.\n"
                "Run: pip install playwright && playwright install chromium"
            ))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to generate PDF: {e}"))

    def _list_report_types(self):
        self.stdout.write("\nAvailable Report Types:\n")
        self.stdout.write("-" * 60)

        for name, config in PdfGenerator.REPORT_CONFIG.items():
            self.stdout.write(f"\n  {self.style.SUCCESS(name)}")
            self.stdout.write(f"    Title: {config.get('title')}")
            self.stdout.write(f"    Route: {config.get('route')}")
            self.stdout.write(f"    Wait selector: {config.get('wait_selector')}")

        self.stdout.write("\n")

    def _list_available_data(self):
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.WARNING("SPC REPORT - Currently uses MOCK DATA (not real API)"))
        self.stdout.write("=" * 70)

        self.stdout.write("\nAvailable mock processes/steps for SPC reports:\n")

        for proc in SPC_MOCK_DATA["processes"]:
            proc_id = proc["id"]
            proc_name = proc["name"]
            self.stdout.write(f"\n  {self.style.SUCCESS(f'Process {proc_id}: {proc_name}')}")
            for step_id in proc["steps"]:
                step = SPC_MOCK_DATA["steps"][step_id]
                step_name = step["name"]
                measurements = step["measurements"]
                self.stdout.write(f"    Step {step_id}: {step_name}")
                self.stdout.write(f"      Measurements: {measurements}")

        self.stdout.write("\n" + "-" * 70)
        self.stdout.write("Example commands:")
        self.stdout.write("  python manage.py generate_pdf spc --process 1 --step 101")
        self.stdout.write("  python manage.py generate_pdf spc --process 2 --step 201 --mode i-mr")
        self.stdout.write("-" * 70)

        # Also show real database data if available
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.SUCCESS("REAL DATABASE DATA"))
        self.stdout.write("=" * 70)

        try:
            from Tracker.models import Processes, Steps, MeasurementDefinition

            processes = Processes.objects.all()[:10]
            if processes.exists():
                self.stdout.write(f"\nProcesses ({Processes.objects.count()} total):")
                for p in processes:
                    step_count = p.process_steps.count()
                    self.stdout.write(f"  ID {p.id}: {p.name} ({step_count} steps)")
            else:
                self.stdout.write("\n  No processes in database.")

            steps = Steps.objects.select_related('process')[:10]
            if steps.exists():
                self.stdout.write(f"\nSteps ({Steps.objects.count()} total):")
                for s in steps:
                    self.stdout.write(f"  ID {s.id}: {s.name} (Process: {s.process.name if s.process else 'N/A'})")
            else:
                self.stdout.write("\n  No steps in database.")

            measurements = MeasurementDefinition.objects.select_related('step')[:10]
            if measurements.exists():
                self.stdout.write(f"\nMeasurement Definitions ({MeasurementDefinition.objects.count()} total):")
                for m in measurements:
                    self.stdout.write(f"  ID {m.id}: {m.name} ({m.nominal} ±{m.tolerance_plus}/{m.tolerance_minus})")
            else:
                self.stdout.write("\n  No measurement definitions in database.")

        except Exception as e:
            self.stdout.write(f"\n  Could not query database: {e}")

        self.stdout.write("\n" + self.style.WARNING(
            "Note: SPC print page currently uses mock data.\n"
            "To use real data, the SpcPrintPage.tsx needs to be wired to the API."
        ))
        self.stdout.write("")

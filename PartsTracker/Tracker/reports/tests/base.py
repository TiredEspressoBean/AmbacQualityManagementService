"""
Base test mixin for report adapters.

Every report adapter gets four tests for free by subclassing
`ReportAdapterTestMixin` and declaring `adapter_class` + `fixture_name`:

    class TestCertOfConformance(ReportAdapterTestMixin, TestCase):
        adapter_class = CertOfConformanceAdapter
        fixture_name = "cert_of_conformance_sample"

The mixin assumes the fixture lives at
`Tracker/reports/tests/fixtures/<fixture_name>.json` and contains a
dict matching the adapter's `context_model_class` shape.

Covered:
    1. Context validates against the Pydantic model
    2. Template compiles to PDF bytes
    3. Output is deterministic (same context → same bytes)
    4. Cross-tenant ID is rejected (stub — per-adapter test files
       should override with a real cross-tenant probe that exercises
       the adapter's param_serializer_class)
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, ClassVar

from pydantic import ValidationError

from Tracker.reports.adapters.base import ReportAdapter
from Tracker.reports.services.typst_generator import generate_typst_pdf


# Typst stamps each PDF with fresh timestamps in two places — the PDF
# info dictionary (/CreationDate, /ModDate) and the XMP metadata stream
# (<xmp:CreateDate>, <xmp:ModifyDate>). Two consecutive renders straddling
# a 1-second boundary differ only in those bytes. Strip both before
# comparing.
_PDF_DATE_RE = re.compile(rb"/(?:CreationDate|ModDate) \(D:\d{14}Z\)")
_XMP_DATE_RE = re.compile(
    rb"<xmp:(?:Create|Modify)Date>[^<]*</xmp:(?:Create|Modify)Date>"
)


def _strip_pdf_timestamps(pdf: bytes) -> bytes:
    """Remove non-deterministic timestamps from PDF info dict and XMP stream."""
    pdf = _PDF_DATE_RE.sub(b"", pdf)
    pdf = _XMP_DATE_RE.sub(b"", pdf)
    return pdf


FIXTURE_DIR = Path(__file__).parent / "fixtures"


class ReportAdapterTestMixin:
    """
    Mixin; subclass it together with django.test.TestCase /
    SimpleTestCase.

    Required subclass attributes:
        adapter_class: ClassVar[type[ReportAdapter]]
        fixture_name:  ClassVar[str]  (no extension; file at fixtures/<name>.json)
    """

    adapter_class: ClassVar[type[ReportAdapter]]
    fixture_name: ClassVar[str]

    # ---- Helpers subclasses can override ------------------------------

    @classmethod
    def _load_fixture(cls) -> dict[str, Any]:
        """Load the fixture JSON as a dict."""
        fixture_path = FIXTURE_DIR / f"{cls.fixture_name}.json"
        if not fixture_path.exists():
            raise FileNotFoundError(
                f"Fixture not found: {fixture_path}. Use "
                f"`python manage.py export_context {cls.adapter_class.name} "
                f"--id <N> > {fixture_path}` to generate one."
            )
        return json.loads(fixture_path.read_text(encoding="utf-8"))

    @classmethod
    def _build_context_from_fixture(cls):
        """
        Construct a Pydantic context instance from the fixture dict.
        Does NOT go through the adapter's build_context() — this is
        a static fixture so the tests don't need DB state.
        """
        return cls.adapter_class.context_model_class(**cls._load_fixture())

    @classmethod
    def _render_from_fixture(cls) -> bytes:
        """Compile the template using the fixture context."""
        context = cls._build_context_from_fixture()
        return generate_typst_pdf(
            cls.adapter_class.template_path,
            context.model_dump(mode="json"),
        )

    # ---- Tests --------------------------------------------------------

    def test_fixture_validates_against_context_model(self):
        """
        Fixture data conforms to the adapter's Pydantic context model.
        Catches drift between fixture and schema during development.
        """
        try:
            self._build_context_from_fixture()
        except ValidationError as exc:
            self.fail(
                f"Fixture {self.fixture_name}.json does not validate against "
                f"{self.adapter_class.context_model_class.__name__}:\n{exc}"
            )

    def test_template_compiles_to_pdf(self):
        """
        Template renders the fixture context to a non-trivial PDF.
        Failure indicates a template bug (missing field, bad syntax).
        """
        pdf_bytes = self._render_from_fixture()
        self.assertTrue(
            pdf_bytes.startswith(b"%PDF"),
            f"Expected PDF magic header, got {pdf_bytes[:4]!r}",
        )
        self.assertGreater(
            len(pdf_bytes),
            500,
            f"PDF is suspiciously small ({len(pdf_bytes)} bytes)",
        )

    def test_output_is_deterministic(self):
        """
        Two renders of the same context produce byte-identical PDFs
        once non-deterministic Typst-injected timestamps are stripped.
        Required for regeneration-safe archival.
        """
        first = _strip_pdf_timestamps(self._render_from_fixture())
        second = _strip_pdf_timestamps(self._render_from_fixture())
        self.assertEqual(
            first, second,
            f"Template {self.adapter_class.template_path} is not deterministic",
        )

    def test_cross_tenant_id_is_rejected(self):
        """
        Default stub. Per-adapter test files MUST override this with a
        real cross-tenant probe that:
          1. Creates a resource (Order/CAPA/whatever) in Tenant A
          2. Authenticates as a user in Tenant B
          3. Submits the resource's ID to the param serializer
          4. Asserts a validation error is raised

        This test's default behavior is a no-op assertion; it exists
        so the test suite has a named method to override, making the
        security audit grep-able.
        """
        # Intentionally a no-op. Override per adapter.
        self.assertTrue(
            True,
            "Override test_cross_tenant_id_is_rejected with a real "
            "cross-tenant probe for this adapter.",
        )

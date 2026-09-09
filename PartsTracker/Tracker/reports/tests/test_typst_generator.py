"""
Smoke tests for the Typst PDF generator service.

Phase 0 deliverable: verifies the Typst pipeline works end-to-end.
These tests do not exercise any real report adapters — they only
prove the compile + context-injection path works and is deterministic.

When this file's tests pass, the Typst infrastructure is functional.
"""
from django.test import SimpleTestCase

from Tracker.reports.services.typst_generator import generate_typst_pdf
from Tracker.reports.tests.base import strip_pdf_timestamps


class TypstGeneratorSmokeTests(SimpleTestCase):
    """
    Verifies typst.Compiler produces valid, deterministic PDFs from
    the hello_world template.
    """

    HELLO_TEMPLATE = "hello_world.typ"

    def _hello_context(self) -> dict:
        return {"name": "Phase 0", "number": 42}

    def test_produces_pdf_bytes(self):
        """Compiled output starts with the PDF magic header."""
        pdf_bytes = generate_typst_pdf(self.HELLO_TEMPLATE, self._hello_context())
        self.assertTrue(
            pdf_bytes.startswith(b"%PDF"),
            f"Expected PDF magic header, got {pdf_bytes[:4]!r}",
        )

    def test_pdf_is_non_trivial_size(self):
        """
        Catch empty-PDF regressions. A real hello-world PDF with
        fonts + page headers is at least several KB.
        """
        pdf_bytes = generate_typst_pdf(self.HELLO_TEMPLATE, self._hello_context())
        self.assertGreater(
            len(pdf_bytes),
            500,
            f"PDF suspiciously small ({len(pdf_bytes)} bytes)",
        )

    def test_compile_is_deterministic(self):
        """
        Two compiles of the same template + context produce byte-identical output
        once Typst's clock-derived bytes are stripped. That is the real requirement
        for regenerable audit documents: the same inputs must render the same
        *document*, not the same timestamp.

        Comparing raw bytes here was a coin flip. Typst stamps a creation date and a
        document id derived from the clock at ~1s granularity, so two compiles inside
        one second matched and two straddling a tick did not — the same root cause as
        the old "NCR-adapter determinism" flake, which `strip_pdf_timestamps` exists
        to handle. This test predated that helper and never adopted it.
        """
        ctx = self._hello_context()
        first = strip_pdf_timestamps(generate_typst_pdf(self.HELLO_TEMPLATE, ctx))
        second = strip_pdf_timestamps(generate_typst_pdf(self.HELLO_TEMPLATE, ctx))
        self.assertEqual(
            first, second,
            "Typst compile is not deterministic - same inputs produced "
            "different PDF bytes (ignoring timestamps and document id)",
        )

    def test_different_context_produces_different_pdf(self):
        """Sanity check: sys.inputs actually reaches the template.

        Timestamps are stripped here too, and for a sharper reason than in the
        determinism test: two renders always differ by clock-derived bytes, so
        comparing raw output would pass this assertion even if the context never
        reached the template at all. Stripping them is what makes the difference
        attributable to the content.
        """
        a = strip_pdf_timestamps(
            generate_typst_pdf(self.HELLO_TEMPLATE, {"name": "Alice", "number": 1}))
        b = strip_pdf_timestamps(
            generate_typst_pdf(self.HELLO_TEMPLATE, {"name": "Bob", "number": 2}))
        self.assertNotEqual(
            a, b,
            "Context does not reach the template - PDFs for different "
            "inputs were byte-identical",
        )

    def test_missing_template_raises(self):
        """Unknown template name surfaces cleanly."""
        with self.assertRaises(FileNotFoundError):
            generate_typst_pdf("does_not_exist.typ", self._hello_context())

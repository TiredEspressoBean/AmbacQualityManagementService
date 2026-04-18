"""
Tests for HelloWorldAdapter — the dummy adapter that proves the full
dispatch path works.

Also serves as the reference implementation for per-adapter tests:
subclass ReportAdapterTestMixin, set adapter_class and fixture_name,
add any adapter-specific tests.
"""
from django.test import SimpleTestCase

from Tracker.reports.adapters.hello_world import HelloWorldAdapter
from Tracker.reports.services.pdf_generator import PdfGenerator, ReportParamError
from Tracker.reports.services.registry import UnknownReportError
from Tracker.reports.tests.base import ReportAdapterTestMixin


class TestHelloWorldAdapter(ReportAdapterTestMixin, SimpleTestCase):
    adapter_class = HelloWorldAdapter
    fixture_name = "hello_world_sample"

    # HelloWorld has no tenant-scoped data, so the cross-tenant test
    # is a no-op. Real adapters (CofC, SPC) must override this method
    # with a probe that creates a resource in Tenant A and asserts the
    # param serializer rejects it when submitted by Tenant B's user.
    def test_cross_tenant_id_is_rejected(self):
        self.skipTest("HelloWorldAdapter has no tenant-scoped params")


class HelloWorldAdapterDispatchTests(SimpleTestCase):
    """
    Dispatch-level tests — exercise the adapter through PdfGenerator
    (not directly). Proves the registry + param validation + context
    build + template compile pipeline works end-to-end.
    """

    def test_dispatches_through_registry(self):
        pdf = PdfGenerator().generate(
            "hello_world",
            {"name": "Dispatch", "number": 7},
        )
        self.assertTrue(pdf.startswith(b"%PDF"))

    def test_rejects_invalid_params(self):
        with self.assertRaises(ReportParamError) as ctx:
            PdfGenerator().generate(
                "hello_world",
                {"number": -1},  # violates min_value
            )
        self.assertIn("number", ctx.exception.errors)

    def test_rejects_unknown_report_type(self):
        with self.assertRaises(UnknownReportError):
            PdfGenerator().generate("does_not_exist", {})

    def test_filename_uses_name(self):
        adapter = HelloWorldAdapter()
        filename = adapter.get_filename({"name": "Phase 1", "number": 42})
        self.assertEqual(filename, "hello_world_Phase_1.pdf")

"""The document frame's branding and print stamp (2026-10-20).

Every report's context gets `_meta` from PdfGenerator, so the frame can print the
organisation, its logo and the print time without any adapter carrying them.
"""
from django.core.files.base import ContentFile
from django.test import TestCase

from Tracker.reports.services.pdf_generator import document_meta
from Tracker.reports.services.typst_generator import generate_typst_pdf


def _png() -> bytes:
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (30, 58, 138)).save(buf, "PNG")
    return buf.getvalue()


class DocumentMetaTests(TestCase):
    def setUp(self):
        from Tracker.models import Tenant
        self.tenant = Tenant.objects.create(name="Frame Co", slug="frame-co",
                                            default_timezone="America/Chicago")

    def test_names_the_organisation_and_stamps_the_print_time(self):
        meta = document_meta(self.tenant)
        self.assertEqual(meta["org_name"], "Frame Co")
        self.assertIsNone(meta["logo"])
        self.assertRegex(meta["printed_at"], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}")

    def test_carries_the_logo_bytes_for_the_template(self):
        self.tenant.logo.save("frame.png", ContentFile(_png()), save=True)
        try:
            meta = document_meta(self.tenant)
            self.assertEqual(bytes(meta["logo"]), _png())
        finally:
            self.tenant.logo.delete(save=False)

    def test_a_logo_typst_cannot_place_prints_unbranded(self):
        self.tenant.logo.save("frame.bmp", ContentFile(b"BM...."), save=True)
        try:
            self.assertIsNone(document_meta(self.tenant)["logo"])
        finally:
            self.tenant.logo.delete(save=False)

    def test_no_tenant_means_no_meta(self):
        self.assertEqual(document_meta(None), {})

    def test_a_branded_document_compiles(self):
        """The logo reaches Typst as an int array and is placed as an image."""
        from Tracker.reports.adapters.ncr import NcrAdapter
        from Tracker.reports.tests.base import FIXTURE_DIR
        import json
        ctx = NcrAdapter.context_model_class(
            **json.loads((FIXTURE_DIR / "ncr_report_sample.json").read_text(encoding="utf-8"))
        ).model_dump(mode="json")
        ctx["_meta"] = {"org_name": "Frame Co", "logo": list(_png()), "printed_at": "2026-10-20 14:05 CDT"}
        self.assertTrue(generate_typst_pdf("ncr_report.typ", ctx).startswith(b"%PDF"))


class LocalizeTimestampsTests(TestCase):
    """Aware timestamps print in plant time — the footer's clock — not UTC."""

    def setUp(self):
        from Tracker.models import Tenant
        self.tenant = Tenant(name="Clock Co", slug="clock-co", default_timezone="America/Chicago")

    def test_utc_moves_onto_the_plant_clock_everywhere_in_the_context(self):
        from Tracker.reports.services.pdf_generator import localize_timestamps
        out = localize_timestamps(
            {"at": "2026-07-15T19:29:30.768453Z", "rows": [{"t": "2026-01-10T12:00:00+00:00"}]},
            self.tenant)
        self.assertEqual(out["at"], "2026-07-15T14:29:30.768453-05:00")   # CDT
        self.assertEqual(out["rows"][0]["t"], "2026-01-10T06:00:00-06:00")  # CST

    def test_naive_datetimes_dates_and_other_strings_are_left_alone(self):
        from Tracker.reports.services.pdf_generator import localize_timestamps
        ctx = {"naive": "2026-03-18T10:30:00", "date": "2026-04-10", "svg": "<svg/>", "n": 3}
        self.assertEqual(localize_timestamps(ctx, self.tenant), ctx)

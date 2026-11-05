"""The shared report table's hyphen breaks leave the PDF's text clean (2026-11-05).

`report-table` lets every column but the first wrap after an in-word hyphen, so an ID
like ORD-2024-QA-INSPECT doesn't print over the next column. That break was a
zero-width space (U+200B) in the text: an ID copied out of the PDF carried it, and
pasted into a search box it didn't match. It's weak zero-width spacing now, which
breaks the line without putting a character into the text.
"""
import io
from pathlib import Path

import typst
from django.test import SimpleTestCase
from PyPDF2 import PdfReader

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"


class ReportTableTextTests(SimpleTestCase):

    def test_a_wrapped_id_extracts_without_hidden_characters(self):
        # A narrow column, so the ID has to wrap at its hyphens.
        source = (
            '#import "/_common/components.typ": report-table\n'
            "#set page(width: 3in, height: auto, margin: 0.2in)\n"
            '#report-table((auto, 0.6in), ("Due", "Order"), '
            '(("2026-10-30", "ORD-2024-QA-INSPECT"),))\n'
        ).encode()
        pdf = typst.compile(source, root=str(TEMPLATES), format="pdf")
        text = PdfReader(io.BytesIO(pdf)).pages[0].extract_text()
        self.assertNotIn("​", text)
        self.assertIn("INSPECT", text)
        self.assertGreater(text.count("\n"), 1, "the ID still wraps in the narrow column")

"""
Base class for document package generators.

Provides shared utilities for:
- PDF form filling (PyPDF2)
- Page rendering (Playwright)
- PDF merging (PyPDF2)
"""
import logging
from io import BytesIO
from typing import BinaryIO, Optional, Union

from django.conf import settings

logger = logging.getLogger(__name__)


class BasePackageGenerator:
    """
    Base class for generating document packages.

    Subclass this for specific package types (PPAP, FAI, CoC, etc.)
    and implement the generate() method.
    """

    package_name: str = "Document Package"

    def __init__(self):
        self.pdf_generator = None  # Lazy load to avoid circular imports

    def generate(self, *args, **kwargs) -> bytes:
        """
        Generate the complete package. Override in subclasses.

        Returns:
            PDF as bytes
        """
        raise NotImplementedError("Subclasses must implement generate()")

    # -------------------------------------------------------------------------
    # Form Filling (PyPDF2)
    # -------------------------------------------------------------------------

    def fill_form(
        self,
        template_path: str,
        field_data: dict,
        flatten: bool = True
    ) -> bytes:
        """
        Fill a PDF form template with data.

        Args:
            template_path: Path to the blank PDF form template
            field_data: Dict mapping field names to values
            flatten: If True, flatten form fields (not editable after)

        Returns:
            Filled PDF as bytes
        """
        from PyPDF2 import PdfReader, PdfWriter

        reader = PdfReader(template_path)
        writer = PdfWriter()

        # Copy all pages
        for page in reader.pages:
            writer.add_page(page)

        # Fill form fields on first page (most forms are single page)
        # For multi-page forms, may need to update specific pages
        writer.update_page_form_field_values(writer.pages[0], field_data)

        if flatten:
            # Make fields read-only / non-editable
            for page in writer.pages:
                if "/Annots" in page:
                    for annot in page["/Annots"]:
                        annot_obj = annot.get_object()
                        if annot_obj.get("/FT") == "/Tx":  # Text field
                            annot_obj.update({"/Ff": 1})  # Read-only flag

        output = BytesIO()
        writer.write(output)
        output.seek(0)
        return output.read()

    def get_form_field_names(self, template_path: str) -> list[str]:
        """
        Get all form field names from a PDF template.
        Useful for debugging/mapping fields.

        Args:
            template_path: Path to the PDF form

        Returns:
            List of field names
        """
        from PyPDF2 import PdfReader

        reader = PdfReader(template_path)
        fields = reader.get_fields()
        return list(fields.keys()) if fields else []

    # -------------------------------------------------------------------------
    # Page Rendering (Playwright)
    # -------------------------------------------------------------------------

    def render_page(self, route: str, params: dict) -> bytes:
        """
        Render a frontend page to PDF using Playwright.

        Args:
            route: Frontend route (e.g., "/spc/print")
            params: Query parameters to pass

        Returns:
            PDF as bytes
        """
        # Lazy import to avoid circular dependency
        if self.pdf_generator is None:
            from Tracker.services.pdf_generator import PdfGenerator
            self.pdf_generator = PdfGenerator()

        # Build a temporary config for this render
        # The PdfGenerator.generate() method expects a report_type that maps to config
        # For flexibility, we'll call the underlying Playwright logic directly
        return self._render_with_playwright(route, params)

    def _render_with_playwright(self, route: str, params: dict) -> bytes:
        """Direct Playwright rendering for arbitrary routes."""
        from urllib.parse import urlencode

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
            raise

        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")
        url = f"{frontend_url}{route}"
        if params:
            url += f"?{urlencode(params)}"

        logger.info(f"Rendering page to PDF: {url}")

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            page = browser.new_page()
            page.goto(url, wait_until="networkidle")

            # Wait for print-ready signal
            try:
                page.wait_for_selector("[data-print-ready]", timeout=30000)
            except Exception as e:
                logger.warning(f"Timeout waiting for [data-print-ready]: {e}")

            pdf_bytes = page.pdf(
                format="Letter",
                print_background=True,
                margin={"top": "0.5in", "bottom": "0.5in", "left": "0.5in", "right": "0.5in"}
            )
            browser.close()

        return pdf_bytes

    # -------------------------------------------------------------------------
    # PDF Merging (PyPDF2)
    # -------------------------------------------------------------------------

    def merge_pdfs(self, pdfs: list[Union[bytes, BinaryIO, str]]) -> bytes:
        """
        Merge multiple PDFs into one.

        Args:
            pdfs: List of PDFs as bytes, file objects, or file paths

        Returns:
            Merged PDF as bytes
        """
        from PyPDF2 import PdfMerger

        merger = PdfMerger()

        for pdf in pdfs:
            if isinstance(pdf, bytes):
                merger.append(BytesIO(pdf))
            elif isinstance(pdf, str):
                # File path
                merger.append(pdf)
            else:
                # File-like object
                merger.append(pdf)

        output = BytesIO()
        merger.write(output)
        output.seek(0)
        return output.read()

    # -------------------------------------------------------------------------
    # Utilities
    # -------------------------------------------------------------------------

    def get_uploaded_document(self, document) -> Optional[bytes]:
        """
        Get PDF bytes from an uploaded Document model instance.

        Args:
            document: Documents model instance

        Returns:
            PDF bytes or None if not a PDF / not accessible
        """
        if not document or not document.file:
            return None

        try:
            # Check if it's a PDF
            if not document.file.name.lower().endswith('.pdf'):
                logger.warning(f"Document {document.id} is not a PDF: {document.file.name}")
                return None

            document.file.seek(0)
            return document.file.read()
        except Exception as e:
            logger.error(f"Failed to read document {document.id}: {e}")
            return None

    def get_filename(self, identifier: str = "package") -> str:
        """
        Generate a filename for the package.

        Args:
            identifier: Unique identifier (e.g., part number, submission ID)

        Returns:
            Filename string
        """
        from django.utils import timezone

        safe_name = self.package_name.replace(" ", "_")
        timestamp = timezone.now().strftime("%Y%m%d")
        return f"{safe_name}_{identifier}_{timestamp}.pdf"

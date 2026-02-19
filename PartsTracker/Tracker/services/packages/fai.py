"""
FAI (First Article Inspection) package generator.

Generates AS9102 compliant FAI packages including:
- Form 1: Part Number Accountability
- Form 2: Product Accountability (materials, processes)
- Form 3: Characteristic Accountability (dimensional results)
- Supporting documentation
"""
import logging
from typing import TYPE_CHECKING

from .base import BasePackageGenerator

if TYPE_CHECKING:
    pass  # from Tracker.models import FirstArticleInspection

logger = logging.getLogger(__name__)


class FAIPackageGenerator(BasePackageGenerator):
    """
    Generates AS9102 First Article Inspection packages.

    Usage:
        generator = FAIPackageGenerator()
        pdf_bytes = generator.generate(fai)
    """

    package_name = "FAI Package"

    # Paths to blank AS9102 form templates
    FORM1_TEMPLATE = "templates/forms/as9102_form1.pdf"
    FORM2_TEMPLATE = "templates/forms/as9102_form2.pdf"
    # Form 3 is typically generated from data, not form-filled

    def generate(self, fai) -> bytes:
        """
        Generate complete FAI package.

        Args:
            fai: FirstArticleInspection model instance (or Part with FAI data)

        Returns:
            Merged PDF containing all forms and supporting docs
        """
        pdfs = []

        # 1. Cover sheet
        cover = self._generate_cover_sheet(fai)
        if cover:
            pdfs.append(cover)

        # 2. Form 1 - Part Number Accountability
        form1 = self._generate_form1(fai)
        if form1:
            pdfs.append(form1)

        # 3. Form 2 - Product Accountability
        form2 = self._generate_form2(fai)
        if form2:
            pdfs.append(form2)

        # 4. Form 3 - Characteristic Accountability (dimensional)
        form3 = self._generate_form3(fai)
        if form3:
            pdfs.append(form3)

        # 5. Supporting documentation
        supporting = self._get_supporting_docs(fai)
        pdfs.extend(supporting)

        if not pdfs:
            raise ValueError("No elements to include in FAI package")

        return self.merge_pdfs(pdfs)

    def _generate_cover_sheet(self, fai) -> bytes | None:
        """Generate FAI package cover sheet."""
        # TODO: Implement cover sheet print route
        return None

    def _generate_form1(self, fai) -> bytes | None:
        """
        Generate AS9102 Form 1 - Part Number Accountability.

        Contains: Part info, drawing info, organization info, FAI reason.
        """
        # TODO: Map FAI data to Form 1 fields
        # field_data = self._map_form1_fields(fai)
        # return self.fill_form(self.FORM1_TEMPLATE, field_data)
        return None

    def _generate_form2(self, fai) -> bytes | None:
        """
        Generate AS9102 Form 2 - Product Accountability.

        Contains: Materials, special processes, functional tests.
        """
        # TODO: Map FAI data to Form 2 fields
        # field_data = self._map_form2_fields(fai)
        # return self.fill_form(self.FORM2_TEMPLATE, field_data)
        return None

    def _generate_form3(self, fai) -> bytes | None:
        """
        Generate AS9102 Form 3 - Characteristic Accountability.

        Contains: Dimensional results table.
        This is typically rendered (not form-filled) due to variable row count.
        """
        # TODO: Render dimensional results page
        # return self.render_page(f"/fai/{fai.id}/form3/print", {"fai_id": fai.id})
        return None

    def _get_supporting_docs(self, fai) -> list[bytes]:
        """Get supporting documentation (certs, test reports, etc.)."""
        # TODO: Gather linked documents
        return []

    def _map_form1_fields(self, fai) -> dict:
        """Map FAI data to Form 1 field names."""
        return {
            "PartNumber": "",
            "PartName": "",
            "DrawingNumber": "",
            "DrawingRevision": "",
            "OrganizationName": "",
            "FAIReason": "",  # New, Change, Other
            # ... more fields
        }

    def _map_form2_fields(self, fai) -> dict:
        """Map FAI data to Form 2 field names."""
        return {
            # Material rows
            # Special process rows
            # Functional test rows
        }

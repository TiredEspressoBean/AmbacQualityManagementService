"""
Certificate of Conformance (C of C) package generator.

Generates shipment documentation packages including:
- Certificate of Conformance
- Inspection summary
- Material certifications
- Test reports
"""
import logging
from typing import TYPE_CHECKING

from .base import BasePackageGenerator

if TYPE_CHECKING:
    from Tracker.models import CustomerOrder

logger = logging.getLogger(__name__)


class CoCPackageGenerator(BasePackageGenerator):
    """
    Generates Certificate of Conformance packages.

    Usage:
        generator = CoCPackageGenerator()
        pdf_bytes = generator.generate(order)
    """

    package_name = "Certificate of Conformance"

    def generate(self, order) -> bytes:
        """
        Generate C of C package for an order.

        Args:
            order: CustomerOrder model instance

        Returns:
            Merged PDF containing C of C and supporting docs
        """
        pdfs = []

        # 1. Certificate of Conformance (main document)
        coc = self._generate_coc(order)
        if coc:
            pdfs.append(coc)

        # 2. Inspection summary
        inspection = self._generate_inspection_summary(order)
        if inspection:
            pdfs.append(inspection)

        # 3. Material certifications
        material_certs = self._get_material_certs(order)
        pdfs.extend(material_certs)

        # 4. Test reports (if any)
        test_reports = self._get_test_reports(order)
        pdfs.extend(test_reports)

        if not pdfs:
            raise ValueError("No documents to include in C of C package")

        return self.merge_pdfs(pdfs)

    def _generate_coc(self, order) -> bytes | None:
        """
        Generate the Certificate of Conformance document.

        Contains: Part list, PO reference, conformance statement, signatures.
        """
        return self.render_page(
            f"/orders/{order.id}/coc/print",
            {"order_id": order.id}
        )

    def _generate_inspection_summary(self, order) -> bytes | None:
        """
        Generate inspection summary for all parts in order.

        Contains: Pass/fail counts, key measurements, inspector info.
        """
        # TODO: Implement inspection summary print route
        # return self.render_page(
        #     f"/orders/{order.id}/inspection-summary/print",
        #     {"order_id": order.id}
        # )
        return None

    def _get_material_certs(self, order) -> list[bytes]:
        """
        Get material certifications linked to the order.

        Returns: List of PDF bytes for each material cert.
        """
        certs = []
        # TODO: Query Documents linked to order with type CERT/MATERIAL
        # for doc in order.documents.filter(document_type__code='CERT'):
        #     pdf = self.get_uploaded_document(doc)
        #     if pdf:
        #         certs.append(pdf)
        return certs

    def _get_test_reports(self, order) -> list[bytes]:
        """
        Get test reports linked to the order.

        Returns: List of PDF bytes for each test report.
        """
        reports = []
        # TODO: Query Documents linked to order with type TEST
        return reports

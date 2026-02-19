"""
8D Report package generator.

Generates 8D problem-solving documentation packages including:
- 8D Report (all 8 disciplines)
- Root cause analysis documentation
- Verification evidence
- Supporting attachments
"""
import logging
from typing import TYPE_CHECKING

from .base import BasePackageGenerator

if TYPE_CHECKING:
    from Tracker.models import CAPA

logger = logging.getLogger(__name__)


class EightDPackageGenerator(BasePackageGenerator):
    """
    Generates 8D Report packages.

    Usage:
        generator = EightDPackageGenerator()
        pdf_bytes = generator.generate(capa)
    """

    package_name = "8D Report"

    def generate(self, capa) -> bytes:
        """
        Generate complete 8D package for a CAPA.

        Args:
            capa: CAPA model instance

        Returns:
            Merged PDF containing 8D report and supporting docs
        """
        pdfs = []

        # 1. Main 8D Report
        report = self._generate_8d_report(capa)
        if report:
            pdfs.append(report)

        # 2. Root cause analysis detail (if extensive)
        rca = self._generate_rca_detail(capa)
        if rca:
            pdfs.append(rca)

        # 3. Verification evidence
        verification = self._generate_verification_evidence(capa)
        if verification:
            pdfs.append(verification)

        # 4. Attachments
        attachments = self._get_attachments(capa)
        pdfs.extend(attachments)

        if not pdfs:
            raise ValueError("No documents to include in 8D package")

        return self.merge_pdfs(pdfs)

    def _generate_8d_report(self, capa) -> bytes | None:
        """
        Generate the main 8D report document.

        Contains all 8 disciplines:
        - D1: Team
        - D2: Problem Description
        - D3: Interim Containment
        - D4: Root Cause Analysis
        - D5: Permanent Corrective Actions
        - D6: Implementation & Verification
        - D7: Preventive Actions
        - D8: Team Recognition
        """
        return self.render_page(
            f"/quality/capas/{capa.id}/8d/print",
            {"capa_id": capa.id}
        )

    def _generate_rca_detail(self, capa) -> bytes | None:
        """
        Generate detailed root cause analysis documentation.

        Includes 5 Whys and/or Fishbone diagram if present.
        """
        if not hasattr(capa, 'rca_record') or not capa.rca_record:
            return None

        # TODO: Implement RCA detail print route
        # return self.render_page(
        #     f"/quality/capas/{capa.id}/rca/print",
        #     {"capa_id": capa.id}
        # )
        return None

    def _generate_verification_evidence(self, capa) -> bytes | None:
        """
        Generate verification evidence summary.

        Shows verification activities and results.
        """
        if not hasattr(capa, 'verification') or not capa.verification:
            return None

        # TODO: Implement verification print route
        return None

    def _get_attachments(self, capa) -> list[bytes]:
        """
        Get attachments linked to the CAPA.

        Returns: List of PDF bytes for each attachment.
        """
        attachments = []
        # TODO: Query Documents linked to CAPA
        # for doc in capa.documents.all():
        #     pdf = self.get_uploaded_document(doc)
        #     if pdf:
        #         attachments.append(pdf)
        return attachments

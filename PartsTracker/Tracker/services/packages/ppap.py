"""
PPAP (Production Part Approval Process) package generator.

Generates complete PPAP submission packages including:
- PSW (Part Submission Warrant) - form filled
- Cover sheet / element index
- All 18 elements (rendered or uploaded)
"""
import logging
from typing import TYPE_CHECKING

from .base import BasePackageGenerator

if TYPE_CHECKING:
    pass  # from Tracker.models import PPAPSubmission

logger = logging.getLogger(__name__)


class PPAPPackageGenerator(BasePackageGenerator):
    """
    Generates PPAP submission packages.

    Usage:
        generator = PPAPPackageGenerator()
        pdf_bytes = generator.generate(submission)
    """

    package_name = "PPAP Package"

    # Path to blank PSW form template (AIAG format)
    PSW_TEMPLATE = "templates/forms/psw_blank.pdf"

    def generate(self, submission) -> bytes:
        """
        Generate complete PPAP package for a submission.

        Args:
            submission: PPAPSubmission model instance

        Returns:
            Merged PDF containing all elements
        """
        pdfs = []

        # 1. Cover sheet / index
        cover = self._generate_cover_sheet(submission)
        if cover:
            pdfs.append(cover)

        # 2. PSW (Element 18 - but goes first in package)
        psw = self._generate_psw(submission)
        if psw:
            pdfs.append(psw)

        # 3. Each element in order
        for element_num in range(1, 19):
            if element_num == 18:
                continue  # PSW already added

            element_pdf = self._generate_element(submission, element_num)
            if element_pdf:
                pdfs.append(element_pdf)

        if not pdfs:
            raise ValueError("No elements to include in PPAP package")

        return self.merge_pdfs(pdfs)

    def _generate_cover_sheet(self, submission) -> bytes:
        """Generate PPAP package cover sheet with element checklist."""
        return self.render_page(
            f"/ppap/{submission.id}/cover/print",
            {"submission_id": submission.id}
        )

    def _generate_psw(self, submission) -> bytes:
        """Fill PSW form with submission data."""
        field_data = self._map_psw_fields(submission)
        return self.fill_form(self.PSW_TEMPLATE, field_data)

    def _map_psw_fields(self, submission) -> dict:
        """
        Map PPAPSubmission data to PSW form field names.

        TODO: Update field names to match actual PSW template fields.
        """
        return {
            # Part Information
            "PartName": submission.part_type.name if submission.part_type else "",
            "PartNumber": submission.part_type.part_number if submission.part_type else "",
            "ECLevel": submission.engineering_change_level or "",
            "SafetyItem": "Yes" if submission.is_safety_item else "No",

            # Organization Information
            "SupplierName": "",  # TODO: Get from settings or company
            "SupplierCode": "",
            "CustomerName": submission.customer.name if submission.customer else "",

            # Submission Information
            "SubmissionReason": submission.get_submission_reason_display() if hasattr(submission, 'get_submission_reason_display') else "",
            "SubmissionLevel": str(submission.submission_level) if submission.submission_level else "3",

            # Element checklist would be checkboxes - handle separately
        }

    def _generate_element(self, submission, element_num: int) -> bytes | None:
        """
        Generate or retrieve a specific PPAP element.

        Args:
            submission: PPAPSubmission instance
            element_num: Element number (1-18)

        Returns:
            PDF bytes or None if element is N/A
        """
        # Check if element is marked N/A
        checklist = submission.element_checklist or {}
        element_status = checklist.get(str(element_num), {})

        if element_status.get("na"):
            return None

        # Route to appropriate generation method
        element_handlers = {
            1: self._element_design_records,
            2: self._element_engineering_change,
            3: self._element_customer_approval,
            4: self._element_design_fmea,
            5: self._element_process_flow,
            6: self._element_process_fmea,
            7: self._element_control_plan,
            8: self._element_msa,
            9: self._element_dimensional,
            10: self._element_material_test,
            11: self._element_initial_process,
            12: self._element_lab_docs,
            13: self._element_aar,
            14: None,  # Sample parts - physical
            15: None,  # Master sample - physical
            16: self._element_checking_aids,
            17: self._element_customer_requirements,
        }

        handler = element_handlers.get(element_num)
        if handler is None:
            return None

        try:
            return handler(submission)
        except Exception as e:
            logger.error(f"Failed to generate PPAP element {element_num}: {e}")
            return None

    # -------------------------------------------------------------------------
    # Element Handlers (stubs - implement as needed)
    # -------------------------------------------------------------------------

    def _element_design_records(self, submission) -> bytes | None:
        """Element 1: Design Records - uploaded drawings."""
        # TODO: Get linked design documents and merge
        return None

    def _element_engineering_change(self, submission) -> bytes | None:
        """Element 2: Engineering Change Documents."""
        # TODO: Get linked ECN/ECO documents
        return None

    def _element_customer_approval(self, submission) -> bytes | None:
        """Element 3: Customer Engineering Approval."""
        # TODO: Render approval status page
        return None

    def _element_design_fmea(self, submission) -> bytes | None:
        """Element 4: Design FMEA - uploaded."""
        # TODO: Get linked DFMEA document
        return None

    def _element_process_flow(self, submission) -> bytes | None:
        """Element 5: Process Flow Diagram."""
        if not submission.part_type or not submission.part_type.process:
            return None
        return self.render_page(
            f"/process/{submission.part_type.process.id}/print",
            {"process_id": submission.part_type.process.id}
        )

    def _element_process_fmea(self, submission) -> bytes | None:
        """Element 6: Process FMEA - uploaded."""
        # TODO: Get linked PFMEA document
        return None

    def _element_control_plan(self, submission) -> bytes | None:
        """Element 7: Control Plan - uploaded or generated."""
        # TODO: Get linked control plan document
        return None

    def _element_msa(self, submission) -> bytes | None:
        """Element 8: MSA / Gage R&R Studies."""
        # TODO: Render MSA report when module exists
        return None

    def _element_dimensional(self, submission) -> bytes | None:
        """Element 9: Dimensional Results."""
        # TODO: Render dimensional results / FAI Form 3
        return None

    def _element_material_test(self, submission) -> bytes | None:
        """Element 10: Material / Performance Test Results."""
        # TODO: Get linked test reports and material certs
        return None

    def _element_initial_process(self, submission) -> bytes | None:
        """Element 11: Initial Process Studies (SPC/Cpk)."""
        # TODO: Render SPC report for part type
        return None

    def _element_lab_docs(self, submission) -> bytes | None:
        """Element 12: Qualified Laboratory Documentation."""
        # TODO: Get linked lab certifications
        return None

    def _element_aar(self, submission) -> bytes | None:
        """Element 13: Appearance Approval Report."""
        # TODO: Fill AAR form template when model exists
        return None

    def _element_checking_aids(self, submission) -> bytes | None:
        """Element 16: Checking Aids."""
        # TODO: Render checking aids list with equipment
        return None

    def _element_customer_requirements(self, submission) -> bytes | None:
        """Element 17: Customer-Specific Requirements."""
        # TODO: Render customer requirements checklist
        return None

"""
Documents seed data: Company documents, approval workflows, revision history.
"""

import random
from datetime import timedelta
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.utils import timezone

from Tracker.models import (
    Documents, DocumentType, Companies,
    ApprovalRequest, ApprovalResponse, ApprovalTemplate,
    Approval_Status_Type, Approval_Type, ApprovalDecision,
    ClassificationLevel, TenantGroup,
)
from .base import BaseSeeder


class DocumentSeeder(BaseSeeder):
    """
    Seeds document-related data.

    Creates:
    - Company-level documents (SOPs, policies, work instructions)
    - Documents with revision history
    - Approval workflows for controlled documents
    - Approval responses
    """

    def seed(self, companies, users):
        """Run the full document seeding process."""
        self.create_company_documents(companies, users)
        self.create_approval_workflow_demo(users)

    # =========================================================================
    # Company Documents with Revision History
    # =========================================================================

    def create_company_documents(self, companies, users):
        """Create company-level documents (SOPs, policies, etc.) with revision history."""
        ambac = companies[0]  # AMBAC is always first

        doc_configs = [
            ('SOP', 'SOP-001 Quality Manual', ClassificationLevel.INTERNAL, True),
            ('SOP', 'SOP-002 Receiving Inspection', ClassificationLevel.INTERNAL, True),
            ('WI', 'WI-001 Injector Disassembly', ClassificationLevel.PUBLIC, True),
            ('WI', 'WI-002 Flow Testing Procedure', ClassificationLevel.PUBLIC, False),
            ('POL', 'POL-001 Quality Policy', ClassificationLevel.PUBLIC, True),
            ('FRM', 'FRM-001 Inspection Checklist', ClassificationLevel.INTERNAL, False),
            ('SPEC', 'SPEC-001 Injector Specifications', ClassificationLevel.CONFIDENTIAL, True),
        ]

        doc_count = 0
        revision_count = 0

        for doc_type_code, doc_name, classification, has_revisions in doc_configs:
            try:
                doc_type = DocumentType.objects.get(code=doc_type_code, tenant=self.tenant)
            except DocumentType.DoesNotExist:
                continue

            file_name = f"{doc_name.lower().replace(' ', '_')}.pdf"
            uploader = self.get_weighted_employee(users)
            approver = self.get_weighted_qa_staff(users)

            # Base timestamp for document creation (spread over past 6 months)
            base_date = timezone.now() - timedelta(days=random.randint(30, 180))

            if has_revisions:
                doc_count += self._create_document_with_revisions(
                    doc_type, doc_name, classification, uploader, approver,
                    ambac, base_date
                )
                revision_count += 1
            else:
                self._create_single_version_document(
                    doc_type, doc_name, classification, uploader, approver,
                    ambac, base_date, file_name
                )
                doc_count += 1

        self.log(f"Created {doc_count} company-level documents ({revision_count} with revisions)")

    def _create_document_with_revisions(self, doc_type, doc_name, classification,
                                        uploader, approver, company, base_date):
        """Create document with revision history: v1 (OBSOLETE) -> v2 (OBSOLETE) -> v3 (RELEASED)."""
        num_versions = random.randint(2, 3)
        previous_doc = None
        doc_count = 0

        for version_num in range(1, num_versions + 1):
            is_current = (version_num == num_versions)
            version_date = base_date + timedelta(days=(version_num - 1) * random.randint(14, 45))

            status = 'RELEASED' if version_num == num_versions else 'OBSOLETE'
            version_file_name = f"{doc_name.lower().replace(' ', '_')}_v{version_num}.pdf"

            doc = Documents.objects.create(
                tenant=self.tenant,
                document_type=doc_type,
                classification=classification,
                is_image=False,
                file_name=version_file_name,
                file=ContentFile(
                    f"Content of {doc_name} - Version {version_num}".encode(),
                    name=version_file_name
                ),
                uploaded_by=uploader,
                content_type=ContentType.objects.get_for_model(Companies),
                object_id=company.id,
                status=status,
                version=version_num,
                previous_version=previous_doc,
                is_current_version=is_current,
                approved_by=approver if status == 'RELEASED' else None,
                approved_at=version_date + timedelta(days=random.randint(1, 7)) if status == 'RELEASED' else None,
            )

            # Backdate the document
            Documents.objects.filter(pk=doc.pk).update(
                created_at=version_date,
                updated_at=version_date + timedelta(days=random.randint(1, 14))
            )

            previous_doc = doc
            doc_count += 1

        return doc_count

    def _create_single_version_document(self, doc_type, doc_name, classification,
                                        uploader, approver, company, base_date, file_name):
        """Create single version document (no revision history)."""
        doc = Documents.objects.create(
            tenant=self.tenant,
            document_type=doc_type,
            classification=classification,
            is_image=False,
            file_name=file_name,
            file=ContentFile(f"Content of {doc_name}".encode(), name=file_name),
            uploaded_by=uploader,
            content_type=ContentType.objects.get_for_model(Companies),
            object_id=company.id,
            status='RELEASED',
            approved_by=approver,
            approved_at=base_date + timedelta(days=random.randint(1, 7)),
        )

        # Backdate the document
        Documents.objects.filter(pk=doc.pk).update(
            created_at=base_date,
            updated_at=base_date + timedelta(days=random.randint(1, 7))
        )

    # =========================================================================
    # Approval Workflows
    # =========================================================================

    def create_approval_workflow_demo(self, users):
        """Create approval workflow demo data for documents requiring approval."""
        try:
            self._create_approval_workflow_demo_inner(users)
        except Exception as e:
            if 'does not exist' in str(e) or 'relation' in str(e):
                self.log(
                    f"  Skipping approval workflow (missing tables - run migrations): {e}",
                    warning=True
                )
            else:
                raise

    def _create_approval_workflow_demo_inner(self, users):
        """Inner implementation of approval workflow demo."""
        # Get documents that should have approval workflows
        documents_needing_approval = Documents.objects.filter(
            document_type__requires_approval=True,
            status='RELEASED'
        )[:15]

        if not documents_needing_approval.exists():
            self.log("  No documents requiring approval found")
            return

        # Get approval template for documents
        try:
            doc_template = ApprovalTemplate.objects.get(approval_type='DOCUMENT_RELEASE')
        except ApprovalTemplate.DoesNotExist:
            self.log("  No DOCUMENT_RELEASE approval template found")
            return

        qa_managers = [
            u for u in users.get('qa_staff', [])
            if u.user_roles.filter(group__name='QA_Manager', group__tenant=self.tenant).exists()
        ]
        if not qa_managers:
            qa_managers = users.get('managers', users['employees'][:2])

        approval_count = 0
        response_count = 0

        # Status distribution for demo
        status_weights = [
            (Approval_Status_Type.APPROVED, 0.4),
            (Approval_Status_Type.PENDING, 0.35),
            (Approval_Status_Type.REJECTED, 0.15),
            (Approval_Status_Type.CANCELLED, 0.1),
        ]

        for doc in documents_needing_approval:
            status = self.weighted_choice(status_weights)
            requester = doc.uploaded_by or random.choice(users['employees'])

            # Create ApprovalRequest
            approval_request = ApprovalRequest.objects.create(
                tenant=self.tenant,
                approval_number=ApprovalRequest.generate_approval_number(tenant=self.tenant),
                content_type=ContentType.objects.get_for_model(Documents),
                object_id=doc.id,
                approval_type=Approval_Type.DOCUMENT_RELEASE,
                status=status,
                requested_by=requester,
                flow_type=doc_template.approval_flow_type,
                due_date=timezone.now() + timedelta(days=doc_template.default_due_days),
                reason=f"Release approval for {doc.file_name}",
            )

            # Add approvers from QA group (TenantGroup)
            qa_group = TenantGroup.objects.filter(name='QA_Manager', tenant=self.tenant).first()
            if qa_group:
                approval_request.approver_groups.add(qa_group)
            for approver in qa_managers[:2]:
                approval_request.add_approver(approver, is_required=True)

            approval_count += 1

            # Create responses for non-pending approvals
            if status != Approval_Status_Type.PENDING:
                response_count += self._create_approval_responses(
                    approval_request, qa_managers[:2], status
                )

                # Set completed_at for approved/rejected
                if status in [Approval_Status_Type.APPROVED, Approval_Status_Type.REJECTED]:
                    approval_request.completed_at = timezone.now()
                    approval_request.save()

        self.log(f"Created {approval_count} approval requests with {response_count} responses")

    def _create_approval_responses(self, approval_request, approvers, status):
        """Create approval responses based on the request status."""
        response_count = 0

        for approver in approvers:
            if status == Approval_Status_Type.APPROVED:
                decision = ApprovalDecision.APPROVED
                comments = "Document reviewed and approved. Content meets quality standards."
            elif status == Approval_Status_Type.REJECTED:
                decision = ApprovalDecision.REJECTED
                comments = "Revisions needed. Please address formatting and technical accuracy."
            else:  # CANCELLED
                decision = ApprovalDecision.APPROVED
                comments = "Approved but request was later cancelled."

            ApprovalResponse.objects.create(
                tenant=self.tenant,
                approval_request=approval_request,
                approver=approver,
                decision=decision,
                comments=comments,
            )
            response_count += 1

        return response_count

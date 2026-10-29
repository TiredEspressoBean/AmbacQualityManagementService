"""
A sequential approval in enforced stages, part of the way through.

A "Controlled Drawing" document type names its own DOCUMENT_RELEASE template, "Drawing
Release (sequential)". It is not the type's default (made after the starters, with
is_default off), so every other document keeps the default release route, and no
other seeded document is a Controlled Drawing.

  Stage 1  Jordan Reyes (Engineering), named
  Stage 2  the QA Manager group — any one member answers for it, and it is required
  Stage 3  Jennifer (Production Manager), named

DWG-1001, raised by Lisa (Document Controller), is submitted through the document
service. Jordan has approved stage 1 (dated two hours ago as it is recorded: responses
are immutable, so it is never re-dated afterward). Stage 2 is open: Maria may answer;
Jennifer, at stage 3, is refused with "Not your turn — waiting on QA Manager." until
she has.
"""
from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from Tracker.models import (
    ApprovalDecision, ApprovalTemplate, Approval_Type, DocumentType, Documents,
    TenantGroup,
)
from Tracker.models.core import ApprovalDelegation, ApprovalFlows, SequenceTypes

from ..base import BaseSeeder

DOC_TYPE = {'code': 'CDWG', 'name': 'Controlled Drawing',
            'description': 'Released engineering drawings, approved in order: '
                           'engineering, quality, production.'}
TEMPLATE_NAME = 'Drawing Release (sequential)'
DRAWING_FILE = 'DWG-1001 Body bore detail'
QA_GROUP = 'QA Manager'


class DemoSequentialApprovalSeeder(BaseSeeder):
    """A three-stage drawing release, stage 1 answered and stage 2 open."""

    def __init__(self, stdout, style, tenant, scale='small'):
        super().__init__(stdout, style, scale=scale)
        self.tenant = tenant

    def seed(self, users):
        from django.core.files.base import ContentFile
        from Tracker.services.core.approval import submit_approval_response
        from Tracker.services.core.documents import submit_document_for_approval

        self.log("Seeding a sequential approval in stages...")
        by_email = (users or {}).get('by_email', {})
        jordan = by_email.get('jordan.eng@demo.ambac.com')
        jennifer = by_email.get('jennifer.mgr@demo.ambac.com')
        lisa = by_email.get('lisa.docs@demo.ambac.com')
        qa_group = TenantGroup.objects.filter(tenant=self.tenant, name=QA_GROUP).first()
        if not all((jordan, jennifer, lisa, qa_group)):
            self.log("  Warning: a user or the QA Manager group is missing; skipping.",
                     warning=True)
            return {}

        with transaction.atomic():
            # Not the default: the starter DOCUMENT_RELEASE template stays the one every
            # other document type uses.
            template, _ = ApprovalTemplate.objects.update_or_create(
                tenant=self.tenant, template_name=TEMPLATE_NAME,
                defaults={
                    'approval_type': Approval_Type.DOCUMENT_RELEASE,
                    'is_default': False,
                    'approval_flow_type': ApprovalFlows.ALL_REQUIRED,
                    'delegation_policy': ApprovalDelegation.DISABLED,
                    'approval_sequence': SequenceTypes.SEQUENTIAL,
                    'approval_stages': [
                        {'users': [jordan.id], 'groups': []},
                        {'users': [], 'groups': [str(qa_group.id)]},
                        {'users': [jennifer.id], 'groups': []},
                    ],
                    'allow_self_approval': False,
                    'default_due_days': 5,
                    'escalation_days': None,
                    'default_threshold': None,
                    'auto_assign_by_role': None,
                    'escalate_to': None,
                    'deactivated_at': None,
                },
            )
            doc_type, _ = DocumentType.objects.update_or_create(
                tenant=self.tenant, code=DOC_TYPE['code'],
                defaults={'name': DOC_TYPE['name'], 'description': DOC_TYPE['description'],
                          'requires_approval': True, 'approval_template': template,
                          'default_review_period_days': 365,
                          'default_retention_days': 2555},
            )

            doc = Documents.objects.filter(tenant=self.tenant, file_name=DRAWING_FILE).first()
            if doc is None:
                doc = Documents(
                    tenant=self.tenant, file_name=DRAWING_FILE, document_type=doc_type,
                    status='DRAFT', uploaded_by=lisa,
                    change_justification='Rev B: bore entry chamfered 0.2 x 45° to remove '
                                         'the burr seen at Body Inspection.',
                )
                doc.file.save(f"{DRAWING_FILE}.txt",
                              ContentFile(b"Body bore detail, rev B: bore entry chamfer "
                                          b"0.2 x 45 deg.\n"),
                              save=False)
                doc.save()
            if doc.status != 'DRAFT':
                self.log(f"  {DRAWING_FILE} already submitted; leaving it as it is.")
                return {'template': template, 'document': doc}

            request = submit_document_for_approval(doc, lisa)
            submit_approval_response(
                request, jordan, ApprovalDecision.APPROVED,
                comments='Chamfer is within the drawing envelope; no fit change.',
                signature_meaning='Approved as the responsible engineer',
                decided_at=timezone.now() - timedelta(hours=2),
            )
            request.refresh_from_db()

        self.log(f"  {request.approval_number}: {DRAWING_FILE} — stage 1 (Jordan) approved, "
                 f"stage 2 ({QA_GROUP}) open, stage 3 (Jennifer) waiting")
        return {'template': template, 'document': doc, 'request': request}

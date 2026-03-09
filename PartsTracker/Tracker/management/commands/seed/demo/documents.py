"""
Demo documents seeder with preset work instructions.

Creates:
- WI-1001: Injector Disassembly (released)
- WI-1002: Nozzle Inspection (released, updated per CAPA)
- WI-1003: Flow Test Procedure (pending approval)

IMPORTANT:
- All enum values MUST be UPPERCASE (e.g., 'DRAFT', 'RELEASED', 'APPROVED')
- All fields MUST be EXPLICITLY set - do NOT rely on model defaults
- Use update_or_create instead of get_or_create for objects with enum fields
"""

from datetime import timedelta
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from Tracker.models import (
    Documents, DocumentType, ApprovalRequest, ApprovalResponse, ApprovalTemplate,
    Approval_Type, Approval_Status_Type, ApprovalFlows, ApprovalDelegation, SequenceTypes,
    ApprovalDecision, User, ClassificationLevel,
)

from ..base import BaseSeeder


# Demo document types
DEMO_DOCUMENT_TYPES = [
    {'name': 'Work Instruction', 'code': 'WI', 'description': 'Standard operating procedures'},
    {'name': 'RCA Report', 'code': 'RCA', 'description': 'Root cause analysis reports'},
    {'name': 'Customer PO', 'code': 'PO', 'description': 'Customer purchase orders'},
]

# Demo approval templates
DEMO_APPROVAL_TEMPLATES = [
    {
        'template_name': 'Document Release',
        'approval_type': 'DOCUMENT_RELEASE',
        'approval_flow_type': 'ALL_REQUIRED',
        'delegation_policy': 'OPTIONAL',
        'approval_sequence': 'PARALLEL',
        'allow_self_approval': False,
        'default_due_days': 5,
        'escalation_days': 3,
        'auto_assign_by_role': 'QA_Manager',
    },
    {
        'template_name': 'Engineering Change',
        'approval_type': 'ECO',
        'approval_flow_type': 'ALL_REQUIRED',
        'delegation_policy': 'DISABLED',
        'approval_sequence': 'SEQUENTIAL',
        'allow_self_approval': False,
        'default_due_days': 7,
        'escalation_days': 5,
        'auto_assign_by_role': 'Production_Manager',
    },
    {
        'template_name': 'CAPA Closure',
        'approval_type': 'CAPA_MAJOR',
        'approval_flow_type': 'THRESHOLD',
        'delegation_policy': 'OPTIONAL',
        'approval_sequence': 'PARALLEL',
        'allow_self_approval': False,
        'default_due_days': 3,
        'escalation_days': 2,
        'default_threshold': 2,
        'auto_assign_by_role': 'QA_Manager',
    },
]

# Demo documents matching DEMO_DATA_SYSTEM.md
# Note: Documents model uses file_name (not title), and doesn't have version/content fields.
# We store metadata in change_justification field for demo purposes.
DEMO_DOCUMENTS = [
    {
        'file_name': 'WI-1001 Injector Disassembly v3.2',
        'type': 'Work Instruction',
        'status': 'RELEASED',
        'created_days_ago': 180,
        'effective_days_ago': 90,
        'change_justification': 'Rev 3.2: Updated torque spec per calibration findings',
        'approval_request': {
            'requested_by': 'lisa.docs@demo.ambac.com',
            'approvers': ['maria.qa@demo.ambac.com', 'jennifer.mgr@demo.ambac.com'],
            'status': 'APPROVED',
            'approved_days_ago': 92,
            'responses': [
                {'approver': 'maria.qa@demo.ambac.com', 'decision': 'APPROVED', 'comments': 'Torque spec update verified.'},
                {'approver': 'jennifer.mgr@demo.ambac.com', 'decision': 'APPROVED', 'comments': 'Approved for release.'},
            ],
        },
    },
    {
        'file_name': 'WI-1002 Nozzle Inspection v2.1',
        'type': 'Work Instruction',
        'status': 'RELEASED',
        'created_days_ago': 120,
        'effective_days_ago': 5,  # Recently updated per CAPA
        'change_justification': 'Rev 2.1: Updated spray angle tolerance per CAPA-2024-003',
        'approval_request': {
            'requested_by': 'lisa.docs@demo.ambac.com',
            'approvers': ['maria.qa@demo.ambac.com'],
            'status': 'APPROVED',
            'approved_days_ago': 6,
            'responses': [
                {'approver': 'maria.qa@demo.ambac.com', 'decision': 'APPROVED', 'comments': 'CAPA-2024-003 corrective action implemented.'},
            ],
        },
    },
    {
        'file_name': 'WI-1003 Flow Test Procedure v4.0',
        'type': 'Work Instruction',
        'status': 'UNDER_REVIEW',  # Pending approval - using valid status
        'created_days_ago': 60,
        'submitted_days_ago': 2,
        'change_justification': 'Rev 4.0: Tightened flow rate tolerance per CAPA-2024-003',
        'approval_request': {
            'requested_by': 'lisa.docs@demo.ambac.com',
            'approvers': ['maria.qa@demo.ambac.com', 'jennifer.mgr@demo.ambac.com'],
            'status': 'PENDING',
        },
    },
]


class DemoDocumentsSeeder(BaseSeeder):
    """
    Creates preset documents with approval workflows.

    All data is deterministic - same result every time.
    """

    def __init__(self, stdout, style, tenant, scale='small'):
        super().__init__(stdout, style, scale=scale)
        self.tenant = tenant
        self.today = timezone.now()

    def seed(self, users):
        """
        Create all demo documents.

        Args:
            users: dict with user lists including by_email lookup

        Returns:
            dict with created documents and approval requests
        """
        self.log("Creating demo documents...")

        result = {
            'document_types': [],
            'approval_templates': [],
            'documents': [],
            'approval_requests': [],
            'approval_responses': [],
        }

        # Get user lookup
        user_map = users.get('by_email', {})

        # Create document types
        result['document_types'] = self._create_document_types()

        # Create approval templates
        result['approval_templates'] = self._create_approval_templates(user_map)

        # Get document type lookup
        type_map = {dt.name: dt for dt in result['document_types']}

        # Create documents
        for doc_data in DEMO_DOCUMENTS:
            doc_type = type_map.get(doc_data['type'])
            doc = self._create_document(doc_data, doc_type, user_map)
            result['documents'].append(doc)

            # Create approval request if specified
            if doc_data.get('approval_request'):
                ar, responses = self._create_approval_request(
                    doc_data['approval_request'],
                    doc,
                    user_map
                )
                if ar:
                    result['approval_requests'].append(ar)
                    result['approval_responses'].extend(responses)

        self.log(f"  Created {len(result['approval_templates'])} approval templates")
        self.log(f"  Created {len(result['documents'])} documents")
        self.log(f"  Created {len(result['approval_requests'])} approval requests")
        self.log(f"  Created {len(result['approval_responses'])} approval responses")

        return result

    def _create_document_types(self):
        """Create document types.

        DocumentType model fields:
        - name: CharField
        - code: CharField
        - description: TextField
        - requires_approval: BooleanField
        - approval_template: ForeignKey to ApprovalTemplate (nullable)
        - default_review_period_days: PositiveIntegerField (nullable)
        - default_retention_days: PositiveIntegerField (nullable)

        IMPORTANT: All fields MUST be EXPLICITLY set - do NOT rely on model defaults.
        """
        doc_types = []

        for dt_data in DEMO_DOCUMENT_TYPES:
            # Use update_or_create - EXPLICITLY set ALL fields
            dt, _ = DocumentType.objects.update_or_create(
                tenant=self.tenant,
                code=dt_data['code'],
                defaults={
                    'name': dt_data['name'],
                    'description': dt_data['description'],
                    # EXPLICITLY set fields - do NOT rely on model defaults
                    'requires_approval': True,  # Work instructions require approval
                    'approval_template': None,  # Will use default DOCUMENT_RELEASE
                    'default_review_period_days': 365,  # 1 year review period
                    'default_retention_days': 2555,  # 7 years retention (compliance)
                }
            )
            doc_types.append(dt)

        return doc_types

    def _create_approval_templates(self, user_map):
        """Create approval templates.

        ApprovalTemplate model fields:
        - template_name: CharField(max_length=100)
        - approval_type: CharField (choices from Approval_Type) - MUST be UPPERCASE
        - default_approvers: ManyToManyField to User
        - default_groups: ManyToManyField to TenantGroup
        - default_threshold: IntegerField (nullable)
        - auto_assign_by_role: CharField (nullable)
        - approval_flow_type: CharField (choices from ApprovalFlows) - MUST be UPPERCASE
        - delegation_policy: CharField (choices from ApprovalDelegation) - MUST be UPPERCASE
        - approval_sequence: CharField (choices from SequenceTypes) - MUST be UPPERCASE
        - allow_self_approval: BooleanField
        - default_due_days: IntegerField
        - escalation_days: IntegerField (nullable)
        - escalate_to: ForeignKey to User (nullable)
        - deactivated_at: DateTimeField (nullable, null = active)

        Unique constraints:
        - (tenant, template_name)
        - (tenant, approval_type)

        IMPORTANT: All enum values MUST be UPPERCASE. All fields MUST be EXPLICITLY set.
        """
        templates = []

        for template_data in DEMO_APPROVAL_TEMPLATES:
            # Map string choices to enum values - ensure UPPERCASE
            approval_type_str = template_data['approval_type'].upper()
            approval_flow_str = template_data['approval_flow_type'].upper()
            delegation_str = template_data['delegation_policy'].upper()
            sequence_str = template_data['approval_sequence'].upper()

            approval_type = getattr(Approval_Type, approval_type_str)
            approval_flow_type = getattr(ApprovalFlows, approval_flow_str)
            delegation_policy = getattr(ApprovalDelegation, delegation_str)
            approval_sequence = getattr(SequenceTypes, sequence_str)

            # Use update_or_create with approval_type for lookup since (tenant, approval_type) is unique
            # EXPLICITLY set ALL fields - do NOT rely on model defaults
            template, _ = ApprovalTemplate.objects.update_or_create(
                tenant=self.tenant,
                approval_type=approval_type,  # UPPERCASE enum
                defaults={
                    'template_name': template_data['template_name'],
                    'approval_flow_type': approval_flow_type,  # UPPERCASE enum
                    'delegation_policy': delegation_policy,  # UPPERCASE enum
                    'approval_sequence': approval_sequence,  # UPPERCASE enum
                    # Boolean fields - EXPLICITLY set
                    'allow_self_approval': template_data.get('allow_self_approval', False),
                    # Integer fields - EXPLICITLY set
                    'default_due_days': template_data.get('default_due_days', 5),
                    'escalation_days': template_data.get('escalation_days'),
                    'default_threshold': template_data.get('default_threshold'),
                    # String fields - EXPLICITLY set
                    'auto_assign_by_role': template_data.get('auto_assign_by_role'),
                    # Nullable fields - EXPLICITLY set to None if not provided
                    'escalate_to': None,
                    'deactivated_at': None,
                }
            )
            templates.append(template)

        return templates

    def _create_document(self, doc_data, doc_type, user_map):
        """Create a document.

        Documents model fields:
        - file_name: CharField(max_length=50) - required
        - file: FileField - REQUIRED (not nullable)
        - document_type: ForeignKey to DocumentType (optional)
        - status: CharField choices (DRAFT, UNDER_REVIEW, APPROVED, RELEASED, OBSOLETE) - MUST be UPPERCASE
        - change_justification: TextField (for revision notes)
        - effective_date: DateField (when document became effective)
        - review_date: DateField (next review date)
        - uploaded_by: ForeignKey to User (optional - can be null)
        - classification: CharField choices - MUST be UPPERCASE
        - is_image: BooleanField
        - ai_readable: BooleanField
        - itar_controlled: BooleanField
        - eccn: CharField
        - export_control_reason: CharField

        IMPORTANT: All enum values MUST be UPPERCASE. All fields MUST be EXPLICITLY set.
        """
        from django.core.files.base import ContentFile

        # Ensure status is UPPERCASE
        status = doc_data['status'].upper()

        # Get the user who uploaded the document (lisa.docs by default)
        uploaded_by = user_map.get('lisa.docs@demo.ambac.com')

        # EXPLICITLY set ALL fields - do NOT rely on model defaults
        defaults = {
            'document_type': doc_type,
            'status': status,  # UPPERCASE enum value
            'change_justification': doc_data.get('change_justification', ''),
            # Classification - UPPERCASE enum value
            'classification': ClassificationLevel.INTERNAL,
            # Boolean fields - explicitly set
            'is_image': False,
            'ai_readable': False,
            # ITAR/Export control fields - explicitly set
            'itar_controlled': False,
            'eccn': '',
            'export_control_reason': '',
            # User who uploaded
            'uploaded_by': uploaded_by,
        }

        # Set effective_date if specified
        if doc_data.get('effective_days_ago'):
            defaults['effective_date'] = (self.today - timedelta(days=doc_data['effective_days_ago'])).date()
        else:
            defaults['effective_date'] = None

        # Set review_date (30 days after effective_date by default for released docs)
        if defaults.get('effective_date') and status == 'RELEASED':
            defaults['review_date'] = defaults['effective_date'] + timedelta(days=365)
        else:
            defaults['review_date'] = None

        # Set obsolete_date and retention_until (only for OBSOLETE status)
        defaults['obsolete_date'] = None
        defaults['retention_until'] = None

        # Note: Documents has no unique constraint on (tenant, file_name)
        # so update_or_create may not find existing records as expected.
        # We filter by file_name to avoid duplicates in demo data.
        doc = Documents.objects.filter(
            tenant=self.tenant,
            file_name=doc_data['file_name']
        ).first()

        if not doc:
            # Create placeholder file content for demo
            file_content = f"Demo document content for {doc_data['file_name']}\n\n"
            file_content += f"Status: {status}\n"
            file_content += f"Change Justification: {doc_data.get('change_justification', '')}\n"

            doc = Documents(
                tenant=self.tenant,
                file_name=doc_data['file_name'],
                **defaults
            )
            # Save file with .txt extension
            doc.file.save(
                f"{doc_data['file_name']}.txt",
                ContentFile(file_content.encode('utf-8')),
                save=False
            )
            doc.save()
        else:
            # Update existing document with ALL fields explicitly
            for key, value in defaults.items():
                setattr(doc, key, value)
            doc.save()

        return doc

    def _create_approval_request(self, ar_data, document, user_map):
        """Create an approval request for a document.

        ApprovalRequest model fields:
        - approval_number: CharField (auto-generated APR-YYYY-####)
        - content_type: ForeignKey to ContentType
        - object_id: CharField (for GenericForeignKey)
        - approval_type: CharField (choices from Approval_Type) - MUST be UPPERCASE
        - status: CharField (choices from Approval_Status_Type) - MUST be UPPERCASE
        - requested_by: ForeignKey to User
        - requested_at: DateTimeField (auto_now_add)
        - reason: TextField

        Unique constraint: (tenant, approval_number)

        IMPORTANT: All enum values MUST be UPPERCASE. All fields MUST be EXPLICITLY set.

        Returns: tuple (ApprovalRequest, list of ApprovalResponse)
        """
        requested_by = user_map.get(ar_data['requested_by'])

        # Determine status - ensure UPPERCASE
        status_str = ar_data.get('status', 'PENDING').upper()
        status = getattr(Approval_Status_Type, status_str, Approval_Status_Type.PENDING)

        # Get content type for Documents
        doc_content_type = ContentType.objects.get_for_model(Documents)

        # Check if approval request already exists for this document
        # (use content_type + object_id to find existing)
        ar = ApprovalRequest.objects.filter(
            tenant=self.tenant,
            content_type=doc_content_type,
            object_id=str(document.id)
        ).first()

        if not ar:
            # Generate approval number only for new requests
            approval_number = ApprovalRequest.generate_approval_number(self.tenant)

            # Create with ALL fields EXPLICITLY set
            ar = ApprovalRequest.objects.create(
                tenant=self.tenant,
                approval_number=approval_number,
                content_type=doc_content_type,
                object_id=str(document.id),
                approval_type=Approval_Type.DOCUMENT_RELEASE,  # UPPERCASE enum
                requested_by=requested_by,
                status=status,  # UPPERCASE enum
                reason=f'Document release approval for {document.file_name}',
            )
        else:
            # Update existing approval request with ALL fields EXPLICITLY
            ar.approval_type = Approval_Type.DOCUMENT_RELEASE  # UPPERCASE enum
            ar.requested_by = requested_by
            ar.status = status  # UPPERCASE enum
            ar.reason = f'Document release approval for {document.file_name}'
            ar.save()

        # Add approvers if specified
        if ar_data.get('approvers'):
            for approver_email in ar_data['approvers']:
                approver = user_map.get(approver_email)
                if approver:
                    ar.add_approver(approver, is_required=True)

        # Create approval responses if specified
        responses = []
        if ar_data.get('responses'):
            for resp_data in ar_data['responses']:
                approver = user_map.get(resp_data['approver'])
                if approver:
                    # Ensure decision is UPPERCASE
                    decision_str = resp_data['decision'].upper()
                    decision = getattr(ApprovalDecision, decision_str, ApprovalDecision.APPROVED)

                    # Use update_or_create since (approval_request, approver) is unique
                    # EXPLICITLY set ALL fields
                    response, _ = ApprovalResponse.objects.update_or_create(
                        tenant=self.tenant,
                        approval_request=ar,
                        approver=approver,
                        defaults={
                            'decision': decision,  # UPPERCASE enum
                            'comments': resp_data.get('comments', ''),
                        }
                    )
                    responses.append(response)

        return ar, responses

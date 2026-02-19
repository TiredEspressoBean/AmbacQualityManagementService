"""
Service for seeding default data (document types, approval templates).

This module provides the canonical definitions for default data and functions
to apply them. Used by both:
- Management commands (setup_document_types, setup_approval_templates)
- Post-migrate signal (apps.py)

Usage:
    from Tracker.services.defaults_service import (
        seed_document_types,
        seed_approval_templates,
        DOCUMENT_TYPES,
        APPROVAL_TEMPLATES,
    )
"""

import logging

from django.db import transaction

from Tracker.models import TenantGroup

logger = logging.getLogger(__name__)


# =============================================================================
# DOCUMENT TYPES - Canonical definitions
# =============================================================================

DOCUMENT_TYPES = [
    # Process Documentation
    {"code": "SOP", "name": "Standard Operating Procedure", "requires_approval": True,
     "description": "Company-level procedures defining how processes are performed"},
    {"code": "WI", "name": "Work Instruction", "requires_approval": True,
     "description": "Step-level instructions for specific manufacturing tasks"},
    {"code": "POL", "name": "Policy", "requires_approval": True,
     "description": "High-level organizational rules and guidelines"},
    {"code": "FRM", "name": "Form/Checklist", "requires_approval": True,
     "description": "Blank forms and checklist templates for quality records"},
    {"code": "CP", "name": "Control Plan", "requires_approval": True,
     "description": "Process control plans per IATF 16949 requirements"},

    # Technical Documentation
    {"code": "DWG", "name": "Drawing/Print", "requires_approval": True,
     "description": "Engineering drawings and prints with GD&T"},
    {"code": "SPEC", "name": "Specification", "requires_approval": True,
     "description": "Technical specifications and requirements documents"},
    {"code": "BOM", "name": "Bill of Materials", "requires_approval": True,
     "description": "Component and assembly lists"},
    {"code": "CAD", "name": "CAD Model", "requires_approval": False,
     "description": "3D/2D CAD source files (STEP, IGES, etc.)"},

    # Material & Supplier Records
    {"code": "MTR", "name": "Material Test Report", "requires_approval": False,
     "description": "Mill certificates and material certifications from suppliers"},
    {"code": "COC", "name": "Certificate of Conformance", "requires_approval": False,
     "description": "Supplier certificates of conformance for incoming materials"},
    {"code": "COA", "name": "Certificate of Analysis", "requires_approval": False,
     "description": "Chemical/material analysis certificates"},
    {"code": "SDS", "name": "Safety Data Sheet", "requires_approval": False,
     "description": "Material safety data sheets (MSDS/SDS)"},
    {"code": "POD", "name": "Proof of Delivery", "requires_approval": False,
     "description": "Shipping and receiving documentation"},

    # Quality Records (Generated)
    {"code": "IR", "name": "Inspection Report", "requires_approval": False,
     "description": "Quality inspection reports generated from inspections"},
    {"code": "TR", "name": "Test Report", "requires_approval": False,
     "description": "Test results and reports"},
    {"code": "NCR", "name": "Nonconformance Report", "requires_approval": False,
     "description": "Nonconformance documentation from dispositions"},

    # Disposition Documentation
    {"code": "CUST_APPR", "name": "Customer Approval Evidence", "requires_approval": False,
     "description": "Customer approval documentation for USE_AS_IS/REPAIR dispositions (emails, POs, faxes)"},
    {"code": "CONT_EVD", "name": "Containment Evidence", "requires_approval": False,
     "description": "Evidence of containment actions taken (photos, segregation tags, etc.)"},
    {"code": "CAR", "name": "Corrective Action Report", "requires_approval": True,
     "description": "Corrective action reports from CAPA system"},
    {"code": "8D", "name": "8D Report", "requires_approval": True,
     "description": "8D problem-solving reports from CAPA system"},
    {"code": "FAI", "name": "First Article Inspection", "requires_approval": True,
     "description": "AS9102 First Article Inspection reports (Forms 1, 2, 3)"},

    # Calibration & Equipment
    {"code": "CAL", "name": "Calibration Certificate", "requires_approval": False,
     "description": "Equipment calibration certificates from cal labs"},
    {"code": "EQM", "name": "Equipment Manual", "requires_approval": False,
     "description": "Equipment manuals and vendor documentation"},

    # Customer & Contract
    {"code": "PO", "name": "Purchase Order", "requires_approval": False,
     "description": "Customer purchase orders"},
    {"code": "CSPEC", "name": "Customer Specification", "requires_approval": False,
     "description": "Customer-specific requirements and specifications"},
    {"code": "NDA", "name": "Non-Disclosure Agreement", "requires_approval": True,
     "description": "Confidentiality and non-disclosure agreements"},
    {"code": "QA", "name": "Quality Agreement", "requires_approval": True,
     "description": "Supplier/customer quality agreements"},

    # Training & Compliance
    {"code": "TRN", "name": "Training Record", "requires_approval": False,
     "description": "Training completion records and certificates"},
    {"code": "CERT", "name": "Certification", "requires_approval": False,
     "description": "Company/facility certifications (ISO, Nadcap, etc.)"},

    # Industry-Specific (Aerospace/Auto)
    {"code": "PPAP", "name": "PPAP Submission", "requires_approval": True,
     "description": "Production Part Approval Process documentation (IATF 16949)"},
    {"code": "PSW", "name": "Part Submission Warrant", "requires_approval": True,
     "description": "PPAP Part Submission Warrant form"},
    {"code": "FMEA", "name": "FMEA", "requires_approval": True,
     "description": "Failure Mode and Effects Analysis documents"},
    {"code": "MSA", "name": "MSA Study", "requires_approval": False,
     "description": "Measurement System Analysis / Gage R&R studies"},
    {"code": "AAR", "name": "Appearance Approval Report", "requires_approval": True,
     "description": "PPAP Element 13 - color, grain, texture approval"},

    # Change Management
    {"code": "ECR", "name": "Engineering Change Request", "requires_approval": True,
     "description": "Request for engineering/design changes"},
    {"code": "ECO", "name": "Engineering Change Order", "requires_approval": True,
     "description": "Approved engineering change orders with effectivity"},

    # Supplier Management
    {"code": "SCAR", "name": "Supplier Corrective Action Request", "requires_approval": True,
     "description": "Corrective action requests issued to suppliers"},

    # General
    {"code": "OTH", "name": "Other", "requires_approval": False,
     "description": "Miscellaneous documents not fitting other categories"},
]


# =============================================================================
# APPROVAL TEMPLATES - Canonical definitions
# =============================================================================

APPROVAL_TEMPLATES = [
    {
        "template_name": "Document Release Approval",
        "approval_type": "DOCUMENT_RELEASE",
        "auto_assign_by_role": "QA_Manager",
        "approval_flow_type": "ALL_REQUIRED",
        "delegation_policy": "OPTIONAL",
        "approval_sequence": "PARALLEL",
        "allow_self_approval": False,
        "default_due_days": 5,
        "escalation_days": 3,
        "default_groups_names": ["QA_Manager", "Document_Controller"],
    },
    {
        "template_name": "Critical CAPA Approval",
        "approval_type": "CAPA_CRITICAL",
        "auto_assign_by_role": "Admin",
        "approval_flow_type": "ALL_REQUIRED",
        "delegation_policy": "DISABLED",
        "approval_sequence": "SEQUENTIAL",
        "allow_self_approval": False,
        "default_due_days": 3,
        "escalation_days": 1,
        "default_groups_names": ["QA_Manager", "Production_Manager", "Admin"],
    },
    {
        "template_name": "Major CAPA Approval",
        "approval_type": "CAPA_MAJOR",
        "auto_assign_by_role": "QA_Manager",
        "approval_flow_type": "ALL_REQUIRED",
        "delegation_policy": "OPTIONAL",
        "approval_sequence": "PARALLEL",
        "allow_self_approval": False,
        "default_due_days": 5,
        "escalation_days": 2,
        "default_groups_names": ["QA_Manager", "Production_Manager"],
    },
    {
        "template_name": "Engineering Change Order Approval",
        "approval_type": "ECO",
        "auto_assign_by_role": "Production_Manager",
        "approval_flow_type": "ALL_REQUIRED",
        "delegation_policy": "OPTIONAL",
        "approval_sequence": "SEQUENTIAL",
        "allow_self_approval": False,
        "default_due_days": 7,
        "escalation_days": 3,
        "default_groups_names": ["QA_Manager", "Production_Manager"],
    },
    {
        "template_name": "Training Certification Approval",
        "approval_type": "TRAINING_CERT",
        "auto_assign_by_role": "Production_Manager",
        "approval_flow_type": "ANY",
        "delegation_policy": "OPTIONAL",
        "approval_sequence": "PARALLEL",
        "allow_self_approval": False,
        "default_due_days": 10,
        "escalation_days": 5,
        "default_groups_names": ["Production_Manager"],
    },
    {
        "template_name": "Process Approval",
        "approval_type": "PROCESS_APPROVAL",
        "auto_assign_by_role": "QA_Manager",
        "approval_flow_type": "ALL_REQUIRED",
        "delegation_policy": "OPTIONAL",
        "approval_sequence": "SEQUENTIAL",
        "allow_self_approval": False,
        "default_due_days": 7,
        "escalation_days": 3,
        "default_groups_names": ["QA_Manager", "Production_Manager"],
        "description": "Approval for manufacturing process definitions before production use",
    },
]


# =============================================================================
# SEEDING FUNCTIONS
# =============================================================================

def seed_document_types(tenant=None, update_existing: bool = False) -> dict:
    """
    Seed default document types for a tenant.

    Args:
        tenant: Tenant instance. If None, seeds without tenant (legacy mode).
        update_existing: If True, update existing records with new values.

    Returns:
        dict with 'created', 'updated', 'skipped', 'errors' counts and lists
    """
    from Tracker.models import DocumentType

    results = {
        'created': 0,
        'updated': 0,
        'skipped': 0,
        'errors': [],
        'details': [],
    }

    with transaction.atomic():
        for dt in DOCUMENT_TYPES:
            try:
                # Filter by tenant if provided
                filter_kwargs = {'code': dt["code"]}
                if tenant:
                    filter_kwargs['tenant'] = tenant

                existing = DocumentType.objects.filter(**filter_kwargs).first()

                if existing:
                    if update_existing:
                        for key, value in dt.items():
                            setattr(existing, key, value)
                        existing.save()
                        results['updated'] += 1
                        results['details'].append(f"Updated: {dt['code']}")
                    else:
                        results['skipped'] += 1
                else:
                    create_data = dict(dt)
                    if tenant:
                        create_data['tenant'] = tenant
                    DocumentType.objects.create(**create_data)
                    results['created'] += 1
                    results['details'].append(f"Created: {dt['code']}")

            except Exception as e:
                results['errors'].append(f"{dt['code']}: {str(e)}")

    return results


def seed_approval_templates(tenant=None, update_existing: bool = False) -> dict:
    """
    Seed default approval templates for a tenant.

    Args:
        tenant: Tenant instance. If None, seeds without tenant (legacy mode).
        update_existing: If True, update existing records with new values.

    Returns:
        dict with 'created', 'updated', 'skipped', 'errors' counts and lists
    """
    from Tracker.models import ApprovalTemplate

    results = {
        'created': 0,
        'updated': 0,
        'skipped': 0,
        'errors': [],
        'details': [],
    }

    with transaction.atomic():
        for t in APPROVAL_TEMPLATES:
            try:
                # Extract M2M field before processing
                group_names = t.get("default_groups_names", [])

                # Filter by tenant if provided
                filter_kwargs = {'approval_type': t["approval_type"]}
                if tenant:
                    filter_kwargs['tenant'] = tenant

                existing = ApprovalTemplate.objects.filter(**filter_kwargs).first()

                if existing:
                    if update_existing:
                        for key, value in t.items():
                            if key not in ("default_groups_names", "description"):
                                setattr(existing, key, value)
                        existing.save()

                        # Update M2M (TenantGroup requires tenant filtering)
                        if tenant and group_names:
                            groups = TenantGroup.objects.filter(tenant=tenant, name__in=group_names)
                            existing.default_groups.set(groups)

                        results['updated'] += 1
                        results['details'].append(f"Updated: {t['approval_type']}")
                    else:
                        results['skipped'] += 1
                else:
                    # Create without M2M field and description (not a model field)
                    create_data = {k: v for k, v in t.items() if k not in ("default_groups_names", "description")}
                    if tenant:
                        create_data['tenant'] = tenant
                    template = ApprovalTemplate.objects.create(**create_data)

                    # Set M2M (TenantGroup requires tenant filtering)
                    if tenant and group_names:
                        groups = TenantGroup.objects.filter(tenant=tenant, name__in=group_names)
                        template.default_groups.set(groups)

                    results['created'] += 1
                    results['details'].append(f"Created: {t['approval_type']}")

            except Exception as e:
                results['errors'].append(f"{t.get('approval_type', 'unknown')}: {str(e)}")

    return results


def seed_all_defaults(tenant=None, update_existing: bool = False) -> dict:
    """
    Seed all default data for a tenant.

    Args:
        tenant: Tenant instance. If None, seeds without tenant (legacy mode).
        update_existing: If True, update existing records with new values.

    Returns:
        dict with results for each category
    """
    return {
        'document_types': seed_document_types(tenant, update_existing),
        'approval_templates': seed_approval_templates(tenant, update_existing),
    }


def seed_reference_data_for_tenant(tenant) -> dict:
    """
    Seed all reference data for a new tenant.

    This is the main entry point called when a tenant is created.
    Includes: document types, approval templates, and any future reference data.

    Args:
        tenant: Tenant instance (required)

    Returns:
        dict with results for each category
    """
    if not tenant:
        raise ValueError("Tenant is required for reference data seeding")

    results = {
        'document_types': seed_document_types(tenant=tenant, update_existing=False),
        'approval_templates': seed_approval_templates(tenant=tenant, update_existing=False),
    }

    # Log summary
    total_created = sum(r.get('created', 0) for r in results.values())
    logger.info(f"Seeded {total_created} reference data records for tenant {tenant.slug}")

    return results

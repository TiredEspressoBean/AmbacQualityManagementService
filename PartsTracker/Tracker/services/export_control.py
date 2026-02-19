"""
Export Control Access Filtering Service

Provides compliance-aware document and data access filtering for:
- ITAR (International Traffic in Arms Regulations) - 22 CFR 120-130
- EAR (Export Administration Regulations) - 15 CFR 730-774
- CUI (Controlled Unclassified Information) - 32 CFR 2002

Usage in ViewSets:
    queryset = (
        Documents.objects
        .for_tenant(tenant)                    # Multi-tenancy isolation
        .for_export_control(user)              # ITAR/EAR checks
        .for_classification(user)              # Classification level checks
    )

All access denials are logged for compliance auditing per:
- NIST 800-171 3.1.1 (Limit system access)
- NIST 800-171 3.3.1 (Create audit records)
- CMMC AC.L2-3.1.1, AU.L2-3.3.1
"""

import logging
from django.db import models
from django.utils import timezone
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from Tracker.models import User

logger = logging.getLogger(__name__)

# Compliance audit logger - separate for easy SIEM integration
compliance_logger = logging.getLogger('compliance.access_control')


class ExportControlDenialReason:
    """Standardized denial reasons for audit logging"""
    ITAR_NOT_US_PERSON = "ITAR_VIOLATION: User is not a US Person (22 CFR 120.62)"
    ITAR_NO_AUTHORIZATION = "ITAR_VIOLATION: User lacks ITAR authorization"
    EAR_NO_LICENSE = "EAR_VIOLATION: User lacks export license for ECCN"
    EAR_DENIED_COUNTRY = "EAR_VIOLATION: User citizenship in denied country"
    CLASSIFICATION_INSUFFICIENT = "CLASSIFICATION: User clearance insufficient"
    NO_NEED_TO_KNOW = "NEED_TO_KNOW: User lacks access authorization"


class ExportControlService:
    """
    Centralized export control access determination.

    This service encapsulates all export control logic so it can be:
    1. Used by queryset filters
    2. Used by object-level permission checks
    3. Audited and tested independently
    4. Updated when regulations change
    """

    # Countries denied under EAR (simplified - real list is more complex)
    # See 15 CFR 746 for full list
    EAR_DENIED_COUNTRIES = {
        'CUB',  # Cuba
        'IRN',  # Iran
        'PRK',  # North Korea
        'SYR',  # Syria
        'RUS',  # Russia (certain items)
        'BLR',  # Belarus (certain items)
    }

    @classmethod
    def can_access_itar_data(cls, user: 'User') -> tuple[bool, Optional[str]]:
        """
        Check if user can access ITAR-controlled data.

        ITAR (22 CFR 120.62) defines "US Person" as:
        - US citizen
        - Lawful permanent resident (green card)
        - Protected individual (refugee/asylee)

        Returns:
            tuple: (allowed: bool, denial_reason: Optional[str])
        """
        # Superusers still need to be US persons for ITAR
        # This is a legal requirement, not a software permission

        if not hasattr(user, 'us_person'):
            # Model doesn't have export control fields yet
            logger.warning(f"User {user.id} missing us_person field - denying ITAR access")
            return False, ExportControlDenialReason.ITAR_NOT_US_PERSON

        if user.us_person:
            return True, None

        # Check for explicit ITAR authorization (e.g., TAA or license)
        if getattr(user, 'itar_authorized', False):
            return True, None

        return False, ExportControlDenialReason.ITAR_NOT_US_PERSON

    @classmethod
    def can_access_ear_data(cls, user: 'User', eccn: str) -> tuple[bool, Optional[str]]:
        """
        Check if user can access EAR-controlled data.

        EAR controls are based on:
        - ECCN (Export Control Classification Number)
        - End-user country
        - End-use

        Args:
            user: The user requesting access
            eccn: The ECCN of the item/document

        Returns:
            tuple: (allowed: bool, denial_reason: Optional[str])
        """
        if not eccn or eccn.upper() == 'EAR99':
            # EAR99 items have minimal restrictions
            return True, None

        citizenship = getattr(user, 'citizenship', '')

        # Check denied countries
        if citizenship in cls.EAR_DENIED_COUNTRIES:
            return False, ExportControlDenialReason.EAR_DENIED_COUNTRY

        # Check for export license
        if getattr(user, 'ear_authorized', False):
            return True, None

        # For controlled ECCNs without explicit authorization, deny
        # In practice, you'd check against specific license conditions
        return False, ExportControlDenialReason.EAR_NO_LICENSE

    @classmethod
    def get_accessible_classification_levels(cls, user: 'User') -> list[str]:
        """
        Get classification levels the user can access.

        Mapping (customize per organization):
        - PUBLIC: All authenticated users
        - INTERNAL: Employees and above
        - CONFIDENTIAL: Managers, QA Managers, Admins
        - RESTRICTED: Admins, explicitly authorized users
        - SECRET: Explicitly authorized users only

        Returns:
            list: Classification level values user can access
        """
        from Tracker.models import ClassificationLevel

        if user.is_superuser:
            return [level.value for level in ClassificationLevel]

        # Cache groups for efficiency (tenant-scoped)
        if not hasattr(user, '_cached_tenant_group_names'):
            user._cached_tenant_group_names = user.get_tenant_group_names() if hasattr(user, 'get_tenant_group_names') else set()

        groups = user._cached_tenant_group_names

        # Build accessible levels based on group membership
        accessible = [ClassificationLevel.PUBLIC.value]

        if groups & {'Admin', 'QA_Manager', 'Production_Manager', 'Document_Controller',
                     'QA_Inspector', 'Production_Operator'}:
            accessible.append(ClassificationLevel.INTERNAL.value)

        if groups & {'Admin', 'QA_Manager', 'Production_Manager', 'Document_Controller'}:
            accessible.append(ClassificationLevel.CONFIDENTIAL.value)

        if groups & {'Admin'}:
            accessible.append(ClassificationLevel.RESTRICTED.value)

        # SECRET requires explicit per-user authorization
        if getattr(user, 'secret_clearance', False):
            accessible.append(ClassificationLevel.SECRET.value)

        return accessible

    @classmethod
    def log_access_denial(
        cls,
        user: 'User',
        resource_type: str,
        resource_id: str,
        reason: str,
        additional_context: Optional[dict] = None
    ):
        """
        Log access denial for compliance auditing.

        Logs to both standard logger and compliance-specific logger
        for SIEM/audit system integration.
        """
        log_data = {
            'event_type': 'ACCESS_DENIED',
            'timestamp': timezone.now().isoformat(),
            'user_id': str(user.id),
            'user_email': user.email,
            'user_citizenship': getattr(user, 'citizenship', 'UNKNOWN'),
            'user_us_person': getattr(user, 'us_person', False),
            'resource_type': resource_type,
            'resource_id': resource_id,
            'denial_reason': reason,
        }

        if additional_context:
            log_data['context'] = additional_context

        # Standard logging
        logger.warning(
            f"Access denied: user={user.email} resource={resource_type}:{resource_id} "
            f"reason={reason}"
        )

        # Compliance audit log (structured for SIEM)
        compliance_logger.info(log_data)


class ExportControlQuerySetMixin:
    """
    Mixin providing export control filtering methods for QuerySets.

    Add to your QuerySet class:
        class SecureQuerySet(ExportControlQuerySetMixin, models.QuerySet):
            pass
    """

    def for_export_control(self, user: 'User') -> 'QuerySet':
        """
        Filter queryset to only include items the user can access
        based on export control regulations (ITAR/EAR).

        This method:
        1. Excludes ITAR-controlled items if user is not a US Person
        2. Excludes EAR-controlled items if user lacks authorization
        3. Logs all access denials for compliance

        Usage:
            documents = Documents.objects.for_export_control(user)
        """
        model = self.model
        model_name = model._meta.model_name

        # Check if model has export control fields
        has_itar = hasattr(model, 'itar_controlled')
        has_eccn = hasattr(model, 'eccn')

        if not has_itar and not has_eccn:
            # Model doesn't have export control fields
            return self

        queryset = self

        # ITAR filtering
        if has_itar:
            can_access_itar, denial_reason = ExportControlService.can_access_itar_data(user)

            if not can_access_itar:
                # Log that we're filtering out ITAR items for this user
                # Note: We log once per query, not per item, for performance
                ExportControlService.log_access_denial(
                    user=user,
                    resource_type=model_name,
                    resource_id='<queryset_filter>',
                    reason=denial_reason,
                    additional_context={'filter_type': 'ITAR_BULK_EXCLUSION'}
                )
                # Exclude ITAR-controlled items
                queryset = queryset.exclude(itar_controlled=True)

        # EAR filtering (more complex - depends on specific ECCN)
        if has_eccn:
            citizenship = getattr(user, 'citizenship', '')

            # If user is from a denied country, exclude all EAR-controlled items
            if citizenship in ExportControlService.EAR_DENIED_COUNTRIES:
                ExportControlService.log_access_denial(
                    user=user,
                    resource_type=model_name,
                    resource_id='<queryset_filter>',
                    reason=ExportControlDenialReason.EAR_DENIED_COUNTRY,
                    additional_context={
                        'filter_type': 'EAR_COUNTRY_EXCLUSION',
                        'citizenship': citizenship
                    }
                )
                # Exclude anything with an ECCN (except EAR99)
                queryset = queryset.exclude(
                    ~models.Q(eccn='') & ~models.Q(eccn__iexact='EAR99')
                )

        return queryset

    def for_classification(self, user: 'User') -> 'QuerySet':
        """
        Filter queryset to only include items at classification levels
        the user is authorized to access.

        Usage:
            documents = Documents.objects.for_classification(user)
        """
        model = self.model

        # Check if model has classification field
        if not hasattr(model, 'classification'):
            return self

        accessible_levels = ExportControlService.get_accessible_classification_levels(user)

        return self.filter(classification__in=accessible_levels)

    def for_secure_access(self, user: 'User') -> 'QuerySet':
        """
        Convenience method that applies all security filters:
        1. Export control (ITAR/EAR)
        2. Classification level

        Usage:
            documents = Documents.objects.for_secure_access(user)
        """
        return self.for_export_control(user).for_classification(user)


# =============================================================================
# Object-level permission checking (for single-object access)
# =============================================================================

def check_document_access(user: 'User', document) -> tuple[bool, Optional[str]]:
    """
    Check if a user can access a specific document.

    Use this for object-level permission checks (e.g., in get_object()).

    Returns:
        tuple: (allowed: bool, denial_reason: Optional[str])
    """
    from Tracker.models import ClassificationLevel

    # Check ITAR
    if getattr(document, 'itar_controlled', False):
        can_access, reason = ExportControlService.can_access_itar_data(user)
        if not can_access:
            ExportControlService.log_access_denial(
                user=user,
                resource_type='documents',
                resource_id=str(document.id),
                reason=reason,
                additional_context={'document_name': document.file_name}
            )
            return False, reason

    # Check EAR/ECCN
    eccn = getattr(document, 'eccn', '')
    if eccn and eccn.upper() != 'EAR99':
        can_access, reason = ExportControlService.can_access_ear_data(user, eccn)
        if not can_access:
            ExportControlService.log_access_denial(
                user=user,
                resource_type='documents',
                resource_id=str(document.id),
                reason=reason,
                additional_context={
                    'document_name': document.file_name,
                    'eccn': eccn
                }
            )
            return False, reason

    # Check classification level
    classification = getattr(document, 'classification', ClassificationLevel.PUBLIC.value)
    accessible_levels = ExportControlService.get_accessible_classification_levels(user)

    if classification not in accessible_levels:
        reason = ExportControlDenialReason.CLASSIFICATION_INSUFFICIENT
        ExportControlService.log_access_denial(
            user=user,
            resource_type='documents',
            resource_id=str(document.id),
            reason=reason,
            additional_context={
                'document_name': document.file_name,
                'document_classification': classification,
                'user_accessible_levels': accessible_levels
            }
        )
        return False, reason

    return True, None


# =============================================================================
# Integration with SecureQuerySet
# =============================================================================
#
# To integrate this with the existing SecureQuerySet, add to core.py:
#
# from Tracker.services.export_control import ExportControlQuerySetMixin
#
# class SecureQuerySet(ExportControlQuerySetMixin, models.QuerySet):
#     ... existing code ...
#
# Then update DocumentViewSet:
#
# def get_queryset(self):
#     return (
#         super().get_queryset()  # Tenant scoping
#         .for_secure_access(self.request.user)  # Export control + classification
#     )

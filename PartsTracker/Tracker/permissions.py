"""
Declarative Permission Structure for PartsTracker.

This is the single source of truth for all group permissions.
Changes here are applied via PermissionService and logged to PermissionChangeLog.

MODULAR DESIGN:
    Permissions are organized by module (core, qms, mes, dms).
    Each module maps to a Django app label via MODULE_APPS.
    Currently all modules map to 'Tracker' - when you split into
    separate Django apps, just update MODULE_APPS.

Structure:
    MODULE_APPS[module] = 'app_label'
    MODULE_PERMISSIONS[module] = [...permissions...]
    GROUP_DEFINITIONS[group] = {modules: [...], extra: [...]}
"""

from typing import Literal

# =============================================================================
# MODULE TO APP MAPPING
# =============================================================================
# When you split into separate Django apps, update these mappings.
# Example: 'qms': 'qms' instead of 'qms': 'Tracker'

MODULE_APPS: dict[str, str] = {
    'core': 'Tracker',      # User, Companies, Documents, Approvals
    'qms': 'Tracker',       # QualityReports, CAPA, RCA, Dispositions
    'mes': 'Tracker',       # Orders, Parts, WorkOrders, Equipment, Sampling
    'dms': 'Tracker',       # DocChunk (AI/vector embeddings)
}

ModuleName = Literal['core', 'qms', 'mes', 'dms']


# =============================================================================
# MODULE PERMISSIONS
# =============================================================================
# Permissions organized by functional module.
# Format: 'codename' (app label is added automatically from MODULE_APPS)

MODULE_PERMISSIONS: dict[str, dict[str, list[str]]] = {
    # -------------------------------------------------------------------------
    # CORE - Foundational infrastructure (always required)
    # -------------------------------------------------------------------------
    'core': {
        'models': [
            # User management
            'add_user', 'change_user', 'delete_user', 'view_user',
            # Companies
            'add_companies', 'change_companies', 'delete_companies', 'view_companies',
            # Documents
            'add_documents', 'change_documents', 'delete_documents', 'view_documents',
            # Document classification (custom)
            'classify_documents',
            'view_confidential_documents',
            'view_restricted_documents',
            'view_secret_documents',
            # Approval workflows
            'add_approvalrequest', 'change_approvalrequest', 'delete_approvalrequest', 'view_approvalrequest',
            'add_approvalresponse', 'change_approvalresponse', 'delete_approvalresponse', 'view_approvalresponse',
            'add_approvaltemplate', 'change_approvaltemplate', 'delete_approvaltemplate', 'view_approvaltemplate',
            # Approval custom permissions
            'respond_to_approval',
            'create_approval_template',
            'manage_approval_workflow',
            # Audit trail access
            'view_auditlog',
            'export_auditlog',
            # Export control management
            'verify_export_control',
            'change_export_classification',
            # Data export
            'export_data',
        ],
        'wildcards': {
            'view_all': 'view_*',
        },
    },

    # -------------------------------------------------------------------------
    # QMS - Quality Management System
    # -------------------------------------------------------------------------
    'qms': {
        'models': [
            # Quality Reports
            'add_qualityreports', 'change_qualityreports', 'delete_qualityreports', 'view_qualityreports',
            'approve_qualityreports', 'approve_own_qualityreports',
            # Quality Errors
            'add_qualityerrorslist', 'change_qualityerrorslist', 'delete_qualityerrorslist', 'view_qualityerrorslist',
            # Dispositions
            'add_quarantinedisposition', 'change_quarantinedisposition', 'delete_quarantinedisposition', 'view_quarantinedisposition',
            'approve_disposition', 'close_disposition',
            # CAPA
            'add_capa', 'change_capa', 'delete_capa', 'view_capa',
            'initiate_capa', 'close_capa', 'approve_capa', 'verify_capa',
            # CAPA Tasks
            'add_capatasks', 'change_capatasks', 'delete_capatasks', 'view_capatasks',
            # RCA
            'add_rcarecord', 'change_rcarecord', 'delete_rcarecord', 'view_rcarecord',
            'conduct_rca', 'review_rca',
            # 3D Models & Heatmaps
            'add_threedmodel', 'change_threedmodel', 'delete_threedmodel', 'view_threedmodel',
            'add_heatmapannotations', 'change_heatmapannotations', 'delete_heatmapannotations', 'view_heatmapannotations',
        ],
        'wildcards': {
            'view_all': 'view_*',
        },
    },

    # -------------------------------------------------------------------------
    # MES - Manufacturing Execution System (Lite)
    # -------------------------------------------------------------------------
    'mes': {
        'models': [
            # Parts & Part Types
            'add_parts', 'change_parts', 'delete_parts', 'view_parts',
            'add_parttypes', 'change_parttypes', 'delete_parttypes', 'view_parttypes',
            # Orders & Work Orders
            'add_orders', 'change_orders', 'delete_orders', 'view_orders',
            'add_workorder', 'change_workorder', 'delete_workorder', 'view_workorder',
            # Processes & Steps
            'add_processes', 'change_processes', 'delete_processes', 'view_processes',
            'add_steps', 'change_steps', 'delete_steps', 'view_steps',
            # Equipment
            'add_equipments', 'change_equipments', 'delete_equipments', 'view_equipments',
            'add_equipmenttype', 'change_equipmenttype', 'delete_equipmenttype', 'view_equipmenttype',
            # Sampling
            'add_samplingruleset', 'change_samplingruleset', 'delete_samplingruleset', 'view_samplingruleset',
            'add_samplingrule', 'change_samplingrule', 'delete_samplingrule', 'view_samplingrule',
        ],
        'wildcards': {
            'view_all': 'view_*',
        },
    },

    # -------------------------------------------------------------------------
    # DMS - Document Management / AI Module
    # -------------------------------------------------------------------------
    'dms': {
        'models': [
            'add_docchunk', 'change_docchunk', 'delete_docchunk', 'view_docchunk',
        ],
        'wildcards': {
            'view_all': 'view_*',
        },
    },
}


# =============================================================================
# GROUP DEFINITIONS
# =============================================================================
# Define groups by which modules they access and specific permissions.

GROUP_DEFINITIONS: dict[str, dict] = {
    'Admin': {
        'description': 'Full system access, all CRUD operations',
        'all_permissions': True,  # Gets everything from all modules
    },

    'QA_Manager': {
        'description': 'QA management, approve inspections, manage documents, full CAPA control',
        'modules_view_all': ['core', 'qms', 'mes'],  # view_* from these modules
        'permissions': {
            'qms': [
                # Quality Reports - full control + approval
                'add_qualityreports', 'change_qualityreports', 'delete_qualityreports',
                'approve_qualityreports', 'approve_own_qualityreports',
                # Dispositions
                'add_quarantinedisposition', 'change_quarantinedisposition',
                'approve_disposition', 'close_disposition',
                # CAPA - full control
                'add_capa', 'change_capa', 'delete_capa',
                'initiate_capa', 'close_capa', 'approve_capa', 'verify_capa',
                # RCA
                'add_rcarecord', 'change_rcarecord', 'delete_rcarecord',
                'conduct_rca', 'review_rca',
                # CAPA Tasks
                'add_capatasks', 'change_capatasks', 'delete_capatasks',
            ],
            'core': [
                # Document classification
                'view_confidential_documents', 'view_restricted_documents',
                'classify_documents',
                # Approvals
                'respond_to_approval', 'create_approval_template', 'manage_approval_workflow',
                'add_approvaltemplate', 'change_approvaltemplate',
                # Audit and export
                'view_auditlog',
                'export_data',
            ],
        },
    },

    'QA_Inspector': {
        'description': 'Perform quality inspections, initiate CAPAs, conduct RCA',
        'modules_view_all': ['core', 'qms', 'mes'],
        'permissions': {
            'qms': [
                # Quality Reports - create and edit
                'add_qualityreports', 'change_qualityreports',
                # CAPA - initiate and work on
                'add_capa', 'change_capa', 'initiate_capa',
                # RCA - conduct
                'add_rcarecord', 'change_rcarecord', 'conduct_rca',
                # CAPA Tasks
                'add_capatasks', 'change_capatasks',
            ],
            'core': [
                'view_confidential_documents',
            ],
        },
    },

    'Production_Manager': {
        'description': 'Production oversight, view/change manufacturing data, respond to approvals',
        'modules_view_all': ['core', 'qms', 'mes'],
        'permissions': {
            'mes': [
                'change_orders', 'change_parts', 'change_workorder',
            ],
            'core': [
                'view_confidential_documents',
                'respond_to_approval',
                'export_data',
            ],
        },
    },

    'Production_Operator': {
        'description': 'Run production, create and update parts',
        'modules_view_all': ['core', 'mes'],
        'permissions': {
            'mes': [
                'add_parts', 'change_parts',
            ],
        },
    },

    'Document_Controller': {
        'description': 'Manage documents, classification, and approval templates',
        'modules_view_all': ['core', 'mes', 'qms'],
        'permissions': {
            'core': [
                # Documents - full CRUD
                'add_documents', 'change_documents', 'delete_documents',
                # Classification
                'classify_documents',
                'view_confidential_documents', 'view_restricted_documents', 'view_secret_documents',
                # Approval templates
                'create_approval_template', 'manage_approval_workflow',
                'add_approvaltemplate', 'change_approvaltemplate',
                # Audit, export control, and data export
                'view_auditlog',
                'export_data',
                'change_export_classification',
            ],
        },
    },

    'Engineering': {
        'description': 'Engineering changes, drawing control, design approvals',
        'modules_view_all': ['core', 'qms', 'mes'],
        'permissions': {
            'core': [
                # Documents - create and edit (drawings, specs, ECOs)
                'add_documents', 'change_documents',
                # Classification
                'view_confidential_documents', 'view_restricted_documents',
                # Approvals
                'respond_to_approval',
            ],
            'qms': [
                # Can initiate CAPAs for design issues
                'add_capa', 'change_capa', 'initiate_capa',
            ],
        },
    },

    'Supplier_Quality': {
        'description': 'Supplier management, incoming inspection, SCARs',
        'modules_view_all': ['core', 'qms', 'mes'],
        'permissions': {
            'qms': [
                # Quality Reports - for incoming inspection
                'add_qualityreports', 'change_qualityreports',
                # Dispositions - for rejected incoming material
                'add_quarantinedisposition', 'change_quarantinedisposition',
                # CAPA - initiate for supplier issues
                'add_capa', 'change_capa', 'initiate_capa',
                # RCA
                'add_rcarecord', 'change_rcarecord', 'conduct_rca',
            ],
            'core': [
                # Documents - supplier certs, SCARs
                'add_documents', 'change_documents',
                'view_confidential_documents',
                # Approvals
                'respond_to_approval',
            ],
        },
    },

    'Customer': {
        'description': 'View own company orders, parts, and documents',
        'permissions': {
            'mes': ['view_orders', 'view_parts', 'view_workorder'],
            'core': ['view_documents', 'view_companies'],
        },
    },
}


# =============================================================================
# BUILT GROUPS (computed from above)
# =============================================================================
# This is what PermissionService actually uses.

def _build_permission_string(module: str, codename: str) -> str:
    """Build full permission string: 'app_label.codename'."""
    app_label = MODULE_APPS.get(module, 'Tracker')
    return f"{app_label}.{codename}"


def _build_wildcard_string(module: str) -> str:
    """Build wildcard pattern for view_* in a module."""
    app_label = MODULE_APPS.get(module, 'Tracker')
    return f"{app_label}.view_*"


def _build_group_permissions(group_name: str, config: dict) -> list[str] | str:
    """Build permission list for a group from its definition."""
    # Admin gets everything
    if config.get('all_permissions'):
        return '__all__'

    permissions = set()

    # Add view_* wildcards for specified modules
    for module in config.get('modules_view_all', []):
        permissions.add(_build_wildcard_string(module))

    # Add specific permissions by module
    for module, perms in config.get('permissions', {}).items():
        for perm in perms:
            permissions.add(_build_permission_string(module, perm))

    return sorted(permissions)


def _build_groups() -> dict:
    """Build the GROUPS dict from GROUP_DEFINITIONS."""
    groups = {}
    for group_name, config in GROUP_DEFINITIONS.items():
        groups[group_name] = {
            'description': config.get('description', ''),
            'permissions': _build_group_permissions(group_name, config),
        }
    return groups


# The actual GROUPS dict used by PermissionService
GROUPS = _build_groups()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_group_names() -> list[str]:
    """Return list of all defined group names."""
    return list(GROUPS.keys())


def get_group_description(group_name: str) -> str:
    """Return description for a group."""
    return GROUPS.get(group_name, {}).get('description', '')


def get_group_permissions(group_name: str) -> list[str] | str:
    """Return permission list for a group."""
    return GROUPS.get(group_name, {}).get('permissions', [])


def get_module_app_label(module: str) -> str:
    """Return the Django app label for a module."""
    return MODULE_APPS.get(module, 'Tracker')


def get_all_app_labels() -> set[str]:
    """Return all unique app labels (for multi-app permission queries)."""
    return set(MODULE_APPS.values())


def validate_structure() -> list[str]:
    """
    Validate the permission structure.
    Returns list of warnings/errors.
    """
    issues = []

    for group_name, config in GROUPS.items():
        if 'description' not in config:
            issues.append(f"Group '{group_name}' missing description")
        if 'permissions' not in config:
            issues.append(f"Group '{group_name}' missing permissions")

        perms = config.get('permissions', [])
        if perms != '__all__' and not isinstance(perms, list):
            issues.append(f"Group '{group_name}' permissions must be list or '__all__'")

    return issues


# =============================================================================
# DRF PERMISSION CLASSES (Tenant-Scoped)
# =============================================================================

from rest_framework.permissions import BasePermission


class TenantPermission(BasePermission):
    """
    Base class for tenant-scoped permissions.

    Checks permissions against TenantGroup.permissions instead of
    Django's global auth.Permission system.

    Tenant resolution is handled automatically by User._resolve_tenant():
    - Dedicated mode: TenantMiddleware sets user._current_tenant to default tenant
    - SaaS mode: TenantMiddleware sets user._current_tenant from header/subdomain

    Permission classes just call user.has_tenant_perm() - no special handling needed.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Superuser bypasses all checks
        if request.user.is_superuser:
            return True

        return True  # Base class allows access; subclasses add restrictions


class TenantModelPermissions(TenantPermission):
    """
    Tenant-scoped model permissions for DRF viewsets.

    Maps HTTP methods to permission codenames:
    - GET/HEAD/OPTIONS -> view_{model}
    - POST -> add_{model}
    - PUT/PATCH -> change_{model}
    - DELETE -> delete_{model}

    Usage:
        class OrderViewSet(viewsets.ModelViewSet):
            permission_classes = [TenantModelPermissions]
            queryset = Orders.objects.all()

    The model name is derived from view.queryset.model._meta.model_name.
    """

    # Map HTTP methods to permission action prefixes
    perms_map = {
        'GET': 'view',
        'OPTIONS': 'view',
        'HEAD': 'view',
        'POST': 'add',
        'PUT': 'change',
        'PATCH': 'change',
        'DELETE': 'delete',
    }

    def get_required_permission(self, request, view):
        """
        Get the permission codename required for this request.

        Returns permission like 'add_orders', 'view_parts', etc.
        """
        # Get action prefix from HTTP method
        action = self.perms_map.get(request.method)
        if not action:
            return None

        # Get model name from view
        if hasattr(view, 'get_queryset'):
            try:
                model = view.get_queryset().model
            except Exception:
                model = getattr(view, 'queryset', None)
                if model is not None:
                    model = model.model
        else:
            model = getattr(view, 'queryset', None)
            if model is not None:
                model = model.model

        if model is None:
            return None

        model_name = model._meta.model_name
        return f"{action}_{model_name}"

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        # Get required permission
        perm = self.get_required_permission(request, view)
        if not perm:
            return True  # No permission required (shouldn't happen normally)

        # Check tenant-scoped permission (tenant auto-resolved by User._resolve_tenant)
        return request.user.has_tenant_perm(perm)


class TenantActionPermissions(TenantPermission):
    """
    Tenant-scoped permissions for custom viewset actions.

    Use this when you need custom permission names for specific actions.

    Usage:
        class OrderViewSet(viewsets.ModelViewSet):
            permission_classes = [TenantActionPermissions]

            # Define permissions per action
            action_permissions = {
                'list': ['view_orders'],
                'create': ['add_orders'],
                'approve': ['approve_orders'],
                'export': ['view_orders', 'export_data'],
            }

            @action(detail=True, methods=['post'])
            def approve(self, request, pk=None):
                ...
    """

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        # Get action-specific permissions
        action = getattr(view, 'action', None)
        if not action:
            return True

        action_permissions = getattr(view, 'action_permissions', {})
        required_perms = action_permissions.get(action, [])

        if not required_perms:
            return True  # No specific permissions required for this action

        # Check if user has ALL required permissions
        return request.user.has_tenant_perms(required_perms)


class RequirePermission(TenantPermission):
    """
    Decorator-style permission that requires specific permission(s).

    Usage as class:
        permission_classes = [RequirePermission('approve_capa')]

    Usage in view for inline check:
        if not RequirePermission.check(request.user, 'approve_capa'):
            raise PermissionDenied()
    """

    def __init__(self, *perms):
        self.required_perms = perms

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        return request.user.has_tenant_perms(self.required_perms)

    @classmethod
    def check(cls, user, *perms):
        """
        Utility method for inline permission checks.

        Usage:
            if not RequirePermission.check(request.user, 'approve_capa'):
                raise PermissionDenied("You don't have permission to approve CAPAs")
        """
        if user.is_superuser:
            return True
        return user.has_tenant_perms(perms)

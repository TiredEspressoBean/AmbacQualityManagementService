# Export all viewsets for backward compatibility and router registration
# This allows `from Tracker.Viewsets import SomeViewSet` to continue working

# Base classes and mixins for tenant scoping
from .base import (
    TenantAwareMixin,
    TenantScopedMixin,
    TenantScopedModelViewSet,
    TenantScopedReadOnlyModelViewSet,
    TenantScopedNestedMixin,
    NonTenantModelViewSet,
)

from .core import (
    # Mixins & Utilities
    ExcelExportMixin,
    with_int_pk_schema,
    serve_media_iframe_safe,

    # User & Company ViewSets
    UserViewSet,
    UserDetailsView,
    UserInvitationViewSet,
    EmployeeSelectViewSet,
    CompanyViewSet,
    CustomerViewSet,

    # Auth & Groups
    GroupViewSet,

    # Audit Logs & Content Types
    LogEntryViewSet,
    ContentTypeViewSet,

    # Document ViewSets (universal infrastructure)
    DocumentViewSet,
    DocumentTypeViewSet,

    # Approval Workflow ViewSets
    ApprovalTemplateViewSet,
    ApprovalRequestViewSet,
    ApprovalResponseViewSet,

    # Scope ViewSet (graph traversal queries)
    ScopeView,

    # Bulk Operations ViewSets
    # (Will add BulkSoftDeleteViewSet, BulkRestoreViewSet when implemented)
)

# Integration ViewSets
from .integrations.hubspot import (
    HubspotGatesViewSet,
)

from .mes_lite import (
    # Order ViewSets
    TrackerOrderViewSet,
    OrdersViewSet,
    PartsByOrderView,

    # Part ViewSets
    PartsViewSet,

    # Work Order ViewSets
    WorkOrderViewSet,

    # Process & Step ViewSets
    ProcessViewSet,
    ProcessWithStepsViewSet,
    StepsViewSet,
    StepExecutionViewSet,
    PartTypeViewSet,

    # Equipment ViewSets
    EquipmentViewSet,
    EquipmentTypeViewSet,
    EquipmentSelectViewSet,
)

from .qms import (
    # Quality ViewSets
    QualityReportViewSet,
    ErrorTypeViewSet,
    QuarantineDispositionViewSet,

    # Sampling ViewSets
    SamplingRuleSetViewSet,
    SamplingRuleViewSet,
    MeasurementsDefinitionViewSet,

    # Notification ViewSets
    NotificationPreferenceViewSet,

    # CAPA ViewSets
    CAPAViewSet,
    CapaTasksViewSet,
    RcaRecordViewSet,
    CapaVerificationViewSet,

    # RCA Detail ViewSets (5 Whys & Fishbone)
    FiveWhysViewSet,
    FishboneViewSet,

    # 3D Model & Heatmap ViewSets (quality visualization)
    ThreeDModelViewSet,
    HeatMapAnnotationsViewSet,
)

# Training ViewSets
from .training import (
    TrainingTypeViewSet,
    TrainingRecordViewSet,
    TrainingRequirementViewSet,
)

# Calibration ViewSets
from .calibration import (
    CalibrationRecordViewSet,
)

# DMS ViewSets (AI/LLM Module)
from .dms import (
    ChatSessionViewSet,
)

# Reports ViewSet (PDF generation)
from .reports import (
    ReportViewSet,
    GeneratedReportSerializer,
)

# SPC ViewSet (Statistical Process Control)
from .spc import (
    SPCViewSet,
    SPCBaselineViewSet,
)

# Dashboard ViewSet (Quality Analytics)
from .dashboard import (
    DashboardViewSet,
)

# MES Standard ViewSets (Scheduling, Traceability, Labor)
from .mes_standard import (
    # Work Centers
    WorkCenterViewSet,
    WorkCenterSelectViewSet,

    # Shifts & Scheduling
    ShiftViewSet,
    ScheduleSlotViewSet,

    # Downtime
    DowntimeEventViewSet,

    # Material Lots
    MaterialLotViewSet,
    MaterialUsageViewSet,

    # Time Entries
    TimeEntryViewSet,

    # BOMs
    BOMViewSet,
    BOMLineViewSet,

    # Assembly Usage
    AssemblyUsageViewSet,
)

# Remanufacturing ViewSets
from .reman import (
    CoreViewSet,
    HarvestedComponentViewSet,
    DisassemblyBOMLineViewSet,
)


__all__ = [
    # Base - Tenant Scoping
    'TenantAwareMixin',
    'TenantScopedMixin',
    'TenantScopedModelViewSet',
    'TenantScopedReadOnlyModelViewSet',
    'TenantScopedNestedMixin',
    'NonTenantModelViewSet',

    # Core - Mixins & Utilities
    'ExcelExportMixin',
    'with_int_pk_schema',
    'serve_media_iframe_safe',

    # Core - User & Company
    'UserViewSet',
    'UserDetailsView',
    'UserInvitationViewSet',
    'EmployeeSelectViewSet',
    'CompanyViewSet',
    'CustomerViewSet',

    # Core - Auth & Groups
    'GroupViewSet',

    # Core - Audit Logs
    'LogEntryViewSet',
    'ContentTypeViewSet',

    # Core - Documents (universal infrastructure)
    'DocumentViewSet',
    'DocumentTypeViewSet',

    # Core - Approval Workflow
    'ApprovalTemplateViewSet',
    'ApprovalRequestViewSet',
    'ApprovalResponseViewSet',

    # Core - Scope (graph traversal)
    'ScopeView',

    # Integrations - HubSpot
    'HubspotGatesViewSet',

    # MES Lite - Orders
    'TrackerOrderViewSet',
    'OrdersViewSet',
    'PartsByOrderView',

    # MES Lite - Parts
    'PartsViewSet',

    # MES Lite - Work Orders
    'WorkOrderViewSet',

    # MES Lite - Processes & Steps
    'ProcessViewSet',
    'ProcessWithStepsViewSet',
    'StepsViewSet',
    'StepExecutionViewSet',
    'PartTypeViewSet',

    # MES Lite - Equipment
    'EquipmentViewSet',
    'EquipmentTypeViewSet',
    'EquipmentSelectViewSet',

    # QMS - Quality
    'QualityReportViewSet',
    'ErrorTypeViewSet',
    'QuarantineDispositionViewSet',

    # QMS - Sampling
    'SamplingRuleSetViewSet',
    'SamplingRuleViewSet',
    'MeasurementsDefinitionViewSet',

    # QMS - Notifications
    'NotificationPreferenceViewSet',

    # QMS - CAPA
    'CAPAViewSet',
    'CapaTasksViewSet',
    'RcaRecordViewSet',
    'CapaVerificationViewSet',

    # QMS - RCA Details (5 Whys & Fishbone)
    'FiveWhysViewSet',
    'FishboneViewSet',

    # QMS - 3D Models & Heatmap Annotations (quality visualization)
    'ThreeDModelViewSet',
    'HeatMapAnnotationsViewSet',

    # DMS - AI/LLM Module
    'ChatSessionViewSet',

    # Reports (PDF generation)
    'ReportViewSet',
    'GeneratedReportSerializer',

    # SPC (Statistical Process Control)
    'SPCViewSet',
    'SPCBaselineViewSet',

    # Dashboard (Quality Analytics)
    'DashboardViewSet',

    # MES Standard - Work Centers
    'WorkCenterViewSet',
    'WorkCenterSelectViewSet',

    # MES Standard - Shifts & Scheduling
    'ShiftViewSet',
    'ScheduleSlotViewSet',

    # MES Standard - Downtime
    'DowntimeEventViewSet',

    # MES Standard - Material Lots
    'MaterialLotViewSet',
    'MaterialUsageViewSet',

    # MES Standard - Time Entries
    'TimeEntryViewSet',

    # MES Standard - BOMs
    'BOMViewSet',
    'BOMLineViewSet',

    # MES Standard - Assembly Usage
    'AssemblyUsageViewSet',

    # Reman - Cores & Components
    'CoreViewSet',
    'HarvestedComponentViewSet',
    'DisassemblyBOMLineViewSet',

    # Training
    'TrainingTypeViewSet',
    'TrainingRecordViewSet',
    'TrainingRequirementViewSet',

    # Calibration
    'CalibrationRecordViewSet',
]


def register_viewsets(router):
    """
    Register all ViewSets with the provided router.

    This function centralizes ViewSet registration for the DRF router.
    Call this from urls.py to register all API endpoints.

    Usage:
        from rest_framework.routers import DefaultRouter
        from Tracker.viewsets import register_viewsets

        router = DefaultRouter()
        register_viewsets(router)
    """
    # ===== CORE VIEWSETS =====
    router.register(r'User', UserViewSet, basename='User')
    router.register(r'UserInvitations', UserInvitationViewSet, basename='UserInvitations')
    router.register(r'Employees-Options', EmployeeSelectViewSet, basename='Employees-Options')
    router.register(r'Companies', CompanyViewSet, basename='Companies')
    router.register(r'Customers', CustomerViewSet, basename='Customers')
    router.register(r'Groups', GroupViewSet, basename='Groups')
    router.register(r'auditlog', LogEntryViewSet, basename='auditlog')
    router.register(r'content-types', ContentTypeViewSet, basename='contenttype')
    router.register(r'HubspotGates', HubspotGatesViewSet, basename='HubspotGates')

    # Approval Workflow
    router.register(r'ApprovalTemplates', ApprovalTemplateViewSet, basename='ApprovalTemplates')
    router.register(r'ApprovalRequests', ApprovalRequestViewSet, basename='ApprovalRequests')
    router.register(r'ApprovalResponses', ApprovalResponseViewSet, basename='ApprovalResponses')

    # Scope (graph traversal queries)
    router.register(r'scope', ScopeView, basename='scope')

    # ===== MES LITE VIEWSETS =====
    router.register(r'TrackerOrders', TrackerOrderViewSet, basename='TrackerOrders')
    router.register(r'Orders', OrdersViewSet, basename='Orders')
    router.register(r'Parts', PartsViewSet, basename='Parts')
    router.register(r'WorkOrders', WorkOrderViewSet, basename='WorkOrders')
    router.register(r'Processes', ProcessViewSet, basename='Processes')
    router.register(r'Processes_with_steps', ProcessWithStepsViewSet)
    router.register(r'Steps', StepsViewSet, basename='Steps')
    router.register(r'StepExecutions', StepExecutionViewSet, basename='StepExecutions')
    router.register(r'PartTypes', PartTypeViewSet, basename='PartTypes')
    router.register(r'Equipment', EquipmentViewSet, basename='equipment')
    router.register(r'Equipment-types', EquipmentTypeViewSet, basename='equipmenttype')
    router.register(r'Equipment-Options', EquipmentSelectViewSet, basename='Equipment-Options')

    # ===== QMS VIEWSETS =====
    router.register(r'ErrorReports', QualityReportViewSet, basename='ErrorReports')
    router.register(r'Error-types', ErrorTypeViewSet, basename='errortype')
    router.register(r'QuarantineDispositions', QuarantineDispositionViewSet, basename='QuarantineDispositions')
    router.register(r'Sampling-rule-sets', SamplingRuleSetViewSet, basename='sampling-rule-sets')
    router.register(r'Sampling-rules', SamplingRuleViewSet, basename='sampling-rules')
    router.register(r'MeasurementDefinitions', MeasurementsDefinitionViewSet)
    router.register(r'NotificationPreferences', NotificationPreferenceViewSet, basename='NotificationPreferences')

    # CAPA
    router.register(r'CAPAs', CAPAViewSet, basename='CAPAs')
    router.register(r'CapaTasks', CapaTasksViewSet, basename='CapaTasks')
    router.register(r'RcaRecords', RcaRecordViewSet, basename='RcaRecords')
    router.register(r'CapaVerifications', CapaVerificationViewSet, basename='CapaVerifications')
    router.register(r'FiveWhys', FiveWhysViewSet, basename='FiveWhys')
    router.register(r'Fishbone', FishboneViewSet, basename='Fishbone')

    # ===== DMS VIEWSETS =====
    router.register(r'Documents', DocumentViewSet, basename='documents')
    router.register(r'DocumentTypes', DocumentTypeViewSet, basename='documenttypes')
    router.register(r'ThreeDModels', ThreeDModelViewSet, basename='ThreeDModels')
    router.register(r'HeatMapAnnotation', HeatMapAnnotationsViewSet, basename='HeatMapAnnotation')
    router.register(r'ChatSessions', ChatSessionViewSet, basename='ChatSessions')

    # ===== REPORTS VIEWSETS =====
    router.register(r'reports', ReportViewSet, basename='reports')

    # ===== SPC VIEWSETS =====
    router.register(r'spc', SPCViewSet, basename='spc')
    router.register(r'spc-baselines', SPCBaselineViewSet, basename='spc-baselines')

    # ===== DASHBOARD VIEWSETS =====
    router.register(r'dashboard', DashboardViewSet, basename='dashboard')

    # ===== MES STANDARD VIEWSETS =====
    # Work Centers
    router.register(r'WorkCenters', WorkCenterViewSet, basename='WorkCenters')
    router.register(r'WorkCenters-Options', WorkCenterSelectViewSet, basename='WorkCenters-Options')

    # Shifts & Scheduling
    router.register(r'Shifts', ShiftViewSet, basename='Shifts')
    router.register(r'ScheduleSlots', ScheduleSlotViewSet, basename='ScheduleSlots')

    # Downtime
    router.register(r'DowntimeEvents', DowntimeEventViewSet, basename='DowntimeEvents')

    # Material Lots & Usage
    router.register(r'MaterialLots', MaterialLotViewSet, basename='MaterialLots')
    router.register(r'MaterialUsages', MaterialUsageViewSet, basename='MaterialUsages')

    # Time Entries
    router.register(r'TimeEntries', TimeEntryViewSet, basename='TimeEntries')

    # BOMs
    router.register(r'BOMs', BOMViewSet, basename='BOMs')
    router.register(r'BOMLines', BOMLineViewSet, basename='BOMLines')

    # Assembly Usage
    router.register(r'AssemblyUsages', AssemblyUsageViewSet, basename='AssemblyUsages')

    # ===== REMAN VIEWSETS =====
    router.register(r'Cores', CoreViewSet, basename='Cores')
    router.register(r'HarvestedComponents', HarvestedComponentViewSet, basename='HarvestedComponents')
    router.register(r'DisassemblyBOMLines', DisassemblyBOMLineViewSet, basename='DisassemblyBOMLines')

    # ===== TRAINING VIEWSETS =====
    router.register(r'TrainingTypes', TrainingTypeViewSet, basename='TrainingTypes')
    router.register(r'TrainingRecords', TrainingRecordViewSet, basename='TrainingRecords')
    router.register(r'TrainingRequirements', TrainingRequirementViewSet, basename='TrainingRequirements')

    # ===== CALIBRATION VIEWSETS =====
    router.register(r'CalibrationRecords', CalibrationRecordViewSet, basename='CalibrationRecords')

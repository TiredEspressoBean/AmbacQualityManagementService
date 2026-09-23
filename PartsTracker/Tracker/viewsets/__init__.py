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

from .mixins import DataExportMixin

from .core import (
    # Mixins & Utilities
    with_int_pk_schema,
    serve_media_iframe_safe,

    # User & Company ViewSets
    UserViewSet,
    UserDetailsView,
    UserInvitationViewSet,
    EmployeeSelectViewSet,
    CompanyViewSet,
    CustomerViewSet,

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
    OrderLineViewSet,
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
    OutsideProcessShipmentViewSet,
    PartTypeViewSet,

    # Equipment ViewSets
    EquipmentViewSet,
    EquipmentTypeViewSet,
    EquipmentSelectViewSet,

    # Milestone ViewSets
    MilestoneTemplateViewSet,
    MilestoneViewSet,
)

from .qms import (
    # Quality ViewSets
    QualityReportViewSet,
    ErrorTypeViewSet,
    QuarantineDispositionViewSet,
    SupplierQualificationViewSet,
    PartApprovalViewSet,

    # Sampling ViewSets
    SamplingRuleSetViewSet,
    SamplingRuleViewSet,
    SamplingSeverityStateViewSet,
    MeasurementsDefinitionViewSet,

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

    # Step Override ViewSets (rollback approvals)
    StepOverrideViewSet,

    # FPI ViewSets (First Piece Inspection)
    FPIRecordViewSet,

    # Step Execution Measurement ViewSets
    StepExecutionMeasurementViewSet,
)

# Training ViewSets
from .training import (
    TrainingTypeViewSet,
    TrainingRecordViewSet,
    TrainingRequirementViewSet,
    JobRoleViewSet,
    CompetenceMatrixView,
)

# Calibration ViewSets
from .calibration import (
    CalibrationRecordViewSet,
)

# DMS ViewSets (AI/LLM Module)
from .dms import (
    ChatSessionViewSet,
)

# Reports ViewSet (PDF generation) - lives in Tracker.reports subpackage
from Tracker.reports.viewsets import (
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
    UserWorkCenterMembershipViewSet,

    # Shifts & Scheduling
    ShiftViewSet,
    ScheduleSlotViewSet,

    # Downtime
    DowntimeEventViewSet,

    # Materials & Lots
    MaterialViewSet,
    MaterialLotViewSet,
    MaterialUsageViewSet,
    IncomingInspectionViewSet,
    InspectionInboxViewSet,

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
    RepairCodeViewSet,
    RebuildScopePresetViewSet,
    RebuildSlotOverrideViewSet,
)

# Scheduling (CP-SAT solver + operator dispatch) ViewSets
from .scheduling import (
    ScheduleViewSet,
    ScheduledTaskViewSet,
    FixtureViewSet,
    PlantCalendarExceptionViewSet,
    LaborCalendarBlockViewSet,
    OvertimeWindowViewSet,
)

# Digital Work Instructions ViewSets
from .dwi import (
    SubstepViewSet,
    SubstepResourceViewSet,
    SubstepTranslationViewSet,
    SubstepCompletionViewSet,
    SubstepGateCompletionViewSet,
    SubstepResponseViewSet,
    BatchExecutionViewSet,
    SamplingDecisionViewSet,
)

# Life Tracking ViewSets
from .life_tracking import (
    LifeLimitDefinitionViewSet,
    PartTypeLifeLimitViewSet,
    LifeTrackingViewSet,
)

from .notifications import (
    NotificationEventTypeCatalogView,
    NotificationFeedViewSet,
    TenantRuleViewSet,
    CustomerRuleViewSet,
    PersonalRuleViewSet,
    ExternalContactViewSet,
    TenantScheduleViewSet,
    CustomerScheduleViewSet,
    PersonalScheduleViewSet,
    ScheduledContentProviderCatalogView,
)

# Change Control ViewSets (PCR / PCO / PCN)
from .change_control import (
    ProcessChangeRequestViewSet,
    ProcessChangeOrderViewSet,
    ProcessChangeNoticeViewSet,
)

from .shift_notes import ShiftNoteViewSet
from .work_queue import WorkQueueViewSet


__all__ = [
    'ShiftNoteViewSet',
    'WorkQueueViewSet',
    'NotificationEventTypeCatalogView',
    'NotificationFeedViewSet',
    'TenantRuleViewSet',
    'CustomerRuleViewSet',
    'PersonalRuleViewSet',
    'ExternalContactViewSet',
    'TenantScheduleViewSet',
    'CustomerScheduleViewSet',
    'PersonalScheduleViewSet',
    'ScheduledContentProviderCatalogView',
    'ProcessChangeRequestViewSet',
    'ProcessChangeOrderViewSet',
    'ProcessChangeNoticeViewSet',
    # Base - Tenant Scoping
    'TenantAwareMixin',
    'TenantScopedMixin',
    'TenantScopedModelViewSet',
    'TenantScopedReadOnlyModelViewSet',
    'TenantScopedNestedMixin',
    'NonTenantModelViewSet',

    # Core - Mixins & Utilities
    'DataExportMixin',
    'with_int_pk_schema',
    'serve_media_iframe_safe',

    # Core - User & Company
    'UserViewSet',
    'UserDetailsView',
    'UserInvitationViewSet',
    'EmployeeSelectViewSet',
    'CompanyViewSet',
    'CustomerViewSet',


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

    # Integrations - HubSpot (legacy)
    'HubspotGatesViewSet',

    # Milestones
    'MilestoneTemplateViewSet',
    'MilestoneViewSet',

    # MES Lite - Orders
    'TrackerOrderViewSet',
    'OrdersViewSet',
    'OrderLineViewSet',
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
    'OutsideProcessShipmentViewSet',
    'PartTypeViewSet',

    # MES Lite - Equipment
    'EquipmentViewSet',
    'EquipmentTypeViewSet',
    'EquipmentSelectViewSet',

    # QMS - Quality
    'QualityReportViewSet',
    'ErrorTypeViewSet',
    'QuarantineDispositionViewSet',
    'SupplierQualificationViewSet',
    'PartApprovalViewSet',

    # QMS - Sampling
    'SamplingRuleSetViewSet',
    'SamplingRuleViewSet',
    'SamplingSeverityStateViewSet',
    'MeasurementsDefinitionViewSet',

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

    # QMS - Step Overrides (rollback approvals)
    'StepOverrideViewSet',

    # QMS - FPI (First Piece Inspection)
    'FPIRecordViewSet',

    # QMS - Step Execution Measurements
    'StepExecutionMeasurementViewSet',

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
    'UserWorkCenterMembershipViewSet',

    # MES Standard - Shifts & Scheduling
    'ShiftViewSet',
    'ScheduleSlotViewSet',

    # MES Standard - Downtime
    'DowntimeEventViewSet',

    # MES Standard - Material Lots
    'MaterialViewSet',
    'MaterialLotViewSet',
    'IncomingInspectionViewSet',
    'InspectionInboxViewSet',
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
    'RepairCodeViewSet',
    'RebuildScopePresetViewSet',
    'RebuildSlotOverrideViewSet',

    # Scheduling (CP-SAT solver + dispatch)
    'ScheduleViewSet',
    'ScheduledTaskViewSet',
    'FixtureViewSet',
    'PlantCalendarExceptionViewSet',
    'LaborCalendarBlockViewSet',
    'OvertimeWindowViewSet',

    # Digital Work Instructions
    'SubstepViewSet',
    'SubstepResourceViewSet',
    'SubstepTranslationViewSet',
    'SubstepCompletionViewSet',
    'SubstepGateCompletionViewSet',
    'SubstepResponseViewSet',
    'BatchExecutionViewSet',
    'SamplingDecisionViewSet',

    # Training
    'TrainingTypeViewSet',
    'TrainingRecordViewSet',
    'TrainingRequirementViewSet',
    'JobRoleViewSet',
    'CompetenceMatrixView',

    # Calibration
    'CalibrationRecordViewSet',

    # Life Tracking
    'LifeLimitDefinitionViewSet',
    'PartTypeLifeLimitViewSet',
    'LifeTrackingViewSet',
]

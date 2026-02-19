"""
Tracker Models Module

This module provides a unified interface to all Tracker app models,
organized into logical groups:

- CORE: Foundational infrastructure (SecureModel, User, Companies, Documents, enums,
        notifications, archive reasons, approval workflows, utility functions)
- MES_LITE: Core manufacturing operations (PartTypes, Processes, Steps, Orders,
            WorkOrder, Parts, MeasurementDefinition)
- MES_STANDARD: Full traceability and compliance (Equipment, Sampling, MaterialLot,
               BOM, TimeEntry, WorkCenter, Scheduling)
- QMS: Quality Management System models including quality reports, measurements,
       equipment usage, dispositions, step transitions, CAPA, RCA, 3D models,
       and heatmap annotations for quality visualization
- REMAN: Remanufacturing add-on (Core, HarvestedComponent, DisassemblyBOMLine)
- SPC: Statistical Process Control (SPCBaseline)
- DMS: Optional AI/LLM module for document intelligence (vector embeddings,
       semantic search, RAG support)

All models are re-exported from this __init__.py for backward compatibility,
so existing code using `from Tracker.models import SomeModel` will continue to work.
"""

# Core foundational infrastructure
from .core import (
    # Base classes and managers
    SecureQuerySet,
    SecureManager,
    SecureModel,

    # Tenant model (multi-tenancy)
    Tenant,

    # Facility (multi-site support)
    Facility,

    # Tenant-scoped groups and roles
    TenantGroup,
    UserRole,

    # User and company models
    User,
    Companies,
    UserInvitation,

    # External integrations (moved here to avoid circular imports)
    ExternalAPIOrderIdentifier,

    # Utility functions and enums
    part_doc_upload_path,
    ClassificationLevel,

    # Archive reasons
    ArchiveReason,

    # Notifications
    NotificationTask,

    # Approval workflow models and enums
    Approval_Type,
    Approval_Status_Type,
    ApprovalFlows,
    SequenceTypes,
    ApprovalDelegation,
    ApprovalDecision,
    VerificationMethod,
    ApprovalRequest,
    ApprovalResponse,
    ApprovalTemplate,

    # Approver assignment (through models for ApprovalRequest)
    ApproverAssignmentSource,
    ApproverAssignment,
    GroupApproverAssignment,

    # Document management (core infrastructure)
    DocumentType,
    Documents,

    # Permission audit logging
    PermissionChangeLog,

    # Tenant-scoped group membership
    TenantGroupMembership,
)

# MES Lite - Core Manufacturing operations
from .mes_lite import (
    # Part and process models
    PartTypes,
    Processes,
    MeasurementDefinition,
    StepMeasurementRequirement,
    Steps,
    ProcessStep,
    StepEdge,
    EdgeType,

    # Order models
    OrderViewer,
    Orders,
    WorkOrder,
    Parts,

    # Status and type enums
    PartsStatus,
    OrdersStatus,
    WorkOrderStatus,
    APQPStage,
    ProcessStatus,

    # Step execution (workflow tracking)
    StepExecution,
)

# MES Standard - Full traceability and compliance
from .mes_standard import (
    # Equipment (Standard tier)
    EquipmentType,
    EquipmentStatus,
    EquipmentQuerySet,
    EquipmentManager,
    Equipments,

    # Sampling infrastructure (Standard tier)
    SamplingRuleSet,
    SamplingRule,
    SamplingRuleType,
    SamplingTriggerState,
    SamplingTriggerManager,
    SamplingAuditLog,
    SamplingAnalytics,

    # Material lot tracking (Standard tier)
    MaterialLot,
    MaterialUsage,

    # Time tracking (Standard tier)
    TimeEntry,

    # Bill of Materials (Standard tier)
    BOM,
    BOMLine,
    AssemblyUsage,

    # Work center and scheduling (Standard tier)
    WorkCenter,
    Shift,
    ScheduleSlot,
    DowntimeEvent,
)

# Remanufacturing add-on
from .reman import (
    Core,
    HarvestedComponent,
    DisassemblyBOMLine,
)

# Integration models - HubSpot
from .integrations.hubspot import (
    HubSpotSyncLog,
)
# Note: ExternalAPIOrderIdentifier imported from core (moved to avoid circular imports)

# QMS models
from .qms import (
    # Quality tracking
    QualityErrorsList,
    DefectSeverity,
    QualityReportDefect,
    QualityReports,
    MeasurementResult,
    EquipmentUsage,
    QaApproval,
    QuarantineDisposition,

    # Step transitions
    StepTransitionLog,

    # 3D Models and Heatmap Annotations (quality visualization)
    ModelProcessingStatus,
    ThreeDModel,
    HeatMapAnnotations,

    # CAPA models and enums
    CapaType,
    CapaSeverity,
    CapaStatus,
    CapaTaskType,
    CapaTaskStatus,
    CapaTaskCompletionMode,
    RcaMethod,
    RcaReviewStatus,
    RootCauseVerificationStatus,
    RootCauseCategory,
    RootCauseRole,
    EffectivenessResult,
    CAPA,
    CapaTasks,
    CapaTaskAssignee,
    RcaRecord,
    FiveWhys,
    Fishbone,
    RootCause,
    CapaVerification,

    # Generated Reports (PDF Audit Trail)
    GeneratedReport,

    # Training & Calibration
    TrainingType,
    TrainingRecord,
    TrainingRequirement,
    CalibrationRecordQuerySet,
    CalibrationRecordManager,
    CalibrationRecord,
)

# SPC models - Statistical Process Control
from .spc import (
    SPCBaseline,
    ChartType,
    BaselineStatus,
)

# DMS models - AI/LLM document intelligence (optional module)
from .dms import (
    DocChunk,
    ChatSession,
)

# Define __all__ for explicit exports
__all__ = [
    # Core (Foundational Infrastructure)
    'SecureQuerySet',
    'SecureManager',
    'SecureModel',
    'Tenant',
    'Facility',
    'TenantGroup',
    'UserRole',
    'User',
    'Companies',
    'UserInvitation',
    'part_doc_upload_path',
    'ClassificationLevel',
    'ArchiveReason',
    'NotificationTask',
    'Approval_Type',
    'Approval_Status_Type',
    'ApprovalFlows',
    'SequenceTypes',
    'ApprovalDelegation',
    'ApprovalDecision',
    'VerificationMethod',
    'ApprovalRequest',
    'ApprovalResponse',
    'ApprovalTemplate',
    'ApproverAssignmentSource',
    'ApproverAssignment',
    'GroupApproverAssignment',
    'DocumentType',
    'Documents',
    'PermissionChangeLog',
    'TenantGroupMembership',

    # MES Lite (Core Manufacturing)
    'PartTypes',
    'Processes',
    'MeasurementDefinition',
    'StepMeasurementRequirement',
    'Steps',
    'ProcessStep',
    'StepEdge',
    'EdgeType',
    'OrderViewer',
    'Orders',
    'WorkOrder',
    'Parts',
    'PartsStatus',
    'OrdersStatus',
    'WorkOrderStatus',
    'APQPStage',
    'ProcessStatus',
    'StepExecution',

    # MES Standard (Full Traceability & Compliance)
    'EquipmentType',
    'EquipmentStatus',
    'EquipmentQuerySet',
    'EquipmentManager',
    'Equipments',
    'SamplingRuleSet',
    'SamplingRule',
    'SamplingRuleType',
    'SamplingTriggerState',
    'SamplingTriggerManager',
    'SamplingAuditLog',
    'SamplingAnalytics',
    'MaterialLot',
    'MaterialUsage',
    'TimeEntry',
    'BOM',
    'BOMLine',
    'AssemblyUsage',
    'WorkCenter',
    'Shift',
    'ScheduleSlot',
    'DowntimeEvent',

    # Remanufacturing Add-on
    'Core',
    'HarvestedComponent',
    'DisassemblyBOMLine',

    # Integrations
    'ExternalAPIOrderIdentifier',
    'HubSpotSyncLog',

    # QMS (Quality Management System including 3D Models, Annotations, and CAPA)
    'QualityErrorsList',
    'DefectSeverity',
    'QualityReportDefect',
    'QualityReports',
    'MeasurementResult',
    'EquipmentUsage',
    'QaApproval',
    'QuarantineDisposition',
    'StepTransitionLog',
    'ModelProcessingStatus',
    'ThreeDModel',
    'HeatMapAnnotations',
    'CapaType',
    'CapaSeverity',
    'CapaStatus',
    'CapaTaskType',
    'CapaTaskStatus',
    'CapaTaskCompletionMode',
    'RcaMethod',
    'RcaReviewStatus',
    'RootCauseVerificationStatus',
    'RootCauseCategory',
    'RootCauseRole',
    'EffectivenessResult',
    'CAPA',
    'CapaTasks',
    'CapaTaskAssignee',
    'RcaRecord',
    'FiveWhys',
    'Fishbone',
    'RootCause',
    'CapaVerification',

    # Generated Reports (PDF Audit Trail)
    'GeneratedReport',

    # Training & Calibration
    'TrainingType',
    'TrainingRecord',
    'TrainingRequirement',
    'CalibrationRecordQuerySet',
    'CalibrationRecordManager',
    'CalibrationRecord',

    # SPC (Statistical Process Control)
    'SPCBaseline',
    'ChartType',
    'BaselineStatus',

    # DMS (Optional AI/LLM Module - Document Intelligence)
    'DocChunk',
    'ChatSession',
]

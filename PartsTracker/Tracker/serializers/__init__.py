# Export all serializers for backward compatibility
# This allows `from Tracker.serializer import SomeSerializer` to continue working

from .core import (
    # Mixins
    SecureModelMixin,
    BulkOperationsMixin,
    DynamicFieldsMixin,

    # User & Company
    UserSelectSerializer,
    EmployeeSelectSerializer,
    CompanySerializer,
    CustomerSerializer,
    UserDetailSerializer,
    UserSerializer,
    UserInvitationSerializer,

    # Auth & Password
    CustomAllAuthPasswordResetForm,
    PasswordResetSerializer,
    GroupSerializer,

    # Audit Logs
    AuditLogSerializer,
    LogEntrySerializer,
    ContentTypeSerializer,

    # Bulk Operations
    BulkSoftDeleteSerializer,
    BulkRestoreSerializer,

    # Approval Workflow
    ApprovalTemplateSerializer,
    ApprovalResponseSerializer,
    ApprovalRequestSerializer,
)

from .mes_lite import (
    # Orders
    OrdersSerializer,
    TrackerPageOrderSerializer,

    # Parts
    PartsSerializer,
    PartSelectSerializer,
    CustomerPartsSerializer,

    # Work Orders
    WorkOrderSerializer,
    WorkOrderListSerializer,
    WorkOrderCSVUploadSerializer,
    WorkOrderUploadSerializer,

    # Steps & Processes
    StageSerializer,
    StepsSerializer,
    StepSerializer,
    ProcessStepSerializer,
    StepEdgeSerializer,
    PartTypesSerializer,
    PartTypeSerializer,
    PartTypeSelectSerializer,
    ProcessesSerializer,
    ProcessWithStepsSerializer,

    # Equipment
    EquipmentTypeSerializer,
    EquipmentsSerializer,
    EquipmentSerializer,
    EquipmentSelectSerializer,

    # Bulk Operations
    BulkAddPartsSerializer,
    BulkRemovePartsSerializer,
    StepAdvancementSerializer,
    IncrementStepSerializer,
    BulkStepAdvancementSerializer,
)

from .integrations import (
    # HubSpot Integration
    ExternalAPIOrderIdentifierSerializer,
    HubSpotSyncLogSerializer,
)

from .qms import (
    # Quality & Errors
    QualityErrorsListSerializer,
    ErrorTypeSerializer,

    # Measurements
    MeasurementDefinitionSerializer,
    MeasurementResultSerializer,

    # Quality Reports
    QualityReportsSerializer,
    QuarantineDispositionSerializer,

    # Sampling Rules
    SamplingRuleSerializer,
    SamplingRuleSetSerializer,
    ResolvedSamplingRuleSetSerializer,
    StepWithResolvedRulesSerializer,

    # Sampling Rules Updates
    SamplingRuleUpdateSerializer,
    SamplingRuleWriteSerializer,
    StepSamplingRulesUpdateSerializer,
    StepSamplingRulesWriteSerializer,
    StepSamplingRulesResponseSerializer,

    # Analytics
    SamplingAnalyticsSerializer,
    SamplingAuditLogSerializer,
    SamplingTriggerStateSerializer,

    # Notifications
    NotificationScheduleSerializer,
    NotificationPreferenceSerializer,

    # CAPA
    RootCauseSerializer,
    FiveWhysSerializer,
    FishboneSerializer,
    RcaRecordSerializer,
    CapaTaskAssigneeSerializer,
    CapaTasksSerializer,
    CapaVerificationSerializer,
    CAPASerializer,
)

from .dms import (
    # Documents
    DocumentsSerializer,
    DocumentSerializer,

    # 3D Models
    ThreeDModelSerializer,
    HeatMapAnnotationsSerializer,

    # Chat Sessions
    ChatSessionSerializer,
)

from .spc import (
    # SPC Baselines
    SPCBaselineSerializer,
    SPCBaselineListSerializer,
    SPCBaselineFreezeSerializer,
)

from .mes_standard import (
    # Work Centers
    WorkCenterSerializer,
    WorkCenterSelectSerializer,

    # Shifts & Scheduling
    ShiftSerializer,
    ScheduleSlotSerializer,

    # Downtime
    DowntimeEventSerializer,

    # Material Lots
    MaterialLotSerializer,
    MaterialLotSplitSerializer,
    MaterialUsageSerializer,

    # Time Entries
    TimeEntrySerializer,
    ClockInSerializer,

    # BOMs
    BOMSerializer,
    BOMListSerializer,
    BOMLineSerializer,

    # Assembly Usage
    AssemblyUsageSerializer,
    AssemblyRemoveSerializer,
)

from .reman import (
    # Cores
    CoreSerializer,
    CoreListSerializer,
    CoreScrapSerializer,

    # Harvested Components
    HarvestedComponentSerializer,
    HarvestedComponentScrapSerializer,
    HarvestedComponentAcceptSerializer,

    # Disassembly BOM
    DisassemblyBOMLineSerializer,
)

from .csv_import import (
    # CSV Import
    ImportMode,
    BaseCSVImportSerializer,
    PartTypesCSVImportSerializer,
    PartsCSVImportSerializer,
    OrdersCSVImportSerializer,
    WorkOrderCSVImportSerializer,
    EquipmentCSVImportSerializer,
    QualityReportsCSVImportSerializer,
    get_csv_import_serializer,
    get_or_create_import_serializer,
    create_import_serializer_for_model,
)

from .training import (
    # Training Management
    TrainingTypeSerializer,
    TrainingRecordSerializer,
    TrainingRequirementSerializer,
)

from .calibration import (
    # Calibration Management
    CalibrationRecordSerializer,
    CalibrationStatsSerializer,
)

__all__ = [
    # Core - Mixins & Base Infrastructure
    'SecureModelMixin',
    'BulkOperationsMixin',
    'DynamicFieldsMixin',

    # Core - Users & Auth
    'UserSelectSerializer',
    'EmployeeSelectSerializer',
    'CompanySerializer',
    'CustomerSerializer',
    'UserDetailSerializer',
    'UserSerializer',
    'UserInvitationSerializer',
    'CustomAllAuthPasswordResetForm',
    'PasswordResetSerializer',
    'GroupSerializer',

    # Core - Audit Logs & Content Types
    'AuditLogSerializer',
    'LogEntrySerializer',
    'ContentTypeSerializer',

    # Core - Bulk Operations
    'BulkSoftDeleteSerializer',
    'BulkRestoreSerializer',

    # Core - Approvals
    'ApprovalTemplateSerializer',
    'ApprovalResponseSerializer',
    'ApprovalRequestSerializer',

    # MES Lite - Manufacturing Operations
    'OrdersSerializer',
    'TrackerPageOrderSerializer',
    'PartsSerializer',
    'PartSelectSerializer',
    'CustomerPartsSerializer',
    'WorkOrderSerializer',
    'WorkOrderListSerializer',
    'WorkOrderCSVUploadSerializer',
    'WorkOrderUploadSerializer',
    'StageSerializer',
    'StepsSerializer',
    'StepSerializer',
    'ProcessStepSerializer',
    'StepEdgeSerializer',
    'PartTypesSerializer',
    'PartTypeSerializer',
    'PartTypeSelectSerializer',
    'ProcessesSerializer',
    'ProcessWithStepsSerializer',
    'EquipmentTypeSerializer',
    'EquipmentsSerializer',
    'EquipmentSerializer',
    'EquipmentSelectSerializer',
    'BulkAddPartsSerializer',
    'BulkRemovePartsSerializer',
    'StepAdvancementSerializer',
    'IncrementStepSerializer',
    'BulkStepAdvancementSerializer',

    # QMS - Quality Management
    'QualityErrorsListSerializer',
    'ErrorTypeSerializer',
    'MeasurementDefinitionSerializer',
    'MeasurementResultSerializer',
    'QualityReportsSerializer',
    'QuarantineDispositionSerializer',
    'SamplingRuleSerializer',
    'SamplingRuleSetSerializer',
    'ResolvedSamplingRuleSetSerializer',
    'StepWithResolvedRulesSerializer',
    'SamplingRuleUpdateSerializer',
    'SamplingRuleWriteSerializer',
    'StepSamplingRulesUpdateSerializer',
    'StepSamplingRulesWriteSerializer',
    'StepSamplingRulesResponseSerializer',
    'SamplingAnalyticsSerializer',
    'SamplingAuditLogSerializer',
    'SamplingTriggerStateSerializer',
    'NotificationScheduleSerializer',
    'NotificationPreferenceSerializer',
    'RootCauseSerializer',
    'FiveWhysSerializer',
    'FishboneSerializer',
    'RcaRecordSerializer',
    'CapaTaskAssigneeSerializer',
    'CapaTasksSerializer',
    'CapaVerificationSerializer',
    'CAPASerializer',

    # DMS - Document Management
    'DocumentsSerializer',
    'DocumentSerializer',
    'ThreeDModelSerializer',
    'HeatMapAnnotationsSerializer',
    'ChatSessionSerializer',

    # Integrations - HubSpot
    'ExternalAPIOrderIdentifierSerializer',
    'HubSpotSyncLogSerializer',

    # SPC - Statistical Process Control
    'SPCBaselineSerializer',
    'SPCBaselineListSerializer',
    'SPCBaselineFreezeSerializer',

    # MES Standard - Work Centers
    'WorkCenterSerializer',
    'WorkCenterSelectSerializer',

    # MES Standard - Shifts & Scheduling
    'ShiftSerializer',
    'ScheduleSlotSerializer',

    # MES Standard - Downtime
    'DowntimeEventSerializer',

    # MES Standard - Material Lots
    'MaterialLotSerializer',
    'MaterialLotSplitSerializer',
    'MaterialUsageSerializer',

    # MES Standard - Time Entries
    'TimeEntrySerializer',
    'ClockInSerializer',

    # MES Standard - BOMs
    'BOMSerializer',
    'BOMListSerializer',
    'BOMLineSerializer',

    # MES Standard - Assembly Usage
    'AssemblyUsageSerializer',
    'AssemblyRemoveSerializer',

    # Reman - Cores
    'CoreSerializer',
    'CoreListSerializer',
    'CoreScrapSerializer',

    # Reman - Harvested Components
    'HarvestedComponentSerializer',
    'HarvestedComponentScrapSerializer',
    'HarvestedComponentAcceptSerializer',

    # Reman - Disassembly BOM
    'DisassemblyBOMLineSerializer',

    # CSV Import/Export
    'ImportMode',
    'BaseCSVImportSerializer',
    'PartTypesCSVImportSerializer',
    'PartsCSVImportSerializer',
    'OrdersCSVImportSerializer',
    'WorkOrderCSVImportSerializer',
    'EquipmentCSVImportSerializer',
    'QualityReportsCSVImportSerializer',
    'get_csv_import_serializer',
    'get_or_create_import_serializer',
    'create_import_serializer_for_model',

    # Training Management
    'TrainingTypeSerializer',
    'TrainingRecordSerializer',
    'TrainingRequirementSerializer',

    # Calibration Management
    'CalibrationRecordSerializer',
    'CalibrationStatsSerializer',
]

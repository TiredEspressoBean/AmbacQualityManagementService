"""
URL configuration for PartsTracker project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path
from django.urls.conf import include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter


# Note: Updated to use new modular viewsets structure
from Tracker.viewsets import *
from Tracker.ai_viewsets import AISearchViewSet, QueryViewSet, EmbeddingViewSet, LLMConfigViewSet
from Tracker.api_views import (
    get_csrf_token, get_user_api_token,
    ThrottledLoginView, ThrottledPasswordResetView,
    ThrottledPasswordResetConfirmView, ThrottledRegisterView,
)
from dj_rest_auth.views import PasswordResetConfirmView, PasswordResetView

from Tracker.health_views import health_check, ready_check
from Tracker.viewsets.tenant import (
    CurrentTenantView, TenantSettingsView, TenantLogoView, TenantViewSet, SignupView,
    TenantGroupViewSet, PermissionListView, PresetListView, EffectivePermissionsView,
    UserTenantsView, SwitchTenantView, DemoResetView, TenantLLMProviderViewSet
)
from Tracker.viewsets.scheduling_setup import (
    StepEquipmentAffinityViewSet, StepTimingViewSet, WorkCenterChangeoverViewSet,
)
from Tracker.viewsets.master_workbook import MasterWorkbookViewSet
from Tracker.viewsets.receipts import ReceiptsViewSet
from Tracker.viewsets.shipping import CustomerShipmentViewSet
from Tracker.viewsets.scan import ScanViewSet

urlpatterns = [
    # Health check endpoints for Azure Container Apps
    path('health/', health_check, name='health_check'),
    path('ready/', ready_check, name='ready_check'),

    path('admin/doc/', include('django.contrib.admindocs.urls')),
    path('admin/', admin.site.urls, name='admin'),

    path("accounts/", include("allauth.urls")),
]

urlpatterns += staticfiles_urlpatterns()

urlpatterns += [
    path("", include("integrations.urls")),
]

# API starts here with Auth


urlpatterns += [
    path(
        "password/reset/confirm/<slug:uidb64>/<slug:token>/",
        ThrottledPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    # Note: UserDetailsView is imported via wildcard from Tracker.viewsets
    path("auth/user/", UserDetailsView.as_view(), name="rest_user_details"),
    # Throttled overrides MUST precede the dj_rest_auth includes so they take
    # precedence for these abuse-prone endpoints (login brute-force, account
    # spam, reset-email bombing). The includes still serve the rest
    # (logout, password-change, verify-email, etc.).
    path("auth/login/", ThrottledLoginView.as_view()),
    path("auth/password/reset/", ThrottledPasswordResetView.as_view()),
    path("auth/registration/", ThrottledRegisterView.as_view()),
    path("auth/", include("dj_rest_auth.urls")),
    path("auth/registration/", include("dj_rest_auth.registration.urls")),
    path("api/csrf/", get_csrf_token),
    path("api/user/token/", get_user_api_token, name="get_user_api_token"),

    # Tenant endpoints
    path("api/tenant/current/", CurrentTenantView.as_view(), name="tenant-current"),
    path("api/tenant/settings/", TenantSettingsView.as_view(), name="tenant-settings"),
    path("api/tenant/logo/", TenantLogoView.as_view(), name="tenant-logo"),
    path("api/tenant/demo-reset/", DemoResetView.as_view(), name="tenant-demo-reset"),
    path("api/tenants/signup/", SignupView.as_view(), name="tenant-signup"),

    # User tenant management (multi-tenant switching)
    path("api/user/tenants/", UserTenantsView.as_view(), name="user-tenants"),
    path("api/user/tenants/switch/", SwitchTenantView.as_view(), name="switch-tenant"),

    # Tenant Group Management - self-service endpoints
    path("api/permissions/", PermissionListView.as_view(), name="permission-list"),
    path("api/presets/", PresetListView.as_view(), name="preset-list"),
    path("api/users/<int:user_id>/effective-permissions/", EffectivePermissionsView.as_view(), name="effective-permissions"),
    path("api/users/me/effective-permissions/", EffectivePermissionsView.as_view(), name="my-effective-permissions"),

    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
]
router = DefaultRouter()
router.register(r'TrackerOrders', TrackerOrderViewSet, basename="TrackerOrders")
router.register(r'Parts', PartsViewSet, basename="Parts")
router.register(r'Orders', OrdersViewSet, basename="Orders")
router.register(r'OrderLines', OrderLineViewSet, basename="OrderLines")
router.register(r'QualityReports', QualityReportViewSet, basename="QualityReports")
router.register(r"Employees-Options", EmployeeSelectViewSet, basename="Employees-Options")
router.register(r"Equipment-Options", EquipmentSelectViewSet, basename="Equipment-Options")
router.register(r"MilestoneTemplates", MilestoneTemplateViewSet, basename="MilestoneTemplates")
router.register(r"Milestones", MilestoneViewSet, basename="Milestones")
router.register(r"Customers", CustomerViewSet, basename="Customers")
router.register(r"Companies", CompanyViewSet, basename="Companies")
router.register(r"Steps", StepsViewSet, basename="Steps")
router.register(r"StepExecutions", StepExecutionViewSet, basename="StepExecutions")
router.register(r"Processes", ProcessViewSet, basename="Processes")
router.register(r"PartTypes", PartTypeViewSet, basename="PartTypes")
router.register(r"WorkOrders", WorkOrderViewSet, basename="WorkOrders")
router.register(r"Equipment", EquipmentViewSet, basename="equipment")
router.register(r"Equipment-types", EquipmentTypeViewSet, basename="equipmenttype")
router.register(r"Error-types", ErrorTypeViewSet, basename="errortype")
router.register(r"Documents", DocumentViewSet, basename="documents")
router.register(r"DocumentTypes", DocumentTypeViewSet, basename="documenttypes")
router.register(r'Processes_with_steps', ProcessWithStepsViewSet)
router.register("Sampling-rule-sets", SamplingRuleSetViewSet, basename="sampling-rule-sets")
router.register("Sampling-rules", SamplingRuleViewSet, basename="sampling-rules")
router.register("SamplingSeverityStates", SamplingSeverityStateViewSet, basename="samplingseveritystates")
router.register("MeasurementDefinitions", MeasurementsDefinitionViewSet)
router.register("content-types", ContentTypeViewSet, basename="contenttype")
router.register("auditlog", LogEntryViewSet, basename="auditlog")
router.register("User", UserViewSet, basename="User")
router.register("TenantGroups", TenantGroupViewSet, basename="TenantGroups")
router.register("Tenants", TenantViewSet, basename="Tenants")
router.register("TenantLLMProviders", TenantLLMProviderViewSet, basename="TenantLLMProviders")
router.register("QuarantineDispositions", QuarantineDispositionViewSet, basename="QuarantineDispositions")
router.register("SupplierQualifications", SupplierQualificationViewSet, basename="SupplierQualifications")
router.register("PartApprovals", PartApprovalViewSet, basename="PartApprovals")
router.register("HeatMapAnnotation", HeatMapAnnotationsViewSet, basename="HeatMapAnnotation")
router.register("ThreeDModels", ThreeDModelViewSet, basename="ThreeDModels")

# User invitation endpoints
router.register("UserInvitations", UserInvitationViewSet, basename="UserInvitations")

# Change Control endpoints (PCR / PCO / PCN)
router.register(
    "process-change-requests",
    ProcessChangeRequestViewSet,
    basename="process-change-requests",
)
router.register(
    "process-change-orders",
    ProcessChangeOrderViewSet,
    basename="process-change-orders",
)
router.register(
    "process-change-notices",
    ProcessChangeNoticeViewSet,
    basename="process-change-notices",
)

# Approval Workflow endpoints
router.register("ApprovalTemplates", ApprovalTemplateViewSet, basename="ApprovalTemplates")
router.register("ApprovalRequests", ApprovalRequestViewSet, basename="ApprovalRequests")
router.register("ApprovalResponses", ApprovalResponseViewSet, basename="ApprovalResponses")

# CAPA (Corrective and Preventive Action) endpoints
router.register("CAPAs", CAPAViewSet, basename="CAPAs")
router.register("CapaTasks", CapaTasksViewSet, basename="CapaTasks")
router.register("RcaRecords", RcaRecordViewSet, basename="RcaRecords")
router.register("CapaVerifications", CapaVerificationViewSet, basename="CapaVerifications")
router.register("FiveWhys", FiveWhysViewSet, basename="FiveWhys")
router.register("Fishbone", FishboneViewSet, basename="Fishbone")

# Step Override endpoints (rollback approvals)
router.register("StepOverrides", StepOverrideViewSet, basename="StepOverrides")

# FPI (First Piece Inspection) endpoints
router.register("FPIRecords", FPIRecordViewSet, basename="FPIRecords")

# Step Execution Measurement endpoints
router.register("StepExecutionMeasurements", StepExecutionMeasurementViewSet, basename="StepExecutionMeasurements")

# AI/RAG endpoints for LangGraph integration
router.register("ai/search", AISearchViewSet, basename="ai-search")
router.register("ai/query", QueryViewSet, basename="ai-query")
router.register("ai/embedding", EmbeddingViewSet, basename="ai-embedding")
router.register("ai/llm", LLMConfigViewSet, basename="ai-llm")

# Scope endpoint for graph traversal queries
router.register("scope", ScopeView, basename="scope")

# Reports endpoint for PDF generation
router.register("reports", ReportViewSet, basename="reports")

# SPC (Statistical Process Control) endpoints
router.register("spc", SPCViewSet, basename="spc")
router.register("spc-baselines", SPCBaselineViewSet, basename="spc-baselines")

# Dashboard (Quality Analytics) endpoints
router.register("dashboard", DashboardViewSet, basename="dashboard")

# Chat Sessions (AI chat history)
router.register("ChatSessions", ChatSessionViewSet, basename="ChatSessions")

# ===== MES STANDARD VIEWSETS =====
# Work Centers
router.register(r'WorkCenters', WorkCenterViewSet, basename='WorkCenters')
router.register(r'WorkCenters-Options', WorkCenterSelectViewSet, basename='WorkCenters-Options')
router.register(r'UserWorkCenterMemberships', UserWorkCenterMembershipViewSet, basename='UserWorkCenterMemberships')

# Shifts & Scheduling
router.register(r'Shifts', ShiftViewSet, basename='Shifts')
router.register(r'ScheduleSlots', ScheduleSlotViewSet, basename='ScheduleSlots')

# Downtime
router.register(r'DowntimeEvents', DowntimeEventViewSet, basename='DowntimeEvents')

# Shift notes (human-authored floor handoff)
router.register(r'ShiftNotes', ShiftNoteViewSet, basename='ShiftNotes')

# Work queue (aggregate: ranked WO×step ready-or-blocked rows for the operator home)
router.register(r'WorkQueue', WorkQueueViewSet, basename='WorkQueue')

# Material Lots & Usage
router.register(r'Materials', MaterialViewSet, basename='Materials')
router.register(r'MaterialLots', MaterialLotViewSet, basename='MaterialLots')
router.register(r'MasterWorkbook', MasterWorkbookViewSet, basename='MasterWorkbook')
router.register(r'Receipts', ReceiptsViewSet, basename='Receipts')
router.register(r'StorageLocations', StorageLocationViewSet, basename='StorageLocations')
router.register(r'MaterialUsages', MaterialUsageViewSet, basename='MaterialUsages')

# Outside processing (subcontract shipments — Flow B)
router.register(r'OutsideProcessShipments', OutsideProcessShipmentViewSet, basename='OutsideProcessShipments')
router.register(r'CustomerShipments', CustomerShipmentViewSet, basename='CustomerShipments')
router.register(r'scan', ScanViewSet, basename='scan')

# Unified incoming-inspection worklist (purchased lots + subcontract returns)
router.register(r'IncomingInspection', IncomingInspectionViewSet, basename='IncomingInspection')
router.register(r'InspectionInbox', InspectionInboxViewSet, basename='InspectionInbox')

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
router.register(r'RepairCodes', RepairCodeViewSet, basename='RepairCodes')
router.register(r'RebuildScopePresets', RebuildScopePresetViewSet, basename='RebuildScopePresets')
router.register(r'RebuildSlotOverrides', RebuildSlotOverrideViewSet, basename='RebuildSlotOverrides')

# ===== LIFE TRACKING VIEWSETS =====
# The classes, serializers and services all existed; only the registration was
# missing, so the whole feature had no API surface. The frontend's ModelEditorPage
# already lists these three basenames, so its editors were pointing at 404s.
router.register(r'LifeLimitDefinitions', LifeLimitDefinitionViewSet, basename='LifeLimitDefinitions')
router.register(r'PartTypeLifeLimits', PartTypeLifeLimitViewSet, basename='PartTypeLifeLimits')
router.register(r'LifeTracking', LifeTrackingViewSet, basename='LifeTracking')
router.register(r'Schedules', ScheduleViewSet, basename='Schedules')
router.register(r'ScheduledTasks', ScheduledTaskViewSet, basename='ScheduledTasks')
router.register(r'Fixtures', FixtureViewSet, basename='Fixtures')
router.register(r'PlantCalendarExceptions', PlantCalendarExceptionViewSet, basename='PlantCalendarExceptions')
router.register(r'LaborCalendarBlocks', LaborCalendarBlockViewSet, basename='LaborCalendarBlocks')
router.register(r'OvertimeWindows', OvertimeWindowViewSet, basename='OvertimeWindows')
# The scheduler's setup data (standard times, machine eligibility, changeovers).
router.register(r'StepTimings', StepTimingViewSet, basename='StepTimings')
router.register(r'StepEquipmentAffinities', StepEquipmentAffinityViewSet, basename='StepEquipmentAffinities')
router.register(r'WorkCenterChangeovers', WorkCenterChangeoverViewSet, basename='WorkCenterChangeovers')

# ===== DWI VIEWSETS =====
router.register(r'Substeps', SubstepViewSet, basename='Substeps')
router.register(r'SubstepResources', SubstepResourceViewSet, basename='SubstepResources')
router.register(r'SubstepTranslations', SubstepTranslationViewSet, basename='SubstepTranslations')
router.register(r'SubstepCompletions', SubstepCompletionViewSet, basename='SubstepCompletions')
router.register(r'SubstepGateCompletions', SubstepGateCompletionViewSet, basename='SubstepGateCompletions')
router.register(r'SubstepResponses', SubstepResponseViewSet, basename='SubstepResponses')
router.register(r'BatchExecutions', BatchExecutionViewSet, basename='BatchExecutions')
router.register(r'SamplingDecisions', SamplingDecisionViewSet, basename='SamplingDecisions')

# ===== TRAINING VIEWSETS =====
router.register(r'TrainingTypes', TrainingTypeViewSet, basename='TrainingTypes')
router.register(r'TrainingRecords', TrainingRecordViewSet, basename='TrainingRecords')
router.register(r'TrainingRequirements', TrainingRequirementViewSet, basename='TrainingRequirements')
router.register(r'JobRoles', JobRoleViewSet, basename='JobRoles')

# ===== CALIBRATION VIEWSETS =====
router.register(r'CalibrationRecords', CalibrationRecordViewSet, basename='CalibrationRecords')

# ===== NOTIFICATION RULES =====
# Phase 3 per-scope rule endpoints + ExternalContacts.
router.register(
    r'notifications/rules/tenant',
    TenantRuleViewSet,
    basename='notification-rules-tenant',
)
router.register(
    r'notifications/rules/customer',
    CustomerRuleViewSet,
    basename='notification-rules-customer',
)
router.register(
    r'notifications/rules/personal',
    PersonalRuleViewSet,
    basename='notification-rules-personal',
)
router.register(
    r'notifications/external-contacts',
    ExternalContactViewSet,
    basename='notification-external-contacts',
)
# The in-app feed — the reader InAppChannel writes toward.
router.register(
    r'notifications/feed',

    NotificationFeedViewSet,
    basename='notification-feed',
)

# Phase 3.5 scheduled notification deliveries.
router.register(
    r'notifications/schedules/tenant',
    TenantScheduleViewSet,
    basename='notification-schedules-tenant',
)
router.register(
    r'notifications/schedules/customer',
    CustomerScheduleViewSet,
    basename='notification-schedules-customer',
)
router.register(
    r'notifications/schedules/personal',
    PersonalScheduleViewSet,
    basename='notification-schedules-personal',
)

urlpatterns += [
    path("media/<path:path>", serve_media_iframe_safe),
    path('api/', include(router.urls)),  # ✅ Adds /api/TrackerOrders/
    path("api/orders/<uuid:order_id>/parts/", PartsByOrderView.as_view(), name="order-parts-list"),
    path("api/CompetenceMatrix/", CompetenceMatrixView.as_view(), name="competence-matrix"),
    # Legacy event-type catalog kept at this path; Phase 3 also exposes it at
    # /api/notifications/events/ below for the new frontend.
    path("api/NotificationEventTypes/", NotificationEventTypeCatalogView.as_view(), name="notification-event-types"),
    path("api/notifications/events/", NotificationEventTypeCatalogView.as_view(), name="notifications-events"),
    path(
        "api/notifications/schedules/providers/",
        ScheduledContentProviderCatalogView.as_view(),
        name="notifications-schedule-providers",
    ),
]
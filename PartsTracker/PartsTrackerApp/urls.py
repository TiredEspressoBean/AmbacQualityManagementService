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
from django.urls import path
from django.urls.conf import include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter


from Tracker import views
# Note: Updated to use new modular viewsets structure
from Tracker.viewsets import *
from Tracker.ai_viewsets import AISearchViewSet, QueryViewSet, EmbeddingViewSet
from Tracker.api_views import get_csrf_token, get_user_api_token
from Tracker.forms import DealForm
from Tracker.generic_views import GenericCreateEntry, GenericUpdateEntry, GenericDeleteEntry, GenericViewEntry
from Tracker.hubspot_view import hubspot_webhook
from Tracker.views import OrderUpdateView, OrderCreateView, ErrorFormView
from dj_rest_auth.views import PasswordResetConfirmView, PasswordResetView

from Tracker.AI_view import chat_ai_view
from Tracker.health_views import health_check, ready_check
from Tracker.viewsets.tenant import (
    CurrentTenantView, TenantSettingsView, TenantLogoView, TenantViewSet, SignupView,
    TenantGroupViewSet, PermissionListView, PresetListView, EffectivePermissionsView,
    UserTenantsView, SwitchTenantView
)

urlpatterns = [
    # Health check endpoints for Azure Container Apps
    path('health/', health_check, name='health_check'),
    path('ready/', ready_check, name='ready_check'),


    path("accounts/", include("django.contrib.auth.urls")),

    path('admin/doc/', include('django.contrib.admindocs.urls')),
    path('admin/', admin.site.urls, name='admin'),
    path('', views.home, name='home'),
    path('tracker/', views.tracker, name='tracker'),
    path('part_view/<int:part_id>/', views.part_view, name='part_view'),
    path('deal_view/<int:order_id>/', views.deal_view, name='deal_view'),

    # TODO: Think I got rid of all uses of these two but not sure?
    path('edit_part/<int:part_id>/', views.edit_part, name='edit_part'),

    path('edit_deal/<int:deal_id>/', views.edit_deal, name='edit_deal'),
    path('edit/', views.edit, name='edit'),

    path("accounts/", include("allauth.urls")),

    path("create/<str:model_name>", GenericCreateEntry.as_view(), name="create_page"),

    path("update/<str:model_name>/<int:pk>", GenericUpdateEntry.as_view(), name="update_entry"),

    path("delete/<str:model_name>/<int:pk>", GenericDeleteEntry, name="delete_entry"),

    path("view/<str:model_name>/<int:pk>", GenericViewEntry.as_view(), name="view_entry"),

    path("QA", views.qa_page.as_view(), name="QA"),

    path("error_form/<int:part_id>", ErrorFormView.as_view(), name="error_form"),

    path("qa_orders", views.qa_orders, name="qa_orders"),

    path("bulk_edit/<int:order_id>", views.bulk_edit_parts, name="bulk_edit"),

    path('deals/<int:order_id>/archive/', views.archive_deal, name='archive_deal'),

    # path("add_parts/<int:order_id>", name="add_parts"),)
]

urlpatterns += staticfiles_urlpatterns()

urlpatterns += [
    path("deals/lineitem/new/", views.add_lineitem_partial, name="add_lineitem_partial"),

    path('bulk_create_parts/', views.BulkCreateParts.as_view(), name='bulk_create_parts'),

    path("orders/<int:order_id>/export-parts/", views.export_parts_csv, name="export_parts_csv"),

    path("orders/<int:order_id>/upload-parts/", views.upload_parts_csv, name="upload_parts_csv"),
]

urlpatterns += [
    path("deals/new/", OrderCreateView.as_view(), name="deal_create"),
    path("deals/<int:order_id>/edit/", OrderUpdateView.as_view(), name="deal_edit"),

    path("deal_pass/<int:order_id>/", views.deal_pass, name="deal_pass"),

    path("partials/parttype_row/", views.add_parttype_partial, name="add_parttype_partial"),
    path("partials/process_row/", views.add_process_partial, name="add_process_partial"),

    path('partials/parttype_select/', views.parttype_select_partial, name='parttype_select_partial'),

    path('partials/process_select/', views.process_select_partial, name='process_select_partial'),

    path("partials/refresh-lineitems/", views.refresh_parttype_process_selects,
         name="refresh_parttype_process_selects"),

    path("tables/generic_table_view/<str:model_name>", views.generic_table_view, name="generic_table_view"),

    path("edit_model_page/<str:model_name>", views.edit_model_page, name="edit_model_page"),
]

urlpatterns += [
    path("part_docs", views.list_part_docs, name="list_part_docs"),
    path("download/<str:model_name>/<int:pk>/<str:field>/", views.download_file, name="download_file"),

    path("upload_part_doc", views.upload_part_doc, name="upload_part_doc"),

    path("history", views.history, name="history"),
]

urlpatterns += [
    path("chat/", chat_ai_view.as_view(), name="chat_ai_view"),

    path("webhooks/hubspot/", hubspot_webhook, name="hubspot_webhook"),
]

# API starts here with Auth


urlpatterns += [
    path(
        "password/reset/confirm/<slug:uidb64>/<slug:token>/",
        PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    # Note: UserDetailsView is imported via wildcard from Tracker.viewsets
    path("auth/user/", UserDetailsView.as_view(), name="rest_user_details"),
    path("auth/", include("dj_rest_auth.urls")),
    path("auth/registration/", include("dj_rest_auth.registration.urls")),
    path("api/csrf/", get_csrf_token),
    path("api/user/token/", get_user_api_token, name="get_user_api_token"),

    # Tenant endpoints
    path("api/tenant/current/", CurrentTenantView.as_view(), name="tenant-current"),
    path("api/tenant/settings/", TenantSettingsView.as_view(), name="tenant-settings"),
    path("api/tenant/logo/", TenantLogoView.as_view(), name="tenant-logo"),
    path("api/tenants/signup/", SignupView.as_view(), name="tenant-signup"),

    # User tenant management (multi-tenant switching)
    path("api/user/tenants/", UserTenantsView.as_view(), name="user-tenants"),
    path("api/user/tenants/switch/", SwitchTenantView.as_view(), name="switch-tenant"),

    # Tenant Group Management - self-service endpoints
    path("api/permissions/", PermissionListView.as_view(), name="permission-list"),
    path("api/presets/", PresetListView.as_view(), name="preset-list"),
    path("api/users/<uuid:user_id>/effective-permissions/", EffectivePermissionsView.as_view(), name="effective-permissions"),
    path("api/users/me/effective-permissions/", EffectivePermissionsView.as_view(), name="my-effective-permissions"),
    path("__reload__/", include(("django_browser_reload.urls", "django_browser_reload"),
                                namespace="django_browser_reload")),

    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
]
router = DefaultRouter()
router.register(r'TrackerOrders', TrackerOrderViewSet, basename="TrackerOrders")
router.register(r'Parts', PartsViewSet, basename="Parts")
router.register(r'Orders', OrdersViewSet, basename="Orders")
router.register(r'ErrorReports', QualityReportViewSet, basename="ErrorReports")
router.register(r"Employees-Options", EmployeeSelectViewSet, basename="Employees-Options")
router.register(r"Equipment-Options", EquipmentSelectViewSet, basename="Equipment-Options")
router.register(r"HubspotGates", HubspotGatesViewSet, basename="HubspotGates")
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
router.register("MeasurementDefinitions", MeasurementsDefinitionViewSet)
router.register("content-types", ContentTypeViewSet, basename="contenttype")
router.register("auditlog", LogEntryViewSet, basename="auditlog")
router.register("User", UserViewSet, basename="User")
router.register("Groups", GroupViewSet, basename="Groups")
router.register("TenantGroups", TenantGroupViewSet, basename="TenantGroups")
router.register("Tenants", TenantViewSet, basename="Tenants")
router.register("QuarantineDispositions", QuarantineDispositionViewSet, basename="QuarantineDispositions")
router.register("HeatMapAnnotation", HeatMapAnnotationsViewSet, basename="HeatMapAnnotation")
router.register("ThreeDModels", ThreeDModelViewSet, basename="ThreeDModels")

# Notification preferences endpoint
router.register("NotificationPreferences", NotificationPreferenceViewSet, basename="NotificationPreferences")

# User invitation endpoints
router.register("UserInvitations", UserInvitationViewSet, basename="UserInvitations")

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

urlpatterns += [
    path("media/<path:path>", serve_media_iframe_safe),
    path('api/', include(router.urls)),  # ✅ Adds /api/TrackerOrders/
    path("api/orders/<uuid:order_id>/parts/", PartsByOrderView.as_view(), name="order-parts-list")
]
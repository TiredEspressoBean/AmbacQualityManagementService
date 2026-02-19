import {createRootRoute, createRoute, createRouter, lazyRouteComponent, ErrorComponent} from "@tanstack/react-router"
import type { QueryClient } from "@tanstack/react-query"

import Layout from "@/components/layout";
import Home from "@/pages/Home";
import Login from '@/components/auth/Login'
import SignupPage from '@/pages/SignupPage'
import { PasswordResetConfirm } from "@/pages/PasswordResetConfirmForm";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { AlertCircle, RefreshCw } from "lucide-react";

// Default loading component for route transitions
function DefaultPendingComponent() {
    return (
        <div className="flex flex-col gap-4 p-6">
            <Skeleton className="h-8 w-64" />
            <Skeleton className="h-4 w-full max-w-md" />
            <div className="flex gap-4 mt-4">
                <Skeleton className="h-32 w-full" />
            </div>
        </div>
    );
}

// Default error component for route errors
function DefaultErrorComponent({ error, reset }: { error: Error; reset?: () => void }) {
    return (
        <div className="flex items-center justify-center p-6">
            <Alert variant="destructive" className="max-w-lg">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>Something went wrong</AlertTitle>
                <AlertDescription className="mt-2">
                    <p className="mb-4">{error.message || "An unexpected error occurred"}</p>
                    {reset && (
                        <Button variant="outline" size="sm" onClick={reset}>
                            <RefreshCw className="h-4 w-4 mr-2" />
                            Try again
                        </Button>
                    )}
                </AlertDescription>
            </Alert>
        </div>
    );
}

// Router context type for data prefetching
export interface RouterContext {
    queryClient: QueryClient
}

export const rootRoute = createRootRoute<RouterContext>({
    component: () => <Layout/>
});


const homeRoute = createRoute({
    getParentRoute: () => rootRoute, path: "/", component: () => <Home/>,
})

const loginRote = createRoute({
    getParentRoute: () => rootRoute, path: "/login", component: () => <Login/>,
})

const signupRoute = createRoute({
    getParentRoute: () => rootRoute, path: "/signup", component: () => <SignupPage/>,
})

const passwordResetRequestRoute = createRoute({
    getParentRoute: () => rootRoute, path: "/password-reset-request",
    component: lazyRouteComponent(() => import("@/pages/PasswordResetConfirmForm"), "PasswordResetRequest"),
})

const passwordResetConfirmRoute = createRoute({
    getParentRoute: () => rootRoute, path: "/reset-password/$uid/$token", component: () => {
        const {uid, token} = passwordResetConfirmRoute.useParams()
        return (<PasswordResetConfirm
            uid={uid}
            token={token}
            onSuccess={() => {
                // Navigate to login or show success message
                window.location.href = '/login'
            }}
        />)
    },
})


const trackerRoute = createRoute({
    getParentRoute: () => rootRoute, path: "/tracker",
    component: lazyRouteComponent(() => import("@/pages/TrackerPage")),
})

const orderDetailsRoute = createRoute({
    getParentRoute: () => rootRoute, path: "/orders/$orderNumber",
    component: lazyRouteComponent(() => import("@/pages/OrderDetailsPage"), "OrderDetailsPage"),
})

const partAnnotatorRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "/partAnnotator/$modelId/$partId",
    component: lazyRouteComponent(() => import("@/pages/PartAnnotator"), "PartAnnotator"),
})

const heatMapViewerPartTypeRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "/heatMapViewer/partType/$partTypeId",
    component: lazyRouteComponent(() => import("@/pages/HeatMapViewer"), "HeatMapViewer"),
})

const heatMapViewerPartRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "/heatMapViewer/part/$partId",
    component: lazyRouteComponent(() => import("@/pages/HeatMapViewer"), "HeatMapViewer"),
})

const QAPage = createRoute({
    getParentRoute: () => rootRoute, path: "/QA",
    component: lazyRouteComponent(() => import("@/pages/QaPartsPage")),
})

export const ordersCreateFormRoute = createRoute({
    getParentRoute: () => rootRoute, path: "/OrderForm/",
    component: lazyRouteComponent(() => import("./pages/OrderFormPage")),
})

export const ordersEditFormRoute = createRoute({
    getParentRoute: () => rootRoute, path: "/OrderForm/$id",
    component: lazyRouteComponent(() => import("./pages/OrderFormPage")),
})

const editLandingPageRoute = createRoute({
    getParentRoute: () => rootRoute, path: "/Edit",
    component: lazyRouteComponent(() => import("./pages/EditLandingPage")),
})

const OrdersEditorPageRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "/editor/orders",
    component: lazyRouteComponent(() => import("@/pages/editors/OrdersEditorPage")),
    loader: async ({ context }) => {
        const { prefetchOrdersEditor } = await import("@/pages/editors/OrdersEditorPage");
        prefetchOrdersEditor(context.queryClient);
    },
});

const EditOrdersPartsFormRoute = createRoute({
    getParentRoute: () => rootRoute, path: "/editOrdersParts/$orderId",
    component: lazyRouteComponent(() => import("@/components/edit-orders-parts-page")),
})

const PartsEditorRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "editor/parts",
    component: lazyRouteComponent(() => import("@/pages/editors/PartsEditorPage"), "PartsEditorPage"),
    loader: async ({ context }) => {
        const { prefetchPartsEditor } = await import("@/pages/editors/PartsEditorPage");
        prefetchPartsEditor(context.queryClient);
    },
})

export const partCreateRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/PartForm/create',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditPartFormPage")),
});

export const partEditRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/PartForm/edit/$id',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditPartFormPage")),
});

export const partTypeCreateRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/PartTypeForm/create',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditPartTypeFormPage")),
});

export const partTypeEditRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/PartTypeForm/edit/$id',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditPartTypeFormPage")),
});

const PartTypesEditorRoute = createRoute({
    getParentRoute: () => rootRoute, path: "editor/partTypes",
    component: lazyRouteComponent(() => import("@/pages/editors/PartTypesEditorPage"), "PartTypesEditorPage"),
    loader: async ({ context }) => {
        const { prefetchPartTypesEditor } = await import("@/pages/editors/PartTypesEditorPage");
        prefetchPartTypesEditor(context.queryClient);
    },
})

export const processCreateRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/ProcessForm/create',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditProcessFormPage")),
});

export const processEditRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/ProcessForm/edit/$id',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditProcessFormPage")),
});

const ProcessEditorRoute = createRoute({
    getParentRoute: () => rootRoute, path: "editor/processes",
    component: lazyRouteComponent(() => import("@/pages/editors/ProcessEditorPage"), "ProcessEditorPage"),
    loader: async ({ context }) => {
        const { prefetchProcessEditor } = await import("@/pages/editors/ProcessEditorPage");
        prefetchProcessEditor(context.queryClient);
    },
})

export const stepCreateRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/StepForm/create',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditStepFormPage")),
});

export const stepEditRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/StepForm/edit/$id',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditStepFormPage")),
});

const StepEditorRoute = createRoute({
    getParentRoute: () => rootRoute, path: "editor/steps",
    component: lazyRouteComponent(() => import("@/pages/editors/StepEditorPage"), "StepsEditorPage"),
    loader: async ({ context }) => {
        const { prefetchStepsEditor } = await import("@/pages/editors/StepEditorPage");
        prefetchStepsEditor(context.queryClient);
    },
})

export const equipmentCreateRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/EquipmentForm/create',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditEquipmentFormPage")),
});

export const equipmentEditRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/EquipmentForm/edit/$id',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditEquipmentFormPage")),
});

const EquipmentEditorRoute = createRoute({
    getParentRoute: () => rootRoute, path: "editor/equipment",
    component: lazyRouteComponent(() => import("@/pages/editors/EquipmentsEditorPage"), "EquipmentEditorPage"),
    loader: async ({ context }) => {
        const { prefetchEquipmentsEditor } = await import("@/pages/editors/EquipmentsEditorPage");
        prefetchEquipmentsEditor(context.queryClient);
    },
})

export const equipmentTypeCreateRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/EquipmentTypeForm/create',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditEquipmentTypeFormPage")),
});

export const equipmentTypeEditRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/EquipmentTypeForm/edit/$id',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditEquipmentTypeFormPage")),
});

const EquipmentTypeEditorRoute = createRoute({
    getParentRoute: () => rootRoute, path: "editor/equipmentTypes",
    component: lazyRouteComponent(() => import("@/pages/editors/EquipmentTypeEditorPage"), "EquipmentTypeEditorPage"),
    loader: async ({ context }) => {
        const { prefetchEquipmentTypesEditor } = await import("@/pages/editors/EquipmentTypeEditorPage");
        prefetchEquipmentTypesEditor(context.queryClient);
    },
})

export const errorTypeCreateRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/ErrorTypeForm/create',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditErrorTypeFormPage")),
});

export const errorTypeEditRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/ErrorTypeForm/edit/$id',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditErrorTypeFormPage")),
});

const ErrorTypeEditorRoute = createRoute({
    getParentRoute: () => rootRoute, path: "editor/errorTypes",
    component: lazyRouteComponent(() => import("@/pages/editors/ErrorTypeEditorPage"), "ErrorTypeEditorPage"),
    loader: async ({ context }) => {
        const { prefetchErrorTypesEditor } = await import("@/pages/editors/ErrorTypeEditorPage");
        prefetchErrorTypesEditor(context.queryClient);
    },
})

const SamplingRulesEditorRoute = createRoute({
    getParentRoute: () => rootRoute, path: "editor/samplingrules",
    component: lazyRouteComponent(() => import("@/pages/editors/SamplingRulesEditorPage"), "SamplingRulesEditorPage"),
    loader: async ({ context }) => {
        const { prefetchSamplingRulesEditor } = await import("@/pages/editors/SamplingRulesEditorPage");
        prefetchSamplingRulesEditor(context.queryClient);
    },
})

export const samplingRulesCreateRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/SamplingRuleForm/create',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditSamplingRuleFormPage")),
});

export const samplingRulesEditRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/SamplingRuleForm/edit/$id',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditSamplingRuleFormPage")),
});

const SamplingRuleSetsEditorRoute = createRoute({
    getParentRoute: () => rootRoute, path: "editor/samplingRuleSets",
    component: lazyRouteComponent(() => import("@/pages/editors/SamplingRuleSetsEditorPage"), "SamplingRuleSetsEditorPage"),
    loader: async ({ context }) => {
        const { prefetchSamplingRuleSetsEditor } = await import("@/pages/editors/SamplingRuleSetsEditorPage");
        prefetchSamplingRuleSetsEditor(context.queryClient);
    },
})

export const samplingRuleSetsCreateRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/SamplingRuleSetForm/create',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditSamplingRuleSetsFormPage")),
});

export const samplingRuleSetsEditRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/SamplingRuleSetForm/edit/$id',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditSamplingRuleSetsFormPage")),
});

const DocumentsRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/documents',
    component: lazyRouteComponent(() => import("@/pages/documents/DocumentsDashboardPage"), "DocumentsDashboardPage"),
})

const DocumentsListRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/documents/list',
    component: lazyRouteComponent(() => import("@/pages/editors/DocumentsEditorPage"), "DocumentsEditorPage"),
    loader: async ({ context }) => {
        const { prefetchDocumentsEditor } = await import("@/pages/editors/DocumentsEditorPage");
        prefetchDocumentsEditor(context.queryClient);
    },
})

export const DocumentDetailRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/documents/$id',
    component: lazyRouteComponent(() => import("@/pages/documents/DocumentDetailPage"), "DocumentDetailPage"),
})

export const DocumentCreateRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/DocumentForm/create',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditDocumentFormPage")),
});

export const DocumentEditRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/DocumentForm/edit/$id',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditDocumentFormPage")),
});

export const ModelDetailRoute = createRoute({
    getParentRoute: () => rootRoute, path: 'details/$model/$id',
    component: lazyRouteComponent(() => import("@/pages/detail pages/ModeDetaisPageWrapper")),
})

export const WorkOrderEditorRoute = createRoute({
    getParentRoute: () => rootRoute, path: 'editor/WorkOrders',
    component: lazyRouteComponent(() => import("@/pages/editors/WorkOrdersEditorPage"), "WorkOrdersEditorPage"),
    loader: async ({ context }) => {
        const { prefetchWorkOrdersEditor } = await import("@/pages/editors/WorkOrdersEditorPage");
        prefetchWorkOrdersEditor(context.queryClient);
    },
})

export const workOrderCreateRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/WorkOrderForm/create',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditWorkOrderFormPage")),
});

export const workOrderEditRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/WorkOrderForm/edit/$id',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditWorkOrderFormPage")),
});

export const companiesEditorRoute = createRoute({
    getParentRoute: () => rootRoute, path: 'editor/Companies',
    component: lazyRouteComponent(() => import("@/pages/editors/CompaniesEditorPage"), "CompaniesEditorPage"),
    loader: async ({ context }) => {
        const { prefetchCompaniesEditor } = await import("@/pages/editors/CompaniesEditorPage");
        prefetchCompaniesEditor(context.queryClient);
    },
})

export const companiesCreateRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/CompaniesForm/create',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditCompanyFormPage")),
});

export const companiesEditRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/CompaniesForm/edit/$id',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditCompanyFormPage")),
});

export const userEditorRoute = createRoute({
    getParentRoute: () => rootRoute, path: 'editor/users',
    component: lazyRouteComponent(() => import("@/pages/editors/UserEditorPage"), "UserEditorPage"),
    loader: async ({ context }) => {
        const { prefetchUsersEditor } = await import("@/pages/editors/UserEditorPage");
        prefetchUsersEditor(context.queryClient);
    },
})

export const usersCreateRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/UserForm/create',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditUserFormPage")),
});

export const usersEditRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/UserForm/edit/$id',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditUserFormPage")),
});

export const qaWorkOrderDetailRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/qa/workorder/$workOrderId',
    component: lazyRouteComponent(() => import("@/pages/editors/QaWorkOrderDetailPage"), "QaWorkOrderDetailPage"),
});

export const aiChatRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/ai-chat',
    component: lazyRouteComponent(() => import("@/pages/AiChatPage")),
});

export const threeDModelsEditorRoute = createRoute({
    getParentRoute: () => rootRoute, path: 'editor/ThreeDModels',
    component: lazyRouteComponent(() => import("@/pages/editors/ThreeDModelsEditorPage"), "ThreeDModelsEditorPage"),
    loader: async ({ context }) => {
        const { prefetchThreeDModelsEditor } = await import("@/pages/editors/ThreeDModelsEditorPage");
        prefetchThreeDModelsEditor(context.queryClient);
    },
})

export const threeDModelsCreateRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/ThreeDModelsForm/create',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditThreeDModelFormPage")),
});

export const threeDModelsEditRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/ThreeDModelsForm/edit/$id',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditThreeDModelFormPage")),
});

export const userProfileRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/profile',
    component: lazyRouteComponent(() => import("@/pages/UserProfilePage"), "UserProfilePage"),
});

export const settingsRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/settings',
    component: lazyRouteComponent(() => import("@/pages/settings/SettingsPage"), "SettingsPage"),
});

export const organizationSettingsRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/settings/organization',
    component: lazyRouteComponent(() => import("@/pages/settings/OrganizationSettingsPage"), "OrganizationSettingsPage"),
});

export const brandingSettingsRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/settings/branding',
    component: lazyRouteComponent(() => import("@/pages/settings/BrandingSettingsPage"), "BrandingSettingsPage"),
});

export const billingSettingsRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/settings/billing',
    component: lazyRouteComponent(() => import("@/pages/settings/BillingPage"), "BillingPage"),
});

export const qualityReportsEditorRoute = createRoute({
    getParentRoute: () => rootRoute, path: 'editor/qualityReports',
    component: lazyRouteComponent(() => import("@/pages/editors/QualityReportsEditorPage"), "QualityReportsEditorPage"),
    loader: async ({ context }) => {
        const { prefetchQualityReportsEditor } = await import("@/pages/editors/QualityReportsEditorPage");
        prefetchQualityReportsEditor(context.queryClient);
    },
});

export const qualityReportCreateRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/editor/qualityReports/create',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditQualityReportFormPage")),
});

export const qualityReportEditRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/editor/qualityReports/edit/$id',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditQualityReportFormPage")),
});

export const annotatorPageRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/annotator',
    component: lazyRouteComponent(() => import("@/pages/AnnotatorPage"), "AnnotatorPage"),
});

export const analysisRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/analysis',
    component: lazyRouteComponent(() => import("@/pages/AnalysisPage")),
});

export const processFlowRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/process-flow',
    component: lazyRouteComponent(() => import("@/pages/ProcessFlowPage")),
});

export const spcRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/spc',
    component: lazyRouteComponent(() => import("@/pages/SpcPage")),
});

export const spcPrintRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/spc/print',
    validateSearch: (search: Record<string, unknown>) => ({
        processId: (search.processId as string) || undefined,
        stepId: (search.stepId as string) || undefined,
        measurementId: (search.measurementId as string) || undefined,
        mode: (search.mode as string) || undefined,
    }),
    component: lazyRouteComponent(() => import("@/pages/SpcPrintPage")),
});

// Quality Module Routes
export const qualityDashboardRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/quality',
    component: lazyRouteComponent(() => import("@/pages/quality/QualityDashboardPage"), "QualityDashboardPage"),
    loader: async ({ context }) => {
        const { prefetchQualityDashboard } = await import("@/pages/quality/QualityDashboardPage");
        prefetchQualityDashboard(context.queryClient);
    },
});

export const capaListRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/quality/capas',
    component: lazyRouteComponent(() => import("@/pages/quality/CapaListPage"), "CapaListPage"),
});

export const capaCreateRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/quality/capas/new',
    component: lazyRouteComponent(() => import("@/pages/quality/CreateCapaPage"), "CreateCapaPage"),
});

export const capaDetailRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/quality/capas/$id',
    component: lazyRouteComponent(() => import("@/pages/quality/CapaDetailPage"), "CapaDetailPage"),
});

export const ncrAnalysisRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/quality/ncrs',
    component: lazyRouteComponent(() => import("@/pages/quality/NcrAnalysisPage"), "NcrAnalysisPage"),
});

export const defectAnalysisRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/quality/defects',
    component: lazyRouteComponent(() => import("@/pages/quality/DefectAnalysisPage"), "DefectAnalysisPage"),
});

// Training Routes
export const trainingDashboardRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/quality/training',
    component: lazyRouteComponent(() => import("@/pages/quality/TrainingDashboardPage"), "TrainingDashboardPage"),
});

export const trainingRecordsRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/quality/training/records',
    component: lazyRouteComponent(() => import("@/pages/quality/TrainingRecordsPage"), "TrainingRecordsPage"),
});

export const trainingTypesRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/quality/training/types',
    component: lazyRouteComponent(() => import("@/pages/quality/TrainingTypesPage"), "TrainingTypesPage"),
});

export const trainingRecordFormRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/TrainingRecordForm/$id',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditTrainingRecordFormPage")),
});

export const trainingTypeFormRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/TrainingTypeForm/$id',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditTrainingTypeFormPage")),
});

// Calibration Routes
export const calibrationDashboardRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/quality/calibrations',
    component: lazyRouteComponent(() => import("@/pages/quality/CalibrationDashboardPage"), "CalibrationDashboardPage"),
});

export const calibrationRecordsRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/quality/calibrations/records',
    component: lazyRouteComponent(() => import("@/pages/quality/CalibrationRecordsPage"), "CalibrationRecordsPage"),
});

export const calibrationRecordFormRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/CalibrationRecordForm/$id',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditCalibrationRecordFormPage")),
});

// Personal Routes
export const inboxRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/inbox',
    component: lazyRouteComponent(() => import("@/pages/InboxPage"), "InboxPage"),
});

// Production Routes
export const workOrdersRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/production/work-orders',
    component: lazyRouteComponent(() => import("@/pages/editors/QaWorkOrdersPage"), "QaWorkOrdersPage"),
});

export const dispositionsRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/production/dispositions',
    component: lazyRouteComponent(() => import("@/pages/editors/QaQuarantinePage"), "QaQuarantinePage"),
});

// Disposition Form Routes
export const dispositionCreateRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/dispositions/create',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditDispositionFormPage")),
});

export const dispositionEditRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/dispositions/edit/$id',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditDispositionFormPage")),
});

// Admin Routes
export const auditLogRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/admin/audit-log',
    component: lazyRouteComponent(() => import("@/pages/editors/HistoryPage"), "AuditLogViewerPage"),
    loader: async ({ context }) => {
        const { prefetchAuditLogEditor } = await import("@/pages/editors/HistoryPage");
        prefetchAuditLogEditor(context.queryClient);
    },
});

// Approval Templates Routes
export const approvalTemplatesEditorRoute = createRoute({
    getParentRoute: () => rootRoute, path: 'editor/approvalTemplates',
    component: lazyRouteComponent(() => import("@/pages/editors/ApprovalTemplatesEditorPage"), "ApprovalTemplatesEditorPage"),
    loader: async ({ context }) => {
        const { prefetchApprovalTemplatesEditor } = await import("@/pages/editors/ApprovalTemplatesEditorPage");
        prefetchApprovalTemplatesEditor(context.queryClient);
    },
});

export const approvalTemplateCreateRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/ApprovalTemplateForm/create',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditApprovalTemplateFormPage")),
});

export const approvalTemplateEditRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/ApprovalTemplateForm/edit/$id',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditApprovalTemplateFormPage")),
});

// Approvals Overview Routes
export const approvalsOverviewRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/approvals',
    component: lazyRouteComponent(() => import("@/pages/approvals/ApprovalsOverviewPage"), "ApprovalsOverviewPage"),
    loader: async ({ context }) => {
        const { prefetchApprovalsOverview } = await import("@/pages/approvals/ApprovalsOverviewPage");
        prefetchApprovalsOverview(context.queryClient);
    },
});

export const approvalsHistoryRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/approvals/history',
    validateSearch: (search: Record<string, unknown>) => ({
        status: (search.status as string) || undefined,
        myRequests: search.myRequests === true || search.myRequests === "true" || undefined,
    }),
    component: lazyRouteComponent(() => import("@/pages/approvals/ApprovalsHistoryPage"), "ApprovalsHistoryPage"),
    loader: async ({ context }) => {
        const { prefetchApprovalsHistory } = await import("@/pages/approvals/ApprovalsHistoryPage");
        prefetchApprovalsHistory(context.queryClient);
    },
});

// Document Types Routes
export const documentTypesEditorRoute = createRoute({
    getParentRoute: () => rootRoute, path: 'editor/documentTypes',
    component: lazyRouteComponent(() => import("@/pages/editors/DocumentTypesEditorPage"), "DocumentTypesEditorPage"),
    loader: async ({ context }) => {
        const { prefetchDocumentTypesEditor } = await import("@/pages/editors/DocumentTypesEditorPage");
        prefetchDocumentTypesEditor(context.queryClient);
    },
});

export const documentTypeCreateRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/DocumentTypeForm/create',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditDocumentTypeFormPage")),
});

export const documentTypeEditRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/DocumentTypeForm/edit/$id',
    component: lazyRouteComponent(() => import("@/pages/editors/forms/EditDocumentTypeFormPage")),
});

// Groups Routes
export const groupsEditorRoute = createRoute({
    getParentRoute: () => rootRoute, path: 'editor/groups',
    component: lazyRouteComponent(() => import("@/pages/editors/GroupsEditorPage"), "GroupsEditorPage"),
    loader: async ({ context }) => {
        const { prefetchGroupsEditor } = await import("@/pages/editors/GroupsEditorPage");
        prefetchGroupsEditor(context.queryClient);
    },
});

export const groupDetailRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/editor/groups/$id',
    component: lazyRouteComponent(() => import("@/pages/editors/GroupDetailPage"), "GroupDetailPage"),
});

// Heatmap Route
export const heatmapRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/heatmap',
    component: lazyRouteComponent(() => import("@/pages/HeatMapViewer"), "HeatMapViewer"),
});

// Big Screen / Shop Floor Display
export const bigScreenRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/big-screen',
    component: lazyRouteComponent(() => import("@/pages/BigScreenPage")),
});

// Error Pages
export const forbiddenRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/forbidden',
    component: lazyRouteComponent(() => import("@/pages/ForbiddenPage")),
});

// Dev Tools
export const schemaAuditRoute = createRoute({
    getParentRoute: () => rootRoute, path: '/dev/schema-audit',
    component: lazyRouteComponent(() => import("@/pages/SchemaAuditPage"), "SchemaAuditPage"),
});

const routeTree = rootRoute.addChildren([homeRoute, loginRote, signupRoute, passwordResetRequestRoute, passwordResetConfirmRoute, trackerRoute, orderDetailsRoute, partAnnotatorRoute, heatMapViewerPartTypeRoute, heatMapViewerPartRoute, heatmapRoute, QAPage, ordersCreateFormRoute, ordersEditFormRoute, editLandingPageRoute, OrdersEditorPageRoute, EditOrdersPartsFormRoute, PartsEditorRoute, partCreateRoute, partEditRoute, PartTypesEditorRoute, partTypeCreateRoute, partTypeEditRoute, processCreateRoute, processEditRoute, ProcessEditorRoute, stepCreateRoute, stepEditRoute, StepEditorRoute, equipmentCreateRoute, equipmentEditRoute, EquipmentEditorRoute, equipmentTypeCreateRoute, equipmentTypeEditRoute, EquipmentTypeEditorRoute, errorTypeCreateRoute, errorTypeEditRoute, ErrorTypeEditorRoute, DocumentsRoute, DocumentsListRoute, DocumentDetailRoute, SamplingRulesEditorRoute, samplingRulesCreateRoute, samplingRulesEditRoute, SamplingRuleSetsEditorRoute, samplingRuleSetsCreateRoute, samplingRuleSetsEditRoute, DocumentCreateRoute, DocumentEditRoute, ModelDetailRoute, WorkOrderEditorRoute, workOrderEditRoute, workOrderCreateRoute, companiesEditorRoute, companiesEditRoute, companiesCreateRoute, userEditorRoute, usersEditRoute, usersCreateRoute, qaWorkOrderDetailRoute, aiChatRoute, threeDModelsEditorRoute, threeDModelsCreateRoute, threeDModelsEditRoute, userProfileRoute, settingsRoute, organizationSettingsRoute, brandingSettingsRoute, billingSettingsRoute, qualityReportsEditorRoute, qualityReportCreateRoute, qualityReportEditRoute, annotatorPageRoute, analysisRoute, processFlowRoute, spcRoute, spcPrintRoute, qualityDashboardRoute, capaListRoute, capaCreateRoute, capaDetailRoute, ncrAnalysisRoute, defectAnalysisRoute, trainingDashboardRoute, trainingRecordsRoute, trainingTypesRoute, trainingRecordFormRoute, trainingTypeFormRoute, calibrationDashboardRoute, calibrationRecordsRoute, calibrationRecordFormRoute, inboxRoute, workOrdersRoute, dispositionsRoute, dispositionCreateRoute, dispositionEditRoute, auditLogRoute, approvalTemplatesEditorRoute, approvalTemplateCreateRoute, approvalTemplateEditRoute, approvalsOverviewRoute, approvalsHistoryRoute, documentTypesEditorRoute, documentTypeCreateRoute, documentTypeEditRoute, groupsEditorRoute, groupDetailRoute, bigScreenRoute, forbiddenRoute, schemaAuditRoute])

// Create router with context
export function createAppRouter(queryClient: QueryClient) {
    return createRouter({
        routeTree,
        defaultPreload: 'intent', // Preload on hover/focus
        defaultPreloadStaleTime: 5000, // Keep prefetched data fresh for 5 seconds
        defaultPendingMs: 200, // Only show loading if navigation takes >200ms
        defaultPendingComponent: DefaultPendingComponent,
        defaultErrorComponent: DefaultErrorComponent as ErrorComponent,
        context: {
            queryClient,
        },
    });
}

// Type for the router
export type AppRouter = ReturnType<typeof createAppRouter>

declare module "@tanstack/react-router" {
    interface Register {
        router: AppRouter;
    }
}
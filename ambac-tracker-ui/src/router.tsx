import {
    Router,
    createRoute,
    createRootRoute,
} from "@tanstack/react-router"

import Layout from "@/components/layout";
import Home from "@/pages/Home";
import Login from '@/components/auth/Login'
import QaPartsPage from '@/pages/QaPartsPage.tsx'
// import TrackerPage from "@/pages/TrackerPage.tsx";
import TrackerPageDemo from "@/pages/TrackerPage.tsx";
import {OrderDetailsPage} from "@/pages/OrderDetailsPage.tsx";
import {PartAnnotator} from "@/pages/PartAnnotator.tsx";
import EditLandingPage from "./pages/EditLandingPage";
import OrdersEditorPage from "@/pages/editors/OrdersEditorPage.tsx";
import EditOrdersPartsPage from "@/components/edit-orders-parts-page.tsx";
import OrderFormPage from "./pages/OrderFormPage";
import {PartsEditorPage} from "@/pages/editors/PartsEditorPage.tsx";
import {PartTypesEditorPage} from "@/pages/editors/PartTypesEditorPage.tsx";
import PartFormPage from "@/pages/editors/forms/EditPartFormPage.tsx"
import PartTypeFormPage from "@/pages/editors/forms/EditPartTypeFormPage.tsx"
import {ProcessEditorPage} from "@/pages/editors/ProcessEditorPage.tsx";
import ProcessFormPage from "@/pages/editors/forms/EditProcessFormPage.tsx";
import StepFormPage from "@/pages/editors/forms/EditStepFormPage.tsx";
import {StepsEditorPage} from "@/pages/editors/StepEditorPage.tsx";
import EquipmentFormPage from "@/pages/editors/forms/EditEquipmentTypeFormPage.tsx";
import {EquipmentEditorPage} from "@/pages/editors/EquipmentsEditorPage.tsx";
import {EquipmentTypeEditorPage} from "@/pages/editors/EquipmentTypeEditorPage.tsx";
import EquipmentTypeFormPage from "@/pages/editors/forms/EditEquipmentTypeFormPage.tsx";
import ErrorTypeFormPage from "@/pages/editors/forms/EditErrorTypeFormPage.tsx";
import {ErrorTypeEditorPage} from "@/pages/editors/ErrorTypeEditorPage.tsx";
import {DocumentsEditorPage} from "@/pages/editors/DocumentsEditorPage.tsx";
import {SamplingRulesEditorPage} from "@/pages/editors/SamplingRulesEditorPage.tsx";
import SamplingRuleFormPage from "@/pages/editors/forms/EditSamplingRuleFormPage.tsx";
import {SamplingRuleSetsEditorPage} from "@/pages/editors/SamplingRuleSetsEditorPage.tsx";
import SamplingRuleSetsFormPage from "@/pages/editors/forms/EditSamplingRuleSetsFormPage.tsx";
import DocumentFormPage from "@/pages/editors/forms/EditDocumentFormPage.tsx";
import ModelDetailPageWrapper from "@/pages/detail pages/ModeDetaisPageWrapper.tsx";
import {WorkOrdersEditorPage} from "@/pages/editors/WorkOrdersEditorPage.tsx";
import WorkOrderFormPage from "@/pages/editors/forms/EditWorkOrderFormPage.tsx";




export const rootRoute = createRootRoute({
    component: () => <Layout />
});

const homeRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "/",
    component: () => <Home />,
})

const loginRote = createRoute({
    getParentRoute: () => rootRoute,
    path: "/login",
    component: () => <Login />,
})

const trackerRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "/tracker",
    component: () => <TrackerPageDemo />
})

const orderDetailsRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "/orders/$orderNumber",
    component: () => <OrderDetailsPage/>
})

const partAnnotatorRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "/partAnnotator",
    component: () => <PartAnnotator/>
})

const QAPage = createRoute({
    getParentRoute: () => rootRoute,
    path: "/QA",
    component: () => <QaPartsPage/>,
})

export const ordersCreateFormRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "/OrderForm/",
    component: () => <OrderFormPage />,
})

export const ordersEditFormRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "/OrderForm/$id",
    component: () => <OrderFormPage/>,
})

const editLandingPageRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "/Edit",
    component: () => <EditLandingPage/>,
})

const OrdersEditorPageRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "/editor/orders",
    component: () => <OrdersEditorPage />, // You’ll build this per model
});

const EditOrdersPartsFormRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "/editOrdersParts/$orderId",
    component: () => <EditOrdersPartsPage/>
})

const PartsEditorRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "editor/parts",
    component: () => <PartsEditorPage/>
})

export const partCreateRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/PartForm/create',
    component: PartFormPage,
});

export const partEditRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/PartForm/edit/$id',
    component: PartFormPage,
});

export const partTypeCreateRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/PartTypeForm/create',
    component: PartTypeFormPage,
});

export const partTypeEditRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/PartTypeForm/edit/$id',
    component: PartTypeFormPage,
});

const PartTypesEditorRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "editor/partTypes",
    component: () => <PartTypesEditorPage/>
})

export const processCreateRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/ProcessForm/create',
    component: ProcessFormPage,
});

export const processEditRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/ProcessForm/edit/$id',
    component: ProcessFormPage,
});

const ProcessEditorRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "editor/processes",
    component: () => <ProcessEditorPage/>
})

export const stepCreateRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/StepForm/create',
    component: StepFormPage,
})

export const stepEditRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/StepForm/edit/$id',
    component: StepFormPage,
});

const StepEditorRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "editor/steps",
    component: () => <StepsEditorPage/>
})

export const equipmentCreateRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/EquipmentForm/create',
    component: EquipmentFormPage,
})

export const equipmentEditRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/EquipmentForm/edit/$id',
    component: EquipmentFormPage,
});

const EquipmentEditorRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "editor/equipment",
    component: () => <EquipmentEditorPage/>
})

export const equipmentTypeCreateRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/EquipmentTypeForm/create',
    component: EquipmentTypeFormPage,
})

export const equipmentTypeEditRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/EquipmentTypeForm/edit/$id',
    component: EquipmentTypeFormPage,
});

const EquipmentTypeEditorRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "editor/equipmentTypes",
    component: () => <EquipmentTypeEditorPage/>
})

export const errorTypeCreateRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/ErrorTypeForm/create',
    component: ErrorTypeFormPage,
})

export const errorTypeEditRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/ErrorTypeForm/edit/$id',
    component: ErrorTypeFormPage,
});

const ErrorTypeEditorRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "editor/errorTypes",
    component: () => <ErrorTypeEditorPage/>
})

const SamplingRulesEditorRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "editor/samplingrules",
    component: () => <SamplingRulesEditorPage/>
})

export const samplingRulesCreateRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/SamplingRuleForm/create',
    component: SamplingRuleFormPage,
})

export const samplingRulesEditRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/SamplingRuleForm/edit/$id',
    component: SamplingRuleFormPage,
});

const SamplingRuleSetsEditorRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "editor/samplingRuleSets",
    component: () => <SamplingRuleSetsEditorPage/>
})

export const samplingRuleSetsCreateRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/SamplingRuleSetForm/create',
    component: SamplingRuleSetsFormPage,
})

export const samplingRuleSetsEditRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/SamplingRuleSetForm/edit/$id',
    component: SamplingRuleSetsFormPage,
});

const DocumentsRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/Documents',
    component: () => <DocumentsEditorPage/>
})

export const DocumentCreateRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/DocumentForm/create',
    component: DocumentFormPage,
})

export const DocumentEditRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/DocumentForm/edit/$id',
    component: DocumentFormPage,
});

export const ModelDetailRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: 'details/$model/$id',
    component: ModelDetailPageWrapper,
})

export const WorkOrderEditorRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: 'editor/WorkOrders',
    component: WorkOrdersEditorPage
})

export const workOrderCreateRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/WorkOrderForm/create',
    component: WorkOrderFormPage,
})

export const workOrderEditRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/WorkOrderForm/edit/$id',
    component: WorkOrderFormPage,
});

const routeTree = rootRoute.addChildren([
    homeRoute,
    loginRote,
    trackerRoute,
    orderDetailsRoute,
    partAnnotatorRoute,
    QAPage,
    ordersCreateFormRoute,
    ordersEditFormRoute,
    editLandingPageRoute,
    OrdersEditorPageRoute,
    EditOrdersPartsFormRoute,
    PartsEditorRoute,
    partCreateRoute,
    partEditRoute,
    PartTypesEditorRoute,
    partTypeCreateRoute,
    partTypeEditRoute,
    processCreateRoute,
    processEditRoute,
    ProcessEditorRoute,
    stepCreateRoute,
    stepEditRoute,
    StepEditorRoute,
    equipmentCreateRoute,
    equipmentEditRoute,
    EquipmentEditorRoute,
    equipmentTypeCreateRoute,
    equipmentTypeEditRoute,
    EquipmentTypeEditorRoute,
    errorTypeCreateRoute,
    errorTypeEditRoute,
    ErrorTypeEditorRoute,
    DocumentsRoute,
    SamplingRulesEditorRoute,
    samplingRulesCreateRoute,
    samplingRulesEditRoute,
    SamplingRuleSetsEditorRoute,
    samplingRuleSetsCreateRoute,
    samplingRuleSetsEditRoute,
    DocumentCreateRoute,
    DocumentEditRoute,
    ModelDetailRoute,
    WorkOrderEditorRoute,
    workOrderEditRoute,
    workOrderCreateRoute
])

export const router = new Router({routeTree})

declare module "@tanstack/react-router" {
    interface Register {
        router: typeof router;
    }
}
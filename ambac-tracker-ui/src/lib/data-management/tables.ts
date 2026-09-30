/**
 * Every table Data Management lists, like the Django admin index: shared config
 * touched monthly or yearly. Day-to-day work lives in the sidebar instead.
 *
 * A table that always belongs to one parent (a BOM line to its BOM, a step's
 * timing to the step) is listed under that parent with `editedOn` naming where its
 * rows are edited: it has no form of its own, only the parent's.
 */

export type DMTable = {
    key: string;
    name: string;
    /** List page. Absent for a child with no list of its own. */
    list?: string;
    /** Create page; absent where rows are only added from another form. */
    add?: string;
    /** Query string the create page needs (a list page that creates in a dialog). */
    addSearch?: Record<string, string>;
    /** Route under /api/ — drives the row count, and Import / Export where the backend has them. */
    endpoint: string;
    /** Extra list filters the count (and export) apply. */
    countQuery?: Record<string, string | boolean>;
    /** A slice of a wider endpoint: an import through it would land as rows of the whole endpoint. */
    slice?: boolean;
    /** Model codename: `view_<model>` shows the row, `add_<model>` the Add link. */
    model: string;
    /** Edits make a new revision. */
    versioned?: boolean;
    /** For a child table: the parent form its rows are edited on. */
    editedOn?: string;
    children?: DMTable[];
};

export type DMGroup = { title: string; tables: DMTable[] };

export const DATA_MANAGEMENT: DMGroup[] = [
    {
        title: "Products & routing",
        tables: [
            {
                key: "part-types", name: "Part Types", list: "/editor/partTypes", add: "/PartTypeForm/create",
                endpoint: "PartTypes", model: "parttypes", versioned: true,
                children: [
                    { key: "boms", name: "BOMs & BOM lines", endpoint: "BOMs", model: "bom", versioned: true, editedOn: "the part type" },
                    { key: "part-type-life-limits", name: "Life limits", endpoint: "PartTypeLifeLimits", model: "parttypelifelimit", editedOn: "the part type" },
                    { key: "teardown", name: "Teardown", endpoint: "DisassemblyBOMLines", model: "disassemblybomline", versioned: true, editedOn: "the part type" },
                ],
            },
            {
                key: "processes", name: "Processes", list: "/editor/processes", add: "/editor/processes", addSearch: { new: "1" },
                endpoint: "Processes", model: "processes", versioned: true,
                children: [
                    { key: "steps", name: "Steps", list: "/editor/steps", endpoint: "Steps", countQuery: { is_current_version: true }, model: "steps", versioned: true, editedOn: "the process" },
                    { key: "step-timings", name: "Step Timings", list: "/production/step-timings", endpoint: "StepTimings", model: "steptiming", editedOn: "the step" },
                    { key: "machine-eligibility", name: "Machine Eligibility", list: "/production/step-equipment-affinities", endpoint: "StepEquipmentAffinities", model: "stepequipmentaffinity", editedOn: "the step or machine" },
                    { key: "measurement-definitions", name: "Measurement Definitions", list: "/quality/measurement-definitions", endpoint: "MeasurementDefinitions", model: "measurementdefinition", versioned: true, editedOn: "the step" },
                    { key: "substeps", name: "Substeps", endpoint: "Substeps", model: "substep", editedOn: "the step" },
                ],
            },
            { key: "error-types", name: "Error Types", list: "/editor/errorTypes", add: "/ErrorTypeForm/create", endpoint: "Error-types", model: "qualityerrorslist", versioned: true },
            { key: "life-limit-definitions", name: "Life Limit Definitions", list: "/editor/life-limit-definitions", add: "/editor/life-limit-definitions/new", endpoint: "LifeLimitDefinitions", model: "lifelimitdefinition", versioned: true },
        ],
    },
    {
        title: "Equipment & scheduling",
        tables: [
            {
                key: "equipment", name: "Equipment", list: "/editor/equipment", add: "/EquipmentForm/create",
                endpoint: "Equipment", model: "equipments", versioned: true,
                children: [
                    { key: "changeovers", name: "Changeovers", list: "/production/work-center-changeovers", endpoint: "WorkCenterChangeovers", model: "workcenterchangeover", editedOn: "the machine" },
                ],
            },
            { key: "equipment-types", name: "Equipment Types", list: "/editor/equipmentTypes", add: "/EquipmentTypeForm/create", endpoint: "Equipment-types", model: "equipmenttype", versioned: true },
            { key: "tooling", name: "Tooling", list: "/editor/tooling", add: "/editor/tooling/new", endpoint: "Fixtures", model: "fixture" },
            { key: "work-centers", name: "Work Centers", list: "/admin/work-centers", endpoint: "WorkCenters", model: "workcenter", versioned: true },
            { key: "shifts", name: "Shifts", list: "/editor/shifts", endpoint: "Shifts", model: "shift", versioned: true },
        ],
    },
    {
        title: "Quality",
        tables: [
            {
                key: "sampling-rule-sets", name: "Sampling Rule Sets", list: "/editor/samplingRuleSets", add: "/SamplingRuleSetForm/create",
                endpoint: "Sampling-rule-sets", model: "samplingruleset", versioned: true,
                children: [
                    { key: "sampling-rules", name: "Sampling Rules", list: "/editor/samplingrules", endpoint: "Sampling-rules", model: "samplingrule", editedOn: "the rule set" },
                ],
            },
            {
                key: "receiving-plans", name: "Receiving Inspection Plans", list: "/production/receiving-plans",
                endpoint: "Steps", countQuery: { step_type: "RECEIVING", standalone: true }, slice: true, model: "steps", versioned: true,
            },
            { key: "document-types", name: "Document Types", list: "/editor/documentTypes", add: "/DocumentTypeForm/create", endpoint: "DocumentTypes", model: "documenttype", versioned: true },
            { key: "approval-templates", name: "Approval Templates", list: "/editor/approvalTemplates", add: "/ApprovalTemplateForm/create", endpoint: "ApprovalTemplates", model: "approvaltemplate", versioned: true },
        ],
    },
    {
        title: "Supply & reman",
        tables: [
            { key: "materials", name: "Purchased Materials", list: "/editor/materials", add: "/editor/materials/new", endpoint: "Materials", model: "material" },
            { key: "companies", name: "Companies", list: "/editor/Companies", add: "/CompaniesForm/create", endpoint: "Companies", model: "companies", versioned: true },
            { key: "repair-codes", name: "Repair Codes", list: "/editor/repair-codes", add: "/editor/repair-codes/new", endpoint: "RepairCodes", model: "repaircode", versioned: true },
            { key: "rebuild-levels", name: "Rebuild Levels", list: "/editor/rebuild-levels", add: "/editor/rebuild-levels/new", endpoint: "RebuildScopePresets", model: "rebuildscopepreset", versioned: true },
        ],
    },
    {
        title: "People & access",
        tables: [
            { key: "users", name: "Users", list: "/editor/users", add: "/UserForm/create", endpoint: "User", model: "user" },
            { key: "groups", name: "User Groups", list: "/editor/groups", endpoint: "TenantGroups", model: "tenantgroup" },
            { key: "job-roles", name: "Job Roles", list: "/quality/training/roles", add: "/quality/training/roles/new", endpoint: "JobRoles", model: "jobrole" },
            { key: "training-types", name: "Training Types", list: "/quality/training/types", add: "/TrainingTypeForm/new", endpoint: "TrainingTypes", model: "trainingtype", versioned: true },
            { key: "external-contacts", name: "External Contacts", list: "/settings/notifications/external-contacts", add: "/settings/notifications/external-contacts/new", endpoint: "notifications/external-contacts", model: "externalcontact" },
        ],
    },
    {
        title: "Orders & records",
        tables: [
            { key: "orders", name: "Orders", list: "/editor/orders", add: "/OrderForm", endpoint: "Orders", model: "orders" },
            { key: "work-orders", name: "Work Orders", list: "/editor/WorkOrders", add: "/WorkOrderForm/create", endpoint: "WorkOrders", model: "workorder" },
            { key: "parts", name: "Parts", list: "/editor/parts", add: "/PartForm/create", endpoint: "Parts", model: "parts" },
            { key: "cores", name: "Cores", list: "/reman/cores", add: "/reman/cores/receive", endpoint: "Cores", model: "core" },
            { key: "milestones", name: "Order Milestones", list: "/editor/milestones", endpoint: "MilestoneTemplates", model: "milestonetemplate", versioned: true },
            { key: "quality-reports", name: "Quality Reports", list: "/editor/qualityReports", add: "/editor/qualityReports/create", endpoint: "QualityReports", model: "qualityreports" },
        ],
    },
    {
        title: "Documents & audit",
        tables: [
            { key: "documents", name: "Documents", list: "/documents/list", add: "/DocumentForm/create", endpoint: "Documents", model: "documents", versioned: true },
            { key: "3d-models", name: "3D Models", list: "/editor/ThreeDModels", add: "/ThreeDModelsForm/create", endpoint: "ThreeDModels", model: "threedmodel", versioned: true },
            { key: "audit-log", name: "Audit Log", list: "/admin/audit-log", endpoint: "auditlog", model: "logentry" },
        ],
    },
];

/** The order to load a new plant's tables in: each one's rows point at earlier ones. */
export const LOAD_ORDER: { key: string; label: string }[] = [
    { key: "companies", label: "Companies" },
    { key: "part-types", label: "Part Types" },
    { key: "materials", label: "Purchased Materials" },
    { key: "equipment-types", label: "Equipment Types" },
    { key: "equipment", label: "Equipment" },
    { key: "work-centers", label: "Work Centers" },
    { key: "shifts", label: "Shifts" },
    { key: "processes", label: "Processes & steps" },
    { key: "step-timings", label: "Step timings" },
    { key: "machine-eligibility", label: "Machine eligibility" },
    { key: "measurement-definitions", label: "Measurement definitions" },
    { key: "sampling-rule-sets", label: "Sampling rules" },
    { key: "job-roles", label: "Job Roles" },
    { key: "training-types", label: "Training Types" },
];

/** Every table, parents and children, flat. */
export const ALL_TABLES: DMTable[] = DATA_MANAGEMENT.flatMap((g) =>
    g.tables.flatMap((t) => [t, ...(t.children ?? [])]));

/** `view_*` codenames of every table — the sidebar shows Data Management to anyone holding one. */
export const DATA_MANAGEMENT_VIEW_PERMS: string[] = [...new Set(ALL_TABLES.map((t) => `view_${t.model}`))];

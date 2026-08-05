import { api } from '@/lib/api/generated';
import type { FieldsConfig } from './ModelDetailPage';
import DocumentsSection from './DocumentsSection';
import AuditTrail from './AuditTrail';
import { PartLinkedRecordsSection } from './PartLinkedRecordsSection';
import { QRMeasurementsSection } from './QRMeasurementsSection';
import { Link } from '@tanstack/react-router';

// List of model types that have detail page configurations
export const SUPPORTED_MODELS = [
    'Parts', 'Orders', 'PartTypes', 'Processes', 'Steps', 'WorkOrders',
    'Equipments', 'SamplingRules', 'SamplingRuleSets', 'Customers',
    'MeasurementDefinitions', 'ErrorTypes', 'EquipmentTypes', 'Companies',
    'Users', 'TrackerOrders', 'QualityReports', 'QuarantineDisposition',
    'Documents', 'AuditLog'
];

// Helper functions for common field renderers
export const commonRenderers = {
    date: (value: any) => value ? new Date(value).toLocaleDateString() : '—',
    datetime: (value: any) => value ? new Date(value).toLocaleString() : '—',
    boolean: (value: any) => value ? 'Yes' : 'No',
    percentage: (value: any) => value ? `${Number(value).toFixed(1)}%` : '—',
    // Handle UUID fields that might come as URLs, objects, or plain IDs
    uuid: (value: any) => {
        if (!value) return '—';
        if (typeof value === 'string') {
            // If it's a URL, extract the UUID from the end
            const uuidMatch = value.match(/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/i);
            if (uuidMatch) return uuidMatch[1];
            return value;
        }
        if (typeof value === 'object' && value.id) return value.id;
        return String(value);
    },
};

// Helper function to create standard system info section
export const createSystemInfoSection = (fields: string[] = ['created_at', 'updated_at']) => ({
    title: 'System Information',
    fields,
    auditLog: true,
});

// Template for creating new model configurations
export const createModelConfig = (config: {
    modelType: string;
    fields: Record<string, { label: string }>;
    getHeader?: (modelData: any) => { title: string; subtitle?: string };
    customRenderers?: Record<string, (value: any, data?: any) => React.ReactNode>;
    sections: Array<{
        title: string;
        fields: string[];
        auditLog?: boolean;
    }>;
    apiPath: string;
    includeDocuments?: boolean;
    includeAudit?: boolean;
    relatedModels?: Array<{
        modelType: string;
        fieldName: string;
        label: string;
        getValue?: (modelData: any) => string | number | null;
    }>;
    actionButtons?: Array<{
        label: string;
        variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link";
        getUrl: (modelData: any) => string;
        condition?: (modelData: any) => boolean;
    }>;
    linkedRecordsComponent?: React.FC<{ modelData: any }>;
}): FieldsConfig => {
    const {
        fields,
        getHeader,
        customRenderers = {},
        sections,
        apiPath,
        includeDocuments = true,
        includeAudit = true,
        relatedModels = [],
        actionButtons = [],
        linkedRecordsComponent,
    } = config;

    return {
        fields,
        ...(getHeader && { getHeader }),
        customRenderers,
        // eslint-disable-next-line local/no-as-any -- dynamic API method dispatch by string key; no index signature on the generated api object
        fetcher: (id) => (api as any)[apiPath]({ params: { id } }),
        sections: {
            header: [],
            info: sections,
            related: [],
            documents: [],
        },
        relatedModels,
        actionButtons,
        subcomponents: {
            ...(includeDocuments && { DocumentsSectionComponent: DocumentsSection }),
            ...(includeAudit && { AuditTrailComponent: AuditTrail }),
            ...(linkedRecordsComponent && { LinkedRecordsComponent: linkedRecordsComponent }),
        },
    };
};

export const getFieldsConfigForModel = (modelType: string): FieldsConfig => {
    const normalizedType = modelType.toLowerCase();

    switch (normalizedType) {
        case 'parts':
            return {
                fields: {
                    ERP_id: { label: 'Serial' },
                    part_status: { label: 'Status' },
                    part_type_name: { label: 'Part Type' },
                    order_name: { label: 'Order' },
                    step_name: { label: 'Current Step' },
                    work_order_erp_id: { label: 'Work Order' },
                    quality_info: { label: 'Latest Inspection' },
                    // Framed by the *action* an inspector would take, not
                    // the raw model flag. A QUARANTINED part with a FAIL
                    // reads "Awaiting inspection: No / Inspections signed
                    // off: No" — technically accurate (the part is out of
                    // the AWAITING_QA state and hasn't finished the
                    // routing) instead of the misleading "Needs QA: No" on
                    // a part that plainly needs a QA *decision* (via
                    // disposition, tracked elsewhere on this page).
                    needs_qa: { label: 'Awaiting inspection' },
                    qa_completed: { label: 'Inspections signed off' },
                    total_rework_count: { label: 'Rework Passes' },
                    has_error: { label: 'Has Open Defect' },
                    requires_sampling: { label: 'Sampling Required' },
                    sampling_context: { label: 'Sampling Reason' },
                    archived: { label: 'Archived' },
                    created_at: { label: 'Created At' },
                    updated_at: { label: 'Last Updated' },
                },
                customRenderers: {
                    created_at: commonRenderers.datetime,
                    updated_at: commonRenderers.datetime,
                    has_error: commonRenderers.boolean,
                    archived: commonRenderers.boolean,
                    requires_sampling: commonRenderers.boolean,
                    needs_qa: commonRenderers.boolean,
                    qa_completed: commonRenderers.boolean,
                    // Link the resolved names in the info sections to their
                    // owning object's detail page — a QA inspector who reads
                    // "Order: Midwest Fleet Order — 24 Injectors" should be
                    // able to click through to that order without hunting.
                    part_type_name: (value, modelData) => {
                        const label = value || 'Part Type';
                        const id = modelData?.part_type;
                        if (!id) return String(label);
                        return (
                            <Link
                                to="/details/$model/$id"
                                params={{ model: 'PartTypes', id: String(id) }}
                                className="text-primary hover:underline font-medium"
                            >
                                {String(label)}
                            </Link>
                        );
                    },
                    order_name: (value, modelData) => {
                        const label = value || 'Order';
                        const id = modelData?.order;
                        if (!id) return String(label);
                        return (
                            <Link
                                to="/details/$model/$id"
                                params={{ model: 'Orders', id: String(id) }}
                                className="text-primary hover:underline font-medium"
                            >
                                {String(label)}
                            </Link>
                        );
                    },
                    step_name: (value, modelData) => {
                        const label = value || 'Step';
                        const id = modelData?.step;
                        if (!id) return String(label);
                        return (
                            <Link
                                to="/details/$model/$id"
                                params={{ model: 'Steps', id: String(id) }}
                                className="text-primary hover:underline font-medium"
                            >
                                {String(label)}
                            </Link>
                        );
                    },
                    // Work Order routes to the CONTROL page (the QA/lead
                    // working surface with exceptions + per-part step
                    // controls) rather than the WO detail — the detail page
                    // is a summary; the control page is where you *do*
                    // things.
                    work_order_erp_id: (value, modelData) => {
                        const label = value || 'Work Order';
                        const id = modelData?.work_order;
                        if (!id) return String(label);
                        return (
                            <Link
                                to="/workorder/$workOrderId/control"
                                params={{ workOrderId: String(id) }}
                                className="text-primary hover:underline font-medium"
                            >
                                {String(label)}
                            </Link>
                        );
                    },
                    // Latest QR status + open error count, drawn from the
                    // serializer's `quality_info` object. A QUARANTINED part
                    // with a FAIL QR reads "FAIL · 1 open defect" instead of
                    // an unhelpful "Has Error: Yes".
                    quality_info: (value, modelData) => {
                        if (!value || typeof value !== 'object') return '—';
                        const info = value as {
                            has_errors?: boolean;
                            latest_status?: string | null;
                            error_count?: number;
                        };
                        const status = info.latest_status ?? '—';
                        const count = info.error_count ?? 0;
                        if (status === '—' && count === 0) return '—';
                        const text = count > 0
                            ? `${status} · ${count} open defect${count === 1 ? '' : 's'}`
                            : String(status);
                        // No stable QR-id on the parts serializer to deep
                        // link into a single report, but the QRs editor list
                        // supports a `part` filter — take the trainee to the
                        // filtered list so they can open the report.
                        const partId = modelData?.id;
                        if (!partId) return text;
                        return (
                            <Link
                                to="/editor/qualityReports"
                                search={{ part: String(partId) } as never}
                                className="text-primary hover:underline font-medium"
                            >
                                {text}
                            </Link>
                        );
                    },
                    // Human-readable "why is this in the QA queue?" from the
                    // sampling_context JSON blob. Falls back to '—' when no
                    // trigger is stored.
                    sampling_context: (value) => {
                        if (!value || typeof value !== 'object') return '—';
                        const ctx = value as { trigger_reason?: string };
                        const reason = ctx.trigger_reason;
                        if (!reason) return '—';
                        // Enum-style keys → readable phrases.
                        const map: Record<string, string> = {
                            PERIODIC_SAMPLING: 'Periodic — every N parts',
                            FIRST_PIECE: 'First piece off the line',
                            RANDOM: 'Random selection',
                            RULE_TRIGGERED: 'Rule triggered',
                        };
                        return map[reason] ?? reason.replace(/_/g, ' ').toLowerCase();
                    },
                },
                fetcher: (id) => api.api_Parts_retrieve({ params: { id } }),
                // Show `INJ-0042-017 · Common Rail Injector` in the header
                // instead of `Parts Detail · ID: 019f6185-…`. Shop floor
                // reads ERP ids, never UUIDs.
                getHeader: (part) => ({
                    title: part.ERP_id || 'Part',
                    subtitle: part.part_type_name || undefined,
                }),
                sections: {
                    header: [],
                    info: [
                        {
                            title: 'General Information',
                            fields: ['ERP_id', 'part_status', 'part_type_name'],
                        },
                        {
                            title: 'Production Details',
                            fields: ['order_name', 'step_name', 'work_order_erp_id'],
                        },
                        {
                            title: 'Quality Control',
                            fields: [
                                'quality_info',
                                'has_error',
                                'needs_qa',
                                'qa_completed',
                                'total_rework_count',
                                'requires_sampling',
                                'sampling_context',
                            ],
                        },
                        createSystemInfoSection(['archived', 'created_at', 'updated_at']),
                    ],
                    related: [],
                    documents: [],
                },
                // Parts gets docs from: Order, WorkOrder, Step, Process (via step), PartType
                relatedModels: [
                    {
                        modelType: 'orders',
                        fieldName: 'order',
                        label: 'Order Documents'
                    },
                    {
                        modelType: 'workorders',
                        fieldName: 'work_order',
                        label: 'Work Order Documents'
                    },
                    {
                        modelType: 'steps',
                        fieldName: 'step',
                        label: 'Step Documents'
                    },
                    {
                        modelType: 'parttypes',
                        fieldName: 'part_type',
                        label: 'Part Type Documents'
                    },
                    // Special case: get process docs via step->process relationship
                    {
                        modelType: 'processes',
                        fieldName: 'process',
                        label: 'Process Documents',
                        getValue: (part) => part.process || null
                    }
                ],
                subcomponents: {
                    DocumentsSectionComponent: DocumentsSection,
                    AuditTrailComponent: AuditTrail,
                    LinkedRecordsComponent: PartLinkedRecordsSection,
                },
            };

        case 'orders':
            return createModelConfig({
                modelType: 'orders',
                fields: {
                    id: { label: 'Order ID' },
                    name: { label: 'Order Name' },
                    order_status: { label: 'Status' },
                    customer: { label: 'Customer ID' },
                    company: { label: 'Company ID' },
                    customer_first_name: { label: 'Customer First Name' },
                    customer_last_name: { label: 'Customer Last Name' },
                    company_name: { label: 'Company' },
                    customer_note: { label: 'Customer Note' },
                    estimated_completion: { label: 'Estimated Completion' },
                    original_completion_date: { label: 'Original Completion Date' },
                    current_milestone: { label: 'Current Milestone' },
                    archived: { label: 'Archived' },
                },
                customRenderers: {
                    estimated_completion: commonRenderers.date,
                    original_completion_date: commonRenderers.date,
                    archived: commonRenderers.boolean,
                },
                sections: [
                    {
                        title: 'Order Information',
                        fields: ['id', 'name', 'order_status'],
                    },
                    {
                        title: 'Customer Details',
                        fields: ['customer_first_name', 'customer_last_name', 'company_name', 'customer_note'],
                    },
                    {
                        title: 'Timeline',
                        fields: ['estimated_completion', 'original_completion_date'],
                    },
                    {
                        title: 'Status & System',
                        fields: ['current_milestone', 'archived'],
                        auditLog: true,
                    },
                ],
                apiPath: 'api_Orders_retrieve',
                relatedModels: [
                    {
                        modelType: 'customers',
                        fieldName: 'customer',
                        label: 'Customer Documents'
                    },
                    {
                        modelType: 'companies',
                        fieldName: 'company',
                        label: 'Company Documents'
                    }
                ],
            });

        case 'parttypes':
            return createModelConfig({
                modelType: 'parttypes',
                fields: {
                    id: { label: 'ID' },
                    name: { label: 'Part Type Name' },
                    ID_prefix: { label: 'ID Prefix' },
                    version: { label: 'Version' },
                    ERP_id: { label: 'ERP ID' },
                    previous_version: { label: 'Previous Version ID' },
                    previous_version_name: { label: 'Previous Version Name' },
                    created_at: { label: 'Created At' },
                    updated_at: { label: 'Last Updated' },
                },
                customRenderers: {
                    created_at: commonRenderers.datetime,
                    updated_at: commonRenderers.datetime,
                },
                sections: [
                    {
                        title: 'Part Type Information',
                        fields: ['id', 'name', 'ID_prefix', 'version', 'ERP_id'],
                    },
                    {
                        title: 'Version History',
                        fields: ['previous_version', 'previous_version_name'],
                    },
                    createSystemInfoSection(['created_at', 'updated_at']),
                ],
                apiPath: 'api_PartTypes_retrieve',
                relatedModels: [
                    {
                        modelType: 'parttypes',
                        fieldName: 'previous_version',
                        label: 'Previous Version Documents'
                    }
                ],
            });

        case 'processes':
            return createModelConfig({
                modelType: 'processes',
                fields: {
                    id: { label: 'Process ID' },
                    name: { label: 'Process Name' },
                    is_remanufactured: { label: 'Is Remanufactured' },
                    part_type: { label: 'Part Type ID' },
                    num_steps: { label: 'Number of Steps' },
                    archived: { label: 'Archived' },
                },
                customRenderers: {
                    is_remanufactured: commonRenderers.boolean,
                },
                sections: [
                    {
                        title: 'Process Information',
                        fields: ['id', 'name', 'part_type', 'archived'],
                    },
                    {
                        title: 'Process Details',
                        fields: ['is_remanufactured', 'num_steps'],
                        auditLog: true,
                    },
                ],
                apiPath: 'api_Processes_retrieve',
                relatedModels: [
                    {
                        modelType: 'parttypes',
                        fieldName: 'part_type',
                        label: 'Part Type Documents'
                    }
                ],
            });

        case 'steps':
            return createModelConfig({
                modelType: 'steps',
                fields: {
                    id: { label: 'Step ID' },
                    name: { label: 'Step Name' },
                    order: { label: 'Order' },
                    description: { label: 'Description' },
                    is_last_step: { label: 'Is Last Step' },
                    process: { label: 'Process ID' },
                    part_type: { label: 'Part Type ID' },
                    process_name: { label: 'Process Name' },
                    part_type_name: { label: 'Part Type Name' },
                },
                customRenderers: {
                    is_last_step: commonRenderers.boolean,
                },
                sections: [
                    {
                        title: 'Step Information',
                        fields: ['id', 'name', 'order', 'description', 'is_last_step'],
                    },
                    {
                        title: 'Process Details',
                        fields: ['process_name', 'part_type_name'],
                        auditLog: true,
                    },
                ],
                apiPath: 'api_Steps_retrieve',
                relatedModels: [
                    {
                        modelType: 'processes',
                        fieldName: 'process',
                        label: 'Process Documents'
                    },
                    {
                        modelType: 'parttypes',
                        fieldName: 'part_type',
                        label: 'Part Type Documents'
                    }
                ],
            });

        case 'workorders':
            return createModelConfig({
                modelType: 'workorders',
                fields: {
                    id: { label: 'Work Order ID' },
                    related_order: { label: 'Related Order ID' },
                    workorder_status: { label: 'Status' },
                    quantity: { label: 'Quantity' },
                    ERP_id: { label: 'ERP ID' },
                    created_at: { label: 'Created At' },
                    updated_at: { label: 'Last Updated' },
                    expected_completion: { label: 'Expected Completion' },
                    expected_duration: { label: 'Expected Duration' },
                    true_completion: { label: 'Actual Completion' },
                    true_duration: { label: 'Actual Duration' },
                    notes: { label: 'Notes' },
                },
                customRenderers: {
                    created_at: commonRenderers.datetime,
                    updated_at: commonRenderers.datetime,
                    expected_completion: commonRenderers.datetime,
                    true_completion: commonRenderers.datetime,
                },
                sections: [
                    {
                        title: 'Work Order Information',
                        fields: ['id', 'ERP_id', 'workorder_status', 'quantity', 'related_order'],
                    },
                    {
                        title: 'Timeline - Expected',
                        fields: ['expected_completion', 'expected_duration'],
                    },
                    {
                        title: 'Timeline - Actual',
                        fields: ['true_completion', 'true_duration'],
                    },
                    {
                        title: 'Additional Information',
                        fields: ['notes'],
                    },
                    createSystemInfoSection(['created_at', 'updated_at']),
                ],
                apiPath: 'api_WorkOrders_retrieve',
                relatedModels: [
                    {
                        modelType: 'orders',
                        fieldName: 'related_order',
                        label: 'Order Documents'
                    }
                ],
            });

        case 'equipments':
            return createModelConfig({
                modelType: 'equipments',
                fields: {
                    id: { label: 'Equipment ID' },
                    name: { label: 'Equipment Name' },
                    equipment_type: { label: 'Equipment Type ID' },
                    equipment_type_name: { label: 'Equipment Type' },
                },
                sections: [
                    {
                        title: 'Equipment Information',
                        fields: ['id', 'name', 'equipment_type_name'],
                        auditLog: true,
                    },
                ],
                apiPath: 'api_Equipment_retrieve',
                relatedModels: [
                    {
                        modelType: 'equipmenttypes',
                        fieldName: 'equipment_type',
                        label: 'Equipment Type Documents'
                    }
                ],
            });

        case 'samplingrules':
            return createModelConfig({
                modelType: 'samplingrules',
                fields: {
                    id: { label: 'Sampling Rule ID' },
                    ruleset: { label: 'Ruleset ID' },
                    ruleset_name: { label: 'Ruleset Name' },
                    rule_type: { label: 'Rule Type ID' },
                    ruletype_name: { label: 'Rule Type' },
                    value: { label: 'Value' },
                    order: { label: 'Order' },
                    created_by: { label: 'Created By ID' },
                    modified_by: { label: 'Modified By ID' },
                    created_at: { label: 'Created At' },
                    modified_at: { label: 'Modified At' },
                },
                customRenderers: {
                    created_at: commonRenderers.datetime,
                    modified_at: commonRenderers.datetime,
                },
                sections: [
                    {
                        title: 'Rule Information',
                        fields: ['id', 'ruletype_name', 'value', 'order'],
                    },
                    {
                        title: 'Ruleset Details',
                        fields: ['ruleset_name', 'ruleset'],
                    },
                    {
                        title: 'System Information',
                        fields: ['created_by', 'modified_by', 'created_at', 'modified_at'],
                        auditLog: true,
                    },
                ],
                apiPath: 'api_SamplingRules_retrieve',
                relatedModels: [
                    {
                        modelType: 'samplingrulesets',
                        fieldName: 'ruleset',
                        label: 'Ruleset Documents'
                    },
                    {
                        modelType: 'customers',
                        fieldName: 'created_by',
                        label: 'Created By Documents'
                    },
                    {
                        modelType: 'customers',
                        fieldName: 'modified_by',
                        label: 'Modified By Documents'
                    }
                ],
            });

        case 'samplingrulesets':
            return createModelConfig({
                modelType: 'samplingrulesets',
                fields: {
                    id: { label: 'Ruleset ID' },
                    name: { label: 'Ruleset Name' },
                    part_type: { label: 'Part Type ID' },
                    process: { label: 'Process ID' },
                    step: { label: 'Step ID' },
                    rules: { label: 'Rules' },
                },
                customRenderers: {
                    rules: (rules) => {
                        if (!rules || !Array.isArray(rules)) return '—';
                        return `${rules.length} rule${rules.length !== 1 ? 's' : ''}`;
                    },
                },
                sections: [
                    {
                        title: 'Ruleset Information',
                        fields: ['id', 'name', 'rules'],
                    },
                    {
                        title: 'Associated Models',
                        fields: ['part_type', 'process', 'step'],
                        auditLog: true,
                    },
                ],
                apiPath: 'api_SamplingRuleSets_retrieve',
                relatedModels: [
                    {
                        modelType: 'parttypes',
                        fieldName: 'part_type',
                        label: 'Part Type Documents'
                    },
                    {
                        modelType: 'processes',
                        fieldName: 'process',
                        label: 'Process Documents'
                    },
                    {
                        modelType: 'steps',
                        fieldName: 'step',
                        label: 'Step Documents'
                    }
                ],
            });

        case 'customers':
            return createModelConfig({
                modelType: 'customers',
                fields: {
                    id: { label: 'Customer ID' },
                    username: { label: 'Username' },
                    first_name: { label: 'First Name' },
                    last_name: { label: 'Last Name' },
                    email: { label: 'Email' },
                    is_staff: { label: 'Is Staff' },
                    parent_company: { label: 'Parent Company ID' },
                },
                customRenderers: {
                    is_staff: commonRenderers.boolean,
                },
                sections: [
                    {
                        title: 'Customer Information',
                        fields: ['id', 'username', 'first_name', 'last_name', 'email'],
                    },
                    {
                        title: 'Company & Permissions',
                        fields: ['parent_company', 'is_staff'],
                        auditLog: true,
                    },
                ],
                apiPath: 'api_Customers_retrieve',
                relatedModels: [
                    {
                        modelType: 'companies',
                        fieldName: 'parent_company',
                        label: 'Company Documents'
                    }
                ],
            });

        case 'measurementdefinitions':
            return createModelConfig({
                modelType: 'measurementdefinitions',
                fields: {
                    id: { label: 'Measurement ID' },
                    label: { label: 'Label' },
                    step_name: { label: 'Step Name' },
                    allow_override: { label: 'Allow Override' },
                    allow_remeasure: { label: 'Allow Remeasure' },
                    allow_quarantine: { label: 'Allow Quarantine' },
                    unit: { label: 'Unit' },
                    require_qa_review: { label: 'Require QA Review' },
                    nominal: { label: 'Nominal Value' },
                    upper_tol: { label: 'Upper Tolerance' },
                    lower_tol: { label: 'Lower Tolerance' },
                    required: { label: 'Required' },
                    type: { label: 'Type' },
                    step: { label: 'Step ID' },
                },
                customRenderers: {
                    allow_override: commonRenderers.boolean,
                    allow_remeasure: commonRenderers.boolean,
                    allow_quarantine: commonRenderers.boolean,
                    require_qa_review: commonRenderers.boolean,
                    required: commonRenderers.boolean,
                },
                sections: [
                    {
                        title: 'Measurement Information',
                        fields: ['id', 'label', 'step_name', 'type', 'unit'],
                    },
                    {
                        title: 'Tolerances & Values',
                        fields: ['nominal', 'upper_tol', 'lower_tol'],
                    },
                    {
                        title: 'Permissions & Requirements',
                        fields: ['allow_override', 'allow_remeasure', 'allow_quarantine', 'require_qa_review', 'required'],
                        auditLog: true,
                    },
                ],
                apiPath: 'api_MeasurementDefinitions_retrieve',
                relatedModels: [
                    {
                        modelType: 'steps',
                        fieldName: 'step',
                        label: 'Step Documents'
                    }
                ],
            });

        // Keep existing models without FK relationships
        case 'errortypes':
            return createModelConfig({
                modelType: 'errortypes',
                fields: {
                    id: { label: 'Error Type ID' },
                    error_name: { label: 'Error Name' },
                    error_example: { label: 'Error Example' },
                    part_type: { label: 'Part Type ID' },
                    part_type_name: { label: 'Part Type Name' },
                },
                sections: [
                    {
                        title: 'Error Information',
                        fields: ['id', 'error_name', 'part_type_name'],
                    },
                    {
                        title: 'Error Details',
                        fields: ['error_example'],
                        auditLog: true,
                    },
                ],
                apiPath: 'api_Error-types_retrieve',
                relatedModels: [
                    {
                        modelType: 'parttypes',
                        fieldName: 'part_type',
                        label: 'Part Type Documents'
                    }
                ],
            });

        case 'equipmenttypes':
            return createModelConfig({
                modelType: 'equipmenttypes',
                fields: {
                    id: { label: 'Equipment Type ID' },
                    name: { label: 'Equipment Type Name' },
                },
                sections: [
                    {
                        title: 'Equipment Type Information',
                        fields: ['id', 'name'],
                        auditLog: true,
                    },
                ],
                apiPath: 'api_EquipmentTypes_retrieve',
            });

        case 'companies':
            return createModelConfig({
                modelType: 'companies',
                fields: {
                    id: { label: 'Company ID' },
                    name: { label: 'Company Name' },
                    description: { label: 'Description' },
                    created_at: { label: 'Created At' },
                    updated_at: { label: 'Last Updated' },
                    archived: { label: 'Archived' },
                },
                customRenderers: {
                    created_at: commonRenderers.datetime,
                    updated_at: commonRenderers.datetime,
                    archived: commonRenderers.boolean,
                },
                sections: [
                    {
                        title: 'Company Information',
                        fields: ['id', 'name', 'description'],
                    },
                    createSystemInfoSection(['archived', 'created_at', 'updated_at']),
                ],
                apiPath: 'api_Companies_retrieve',
            });

        case 'users':
            return createModelConfig({
                modelType: 'users',
                fields: {
                    id: { label: 'User ID' },
                    username: { label: 'Username' },
                    first_name: { label: 'First Name' },
                    last_name: { label: 'Last Name' },
                    email: { label: 'Email' },
                    is_staff: { label: 'Platform Staff' },
                    is_active: { label: 'Active Status' },
                    date_joined: { label: 'Date Joined' },
                    parent_company: { label: 'Parent Company ID' },
                    parent_company_name: { label: 'Company Name' },
                    // New fields
                    user_type: { label: 'User Type' },
                    user_type_display: { label: 'User Type' },
                    tenant_name: { label: 'Tenant' },
                },
                customRenderers: {
                    is_staff: commonRenderers.boolean,
                    is_active: commonRenderers.boolean,
                    date_joined: commonRenderers.datetime,
                    username: (value: any, data: any) => value || data?.email || '—',
                    full_name: (_value: any, data: any) => {
                        const firstName = data?.first_name || "";
                        const lastName = data?.last_name || "";
                        const fullName = `${firstName} ${lastName}`.trim();
                        return fullName || data?.username || data?.email || "—";
                    },
                    user_type_display: (value: any) => value || '—',
                    tenant_name: (_value: any, data: any) => data?.tenant?.name || '—',
                },
                sections: [
                    {
                        title: 'User Information',
                        fields: ['id', 'username', 'first_name', 'last_name', 'email'],
                    },
                    {
                        title: 'Account Status',
                        fields: ['is_active', 'user_type_display', 'is_staff', 'date_joined'],
                    },
                    {
                        title: 'Organization',
                        fields: ['tenant_name', 'parent_company_name'],
                        auditLog: true,
                    },
                ],
                apiPath: 'api_User_retrieve',
                relatedModels: [
                    {
                        modelType: 'companies',
                        fieldName: 'parent_company',
                        label: 'Company Documents'
                    }
                ],
            });

        case 'trackerorders':
            return createModelConfig({
                modelType: 'trackerorders',
                fields: {
                    id: { label: 'Tracker Order ID' },
                    order_status: { label: 'Order Status' },
                    name: { label: 'Order Name' },
                    customer_note: { label: 'Customer Note' },
                    estimated_completion: { label: 'Estimated Completion' },
                    original_completion_date: { label: 'Original Completion Date' },
                    archived: { label: 'Archived' },
                    created_at: { label: 'Created At' },
                    updated_at: { label: 'Last Updated' },
                },
                customRenderers: {
                    estimated_completion: commonRenderers.date,
                    original_completion_date: commonRenderers.date,
                    archived: commonRenderers.boolean,
                    created_at: commonRenderers.datetime,
                    updated_at: commonRenderers.datetime,
                },
                sections: [
                    {
                        title: 'Order Information',
                        fields: ['id', 'name', 'order_status'],
                    },
                    {
                        title: 'Timeline',
                        fields: ['estimated_completion', 'original_completion_date'],
                    },
                    {
                        title: 'Additional Details',
                        fields: ['customer_note', 'archived'],
                    },
                    createSystemInfoSection(['created_at', 'updated_at']),
                ],
                apiPath: 'api_TrackerOrders_retrieve',
            });

        case 'qualityreports':
            return createModelConfig({
                modelType: 'qualityreports',
                // Header reads "QR-2026-000015 · Nozzle Inspection" instead of
                // the generic "QualityReports Detail" — inspectors identify a
                // report by its number, not a UUID.
                getHeader: (qr) => ({
                    title: qr.report_number || 'Quality Report',
                    subtitle: qr.step_info?.name
                        ? (qr.step_info.process_name
                            ? `${qr.step_info.process_name} › ${qr.step_info.name}`
                            : qr.step_info.name)
                        : undefined,
                }),
                fields: {
                    report_number: { label: 'Report #' },
                    status_display: { label: 'Result' },
                    is_first_piece: { label: 'First Piece Inspection' },
                    description: { label: 'Description' },
                    part_info: { label: 'Part' },
                    step_info: { label: 'Process Step' },
                    machine_info: { label: 'Machine' },
                    sampling_method: { label: 'Sampling Method' },
                    detected_by_info: { label: 'Detected By' },
                    verified_by_info: { label: 'Verified By' },
                    operators_info: { label: 'Operators' },
                    errors_info: { label: 'Defect / Error Types' },
                    sample_size: { label: 'Sample Size' },
                    accept_number: { label: 'Accept (Ac)' },
                    reject_number: { label: 'Reject (Re)' },
                    file_info: { label: 'Attached File' },
                    created_at: { label: 'Created At' },
                },
                customRenderers: {
                    created_at: commonRenderers.datetime,
                    is_first_piece: commonRenderers.boolean,
                    // Colored pass/fail chip — scannable at a glance, the way a
                    // QA person triages a queue of reports.
                    status_display: (value: string, data: Record<string, unknown>) => {
                        const status = String((data?.status as string) || value || '').toUpperCase();
                        if (!status) return '—';
                        const tone = status === 'PASS'
                            ? 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300'
                            : status === 'FAIL'
                                ? 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300'
                                : 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300';
                        return <span className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-semibold ${tone}`}>{value || status}</span>;
                    },
                    part_info: (info) => {
                        if (!info) return '—';
                        const label = info.erp_id || `#${info.id}`;
                        const suffix = info.status ? ` · ${info.status}` : '';
                        if (!info.id) return `${label}${suffix}`;
                        return (
                            <Link to="/details/$model/$id" params={{ model: 'Parts', id: String(info.id) }} className="text-primary hover:underline font-medium">
                                {label}{suffix}
                            </Link>
                        );
                    },
                    step_info: (info) => {
                        if (!info) return '—';
                        const text = info.process_name ? `${info.process_name} › ${info.name}` : info.name;
                        if (!info.id) return text;
                        return (
                            <Link to="/details/$model/$id" params={{ model: 'Steps', id: String(info.id) }} className="text-primary hover:underline font-medium">
                                {text}
                            </Link>
                        );
                    },
                    machine_info: (info) => {
                        if (!info) return '—';
                        return info.type ? `${info.name} (${info.type})` : info.name;
                    },
                    detected_by_info: (info) => info ? (info.full_name || info.username) : '—',
                    verified_by_info: (info) => info ? (info.full_name || info.username) : '—',
                    operators_info: (operators) => {
                        if (!operators || !Array.isArray(operators) || operators.length === 0) return '—';
                        return operators.map(op => op.full_name || op.username).join(', ');
                    },
                    errors_info: (errors) => {
                        if (!errors || !Array.isArray(errors) || errors.length === 0) return '—';
                        return errors.map(err => err.name).join(', ');
                    },
                    // Link the attachment to its document detail so the drawing
                    // / cert / photo is one click away.
                    file_info: (info) => {
                        if (!info) return '—';
                        if (!info.id) return info.file_name || '—';
                        return (
                            <Link to="/details/$model/$id" params={{ model: 'Documents', id: String(info.id) }} className="text-primary hover:underline font-medium">
                                {info.file_name || 'Attachment'}
                            </Link>
                        );
                    },
                },
                sections: [
                    {
                        title: 'Report',
                        fields: ['report_number', 'status_display', 'is_first_piece', 'description'],
                    },
                    {
                        title: 'Inspection',
                        fields: ['part_info', 'step_info', 'machine_info', 'sampling_method'],
                    },
                    {
                        title: 'Personnel',
                        fields: ['detected_by_info', 'verified_by_info', 'operators_info'],
                    },
                    {
                        title: 'Findings',
                        fields: ['errors_info'],
                    },
                    // Populated for receiving / OSP acceptance-sampling reports;
                    // blank for ordinary in-process inspections.
                    {
                        title: 'Acceptance Sampling',
                        fields: ['sample_size', 'accept_number', 'reject_number'],
                    },
                    {
                        title: 'Attachments',
                        fields: ['file_info'],
                    },
                    createSystemInfoSection(['created_at']),
                ],
                apiPath: 'api_QualityReports_retrieve',
                relatedModels: [
                    {
                        modelType: 'steps',
                        fieldName: 'step',
                        label: 'Step Documents'
                    },
                    {
                        modelType: 'parts',
                        fieldName: 'part',
                        label: 'Part Documents'
                    }
                    // No single-machine documents link — equipment is role-tagged
                    // on equipment_links, not a single FK.
                ],
                actionButtons: [
                    {
                        label: 'Create CAPA',
                        variant: 'default',
                        getUrl: (modelData) => `/quality/capas/new?quality_reports=${modelData.id}`,
                        condition: (modelData) => modelData.status === 'FAIL',
                    },
                    {
                        label: 'Edit Report',
                        variant: 'outline',
                        getUrl: (modelData) => `/editor/qualityReports/edit/${modelData.id}`,
                    },
                ],
                linkedRecordsComponent: QRMeasurementsSection,
            });

        case 'quarantinedisposition':
            return createModelConfig({
                modelType: 'quarantinedisposition',
                // "DISP-2026-000016 · REWORK · IN_PROGRESS" beats a UUID header.
                getHeader: (d) => ({
                    title: d.disposition_number || 'Disposition',
                    subtitle: [d.disposition_type, d.current_state].filter(Boolean).join(' · ') || undefined,
                }),
                fields: {
                    disposition_number: { label: 'Disposition #' },
                    current_state: { label: 'State' },
                    disposition_type: { label: 'Type' },
                    severity_display: { label: 'Severity' },
                    completion_blockers: { label: 'Closure Status' },
                    rework_limit_exceeded: { label: 'Rework Limit' },
                    assignee_name: { label: 'Assigned To' },
                    due_date: { label: 'Due' },
                    part: { label: 'Part' },
                    step_info: { label: 'Step' },
                    work_order_erp_id: { label: 'Work Order' },
                    description: { label: 'Description' },
                    quality_reports: { label: 'Quality Reports' },
                    containment_action: { label: 'Containment Action' },
                    containment_completed_by_name: { label: 'Containment Completed By' },
                    containment_completed_at: { label: 'Containment Completed At' },
                    resolution_notes: { label: 'Resolution Notes' },
                    resolution_completed: { label: 'Resolution Complete' },
                    resolution_completed_by_name: { label: 'Completed By' },
                    resolution_completed_at: { label: 'Completed At' },
                    requires_customer_approval: { label: 'Customer Approval Required' },
                    customer_approval_received: { label: 'Approval Received' },
                    customer_approval_reference: { label: 'Approval Reference' },
                    customer_approval_date: { label: 'Approval Date' },
                    scrap_verified: { label: 'Scrap Verified' },
                    scrap_verification_method: { label: 'Verification Method' },
                    scrap_verified_by_name: { label: 'Verified By' },
                    scrap_verified_at: { label: 'Verified At' },
                    created_at: { label: 'Opened At' },
                    updated_at: { label: 'Last Updated' },
                    archived: { label: 'Archived' },
                },
                customRenderers: {
                    due_date: commonRenderers.date,
                    created_at: commonRenderers.datetime,
                    updated_at: commonRenderers.datetime,
                    resolution_completed_at: commonRenderers.datetime,
                    resolution_completed: commonRenderers.boolean,
                    containment_completed_at: commonRenderers.datetime,
                    customer_approval_date: commonRenderers.date,
                    customer_approval_received: commonRenderers.boolean,
                    requires_customer_approval: commonRenderers.boolean,
                    scrap_verified: commonRenderers.boolean,
                    scrap_verified_at: commonRenderers.datetime,
                    archived: commonRenderers.boolean,
                    // An OPEN disposition legitimately has no type yet.
                    disposition_type: (value) => value || '— (undecided)',
                    // Colored state chip — OPEN amber, IN_PROGRESS blue, CLOSED
                    // green, CANCELLED grey. The at-a-glance triage signal.
                    current_state: (value) => {
                        const s = String(value || '').toUpperCase();
                        if (!s) return '—';
                        const tone = s === 'CLOSED' ? 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300'
                            : s === 'IN_PROGRESS' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300'
                            : s === 'CANCELLED' ? 'bg-muted text-muted-foreground'
                            : 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300';
                        return <span className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-semibold ${tone}`}>{s.replace(/_/g, ' ')}</span>;
                    },
                    // Severity chip — CRITICAL red, MAJOR orange, MINOR yellow.
                    severity_display: (value, d) => {
                        if (!value) return '—';
                        const sev = String(d?.severity || '').toUpperCase();
                        const tone = sev === 'CRITICAL' ? 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300'
                            : sev === 'MAJOR' ? 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300'
                            : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300';
                        return <span className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-semibold ${tone}`}>{String(value)}</span>;
                    },
                    // The money field for QA: can I close this, and if not, why?
                    // Server computes the blocker list; render it plainly so the
                    // inspector doesn't have to guess (or hit Save to find out).
                    completion_blockers: (value, d) => {
                        const blockers = Array.isArray(value) ? value.filter(Boolean) : [];
                        if (blockers.length === 0) {
                            if (String(d?.current_state).toUpperCase() === 'CLOSED') {
                                return <span className="text-muted-foreground">Closed</span>;
                            }
                            return d?.can_be_completed
                                ? <span className="font-medium text-green-600 dark:text-green-400">Ready to close</span>
                                : '—';
                        }
                        return (
                            <ul className="list-disc space-y-0.5 pl-4 text-destructive">
                                {blockers.map((b: string, i: number) => <li key={i}>{b}</li>)}
                            </ul>
                        );
                    },
                    rework_limit_exceeded: (value) => value
                        ? <span className="font-medium text-destructive">Exceeded — escalate</span>
                        : <span className="text-muted-foreground">Within limit</span>,
                    part: (value, d) => {
                        const id = value || d?.part;
                        if (!id) return '—';
                        return (
                            <Link
                                to="/details/$model/$id"
                                params={{ model: 'Parts', id: String(id) }}
                                className="text-primary hover:underline font-medium"
                            >
                                View part
                            </Link>
                        );
                    },
                    step_info: (info) => {
                        if (!info) return '—';
                        if (info.id) {
                            return (
                                <Link
                                    to="/details/$model/$id"
                                    params={{ model: 'Steps', id: String(info.id) }}
                                    className="text-primary hover:underline font-medium"
                                >
                                    {info.name || 'Step'}
                                </Link>
                            );
                        }
                        return info.name || '—';
                    },
                    // WO routes to Control (the working surface), mirroring the
                    // Parts config.
                    work_order_erp_id: (value, d) => {
                        const label = value || 'Work Order';
                        const id = d?.work_order_id;
                        if (!id) return String(label);
                        return (
                            <Link
                                to="/workorder/$workOrderId/control"
                                params={{ workOrderId: String(id) }}
                                className="text-primary hover:underline font-medium"
                            >
                                {String(label)}
                            </Link>
                        );
                    },
                    quality_reports: (value) => {
                        if (!Array.isArray(value) || value.length === 0) return '—';
                        return (
                            <div className="flex flex-col gap-1">
                                {value.map((id: string, i: number) => (
                                    <Link
                                        key={id}
                                        to="/details/$model/$id"
                                        params={{ model: 'QualityReports', id: String(id) }}
                                        className="text-primary hover:underline text-sm"
                                    >
                                        {value.length > 1 ? `View report ${i + 1}` : 'View report'}
                                    </Link>
                                ))}
                            </div>
                        );
                    },
                },
                sections: [
                    {
                        title: 'Disposition',
                        fields: ['disposition_number', 'current_state', 'disposition_type', 'severity_display'],
                    },
                    {
                        title: 'Closure',
                        fields: ['completion_blockers', 'rework_limit_exceeded'],
                    },
                    {
                        title: 'Assignment',
                        fields: ['assignee_name', 'due_date'],
                    },
                    {
                        title: 'Context',
                        fields: ['part', 'step_info', 'work_order_erp_id', 'quality_reports'],
                    },
                    {
                        title: 'Containment',
                        fields: ['containment_action', 'containment_completed_by_name', 'containment_completed_at'],
                    },
                    {
                        title: 'Resolution',
                        fields: ['description', 'resolution_notes', 'resolution_completed',
                            'resolution_completed_by_name', 'resolution_completed_at'],
                    },
                    // USE_AS_IS / concession dispositions only; blank otherwise.
                    {
                        title: 'Customer Approval',
                        fields: ['requires_customer_approval', 'customer_approval_received',
                            'customer_approval_reference', 'customer_approval_date'],
                    },
                    // SCRAP dispositions only; blank otherwise.
                    {
                        title: 'Scrap Verification',
                        fields: ['scrap_verified', 'scrap_verification_method', 'scrap_verified_by_name', 'scrap_verified_at'],
                    },
                    {
                        title: 'System',
                        fields: ['created_at', 'updated_at', 'archived'],
                        auditLog: true,
                    },
                ],
                apiPath: 'api_QuarantineDispositions_retrieve',
                relatedModels: [
                    { modelType: 'parts', fieldName: 'part', label: 'Part Documents' },
                    { modelType: 'steps', fieldName: 'step', label: 'Step Documents' },
                ],
                // Detail is read-only; jumping to the editor is the action.
                actionButtons: [
                    {
                        label: 'Edit Disposition',
                        variant: 'default',
                        getUrl: (d) => `/dispositions/edit/${d.id}`,
                    },
                ],
            });

        case 'documents':
            return {
                fields: {
                    file_name: { label: 'File Name' },
                    classification: { label: 'Classification' },
                    is_image: { label: 'Is Image' },
                    version: { label: 'Version' },
                    upload_date: { label: 'Upload Date' },
                    uploaded_by_name: { label: 'Uploaded By' },
                    file_size: { label: 'File Size' },
                    content_type: { label: 'Content Type' },
                    created_at: { label: 'Created At' },
                    updated_at: { label: 'Last Updated' },
                },
                customRenderers: {
                    upload_date: commonRenderers.datetime,
                    created_at: commonRenderers.datetime,
                    updated_at: commonRenderers.datetime,
                    is_image: commonRenderers.boolean,
                    file_size: (value) => value ? `${(value / 1024).toFixed(2)} KB` : '—',
                },
                fetcher: (id) => api.api_Documents_retrieve({ params: { id } }),
                sections: {
                    header: [],
                    info: [
                        {
                            title: 'Document Information',
                            fields: ['file_name', 'classification', 'is_image', 'version'],
                        },
                        {
                            title: 'Upload Details',
                            fields: ['upload_date', 'uploaded_by_name', 'file_size', 'content_type'],
                        },
                        createSystemInfoSection(['created_at', 'updated_at']),
                    ],
                    related: [],
                    documents: [],
                },
                subcomponents: {
                    AuditTrailComponent: AuditTrail,
                },
            };

        case 'auditlog':
            return {
                fields: {
                    action: { label: 'Action' },
                    timestamp: { label: 'Timestamp' },
                    content_type_name: { label: 'Object Type' },
                    object_repr: { label: 'Object' },
                    object_pk: { label: 'Object ID' },
                    actor_display: { label: 'User' },
                    remote_addr: { label: 'IP Address' },
                    changes_display: { label: 'Changes' },
                },
                customRenderers: {
                    action: (value: number) => {
                        const labels: Record<number, { text: string; className: string }> = {
                            0: { text: 'Created', className: 'text-green-600 dark:text-green-400 font-medium' },
                            1: { text: 'Updated', className: 'text-blue-600 dark:text-blue-400 font-medium' },
                            2: { text: 'Deleted', className: 'text-red-600 dark:text-red-400 font-medium' },
                            3: { text: 'Accessed', className: 'text-gray-600 dark:text-gray-400 font-medium' },
                        };
                        const config = labels[value] || { text: 'Unknown', className: '' };
                        return <span className={config.className}>{config.text}</span>;
                    },
                    timestamp: commonRenderers.datetime,
                    actor_display: (_value: any, modelData: any) => {
                        const actor = modelData?.actor_info;
                        if (!actor) return <span className="text-muted-foreground">System</span>;
                        return (
                            <div>
                                <div className="font-medium">{actor.full_name || actor.username}</div>
                                {actor.email && <div className="text-sm text-muted-foreground">{actor.email}</div>}
                            </div>
                        );
                    },
                    object_repr: (_value: any, modelData: any) => {
                        // Try to link to the object
                        const contentType = modelData?.content_type_name?.toLowerCase();
                        const objectPk = modelData?.object_pk;
                        const objectRepr = modelData?.object_repr || `#${objectPk}`;

                        // Map content type to route model name
                        const modelMap: Record<string, string> = {
                            order: 'Orders', orders: 'Orders',
                            part: 'Parts', parts: 'Parts',
                            workorder: 'WorkOrders', work_order: 'WorkOrders',
                            process: 'Processes', processes: 'Processes',
                            step: 'Steps', steps: 'Steps',
                            parttype: 'PartTypes', part_type: 'PartTypes',
                            equipment: 'Equipments',
                            documents: 'Documents', document: 'Documents',
                            company: 'Companies', companies: 'Companies',
                            user: 'Users',
                        };

                        const routeModel = modelMap[contentType?.replace(/\s+/g, '')];

                        if (routeModel && objectPk && modelData?.action !== 2) {
                            return (
                                <Link
                                    to="/details/$model/$id"
                                    params={{ model: String(routeModel), id: String(objectPk) }}
                                    className="text-primary hover:underline font-medium"
                                >
                                    {objectRepr}
                                </Link>
                            );
                        }

                        return (
                            <span className={modelData?.action === 2 ? 'line-through text-muted-foreground' : ''}>
                                {objectRepr}
                            </span>
                        );
                    },
                    changes_display: (_value: any, modelData: any) => {
                        const changes = modelData?.changes;
                        if (!changes || typeof changes !== 'object') {
                            return <span className="text-muted-foreground">No changes recorded</span>;
                        }

                        const IGNORED = ['id', 'created_at', 'modified_at', 'created_by'];
                        const entries = Object.entries(changes).filter(
                            ([field, val]) =>
                                !IGNORED.includes(field) &&
                                Array.isArray(val) &&
                                val.length === 2 &&
                                !(val[0] === null && val[1] === null)
                        ) as [string, [any, any]][];

                        if (entries.length === 0) {
                            return <span className="text-muted-foreground">No significant changes</span>;
                        }

                        const formatFieldName = (f: string) => f.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                        const formatValue = (v: any) => {
                            if (v === null || v === undefined) return '—';
                            if (typeof v === 'string' && v.length > 50) return v.substring(0, 50) + '...';
                            return String(v);
                        };

                        return (
                            <div className="space-y-2">
                                {entries.map(([field, [oldVal, newVal]]) => (
                                    <div key={field} className="text-sm border-l-2 border-muted pl-3 py-1">
                                        <div className="font-medium text-foreground">{formatFieldName(field)}</div>
                                        <div className="flex flex-wrap gap-2 mt-1">
                                            <span className="text-red-600 dark:text-red-400 line-through">{formatValue(oldVal)}</span>
                                            <span className="text-muted-foreground">→</span>
                                            <span className="text-green-600 dark:text-green-400">{formatValue(newVal)}</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        );
                    },
                },
                fetcher: (id) => api.api_auditlog_retrieve({ params: { id: Number(id) } }),
                sections: {
                    header: [],
                    info: [
                        {
                            title: 'Event Details',
                            fields: ['action', 'timestamp', 'remote_addr'],
                        },
                        {
                            title: 'Audited Object',
                            fields: ['content_type_name', 'object_repr', 'object_pk'],
                        },
                        {
                            title: 'User',
                            fields: ['actor_display'],
                        },
                        {
                            title: 'Changes',
                            fields: ['changes_display'],
                        },
                    ],
                    related: [],
                    documents: [],
                },
                subcomponents: {},
            };

        default:
            // Return a minimal config for unknown models instead of throwing
            return {
                fields: {},
                fetcher: () => Promise.resolve({ id: 'unknown', error: `No detail view available for "${modelType}"` }),
                sections: {
                    header: [],
                    info: [{
                        title: 'Not Available',
                        fields: ['error'],
                    }],
                    related: [],
                    documents: [],
                },
                subcomponents: {},
            };
    }
};
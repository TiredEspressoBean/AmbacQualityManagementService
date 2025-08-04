import { api } from '@/lib/api/generated';
import type { FieldsConfig } from './ModelDetailPage';
import DocumentsSection from './DocumentsSection';
import AuditTrail from './AuditTrail';

// Helper functions for common field renderers
export const commonRenderers = {
    date: (value: any) => value ? new Date(value).toLocaleDateString() : '—',
    datetime: (value: any) => value ? new Date(value).toLocaleString() : '—',
    boolean: (value: any) => value ? 'Yes' : 'No',
    percentage: (value: any) => value ? `${Number(value).toFixed(1)}%` : '—',
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
    customRenderers?: Record<string, (value: any) => React.ReactNode>;
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
        getValue?: (modelData: any) => number | null;
    }>;
}): FieldsConfig => {
    const {
        modelType,
        fields,
        customRenderers = {},
        sections,
        apiPath,
        includeDocuments = true,
        includeAudit = true,
        relatedModels = [],
    } = config;

    return {
        fields,
        customRenderers,
        fetcher: (id) => (api as any)[apiPath]({ params: { id: Number(id) } }),
        sections: {
            header: [],
            info: sections,
            related: [],
            documents: [],
        },
        relatedModels,
        subcomponents: {
            ...(includeDocuments && { DocumentsSectionComponent: DocumentsSection }),
            ...(includeAudit && { AuditTrailComponent: AuditTrail }),
        },
    };
};

export const getFieldsConfigForModel = (modelType: string): FieldsConfig => {
    const normalizedType = modelType.toLowerCase();

    switch (normalizedType) {
        case 'parts':
            return {
                fields: {
                    part_status: { label: 'Status' },
                    ERP_id: { label: 'ERP ID' },
                    order_name: { label: 'Order' },
                    order: { label: 'Order ID' },
                    part_type_name: { label: 'Part Type' },
                    part_type: { label: 'Part Type ID' },
                    step_description: { label: 'Step' },
                    step: { label: 'Step ID' },
                    requires_sampling: { label: 'Requires Sampling' },
                    sampling_rule: { label: 'Sampling Rule ID' },
                    sampling_ruleset: { label: 'Sampling Ruleset ID' },
                    work_order: { label: 'Work Order ID' },
                    work_order_erp_id: { label: 'Work Order ERP ID' },
                    has_error: { label: 'Has Error' },
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
                },
                fetcher: (id) => api.api_Parts_retrieve({ params: { id: Number(id) } }),
                sections: {
                    header: [],
                    info: [
                        {
                            title: 'General Information',
                            fields: ['ERP_id', 'part_status', 'part_type_name', 'part_type'],
                        },
                        {
                            title: 'Production Details',
                            fields: ['order_name', 'order', 'step_description', 'step', 'work_order', 'work_order_erp_id'],
                        },
                        {
                            title: 'Quality Control',
                            fields: ['requires_sampling', 'sampling_rule', 'sampling_ruleset', 'has_error'],
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
                        fieldName: 'process', // Not used since we have getValue
                        label: 'Process Documents',
                        getValue: (part) => part.step_process_id || null // Assuming this field exists in your API response
                    }
                ],
                subcomponents: {
                    DocumentsSectionComponent: DocumentsSection,
                    AuditTrailComponent: AuditTrail,
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
                    current_hubspot_gate: { label: 'Current HubSpot Gate' },
                    last_synced_hubspot_stage: { label: 'Last Synced HubSpot Stage' },
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
                        title: 'Integration & System',
                        fields: ['current_hubspot_gate', 'last_synced_hubspot_stage', 'archived'],
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
                    hubspot_api_id: { label: 'HubSpot API ID' },
                },
                sections: [
                    {
                        title: 'Company Information',
                        fields: ['id', 'name', 'description'],
                    },
                    {
                        title: 'Integration',
                        fields: ['hubspot_api_id'],
                        auditLog: true,
                    },
                ],
                apiPath: 'api_Companies_retrieve',
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
                fetcher: (id) => api.api_Documents_retrieve({ params: { id: Number(id) } }),
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

        default:
            throw new Error(`Unknown model type: ${modelType}`);
    }
};
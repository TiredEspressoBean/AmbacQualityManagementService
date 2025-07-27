import { api } from '@/lib/api/generated';
import type { FieldsConfig } from './ModelDetailPage';

export const getFieldsConfigForModel = (modelType: string): FieldsConfig => {
    const normalizedType = modelType.toLowerCase();

    switch (normalizedType) {
        case 'parts':
            return {
                fields: {
                    part_status: { label: 'Status' },
                    ERP_id: { label: 'ERP ID' },
                    order_name: { label: 'Order' },
                    part_type_name: { label: 'Part Type' },
                    step_description: { label: 'Step' },
                    has_error: { label: 'Has Error' },
                    archived: { label: 'Archived' },
                    created_at: { label: 'Created At' },
                    updated_at: { label: 'Last Updated' }, // may be null
                },
                customRenderers: {
                    created_at: (value) => new Date(value).toLocaleString(),
                    updated_at: (value) => value ? new Date(value).toLocaleString() : '—',
                    has_error: (value) => (value ? 'Yes' : 'No'),
                    archived: (value) => (value ? 'Yes' : 'No'),
                },
                fetcher: (id) => api.api_Parts_retrieve({ params: { id: Number(id) } }),
            };


        case 'processes':
            return {
                fields: {
                    name: { label: 'Process Name' },
                    is_remanufactured: { label: 'Remanufactured' },
                    created_at: { label: 'Created At' },
                },
                customRenderers: {
                    is_remanufactured: (value) => (value ? 'Yes' : 'No'),
                    created_at: (value) => new Date(value).toLocaleString(),
                },
                fetcher: (id) => api.api_Processes_retrieve({ params: { id: Number(id) } }),
            };

        case 'orders':
            return {
                fields: {
                    customer_name: { label: 'Customer' },
                    company_name: { label: 'Company' },
                    status: { label: 'Status' },
                    created_at: { label: 'Created' },
                },
                customRenderers: {
                    created_at: (value) => new Date(value).toLocaleString(),
                },
                fetcher: (id) => api.api_Orders_retrieve({ params: { id: Number(id) } }),
            };

        case 'documents':
            return {
                fields: {
                    title: { label: 'Title' },
                    classification: { label: 'Classification' },
                    uploaded_by: { label: 'Uploaded By' },
                    uploaded_at: { label: 'Uploaded At' },
                },
                customRenderers: {
                    uploaded_at: (value) => new Date(value).toLocaleString(),
                },
                fetcher: (id) => api.api_Documents_retrieve({ params: { id: Number(id) } }),
            };

        default:
            return {
                fields: {},
                fetcher: async () => {
                    throw new Error(`Unknown model type: ${modelType}`);
                },
            };
    }
};

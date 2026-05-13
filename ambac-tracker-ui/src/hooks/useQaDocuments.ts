import { useQuery, queryOptions } from '@tanstack/react-query';
import { api } from '@/lib/api/generated';

export const qaDocumentsOptions = (workOrderId: string) => queryOptions({
    queryKey: ['qa-documents', workOrderId] as const,
    queryFn: () => api.api_WorkOrders_qa_documents_retrieve({ params: { id: workOrderId } }),
});

export function useQaDocuments(workOrderId: string) {
    return useQuery({
        ...qaDocumentsOptions(workOrderId),
        enabled: !!workOrderId
    });
}

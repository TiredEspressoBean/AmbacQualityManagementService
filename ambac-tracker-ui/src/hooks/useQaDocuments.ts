import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api/generated';

export function useQaDocuments(workOrderId: string) {
    return useQuery({
        queryKey: ['qa-documents', workOrderId],
        queryFn: () => api.api_WorkOrders_qa_documents_retrieve({ params: { id: workOrderId } }),
        enabled: !!workOrderId
    });
}
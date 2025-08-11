import { useQuery } from '@tanstack/react-query';

export function useQaDocuments(workOrderId: number) {
    return useQuery({
        queryKey: ['qa-documents', workOrderId],
        queryFn: async () => {
            // This will use the new qa_documents endpoint once the API is regenerated
            // For now, we'll use a direct fetch call
            const response = await fetch(`/api/WorkOrders/${workOrderId}/qa_documents/`);
            if (!response.ok) {
                throw new Error('Failed to fetch QA documents');
            }
            return response.json();
        },
        enabled: !!workOrderId
    });
}
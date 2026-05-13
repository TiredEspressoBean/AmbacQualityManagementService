import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export const documentVersionHistoryOptions = (documentId: string | undefined) => queryOptions({
    queryKey: ["document", documentId, "version-history"] as const,
    queryFn: () => api.api_Documents_version_history_retrieve({ params: { id: documentId! } }),
});

export function useDocumentVersionHistory(documentId: string | undefined) {
    return useQuery({
        ...documentVersionHistoryOptions(documentId),
        enabled: documentId !== undefined,
    });
}

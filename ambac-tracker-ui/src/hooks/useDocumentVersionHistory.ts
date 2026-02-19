import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export function useDocumentVersionHistory(documentId: string | undefined) {
    return useQuery({
        queryKey: ["document", documentId, "version-history"],
        queryFn: () => api.api_Documents_version_history_retrieve({ params: { id: documentId! } }),
        enabled: documentId !== undefined,
    });
}

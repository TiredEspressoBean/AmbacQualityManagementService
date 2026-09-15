import { useQuery, queryOptions, skipToken } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

/**
 * A document's full version lineage.
 *
 * The action returns `many=True` but declared no response, so spectacular
 * assumed the single-object detail serializer and the generated client
 * rejected every response with "expected object, received array" — the panel
 * never had data. Declaring `responses=DocumentsSerializer(many=True)` also
 * renamed the alias from `_retrieve` to `_list`, since it is a list endpoint.
 */
export const documentVersionHistoryOptions = (documentId: string | undefined) =>
    queryOptions({
        queryKey: ["document", documentId, "version-history"] as const,
        queryFn: documentId
            ? () => api.api_Documents_version_history_list({ params: { id: documentId } })
            : skipToken,
    });

export function useDocumentVersionHistory(documentId: string | undefined) {
    return useQuery(documentVersionHistoryOptions(documentId));
}

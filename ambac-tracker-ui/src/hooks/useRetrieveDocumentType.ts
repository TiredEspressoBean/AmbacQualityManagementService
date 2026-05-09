import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { Schema } from "@/lib/api/types";

type DocumentTypeResponse = Schema<"DocumentType">;

export function useRetrieveDocumentType(
    options: { params: { id: string } },
    queryOptions?: { enabled?: boolean }
) {
    return useQuery<DocumentTypeResponse>({
        queryKey: ["documentType", options.params],
        queryFn: () => api.api_DocumentTypes_retrieve({ params: options.params }) as Promise<DocumentTypeResponse>,
        enabled: queryOptions?.enabled ?? true,
    });
}

import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { Schema } from "@/lib/api/types";

type DocumentTypeResponse = Schema<"DocumentType">;

export const retrieveDocumentTypeOptions = (options: { params: { id: string } }) => queryOptions({
    queryKey: ["documentType", options.params] as const,
    queryFn: () => api.api_DocumentTypes_retrieve({ params: options.params }) as Promise<DocumentTypeResponse>,
});

export function useRetrieveDocumentType(
    options: { params: { id: string } },
    queryOpts?: { enabled?: boolean }
) {
    return useQuery({
        ...retrieveDocumentTypeOptions(options),
        enabled: queryOpts?.enabled ?? true,
    });
}

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export function useRetrieveDocumentType(
    options: { params: { id: string } },
    queryOptions?: { enabled?: boolean }
) {
    return useQuery({
        queryKey: ["documentType", options.params],
        queryFn: () => api.api_DocumentTypes_retrieve({ params: options.params }),
        enabled: queryOptions?.enabled ?? true,
    });
}

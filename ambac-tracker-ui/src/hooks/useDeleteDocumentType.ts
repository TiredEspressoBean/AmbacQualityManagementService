import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

// Invalidation-only helper (not a real queryOptions — no queryFn needed).
const documentTypesKeyOptions = () => ({ queryKey: ["documentTypes"] as const });

export function useDeleteDocumentType() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (id: string) => api.api_DocumentTypes_destroy(undefined, { params: { id } }),
        onSuccess: () => {
            queryClient.invalidateQueries(documentTypesKeyOptions());
        },
    });
}

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export function useSubmitDocumentForApproval(documentId: string) {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: () => api.api_Documents_submit_for_approval_create(undefined, { params: { id: documentId } }),
        onSuccess: () => {
            // Invalidate document and approval queries
            queryClient.invalidateQueries({
                predicate: (q) => q.queryKey[0] === "document" && q.queryKey[1] === documentId,
            });
            queryClient.invalidateQueries({
                predicate: (q) =>
                    q.queryKey[0] === "approvals" && q.queryKey[1] === "document" && q.queryKey[2] === documentId,
            });
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "documents" });
        },
    });
}

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export function useSubmitDocumentForApproval(documentId: string) {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: () => api.api_Documents_submit_for_approval_create({ id: documentId }),
        onSuccess: () => {
            // Invalidate document and approval queries
            queryClient.invalidateQueries({ queryKey: ["document", documentId] });
            queryClient.invalidateQueries({ queryKey: ["approvals", "document", documentId] });
            queryClient.invalidateQueries({ queryKey: ["documents"] });
        },
    });
}

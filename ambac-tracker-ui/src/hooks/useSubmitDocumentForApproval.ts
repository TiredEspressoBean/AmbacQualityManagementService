import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export function useSubmitDocumentForApproval(documentId: string) {
    const queryClient = useQueryClient();

    return useMutation({
        // eslint-disable-next-line local/no-as-any -- api_Documents_submit_for_approval_create requires a typed body but this action takes none; passing empty object
        mutationFn: () => api.api_Documents_submit_for_approval_create({} as any, { params: { id: documentId } }),
        onSuccess: () => {
            // Invalidate document and approval queries
            queryClient.invalidateQueries({ queryKey: ["document", documentId] });
            queryClient.invalidateQueries({ queryKey: ["approvals", "document", documentId] });
            queryClient.invalidateQueries({ queryKey: ["documents"] });
        },
    });
}

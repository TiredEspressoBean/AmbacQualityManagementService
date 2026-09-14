import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

// Invalidation-only helper (not a real queryOptions — no queryFn needed).
const approvalTemplatesKeyOptions = () => ({ queryKey: ["approvalTemplates"] as const });

export function useDeleteApprovalTemplate() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (id: string) => api.api_ApprovalTemplates_destroy(undefined, { params: { id } }),
        onSuccess: () => {
            queryClient.invalidateQueries(approvalTemplatesKeyOptions());
        },
    });
}

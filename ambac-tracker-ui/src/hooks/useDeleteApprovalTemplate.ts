import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export function useDeleteApprovalTemplate() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (id: string) => api.api_ApprovalTemplates_destroy({ params: { id } }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["approvalTemplates"] });
        },
    });
}

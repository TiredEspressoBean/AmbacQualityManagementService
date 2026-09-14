import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils.ts";

// Invalidation-only helper (not a real queryOptions — no queryFn needed).
const workordersKeyOptions = () => ({ queryKey: ["workorders"] as const });

export function useDeleteWorkOrder() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (id: string) =>
            api.api_WorkOrders_destroy(undefined, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        mutationKey: ["workorder", "delete"],
        onSuccess: () => {
            queryClient.invalidateQueries(workordersKeyOptions());
        },
    });
}

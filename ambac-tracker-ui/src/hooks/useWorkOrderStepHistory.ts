import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export function useWorkOrderStepHistory(
    workOrderId: string,
    options?: { enabled?: boolean }
) {
    return useQuery({
        queryKey: ["workorder-step-history", workOrderId],
        queryFn: () => api.api_WorkOrders_step_history_retrieve({ params: { id: workOrderId } }),
        enabled: (options?.enabled ?? true) && !!workOrderId,
    });
}

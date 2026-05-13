import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { Schema } from "@/lib/api/types";

type StepHistoryResponse = Schema<"WorkOrderStepHistoryResponse">;

export const workOrderStepHistoryOptions = (workOrderId: string) => queryOptions({
    queryKey: ["workorder-step-history", workOrderId] as const,
    // eslint-disable-next-line local/no-double-cast-via-unknown -- api_WorkOrders_step_history_retrieve returns Zod-inferred shape that doesn't match Schema<"WorkOrderStepHistoryResponse">
    queryFn: () => api.api_WorkOrders_step_history_retrieve({ params: { id: workOrderId } }) as unknown as Promise<StepHistoryResponse>,
});

export function useWorkOrderStepHistory(
    workOrderId: string,
    options?: { enabled?: boolean }
) {
    return useQuery({
        ...workOrderStepHistoryOptions(workOrderId),
        enabled: (options?.enabled ?? true) && !!workOrderId,
    });
}

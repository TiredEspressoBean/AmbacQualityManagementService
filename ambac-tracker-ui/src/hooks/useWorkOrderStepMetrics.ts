import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

/** Live part distribution at one step for a work order (4c). */
export type StepLiveMetrics = {
    step_id: string;
    total: number;
    in_rework: number;
    quarantined: number;
    awaiting_qa: number;
};

type StepMetricsResponse = { steps: StepLiveMetrics[] };

/**
 * Live per-step part counts + attention breakdown for a work order's flow map
 * (4c). Backed by a single grouped query (`/WorkOrders/{id}/step_metrics/`),
 * so counts are accurate regardless of list pagination.
 */
export function useWorkOrderStepMetrics(
    workOrderId: string | null | undefined,
    options?: { enabled?: boolean },
) {
    return useQuery({
        queryKey: ["workorder-step-metrics", workOrderId] as const,
        queryFn: () =>
            api.api_WorkOrders_step_metrics_retrieve({
                params: { id: String(workOrderId) },
            }) as Promise<StepMetricsResponse>,
        enabled: Boolean(workOrderId) && (options?.enabled ?? true),
    });
}

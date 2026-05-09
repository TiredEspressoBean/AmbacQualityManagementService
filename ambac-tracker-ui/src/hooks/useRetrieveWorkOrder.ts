import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { Schema } from "@/lib/api/types";

type WorkOrderResponse = Schema<"WorkOrder">;

export function useRetrieveWorkOrder(
    id: string,
    options?: { enabled?: boolean }
) {
    return useQuery<WorkOrderResponse>({
        queryKey: ["workorder", id],
        queryFn: () => api.api_WorkOrders_retrieve({ params: { id } }) as Promise<WorkOrderResponse>,
        enabled: options?.enabled ?? true,
    });
}
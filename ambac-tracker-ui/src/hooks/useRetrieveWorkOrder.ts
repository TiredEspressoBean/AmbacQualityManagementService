import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { Schema } from "@/lib/api/types";

type WorkOrderResponse = Schema<"WorkOrder">;

export const retrieveWorkOrderOptions = (id: string) => queryOptions({
    queryKey: ["workorder", id] as const,
    queryFn: () => api.api_WorkOrders_retrieve({ params: { id } }) as Promise<WorkOrderResponse>,
});

export function useRetrieveWorkOrder(
    id: string,
    options?: { enabled?: boolean }
) {
    return useQuery({
        ...retrieveWorkOrderOptions(id),
        enabled: options?.enabled ?? true,
    });
}

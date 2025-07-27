import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

export function useRetrieveWorkOrder(
    queries: Parameters<typeof api.api_WorkOrders_retrieve>[0],
    options?: { enabled?: boolean }
) {
    return useQuery({
        queryKey: ["workorder", queries],
        queryFn: () => api.api_WorkOrders_retrieve(queries),
        enabled: options?.enabled ?? true,
    });
}
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

export function useRetrieveWorkOrder(
    id: number,
    options?: { enabled?: boolean }
) {
    return useQuery({
        queryKey: ["workorder", id],
        queryFn: () => api.api_WorkOrders_retrieve({ params: { id } }),
        enabled: options?.enabled ?? true,
    });
}
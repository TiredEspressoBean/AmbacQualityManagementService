import { api } from "@/lib/api/generated";
import { useQuery } from "@tanstack/react-query";
import type { Schema } from "@/lib/api/types";

type OrdersResponse = Schema<"Orders">;

export const useRetrieveOrder = (id: string, p0: { enabled: boolean; }) => {
    return useQuery<OrdersResponse>({
        queryKey: ["order", id],
        queryFn: () => api.api_Orders_retrieve({ params: { id } }) as Promise<OrdersResponse>,
        ...p0
    });
};
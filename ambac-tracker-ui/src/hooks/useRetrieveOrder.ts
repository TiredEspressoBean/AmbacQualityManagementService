import { api } from "@/lib/api/generated";
import { useQuery, queryOptions } from "@tanstack/react-query";
import type { Schema } from "@/lib/api/types";

type OrdersResponse = Schema<"Orders">;

export const retrieveOrderOptions = (id: string) => queryOptions({
    queryKey: ["order", id] as const,
    queryFn: () => api.api_Orders_retrieve({ params: { id } }) as Promise<OrdersResponse>,
});

export const useRetrieveOrder = (id: string, p0: { enabled: boolean; }) => {
    return useQuery({
        ...retrieveOrderOptions(id),
        ...p0
    });
};

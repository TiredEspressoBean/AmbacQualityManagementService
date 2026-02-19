import { api } from "@/lib/api/generated";
import { useQuery } from "@tanstack/react-query";
import { schemas } from "@/lib/api/generated";
import { z } from "zod";

type OrderType = z.infer<typeof schemas.Orders>;

export const useRetrieveOrder = (id: string, p0: { enabled: boolean; }) => {
    return useQuery<OrderType>({
        queryKey: ["order", id],
        queryFn: () => api.api_Orders_retrieve({ params: { id } }),
        ...p0
    });
};
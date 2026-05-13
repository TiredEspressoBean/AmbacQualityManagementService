import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type UpdateOrderInput = Schema<"PatchedOrdersRequest">;
type UpdateOrderResponse = Schema<"Orders">;

export const useUpdateOrder = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateOrderResponse, unknown, { id: string; newData: UpdateOrderInput }>({
        mutationFn: async ({ id, newData }) => {
            return api.api_Orders_partial_update(newData as never, {
                params: { id },
                headers: {
                    "X-CSRFToken": getCookie("csrftoken"),
                },
            }) as Promise<UpdateOrderResponse>;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["orders"],
                predicate: (query) => query.queryKey[0] === "orders",
            });
        },
    });
};

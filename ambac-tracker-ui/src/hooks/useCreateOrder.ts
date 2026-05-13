import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type CreateOrderInput = Schema<"OrdersRequest">;
type CreateOrderResponse = Schema<"Orders">;

export const useCreateOrder = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateOrderResponse, unknown, CreateOrderInput>({
        mutationFn: (body) =>
            api.api_Orders_create(body as never, {
                headers: {
                    "X-CSRFToken": getCookie("csrftoken"),
                },
            }) as Promise<CreateOrderResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["orders"],
                predicate: (query) => query.queryKey[0] === "orders",
            });
        },
    });
};

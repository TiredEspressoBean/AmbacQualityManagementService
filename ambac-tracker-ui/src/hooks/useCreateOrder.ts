import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

// 1️⃣ Infer the exact “body” type that your create endpoint wants:
type CreateOrderInput = Parameters<typeof api.api_Orders_create>[0];
// 2️⃣ (Optionally) infer the return type, if you need it:
type CreateOrderResponse = Awaited<ReturnType<typeof api.api_Orders_create>>;

export const useCreateOrder = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateOrderResponse, unknown, CreateOrderInput>({
        mutationFn: (body) =>
            api.api_Orders_create(body, {
                headers: {
                    "X-CSRFToken": getCookie("csrftoken"),
                },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["orders"],
                predicate: (query) => query.queryKey[0] === "orders",
            });
        },
    });
};

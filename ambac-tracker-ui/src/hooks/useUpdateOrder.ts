import {api} from "@/lib/api/generated";
import {useMutation, useQueryClient} from "@tanstack/react-query";
import {schemas} from "@/lib/api/generated";
import {z} from "zod";
import {getCookie} from "@/lib/utils.ts"; // adjust if needed

type PatchedOrderType = z.infer<typeof schemas.PatchedOrdersRequest>;

export const useUpdateOrder = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async ({id, newData}: { id: string; newData: PatchedOrderType }) => {
            return api.api_Orders_partial_update(newData, {
                params: {id: id}, headers: {
                    "X-CSRFToken": getCookie("csrftoken")
                }
            },);
        }, onSuccess: () => {
            // Invalidate any keys that may be affected by this update
            queryClient.invalidateQueries({

                queryKey: ["orders"], predicate: (query) => query.queryKey[0] === "orders",
            });
        },
    });
};
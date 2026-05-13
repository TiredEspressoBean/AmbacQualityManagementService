import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type UpdateWorkOrderInput = Schema<"PatchedWorkOrderRequest">;
type UpdateWorkOrderResponse = Schema<"WorkOrder">;

type UpdateWorkOrderVariables = {
    id: string;
    data: UpdateWorkOrderInput;
};

export const useUpdateWorkOrder = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateWorkOrderResponse, unknown, UpdateWorkOrderVariables>({
        mutationFn: ({ id, data }) =>
            api.api_WorkOrders_partial_update(data as never, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<UpdateWorkOrderResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({
                predicate: (query) => {
                    const key = query.queryKey[0];
                    return key === "workorder" || key === "work-order";
                },
            });
        },
    });
};

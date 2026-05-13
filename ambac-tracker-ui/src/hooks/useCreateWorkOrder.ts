import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type CreateWorkOrderInput = Schema<"WorkOrderRequest">;
type CreateWorkOrderResponse = Schema<"WorkOrder">;

export const useCreateWorkOrder = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateWorkOrderResponse, unknown, CreateWorkOrderInput>({
        mutationFn: (data) =>
            api.api_WorkOrders_create(data as never, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<CreateWorkOrderResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["workorder"] });
        },
    });
};

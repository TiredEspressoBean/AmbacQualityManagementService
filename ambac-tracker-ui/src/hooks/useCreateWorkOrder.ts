import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

type CreateWorkorderInput = Parameters<typeof api.api_WorkOrders_create>[0];

type CreateWorkOrderResponse = Awaited<ReturnType<typeof api.api_WorkOrders_create>>;

export const useCreateWorkOrder = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateWorkOrderResponse, unknown, CreateWorkorderInput>({
        mutationFn: (data) =>
            api.api_WorkOrders_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["workorder"] });
        },
    });
};

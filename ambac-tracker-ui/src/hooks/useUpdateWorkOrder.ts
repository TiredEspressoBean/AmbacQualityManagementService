import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

// 1️⃣ Infer the exact input (body) that the partial-update endpoint wants:
type UpdateWorkOrderInput = Parameters<typeof api.api_WorkOrders_partial_update>[0];

// 2️⃣ Infer the shape of the `params` object:
type UpdateWorkOrderConfig = Parameters<typeof api.api_WorkOrders_partial_update>[1];
type UpdateWorkOrderParams = UpdateWorkOrderConfig["params"];

// 3️⃣ Infer the response type, if you need it:
type UpdateWorkOrderResponse = Awaited<ReturnType<typeof api.api_WorkOrders_partial_update>>;

// 4️⃣ Compose the variables your hook will accept:
type UpdateWorkOrderVariables = {
    id: UpdateWorkOrderParams["id"];   // number
    data: UpdateWorkOrderInput;        // exactly the patched-part payload
};

export const useUpdateWorkOrder = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateWorkOrderResponse, unknown, UpdateWorkOrderVariables>({
        mutationFn: ({ id, data }) =>
            api.api_WorkOrders_partial_update(data, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["workorder"],
                predicate: (query) => query.queryKey[0] === "workorder",
            });
        },
    });
};

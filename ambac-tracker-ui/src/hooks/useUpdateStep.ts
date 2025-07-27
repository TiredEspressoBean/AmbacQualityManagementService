import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

// 1️⃣ Infer the exact input (body) that the partial-update endpoint wants:
type UpdateStepInput = Parameters<typeof api.api_Steps_partial_update>[0];

// 2️⃣ Infer the shape of the `params` object:
type UpdateStepConfig = Parameters<typeof api.api_Steps_partial_update>[1];
type UpdateStepParams = UpdateStepConfig["params"];

// 3️⃣ Infer the response type, if you need it:
type UpdateStepResponse = Awaited<ReturnType<typeof api.api_Steps_partial_update>>;

// 4️⃣ Compose the variables your hook will accept:
type UpdateStepVariables = {
    id: UpdateStepParams["id"];   // number
    data: UpdateStepInput;        // exactly the patched-part payload
};

export const useUpdateStep = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateStepResponse, unknown, UpdateStepVariables>({
        mutationFn: ({ id, data }) =>
            api.api_Steps_partial_update(data, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["step"],
                predicate: (query) => query.queryKey[0] === "step",
            });
        },
    });
};

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

// 1️⃣ Infer the exact input (body) that the partial-update endpoint wants:
type UpdateProcessInput = Parameters<typeof api.api_Processes_partial_update>[0];

// 2️⃣ Infer the shape of the `params` object:
type UpdateProcessConfig = Parameters<typeof api.api_Processes_partial_update>[1];
type UpdateProcessParams = UpdateProcessConfig["params"];

// 3️⃣ Infer the response type, if you need it:
type UpdateProcessResponse = Awaited<ReturnType<typeof api.api_Processes_partial_update>>;

// 4️⃣ Compose the variables your hook will accept:
type UpdateProcessVariables = {
    id: UpdateProcessParams["id"];   // number
    data: UpdateProcessInput;        // exactly the patched-part payload
};

export const useUpdateProcess = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateProcessResponse, unknown, UpdateProcessVariables>({
        mutationFn: ({ id, data }) =>
            api.api_Processes_partial_update(data, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["process"],
                predicate: (query) => query.queryKey[0] === "process",
            });
        },
    });
};

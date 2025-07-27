import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

// 1️⃣ Infer the exact input (body) that the partial-update endpoint wants:
type UpdateErrorTypeInput = Parameters<typeof api.api_Error_types_partial_update>[0];

// 2️⃣ Infer the shape of the `params` object:
type UpdateErrorTypeConfig = Parameters<typeof api.api_Error_types_partial_update>[1];
type UpdateErrorTypeParams = UpdateErrorTypeConfig["params"];

// 3️⃣ Infer the response type, if you need it:
type UpdateErrorTypeResponse = Awaited<ReturnType<typeof api.api_Error_types_partial_update>>;

// 4️⃣ Compose the variables your hook will accept:
type UpdateErrorTypeVariables = {
    id: UpdateErrorTypeParams["id"];   // number
    data: UpdateErrorTypeInput;        // exactly the patched-part payload
};

export const useUpdateErrorType = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateErrorTypeResponse, unknown, UpdateErrorTypeVariables>({
        mutationFn: ({ id, data }) =>
            api.api_Error_types_partial_update(data, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["error-types"],
                predicate: (query) => query.queryKey[0] === "error-types",
            });
        },
    });
};

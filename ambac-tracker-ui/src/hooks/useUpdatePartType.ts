import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

// 1️⃣ Infer the exact input (body) that the partial-update endpoint wants:
type UpdatePartTypeInput = Parameters<typeof api.api_PartTypes_partial_update>[0];

// 2️⃣ Infer the shape of the `params` object:
type UpdatePartTypeConfig = Parameters<typeof api.api_PartTypes_partial_update>[1];
type UpdatePartTypeParams = UpdatePartTypeConfig["params"];

// 3️⃣ Infer the response type, if you need it:
type UpdatePartTypeResponse = Awaited<ReturnType<typeof api.api_PartTypes_partial_update>>;

// 4️⃣ Compose the variables your hook will accept:
type UpdatePartTypeVariables = {
    id: UpdatePartTypeParams["id"];   // number
    data: UpdatePartTypeInput;        // exactly the patched-part payload
};

export const useUpdatePartType = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdatePartTypeResponse, unknown, UpdatePartTypeVariables>({
        mutationFn: ({ id, data }) =>
            api.api_PartTypes_partial_update(data, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["parttypes"],
                predicate: (query) => query.queryKey[0] === "parttypes",
            });
        },
    });
};

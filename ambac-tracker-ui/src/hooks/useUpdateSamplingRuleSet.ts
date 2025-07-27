import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

// 1️⃣ Infer the exact input (body) that the partial-update endpoint wants:
type UpdatePartInput = Parameters<typeof api.api_Sampling_rule_sets_partial_update>[0];

// 2️⃣ Infer the shape of the `params` object:
type UpdatePartConfig = Parameters<typeof api.api_Sampling_rule_sets_partial_update>[1];
type UpdatePartParams = UpdatePartConfig["params"];

// 3️⃣ Infer the response type, if you need it:
type UpdatePartResponse = Awaited<ReturnType<typeof api.api_Sampling_rule_sets_partial_update>>;

// 4️⃣ Compose the variables your hook will accept:
type UpdatePartVariables = {
    id: UpdatePartParams["id"];   // number
    data: UpdatePartInput;        // exactly the patched-part payload
};

export const useUpdateSamplingRuleSet = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdatePartResponse, unknown, UpdatePartVariables>({
        mutationFn: ({ id, data }) =>
            api.api_Sampling_rule_sets_partial_update(data, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["sampling_rule_set"],
                predicate: (query) => query.queryKey[0] === "sampling_rule_set",
            });
        },
    });
};

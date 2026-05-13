import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type UpdateSamplingRuleSetInput = Schema<"PatchedSamplingRuleSetRequest">;
type UpdateSamplingRuleSetResponse = Schema<"SamplingRuleSet">;

type UpdateSamplingRuleSetVariables = {
    id: string;
    data: UpdateSamplingRuleSetInput;
};

export const useUpdateSamplingRuleSet = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateSamplingRuleSetResponse, unknown, UpdateSamplingRuleSetVariables>({
        mutationFn: ({ id, data }) =>
            api.api_Sampling_rule_sets_partial_update(data as never, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<UpdateSamplingRuleSetResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["sampling_rule_set"],
                predicate: (query) => query.queryKey[0] === "sampling_rule_set",
            });
        },
    });
};

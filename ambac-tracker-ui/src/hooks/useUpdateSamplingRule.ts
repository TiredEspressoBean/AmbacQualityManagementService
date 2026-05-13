import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type UpdateSamplingRuleInput = Schema<"PatchedSamplingRuleRequest">;
type UpdateSamplingRuleResponse = Schema<"SamplingRule">;

type UpdateSamplingRuleVariables = {
    id: string;
    data: UpdateSamplingRuleInput;
};

export const useUpdateSamplingRule = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateSamplingRuleResponse, unknown, UpdateSamplingRuleVariables>({
        mutationFn: ({ id, data }) =>
            api.api_Sampling_rules_partial_update(data as never, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<UpdateSamplingRuleResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["sampling-rule"],
                predicate: (query) => query.queryKey[0] === "sampling-rule",
            });
        },
    });
};

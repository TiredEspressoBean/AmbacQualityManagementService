import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

// Types inferred from generated Zodios client
type UpdateSamplingRulesInput = Parameters<typeof api.api_Steps_update_sampling_rules_create>[0];
type UpdateSamplingRulesParams = Parameters<typeof api.api_Steps_update_sampling_rules_create>[1]["params"];
type UpdateSamplingRulesResponse = Awaited<ReturnType<typeof api.api_Steps_update_sampling_rules_create>>;

type UpdateSamplingRulesVariables = {
    id: UpdateSamplingRulesParams["id"];
    data: UpdateSamplingRulesInput;
};

export const useUpdateStepSamplingRules = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateSamplingRulesResponse, unknown, UpdateSamplingRulesVariables>({
        mutationFn: ({ id, data }) =>
            api.api_Steps_update_sampling_rules_create(data, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["sampling_rule_set"],
                predicate: (q) => q.queryKey[0] === "sampling_rule_set",
            });
        },
    });
};

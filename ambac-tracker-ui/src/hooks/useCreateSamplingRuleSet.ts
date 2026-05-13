import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type CreateSamplingRuleSetInput = Schema<"SamplingRuleSetRequest">;
type CreateSamplingRuleSetResponse = Schema<"SamplingRuleSet">;

export const useCreateSamplingRuleSet = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateSamplingRuleSetResponse, unknown, CreateSamplingRuleSetInput>({
        mutationFn: (data) =>
            api.api_Sampling_rule_sets_create(data as never, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<CreateSamplingRuleSetResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["sampling_rule_set"] });
        },
    });
};

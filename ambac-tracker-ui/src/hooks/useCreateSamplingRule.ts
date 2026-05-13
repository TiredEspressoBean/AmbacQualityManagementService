import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type CreateSamplingRuleInput = Schema<"SamplingRuleRequest">;
type CreateSamplingRuleResponse = Schema<"SamplingRule">;

export const useCreateSamplingRule = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateSamplingRuleResponse, unknown, CreateSamplingRuleInput>({
        mutationFn: (data) =>
            api.api_Sampling_rules_create(data as never, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<CreateSamplingRuleResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["sampling-rule"] });
        },
    });
};

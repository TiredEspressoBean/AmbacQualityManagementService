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

// Invalidation-only helper (not a real queryOptions — no queryFn needed).
const samplingRuleInvalidateOptions = () => ({
    queryKey: ["sampling-rule"] as const,
    predicate: (query: { queryKey: readonly unknown[] }) => query.queryKey[0] === "sampling-rule",
});

export const useUpdateSamplingRule = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateSamplingRuleResponse, unknown, UpdateSamplingRuleVariables>({
        mutationFn: ({ id, data }) =>
            api.api_Sampling_rules_partial_update(data as never, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<UpdateSamplingRuleResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries(samplingRuleInvalidateOptions());
        },
    });
};

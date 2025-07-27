import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated.ts"

export function useRetrieveSamplingRulesSets (queries: Parameters<typeof api.api_Sampling_rule_sets_list>[0]) {
    return useQuery({
        queryKey: ["sampling-rules-sets", queries],
        queryFn: () => api.api_Sampling_rule_sets_list(queries),
    });
};
import { useQuery, queryOptions } from "@tanstack/react-query"
import { api } from "@/lib/api/generated.ts"

type QueryKey = Parameters<typeof api.api_Sampling_rule_sets_retrieve>[0]

export const retrieveSamplingRuleSetOptions = (queries: QueryKey) => queryOptions({
    queryKey: ["sampling_rule_set", queries] as const,
    queryFn: () => api.api_Sampling_rule_sets_retrieve(queries),
});

export function useRetrieveSamplingRuleSet(
    queries: QueryKey,
    options?: Omit<ReturnType<typeof retrieveSamplingRuleSetOptions>, "queryKey" | "queryFn">
) {
    return useQuery({
        ...retrieveSamplingRuleSetOptions(queries),
        ...options,
    })
}

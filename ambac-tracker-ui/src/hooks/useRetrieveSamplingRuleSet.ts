import { useQuery, type UseQueryOptions } from "@tanstack/react-query"
import { api } from "@/lib/api/generated.ts"

type QueryKey = Parameters<typeof api.api_Sampling_rule_sets_retrieve>[0]
type QueryReturn = Awaited<ReturnType<typeof api.api_Sampling_rule_sets_retrieve>>

export function useRetrieveSamplingRuleSet(
    queries: QueryKey,
    options?: Omit<UseQueryOptions<QueryReturn, Error>, "queryKey" | "queryFn">
) {
    return useQuery({
        queryKey: ["sampling_rule_set", queries],
        queryFn: () => api.api_Sampling_rule_sets_retrieve(queries),
        ...options,
    })
}
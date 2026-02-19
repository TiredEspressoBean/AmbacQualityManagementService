import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

export function useRetrieveSamplingRulesSets(
  queries?: Parameters<typeof api.api_Sampling_rule_sets_list>[0],
  options?: Omit<
    UseQueryOptions<
      Awaited<ReturnType<typeof api.api_Sampling_rule_sets_list>>,
      Error
    >,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: ["sampling-rules-sets", queries],
    queryFn: () => api.api_Sampling_rule_sets_list(queries),
    ...options,
  });
}
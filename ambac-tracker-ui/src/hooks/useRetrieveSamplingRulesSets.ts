import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

type SamplingRuleSetsListQueries = NonNullable<operations["api_Sampling_rule_sets_list"]["parameters"]["query"]>;
type SamplingRuleSetsListResponse = components["schemas"]["PaginatedSamplingRuleSetList"];

type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrieveSamplingRulesSets(
  queries?: SamplingRuleSetsListQueries,
  config?: ListHookConfig,
  options?: Omit<UseQueryOptions<SamplingRuleSetsListResponse, Error>, "queryKey" | "queryFn">
) {
  return useQuery<SamplingRuleSetsListResponse, Error>({
    queryKey: ["sampling-rules-sets", queries, config],
    queryFn: () =>
      api.api_Sampling_rule_sets_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<SamplingRuleSetsListResponse>,
    ...options,
  });
}

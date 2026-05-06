import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

type SamplingRulesListQueries = NonNullable<operations["api_Sampling_rules_list"]["parameters"]["query"]>;
type SamplingRulesListResponse = components["schemas"]["PaginatedSamplingRuleList"];

type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrieveSamplingRules(
  queries?: SamplingRulesListQueries,
  config?: ListHookConfig,
  options?: Omit<UseQueryOptions<SamplingRulesListResponse, Error>, "queryKey" | "queryFn">
) {
  return useQuery<SamplingRulesListResponse, Error>({
    queryKey: ["sampling-rules", queries, config],
    queryFn: () =>
      api.api_Sampling_rules_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<SamplingRulesListResponse>,
    ...options,
  });
}

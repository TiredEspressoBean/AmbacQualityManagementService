import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

type SamplingRuleSetsListQueries = NonNullable<operations["api_Sampling_rule_sets_list"]["parameters"]["query"]>;
type SamplingRuleSetsListResponse = components["schemas"]["PaginatedSamplingRuleSetList"];

type ListHookConfig = {
  headers?: Record<string, string>;
};

export const samplingRuleSetsOptions = (queries?: SamplingRuleSetsListQueries, config?: ListHookConfig) =>
  queryOptions({
    queryKey: ["sampling-rules-sets", queries, config] as const,
    queryFn: () =>
      api.api_Sampling_rule_sets_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<SamplingRuleSetsListResponse>,
  });

export const samplingRuleSetsMetadataOptions = () =>
  queryOptions({
    queryKey: ["metadata", "SamplingRuleSets", "Sampling-rule-sets"] as const,
    queryFn: () => api.api_Sampling_rule_sets_metadata_retrieve(),
  });

export function useRetrieveSamplingRulesSets(
  queries?: SamplingRuleSetsListQueries,
  config?: ListHookConfig,
  options?: Omit<ReturnType<typeof samplingRuleSetsOptions>, "queryKey" | "queryFn">
) {
  return useQuery({
    ...samplingRuleSetsOptions(queries, config),
    ...options,
  });
}

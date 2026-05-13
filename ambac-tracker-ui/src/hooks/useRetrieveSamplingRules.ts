import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

type SamplingRulesListQueries = NonNullable<operations["api_Sampling_rules_list"]["parameters"]["query"]>;
type SamplingRulesListResponse = components["schemas"]["PaginatedSamplingRuleList"];

type ListHookConfig = {
  headers?: Record<string, string>;
};

export const samplingRulesOptions = (queries?: SamplingRulesListQueries, config?: ListHookConfig) =>
  queryOptions({
    queryKey: ["sampling-rules", queries, config] as const,
    queryFn: () =>
      api.api_Sampling_rules_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<SamplingRulesListResponse>,
  });

export const samplingRulesMetadataOptions = () =>
  queryOptions({
    queryKey: ["metadata", "SamplingRules", "Sampling-rules"] as const,
    queryFn: () => api.api_Sampling_rules_metadata_retrieve(),
  });

export function useRetrieveSamplingRules(
  queries?: SamplingRulesListQueries,
  config?: ListHookConfig,
  options?: Omit<ReturnType<typeof samplingRulesOptions>, "queryKey" | "queryFn">
) {
  return useQuery({
    ...samplingRulesOptions(queries, config),
    ...options,
  });
}

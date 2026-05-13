import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { components, operations } from "@/lib/api/generated-types";

// Strict query types pulled from the OpenAPI spec (avoids zodios passthrough leakage).
type MeasurementDefinitionsListQueries = NonNullable<operations["api_MeasurementDefinitions_list"]["parameters"]["query"]>;
type MeasurementDefinitionsListResponse = components["schemas"]["PaginatedMeasurementDefinitionList"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export const retrieveMeasurementDefinitionsOptions = (queries?: MeasurementDefinitionsListQueries, config?: ListHookConfig) => queryOptions({
  queryKey: ["measurementDefinitions", queries, config] as const,
  queryFn: () =>
    api.api_MeasurementDefinitions_list(
      (queries || config ? { queries, ...config } : undefined) as never,
    ) as Promise<MeasurementDefinitionsListResponse>,
});

export function useRetrieveMeasurementDefinitions(
  queries?: MeasurementDefinitionsListQueries,
  config?: ListHookConfig,
  options?: Omit<ReturnType<typeof retrieveMeasurementDefinitionsOptions>, "queryKey" | "queryFn">
) {
  return useQuery({
    ...retrieveMeasurementDefinitionsOptions(queries, config),
    ...options,
  });
}

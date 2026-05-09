import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { components, operations } from "@/lib/api/generated-types";

// Strict query types pulled from the OpenAPI spec (avoids zodios passthrough leakage).
type MeasurementDefinitionsListQueries = NonNullable<operations["api_MeasurementDefinitions_list"]["parameters"]["query"]>;
type MeasurementDefinitionsListResponse = components["schemas"]["PaginatedMeasurementDefinitionList"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrieveMeasurementDefinitions(
  queries?: MeasurementDefinitionsListQueries,
  config?: ListHookConfig,
  options?: Omit<UseQueryOptions<MeasurementDefinitionsListResponse, Error>, "queryKey" | "queryFn">
) {
  return useQuery<MeasurementDefinitionsListResponse, Error>({
    queryKey: ["measurementDefinitions", queries, config],
    queryFn: () =>
      api.api_MeasurementDefinitions_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<MeasurementDefinitionsListResponse>,
    ...options,
  });
}

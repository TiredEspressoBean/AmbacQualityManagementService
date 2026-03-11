import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

// Extract queries type from Zodios endpoint
type MeasurementDefinitionsListQueries = Parameters<typeof api.api_MeasurementDefinitions_list>[0] extends { queries?: infer Q } ? Q : Parameters<typeof api.api_MeasurementDefinitions_list>[0];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrieveMeasurementDefinitions(
  queries?: MeasurementDefinitionsListQueries,
  config?: ListHookConfig,
  options?: Omit<
    UseQueryOptions<
      Awaited<ReturnType<typeof api.api_MeasurementDefinitions_list>>,
      Error
    >,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: ["measurementDefinitions", queries, config],
    queryFn: () => api.api_MeasurementDefinitions_list(queries || config ? { queries, ...config } : undefined),
    ...options,
  });
}

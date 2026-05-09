import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

// Strict types pulled from the OpenAPI spec.
type HeatMapAnnotationListQueries = NonNullable<operations["api_HeatMapAnnotation_list"]["parameters"]["query"]>;
type HeatMapAnnotationListResponse = components["schemas"]["PaginatedHeatMapAnnotationsList"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrieveHeatMapAnnotations(
  queries?: HeatMapAnnotationListQueries,
  config?: ListHookConfig,
  options?: Omit<UseQueryOptions<HeatMapAnnotationListResponse, Error>, "queryKey" | "queryFn">
) {
  return useQuery<HeatMapAnnotationListResponse, Error>({
    queryKey: ["heatMapAnnotation", queries, config],
    queryFn: () =>
      api.api_HeatMapAnnotation_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<HeatMapAnnotationListResponse>,
    ...options,
  });
}

import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

// Strict types pulled from the OpenAPI spec.
type HeatMapAnnotationListQueries = NonNullable<operations["api_HeatMapAnnotation_list"]["parameters"]["query"]>;
type HeatMapAnnotationListResponse = components["schemas"]["PaginatedHeatMapAnnotationsList"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export const retrieveHeatMapAnnotationsOptions = (queries?: HeatMapAnnotationListQueries, config?: ListHookConfig) => queryOptions({
  queryKey: ["heatMapAnnotation", queries, config] as const,
  queryFn: () =>
    api.api_HeatMapAnnotation_list(
      (queries || config ? { queries, ...config } : undefined) as never,
    ) as Promise<HeatMapAnnotationListResponse>,
});

export function useRetrieveHeatMapAnnotations(
  queries?: HeatMapAnnotationListQueries,
  config?: ListHookConfig,
  options?: Omit<ReturnType<typeof retrieveHeatMapAnnotationsOptions>, "queryKey" | "queryFn">
) {
  return useQuery({
    ...retrieveHeatMapAnnotationsOptions(queries, config),
    ...options,
  });
}

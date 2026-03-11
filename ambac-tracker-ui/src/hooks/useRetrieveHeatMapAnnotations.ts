import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

// Extract queries type from Zodios endpoint
type HeatMapAnnotationListQueries = Parameters<typeof api.api_HeatMapAnnotation_list>[0] extends { queries?: infer Q } ? Q : Parameters<typeof api.api_HeatMapAnnotation_list>[0];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrieveHeatMapAnnotations(
  queries?: HeatMapAnnotationListQueries,
  config?: ListHookConfig,
  options?: Omit<
    UseQueryOptions<
      Awaited<ReturnType<typeof api.api_HeatMapAnnotation_list>>,
      Error
    >,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: ["heatMapAnnotation", queries, config],
    queryFn: () => api.api_HeatMapAnnotation_list(queries || config ? { queries, ...config } : undefined),
    ...options,
  });
}

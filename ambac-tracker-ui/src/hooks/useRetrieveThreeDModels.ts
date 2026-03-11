import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

// Extract queries type from Zodios endpoint
type ThreeDModelsListQueries = Parameters<typeof api.api_ThreeDModels_list>[0] extends { queries?: infer Q } ? Q : Parameters<typeof api.api_ThreeDModels_list>[0];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrieveThreeDModels(
  queries?: ThreeDModelsListQueries,
  config?: ListHookConfig,
  options?: Omit<
    UseQueryOptions<
      Awaited<ReturnType<typeof api.api_ThreeDModels_list>>,
      Error
    >,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: ["threeDModel", queries, config],
    queryFn: () => api.api_ThreeDModels_list(queries || config ? { queries, ...config } : undefined),
    ...options,
  });
}

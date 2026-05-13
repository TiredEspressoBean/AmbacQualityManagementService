import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

type ThreeDModelsListQueries = NonNullable<operations["api_ThreeDModels_list"]["parameters"]["query"]>;
type ThreeDModelsListResponse = components["schemas"]["PaginatedThreeDModelList"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export const threeDModelsOptions = (queries?: ThreeDModelsListQueries, config?: ListHookConfig) =>
  queryOptions({
    queryKey: ["threeDModel", queries, config] as const,
    queryFn: () =>
      api.api_ThreeDModels_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<ThreeDModelsListResponse>,
  });

export const threeDModelsMetadataOptions = () =>
  queryOptions({
    queryKey: ["metadata", "ThreeDModels", "ThreeDModels"] as const,
    queryFn: () => api.api_ThreeDModels_metadata_retrieve(),
  });

export function useRetrieveThreeDModels(
  queries?: ThreeDModelsListQueries,
  config?: ListHookConfig,
  options?: Omit<ReturnType<typeof threeDModelsOptions>, "queryKey" | "queryFn">
) {
  return useQuery({
    ...threeDModelsOptions(queries, config),
    ...options,
  });
}

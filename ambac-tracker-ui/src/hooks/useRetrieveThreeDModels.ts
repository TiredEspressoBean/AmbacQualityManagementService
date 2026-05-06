import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

type ThreeDModelsListQueries = NonNullable<operations["api_ThreeDModels_list"]["parameters"]["query"]>;
type ThreeDModelsListResponse = components["schemas"]["PaginatedThreeDModelList"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrieveThreeDModels(
  queries?: ThreeDModelsListQueries,
  config?: ListHookConfig,
  options?: Omit<
    UseQueryOptions<ThreeDModelsListResponse, Error>,
    "queryKey" | "queryFn"
  >
) {
  return useQuery<ThreeDModelsListResponse, Error>({
    queryKey: ["threeDModel", queries, config],
    queryFn: () =>
      api.api_ThreeDModels_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<ThreeDModelsListResponse>,
    ...options,
  });
}

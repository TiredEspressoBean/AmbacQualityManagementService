import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

type HarvestedComponentsListQueries = NonNullable<operations["api_HarvestedComponents_list"]["parameters"]["query"]>;
type HarvestedComponentsListResponse = components["schemas"]["PaginatedHarvestedComponentList"];

type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrieveHarvestedComponents(
  queries?: HarvestedComponentsListQueries,
  config?: ListHookConfig,
  options?: Omit<UseQueryOptions<HarvestedComponentsListResponse, Error>, "queryKey" | "queryFn">
) {
  return useQuery<HarvestedComponentsListResponse, Error>({
    queryKey: ["harvested-components", queries, config],
    queryFn: () =>
      api.api_HarvestedComponents_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<HarvestedComponentsListResponse>,
    ...options,
  });
}

import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

type HarvestedComponentsListQueries = NonNullable<operations["api_HarvestedComponents_list"]["parameters"]["query"]>;
type HarvestedComponentsListResponse = components["schemas"]["PaginatedHarvestedComponentList"];

type ListHookConfig = {
  headers?: Record<string, string>;
};

export const retrieveHarvestedComponentsOptions = (queries?: HarvestedComponentsListQueries, config?: ListHookConfig) => queryOptions({
  queryKey: ["harvested-components", queries, config] as const,
  queryFn: () =>
    api.api_HarvestedComponents_list(
      (queries || config ? { queries, ...config } : undefined) as never,
    ) as Promise<HarvestedComponentsListResponse>,
});

export function useRetrieveHarvestedComponents(
  queries?: HarvestedComponentsListQueries,
  config?: ListHookConfig,
  options?: Omit<ReturnType<typeof retrieveHarvestedComponentsOptions>, "queryKey" | "queryFn">
) {
  return useQuery({
    ...retrieveHarvestedComponentsOptions(queries, config),
    ...options,
  });
}

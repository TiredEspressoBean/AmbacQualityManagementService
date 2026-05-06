import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

type CapasListQueries = NonNullable<operations["api_CAPAs_list"]["parameters"]["query"]>;
type CapasListResponse = components["schemas"]["PaginatedCAPAList"];

type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useListCapas(
  queries?: CapasListQueries,
  config?: ListHookConfig,
  options?: Omit<UseQueryOptions<CapasListResponse, Error>, "queryKey" | "queryFn">
) {
  return useQuery<CapasListResponse, Error>({
    queryKey: ["capas", queries, config],
    queryFn: () =>
      api.api_CAPAs_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<CapasListResponse>,
    ...options,
  });
}

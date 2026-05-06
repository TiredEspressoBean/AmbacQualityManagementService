import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

type CoresListQueries = NonNullable<operations["api_Cores_list"]["parameters"]["query"]>;
type CoresListResponse = components["schemas"]["PaginatedCoreListList"];

type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrieveCores(
  queries?: CoresListQueries,
  config?: ListHookConfig,
  options?: Omit<UseQueryOptions<CoresListResponse, Error>, "queryKey" | "queryFn">
) {
  return useQuery<CoresListResponse, Error>({
    queryKey: ["cores", queries, config],
    queryFn: () =>
      api.api_Cores_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<CoresListResponse>,
    ...options,
  });
}

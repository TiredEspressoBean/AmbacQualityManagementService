import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

type CoresListQueries = NonNullable<operations["api_Cores_list"]["parameters"]["query"]>;
type CoresListResponse = components["schemas"]["PaginatedCoreListList"];

type ListHookConfig = {
  headers?: Record<string, string>;
};

export const coresOptions = (queries?: CoresListQueries, config?: ListHookConfig) =>
  queryOptions({
    queryKey: ["cores", queries, config] as const,
    queryFn: () =>
      api.api_Cores_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<CoresListResponse>,
  });

export function useRetrieveCores(
  queries?: CoresListQueries,
  config?: ListHookConfig,
  options?: Omit<ReturnType<typeof coresOptions>, "queryKey" | "queryFn">
) {
  return useQuery({
    ...coresOptions(queries, config),
    ...options,
  });
}

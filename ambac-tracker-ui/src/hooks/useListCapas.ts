import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

type CapasListQueries = NonNullable<operations["api_CAPAs_list"]["parameters"]["query"]>;
type CapasListResponse = components["schemas"]["PaginatedCAPAList"];

type ListHookConfig = {
  headers?: Record<string, string>;
};

export const listCapasOptions = (queries?: CapasListQueries, config?: ListHookConfig) => queryOptions({
  queryKey: ["capas", queries, config] as const,
  queryFn: () =>
    api.api_CAPAs_list(
      (queries || config ? { queries, ...config } : undefined) as never,
    ) as Promise<CapasListResponse>,
});

export function useListCapas(
  queries?: CapasListQueries,
  config?: ListHookConfig,
  options?: Omit<ReturnType<typeof listCapasOptions>, "queryKey" | "queryFn">
) {
  return useQuery({
    ...listCapasOptions(queries, config),
    ...options,
  });
}

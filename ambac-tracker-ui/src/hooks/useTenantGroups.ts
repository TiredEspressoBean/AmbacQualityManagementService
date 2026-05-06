import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { components, operations } from "@/lib/api/generated-types";

type TenantGroupsListQueries = NonNullable<operations["api_TenantGroups_list"]["parameters"]["query"]>;
type TenantGroupsListResponse = components["schemas"]["PaginatedTenantGroupList"];

type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useTenantGroups(
  queries?: TenantGroupsListQueries,
  config?: ListHookConfig,
  options?: Omit<UseQueryOptions<TenantGroupsListResponse, Error>, "queryKey" | "queryFn">
) {
  return useQuery<TenantGroupsListResponse, Error>({
    queryKey: ["tenantGroups", queries, config],
    queryFn: () =>
      api.api_TenantGroups_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<TenantGroupsListResponse>,
    ...options,
  });
}

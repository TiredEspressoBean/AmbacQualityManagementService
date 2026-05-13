import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { components, operations } from "@/lib/api/generated-types";

type TenantGroupsListQueries = NonNullable<operations["api_TenantGroups_list"]["parameters"]["query"]>;
type TenantGroupsListResponse = components["schemas"]["PaginatedTenantGroupList"];

type ListHookConfig = {
  headers?: Record<string, string>;
};

export const tenantGroupsOptions = (queries?: TenantGroupsListQueries, config?: ListHookConfig) =>
  queryOptions({
    queryKey: ["tenantGroups", queries, config] as const,
    queryFn: () =>
      api.api_TenantGroups_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<TenantGroupsListResponse>,
  });

export function useTenantGroups(
  queries?: TenantGroupsListQueries,
  config?: ListHookConfig,
  options?: Omit<ReturnType<typeof tenantGroupsOptions>, "queryKey" | "queryFn">
) {
  return useQuery({
    ...tenantGroupsOptions(queries, config),
    ...options,
  });
}

import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { components, operations } from "@/lib/api/generated-types";

type GroupsListQueries = NonNullable<operations["api_Groups_list"]["parameters"]["query"]>;
type GroupsListResponse = components["schemas"]["PaginatedGroupList"];

type ListHookConfig = {
  headers?: Record<string, string>;
};

export const retrieveGroupsOptions = (queries?: GroupsListQueries, config?: ListHookConfig) => queryOptions({
  queryKey: ["groups", queries, config] as const,
  queryFn: () =>
    api.api_Groups_list(
      (queries || config ? { queries, ...config } : undefined) as never,
    ) as Promise<GroupsListResponse>,
});

export function useRetrieveGroups(
  queries?: GroupsListQueries,
  config?: ListHookConfig,
  options?: Omit<ReturnType<typeof retrieveGroupsOptions>, "queryKey" | "queryFn">
) {
  return useQuery({
    ...retrieveGroupsOptions(queries, config),
    ...options,
  });
}

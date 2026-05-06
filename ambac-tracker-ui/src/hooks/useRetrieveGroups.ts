import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { components, operations } from "@/lib/api/generated-types";

type GroupsListQueries = NonNullable<operations["api_Groups_list"]["parameters"]["query"]>;
type GroupsListResponse = components["schemas"]["PaginatedGroupList"];

type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrieveGroups(
  queries?: GroupsListQueries,
  config?: ListHookConfig,
  options?: Omit<UseQueryOptions<GroupsListResponse, Error>, "queryKey" | "queryFn">
) {
  return useQuery<GroupsListResponse, Error>({
    queryKey: ["groups", queries, config],
    queryFn: () =>
      api.api_Groups_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<GroupsListResponse>,
    ...options,
  });
}

import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

type UserListQueries = NonNullable<operations["api_User_list"]["parameters"]["query"]>;
type UserListResponse = components["schemas"]["PaginatedUserList"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export const usersOptions = (queries?: UserListQueries, config?: ListHookConfig) =>
  queryOptions({
    queryKey: ["user", queries, config] as const,
    queryFn: () =>
      api.api_User_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<UserListResponse>,
  });

export const usersMetadataOptions = () =>
  queryOptions({
    queryKey: ["metadata", "Users", "User"] as const,
    queryFn: () => api.api_User_metadata_retrieve(),
  });

export function useRetrieveUsers(
  queries?: UserListQueries,
  config?: ListHookConfig,
  options?: Omit<ReturnType<typeof usersOptions>, "queryKey" | "queryFn">
) {
  return useQuery({
    ...usersOptions(queries, config),
    ...options,
  });
}

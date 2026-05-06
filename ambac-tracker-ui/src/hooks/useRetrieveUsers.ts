import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

type UserListQueries = NonNullable<operations["api_User_list"]["parameters"]["query"]>;
type UserListResponse = components["schemas"]["PaginatedUserList"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrieveUsers(
  queries?: UserListQueries,
  config?: ListHookConfig,
  options?: Omit<
    UseQueryOptions<UserListResponse, Error>,
    "queryKey" | "queryFn"
  >
) {
  return useQuery<UserListResponse, Error>({
    queryKey: ["user", queries, config],
    queryFn: () =>
      api.api_User_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<UserListResponse>,
    ...options,
  });
}

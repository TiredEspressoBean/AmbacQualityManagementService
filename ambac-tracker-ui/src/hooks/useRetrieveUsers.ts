import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api, type PaginatedUserList } from "@/lib/api/generated.ts";

// Type for the query parameters (extracted from the Zodios endpoint)
type UserListQueries = Parameters<typeof api.api_User_list>[0] extends { queries?: infer Q } ? Q : Parameters<typeof api.api_User_list>[0];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrieveUsers(
  queries?: UserListQueries,
  config?: ListHookConfig,
  options?: Omit<
    UseQueryOptions<PaginatedUserList, Error>,
    "queryKey" | "queryFn"
  >
) {
  return useQuery<PaginatedUserList, Error>({
    queryKey: ["user", queries, config],
    queryFn: () => api.api_User_list(queries || config ? { queries, ...config } : undefined),
    ...options,
  });
}

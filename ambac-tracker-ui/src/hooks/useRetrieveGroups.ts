import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

// Extract queries type from Zodios endpoint
type GroupsListQueries = Parameters<typeof api.api_Groups_list>[0] extends { queries?: infer Q } ? Q : Parameters<typeof api.api_Groups_list>[0];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrieveGroups(
  queries?: GroupsListQueries,
  config?: ListHookConfig,
  options?: Omit<
    UseQueryOptions<
      Awaited<ReturnType<typeof api.api_Groups_list>>,
      Error
    >,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: ["groups", queries, config],
    queryFn: () => api.api_Groups_list(queries || config ? { queries, ...config } : undefined),
    ...options,
  });
}

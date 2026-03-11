import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

// Extract queries type from Zodios endpoint
type NotificationPreferencesListQueries = Parameters<typeof api.api_NotificationPreferences_list>[0] extends { queries?: infer Q } ? Q : Parameters<typeof api.api_NotificationPreferences_list>[0];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrieveNotificationPreferences(
  queries?: NotificationPreferencesListQueries,
  config?: ListHookConfig,
  options?: Omit<
    UseQueryOptions<
      Awaited<ReturnType<typeof api.api_NotificationPreferences_list>>,
      Error
    >,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: ["NotificationPreferences", queries, config],
    queryFn: () => api.api_NotificationPreferences_list(queries || config ? { queries, ...config } : undefined),
    ...options,
  });
}

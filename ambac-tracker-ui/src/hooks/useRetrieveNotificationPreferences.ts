import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

// Extract queries type from Zodios endpoint
type NotificationPreferencesListQueries = Parameters<typeof api.api_NotificationPreferences_list>[0] extends { queries?: infer Q } ? Q : Parameters<typeof api.api_NotificationPreferences_list>[0];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export const retrieveNotificationPreferencesOptions = (queries?: NotificationPreferencesListQueries, config?: ListHookConfig) => queryOptions({
  queryKey: ["NotificationPreferences", queries, config] as const,
  queryFn: () => api.api_NotificationPreferences_list(
    (queries || config ? { queries, ...config } : undefined) as never,
  ),
});

export function useRetrieveNotificationPreferences(
  queries?: NotificationPreferencesListQueries,
  config?: ListHookConfig,
  options?: Omit<ReturnType<typeof retrieveNotificationPreferencesOptions>, "queryKey" | "queryFn">
) {
  return useQuery({
    ...retrieveNotificationPreferencesOptions(queries, config),
    ...options,
  });
}

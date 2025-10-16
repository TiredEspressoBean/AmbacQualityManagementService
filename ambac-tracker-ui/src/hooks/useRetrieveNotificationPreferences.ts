import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export function useRetrieveNotificationPreferences(
  queries?: Parameters<typeof api.api_NotificationPreferences_list>[0],
  options?: Omit<
    UseQueryOptions<
      Awaited<ReturnType<typeof api.api_NotificationPreferences_list>>,
      Error
    >,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: ["NotificationPreferences", queries],
    queryFn: () => api.api_NotificationPreferences_list(queries),
    ...options,
  });
}

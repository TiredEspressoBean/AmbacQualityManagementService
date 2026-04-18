import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export function useIntegrationSyncLogs(
    query: Parameters<typeof api.api_integrations_sync_logs_list>[0],
    options?: { enabled?: boolean }
) {
    return useQuery({
        queryKey: ["integration-sync-logs", query],
        queryFn: () => api.api_integrations_sync_logs_list(query),
        enabled: options?.enabled ?? true,
    });
}

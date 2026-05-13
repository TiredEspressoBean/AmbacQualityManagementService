import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export const integrationSyncLogsOptions = (query: Parameters<typeof api.api_integrations_sync_logs_list>[0]) => queryOptions({
    queryKey: ["integration-sync-logs", query] as const,
    queryFn: () => api.api_integrations_sync_logs_list(query),
});

export function useIntegrationSyncLogs(query: Parameters<typeof api.api_integrations_sync_logs_list>[0], options?: { enabled?: boolean }){
    return useQuery({ ...integrationSyncLogsOptions(query), enabled: options?.enabled ?? true });
}

import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated.ts"

export function useRetrieveAuditLogEntries (queries: Parameters<typeof api.api_auditlog_list>[0]) {
    return useQuery({
        queryKey: ["logs", queries],
        queryFn: () => api.api_auditlog_list(queries),
    });
};
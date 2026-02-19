import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

export function useRetrieveAuditLogEntries(
  queries?: Parameters<typeof api.api_auditlog_list>[0],
  options?: Omit<
    UseQueryOptions<
      Awaited<ReturnType<typeof api.api_auditlog_list>>,
      Error
    >,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: ["logs", queries],
    queryFn: () => api.api_auditlog_list(queries),
    ...options,
  });
}
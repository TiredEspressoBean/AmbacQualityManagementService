import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

type AuditLogListQueries = NonNullable<operations["api_auditlog_list"]["parameters"]["query"]>;
type AuditLogListResponse = components["schemas"]["PaginatedAuditLogList"];

type ListHookConfig = {
  headers?: Record<string, string>;
};

export const auditLogOptions = (queries?: AuditLogListQueries, config?: ListHookConfig) =>
  queryOptions({
    queryKey: ["logs", queries, config] as const,
    queryFn: () =>
      api.api_auditlog_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<AuditLogListResponse>,
  });

export function useRetrieveAuditLogEntries(
  queries?: AuditLogListQueries,
  config?: ListHookConfig,
  options?: Omit<ReturnType<typeof auditLogOptions>, "queryKey" | "queryFn">
) {
  return useQuery({
    ...auditLogOptions(queries, config),
    ...options,
  });
}

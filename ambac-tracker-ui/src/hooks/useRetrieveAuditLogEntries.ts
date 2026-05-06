import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

type AuditLogListQueries = NonNullable<operations["api_auditlog_list"]["parameters"]["query"]>;
type AuditLogListResponse = components["schemas"]["PaginatedAuditLogList"];

type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrieveAuditLogEntries(
  queries?: AuditLogListQueries,
  config?: ListHookConfig,
  options?: Omit<UseQueryOptions<AuditLogListResponse, Error>, "queryKey" | "queryFn">
) {
  return useQuery<AuditLogListResponse, Error>({
    queryKey: ["logs", queries, config],
    queryFn: () =>
      api.api_auditlog_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<AuditLogListResponse>,
    ...options,
  });
}

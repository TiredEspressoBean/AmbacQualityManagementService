import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

// Extract queries type from Zodios endpoint
type ApprovalTemplatesListQueries = Parameters<typeof api.api_ApprovalTemplates_list>[0] extends { queries?: infer Q } ? Q : Parameters<typeof api.api_ApprovalTemplates_list>[0];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrieveApprovalTemplates(
  queries?: ApprovalTemplatesListQueries,
  config?: ListHookConfig,
  options?: Omit<
    UseQueryOptions<
      Awaited<ReturnType<typeof api.api_ApprovalTemplates_list>>,
      Error
    >,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: ["approval-template", queries, config],
    queryFn: () => api.api_ApprovalTemplates_list(queries || config ? { queries, ...config } : undefined),
    ...options,
  });
}

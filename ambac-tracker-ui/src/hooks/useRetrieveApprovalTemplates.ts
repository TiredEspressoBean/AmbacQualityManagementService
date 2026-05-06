import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { components, operations } from "@/lib/api/generated-types";

type ApprovalTemplatesListQueries = NonNullable<operations["api_ApprovalTemplates_list"]["parameters"]["query"]>;
type ApprovalTemplatesListResponse = components["schemas"]["PaginatedApprovalTemplateList"];

type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrieveApprovalTemplates(
  queries?: ApprovalTemplatesListQueries,
  config?: ListHookConfig,
  options?: Omit<UseQueryOptions<ApprovalTemplatesListResponse, Error>, "queryKey" | "queryFn">
) {
  return useQuery<ApprovalTemplatesListResponse, Error>({
    queryKey: ["approval-template", queries, config],
    queryFn: () =>
      api.api_ApprovalTemplates_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<ApprovalTemplatesListResponse>,
    ...options,
  });
}

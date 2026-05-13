import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { components, operations } from "@/lib/api/generated-types";

type ApprovalTemplatesListQueries = NonNullable<operations["api_ApprovalTemplates_list"]["parameters"]["query"]>;
type ApprovalTemplatesListResponse = components["schemas"]["PaginatedApprovalTemplateList"];

type ListHookConfig = {
  headers?: Record<string, string>;
};

export const approvalTemplatesOptions = (queries?: ApprovalTemplatesListQueries, config?: ListHookConfig) =>
  queryOptions({
    queryKey: ["approval-template", queries, config] as const,
    queryFn: () =>
      api.api_ApprovalTemplates_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<ApprovalTemplatesListResponse>,
  });

export const approvalTemplatesMetadataOptions = () =>
  queryOptions({
    queryKey: ["metadata", "ApprovalTemplates", "ApprovalTemplates"] as const,
    queryFn: () => api.api_ApprovalTemplates_metadata_retrieve(),
  });

export function useRetrieveApprovalTemplates(
  queries?: ApprovalTemplatesListQueries,
  config?: ListHookConfig,
  options?: Omit<ReturnType<typeof approvalTemplatesOptions>, "queryKey" | "queryFn">
) {
  return useQuery({
    ...approvalTemplatesOptions(queries, config),
    ...options,
  });
}

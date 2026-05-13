import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

// Strict types pulled from the OpenAPI spec (no zod passthrough leakage).
type WorkOrdersListQueries = NonNullable<operations["api_WorkOrders_list"]["parameters"]["query"]>;
type WorkOrdersListResponse = components["schemas"]["PaginatedWorkOrderListList"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export const workOrdersOptions = (queries?: WorkOrdersListQueries, config?: ListHookConfig) =>
  queryOptions({
    queryKey: ["work-order", queries, config] as const,
    queryFn: () =>
      api.api_WorkOrders_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<WorkOrdersListResponse>,
  });

export const workOrdersMetadataOptions = () =>
  queryOptions({
    queryKey: ["metadata", "WorkOrders", "WorkOrders"] as const,
    queryFn: () => api.api_WorkOrders_metadata_retrieve(),
  });

export function useRetrieveWorkOrders(
  queries?: WorkOrdersListQueries,
  config?: ListHookConfig,
  options?: Omit<ReturnType<typeof workOrdersOptions>, "queryKey" | "queryFn">
) {
  return useQuery({
    ...workOrdersOptions(queries, config),
    ...options,
  });
}

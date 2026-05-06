import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

// Strict types pulled from the OpenAPI spec (no zod passthrough leakage).
type WorkOrdersListQueries = NonNullable<operations["api_WorkOrders_list"]["parameters"]["query"]>;
type WorkOrdersListResponse = components["schemas"]["PaginatedWorkOrderListList"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrieveWorkOrders(
  queries?: WorkOrdersListQueries,
  config?: ListHookConfig,
  options?: Omit<
    UseQueryOptions<WorkOrdersListResponse, Error>,
    "queryKey" | "queryFn"
  >
) {
  return useQuery<WorkOrdersListResponse, Error>({
    queryKey: ["work-order", queries, config],
    queryFn: () =>
      api.api_WorkOrders_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<WorkOrdersListResponse>,
    ...options,
  });
}

import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

// Strict types pulled from the OpenAPI spec (no zod passthrough leakage).
type EquipmentListQueries = NonNullable<operations["api_Equipment_list"]["parameters"]["query"]>;
type EquipmentListResponse = components["schemas"]["PaginatedEquipmentsList"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrieveEquipments(
  queries?: EquipmentListQueries,
  config?: ListHookConfig,
  options?: Omit<
    UseQueryOptions<EquipmentListResponse, Error>,
    "queryKey" | "queryFn"
  >
) {
  return useQuery<EquipmentListResponse, Error>({
    queryKey: ["equipment", queries, config],
    queryFn: () =>
      api.api_Equipment_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<EquipmentListResponse>,
    ...options,
  });
}

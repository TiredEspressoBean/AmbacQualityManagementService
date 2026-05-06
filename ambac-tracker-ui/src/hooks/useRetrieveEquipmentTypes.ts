import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

// Strict types pulled from the OpenAPI spec (no zod passthrough leakage).
type EquipmentTypesListQueries = NonNullable<operations["api_Equipment_types_list"]["parameters"]["query"]>;
type EquipmentTypesListResponse = components["schemas"]["PaginatedEquipmentTypeList"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrieveEquipmentTypes(
  queries?: EquipmentTypesListQueries,
  config?: ListHookConfig,
  options?: Omit<
    UseQueryOptions<EquipmentTypesListResponse, Error>,
    "queryKey" | "queryFn"
  >
) {
  return useQuery<EquipmentTypesListResponse, Error>({
    queryKey: ["equipment-types", queries, config],
    queryFn: () =>
      api.api_Equipment_types_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<EquipmentTypesListResponse>,
    ...options,
  });
}

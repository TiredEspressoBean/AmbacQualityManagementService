import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

// Strict types pulled from the OpenAPI spec (no zod passthrough leakage).
type EquipmentTypesListQueries = NonNullable<operations["api_Equipment_types_list"]["parameters"]["query"]>;
type EquipmentTypesListResponse = components["schemas"]["PaginatedEquipmentTypeList"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export const equipmentTypesOptions = (queries?: EquipmentTypesListQueries, config?: ListHookConfig) =>
  queryOptions({
    queryKey: ["equipment-types", queries, config] as const,
    queryFn: () =>
      api.api_Equipment_types_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<EquipmentTypesListResponse>,
  });

export const equipmentTypesMetadataOptions = () =>
  queryOptions({
    queryKey: ["metadata", "EquipmentTypes", "Equipment-types"] as const,
    queryFn: () => api.api_Equipment_types_metadata_retrieve(),
  });

export function useRetrieveEquipmentTypes(
  queries?: EquipmentTypesListQueries,
  config?: ListHookConfig,
  options?: Omit<ReturnType<typeof equipmentTypesOptions>, "queryKey" | "queryFn">
) {
  return useQuery({
    ...equipmentTypesOptions(queries, config),
    ...options,
  });
}
